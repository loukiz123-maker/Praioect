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

    def test_auth_and_private_files_are_not_public(self):
        for path in ("/admin/api/reviews", "/admin/api/session"):
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
        reopened = AdminQueue(self.root / "queue.sqlite3")
        self.assertEqual(reopened.get(review_id)["status"], "waiting")
        with sqlite3.connect(self.root / "queue.sqlite3") as conn:
            conn.execute("UPDATE reviews SET created_at = ?", (int(time.time()) - 15 * 86400,))
        self.assertEqual(reopened.list_reviews()["counts"]["waiting"], 0)
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
            first = queue.list_reviews(view="active")
            second = queue.list_reviews(view="active", offset=50)
            self.assertEqual(first["filtered_total"], 51)
            self.assertEqual((len(first["items"]), len(second["items"])), (50, 1))
            self.assertEqual(len({row["id"] for row in first["items"] + second["items"]}), 51)
            self.assertEqual(queue.list_reviews(view="resolved")["filtered_total"], 2)
            self.assertEqual(queue.list_reviews(view="all")["filtered_total"], 53)

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
