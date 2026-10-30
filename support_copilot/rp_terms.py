"""Conservative retrieval of named, unnumbered RP terms from rules.json.

The organizer's catalog may contain a whole source entry with a real ``id``
but no numbered points. A term's label is NOT a made-up point number: the
draft identifies the source entry and quotes its text, but `cited` stays empty.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .text import normalize


@dataclass(frozen=True)
class NamedRule:
    section_id: str
    section: str
    label: str
    abbreviation: str
    text: str
    excerpt: str


# Read a single bullet only. Do not assign its position an artificial number.
TERM_LINE = re.compile(
    r"^[ \t]*[•*][ \t]*(?P<label>[^\n()|]{1,80}?)\s*"
    r"\(\s*сокращенно\s+(?P<abbreviation>[A-Za-z][A-Za-z ]{0,20})\s*\)"
    r"\s*[—–-]\s*(?P<description>[^\n]+)$",
    re.IGNORECASE,
)
SOURCE_ID = re.compile(r"[A-Za-z0-9_-]{1,64}\Z")
PENALTY = re.compile(
    r"\s+\|\s*(?=(?:Нарушение|Грубое|Наказание|MUTE|DEMORGAN|WARN|Блокировка)\b)",
    re.IGNORECASE,
)
EXPECTED_LABELS = {
    "DM": "deathmatch", "MASS DM": "massivedeathmatch",
    "MASS DM GZ": "massivedeathmatchgreenzone", "DB": "driveby",
    "MG": "metagaming", "PG": "powergaming", "NONRP": "nonroleplay",
    "SK": "spawnkill", "MASS SK": "massivespawnkill",
    "RK": "revengekill", "TK": "teamkill",
}


def parse_named_terms(section_id: str, section: str, text: str) -> list[NamedRule]:
    """Read only explicitly named RP-term bullets from a term section."""
    name = normalize(section)
    if not SOURCE_ID.fullmatch(section_id) or "термин" not in name or not ("rp" in name or "рп" in name):
        return []
    terms: list[NamedRule] = []
    for line in text.splitlines():
        match = TERM_LINE.match(line)
        if not match:
            continue
        abbreviation = " ".join(match.group("abbreviation").upper().split())
        label = match.group("label").strip()
        # Ensure a stale/mislabelled section cannot turn an arbitrary "DM"
        # into the source for DeathMatch. Some source text mixes Latin and
        # Cyrillic lookalikes in the label (e.g. MetaGаming).
        comparable = re.sub(r"[^a-z]", "", normalize(label).replace("а", "a"))
        if EXPECTED_LABELS.get(abbreviation) != comparable:
            continue
        # Keep the real label and text from the source. Drop penalty tables;
        # the assistant must not prescribe a punishment.
        excerpt = PENALTY.split(line.lstrip(" \t•*"), maxsplit=1)[0].strip()
        if not excerpt or len(excerpt) > 1000:
            continue
        terms.append(NamedRule(section_id, section, label, abbreviation, line, excerpt))
    return terms


# These aliases map player wording to the source's own abbreviations. A bare
# "тк" (Russian "because") and "ск" ("how much") are intentionally omitted.
# More-specific forms take precedence so e.g. Mass DM is not reported as DM.
_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("MASS DM GZ", re.compile(r"(?<!\w)(?:mass(?:ive)?\s*(?:dm|death\s*match)|масс\w*\s*дм)\s*(?:gz|гз)(?!\w)")),
    ("MASS DM", re.compile(r"(?<!\w)(?:mass(?:ive)?\s*(?:dm|death\s*match)|масс\w*\s*дм)(?!\w)")),
    ("MASS SK", re.compile(r"(?<!\w)(?:mass(?:ive)?\s*(?:sk|spawn\s*kill)|масс\w*\s*ск)(?!\w)")),
    ("DM", re.compile(r"(?<!\w)(?:dm|death\s*match|дм|дм(?:ит|ят|ил\w*|ить|ишь|или|ятс?я))(?!\w)")),
    ("DB", re.compile(r"(?<!\w)(?:db|drive\s*by|дб|дб(?:ит|ят|ил\w*|ить|ишь|или))(?!\w)")),
    ("MG", re.compile(r"(?<!\w)(?:mg|мг|meta\s*gaming|метагейм\w*)(?!\w)")),
    ("PG", re.compile(r"(?<!\w)(?:pg|пг|power\s*gaming|пауэргейм\w*)(?!\w)")),
    ("NONRP", re.compile(r"(?<!\w)(?:non[\s-]*rp|нон[\s-]*рп)(?!\w)")),
    ("SK", re.compile(r"(?<!\w)(?:sk|spawn\s*kill|спавн\s*килл)(?!\w)")),
    ("RK", re.compile(r"(?<!\w)(?:rk|рк|revenge\s*kill|ревендж\s*килл)(?!\w)")),
    ("TK", re.compile(r"(?<!\w)(?:tk|team\s*kill|тим\s*килл)(?!\w)")),
)
_NEGATION_BEFORE = re.compile(r"(?:^|\W)(?:не|нет|без|not|no|without|емес|жоқ|emas)(?:\s+(?:был\w*|было|было\s+никак\w*|was|is|a))?\s*$")
_NEGATION_AFTER = re.compile(r"^\s*(?:не\s+(?:был\w*|было|происходил\w*|совершал\w*)|нет|не\s+было|was\s+not|did\s+not\s+happen)(?:\b|$)")
_KILL = re.compile(r"(?<!\w)(?:убил\w*|убива\w*|убийств\w*|kill(?:ed|ing|s)?)(?!\w)")
_UNPROVOKED = re.compile(
    r"(?<!\w)(?:без\s+(?:(?:какой[- ]либо|веской|рп|rp)\s+)?причин\w*|"
    r"просто\s+так|ни\s+за\s+что|without\s+(?:(?:a|any|good|rp)\s+){0,2}reason)(?!\w)"
)


def described_deathmatch(text: str, lang: str) -> bool:
    """Recognize a narrow description of killing without a reason.

    This identifies a possibly relevant definition, not a verdict. Conflicting
    or negated terms are excluded instead of being reduced to a generic DM.
    """
    value = normalize(text, lang)
    if any(pattern.search(value) for _, pattern in _PATTERNS):
        return False
    kills = list(_KILL.finditer(value))
    reasons = list(_UNPROVOKED.finditer(value))
    if not kills or not reasons:
        return False
    return not any(
        _NEGATION_BEFORE.search(value[max(0, match.start() - 48):match.start()])
        or _NEGATION_AFTER.search(value[match.end():match.end() + 48])
        for match in [*kills, *reasons]
    )


def mentioned_term(text: str, lang: str) -> str | None:
    """Return one explicitly mentioned, non-negated term, or abstain.

    Multiple different terms are ambiguous. Short aliases are merely the
    player's description, not evidence that a violation took place.
    """
    value = normalize(text, lang)
    occupied: list[tuple[int, int]] = []
    matches: list[tuple[str, int, int]] = []
    for abbreviation, pattern in _PATTERNS:
        for match in pattern.finditer(value):
            start, end = match.span()
            if any(start < right and left < end for left, right in occupied):
                continue
            occupied.append((start, end))
            matches.append((abbreviation, start, end))
    if not matches:
        return None
    codes = {code for code, _, _ in matches}
    if len(codes) != 1:
        return None
    for _, start, end in matches:
        # Only direct local negation: "не согласен с баном за DM" is not
        # equivalent to "не DM". Sensitive cases are separately withheld.
        before, after = value[max(0, start - 48):start], value[end:end + 48]
        if _NEGATION_BEFORE.search(before) or _NEGATION_AFTER.search(after):
            return None
    return matches[0][0]
