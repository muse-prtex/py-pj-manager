"""Static smoke tests for the desktop UI (desktop/ui/index.html).

The frontend is a single dependency-free HTML file; these tests guard the
element ids and behaviours the screenshot tool (day-run/tools/desktop_shot.py)
relies on, and check the inline <script> parses (via node when available).
They do not render the page — visual checks live in the screenshots.
"""

import json
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HTML = ROOT / "desktop" / "ui" / "index.html"


def _read_html():
    return HTML.read_text(encoding="utf-8")


def _script(html):
    m = re.search(r"<script>(.*)</script>", html, re.S)
    assert m, "no <script> block found"
    return m.group(1)


class DesktopUiTestCase(unittest.TestCase):
    def test_file_exists(self):
        self.assertTrue(HTML.is_file())

    def test_modals_present(self):
        html = _read_html()
        for element_id in ("modal-new", "modal-commit", "f-name", "f-name-err",
                           "c-msg", "c-msg-err", "c-title", "f-create", "c-do"):
            self.assertIn(f'id="{element_id}"', html, element_id)

    def test_empty_state_present(self):
        html = _read_html()
        for element_id in ("empty-hero", "btn-new-empty", "btn-register-empty",
                           "detail-card", "open-card", "git-card"):
            self.assertIn(f'id="{element_id}"', html, element_id)
        self.assertIn("renderEmpty", _script(html))
        self.assertIn("demo=empty", _script(html))
        self.assertIn("DEMO_EMPTY", _script(html))

    def test_modal_close_behaviour(self):
        script = _script(_read_html())
        self.assertIn('"Escape"', script)  # Esc closes modals
        self.assertIn("e.target === o", script)  # overlay click closes

    def test_inline_validation(self):
        script = _script(_read_html())
        self.assertIn("NAME_RE", script)
        self.assertIn("setFieldError", script)
        self.assertNotIn("alert(", script)  # errors are inline, not alert()

    @unittest.skipUnless(shutil.which("node"), "node not available")
    def test_script_parses(self):
        with tempfile.NamedTemporaryFile("w", suffix=".js",
                                         delete=False, encoding="utf-8") as f:
            f.write(_script(_read_html()))
            tmp = f.name
        r = subprocess.run(["node", "--check", tmp],
                           capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)


def _i18n_dict():
    """I18N リテラルを node で評価して dict として返す。"""
    script = _script(_read_html())
    m = re.search(r"const I18N = (\{.*?\n\});", script, re.S)
    assert m, "no I18N literal found"
    code = "const I18N = " + m.group(1) + ";\nconsole.log(JSON.stringify(I18N));"
    r = subprocess.run(["node", "-e", code],
                       capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def _i18n_keys():
    script = _script(_read_html())
    m = re.search(r"const I18N = \{.*?\n\};", script, re.S)
    assert m, "no I18N literal found"
    return set(re.findall(r"^  (\w+): \{", m.group(0), re.M))


class DesktopUiI18nTestCase(unittest.TestCase):
    def test_language_select_present(self):
        html = _read_html()
        self.assertIn('id="lang-select"', html)
        self.assertIn('<option value="ja">', html)
        self.assertIn('<option value="en">', html)
        script = _script(html)
        self.assertIn("applyLanguage", script)
        self.assertIn("document.documentElement.lang", script)
        # Tauri では config set-language で保存し、CLI / tkinter と共有する
        self.assertIn('"set-language"', script)
        # デモでは localStorage、URL は ?lang= で指定できる
        self.assertIn("pj_lang", script)
        self.assertIn('"lang"', script)

    def test_data_i18n_keys_exist(self):
        html = _read_html()
        keys = _i18n_keys()
        used = set(re.findall(r'data-i18n="(\w+)"', html))
        used |= set(re.findall(r'data-i18n-placeholder="(\w+)"', html))
        self.assertTrue(used, "no data-i18n attributes found")
        self.assertEqual(used - keys, set(), "data-i18n key missing from I18N")

    def test_every_i18n_key_is_used(self):
        """辞書の孤児キー（どこからも参照されない文字列）を許さない。"""
        html = _read_html()
        script = _script(html)
        keys = _i18n_keys()
        used = set(re.findall(r'data-i18n="(\w+)"', html))
        used |= set(re.findall(r'data-i18n-placeholder="(\w+)"', html))
        used |= set(re.findall(r'\bt\("(\w+)"', script))
        self.assertEqual(keys - used, set(), "I18N key never used")

    def test_dynamic_strings_use_i18n(self):
        script = _script(_read_html())
        for key in ("pill_no_git", "pill_folder_missing", "chip_venv_yes",
                    "chip_branch", "detail_registered", "detail_last_commit",
                    "detail_github", "commit_title", "err_name_chars",
                    "err_msg_required", "log_failed", "log_created",
                    "confirm_unregister", "doctor_line", "ver_demo",
                    "dialog_register_title"):
            self.assertIn(f't("{key}"', script, key)
        # デモの doctor 結果は言語で組み立てる関数（定数オブジェクトではない）
        self.assertIn("function demoDoctor", script)
        self.assertNotIn("const DEMO_DOCTOR", script)

    def test_apply_language_renders_version_line(self):
        """言語切替でバージョン行も書き直す（初期表示の言語のまま残さない）。"""
        script = _script(_read_html())
        m = re.search(r"function applyLanguage\(\)\{(.*?)\n\}", script, re.S)
        assert m, "no applyLanguage function found"
        self.assertIn('"ver"', m.group(1))
        self.assertIn('t("ver_demo")', m.group(1))

    @unittest.skipUnless(shutil.which("node"), "node not available")
    def test_i18n_dict_complete(self):
        data = _i18n_dict()
        self.assertTrue(data, "I18N dict is empty")
        fmt = re.compile(r"\{(\w+)\}")
        for key, entry in sorted(data.items()):
            self.assertIn("ja", entry, key)
            self.assertIn("en", entry, key)
            self.assertTrue(entry["ja"], f"{key}: empty ja")
            self.assertTrue(entry["en"], f"{key}: empty en")
            ph_ja = set(fmt.findall(entry["ja"]))
            ph_en = set(fmt.findall(entry["en"]))
            self.assertEqual(ph_ja, ph_en,
                             f"{key}: placeholders differ ja={sorted(ph_ja)} "
                             f"en={sorted(ph_en)}")


if __name__ == "__main__":
    unittest.main()
