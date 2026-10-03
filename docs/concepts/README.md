# Concepts

Each page explains one idea in plain language: **what it is, why it
matters, how ActionGraph implements it (with file pointers), common
pitfalls, and something to try.** They map to the seven LLM components in the
project brief.

| # | Concept | Brief component |
|---|---------|-----------------|
| [01](01-structured-outputs.md) | Structured outputs: making an LLM return data, not prose | 3. Structured output |
| [02](02-anatomy-of-an-llm-call.md) | Anatomy of an LLM call: messages, tokens, effort, stop reasons, caching, cost | 2. LLM extraction |
| [03](03-grounding-and-hallucinations.md) | Grounding: catching hallucinations with evidence quotes | 7. Human-in-the-loop |
| [04](04-entity-resolution.md) | Entity resolution: many names, one person | 4. Entity resolution |
| [05](05-temporal-reasoning.md) | Temporal reasoning: "by Friday" → a date | 5. Temporal understanding |
| [06](06-human-in-the-loop.md) | Human-in-the-loop: confidence, reasons, review | 7. Human-in-the-loop |
| [07](07-cross-meeting-tracking.md) | Cross-meeting tracking: state across conversations | 6. Cross-meeting tracking |
| [08](08-speech-to-text.md) | Speech-to-text with Whisper | 1. Speech-to-text |
