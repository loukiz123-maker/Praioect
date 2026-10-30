import json
import tempfile
import unittest
from pathlib import Path

from helpers import ticket, write_fixtures
from support_copilot.audit import audit
from support_copilot.catalog import Catalog
from support_copilot.service import TriageService


class AggregateAuditTests(unittest.TestCase):
    def test_aggregate_report_never_contains_player_or_admin_contents(self):
        with tempfile.TemporaryDirectory() as directory:
            rules, taxonomy, _ = write_fixtures(directory)
            service = TriageService(Catalog(rules, taxonomy))
            rows = [
                ticket("Игрок оскорбил меня в чате PRIVATE_PLAYER_MARKER", ticket_id="SECRET_ID_1", verdict="historic_decision", punishment="historic_penalty", violation="historic_violation"),
                ticket("Нужна помощь PRIVATE_OTHER_MARKER", kind="report", ticket_id="SECRET_ID_2"),
            ]
            rows[0]["messages"].append({"role": "admin", "text": "PRIVATE_ADMIN_MARKER: недостаточно доказательств, возможен пункт 2.1."})
            rows[1]["messages"].append({"role": "admin", "text": "ANOTHER_PRIVATE_ADMIN_MARKER"})
            source = Path(directory) / "synthetic.jsonl"
            source.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
            report = audit(service, str(source))
            counts = report["counts"]
            self.assertEqual(counts["tickets"], 2)
            self.assertEqual(counts["historical_admin_reply_present"], 2)
            self.assertEqual(counts["historical_verdict_field_present"], 1)
            self.assertEqual(counts["historical_punishment_field_present"], 1)
            self.assertEqual(counts["historical_violation_field_present"], 1)
            self.assertEqual(counts["historical_reply_evidence_gap_phrase"], 1)
            self.assertEqual(counts["historical_reply_existing_number_mentioned"], 1)
            self.assertEqual(counts["generated_number_also_mentioned_in_historical_reply"], 1)
            serialized = json.dumps(report, ensure_ascii=False)
            for marker in ("PRIVATE_PLAYER_MARKER", "PRIVATE_OTHER_MARKER", "PRIVATE_ADMIN_MARKER", "SECRET_ID_1", "historic_decision", "historic_penalty", "historic_violation"):
                self.assertNotIn(marker, serialized)
            self.assertIn("не подтверждает", serialized)


if __name__ == "__main__":
    unittest.main()
