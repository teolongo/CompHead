# Phase 2: All 4 Verticali + KB - Pattern Map

**Mapped:** 2026-06-13
**Files analyzed:** 8
**Analogs found:** 7 / 8

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `backend/agent/tools/erp.py` | service (LLM tool) | request-response, transform | `backend/agent/tools/crm.py` | exact |
| `backend/agent/tools/calls.py` | service (LLM tool) | request-response, transform | `backend/agent/tools/crm.py` | exact |
| `backend/agent/tools/kb.py` | service (LLM tool) | file-I/O, transform | `backend/agent/tools/crm.py` + `backend/main.py` (Path) | role-match |
| `backend/agent/tools/crm.py` | service (LLM tool) | request-response, transform | `backend/agent/tools/crm.py` (extend in place) | exact |
| `backend/agent/tools/__init__.py` | utility (barrel) | merge/dispatch | `backend/agent/loop.py` (current import pattern) | partial |
| `backend/agent/loop.py` | controller (orchestrator) | request-response | `backend/agent/loop.py` (extend in place) | exact |
| `backend/agent/prompts.py` | config | — | `backend/agent/prompts.py` (extend in place) | exact |
| `backend/pyproject.toml` | config | — | `backend/pyproject.toml` (uncomment dep) | exact |

---

## Pattern Assignments

### `backend/agent/tools/erp.py` (service, request-response + transform)

**Analog:** `backend/agent/tools/crm.py`

**Module header + imports** (lines 1-10):

```python
"""CRM tools for the agent loop."""

from __future__ import annotations

import json
from typing import Any

from services.api_client import get_client
```

Adapt docstring to `"""ERP tools for the agent loop."""`. Same import block; add domain constants if needed (e.g. inventory types).

**Tool schema pattern** (lines 12-38):

```python
TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "list_opportunities",
            "description": (
                "List CRM opportunities with optional filters. Returns count, total EUR "
                "value, and a sample of rows. Open stages are qualification and negotiation."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_id": {
                        "type": "string",
                        "description": "Filter by customer id, e.g. CUST-0132",
                    },
                    ...
                },
                "additionalProperties": False,
            },
        },
    }
]
```

For ERP inventory (Q2): define `get_inventory` (or similar) with `sku`, `below_min`, `type` filters per `API.md`. Description must state pre-computed fields (`below_minimum`, `on_hand_qty`, `minimum_qty`) so the LLM does not compare raw rows.

**Public exports** (lines 41-42):

```python
def get_tool_definitions() -> list[dict[str, Any]]:
    return TOOL_DEFINITIONS
```

**Pre-computation helper** (lines 45-48):

```python
def _compute_open_stats(rows: list[dict[str, Any]]) -> tuple[int, float]:
    open_rows = [row for row in rows if row.get("stage") in OPEN_STAGES]
    total = sum(float(row.get("value_eur") or row.get("value") or 0) for row in open_rows)
    return len(open_rows), total
```

Mirror with `_compute_inventory_status(row)` returning explicit booleans and quantities before JSON serialization.

**Tool executor + source string** (lines 51-79):

```python
def run_crm_tool(name: str, arguments: dict[str, Any]) -> tuple[str, str]:
    if name != "list_opportunities":
        raise ValueError(f"Unknown CRM tool: {name}")

    params: dict[str, str] = {}
    if customer_id := arguments.get("customer_id"):
        params["customer_id"] = customer_id
    ...

    payload = get_client().get("/crm/opportunities", params=params or None)
    rows = payload.get("data") or []

    ...
    result = {
        "count": count,
        "total_value_eur": total,
        "opportunities_sample": rows[:5],
        "note": (...),
    }
    return json.dumps(result), "crm/opportunities"
```

ERP pattern: `run_erp_tool(name, arguments) -> tuple[str, str]`; call `get_client().get("/erp/inventory", params=...)`; return source `"erp/inventory"`. Cap sample rows at 100 (D-03). Compute `below_minimum: bool`, `on_hand_qty`, `minimum_qty` in Python (D-01, D-02).

---

### `backend/agent/tools/calls.py` (service, request-response + transform)

**Analog:** `backend/agent/tools/crm.py` (two tools in one module, same executor dispatch style)

**API client usage** — same as CRM (via `get_client().get()`):

```python
payload = get_client().get("/crm/opportunities", params=params or None)
rows = payload.get("data") or []
```

