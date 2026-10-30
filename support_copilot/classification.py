"""Taxonomy-driven, multilingual heuristic classification and safety signals."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any

from .rp_terms import mentioned_term
from .text import mentions_abuse_shorthand, negates_abuse, normalize, stems, words

# Intents are deliberately broader than the few examples in the supplied
# taxonomy. They are only a baseline until labeled data is available.
INTENTS: dict[str, tuple[str, ...]] = {
    "insult": ("оскорб", "обозва", "матер", "токсич", "унижа", "расиз", "расист", "insult", "toxic", "racis", "haqorat", "ҳақорат", "қорла", "қорлық", "insultó", "insultou"),
    "cheat": ("чит", "читер", "аим", "aimbot", "cheat", "wallhack", "speedhack", "спидхак", "софт", "читерлік", "firibgar dastur"),
    "dm": ("убил", "убива", "убий", "стреля", "урон", "дм", "дмит", "дмят", "deathmatch", "killed", "kill", "атаковал", "напал", "өлтір", "oldir", "o'ldir", "mató", "matou"),
    "scam": ("мошенн", "обман", "скам", "украл", "кидал", "кинул", "вымога", "scam", "fraud", "stole", "алда", "алаяқ", "firib", "aldadi", "estafa", "golpe"),
    "rmt_ads": ("реклам", "рмт", "rmt", "advertis", "reklama", "жарнама", "vender cuenta", "sell account"),
    "admin": ("админ", "admin", "әкімші", "administrator", "administrador"),
    "payment": ("донат", "платеж", "оплат", "оплач", "пополни", "транзакц", "списал", "списани", "гк", "payment", "paid", "purchase", "charged", "credit card", "to'lov", "tolov", "тўлов", "пул ечил", "төлем", "төлед", "pul yechildi", "pago", "pagué", "pagamento", "paguei"),
    "account": ("аккаунт", "акк", "учетн", "профил", "парол", "account", "password", "akkaunt", "hisob", "ҳисоб", "тіркелг", "есептік", "құпиясөз", "cuenta", "conta", "senha"),
    "account_hack": ("взлом", "угнал", "угнали", "украл", "украден", "hacked", "hijack", "stolen", "stole", "hackeado", "hackeada", "buzib", "buzil", "бузиб", "бузил", "o'g'irl", "ўғирла", "ұрла", "бұз"),
    "access_loss": ("не могу войти", "не могу зайти", "нет доступа", "потерял доступ", "не заходит в аккаунт", "не входит в аккаунт", "can't log in", "cannot log in", "lost access", "no puedo entrar", "não consigo entrar", "kira olmay", "кіре алмай"),
    "ban": ("забан", "разбан", "заблокир", "блокиров", "апелляц", "аппеляц", "бұғат", "баннан", "banned", "unban", "appeal", "bloqueado", "bloqueada", "bloqueio", "bloklangan"),
    "help": ("застря", "текстур", "завис", "вылет", "баг", "ошибк", "телепорт", "выбрат", "stuck", "bug", "teleport", "glitch", "qotib", "yordam", "көмек", "тұрып", "atascado", "preso"),
    "question": ("как", "где", "почему", "зачем", "сколько", "how", "where", "why", "қалай", "қайда", "неге", "qanday", "qayer", "nega", "cómo", "dónde", "como", "onde"),
    "rule_question": ("правил", "правило", "rule", "ереже", "qoida", "қоида", "regla", "regra"),
    "real_threat": ("реальной жизни", "в реале", "real life", "настоящей жизни", "докс", "doxx", "hayotda", "өмірде"),
    "threat": ("угрож", "угроз", "threat", "қорқыт", "tahdid", "amenaza", "ameaça"),
    "mass": ("у всех", "массов", "весь сервер", "все игроки", "everyone", "all players", "барлық ойыншы", "barcha o'yinchi"),
    "property": ("имущество", "машин", "авто", "деньг", "дом", "валют", "property", "car", "money", "мүлк", "ақша", "mashina", "pul"),
    "lost": ("пропал", "исчез", "потеря", "не приш", "не получил", "missing", "disappear", "lost", "жоғал", "yo'qol", "kelmadi"),
}


def _pattern_matches(text: str, tokens: list[str], pattern: str) -> bool:
    pattern = normalize(pattern)
    if " " in pattern or "'" in pattern:
        return pattern in text
    return any(token.startswith(pattern) for token in tokens)


def find_signals(text: str, lang: str) -> set[str]:
    value = normalize(text, lang)
    tokens = words(value)
    found = {name for name, patterns in INTENTS.items() if any(_pattern_matches(value, tokens, p) for p in patterns)}
    if mentions_abuse_shorthand(value, lang):
        found.add("insult")
    if negates_abuse(value, lang):
        found.discard("insult")
    term = mentioned_term(text, lang)
    if term in {"DM", "MASS DM", "MASS DM GZ", "DB", "SK", "MASS SK", "RK", "TK"}:
        found.add("dm")
    # An appeal can concern a mute, warning or other penalty, not just a ban.
    # Require both an appeal/disagreement and a sanction; do not infer one from
    # "наказание" alone or from a routine request to punish someone else.
    appeal = r"(?:не\s+соглас\w*|несоглас\w*|обжал\w*|оспор\w*|апелляц\w*|appeal\w*|disagree\w*|unfair\w*)"
    sanction = r"(?:наказан\w*|санкц\w*|мут\w*|варн\w*|джайл\w*|mute\w*|warn\w*|jail\w*|penalt\w*|punish\w*)"
    if re.search(rf"{appeal}.{{0,60}}{sanction}|{sanction}.{{0,60}}{appeal}", value):
        found.add("ban")
    # Avoid treating "в банке" as a ban. Exact short terms are separate.
    if any(t in {"бан", "бане", "бана", "баном", "ban", "banim", "блокировка"} for t in tokens):
        found.add("ban")
    if ("account" in found and "account_hack" in found) or "access_loss" in found:
        found.add("compromise")
    elif "account_hack" in found and any(token.startswith(("взлома", "hacked")) for token in tokens):
        # "Меня взломали" is a sufficiently strong loss-of-account signal;
        # "угнали" alone could instead refer to an in-game vehicle.
        found.add("compromise")
    if "lost" in found and "property" in found:
        found.add("missing_property")
    return found


@dataclass(frozen=True)
class Classification:
    category: str
    confidence: float
    signals: frozenset[str]
    related_complaint: str | None


def _prototype_similarity(text_terms: set[str], category: dict[str, Any]) -> float:
    samples: list[str] = [str(category.get("title", ""))]
    examples = category.get("examples", [])
    if isinstance(examples, list):
        samples += [str(x) for x in examples]
    best = 0.0
    for sample in samples:
        terms = stems(sample)
        if terms and text_terms:
            best = max(best, len(terms & text_terms) / math.sqrt(len(terms) * len(text_terms)))
    return best


def classify(kind: str, text: str, lang: str, categories: dict[str, dict[str, Any]]) -> Classification:
    q = normalize(text, lang)
    tokens = words(q)
    signals = find_signals(text, lang)
    terms = stems(text, lang)
    candidates = {code: category for code, category in categories.items() if category.get("kind") == kind}
    scores = {code: 2.2 * _prototype_similarity(terms, category) for code, category in candidates.items()}

    complaint_intents = {
        "complaint.insult": "insult",
        "complaint.cheat": "cheat",
        "complaint.dm": "dm",
        "complaint.scam": "scam",
        "complaint.rmt_ads": "rmt_ads",
    }
    for code, signal in complaint_intents.items():
        if code in scores and signal in signals:
            scores[code] += 3.0
    if "complaint.admin" in scores and "admin" in signals and ("ban" in signals or any(p in q for p in ("жалоб", "пожаловать", "оскорб", "abuse", "complain", "шағым"))):
        scores["complaint.admin"] += 3.4
    if "complaint.rmt_ads" in scores and any(p in q for p in ("за реал", "за реальные деньги", "real money", "sell account", "sotaman")):
        scores["complaint.rmt_ads"] += 3.0

    related: str | None = None
    if "admin" in signals and ("ban" in signals or any(p in q for p in ("жалоб", "пожаловать", "обжал", "complain", "appeal", "шағым"))):
        if "complaint.admin" in categories:
            related = "complaint.admin"
    if related is None:
        for code, signal in complaint_intents.items():
            if signal in signals and code in categories:
                related = code
                break

    if kind == "report":
        if "report.payment" in scores and "payment" in signals:
            scores["report.payment"] += 5.0
        if "report.account" in scores and ({"account", "compromise", "missing_property"} & signals):
            scores["report.account"] += 4.0
        if "report.complaint" in scores and related:
            scores["report.complaint"] += 3.5
        if "report.help" in scores and "help" in signals:
            scores["report.help"] += 3.0
        if "report.question" in scores and ("question" in signals or "?" in q):
            scores["report.question"] += 1.8
        generic = {"помогите", "помощь", "привет", "ау", "админ", "help", "hello", "hi", "yordam", "salom", "көмек", "сәлем"}
        if "report.offtopic" in scores and (not tokens or (len(tokens) <= 2 and all(t in generic for t in tokens))):
            scores["report.offtopic"] += 4.0

    ordered = sorted(scores.items(), key=lambda pair: pair[1], reverse=True)
    best_code, best_score = ordered[0]
    if best_score < 0.45:
        fallback = "complaint.other" if kind == "complaint" else "report.question"
        best_code = fallback if fallback in candidates else best_code
        return Classification(best_code, 0.25, frozenset(signals), related)
    second = ordered[1][1] if len(ordered) > 1 else 0.0
    gap = max(0.0, best_score - second)
    # This is a ranking heuristic, NOT a calibrated probability.
    confidence = round(min(0.9, 0.45 + min(best_score, 5.0) * 0.055 + min(gap, 3.0) * 0.035), 2)
    return Classification(best_code, confidence, frozenset(signals), related)


def priority_for(kind: str, category: str, signals: frozenset[str], has_evidence: bool) -> str:
    if "payment" in signals or "compromise" in signals or ("mass" in signals and "help" in signals) or ({"real_threat", "threat"} <= signals):
        return "p0"
    if "cheat" in signals or "rmt_ads" in signals or ("scam" in signals and "property" in signals):
        return "p1"
    if kind == "complaint" and has_evidence:
        return "p1"
    if kind == "complaint" and not has_evidence:
        return "p3"
    if category == "report.question":
        return "p2" if "rule_question" in signals else "p3"
    if category in {"report.offtopic", "complaint.invalid"}:
        return "p3"
    return "p2"
