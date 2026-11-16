"""Tests for git identity handling (pj_manager.core).

When git user.name / user.email is not set, `git commit` exits 128 with
the raw English "Author identity unknown / Please tell me who you are".
The desired end state (a commit) is not met, so commit_all still fails —
but with a friendly, localized message that gives the two
`git config --global` commands, instead of git's raw output. Detection
is `core.git_identity_configured()` (`git config user.name` /
`user.email` exit codes, plus the GIT_AUTHOR_* / GIT_COMMITTER_*
fallbacks git itself honors), so it does not depend on git's message
text (which changes with locale). A commit on a clean tree still
succeeds with no identity set — there is nothing to commit.
`doctor` warns about a missing *global* identity (per-repository
identity still works for commits, and the hint says so).
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pj_manager import cli, core, i18n  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

# No global / system git config at all, so `git config user.name`
# reports "not set" (exit 1) unless the repo has a local identity or
# the GIT_AUTHOR_* / GIT_COMMITTER_* env vars fill it in.
ISOLATED_GIT = {"GIT_CONFIG_GLOBAL": "/dev/null",
                "GIT_CONFIG_SYSTEM": "/dev/null"}

IDENTITY_ENV = {"GIT_AUTHOR_NAME": "Env Author",
                "GIT_AUTHOR_EMAIL": "author@example.com",
                "GIT_COMMITTER_NAME": "Env Committer",
                "GIT_COMMITTER_EMAIL": "committer@example.com"}


def _make_project(tmp: Path, name: str = "proj",
                  local_identity: bool = False) -> Path:
    entry = core.create_project(
        name, tmp / "root",
        make_venv=False, init_git=True, log=lambda *a: None,
    )
    path = Path(entry["path"])
    if local_identity:
        core.git_op(path, "config", "user.email", "local@example.com")
        core.git_op(path, "config", "user.name", "Local")
    return path


def _dirty(path: Path) -> None:
    (path / "main.py").write_text(
        (path / "main.py").read_text(encoding="utf-8") + "\n# change\n",
        encoding="utf-8")


def _commit_count(path: Path) -> int:
    ok, out = core.git_op(path, "rev-list", "--count", "HEAD")
    return int(out) if ok else -1


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

    def set_language(self, lang: str) -> None:
        core.CONFIG_FILE.write_text(
            json.dumps({"language": lang}, ensure_ascii=False),
            encoding="utf-8")


class TestGitIdentityConfigured(CoreTestCase):
    def test_identity_from_global_config(self):
        if core.shutil.which("git") is None:
            self.skipTest("git not available")
        path = _make_project(self.tmp)
        # This VM has a global identity (user.name / user.email set),
        # so the effective identity is configured with no local config.
        self.assertTrue(core.git_identity_configured(path))

    def test_identity_from_local_config(self):
        if core.shutil.which("git") is None:
            self.skipTest("git not available")
        path = _make_project(self.tmp, local_identity=True)
        with mock.patch.dict(os.environ, ISOLATED_GIT):
            self.assertTrue(core.git_identity_configured(path))

    def test_identity_missing(self):
        if core.shutil.which("git") is None:
            self.skipTest("git not available")
        path = _make_project(self.tmp)
        with mock.patch.dict(os.environ, ISOLATED_GIT):
            self.assertFalse(core.git_identity_configured(path))

    def test_identity_from_env_vars(self):
        if core.shutil.which("git") is None:
            self.skipTest("git not available")
        path = _make_project(self.tmp)
        env = dict(ISOLATED_GIT, **IDENTITY_ENV)
        with mock.patch.dict(os.environ, env):
            self.assertTrue(core.git_identity_configured(path))

    def test_identity_env_author_only_is_not_enough(self):
        if core.shutil.which("git") is None:
            self.skipTest("git not available")
        path = _make_project(self.tmp)
        env = dict(ISOLATED_GIT,
                   GIT_AUTHOR_NAME="Env Author",
                   GIT_AUTHOR_EMAIL="author@example.com")
        with mock.patch.dict(os.environ, env):
            # The committer side is still unresolved, so git commit
            # would fail — the check must not claim success.
            self.assertFalse(core.git_identity_configured(path))


class TestCommitWithoutIdentity(CoreTestCase):
    def test_commit_fails_friendly_ja_and_en(self):
        if core.shutil.which("git") is None:
            self.skipTest("git not available")
        path = _make_project(self.tmp)
        _dirty(path)
        with mock.patch.dict(os.environ, ISOLATED_GIT):
            ok, out = core.commit_all(path, "change")
            self.assertFalse(ok)
            self.assertIn("git config --global user.name", out)
            self.assertIn("git config --global user.email", out)
            self.assertNotIn("Author identity unknown", out)
            self.assertNotIn("fatal:", out)
            self.assertEqual(_commit_count(path), 1)
            # English, with the change still uncommitted.
            self.set_language("en")
            ok, out = core.commit_all(path, "change")
            self.assertFalse(ok)
            self.assertIn("git user.name / user.email is not set", out)
            self.assertNotIn("Author identity unknown", out)
            self.assertEqual(_commit_count(path), 1)

    def test_commit_succeeds_on_clean_tree_without_identity(self):
        if core.shutil.which("git") is None:
            self.skipTest("git not available")
        path = _make_project(self.tmp)
        with mock.patch.dict(os.environ, ISOLATED_GIT):
            ok, out = core.commit_all(path, "nothing to do")
            self.assertTrue(ok)
            self.assertIn(i18n.t("core_nothing_to_commit", lang="ja"), out)
            self.assertEqual(_commit_count(path), 1)

    def test_commit_succeeds_once_identity_set(self):
        if core.shutil.which("git") is None:
            self.skipTest("git not available")
        path = _make_project(self.tmp)
        _dirty(path)
        with mock.patch.dict(os.environ, ISOLATED_GIT):
            ok, _out = core.commit_all(path, "change")
            self.assertFalse(ok)
            core.git_op(path, "config", "user.email", "local@example.com")
            core.git_op(path, "config", "user.name", "Local")
            ok, _out = core.commit_all(path, "change")
            self.assertTrue(ok)
            self.assertEqual(_commit_count(path), 2)


class TestDoctorGitIdentity(CoreTestCase):
    def _identity_level(self, result):
        return next(c for c in result["checks"]
                    if c["name"] == "git_identity")["level"]

    def test_doctor_ok_with_global_identity(self):
        if core.shutil.which("git") is None:
            self.skipTest("git not available")
        r = core.doctor()
        self.assertEqual(self._identity_level(r), "ok")

    def test_doctor_warns_without_global_identity(self):
        if core.shutil.which("git") is None:
            self.skipTest("git not available")
        with mock.patch.dict(os.environ, ISOLATED_GIT):
            r = core.doctor()
        self.assertEqual(self._identity_level(r), "warn")
        check = next(c for c in r["checks"]
                     if c["name"] == "git_identity")
        self.assertIn("git config --global user.name", check["hint"])
        self.assertIn("リポジトリごと", check["hint"])
        self.assertTrue(r["ok"])  # a warning is not a failure


class CliTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.env = dict(os.environ)
        self.env["PYTHONPATH"] = str(SRC)
        self.env["PJ_MANAGER_DATA_DIR"] = str(self.tmp / "data")

    def tearDown(self):
        self._tmp.cleanup()

    def run_cli(self, *argv, env=None):
        return subprocess.run(
            [sys.executable, "-m", "pj_manager.cli", *argv],
            capture_output=True, text=True,
            env=self.env if env is None else env, timeout=120,
        )

    def isolated_env(self):
        env = dict(self.env, **ISOLATED_GIT)
        return env

    def create(self, name="demo"):
        r = self.run_cli("create", name, "--root", str(self.tmp / "Projects"),
                         "--no-venv")
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        return self.tmp / "Projects" / name


class TestCliCommitWithoutIdentity(CliTestCase):
    def test_cli_commit_friendly_ja_en_and_json(self):
        if core.shutil.which("git") is None:
            self.skipTest("git not available")
        path = self.create()
        (path / "main.py").write_text("print('change')\n",
                                      encoding="utf-8")
        env = self.isolated_env()
        r = self.run_cli("commit", "demo", "-m", "change", env=env)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("git config --global user.name", r.stderr)
        self.assertNotIn("Author identity unknown", r.stderr)
        r = self.run_cli("commit", "demo", "-m", "change", "--json", env=env)
        result = json.loads(r.stdout)
        self.assertEqual(r.returncode, 1)
        self.assertFalse(result["ok"])
        self.assertIn("git config --global user.name", result["error"])
        # English, then set a local identity and the commit succeeds.
        self.run_cli("config", "set-language", "en")
        r = self.run_cli("commit", "demo", "-m", "change", env=env)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("git user.name / user.email is not set", r.stderr)
        subprocess.run(["git", "config", "user.email", "local@example.com"],
                       cwd=path, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Local"],
                       cwd=path, check=True, capture_output=True)
        r = self.run_cli("commit", "demo", "-m", "change", env=env)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_cli_doctor_git_identity(self):
        if core.shutil.which("git") is None:
            self.skipTest("git not available")
        r = self.run_cli("doctor", "--json")
        result = json.loads(r.stdout)
        levels = {c["name"]: c["level"] for c in result["checks"]}
        self.assertEqual(levels["git_identity"], "ok")
        r = self.run_cli("doctor", "--json", env=self.isolated_env())
        result = json.loads(r.stdout)
        levels = {c["name"]: c["level"] for c in result["checks"]}
        self.assertEqual(levels["git_identity"], "warn")


if __name__ == "__main__":
    unittest.main()
