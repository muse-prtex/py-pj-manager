"""Tests for the language switch groundwork (i18n).

- The string dictionaries are complete (ja/en keys match, placeholders
  match) and every key referenced from core.py / cli.py / app.py exists.
- core messages and CLI human output follow config.json `language`
  ("ja" default / "en"); --json output does not change with language.
- `config set-language` switches the language; unknown values are
  rejected and the default stays Japanese.
"""

import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from pj_manager import core, i18n  # noqa: E402

CJK = re.compile(r"[\u3040-\u30ff\u4e00-\u9fff]")


class DictionaryTestCase(unittest.TestCase):
    def test_dictionaries_are_complete(self):
        """ja/en のキー・空文字・placeholder が一致する。"""
        self.assertEqual(i18n.check_dictionaries(), [])

    def test_all_referenced_keys_exist(self):
        """core/cli/app が参照するキーは全て辞書にある。"""
        used = set()
        for path in (SRC / "pj_manager").glob("*.py"):
            text = path.read_text(encoding="utf-8")
            for m in re.finditer(r"(?:i18n\.t|_t|self\.tr)\(\s*\"([a-z0-9_]+)\"",
                                 text):
                used.add(m.group(1))
        self.assertTrue(used, "no keys found — the regex broke")
        missing = sorted(k for k in used if k not in i18n.STRINGS)
        self.assertEqual(missing, [])

    def test_normalize_language(self):
        self.assertEqual(i18n.normalize_language("en"), "en")
        self.assertEqual(i18n.normalize_language("EN"), "en")
        self.assertEqual(i18n.normalize_language(" ja "), "ja")
        self.assertEqual(i18n.normalize_language("fr"), "ja")
        self.assertEqual(i18n.normalize_language(""), "ja")
        self.assertEqual(i18n.normalize_language(None), "ja")
        self.assertEqual(i18n.normalize_language(123), "ja")


class GetLanguageTestCase(unittest.TestCase):
    def test_get_language_from_config_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = Path(tmp) / "config.json"
            self.assertEqual(i18n.get_language(cfg), "ja")  # 無い＝既定
            cfg.write_text(json.dumps({"language": "en"}), encoding="utf-8")
            self.assertEqual(i18n.get_language(cfg), "en")
            cfg.write_text(json.dumps({"language": "fr"}), encoding="utf-8")
            self.assertEqual(i18n.get_language(cfg), "ja")  # 知らない値
            cfg.write_text("{not json", encoding="utf-8")
            self.assertEqual(i18n.get_language(cfg), "ja")  # 壊れ
            cfg.write_text(json.dumps(["not", "a", "dict"]), encoding="utf-8")
            self.assertEqual(i18n.get_language(cfg), "ja")

    def test_load_config_normalizes_language(self):
        with tempfile.TemporaryDirectory() as tmp:
            orig = (core.DATA_DIR, core.REGISTRY_FILE, core.CONFIG_FILE)
            try:
                core.DATA_DIR = Path(tmp) / "data"
                core.REGISTRY_FILE = core.DATA_DIR / "projects.json"
                core.CONFIG_FILE = core.DATA_DIR / "config.json"
                self.assertEqual(core.load_config()["language"], "ja")
                core.save_config({"language": "fr",
                                  "projects_root": str(Path(tmp))})
                self.assertEqual(core.load_config()["language"], "ja")
                core.save_config({"language": "en",
                                  "projects_root": str(Path(tmp))})
                self.assertEqual(core.load_config()["language"], "en")
            finally:
                core.DATA_DIR, core.REGISTRY_FILE, core.CONFIG_FILE = orig


