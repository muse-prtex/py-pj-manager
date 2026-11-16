"""Tests for the tkinter GUI keyboard shortcuts (app.py SHORTCUTS).

The GUI itself needs a display (Xvfb), so these tests check everything
that can be verified without opening a window:

- the SHORTCUTS table lists the expected keys, scopes and handlers;
- every handler named in the table exists on App;
- no key is bound twice in the same scope;
- the shortcuts hint exists in both languages and names every shortcut.

Real use (Ctrl+N actually opening the new-project dialog, F5 refreshing)
is verified with day-run/tools/gui_shot.py on Xvfb and kept in the
session screenshots.
"""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from pj_manager import app as app_module  # noqa: E402
from pj_manager import i18n  # noqa: E402

App = app_module.App
SHORTCUTS = app_module.SHORTCUTS

EXPECTED = {
    ("<Control-n>", "root", "dialog_new"),
    ("<Control-o>", "root", "dialog_register"),
    ("<F5>", "root", "refresh_all"),
    ("<Control-r>", "root", "refresh_all"),
    ("<Control-q>", "root", "quit_app"),
    ("<Return>", "list", "do_open_terminal"),
    ("<Delete>", "list", "do_unregister"),
}


class ShortcutsTableTestCase(unittest.TestCase):
    def test_table_lists_expected_shortcuts(self):
        self.assertEqual(set(SHORTCUTS), EXPECTED)

    def test_every_handler_exists_on_app(self):
        for _key, _scope, handler_name in SHORTCUTS:
            self.assertTrue(hasattr(App, handler_name),
                            f"App has no method {handler_name}")
            self.assertTrue(callable(getattr(App, handler_name)))

    def test_no_duplicate_key_per_scope(self):
        seen = set()
        for key, scope, _handler in SHORTCUTS:
            self.assertNotIn((key, scope), seen,
                             f"{key} is bound twice in scope {scope}")
            seen.add((key, scope))

    def test_scopes_are_known(self):
        for _key, scope, _handler in SHORTCUTS:
            self.assertIn(scope, ("root", "list"))


class ShortcutsHintTestCase(unittest.TestCase):
    def test_hint_exists_in_both_languages(self):
        for lang in ("ja", "en"):
            text = i18n.t("app_shortcuts_hint", lang=lang)
            self.assertTrue(text, f"empty hint for {lang}")
            self.assertNotEqual(text, "app_shortcuts_hint")

    def test_hint_names_every_shortcut(self):
        # The hint is the user's only map of the shortcuts, so every key
        # in the table must be visible in it (both languages).
        labels = ("Ctrl+N", "Ctrl+O", "F5", "Ctrl+R", "Enter", "Del",
                  "Ctrl+Q")
        for lang in ("ja", "en"):
            text = i18n.t("app_shortcuts_hint", lang=lang)
            for label in labels:
                self.assertIn(label, text,
                              f"{lang} hint misses {label}: {text}")

    def test_dictionaries_stay_complete(self):
        self.assertEqual(i18n.check_dictionaries(), [])


class ShortcutsWiringTestCase(unittest.TestCase):
    def test_build_binds_shortcuts(self):
        source = (ROOT / "src" / "pj_manager" / "app.py").read_text(
            encoding="utf-8")
        self.assertIn("def _bind_shortcuts", source)
        # _build() must (re)bind on every rebuild (language switch
        # destroys and recreates the widgets).
        self.assertIn("self._bind_shortcuts()", source)

    def test_refresh_and_quit_helpers_exist(self):
        self.assertTrue(callable(getattr(App, "refresh_all")))
        self.assertTrue(callable(getattr(App, "quit_app")))


if __name__ == "__main__":
    unittest.main()
