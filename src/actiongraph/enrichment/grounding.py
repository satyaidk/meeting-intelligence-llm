"""Evidence grounding: a cheap, effective hallucination check.

Every extracted item comes with an ``evidence`` quote. If the quote does not
actually appear in the transcript, the model either paraphrased heavily or
made the item up - either way a human should look at it.

The score is the fraction of the quote's words that appear, in order, in one
nearby stretch of the transcript:

    1.0   exact (after normalising case and punctuation)
    ~0.85 a filler word was dropped ("we'll, um, update" -> "we'll update")
    <0.5  not really there
"""

from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher

from actiongraph.enrichment.text_utils import normalize_text

GROUNDED_THRESHOLD = 0.8


@dataclass(frozen=True)
class GroundingResult:
    score: float

    @property
    def is_grounded(self) -> bool:
        return self.score >= GROUNDED_THRESHOLD


def ground_evidence(evidence: str, transcript: str) -> GroundingResult:
    quote_words = normalize_text(evidence).split()
    if not quote_words:
        return GroundingResult(0.0)

    transcript_norm = normalize_text(transcript)
    if " ".join(quote_words) in transcript_norm:
        return GroundingResult(1.0)

    transcript_words = transcript_norm.split()
    # autojunk=False: by default difflib ignores "popular" items in long
    # sequences, which would make common words invisible to the matcher.
    matcher = SequenceMatcher(None, quote_words, transcript_words, autojunk=False)
    anchor = matcher.find_longest_match(0, len(quote_words), 0, len(transcript_words))
    if anchor.size == 0:
        return GroundingResult(0.0)

    # Look at a window of the transcript around the longest exact run and
    # count how many quote words appear there in order (tolerates small edits).
    start = max(0, anchor.b - anchor.a)
    window = transcript_words[start : start + int(len(quote_words) * 1.5) + 2]
    window_matcher = SequenceMatcher(None, quote_words, window, autojunk=False)
    matched = sum(block.size for block in window_matcher.get_matching_blocks())

    score = max(anchor.size, matched) / len(quote_words)
    return GroundingResult(round(min(score, 1.0), 3))
