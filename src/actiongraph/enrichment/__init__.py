"""Enrichment layer: deterministic post-processing of LLM output.

The LLM is good at *understanding* language; plain code is better at things
that must be exact and repeatable. So the work is split:

    grounding.py          Is the evidence quote really in the transcript?
    entity_resolution.py  "Priya", "Priya S.", "@priya"  ->  one person
    temporal.py           "by Friday" + meeting date      ->  2026-09-11
    confidence.py         Combine all signals -> auto-approve or send to review

All functions here are pure (no database, no network), so they are fast and
easy to unit-test.
"""
