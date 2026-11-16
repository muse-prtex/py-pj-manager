"""Tests for `create` when the destination is blocked by a file.

`create --root <a file>` used to fail with Python's raw
`FileExistsError: [Errno 17] File exists: ...`, and a `--root` whose
parent is a file failed with a raw `NotADirectoryError`. A target
name that already exists as a file was reported as \"the same folder
already exists\", which is misleading. All three are caller errors,
so `create_project` now fails before touching anything, with a
friendly, localized message that says what to do next — the same
idea as the empty commit message (v0.22.0) and the invalid `log -n`
count (v0.23.0). A failure leaves no folder and no registry entry
behind, and a later create with a good root still works.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pj_manager import core, i18n

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"


class CoreTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self._orig_registry = core.REGISTRY_FILE
        self._orig_config = core.CONFIG_FILE
        core.REGISTRY_FILE = self.tmp / "data" / "projects.json"
        core.CONFIG_FILE = self.tmp / "data" / "config.json"
        (self.tmp / "data").mkdir()

    def tearDown(self):
        core.REGISTRY_FILE = self._orig_registry
        core.CONFIG_FILE = self._orig_config
        self._tmp.cleanup()

    def _create(self, name, root):
        return core.create_project(name, root, make_venv=False,
                                   init_git=False, log=lambda *a: None)


class TestCreateRootIsFile(CoreTestCase):
    def test_root_is_file_fails_friendly(self):
        blocker = self.tmp / "somefile.txt"
        blocker.write_text("not a folder", encoding="utf-8")
        with self.assertRaises(ValueError) as cm:
            self._create("demo", blocker)
        self.assertEqual(str(cm.exception),
                         i18n.t("root_not_a_folder", lang="ja", path=blocker))
        self.assertNotIn("FileExistsError", str(cm.exception))
        self.assertNotIn("Errno", str(cm.exception))
        # Nothing was created or registered.
        self.assertFalse((self.tmp / "demo").exists())
        self.assertEqual(core.load_registry(), [])

    def test_root_is_file_in_english(self):
        core.save_config({"language": "en"})
        blocker = self.tmp / "somefile.txt"
        blocker.write_text("not a folder", encoding="utf-8")
        with self.assertRaises(ValueError) as cm:
            self._create("demo", blocker)
        self.assertEqual(str(cm.exception),
                         'The destination is not a folder: '
                         f'{blocker} (a file exists there. '
                         'Pick another location)')

    def test_root_parent_is_file_fails_friendly(self):
        blocker = self.tmp / "blocker.txt"
        blocker.write_text("not a folder", encoding="utf-8")
        with self.assertRaises(ValueError) as cm:
            self._create("demo", blocker / "sub")
        self.assertEqual(str(cm.exception),
                         i18n.t("root_parent_is_file", lang="ja",
                                path=blocker / "sub"))
        self.assertNotIn("NotADirectoryError", str(cm.exception))
        self.assertNotIn("Errno", str(cm.exception))
        self.assertEqual(core.load_registry(), [])

    def test_target_name_is_file_fails_as_file_not_folder(self):
        root = self.tmp / "Projects"
        root.mkdir()
        (root / "demo").write_text("a file, not a folder", encoding="utf-8")
        with self.assertRaises(ValueError) as cm:
            self._create("demo", root)
        self.assertEqual(str(cm.exception),
                         i18n.t("file_exists", lang="ja", path=root / "demo"))
        self.assertNotIn("フォルダがすでにあります", str(cm.exception))
        self.assertEqual(core.load_registry(), [])

    def test_create_still_works_after_failed_attempts(self):
        blocker = self.tmp / "somefile.txt"
        blocker.write_text("not a folder", encoding="utf-8")
        with self.assertRaises(ValueError):
            self._create("demo", blocker)
        entry = self._create("demo", self.tmp / "Projects")
        self.assertEqual(entry["name"], "demo")
        self.assertTrue((self.tmp / "Projects" / "demo").is_dir())
        self.assertEqual(len(core.load_registry()), 1)


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

    def test_cli_root_is_file_friendly(self):
        blocker = self.tmp / "somefile.txt"
        blocker.write_text("not a folder", encoding="utf-8")
        r = self.run_cli("create", "demo", "--root", str(blocker),
                         "--no-venv", "--no-git")
        self.assertEqual(r.returncode, 1)
        self.assertIn("作成先がフォルダではありません", r.stderr)
        self.assertNotIn("FileExistsError", r.stderr)
        self.assertNotIn("Errno", r.stderr)

    def test_cli_root_is_file_json(self):
        blocker = self.tmp / "somefile.txt"
        blocker.write_text("not a folder", encoding="utf-8")
        r = self.run_cli("create", "demo", "--root", str(blocker),
                         "--no-venv", "--no-git", "--json")
        self.assertEqual(r.returncode, 1)
        body = json.loads(r.stdout)
        self.assertFalse(body["ok"])
        self.assertIn("作成先がフォルダではありません", body["error"])
        self.assertNotIn("FileExistsError", body["error"])

    def test_cli_root_is_file_english(self):
        self.run_cli("config", "set-language", "en", "--json")
        blocker = self.tmp / "somefile.txt"
        blocker.write_text("not a folder", encoding="utf-8")
        r = self.run_cli("create", "demo", "--root", str(blocker),
                         "--no-venv", "--no-git")
        self.assertEqual(r.returncode, 1)
        self.assertIn("The destination is not a folder", r.stderr)
        self.assertNotIn("FileExistsError", r.stderr)

    def test_cli_target_name_is_file_friendly(self):
        root = self.tmp / "Projects"
        root.mkdir()
        (root / "demo").write_text("a file", encoding="utf-8")
        r = self.run_cli("create", "demo", "--root", str(root),
                         "--no-venv", "--no-git")
        self.assertEqual(r.returncode, 1)
        self.assertIn("同じ名前のファイルがすでにあります", r.stderr)
        self.assertNotIn("フォルダがすでにあります", r.stderr)


if __name__ == "__main__":
    unittest.main()
