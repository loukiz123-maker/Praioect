"""Local HTTP API, support interface, and protected administrator queue."""

from __future__ import annotations

import argparse
import hmac
import json
import math
import mimetypes
import os
import sqlite3
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

from .admin_queue import (
    AdminQueue,
    QueueConflict,
    QueueFull,
    QueueNotFound,
    load_admin_key,
    new_receipt,
    validate_receipt,
)
from .catalog import CatalogError
from .config import add_data_arguments, make_service
from .service import InputError, TriageService, validate_ticket
from .text import SUPPORTED_LANGUAGES

STATIC = Path(__file__).resolve().parent / "static"
MAX_REQUEST_BYTES = 1_048_576
ASSETS = {
    "/": "index.html",
    "/admin": "admin.html",
    "/admin/": "admin.html",
    "/app.css": "app.css",
    "/app.js": "app.js",
    "/admin.css": "admin.css",
    "/admin.js": "admin.js",
    "/brand-g.svg": "brand-g.svg",
    "/favicon.svg": "favicon.svg",
    "/city-banner.jpg": "city-banner.jpg",
}
RESULT_KEYS = {
    "lang", "category", "priority", "is_spam_or_duplicate", "extracted",
    "draft_reply", "needs_human", "confidence", "reasons",
}


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
        rule_numbers = {rule.number for rule in service.catalog.rules}
        if any(ref not in rule_numbers or ref not in draft["text"] for ref in draft["cited"]):
            return False
    try:
        json.dumps(value, ensure_ascii=False).encode("utf-8")
    except (TypeError, UnicodeError, ValueError, RecursionError):
        return False
    return True


def _string_list(value: Any, max_items: int, max_length: int) -> bool:
    return isinstance(value, list) and len(value) <= max_items and all(isinstance(x, str) and len(x) <= max_length for x in value)


def _ensure_safety_review(result: dict[str, Any], service: TriageService) -> dict[str, Any]:
    risk = result["category"] in {"report.payment", "report.account", "complaint.admin"}
    risk = risk or result["category"] in service.catalog.always_human
    risk = risk or result["priority"] == "p0" or result["confidence"] < 0.6 or result["lang"] == "und" or result["is_spam_or_duplicate"]
    if risk and not result["needs_human"]:
        result = dict(result)
        result["needs_human"] = True
        result["reasons"] = [*result["reasons"], "Проверка человеком обязательна из-за риска или неуверенности."]
    return result


class HttpFailure(Exception):
    def __init__(self, status: int, message: str):
        self.status = status
        super().__init__(message)


class CopilotServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(
        self, server_address: tuple[str, int], service: TriageService | None,
        queue: AdminQueue | None = None, admin_key: str | None = None,
    ):
        self.service = service
        self.queue = queue if admin_key else None
        self.admin_key = admin_key if queue else None
        self.auth_lock = threading.Lock()
        self.auth_failures: dict[str, list[float]] = {}
        super().__init__(server_address, CopilotHandler)


