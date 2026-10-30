import gzip
import http.client
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from helpers import ticket, write_fixtures
from support_copilot.batch import predict
from support_copilot.catalog import Catalog
from support_copilot.evaluate import evaluate, macro_f1
from support_copilot.server import CopilotServer
from support_copilot.service import InputError, TriageService


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        rules, taxonomy, _ = write_fixtures(self.tmp.name)
        self.service = TriageService(Catalog(rules, taxonomy))
        self.server = CopilotServer(("127.0.0.1", 0), self.service)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.tmp.cleanup()

    def post(self, path: str, data: bytes):
        request = urllib.request.Request(self.url + path, data=data, headers={"Content-Type": "application/json"})
        return urllib.request.urlopen(request, timeout=3)

    def test_health_and_static_assets(self):
        with urllib.request.urlopen(self.url + "/health", timeout=3) as response:
            health = json.load(response)
        self.assertEqual(health["status"], "ok")
        self.assertGreater(health["rules_loaded"], 0)
        with urllib.request.urlopen(self.url + "/", timeout=3) as response:
            self.assertIn("Support Copilot", response.read().decode())
            self.assertIn("no-store", response.headers["Cache-Control"])
        with urllib.request.urlopen(self.url + "/brand-g.svg", timeout=3) as response:
            self.assertEqual(response.headers.get_content_type(), "image/svg+xml")
            self.assertIn(b"<svg", response.read())
        with urllib.request.urlopen(self.url + "/favicon.svg", timeout=3) as response:
            self.assertEqual(response.headers.get_content_type(), "image/svg+xml")
            self.assertIn(b"<svg", response.read())
        with urllib.request.urlopen(self.url + "/admin", timeout=3) as response:
            self.assertIn("Панель администратора", response.read().decode())
        for path in ("/admin.css", "/admin.js"):
            with urllib.request.urlopen(self.url + path, timeout=3) as response:
                self.assertEqual(response.status, 200)
        with urllib.request.urlopen(self.url + "/city-banner.jpg", timeout=3) as response:
            self.assertEqual(response.headers.get_content_type(), "image/jpeg")
            self.assertTrue(response.read().startswith(b"\xff\xd8\xff"))
        with self.assertRaises(urllib.error.HTTPError) as failure:
            urllib.request.urlopen(self.url + "/data/rules.json", timeout=3)
        self.assertEqual(failure.exception.code, 404)

    def test_post_triage_contract(self):
        payload = ticket("Alex_Nova оскорбил меня в чате")
        payload["messages"][0]["attachments"] = 1
        with self.post("/triage", json.dumps(payload, ensure_ascii=False).encode()) as response:
            result = json.load(response)
        self.assertEqual(set(result), {"lang", "category", "priority", "is_spam_or_duplicate", "extracted", "draft_reply", "needs_human", "confidence", "reasons"})
        self.assertEqual(result["category"], "complaint.insult")
        self.assertEqual(result["draft_reply"]["cited"], ["2.1"])
        self.assertTrue(result["needs_human"])

    def test_mentions_are_unverified_and_server_is_a_string_over_http(self):
        payload = ticket("Игрок оскорбил меня, скриншоты есть", server=12)
        with self.post("/triage", json.dumps(payload, ensure_ascii=False).encode()) as response:
            result = json.load(response)
        self.assertTrue(result["extracted"]["has_evidence"])
        self.assertEqual(result["extracted"]["server"], "12")
        self.assertTrue(any("не подтверждены" in reason for reason in result["reasons"]))

    def test_invalid_json_and_types_are_400_without_echoing_input(self):
        invalid_unicode = b'{"kind":"report","messages":[{"role":"player","text":"' + bytes([92]) + b'ud800"}]}'
        for body in (b"not json", b'{"kind": [], "messages": []}', invalid_unicode):
            with self.subTest(body=body):
                with self.assertRaises(urllib.error.HTTPError) as failure:
                    self.post("/triage", body)
                self.assertEqual(failure.exception.code, 400)
                self.assertIn("error", json.load(failure.exception))

    def test_oversized_body_is_rejected(self):
        # The server rejects from the header without waiting for a 1 MB body.
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=3)
        try:
            connection.putrequest("POST", "/triage")
            connection.putheader("Content-Length", str(1_048_576 + 1))
            connection.endheaders()
            self.assertEqual(connection.getresponse().status, 413)
        finally:
            connection.close()


class BatchAndEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        rules, taxonomy, _ = write_fixtures(self.tmp.name)
        self.service = TriageService(Catalog(rules, taxonomy))

    def tearDown(self):
        self.tmp.cleanup()

    def test_gzip_input_and_output_and_order(self):
        first = ticket("Игрок оскорбил меня в чате", ticket_id="one", verdict="approved")
        first["messages"].append({"role": "admin", "text": "Платёж и взлом"})
        second = ticket("Привет", kind="report", ticket_id="two")
        input_path, output_path = self.root / "input.jsonl.gz", self.root / "output.jsonl.gz"
        with gzip.open(input_path, "wt", encoding="utf-8") as stream:
            stream.write(json.dumps(first, ensure_ascii=False) + "\n\n" + json.dumps(second, ensure_ascii=False) + "\n")
        self.assertEqual(predict(self.service, str(input_path), str(output_path)), 2)
        with gzip.open(output_path, "rt", encoding="utf-8") as stream:
            rows = [json.loads(line) for line in stream]
        self.assertEqual([row["ticket_id"] for row in rows], ["one", "two"])
        self.assertEqual(rows[0]["category"], "complaint.insult")
        self.assertEqual(rows[1]["category"], "report.offtopic")
        self.assertNotIn("verdict", rows[0])

    def test_failure_does_not_overwrite_previous_output(self):
        input_path, output_path = self.root / "input.jsonl", self.root / "output.jsonl"
        input_path.write_text(json.dumps(ticket("Привет", kind="report")) + "\nnot-json\n", encoding="utf-8")
        output_path.write_text("prior-output", encoding="utf-8")
        with self.assertRaises(InputError):
            predict(self.service, str(input_path), str(output_path))
        self.assertEqual(output_path.read_text(), "prior-output")
        self.assertEqual(list(self.root.glob(".copilot-*")), [])

    def test_same_input_output_rejected(self):
        path = self.root / "same.jsonl"
        path.write_text("", encoding="utf-8")
        with self.assertRaises(InputError):
            predict(self.service, str(path), str(path))

    def test_missing_labels_are_null_not_invented_metrics(self):
        path = self.root / "valid.jsonl"
        path.write_text(json.dumps(ticket("Привет", kind="report"), ensure_ascii=False) + "\n", encoding="utf-8")
        result = evaluate(self.service, str(path))
        self.assertEqual(result["tickets"], 1)
        self.assertEqual(result["category_labeled"], 0)
        self.assertIsNone(result["category_accuracy"])
        self.assertIsNone(result["priority_macro_f1"])
        self.assertIsNotNone(result["local_pipeline_p95_ms"])

    def test_macro_f1_uses_present_labels(self):
        self.assertAlmostEqual(macro_f1(["p0", "p0", "p1"], ["p0", "p1", "p1"]), (2/3 + 2/3) / 2)
        self.assertIsNone(macro_f1([], []))


if __name__ == "__main__":
    unittest.main()
