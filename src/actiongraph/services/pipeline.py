"""The meeting-processing pipeline.

This file is the best place to start reading the code: ``MeetingProcessor.process``
follows the architecture diagram stage by stage.

    Transcript
      |  1. load context: open actions + known people from earlier meetings
      |  2. extract:      LLM (or rules) -> MeetingExtraction       [slow, costs money]
      |  3. save meeting
      |  4. resolve people ("Priya S." -> Priya Sharma)
      |  5. actions:      ground -> resolve deadline -> score -> dedupe -> save
      |  6. decisions:    ground -> score -> save
      |  7. status updates on earlier actions: validate -> score -> apply or queue
      |  8. risks:        ground -> score -> link to the action they block -> save
      v  9. commit (all-or-nothing)
    ProcessingReport

Design notes:
* The LLM call happens *before* anything is written, and everything is
  committed in one transaction at the end. A failure leaves the database untouched.
* Stages 4-8 use only deterministic code, so their behaviour is fully unit-tested.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from actiongraph.domain.enums import ActionStatus, EventType, ReviewStatus
from actiongraph.enrichment.confidence import deadline_reasons, review_action, review_item
from actiongraph.enrichment.entity_resolution import EntityResolver, OwnerResolution
from actiongraph.enrichment.grounding import ground_evidence
from actiongraph.enrichment.temporal import resolve_deadline
from actiongraph.errors import IngestionError
from actiongraph.extraction.base import (
    ExtractionRequest,
    ExtractionResult,
    Extractor,
    OpenAction,
    TokenUsage,
)
from actiongraph.ingestion.transcript import Transcript
from actiongraph.services.tracking import (
    apply_event,
    describe_change,
    find_blocked_action,
    find_duplicate,
)
from actiongraph.storage.models import ActionEvent, ActionItem, Decision, Meeting, Person, Risk
from actiongraph.storage.repository import Repository

logger = logging.getLogger(__name__)


@dataclass
class ProcessingReport:
    """What happened while processing one meeting (returned by the API and CLI)."""

    meeting_id: int
    provider: str
    model: str
    latency_seconds: float
    usage: TokenUsage | None = None
    actions_created: int = 0
    decisions_created: int = 0
    risks_created: int = 0
    status_updates_applied: int = 0
    status_updates_pending: int = 0
    duplicates_merged: int = 0
    items_needing_review: int = 0
    warnings: list[str] = field(default_factory=list)


class MeetingProcessor:
    def __init__(self, session: Session, extractor: Extractor, review_threshold: float = 0.7):
        self.session = session
        self.repo = Repository(session)
        self.extractor = extractor
        self.threshold = review_threshold

    def process(
        self, transcript: Transcript, *, title: str, meeting_date: date
    ) -> ProcessingReport:
        if transcript.is_empty:
            raise IngestionError("The transcript is empty.")
        try:
            report = self._process(transcript, title=title, meeting_date=meeting_date)
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
        logger.info(
            "Meeting %d processed: %d actions, %d decisions, %d risks, %d updates applied, "
            "%d need review",
            report.meeting_id, report.actions_created, report.decisions_created,
            report.risks_created, report.status_updates_applied, report.items_needing_review,
        )  # fmt: skip
        return report

    def _process(
        self, transcript: Transcript, *, title: str, meeting_date: date
    ) -> ProcessingReport:
        text = transcript.text

        # 1. Context from earlier meetings ---------------------------------
        open_actions = list(self.repo.open_actions())
        resolver = EntityResolver(self.repo.known_people())

        # 2. Extraction -------------------------------------------------------
        request = ExtractionRequest(
            transcript=text,
            meeting_date=meeting_date,
            meeting_title=title,
            open_actions=[
                OpenAction(a.id, a.task, a.owner_name, a.deadline_text, a.status)
                for a in open_actions
            ],
            known_people=[p.display_name for p in resolver.people],
        )
        result = self.extractor.extract(request)
        extraction = result.extraction
        logger.info(
            "Extracted with %s/%s in %.1fs", result.provider, result.model, result.latency_seconds
        )

        # 3. Save the meeting -------------------------------------------------
        meeting = self._save_meeting(transcript, title, meeting_date, result)
        report = ProcessingReport(
            meeting_id=meeting.id,
            provider=result.provider,
            model=result.model,
            latency_seconds=result.latency_seconds,
            usage=result.usage,
        )

        # 4. People: register speakers first so later mentions resolve to them
        for name in dict.fromkeys([*transcript.speakers, *extraction.participants]):
            resolver.resolve(name)
        action_owners = [resolver.resolve(a.owner) for a in extraction.actions]
        decision_makers = [resolver.resolve(d.made_by) for d in extraction.decisions]
        people = {known.key: self.repo.save_person(known) for known in resolver.people}

        def person_for(resolution: OwnerResolution) -> Person | None:
            return people[resolution.person.key] if resolution.person else None

        # 5. New action items ---------------------------------------------------
        new_actions: list[ActionItem] = []
        for item, owner in zip(extraction.actions, action_owners, strict=True):
            grounding = ground_evidence(item.evidence, text)
            deadline = resolve_deadline(item.deadline_text, meeting_date)
            review = review_action(item.confidence, grounding, owner, deadline, self.threshold)
            owner_person = person_for(owner)

            duplicate = find_duplicate(
                item.task, owner_person.id if owner_person else None, open_actions
            )
            if duplicate is not None:
                self._add_event(
                    duplicate,
                    meeting=meeting,
                    event_type=EventType.MENTIONED,
                    from_status=duplicate.status,
                    to_status=duplicate.status,
                    note=f"Mentioned again as '{item.task}'.",
                    evidence=item.evidence,
                    confidence=review.confidence,
                    review_status=ReviewStatus.AUTO_APPROVED,
                    applied=True,
                )
                report.duplicates_merged += 1
                continue

            action = ActionItem(
                meeting=meeting,
                task=item.task,
                owner=owner_person,
                owner_raw=item.owner,
                is_team_owned=owner.is_team,
                deadline_text=item.deadline_text,
                due_date=deadline.due_date,
                status=ActionStatus.OPEN,
                confidence=review.confidence,
                evidence=item.evidence,
                review_status=review.status,
                review_reasons=list(review.reasons),
            )
            self.session.add(action)
            self._add_event(
                action,
                meeting=meeting,
                event_type=EventType.CREATED,
                to_status=ActionStatus.OPEN,
                deadline_text=item.deadline_text,
                due_date=deadline.due_date,
                note=f"Created in '{title}'.",
                evidence=item.evidence,
                confidence=review.confidence,
                review_status=ReviewStatus.AUTO_APPROVED,
                applied=True,
            )
            new_actions.append(action)
            report.actions_created += 1
            report.items_needing_review += review.needs_review
        self.session.flush()  # give the new actions ids (risks may link to them)

        # 6. Decisions --------------------------------------------------------------
        for item, maker in zip(extraction.decisions, decision_makers, strict=True):
            review = review_item(
                item.confidence, ground_evidence(item.evidence, text), self.threshold
            )
            self.session.add(
                Decision(
                    meeting=meeting,
                    text=item.decision,
                    made_by=person_for(maker),
                    made_by_raw=item.made_by,
                    evidence=item.evidence,
                    confidence=review.confidence,
                    review_status=review.status,
                    review_reasons=list(review.reasons),
                )
            )
            report.decisions_created += 1
            report.items_needing_review += review.needs_review

        # 7. Status updates on earlier actions -----------------------------------
        open_by_id = {a.id: a for a in open_actions}
        updated_ids: set[int] = set()
        for update in extraction.status_updates:
            action = open_by_id.get(update.action_id)
            if action is None:
                # The model referenced an id we never gave it: a hallucination.
                report.warnings.append(
                    f"Ignored a status update for unknown action id {update.action_id}."
                )
                continue
            if update.action_id in updated_ids:
                report.warnings.append(f"Ignored a second status update for action {action.id}.")
                continue
            updated_ids.add(update.action_id)

            deadline = resolve_deadline(update.new_deadline_text, meeting_date)
            review = review_item(
                update.confidence,
                ground_evidence(update.evidence, text),
                self.threshold,
                extra_reasons=deadline_reasons(deadline),
            )
            # Discussed, but nothing actually changed -> just note the mention.
            unchanged = update.new_status == action.status and not update.new_deadline_text
            event = self._add_event(
                action,
                meeting=meeting,
                event_type=EventType.MENTIONED
                if unchanged
                else describe_change(action.status, update.new_status, update.new_deadline_text),
                from_status=action.status,
                to_status=update.new_status,
                deadline_text=update.new_deadline_text,
                due_date=deadline.due_date,
                note=update.note,
                evidence=update.evidence,
                confidence=review.confidence,
                review_status=ReviewStatus.AUTO_APPROVED if unchanged else review.status,
                review_reasons=[] if unchanged else list(review.reasons),
                applied=unchanged,
            )

            if unchanged:
                continue
            if review.needs_review:
                report.status_updates_pending += 1
                report.items_needing_review += 1
            else:
                apply_event(event)
                report.status_updates_applied += 1

        # 8. Risks and blockers ---------------------------------------------------
        link_candidates = new_actions + open_actions
        for item in extraction.risks:
            review = review_item(
                item.confidence, ground_evidence(item.evidence, text), self.threshold
            )
            blocked = find_blocked_action(item.blocks_task, link_candidates)
            if item.blocks_task and blocked is None:
                report.warnings.append(
                    f"Risk '{item.description[:60]}' names a blocked task that matched no action."
                )
            self.session.add(
                Risk(
                    meeting=meeting,
                    description=item.description,
                    kind=item.kind,
                    severity=item.severity,
                    blocks_action=blocked,
                    evidence=item.evidence,
                    confidence=review.confidence,
                    review_status=review.status,
                    review_reasons=list(review.reasons),
                )
            )
            report.risks_created += 1
            report.items_needing_review += review.needs_review

        # 9. Commit happens in process() ------------------------------------------
        return report

    def _add_event(self, action: ActionItem, **fields: Any) -> ActionEvent:
        # no_autoflush: appending to action.events may lazy-load that list from
        # the database, and SQLAlchemy would otherwise try to save the
        # half-attached event first and warn about it.
        with self.session.no_autoflush:
            event = ActionEvent(**fields)
            action.events.append(event)
        return event

    def _save_meeting(
        self, transcript: Transcript, title: str, meeting_date: date, result: ExtractionResult
    ) -> Meeting:
        meeting = Meeting(
            title=title,
            meeting_date=meeting_date,
            source_type=transcript.source_type,
            source_name=transcript.source_name,
            transcript=transcript.text,
            summary=result.extraction.summary,
            participants=result.extraction.participants or transcript.speakers,
            llm_provider=result.provider,
            llm_model=result.model,
            llm_usage=asdict(result.usage) if result.usage else None,
            latency_seconds=result.latency_seconds,
        )
        self.session.add(meeting)
        self.session.flush()
        return meeting
