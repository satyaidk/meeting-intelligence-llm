"""Small text helpers shared by grounding, deduplication and evaluation."""

from __future__ import annotations

import re
from collections.abc import Hashable, Sequence
from difflib import SequenceMatcher
from typing import TypeVar

K = TypeVar("K", bound=Hashable)

STOPWORDS = frozenset(
    """a an and are as at be by for from has have i in is it its of on or our please so that
    the their them this to up we will with you your can could would should need needs going
    get make do does done just also all some any about into out over then than there these
    those me my us he she they his her was were been being not no yes ok okay well let
    lets""".split()
)


def normalize_text(text: str) -> str:
    """Lower-case, unify quotes, drop punctuation, collapse whitespace.

    Apostrophes are removed without a space (``we'll`` -> ``well``) and other
    punctuation becomes a space, so both sides of a comparison are treated
    identically.
    """
    text = text.lower().replace("’", "'").replace("‘", "'")
    text = text.replace("'", "")
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _light_stem(word: str) -> str:
    # Plural -> singular is enough for our short task descriptions.
    if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def content_words(text: str) -> set[str]:
    """The meaningful words of a phrase (no stopwords, roughly singular)."""
    return {_light_stem(w) for w in normalize_text(text).split() if w not in STOPWORDS}


def similarity(a: str, b: str) -> float:
    """How alike two short phrases are, from 0.0 to 1.0.

    Average of two complementary measures:
    * word overlap (Jaccard) - robust to word order ("auth changes" vs "changes to auth")
    * character sequence ratio - robust to small spelling differences
    """
    norm_a, norm_b = normalize_text(a), normalize_text(b)
    if not norm_a or not norm_b:
        return 0.0
    words_a, words_b = content_words(a), content_words(b)
    union = words_a | words_b
    jaccard = len(words_a & words_b) / len(union) if union else 0.0
    sequence = SequenceMatcher(None, norm_a, norm_b).ratio()
    return round(0.5 * jaccard + 0.5 * sequence, 3)


def best_match(
    query: str, candidates: Sequence[tuple[K, str]], threshold: float
) -> tuple[K, float] | None:
    """Return ``(key, score)`` of the candidate text most similar to ``query``.

    ``candidates`` is a list of ``(key, text)`` pairs. Returns ``None`` if the
    best score is below ``threshold``.
    """
    best: tuple[K, float] | None = None
    for key, text in candidates:
        score = similarity(query, text)
        if score >= threshold and (best is None or score > best[1]):
            best = (key, score)
    return best
