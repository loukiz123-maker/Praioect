"""Dependency-free checks for the demo's markup and JavaScript contract."""

import re
import unittest
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path


STATIC = Path(__file__).resolve().parents[1] / "support_copilot" / "static"


class Markup(HTMLParser):
    def __init__(self):
        super().__init__()
        self.elements = []
        self.ids = []

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        self.elements.append((tag, attrs))
        if "id" in attrs:
            self.ids.append(attrs["id"])


class UiMarkupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.markup = Markup()
        cls.markup.feed((STATIC / "index.html").read_text(encoding="utf-8"))
        cls.script = (STATIC / "app.js").read_text(encoding="utf-8")

    def test_unique_ids_and_javascript_targets_exist(self):
        counts = Counter(self.markup.ids)
        self.assertFalse([element_id for element_id, count in counts.items() if count > 1])
        script_ids = set(re.findall(r'\$\("([\w-]+)"\)', self.script))
        self.assertTrue(script_ids)
        self.assertFalse(script_ids - counts.keys())

    def test_labels_and_accessible_references_resolve(self):
        ids = set(self.markup.ids)
        for tag, attrs in self.markup.elements:
            if tag == "label" and "for" in attrs:
                self.assertIn(attrs["for"], ids)
            for target in attrs.get("aria-labelledby", "").split():
                self.assertIn(target, ids)

    def test_reset_is_a_non_submitting_control(self):
        buttons = [attrs for tag, attrs in self.markup.elements if tag == "button"]
        reset = next(attrs for attrs in buttons if attrs.get("id") == "clear-form")
        self.assertEqual(reset.get("type"), "button")
        self.assertIn('$("clear-form").addEventListener("click"', self.script)

    def test_mobile_navigation_links_have_accessible_names(self):
        links = [
            attrs
            for tag, attrs in self.markup.elements
            if tag == "a" and "nav-link" in attrs.get("class", "").split()
        ]
        self.assertEqual(len(links), 3)
        for link in links:
            self.assertTrue(link.get("aria-label"))
            self.assertIn(link.get("href", "").lstrip("#"), self.markup.ids)


if __name__ == "__main__":
    unittest.main()
