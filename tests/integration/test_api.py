"""HTTP API tests with FastAPI's TestClient (offline extractor, temporary database)."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from actiongraph.api.app import create_app
from actiongraph.config import Settings
from tests.conftest import SAMPLES

PLANNING = (SAMPLES / "transcripts" / "2026-09-07_sprint-14-planning.txt").read_text(
    encoding="utf-8"
)


@pytest.fixture
def client(offline_settings: Settings) -> Iterator[TestClient]:
    with TestClient(create_app(offline_settings)) as test_client:
        yield test_client


@pytest.fixture
def processed(client: TestClient) -> TestClient:
    response = client.post(
        "/api/meetings",
        json={"title": "Sprint 14 Planning", "meeting_date": "2026-09-07", "transcript": PLANNING},
    )
    assert response.status_code == 201, response.text
    return client


def test_health(client: TestClient) -> None:
    body = client.get("/api/health").json()
    assert body["status"] == "ok"
    assert body["llm_provider"] == "offline"


def test_ui_is_served(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "ActionGraph" in response.text


def test_process_meeting_returns_report(client: TestClient) -> None:
    response = client.post(
        "/api/meetings",
        json={"title": "Planning", "meeting_date": "2026-09-07", "transcript": PLANNING},
    )
    report = response.json()
    assert report["meeting_id"] == 1
    assert report["actions_created"] >= 5
    assert report["provider"] == "offline"


def test_validation_error(client: TestClient) -> None:
    response = client.post("/api/meetings", json={"title": "", "meeting_date": "not-a-date"})
    assert response.status_code == 422


def test_list_and_get_actions(processed: TestClient) -> None:
    actions = processed.get("/api/actions").json()
    api_design = next(a for a in actions if a["task"] == "Update the API design")
    assert api_design["owner"] == "Team"
    assert api_design["due_date"] == "2026-09-11"

    detail = processed.get(f"/api/actions/{api_design['id']}").json()
    assert detail["events"][0]["event_type"] == "created"
    assert detail["events"][0]["meeting_title"] == "Sprint 14 Planning"


def test_filter_actions_by_status(processed: TestClient) -> None:
    assert processed.get("/api/actions?status=done").json() == []
    assert processed.get("/api/actions?status=nonsense").status_code == 422


def test_review_queue_and_approve(processed: TestClient) -> None:
    queue = processed.get("/api/review").json()
    assert queue["total"] >= 1
    item = queue["actions"][0]
    assert item["review_reasons"]

    response = processed.post(f"/api/review/action/{item['id']}/approve")
    assert response.json()["review_status"] == "approved"
    assert processed.get("/api/review").json()["total"] == queue["total"] - 1


def test_patch_action(processed: TestClient) -> None:
    response = processed.patch("/api/actions/1", json={"status": "in_progress", "owner": "Alex"})
    body = response.json()
    assert body["status"] == "in_progress"
    assert body["owner"] == "Alex Kim"  # entity resolution: "Alex" is the known Alex Kim
    assert body["events"][-1]["event_type"] == "edited"


def test_patch_with_nothing_to_change_is_a_conflict(processed: TestClient) -> None:
    response = processed.patch("/api/actions/1", json={})
    assert response.status_code == 409
    assert response.json()["error"] == "InvalidOperationError"


def test_meeting_detail(processed: TestClient) -> None:
    meetings = processed.get("/api/meetings").json()
    detail = processed.get(f"/api/meetings/{meetings[0]['id']}").json()
    assert len(detail["decisions"]) == 2
    assert "Maya Chen" in detail["participants"]


def test_people_are_merged(processed: TestClient) -> None:
    people = {p["display_name"]: p for p in processed.get("/api/people").json()}
    assert "sam" in people["Sam Lee"]["aliases"]


def test_upload_vtt(client: TestClient) -> None:
    path = SAMPLES / "other_formats" / "design-review.vtt"
    with path.open("rb") as fh:
        response = client.post(
            "/api/meetings/upload",
            files={"file": ("design-review.vtt", fh, "text/vtt")},
            data={"title": "Design Review", "meeting_date": "2026-09-22"},
        )
    assert response.status_code == 201, response.text
    meeting = client.get(f"/api/meetings/{response.json()['meeting_id']}").json()
    assert meeting["source_name"] == "design-review.vtt"
    assert meeting["source_type"] == "transcript_file"


def test_upload_rejects_unknown_file_types(client: TestClient) -> None:
    response = client.post(
        "/api/meetings/upload",
        files={"file": ("notes.pdf", b"%PDF-1.7", "application/pdf")},
        data={"title": "x", "meeting_date": "2026-09-22"},
    )
    assert response.status_code == 415


def test_not_found(client: TestClient) -> None:
    response = client.get("/api/meetings/42")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


def test_graph_endpoints(processed: TestClient) -> None:
    graph = processed.get("/api/graph").json()
    assert {n["type"] for n in graph["nodes"]} >= {"meeting", "action", "person", "decision"}
    mermaid = processed.get("/api/graph/mermaid")
    assert mermaid.text.startswith("flowchart LR")
