"""Tests for committing a clean tree (pj_manager.core.commit_all).

A commit with nothing to commit is not a failure: git exits 1 with
"nothing to commit", but the desired end state (everything committed)
already holds, so commit_all reports success with a friendly,
localized message instead of surfacing git's raw output as an error.
A real failure (e.g. a hook rejecting the commit while changes are
staged) must still fail.
"""

import json
import os
import stat
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


class TestCommitCleanTree(CoreTestCase):
    def test_clean_tree_commit_succeeds(self):
        if core.shutil.which("git") is None:
            self.skipTest("git not available")
        path = _make_git_project(self.tmp)
        ok, out = core.commit_all(path, "nothing to commit")
        self.assertTrue(ok)
        self.assertEqual(out, i18n.t("core_nothing_to_commit", lang="ja"))
        # No new commit was created.
        ok, log = core.git_op(path, "log", "--oneline")
        self.assertTrue(ok)
        self.assertEqual(len(log.splitlines()), 1)

    def test_commit_with_changes_creates_commit(self):
        if core.shutil.which("git") is None:
            self.skipTest("git not available")
        path = _make_git_project(self.tmp)
        (path / "extra.txt").write_text("hello", encoding="utf-8")
        ok, out = core.commit_all(path, "add extra")
        self.assertTrue(ok)
        self.assertNotIn("コミットする変更はありません", out)
        ok, log = core.git_op(path, "log", "--oneline")
        self.assertEqual(len(log.splitlines()), 2)

    def test_real_failure_still_fails(self):
        if core.shutil.which("git") is None:
            self.skipTest("git not available")
        path = _make_git_project(self.tmp)
        hook = path / ".git" / "hooks" / "pre-commit"
        hook.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
        hook.chmod(hook.stat().st_mode | stat.S_IXUSR)
        (path / "extra.txt").write_text("hello", encoding="utf-8")
        ok, out = core.commit_all(path, "blocked by hook")
        self.assertFalse(ok)
        self.assertNotIn("コミットする変更はありません", out)
        # The staged change is still there: the failure is real.
        self.assertEqual(core.git_status(path)["dirty"], 1)

    def test_nothing_to_commit_message_in_english(self):
        if core.shutil.which("git") is None:
            self.skipTest("git not available")
        core.save_config({"projects_root": str(self.tmp / "root"),
                          "language": "en"})
        path = _make_git_project(self.tmp)
        ok, out = core.commit_all(path, "nothing to commit")
        self.assertTrue(ok)
        self.assertEqual(out, "Nothing to commit (working tree clean)")


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
        return path

    def test_cli_commit_clean_tree_exits_zero(self):
        self._create()
        r = self.run_cli("commit", "cli-proj", "-m", "second try", "--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        body = json.loads(r.stdout)
        self.assertTrue(body["ok"])
        self.assertIn("コミットする変更はありません", body["output"])

    def test_cli_commit_clean_tree_human_output(self):
        self._create()
        r = self.run_cli("commit", "cli-proj", "-m", "second try")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("コミットする変更はありません", r.stdout)

    def test_cli_commit_clean_tree_in_english(self):
        self._create()
        r = self.run_cli("config", "set-language", "en", "--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        r = self.run_cli("commit", "cli-proj", "-m", "second try", "--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Nothing to commit", json.loads(r.stdout)["output"])


if __name__ == "__main__":
    unittest.main()
