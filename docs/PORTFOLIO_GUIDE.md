# Portfolio guide: presenting ActionGraph

How to describe this project on a resume, a GitHub profile and in
interviews. **Only claim what you can explain and have run yourself.**
Interviewers will ask you to go one level deeper on anything you list. Work
through the [learning path](LEARNING_PATH.md) first.

## One-line description
> ActionGraph: an LLM-powered meeting-intelligence system that extracts decisions, action items, owners, deadlines and risks from transcripts or audio as validated structured data, tracks each action across meetings, and routes uncertain extractions to human review.

## Resume bullets (pick 3–4, adapt the numbers to your own runs)
- Built an LLM extraction pipeline (Python, Claude API, **structured outputs** with Pydantic schemas) converting meeting transcripts and audio (Whisper) into tracked decisions, action items and risks.
- Designed **hallucination safeguards**: evidence-quote grounding against the source transcript, model-confidence capping, and a **human-in-the-loop** review queue with per-item explanations.
- Implemented deterministic **entity resolution** (name variants → one person, ambiguity detection) and **temporal resolution** ("by end of next week" → date with confidence), with 60+ parametrised unit tests.
- Added **cross-meeting tracking** (status/deadline updates, duplicate folding, risk→action links) on an event-sourced history, exposed through a FastAPI REST API, CLI and interactive graph UI.
- Built an **evaluation harness** (precision/recall/F1 on a labelled set with a held-out case) and showed that a regex baseline scoring 0.96 F1 on tuned data dropped to 0.00 on unseen natural speech, motivating the LLM approach.
- Maintained 160 automated tests (~96% coverage) with fakes for the LLM layer, CI via GitHub Actions, and design docs/ADRs for major decisions.

## The 60-second pitch
1. **Problem:** meetings produce commitments that get lost; summaries are not trackable.
2. **Approach:** one structured-output LLM call per meeting, then deterministic code for everything that must be exact (dates, identity, verification).
3. **Trust:** every item quotes the transcript; anything uncertain goes to a human with a reason.
4. **Memory:** each meeting is read with the open work from earlier meetings, so actions move from open → blocked → done.
5. **Evidence:** an evaluation harness with a held-out set, not just demos.

## Questions you should be ready for
| Question | Where to find your answer |
|----------|---------------------------|
| Why not let the LLM compute dates? | [ADR-0005](adr/0005-deterministic-temporal-resolution.md), [concepts/05](concepts/05-temporal-reasoning.md) |
| How do you know the output is correct? | Grounding ([concepts/03](concepts/03-grounding-and-hallucinations.md)) + review routing + [EVALUATION.md](guides/EVALUATION.md) |
| How do you test code that calls an LLM? | [TESTING.md](guides/TESTING.md): fakes vs. evals |
| What happens if the API is down mid-processing? | Transactions: [DESIGN §7](design/DESIGN.md#reliability), `test_failed_extraction_leaves_database_untouched` |
| How would you scale this to 1,000 teams? | [ARCHITECTURE §7](architecture/ARCHITECTURE.md#7-scaling-path-not-needed-yet) |
| What about prompt injection? | System prompt + id validation + grounding; eval case 05 |
| Why a relational DB for a "graph"? | [ADR-0003](adr/0003-relational-storage-for-the-graph.md) |
| What would you improve next? | Diarization, semantic matching, async jobs (Roadmap) |
| What was the hardest bug? | Have your own story ready, e.g. the "next Friday" ambiguity or the SQLAlchemy autoflush warning |

## Making the GitHub repository shine
- Pin the repo; the README's first screen should show the input → output example.
- Add a short GIF or screenshots of the UI (Review queue and Graph tabs).
- Keep CI green; the badge matters.
- Write commit messages in Conventional Commits style; reviewers read history.
- Add one or two of the Stage-9 extensions from the learning path, each with its own ADR. That shows you can *extend* a system, not just follow a tutorial.
