"""Synthetic tests for protected human review and failure handoff."""

import io
import json
import os
import sqlite3
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import patch

from helpers import ticket, write_fixtures

from support_copilot import server as server_module
from support_copilot.admin_queue import (
    AdminQueue,
    QueueConflict,
    QueueFull,
    QueueNotFound,
    load_admin_key,
    new_receipt,
)
from support_copilot.catalog import Catalog
from support_copilot.server import CopilotServer
from support_copilot.service import InputError, TriageService

# A synthetic fixture, not an actual access key.
TEST_KEY = "synthetic-admin-access-key-1234567890"


class AdminApiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        rules, taxonomy, _ = write_fixtures(self.tmp.name)
        self.service = TriageService(Catalog(rules, taxonomy))
        self.queue = AdminQueue(self.root / "queue.sqlite3")
        self.server = CopilotServer(("127.0.0.1", 0), self.service, self.queue, TEST_KEY)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.tmp.cleanup()

    def request(self, path, *, method="GET", value=None, key=None, receipt=None, content_type="application/json"):
        headers = {}
        data = None
        if value is not None:
            headers["Content-Type"] = content_type
            data = json.dumps(value, ensure_ascii=False).encode("utf-8")
        if key is not None:
            headers["Authorization"] = f"Bearer {key}"
        if receipt is not None:
            headers["X-Review-Receipt"] = receipt
        request = urllib.request.Request(self.url + path, method=method, data=data, headers=headers)
        try:
            response = urllib.request.urlopen(request, timeout=5)
        except urllib.error.HTTPError as exc:
            response = exc
        with response:
            return response.status, response.headers, json.load(response)

    def triage(self, payload=None, receipt=None):
        return self.request("/triage", method="POST", value=payload or ticket("Игрок оскорбил меня"), receipt=receipt)

    def admin_list(self):
        status, _, body = self.request("/admin/api/reviews", key=TEST_KEY)
        self.assertEqual(status, 200)
        return body

    def feedback(self):
        request = urllib.request.Request(
            self.url + "/admin/api/feedback/export", headers={"Authorization": f"Bearer {TEST_KEY}"},
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            raw = response.read()
            rows = [json.loads(line) for line in raw.decode("utf-8").splitlines()]
            self.assertEqual(int(response.headers["X-Feedback-Count"]), len(rows))
            self.assertEqual(int(response.headers["Content-Length"]), len(raw))
            self.assertEqual(response.headers.get_content_type(), "application/x-ndjson")
            self.assertEqual(response.headers["Cache-Control"], "no-store")
            return rows, raw

    def test_auth_and_private_files_are_not_public(self):
        for path in ("/admin/api/reviews", "/admin/api/session", "/admin/api/feedback/export"):
            self.assertEqual(self.request(path)[0], 401)
            status, _, body = self.request(path, key="not-the-right-key")
            self.assertEqual(status, 401)
            self.assertNotIn(TEST_KEY, json.dumps(body))
        self.assertEqual(self.request("/admin/api/session", key=TEST_KEY)[0], 200)
        self.assertEqual(self.request("/data/admin.key")[0], 404)
        self.assertEqual(self.request("/data/admin-queue.sqlite3")[0], 404)
        self.assertEqual(self.request("/admin/api/reviews/" + "a" * 32, method="POST", value={}, key=None)[0], 401)
        self.assertEqual(self.triage(receipt="not-a-token")[0], 400)
        self.assertEqual(self.request("/triage", method="POST", value=ticket("hello"), content_type="text/plain")[0], 415)

    def test_human_review_queues_automatically_and_admin_can_return_a_reply(self):
        payload = ticket("Игрок Alex_Nova оскорбил меня", reporter_hash="private-hash", verdict="secret-verdict")
        payload["messages"][0]["attachments"] = [{"content": "secret-attachment"}]
        payload["messages"].append({"role": "admin", "text": "secret-admin-message"})
        receipt = new_receipt()
        status, headers, result = self.triage(payload, receipt)
        self.assertEqual(status, 200)
        self.assertTrue(result["needs_human"])
        self.assertEqual(headers["X-Review-Status"], "queued")
        self.assertEqual(headers["X-Review-Receipt"], receipt)
        self.assertNotIn(receipt.encode(), (self.root / "queue.sqlite3").read_bytes())
        rows = self.admin_list()
        self.assertEqual(rows["counts"]["waiting"], 1)
        review_id = rows["items"][0]["id"]
        status, _, detail = self.request(f"/admin/api/reviews/{review_id}", key=TEST_KEY)
        self.assertEqual(status, 200)
        self.assertIn("Alex_Nova", detail["message"])
        self.assertTrue(detail["metadata"]["attachments_indicated"])
        detail_text = json.dumps(detail, ensure_ascii=False)
        for forbidden in ("secret-attachment", "secret-admin-message", "secret-verdict", "private-hash", receipt):
            self.assertNotIn(forbidden, detail_text)
        self.assertEqual(self.request("/reviews/status", receipt=new_receipt())[0], 404)
        self.assertEqual(self.request("/reviews/status")[0], 400)
        status, _, waiting = self.request("/reviews/status", receipt=receipt)
        self.assertEqual((status, waiting), (200, {"status": "waiting", "reply": None}))
        status, _, working = self.request(
            f"/admin/api/reviews/{review_id}", method="POST", key=TEST_KEY,
            value={"version": detail["version"], "status": "in_progress", "draft": "Черновик администратора"},
        )
        self.assertEqual((status, working["version"]), (200, 2))
        self.assertIsNone(self.request("/reviews/status", receipt=receipt)[2]["reply"])
        self.assertEqual(self.request(
            f"/admin/api/reviews/{review_id}", method="POST", key=TEST_KEY,
            value={"version": 1, "status": "resolved", "draft": "устаревший ответ"},
        )[0], 409)
        self.assertEqual(self.request(
            f"/admin/api/reviews/{review_id}", method="POST", key=TEST_KEY,
            value={"version": 2, "status": "resolved", "draft": "  "},
        )[0], 400)
        status, _, resolved = self.request(
            f"/admin/api/reviews/{review_id}", method="POST", key=TEST_KEY,
            value={"version": 2, "status": "resolved", "draft": "Проверенный ответ администратора"},
        )
        self.assertEqual((status, resolved["status"]), (200, "resolved"))
        self.assertEqual(
            self.request("/reviews/status", receipt=receipt)[2],
            {"status": "resolved", "reply": "Проверенный ответ администратора"},
        )
        self.assertEqual(self.request(
            f"/admin/api/reviews/{review_id}", method="DELETE", key=TEST_KEY, value={"version": 2},
        )[0], 409)
        self.assertEqual(self.request(
            f"/admin/api/reviews/{review_id}", method="DELETE", key=TEST_KEY, value={"version": 3},
        )[0], 200)
        self.assertEqual(self.request("/reviews/status", receipt=receipt)[0], 404)

    def test_admin_creates_selected_language_drafts_without_saving_or_duplicate_events(self):
        payload = ticket("Игрок Alex_Nova оскорбил меня в чате", reporter_hash="private-hash", reply_language="en")
        payload["messages"].append({"role": "admin", "text": "SECRET_HISTORICAL_RESPONSE"})
        receipt = new_receipt()
        _, _, result = self.triage(payload, receipt)
        review_id = self.admin_list()["items"][0]["id"]
        path = f"/admin/api/reviews/{review_id}/draft"
        detail_before = self.queue.get(review_id)
        events_before = {key: tuple(events) for key, events in self.service.duplicates._events.items()}
        self.assertEqual((result["lang"], result["draft_reply"]["lang"]), ("ru", "en"))
        for language, greeting in (("ru", "Здравствуйте"), ("en", "Hello"), ("kk", "Сәлеметсіз бе")):
            status, headers, body = self.request(path, method="POST", key=TEST_KEY, value={"version": 1, "language": language})
            self.assertEqual(status, 200)
            self.assertEqual(headers["Cache-Control"], "no-store")
            self.assertEqual(set(body), {"version", "draft_reply"})
            self.assertEqual((body["version"], body["draft_reply"]["lang"]), (1, language))
            self.assertIn(greeting, body["draft_reply"]["text"])
            self.assertEqual(body["draft_reply"]["cited"], result["draft_reply"]["cited"])
            self.assertIn("В игровом чате нельзя оскорблять", body["draft_reply"]["text"])
            self.assertNotIn("SECRET_HISTORICAL_RESPONSE", json.dumps(body))
            self.assertEqual(self.queue.get(review_id), detail_before)
            self.assertEqual({key: tuple(events) for key, events in self.service.duplicates._events.items()}, events_before)
            self.assertEqual(self.request("/reviews/status", receipt=receipt)[2], {"status": "waiting", "reply": None})
            self.assertEqual(self.feedback()[0], [])

    def test_admin_draft_requires_auth_validation_and_current_version(self):
        self.triage(receipt=new_receipt())
        review_id = self.admin_list()["items"][0]["id"]
        path = f"/admin/api/reviews/{review_id}/draft"
        valid = {"version": 1, "language": "en"}
        self.assertEqual(self.request(path, method="POST", value=valid)[0], 401)
        self.assertEqual(self.request(path, method="POST", key="invalid-key", value=valid)[0], 401)
        for body in (
            {}, {"version": True, "language": "en"}, {"version": 0, "language": "en"},
            {"version": 1, "language": []}, {"version": 1, "language": "auto"},
            {"version": 1, "language": "uz"}, {"version": 1, "language": "en", "message": "REPLACEMENT"},
        ):
            with self.subTest(body=body):
                self.assertEqual(self.request(path, method="POST", key=TEST_KEY, value=body)[0], 400)
        self.assertEqual(self.request(path, method="POST", key=TEST_KEY, value={"version": 999, "language": "en"})[0], 409)
        # The cancelled message-translation endpoints and asset are gone.
        self.assertEqual(self.request("/admin/api/translation", key=TEST_KEY)[0], 404)
        self.assertEqual(self.request(f"/admin/api/reviews/{review_id}/translate", method="POST", key=TEST_KEY, value={"target": "en"})[0], 404)
        self.assertEqual(self.request("/translated-by-google.png")[0], 404)
        self.assertEqual(self.queue.get(review_id)["version"], 1)

    def test_admin_draft_fails_closed_for_missing_or_changed_context(self):
        receipt = new_receipt()
        payload = ticket("Игрок оскорбил меня в чате")
        _, _, result = self.triage(payload, receipt)
        review_id = self.admin_list()["items"][0]["id"]
        path = f"/admin/api/reviews/{review_id}/draft"
        request = {"version": 1, "language": "kk"}
        # Even a structurally valid but tampered original cannot introduce a
        # different claim or rule quotation into a newly generated draft.
        tampered = json.loads(json.dumps(result))
        tampered["draft_reply"]["text"] += " 2.1 ПОДМЕНА"
        with sqlite3.connect(self.queue.path) as conn:
            conn.execute("UPDATE reviews SET result_json=? WHERE id=?", (json.dumps(tampered, ensure_ascii=False), review_id))
        self.assertEqual(self.request(path, method="POST", key=TEST_KEY, value=request)[0], 409)
        with sqlite3.connect(self.queue.path) as conn:
            conn.execute("UPDATE reviews SET result_json=NULL WHERE id=?", (review_id,))
        self.assertEqual(self.request(path, method="POST", key=TEST_KEY, value=request)[0], 503)
        self.assertEqual(self.queue.get(review_id)["version"], 1)
        self.assertEqual(self.request("/reviews/status", receipt=receipt)[2]["reply"], None)

    def test_admin_draft_rejects_changed_rule_catalog(self):
        self.triage(receipt=new_receipt())
        review_id = self.admin_list()["items"][0]["id"]
        rules_path = self.root / "rules.json"
        data = json.loads(rules_path.read_text(encoding="utf-8"))
        data["rules"][0]["text"] = data["rules"][0]["text"].replace(
            "В игровом чате нельзя оскорблять других людей и их родственников.",
            "В игровом чате нельзя оскорблять других людей и их родственников. Изменённый источник.",
        )
        rules_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        self.service.catalog = Catalog(str(rules_path), str(self.root / "taxonomy.json"))
        status, _, _ = self.request(
            f"/admin/api/reviews/{review_id}/draft", method="POST", key=TEST_KEY,
            value={"version": 1, "language": "en"},
        )
        self.assertEqual(status, 409)
        self.assertEqual(self.queue.get(review_id)["version"], 1)

    def test_admin_draft_supports_legacy_uzbek_original(self):
        receipt = new_receipt()
        status, _, result = self.triage(ticket("Meni chatda haqorat qildi"), receipt)
        self.assertEqual((status, result["draft_reply"]["lang"]), (200, "uz"))
        review_id = self.admin_list()["items"][0]["id"]
        status, _, body = self.request(
            f"/admin/api/reviews/{review_id}/draft", method="POST", key=TEST_KEY,
            value={"version": 1, "language": "kk"},
        )
        self.assertEqual((status, body["draft_reply"]["lang"]), (200, "kk"))
        self.assertEqual(body["draft_reply"]["cited"], result["draft_reply"]["cited"])

    def test_admin_draft_rejects_changes_that_occur_during_generation(self):
        self.triage(receipt=new_receipt())
        review_id = self.admin_list()["items"][0]["id"]
        path = f"/admin/api/reviews/{review_id}/draft"
        actual_triage = self.service.triage
        calls = 0
        def change_during_request(snapshot, *, reply_language=None):
            nonlocal calls
            calls += 1
            if calls == 2:
                self.queue.update(review_id, 1, "in_progress", "Другая сохранённая правка")
            return actual_triage(snapshot, reply_language=reply_language)
        with patch.object(self.service, "triage", side_effect=change_during_request):
            status, _, _ = self.request(path, method="POST", key=TEST_KEY, value={"version": 1, "language": "en"})
        self.assertEqual((status, calls), (409, 2))
        detail = self.queue.get(review_id)
        self.assertEqual((detail["version"], detail["admin_draft"]), (2, "Другая сохранённая правка"))

    def test_claimed_rule_candidates_are_private_bounded_and_not_citations(self):
        payload = ticket("Прошу проверить пункт 2.1.", rule_refs_raw="2.1")
        payload["messages"].append({"role": "admin", "text": "3.4 SECRET_HISTORICAL_RESPONSE"})
        status, _, result = self.triage(payload, new_receipt())
        self.assertEqual(status, 200)
        self.assertEqual(result["draft_reply"]["cited"], [])
        review_id = self.admin_list()["items"][0]["id"]
        path = f"/admin/api/reviews/{review_id}"
        self.assertEqual(self.request(path)[0], 401)
        detail = self.request(path, key=TEST_KEY)[2]
        candidates = detail["rule_candidates"]
        self.assertEqual(candidates["refs"], ["2.1"])
        self.assertEqual(len(candidates["items"]), 3)
        self.assertEqual({item["section_id"] for item in candidates["items"]}, {"general", "complaints", "green"})
        self.assertTrue(all(item["number"] == "2.1" for item in candidates["items"]))
        self.assertNotIn("SECRET_HISTORICAL_RESPONSE", json.dumps(detail))
        self.assertFalse(candidates["truncated"])
        _, _, updated = self.request(path, method="POST", key=TEST_KEY, value={"version": 1, "status": "in_progress", "draft": ""})
        self.assertEqual(updated["rule_candidates"], candidates)

    def test_candidate_list_is_bounded_and_unknown_numbers_are_not_fabricated(self):
        payload = ticket("Жалоба по указанным номерам", rule_refs_raw="1.1 2.1 3.1 4.1 5.1 6.1 7.1 8.1 9.1")
        self.triage(payload, new_receipt())
        review_id = self.admin_list()["items"][0]["id"]
        candidates = self.request(f"/admin/api/reviews/{review_id}", key=TEST_KEY)[2]["rule_candidates"]
        self.assertTrue(candidates["truncated"])
        self.assertEqual(len(candidates["refs"]), 8)
        self.assertLessEqual(len(candidates["items"]), 30)
        self.assertTrue(all(rule["number"] in candidates["refs"] for rule in candidates["items"]))
        self.assertFalse(any(rule["number"] == "5.1" for rule in candidates["items"]))

    def test_manual_flag_and_retry_are_idempotent(self):
        payload = ticket("Привет", kind="report")
        receipt = new_receipt()
        status, headers, result = self.triage(payload, receipt)
        self.assertEqual(status, 200)
        self.assertFalse(result["needs_human"])
        self.assertEqual(headers["X-Review-Status"], "not_required")
        body = {"ticket": payload, "source": "manual", "result": result, "draft": "Ручная правка"}
        self.assertEqual(self.request("/reviews/request", method="POST", value=body, receipt=receipt)[0], 201)
        self.assertEqual(self.request("/reviews/request", method="POST", value=body, receipt=receipt)[0], 200)
        self.assertEqual(self.admin_list()["counts"]["waiting"], 1)
        review_id = self.admin_list()["items"][0]["id"]
        detail = self.request(f"/admin/api/reviews/{review_id}", key=TEST_KEY)[2]
        self.assertEqual(detail["operator_draft"], "Ручная правка")
        self.assertEqual(detail["version"], 1)
        body["draft"] = "Обновлённая ручная правка"
        self.assertEqual(self.request("/reviews/request", method="POST", value=body, receipt=receipt)[0], 200)
        self.assertEqual(self.request(f"/admin/api/reviews/{review_id}", key=TEST_KEY)[2]["version"], 2)
        self.assertEqual(self.request(
            f"/admin/api/reviews/{review_id}", method="POST", key=TEST_KEY,
            value={"version": 2, "status": "resolved", "draft": "Готовый ответ"},
        )[0], 200)
        status, _, repeated = self.request("/reviews/request", method="POST", value=body, receipt=receipt)
        self.assertEqual((status, repeated["status"]), (200, "resolved"))
        body["draft"] = "Другая правка после проверки"
        self.assertEqual(self.request("/reviews/request", method="POST", value=body, receipt=receipt)[0], 409)
        body["ticket"] = ticket("Другое обращение")
        self.assertEqual(self.request("/reviews/request", method="POST", value=body, receipt=receipt)[0], 409)

    def test_operator_updates_do_not_overwrite_admin_edits(self):
        payload = ticket("Игрок оскорбил меня")
        receipt = new_receipt()
        status, _, result = self.triage(payload, receipt)
        self.assertEqual(status, 200)
        review_id = self.admin_list()["items"][0]["id"]
        self.assertEqual(self.request(
            f"/admin/api/reviews/{review_id}", method="POST", key=TEST_KEY,
            value={"version": 1, "status": "in_progress", "draft": "Правка администратора"},
        )[0], 200)
        manual = {"ticket": payload, "source": "manual", "result": result, "draft": "Обновление оператора"}
        self.assertEqual(self.request("/reviews/request", method="POST", value=manual, receipt=receipt)[0], 200)
        self.assertEqual(self.request(
            f"/admin/api/reviews/{review_id}", method="POST", key=TEST_KEY,
            value={"version": 2, "status": "resolved", "draft": "устаревший текст"},
        )[0], 409)
        detail = self.request(f"/admin/api/reviews/{review_id}", key=TEST_KEY)[2]
        self.assertEqual(detail["admin_draft"], "Правка администратора")
        self.assertEqual(detail["operator_draft"], "Обновление оператора")
        self.assertEqual(detail["version"], 3)

    def test_escalation_is_visible_in_queue_and_not_sent_as_a_reply(self):
        receipt = new_receipt()
        self.triage(receipt=receipt)
        review_id = self.admin_list()["items"][0]["id"]
        status, _, detail = self.request(
            f"/admin/api/reviews/{review_id}", method="POST", key=TEST_KEY,
            value={"version": 1, "status": "escalated", "draft": "Нужна дополнительная проверка"},
        )
        self.assertEqual((status, detail["status"]), (200, "escalated"))
        self.assertEqual(self.request("/reviews/status", receipt=receipt)[2], {"status": "escalated", "reply": None})
        active = self.admin_list()
        self.assertEqual((active["counts"]["escalated"], active["filtered_total"]), (1, 1))
        escalated = self.request("/admin/api/reviews?view=escalated", key=TEST_KEY)[2]
        self.assertEqual((escalated["filtered_total"], escalated["items"][0]["id"]), (1, review_id))
        _, _, final = self.request(
            f"/admin/api/reviews/{review_id}", method="POST", key=TEST_KEY,
            value={"version": 2, "status": "resolved", "draft": "Ответ после проверки"},
        )
        self.assertEqual(final["status"], "resolved")
        self.assertEqual(self.request("/reviews/status", receipt=receipt)[2]["reply"], "Ответ после проверки")
        self.assertEqual(self.request("/admin/api/reviews?view=escalated", key=TEST_KEY)[2]["filtered_total"], 0)

    def test_feedback_is_private_versioned_persistent_and_exportable(self):
        payload = ticket("Тестовое сообщение игрока", reporter_hash="private-hash", verdict="secret-verdict")
        payload["messages"][0]["attachments"] = [{"content": "secret-attachment"}]
        payload["messages"].append({"role": "admin", "text": "secret-admin-message"})
        receipt = new_receipt()
        _, _, result = self.triage(payload, receipt)
        review_id = self.admin_list()["items"][0]["id"]
        self.assertEqual(self.feedback()[0], [])
        def update(version, status, text):
            return self.request(
                f"/admin/api/reviews/{review_id}", method="POST", key=TEST_KEY,
                value={"version": version, "status": status, "draft": text},
            )
        self.assertEqual(update(1, "in_progress", "Черновая правка")[0], 200)
        self.assertEqual(self.admin_list()["feedback_count"], 1)
        rows, raw = self.feedback()
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["schema"], "support_copilot.admin_feedback.v1")
        self.assertEqual(row["assistant"]["draft"], result["draft_reply"]["text"])
        self.assertEqual(row["ticket"]["text"], "Тестовое сообщение игрока")
        self.assertEqual((row["admin_draft"], row["feedback_type"]), ("Черновая правка", "edited"))
        self.assertTrue(row["is_current"])
        self.assertFalse(row["approved"])
        for forbidden in ("private-hash", "secret-verdict", "secret-attachment", "secret-admin-message", receipt, TEST_KEY):
            self.assertNotIn(forbidden.encode(), raw)
        reopened = AdminQueue(self.root / "queue.sqlite3")
        persisted = io.BytesIO()
        self.assertEqual(reopened.write_feedback(persisted), 1)
        self.assertEqual(json.loads(persisted.getvalue()), row)
        self.assertEqual(update(2, "escalated", "Исправленный ответ")[0], 200)
        row = self.feedback()[0][0]
        self.assertEqual((row["status"], row["admin_draft"], row["approved"]), ("escalated", "Исправленный ответ", False))
        manual = {"ticket": payload, "source": "manual", "result": result, "draft": "Правка оператора"}
        self.assertEqual(self.request("/reviews/request", method="POST", value=manual, receipt=receipt)[0], 200)
        self.assertFalse(self.feedback()[0][0]["is_current"])
        self.assertEqual(update(3, "resolved", "Старая версия")[0], 409)
        self.assertEqual(update(4, "resolved", "Проверенный ответ")[0], 200)
        row = self.feedback()[0][0]
        self.assertTrue(row["approved"])
        self.assertTrue(row["is_current"])
        self.assertEqual((row["operator_draft"], row["admin_draft"]), ("Правка оператора", "Проверенный ответ"))
        self.assertEqual(len(self.feedback()[0]), 1)
        self.assertEqual(update(5, "in_progress", "Проверенный ответ")[0], 200)
        self.assertFalse(self.feedback()[0][0]["approved"])
        self.assertEqual(self.request(
            f"/admin/api/reviews/{review_id}", method="DELETE", key=TEST_KEY, value={"version": 6},
        )[0], 200)
        self.assertEqual(self.feedback()[0], [])

    def test_export_keeps_multiline_content_as_separate_jsonl_records(self):
        for index in range(2):
            self.triage(payload=ticket(f"Игрок пишет строку {index}\nВторая строка"))
        items = self.admin_list()["items"]
        for index, item in enumerate(items):
            self.assertEqual(self.request(
                f"/admin/api/reviews/{item['id']}", method="POST", key=TEST_KEY,
                value={"version": 1, "status": "resolved", "draft": f"Ответ {index}\nВторая строка"},
            )[0], 200)
        rows, raw = self.feedback()
        self.assertEqual(len(rows), 2)
        self.assertEqual(len(raw.splitlines()), 2)
        self.assertTrue(all("\n" in row["ticket"]["text"] and "\n" in row["admin_draft"] for row in rows))

    def test_unchanged_approval_is_distinct_from_unedited_work(self):
        _, _, result = self.triage()
        review_id = self.admin_list()["items"][0]["id"]
        text = result["draft_reply"]["text"]
        self.assertEqual(self.request(
            f"/admin/api/reviews/{review_id}", method="POST", key=TEST_KEY,
            value={"version": 1, "status": "in_progress", "draft": text},
        )[0], 200)
        self.assertEqual(self.feedback()[0], [])
        self.assertEqual(self.request(
            f"/admin/api/reviews/{review_id}", method="POST", key=TEST_KEY,
            value={"version": 2, "status": "resolved", "draft": text},
        )[0], 200)
        row = self.feedback()[0][0]
        self.assertEqual(row["feedback_type"], "unchanged")
        self.assertTrue(row["approved"])

    def test_export_failure_does_not_return_a_partial_download(self):
        with patch.object(self.queue, "write_feedback", side_effect=OSError("private path details")):
            status, headers, body = self.request("/admin/api/feedback/export", key=TEST_KEY)
        self.assertEqual(status, 503)
        self.assertNotIn("Content-Disposition", headers)
        self.assertNotIn("private path details", json.dumps(body))

    def test_feedback_without_assistant_output_is_marked_as_human(self):
        self.server.service = None
        self.triage()
        review_id = self.admin_list()["items"][0]["id"]
        self.assertEqual(self.request(
            f"/admin/api/reviews/{review_id}", method="POST", key=TEST_KEY,
            value={"version": 1, "status": "resolved", "draft": "Ответ без авторазбора"},
        )[0], 200)
        row = self.feedback()[0][0]
        self.assertIsNone(row["assistant"])
        self.assertEqual(row["feedback_type"], "human_reply")
        self.assertTrue(row["approved"])

    def test_classifier_exception_and_malformed_response_fail_closed(self):
        for broken in (RuntimeError("sensitive exception details"), InputError("sensitive exception details"), {"category": "made-up"}):
            with self.subTest(broken=type(broken).__name__):
                receipt = new_receipt()
                kwargs = {"side_effect": broken} if isinstance(broken, Exception) else {"return_value": broken}
                with patch.object(self.service, "triage", **kwargs):
                    status, headers, body = self.triage(receipt=receipt)
                self.assertEqual(status, 500)
                self.assertEqual(headers["X-Review-Status"], "queued")
                self.assertNotIn("sensitive exception details", json.dumps(body))
                review_id = next(item["id"] for item in self.admin_list()["items"] if item["source"] == "failure")
                detail = self.request(f"/admin/api/reviews/{review_id}", key=TEST_KEY)[2]
                self.assertIsNone(detail["result"])
                self.assertEqual(self.request("/reviews/status", receipt=receipt)[2]["status"], "waiting")

    def test_fabricated_citation_is_queued_as_an_invalid_result(self):
        payload = ticket("Игрок оскорбил меня")
        unsafe = self.service.triage(payload)
        unsafe["draft_reply"]["cited"] = ["99.99"]
        unsafe["draft_reply"]["text"] += " Пункт 99.99."
        with patch.object(self.service, "triage", return_value=unsafe):
            status, headers, body = self.triage(payload, new_receipt())
        self.assertEqual(status, 500)
        self.assertEqual(headers["X-Review-Status"], "queued")
        self.assertNotIn("99.99", json.dumps(body))
        detail_id = self.admin_list()["items"][0]["id"]
        self.assertIsNone(self.request(f"/admin/api/reviews/{detail_id}", key=TEST_KEY)[2]["result"])

    def test_independent_safety_guard_routes_critical_result_to_human(self):
        payload = ticket("Привет", kind="report")
        unsafe = self.service.triage(payload)
        self.assertFalse(unsafe["needs_human"])
        unsafe["priority"] = "p0"
        with patch.object(self.service, "triage", return_value=unsafe):
            status, headers, result = self.triage(payload, new_receipt())
        self.assertEqual(status, 200)
        self.assertTrue(result["needs_human"])
        self.assertEqual(headers["X-Review-Status"], "queued")
        self.assertEqual(self.admin_list()["counts"]["waiting"], 1)

    def test_missing_classifier_keeps_admin_queue_usable(self):
        self.server.service = None
        self.assertEqual(self.request("/health")[2]["status"], "degraded")
        receipt = new_receipt()
        status, headers, body = self.triage(receipt=receipt)
        self.assertEqual(status, 503)
        self.assertEqual(headers["X-Review-Status"], "queued")
        self.assertIn("недоступен", body["error"])
        self.assertEqual(self.admin_list()["counts"]["waiting"], 1)
        self.assertEqual(self.request("/reviews/status", receipt=receipt)[2]["status"], "waiting")
        self.assertEqual(self.triage(payload={"kind": "invalid"})[0], 400)

    def test_queue_unavailable_never_claims_delivery(self):
        self.server.queue = None
        status, headers, result = self.triage()
        self.assertEqual(status, 200)
        self.assertTrue(result["needs_human"])
        self.assertEqual(headers["X-Review-Status"], "unavailable")
        self.assertNotIn("X-Review-Receipt", headers)
        self.assertEqual(self.request("/admin/api/session", key=TEST_KEY)[0], 503)

    def test_invalid_review_parameters_are_controlled_errors(self):
        invalid = {"ticket": ticket("Тестовое обращение"), "source": []}
        status, _, _ = self.request("/reviews/request", method="POST", value=invalid, receipt=new_receipt())
        self.assertEqual(status, 400)
        status, _, _ = self.request("/admin/api/reviews?offset=999999999999999999999999", key=TEST_KEY)
        self.assertEqual(status, 400)

    def test_unexpected_storage_error_is_reported_as_unavailable(self):
        with patch.object(self.queue, "enqueue", side_effect=RuntimeError("private storage details")):
            status, headers, body = self.triage()
        self.assertEqual(status, 200)
        self.assertTrue(body["needs_human"])
        self.assertEqual(headers["X-Review-Status"], "unavailable")
        self.assertNotIn("private storage details", json.dumps(body))

    def test_review_survives_queue_reopen_and_old_data_is_purged(self):
        receipt = new_receipt()
        self.triage(receipt=receipt)
        review_id = self.admin_list()["items"][0]["id"]
        self.assertEqual(self.request(
            f"/admin/api/reviews/{review_id}", method="POST", key=TEST_KEY,
            value={"version": 1, "status": "in_progress", "draft": "Сохранённая правка"},
        )[0], 200)
        self.assertEqual(len(self.feedback()[0]), 1)
        reopened = AdminQueue(self.root / "queue.sqlite3")
        self.assertEqual(reopened.get(review_id)["status"], "in_progress")
        with sqlite3.connect(self.root / "queue.sqlite3") as conn:
            conn.execute("UPDATE reviews SET created_at = ?", (int(time.time()) - 15 * 86400,))
        self.assertEqual(reopened.list_reviews()["counts"]["in_progress"], 0)
        self.assertEqual(reopened.write_feedback(io.BytesIO()), 0)
        with sqlite3.connect(self.root / "queue.sqlite3") as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM admin_feedback").fetchone()[0], 0)
        with self.assertRaises(QueueNotFound):
            reopened.status(receipt)

    def test_concurrent_admin_changes_never_overwrite_each_other(self):
        receipt = new_receipt()
        self.triage(receipt=receipt)
        review_id = self.admin_list()["items"][0]["id"]
        barrier = threading.Barrier(2)
        outcomes = []

        def update(text):
            barrier.wait()
            try:
                self.queue.update(review_id, 1, "resolved", text)
                outcomes.append("saved")
            except QueueConflict:
                outcomes.append("conflict")

        threads = [threading.Thread(target=update, args=(text,)) for text in ("Ответ 1", "Ответ 2")]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=5)
        self.assertCountEqual(outcomes, ["saved", "conflict"])


