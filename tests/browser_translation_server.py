"""Isolated UI test server with synthetic fixtures and a fake translator.

Never use this server for real tickets: its admin key is public test data and
its translations are deliberately fake. No network request is made to Google.
"""

from __future__ import annotations

import argparse
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from helpers import write_fixtures  # noqa: E402
from support_copilot.admin_queue import AdminQueue  # noqa: E402
from support_copilot.catalog import Catalog  # noqa: E402
from support_copilot.server import CopilotServer  # noqa: E402
from support_copilot.service import TriageService  # noqa: E402


TEST_ADMIN_KEY = "synthetic-admin-browser-key-only-123456"


class FakeTranslator:
    configured = True

    def translate(self, text: str, target: str) -> str:
        if "SLOW_MARKER" in text:
            time.sleep(1.2)
        # Intentional HTML-like text verifies that the UI uses textContent.
        return {
            "ru": "Тестовый перевод <b>не HTML</b>",
            "en": "Synthetic translation <b>not HTML</b>",
            "kk": "Сынақ аудармасы <b>HTML емес</b>",
        }[target]


def main() -> None:
    parser = argparse.ArgumentParser(description="Isolated synthetic translation browser test server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8012)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="copilot-ui-translation-") as directory:
        rules, taxonomy, _ = write_fixtures(directory)
        service = TriageService(Catalog(rules, taxonomy))
        queue = AdminQueue(Path(directory) / "queue.sqlite3")
        server = CopilotServer((args.host, args.port), service, queue, TEST_ADMIN_KEY, FakeTranslator())
        print("Synthetic UI test server; Google calls are mocked. Do not use real tickets.", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()


if __name__ == "__main__":
    main()
