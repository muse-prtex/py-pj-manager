"""Tests for `log -n` with an invalid count (0 or negative).

`log -n -1` used to pass "--1" straight to `git log`, so git failed
with its raw English "fatal: unrecognized argument: --1". `-n 0`
silently returned an empty list. A bad count is a caller error, so
the CLI now fails before calling git, with a friendly, localized
message that says what to do next — the same idea as the empty
commit message (v0.22.0). The check runs before the empty-repo
success path, so it also fails on a repository with no commits yet.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"


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
        (path / "extra.txt").write_text("hello", encoding="utf-8")
        r = self.run_cli("commit", name, "-m", "add extra", "--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        return path

    def test_log_negative_n_fails_japanese(self):
        self._create_committed()
        r = self.run_cli("log", "cli-proj", "-n", "-1")
        self.assertEqual(r.returncode, 1, r.stderr)
        self.assertIn("表示件数には1以上の整数を指定してください", r.stderr)
        self.assertNotIn("fatal:", r.stdout + r.stderr)

    def test_log_zero_n_fails_japanese(self):
        self._create_committed()
        r = self.run_cli("log", "cli-proj", "-n", "0")
        self.assertEqual(r.returncode, 1, r.stderr)
        self.assertIn("表示件数には1以上の整数を指定してください", r.stderr)
        self.assertNotIn("fatal:", r.stdout + r.stderr)

    def test_log_negative_n_fails_json(self):
        self._create_committed()
        r = self.run_cli("log", "cli-proj", "-n", "-1", "--json")
        self.assertEqual(r.returncode, 1, r.stderr)
        body = json.loads(r.stdout)
        self.assertFalse(body["ok"])
        self.assertIn("表示件数には1以上の整数を指定してください",
                      body["error"])
        self.assertNotIn("fatal:", r.stdout + r.stderr)

    def test_log_negative_n_fails_english(self):
        self._create_committed()
        r = self.run_cli("config", "set-language", "en", "--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        r = self.run_cli("log", "cli-proj", "-n", "-1")
        self.assertEqual(r.returncode, 1, r.stderr)
        self.assertIn("Number of commits must be a positive integer",
                      r.stderr)
        self.assertNotIn("fatal:", r.stdout + r.stderr)

    def test_log_zero_n_fails_on_empty_repo(self):
        # Validation runs before the empty-repo success path.
        self._create_empty_git()
        r = self.run_cli("log", "empty-proj", "-n", "0", "--json")
        self.assertEqual(r.returncode, 1, r.stderr)
        body = json.loads(r.stdout)
        self.assertFalse(body["ok"])
        self.assertIn("表示件数には1以上の整数を指定してください",
                      body["error"])

    def test_log_positive_n_still_works(self):
        self._create_committed()
        r = self.run_cli("log", "cli-proj", "-n", "1", "--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        body = json.loads(r.stdout)
        self.assertTrue(body["ok"])
        self.assertEqual(len(body["log"]), 1)
        self.assertIn("add extra", body["log"][0])
        r = self.run_cli("log", "cli-proj", "-n", "2", "--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(len(json.loads(r.stdout)["log"]), 2)


if __name__ == "__main__":
    unittest.main()
