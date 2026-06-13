---
phase: 02-all-4-verticali-kb
verified: 2026-06-13T12:00:00Z
status: human_needed
score: 4/5 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Run Q1-Q4 integration battery with dotenv loaded and ≥2s delay between tests"
    expected: "All four test_phase2_integration cases pass; answers contain reference facts and correct verticale"
    why_human: "Mistral free-tier rate limits (429) caused Q3 and batch runs to fail during automated verification; Q1/Q2/Q4 passed individually with dotenv"
  - test: "Run `cd backend && uv run pytest tests/ -q` after adding dotenv to conftest"
    expected: "Integration tests execute (not skip) when .env is present; unit + integration green"
    why_human: "conftest.py does not call load_dotenv(); default pytest run skips all 7 integration tests even when backend/.env is configured"
gaps:
  - truth: "Sample questions 1-4 pass locally"
    status: partial
    reason: "Default `pytest tests/ -q` skips all integration tests (7 passed, 7 skipped). With dotenv, Q1/Q2/Q4 pass individually; Q3 failed with 429 rate limit in sequential retries; full `-m integration` battery failed 6/7 on rate limits."
    artifacts:
      - path: backend/tests/conftest.py
        issue: "Missing load_dotenv() — integration tests skip unless env vars exported manually"
    missing:
      - "Add load_dotenv() to conftest.py so local pytest loads backend/.env"
      - "Re-run Q1-Q4 integration battery sequentially after rate-limit cooldown to confirm E2E pass"
---

# Phase 2: All 4 Verticali + KB Verification Report

**Phase Goal:** Agent handles crm, erp, calls, and kb questions with proper tools.
**Verified:** 2026-06-13T12:00:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
| --- | ------- | ---------- | -------------- |
| 1 | CRM tools cover customers, opportunities, orders, invoices with filters | ✓ VERIFIED | `crm.py` defines `list_opportunities`, `list_customers`, `list_orders`, `list_invoices` with API filters; barrel dispatch in `__init__.py` |
| 2 | ERP tools cover inventory, production, BOM, suppliers, shipments | ✓ VERIFIED | `erp.py` defines `get_inventory` (pre-computed below_minimum/on_hand/minimum) plus `list_bom`, `list_suppliers`, `list_production_orders`, `list_shipments` |
| 3 | Calls tool uses transcript search with `?search=` (not full download) | ✓ VERIFIED | `calls.py` `_run_search_transcript` calls `get_client().get(f"/calls/{call_id}/transcript", params={"search": search})`; segments capped at 20 |
| 4 | KB retrieval over `data/kb/` with whole-doc return | ✓ VERIFIED | `kb.py` SKU exact match + BM25 fallback; returns `full_document_text`; source is `DOC-###`; `rank-bm25>=0.2.2` in pyproject.toml |
| 5 | Sample questions Q1-Q4 pass locally | ? UNCERTAIN | Unit tests 7/7 pass; integration Q1/Q2/Q4 pass individually with dotenv; Q3 flaky (429); default pytest skips integration |

