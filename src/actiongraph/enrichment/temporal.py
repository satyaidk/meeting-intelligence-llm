"""Temporal resolution: "by Friday" + meeting date -> a calendar date.

Why not ask the LLM to output dates directly? Calendar arithmetic is exactly
the kind of task where language models make small, confident mistakes
(off-by-one weekdays, wrong month lengths). Deterministic code is always right,
is free, and can explain itself. So the LLM copies the phrase and this module
does the maths (docs/adr/0005-deterministic-temporal-resolution.md).

Every result carries a ``confidence`` and a plain-English ``rule`` so a
reviewer can see *why* a date was chosen. Genuinely ambiguous phrases
("next Friday") get a low confidence and go to review; phrases tied to unknown
events ("before the next release") stay unresolved instead of being guessed.

All weekday maths uses Python's convention: Monday = 0 ... Sunday = 6.
"""

from __future__ import annotations

import calendar
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, timedelta

WEEKDAYS = {
    "monday": 0, "mon": 0, "tuesday": 1, "tue": 1, "tues": 1, "wednesday": 2, "wed": 2,
    "thursday": 3, "thu": 3, "thur": 3, "thurs": 3, "friday": 4, "fri": 4,
    "saturday": 5, "sat": 5, "sunday": 6, "sun": 6,
}  # fmt: skip
MONTHS = {
    "january": 1, "jan": 1, "february": 2, "feb": 2, "march": 3, "mar": 3, "april": 4,
    "apr": 4, "may": 5, "june": 6, "jun": 6, "july": 7, "jul": 7, "august": 8, "aug": 8,
    "september": 9, "sept": 9, "sep": 9, "october": 10, "oct": 10, "november": 11,
    "nov": 11, "december": 12, "dec": 12,
}  # fmt: skip
NUMBER_WORDS = {
    "a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
    "a couple of": 2, "couple of": 2, "a few": 3, "few": 3,
}  # fmt: skip

FRIDAY = 4


def _alternation(words: dict[str, int]) -> str:
    # Longest first so "september" wins over "sep".
    return "|".join(sorted(map(re.escape, words), key=len, reverse=True))


_WEEKDAY_RE = _alternation(WEEKDAYS)
_MONTH_RE = _alternation(MONTHS)
_NUMBER_RE = rf"\d+|{_alternation(NUMBER_WORDS)}"
_LEADING_FILLER = re.compile(
    r"^(?:by|before|until|till|til|on|due|for|around|ideally|no later than|not later than|"
    r"latest|the)\s+"
)


@dataclass(frozen=True)
class DeadlineResolution:
    text: str | None
    due_date: date | None
    confidence: float
    rule: str  # human-readable explanation of how the date was chosen

    @property
    def has_text(self) -> bool:
        return bool(self.text and self.text.strip())

    @property
    def is_resolved(self) -> bool:
        return self.due_date is not None


def resolve_deadline(text: str | None, reference: date) -> DeadlineResolution:
    """Convert a deadline phrase to a date, relative to ``reference`` (the meeting date)."""
    if not text or not text.strip():
        return DeadlineResolution(text, None, 1.0, "no deadline given")

    phrase = _clean(text)
    for rule in _RULES:
        outcome = rule(phrase, reference)
        if outcome is not None:
            due, confidence, explanation = outcome
            return DeadlineResolution(text, due, confidence, explanation)
    return DeadlineResolution(
        text, None, 0.0, "no calendar date found (the phrase may depend on an unknown event)"
    )


def _clean(text: str) -> str:
    phrase = text.lower().replace("’", "'")
    phrase = re.sub(r"[,.!?;:()]", " ", phrase)
    phrase = re.sub(r"(?<!\d)-|-(?!\d)", " ", phrase)  # keep hyphens only inside 2026-09-11
    phrase = re.sub(r"\s+", " ", phrase).strip()
    previous = None
    while previous != phrase:  # strip several fillers: "by the end of week"
        previous, phrase = phrase, _LEADING_FILLER.sub("", phrase)
    return phrase


