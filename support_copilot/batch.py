"""Stream JSONL/JSONL.GZ records through the exact same triage pipeline."""

from __future__ import annotations

import argparse
import gzip
import json
import os
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, TextIO

from .catalog import CatalogError
from .config import add_data_arguments, make_service
from .service import InputError, TriageService


@contextmanager
def open_input(path: str) -> Iterator[TextIO]:
    if path == "-":
        yield sys.stdin
    elif path.endswith(".gz"):
        with gzip.open(path, "rt", encoding="utf-8") as stream:
            yield stream
    else:
        with open(path, encoding="utf-8") as stream:
            yield stream


def iter_tickets(path: str) -> Iterator[tuple[int, dict]]:
    with open_input(path) as source:
        for line_number, line in enumerate(source, 1):
            if not line.strip():
                continue
            try:
                ticket = json.loads(line)
            except json.JSONDecodeError as exc:
                raise InputError(f"Строка {line_number}: некорректный JSON") from exc
            if not isinstance(ticket, dict):
                raise InputError(f"Строка {line_number}: ожидается объект")
            yield line_number, ticket


def _write_predictions(service: TriageService, input_path: str, output: TextIO) -> int:
    count = 0
    for line_number, ticket in iter_tickets(input_path):
        try:
            prediction = service.triage(ticket)
        except InputError as exc:
            raise InputError(f"Строка {line_number}: {exc}") from exc
        if ticket.get("ticket_id") is not None:
            prediction = {"ticket_id": ticket["ticket_id"], **prediction}
        output.write(json.dumps(prediction, ensure_ascii=False, separators=(",", ":")) + "\n")
        count += 1
    return count


def predict(service: TriageService, input_path: str, output_path: str) -> int:
    if input_path != "-" and output_path != "-" and Path(input_path).resolve() == Path(output_path).resolve():
        raise InputError("Входной и выходной файл должны различаться")
    if output_path == "-":
        return _write_predictions(service, input_path, sys.stdout)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    # Write privately, then replace atomically only after all rows succeed.
    fd, tmp_path = tempfile.mkstemp(prefix=".copilot-", suffix=".tmp", dir=output.parent)
    os.close(fd)
    try:
        if output_path.endswith(".gz"):
            stream = gzip.open(tmp_path, "wt", encoding="utf-8")
        else:
            stream = open(tmp_path, "w", encoding="utf-8")
        with stream:
            count = _write_predictions(service, input_path, stream)
        os.replace(tmp_path, output)
        return count
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Предсказания Support Copilot для JSONL")
    add_data_arguments(parser)
    parser.add_argument("--in", dest="input_path", required=True, help="Входной .jsonl или .jsonl.gz; - для stdin")
    parser.add_argument("--out", dest="output_path", required=True, help="Выходной .jsonl или .jsonl.gz; - для stdout")
    args = parser.parse_args()
    try:
        service = make_service(args)
        count = predict(service, args.input_path, args.output_path)
    except (CatalogError, InputError, OSError, UnicodeError) as exc:
        print(f"Ошибка: {exc}", file=sys.stderr)
        return 2
    print(f"Обработано обращений: {count}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
