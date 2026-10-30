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
            for attribute in ("aria-labelledby", "aria-describedby"):
                for target in attrs.get(attribute, "").split():
                    self.assertIn(target, ids)

    def test_results_have_accessible_status_and_spam_indicator(self):
        by_id = {attrs["id"]: attrs for _, attrs in self.markup.elements if "id" in attrs}
        self.assertEqual(by_id["result-announcement"].get("role"), "status")
        self.assertIn("hidden", by_id["duplicate-pill"])
        self.assertIn('$("duplicate-pill").hidden = !result.is_spam_or_duplicate', self.script)
        self.assertIn('$("result-announcement").textContent', self.script)
        self.assertIn('$("source-text").textContent = item.text', self.script)

    def test_handoff_conflict_checks_status_without_losing_editor(self):
        self.assertIn("error.status = response.status", self.script)
        self.assertIn('error.status === 409) await refreshReview(item, { force: true })', self.script)
        self.assertIn('item.reviewErrorKind === "conflict"', self.script)
        self.assertIn('$("admin-answer").value = item.adminReply', self.script)

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
        self.assertEqual(len(links), 4)
        for link in links:
            self.assertTrue(link.get("aria-label"))
            href = link.get("href", "")
            if href.startswith("#"):
                self.assertIn(href.lstrip("#"), self.markup.ids)
            else:
                self.assertEqual(href, "/admin")
                self.assertEqual(link.get("target"), "_blank")


class AdminUiMarkupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.markup = Markup()
        cls.markup.feed((STATIC / "admin.html").read_text(encoding="utf-8"))
        cls.script = (STATIC / "admin.js").read_text(encoding="utf-8")

    def test_admin_is_separate_and_javascript_targets_exist(self):
        counts = Counter(self.markup.ids)
        self.assertFalse([element_id for element_id, count in counts.items() if count > 1])
        script_ids = set(re.findall(r'\$\("([\w-]+)"\)', self.script))
        self.assertTrue(script_ids)
        self.assertFalse(script_ids - counts.keys())
        self.assertIn("login-form", counts)
        self.assertIn("admin-draft", counts)

    def test_labels_and_accessibility_references_resolve(self):
        ids = set(self.markup.ids)
        for tag, attrs in self.markup.elements:
            if tag == "label" and "for" in attrs:
                self.assertIn(attrs["for"], ids)
            for attribute in ("aria-labelledby", "aria-describedby"):
                for target in attrs.get(attribute, "").split():
                    self.assertIn(target, ids)
        nav_links = [attrs for tag, attrs in self.markup.elements if tag == "a" and "admin-nav-link" in attrs.get("class", "").split()]
        self.assertTrue(all(link.get("aria-label") for link in nav_links))

    def test_no_browser_storage_or_html_injection_for_private_data(self):
        self.assertNotIn("localStorage", self.script)
        self.assertNotIn("sessionStorage", self.script)
        self.assertNotIn("innerHTML", self.script)
        self.assertIn('$("review-message").textContent = detail.message', self.script)


if __name__ == "__main__":
    unittest.main()
