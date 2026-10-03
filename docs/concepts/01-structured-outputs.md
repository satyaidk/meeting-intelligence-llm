# 01. Structured outputs: making an LLM return data, not prose

## What it is
A language model produces text one token at a time. **Structured outputs**
constrain that generation so the text is guaranteed to be valid JSON that
matches a JSON Schema you supply. You get *data* back, not a paragraph you
have to parse.

## Why it matters
Software needs predictable shapes. Without constraints, you might ask for
JSON and receive:

```text
Sure! Here are the action items:
```json
{"actions": [{"task": "Update API", "owner": "Priya"   <- cut off, or trailing comma, or a missing field
```

Every one of those failure modes would need detection, repair and retry
code. With structured outputs, the shape is guaranteed by the API.

## How ActionGraph does it

1. **Define the shape once, in Python** (`src/actiongraph/domain/schemas.py`):

   ```python
   class ExtractedAction(BaseModel):
       task: str = Field(description="Short imperative description of the work...")
       owner: str | None = Field(description="Who is responsible ... null when nobody is named.")
       deadline_text: str | None = Field(description="The deadline phrase copied from the transcript...")
       evidence: str = Field(description="A short verbatim quote ...")
       confidence: float = Field(ge=0.0, le=1.0, description="...")
   ```

2. **Pass the class to the SDK** (`extraction/anthropic_extractor.py`):

   ```python
   response = client.beta.messages.parse(..., output_format=MeetingExtraction)
   extraction = response.parsed_output        # a validated MeetingExtraction instance
   ```

   Behind the scenes the SDK: (a) generates a JSON Schema from the Pydantic
   model, (b) adapts it to what the API supports (unsupported constraints
   like `ge/le` are moved into the description), (c) sends it as
   `output_config.format`, and (d) validates the reply back into Pydantic.

3. **Still check the edges:** `stop_reason == "max_tokens"` means the JSON was
   cut off; `"refusal"` means there is no output; a Pydantic `ValidationError`
   means a *value* broke a rule (e.g. confidence 1.4). All three are handled.

## Design rules we follow
- **Descriptions are prompts.** The model reads every `description=`. Write them like instructions, with examples.
- **Required + nullable beats optional.** `owner: str | None` with no default forces the model to say `null` explicitly.
- **Ask for what the model is good at.** We ask for `deadline_text` (a phrase it can copy), not `due_date` (arithmetic it can get wrong); see [05](05-temporal-reasoning.md).
- **Add fields that make verification possible.** `evidence` exists purely so code can check the model ([03](03-grounding-and-hallucinations.md)).

## Pitfalls
- Structured output guarantees *shape*, not *truth*. A perfectly valid JSON object can still contain an invented action.
- Big schemas cost tokens (the schema is sent with each request) and can confuse the model; keep fields purposeful.
- Changing the schema changes model behaviour. Re-run the evaluation after schema edits.

## Try it
Remove the `description` from `ExtractedAction.owner`, run
`actiongraph eval --provider anthropic` before and after, and compare owner accuracy.

Related: [ADR-0004](../adr/0004-structured-outputs.md) · [02. Anatomy of an LLM call](02-anatomy-of-an-llm-call.md)
