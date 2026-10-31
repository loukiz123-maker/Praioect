"""Dependency-free checks for the demo's markup and JavaScript contract."""

import ast
import json
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
        self.text = []

    def handle_data(self, text):
        normalized = " ".join(text.split())
        if normalized:
            self.text.append(normalized)

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
        self.assertEqual(by_id["knowledge-warning"].get("role"), "status")
        self.assertIn("hidden", by_id["knowledge-warning"])
        self.assertIn('health.knowledge_articles', self.script)
        self.assertIn("hidden", by_id["duplicate-pill"])
        self.assertIn('$("duplicate-pill").hidden = !result.is_spam_or_duplicate', self.script)
        self.assertIn('$("result-announcement").textContent', self.script)
        self.assertIn('$("source-text").textContent = item.text', self.script)

    def test_reply_language_is_separate_from_interface_and_persisted_for_the_form(self):
        html = (STATIC / "index.html").read_text(encoding="utf-8")
        select = re.search(r'<select\b[^>]*id="reply-language"[^>]*>(.*?)</select>', html, re.DOTALL)
        self.assertIsNotNone(select)
        self.assertEqual(re.findall(r'<option\s+value="([^"]+)"', select.group(1)), ["auto", "ru", "en", "kk", "uz"])
        buttons = {attrs.get("id"): attrs for tag, attrs in self.markup.elements if tag == "button"}
        self.assertEqual(buttons["select-uzbek-reply"].get("type"), "button")
        self.assertEqual(buttons["select-uzbek-reply"].get("aria-pressed"), "false")
        self.assertIn('$("select-uzbek-reply").addEventListener("click"', self.script)
        self.assertIn('replyLanguage: $("reply-language").value', self.script)
        self.assertIn("payload.reply_language = requestedReplyLanguage", self.script)
        self.assertIn("original && item.editBuffer === original.text ? original.lang : \"und\"", self.script)
        self.assertIn('id="language-switch"', html)

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
                self.assertNotEqual(link.get("target"), "_blank")

    def test_jury_explanation_is_linked_and_covers_storage_and_limits(self):
        by_id = {attrs["id"]: (tag, attrs) for tag, attrs in self.markup.elements if "id" in attrs}
        tag, section = by_id["about-section"]
        self.assertEqual(tag, "section")
        self.assertEqual(section.get("aria-labelledby"), "explanation-title")
        self.assertEqual(section.get("tabindex"), "-1")
        hero_link = next(
            attrs for tag, attrs in self.markup.elements
            if tag == "a" and "hero-explainer-link" in attrs.get("class", "").split()
        )
        self.assertEqual(hero_link.get("href"), "#about-section")
        steps = [attrs for tag, attrs in self.markup.elements if tag == "li" and attrs.get("class") == "explanation-step"]
        self.assertEqual(len(steps), 4)
        content = " ".join(self.markup.text)
        for important_limit in (
            "не видит содержимое скриншотов",
            "Игроку ответ автоматически не отправляется",
            "sessionStorage",
            "после закрытия вкладки могут пропасть",
            "SQLite",
            "Записи старше 14 дней удаляются",
            "автоматически не восстановится с сервера",
            "14 дней после объявления победителей",
            "не переводятся",
            "без LLM и внешних API",
            "В проверенной выборке из 1000 обращений нет меток категорий и приоритетов",
            "проверка цитат и база знаний",
            "Автоматического обучения нет",
            "в браузере не шифруются",
        ):
            with self.subTest(limit=important_limit):
                self.assertIn(important_limit, content)


class TranslationCoverageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.script = (STATIC / "i18n.js").read_text(encoding="utf-8")
        quoted = r'"(?:[^"\\]|\\.)*"'
        pattern = rf'^\s*({quoted}|[\w$]+)\s*:\s*\[\s*({quoted})\s*,\s*({quoted})\s*,\s*({quoted})\s*,?\s*\]'
        dictionary = cls.script.split('  const LANGUAGE_KEY', 1)[0]
        rows = re.findall(pattern, dictionary, re.MULTILINE)
        all_keys = re.findall(rf'^\s*({quoted}|[\w$]+)\s*:\s*\[', dictionary, re.MULTILINE)
        cls.messages = {
            (json.loads(key) if key.startswith('"') else key): (json.loads(en), json.loads(kk), json.loads(uz))
            for key, en, kk, uz in rows
        }
        if len(rows) != len(all_keys) or len(rows) != len(cls.messages):
            raise AssertionError("Missing translation or duplicate interface translation key")

    def test_both_pages_have_accessible_language_controls_and_translated_static_text(self):
        for filename in ("index.html", "admin.html"):
            with self.subTest(page=filename):
                markup = Markup()
                html = (STATIC / filename).read_text(encoding="utf-8")
                markup.feed(html)
                by_id = {attrs["id"]: (tag, attrs) for tag, attrs in markup.elements if "id" in attrs}
                self.assertEqual(by_id["language-switch"][0], "select")
                selector = re.search(r'<select\b[^>]*id="language-switch"[^>]*>(.*?)</select>', html, re.DOTALL)
                self.assertIsNotNone(selector)
                self.assertEqual(re.findall(r'<option\s+value="([^"]+)"', selector.group(1)), ["ru", "en", "kk", "uz"])
                self.assertIn('<option value="uz" lang="uz">O‘zbekcha</option>', selector.group(1))
                self.assertTrue(any(tag == "label" and attrs.get("for") == "language-switch" for tag, attrs in markup.elements))
                scripts = [attrs.get("src") for tag, attrs in markup.elements if tag == "script"]
                self.assertLess(scripts.index("/i18n.js"), len(scripts) - 1)
                strings = list(markup.text)
                for _, attrs in markup.elements:
                    strings.extend(" ".join(attrs[name].split()) for name in ("aria-label", "placeholder", "title") if name in attrs)
                missing = [value for value in strings if re.search(r"[А-Яа-яЁё]", value) and value not in self.messages]
                self.assertEqual(missing, [], f"Untranslated static text in {filename}")

    def test_translation_templates_keep_all_placeholders(self):
        self.assertGreater(len(self.messages), 300)
        for source, translations in self.messages.items():
            expected = set(re.findall(r"\{\w+\}", source))
            for translated in translations:
                self.assertTrue(translated, source)
                self.assertEqual(set(re.findall(r"\{\w+\}", translated)), expected, source)

    def test_interface_owned_russian_strings_have_translations(self):
        # Deliberately untranslated example text and grammatical stems handled by
        # pluralForm are not standalone interface labels.
        exclusions = {
            "Ойыншы мені чатта ќорлады. Көмек беріңіз.",
            "обращение", "обращения", "пункт", "пункта", "символ", "символа", "символов",
            "өтініш", "таңба", "тармақ",
        }
        for filename in ("app.js", "admin.js"):
            script = (STATIC / filename).read_text(encoding="utf-8")
            literals = re.findall(r'"([^"\n]*[А-Яа-яЁё][^"\n]*)"', script)
            missing = [value for value in literals if value not in self.messages and value not in exclusions]
            self.assertEqual(missing, [], f"Untranslated application text in {filename}")

    def test_classifier_and_api_explanations_and_errors_have_translations(self):
        root = STATIC.parents[1]
        called = {"append", "InputError", "HttpFailure", "QueueConflict", "QueueNotFound", "QueueFull"}
        for name in ("service.py", "server.py", "admin_queue.py", "result_validation.py"):
            tree = ast.parse((root / "support_copilot" / name).read_text(encoding="utf-8"))
            missing = []
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call) or not isinstance(node.func, (ast.Name, ast.Attribute)):
                    continue
                function = node.func.id if isinstance(node.func, ast.Name) else node.func.attr
                if function not in called:
                    continue
                for value in node.args:
                    if (isinstance(value, ast.Constant) and isinstance(value.value, str)
                        and re.search(r"[А-Яа-яЁё]", value.value) and value.value not in self.messages):
                        missing.append(value.value)
            self.assertEqual(missing, [], f"Untranslated server text in {name}")

    def test_player_data_and_admin_secrets_remain_separate(self):
        operator = (STATIC / "app.js").read_text(encoding="utf-8")
        admin = (STATIC / "admin.js").read_text(encoding="utf-8")
        self.assertIn("sessionStorage.setItem(SESSION_KEY", operator)
        self.assertIn("restoreSession()", operator)
        self.assertNotIn("sessionStorage.setItem", admin)
        for selector in ("#source-text", "#review-message", "#operator-draft-text", ".admin-item-message"):
            self.assertIn(selector, self.script)
        self.assertIn('window.addEventListener("pagehide", () => showLogin())', admin)


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

    def test_review_actions_and_feedback_controls_are_available(self):
        buttons = {attrs.get("id"): attrs for tag, attrs in self.markup.elements if tag == "button"}
        for element_id in ("edit-button", "save-button", "resolve-button", "escalate-review", "export-feedback"):
            self.assertEqual(buttons[element_id].get("type"), "button")
            self.assertIn(f'$("{element_id}").addEventListener', self.script)
        filters = [attrs.get("data-filter") for tag, attrs in self.markup.elements if tag == "button"]
        self.assertIn("escalated", filters)
        self.assertIn('/admin/api/feedback/export', self.script)

    def test_local_reply_generator_has_four_languages_and_no_translation_widget(self):
        html = (STATIC / "admin.html").read_text(encoding="utf-8")
        select = re.search(r'<select\b[^>]*id="admin-reply-language"[^>]*>(.*?)</select>', html, re.DOTALL)
        self.assertIsNotNone(select)
        self.assertEqual(re.findall(r'<option\s+value="([^"]+)"', select.group(1)), ["ru", "en", "kk", "uz"])
        by_id = {attrs.get("id"): attrs for tag, attrs in self.markup.elements if tag == "button"}
        self.assertEqual(by_id["generate-draft"].get("type"), "button")
        self.assertEqual(by_id["generate-uzbek"].get("type"), "button")
        self.assertIn('$("generate-draft").addEventListener("click", () => generateDraft())', self.script)
        self.assertIn('$("generate-uzbek").addEventListener("click", () => generateDraft("uz"))', self.script)
        self.assertIn('$("generate-uzbek").disabled = state.busy || !available', self.script)
        self.assertIn('body: { version, language }', self.script)
        self.assertFalse((STATIC.parent / "translation.py").exists())
        self.assertFalse((STATIC / "translated-by-google.png").exists())
        self.assertNotIn("/translate", self.script)

    def test_no_browser_storage_or_html_injection_for_private_data(self):
        self.assertNotIn("localStorage", self.script)
        self.assertNotIn("sessionStorage", self.script)
        self.assertNotIn("innerHTML", self.script)
        self.assertRegex(self.script, r'\$\("review-message"\)\.textContent\s*=\s*detail\.message')


if __name__ == "__main__":
    unittest.main()
