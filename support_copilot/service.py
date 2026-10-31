"""The contract-preserving triage pipeline."""

from __future__ import annotations

import re
from typing import Any

from .catalog import Catalog, RuleMatch
from .classification import Classification, classify, priority_for
from .dedup import DuplicateDetector, obvious_spam
from .rp_terms import NamedRule
from .text import SUPPORTED_LANGUAGES, detect_language, normalize

# Allow a sentence-ending period after a reference, but never match a prefix
# of a longer dotted number or a component of an invalid long identifier.
RULE_REF_RE = re.compile(r"(?<![\d.])\d{1,3}(?:\.\d{1,3}){1,4}(?!\d|\.\d)")
NICK_RE = re.compile(r"(?<![\w])([A-Za-z][A-Za-z0-9]{1,24}_[A-Za-z][A-Za-z0-9]{1,24})(?![\w])")
SERVER_RE = re.compile(r"(?i)\b(?:сервер(?:е|а)?|server|сервері|serveri)\s*[:№#-]?\s*(\d{1,3})\b")
EVIDENCE_RE = re.compile(
    r"(?<!\w)(?:скрин\w*|заскрин\w*|screenshot\w*|screen\s*shot\w*|skrin\w*|"
    r"видео\w*|video\w*|запись|записи|recording\w*|"
    r"доказательств\w*|пруф\w*|proof\w*|evidence|"
    r"дәлел\w*|далел\w*|dalil\w*|isbot\w*|сурет\w*|фото\w*|photo\w*)(?!\w)"
)
CLAUSE_BOUNDARY_RE = re.compile(r"[,.!?;\n]|\b(?:но|однако|but|however|бірақ|lekin)\b")
NEGATED_BEFORE_RE = re.compile(
    r"(?:^|\W)(?:нет(?:у)?|без|no|without|жоқ|yo'q|yoq|"
    r"не\s+(?:было|был|име\w*|сохранил\w*|сделал\w*|снял\w*))"
    r"\s+(?:\w+\s+){0,3}$"
)
NEGATED_AFTER_RE = re.compile(
    r"^\s*(?:у\s+меня\s+)?(?:нет(?:у)?|отсутств\w*|жоқ|yo'q|yoq|not\s+(?:available|present))(?:\b|$)"
)
GREETING_RE = re.compile(r"(?:привет|здравствуйте|здравствуй|hello|hi|hey|salom|сәлем|сәлеметсіз бе|hola|olá|ola)[\s!?.]*")
NAMED_RULE_REASON = "Найден ненумерованный термин из правил; он не заменяет проверенный номер пункта."
# UI choices for a deliberate reply-language override. Without an override,
# keep using the player's detected language, including ES/PT.
REPLY_LANGUAGE_CHOICES = frozenset({"ru", "en", "kk", "uz"})


class InputError(ValueError):
    pass


