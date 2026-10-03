"""Offline, rule-based extractor (the "before LLMs" baseline).

Why keep a regex extractor in an LLM project?

1. **Run everything without an API key.** The full pipeline, API, UI and
   tests work offline, which makes the project easy to try and to learn from.
2. **A baseline to beat.** ``actiongraph eval`` scores both extractors on the
   same labelled data, so you can *measure* what the LLM adds instead of
   assuming it.
3. **It teaches why LLMs are needed.** Read the patterns below and you will see
   how quickly hand-written rules become brittle: "Will do." vs "I'll do it",
   hedges ("maybe"), pronouns ("push *it* to next week"), and so on.

It returns the same ``MeetingExtraction`` schema as the LLM extractor, so the
rest of the pipeline cannot tell the difference.
"""

from __future__ import annotations

import re
import time

from actiongraph.domain.enums import ActionStatus, RiskKind, Severity
from actiongraph.domain.schemas import (
    ExtractedAction,
    ExtractedDecision,
    ExtractedRisk,
    ExtractedStatusUpdate,
    MeetingExtraction,
)
from actiongraph.enrichment.entity_resolution import TEAM_ALIASES
from actiongraph.enrichment.text_utils import content_words
from actiongraph.extraction.base import ExtractionRequest, ExtractionResult, OpenAction
from actiongraph.ingestion.transcript import Transcript

_NAME = r"@\w+|[A-Z][a-z]+(?: [A-Z]\.| [A-Z][a-z]+)?"
_NOT_NAMES = frozenset(
    """i we you they he she it this that there someone somebody nobody yes no ok okay good
    great so and also well now then sure thanks alright right perfect cool fine""".split()
)

# --- action patterns: (regex, owner rule, base confidence) -----------------
_REQUEST = re.compile(  # "Sam, please share the research"  /  "@priya, once X, please pair..."
    rf"^(?P<owner>{_NAME}),\s+(?:[^,]+,\s+)?(?:please|can you|could you|would you)\s+(?P<task>.+)$"
)
_NAMED_WILL = re.compile(  # "Priya will handle the authentication changes"
    rf"\b(?P<owner>{_NAME})\s+(?:will|is going to|is gonna)\s+(?P<task>.+)$"
)
_SELF = re.compile(  # "I'll draft the email" -> the speaker owns it
    r"\bI(?:'ll| will| am going to|'m going to|'m gonna| can)\s+(?P<task>.+)$"
)
_TEAM = re.compile(  # "We'll update the API design"
    r"\b[Ww]e(?:'ll| will| need to| must| have to| should| are going to|'re going to)"
    r"\s+(?P<task>.+)$"
)
_EXPLICIT = re.compile(r"\b(?:action item|todo|to-do)s?\s*[:\-]\s*(?P<task>.+)$", re.IGNORECASE)

_DECISION = re.compile(
    r"\b(?:we(?:'ve| have)? decided|decision\s*:|we agreed|agreed (?:to|that|on)|"
    r"we(?:'re| are) going with|let's go with|we(?:'ll| will) go with|final call)\b",
    re.IGNORECASE,
)
_RISK = re.compile(
    r"\b(blocked|blocker|blocking|stuck|waiting (?:on|for)|risks?|risky|concerns?|concerned|"
    r"worried|depends on|dependency|delays?|slips?)\b",
    re.IGNORECASE,
)
_BLOCKER_WORDS = re.compile(r"\b(blocked|blocker|blocking|stuck|waiting)\b", re.IGNORECASE)
_HIGH_SEVERITY = re.compile(r"\b(critical|major|serious|severe|urgent)\b", re.IGNORECASE)
_HEDGE = re.compile(r"\b(maybe|might|perhaps|possibly|at some point|some ?day)\b", re.IGNORECASE)

_DEADLINE = re.compile(
    r"\b(?:by|before|until|due|no later than)\s+(?:the\s+)?(?:"
    r"end of (?:the )?(?:day|week|month|quarter|year|next week|next month)"
    r"|next \w+|this \w+|tomorrow|today|eod|eow|\w+day"
    r"|(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.? \d{1,2}(?:st|nd|rd|th)?"
    r"|\d{4}-\d{2}-\d{2})"
    r"|\b(?:today|tomorrow|tonight|next week|this week|end of (?:the )?(?:day|week|month))\b",
    re.IGNORECASE,
)
_NEW_DEADLINE = re.compile(  # "push it to next Wednesday"
    r"\b(?:to|until|till)\s+((?:next|this)\s+\w+|\w+day\b|"
    r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.? \d{1,2}(?:st|nd|rd|th)?)",
    re.IGNORECASE,
)