**Score:** 4/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | ----------- | ------ | ------- |
| `backend/agent/tools/crm.py` | CRM vertical tools | ✓ VERIFIED | 4 list tools, pre-computed opportunity stats, SAMPLE_CAP=100 |
| `backend/agent/tools/erp.py` | ERP vertical tools | ✓ VERIFIED | get_inventory + 4 thin list tools |
| `backend/agent/tools/calls.py` | Calls two-tool workflow | ✓ VERIFIED | list_calls + search_transcript |
| `backend/agent/tools/kb.py` | KB SKU + BM25 retrieval | ✓ VERIFIED | Whole-doc return, DOC-### sources |
| `backend/agent/tools/__init__.py` | Barrel dispatch + submit_answer | ✓ VERIFIED | Merges all 4 verticali + terminal submit_answer tool |
| `backend/agent/loop.py` | Agent loop with verticale extraction | ✓ VERIFIED | MAX_ITERATIONS=8; verticale from submit_answer; _infer_verticale fallback |
| `backend/agent/prompts.py` | Per-verticale routing hints | ✓ VERIFIED | CRM/ERP/calls/kb sections with tool guidance |
| `backend/tests/test_phase2_q1_q4.py` | Q1-Q4 integration battery | ✓ VERIFIED | Parametrized integration tests exist with correct assertions |

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | --- | --- | ------ | ------- |
| `loop.py` | `tools/__init__.py` | `run_tool` dispatch | ✓ WIRED | `from agent.tools import get_tool_definitions, run_tool` |
| `tools/__init__.py` | `crm/erp/calls/kb` | barrel routing | ✓ WIRED | CRM_TOOLS/ERP_TOOLS/CALLS_TOOLS/KB_TOOLS sets |
| `loop.py` | submit_answer | verticale extraction | ✓ WIRED | Parses submit_answer payload; `_validate_verticale` |
| `main.py` | `run_agent` | POST /ask | ✓ WIRED | Returns AskResponse with answer/sources/verticale |
| `calls.py` | `/calls/{id}/transcript` | search param | ✓ WIRED | `params={"search": search}` confirmed |
| `kb.py` | `data/kb/` | DOC-*.md glob | ✓ WIRED | `_KB_DIR` resolves to backend/data/kb |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| `crm.py` list_opportunities | count, total_value_eur | get_client().get("/crm/opportunities") | Yes (Python pre-compute) | ✓ FLOWING |
| `erp.py` get_inventory | below_minimum, on_hand_qty | get_client().get("/erp/inventory") | Yes (Python pre-compute) | ✓ FLOWING |
| `calls.py` search_transcript | complaint_type, lot_id | transcript segments via search= | Yes (regex extraction) | ✓ FLOWING |
| `kb.py` search_kb | full_document_text | DOC-*.md filesystem read | Yes (DOC-001 for PAS-SPA-500) | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Unit tests (all verticali tools) | `cd backend && uv run pytest tests/ -q` | 7 passed, 7 skipped in 0.12s | ✓ PASS |
| Q1 integration (with dotenv) | `pytest test_phase2_integration[q1_crm]` | 1 passed in 9.28s | ✓ PASS |
| Q2 integration (with dotenv) | `pytest test_phase2_integration[q2_erp]` | 1 passed in 15.50s | ✓ PASS |
| Q3 integration (with dotenv) | `pytest test_phase2_integration[q3_calls]` | 429 rate limit error | ✗ FAIL |
| Q4 integration (with dotenv) | `pytest test_phase2_integration[q4_kb]` | 1 passed in 14.49s | ✓ PASS |
| Full integration battery | `pytest -m integration` (with dotenv) | 1 passed, 6 failed (429) | ✗ FAIL |

### Probe Execution

Step 7c: SKIPPED — no probe scripts declared for this phase.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ---------- | ----------- | ------ | -------- |
| CRM-01 | 02-04 | Search/list customers, opportunities, orders, invoices | ✓ SATISFIED | Four CRM tools in crm.py |
| ERP-01 | 02-01 | Query production, inventory, suppliers, BOM, shipments | ✓ SATISFIED | Five ERP tools in erp.py |
| CALLS-01 | 02-02 | List calls; search transcripts surgically | ✓ SATISFIED | list_calls + search_transcript with search= |
| KB-01 | 02-03 | Retrieve relevant KB documents by query | ✓ SATISFIED | search_kb with SKU + BM25 |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| — | — | No TBD/FIXME/stub markers in agent/ | — | Clean |

### Human Verification Required

### 1. Q1-Q4 End-to-End Integration Battery

**Test:** Load dotenv, run each `test_phase2_integration` case sequentially with ≥2s delay between tests (or after rate-limit cooldown).
**Expected:** All four cases pass with correct facts, verticale, and non-empty sources.
**Why human:** Mistral free-tier 429 errors blocked automated batch verification; Q3 requires two-step LLM loop (more API calls).

### 2. Default Pytest Local Run

**Test:** Run `cd backend && uv run pytest tests/ -q` as documented in phase workflow.
**Expected:** Integration tests run (not skip) when `.env` exists.
**Why human:** `conftest.py` lacks `load_dotenv()` — current run skips 7 integration tests despite configured `.env`.

### Gaps Summary

Implementation for all four verticali is complete and wired: barrel dispatch, submit_answer verticale extraction, per-domain tools, and unit tests all pass. The phase goal's explicit criterion "Sample questions 1-4 pass locally" is not fully verified: the canonical `pytest tests/ -q` command skips integration tests, and running integration with dotenv hit Mistral rate limits (Q3 failed; batch run 6/7 failed). Q1, Q2, and Q4 integration tests passed individually, and Q3 tool-layer unit tests pass — suggesting the gap is test infrastructure (conftest dotenv) and LLM provider rate limits rather than missing tool code.

---

_Verified: 2026-06-13T12:00:00Z_
_Verifier: Claude (gsd-verifier)_