class CoreLanguageTestCase(unittest.TestCase):
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

    def _set_lang(self, lang: str) -> None:
        core.save_config({"language": lang,
                          "projects_root": str(self.tmp / "Projects")})

    def test_error_messages_follow_language(self):
        """ValueError / run_cmd の文言が言語で切り替わる。"""
        self._set_lang("ja")
        with self.assertRaisesRegex(ValueError, "フォルダがありません"):
            core.register_existing(self.tmp / "nope")
        with self.assertRaisesRegex(ValueError, "半角英数字"):
            core.create_project("bad name!", self.tmp / "Projects",
                                make_venv=False, init_git=False)
        self.assertEqual(core.run_cmd(["git", "--version"],
                                      cwd=self.tmp / "nope")[1],
                         f"フォルダがありません: {self.tmp / 'nope'}")

        self._set_lang("en")
        with self.assertRaisesRegex(ValueError, "Folder not found"):
            core.register_existing(self.tmp / "nope")
        with self.assertRaisesRegex(ValueError, "must use letters"):
            core.create_project("bad name!", self.tmp / "Projects",
                                make_venv=False, init_git=False)
        self.assertEqual(core.run_cmd(["git", "--version"],
                                      cwd=self.tmp / "nope")[1],
                         f"Folder not found: {self.tmp / 'nope'}")

    def test_doctor_details_follow_language(self):
        """doctor の detail / hint に言語外の文字が混ざらない。"""
        self._set_lang("en")
        details = [c["detail"] for c in core.doctor()["checks"]]
        hints = [c.get("hint", "") for c in core.doctor()["checks"]]
        for text in details + hints:
            self.assertNotRegex(text, CJK, f"Japanese in en detail: {text}")
        self._set_lang("ja")
        details = [c["detail"] for c in core.doctor()["checks"]]
        self.assertTrue(any(CJK.search(d) for d in details),
                        "no Japanese detail in ja mode")

    def test_create_logs_follow_language(self):
        """create_project のログ行も言語で切り替わる。"""
        self._set_lang("en")
        logs: list[str] = []
        core.create_project("lang-demo", self.tmp / "Projects",
                            make_venv=False, init_git=False, log=logs.append)
        self.assertIn(f"Created folder: {self.tmp / 'Projects' / 'lang-demo'}",
                      logs)
        self.assertIn("Registered the project in the list", logs)
        self.assertFalse(any(CJK.search(x) for x in logs))


class CliLanguageTestCase(unittest.TestCase):
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

    def test_set_language_switches_human_output(self):
        """config set-language で人間向け出力が切り替わる。"""
        plain = self.tmp / "plain"
        plain.mkdir()
        self.run_cli("register", str(plain), "--json")

        r = self.run_cli("status", "plain")  # ja（既定）
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("git: not a repository", r.stdout)

        r = self.run_cli("config", "set-language", "en")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("language: en", r.stdout)

        r = self.run_cli("status", "plain")
        self.assertIn("git: not a repository", r.stdout)
        r = self.run_cli("commit", "plain", "-m", "x")
        self.assertEqual(r.returncode, 1)
        self.assertIn("Not a git repository", r.stderr)
        r = self.run_cli("status", "no-such-project")
        self.assertIn("Project not found", r.stderr)
        r = self.run_cli("doctor")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotRegex(r.stdout, CJK)

        r = self.run_cli("config", "set-language", "ja")
        self.assertIn("language: ja", r.stdout)
        r = self.run_cli("commit", "plain", "-m", "x")
        self.assertIn("git リポジトリではありません", r.stderr)

    def test_set_language_rejects_unknown(self):
        r = self.run_cli("config", "set-language", "fr")
        self.assertEqual(r.returncode, 1)
        self.assertIn("言語は ja か en", r.stderr)
        r = self.run_cli("config", "set-language", "en")
        self.assertEqual(r.returncode, 0)
        r = self.run_cli("config", "set-language", "fr")
        self.assertIn("Language must be ja or en", r.stderr)
        # 拒否されても言語は en のまま
        self.assertEqual(json.loads(
            self.run_cli("config", "show", "--json").stdout
        )["config"]["language"], "en")

    def test_json_output_is_language_independent(self):
        """--json のキーと値は言語で変わらない。"""
        self.run_cli("config", "set-language", "en")
        r_en = self.run_cli("doctor", "--json")
        self.run_cli("config", "set-language", "ja")
        r_ja = self.run_cli("doctor", "--json")
        en, ja = json.loads(r_en.stdout), json.loads(r_ja.stdout)
        self.assertEqual([c["name"] for c in en["checks"]],
                         [c["name"] for c in ja["checks"]])
        self.assertEqual(en["status"], ja["status"])
        self.assertEqual(en["summary"], ja["summary"])
        # detail だけが言語で変わる
        self.assertNotEqual([c["detail"] for c in en["checks"]],
                            [c["detail"] for c in ja["checks"]])

    def test_config_show_includes_language(self):
        cfg = json.loads(self.run_cli("config", "show", "--json").stdout)
        self.assertEqual(cfg["config"]["language"], "ja")


if __name__ == "__main__":
    unittest.main()
