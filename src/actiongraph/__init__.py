"""ActionGraph: turn meeting conversations into trackable, reviewable work.

Package map (read in this order if you are new - see docs/LEARNING_PATH.md):

    domain/       Shared vocabulary: enums + the Pydantic schema the LLM must fill in
    ingestion/    Audio / subtitle / text files  ->  Transcript
    extraction/   Transcript  ->  MeetingExtraction (LLM or offline rules)
    enrichment/   Deterministic post-processing: grounding, people, dates, confidence
    storage/      SQLAlchemy tables + a Repository for queries
    services/     Orchestration: the processing pipeline, cross-meeting tracking, review
    graph/        Build the Meeting/Action/Person/Risk graph from the database
    evaluation/   Measure extraction quality against a hand-labelled dataset
    api/ cli.py   The two ways to drive the system (HTTP and terminal)
"""

__version__ = "0.1.0"