_STATUS_CUES: list[tuple[ActionStatus, re.Pattern[str]]] = [
    (ActionStatus.BLOCKED, re.compile(r"\b(blocked|stuck|waiting on|waiting for|on hold)\b", re.I)),
    (ActionStatus.DONE, re.compile(
        r"\b(done|finished|complete|completed|shipped|merged|delivered|shared|sent|submitted|"
        r"wrapped up|closed)\b", re.I)),
    (ActionStatus.IN_PROGRESS, re.compile(
        r"\b(in progress|working on|started|underway|migrating|halfway|mostly)\b", re.I)),
]  # fmt: skip
_POSTPONE = re.compile(
    r"\b(?:push(?:ed)?(?: it)?(?: back)? to|postponed?|delay(?:ed)?(?: it)? (?:to|until)|"
    r"move[d]?(?: it)? to|slip(?:ped)? to|reschedule[d]? (?:to|for)|extend(?:ed)?(?: it)? to)\b",
    re.IGNORECASE,
)
_VAGUE_TASK = re.compile(
    r"^(?:take care of|do|handle|look into|check|own|take)\s+(?:it|that|this|them)$", re.I
)


class RuleBasedExtractor:
    name = "offline"

    def extract(self, request: ExtractionRequest) -> ExtractionResult:
        started = time.perf_counter()
        transcript = Transcript.from_text(request.transcript.replace("’", "'"))

        decisions: list[ExtractedDecision] = []
        actions: list[ExtractedAction] = []
        risks: list[ExtractedRisk] = []
        updates: dict[int, ExtractedStatusUpdate] = {}

        for segment in transcript.segments:
            current_action: OpenAction | None = None  # open item this turn is talking about
            risk_found = False
            for sentence in _split_sentences(segment.text):
                matched = _best_open_action(sentence, request.open_actions)
                current_action = matched or current_action

                if current_action and (update := _status_update(sentence, current_action, updates)):
                    updates[current_action.id] = update
                    status_sentence = True
                else:
                    status_sentence = False

                if not risk_found and (risk := _risk(sentence, request.open_actions, actions)):
                    risks.append(risk)
                    risk_found = True  # one risk per speaker turn keeps duplicates down

                if _DECISION.search(sentence):
                    decision = re.sub(r"^decision\s*:\s*", "", sentence, flags=re.I)
                    decisions.append(
                        ExtractedDecision(
                            decision=decision,
                            made_by=segment.speaker,
                            evidence=sentence,
                            confidence=0.8,
                        )
                    )
                elif not status_sentence and (action := _action(sentence, segment.speaker)):
                    if all(a.task.lower() != action.task.lower() for a in actions):
                        actions.append(action)

        extraction = MeetingExtraction(
            summary=_summary(transcript, decisions, actions, risks, updates),
            participants=transcript.speakers,
            decisions=decisions,
            actions=actions,
            risks=risks,
            status_updates=list(updates.values()),
        )
        return ExtractionResult(
            extraction=extraction,
            provider=self.name,
            model="rule-based-v1",
            latency_seconds=round(time.perf_counter() - started, 3),
        )


def _split_sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


def _action(sentence: str, speaker: str | None) -> ExtractedAction | None:
    owner: str | None
    if m := _REQUEST.search(sentence):
        owner, task, confidence = m["owner"], m["task"], 0.8
    elif (m := _NAMED_WILL.search(sentence)) and m["owner"].lower() not in _NOT_NAMES:
        owner, task, confidence = m["owner"], m["task"], 0.75
        if owner.lower() in TEAM_ALIASES:
            owner = "Team"
    elif m := _SELF.search(sentence):
        is_offer = " can " in m.group(0)
        owner, task, confidence = speaker, m["task"], 0.6 if is_offer else 0.75
    elif m := _TEAM.search(sentence):
        owner, task, confidence = "Team", m["task"], 0.7
    elif m := _EXPLICIT.search(sentence):
        owner, task, confidence = None, m["task"], 0.7
    else:
        return None

    if owner and owner.split()[0].lower() in _NOT_NAMES:
        return None
    deadline_match = _DEADLINE.search(task)
    deadline = deadline_match.group(0) if deadline_match else None
    if deadline_match:
        task = task.replace(deadline_match.group(0), " ")
        confidence += 0.1
    task = _clean_task(task)
    if not task or _VAGUE_TASK.match(task) or len(task.split()) < 2:
        return None
    if _HEDGE.search(sentence):
        confidence = 0.4
    return ExtractedAction(
        task=task,
        owner=owner,
        deadline_text=deadline,
        evidence=sentence,
        confidence=round(min(confidence, 0.9), 2),
    )


