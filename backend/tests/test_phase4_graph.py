"""Contract tests for GET /api/graph (UI-only endpoint)."""

from __future__ import annotations

from unittest.mock import patch

import main
from fastapi.testclient import TestClient

client = TestClient(main.app)

SAMPLE_GRAPH = {
    "nodes": [
        {"id": "customer:CUST-0132", "label": "Primato", "kind": "customer"},
        {"id": "product:PAS-SPA-500", "label": "Spaghetti 500g", "kind": "product"},
        {"id": "supplier:SUP-001", "label": "Molino", "kind": "supplier"},
        {"id": "material:RAW-SEM-003", "label": "Semolina", "kind": "material"},
        {"id": "kb:DOC-001", "label": "Spaghetti spec", "kind": "kb-doc"},
        {"id": "kb:product-specs", "label": "Product specifications", "kind": "kb-category"},
    ],
    "edges": [
        {
            "source": "product:PAS-SPA-500",
            "target": "material:RAW-SEM-003",
            "relation": "uses",
        },
        {
            "source": "supplier:SUP-001",
            "target": "material:RAW-SEM-003",
            "relation": "supplies",
        },
        {
            "source": "kb:DOC-001",
            "target": "product:PAS-SPA-500",
            "relation": "documented-by",
        },
        {
            "source": "kb:DOC-001",
            "target": "kb:product-specs",
            "relation": "in-category",
        },
    ],
    "meta": {
        "customers": 1,
        "products": 1,
        "suppliers": 1,
        "materials": 1,
        "kb_docs": 1,
        "kb_categories": 1,
    },
}

VALID_KINDS = {"customer", "product", "supplier", "material", "kb-doc", "kb-category"}


def test_api_graph_returns_200_with_nodes_and_edges() -> None:
    with patch("main.get_graph_cached", return_value=SAMPLE_GRAPH):
        response = client.get("/api/graph")
    assert response.status_code == 200
    payload = response.json()
    assert "nodes" in payload
    assert "edges" in payload
    assert isinstance(payload["nodes"], list)
    assert isinstance(payload["edges"], list)


def test_api_graph_node_kinds_are_valid() -> None:
    with patch("main.get_graph_cached", return_value=SAMPLE_GRAPH):
        payload = client.get("/api/graph").json()
    for node in payload["nodes"]:
        assert node["kind"] in VALID_KINDS


def test_api_graph_no_auth_required() -> None:
    with patch("main.get_graph_cached", return_value=SAMPLE_GRAPH):
        response = client.get("/api/graph")
    assert response.status_code == 200


def test_flatten_bom_components_nested() -> None:
    from services.graph import _flatten_bom_components

    row = {
        "sku": "PAS-SPA-500",
        "components": [
            {"raw_sku": "RAW-SEM-003", "description": "Durum semolina"},
            {"raw_sku": "RAW-PCK-001", "description": "Film wrap"},
        ],
    }
    flat = _flatten_bom_components(row)
    assert len(flat) == 2
    assert flat[0]["component_sku"] == "RAW-SEM-003"
    assert flat[0]["finished_sku"] == "PAS-SPA-500"


def test_kb_nodes_and_edges_offline() -> None:
    from services.graph import _kb_nodes_and_edges

    nodes = {
        "product:PAS-SPA-500": {"id": "product:PAS-SPA-500", "kind": "product", "label": "Spaghetti"},
        "customer:CUST-0132": {"id": "customer:CUST-0132", "kind": "customer", "label": "Primato", "channel": "GDO"},
        "supplier:SUP-001": {"id": "supplier:SUP-001", "kind": "supplier", "label": "Molino", "category": "semolina"},
    }
    edges: list = []
    seen: set = set()

    def add_edge(source: str, target: str, relation: str) -> None:
        key = (source, target, relation)
        if key in seen:
            return
        seen.add(key)
        edges.append({"source": source, "target": target, "relation": relation})

    count = _kb_nodes_and_edges(nodes, add_edge)
    assert count == 35
    assert any(n["kind"] == "kb-doc" for n in nodes.values())
    assert any(n["kind"] == "kb-category" for n in nodes.values())
    assert any(e["relation"] == "documented-by" for e in edges)
