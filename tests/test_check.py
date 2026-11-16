"""Tests for core.check_all() / project_health() and the `check` CLI.

The cross-project health check: one JSON object with every registered
project's state (ok / attention / missing), its git numbers (dirty /
ahead / behind), venv presence, and a summary. A missing folder is the
only thing that makes the overall result not-ok (same thinking as
doctor: dirty / ahead / behind / no-venv are attention, not failure).
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from pj_manager import core  # noqa: E402

GIT_ENV = dict(os.environ, GIT_AUTHOR_NAME="test", GIT_AUTHOR_EMAIL="t@t",
               GIT_COMMITTER_NAME="test", GIT_COMMITTER_EMAIL="t@t")


def _git(*args, cwd):
    ok, out = core.run_cmd(["git", *args], cwd=cwd)
    assert ok, out
    return out


def _make_repo(path: Path, commit: bool = True) -> None:
    path.mkdir(parents=True, exist_ok=True)
    _git("init", "-b", "main", cwd=path)
    (path / "main.py").write_text("print('hi')\n", encoding="utf-8")
    # .venv は実プロジェクトと同じく無視対象（作った後に dirty 扱い
    # にならないように、コミット前に .gitignore へ入れておく）。
    (path / ".gitignore").write_text(".venv/\n", encoding="utf-8")
    if commit:
        _git("add", "-A", cwd=path)
        # run_cmd does not take env, so commit through subprocess here.
        subprocess.run(["git", "commit", "-m", "init"], cwd=path,
                       env=GIT_ENV, capture_output=True, check=True)


def _fake_venv(path: Path) -> None:
    (path / ".venv" / "bin").mkdir(parents=True, exist_ok=True)
    (path / ".venv" / "bin" / "activate").write_text("", encoding="utf-8")


class CheckCoreTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self._orig = (core.DATA_DIR, core.REGISTRY_FILE, core.CONFIG_FILE)
        core.DATA_DIR = self.tmp / "data"
        core.REGISTRY_FILE = core.DATA_DIR / "projects.json"
        core.CONFIG_FILE = core.DATA_DIR / "config.json"
        self.projects = self.tmp / "projects"
        self.projects.mkdir()

    def tearDown(self):
        core.DATA_DIR, core.REGISTRY_FILE, core.CONFIG_FILE = self._orig
        self._tmp.cleanup()

    def register(self, name, path):
        entries = core.load_registry()
        entries.append({"name": name, "path": str(path),
                        "created_at": "2026-11-16", "origin": "existing"})
        core.save_registry(entries)

    def test_empty_registry_is_ok(self):
        r = core.check_all()
        self.assertTrue(r["ok"])
        self.assertEqual(r["projects"], [])
        self.assertEqual(r["summary"]["total"], 0)

    def test_clean_project_with_venv_is_ok(self):
        p = self.projects / "clean"
        _make_repo(p)
        _fake_venv(p)
        self.register("clean", p)
        r = core.check_all()
        self.assertTrue(r["ok"])
        (proj,) = r["projects"]
        self.assertEqual(proj["state"], "ok")
        self.assertEqual(proj["issues"], [])
        self.assertTrue(proj["has_venv"])
        self.assertEqual(proj["git"]["dirty"], 0)
        self.assertEqual(r["summary"], {
            "total": 1, "ok": 1, "attention": 0, "missing": 0,
            "dirty": 0, "ahead": 0, "behind": 0, "no_venv": 0,
            "not_git": 0})

    def test_dirty_project_is_attention_not_failure(self):
        p = self.projects / "dirty"
        _make_repo(p)
        (p / "main.py").write_text("print('changed')\n", encoding="utf-8")
        self.register("dirty", p)
        r = core.check_all()
        self.assertTrue(r["ok"])  # attention keeps the overall ok
        (proj,) = r["projects"]
        self.assertEqual(proj["state"], "attention")
        self.assertIn("dirty:1", proj["issues"])
        self.assertIn("no-venv", proj["issues"])
        self.assertEqual(r["summary"]["dirty"], 1)
        self.assertEqual(r["summary"]["no_venv"], 1)

    def test_ahead_and_behind_against_a_bare_remote(self):
        remote = self.tmp / "remote.git"
        subprocess.run(["git", "init", "--bare", str(remote)],
                       capture_output=True, check=True)
        # clone が main をチェックアウトするよう、bare 側の HEAD を main に。
        _git("symbolic-ref", "HEAD", "refs/heads/main", cwd=remote)
        ahead = self.projects / "ahead"
        _make_repo(ahead)
        _git("remote", "add", "origin", str(remote), cwd=ahead)
        _git("push", "-u", "origin", "main", cwd=ahead)
        (ahead / "main.py").write_text("print('v2')\n", encoding="utf-8")
        _git("add", "-A", cwd=ahead)
        subprocess.run(["git", "commit", "-m", "v2"], cwd=ahead,
                       env=GIT_ENV, capture_output=True, check=True)

        behind = self.projects / "behind"
        _make_repo(behind)
        _git("remote", "add", "origin", str(remote), cwd=behind)
        _git("fetch", "origin", cwd=behind)
        # ローカルの main をリモートの main に合わせる（_make_repo の
        # 初期コミットとは別物なので reset で置き換える）。
        _git("reset", "--hard", "origin/main", cwd=behind)
        # behind を数えるには upstream が要る（ahead 側は push -u で設定済み）。
        _git("branch", "--set-upstream-to=origin/main", "main", cwd=behind)
        # A second clone moves the remote forward; behind then fetches.
        clone = self.tmp / "clone"
        subprocess.run(["git", "clone", "-q", str(remote), str(clone)],
                       capture_output=True, check=True)
        (clone / "other.py").write_text("x = 1\n", encoding="utf-8")
        _git("add", "-A", cwd=clone)
        subprocess.run(["git", "commit", "-m", "other"], cwd=clone,
                       env=GIT_ENV, capture_output=True, check=True)
        _git("push", "origin", "main", cwd=clone)
        _git("fetch", "origin", cwd=behind)

        self.register("ahead", ahead)
        self.register("behind", behind)
        r = core.check_all()
        by_name = {p["name"]: p for p in r["projects"]}
        self.assertEqual(by_name["ahead"]["git"]["ahead"], 1)
        self.assertIn("ahead:1", by_name["ahead"]["issues"])
        self.assertEqual(by_name["behind"]["git"]["behind"], 1)
        self.assertIn("behind:1", by_name["behind"]["issues"])
        self.assertEqual(r["summary"]["ahead"], 1)
        self.assertEqual(r["summary"]["behind"], 1)
        self.assertTrue(r["ok"])

    def test_non_git_folder_is_attention(self):
        p = self.projects / "plain"
        p.mkdir()
        (p / "notes.txt").write_text("hi\n", encoding="utf-8")
        self.register("plain", p)
        r = core.check_all()
        (proj,) = r["projects"]
        self.assertEqual(proj["state"], "attention")
        self.assertIn("not-git", proj["issues"])
        self.assertFalse(proj["git"]["is_git"])
        self.assertEqual(r["summary"]["not_git"], 1)

    def test_missing_folder_is_the_only_failure(self):
        p = self.projects / "ghost"
        p.mkdir()
        self.register("ghost", p)
        shutil.rmtree(p)
        r = core.check_all()
        self.assertFalse(r["ok"])
        (proj,) = r["projects"]
        self.assertEqual(proj["state"], "missing")
        self.assertEqual(proj["issues"], ["missing"])
        self.assertFalse(proj["has_venv"])
        self.assertEqual(r["summary"]["missing"], 1)
        # A missing folder is not counted as no-venv / not-git.
        self.assertEqual(r["summary"]["no_venv"], 0)
        self.assertEqual(r["summary"]["not_git"], 0)

    def test_mixed_summary_counts(self):
        clean = self.projects / "clean"
        _make_repo(clean)
        _fake_venv(clean)
        dirty = self.projects / "dirty"
        _make_repo(dirty)
        (dirty / "main.py").write_text("print('x')\n", encoding="utf-8")
        ghost = self.projects / "ghost"
        ghost.mkdir()
        self.register("clean", clean)
        self.register("dirty", dirty)
        self.register("ghost", ghost)
        shutil.rmtree(ghost)
        r = core.check_all()
        self.assertFalse(r["ok"])
        self.assertEqual(r["summary"]["total"], 3)
        self.assertEqual(r["summary"]["ok"], 1)
        self.assertEqual(r["summary"]["attention"], 1)
        self.assertEqual(r["summary"]["missing"], 1)


class CheckCliTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.env = dict(os.environ)
        self.env["PYTHONPATH"] = str(SRC)
        self.env["PJ_MANAGER_DATA_DIR"] = str(self.tmp / "data")

    def tearDown(self):
        self._tmp.cleanup()

    def run_cli(self, *argv):
        return subprocess.run(
            [sys.executable, "-m", "pj_manager.cli", *argv],
            capture_output=True, text=True, env=self.env, timeout=120,
        )

    def test_check_json_empty(self):
        r = self.run_cli("check", "--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        result = json.loads(r.stdout)
        self.assertTrue(result["ok"])
        self.assertEqual(result["projects"], [])
        self.assertEqual(result["summary"]["total"], 0)

    def test_check_human_output(self):
        r = self.run_cli("check")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("check: 0 projects", r.stdout)

    def test_check_exit_code_1_when_missing(self):
        # Register a folder, then delete it: check must fail (exit 1).
        folder = self.tmp / "gone"
        folder.mkdir()
        r = self.run_cli("register", str(folder), "--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        shutil.rmtree(folder)
        r = self.run_cli("check", "--json")
        self.assertEqual(r.returncode, 1)
        result = json.loads(r.stdout)
        self.assertFalse(result["ok"])
        self.assertEqual(result["projects"][0]["state"], "missing")

    def test_check_reports_dirty_real_project(self):
        folder = self.tmp / "real"
        _make_repo(folder)
        r = self.run_cli("register", str(folder), "--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        (folder / "main.py").write_text("print('dirty')\n", encoding="utf-8")
        r = self.run_cli("check", "--json")
        self.assertEqual(r.returncode, 0, r.stderr)  # attention, not failure
        result = json.loads(r.stdout)
        self.assertTrue(result["ok"])
        (proj,) = result["projects"]
        self.assertEqual(proj["state"], "attention")
        self.assertEqual(proj["git"]["dirty"], 1)


if __name__ == "__main__":
    unittest.main()
