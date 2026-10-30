"""Private review identifiers, source snapshots and reproducibility hashes."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from .service import InputError, _positive_attachment, validate_ticket


def _fingerprint(value: Any) -> str:
    canonical = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def draft_fingerprint(draft: dict[str, Any]) -> str:
    return _fingerprint(draft)


def source_fingerprint(source: dict[str, Any]) -> str:
    return _fingerprint(source)


def ticket_key(ticket: dict[str, Any]) -> str:
    value = ticket.get("ticket_id")
    if isinstance(value, bool) or not isinstance(value, (str, int)) or not str(value).strip() or len(str(value)) > 512:
        raise InputError("Для ручной оценки каждой строке нужен уникальный ticket_id")
    return str(value)


def source_snapshot(ticket: dict[str, Any]) -> dict[str, Any]:
    """Review only player-side input, without gold labels or admin messages."""
    kind, messages = validate_ticket(ticket)
    source: dict[str, Any] = {
        "kind": kind,
        "player_messages": [message.get("text", "") for message in messages],
        "attachments_indicated": _positive_attachment(ticket.get("images_count"))
        or any(_positive_attachment(message.get("attachments")) for message in messages),
    }
    for name in ("reported_nick", "rule_refs_raw", "images_count", "server", "region", "created_at", "lang"):
        value = ticket.get(name)
        if isinstance(value, (str, int, float)) and not isinstance(value, bool):
            source[name] = value
    return source
