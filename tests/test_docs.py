"""Tests for the documentation (docs/usage.md, READMEs, docs/images/).

The screenshots in docs/images/ are real captures taken while using the
tool. These tests guard the wiring: every image a doc references must
exist and be a real PNG, every image in docs/images/ must be used, and
the links inside the docs must resolve within the repository.
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = [ROOT / "README.md", ROOT / "README.ja.md", ROOT / "docs" / "usage.md"]
IMAGES_DIR = ROOT / "docs" / "images"

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"

IMAGE_RE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
LINK_RE = re.compile(r"(?<!!)\[[^\]]*\]\(([^)]+)\)")

REQUIRED_USAGE_SECTIONS = [
    "## インストールと起動",
    "## GUI の使い方",
    "## デスクトップアプリ",
    "## 表示言語の切替",
    "## CLI",
    "### doctor",
    "### check",
    "## データファイルとサンドボックス",
    "## トラブルシューティング",
]


def _images_of(text):
    return IMAGE_RE.findall(text)


def _links_of(text):
    return LINK_RE.findall(text)


def _resolve(doc_path, target):
    return (doc_path.parent / target).resolve()


class DocsTestCase(unittest.TestCase):
    def test_docs_exist(self):
        for doc in DOCS:
            self.assertTrue(doc.is_file(), f"missing doc: {doc}")

    def test_referenced_images_exist(self):
        for doc in DOCS:
            text = doc.read_text(encoding="utf-8")
            for target in _images_of(text):
                self.assertFalse(target.startswith(("http://", "https://")),
                                 f"{doc.name} links an external image: {target}")
                path = _resolve(doc, target)
                self.assertTrue(path.is_file(),
                                f"{doc.name} references missing image: {target}")

    def test_referenced_images_are_real_pngs(self):
        for doc in DOCS:
            text = doc.read_text(encoding="utf-8")
            for target in _images_of(text):
                path = _resolve(doc, target)
                data = path.read_bytes()
                self.assertGreater(len(data), 1000,
                                   f"image suspiciously small: {target}")
                self.assertTrue(data.startswith(PNG_MAGIC),
                                f"not a PNG file: {target}")

    def test_every_image_in_docs_images_is_used(self):
        used = set()
        for doc in DOCS:
            text = doc.read_text(encoding="utf-8")
            for target in _images_of(text):
                used.add(_resolve(doc, target))
        for path in sorted(IMAGES_DIR.glob("*.png")):
            self.assertIn(path.resolve(), used,
                          f"orphan image in docs/images/: {path.name}")

    def test_usage_has_required_sections(self):
        text = (ROOT / "docs" / "usage.md").read_text(encoding="utf-8")
        for section in REQUIRED_USAGE_SECTIONS:
            self.assertIn(section, text, f"usage.md lacks section: {section}")

    def test_usage_documents_doctor_and_check_commands(self):
        text = (ROOT / "docs" / "usage.md").read_text(encoding="utf-8")
        for command in ("pj-manager doctor", "pj-manager check",
                        "pj-manager list", "pj-manager status",
                        "pj-manager config set-language"):
            self.assertIn(command, text, f"usage.md lacks command: {command}")

    def test_readmes_link_to_usage_guide(self):
        for doc in (ROOT / "README.md", ROOT / "README.ja.md"):
            text = doc.read_text(encoding="utf-8")
            self.assertIn("docs/usage.md", text,
                          f"{doc.name} does not link to the usage guide")

    def test_internal_links_resolve(self):
        for doc in DOCS:
            text = doc.read_text(encoding="utf-8")
            for target in _links_of(text):
                if target.startswith(("http://", "https://", "#", "mailto:")):
                    continue
                target = target.split("#", 1)[0]
                if not target:
                    continue
                path = _resolve(doc, target)
                self.assertTrue(path.exists(),
                                f"{doc.name} links to missing file: {target}")

    def test_no_sandbox_urls_leak_into_docs(self):
        for doc in DOCS:
            text = doc.read_text(encoding="utf-8")
            self.assertNotIn("sandbox://", text,
                             f"{doc.name} contains a sandbox:// URL")


if __name__ == "__main__":
    unittest.main()