# --------------------------------------------------------------------------
# Rules. Each takes (phrase, reference) and returns (date, confidence,
# explanation) or None. ORDER MATTERS: more specific rules come first.
# --------------------------------------------------------------------------
Outcome = tuple[date, float, str] | None


def _iso_date(phrase: str, ref: date) -> Outcome:
    m = re.search(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b", phrase)
    if not m:
        return None
    try:
        return date(int(m[1]), int(m[2]), int(m[3])), 1.0, "explicit ISO date"
    except ValueError:
        return None


def _named_month_date(phrase: str, ref: date) -> Outcome:
    # "october 15", "oct 15th 2026", "15 october", "15th of oct"
    m = re.search(rf"\b({_MONTH_RE})\s+(\d{{1,2}})(?:st|nd|rd|th)?(?:\s+(\d{{4}}))?\b", phrase)
    if m:
        month, day, year = MONTHS[m[1]], int(m[2]), m[3]
    else:
        m = re.search(
            rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+(?:of\s+)?({_MONTH_RE})(?:\s+(\d{{4}}))?\b", phrase
        )
        if not m:
            return None
        day, month, year = int(m[1]), MONTHS[m[2]], m[3]
    try:
        due = date(int(year) if year else ref.year, month, day)
    except ValueError:
        return None
    if not year and due < ref:  # "Jan 5" said in December means next year
        due = due.replace(year=ref.year + 1)
    return due, 0.95, "explicit calendar date"


def _day_after_tomorrow(phrase: str, ref: date) -> Outcome:
    if "day after tomorrow" in phrase:
        return ref + timedelta(days=2), 0.95, "day after tomorrow"
    return None


def _tomorrow(phrase: str, ref: date) -> Outcome:
    if re.search(r"\btomorrow\b", phrase):
        return ref + timedelta(days=1), 0.95, "tomorrow = meeting date + 1 day"
    return None


def _in_n_units(phrase: str, ref: date) -> Outcome:
    m = re.search(
        rf"\b(?:in|within)\s+({_NUMBER_RE})\s+(business day|working day|day|week|month)s?\b",
        phrase,
    )
    if not m:
        m = re.search(
            rf"\b({_NUMBER_RE})\s+(business day|working day|day|week|month)s?\s+from now\b", phrase
        )
    if not m:
        return None
    n = int(m[1]) if m[1].isdigit() else NUMBER_WORDS[m[1]]
    unit = m[2]
    if unit in ("business day", "working day"):
        due = _add_business_days(ref, n)
    elif unit == "day":
        due = ref + timedelta(days=n)
    elif unit == "week":
        due = ref + timedelta(weeks=n)
    else:
        due = _add_months(ref, n)
    return due, 0.9, f"meeting date + {n} {unit}(s)"


def _weekday(phrase: str, ref: date) -> Outcome:
    m = re.search(
        rf"\b(?:(this|next|coming)\s+)?({_WEEKDAY_RE})\b(?:\s+(next week|this week))?", phrase
    )
    if not m:
        return None
    modifier, target, suffix = m[1], WEEKDAYS[m[2]], m[3]
    name = calendar.day_name[target]
    days_until = (target - ref.weekday()) % 7  # 0 = same weekday as the meeting

    if suffix == "next week":
        return _monday_of_next_week(ref) + timedelta(days=target), 0.85, f"{name} of next week"
    if modifier == "next":
        # "next Friday" is genuinely ambiguous in English. We read it as the
        # Friday of *next* week, and flag it with a low confidence.
        due = ref + timedelta(days=days_until or 7)
        if target > ref.weekday():
            due += timedelta(days=7)
        return due, 0.65, f"'next {name}' read as {name} of next week (ambiguous phrase)"
    if days_until == 0:
        return ref + timedelta(days=7), 0.6, f"meeting is on a {name}; assumed {name} next week"
    return ref + timedelta(days=days_until), 0.9, f"first {name} after the meeting"


def _end_of_next_week(phrase: str, ref: date) -> Outcome:
    if re.search(r"\bend of (?:the )?next week\b", phrase):
        return _monday_of_next_week(ref) + timedelta(days=FRIDAY), 0.85, "Friday of next week"
    return None


def _next_week(phrase: str, ref: date) -> Outcome:
    if re.search(r"\bnext week\b", phrase):
        return (
            _monday_of_next_week(ref) + timedelta(days=FRIDAY),
            0.6,
            "'next week' read as the end of next week (Friday)",
        )
    return None


def _end_of_week(phrase: str, ref: date) -> Outcome:
    if re.search(r"\b(?:end of (?:the |this )?week|eow|this week|week end)\b", phrase):
        return (
            ref + timedelta(days=(FRIDAY - ref.weekday()) % 7),
            0.9,
            "Friday of the meeting's week",
        )
    if re.search(r"\b(?:the |this )?weekend\b", phrase):  # "before the weekend" = Friday
        return (
            ref + timedelta(days=(FRIDAY - ref.weekday()) % 7),
            0.8,
            "'the weekend' read as the last working day before it (Friday)",
        )
    return None


def _next_month(phrase: str, ref: date) -> Outcome:
    if re.search(r"\bnext month\b", phrase):
        nxt = _add_months(ref.replace(day=1), 1)
        explicit_end = "end of" in phrase
        return (
            _last_day_of_month(nxt.year, nxt.month),
            0.85 if explicit_end else 0.6,
            "last day of next month",
        )
    return None


def _end_of_month(phrase: str, ref: date) -> Outcome:
    if re.search(r"\b(?:end of (?:the |this )?month|eom|this month|month end)\b", phrase):
        return _last_day_of_month(ref.year, ref.month), 0.9, "last day of the meeting's month"
    return None


def _quarter(phrase: str, ref: date) -> Outcome:
    m = re.search(r"\bq([1-4])\b", phrase)
    if m:
        quarter = int(m[1])
        due = _last_day_of_month(ref.year, quarter * 3)
        if due < ref:
            due = _last_day_of_month(ref.year + 1, quarter * 3)
        return due, 0.85, f"last day of Q{quarter}"
    if re.search(r"\b(?:end of (?:the |this )?quarter|eoq|this quarter)\b", phrase):
        quarter_end_month = ((ref.month - 1) // 3 + 1) * 3
        return _last_day_of_month(ref.year, quarter_end_month), 0.85, "last day of this quarter"
    return None


def _end_of_year(phrase: str, ref: date) -> Outcome:
    if re.search(r"\b(?:end of (?:the |this )?year|eoy|this year)\b", phrase):
        return date(ref.year, 12, 31), 0.85, "last day of the year"
    return None


def _today(phrase: str, ref: date) -> Outcome:
    if re.search(r"\b(?:today|tonight|eod|end of (?:the )?day|close of business|cob)\b", phrase):
        return ref, 0.95, "same day as the meeting"
    return None


_RULES: list[Callable[[str, date], Outcome]] = [
    _iso_date,
    _named_month_date,
    _day_after_tomorrow,
    _tomorrow,
    _in_n_units,
    _weekday,  # before the "week" rules so "Friday next week" is handled here
    _end_of_next_week,
    _next_week,
    _end_of_week,
    _next_month,
    _end_of_month,
    _quarter,
    _end_of_year,
    _today,
]


# ------------------------------------------------------------------ helpers
def _monday_of_next_week(ref: date) -> date:
    return ref + timedelta(days=7 - ref.weekday())


def _last_day_of_month(year: int, month: int) -> date:
    return date(year, month, calendar.monthrange(year, month)[1])


def _add_months(ref: date, months: int) -> date:
    month_index = ref.month - 1 + months
    year, month = ref.year + month_index // 12, month_index % 12 + 1
    return date(year, month, min(ref.day, calendar.monthrange(year, month)[1]))


def _add_business_days(ref: date, days: int) -> date:
    current = ref
    while days > 0:
        current += timedelta(days=1)
        if current.weekday() < 5:
            days -= 1
    return current
