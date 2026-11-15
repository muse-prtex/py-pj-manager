"""Smoke tests for pj_manager.core (standard library unittest only).

Run from the repository root:

    python -m unittest discover -s tests -v
"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pj_manager import core


class CoreTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        # Redirect the registry/config files into the sandbox.
        self._orig_registry = core.REGISTRY_FILE
        self._orig_config = core.CONFIG_FILE
        core.REGISTRY_FILE = self.tmp / "projects.json"
        core.CONFIG_FILE = self.tmp / "config.json"

    def tearDown(self):
        core.REGISTRY_FILE = self._orig_registry
        core.CONFIG_FILE = self._orig_config
        self._tmp.cleanup()


class TestRegistry(CoreTestCase):
    def test_register_and_unregister_existing(self):
        proj = self.tmp / "demo"
        proj.mkdir()
        entry = core.register_existing(proj)
        self.assertEqual(entry["name"], "demo")
        self.assertEqual(len(core.load_registry()), 1)
        # The folder itself must survive unregistering.
        self.assertTrue(core.unregister("demo"))
        self.assertTrue(proj.is_dir())
        self.assertEqual(core.load_registry(), [])
        self.assertFalse(core.unregister("demo"))

    def test_register_duplicate_rejected(self):
        proj = self.tmp / "demo"
        proj.mkdir()
        core.register_existing(proj)
        with self.assertRaises(ValueError):
            core.register_existing(proj)

    def test_register_missing_folder_rejected(self):
        with self.assertRaises(ValueError):
            core.register_existing(self.tmp / "does-not-exist")


class TestCreateProject(CoreTestCase):
    def test_create_python_project_without_venv_or_git(self):
        entry = core.create_project(
            "my-proj", self.tmp / "root",
            make_venv=False, init_git=False, log=lambda *a: None,
        )
        path = Path(entry["path"])
        self.assertTrue((path / "main.py").is_file())
        self.assertTrue((path / "README.md").is_file())
        self.assertTrue((path / "requirements.txt").is_file())
        self.assertEqual(core.load_registry()[0]["name"], "my-proj")

    def test_invalid_names_rejected(self):
        for bad in ["", " ", "-lead", "with space", "日本語", "a/b"]:
            with self.assertRaises(ValueError, msg=bad):
                core.create_project(
                    bad, self.tmp / "root",
                    make_venv=False, init_git=False, log=lambda *a: None,
                )

    def test_duplicate_folder_rejected(self):
        (self.tmp / "root" / "dup").mkdir(parents=True)
        with self.assertRaises(ValueError):
            core.create_project(
                "dup", self.tmp / "root",
                make_venv=False, init_git=False, log=lambda *a: None,
            )


class TestGit(CoreTestCase):
    def test_git_status_and_commit(self):
        if core.shutil.which("git") is None:
            self.skipTest("git not available")
        entry = core.create_project(
            "gitproj", self.tmp / "root",
            make_venv=False, init_git=True, log=lambda *a: None,
        )
        path = Path(entry["path"])
        status = core.git_status(path)
        self.assertTrue(status.get("is_git"))
        core.git_op(path, "config", "user.email", "test@example.com")
        core.git_op(path, "config", "user.name", "Test")
        (path / "extra.txt").write_text("hello", encoding="utf-8")
        ok, _ = core.commit_all(path, "add extra")
        self.assertTrue(ok)
        status = core.git_status(path)
        self.assertEqual(status.get("dirty", 0), 0)


if __name__ == "__main__":
    unittest.main()
