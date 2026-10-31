"""Synthetic tests for validation exports, human review and loopback timing."""

import argparse
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from helpers import ticket, write_fixtures
from support_copilot.audit import audit
from support_copilot.batch import iter_tickets, predict
from support_copilot.benchmark import benchmark
from support_copilot.catalog import Catalog
from support_copilot.config import make_service
from support_copilot.evaluate import evaluate
from support_copilot.review_pack import create_review_pack
from support_copilot.service import InputError, TriageService


class QualityToolsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.rules, self.taxonomy, self.knowledge = write_fixtures(self.tmp.name)
        self.input = self.root / "validation.jsonl"
        entries = []
        for i in range(8):
            entry = ticket("Игрок оскорбил меня в чате <digits> и <url>", ticket_id=f"synthetic-{i}", category="do-not-leak", verdict="private-verdict")
            entry["messages"].append({"role": "admin", "text": "private-administrator-message"})
            entries.append(entry)
        self.input.write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in entries), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def service(self):
        return TriageService(Catalog(self.rules, self.taxonomy))

    def test_html_wrapper_reads_json_lines_without_dom_data_loss(self):
        source = self.root / "synthetic.HTML"
        payload = ticket("Сохрани буквально <digits> и <url>", kind="report", ticket_id="one")
        source.write_text("\ufeff<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n<meta charset=\"UTF-8\">\n<title>Document</title>\n</head>\n<body>\n<h4>\n" + json.dumps(payload, ensure_ascii=False) + "\n</h4>\n</body>\n</html>\n", encoding="utf-8")
        records = list(iter_tickets(str(source)))
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0][1], payload)
        output = self.root / "predictions.jsonl"
        self.assertEqual(predict(self.service(), str(source), str(output)), 1)
        self.assertEqual(json.loads(output.read_text(encoding="utf-8"))["ticket_id"], "one")

    def test_html_unknown_content_invalid_json_and_empty_fail_without_overwriting(self):
        output = self.root / "predictions.jsonl"
        output.write_text("unchanged", encoding="utf-8")
        for contents in ("<body>\n<script>bad</script>\n</body>", "<body>\n{broken}\n</body>", "<body>\n</body>"):
            with self.subTest(contents=contents):
                source = self.root / "validation.html"
                source.write_text(contents, encoding="utf-8")
                with self.assertRaises(InputError):
                    predict(self.service(), str(source), str(output))
                self.assertEqual(output.read_text(encoding="utf-8"), "unchanged")

    def test_local_tools_reject_a_forged_excerpt_and_preserve_outputs(self):
        service = self.service()
        unsafe = service.triage(ticket("Игрок оскорбил меня в чате"))
        self.assertEqual(unsafe["draft_reply"]["cited"], ["2.1"])
        unsafe["draft_reply"]["text"] = "Пункт 2.1: выдуманная формулировка."
        output = self.root / "output.jsonl"
        output.write_text("prior-output", encoding="utf-8")
        commands = (
            lambda: predict(service, str(self.input), str(output)),
            lambda: create_review_pack(service, str(self.input), str(output), count=2),
            lambda: evaluate(service, str(self.input)),
            lambda: audit(service, str(self.input)),
        )
        with patch.object(service, "triage", return_value=unsafe):
            for command in commands:
                with self.subTest(command=command), self.assertRaises(InputError):
                    command()
                self.assertEqual(output.read_text(encoding="utf-8"), "prior-output")
        self.assertEqual(list(self.root.glob(".copilot-*")), [])

    def test_deterministic_review_pack_excludes_gold_and_admin_messages(self):
        first, second = self.root / "review-a.jsonl", self.root / "review-b.jsonl"
        self.assertEqual(create_review_pack(self.service(), str(self.input), str(first), count=3, seed=42), 3)
        self.assertEqual(create_review_pack(self.service(), str(self.input), str(second), count=3, seed=42), 3)
        self.assertEqual(first.read_text(encoding="utf-8"), second.read_text(encoding="utf-8"))
        rows = [json.loads(line) for line in first.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(len({row["ticket_id"] for row in rows}), 3)
        for row in rows:
            content = json.dumps(row, ensure_ascii=False)
            self.assertNotIn("private-administrator-message", content)
            self.assertNotIn("private-verdict", content)
            self.assertNotIn("do-not-leak", content)
            self.assertIn("<digits> и <url>", content)
            self.assertIsNone(row["review"]["category"])
            self.assertEqual(len(row["draft_sha256"]), 64)
        if os.name != "nt":
            self.assertEqual(first.stat().st_mode & 0o077, 0)

    def test_human_scores_are_aggregated_only_when_fingerprint_matches(self):
        sample = self.root / "review.jsonl"
        create_review_pack(self.service(), str(self.input), str(sample), count=3, seed=42)
        rows = [json.loads(line) for line in sample.read_text(encoding="utf-8").splitlines()]
        for row in rows:
            row["review"].update(category="complaint.insult", priority="p1", draft_rating=4, citations_relevant=True, language_rating=5, reviewer_native=True)
        sample.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
        result = evaluate(self.service(), str(self.input), str(sample))
        self.assertEqual(result["tickets"], 8)
        self.assertEqual(result["category_labeled"], 3)
        self.assertEqual(result["category_accuracy"], 1.0)
        self.assertEqual(result["priority_labeled"], 3)
        self.assertEqual(result["draft_rating_reviewed"], 3)
        self.assertEqual(result["draft_rating_mean"], 4.0)
        self.assertEqual(result["citation_relevance_share"], 1.0)
        self.assertEqual(result["native_language_reviews"], {"ru": 3})
        rows[0]["draft_sha256"] = "0" * 64
        sample.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
        with self.assertRaises(InputError):
            evaluate(self.service(), str(self.input), str(sample))

    def test_blind_class_labels_and_draft_reviews_can_be_independent(self):
        blind = self.root / "blind.jsonl"
        drafts = self.root / "drafts.jsonl"
        create_review_pack(self.service(), str(self.input), str(blind), count=3, seed=5, blind_labels=True)
        create_review_pack(self.service(), str(self.input), str(drafts), count=3, seed=5)
        blind_rows = [json.loads(line) for line in blind.read_text(encoding="utf-8").splitlines()]
        draft_rows = [json.loads(line) for line in drafts.read_text(encoding="utf-8").splitlines()]
        self.assertEqual([r["ticket_id"] for r in blind_rows], [r["ticket_id"] for r in draft_rows])
        for row in blind_rows:
            self.assertNotIn("draft_reply", row)
            self.assertNotIn("draft_sha256", row)
            self.assertNotIn("needs_human", row)
            row["review"].update(category="complaint.insult", priority="p1")
        for row in draft_rows:
            row["review"].update(draft_rating=4, citations_relevant=True)
        blind.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in blind_rows), encoding="utf-8")
        drafts.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in draft_rows), encoding="utf-8")
        result = evaluate(self.service(), str(self.input), str(blind), str(drafts))
        self.assertEqual(result["category_labeled"], 3)
        self.assertEqual(result["draft_rating_reviewed"], 3)
        self.assertEqual(result["citation_relevance_reviewed"], 3)
        changed = [json.loads(line) for line in self.input.read_text(encoding="utf-8").splitlines()]
        index = next(i for i, row in enumerate(changed) if row["ticket_id"] == blind_rows[0]["ticket_id"])
        changed[index]["messages"][0]["text"] += " changed"
        self.input.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in changed), encoding="utf-8")
        with self.assertRaises(InputError):
            evaluate(self.service(), str(self.input), str(blind), str(drafts))

    def test_language_filtered_review_is_based_on_detected_not_gold_language(self):
        sample = self.root / "filtered.jsonl"
        self.assertEqual(create_review_pack(self.service(), str(self.input), str(sample), count=3, language="ru"), 3)
        self.assertEqual(create_review_pack(self.service(), str(self.input), str(sample), count=3, language="kk"), 0)
        self.assertEqual(sample.read_text(encoding="utf-8"), "")
        with self.assertRaises(InputError):
            create_review_pack(self.service(), str(self.input), str(sample), count=3, language="unknown")

    def test_edited_review_pack_source_or_draft_is_rejected(self):
        sample = self.root / "review.jsonl"
        create_review_pack(self.service(), str(self.input), str(sample), count=2)
        rows = [json.loads(line) for line in sample.read_text(encoding="utf-8").splitlines()]
        rows[0]["source"]["player_messages"][0] = "changed"
        sample.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
        with self.assertRaises(InputError):
            evaluate(self.service(), str(self.input), str(sample))
        create_review_pack(self.service(), str(self.input), str(sample), count=2)
        rows = [json.loads(line) for line in sample.read_text(encoding="utf-8").splitlines()]
        rows[0]["draft_reply"]["text"] = "changed"
        sample.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
        with self.assertRaises(InputError):
            evaluate(self.service(), str(self.input), str(sample))

    def test_bad_or_unmatched_human_labels_are_not_silently_accepted(self):
        sample = self.root / "labels.jsonl"
        invalid = [
            {"ticket_id": "synthetic-0", "category": "not.in.taxonomy"},
            {"ticket_id": "synthetic-0", "draft_rating": 4},
            {"ticket_id": "synthetic-0", "draft_rating": True, "draft_sha256": "0" * 64},
            {"ticket_id": "not-in-validation", "category": "complaint.insult"},
        ]
        for entry in invalid:
            with self.subTest(entry=entry):
                sample.write_text(json.dumps(entry, ensure_ascii=False) + "\n", encoding="utf-8")
                with self.assertRaises(InputError):
                    evaluate(self.service(), str(self.input), str(sample))
        duplicate = {"ticket_id": "synthetic-0", "category": "complaint.insult"}
        sample.write_text((json.dumps(duplicate) + "\n") * 2, encoding="utf-8")
        with self.assertRaises(InputError):
            evaluate(self.service(), str(self.input), str(sample))

    def test_unlabeled_data_and_rule_coverage_are_reported_honestly(self):
        # Remove the intentionally invalid gold placeholder from this synthetic input.
        rows = [json.loads(line) for line in self.input.read_text(encoding="utf-8").splitlines()]
        for row in rows:
            row.pop("category")
        self.input.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
        result = evaluate(self.service(), str(self.input))
        self.assertEqual(result["rules_required_count"], 8)
        self.assertEqual(result["rules_required_with_citation"], 8)
        self.assertEqual(result["knowledge_articles_loaded"], 0)
        self.assertEqual(result["category_labeled"], 0)
        self.assertIsNone(result["category_accuracy"])
        self.assertEqual(result["draft_rating_reviewed"], 0)
        self.assertIsNone(result["draft_rating_mean"])
        self.assertIsNone(result["citation_relevance_share"])

    def test_invalid_embedded_gold_label_fails_instead_of_counting_a_metric(self):
        with self.assertRaises(InputError):
            evaluate(self.service(), str(self.input))

    def test_loopback_benchmark_reports_status_and_review_handoff(self):
        result = benchmark(self.service(), str(self.input), requests=3, workers=1)
        self.assertEqual(result["requests"], 3)
        self.assertEqual(result["http_status_counts"], {"200": 3})
        self.assertEqual(result["valid_result_count"], 3)
        self.assertEqual(result["review_handoff_counts"], {"queued": 3})
        self.assertEqual(result["required_handoff_failures"], 0)
        self.assertGreaterEqual(result["http_p95_ms"], 0)
        concurrent = benchmark(self.service(), str(self.input), requests=8, workers=4)
        self.assertEqual(concurrent["http_status_counts"], {"200": 8})
        self.assertEqual(concurrent["required_handoff_failures"], 0)

    def test_local_knowledge_file_is_discovered_but_explicit_path_wins(self):
        data = self.root / "data"
        data.mkdir()
        (data / "knowledge.json").write_text(Path(self.knowledge).read_text(encoding="utf-8"), encoding="utf-8")
        current = os.getcwd()
        try:
            os.chdir(self.root)
            args = argparse.Namespace(rules=self.rules, taxonomy=self.taxonomy, knowledge=None)
            self.assertEqual(len(make_service(args).catalog.articles), 1)
            empty = self.root / "empty-knowledge.json"
            empty.write_text('{"articles": []}', encoding="utf-8")
            args.knowledge = str(empty)
            self.assertEqual(len(make_service(args).catalog.articles), 0)
        finally:
            os.chdir(current)


if __name__ == "__main__":
    unittest.main()
