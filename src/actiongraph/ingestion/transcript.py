"""The ``Transcript`` data structure: the common output of every input format."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from actiongraph.domain.enums import SourceType

# "Priya: We'll update the API design."  or  "[00:01:12] Sam Lee: Sounds good."
# Group 1 = speaker name, group 2 = what they said.
_SPEAKER_LINE = re.compile(
    r"^\s*(?:\[[\d:.]+\]\s*)?"  # optional [hh:mm:ss] timestamp
    r"([@A-Z][\w@.'\- ]{0,40}?)"  # speaker: starts with a capital letter or @
    r"\s*:\s+(.+)$"
)


@dataclass
class Segment:
    """One stretch of speech, usually one speaker turn."""

    text: str
    speaker: str | None = None
    start: float | None = None  # seconds from the start of the recording
    end: float | None = None


@dataclass
class Transcript:
    segments: list[Segment]
    source_type: SourceType = SourceType.TEXT
    source_name: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)

    @property
    def text(self) -> str:
        """The transcript as "Speaker: text" lines - the format we send to the LLM."""
        return "\n".join(
            f"{seg.speaker}: {seg.text}" if seg.speaker else seg.text for seg in self.segments
        )

    @property
    def speakers(self) -> list[str]:
        """Unique speaker names in order of first appearance."""
        seen: dict[str, None] = {}
        for seg in self.segments:
            if seg.speaker:
                seen.setdefault(seg.speaker, None)
        return list(seen)

    @property
    def is_empty(self) -> bool:
        return not any(seg.text.strip() for seg in self.segments)

    @classmethod
    def from_text(
        cls,
        raw: str,
        source_type: SourceType = SourceType.TEXT,
        source_name: str | None = None,
    ) -> Transcript:
        """Parse plain text where lines may start with "Speaker:".

        Lines without a speaker prefix are treated as a continuation of the
        previous speaker's turn (people often paste wrapped text).
        """
        segments: list[Segment] = []
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            match = _SPEAKER_LINE.match(line)
            if match:
                segments.append(
                    Segment(text=match.group(2).strip(), speaker=match.group(1).strip())
                )
            elif segments:
                segments[-1].text += " " + line
            else:
                segments.append(Segment(text=line))
        return cls(segments=segments, source_type=source_type, source_name=source_name)


def split_speaker(line: str) -> tuple[str | None, str]:
    """Split "Speaker: text" into its parts; returns (None, line) when there is no speaker."""
    match = _SPEAKER_LINE.match(line)
    if match:
        return match.group(1).strip(), match.group(2).strip()
    return None, line.strip()
