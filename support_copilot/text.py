"""Small, dependency-free text utilities. These are heuristics, not a language model."""

from __future__ import annotations

import re
import unicodedata
from collections import Counter
from typing import Iterable

SUPPORTED_LANGUAGES = frozenset({"ru", "kk", "uz", "en", "es", "pt"})

# The game replaces some Kazakh letters with visually similar CP1251 characters.
# Do not apply this to Uzbek, where e.g. ў is an ordinary letter.
KAZAKH_GAME_CHARS = str.maketrans({"ќ": "қ", "ґ": "ғ", "ѕ": "ң", "є": "ә", "ј": "ө", "ў": "ұ", "ї": "ү"})

WORD_RE = re.compile(r"[^\W_]+(?:['’‘ʻ][^\W_]+)?", re.UNICODE)

LANGUAGE_WORDS = {
    "ru": {"здравствуйте", "привет", "помогите", "помощь", "меня", "мне", "игрок", "игры", "игре", "аккаунт", "пожалуйста", "оскорбил", "застрял", "оплата", "деньги", "как", "почему", "что", "где", "жалоба", "взломали"},
    "kk": {"сәлем", "сәлеметсіз", "мені", "менің", "маған", "көмек", "көмектесіңіз", "ойын", "ойыншы", "қорлады", "қорлап", "шағым", "ақша", "төлем", "шот", "тіркелгі", "бұзды", "қайтару", "неге", "қалай", "және", "беріңіз", "мұны", "мұнда", "құпия", "ұрлады", "ұры"},
    "uz": {"salom", "meni", "mening", "menga", "yordam", "iltimos", "hisob", "hisobim", "akkaunt", "oyin", "o'yin", "o'yinchi", "haqorat", "qildi", "qilmoqda", "pul", "to'lov", "tolov", "qaytar", "qanday", "nega", "мени", "менинг", "ёрдам", "илтимос", "ҳақорат", "ҳисоб", "тўлов", "ўйин"},
    "en": {"hello", "hi", "help", "please", "player", "account", "my", "me", "the", "and", "was", "insulted", "stuck", "payment", "money", "banned", "cheating", "how", "where", "why", "hacked"},
    "es": {"hola", "ayuda", "jugador", "cuenta", "pago", "gracias", "estoy", "por", "favor", "dinero", "cómo", "dónde", "insultó", "estafa", "bloqueada"},
    "pt": {"olá", "ola", "ajuda", "jogador", "conta", "pagamento", "obrigado", "obrigada", "estou", "favor", "dinheiro", "como", "onde", "insultou", "golpe", "bloqueada", "minha"},
}

# Ignore high-frequency terms when matching a question to rule text. These are
# lexical stop words, not copied ticket or rule data.
STOP_WORDS = {
    "это", "этот", "этого", "как", "что", "где", "когда", "который", "почему", "можно", "ли", "на", "по", "за", "от", "для", "или", "его", "ее", "меня", "мне", "мой", "моя", "мои", "пожалуйста", "здравствуйте", "привет", "игрок", "игрока", "игроков", "игре", "игры", "игра", "правила", "правило", "правил", "пункт", "сервер", "сервере", "запрещено", "разрешено", "ситуации", "любые", "любое", "помогите", "жалоба", "жалобу", "репорт", "нарушение", "нарушил", "нарушения", "стороны", "только", "данное", "своих", "своего", "если", "через", "были", "после", "без", "под", "уже", "есть", "себя", "всем", "всех", "the", "and", "for", "this", "that", "with", "you", "your", "player", "game", "please", "hello", "help", "мені", "менің", "маған", "ойыншы", "ойын", "сәлем", "менинг", "meni", "mening", "menga", "iltimos", "yordam", "salom", "oyin", "o'yin",
}


def normalize(text: str, lang: str | None = None) -> str:
    """Normalize for matching, keeping the original text for output."""
    value = unicodedata.normalize("NFKC", str(text)).casefold()
    value = value.replace("ё", "е").replace("’", "'").replace("‘", "'").replace("ʻ", "'").replace("`", "'")
    if lang == "kk":
        value = value.translate(KAZAKH_GAME_CHARS)
    return value


def words(text: str, lang: str | None = None) -> list[str]:
    return WORD_RE.findall(normalize(text, lang))


def detect_language(text: str, hint: str | None = None) -> str:
    """Guess language from the player's text. A hint is evidence, not proof."""
    value = normalize(text)
    tokens = WORD_RE.findall(value)
    hint = str(hint or "").lower().split("-")[0]
    if not tokens:
        return hint if hint in SUPPORTED_LANGUAGES else "und"

    scores: Counter[str] = Counter()
    for lang, dictionary in LANGUAGE_WORDS.items():
        for token in tokens:
            if token in dictionary:
                scores[lang] += 2.0
    if re.search(r"[а-я]", value):
        scores["ru"] += 1.2
    if re.search(r"[a-z]", value):
        scores["en"] += 0.2
    # These characters are distinctive; қ/ғ alone occur in both languages.
    if re.search(r"[әіңөұүһќґѕєјї]", value):
        scores["kk"] += 4.0
    if re.search(r"[ўҳ]", value) and not re.search(r"[ќґѕєјї]", value):
        scores["uz"] += 4.0
    # Ў is also the game's substitute for Kazakh ұ. Use words and an
    # explicit language hint to resolve some cases without rewriting Uzbek.
    if "ў" in value:
        repaired = value.translate(KAZAKH_GAME_CHARS)
        repaired_tokens = WORD_RE.findall(repaired)
        scores["kk"] += 2.5 * sum(token in LANGUAGE_WORDS["kk"] and token not in tokens for token in repaired_tokens)
        if hint == "kk":
            scores["kk"] += 2.5
    if re.search(r"[қғ]", value):
        scores["kk"] += 0.8
        scores["uz"] += 0.5
    if re.search(r"[o'g']+'(?:yin|z|ri|lov)", value):
        scores["uz"] += 1.0
    if hint in SUPPORTED_LANGUAGES:
        scores[hint] += 1.5
    if not scores:
        return "und"
    best, score = scores.most_common(1)[0]
    return best if score >= 1.0 else "und"


def stems(text: str, lang: str | None = None) -> set[str]:
    """Cheap prefix stemming for recall in Russian and other languages."""
    result: set[str] = set()
    for token in words(text, lang):
        if token in STOP_WORDS or len(token) < 3 or token.isdigit():
            continue
        result.add(token[:6] if len(token) >= 6 else token)
    return result


def contains_any(text: str, patterns: Iterable[str]) -> bool:
    return any(pattern in text for pattern in patterns)
