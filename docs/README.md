# ActionGraph documentation

This folder follows a "docs as code" approach: documentation lives next to
the code, is reviewed in the same pull requests, and is updated when behaviour
changes. Each document has one job. Use the table to find the one you need.

## Where to start

| If you want to… | Read |
|-----------------|------|
| Learn the codebase step by step (beginners start here) | [LEARNING_PATH.md](LEARNING_PATH.md) |
| Install and run it for the first time | [guides/GETTING_STARTED.md](guides/GETTING_STARTED.md) |
| Understand *what* we built and *why* | [design/DESIGN.md](design/DESIGN.md) |
| See how the pieces fit together | [architecture/ARCHITECTURE.md](architecture/ARCHITECTURE.md) |
| Follow one meeting through every stage | [architecture/PIPELINE.md](architecture/PIPELINE.md) |
| Understand the database tables and state machines | [architecture/DATA_MODEL.md](architecture/DATA_MODEL.md) |
| Know why a technology or approach was chosen | [adr/](adr/README.md) |
| Understand an LLM-engineering concept in depth | [concepts/](concepts/README.md) |
| Change code safely | [guides/DEVELOPMENT.md](guides/DEVELOPMENT.md), [guides/TESTING.md](guides/TESTING.md) |
| Measure whether a change made extraction better | [guides/EVALUATION.md](guides/EVALUATION.md) |
| Edit the prompt | [guides/PROMPT_ENGINEERING.md](guides/PROMPT_ENGINEERING.md) |
| Call the HTTP API | [api/API_REFERENCE.md](api/API_REFERENCE.md) |
| Fix something that is broken | [operations/RUNBOOK.md](operations/RUNBOOK.md) |
| Look up a term | [GLOSSARY.md](GLOSSARY.md) |

## Document types (and how industry teams use them)

| Type | Purpose | Lifetime |
|------|---------|----------|
| **Design doc** | Proposes a system *before/while* building it: goals, non-goals, design, alternatives, risks. Reviewed by peers. | Written once, updated at major milestones |
| **ADR** (Architecture Decision Record) | One significant decision, its context and its consequences. Never edited after acceptance; superseded by a new ADR instead. | Permanent, append-only |
| **Architecture docs** | How the system *is* built today. | Kept current with the code |
| **Guides** | Task-oriented how-tos ("how do I run the tests?"). | Kept current |
| **Concepts** | Explanations of ideas that are not specific to one file. | Rarely change |
| **Reference** | Exhaustive facts: API endpoints, config options, glossary. | Kept current; ideally generated |
| **Runbook** | What to do when something goes wrong. | Grows with every incident |

## Conventions

- Diagrams use [Mermaid](https://mermaid.js.org/) so they render on GitHub and live in plain text.
- Code is referenced by path (`src/actiongraph/services/pipeline.py`) so you can jump to it.
- Every document starts with what it is for and who should read it.
- When behaviour changes, the PR that changes it also updates the docs (see the PR template).
