# Data model

Tables are defined in `src/actiongraph/storage/models.py` (SQLAlchemy 2.0).
Enum-like columns store the string values from `domain/enums.py`.

## Entity-relationship diagram

```mermaid
erDiagram
    MEETING ||--o{ ACTION_ITEM : "creates"
    MEETING ||--o{ DECISION : "records"
    MEETING ||--o{ RISK : "raises"
    MEETING |o--o{ ACTION_EVENT : "reports"
    PERSON ||--o{ PERSON_ALIAS : "is known as"
    PERSON |o--o{ ACTION_ITEM : "owns"
    PERSON |o--o{ DECISION : "made"
    ACTION_ITEM ||--o{ ACTION_EVENT : "has history"
    RISK }o--o| ACTION_ITEM : "blocks"

    MEETING {
        int id PK
        string title
        date meeting_date
        string source_type
        text transcript
        text summary
        json participants
        string llm_provider
        string llm_model
        json llm_usage
        float latency_seconds
    }
    PERSON {
        int id PK
        string display_name
    }
    PERSON_ALIAS {
        int id PK
        int person_id FK
        string alias UK "normalised, e.g. 'priya s'"
    }
    ACTION_ITEM {
        int id PK
        int meeting_id FK "meeting that created it"
        text task
        int owner_id FK "nullable"
        string owner_raw "name as spoken"
        bool is_team_owned
        string deadline_text "as spoken"
        date due_date "resolved"
        string status
        float confidence
        text evidence
        string review_status
        json review_reasons
    }
    ACTION_EVENT {
        int id PK
        int action_id FK
        int meeting_id FK "null for manual edits"
        string event_type
        string from_status
        string to_status
        string deadline_text
        date due_date
        bool applied
        string review_status
    }
    DECISION {
        int id PK
        int meeting_id FK
        text text
        int made_by_id FK
    }
    RISK {
        int id PK
        int meeting_id FK
        text description
        string kind "risk | blocker"
        string severity
        int blocks_action_id FK
    }
```

`ActionItem`, `Decision`, `Risk` and `ActionEvent` also share the
*reviewable* columns from `ReviewableMixin`: `confidence`, `evidence`,
`review_status`, `review_reasons`, `created_at`.

## Design notes

**Raw and resolved values are both kept.** `owner_raw` ("@priya") and
`owner_id` (Priya Sharma); `deadline_text` ("by Friday") and `due_date`
(2026-09-11). The raw value is evidence; the resolved value is what we track.
A reviewer can always see what was actually said.

**History is append-only.** Status is not just overwritten; every change is an
`ActionEvent`. The current `ActionItem.status` is a convenience copy of the
latest applied event. This gives the cross-meeting timeline for free and an
audit trail of who/what changed what.

**Proposals vs. facts.** An event with `applied = false` is a *proposal*
waiting for review; it does not affect the action until approved.

**Rejected is hidden, not deleted.** Rejected items stay in the database
(useful for auditing and for building evaluation data from real mistakes) but
are excluded from tracking queries and the graph.

## Action status state machine

```mermaid
stateDiagram-v2
    [*] --> open: created in a meeting
    open --> in_progress
    open --> blocked
    in_progress --> blocked
    blocked --> in_progress: unblocked
    open --> done
    in_progress --> done
    blocked --> done
    open --> cancelled
    in_progress --> cancelled
    blocked --> cancelled
    done --> [*]
    cancelled --> [*]
```

Transitions come from a meeting (status update) or a human edit. A deadline
change keeps the status and is recorded as a `deadline_changed` event
("postponed"). `done` and `cancelled` are *closed*: closed actions are no
longer sent to the extractor as context.

## Review status state machine

```mermaid
stateDiagram-v2
    [*] --> auto_approved: all checks passed
    [*] --> needs_review: any check failed
    needs_review --> approved: human approves (pending updates are applied)
    needs_review --> rejected: human rejects
    needs_review --> superseded: a newer update for the same action was applied
    auto_approved --> approved: human edits the item
    auto_approved --> rejected: human rejects
```

## Event types

| `event_type` | Created when | Changes the action? |
|--------------|-------------|---------------------|
| `created` | an action is first extracted | – (it is the creation) |
| `status_changed` | a later meeting reports progress | yes, once applied |
| `deadline_changed` | a later meeting moves the deadline | yes, once applied |
| `mentioned` | discussed again with no change, or a duplicate was folded in | no |
| `edited` | a human edits the action | yes (immediately) |

## Indexes

Foreign keys used for filtering are indexed: `action_items.meeting_id`,
`owner_id`, `status`; `action_events.action_id`; `decisions.meeting_id`;
`risks.meeting_id`; `person_aliases.alias` (unique).
