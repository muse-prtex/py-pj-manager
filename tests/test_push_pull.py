"""Tests for `push` / `pull` with no remote or no upstream branch.

A freshly created project has a local repository with no remote, so
`push` used to exit 1 with git's raw English output ("fatal: No
configured push destination." / "The current branch main has no
upstream branch." / "There is no tracking information for the current
branch."). The desired end state (pushed / pulled) is not met, so the
commands still fail — but now with a friendly, localized message that
says what to do next, the same idea as the clean-tree commit (v0.17.0)
and the empty-repo log (v0.19.0). A real failure (an unreachable
remote, an authentication error) still passes git's output through
unchanged. Detection uses exit codes only (`git remote`,
`git rev-parse @{u}`), never git's message text.
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


def _make_committed_project(tmp: Path, name: str = "proj") -> Path:
    """A git repo with one commit: plain folder + register + init + commit."""
    path = tmp / "root" / name
    path.mkdir(parents=True)
    core.register_existing(path)
    ok, out = core.git_op(path, "init", "-b", "main")
    assert ok, out
    core.git_op(path, "config", "user.email", "test@example.com")
    core.git_op(path, "config", "user.name", "Test")
    (path / "file.txt").write_text("hello", encoding="utf-8")
    ok, out = core.commit_all(path, "first")
    assert ok, out
    return path


def _make_bare_remote(tmp: Path, name: str = "remote.git") -> Path:
    path = tmp / name
    ok, out = core.git_op(tmp, "init", "--bare", "-q", str(path))
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

    def test_upstream_state_no_remote(self):
        if core.shutil.which("git") is None:
            self.skipTest("git not available")
        path = _make_committed_project(self.tmp)
        self.assertEqual(core.upstream_state(path), "no-remote")

    def test_upstream_state_no_upstream_after_remote_add(self):
        if core.shutil.which("git") is None:
            self.skipTest("git not available")
        path = _make_committed_project(self.tmp)
        remote = _make_bare_remote(self.tmp)
        ok, out = core.git_op(path, "remote", "add", "origin", str(remote))
        self.assertTrue(ok, out)
        self.assertEqual(core.upstream_state(path), "no-upstream")

    def test_upstream_state_ok_after_set_upstream(self):
        if core.shutil.which("git") is None:
            self.skipTest("git not available")
        path = _make_committed_project(self.tmp)
        remote = _make_bare_remote(self.tmp)
        core.git_op(path, "remote", "add", "origin", str(remote))
        ok, out = core.git_op(path, "push", "--set-upstream",
                              "origin", "main")
        self.assertTrue(ok, out)
        self.assertEqual(core.upstream_state(path), "ok")

    def test_push_no_remote_is_friendly_not_raw(self):
        if core.shutil.which("git") is None:
            self.skipTest("git not available")
        path = _make_committed_project(self.tmp)
        ok, out = core.git_push_pull(path, "push")
        self.assertFalse(ok)
        self.assertIn("リモートが設定されていません", out)
        self.assertIn("git remote add origin", out)
        self.assertNotIn("fatal:", out)

    def test_pull_no_remote_is_friendly_not_raw(self):
        if core.shutil.which("git") is None:
            self.skipTest("git not available")
        path = _make_committed_project(self.tmp)
        ok, out = core.git_push_pull(path, "pull")
        self.assertFalse(ok)
        self.assertIn("リモートが設定されていません", out)
        self.assertNotIn("fatal:", out)

    def test_push_no_upstream_names_set_upstream_command(self):
        if core.shutil.which("git") is None:
            self.skipTest("git not available")
        path = _make_committed_project(self.tmp)
        remote = _make_bare_remote(self.tmp)
        core.git_op(path, "remote", "add", "origin", str(remote))
        ok, out = core.git_push_pull(path, "push")
        self.assertFalse(ok)
        self.assertIn("上流ブランチが設定されていません", out)
        self.assertIn("git push --set-upstream origin main", out)
        self.assertNotIn("fatal:", out)

    def test_pull_no_upstream_names_pull_command(self):
        if core.shutil.which("git") is None:
            self.skipTest("git not available")
        path = _make_committed_project(self.tmp)
        remote = _make_bare_remote(self.tmp)
        core.git_op(path, "remote", "add", "origin", str(remote))
        ok, out = core.git_push_pull(path, "pull")
        self.assertFalse(ok)
        self.assertIn("上流ブランチが設定されていません", out)
        self.assertIn("git pull origin main", out)
        self.assertNotIn("fatal:", out)

    def test_push_with_upstream_still_succeeds(self):
        if core.shutil.which("git") is None:
            self.skipTest("git not available")
        path = _make_committed_project(self.tmp)
        remote = _make_bare_remote(self.tmp)
        core.git_op(path, "remote", "add", "origin", str(remote))
        ok, out = core.git_op(path, "push", "--set-upstream",
                              "origin", "main")
        self.assertTrue(ok, out)
        ok, out = core.git_push_pull(path, "push")
        self.assertTrue(ok, out)

    def test_push_unreachable_remote_stays_raw(self):
        if core.shutil.which("git") is None:
            self.skipTest("git not available")
        path = _make_committed_project(self.tmp)
        remote = _make_bare_remote(self.tmp)
        core.git_op(path, "remote", "add", "origin", str(remote))
        ok, out = core.git_op(path, "push", "--set-upstream",
                              "origin", "main")
        self.assertTrue(ok, out)
        core.git_op(path, "remote", "set-url", "origin",
                    str(self.tmp / "gone.git"))
        ok, out = core.git_push_pull(path, "push")
        self.assertFalse(ok)
        self.assertIn("fatal:", out)
        self.assertNotIn("リモートが設定されていません", out)
        self.assertNotIn("上流ブランチが設定されていません", out)

    def test_push_empty_repo_stays_raw(self):
        if core.shutil.which("git") is None:
            self.skipTest("git not available")
        path = self.tmp / "root" / "empty"
        path.mkdir(parents=True)
        core.register_existing(path)
        ok, out = core.git_op(path, "init", "-b", "main")
        self.assertTrue(ok, out)
        remote = _make_bare_remote(self.tmp)
        core.git_op(path, "remote", "add", "origin", str(remote))
        ok, out = core.git_push_pull(path, "push")
        self.assertFalse(ok)
        self.assertNotIn("上流ブランチが設定されていません", out)
        self.assertNotIn("リモートが設定されていません", out)


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

    def _create(self, name="push-demo"):
        r = self.run_cli("create", name, "--root", str(self.tmp / "Projects"),
                         "--no-venv", "--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        path = Path(json.loads(r.stdout)["project"]["path"])
        subprocess.run(["git", "-C", str(path), "config", "user.email",
                        "test@example.com"], check=True, timeout=30)
        subprocess.run(["git", "-C", str(path), "config", "user.name",
                        "Test"], check=True, timeout=30)
        return path

    def _add_bare_remote(self, path: Path) -> Path:
        remote = self.tmp / "remote.git"
        subprocess.run(["git", "init", "--bare", "-q", str(remote)],
                       check=True, timeout=30)
        subprocess.run(["git", "-C", str(path), "remote", "add",
                        "origin", str(remote)], check=True, timeout=30)
        return remote

    def test_push_no_remote_human_japanese(self):
        self._create()
        r = self.run_cli("push", "push-demo")
        self.assertEqual(r.returncode, 1, r.stderr)
        self.assertIn("リモートが設定されていません", r.stderr)
        self.assertNotIn("fatal:", r.stdout + r.stderr)

    def test_push_no_remote_json(self):
        self._create()
        r = self.run_cli("push", "push-demo", "--json")
        self.assertEqual(r.returncode, 1, r.stderr)
        body = json.loads(r.stdout)
        self.assertFalse(body["ok"])
        self.assertIn("リモートが設定されていません", body["error"])

    def test_push_no_upstream_human_english(self):
        path = self._create()
        self._add_bare_remote(path)
        r = self.run_cli("config", "set-language", "en", "--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        r = self.run_cli("push", "push-demo")
        self.assertEqual(r.returncode, 1, r.stderr)
        self.assertIn("No upstream branch is configured", r.stderr)
        self.assertIn("git push --set-upstream origin main", r.stderr)
        self.assertNotIn("fatal:", r.stdout + r.stderr)

    def test_pull_no_upstream_human_japanese(self):
        path = self._create()
        self._add_bare_remote(path)
        r = self.run_cli("pull", "push-demo")
        self.assertEqual(r.returncode, 1, r.stderr)
        self.assertIn("上流ブランチが設定されていません", r.stderr)
        self.assertIn("git pull origin main", r.stderr)
        self.assertNotIn("fatal:", r.stdout + r.stderr)

    def test_push_with_upstream_succeeds(self):
        path = self._create()
        self._add_bare_remote(path)
        r = subprocess.run(["git", "-C", str(path), "push",
                            "--set-upstream", "origin", "main"],
                           capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)
        r = self.run_cli("push", "push-demo", "--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        body = json.loads(r.stdout)
        self.assertTrue(body["ok"])


if __name__ == "__main__":
    unittest.main()
