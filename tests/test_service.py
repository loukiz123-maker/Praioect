import tempfile
import unittest

from helpers import ticket, write_fixtures
from support_copilot.catalog import Catalog
from support_copilot.service import InputError, TriageService
from support_copilot.text import detect_language, normalize


class TriageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.rules, self.taxonomy, self.knowledge = write_fixtures(self.tmp.name)
        self.catalog = Catalog(self.rules, self.taxonomy)
        self.service = TriageService(self.catalog)

    def tearDown(self):
        self.tmp.cleanup()

    def test_insult_is_grounded_in_correct_section_without_verdict(self):
        obj = ticket("Alex_Nova оскорбил меня и мою семью в чате 2.1")
        obj["messages"][0]["attachments"] = 2
        result = self.service.triage(obj)
        self.assertEqual(result["category"], "complaint.insult")
        self.assertEqual(result["priority"], "p1")
        self.assertEqual(result["draft_reply"]["cited"], ["2.1"])
        self.assertIn("Общие правила игры", result["draft_reply"]["text"])
        self.assertNotIn("Синтетический другой раздел", result["draft_reply"]["text"])
        self.assertTrue(result["needs_human"])
        self.assertTrue(result["extracted"]["has_evidence"])
        self.assertEqual(result["extracted"]["nickname"], "Alex_Nova")
        self.assertTrue(any("содержимое" in reason for reason in result["reasons"]))
        lower = result["draft_reply"]["text"].lower()
        for forbidden in ("жалоба одобрена", "получит мут", "по скриншотам видно", "накажем"):
            self.assertNotIn(forbidden, lower)

    def test_draft_separates_greeting_rule_and_review_into_paragraphs(self):
        result = self.service.triage(ticket("Игрок оскорбил меня в чате"))
        paragraphs = result["draft_reply"]["text"].split("\n\n")
        self.assertEqual(paragraphs[0], "Здравствуйте!")
        self.assertGreaterEqual(len(paragraphs), 3)
        self.assertIn("пункт", paragraphs[1])
        self.assertIn("администратор", paragraphs[2])

    def test_claimed_rule_is_extracted_but_never_blindly_cited(self):
        result = self.service.triage(ticket("Меня оскорбили, пункт 99.99", rule_refs_raw="99.99"))
        self.assertIn("99.99", result["extracted"]["rule_refs"])
        self.assertNotIn("99.99", result["draft_reply"]["cited"])

    def test_specific_house_rule_not_cited_for_killing_at_the_bank(self):
        result = self.service.triage(ticket("Игрок убил меня у банка"))
        self.assertEqual(result["category"], "complaint.dm")
        self.assertEqual(result["draft_reply"]["cited"], [])
        self.assertTrue(result["needs_human"])
        self.assertTrue(any("не подтверждён" in x for x in result["reasons"]))
        english = self.service.triage(ticket("A guy killed me in the bank"))
        self.assertEqual(english["draft_reply"]["cited"], [])

    def test_green_zone_is_scoped_and_pipe_is_preserved(self):
        result = self.service.triage(ticket("Игрок убил меня в зелёной зоне"))
        self.assertEqual(result["lang"], "ru")
        self.assertEqual(result["draft_reply"]["cited"], ["1.1"])
        self.assertIn("Правила Зелёной Зоны", result["draft_reply"]["text"])
        self.assertIn("Green Zone | GZ", result["draft_reply"]["text"])
        abbreviation = self.service.triage(ticket("GZ: игрок убил меня"))
        self.assertEqual(abbreviation["draft_reply"]["cited"], ["1.1"])

    def test_scam_does_not_get_the_extortion_rule_without_extortion(self):
        result = self.service.triage(ticket("Игрок обманул меня и забрал деньги"))
        self.assertEqual(result["category"], "complaint.scam")
        self.assertEqual(result["draft_reply"]["cited"], ["4.1"])

    def test_admin_messages_and_label_fields_are_not_used_at_inference(self):
        base = ticket("Игрок оскорбил меня в чате")
        poisoned = {**base, "category": "report.payment", "priority": "p0", "verdict": "approved", "punishment": "бан"}
        poisoned["messages"] = base["messages"] + [{"role": "admin", "text": "Взломали аккаунт, платеж, жалоба одобрена"}, {"role": "reported_player", "text": "Платеж и бан"}]
        expected = TriageService(self.catalog).triage(base)
        actual = TriageService(self.catalog).triage(poisoned)
        self.assertEqual(actual, expected)

    def test_high_risk_cases_always_escalate_even_if_kind_is_complaint(self):
        samples = [
            ("Оплатил донат, платёж не поступил", "p0"),
            ("Взломали мой аккаунт и украли доступ", "p0"),
            ("У меня украли аккаунт", "p0"),
            ("Менің тіркелгімді бұзған", "p0"),
            ("Ҳисобимни бузиб киришди", "p0"),
            ("Администратор забанил меня, хочу обжаловать", None),
        ]
        for text, priority in samples:
            with self.subTest(text=text):
                result = self.service.triage(ticket(text))
                self.assertTrue(result["needs_human"])
                if priority:
                    self.assertEqual(result["priority"], priority)
                draft = result["draft_reply"]["text"].lower()
                self.assertNotIn("вернём деньги", draft)
                self.assertNotIn("разбаним", draft)

    def test_stolen_vehicle_is_not_automatically_a_hacked_account(self):
        result = self.service.triage(ticket("Игрок угнал мою машину"))
        self.assertNotEqual(result["priority"], "p0")
        self.assertNotIn("вопроса с аккаунтом", result["draft_reply"]["text"])
        self.assertTrue(result["needs_human"])

    def test_evidence_mention_is_not_treated_as_a_verified_attachment(self):
        result = self.service.triage(ticket("Игрок оскорбил меня, скриншоты есть"))
        self.assertTrue(result["extracted"]["has_evidence"])
        self.assertTrue(any("не подтверждены" in reason for reason in result["reasons"]))
        self.assertNotIn("по скриншотам видно", result["draft_reply"]["text"].lower())
        with_count = self.service.triage(ticket("Игрок оскорбил меня", images_count=1))
        self.assertTrue(with_count["extracted"]["has_evidence"])
        self.assertTrue(any("Метаданные" in reason for reason in with_count["reasons"]))

    def test_evidence_negation_and_multiple_languages(self):
        for text in ("Скриншотов нет", "Нет скриншота", "Жалоба без скринов", "I have no screenshot", "Скриншот жоқ"):
            with self.subTest(text=text):
                result = self.service.triage(ticket(text))
                self.assertFalse(result["extracted"]["has_evidence"])
        for text in ("I have screenshots", "Скриншот бар", "Нет видео, но есть скриншот"):
            with self.subTest(text=text):
                result = self.service.triage(ticket(text))
                self.assertTrue(result["extracted"]["has_evidence"])
        # Explicit attachment metadata takes precedence over a negative claim.
        result = self.service.triage(ticket("Скриншотов нет", images_count=1))
        self.assertTrue(result["extracted"]["has_evidence"])

    def test_server_and_region_are_strings_not_language_hints(self):
        for extra, expected in (({"server": 12}, "12"), ({"server": " 03 "}, "03"), ({"region": "kz"}, "kz"), ({"server_lang": "kk"}, None)):
            with self.subTest(extra=extra):
                result = self.service.triage(ticket("Игрок оскорбил меня", **extra))
                self.assertEqual(result["extracted"]["server"], expected)
        result = self.service.triage(ticket("Игрок оскорбил меня на сервере 17", region="kz"))
        self.assertEqual(result["extracted"]["server"], "17")

    def test_ambiguous_request_needs_human_review(self):
        for text in ("Помогите", "Ау", ""):
            with self.subTest(text=text):
                result = self.service.triage(ticket(text, kind="report"))
                self.assertTrue(result["needs_human"])
                self.assertTrue(result["reasons"])

    def test_multilingual_and_cp1251(self):
        kazakh = self.service.triage(ticket("Ойыншы мені чатта ќорлады"))
        self.assertEqual(kazakh["lang"], "kk")
        self.assertEqual(kazakh["category"], "complaint.insult")
        self.assertEqual(kazakh["draft_reply"]["lang"], "kk")
        uzbek = self.service.triage(ticket("Meni chatda haqorat qildi"))
        self.assertEqual(uzbek["lang"], "uz")
        self.assertEqual(uzbek["category"], "complaint.insult")
        self.assertEqual(uzbek["draft_reply"]["lang"], "uz")
        self.assertEqual(normalize("ўйин", "uz"), "ўйин")
        self.assertEqual(normalize("ќорлады", "kk"), "қорлады")
        self.assertEqual(detect_language("Менің аккаунтымды ўрлады", "kk"), "kk")
        self.assertEqual(detect_language("мени ўйинда ҳақорат қилди"), "uz")
        self.assertEqual(detect_language("Убил в зелёной зоне"), "ru")

    def test_payment_and_ban_never_trigger_automatic_clarification(self):
        for text in ("Payment failed", "Меня забанили", "Потерял доступ к аккаунту"):
            result = self.service.triage(ticket(text, kind="report"))
            self.assertTrue(result["needs_human"], text)
        benign = self.service.triage(ticket("Привет", kind="report"))
        self.assertEqual(benign["category"], "report.offtopic")
        self.assertFalse(benign["needs_human"])

    def test_optional_knowledge_is_extractive_and_reviewed(self):
        service = TriageService(Catalog(self.rules, self.taxonomy, self.knowledge))
        result = service.triage(ticket("Как починить двигатель?", kind="report"))
        self.assertEqual(result["category"], "report.question")
        self.assertIn("используйте игровой сервис ремонта", result["draft_reply"]["text"])
        self.assertEqual(result["draft_reply"]["cited"], [])
        self.assertTrue(result["needs_human"])

    def test_invalid_inputs_are_controlled_errors(self):
        cases = [None, {}, {"kind": []}, {"kind": "report", "messages": [{"role": [], "text": "x"}]}, {"kind": "report", "messages": [{"role": "admin", "text": "x"}]}]
        for item in cases:
            with self.subTest(item=item), self.assertRaises(InputError):
                self.service.triage(item)

    def test_spam_is_detected(self):
        result = self.service.triage(ticket("аааааааааааааааа", kind="report"))
        self.assertTrue(result["is_spam_or_duplicate"])
        self.assertTrue(result["needs_human"])


class DuplicateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        rules, taxonomy, _ = write_fixtures(self.tmp.name)
        self.service = TriageService(Catalog(rules, taxonomy))

    def tearDown(self):
        self.tmp.cleanup()

    def make(self, reporter: str, number: int, minute: int, target: str = "target") -> dict:
        return ticket("Игрок оскорбил меня в чате", reporter_hash=reporter, reported_hash=target, ticket_id=str(number), created_at=f"2026-03-14T10:{minute:02d}:00")

    def test_fifth_similar_ticket_same_reporter_is_flagged(self):
        results = [self.service.triage(self.make("r1", n, n)) for n in range(1, 6)]
        self.assertEqual([r["is_spam_or_duplicate"] for r in results], [False, False, False, False, True])
        self.assertFalse(self.service.triage(self.make("r2", 6, 6))["is_spam_or_duplicate"])
        self.assertFalse(self.service.triage(self.make("r1", 7, 7, target="different"))["is_spam_or_duplicate"])

    def test_repeating_identical_ticket_id_is_idempotent(self):
        obj = self.make("r1", 1, 1)
        for _ in range(6):
            self.assertFalse(self.service.triage(obj)["is_spam_or_duplicate"])

    def test_no_identity_never_merges_players(self):
        for _ in range(6):
            self.assertFalse(self.service.triage(ticket("Игрок оскорбил меня в чате"))["is_spam_or_duplicate"])


if __name__ == "__main__":
    unittest.main()
