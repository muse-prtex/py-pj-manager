"""Tests for the agent CLI (pj_manager.cli).

The CLI is exercised as a subprocess with PJ_MANAGER_DATA_DIR pointed at a
sandbox, exactly the way an AI agent or script would use it.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

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

    def test_create_list_status_flow(self):
        r = self.run_cli("create", "agent-demo", "--root", str(self.tmp / "Projects"),
                         "--no-venv", "--no-git", "--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        created = json.loads(r.stdout)
        self.assertTrue(created["ok"])
        self.assertEqual(created["project"]["name"], "agent-demo")

        r = self.run_cli("list", "--json")
        names = [p["name"] for p in json.loads(r.stdout)["projects"]]
        self.assertIn("agent-demo", names)

        r = self.run_cli("status", "agent-demo", "--json")
        status = json.loads(r.stdout)
        self.assertTrue(status["ok"])
        self.assertEqual(status["project"]["path"], created["project"]["path"])

    def test_error_is_json_with_exit_1(self):
        r = self.run_cli("status", "no-such-project", "--json")
        self.assertEqual(r.returncode, 1)
        self.assertFalse(json.loads(r.stdout)["ok"])

    def test_unregister_keeps_folder(self):
        proj = self.tmp / "keepme"
        proj.mkdir()
        r = self.run_cli("register", str(proj), "--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        r = self.run_cli("unregister", "keepme", "--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(proj.is_dir())


if __name__ == "__main__":
    unittest.main()
