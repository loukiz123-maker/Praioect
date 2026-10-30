"""Entirely synthetic fixtures; no organizer data is copied into tests."""

import json
from pathlib import Path


def write_fixtures(directory: str) -> tuple[str, str, str]:
    root = Path(directory)
    rules = {
        "rules": [
            {"id": "general", "category": "Общие правила игры", "text": "\n".join([
                "1.4 Игрок отвечает за сохранность аккаунта.",
                "2.1 В игровом чате нельзя оскорблять других людей и их родственников.",
                "2.4 В чате недопустимы расизм и оскорбление религии.",
                "2.6 Нельзя угрожать и публиковать личную информацию.",
                "3.1 Не используйте репорт для спама или запроса телепорта.",
                "3.4 Для жалобы на администратора предусмотрен отдельный раздел.",
                "4.1 Запрещено мошенничество с игровой валютой.",
                "4.2 Запрещено вымогательство игровых ценностей.",
                "5.2 Нельзя использовать стороннее программное обеспечение для преимущества.",
                "5.3 Нельзя прерывать ролевую ситуацию выходом из игры.",
                "5.4 Запрещено убийство жильцам у входа в дом.",
            ])},
            {"id": "complaints", "category": "Правила жалоб", "text": "1.1.2 Жалобы не предназначены для общих вопросов.\n1.2.7 Нельзя оскорблять других в жалобе.\n2.1 Синтетический другой раздел."},
            {"id": "green", "category": "Правила Зелёной Зоны", "text": "1.1 Убийство и нанесение урона запрещены в Зелёной Зоне [Green Zone | GZ].\n2.1 Другой пункт зоны."},
        ]
    }
    categories = [
        ("complaint.insult", "complaint", "Оскорбления", ["2.1", "2.4", "2.6"], ["меня оскорбили в чате"]),
        ("complaint.cheat", "complaint", "Читы", ["5.2"], ["игрок использует читы"]),
        ("complaint.dm", "complaint", "Убийство", ["5.3", "5.4", "GZ"], ["игрок убил меня"]),
        ("complaint.scam", "complaint", "Мошенничество", ["4.1", "4.2"], ["обманул меня"]),
        ("complaint.rmt_ads", "complaint", "Реклама", ["4.1"], ["рекламирует продажу"]),
        ("complaint.admin", "complaint", "Жалоба на администратора", ["3.4"], ["администратор выдал бан"]),
        ("complaint.other", "complaint", "Другое", [], []),
        ("complaint.invalid", "complaint", "Некорректное обращение", ["ЖБ 1.1.2"], ["случайный вопрос"]),
        ("report.question", "report", "Вопрос", [], ["как починить двигатель"]),
        ("report.help", "report", "Помощь", ["3.1"], ["застрял в текстурах"]),
        ("report.complaint", "report", "Жалоба", [], ["меня оскорбляют"]),
        ("report.account", "report", "Аккаунт", ["1.4"], ["взломали аккаунт"]),
        ("report.payment", "report", "Платёж", [], ["не пришел платеж"]),
        ("report.offtopic", "report", "Пустое сообщение", ["3.1"], ["привет"]),
    ]
    taxonomy = {
        "version": "synthetic-test",
        "categories": [{"code": code, "kind": kind, "title": title, "rules": refs, "examples": examples} for code, kind, title, refs, examples in categories],
        "priorities": [{"code": code} for code in ("p0", "p1", "p2", "p3")],
        "needs_human_always": ["report.payment", "report.account", "complaint.admin"],
    }
    knowledge = {"articles": [{"id": "synthetic-1", "title": "Ремонт двигателя", "text": "Чтобы починить двигатель, используйте игровой сервис ремонта.", "categories": ["report.question"]}]}
    paths = [root / "rules.json", root / "taxonomy.json", root / "knowledge.json"]
    for path, obj in zip(paths, (rules, taxonomy, knowledge)):
        path.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
    return tuple(map(str, paths))


def ticket(text: str, kind: str = "complaint", **kwargs: object) -> dict:
    return {"kind": kind, "messages": [{"role": "player", "text": text}], **kwargs}
