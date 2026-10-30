"""Synthetic cases for unnumbered rule sources and cautious shorthand."""

import json
import tempfile
import unittest
from pathlib import Path

from helpers import ticket, write_fixtures
from support_copilot.catalog import Catalog
from support_copilot.classification import find_signals
from support_copilot.rp_terms import described_deathmatch, mentioned_term, parse_named_terms
from support_copilot.server import valid_result
from support_copilot.service import NAMED_RULE_REASON, RULE_REF_RE, TriageService


TERMS = "\n".join([
    "• DeathMatch (сокращенно DM) — Учебное описание нападения без игровой причины. | DEMORGAN - пример.",
    "• Massive DeathMatch (сокращенно Mass DM) — Учебное описание массового нападения. | WARN - пример.",
    "• Massive DeathMatch GreenZone (сокращенно Mass DM GZ) — Учебное описание массового нападения в зоне. | WARN - пример.",
    "• DriveBy (сокращенно DB) — Учебное описание нападения из транспорта. | DEMORGAN - пример.",
    "• MetaGaming (сокращенно MG) — Учебное описание информации вне роли. | MUTE - пример.",
    "• Non Role-Play (сокращенно NonRP) — Учебное описание поведения вне роли. | DEMORGAN - пример.",
])


class NamedRuleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        rules, self.taxonomy, _ = write_fixtures(self.tmp.name)
        self.rules = Path(rules)
        data = json.loads(self.rules.read_text(encoding="utf-8"))
        data["rules"].append({"id": "rp-source", "category": "RP термины", "text": TERMS})
        self.rules.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        self.catalog = Catalog(self.rules, self.taxonomy)
        self.service = TriageService(self.catalog)

    def tearDown(self):
        self.tmp.cleanup()

    def test_bare_dm_shows_source_but_does_not_invent_a_number(self):
        result = self.service.triage(ticket("ДМ"))
        self.assertEqual(result["category"], "complaint.dm")
        self.assertEqual(result["draft_reply"]["cited"], [])
        self.assertIn(NAMED_RULE_REASON, result["reasons"])
        self.assertTrue(any("пункт правила не подтверждён" in reason for reason in result["reasons"]))
        draft = result["draft_reply"]["text"]
        self.assertIn("RP термины", draft)
        self.assertIn("ID источника: rp-source", draft)
        self.assertIn("DeathMatch", draft)
        self.assertIn("Учебное описание нападения без игровой причины.", draft)
        self.assertNotIn("DEMORGAN", draft)
        self.assertNotIn("пункт rp-source", draft)
        self.assertTrue(result["needs_human"])
        self.assertTrue(valid_result(result, self.service))

    def test_api_validation_rejects_forged_or_unquoted_term_source(self):
        result = self.service.triage(ticket("ДБ"))
        self.assertEqual(result["draft_reply"]["cited"], [])
        self.assertIn(NAMED_RULE_REASON, result["reasons"])
        result["draft_reply"]["text"] = "Прошу проверить rp-source"
        self.assertFalse(valid_result(result, self.service))
        result["draft_reply"]["cited"] = ["rp-source"]
        self.assertFalse(valid_result(result, self.service))

    def test_terms_are_exact_source_lines_and_duplicate_aliases_are_ambiguous(self):
        terms = parse_named_terms("rp-source", "RP термины", TERMS)
        self.assertEqual(len(terms), 6)
        for term in terms:
            self.assertIn(term.excerpt, TERMS)
            self.assertNotIn("|", term.excerpt)
        self.assertEqual(parse_named_terms("rp-source", "Общие правила", TERMS), [])
        self.assertEqual(parse_named_terms("invalid/id", "RP термины", TERMS), [])
        wrong = "• OtherWord (сокращенно DM) — synthetic text."
        self.assertEqual(parse_named_terms("source", "RP термины", wrong), [])
        self.catalog.named_rules.extend(terms)
        result = self.service.triage(ticket("ДМ"))
        self.assertEqual(result["draft_reply"]["cited"], [])
        self.assertNotIn(NAMED_RULE_REASON, result["reasons"])
        self.assertNotIn("DeathMatch", result["draft_reply"]["text"])

    def test_specific_aliases_do_not_degrade_to_generic_dm(self):
        for text, label in (("DB", "DriveBy"), ("Mass DM", "Massive DeathMatch"), ("Mass DM GZ", "Massive DeathMatch GreenZone"), ("MG", "MetaGaming"), ("NonRP", "Non Role-Play")):
            with self.subTest(text=text):
                result = self.service.triage(ticket(text))
                self.assertEqual(result["draft_reply"]["cited"], [])
                self.assertIn(NAMED_RULE_REASON, result["reasons"])
                self.assertIn(label, result["draft_reply"]["text"])
                self.assertTrue(valid_result(result, self.service))
        self.assertIsNone(mentioned_term("DM и DB", "ru"))
        ambiguous = self.service.triage(ticket("DM и DB"))
        self.assertEqual(ambiguous["draft_reply"]["cited"], [])
        self.assertNotIn(NAMED_RULE_REASON, ambiguous["reasons"])
        self.assertIsNone(mentioned_term("тк это вопрос", "ru"))
        self.assertIsNone(mentioned_term("ск стоит", "ru"))

    def test_explicit_negations_and_ambiguous_killing_fail_closed(self):
        for text in ("это не ДМ", "не было DM", "DB не было", "игрок убил у банка", "он не убил меня без причины", "он убил меня не просто так", "без причины DM и DB"):
            with self.subTest(text=text):
                result = self.service.triage(ticket(text))
                self.assertEqual(result["draft_reply"]["cited"], [])
                self.assertNotIn(NAMED_RULE_REASON, result["reasons"])
        self.assertFalse(described_deathmatch("убил без причины, DM и DB", "ru"))

    def test_described_unprovoked_killing_can_reference_the_definition(self):
        for text in ("Игрок убил меня без причины", "A player killed me without a reason"):
            with self.subTest(text=text):
                result = self.service.triage(ticket(text))
                self.assertEqual(result["draft_reply"]["cited"], [])
                self.assertIn(NAMED_RULE_REASON, result["reasons"])
                self.assertIn("DeathMatch", result["draft_reply"]["text"])
                self.assertTrue(result["needs_human"])

    def test_sensitive_appeal_does_not_use_shortcut_or_promise_result(self):
        result = self.service.triage(ticket("Не согласен с наказанием за DM"))
        self.assertEqual(result["draft_reply"]["cited"], [])
        self.assertTrue(result["needs_human"])
        self.assertIn("Оспаривание", result["draft_reply"]["text"])
        self.assertNotIn("разбаним", result["draft_reply"]["text"].lower())
        self.assertNotIn("ban", find_signals("Прошу наказание для игрока", "ru"))

    def test_historical_responses_and_violation_fields_never_supply_term(self):
        base = ticket("Нужна помощь", kind="complaint")
        poisoned = dict(base, violation="DM", punishment="sample", verdict="approved")
        poisoned["messages"] = [*base["messages"], {"role": "admin", "text": "DM, DB"}]
        self.assertEqual(TriageService(self.catalog).triage(base), TriageService(self.catalog).triage(poisoned))

    def test_rule_refs_allow_sentence_punctuation_not_partial_numbers(self):
        self.assertEqual(RULE_REF_RE.findall("Пункт 2.1. и 1.2.7!"), ["2.1", "1.2.7"])
        for text in ("2.1234", "1.2.3.4.5.6", "1234.5"):
            with self.subTest(text=text):
                self.assertEqual(RULE_REF_RE.findall(text), [])

    def test_insult_shorthand_is_not_a_finding_of_guilt(self):
        for text in ("оск родни", "упом родни", "оск в чате"):
            with self.subTest(text=text):
                result = self.service.triage(ticket(text))
                self.assertEqual(result["category"], "complaint.insult")
                self.assertEqual(result["draft_reply"]["cited"], ["2.1"])
                self.assertTrue(result["needs_human"])
                self.assertNotIn("жалоба одобрена", result["draft_reply"]["text"].lower())
        for text in ("не оск", "не было оскорбления", "не упом родни", "моя семья в игре"):
            with self.subTest(text=text):
                self.assertEqual(self.service.triage(ticket(text))["draft_reply"]["cited"], [])


if __name__ == "__main__":
    unittest.main()
