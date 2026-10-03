"""The extractor contract.

``Extractor`` is a ``typing.Protocol``: any class with a matching ``name``
attribute and ``extract`` method *is* an Extractor - no inheritance needed.
This is "structural typing" (duck typing that the type checker understands).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Protocol

from actiongraph.domain.schemas import MeetingExtraction


@dataclass(frozen=True)
class OpenAction:
    """An unfinished action item from an earlier meeting, shown to the extractor
    so it can report progress on it instead of creating a duplicate."""

    id: int
    task: str
    owner: str | None
    deadline: str | None
    status: str


@dataclass(frozen=True)
class ExtractionRequest:
    transcript: str
    meeting_date: date
    meeting_title: str
    open_actions: list[OpenAction] = field(default_factory=list)
    known_people: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class TokenUsage:
    input_tokens: int
    output_tokens: int
    cache_read_input_tokens: int = 0
    cache_creation_input_tokens: int = 0


@dataclass(frozen=True)
class ExtractionResult:
    extraction: MeetingExtraction
    provider: str  # "anthropic", "offline", "fake", ...
    model: str  # the model that actually served the request
    latency_seconds: float
    usage: TokenUsage | None = None


class Extractor(Protocol):
    name: str

    def extract(self, request: ExtractionRequest) -> ExtractionResult: ...
