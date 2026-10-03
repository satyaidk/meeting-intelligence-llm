"""The LLM output contract.

These Pydantic models are the single most important design artefact in the
project. They are used three ways:

1. **As instructions.** The SDK converts ``MeetingExtraction`` to a JSON
   schema and sends it to Claude. Every ``description=`` below is read by the
   model, so descriptions are written like prompt text.
2. **As a constraint.** With structured outputs the API guarantees the reply
   is valid JSON that matches this schema - no regex-parsing of free text.
3. **As validation.** Pydantic re-checks the reply (e.g. ``confidence`` must be
   between 0 and 1) before any of our code touches it.

Design choices worth noticing (see docs/adr/0004-structured-outputs.md):

* Every field is required, even the nullable ones. The model must say
  ``"owner": null`` explicitly, which is less ambiguous than omitting the key.
* The LLM copies ``deadline_text`` verbatim and does **not** compute dates.
  Calendar maths is done by deterministic code (``enrichment/temporal.py``).
* Every item carries an ``evidence`` quote so we can verify it against the
  transcript (``enrichment/grounding.py``) and catch hallucinations.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from actiongraph.domain.enums import ActionStatus, RiskKind, Severity

_CONFIDENCE = (
    "Your confidence from 0.0 to 1.0. Use 0.9+ for explicit commitments with a clear owner, "
    "0.6-0.8 when the item is implied, and below 0.5 when it is speculative."
)
_EVIDENCE = (
    "A short verbatim quote (one sentence) copied exactly from the transcript that "
    "supports this item. Do not paraphrase."
)


class ExtractedAction(BaseModel):
    """A commitment for someone to do something after the meeting."""

    task: str = Field(
        description="Short imperative description of the work, e.g. 'Update the API design'."
    )
    owner: str | None = Field(
        description=(
            "Who is responsible, written the way the transcript names them (e.g. 'Priya', "
            "'@sam'). Resolve 'I'/'I'll' to the speaker's name. Use 'Team' when the group "
            "as a whole owns it ('we will...'). null when nobody is named."
        )
    )
    deadline_text: str | None = Field(
        description=(
            "The deadline phrase copied from the transcript, e.g. 'by Friday', 'next week', "
            "'before the next release'. Do NOT convert it to a date. null when none is given."
        )
    )
    evidence: str = Field(description=_EVIDENCE)
    confidence: float = Field(ge=0.0, le=1.0, description=_CONFIDENCE)


class ExtractedDecision(BaseModel):
    """A choice the group agreed on."""

    decision: str = Field(description="What was decided, as one clear sentence.")
    made_by: str | None = Field(
        description="Person who made or announced the decision, or 'Team' if collective."
    )
    evidence: str = Field(description=_EVIDENCE)
    confidence: float = Field(ge=0.0, le=1.0, description=_CONFIDENCE)


class ExtractedRisk(BaseModel):
    """Something that could stop or delay work."""

    description: str = Field(description="The risk or blocker in one sentence.")
    kind: RiskKind = Field(
        description="'blocker' if it is stopping work right now, 'risk' if it might cause problems."
    )
    severity: Severity
    blocks_task: str | None = Field(
        description=(
            "If this blocks a specific action item (new or already open), that item's task "
            "text. null otherwise."
        )
    )
    evidence: str = Field(description=_EVIDENCE)
    confidence: float = Field(ge=0.0, le=1.0, description=_CONFIDENCE)


class ExtractedStatusUpdate(BaseModel):
    """Progress reported on an action item created in an *earlier* meeting."""

    action_id: int = Field(
        description="The id of the item from <open_action_items>. Never invent an id."
    )
    new_status: ActionStatus = Field(
        description="The item's status after this meeting ('done', 'blocked', 'in_progress', ...)."
    )
    new_deadline_text: str | None = Field(
        description="If the deadline moved, the new deadline phrase verbatim. null otherwise."
    )
    note: str = Field(description="One sentence describing what changed.")
    evidence: str = Field(description=_EVIDENCE)
    confidence: float = Field(ge=0.0, le=1.0, description=_CONFIDENCE)


class MeetingExtraction(BaseModel):
    """Everything the extractor found in one meeting. Return empty lists when nothing applies."""

    summary: str = Field(description="2-4 sentence neutral summary of the meeting.")
    participants: list[str] = Field(description="Names of the people who spoke.")
    decisions: list[ExtractedDecision]
    actions: list[ExtractedAction] = Field(
        description="NEW action items only. Progress on already-open items goes in status_updates."
    )
    risks: list[ExtractedRisk]
    status_updates: list[ExtractedStatusUpdate]
