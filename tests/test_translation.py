"""Offline Google request, privacy, authorization and translation UI contracts."""

import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.client import IncompleteRead
from pathlib import Path
from unittest.mock import patch

from helpers import ticket, write_fixtures
from support_copilot.admin_queue import AdminQueue, new_receipt
from support_copilot.catalog import Catalog
from support_copilot.server import CopilotServer
from support_copilot.service import TriageService
from support_copilot.translation import (
    GOOGLE_TIMEOUT_SECONDS,
    GOOGLE_TRANSLATE_URL,
    MAX_RESPONSE_BYTES,
    MAX_TRANSLATION_CHARACTERS,
    GoogleTranslator,
    TranslationBusy,
    TranslationLimiter,
    TranslationRateLimited,
    TranslationUnavailable,
    _NoRedirect,
)

# Synthetic values only; no external request is made in these tests.
TEST_ADMIN = "synthetic-admin-token-only-for-tests-0123"
TEST_GOOGLE_KEY = "synthetic-google-key-only-for-tests"
PLAYER = "Синтетическое сообщение игрока для перевода."
TRANSLATED = "Synthetic translated message."


class FakeResponse:
    def __init__(self, body):
        self.body = body
        self.requested = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, maximum):
        self.requested = maximum
        return self.body[:maximum]


class FakeOpener:
    def __init__(self, body=None, error=None):
        self.body = body
        self.error = error
        self.calls = []

    def open(self, request, timeout):
        self.calls.append((request, timeout))
        if self.error:
            raise self.error
        return FakeResponse(self.body)


class GoogleTranslationTests(unittest.TestCase):
    def test_disabled_or_header_unsafe_keys_do_not_make_requests(self):
        for key in (None, "", "not\na-key", "key with spaces", "ключ", "x" * 513):
            with self.subTest(key=bool(key)):
                opener = FakeOpener()
                provider = GoogleTranslator(key, opener=opener)
                self.assertFalse(provider.configured)
                with self.assertRaises(TranslationUnavailable):
                    provider.translate(PLAYER, "en")
                self.assertEqual(opener.calls, [])

    def test_uses_fixed_google_https_endpoint_and_header_not_url(self):
        payload = {"data": {"translations": [{"translatedText": "It&#39;s &lt;safe&gt;."}]}}
        opener = FakeOpener(json.dumps(payload).encode())
        provider = GoogleTranslator(TEST_GOOGLE_KEY, opener=opener)
        self.assertEqual(provider.translate(PLAYER, "en"), "It's <safe>.")
        request, timeout = opener.calls[0]
        self.assertEqual(request.full_url, GOOGLE_TRANSLATE_URL)
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(timeout, GOOGLE_TIMEOUT_SECONDS)
        self.assertEqual(request.get_header("X-goog-api-key"), TEST_GOOGLE_KEY)
        self.assertNotIn(TEST_GOOGLE_KEY, request.full_url)
        body = json.loads(request.data.decode("utf-8"))
        self.assertEqual(body, {"q": PLAYER, "target": "en", "format": "text"})
        self.assertNotIn(TEST_GOOGLE_KEY, request.data.decode())
        self.assertIsNone(_NoRedirect().redirect_request(request, None, 302, "Found", {}, "https://evil.invalid"))

    def test_malformed_responses_and_provider_errors_are_not_exposed(self):
        failures = [
            FakeOpener(error=urllib.error.URLError("synthetic secret and player text")),
            FakeOpener(error=TimeoutError("synthetic secret and player text")),
            FakeOpener(b"not json"),
            FakeOpener(b"x" * (MAX_RESPONSE_BYTES + 1)),
            FakeOpener(b'{"data":{"translations":[]}}'),
            FakeOpener(b'{"data":{"translations":[{"translatedText":""}]}}'),
            FakeOpener(b'{"data":{"translations":[{"translatedText":"\\ud800"}]}}'),
        ]
        for opener in failures:
            with self.subTest(opener=type(opener.error).__name__ if opener.error else len(opener.body)):
                provider = GoogleTranslator(TEST_GOOGLE_KEY, opener=opener)
                with self.assertRaises(TranslationUnavailable) as caught:
                    provider.translate(PLAYER, "en")
                self.assertEqual(str(caught.exception), "")

    def test_truncated_provider_response_fails_closed(self):
        opener = FakeOpener(b"")
        provider = GoogleTranslator(TEST_GOOGLE_KEY, opener=opener)
        with patch.object(FakeResponse, "read", side_effect=IncompleteRead(b"synthetic private text", 20)):
            with self.assertRaises(TranslationUnavailable) as caught:
                provider.translate(PLAYER, "en")
        self.assertEqual(str(caught.exception), "")
        self.assertEqual(len(opener.calls), 1)

    def test_source_and_target_are_bounded_before_network_access(self):
        opener = FakeOpener()
        provider = GoogleTranslator(TEST_GOOGLE_KEY, opener=opener)
        for text, target in (("", "en"), (" " * 2, "en"), ("x" * (MAX_TRANSLATION_CHARACTERS + 1), "en"), (PLAYER, "evil"), (PLAYER, [])):
            with self.subTest(target=target, length=len(text)), self.assertRaises(ValueError):
                provider.translate(text, target)
        self.assertFalse(opener.calls)

    def test_rate_and_concurrency_limits_release_even_after_failure(self):
        now = [100.0]
        limiter = TranslationLimiter(max_per_minute=2, max_concurrent=1, clock=lambda: now[0])
        with limiter.acquire():
            with self.assertRaises(TranslationBusy):
                with limiter.acquire():
                    pass
        with self.assertRaises(RuntimeError):
            with limiter.acquire():
                raise RuntimeError("synthetic failure")
        with self.assertRaises(TranslationRateLimited):
            with limiter.acquire():
                pass
        now[0] += 61
        with limiter.acquire():
            pass