def _clean_task(task: str) -> str:
    # Cut off purpose/condition clauses: "update X so the team can review it" -> "update X"
    task = re.split(r"\s+(?:so that|so|because|since|once|if|when|which)\s+", task, maxsplit=1)[0]
    previous = None
    while previous != task:
        previous = task
        task = re.sub(
            r"^(?:also|just|then|probably|definitely|quickly|go ahead and|try to|please)\s+",
            "", task.strip(), flags=re.IGNORECASE,
        )  # fmt: skip
    task = re.sub(r"\s+", " ", task).strip(" .!?,;")
    return task[:1].upper() + task[1:]


def _risk(
    sentence: str, open_actions: list[OpenAction], new_actions: list[ExtractedAction]
) -> ExtractedRisk | None:
    if not _RISK.search(sentence) or len(sentence.split()) < 5:
        return None
    candidates = [a.task for a in open_actions] + [a.task for a in new_actions]
    blocks = _best_overlap(sentence, candidates)
    return ExtractedRisk(
        description=sentence,
        kind=RiskKind.BLOCKER if _BLOCKER_WORDS.search(sentence) else RiskKind.RISK,
        severity=Severity.HIGH if _HIGH_SEVERITY.search(sentence) else Severity.MEDIUM,
        blocks_task=blocks,
        evidence=sentence,
        confidence=0.7,
    )


def _overlap_score(sentence_words: set[str], task: str) -> float:
    # Long words ("authentication", "staging") are more distinctive than short ones.
    shared = sentence_words & content_words(task)
    return sum(1.0 if len(w) >= 7 else 0.5 for w in shared)


def _best_overlap(sentence: str, tasks: list[str]) -> str | None:
    words = content_words(sentence)
    scored = [(_overlap_score(words, t), t) for t in tasks]
    best = max(scored, default=(0.0, None))
    return best[1] if best[0] >= 1.0 else None


def _best_open_action(sentence: str, open_actions: list[OpenAction]) -> OpenAction | None:
    words = content_words(sentence)
    best_score, best = 0.0, None
    for action in open_actions:
        score = _overlap_score(words, action.task)
        if score > best_score:
            best_score, best = score, action
    return best if best_score >= 1.0 else None


def _status_update(
    sentence: str, action: OpenAction, existing: dict[int, ExtractedStatusUpdate]
) -> ExtractedStatusUpdate | None:
    previous = existing.get(action.id)
    new_status = previous.new_status if previous else ActionStatus(action.status)
    new_deadline = previous.new_deadline_text if previous else None
    changed = False

    for status, cue in _STATUS_CUES:
        if cue.search(sentence):
            new_status, changed = status, True
            break
    if _POSTPONE.search(sentence) and (m := _NEW_DEADLINE.search(sentence)):
        new_deadline, changed = m.group(1), True

    if not changed:
        return None
    if previous and (new_status, new_deadline) == (previous.new_status, previous.new_deadline_text):
        return None  # same news repeated - keep the first sentence as evidence
    note = f"Status reported as {new_status.value.replace('_', ' ')}"
    if new_deadline:
        note += f"; deadline moved to '{new_deadline}'"
    return ExtractedStatusUpdate(
        action_id=action.id,
        new_status=new_status,
        new_deadline_text=new_deadline,
        note=note + ".",
        evidence=sentence,
        confidence=0.75,
    )


def _summary(
    transcript: Transcript,
    decisions: list[ExtractedDecision],
    actions: list[ExtractedAction],
    risks: list[ExtractedRisk],
    updates: dict[int, ExtractedStatusUpdate],
) -> str:
    speakers = ", ".join(transcript.speakers) or "unknown speakers"
    return (
        f"Offline rule-based extraction. {len(decisions)} decision(s), {len(actions)} new action "
        f"item(s), {len(risks)} risk(s)/blocker(s) and {len(updates)} status update(s) were "
        f"detected in a discussion between {speakers}."
    )