# The reply templates are conservative and do not assert that a claim is true
# or that any action has already been taken. Rules themselves are never invented.
TEMPLATES = {
    "ru": {
        "hello": "Здравствуйте!",
        "rule": "К описанной ситуации может относиться пункт {number} раздела «{section}»: «{excerpt}»",
        "term": "К описанной ситуации может относиться термин «{label}» из раздела «{section}» (ID источника: {source_id}): «{excerpt}»",
        "review": "Обстоятельства обращения и, при наличии, материалы должен проверить администратор.",
        "clarify": "Пожалуйста, подробнее опишите проблему: что произошло, когда и на каком сервере. Если есть подтверждающие материалы, приложите их к обращению.",
        "payment": "Для решения вопроса с платежом необходима проверка администратором. Укажите время операции и способ оплаты, но не передавайте пароль и коды подтверждения.",
        "account": "Для решения вопроса с аккаунтом необходима проверка администратором. Не передавайте никому пароль и коды подтверждения.",
        "ban": "Оспаривание блокировки или наказания требует проверки администратором. Укажите ник, сервер и время наказания или ограничения, но не передавайте пароль и коды подтверждения.",
        "knowledge": "В справочной статье «{title}» указано: «{excerpt}». Это выдержка из исходного материала.",
        "knowledge_source": "Источник: {source}",
        "missing_rule": "Пункт правил не установлен. Черновик неполный: перед отправкой его должен проверить администратор.",
        "missing_knowledge": "Подходящая статья базы знаний не найдена. Черновик неполный и требует проверки администратором.",
    },
    "kk": {
        "hello": "Сәлеметсіз бе!",
        "rule": "Сипатталған жағдайға «{section}» бөлімінің {number}-тармағы қатысты болуы мүмкін. Түпнұсқада: «{excerpt}».",
        "term": "Сипатталған жағдайға «{section}» бөліміндегі «{label}» термині қатысты болуы мүмкін (дереккөз ID: {source_id}). Түпнұсқа: «{excerpt}».",
        "review": "Мән-жайды әкімші тексеруі керек.",
        "clarify": "Мәселені толығырақ сипаттаңыз: не болды, қашан және қай серверде? Растайтын материалдарыңыз болса, оларды тіркеңіз.",
        "payment": "Төлем мәселесін әкімші тексеруі керек. Төлем уақыты мен тәсілін көрсетіңіз, бірақ құпиясөз бен растау кодтарын ешкімге бермеңіз.",
        "account": "Аккаунт мәселесін әкімші тексеруі керек. Құпиясөз бен растау кодтарын ешкімге бермеңіз.",
        "ban": "Бұғаттау немесе жазаға шағымды әкімші тексеруі керек. Никіңізді, серверді және жаза немесе шектеу уақытын көрсетіңіз; құпиясөз бен растау кодтарын бермеңіз.",
        "knowledge": "«{title}» анықтамалық материалындағы түпнұсқа үзінді: «{excerpt}».",
        "knowledge_source": "Дереккөз: {source}",
        "missing_rule": "Қолданылатын ереже анықталмады. Жауап жобасы толық емес: жіберер алдында әкімші тексеруі керек.",
        "missing_knowledge": "Тиісті анықтамалық мақала табылмады. Жауап жобасы толық емес, әкімші тексеруі керек.",
    },
    "uz": {
        "hello": "Salom!",
        "rule": "Ta’riflangan holatga «{section}» bo‘limining {number}-bandi tegishli bo‘lishi mumkin. Asl matn: «{excerpt}».",
        "term": "Ta’riflangan holatga «{section}» bo‘limidagi «{label}» atamasi tegishli bo‘lishi mumkin (manba ID: {source_id}). Asl matn: «{excerpt}».",
        "review": "Vaziyatni administrator tekshirishi kerak.",
        "clarify": "Muammoni batafsil yozing: nima, qachon va qaysi serverda sodir bo‘ldi? Tasdiqlovchi materiallar bo‘lsa, ularni ilova qiling.",
        "payment": "To‘lov masalasini administrator tekshirishi kerak. To‘lov vaqti va usulini ko‘rsating, ammo parol va tasdiqlash kodlarini hech kimga bermang.",
        "account": "Akkaunt masalasini administrator tekshirishi kerak. Parol va tasdiqlash kodlarini hech kimga bermang.",
        "ban": "Bloklash yoki jazoga e’tirozni administrator tekshirishi kerak. Nik, server va jazo yoki cheklov vaqtini ko‘rsating; parol va tasdiqlash kodlarini bermang.",
        "knowledge": "«{title}» ma’lumotnomasidan asl parcha: «{excerpt}».",
        "knowledge_source": "Manba: {source}",
        "missing_rule": "Tegishli qoida aniqlanmadi. Javob loyihasi to‘liq emas, yuborishdan oldin administrator tekshirishi kerak.",
        "missing_knowledge": "Tegishli ma’lumotnoma maqolasi topilmadi. Javob loyihasi to‘liq emas, administrator tekshirishi kerak.",
    },
    "en": {
        "hello": "Hello!",
        "rule": "Section {number} of «{section}» may be relevant to the situation you described. Original text: «{excerpt}».",
        "term": "The term «{label}» in «{section}» may be relevant (source ID: {source_id}). Original text: «{excerpt}».",
        "review": "An administrator needs to review the circumstances and any materials provided.",
        "clarify": "Please describe what happened, when, and on which server. Attach any supporting material if available.",
        "payment": "An administrator needs to review the payment issue. Please provide the time and payment method, but never share your password or verification codes.",
        "account": "An administrator needs to review the account issue. Never share your password or verification codes.",
        "ban": "An administrator needs to review an appeal about a ban or penalty. Please provide your nickname, server and the time of the restriction or penalty; never share your password or verification codes.",
        "knowledge": "Original excerpt from the help article «{title}»: «{excerpt}».",
        "knowledge_source": "Source: {source}",
        "missing_rule": "The applicable rule has not been established. This draft is incomplete and must be reviewed by an administrator before delivery.",
        "missing_knowledge": "No relevant knowledge-base article was found. This draft is incomplete and requires an administrator’s review.",
    },
    "es": {
        "hello": "¡Hola!",
        "rule": "El apartado {number} de «{section}» podría estar relacionado con la situación descrita. Texto original: «{excerpt}».",
        "term": "El término «{label}» de «{section}» podría ser relevante (ID de fuente: {source_id}). Texto original: «{excerpt}».",
        "review": "Un administrador debe revisar las circunstancias y los materiales aportados.",
        "clarify": "Describe qué ocurrió, cuándo y en qué servidor. Adjunta pruebas si las tienes.",
        "payment": "Un administrador debe revisar el problema de pago. Indica la hora y el método de pago, pero no compartas tu contraseña ni códigos de verificación.",
        "account": "Un administrador debe revisar el problema de la cuenta. No compartas tu contraseña ni códigos de verificación.",
        "ban": "Un administrador debe revisar la apelación del bloqueo o la sanción. Indica tu nombre, servidor y hora de la sanción o del bloqueo; no compartas tu contraseña ni códigos.",
        "knowledge": "Fragmento original del artículo «{title}»: «{excerpt}».",
        "knowledge_source": "Fuente: {source}",
        "missing_rule": "No se ha identificado la regla aplicable. El borrador está incompleto y un administrador debe revisarlo antes de enviarlo.",
        "missing_knowledge": "No se encontró un artículo de ayuda pertinente. El borrador está incompleto y requiere revisión de un administrador.",
    },
    "pt": {
        "hello": "Olá!",
        "rule": "O item {number} de «{section}» pode ser relevante para a situação descrita. Texto original: «{excerpt}».",
        "term": "O termo «{label}» em «{section}» pode ser relevante (ID da fonte: {source_id}). Texto original: «{excerpt}».",
        "review": "Um administrador precisa analisar as circunstâncias e os materiais apresentados.",
        "clarify": "Descreva o que aconteceu, quando e em qual servidor. Anexe materiais de apoio, se houver.",
        "payment": "Um administrador precisa analisar o problema de pagamento. Informe o horário e a forma de pagamento, mas não compartilhe sua senha ou códigos de verificação.",
        "account": "Um administrador precisa analisar o problema da conta. Não compartilhe sua senha ou códigos de verificação.",
        "ban": "Um administrador precisa analisar o recurso sobre o bloqueio ou a penalidade. Informe seu apelido, servidor e horário da penalidade ou do bloqueio; não compartilhe sua senha ou códigos.",
        "knowledge": "Trecho original do artigo de ajuda «{title}»: «{excerpt}».",
        "knowledge_source": "Fonte: {source}",
        "missing_rule": "A regra aplicável não foi identificada. O rascunho está incompleto e deve ser revisado por um administrador antes do envio.",
        "missing_knowledge": "Nenhum artigo de ajuda relevante foi encontrado. O rascunho está incompleto e precisa da revisão de um administrador.",
    },
}