Calls endpoints (from `API.md`):
- `GET /calls` — filters: `customer_id`, `type`, `outcome`, `from`, `to`
- `GET /calls/{id}/transcript` — params: `search`, `speaker`, `offset`, `limit`

**Two-tool module structure** (D-09): one `TOOL_DEFINITIONS` list with `list_calls` and `search_transcript` entries; single `run_calls_tool(name, arguments)` with `if name == "list_calls": ... elif name == "search_transcript": ... else: raise ValueError(...)`.

**Pre-compute "most recent call"** (D-10): after fetching `/calls`, sort rows by date descending in Python; surface `most_recent_call_id`, date, customer metadata when question implies "last call". Do not leave ordering to the LLM.

**Transcript hybrid payload** (D-11, D-12):

```python
result = {
    "count": count,
    "total_value_eur": total,
    "opportunities_sample": rows[:5],
    "note": (...),
}
return json.dumps(result), "crm/opportunities"
```

Adapt to:

```python
result = {
    "call_id": call_id,
    "complaint_type": extracted_type,      # pre-extracted in Python where possible
    "lot_id": extracted_lot,               # regex/heuristic on matched segments
    "matched_segments": segments[:20],       # cap at 20 (D-12)
}
return json.dumps(result), f"calls/{call_id}/transcript"
```

Source strings: `"calls"` for list; `"calls/{id}/transcript"` for transcript search (matches Phase 1 `"crm/opportunities"` convention).

---

### `backend/agent/tools/kb.py` (service, file-I/O + transform)

**Analog (tool shape):** `backend/agent/tools/crm.py`
**Analog (filesystem):** `backend/main.py`

**Path resolution** (main.py lines 26-28):

```python
_STATIC = Path(__file__).resolve().parent / "static"
_FILES = _STATIC / "files"
_FILES.mkdir(parents=True, exist_ok=True)
```

KB index root:

```python
_KB_DIR = Path(__file__).resolve().parents[2] / "data" / "kb"
```

(or `Path(__file__).resolve().parent.parent / "data" / "kb"` from `backend/agent/tools/kb.py`).

**Tool executor return shape** — copy CRM JSON + source pattern:

```python
return json.dumps(result), "crm/opportunities"
```

KB sources use document IDs only (D-07): return `"DOC-001"`, not file paths.

**Result payload** (D-05, D-06):

```python
result = {
    "document_id": "DOC-001",
    "match_method": "sku_exact",  # or "bm25"
    "sku": "PAS-SPA-500",         # when matched
    "full_document_text": text,   # whole doc, no chunking (D-06)
}
return json.dumps(result), "DOC-001"
```

**Two-stage retrieval** (D-05): (1) scan all `DOC-*.md` for exact SKU string; (2) if no hit, BM25 over full document bodies via `rank-bm25`. Index build strategy is planner discretion (startup vs lazy).

**No existing BM25/index code** in repo — implement net-new using `rank-bm25>=0.2.2` per pyproject.toml comment.

---

### `backend/agent/tools/crm.py` (service, extend)

**Analog:** self (Phase 1 reference implementation)

Extend using the same patterns already in file. Optional additional list tools (customers, orders, invoices) follow identical structure: `TOOL_DEFINITIONS` entry → `run_crm_tool` branch → `get_client().get("/crm/...")` → pre-computed summary → `json.dumps`, source `"crm/{endpoint}"`.

Keep `OPEN_STAGES` convention for open-opportunity logic (lines 10, 45-48, 64-68).

---

### `backend/agent/tools/__init__.py` (utility, merge/dispatch)

**Analog:** `backend/agent/loop.py` lines 9, 37 (current single-module import)

Current stub:

```python
"""LLM tool definitions and executors."""
```

**Target pattern** — aggregate from all verticale modules (planner discretion on exact API):

```python
from agent.tools.crm import get_tool_definitions as get_crm_tools, run_crm_tool
from agent.tools.erp import get_tool_definitions as get_erp_tools, run_erp_tool
from agent.tools.calls import get_tool_definitions as get_calls_tools, run_calls_tool
from agent.tools.kb import get_tool_definitions as get_kb_tools, run_kb_tool

def get_tool_definitions() -> list[dict[str, Any]]:
    return get_crm_tools() + get_erp_tools() + get_calls_tools() + get_kb_tools()

def run_tool(name: str, arguments: dict[str, Any]) -> tuple[str, str]:
    # dispatch by tool name prefix or explicit registry
    ...
```

