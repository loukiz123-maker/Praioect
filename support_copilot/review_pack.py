"""Create a private, reproducible sample for independent human review."""

from __future__ import annotations

import argparse
import hashlib
import heapq
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

from .batch import iter_tickets
from .catalog import CatalogError
from .config import add_data_arguments, make_service
from .review_common import draft_fingerprint, source_fingerprint, source_snapshot, ticket_key
from .service import InputError, TriageService
from .text import SUPPORTED_LANGUAGES


def create_review_pack(
    service: TriageService, input_path: str, output_path: str, count: int = 100, seed: int = 42, *,
    blind_labels: bool = False, language: str | None = None,
) -> int:
    if language is not None and language not in SUPPORTED_LANGUAGES | {"und"}:
        raise InputError("Неизвестный язык для выборки")
    if count < 1 or count > 10_000:
        raise InputError("Размер выборки должен быть от 1 до 10000")
    if output_path == "-" or not output_path.lower().endswith(".jsonl"):
        raise InputError("Ручная выборка должна сохраняться в приватный файл .jsonl")
    if input_path != "-" and Path(input_path).resolve() == Path(output_path).resolve():
        raise InputError("Входной и выходной файл должны различаться")

    # Process the full input in its original order (deduplication is stateful),
    # but retain only the smallest keyed hashes. Output remains in input order.
    sample: list[tuple[int, int, dict[str, Any]]] = []
    seen: set[str] = set()
    for line_number, ticket in iter_tickets(input_path):
        key = ticket_key(ticket)
        if key in seen:
            raise InputError(f"Строка {line_number}: повторный ticket_id")
        seen.add(key)
        try:
            result = service.triage(ticket)
        except InputError as exc:
            raise InputError(f"Строка {line_number}: {exc}") from exc
        if language is not None and result["lang"] != language:
            continue
        rank = int.from_bytes(hashlib.sha256(f"{seed}\0{key}".encode("utf-8")).digest(), "big")
        if len(sample) == count and rank >= -sample[0][0]:
            continue
        # Private player text, without gold labels, administrator messages,
        # image contents or a predicted class. Blind mode hides the draft too.
        source = source_snapshot(ticket)
        row = {
            "ticket_id": ticket["ticket_id"],
            "source": source,
            "source_sha256": source_fingerprint(source),
            "review": {"category": None, "priority": None},
        }
        if not blind_labels:
            row.update({
                "draft_reply": result["draft_reply"],
                "needs_human": result["needs_human"],
                "draft_sha256": draft_fingerprint(result["draft_reply"]),
            })
            row["review"].update({
                "draft_rating": None,
                "citations_relevant": None,
                "language_rating": None,
                "reviewer_native": None,
            })
        item = (-rank, -line_number, row)
        if len(sample) < count:
            heapq.heappush(sample, item)
        else:
            heapq.heapreplace(sample, item)
    rows = [item[2] for item in sorted(sample, key=lambda item: -item[1])]
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix=".copilot-review-", suffix=".tmp", dir=output.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            for row in rows:
                stream.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
        os.replace(tmp_path, output)
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
    return len(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Приватная детерминированная выборка для ручной оценки")
    add_data_arguments(parser)
    parser.add_argument("--in", dest="input_path", required=True)
    parser.add_argument("--out", dest="output_path", required=True, help="Приватный выходной .jsonl")
    parser.add_argument("--count", type=int, default=100)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--blind-labels", action="store_true", help="Скрыть черновик и выход модели для независимой разметки категории/приоритета")
    parser.add_argument("--language", choices=sorted(SUPPORTED_LANGUAGES | {"und"}), help="Фильтр по эвристически распознанному языку, не по экспертной разметке")
    args = parser.parse_args()
    try:
        count = create_review_pack(make_service(args), args.input_path, args.output_path, args.count, args.seed, blind_labels=args.blind_labels, language=args.language)
    except (CatalogError, InputError, OSError, UnicodeError) as exc:
        print(f"Ошибка: {exc}", file=sys.stderr)
        return 2
    print(f"Подготовлено обращений для ручной оценки: {count}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