class CopilotHandler(BaseHTTPRequestHandler):
    server: CopilotServer
    server_version = "SupportCopilot"
    sys_version = ""

    def log_message(self, format: str, *args: object) -> None:
        # Never log ticket text, URL parameters, receipts, or caller identifiers.
        return

    def _write(self, status: int, body: bytes, content_type: str, headers: dict[str, str] | None = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; img-src 'self' data:; script-src 'self'; style-src 'self'; base-uri 'none'; form-action 'self'")
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status: int, value: object, headers: dict[str, str] | None = None) -> None:
        try:
            self._write(status, json.dumps(value, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8", headers)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            # A browser may have timed out and retried the handoff independently.
            pass

    def _body(self) -> Any:
        raw_length = self.headers.get("Content-Length")
        try:
            length = int(raw_length) if raw_length is not None else -1
        except ValueError:
            length = -1
        if length < 0:
            raise HttpFailure(411, "Необходим корректный Content-Length")
        if length > MAX_REQUEST_BYTES:
            raise HttpFailure(413, "Запрос слишком большой")
        if self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower() != "application/json":
            raise HttpFailure(415, "Используйте Content-Type: application/json")
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            # Reject escaped unpaired surrogates before they reach HTTP/SQLite.
            json.dumps(payload, ensure_ascii=False).encode("utf-8")
            return payload
        except (UnicodeError, ValueError, RecursionError) as exc:
            raise HttpFailure(400, "Тело запроса должно быть корректным JSON в UTF-8") from exc

    def _authorize(self) -> None:
        if not self.server.queue or not self.server.admin_key:
            raise HttpFailure(503, "Очередь администратора недоступна")
        authorization = self.headers.get("Authorization", "")
        if not authorization:
            raise HttpFailure(401, "Нужен ключ доступа администратора")
        now = time.monotonic()
        # This simple local limiter is not a replacement for production identity,
        # TLS, and access controls. No addresses are written to disk or logs.
        client = self.client_address[0]
        with self.server.auth_lock:
            attempts = [entry for entry in self.server.auth_failures.get(client, []) if now - entry < 60]
            if len(attempts) >= 8:
                raise HttpFailure(429, "Слишком много попыток. Подождите минуту")
            try:
                candidate = authorization.removeprefix("Bearer ").encode("ascii")
                correct = authorization.startswith("Bearer ") and hmac.compare_digest(candidate, self.server.admin_key.encode("ascii"))
            except UnicodeError:
                correct = False
            if not correct:
                attempts.append(now)
                self.server.auth_failures[client] = attempts
                raise HttpFailure(401, "Неверный ключ администратора")
            self.server.auth_failures.pop(client, None)

    def _queue(self) -> AdminQueue:
        if not self.server.queue or not self.server.admin_key:
            raise HttpFailure(503, "Очередь администратора недоступна")
        return self.server.queue

    def _receipt(self, *, create: bool = False) -> str:
        value = self.headers.get("X-Review-Receipt")
        if value is None and create:
            return new_receipt()
        return validate_receipt(value)

    def _try_enqueue(
        self, payload: Any, receipt: str, source: str, result: dict[str, Any] | None = None,
    ) -> dict[str, str]:
        if not self.server.queue or not self.server.admin_key:
            return {"X-Review-Status": "unavailable"}
        try:
            self.server.queue.enqueue(payload, receipt, source, result=result)
        except Exception as exc:
            print(f"Очередь администратора недоступна: {type(exc).__name__}", file=sys.stderr)
            return {"X-Review-Status": "unavailable"}
        return {"X-Review-Status": "queued", "X-Review-Receipt": receipt}

    def _triage(self, payload: Any) -> None:
        # Validate independently so a broken classifier cannot queue invalid input.
        validate_ticket(payload)
        receipt = self._receipt(create=True)
        service = self.server.service
        if service is None:
            headers = self._try_enqueue(payload, receipt, "failure")
            self._json(503, {"error": "Автоматический разбор недоступен"}, headers)
            return
        try:
            result = service.triage(payload)
            if not valid_result(result, service):
                raise ValueError("invalid classifier result")
            result = _ensure_safety_review(result, service)
        except Exception as exc:  # Input was already validated; any classifier error needs review.
            print(f"Ошибка обработки запроса: {type(exc).__name__}", file=sys.stderr)
            headers = self._try_enqueue(payload, receipt, "failure")
            self._json(500, {"error": "Не удалось автоматически разобрать обращение"}, headers)
            return
        headers = self._try_enqueue(payload, receipt, "needs_human", result) if result["needs_human"] else {"X-Review-Status": "not_required"}
        self._json(200, result, headers)

    def _review_request(self, body: Any) -> None:
        if not isinstance(body, dict):
            raise InputError("Нужен JSON-объект")
        ticket = body.get("ticket")
        validate_ticket(ticket)
        source = body.get("source")
        if not isinstance(source, str) or source not in {"manual", "failure"}:
            raise InputError("Неверная причина передачи")
        result = body.get("result")
        if result is not None and not valid_result(result, self.server.service):
            raise InputError("Результат разбора некорректен")
        receipt = self._receipt()
        review = self._queue().enqueue(
            ticket, receipt, source, result=result, draft=body.get("draft"),
            update_draft=source == "manual" and body.get("draft") is not None,
        )
        self._json(200 if not review["created"] else 201, {"status": review["status"]})

    def _admin_detail_id(self, path: str) -> str | None:
        prefix = "/admin/api/reviews/"
        return path[len(prefix):] if path.startswith(prefix) else None

    def do_GET(self) -> None:
        path = urlsplit(self.path).path
        try:
            if path == "/health":
                service = self.server.service
                catalog = service.catalog if service else None
                self._json(200, {
                    "status": "ok" if catalog else "degraded",
                    "rules_loaded": len(catalog.rules) if catalog else 0,
                    "knowledge_articles": len(catalog.articles) if catalog else 0,
                    "taxonomy_version": catalog.taxonomy.get("version") if catalog else None,
                    "admin_queue": "ready" if self.server.queue and self.server.admin_key else "unavailable",
                })
            elif path == "/reviews/status":
                self._json(200, self._queue().status(self._receipt()))
            elif path == "/admin/api/session":
                self._authorize()
                self._json(200, {"authenticated": True})
            elif path == "/admin/api/reviews":
                self._authorize()
                params = parse_qs(urlsplit(self.path).query, keep_blank_values=True)
                view = params.get("view", ["active"])[0]
                try:
                    offset = int(params.get("offset", ["0"])[0])
                except ValueError:
                    raise InputError("Неверные параметры списка обращений") from None
                self._json(200, self._queue().list_reviews(view=view, offset=offset))
            elif (review_id := self._admin_detail_id(path)) is not None:
                self._authorize()
                self._json(200, self._queue().get(review_id))
            elif path in ASSETS:
                asset = STATIC / ASSETS[path]
                try:
                    body = asset.read_bytes()
                except OSError:
                    raise HttpFailure(404, "Ресурс не найден") from None
                content_type = mimetypes.guess_type(asset.name)[0] or "application/octet-stream"
                if content_type.startswith("text/") or content_type == "application/javascript":
                    content_type += "; charset=utf-8"
                self._write(200, body, content_type)
            else:
                raise HttpFailure(404, "Маршрут не найден")
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass
        except Exception as exc:
            self._handle_error(exc)

    def do_POST(self) -> None:
        path = urlsplit(self.path).path
        try:
            if path == "/triage":
                self._triage(self._body())
            elif path == "/reviews/request":
                self._review_request(self._body())
            elif (review_id := self._admin_detail_id(path)) is not None:
                self._authorize()
                body = self._body()
                if not isinstance(body, dict):
                    raise InputError("Нужен JSON-объект")
                self._json(200, self._queue().update(review_id, body.get("version"), body.get("status"), body.get("draft")))
            else:
                raise HttpFailure(404, "Маршрут не найден")
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass
        except Exception as exc:
            self._handle_error(exc)

    def do_DELETE(self) -> None:
        try:
            review_id = self._admin_detail_id(urlsplit(self.path).path)
            if review_id is None:
                raise HttpFailure(404, "Маршрут не найден")
            self._authorize()
            body = self._body()
            if not isinstance(body, dict):
                raise InputError("Нужен JSON-объект")
            self._queue().delete(review_id, body.get("version"))
            self._json(200, {"deleted": True})
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass
        except Exception as exc:
            self._handle_error(exc)

    def _handle_error(self, exc: Exception) -> None:
        if isinstance(exc, HttpFailure):
            self._json(exc.status, {"error": str(exc)})
        elif isinstance(exc, InputError):
            self._json(400, {"error": str(exc)})
        elif isinstance(exc, QueueNotFound):
            self._json(404, {"error": str(exc)})
        elif isinstance(exc, QueueConflict):
            self._json(409, {"error": str(exc)})
        elif isinstance(exc, QueueFull):
            self._json(503, {"error": str(exc)})
        elif isinstance(exc, (sqlite3.Error, OSError)):
            print(f"Ошибка очереди администратора: {type(exc).__name__}", file=sys.stderr)
            self._json(503, {"error": "Очередь администратора временно недоступна"})
        else:
            print(f"Ошибка сервера: {type(exc).__name__}", file=sys.stderr)
            self._json(500, {"error": "Не удалось выполнить запрос"})


def main() -> int:
    parser = argparse.ArgumentParser(description="Локальный API Support Copilot")
    add_data_arguments(parser)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--admin-db", default=os.environ.get("COPILOT_ADMIN_DB", "data/admin-queue.sqlite3"))
    parser.add_argument("--admin-key-file", default=os.environ.get("COPILOT_ADMIN_KEY_FILE", "data/admin.key"))
    args = parser.parse_args()
    queue = None
    key = None
    try:
        key = load_admin_key(args.admin_key_file, os.environ.get("COPILOT_ADMIN_TOKEN") or None)
        queue = AdminQueue(args.admin_db)
    except (OSError, ValueError, sqlite3.Error) as exc:
        print(f"Очередь администратора недоступна: {type(exc).__name__}. Проверьте доступ к папке данных и ключ.", file=sys.stderr)
    try:
        service = make_service(args)
    except (CatalogError, OSError) as exc:
        # Keep manual review usable even if the classifier cannot initialize.
        print(f"Автоматический разбор недоступен: {exc}", file=sys.stderr)
        service = None
    except Exception as exc:
        # Unexpected initialization errors must not take manual review down.
        print(f"Автоматический разбор недоступен: {type(exc).__name__}", file=sys.stderr)
        service = None
    try:
        server = CopilotServer((args.host, args.port), service, queue, key)
    except OSError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"Support Copilot запущен на {args.host}:{server.server_port}", flush=True)
    if queue and key:
        if os.environ.get("COPILOT_ADMIN_TOKEN"):
            print("Панель администратора: /admin. Ключ задан переменной COPILOT_ADMIN_TOKEN.", flush=True)
        else:
            print(f"Панель администратора: /admin. Ключ хранится в файле {args.admin_key_file}.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
