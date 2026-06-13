"""KB tools for the agent loop."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from rank_bm25 import BM25Okapi

_KB_DIR = Path(__file__).resolve().parents[2] / "data" / "kb"
_SKU_PATTERN = re.compile(r"PAS-[A-Z]{3}-\d{3}")

_bm25_index: BM25Okapi | None = None
_doc_ids: list[str] = []
_docs_text: list[str] = []

TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "search_kb",
            "description": (
                "Search the knowledge base for product specs, policies, price lists, "
                "and customer requirements. Pass a SKU (e.g. PAS-SPA-500) for exact "
                "product spec lookup, or keywords for policy/topic search."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "SKU such as PAS-SPA-500 or topic keywords such as "
                            "returns policy or shelf life"
                        ),
                    },
                },
                "required": ["query"],
                "additionalProperties": False,
            },
        },
    }
]


def get_tool_definitions() -> list[dict[str, Any]]:
    return TOOL_DEFINITIONS


def _load_documents() -> list[tuple[str, str]]:
    docs: list[tuple[str, str]] = []
    for path in sorted(_KB_DIR.glob("DOC-*.md")):
        docs.append((path.stem, path.read_text(encoding="utf-8")))
    return docs


def _get_bm25_index() -> tuple[BM25Okapi, list[str], list[str]]:
    global _bm25_index, _doc_ids, _docs_text
    if _bm25_index is None:
        loaded = _load_documents()
        _doc_ids = [doc_id for doc_id, _ in loaded]
        _docs_text = [text for _, text in loaded]
        tokenized = [text.lower().split() for text in _docs_text]
        _bm25_index = BM25Okapi(tokenized)
    return _bm25_index, _doc_ids, _docs_text


def _find_by_sku(query: str) -> tuple[str, str, str] | None:
    sku_match = _SKU_PATTERN.search(query)
    if not sku_match:
        return None

    sku = sku_match.group(0)
    for path in sorted(_KB_DIR.glob("DOC-*.md")):
        text = path.read_text(encoding="utf-8")
        if sku in text:
            return path.stem, text, sku
    return None


def _find_by_bm25(query: str) -> tuple[str, str]:
    bm25, doc_ids, docs_text = _get_bm25_index()
    scores = bm25.get_scores(query.lower().split())
    best_idx = max(range(len(scores)), key=lambda i: scores[i])
    return doc_ids[best_idx], docs_text[best_idx]


def run_kb_tool(name: str, arguments: dict[str, Any]) -> tuple[str, str]:
    if name != "search_kb":
        raise ValueError(f"Unknown KB tool: {name}")

    query = str(arguments.get("query") or "").strip()
    if not query:
        raise ValueError("query is required")

    sku_result = _find_by_sku(query)
    if sku_result:
        doc_id, text, sku = sku_result
        result = {
            "document_id": doc_id,
            "match_method": "sku_exact",
            "sku": sku,
            "full_document_text": text,
        }
        return json.dumps(result), doc_id

    doc_id, text = _find_by_bm25(query)
    result = {
        "document_id": doc_id,
        "match_method": "bm25",
        "full_document_text": text,
    }
    return json.dumps(result), doc_id
