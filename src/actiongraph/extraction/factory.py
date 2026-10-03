"""Choose an extractor implementation from configuration (the "factory" pattern)."""

from __future__ import annotations

from actiongraph.config import Settings
from actiongraph.extraction.base import Extractor


def build_extractor(settings: Settings) -> Extractor:
    if settings.llm_provider == "offline":
        from actiongraph.extraction.rule_based import RuleBasedExtractor

        return RuleBasedExtractor()

    from actiongraph.extraction.anthropic_extractor import AnthropicExtractor

    return AnthropicExtractor.from_settings(settings)
