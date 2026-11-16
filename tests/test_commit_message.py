"""Tests for committing with an empty commit message
(pj_manager.core.commit_all).

An empty (-m "" or whitespace-only) commit message is not a git
mystery: git exits 1 with "Aborting commit due to empty commit
message." The fix is the same as the clean-tree commit (v0.17.0),
the no-identity commit (v0.21.0) and friends: fail (exit 1 — the
desired end state, a commit, is not met) with a friendly, localized
message that says what to do next, before running `git add -A`, so
a failed attempt leaves nothing staged.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pj_manager import cli, core, i18n

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"


def _make_git_project(tmp: Path, name: str = "proj") -> Path:
    entry = core.create_project(
        name, tmp / "root",
        make_venv=False, init_git=True, log=lambda *a: None,
    )
    path = Path(entry["path"])
    core.git_op(path, "config", "user.email", "test@example.com")
    core.git_op(path, "config", "user.name", "Test")
    return path


def _log_count(path: Path) -> int:
    ok, log = core.git_op(path, "log", "--oneline")
    assert ok
    return len(log.splitlines())


def _staged_files(path: Path) -> list[str]:
    ok, out = core.git_op(path, "diff", "--cached", "--name-only")
    assert ok
    return [ln for ln in out.splitlines() if ln.strip()]


class CoreTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self._orig_registry = core.REGISTRY_FILE
        self._orig_config = core.CONFIG_FILE
        core.REGISTRY_FILE = self.tmp / "projects.json"
        core.CONFIG_FILE = self.tmp / "config.json"

    def tearDown(self):
        core.REGISTRY_FILE = self._orig_registry
        core.CONFIG_FILE = self._orig_config
        self._tmp.cleanup()


class TestCommitEmptyMessage(CoreTestCase):
    def test_empty_message_fails_friendly(self):
        if core.shutil.which("git") is None:
            self.skipTest("git not available")
        path = _make_git_project(self.tmp)
        (path / "extra.txt").write_text("hello", encoding="utf-8")
        ok, out = core.commit_all(path, "")
        self.assertFalse(ok)
        self.assertEqual(out, i18n.t("core_empty_commit_message", lang="ja"))
        self.assertNotIn("Aborting commit", out)
        # No commit was created and nothing was staged.
        self.assertEqual(_log_count(path), 1)
        self.assertEqual(_staged_files(path), [])
        self.assertEqual(core.git_status(path)["dirty"], 1)

    def test_whitespace_only_message_fails_friendly(self):
        if core.shutil.which("git") is None:
            self.skipTest("git not available")
        path = _make_git_project(self.tmp)
        (path / "extra.txt").write_text("hello", encoding="utf-8")
        ok, out = core.commit_all(path, "   \n\t ")
        self.assertFalse(ok)
        self.assertEqual(out, i18n.t("core_empty_commit_message", lang="ja"))
        self.assertNotIn("Aborting commit", out)
        self.assertEqual(_log_count(path), 1)
        self.assertEqual(_staged_files(path), [])

    def test_empty_message_in_english(self):
        if core.shutil.which("git") is None:
            self.skipTest("git not available")
        core.save_config({"projects_root": str(self.tmp / "root"),
                          "language": "en"})
        path = _make_git_project(self.tmp)
        (path / "extra.txt").write_text("hello", encoding="utf-8")
        ok, out = core.commit_all(path, "")
        self.assertFalse(ok)
        self.assertEqual(out, 'Commit message is empty (specify one with -m "message")')

    def test_empty_message_on_clean_tree_still_fails(self):
        # An empty message is a caller error even when there is nothing
        # to commit: the clean-tree success (v0.17.0) must not swallow it.
        if core.shutil.which("git") is None:
            self.skipTest("git not available")
        path = _make_git_project(self.tmp)
        ok, out = core.commit_all(path, "")
        self.assertFalse(ok)
        self.assertIn("コミットメッセージが空です", out)
        self.assertEqual(_log_count(path), 1)

    def test_real_message_still_commits_after_failed_empty_one(self):
        if core.shutil.which("git") is None:
            self.skipTest("git not available")
        path = _make_git_project(self.tmp)
        (path / "extra.txt").write_text("hello", encoding="utf-8")
        ok, _out = core.commit_all(path, "")
        self.assertFalse(ok)
        ok, _out = core.commit_all(path, "add extra")
        self.assertTrue(ok)
        self.assertEqual(_log_count(path), 2)


class CliTestCase(unittest.TestCase):
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

    def _create(self, name="cli-proj"):
        r = self.run_cli("create", name, "--root", str(self.tmp / "Projects"),
                         "--no-venv", "--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        path = Path(json.loads(r.stdout)["project"]["path"])
        subprocess.run(["git", "-C", str(path), "config", "user.email",
                        "test@example.com"], check=True, timeout=30)
        subprocess.run(["git", "-C", str(path), "config", "user.name",
                        "Test"], check=True, timeout=30)
        (path / "extra.txt").write_text("hello", encoding="utf-8")
        return path

    def test_cli_commit_empty_message_human_output(self):
        self._create()
        r = self.run_cli("commit", "cli-proj", "-m", "")
        self.assertEqual(r.returncode, 1, r.stderr)
        self.assertIn("コミットメッセージが空です", r.stderr)
        self.assertNotIn("Aborting commit", r.stderr)

    def test_cli_commit_empty_message_json(self):
        self._create()
        r = self.run_cli("commit", "cli-proj", "-m", "", "--json")
        self.assertEqual(r.returncode, 1, r.stderr)
        body = json.loads(r.stdout)
        self.assertFalse(body["ok"])
        self.assertIn("コミットメッセージが空です", body["error"])
        self.assertNotIn("Aborting commit", body["error"])

    def test_cli_commit_empty_message_in_english(self):
        self._create()
        r = self.run_cli("config", "set-language", "en", "--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        r = self.run_cli("commit", "cli-proj", "-m", "   ", "--json")
        self.assertEqual(r.returncode, 1, r.stderr)
        body = json.loads(r.stdout)
        self.assertFalse(body["ok"])
        self.assertEqual(body["error"],
                         'Commit message is empty (specify one with -m "message")')


if __name__ == "__main__":
    unittest.main()