class AdminStorageTests(unittest.TestCase):
    def test_unexpected_classifier_startup_failure_keeps_admin_running(self):
        class FakeServer:
            server_port = 8000

            def serve_forever(self):
                pass

            def server_close(self):
                pass

        output, errors = io.StringIO(), io.StringIO()
        with patch("sys.argv", ["server"]), patch("sys.stdout", output), patch("sys.stderr", errors), \
             patch.object(server_module, "load_admin_key", return_value=TEST_KEY), \
             patch.object(server_module, "AdminQueue", return_value=object()), \
             patch.object(server_module, "make_service", side_effect=RuntimeError("private exception")), \
             patch.object(server_module, "CopilotServer", return_value=FakeServer()) as factory:
            self.assertEqual(server_module.main(), 0)
        self.assertIsNone(factory.call_args.args[1])
        self.assertIn("RuntimeError", errors.getvalue())
        self.assertNotIn("private exception", errors.getvalue())

    def test_key_is_generated_once_and_is_not_world_readable_on_posix(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "private" / "admin.key"
            key = load_admin_key(path)
            self.assertEqual(key, load_admin_key(path))
            self.assertGreaterEqual(len(key), 24)
            if os.name == "posix":
                self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            with self.assertRaises(ValueError):
                load_admin_key(path, "weak")
            self.assertEqual(load_admin_key(path, TEST_KEY), TEST_KEY)
            if hasattr(os, "symlink"):
                link = path.parent / "other.key"
                try:
                    link.symlink_to(path)
                except OSError:
                    return
                with self.assertRaises(ValueError):
                    load_admin_key(link)

    def test_filters_and_pagination_can_reach_every_case(self):
        with tempfile.TemporaryDirectory() as directory:
            queue = AdminQueue(Path(directory) / "queue.sqlite3")
            ids = [queue.enqueue(ticket(f"Обращение {i}"), new_receipt(), "failure")["id"] for i in range(53)]
            for review_id in ids[:2]:
                queue.update(review_id, 1, "resolved", "Ответ администратора")
            for review_id in ids[2:4]:
                queue.update(review_id, 1, "escalated", "")
            first = queue.list_reviews(view="active")
            second = queue.list_reviews(view="active", offset=50)
            self.assertEqual(first["filtered_total"], 51)
            self.assertEqual((len(first["items"]), len(second["items"])), (50, 1))
            self.assertEqual(len({row["id"] for row in first["items"] + second["items"]}), 51)
            self.assertEqual([row["status"] for row in first["items"][:2]], ["escalated", "escalated"])
            self.assertEqual(queue.list_reviews(view="escalated")["filtered_total"], 2)
            self.assertEqual(queue.list_reviews(view="resolved")["filtered_total"], 2)
            self.assertEqual(queue.list_reviews(view="all")["filtered_total"], 53)

    def test_feedback_write_failure_rolls_back_review_update(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "queue.sqlite3"
            queue = AdminQueue(path)
            review_id = queue.enqueue(ticket("Тестовое сообщение"), new_receipt(), "failure")["id"]
            with sqlite3.connect(path) as conn:
                conn.execute("CREATE TRIGGER fail_feedback BEFORE INSERT ON admin_feedback BEGIN SELECT RAISE(FAIL, 'test failure'); END")
            with self.assertRaises(sqlite3.DatabaseError):
                queue.update(review_id, 1, "resolved", "Подготовленный ответ")
            detail = queue.get(review_id)
            self.assertEqual((detail["version"], detail["status"], detail["admin_draft"]), (1, "waiting", None))
            self.assertEqual(queue.write_feedback(io.BytesIO()), 0)

    def test_existing_database_gains_feedback_table_without_losing_reviews(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "queue.sqlite3"
            legacy = AdminQueue(path)
            review_id = legacy.enqueue(ticket("Существующее обращение"), new_receipt(), "failure")["id"]
            with sqlite3.connect(path) as conn:
                conn.execute("DROP TABLE admin_feedback")
            migrated = AdminQueue(path)
            self.assertEqual(migrated.get(review_id)["message"], "Существующее обращение")
            migrated.update(review_id, 1, "resolved", "Ответ администратора")
            self.assertEqual(migrated.write_feedback(io.BytesIO()), 1)

    def test_queue_capacity_does_not_silently_discard_open_cases(self):
        with tempfile.TemporaryDirectory() as directory:
            queue = AdminQueue(Path(directory) / "queue.sqlite3", max_items=1)
            receipt = new_receipt()
            queue.enqueue(ticket("Первое"), receipt, "failure")
            queue.enqueue(ticket("Первое"), receipt, "failure")
            with self.assertRaises(QueueFull):
                queue.enqueue(ticket("Второе"), new_receipt(), "failure")
            self.assertEqual(queue.list_reviews()["counts"]["waiting"], 1)


if __name__ == "__main__":
    unittest.main()
