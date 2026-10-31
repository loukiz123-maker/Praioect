"""Opt-in Google Cloud Translation for an administrator's explicit request.

Only the supplied player message is sent to the fixed Google endpoint. The
credential remains on the server, and neither messages nor translations are
persisted or logged by this module. Network failures fail closed.
"""

from __future__ import annotations

import html
import json
import threading
import time
from contextlib import contextmanager
from http.client import HTTPException
from typing import Iterator
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

GOOGLE_TRANSLATE_URL = "https://translation.googleapis.com/language/translate/v2"
TARGET_LANGUAGES = frozenset({"ru", "en", "kk"})
MAX_TRANSLATION_CHARACTERS = 5000
MAX_RESPONSE_BYTES = 200_000
MAX_TRANSLATED_CHARACTERS = 30_000
GOOGLE_TIMEOUT_SECONDS = 8


class TranslationUnavailable(Exception):
    """The provider could not return a usable translation; no raw error is exposed."""


class TranslationBusy(Exception):
    pass


class TranslationRateLimited(Exception):
    pass


class _NoRedirect(HTTPRedirectHandler):
    # Never forward an API key or private text to a different destination.
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class GoogleTranslator:
    """Google Cloud Translation Basic, using a server-side API key only."""

    def __init__(self, api_key: str | None, *, opener=None):
        self._api_key = api_key or ""
        self._opener = opener if opener is not None else build_opener(_NoRedirect())

    @property
    def configured(self) -> bool:
        # Do not allow newlines/control characters in a credential header.
        key = self._api_key
        return bool(key and len(key) <= 512 and key.isascii() and all("!" <= char <= "~" for char in key))

    def translate(self, text: str, target: str) -> str:
        if not self.configured:
            raise TranslationUnavailable()
        if not isinstance(text, str) or not text.strip() or len(text) > MAX_TRANSLATION_CHARACTERS:
            raise ValueError("invalid source text")
        if not isinstance(target, str) or target not in TARGET_LANGUAGES:
            raise ValueError("invalid target language")
        try:
            body = json.dumps({"q": text, "target": target, "format": "text"}, ensure_ascii=False).encode("utf-8")
            request = Request(GOOGLE_TRANSLATE_URL, data=body, method="POST", headers={
                "Content-Type": "application/json; charset=utf-8",
                "Accept": "application/json",
                "X-Goog-Api-Key": self._api_key,
            })
            with self._opener.open(request, timeout=GOOGLE_TIMEOUT_SECONDS) as response:
                raw = response.read(MAX_RESPONSE_BYTES + 1)
            if len(raw) > MAX_RESPONSE_BYTES:
                raise ValueError("provider response too large")
            payload = json.loads(raw.decode("utf-8"))
            translations = payload["data"]["translations"]
            if not isinstance(translations, list) or len(translations) != 1:
                raise ValueError("invalid provider response")
            translated = translations[0]["translatedText"]
            if not isinstance(translated, str):
                raise ValueError("invalid provider response")
            # Google may HTML-escape entities even for plain-text requests. The
            # UI inserts this string via textContent, never as HTML.
            translated = html.unescape(translated)
            if not translated.strip() or len(translated) > MAX_TRANSLATED_CHARACTERS:
                raise ValueError("invalid provider response")
            translated.encode("utf-8")
            return translated
        except (HTTPError, URLError, HTTPException, OSError, TimeoutError, UnicodeError, ValueError, KeyError, IndexError, TypeError):
            # Never forward provider errors, which may contain credentials or text.
            raise TranslationUnavailable() from None


class TranslationLimiter:
    """Bound requests per process without retaining user data or identifiers."""

    def __init__(self, *, max_per_minute: int = 20, max_concurrent: int = 2, clock=time.monotonic):
        self._max_per_minute = max_per_minute
        self._max_concurrent = max_concurrent
        self._clock = clock
        self._lock = threading.Lock()
        self._timestamps: list[float] = []
        self._active = 0

    @contextmanager
    def acquire(self) -> Iterator[None]:
        with self._lock:
            now = self._clock()
            self._timestamps = [stamp for stamp in self._timestamps if now - stamp < 60]
            if len(self._timestamps) >= self._max_per_minute:
                raise TranslationRateLimited()
            if self._active >= self._max_concurrent:
                raise TranslationBusy()
            self._timestamps.append(now)
            self._active += 1
        try:
            yield
        finally:
            with self._lock:
                self._active -= 1
