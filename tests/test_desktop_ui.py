"""Static smoke tests for the desktop UI (desktop/ui/index.html).

The frontend is a single dependency-free HTML file; these tests guard the
element ids and behaviours the screenshot tool (day-run/tools/desktop_shot.py)
relies on, and check the inline <script> parses (via node when available).
They do not render the page — visual checks live in the screenshots.
"""

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


if __name__ == "__main__":
    unittest.main()