class StubTranslator:
    def __init__(self):
        self.configured = True
        self.calls = []
        self.result = TRANSLATED
        self.error = None

    def translate(self, text, target):
        self.calls.append((text, target))
        if self.error:
            raise self.error
        return self.result


class TranslationApiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        rules, taxonomy, _ = write_fixtures(self.tmp.name)
        self.queue = AdminQueue(self.root / "queue.sqlite3")
        self.stub = StubTranslator()
        service = TriageService(Catalog(rules, taxonomy))
        self.server = CopilotServer(("127.0.0.1", 0), service, self.queue, TEST_ADMIN, self.stub)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"
        self.review_id = self.queue.enqueue(ticket(PLAYER), new_receipt(), "manual")["id"]
        self.path = f"/admin/api/reviews/{self.review_id}/translate"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.tmp.cleanup()

    def request(self, path, *, method="GET", value=None, key=None):
        headers = {}
        data = None
        if value is not None:
            data = json.dumps(value).encode("utf-8")
            headers["Content-Type"] = "application/json"
        if key is not None:
            headers["Authorization"] = f"Bearer {key}"
        request = urllib.request.Request(self.base + path, data=data, headers=headers, method=method)
        try:
            response = urllib.request.urlopen(request, timeout=5)
        except urllib.error.HTTPError as exc:
            response = exc
        with response:
            return response.status, response.headers, json.load(response)

    def translate(self, body=None, key=TEST_ADMIN):
        if body is None:
            body = {"target": "en", "version": 1, "consent": True}
        return self.request(self.path, method="POST", value=body, key=key)

    def test_google_attribution_badge_is_served_locally(self):
        with urllib.request.urlopen(self.base + "/translated-by-google.png", timeout=5) as response:
            self.assertEqual(response.status, 200)
            self.assertEqual(response.headers.get_content_type(), "image/png")
            self.assertTrue(response.read().startswith(b"\x89PNG\r\n\x1a\n"))

    def test_status_and_translation_require_admin_auth(self):
        self.assertEqual(self.request("/admin/api/translation")[0], 401)
        self.assertEqual(self.translate(key=None)[0], 401)
        status, _, body = self.request("/admin/api/translation", key=TEST_ADMIN)
        self.assertEqual((status, body), (200, {"configured": True, "max_characters": 5000}))
        self.assertEqual(self.stub.calls, [])

    def test_only_stored_player_message_is_translated_and_nothing_saved(self):
        before = self.queue.get(self.review_id)
        status, headers, body = self.translate()
        self.assertEqual(status, 200)
        self.assertEqual(headers["Cache-Control"], "no-store")
        self.assertEqual(body, {"translation": TRANSLATED, "target": "en"})
        self.assertEqual(self.stub.calls, [(PLAYER, "en")])
        self.assertEqual(self.queue.get(self.review_id), before)
        self.assertNotIn(TRANSLATED.encode(), (self.root / "queue.sqlite3").read_bytes())
        self.assertEqual(self.translate({"target": "en", "version": 1, "consent": True, "text": "injected"})[0], 400)
        self.assertEqual(self.stub.calls, [(PLAYER, "en")])

    def test_consent_language_version_and_size_are_checked_before_network(self):
        bad = [
            ({"target": "en", "version": 1, "consent": False}, 400),
            ({"target": "en", "version": 1, "consent": "true"}, 400),
            ({"target": "en", "version": 1}, 400),
            ({"target": "zz", "version": 1, "consent": True}, 400),
            ({"target": [], "version": 1, "consent": True}, 400),
            ({"target": "en", "version": True, "consent": True}, 400),
            ({"target": "en", "version": 2, "consent": True}, 409),
        ]
        for body, expected in bad:
            with self.subTest(body=body):
                self.assertEqual(self.translate(body)[0], expected)
        self.assertEqual(self.request(
            f"/admin/api/reviews/{'a' * 32}/translate", method="POST",
            value={"target": "en", "version": 1, "consent": True}, key=TEST_ADMIN,
        )[0], 404)
        long_id = self.queue.enqueue(ticket("x" * 5001), new_receipt(), "manual")["id"]
        status, _, _ = self.request(
            f"/admin/api/reviews/{long_id}/translate", method="POST",
            value={"target": "en", "version": 1, "consent": True}, key=TEST_ADMIN,
        )
        self.assertEqual(status, 413)
        self.assertEqual(self.stub.calls, [])

    def test_disabled_failure_and_rate_limit_are_clear_without_leaking_details(self):
        self.stub.configured = False
        self.assertFalse(self.request("/admin/api/translation", key=TEST_ADMIN)[2]["configured"])
        self.assertEqual(self.translate()[0], 503)
        self.assertEqual(self.stub.calls, [])
        self.stub.configured = True
        self.stub.error = TranslationUnavailable("SECRET PROVIDER ERROR")
        status, _, body = self.translate()
        self.assertEqual(status, 502)
        self.assertNotIn("SECRET", json.dumps(body))
        self.stub.error = None
        self.server.translation_limiter = TranslationLimiter(max_per_minute=1)
        self.assertEqual(self.translate()[0], 200)
        self.assertEqual(self.translate()[0], 429)

    def test_concurrent_translation_is_bounded(self):
        started = threading.Event()
        release = threading.Event()
        original = self.stub.translate

        def slow(text, target):
            started.set()
            if not release.wait(3):
                raise TranslationUnavailable()
            return original(text, target)

        self.stub.translate = slow
        self.server.translation_limiter = TranslationLimiter(max_concurrent=1)
        results = []
        worker = threading.Thread(target=lambda: results.append(self.translate()[0]))
        worker.start()
        try:
            self.assertTrue(started.wait(2))
            self.assertEqual(self.translate()[0], 503)
        finally:
            release.set()
            worker.join(4)
        self.assertEqual(results, [200])


if __name__ == "__main__":
    unittest.main()
