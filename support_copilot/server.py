"""Small local HTTP API and demonstration interface (no external services)."""

from __future__ import annotations

import argparse
import json
import mimetypes
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from .catalog import CatalogError
from .config import add_data_arguments, make_service
from .service import InputError, TriageService

STATIC = Path(__file__).resolve().parent / "static"
MAX_REQUEST_BYTES = 1_048_576
ASSETS = {
    "/": "index.html",
    "/app.css": "app.css",
    "/app.js": "app.js",
    "/brand-g.svg": "brand-g.svg",
    "/favicon.svg": "favicon.svg",
    "/city-banner.jpg": "city-banner.jpg",
}


class CopilotServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, server_address: tuple[str, int], service: TriageService):
        self.service = service
        super().__init__(server_address, CopilotHandler)


class CopilotHandler(BaseHTTPRequestHandler):
    server: CopilotServer
    server_version = "SupportCopilot"
    sys_version = ""

    def log_message(self, format: str, *args: object) -> None:
        # Never log ticket text, URL parameters, or caller identifiers.
        return

    def _write(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; img-src 'self' data:; script-src 'self'; style-src 'self'; base-uri 'none'")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status: int, value: object) -> None:
        self._write(status, json.dumps(value, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

    def do_GET(self) -> None:
        path = urlsplit(self.path).path
        if path == "/health":
            catalog = self.server.service.catalog
            self._json(200, {"status": "ok", "rules_loaded": len(catalog.rules), "knowledge_articles": len(catalog.articles), "taxonomy_version": catalog.taxonomy.get("version")})
            return
        if path in ASSETS:
            asset = STATIC / ASSETS[path]
            try:
                body = asset.read_bytes()
            except OSError:
                self._json(404, {"error": "Ресурс не найден"})
                return
            content_type = mimetypes.guess_type(asset.name)[0] or "application/octet-stream"
            if content_type.startswith("text/") or content_type == "application/javascript":
                content_type += "; charset=utf-8"
            self._write(200, body, content_type)
            return
        self._json(404, {"error": "Маршрут не найден"})

    def do_POST(self) -> None:
        if urlsplit(self.path).path != "/triage":
            self._json(404, {"error": "Маршрут не найден"})
            return
        raw_length = self.headers.get("Content-Length")
        try:
            length = int(raw_length) if raw_length is not None else -1
        except ValueError:
            length = -1
        if length < 0:
            self._json(411, {"error": "Необходим корректный Content-Length"})
            return
        if length > MAX_REQUEST_BYTES:
            self._json(413, {"error": "Запрос слишком большой"})
            return
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            # Reject escaped unpaired surrogates instead of failing later when
            # the response or an identifier is encoded back to UTF-8.
            json.dumps(payload, ensure_ascii=False).encode("utf-8")
        except (UnicodeError, ValueError, RecursionError):
            self._json(400, {"error": "Тело запроса должно быть корректным JSON в UTF-8"})
            return
        try:
            result = self.server.service.triage(payload)
        except InputError as exc:
            self._json(400, {"error": str(exc)})
            return
        except Exception as exc:  # Do not leak payloads or paths over HTTP.
            print(f"Ошибка обработки запроса: {type(exc).__name__}", file=sys.stderr)
            self._json(500, {"error": "Не удалось обработать обращение"})
            return
        self._json(200, result)


def main() -> int:
    parser = argparse.ArgumentParser(description="Локальный API Support Copilot")
    add_data_arguments(parser)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    try:
        service = make_service(args)
        server = CopilotServer((args.host, args.port), service)
    except (CatalogError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"Support Copilot запущен на {args.host}:{server.server_port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
