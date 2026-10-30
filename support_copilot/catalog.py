"""Load the private case files and retrieve verified, section-scoped passages."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .text import contains_any, normalize, stems

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


@dataclass(frozen=True)
class Article:
    article_id: str
    title: str
    text: str
    categories: tuple[str, ...]


@dataclass(frozen=True)
class RuleMatch:
    rule: Rule
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
    return q + " " + " ".join(additions)


def _in_scope(rule: Rule, query: str) -> bool:
    """Reject some dangerous near matches to narrowly scoped rules."""
    body = normalize(rule.excerpt)
    q = normalize(query)
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
                self.categories[item["code"]] = item
        if not any(c.get("kind") == "complaint" for c in self.categories.values()) or not any(c.get("kind") == "report" for c in self.categories.values()):
            raise CatalogError("Нужна хотя бы одна категория для complaint и report")
        priorities = taxonomy.get("priorities", [])
        self.priority_codes = {p.get("code") for p in priorities if isinstance(p, dict)}
        if not {"p0", "p1", "p2", "p3"}.issubset(self.priority_codes):
            raise CatalogError("В таксономии должны быть приоритеты p0–p3")
        self.always_human = set(taxonomy.get("needs_human_always", []))

        self.rules: list[Rule] = []
        self.sections: list[tuple[str, str]] = []
        for index, section in enumerate(rules_data["rules"]):
            if not isinstance(section, dict) or not isinstance(section.get("text"), str):
                continue
            section_id = str(section.get("id", index))
            section_name = str(section.get("category", "Правила"))
            self.sections.append((section_id, section_name))
            body = section["text"]
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
        self.articles = self._load_articles(knowledge_path) if knowledge_path else []

    @staticmethod
    def _load_articles(path: str | Path) -> list[Article]:
        data = _load_json(path, "базу знаний")
        entries = data.get("articles") if isinstance(data, dict) else data
        if not isinstance(entries, list):
            raise CatalogError("В базе знаний нужен массив articles")
        articles: list[Article] = []
        for item in entries:
            if not isinstance(item, dict) or not isinstance(item.get("text"), str):
                continue
            if not item.get("id") or not item.get("title"):
                continue
            categories = item.get("categories", [])
            if not isinstance(categories, list):
                categories = []
            articles.append(Article(str(item["id"]), str(item["title"]), item["text"], tuple(str(c) for c in categories)))
        return articles

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

    def retrieve_rule(self, category_codes: Iterable[str], query: str, lang: str) -> RuleMatch | None:
        expanded = _expanded_query(query, lang)
        query_terms = stems(expanded, lang)
        if not query_terms:
            return None
        matches: list[tuple[int, Rule]] = []
        for rule in self.candidate_rules(category_codes, expanded):
            if not _in_scope(rule, expanded):
                continue
            overlap = query_terms & stems(rule.excerpt)
            # Numbers, boilerplate and claimed rule IDs never establish relevance.
            useful = {term for term in overlap if len(term) >= 5}
            if useful:
                matches.append((len(useful), rule))
        if not matches:
            return None
        # Stable ordering retains the taxonomy's own ordering when scores tie.
        score, rule = max(matches, key=lambda pair: pair[0])
        return RuleMatch(rule, score)

    def retrieve_article(self, category: str, query: str, lang: str) -> Article | None:
        query_terms = stems(_expanded_query(query, lang), lang)
        if len(query_terms) < 2:
            return None
        best: tuple[int, Article] | None = None
        for article in self.articles:
            if article.categories and category not in article.categories:
                continue
            overlap = query_terms & stems(article.title + " " + article.text)
            score = len({x for x in overlap if len(x) >= 5})
            if score >= 2 and (best is None or score > best[0]):
                best = (score, article)
        return best[1] if best else None