def _positive_attachment(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value > 0
    if isinstance(value, str):
        digits = value.strip()
        # Avoid converting an arbitrarily large numeric string to an integer.
        return bool(re.fullmatch(r"[0-9]+", digits) and digits.lstrip("0"))
    if isinstance(value, (list, tuple)):
        return bool(value)
    if isinstance(value, dict):
        if "count" in value:
            return _positive_attachment(value["count"])
        return bool(value)
    return False


def _evidence_mentioned(text: str, lang: str) -> bool:
    """Detect evidence mentions without claiming that the evidence exists.

    This is intentionally conservative around explicit negation. The caller
    must still distinguish a player's mention from attachment metadata.
    """
    value = normalize(text, lang)
    for match in EVIDENCE_RE.finditer(value):
        before = CLAUSE_BOUNDARY_RE.split(value[max(0, match.start() - 100):match.start()])[-1]
        after = CLAUSE_BOUNDARY_RE.split(value[match.end():match.end() + 100])[0]
        if not NEGATED_BEFORE_RE.search(before) and not NEGATED_AFTER_RE.search(after):
            return True
    return False


def _player_messages(ticket: dict[str, Any]) -> list[dict[str, Any]]:
    messages = ticket.get("messages")
    if not isinstance(messages, list):
        raise InputError("Поле messages должно быть массивом сообщений")
    if len(messages) > 200:
        raise InputError("Слишком много сообщений в обращении")
    players: list[dict[str, Any]] = []
    for message in messages:
        if not isinstance(message, dict):
            raise InputError("Каждое сообщение должно быть объектом")
        # Admin replies and gold labels must never become inference features.
        role = message.get("role")
        if isinstance(role, str) and role in {"player", "reporter"}:
            if not isinstance(message.get("text", ""), str):
                raise InputError("Текст сообщения должен быть строкой")
            players.append(message)
    if not players:
        raise InputError("Необходимо хотя бы одно сообщение игрока (role: player)")
    if sum(len(m.get("text", "")) for m in players) > 100_000:
        raise InputError("Текст обращения превышает допустимый размер")
    return players


def _extract(
    ticket: dict[str, Any], player_messages: list[dict[str, Any]], text: str, lang: str,
) -> tuple[dict[str, Any], bool, bool]:
    raw_nick = ticket.get("reported_nick")
    nickname = raw_nick.strip()[:64] if isinstance(raw_nick, str) and raw_nick.strip() else None
    if not nickname:
        match = NICK_RE.search(text)
        nickname = match.group(1) if match else None
    raw_refs = str(ticket.get("rule_refs_raw") or "") + " " + text
    rule_refs = list(dict.fromkeys(RULE_REF_RE.findall(raw_refs)))[:20]
    attached = _positive_attachment(ticket.get("images_count")) or any(_positive_attachment(m.get("attachments")) for m in player_messages)
    mentioned = _evidence_mentioned(text, lang)

    raw_server = ticket.get("server")
    if isinstance(raw_server, int) and not isinstance(raw_server, bool):
        server: str | None = str(raw_server)
    elif isinstance(raw_server, str) and raw_server.strip():
        server = raw_server.strip()
    else:
        server_match = SERVER_RE.search(text)
        region = ticket.get("region")
        server = server_match.group(1) if server_match else (region.strip() if isinstance(region, str) and region.strip() else None)
    return {"nickname": nickname, "rule_refs": rule_refs, "has_evidence": attached or mentioned, "server": server}, attached, mentioned


def _safe_article_excerpt(text: str) -> str | None:
    # Unreviewed source material can contain procedures, promises, or requests
    # for secrets. Fail closed rather than quoting such material automatically.
    if re.search(
        r"(?i)(разбан|забан|разблок|блокиров|накаж|наказан|возврат|возмещ|возвращ|верн\w*|компенс|"
        r"выплат|деньг|восстанов|гарант|обеща|refund|unban|unblock|unlock|punish|\bban\b|banned|money|"
        r"payment|restore|recover|guarantee|promise|бұғат|қайтар|qaytar|парол|құпиясөз|password|parol|"
        r"код[аы]?\s+подтвержден|verification\s+code|tasdiqlash\s+kod|"
        r"персональн\w*\s+данн|личн\w*\s+данн|personal\s+data|\bcvv\b|\botp\b)",
        text,
    ):
        return None
    line = re.sub(r"\s+", " ", text.strip().split("\n", 1)[0]).strip()
    if not line:
        return None
    return line if len(line) <= 340 else line[:337].rsplit(" ", 1)[0] + "…"


def requires_rule(catalog: Catalog, kind: str, category: str) -> bool:
    """Whether the predicted category needs a rule; not a gold relevance label."""
    return category != "report.offtopic" and (
        bool(catalog.categories[category].get("rules")) or kind == "complaint" or category == "report.complaint"
    )


def _claimed_fallback_refs(ticket: dict[str, Any]) -> list[str]:
    raw = ticket.get("rule_refs_raw")
    if not isinstance(raw, str) or re.search(
        r"(?i)(?<!\w)(?:не|нет|ошибк\w*|not|wrong|incorrect|емес|жоқ|emas)(?!\w)", raw
    ):
        return []
    return list(dict.fromkeys(RULE_REF_RE.findall(raw)))


def validate_ticket(ticket: Any) -> tuple[str, list[dict[str, Any]]]:
    """Validate the input independently of the classifier for safe fallback."""
    if not isinstance(ticket, dict):
        raise InputError("Запрос должен быть JSON-объектом")
    kind = ticket.get("kind")
    if not isinstance(kind, str) or kind not in {"complaint", "report"}:
        raise InputError("kind должен быть complaint или report")
    if "reply_language" in ticket:
        language = ticket["reply_language"]
        if not isinstance(language, str) or language not in REPLY_LANGUAGE_CHOICES | {"auto"}:
            raise InputError("Выберите язык ответа: автоматически, RU, EN, KK или UZ.")
    # These fields can be returned as extracted.server; rejecting excessive
    # metadata here avoids turning valid JSON into an internal result error.
    for name in ("server", "region"):
        value = ticket.get(name)
        if isinstance(value, str):
            too_long = len(value.strip()) > 1024
        elif isinstance(value, int) and not isinstance(value, bool):
            try:
                too_long = len(str(value)) > 1024
            except ValueError:  # Interpreter limit for huge integer strings.
                too_long = True
        else:
            too_long = False
        if too_long:
            raise InputError("Поле server или region должно быть не длиннее 1024 символов.")
    return kind, _player_messages(ticket)


class TriageService:
    def __init__(self, catalog: Catalog):
        self.catalog = catalog
        self.duplicates = DuplicateDetector()

    def triage(self, ticket: dict[str, Any], *, reply_language: str | None = None) -> dict[str, Any]:
        kind, player_messages = validate_ticket(ticket)
        text = "\n".join(m.get("text", "") for m in player_messages)
        # The reply choice is independent of language detection and classification.
        # The private override can also reproduce older UZ/ES/PT drafts.
        if reply_language is not None and (
            not isinstance(reply_language, str) or reply_language not in SUPPORTED_LANGUAGES
        ):
            raise InputError("Неверный язык черновика ответа.")
        lang = detect_language(text, ticket.get("lang"))
        chosen = ticket.get("reply_language")
        reply_lang = reply_language or (chosen if chosen in REPLY_LANGUAGE_CHOICES else None)
        reply_lang = reply_lang or (lang if lang in SUPPORTED_LANGUAGES else "ru")
        extracted, attached_evidence, mentioned_evidence = _extract(ticket, player_messages, text, lang)
        classification: Classification = classify(kind, text, lang, self.catalog.categories)
        category = classification.category
        priority = priority_for(kind, category, classification.signals, extracted["has_evidence"])
        is_spam = obvious_spam(text)
        is_duplicate = self.duplicates.check(
            reporter=ticket.get("reporter_hash"), target=ticket.get("reported_hash"),
            ticket_id=ticket.get("ticket_id"), kind=kind, category=category,
            text=text, created_at=ticket.get("created_at"), lang=lang,
        )

        category_codes = [category]
        if category == "report.complaint" and classification.related_complaint:
            category_codes.append(classification.related_complaint)
        needs_rule = requires_rule(self.catalog, kind, category)
        sensitive_case = bool(classification.signals & {"payment", "compromise", "ban"}) or category in {"report.payment", "report.account"}
        # Sensitive cases still go to a human, but an independently supported
        # source may be shown for review. Require stronger direct-word evidence.
        match: RuleMatch | None = self.catalog.retrieve_rule(
            category_codes, text, lang,
            claimed_refs=_claimed_fallback_refs(ticket), strict=sensitive_case,
        ) if needs_rule else None
        has_numbered_rule = bool(match and not isinstance(match.rule, NamedRule))
        article_match = next((found for code in category_codes if (found := self.catalog.retrieve_article(code, text, lang))), None)
        article = article_match.article if article_match else None
        article_excerpt = _safe_article_excerpt(article_match.passage) if article_match else None
        article_title = _safe_article_excerpt(article.title) if article else None
        if not article_title:
            article_excerpt = None
        needs_knowledge = category in {"report.question", "report.help"}

        reasons: list[str] = []
        signals = classification.signals
        if "payment" in signals or category == "report.payment":
            reasons.append("Платёжные обращения обязательно рассматривает человек.")
        if "compromise" in signals or category == "report.account":
            reasons.append("Вопросы аккаунта и возможного взлома требуют проверки человеком.")
        if "ban" in signals:
            reasons.append("Блокировки и апелляции рассматривает человек.")
        if kind == "complaint" or category == "report.complaint":
            reasons.append("Обстоятельства жалобы и решение по ней проверяет администратор.")
        if category in self.catalog.always_human:
            reasons.append("Категория требует участия администратора по таксономии.")
        if attached_evidence:
            reasons.append("Метаданные указывают на вложения; их содержимое недоступно сервису.")
        elif mentioned_evidence:
            reasons.append("Игрок упомянул доказательства; их наличие и содержимое не подтверждены.")
        if match and isinstance(match.rule, NamedRule):
            reasons.append(NAMED_RULE_REASON)
        if needs_rule and not has_numbered_rule:
            reasons.append("Релевантный пункт правила не подтверждён; черновик не готов к отправке.")
        if needs_knowledge and not article_excerpt:
            reasons.append("Подходящая статья базы знаний не подтверждена; черновик требует ручной проверки.")
        if lang == "und":
            reasons.append("Язык не удалось уверенно определить; требуется проверка ответа.")
        if classification.confidence < 0.6:
            reasons.append("Категория определена неуверенно.")
        if is_duplicate:
            reasons.append("Похоже на пятое обращение того же игрока по той же проблеме за час.")
        if is_spam:
            reasons.append("Обнаружен признак автоматического или повторяющегося спама.")

        # A plain greeting can receive a clarification automatically. A vague
        # request for help is different: its urgency is unknown and needs review.
        greeting_only = bool(GREETING_RE.fullmatch(normalize(text.strip(), lang)))
        if category == "report.offtopic" and not greeting_only:
            reasons.append("Недостаточно информации, чтобы оценить суть и срочность обращения.")
        auto_clarification = category == "report.offtopic" and greeting_only and not (signals & {"payment", "compromise", "ban"}) and lang != "und" and not is_spam and not is_duplicate
        needs_human = not auto_clarification or bool(reasons)
        if needs_human and not reasons:
            reasons.append("Ответ и факты необходимо проверить администратору.")

        template = TEMPLATES[reply_lang]
        parts = [template["hello"]]
        risk_template = None
        if "payment" in signals or category == "report.payment":
            risk_template = "payment"
        elif "compromise" in signals or category == "report.account":
            risk_template = "account"
        elif "ban" in signals:
            risk_template = "ban"
        if risk_template:
            parts.append(template[risk_template])
        if match:
            if isinstance(match.rule, NamedRule):
                parts.append(template["term"].format(
                    label=match.rule.label, section=match.rule.section,
                    source_id=match.rule.section_id, excerpt=match.rule.excerpt,
                ))
            else:
                parts.append(template["rule"].format(number=match.rule.number, section=match.rule.section, excerpt=match.rule.excerpt))
        if article_excerpt and article_title:
            parts.append(template["knowledge"].format(title=article_title, excerpt=article_excerpt))
            if article and article.source_url:
                parts.append(template["knowledge_source"].format(source=article.source_url))
        if not risk_template:
            parts.append(template["clarify"] if category == "report.offtopic" else template["review"])
            if needs_rule and not has_numbered_rule and not extracted["has_evidence"]:
                parts.append(template["clarify"])
        if needs_rule and not has_numbered_rule:
            parts.append(template["missing_rule"])
        if needs_knowledge and not article_excerpt:
            parts.append(template["missing_knowledge"])

        # The contract's cited field contains numbered points only. An
        # unnumbered definition is shown with its true source ID in the draft,
        # but must not be presented as a fabricated point number.
        cited = [match.rule.citation_ref] if has_numbered_rule and match else []
        return {
            "lang": lang,
            "category": category,
            "priority": priority,
            "is_spam_or_duplicate": bool(is_spam or is_duplicate),
            "extracted": extracted,
            "draft_reply": {"lang": reply_lang, "text": "\n\n".join(parts), "cited": cited},
            "needs_human": needs_human,
            "confidence": classification.confidence,
            "reasons": list(dict.fromkeys(reasons)),
        }
