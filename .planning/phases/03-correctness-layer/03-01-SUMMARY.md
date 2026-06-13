---
phase: 03-correctness-layer
plan: 01
subsystem: api
tags: [pagination, aggregation, crm, calls, tdd, pytest]

requires:
  - phase: 02-all-4-verticali-kb
    provides: CRM/ERP/calls/KB tools and submit_answer verticale extraction
provides:
  - MockApiClient.get_all_pages pagination helper (follows pagination.total)
  - CRM list_opportunities group_by=customer_channel Python-side totals (Q6)
  - count_calls_by_defect paginated, targeted-search defect counter (Q11)
affects: [phase-3-traps-multihop, phase-4-artifacts-ui]

tech-stack:
  added: []
  patterns:
    - get_all_pages caps limit at 200, stops on total or empty page, no param mutation
    - Aggregate totals/counts computed in Python from full row set, never in the LLM
    - Defect counting via targeted /calls/{id}/transcript?search= (no full downloads)

key-files:
  created:
    - backend/tests/test_phase3_pagination.py
  modified:
    - backend/services/api_client.py
    - backend/agent/tools/crm.py
    - backend/agent/tools/calls.py

key-decisions:
  - "get_all_pages advances offset by collected-row count and stops on pagination.total or empty page"
  - "Customer-specific opportunity lookups keep single-call behavior to preserve Q1 contract"
  - "count_calls_by_defect searches every call's transcript with a targeted search term (correctness over minimal calls)"

metrics:
  duration: 20min
  tasks: 3
  files: 4
  completed: 2026-06-13
---

# Phase 3 Plan 01: Pagination & Python Aggregation Summary

**Shared `get_all_pages` helper plus pagination-aware CRM channel grouping (Q6) and a paginated broken-pasta defect counter (Q11), all summing in Python with TDD coverage.**

## Performance

- **Duration:** ~20 min
- **Tasks:** 3
- **Files modified:** 4 (1 created, 3 modified)

## Accomplishments

- `MockApiClient.get_all_pages(path, params, limit=200, data_key="data")` follows `pagination.total`, caps per-page `limit` at 200, stops on empty pages, and never mutates the caller's params dict (mitigates DoS threat T-03-01).
- `list_opportunities` gained a `group_by` argument; `group_by="customer_channel"` pages every negotiation opportunity and computes GDO / distributor / horeca totals in Python, with `/crm/customers/{id}` lookups only as a fallback when the row lacks a channel field. Existing customer-specific Q1 behaviour (count 4 / 740000 via a single call) is preserved.
- New `count_calls_by_defect` calls tool pages the entire call log via `get_all_pages("/calls")`, then runs a targeted `?search=<defect>` transcript query per call, counts matches in Python, and returns `count`, `searched_call_count`, and a capped `matching_call_ids_sample` — giving the LLM a deterministic single-tool path for Q11.
- Both new tools auto-register through the existing `get_tool_definitions()` aggregation in `agent/tools/__init__.py` (no loop changes needed).

## Task Commits

1. **Task 1: Failing multi-page aggregate tests (RED)** - `17eed6b` (test)
2. **Task 2: get_all_pages + CRM channel grouping (GREEN)** - `c731850` (feat)
3. **Task 3: Paginated broken-pasta complaint counter (GREEN)** - `6e27231` (feat)

## Verification

- `uv run pytest tests/test_phase3_pagination.py tests/test_phase2_q1_q4.py::test_list_opportunities_cust_0132_open_stats -q` → 4 passed.
- `uv run pytest -m "not integration" -q` → 10 passed, 19 deselected.
- Live integration cases (`q06_crm_negotiation_by_channel`, `q11_calls_broken_pasta_count`) require `MOCK_API_TOKEN`/`LLM_API_KEY` and were not run in this sandbox.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Corrected an arithmetic typo in my own RED test**
- **Found during:** Task 2 verification
- **Issue:** The horeca assertion expected 375 but the fixture rows sum to 325 (300 + 25); the implementation was correct.
- **Fix:** Updated the expected value to 325 in `test_phase3_pagination.py`.
- **Files modified:** backend/tests/test_phase3_pagination.py
- **Commit:** c731850

`backend/tests/test_sample_questions.py` was listed in the plan's file set but needed no change — Q6/Q11 are already isolated with ids `q06_crm_negotiation_by_channel` and `q11_calls_broken_pasta_count` and already assert the channel totals and count 9.

## Threat Surface

Threat model mitigations were honoured: T-03-01 (page cap + total/empty-page stop), T-03-02 (Python arithmetic asserted by unit tests), T-03-03 (targeted transcript search, segment cap, no full downloads). No new threat surface introduced; `/ask` schema and auth are unchanged.

## Self-Check: PASSED

- FOUND: backend/services/api_client.py
- FOUND: backend/agent/tools/crm.py
- FOUND: backend/agent/tools/calls.py
- FOUND: backend/tests/test_phase3_pagination.py
- FOUND: 17eed6b
- FOUND: c731850
- FOUND: 6e27231

---
*Phase: 03-correctness-layer*
*Completed: 2026-06-13*
