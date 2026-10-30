"""Opt-in import of official public help pages into a PRIVATE review draft.

No ticket, player message, historical administrator answer or identifier is
sent. This module fetches only the fixed HTTPS pages below; inference is local.
Imported articles are unapproved until an operator checks rights, currency,
language, relevance and content. The output is never silently overwritten.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


@dataclass(frozen=True)
class OfficialPage:
    article_id: str
    title: str
    url: str
    language: str
    categories: tuple[str, ...]


# Public source metadata only; article contents and private case files are not
# distributed with the code. Update this allowlist deliberately when needed.
PAGES = (
    OfficialPage("gm-complaint-ru", "Как подать жалобу на другого игрока", "https://support.grnd.gg/ru/articles/11071809", "ru", ("report.question", "report.complaint", "complaint.other")),
    OfficialPage("gm-complaints-ru", "Жалобы на игроков", "https://support.grnd.gg/ru/articles/11071798", "ru", ("report.question", "report.complaint", "complaint.other")),
    OfficialPage("gm-appeal-ru", "Обжалование санкций", "https://support.grnd.gg/ru/articles/11071819", "ru", ("report.question", "complaint.admin", "complaint.other")),
    OfficialPage("gm-appeal-process-ru", "Процесс подачи апелляции", "https://support.grnd.gg/ru/articles/11071824", "ru", ("report.question", "complaint.admin", "complaint.other")),
    OfficialPage("gm-account-ru", "Как восстановить доступ к своему аккаунту", "https://support.grnd.gg/ru/articles/11029944", "ru", ("report.question", "report.account")),
    OfficialPage("gm-security-ru", "Рекомендации по защите аккаунта", "https://support.grnd.gg/ru/articles/11029952", "ru", ("report.question", "report.account")),
    OfficialPage("gm-trade-ru", "Система обмена", "https://support.grnd.gg/ru/articles/11918168", "ru", ("report.question", "report.complaint", "complaint.scam")),
    OfficialPage("gm-help-ru", "Система помощи игрокам", "https://support.grnd.gg/ru/articles/12342952", "ru", ("report.question", "report.help")),
    OfficialPage("gm-server-ru", "Не могу зайти на сервер", "https://support.grnd.gg/ru/articles/12802228", "ru", ("report.question", "report.help", "report.account")),
    OfficialPage("gm-complaint-en", "How to Report a Rule Violation", "https://support.grnd.gg/en/articles/11163867", "en", ("report.question", "report.complaint", "complaint.other")),
    OfficialPage("gm-complaints-en", "Complaints About Players", "https://support.grnd.gg/en/articles/11163863", "en", ("report.question", "report.complaint", "complaint.other")),
    OfficialPage("gm-appeal-en", "Sanctions Appeal", "https://support.grnd.gg/en/articles/11163870", "en", ("report.question", "complaint.admin", "complaint.other")),
)
MAX_PAGE_BYTES = 2_000_000
VOID_TAGS = frozenset({"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"})
BLOCKED_TAGS = frozenset({"script", "style", "nav", "header", "footer", "form", "button", "svg", "noscript"})
TEXT_TAGS = frozenset({"h1", "h2", "h3", "h4", "p", "li"})


def allowed_url(url: str) -> bool:
    try:
        parsed = urlsplit(url)
        return bool(
            parsed.scheme == "https" and parsed.hostname == "support.grnd.gg"
            and parsed.port in (None, 443) and parsed.username is None and parsed.password is None
            and re.match(r"^/(?:ru|en)/articles/\d+(?:-|$)", parsed.path)
            and not parsed.query and not parsed.fragment
        )
    except (ValueError, TypeError):
        return False


class OfficialRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not allowed_url(newurl):
            raise ValueError("Перенаправление вне разрешённого справочного центра")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def download_html(url: str) -> str:
    if not allowed_url(url):
        raise ValueError("Адрес не входит в разрешённый справочный центр")
    request = Request(url, headers={"User-Agent": "GrandMobileSupportCopilot/1.0", "Accept": "text/html"}, method="GET")
    with build_opener(OfficialRedirects()).open(request, timeout=15) as response:
        if not allowed_url(response.geturl()):
            raise ValueError("Неожиданный конечный адрес статьи")
        if response.headers.get_content_type() not in {"text/html", "application/xhtml+xml"}:
            raise ValueError("Сервер вернул не HTML-страницу")
        body = response.read(MAX_PAGE_BYTES + 1)
        if len(body) > MAX_PAGE_BYTES:
            raise ValueError("Страница слишком большая")
        charset = response.headers.get_content_charset() or "utf-8"
        try:
            return body.decode(charset, errors="strict")
        except (LookupError, UnicodeError) as exc:
            raise ValueError("Неподдерживаемая кодировка страницы") from exc


class ArticleParser(HTMLParser):
    """Extract visible paragraphs from article/main; ignore scripts and nav."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.scope: int | None = None
        self.blocked: list[int] = []
        self.captures: list[tuple[str, int, list[str]]] = []
        self.lines: list[str] = []
        self.seen: set[str] = set()
        self.after_related = False

    def handle_starttag(self, tag: str, attrs) -> None:
        tag = tag.lower()
        if tag in VOID_TAGS:
            if tag == "br" and not self.blocked:
                for _, _, chunks in self.captures:
                    chunks.append(" ")
            return
        self.depth += 1
        if self.scope is None and tag in {"main", "article"}:
            self.scope = self.depth
        if self.scope is not None and tag in BLOCKED_TAGS:
            self.blocked.append(self.depth)
        if self.scope is not None and not self.blocked and not self.after_related and tag in TEXT_TAGS:
            self.captures.append((tag, self.depth, []))

    def handle_data(self, data: str) -> None:
        if self.scope is not None and not self.blocked and not self.after_related:
            for _, _, chunks in self.captures:
                chunks.append(data)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in VOID_TAGS:
            return
        remaining: list[tuple[str, int, list[str]]] = []
        for capture_tag, depth, chunks in self.captures:
            if depth == self.depth and capture_tag == tag:
                value = re.sub(r"\s+", " ", "".join(chunks)).strip()
                if value.casefold() in {"другие статьи по теме", "related articles", "нашли ответ на свой вопрос?", "did this answer your question?"}:
                    self.after_related = True
                elif value and value not in self.seen and not self.after_related:
                    self.lines.append(value)
                    self.seen.add(value)
            else:
                remaining.append((capture_tag, depth, chunks))
        self.captures = remaining
        if self.blocked and self.blocked[-1] == self.depth:
            self.blocked.pop()
        if self.scope == self.depth and tag in {"main", "article"}:
            self.scope = None
        self.depth = max(0, self.depth - 1)


