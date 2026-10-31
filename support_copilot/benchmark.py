"""Reproducible loopback HTTP benchmark with an isolated, temporary queue."""

from __future__ import annotations

import argparse
import http.client
import itertools
import json
import math
import secrets
import sys
import tempfile
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from .admin_queue import AdminQueue
from .batch import iter_tickets
from .catalog import CatalogError
from .config import add_data_arguments, make_service
from .server import CopilotServer, valid_result
from .service import InputError, TriageService


def _percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return round(ordered[max(0, math.ceil(fraction * len(ordered)) - 1)] * 1000, 3)


def benchmark(service: TriageService, input_path: str, requests: int = 1000, workers: int = 1) -> dict[str, Any]:
    if not 1 <= requests <= 10_000 or not 1 <= workers <= 32:
        raise InputError("Нужно 1–10000 запросов и 1–32 одновременных клиента")
    tickets = [ticket for _, ticket in itertools.islice(iter_tickets(input_path), requests)]
    if not tickets:
        raise InputError("Во входном файле нет обращений")

    with tempfile.TemporaryDirectory(prefix="copilot-benchmark-") as tmp:
        queue = AdminQueue(Path(tmp) / "queue.sqlite3", max_items=max(1000, len(tickets)))
        server = CopilotServer(("127.0.0.1", 0), service, queue, secrets.token_urlsafe(32))
        thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
        thread.start()

        def send(ticket: dict[str, Any]) -> tuple[float, str, str, bool, bool]:
            start = time.perf_counter()
            connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=30)
            try:
                body = json.dumps(ticket, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
                connection.request("POST", "/triage", body, {"Content-Type": "application/json"})
                response = connection.getresponse()
                raw = response.read()
                elapsed = time.perf_counter() - start
                status = str(response.status)
                handoff = response.getheader("X-Review-Status") or "none"
                try:
                    result = json.loads(raw)
                except (json.JSONDecodeError, UnicodeError):
                    return elapsed, status, handoff, False, False
                is_valid = response.status == 200 and valid_result(result, service)
                needs_human = bool(result.get("needs_human")) if isinstance(result, dict) and is_valid else False
                return elapsed, status, handoff, is_valid, needs_human
            except (OSError, UnicodeError, ValueError, http.client.HTTPException):
                return time.perf_counter() - start, "transport_error", "none", False, False
            finally:
                connection.close()

        try:
            with ThreadPoolExecutor(max_workers=workers) as executor:
                outcomes = list(executor.map(send, tickets))
        finally:
            server.shutdown()
            server.server_close()
            thread.join()
    durations = [item[0] for item in outcomes]
    statuses = Counter(item[1] for item in outcomes)
    handoffs = Counter(item[2] for item in outcomes)
    return {
        "requests": len(outcomes),
        "concurrent_clients": workers,
        "http_status_counts": dict(sorted(statuses.items())),
        "valid_result_count": sum(item[3] for item in outcomes),
        "review_handoff_counts": dict(sorted(handoffs.items())),
        "required_handoff_failures": sum(item[4] and item[2] != "queued" for item in outcomes),
        "http_p50_ms": _percentile(durations, 0.50),
        "http_p95_ms": _percentile(durations, 0.95),
        "http_p99_ms": _percentile(durations, 0.99),
        "http_max_ms": round(max(durations) * 1000, 3),
        "notes": [
            "Временный локальный HTTP-сервер и отдельная SQLite-очередь; данные удаляются после теста.",
            "Замеры включают локальную сериализацию, HTTP и постановку в очередь, но не браузер и внешнюю сеть.",
            "Это не production-нагрузочный тест, не стоимость инфраструктуры и не подтверждение SLA.",
            "При нескольких клиентах порядок обработки и дедупликация могут измениться.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Локальный HTTP benchmark без внешних сервисов")
    add_data_arguments(parser)
    parser.add_argument("--in", dest="input_path", required=True)
    parser.add_argument("--requests", type=int, default=1000)
    parser.add_argument("--workers", type=int, default=1)
    args = parser.parse_args()
    try:
        result = benchmark(make_service(args), args.input_path, args.requests, args.workers)
    except (CatalogError, InputError, OSError, UnicodeError) as exc:
        print(f"Ошибка: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
