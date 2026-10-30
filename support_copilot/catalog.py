"""Load the private case files and retrieve verified, section-scoped passages."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlsplit

from .rp_terms import NamedRule, described_deathmatch, mentioned_term, parse_named_terms
from .text import contains_any, mentions_abuse_shorthand, negates_abuse, normalize, stems

RULE_START = re.compile(r"(?m)^[ \t]*(\d+(?:\.\d+){1,4})[ \t]+")
NUMBER_REF = re.compile(r"^\d+(?:\.\d+){1,4}$")


class CatalogError(ValueError):
    """A case data file is missing or has an unexpected schema."""


@dataclass(frozen=True)
class Rule:
    number: str
    section_id: str
    section: str
    text: str
    excerpt: str

    @property
    def citation_ref(self) -> str:
        return self.number


@dataclass(frozen=True)
class Article:
    article_id: str
    title: str
    text: str
    categories: tuple[str, ...]
    source_url: str | None = None


@dataclass(frozen=True)
class ArticleMatch:
    article: Article
    passage: str
    overlap: int


@dataclass(frozen=True)
class RuleMatch:
    rule: Rule | NamedRule
    overlap: int


def _load_json(path: str | Path, description: str) -> Any:
    try:
        with open(path, encoding="utf-8") as stream:
            return json.load(stream)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CatalogError(f"Не удалось прочитать {description}: {path} ({exc})") from exc


def _excerpt(text: str) -> str:
    # Use an actual substring of the source. Do not reproduce penalty tables.
    first_line = text.strip().split("\n", 1)[0]
    # A vertical bar can also appear inside a term such as [Green Zone | GZ].
    # Only remove an inline penalty table, not part of the rule itself.
    first_line = re.split(r"\s+\|\s*(?=(?:Нарушение|Грубое|Наказание|MUTE|DEMORGAN|Блокировка)\b)", first_line, maxsplit=1, flags=re.IGNORECASE)[0].strip()
    first_line = re.sub(r"\s+", " ", first_line)
    if len(first_line) > 340:
        cut = first_line[:337].rsplit(" ", 1)[0]
        return cut + "…"
    return first_line


def _mentions_green_zone(text: str) -> bool:
    value = normalize(text)
    return contains_any(value, ("зелен", "green zone", "гз", "жасыл аймақ")) or bool(re.search(r"(?<!\w)gz(?!\w)", value))


def _mentions_house(text: str) -> bool:
    value = normalize(text)
    return contains_any(value, ("дом", "квартир", "house", "home", "үй")) or bool(re.search(r"(?<!\w)uy(?:im|i|da|ga)?(?!\w)", value))


def _expanded_query(text: str, lang: str) -> str:
    """Bridge common player wording and the Russian rule vocabulary.

    Expansions are only used for retrieval, never presented as facts.
    """
    q = normalize(text, lang)
    additions: list[str] = []
    expansions = (
        (("оскорб", "обозва", "матер", "insult", "haqorat", "ҳақорат", "қорла", "ругал", "toxic", "токсич", "insultó", "insultou"), "оскорбление"),
        (("родител", "родны", "семь", "family", "семья", "отец", "мать", "ана", "әке"), "родственников родных"),
        (("расиз", "наци", "религи", "racis", "ксенофоб", "дискриминац"), "расизм религии ксенофобия"),
        (("угроз", "угрож", "докс", "threat", "doxx", "қорқыт", "tahdid"), "угрожать личную информацию"),
        (("чит", "аим", "aimbot", "cheat", "хак", "hack", "сторонн", "софт", "дастур"), "стороннее программное обеспечение игровые преимущества"),
        (("убил", "убива", "убий", "урон", "стреля", "дм", "deathmatch", "killed", "kill", "өлтір", "oldir", "o'ldir"), "убийство нанесение урона"),
        (("зелен", "green zone", " gz", "гз", "жасыл аймақ"), "зеленой зоне"),
        (("мошенн", "обман", "скам", "украл", "scam", "fraud", "алда", "firib"), "мошенничество имущество валюта"),
        (("вымога", "вымог", "шантаж", "extort", "blackmail"), "вымогательство угрозы ультиматумы"),
        (("реал", "rmt", "real money", "настоящие деньги", "sot", "прода"), "реальные деньги сделка продажа"),
        (("реклам", "спам", "advertis", "reklama", "жарнама"), "реклама"),
        (("админ", "admin", "әкімші", "administrator"), "администратора администрации жалобы"),
        (("телепорт", "teleport", "телепорттау"), "телепорт"),
    )
    for triggers, expansion in expansions:
        if contains_any(q, triggers):
            additions.append(expansion)
    if _mentions_green_zone(q):
        additions.append("зеленой зоне")
    if _mentions_house(q):
        additions.append("дом квартира жильцам")
    if mentions_abuse_shorthand(q, lang):
        # Retrieval vocabulary only; the statement remains an unverified claim.
        additions.append("оскорбление")
        if contains_any(q, ("родн", "родител", "семь", "мам", "матер", "отц", "пап")):
            additions.append("упоминание родственников")
    return q + " " + " ".join(additions)


def _in_scope(rule: Rule, query: str) -> bool:
    """Reject some dangerous near matches to narrowly scoped rules."""
    body = normalize(rule.excerpt)
    q = normalize(query)
    if "оскорб" in body and negates_abuse(q):
        return False
    if ("жильцам" in body or ("территори" in body and ("дома" in body or "квартир" in body))):
        if not _mentions_house(q):
            return False
    if contains_any(body, ("зеленой зоне", "зеленых зон", "green zone")):
        if not _mentions_green_zone(q):
            return False
    if "расизм" in body and "религи" in body:
        if not contains_any(q, ("расиз", "наци", "религи", "racis", "ксенофоб", "дискриминац", "ненавист", "hate", "politic", "политик")):
            return False
    if "вымогательств" in body:
        if not contains_any(q, ("вымога", "вымог", "шантаж", "extort", "blackmail", "ультиматум")):
            return False
    if "личную информацию" in body and "угрожа" in body:
        if not contains_any(q, ("угроз", "угрож", "докс", "личн", "threat", "doxx", "қорқыт", "tahdid")):
            return False
    return True


class Catalog:
    def __init__(self, rules_path: str | Path, taxonomy_path: str | Path, knowledge_path: str | Path | None = None):
        taxonomy = _load_json(taxonomy_path, "таксономию")
        rules_data = _load_json(rules_path, "правила")
        if not isinstance(taxonomy, dict) or not isinstance(taxonomy.get("categories"), list):
            raise CatalogError("В таксономии нужен массив categories")
        if not isinstance(rules_data, dict) or not isinstance(rules_data.get("rules"), list):
            raise CatalogError("В правилах нужен массив rules")

        self.taxonomy = taxonomy
        self.categories: dict[str, dict[str, Any]] = {}
        for item in taxonomy["categories"]:
            if isinstance(item, dict) and isinstance(item.get("code"), str) and item.get("kind") in {"complaint", "report"}:
                if item["code"] in self.categories:
                    raise CatalogError("В таксономии повторяется код категории")
                self.categories[item["code"]] = item
        if not any(c.get("kind") == "complaint" for c in self.categories.values()) or not any(c.get("kind") == "report" for c in self.categories.values()):
            raise CatalogError("Нужна хотя бы одна категория для complaint и report")
        priorities = taxonomy.get("priorities", [])
        self.priority_codes = {p.get("code") for p in priorities if isinstance(p, dict)}
        if not {"p0", "p1", "p2", "p3"}.issubset(self.priority_codes):
            raise CatalogError("В таксономии должны быть приоритеты p0–p3")
        self.always_human = set(taxonomy.get("needs_human_always", []))

        self.rules: list[Rule] = []
        self.named_rules: list[NamedRule] = []
        self.sections: list[tuple[str, str]] = []
        section_ids: set[str] = set()
        for index, section in enumerate(rules_data["rules"]):
            if not isinstance(section, dict) or not isinstance(section.get("text"), str):
                continue
            section_id = str(section.get("id", index))
            section_name = str(section.get("category", "Правила"))
            if section_id in section_ids:
                raise CatalogError("В правилах повторяется идентификатор раздела")
            section_ids.add(section_id)
            self.sections.append((section_id, section_name))
            body = section["text"]
            self.named_rules.extend(parse_named_terms(section_id, section_name, body))
            starts = list(RULE_START.finditer(body))
            for pos, match in enumerate(starts):
                end = starts[pos + 1].start() if pos + 1 < len(starts) else len(body)
                text = body[match.end():end].strip()
                excerpt = _excerpt(text)
                if excerpt:
                    self.rules.append(Rule(match.group(1), section_id, section_name, text, excerpt))
        if not self.rules:
            raise CatalogError("Не найдено ни одного нумерованного пункта правил")

        # Bare taxonomy references refer to the general rules, not arbitrary
        # sections that happen to reuse the same subsection number.
        self.primary_section = next((sid for sid, name in self.sections if "общие правила игры" in normalize(name)), self.sections[0][0])
        self.complaint_section = next((sid for sid, name in self.sections if "правила жалоб" in normalize(name)), None)
        self.green_section = next((sid for sid, name in self.sections if "зелен" in normalize(name) and "зон" in normalize(name)), None)
        self.by_section_and_number = {(r.section_id, r.number): r for r in self.rules}
        if len(self.by_section_and_number) != len(self.rules):
            raise CatalogError("В одном разделе правил повторяется номер пункта")
        self.articles = self._load_articles(knowledge_path, set(self.categories)) if knowledge_path else []

    @staticmethod
    def _load_articles(path: str | Path, valid_categories: set[str]) -> list[Article]:
        data = _load_json(path, "базу знаний")
        entries = data.get("articles") if isinstance(data, dict) else data
        if not isinstance(entries, list):
            raise CatalogError("В базе знаний нужен массив articles")
        articles: list[Article] = []
        ids: set[str] = set()
        for item in entries:
            if not isinstance(item, dict):
                raise CatalogError("Каждая статья базы знаний должна быть объектом")
            approved = item.get("approved", True)
            if not isinstance(approved, bool):
                raise CatalogError("Поле approved в статье должно быть true или false")
            if not approved:
                continue
            article_id, title, text = item.get("id"), item.get("title"), item.get("text")
            if not all(isinstance(value, str) and value.strip() for value in (article_id, title, text)):
                raise CatalogError("Для статьи базы знаний нужны непустые строки id, title и text")
            if article_id in ids:
                raise CatalogError("Идентификаторы статей базы знаний должны быть уникальными")
            categories = item.get("categories", [])
            if not isinstance(categories, list) or any(not isinstance(c, str) or c not in valid_categories for c in categories):
                raise CatalogError("Категории статьи должны быть кодами из таксономии")
            source_url = item.get("source_url")
            if source_url is not None:
                if not isinstance(source_url, str) or not source_url or len(source_url) > 2048 or re.search(r"\s", source_url):
                    raise CatalogError("source_url должен быть корректным HTTPS-адресом")
                try:
                    parsed = urlsplit(source_url)
                    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.port not in (None, 443):
                        raise CatalogError("source_url должен быть корректным HTTPS-адресом")
                except ValueError as exc:
                    raise CatalogError("source_url должен быть корректным HTTPS-адресом") from exc
            ids.add(article_id)
            articles.append(Article(article_id, title, text, tuple(categories), source_url))
        return articles

    def named_sources_in_draft(self, draft: str) -> list[NamedRule]:
        """Identify literal, attributed term passages for audit/validation."""
        return [
            term for term in self.named_rules
            if term.section_id in draft and term.section in draft and term.excerpt in draft
        ]

    def candidate_rules(self, category_codes: Iterable[str], query: str) -> list[Rule]:
        result: dict[tuple[str, str], Rule] = {}
        q = normalize(query)
        for code in category_codes:
            entry = self.categories.get(code, {})
            refs = entry.get("rules", [])
            if not isinstance(refs, list):
                continue
            for raw_ref in refs:
                ref = str(raw_ref).strip()
                section_id = self.primary_section
                number = ref
                if ref.upper().startswith("ЖБ "):
                    section_id, number = self.complaint_section, ref.split(None, 1)[1]
                elif ref.upper().startswith("GZ"):
                    # GZ in the taxonomy names a section, not a rule ID.
                    if not self.green_section or not _mentions_green_zone(q):
                        continue
                    tail = ref[2:].strip()
                    if NUMBER_REF.fullmatch(tail):
                        candidates = [self.by_section_and_number.get((self.green_section, tail))]
                    else:
                        candidates = [r for r in self.rules if r.section_id == self.green_section]
                    for rule in candidates:
                        if rule:
                            result[(rule.section_id, rule.number)] = rule
                    continue
                if not section_id or not NUMBER_REF.fullmatch(number):
                    continue
                rule = self.by_section_and_number.get((section_id, number))
                if rule:
                    result[(rule.section_id, rule.number)] = rule
        return list(result.values())

    def retrieve_rule(
        self, category_codes: Iterable[str], query: str, lang: str, *,
        claimed_refs: Iterable[str] = (), strict: bool = False,
    ) -> RuleMatch | None:
        """Retrieve an existing, context-matching clause, or fail closed.

        A player's reference can only narrow a fallback search for an otherwise
        unclassified complaint. It is never evidence of relevance: fallback
        candidates must independently match two informative words in the
        player's message. Ties are not resolved by arbitrary section ordering.
        """
        codes = tuple(category_codes)
        expanded = _expanded_query(query, lang)
        direct_terms = stems(query, lang)
        query_terms = direct_terms if strict else stems(expanded, lang)
        named_match: RuleMatch | None = None
        explicit_term = False
        if not strict and any(code.startswith("complaint.") or code == "report.complaint" for code in codes):
            abbreviation = mentioned_term(query, lang)
            explicit_term = bool(abbreviation)
            if not abbreviation and described_deathmatch(query, lang):
                abbreviation = "DM"
            candidates = [term for term in self.named_rules if term.abbreviation == abbreviation] if abbreviation else []
            # Ambiguous source versions or duplicate labels must not be chosen
            # by file order. The source ID is real but is not a point number.
            if len(candidates) == 1:
                named_match = RuleMatch(candidates[0], 1)
        if not query_terms:
            return named_match
        # A specific named allegation (e.g. Mass DM GZ) is preferable to a
        # broader numeric result generated only by query expansion. Do not
        # override a separate, specifically classified non-RP complaint.
        if named_match and explicit_term and set(codes).issubset({"complaint.dm", "complaint.other", "report.complaint"}):
            return named_match

        def score_rules(rules: Iterable[Rule], terms: set[str], minimum: int) -> list[tuple[int, Rule]]:
            matches: list[tuple[int, Rule]] = []
            for rule in rules:
                if not _in_scope(rule, expanded):
                    continue
                overlap = terms & stems(rule.excerpt)
                # Claimed numbers and common boilerplate never establish relevance.
                useful = {term for term in overlap if len(term) >= 5}
                if len(useful) >= minimum:
                    matches.append((len(useful), rule))
            return matches

        def unique_best(matches: list[tuple[int, Rule]]) -> RuleMatch | None:
            if not matches:
                return None
            score = max(value for value, _ in matches)
            best = [rule for value, rule in matches if value == score]
            return RuleMatch(best[0], score) if len(best) == 1 else None

        ordinary = score_rules(self.candidate_rules(codes, expanded), query_terms, 2 if strict else 1)
        if ordinary:
            # An ambiguous numerical match is not silently replaced by a term.
            return unique_best(ordinary)
        if named_match:
            return named_match

        # Only use an unambiguous reference as an extra search hint for the
        # broad complaint fallback. It may occur in several rule sections.
        refs = {str(value) for value in claimed_refs if NUMBER_REF.fullmatch(str(value))}
        if "complaint.other" not in codes or len(refs) != 1:
            return None
        candidates = (rule for rule in self.rules if rule.number in refs)
        return unique_best(score_rules(candidates, direct_terms, 2))

    def retrieve_article(self, category: str, query: str, lang: str) -> ArticleMatch | None:
        """Match and return the actual passage, not an unrelated first line.

        At least two informative query stems must occur in the passage itself.
        A tie between different passages is ambiguous and fails closed.
        """
        query_terms = {term for term in stems(_expanded_query(query, lang), lang) if len(term) >= 5}
        if len(query_terms) < 2:
            return None
        candidates: dict[tuple[str, str], ArticleMatch] = {}
        for article in self.articles:
            if article.categories and category not in article.categories:
                continue
            for raw_line in article.text.splitlines():
                line = raw_line.strip()
                if not line:
                    continue
                # A long paragraph may contain unrelated facts; score bounded
                # sentences individually rather than clipping a matching tail.
                passages = [line] if len(line) <= 340 else re.split(r"(?<=[.!?])\s+", line)
                for passage in passages:
                    passage = passage.strip()
                    if not passage or len(passage) > 340:
                        continue
                    overlap = query_terms & stems(passage, lang)
                    if len(overlap) >= 2:
                        candidates[(article.article_id, passage)] = ArticleMatch(article, passage, len(overlap))
        if not candidates:
            return None
        score = max(match.overlap for match in candidates.values())
        best = [match for match in candidates.values() if match.overlap == score]
        return best[0] if len(best) == 1 else None
