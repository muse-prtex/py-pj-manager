"""Tests for `log` on a repository with no commits yet.

`git log` on a fresh `git init` (no commits) exits 128 with
"fatal: your current branch 'main' does not have any commits yet".
An empty history is not a failure — the desired end state (showing
the history, which happens to be empty) already holds — so `log`
returns success with an empty list and a friendly, localized message,
the same idea as committing a clean tree. A real failure (e.g. a
corrupt repository) must still fail.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pj_manager import cli, core

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"


def _make_plain_git_project(tmp: Path, name: str = "proj") -> Path:
    """A git repo with no commits: plain folder + register + init."""
    path = tmp / "root" / name
    path.mkdir(parents=True)
    core.register_existing(path)
    ok, out = core.git_op(path, "init", "-b", "main")
    assert ok, out
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

    def test_has_commits_false_before_first_commit(self):
        if core.shutil.which("git") is None:
            self.skipTest("git not available")
        path = _make_plain_git_project(self.tmp)
        self.assertFalse(core.has_commits(path))

    def test_has_commits_true_after_first_commit(self):
        if core.shutil.which("git") is None:
            self.skipTest("git not available")
        path = _make_plain_git_project(self.tmp)
        core.git_op(path, "config", "user.email", "test@example.com")
        core.git_op(path, "config", "user.name", "Test")
        (path / "file.txt").write_text("hello", encoding="utf-8")
        ok, out = core.commit_all(path, "first")
        self.assertTrue(ok, out)
        self.assertTrue(core.has_commits(path))


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

    def _create_empty_git(self, name="empty-proj"):
        path = self.tmp / "Projects" / name
        path.mkdir(parents=True)
        r = self.run_cli("register", str(path), "--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        r = self.run_cli("init", name, "--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        return path

    def _create_committed(self, name="cli-proj"):
        r = self.run_cli("create", name, "--root", str(self.tmp / "Projects"),
                         "--no-venv", "--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        path = Path(json.loads(r.stdout)["project"]["path"])
        subprocess.run(["git", "-C", str(path), "config", "user.email",
                        "test@example.com"], check=True, timeout=30)
        subprocess.run(["git", "-C", str(path), "config", "user.name",
                        "Test"], check=True, timeout=30)
        return path

    def test_log_empty_repo_succeeds_json(self):
        self._create_empty_git()
        r = self.run_cli("log", "empty-proj", "--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        body = json.loads(r.stdout)
        self.assertTrue(body["ok"])
        self.assertEqual(body["log"], [])

    def test_log_empty_repo_human_japanese(self):
        self._create_empty_git()
        r = self.run_cli("log", "empty-proj")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("まだコミットがありません", r.stdout)
        self.assertNotIn("fatal:", r.stdout + r.stderr)

    def test_log_empty_repo_human_english(self):
        self._create_empty_git()
        r = self.run_cli("config", "set-language", "en", "--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        r = self.run_cli("log", "empty-proj")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("No commits yet", r.stdout)

    def test_log_with_commits_still_lists_them(self):
        path = self._create_committed()
        (path / "extra.txt").write_text("hello", encoding="utf-8")
        r = self.run_cli("commit", "cli-proj", "-m", "add extra", "--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        r = self.run_cli("log", "cli-proj", "--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        body = json.loads(r.stdout)
        self.assertTrue(body["ok"])
        self.assertEqual(len(body["log"]), 2)
        self.assertIn("Initial commit", body["log"][1])
        self.assertIn("add extra", body["log"][0])

    def test_log_n_limits_output(self):
        path = self._create_committed()
        (path / "extra.txt").write_text("hello", encoding="utf-8")
        r = self.run_cli("commit", "cli-proj", "-m", "add extra", "--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        r = self.run_cli("log", "cli-proj", "-n", "1", "--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        body = json.loads(r.stdout)
        self.assertEqual(len(body["log"]), 1)
        self.assertIn("add extra", body["log"][0])

    def test_log_on_non_git_folder_still_fails(self):
        path = self.tmp / "Projects" / "plain"
        path.mkdir(parents=True)
        r = self.run_cli("register", str(path), "--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        r = self.run_cli("log", "plain", "--json")
        self.assertEqual(r.returncode, 1, r.stderr)
        body = json.loads(r.stdout)
        self.assertFalse(body["ok"])


if __name__ == "__main__":
    unittest.main()
