"""Tests for KB retrieval tool (Q4: PAS-SPA-500 shelf life and allergens)."""

from __future__ import annotations

import json
import os

import pytest

Q4_QUESTION = (
    "What is the shelf life (TMC) and the declared allergens for "
    "Spaghetti n.5 - 500g box (SKU PAS-SPA-500)?"
)


def _has_integration_env() -> bool:
    return bool(os.environ.get("MOCK_API_TOKEN") and os.environ.get("LLM_API_KEY"))


def test_search_kb_sku_exact_match() -> None:
    """PAS-SPA-500 query returns DOC-001 via SKU scan with full document text."""
    from agent.tools.kb import run_kb_tool

    result_json, source = run_kb_tool("search_kb", {"query": "PAS-SPA-500"})
    result = json.loads(result_json)

    assert source == "DOC-001"
    assert "/" not in source
    assert result["document_id"] == "DOC-001"
    assert result["match_method"] == "sku_exact"
    assert result["sku"] == "PAS-SPA-500"
    assert "36 months" in result["full_document_text"]
    assert "gluten" in result["full_document_text"].lower()


def test_search_kb_bm25_fallback() -> None:
    """Generic query without SKU uses BM25 over whole documents."""
    from agent.tools.kb import run_kb_tool

    result_json, source = run_kb_tool("search_kb", {"query": "returns policy"})
    result = json.loads(result_json)

    assert result["match_method"] == "bm25"
    assert source == result["document_id"]
    assert source.startswith("DOC-")
    assert "/" not in source
    assert result["full_document_text"]


@pytest.mark.integration
@pytest.mark.skipif(not _has_integration_env(), reason="MOCK_API_TOKEN and LLM_API_KEY required")
def test_q4_agent_integration() -> None:
    """Q4 via run_agent mentions 36 months, gluten, and DOC-001 source."""
    from agent.loop import run_agent

    response = run_agent(Q4_QUESTION)
    answer = response["answer"].lower()

    assert "36" in response["answer"] and "month" in answer
    assert "gluten" in answer
    assert any(source.startswith("DOC-") for source in response["sources"])
