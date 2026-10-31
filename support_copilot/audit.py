"""Aggregate-only, local audit of player requests and historical admin replies.

Historical answers/derived verdicts are inspected only for this report. They
are never passed as additional features to a new ticket's inference. The
report does not contain ticket IDs, player text, admin text, or raw labels.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from typing import Any

from .batch import iter_tickets
from .config import add_data_arguments, make_service
from .service import RULE_REF_RE, TriageService, requires_rule

EVIDENCE_GAP = re.compile(
    r"(?i)(?:недостаточно\s+(?:доказательств|материалов)|нет\s+доказательств|"
    r"без\s+доказательств|не\s+хватает\s+(?:доказательств|материалов)|"
    r"insufficient\s+evidence|lack\s+of\s+evidence|no\s+evidence)"
)


def _role_text(ticket: dict[str, Any], roles: set[str]) -> str:
    messages = ticket.get("messages")
    if not isinstance(messages, list):
        return ""
    return "\n".join(
        message.get("text", "") for message in messages
        if isinstance(message, dict) and message.get("role") in roles and isinstance(message.get("text", ""), str)
    )


def audit(service: TriageService, input_path: str) -> dict[str, Any]:
    counts: Counter[str] = Counter()
    categories: Counter[str] = Counter()
    lengths: Counter[str] = Counter()
    missing_categories: Counter[str] = Counter()
    missing_lengths: Counter[str] = Counter()
    known_numbers = {rule.number for rule in service.catalog.rules}
    for _, ticket in iter_tickets(input_path):
        # TriageService selects player/reporter messages itself and excludes
        # admin responses, reported-player responses and gold/derived fields.
        result = service.triage(ticket)
        player_text = _role_text(ticket, {"player", "reporter"})
        admin_text = _role_text(ticket, {"admin"})
        refs = result["draft_reply"]["cited"]
        needs_rule = requires_rule(service.catalog, ticket["kind"], result["category"])
        counts["tickets"] += 1
        counts["historical_admin_reply_present"] += bool(admin_text.strip())
        counts["historical_verdict_field_present"] += bool(ticket.get("verdict"))
        counts["historical_punishment_field_present"] += bool(ticket.get("punishment"))
        counts["historical_violation_field_present"] += bool(ticket.get("violation"))
        counts["historical_reply_evidence_gap_phrase"] += bool(EVIDENCE_GAP.search(admin_text))
        admin_refs = set(RULE_REF_RE.findall(admin_text)) & known_numbers
        counts["historical_reply_existing_number_mentioned"] += bool(admin_refs)
        counts["generated_number_also_mentioned_in_historical_reply"] += bool(set(refs) & admin_refs)
        categories[result["category"]] += 1
        length = len(player_text.strip())
        length_band = "under_20" if length < 20 else "20_to_79" if length < 80 else "80_to_199" if length < 200 else "200_plus"
        lengths[length_band] += 1
        if needs_rule:
            counts["rule_required_by_predicted_category"] += 1
            has_numbered = any(ref in known_numbers for ref in refs)
            has_named_source = bool(service.catalog.named_sources_in_draft(result["draft_reply"]["text"]))
            counts["with_numbered_point"] += has_numbered
            counts["with_named_section_source"] += has_named_source
            counts["without_any_rule_source"] += not (has_numbered or has_named_source)
            counts["without_numbered_point"] += not has_numbered
            if not has_numbered:
                missing_categories[result["category"]] += 1
                missing_lengths[length_band] += 1
    return {
        "counts": dict(sorted(counts.items())),
        "predicted_categories": dict(sorted(categories.items())),
        "player_message_length_bands": dict(sorted(lengths.items())),
        "uncited_predicted_categories": dict(sorted(missing_categories.items())),
        "uncited_player_message_length_bands": dict(sorted(missing_lengths.items())),
        "notes": [
            "Это агрегированное исследование, а не разметка качества или независимая проверка модели.",
            "Совпадение номера с историческим ответом не подтверждает его раздел или релевантность: номера повторяются.",
            "Ненумерованный источник не входит в cited и не заменяет требуемый номер пункта.",
            "Ответы администраторов и извлечённые из них вердикты не используются при обработке нового обращения.",
            "Количество источников и совпадений не равно оценке правильности: необходима слепая проверка человеком.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Локальный агрегированный анализ жалоб и исторических ответов без публикации текстов")
    add_data_arguments(parser)
    parser.add_argument("--in", dest="input_path", required=True, help="Приватный JSONL или предоставленная HTML-обёртка")
    args = parser.parse_args()
    print(json.dumps(audit(make_service(args), args.input_path), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
