"""Tests for `status` / `list` on a registered project whose folder is gone.

A "ghost" registration used to look healthy: `status` printed
"git: not a repository" with exit 0 (the folder does not exist at all —
it is not a non-git folder), and `list` showed the ghost exactly like a
live project. `status` now fails with the folder-missing message (the
same `folder_missing` string the git commands already use) and `list`
marks the row `[missing]`, matching how `check` treats missing folders.
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


class StatusMissingTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.env = dict(os.environ)
        self.env["PYTHONPATH"] = str(SRC)
        self.env["PJ_MANAGER_DATA_DIR"] = str(self.tmp / "data")
        self.projects_root = self.tmp / "Projects"

    def tearDown(self):
        self._tmp.cleanup()

    def run_cli(self, *argv):
        return subprocess.run(
            [sys.executable, "-m", "pj_manager.cli", *argv],
            capture_output=True, text=True, env=self.env, timeout=120,
        )

    def _make_ghost(self, name="ghost-demo"):
        r = self.run_cli("create", name, "--root", str(self.projects_root),
                         "--no-venv", "--no-git", "--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        shutil.rmtree(self.projects_root / name)
        return self.projects_root / name

    def test_status_ghost_fails_json(self):
        path = self._make_ghost()
        r = self.run_cli("status", "ghost-demo", "--json")
        self.assertEqual(r.returncode, 1, r.stdout)
        body = json.loads(r.stdout)
        self.assertFalse(body["ok"])
        self.assertIn(str(path), body["error"])

    def test_status_ghost_fails_human_ja(self):
        self._make_ghost()
        r = self.run_cli("status", "ghost-demo")
        self.assertEqual(r.returncode, 1)
        self.assertIn("フォルダがありません", r.stderr)
        self.assertNotIn("not a repository", r.stderr)

    def test_status_ghost_fails_human_en(self):
        self._make_ghost()
        r = self.run_cli("config", "set-language", "en", "--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        r = self.run_cli("status", "ghost-demo")
        self.assertEqual(r.returncode, 1)
        self.assertIn("Folder not found", r.stderr)

    def test_status_live_still_ok(self):
        r = self.run_cli("create", "live-demo", "--root",
                         str(self.projects_root), "--no-venv", "--no-git",
                         "--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        r = self.run_cli("status", "live-demo", "--json")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertTrue(json.loads(r.stdout)["ok"])

    def test_status_unregistered_missing_path_still_not_found(self):
        # An unregistered path that does not exist keeps the old
        # "project not found" error (it never reaches the folder check).
        r = self.run_cli("status", str(self.tmp / "no-such-folder"), "--json")
        self.assertEqual(r.returncode, 1)
        self.assertFalse(json.loads(r.stdout)["ok"])

    def test_list_marks_missing_human(self):
        self._make_ghost()
        r = self.run_cli("create", "live-demo", "--root",
                         str(self.projects_root), "--no-venv", "--no-git",
                         "--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        r = self.run_cli("list")
        self.assertEqual(r.returncode, 0, r.stderr)
        ghost_line = next(ln for ln in r.stdout.splitlines()
                          if "ghost-demo" in ln)
        live_line = next(ln for ln in r.stdout.splitlines()
                         if "live-demo" in ln)
        self.assertIn("[missing]", ghost_line)
        self.assertNotIn("[missing]", live_line)

    def test_list_json_keeps_exists_flag(self):
        self._make_ghost()
        r = self.run_cli("list", "--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        projects = json.loads(r.stdout)["projects"]
        self.assertEqual(len(projects), 1)
        self.assertFalse(projects[0]["exists"])
        self.assertFalse(projects[0]["has_venv"])


if __name__ == "__main__":
    unittest.main()
