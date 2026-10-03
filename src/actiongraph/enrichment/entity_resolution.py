"""Entity resolution: decide which *person* a name refers to.

Meetings refer to the same human in many ways::

    "Priya"   "Priya S."   "@priya"   "priya.sharma@acme.com"   "Priya Sharma"

If each spelling became its own person, the tracker would show five people
with one task each. The resolver maps every spelling onto one ``KnownPerson``
using a ladder of increasingly fuzzy rules, and *refuses to guess* when a name
could mean two different people - that case is sent to human review.

Rules, tried in order (first match wins):

    1. Team words ("we", "team", "everyone")  ->  no person, owned by the team
    2. Exact alias match                       ->  confidence 1.0
    3. Compatible name ("Priya S." ~ "Priya Sharma")  ->  0.9
    4. Close spelling ("Pryia" ~ "Priya")      ->  similarity x 0.9, flagged for review
    5. Otherwise a brand-new person            ->  0.85
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from enum import StrEnum

TEAM_ALIASES = frozenset(
    {
        "team",
        "the team",
        "whole team",
        "the whole team",
        "we",
        "us",
        "everyone",
        "everybody",
        "all",
        "all of us",
        "group",
        "the group",
    }
)
_HONORIFICS = frozenset({"mr", "mrs", "ms", "miss", "dr", "prof"})
FUZZY_THRESHOLD = 0.8


class ResolutionMethod(StrEnum):
    EXACT = "exact"
    PARTIAL = "partial"
    FUZZY = "fuzzy"
    NEW = "new"
    TEAM = "team"
    AMBIGUOUS = "ambiguous"
    NONE = "none"


@dataclass
class KnownPerson:
    """A person the resolver knows about.

    ``key`` is the database id as a string for stored people, or ``"new:N"``
    for people first seen in the current meeting (not saved yet).
    """

    key: str
    display_name: str
    aliases: set[str] = field(default_factory=set)

    @property
    def is_new(self) -> bool:
        return self.key.startswith("new:")

    def add_alias(self, raw: str) -> None:
        norm = normalize_person_name(raw)
        if not norm:
            return
        self.aliases.add(norm)
        # Prefer the most complete spelling as the display name:
        # "Priya" -> "Priya S." -> "Priya Sharma"
        if len(norm) > len(normalize_person_name(self.display_name)):
            self.display_name = display_name_for(raw)


@dataclass(frozen=True)
class OwnerResolution:
    raw: str | None
    person: KnownPerson | None
    method: ResolutionMethod
    confidence: float
    candidates: tuple[str, ...] = ()  # filled in when the name is ambiguous

    @property
    def is_team(self) -> bool:
        return self.method is ResolutionMethod.TEAM


def normalize_person_name(raw: str) -> str:
    """Reduce any spelling of a name to a comparable key.

    >>> normalize_person_name("@Priya.Sharma")
    'priya sharma'
    >>> normalize_person_name("priya.sharma@acme.com")
    'priya sharma'
    >>> normalize_person_name("Priya S.")
    'priya s'
    """
    text = raw.strip()
    if "@" in text[1:]:  # an email address: keep the part before @
        text = text.split("@", 1)[0]
    text = text.lstrip("@")
    text = re.sub(r"[._\-]+", " ", text)
    text = re.sub(r"[^\w\s]", "", text)
    return " ".join(t for t in text.lower().split() if t not in _HONORIFICS)


def display_name_for(raw: str) -> str:
    """A human-friendly version of a raw name ("@sam" -> "Sam")."""
    cleaned = raw.strip().lstrip("@")
    if "@" in cleaned or "_" in cleaned or cleaned.islower() or re.search(r"\w\.\w", cleaned):
        return normalize_person_name(raw).title()
    return re.sub(r"\s+", " ", cleaned)


def names_compatible(a: str, b: str) -> bool:
    """True when two normalised names could be the same person.

    First names must match exactly; later tokens must match or be an initial
    of each other. ``"priya s"`` ~ ``"priya sharma"`` but not ``"priya k"``.
    """
    tokens_a, tokens_b = a.split(), b.split()
    if not tokens_a or not tokens_b or tokens_a[0] != tokens_b[0]:
        return False
    for x, y in zip(tokens_a[1:], tokens_b[1:], strict=False):
        if x == y or (len(x) == 1 and y.startswith(x)) or (len(y) == 1 and x.startswith(y)):
            continue
        return False
    return True


class EntityResolver:
    """Resolves raw names against a growing registry of people.

    New people discovered while processing a meeting are added to the
    registry, so "Priya" and "Priya S." in the *same* meeting also merge.
    """

    def __init__(self, people: Iterable[KnownPerson] = ()) -> None:
        self.people: list[KnownPerson] = list(people)
        self._new_count = 0

    def resolve(self, raw: str | None) -> OwnerResolution:
        norm = normalize_person_name(raw) if raw else ""
        if not norm:
            return OwnerResolution(raw, None, ResolutionMethod.NONE, 0.0)
        if norm in TEAM_ALIASES:
            return OwnerResolution(raw, None, ResolutionMethod.TEAM, 1.0)

        # Rule 2: exact alias
        exact = [p for p in self.people if norm in p.aliases]
        if len(exact) == 1:
            return self._matched(raw, exact[0], ResolutionMethod.EXACT, 1.0)
        if len(exact) > 1:
            return self._ambiguous(raw, exact)

        # Rule 3: compatible names
        compatible = [p for p in self.people if self._is_compatible(norm, p)]
        if len(compatible) == 1:
            return self._matched(raw, compatible[0], ResolutionMethod.PARTIAL, 0.9)
        if len(compatible) > 1:
            return self._ambiguous(raw, compatible)

        # Rule 4: close spelling (typos, transcription errors)
        best_score, best_person = 0.0, None
        for person in self.people:
            for alias in person.aliases:
                score = SequenceMatcher(None, norm, alias).ratio()
                if score > best_score:
                    best_score, best_person = score, person
        if best_person is not None and best_score >= FUZZY_THRESHOLD:
            return self._matched(
                raw, best_person, ResolutionMethod.FUZZY, round(best_score * 0.9, 3)
            )

        # Rule 5: someone we have not met before
        return self._create(raw, norm)

    @staticmethod
    def _is_compatible(norm: str, person: KnownPerson) -> bool:
        # Compatible with at least one alias, and with every multi-word alias:
        # "priya kumar" must NOT match someone already known as "priya sharma".
        if not any(names_compatible(norm, alias) for alias in person.aliases):
            return False
        return all(names_compatible(norm, a) for a in person.aliases if len(a.split()) > 1)

    def _matched(
        self, raw: str, person: KnownPerson, method: ResolutionMethod, confidence: float
    ) -> OwnerResolution:
        person.add_alias(raw)
        return OwnerResolution(raw, person, method, confidence)

    @staticmethod
    def _ambiguous(raw: str, people: list[KnownPerson]) -> OwnerResolution:
        names = tuple(sorted(p.display_name for p in people))
        return OwnerResolution(raw, None, ResolutionMethod.AMBIGUOUS, 0.3, candidates=names)

    def _create(self, raw: str, norm: str) -> OwnerResolution:
        self._new_count += 1
        person = KnownPerson(
            key=f"new:{self._new_count}", display_name=display_name_for(raw), aliases={norm}
        )
        self.people.append(person)
        return OwnerResolution(raw, person, ResolutionMethod.NEW, 0.85)
