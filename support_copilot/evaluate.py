"""Aggregate local evaluation; never invent labels or human judgments."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
import time
from typing import Any

from .batch import iter_tickets
from .catalog import Catalog, CatalogError
from .config import add_data_arguments, make_service
from .review_common import draft_fingerprint, source_fingerprint, source_snapshot, ticket_key
from .service import InputError, TriageService, requires_rule


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


def _rating(value: Any, description: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 5:
        raise InputError(f"{description}: оценка должна быть целым числом от 1 до 5 или null")
    return value


def _load_reviews(path: str, catalog: Catalog) -> dict[str, tuple[dict[str, Any], str | None, str | None]]:
    reviews: dict[str, tuple[dict[str, Any], str | None, str | None]] = {}
    for line_number, entry in iter_tickets(path):
        key = ticket_key(entry)
        if key in reviews:
            raise InputError(f"Строка {line_number}: повторный ticket_id в ручной разметке")
        review = entry.get("review", entry)
        if not isinstance(review, dict):
            raise InputError(f"Строка {line_number}: review должен быть объектом")
        category = review.get("category")
        priority = review.get("priority")
        if category is not None and (not isinstance(category, str) or category not in catalog.categories):
            raise InputError(f"Строка {line_number}: неизвестная категория в ручной разметке")
        if priority is not None and (not isinstance(priority, str) or priority not in {"p0", "p1", "p2", "p3"}):
            raise InputError(f"Строка {line_number}: неизвестный приоритет в ручной разметке")
        _rating(review.get("draft_rating"), "Качество черновика")
        _rating(review.get("language_rating"), "Качество языка")
        for name in ("citations_relevant", "reviewer_native"):
            if review.get(name) is not None and not isinstance(review[name], bool):
                raise InputError(f"Строка {line_number}: {name} должно быть true, false или null")
        fingerprint = entry.get("draft_sha256")
        source_hash = entry.get("source_sha256")
        draft_judged = any(review.get(name) is not None for name in ("draft_rating", "language_rating", "citations_relevant"))
        if draft_judged and (not isinstance(fingerprint, str) or not re.fullmatch(r"[0-9a-f]{64}", fingerprint)):
            raise InputError(f"Строка {line_number}: для оценки черновика нужен draft_sha256 из review-pack")
        if fingerprint is not None and (not isinstance(fingerprint, str) or not re.fullmatch(r"[0-9a-f]{64}", fingerprint)):
            raise InputError(f"Строка {line_number}: некорректный draft_sha256")
        if source_hash is not None and (not isinstance(source_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", source_hash)):
            raise InputError(f"Строка {line_number}: некорректный source_sha256")
        if "source" in entry and source_hash is not None:
            if not isinstance(entry["source"], dict) or source_fingerprint(entry["source"]) != source_hash:
                raise InputError(f"Строка {line_number}: исходное обращение в ручной выборке изменено")
        if "draft_reply" in entry and fingerprint is not None:
            if not isinstance(entry["draft_reply"], dict) or draft_fingerprint(entry["draft_reply"]) != fingerprint:
                raise InputError(f"Строка {line_number}: черновик в ручной выборке изменён")
        reviews[key] = (review, fingerprint, source_hash)
    return reviews


def evaluate(
    service: TriageService, input_path: str, labels_path: str | None = None, reviews_path: str | None = None,
) -> dict[str, Any]:
    labels = _load_reviews(labels_path, service.catalog) if labels_path is not None else None
    reviews = _load_reviews(reviews_path, service.catalog) if reviews_path is not None else labels
    seen_ids: set[str] = set()
    category_gold: list[str] = []
    category_pred: list[str] = []
    priority_gold: list[str] = []
    priority_pred: list[str] = []
    draft_ratings: list[int] = []
    language_ratings: list[int] = []
    citation_reviews: list[bool] = []
    native_language_reviews: dict[str, int] = {}
    times: list[float] = []
    human = cited = required = required_cited = total = 0
    for line_number, ticket in iter_tickets(input_path):
        key = ticket_key(ticket) if labels is not None or reviews is not None else None
        if key is not None:
            if key in seen_ids:
                raise InputError(f"Строка {line_number}: повторный ticket_id во входных данных")
            seen_ids.add(key)
        start = time.perf_counter()
        try:
            result = service.triage(ticket)
        except InputError as exc:
            raise InputError(f"Строка {line_number}: {exc}") from exc
        times.append(time.perf_counter() - start)
        total += 1
        human += bool(result["needs_human"])
        has_citation = bool(result["draft_reply"]["cited"])
        cited += has_citation
        if requires_rule(service.catalog, ticket["kind"], result["category"]):
            required += 1
            required_cited += has_citation

        # When provided, bind each private review file to the original player
        # input as well as to the exact reviewed draft. Flat label-only files
        # without a source hash remain supported but have weaker provenance.
        source_hashes = [collection[key][2] for collection in (labels, reviews) if collection is not None and key in collection and collection[key][2] is not None]
        if source_hashes:
            actual_source = source_fingerprint(source_snapshot(ticket))
            if any(value != actual_source for value in source_hashes):
                raise InputError(f"Строка {line_number}: входное обращение изменилось после ручной разметки")
        label: dict[str, Any] = labels.get(key, ({}, None, None))[0] if labels is not None else ticket
        if reviews is not None:
            review, fingerprint, _ = reviews.get(key, ({}, None, None))
            judged = any(review.get(name) is not None for name in ("draft_rating", "language_rating", "citations_relevant"))
            if judged and fingerprint != draft_fingerprint(result["draft_reply"]):
                raise InputError(f"Строка {line_number}: черновик изменился после ручной оценки; нужна повторная проверка")
            if review.get("draft_rating") is not None:
                draft_ratings.append(review["draft_rating"])
            if review.get("language_rating") is not None:
                language_ratings.append(review["language_rating"])
                if review.get("reviewer_native") is True:
                    language = result["draft_reply"]["lang"]
                    native_language_reviews[language] = native_language_reviews.get(language, 0) + 1
            if review.get("citations_relevant") is not None:
                citation_reviews.append(review["citations_relevant"])

        category = label.get("category")
        priority = label.get("priority")
        if category is not None and not (isinstance(category, str) and not category.strip()):
            if not isinstance(category, str) or category not in service.catalog.categories:
                raise InputError(f"Строка {line_number}: неизвестная категория в разметке")
            category_gold.append(category)
            category_pred.append(result["category"])
        if priority is not None and not (isinstance(priority, str) and not priority.strip()):
            if not isinstance(priority, str) or priority not in {"p0", "p1", "p2", "p3"}:
                raise InputError(f"Строка {line_number}: неизвестный приоритет в разметке")
            priority_gold.append(priority)
            priority_pred.append(result["priority"])
    if any(collection is not None and set(collection) - seen_ids for collection in (labels, reviews)):
        raise InputError("Некоторые ticket_id ручной разметки отсутствуют во входных данных")
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
        "rules_required_count": required,
        "rules_required_with_citation": required_cited,
        "rules_required_without_citation": required - required_cited,
        "rules_required_citation_share": round(required_cited / required, 4) if required else None,
        "knowledge_articles_loaded": len(service.catalog.articles),
        "draft_rating_reviewed": len(draft_ratings),
        "draft_rating_mean": round(sum(draft_ratings) / len(draft_ratings), 4) if draft_ratings else None,
        "citation_relevance_reviewed": len(citation_reviews),
        "citation_relevance_share": round(sum(citation_reviews) / len(citation_reviews), 4) if citation_reviews else None,
        "language_rating_reviewed": len(language_ratings),
        "language_rating_mean": round(sum(language_ratings) / len(language_ratings), 4) if language_ratings else None,
        "native_language_reviews": native_language_reviews,
        "local_pipeline_p95_ms": round(p95 * 1000, 3) if p95 is not None else None,
        "external_api_cost_usd_per_ticket": 0.0,
        "notes": [
            "p95 измерен в локальном процессе, без HTTP и стоимости инфраструктуры.",
            "Метрики классификации рассчитываются только по строкам с имеющейся разметкой.",
            "Обязательность правил определена предсказанной категорией, а не экспертной разметкой.",
            "Наличие цитаты не подтверждает её релевантность; ручные оценки считаются только по предоставленным отзывам.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Честная оценка на доступной разметке")
    add_data_arguments(parser)
    parser.add_argument("--in", dest="input_path", required=True)
    parser.add_argument("--labels", help="Приватный JSONL с независимой разметкой категории и приоритета")
    parser.add_argument("--reviews", help="Отдельный приватный JSONL с ручной оценкой черновиков и цитат")
    args = parser.parse_args()
    try:
        result = evaluate(make_service(args), args.input_path, args.labels, args.reviews)
    except (CatalogError, InputError, OSError, UnicodeError) as exc:
        print(f"Ошибка: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
