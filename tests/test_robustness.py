"""Robustness tests: boundary cases found by actually exercising the CLI.

- Japanese-named folders, deep/long paths
- git-uninitialized folders and ghost (deleted) registrations
- duplicate names (register / create), symlink duplicates
- corrupt / malformed / empty registry and config files
- over-long project names

The CLI is exercised as a subprocess with PJ_MANAGER_DATA_DIR pointed
at a sandbox, exactly the way an AI agent or script would use it.
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


class RobustCliTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.work = self.tmp / "work"
        self.work.mkdir()
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

    def out_json(self, result):
        return json.loads(result.stdout)

    def registry_path(self):
        return self.tmp / "data" / "projects.json"

    # ---- empty registry ----
    def test_empty_registry_list_and_doctor(self):
        r = self.run_cli("list", "--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.out_json(r)["projects"], [])
        r = self.run_cli("list")
        self.assertEqual(r.returncode, 0)
        self.assertIn("no projects", r.stdout)
        r = self.run_cli("doctor", "--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        checks = {c["name"]: c for c in self.out_json(r)["checks"]}
        self.assertEqual(checks["registry"]["level"], "ok")
        self.assertEqual(checks["config"]["level"], "ok")

    def test_empty_registry_files_are_not_corrupt(self):
        data = self.tmp / "data"
        data.mkdir()
        (data / "projects.json").write_text("", encoding="utf-8")
        (data / "config.json").write_text("  \n", encoding="utf-8")
        r = self.run_cli("doctor", "--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        checks = {c["name"]: c for c in self.out_json(r)["checks"]}
        self.assertEqual(checks["registry"]["level"], "ok")
        self.assertEqual(checks["config"]["level"], "ok")
        r = self.run_cli("list", "--json")
        self.assertEqual(self.out_json(r)["projects"], [])

    # ---- Japanese names & long paths ----
    def test_japanese_folder_name_round_trip(self):
        proj = self.work / "日本語プロジェクト"
        proj.mkdir()
        r = self.run_cli("register", str(proj), "--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.out_json(r)["project"]["name"],
                         "日本語プロジェクト")
        r = self.run_cli("status", "日本語プロジェクト", "--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(self.out_json(r)["project"]["exists"])
        r = self.run_cli("unregister", "日本語プロジェクト", "--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(proj.is_dir())  # フォルダは残る

    def test_deep_long_path_registers(self):
        deep = self.work.joinpath(*(["abcdefghij"] * 18))
        deep.mkdir(parents=True)
        self.assertGreater(len(str(deep).encode()), 200)
        r = self.run_cli("register", str(deep), "--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        r = self.run_cli("status", str(deep), "--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(self.out_json(r)["project"]["exists"])

    # ---- git-uninitialized folders ----
    def test_non_git_folder_git_commands_fail_friendly(self):
        proj = self.work / "plain"
        proj.mkdir()
        (proj / "note.txt").write_text("hello", encoding="utf-8")
        r = self.run_cli("register", str(proj), "--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        status = self.out_json(self.run_cli("status", "plain", "--json"))
        self.assertFalse(status["project"]["git"]["is_git"])
        for argv in (("commit", "plain", "-m", "x"),
                     ("log", "plain"), ("push", "plain")):
            r = self.run_cli(*argv, "--json")
            self.assertEqual(r.returncode, 1, argv)
            err = self.out_json(r)["error"]
            self.assertIn("git リポジトリではありません", err)
            self.assertNotIn("fatal:", err)
        r = self.run_cli("init", "plain", "--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        status = self.out_json(self.run_cli("status", "plain", "--json"))
        self.assertTrue(status["project"]["git"]["is_git"])
        self.assertEqual(status["project"]["git"]["branch"], "main")

    # ---- ghost registrations ----
    def test_ghost_folder_operations_fail_friendly(self):
        proj = self.work / "ghosty"
        proj.mkdir()
        self.run_cli("register", str(proj), "--json")
        proj.rmdir()
        status = self.out_json(self.run_cli("status", "ghosty", "--json"))
        self.assertFalse(status["project"]["exists"])
        for argv in (("commit", "ghosty", "-m", "x"),
                     ("init", "ghosty")):
            r = self.run_cli(*argv, "--json")
            self.assertEqual(r.returncode, 1, argv)
            err = self.out_json(r)["error"]
            self.assertIn("フォルダがありません", err)
            self.assertNotIn("コマンドが見つかりません", err)

    # ---- duplicate names ----
    def test_duplicate_name_rejected_on_register_and_create(self):
        a = self.work / "a" / "dup-name"
        b = self.work / "b" / "dup-name"
        a.mkdir(parents=True)
        b.mkdir(parents=True)
        r = self.run_cli("register", str(a), "--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        r = self.run_cli("register", str(b), "--json")
        self.assertEqual(r.returncode, 1)
        self.assertIn("同じ名前", self.out_json(r)["error"])
        # 同名で create しても二重登録にならない
        r = self.run_cli("create", "dup-name", "--root",
                         str(self.work / "other"), "--no-venv",
                         "--no-git", "--json")
        self.assertEqual(r.returncode, 1)
        self.assertIn("同じ名前", self.out_json(r)["error"])
        names = [p["name"] for p in
                 self.out_json(self.run_cli("list", "--json"))["projects"]]
        self.assertEqual(names.count("dup-name"), 1)

    def test_symlink_duplicate_rejected(self):
        proj = self.work / "plain"
        proj.mkdir()
        self.run_cli("register", str(proj), "--json")
        link = self.work / "plain-link"
        link.symlink_to(proj, target_is_directory=True)
        r = self.run_cli("register", str(link), "--json")
        self.assertEqual(r.returncode, 1)
        self.assertIn("すでに登録されています", self.out_json(r)["error"])

    # ---- corrupt / malformed registry ----
    def test_corrupt_registry_is_backed_up_on_register(self):
        data = self.tmp / "data"
        data.mkdir()
        (data / "projects.json").write_text("{not json", encoding="utf-8")
        proj = self.work / "fresh"
        proj.mkdir()
        r = self.run_cli("register", str(proj), "--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        backups = sorted(data.glob("projects.json.bak-*"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_text(encoding="utf-8"), "{not json")
        self.assertEqual(len(self.out_json(
            self.run_cli("list", "--json"))["projects"]), 1)

    def test_malformed_entries_do_not_crash_list(self):
        data = self.tmp / "data"
        data.mkdir()
        (data / "projects.json").write_text(json.dumps([
            {"name": "good", "path": str(self.work / "fresh"),
             "created_at": "2026-11-16", "origin": "existing"},
            {"name": "nopath"},
            "just-a-string",
            {"name": "alsogood", "path": str(self.work / "plain"),
             "created_at": "2026-11-16", "origin": "existing"},
        ], ensure_ascii=False), encoding="utf-8")
        (self.work / "fresh").mkdir()
        (self.work / "plain").mkdir()
        r = self.run_cli("list", "--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        names = [p["name"] for p in self.out_json(r)["projects"]]
        self.assertEqual(names, ["good", "alsogood"])  # ファイル順を保つ
        r = self.run_cli("doctor", "--json")
        checks = {c["name"]: c for c in self.out_json(r)["checks"]}
        self.assertEqual(checks["registry"]["level"], "warn")
        self.assertIn("読み取れない", checks["registry"]["detail"])
        # 次の保存で読み取れない件は .bak へ退避される
        (self.work / "another").mkdir()
        r = self.run_cli("register", str(self.work / "another"), "--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(len(list(data.glob("projects.json.bak-*"))), 1)

    def test_duplicate_names_in_registry_warn_in_doctor(self):
        data = self.tmp / "data"
        data.mkdir()
        (data / "projects.json").write_text(json.dumps([
            {"name": "dup", "path": str(self.work / "a"),
             "created_at": "2026-11-16", "origin": "existing"},
            {"name": "dup", "path": str(self.work / "b"),
             "created_at": "2026-11-16", "origin": "existing"},
        ]), encoding="utf-8")
        (self.work / "a").mkdir()
        (self.work / "b").mkdir()
        r = self.run_cli("doctor", "--json")
        checks = {c["name"]: c for c in self.out_json(r)["checks"]}
        self.assertEqual(checks["registry"]["level"], "warn")
        self.assertIn("重複", checks["registry"]["detail"])

    # ---- over-long names ----
    def test_overlong_project_name_rejected_friendly(self):
        r = self.run_cli("create", "x" * 300, "--root", str(self.work),
                         "--no-venv", "--no-git", "--json")
        self.assertEqual(r.returncode, 1)
        err = self.out_json(r)["error"]
        self.assertIn("長すぎます", err)
        self.assertNotIn("OSError", err)
        self.assertNotIn("Errno 36", err)


class RobustCoreTestCase(unittest.TestCase):
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

    def test_run_cmd_missing_cwd_reports_folder(self):
        ok, out = core.run_cmd(["git", "status"],
                               cwd=self.tmp / "does-not-exist")
        self.assertFalse(ok)
        self.assertIn("フォルダがありません", out)
        self.assertNotIn("コマンドが見つかりません", out)

    def test_load_registry_filters_malformed(self):
        core.DATA_DIR.mkdir(parents=True, exist_ok=True)
        core.REGISTRY_FILE.write_text(
            '[{"name": "ok", "path": "/tmp"}, {"name": "bad"}, 42]',
            encoding="utf-8")
        entries = core.load_registry()
        self.assertEqual([e["name"] for e in entries], ["ok"])


if __name__ == "__main__":
    unittest.main()
