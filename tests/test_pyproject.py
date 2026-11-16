"""Tests for the packaging metadata (pyproject.toml) and the `pj-manager`
console script entry point.

The packaging must stay dependency-free (the Python core is standard
library only) and the declared version must match pj_manager.__version__.
The console script itself is exercised as a subprocess the same way pip
would invoke it: `from pj_manager.cli import main; SystemExit(main(...))`.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10: tomllib arrived in 3.11
    try:
        import tomli as tomllib
    except ModuleNotFoundError:
        tomllib = None

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

sys.path.insert(0, str(SRC))

from pj_manager import __version__  # noqa: E402


@unittest.skipIf(tomllib is None, "tomllib/tomli unavailable")
class PyprojectTestCase(unittest.TestCase):
    def setUp(self):
        with open(ROOT / "pyproject.toml", "rb") as f:
            self.meta = tomllib.load(f)

    def test_build_system_is_setuptools(self):
        build = self.meta["build-system"]
        self.assertEqual(build["build-backend"], "setuptools.build_meta")
        self.assertTrue(any(r.startswith("setuptools")
                            for r in build["requires"]))

    def test_project_name_and_no_dependencies(self):
        project = self.meta["project"]
        self.assertEqual(project["name"], "py-pj-manager")
        # The Python core is standard library only — keep it that way.
        self.assertEqual(project["dependencies"], [])
        self.assertIn("3.10", project["requires-python"])

    def test_version_matches_package(self):
        dynamic = self.meta["tool"]["setuptools"]["dynamic"]
        self.assertEqual(dynamic["version"],
                         {"attr": "pj_manager.__version__"})
        # PEP 621: a dynamic field must be declared in [project].dynamic,
        # otherwise setuptools rejects the file (caught by a real install).
        self.assertIn("version", self.meta["project"]["dynamic"])
        # The version comes from the package, not from this file.
        self.assertRegex(__version__, r"^\d+\.\d+\.\d+$")

    def test_console_script_entry_point(self):
        scripts = self.meta["project"]["scripts"]
        self.assertEqual(scripts["pj-manager"], "pj_manager.cli:main")
        # The target must be importable and callable, like a console
        # script wrapper expects.
        from pj_manager.cli import main
        self.assertTrue(callable(main))

    def test_src_layout_packages(self):
        find = self.meta["tool"]["setuptools"]["packages"]["find"]
        self.assertEqual(find["where"], ["src"])


class ConsoleScriptTestCase(unittest.TestCase):
    """Run the entry-point function the way an installed console script
    would, in a sandbox data dir."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.env = dict(os.environ)
        self.env["PYTHONPATH"] = str(SRC)
        self.env["PJ_MANAGER_DATA_DIR"] = str(self.tmp / "data")

    def tearDown(self):
        self._tmp.cleanup()

    def run_entry_point(self, *argv):
        code = ("from pj_manager.cli import main\n"
                "import sys\n"
                f"sys.exit(main({list(argv)!r}))\n")
        return subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True, text=True, env=self.env, timeout=120,
        )

    def test_entry_point_list_json(self):
        r = self.run_entry_point("list", "--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout),
                         {"ok": True, "projects": []})

    def test_entry_point_create_and_doctor(self):
        r = self.run_entry_point(
            "create", "entry-demo", "--root", str(self.tmp / "Projects"),
            "--no-venv", "--no-git", "--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(json.loads(r.stdout)["ok"])
        r = self.run_entry_point("doctor", "--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        result = json.loads(r.stdout)
        self.assertIn(result["status"], ("ok", "warn", "fail"))


if __name__ == "__main__":
    unittest.main()