def extract_article(html: str) -> str:
    parser = ArticleParser()
    parser.feed(html)
    parser.close()
    text = "\n".join(parser.lines).strip()
    if len(text) < 40:
        raise ValueError("Не удалось надёжно извлечь текст статьи: проверьте страницу вручную")
    return text


def build_draft(fetch=download_html, pages=PAGES) -> dict:
    articles = []
    errors = []
    fetched_at = datetime.now(timezone.utc).isoformat()
    for page in pages:
        try:
            if not allowed_url(page.url):
                raise ValueError("Недопустимый адрес")
            text = extract_article(fetch(page.url))
            articles.append({
                "id": page.article_id, "title": page.title, "text": text,
                "categories": list(page.categories), "source_url": page.url,
                "language": page.language, "fetched_at": fetched_at, "approved": False,
            })
        except (OSError, HTTPError, URLError, ValueError) as exc:
            # Do not include any local paths or private ticket text in errors.
            errors.append({"id": page.article_id, "error": type(exc).__name__})
    return {"articles": articles, "fetch_errors": errors, "review_required": True}


def write_new_file(path: str | Path, data: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    fd = os.open(path, flags, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as out:
            json.dump(data, out, ensure_ascii=False, indent=2)
            out.write("\n")
    except BaseException:
        # fdopen owns the descriptor once successful; remove only the partial
        # file this function itself created, never an existing destination.
        try:
            path.unlink()
        except OSError:
            pass
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description="Загрузить официальные справочные страницы для приватной ручной проверки")
    parser.add_argument("--download", action="store_true", required=True, help="Явно разрешить HTTPS-запросы только к support.grnd.gg")
    parser.add_argument("--out", required=True, help="Новый приватный JSON-файл; существующий файл не перезаписывается")
    args = parser.parse_args()
    data = build_draft()
    if not data["articles"]:
        print("Не удалось загрузить ни одной статьи. Проверьте доступ к support.grnd.gg; файл не создан.")
        return 1
    try:
        write_new_file(args.out, data)
    except OSError as exc:
        print(f"Не удалось создать новый файл: {exc}")
        return 1
    print(f"Загружено статей: {len(data['articles'])}; ошибок: {len(data['fetch_errors'])}.")
    print("Все статьи выключены: проверьте актуальность, права и содержание, затем отметьте approved: true вручную.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
