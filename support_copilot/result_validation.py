"""Shared structural and human-review safeguards for classifier results."""

from __future__ import annotations

import json
import math
from typing import Any

from .service import NAMED_RULE_REASON, TEMPLATES, InputError, TriageService
from .text import SUPPORTED_LANGUAGES

RESULT_KEYS = {
    "lang", "category", "priority", "is_spam_or_duplicate", "extracted",
    "draft_reply", "needs_human", "confidence", "reasons",
}


def _string_list(value: Any, max_items: int, max_length: int) -> bool:
    return isinstance(value, list) and len(value) <= max_items and all(isinstance(x, str) and len(x) <= max_length for x in value)


def valid_result(value: Any, service: TriageService | None) -> bool:
    """Fail closed on a broken or incomplete classifier response.

    Valid shape cannot prove semantic correctness: administrators still need
    to review high-risk, uncertain, and manually reported results.
    """
    if not isinstance(value, dict) or set(value) != RESULT_KEYS:
        return False
    if not isinstance(value["lang"], str) or value["lang"] not in SUPPORTED_LANGUAGES | {"und"}:
        return False
    category = value["category"]
    if not isinstance(category, str) or not category or len(category) > 128:
        return False
    if service is not None and category not in service.catalog.categories:
        return False
    if value["priority"] not in ("p0", "p1", "p2", "p3"):
        return False
    if not isinstance(value["is_spam_or_duplicate"], bool) or not isinstance(value["needs_human"], bool):
        return False
    confidence = value["confidence"]
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1 or not math.isfinite(confidence):
        return False
    extracted = value["extracted"]
    if not isinstance(extracted, dict) or set(extracted) != {"nickname", "rule_refs", "server", "has_evidence"}:
        return False
    if not isinstance(extracted["has_evidence"], bool):
        return False
    if any(v is not None and (not isinstance(v, str) or len(v) > 1024) for v in (extracted["nickname"], extracted["server"])):
        return False
    if not _string_list(extracted["rule_refs"], 100, 100):
        return False
    draft = value["draft_reply"]
    if not isinstance(draft, dict) or set(draft) != {"lang", "text", "cited"}:
        return False
    if not isinstance(draft["lang"], str) or draft["lang"] not in SUPPORTED_LANGUAGES:
        return False
    if not isinstance(draft["text"], str) or not draft["text"].strip() or len(draft["text"]) > 100_000:
        return False
    if not _string_list(draft["cited"], 100, 100) or not _string_list(value["reasons"], 100, 2000):
        return False
    if service is not None:
        # Numbers may repeat across sections. Check the attributed section and
        # the exact excerpt together, not merely the presence of the number.
        rule_template = TEMPLATES[draft["lang"]]["rule"]
        for ref in draft["cited"]:
            if not any(
                rule.number == ref and rule_template.format(
                    number=rule.number, section=rule.section, excerpt=rule.excerpt,
                ) in draft["text"]
                for rule in service.catalog.rules
            ):
                return False
        # A term source is separate context, not a number in `cited`. If the
        # assistant says it found a term, require a literal attributed source.
        if NAMED_RULE_REASON in value["reasons"] and not service.catalog.named_sources_in_draft(draft["text"]):
            return False
    try:
        json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (TypeError, UnicodeError, ValueError, RecursionError):
        return False
    return True


def ensure_safety_review(result: dict[str, Any], service: TriageService) -> dict[str, Any]:
    risk = result["category"] in {"report.payment", "report.account", "complaint.admin", "report.complaint"}
    risk = risk or result["category"].startswith("complaint.") or NAMED_RULE_REASON in result["reasons"]
    risk = risk or result["category"] in service.catalog.always_human
    risk = risk or result["priority"] == "p0" or result["confidence"] < 0.6 or result["lang"] == "und" or result["is_spam_or_duplicate"]
    if risk and not result["needs_human"]:
        result = dict(result)
        result["needs_human"] = True
        result["reasons"] = [*result["reasons"][:99], "Проверка человеком обязательна из-за риска или неуверенности."]
    return result


def checked_triage(service: TriageService, ticket: dict[str, Any]) -> dict[str, Any]:
    """Use the same structural and safety checks for HTTP and local tools."""
    result = service.triage(ticket)
    if not valid_result(result, service):
        raise InputError("Результат разбора некорректен")
    return ensure_safety_review(result, service)
