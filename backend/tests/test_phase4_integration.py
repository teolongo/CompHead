"""Phase 4 integration smoke tests for UI routes and /ask contract."""

from __future__ import annotations

from unittest.mock import patch

import main
from fastapi.testclient import TestClient

client = TestClient(main.app)

FROZEN_KEYS = {"answer", "sources", "verticale", "artifact_url"}


def test_get_root_returns_html() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "Company Brain" in response.text


def test_get_api_graph_returns_nodes() -> None:
    sample = {"nodes": [{"id": "x", "label": "X", "kind": "customer"}], "edges": [], "meta": {}}
    with patch("main.get_graph_cached", return_value=sample):
        response = client.get("/api/graph")
    assert response.status_code == 200
    assert "nodes" in response.json()


def test_post_ask_frozen_schema(monkeypatch) -> None:
    monkeypatch.setattr(
        main,
        "run_agent",
        lambda q: {
            "answer": "ok",
            "sources": ["crm/customers"],
            "verticale": "crm",
            "artifact_url": None,
        },
    )
    response = client.post("/ask", json={"question": "test?"})
    assert response.status_code == 200
    assert set(response.json().keys()) == FROZEN_KEYS


def test_artifact_url_pattern(monkeypatch) -> None:
    monkeypatch.setattr(
        main,
        "run_agent",
        lambda q: {
            "answer": "PDF ready",
            "sources": ["erp/inventory"],
            "verticale": "erp",
            "artifact_url": "https://example.com/files/report-abc.pdf",
        },
    )
    payload = client.post("/ask", json={"question": "pdf please"}).json()
    assert payload["artifact_url"].startswith("http")
    assert "/files/" in payload["artifact_url"]