Loop should import from `agent.tools` (barrel) instead of `agent.tools.crm` only.

---

### `backend/agent/loop.py` (controller, request-response)

**Analog:** self (extend Phase 1 loop)

**Imports** (lines 8-10):

```python
from agent.prompts import SYSTEM_PROMPT
from agent.tools.crm import get_tool_definitions, run_crm_tool
from services.llm_client import get_llm_client, get_model
```

Change to barrel import: `from agent.tools import get_tool_definitions, run_tool`.

**Constants** (line 12):

```python
MAX_ITERATIONS = 5
```

Increase to `8` (D-16) for list_calls → search_transcript chains.

**Tool dispatch** (lines 25-27):

```python
def _execute_tool(name: str, arguments: str) -> tuple[str, str]:
    args = json.loads(arguments) if arguments else {}
    return run_crm_tool(name, args)
```

Replace with unified `run_tool(name, args)` dispatching to crm/erp/calls/kb executors.

**Sources accumulation** (lines 72-78):

```python
for call in tool_calls:
    result, source = _execute_tool(
        call.function.name,
        call.function.arguments or "{}",
    )
    if source not in sources:
        sources.append(source)
```

Keep dedup logic unchanged for all verticali.

**Verticale extraction** (lines 32, 101):

```python
verticale = "crm"
...
return {
    "answer": answer,
    "sources": sources,
    "verticale": verticale,
    ...
}
```

Replace hardcoded `"crm"` (D-13). No existing extraction mechanism — options (planner discretion):
- Parse JSON block from final assistant message, e.g. `{"verticale": "erp", "answer": "..."}`
- Require LLM to call a no-op `declare_answer` tool with `verticale` + `answer` fields
- Regex/keyword fallback from `sources` prefix (`crm/`, `erp/`, `calls/`, `DOC-`)

Prompt already hints at verticale (prompts.py line 8); loop must enforce reliable extraction.

**Message text extraction** (lines 15-22):

```python
def _extract_message_text(message: Any) -> str:
    content = getattr(message, "content", None)
    if content:
        return content.strip()
    reasoning = getattr(message, "reasoning_content", None)
    if reasoning:
        return reasoning.strip()
    return ""
```

Keep for Regolo reasoning models.

**Error handling — HTTP 200 path** (lines 104-110):

```python
except Exception as exc:
    return {
        "answer": f"I cannot answer right now because of an error: {exc}",
        "sources": sources,
        "verticale": verticale,
        "artifact_url": None,
    }
```

Same pattern for all verticali; never raise to FastAPI for agent failures.

**Agent loop core** (lines 43-90):

```python
for _ in range(MAX_ITERATIONS):
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        tools=tools,
        tool_choice="auto",
    )
    ...
    if tool_calls:
        messages.append({...})
        for call in tool_calls:
            ...
        continue

    answer = _extract_message_text(message)
    if answer:
        break
```

Unchanged structure; only tools list grows. Supports parallel tool_calls in one round (existing pattern).

---

### `backend/agent/prompts.py` (config)

**Analog:** self (extend)

**Current prompt** (lines 3-11):

```python
SYSTEM_PROMPT = """You are the company brain for Al Dente S.r.l., a pasta manufacturer.

Rules:
- Answer using the provided tools only. Never invent customers, figures, or policies.
- When tools return computed totals or counts, use those exact numbers in your answer.
- Set verticale to the dominant data source: crm for CRM questions, erp, calls, or kb otherwise.
- If data is missing, say honestly that it is not available in the sources.
- Respond in English with concise, factual answers.
"""
```

Expand (D-15) with per-verticale routing hints:
- **crm**: opportunities, customers, orders, invoices; open = qualification + negotiation
- **erp**: inventory (`below_min`, SKU search), BOM, suppliers, lots, shipments
- **calls**: use `list_calls` first for "last call", then `search_transcript` with `search=` — never request full transcript
- **kb**: product specs (shelf life, allergens), policies, price list; tools return full document text

Align verticale declaration mechanism with loop extraction (D-13).

---

### `backend/pyproject.toml` (config)

**Analog:** self — uncomment existing suggestion (line 13):

```toml
    # "rank-bm25>=0.2.2",        # lightweight lexical retrieval, zero infra
```

