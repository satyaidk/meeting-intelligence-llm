"""Extraction layer: Transcript -> MeetingExtraction.

    base.py                 The ``Extractor`` interface every implementation follows
    prompts.py              System prompt + how the user message is assembled
    anthropic_extractor.py  Real extraction with Claude (structured outputs)
    rule_based.py           Offline regex baseline - no API key, no cost
    factory.py              Picks an implementation from settings

Because the rest of the system only depends on the ``Extractor`` interface,
swapping the LLM (or using a fake one in tests) needs no other code changes.
"""

from actiongraph.extraction.base import (
    ExtractionRequest,
    ExtractionResult,
    Extractor,
    OpenAction,
    TokenUsage,
)
from actiongraph.extraction.factory import build_extractor

__all__ = [
    "ExtractionRequest",
    "ExtractionResult",
    "Extractor",
    "OpenAction",
    "TokenUsage",
    "build_extractor",
]
