"""Ephemeral duplicate detection; never persist player messages."""

from __future__ import annotations

import hashlib
import re
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime, timezone

from .text import normalize, stems, words


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _time(value: object) -> float:
    if isinstance(value, str) and value.strip():
        try:
            parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.timestamp()
        except (ValueError, OverflowError, OSError):
            pass
    return time.time()


def obvious_spam(text: str) -> bool:
    clean = normalize(text)
    if re.search(r"(.)\1{11,}", re.sub(r"\s+", "", clean)):
        return True
    tokens = words(clean)
    if len(tokens) >= 8 and len(set(tokens)) == 1:
        return True
    return len(re.findall(r"https?://", clean)) >= 4


@dataclass(frozen=True)
class _Event:
    timestamp: float
    ticket_id: str | None
    target: str | None
    kind: str
    category: str
    fingerprint: str
    tokens: frozenset[str]


class DuplicateDetector:
    """Flag the fifth similar ticket by the same reporter within one hour.

    State is bounded and in-process. There is intentionally no cross-reporter
    matching: the API often lacks a reporter identifier, and guessing would
    merge different players' complaints.
    """

    def __init__(self, max_reporters: int = 5000, max_events_per_reporter: int = 100):
        self._events: OrderedDict[str, list[_Event]] = OrderedDict()
        self._lock = threading.Lock()
        self.max_reporters = max_reporters
        self.max_events_per_reporter = max_events_per_reporter

    def check(self, *, reporter: object, target: object, ticket_id: object, kind: str, category: str, text: str, created_at: object, lang: str) -> bool:
        if not isinstance(reporter, str) or not reporter.strip() or not text.strip():
            return False
        # Do not retain the supplied identifiers or text verbatim in memory.
        reporter_key = _digest(reporter.strip())
        target_key = _digest(str(target)) if target else None
        ticket_key = _digest(str(ticket_id)) if ticket_id else None
        timestamp = _time(created_at)
        canonical = " ".join(words(text, lang))
        fingerprint = _digest(canonical)
        tokens = frozenset(_digest(token) for token in stems(text, lang))
        with self._lock:
            events = self._events.pop(reporter_key, [])
            # Keep future-dated events for possible out-of-order arrivals, but
            # only count earlier events when evaluating the current ticket.
            events = [event for event in events if timestamp - event.timestamp <= 3600]
            already_seen = any(ticket_key and event.ticket_id == ticket_key for event in events)
            similar = 0
            for event in events:
                if not 0 <= timestamp - event.timestamp <= 3600:
                    continue
                if event.kind != kind or event.category != category:
                    continue
                # If only one report identifies a target, do not assume the
                # unknown target is the same person.
                if target_key != event.target and (target_key or event.target):
                    continue
                if ticket_key and event.ticket_id == ticket_key:
                    continue
                union = tokens | event.tokens
                same = fingerprint == event.fingerprint or (len(union) >= 3 and len(tokens & event.tokens) / len(union) >= 0.8)
                if same:
                    similar += 1
            if not already_seen:
                events.append(_Event(timestamp, ticket_key, target_key, kind, category, fingerprint, tokens))
            self._events[reporter_key] = events[-self.max_events_per_reporter:]
            while len(self._events) > self.max_reporters:
                self._events.popitem(last=False)
            return similar >= 4
