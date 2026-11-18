"""Tests for core.doctor() and the `doctor` CLI command.

core.doctor() is exercised directly with DATA_DIR / REGISTRY_FILE /
CONFIG_FILE monkey-patched at a sandbox; the CLI is exercised as a
subprocess with PJ_MANAGER_DATA_DIR pointed at a sandbox, exactly the
way an AI agent or script would use it.
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
sys.path.insert(0, str(SRC))

from pj_manager import core  # noqa: E402


class DoctorCoreTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self._orig = (core.DATA_DIR, core.REGISTRY_FILE, core.CONFIG_FILE)
        core.DATA_DIR = self.tmp / "data"
        core.REGISTRY_FILE = core.DATA_DIR / "projects.json"
        core.CONFIG_FILE = core.DATA_DIR / "config.json"

    def tearDown(self):
        core.DATA_DIR, core.REGISTRY_FILE, core.CONFIG_FILE = self._orig
        self._tmp.cleanup()

    def levels(self, result):
        return {c["name"]: c["level"] for c in result["checks"]}

    def test_empty_sandbox_is_healthy(self):
        """空のサンドボックスでは fail が無く、終了コード相当が ok。"""
        r = core.doctor()
        self.assertTrue(r["ok"])
        self.assertIn(r["status"], ("ok", "warn"))  # gh 未導入なら warn
        lv = self.levels(r)
        self.assertEqual(lv["python"], "ok")
        self.assertEqual(lv["venv"], "ok")
        self.assertEqual(lv["registry"], "ok")
        self.assertEqual(lv["data_dir"], "ok")
        self.assertEqual(
            r["summary"]["fail"], 0)
        self.assertEqual(
            r["summary"]["ok"] + r["summary"]["warn"],
            len(r["checks"]))

    def test_missing_project_folder_warns(self):
        """フォルダが無くなった登録は warn（fail ではない）。"""
        core.save_registry([{
            "name": "ghost", "path": str(self.tmp / "nope"),
            "created_at": "2026-11-16", "origin": "existing"}])
        r = core.doctor()
        self.assertEqual(self.levels(r)["registry"], "warn")
        self.assertTrue(r["ok"])
        detail = next(c for c in r["checks"]
                      if c["name"] == "registry")["detail"]
        self.assertIn("ghost", detail)

    def test_corrupt_registry_fails(self):
        """壊れた projects.json は fail。"""
        core.DATA_DIR.mkdir(parents=True, exist_ok=True)
        core.REGISTRY_FILE.write_text("{not json", encoding="utf-8")
        r = core.doctor()
        self.assertEqual(self.levels(r)["registry"], "fail")
        self.assertFalse(r["ok"])
        self.assertEqual(r["status"], "fail")

    def test_registry_not_a_list_fails(self):
        core.DATA_DIR.mkdir(parents=True, exist_ok=True)
        core.REGISTRY_FILE.write_text('{"name": "x"}', encoding="utf-8")
        r = core.doctor()
        self.assertEqual(self.levels(r)["registry"], "fail")
        self.assertFalse(r["ok"])

    def test_corrupt_config_warns(self):
        core.DATA_DIR.mkdir(parents=True, exist_ok=True)
        core.CONFIG_FILE.write_text("{not json", encoding="utf-8")
        r = core.doctor()
        self.assertEqual(self.levels(r)["config"], "warn")
        self.assertTrue(r["ok"])

    def test_projects_root_is_file_fails(self):
        """projects_root がファイルだと fail（create が弾くのに doctor が
        ok を出す矛盾を直す。v0.24.0 の create --root と同じ考え方）。"""
        blocker = self.tmp / "blocker"
        blocker.write_text("not a folder", encoding="utf-8")
        core.save_config({"projects_root": str(blocker), "language": "ja"})
        r = core.doctor()
        self.assertEqual(self.levels(r)["projects_root"], "fail")
        self.assertFalse(r["ok"])
        self.assertEqual(r["status"], "fail")
        check = next(c for c in r["checks"]
                     if c["name"] == "projects_root")
        self.assertIn(str(blocker), check["detail"])
        self.assertIn("config set-root", check.get("hint", ""))

    def test_projects_root_is_file_fails_in_english(self):
        blocker = self.tmp / "blocker"
        blocker.write_text("not a folder", encoding="utf-8")
        core.save_config({"projects_root": str(blocker), "language": "en"})
        r = core.doctor()
        self.assertEqual(self.levels(r)["projects_root"], "fail")
        check = next(c for c in r["checks"]
                     if c["name"] == "projects_root")
        self.assertIn("Not a folder", check["detail"])

    def test_projects_root_missing_but_creatable_stays_ok(self):
        """まだ無い projects_root（親が書き込める）は従来どおり ok。"""
        missing = self.tmp / "Projects"
        core.save_config({"projects_root": str(missing), "language": "ja"})
        r = core.doctor()
        self.assertEqual(self.levels(r)["projects_root"], "ok")
        self.assertEqual(r["summary"]["fail"], 0)


class DoctorCliTestCase(unittest.TestCase):
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

    def test_doctor_json(self):
        r = self.run_cli("doctor", "--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        result = json.loads(r.stdout)
        self.assertTrue(result["ok"])
        names = [c["name"] for c in result["checks"]]
        for want in ("python", "git", "gh", "projects_root",
                     "data_dir", "registry"):
            self.assertIn(want, names)

    def test_doctor_human_output(self):
        r = self.run_cli("doctor")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("python:", r.stdout)
        self.assertIn("status:", r.stdout)

    def test_doctor_projects_root_is_file_exits_1(self):
        """projects_root がファイルだと CLI の doctor は exit 1。"""
        blocker = self.tmp / "blocker"
        blocker.write_text("not a folder", encoding="utf-8")
        r = self.run_cli("config", "set-root", str(blocker), "--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        r = self.run_cli("doctor", "--json")
        self.assertEqual(r.returncode, 1, r.stdout)
        result = json.loads(r.stdout)
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "fail")
        check = next(c for c in result["checks"]
                     if c["name"] == "projects_root")
        self.assertEqual(check["level"], "fail")
        self.assertIn(str(blocker), check["detail"])


if __name__ == "__main__":
    unittest.main()
