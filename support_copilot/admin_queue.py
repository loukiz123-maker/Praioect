"""Private, local review queue for the administrator dashboard.

Only player-side text, limited metadata, and human feedback are stored.
Receipts are random capabilities; only their SHA-256 hashes are kept on disk.
Attachment contents, reporter hashes, exception messages, and HTTP logs are
not stored. Player text and drafts may themselves contain sensitive data.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import sqlite3
import stat
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, BinaryIO

from .service import InputError, _positive_attachment, validate_ticket

RECEIPT_RE = re.compile(r"^[0-9a-f]{64}$")
REVIEW_ID_RE = re.compile(r"^[0-9a-f]{32}$")
KEY_RE = re.compile(r"^[A-Za-z0-9._~-]{24,200}$")
STATUSES = {"waiting", "in_progress", "escalated", "resolved"}
SOURCES = {"needs_human", "failure", "manual"}
MAX_DRAFT_CHARS = 100_000


class QueueError(Exception):
    """A review cannot be safely created or changed."""


class QueueFull(QueueError):
    pass


class QueueConflict(QueueError):
    pass


class QueueNotFound(QueueError):
    pass


def new_receipt() -> str:
    return secrets.token_hex(32)


def validate_receipt(receipt: Any) -> str:
    if not isinstance(receipt, str) or not RECEIPT_RE.fullmatch(receipt):
        raise InputError("Неверный идентификатор проверки")
    return receipt


def load_admin_key(path: str | Path, override: str | None = None) -> str:
    """Read or create a random key locally; never put it in logs or URLs."""
    if override is not None:
        if not KEY_RE.fullmatch(override):
            raise ValueError("Ключ администратора должен содержать 24–200 символов ASCII без пробелов")
        return override
    key_path = Path(path)
    key_path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    if key_path.is_symlink():
        raise ValueError("Файл ключа администратора не должен быть ссылкой")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(str(key_path), flags, 0o600)
    except FileExistsError:
        pass
    else:
        try:
            with os.fdopen(fd, "w", encoding="ascii") as stream:
                stream.write(secrets.token_urlsafe(32) + "\n")
                stream.flush()
                os.fsync(stream.fileno())
        except BaseException:
            try:
                key_path.unlink()
            except OSError:
                pass
            raise
    read_flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(str(key_path), read_flags)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise ValueError("Файл ключа администратора должен быть обычным файлом")
        with os.fdopen(fd, "r", encoding="ascii") as stream:
            fd = -1
            key = stream.read(202).strip()
    finally:
        if fd >= 0:
            os.close(fd)
    if not KEY_RE.fullmatch(key):
        raise ValueError("Файл ключа администратора повреждён или содержит недопустимый ключ")
    # On Windows this is limited by OS ACL semantics; see README.
    os.chmod(key_path, 0o600)
    return key


def _short_string(value: Any, limit: int) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()[:limit]
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)[:limit]
    return None


def _snapshot(ticket: Any) -> tuple[str, str, dict[str, Any], str]:
    kind, messages = validate_ticket(ticket)
    text = "\n\n".join(message.get("text", "") for message in messages)
    metadata = {
        "attachments_indicated": _positive_attachment(ticket.get("images_count"))
        or any(_positive_attachment(message.get("attachments")) for message in messages),
        "server": _short_string(ticket.get("server"), 128) or _short_string(ticket.get("region"), 128),
        "reported_nick": _short_string(ticket.get("reported_nick"), 64),
        "rule_refs_raw": _short_string(ticket.get("rule_refs_raw"), 512),
    }
    # A receipt cannot silently be reused for a different ticket.
    canonical = json.dumps([kind, text, metadata], ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    try:
        digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    except UnicodeError as exc:
        raise InputError("Текст обращения должен быть корректным Unicode") from exc
    return kind, text, metadata, digest


def _draft(value: Any, *, required: bool = False) -> str:
    if not isinstance(value, str) or len(value) > MAX_DRAFT_CHARS:
        raise InputError("Черновик должен быть строкой длиной не более 100000 символов")
    try:
        value.encode("utf-8")
    except UnicodeError as exc:
        raise InputError("Черновик должен быть корректным Unicode") from exc
    if required and not value.strip():
        raise InputError("Добавьте текст ответа перед завершением проверки")
    return value


class AdminQueue:
    """SQLite-backed queue, shared by browser sessions and server restarts."""

    def __init__(self, path: str | Path, *, retention_days: int = 14, max_items: int = 1000):
        self.path = Path(path)
        self.retention_seconds = retention_days * 24 * 60 * 60
        self.max_items = max_items
        self.path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
        if self.path.is_symlink():
            raise ValueError("Файл очереди не должен быть ссылкой")
        fd = os.open(str(self.path), os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0), 0o600)
        try:
            if not stat.S_ISREG(os.fstat(fd).st_mode):
                raise ValueError("Файл очереди должен быть обычным файлом")
        finally:
            os.close(fd)
        os.chmod(self.path, 0o600)
        with self._connect() as conn:
            conn.execute("PRAGMA journal_mode = DELETE")
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS reviews (
                    id TEXT PRIMARY KEY,
                    receipt_hash TEXT NOT NULL UNIQUE,
                    ticket_hash TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    source TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    message TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    result_json TEXT,
                    operator_draft TEXT NOT NULL,
                    admin_draft TEXT,
                    version INTEGER NOT NULL DEFAULT 1
                );
                CREATE INDEX IF NOT EXISTS reviews_created_at ON reviews(created_at);
                CREATE TABLE IF NOT EXISTS admin_feedback (
                    review_id TEXT PRIMARY KEY REFERENCES reviews(id) ON DELETE CASCADE,
                    review_version INTEGER NOT NULL,
                    recorded_at INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    assistant_draft TEXT,
                    operator_draft TEXT NOT NULL,
                    corrected_draft TEXT NOT NULL
                );
                """
            )

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(str(self.path), timeout=5, isolation_level=None)
        try:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("PRAGMA secure_delete = ON")
            yield connection
            if connection.in_transaction:
                connection.commit()
        except BaseException:
            if connection.in_transaction:
                connection.rollback()
            raise
        finally:
            connection.close()

    def _cleanup(self, conn: sqlite3.Connection) -> None:
        conn.execute("DELETE FROM reviews WHERE created_at < ?", (int(time.time()) - self.retention_seconds,))

    def enqueue(
        self, ticket: Any, receipt: str, source: str, *, result: dict[str, Any] | None = None,
        draft: str | None = None, update_draft: bool = False,
    ) -> dict[str, Any]:
        validate_receipt(receipt)
        if not isinstance(source, str) or source not in SOURCES:
            raise InputError("Неверная причина передачи администратору")
        kind, text, metadata, ticket_hash = _snapshot(ticket)
        if draft is None:
            draft = result["draft_reply"]["text"] if result is not None else ""
        draft = _draft(draft)
        result_json = json.dumps(result, ensure_ascii=False, separators=(",", ":")) if result is not None else None
        # Catch unpaired surrogates before they can reach SQLite's encoder.
        if result_json is not None:
            try:
                result_json.encode("utf-8")
            except UnicodeError as exc:
                raise InputError("Результат должен быть корректным Unicode") from exc
        hashed = hashlib.sha256(receipt.encode("ascii")).hexdigest()
        now = int(time.time())
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            self._cleanup(conn)
            existing = conn.execute("SELECT * FROM reviews WHERE receipt_hash = ?", (hashed,)).fetchone()
            if existing:
                if existing["ticket_hash"] != ticket_hash:
                    raise QueueConflict("Этот идентификатор уже связан с другим обращением")
                if update_draft and existing["operator_draft"] != draft:
                    if existing["status"] == "resolved":
                        raise QueueConflict("Проверка уже завершена; черновик не изменён")
                    conn.execute(
                        "UPDATE reviews SET operator_draft = ?, updated_at = ?, version = version + 1 WHERE id = ?",
                        (draft, now, existing["id"]),
                    )
                conn.commit()
                return {"id": existing["id"], "status": existing["status"], "created": False}
            if conn.execute("SELECT COUNT(*) FROM reviews").fetchone()[0] >= self.max_items:
                raise QueueFull("Очередь администратора заполнена")
            review_id = secrets.token_hex(16)
            conn.execute(
                """INSERT INTO reviews
                   (id, receipt_hash, ticket_hash, created_at, updated_at, status, source,
                    kind, message, metadata_json, result_json, operator_draft)
                   VALUES (?, ?, ?, ?, ?, 'waiting', ?, ?, ?, ?, ?, ?)""",
                (review_id, hashed, ticket_hash, now, now, source, kind, text,
                 json.dumps(metadata, ensure_ascii=False), result_json, draft),
            )
            conn.commit()
            return {"id": review_id, "status": "waiting", "created": True}

    def status(self, receipt: str) -> dict[str, Any]:
        validate_receipt(receipt)
        hashed = hashlib.sha256(receipt.encode("ascii")).hexdigest()
        with self._connect() as conn:
            self._cleanup(conn)
            row = conn.execute("SELECT status, admin_draft FROM reviews WHERE receipt_hash = ?", (hashed,)).fetchone()
        if row is None:
            raise QueueNotFound("Проверка не найдена")
        return {"status": row["status"], "reply": row["admin_draft"] if row["status"] == "resolved" else None}

    def list_reviews(self, *, view: str = "active", offset: int = 0, limit: int = 50) -> dict[str, Any]:
        where = {
            "active": "WHERE status IN ('waiting', 'in_progress', 'escalated')",
            "escalated": "WHERE status = 'escalated'",
            "resolved": "WHERE status = 'resolved'",
            "all": "",
        }
        if not isinstance(view, str) or view not in where or not isinstance(offset, int) or isinstance(offset, bool) or not 0 <= offset <= 2**63 - 1:
            raise InputError("Неверные параметры списка обращений")
        if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 100:
            raise InputError("Неверный размер страницы")
        with self._connect() as conn:
            self._cleanup(conn)
            rows = conn.execute(
                """SELECT id, created_at, updated_at, status, source, kind,
                          substr(message, 1, 180) AS preview, result_json, version
                   FROM reviews """ + where[view] + """ ORDER BY
                       CASE status WHEN 'escalated' THEN 0 WHEN 'waiting' THEN 1 WHEN 'in_progress' THEN 2 ELSE 3 END,
                       updated_at DESC, id DESC LIMIT ? OFFSET ?""", (limit, offset),
            ).fetchall()
            counts = {status: 0 for status in STATUSES}
            for row in conn.execute("SELECT status, COUNT(*) AS count FROM reviews GROUP BY status"):
                if row["status"] in counts:
                    counts[row["status"]] = row["count"]
            feedback_count = conn.execute("SELECT COUNT(*) FROM admin_feedback").fetchone()[0]
        items = []
        for row in rows:
            result = json.loads(row["result_json"]) if row["result_json"] else None
            items.append({
                "id": row["id"], "created_at": row["created_at"], "updated_at": row["updated_at"],
                "status": row["status"], "source": row["source"], "kind": row["kind"],
                "preview": row["preview"], "version": row["version"],
                "category": result.get("category") if result else None,
                "priority": result.get("priority") if result else None,
            })
        total = (counts["waiting"] + counts["in_progress"] + counts["escalated"] if view == "active"
                 else counts["escalated"] if view == "escalated"
                 else counts["resolved"] if view == "resolved" else sum(counts.values()))
        return {
            "items": items, "counts": counts, "feedback_count": feedback_count,
            "limit": limit, "offset": offset, "filtered_total": total,
        }

    def get(self, review_id: str) -> dict[str, Any]:
        if not REVIEW_ID_RE.fullmatch(review_id):
            raise QueueNotFound("Обращение не найдено")
        with self._connect() as conn:
            self._cleanup(conn)
            row = conn.execute("SELECT * FROM reviews WHERE id = ?", (review_id,)).fetchone()
        if row is None:
            raise QueueNotFound("Обращение не найдено")
        return {
            "id": row["id"], "created_at": row["created_at"], "updated_at": row["updated_at"],
            "status": row["status"], "source": row["source"], "kind": row["kind"],
            "message": row["message"], "metadata": json.loads(row["metadata_json"]),
            "result": json.loads(row["result_json"]) if row["result_json"] else None,
            "operator_draft": row["operator_draft"], "admin_draft": row["admin_draft"],
            "version": row["version"],
        }

    def update(self, review_id: str, version: Any, status: Any, draft: Any) -> dict[str, Any]:
        if not REVIEW_ID_RE.fullmatch(review_id):
            raise QueueNotFound("Обращение не найдено")
        if not isinstance(version, int) or isinstance(version, bool) or version < 1:
            raise InputError("Не указана версия обращения")
        if not isinstance(status, str) or status not in STATUSES:
            raise InputError("Неверный статус обращения")
        draft = _draft(draft, required=status == "resolved")
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            self._cleanup(conn)
            row = conn.execute("SELECT * FROM reviews WHERE id = ?", (review_id,)).fetchone()
            if row is None:
                raise QueueNotFound("Обращение не найдено")
            if row["version"] != version:
                raise QueueConflict("Обращение изменилось. Обновите данные и проверьте их заново")
            previous = row["admin_draft"] if row["admin_draft"] is not None else row["operator_draft"]
            has_feedback = conn.execute("SELECT 1 FROM admin_feedback WHERE review_id = ?", (review_id,)).fetchone()
            now = int(time.time())
            conn.execute(
                "UPDATE reviews SET status = ?, admin_draft = ?, updated_at = ?, version = version + 1 WHERE id = ?",
                (status, draft, now, review_id),
            )
            # Keep one current signal per review, and commit it atomically with
            # the human action. Drafts are explicitly marked as unapproved.
            if draft != previous or status == "resolved" or has_feedback:
                result = json.loads(row["result_json"]) if row["result_json"] else None
                assistant_draft = result["draft_reply"]["text"] if result is not None else None
                conn.execute(
                    """INSERT INTO admin_feedback
                       (review_id, review_version, recorded_at, status, assistant_draft,
                        operator_draft, corrected_draft)
                       VALUES (?, ?, ?, ?, ?, ?, ?)
                       ON CONFLICT(review_id) DO UPDATE SET
                           review_version = excluded.review_version,
                           recorded_at = excluded.recorded_at,
                           status = excluded.status,
                           assistant_draft = excluded.assistant_draft,
                           operator_draft = excluded.operator_draft,
                           corrected_draft = excluded.corrected_draft""",
                    (review_id, version + 1, now, status, assistant_draft, row["operator_draft"], draft),
                )
            conn.commit()
        return self.get(review_id)

    def write_feedback(self, stream: BinaryIO) -> int:
        """Write a consistent, private JSONL export of current human feedback.

        Unfinished and stale edits are included but explicitly marked; they
        are not equivalent to approved training examples. No receipts,
        reporter hashes, administrator messages, or attachment content leave
        the queue. Player text and drafts may still contain personal data.
        """
        count = 0
        with self._connect() as conn:
            self._cleanup(conn)
            conn.execute("BEGIN")
            rows = conn.execute(
                """SELECT f.*, r.kind, r.source, r.message, r.metadata_json, r.result_json,
                          r.version AS current_version, r.status AS current_status
                   FROM admin_feedback AS f JOIN reviews AS r ON r.id = f.review_id
                   ORDER BY f.review_id"""
            )
            for row in rows:
                metadata = json.loads(row["metadata_json"])
                result = json.loads(row["result_json"]) if row["result_json"] else None
                original = row["assistant_draft"]
                corrected = row["corrected_draft"]
                is_current = row["review_version"] == row["current_version"]
                approved = is_current and row["status"] == "resolved" and row["current_status"] == "resolved"
                record = {
                    "schema": "support_copilot.admin_feedback.v1",
                    "review_id": row["review_id"],
                    "review_version": row["review_version"],
                    "recorded_at": row["recorded_at"],
                    "status": row["status"],
                    "is_current": is_current,
                    "approved": approved,
                    "feedback_type": "human_reply" if original is None else "unchanged" if original == corrected else "edited",
                    "source": row["source"],
                    "ticket": {
                        "kind": row["kind"],
                        "text": row["message"],
                        "server": metadata.get("server"),
                        "attachments_indicated": bool(metadata.get("attachments_indicated")),
                    },
                    "assistant": {
                        "lang": result["lang"], "category": result["category"],
                        "priority": result["priority"], "draft": original,
                    } if result is not None else None,
                    "operator_draft": row["operator_draft"],
                    "admin_draft": corrected,
                }
                stream.write((json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8"))
                count += 1
        return count

    def delete(self, review_id: str, version: Any) -> None:
        if not REVIEW_ID_RE.fullmatch(review_id):
            raise QueueNotFound("Обращение не найдено")
        if not isinstance(version, int) or isinstance(version, bool) or version < 1:
            raise InputError("Не указана версия обращения")
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            self._cleanup(conn)
            row = conn.execute("SELECT version FROM reviews WHERE id = ?", (review_id,)).fetchone()
            if row is None:
                raise QueueNotFound("Обращение не найдено")
            if row["version"] != version:
                raise QueueConflict("Обращение изменилось. Обновите данные перед удалением")
            conn.execute("DELETE FROM reviews WHERE id = ?", (review_id,))
            conn.commit()
