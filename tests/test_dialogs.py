"""Tests for the new-project dialog placement (app.py center_geometry).

The new-project dialog used to open offset to the top-left of the main
window because it set a bare geometry("460x380") and left placement to
the window manager (spotted in the session 11 screenshot). It is now
centered over the parent window with center_geometry().

These tests need no display: center_geometry() is a pure function, and
the wiring (dialog_new uses _center_dialog, _center_dialog uses the
live parent/screen sizes) is checked against the source. Real use
(the dialog actually opening centered) is verified with
day-run/tools/gui_shot.py on Xvfb and kept in the session screenshots.
"""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from pj_manager import app as app_module  # noqa: E402

center_geometry = app_module.center_geometry


class CenterGeometryTestCase(unittest.TestCase):
    def test_centers_over_parent(self):
        # Main window at (70, 50), 1080x660; dialog 460x380 on a
        # 1280x900 screen (the gui_shot.py setup).
        self.assertEqual(
            center_geometry(70, 50, 1080, 660, 460, 380, 1280, 900),
            "460x380+380+190")

    def test_centers_at_origin_parent(self):
        self.assertEqual(
            center_geometry(0, 0, 800, 600, 400, 300, 1920, 1080),
            "400x300+200+150")

    def test_clamps_to_right_and_bottom_screen_edges(self):
        # Parent hugging the bottom-right corner: the centered spot
        # would spill off-screen, so it is pulled back inside.
        self.assertEqual(
            center_geometry(1000, 800, 800, 600, 460, 380, 1280, 900),
            "460x380+820+520")

    def test_clamps_to_top_left_when_dialog_is_bigger_than_screen(self):
        # A dialog larger than the screen cannot be centered; it must
        # not end up at a negative position.
        self.assertEqual(
            center_geometry(100, 100, 800, 600, 2000, 1200, 1280, 900),
            "2000x1200+0+0")

    def test_same_size_as_parent_is_parent_position(self):
        self.assertEqual(
            center_geometry(70, 50, 1080, 660, 1080, 660, 1920, 1080),
            "1080x660+70+50")


class DialogWiringTestCase(unittest.TestCase):
    def test_center_dialog_helper_exists(self):
        self.assertTrue(callable(getattr(app_module.App, "_center_dialog")))

    def test_dialog_new_centers_itself(self):
        source = (ROOT / "src" / "pj_manager" / "app.py").read_text(
            encoding="utf-8")
        self.assertIn("self._center_dialog(win, 460, 380)", source)

    def test_no_bare_fixed_geometry_left_for_the_dialog(self):
        source = (ROOT / "src" / "pj_manager" / "app.py").read_text(
            encoding="utf-8")
        self.assertNotIn('win.geometry("460x380")', source)

    def test_center_dialog_reads_live_parent_and_screen_sizes(self):
        source = (ROOT / "src" / "pj_manager" / "app.py").read_text(
            encoding="utf-8")
        for call in ("self.winfo_x()", "self.winfo_y()",
                     "self.winfo_width()", "self.winfo_height()",
                     "self.winfo_screenwidth()", "self.winfo_screenheight()",
                     "self.update_idletasks()"):
            self.assertIn(call, source)


if __name__ == "__main__":
    unittest.main()