Change to active dependency:

```toml
    "rank-bm25>=0.2.2",
```

Run `uv sync` after edit. No other deps needed for Phase 2.

---

## Shared Patterns

### Mock API client (all API tools)

**Source:** `backend/services/api_client.py`
**Apply to:** `erp.py`, `calls.py`, extended `crm.py`

```python
class MockApiClient:
    def get(self, path: str, params: dict | None = None) -> dict:
        url = f"{self._base_url}{path if path.startswith('/') else f'/{path}'}"
        response = self._client.get(
            url,
            params=params,
            headers={"Authorization": f"Bearer {self._token}"},
        )
        if response.status_code >= 400:
            ...
        return response.json()

def get_client() -> MockApiClient:
    return MockApiClient(get_settings())
```

Pagination envelope: `payload.get("data") or []`, `payload.get("pagination", {}).get("total")`. Phase 2 sample questions are single-page; still read `API.md` filters to avoid bulk downloads.

### Pre-computed tool JSON (accuracy-first)

**Source:** `backend/agent/tools/crm.py` lines 70-78
**Apply to:** all new tools (D-01, D-02, D-04)

```python
result = {
    "count": count,
    "total_value_eur": total,
    "opportunities_sample": rows[:5],
    "note": (...),  # optional; only when it helps reliability
}
return json.dumps(result), "crm/opportunities"
```

Rules: Python computes aggregates/comparisons; explicit boolean fields (`below_minimum`); cap samples at 100 rows / 20 transcript segments; final `/ask` answer is fluent English (not raw JSON).

### Source string convention

**Source:** `backend/agent/tools/crm.py` line 79; `backend/main.py` AskResponse
**Apply to:** all tools

| Verticale | Source format | Example |
|-----------|---------------|---------|
| CRM | `crm/{endpoint}` | `crm/opportunities` |
| ERP | `erp/{endpoint}` | `erp/inventory` |
| Calls | `calls` or `calls/{id}/transcript` | `calls/CALL-58020/transcript` |
| KB | `DOC-###` only | `DOC-001` |

Loop deduplicates before returning (loop.py lines 77-78).

### POST /ask contract (unchanged)

**Source:** `backend/main.py` lines 44-71

```python
class AskResponse(BaseModel):
    answer: str
    sources: list[str]
    verticale: str  # one of: "crm", "erp", "calls", "kb"
    artifact_url: str | None = None

@app.post("/ask", response_model=AskResponse)
def ask(request: AskRequest) -> AskResponse:
    try:
        result = run_agent(request.question)
        return AskResponse(**result)
    except Exception as exc:
        return AskResponse(
            answer=f"I cannot answer right now because of an error: {exc}",
            sources=[],
            verticale="crm",
            artifact_url=None,
        )
```

Phase 2 does not modify `main.py` unless barrel imports require it (not expected).

### LLM client factory

**Source:** `backend/services/llm_client.py`
**Apply to:** `loop.py` only

```python
def get_llm_client() -> OpenAI:
    settings = get_settings()
    return OpenAI(api_key=settings.LLM_API_KEY, base_url=settings.LLM_BASE_URL)
```

Tool-calling requires model with function support (`get_model()`).

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| Verticale extraction in `loop.py` | orchestration metadata | transform | Phase 1 hardcodes `"crm"`; no structured-output or declare-answer pattern exists yet (D-13 — planner discretion) |
| BM25 index + SKU scan in `kb.py` | retrieval | batch/transform | No RAG/retrieval code in repo; only commented pyproject suggestion |

---

## Metadata

**Analog search scope:** `backend/agent/`, `backend/services/`, `backend/main.py`, `backend/pyproject.toml`, `backend/data/kb/` (structure only)
**Files scanned:** 12 Python modules + pyproject + 1 KB sample doc
**Pattern extraction date:** 2026-06-13

**Phase 2 success targets (from CONTEXT.md):**
- Q1: CRM aggregate (existing `list_opportunities`)
- Q2: ERP inventory below minimum — `PAS-PEN-500`, on-hand 462 vs min 2000
- Q3: Calls last NordSpesa complaint — lot `LOT-2026-0658`, call `CALL-58020`
- Q4: KB shelf life + allergens — `PAS-SPA-500` from `DOC-001`, 36 months, gluten (+ may contain soy, mustard)
