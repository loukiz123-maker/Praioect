"""Measure only labels actually present in a local validation file."""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from typing import Any

from .batch import iter_tickets
from .catalog import CatalogError
from .config import add_data_arguments, make_service
from .service import InputError, TriageService


def macro_f1(gold: list[str], predicted: list[str]) -> float | None:
    if not gold:
        return None
    labels = set(gold) | set(predicted)
    scores: list[float] = []
    for label in labels:
        tp = sum(g == label and p == label for g, p in zip(gold, predicted))
        fp = sum(g != label and p == label for g, p in zip(gold, predicted))
        fn = sum(g == label and p != label for g, p in zip(gold, predicted))
        denominator = 2 * tp + fp + fn
        scores.append(2 * tp / denominator if denominator else 0.0)
    return sum(scores) / len(scores)


def evaluate(service: TriageService, input_path: str) -> dict[str, Any]:
    category_gold: list[str] = []
    category_pred: list[str] = []
    priority_gold: list[str] = []
    priority_pred: list[str] = []
    times: list[float] = []
    human = cited = total = 0
    for line_number, ticket in iter_tickets(input_path):
        start = time.perf_counter()
        try:
            result = service.triage(ticket)
        except InputError as exc:
            raise InputError(f"Строка {line_number}: {exc}") from exc
        times.append(time.perf_counter() - start)
        total += 1
        human += bool(result["needs_human"])
        cited += bool(result["draft_reply"]["cited"])
        category = ticket.get("category")
        priority = ticket.get("priority")
        if isinstance(category, str) and category.strip():
            category_gold.append(category)
            category_pred.append(result["category"])
        if isinstance(priority, str) and priority.strip():
            priority_gold.append(priority)
            priority_pred.append(result["priority"])
    times.sort()
    p95 = times[max(0, math.ceil(0.95 * len(times)) - 1)] if times else None
    accuracy = (sum(g == p for g, p in zip(category_gold, category_pred)) / len(category_gold)) if category_gold else None
    return {
        "tickets": total,
        "category_labeled": len(category_gold),
        "category_accuracy": round(accuracy, 4) if accuracy is not None else None,
        "priority_labeled": len(priority_gold),
        "priority_macro_f1": round(value, 4) if (value := macro_f1(priority_gold, priority_pred)) is not None else None,
        "needs_human_share": round(human / total, 4) if total else None,
        "cited_reply_share": round(cited / total, 4) if total else None,
        "local_pipeline_p95_ms": round(p95 * 1000, 3) if p95 is not None else None,
        "external_api_cost_usd_per_ticket": 0.0,
        "notes": [
            "p95 измерен в локальном процессе, без HTTP и стоимости инфраструктуры.",
            "Метрики классификации рассчитываются только по строкам с имеющейся разметкой.",
            "Качество, релевантность цитат и языки требуют отдельной оценки людьми.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Честная оценка на доступной разметке")
    add_data_arguments(parser)
    parser.add_argument("--in", dest="input_path", required=True)
    args = parser.parse_args()
    try:
        result = evaluate(make_service(args), args.input_path)
    except (CatalogError, InputError, OSError, UnicodeError) as exc:
        print(f"Ошибка: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
