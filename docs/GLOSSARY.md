# Glossary

| Term | Meaning in this project |
|------|-------------------------|
| **Action item** | A commitment for someone to do something after the meeting. Table `action_items`. |
| **ADR** | Architecture Decision Record: a short document capturing one decision and its trade-offs (`docs/adr/`). |
| **Alias** | One normalised spelling of a person's name (`priya s`). Table `person_aliases`. |
| **App factory** | A function (`create_app`) that builds a configured application, so tests can build isolated copies. |
| **Blocker** | A risk that is stopping work *now* (`kind = "blocker"`). |
| **Confidence** | A 0–1 score of how trustworthy an item is: the model's self-assessment, capped by grounding. |
| **Context window** | The maximum amount of text (tokens) a model can read in one request. |
| **Dependency injection** | Passing a component's dependencies in (sessions, settings, extractor) instead of creating them inside, which makes swapping and testing easy. |
| **Diarization** | Determining *who* spoke when in audio. Not yet implemented. |
| **Effort** | API setting controlling how much the model reasons before answering (`low` … `max`). |
| **Entity resolution** | Deciding that different names refer to the same person. |
| **Evaluation (eval)** | Measuring output quality on a labelled dataset with metrics. |
| **Event** | One entry in an action's history (`created`, `status_changed`, …). Table `action_events`. |
| **Evidence** | A verbatim transcript quote that supports an extracted item. |
| **Extractor** | Anything implementing `extract(request) -> result`: Claude, the offline rules, or a test fake. |
| **F1** | Harmonic mean of precision and recall. |
| **Fake** | A simple working stand-in used in tests (e.g. `FakeExtractor`). |
| **Fallback (server-side)** | If a model declines a request, the API retries it on another model within the same call. |
| **Grounding** | Verifying that model output is supported by the source text. |
| **Hallucination** | Model output that is plausible but not supported by the input. |
| **Held-out set** | Evaluation data never used while tuning, which gives an honest estimate of quality on new data. |
| **HITL** | Human-in-the-loop: humans handle the cases automation is unsure about. |
| **Micro-average** | Summing TP/FP/FN over all cases before computing ratios. |
| **Normalisation** | Converting text to a canonical form (lower-case, no punctuation) before comparing. |
| **ORM** | Object-Relational Mapper (SQLAlchemy): Python classes ↔ database tables. |
| **Overfitting** | Doing well on the data you tuned on and badly on new data. |
| **Precision** | Of the items extracted, the fraction that are correct. |
| **Prompt caching** | Reusing the processed prefix of a request across calls to save cost and latency. |
| **Prompt injection** | Text in the input that tries to give the model instructions. |
| **Protocol** | Python's structural interface type: any class with the right methods qualifies. |
| **Recall** | Of the items that should have been extracted, the fraction found. |
| **Repository** | A class that contains all database queries, named by meaning. |
| **Review queue** | Items with `review_status = needs_review`, waiting for a human. |
| **Session** | SQLAlchemy's unit of work: collects changes and commits them in one transaction. |
| **Status update** | A model-reported change to an action from an earlier meeting. Stored as an event. |
| **Stop reason** | Why the model stopped generating (`end_turn`, `max_tokens`, `refusal`, …). |
| **Structured outputs** | API feature that constrains model output to a JSON schema. |
| **Superseded** | A pending update made obsolete by a newer applied update for the same action. |
| **Temporal resolution** | Converting phrases like "by Friday" into dates. |
| **Token** | The unit models read and write (≈ ¾ of an English word). Billing is per token. |
| **Transaction** | A group of database changes that succeed or fail together. |
| **VAD** | Voice activity detection: finding the parts of audio that contain speech. |
