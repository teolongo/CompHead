---
phase: 02-all-4-verticali-kb
plan: 04
subsystem: api
tags: [crm, verticale, submit_answer, pytest, agent-loop]

requires:
  - phase: 02-all-4-verticali-kb
    provides: ERP, calls, KB tools from plans 02-01 through 02-03
provides:
  - Expanded CRM tools (customers, orders, invoices)
  - submit_answer terminal tool with verticale extraction (D-13)
  - MAX_ITERATIONS=8 and per-verticale routing prompts (D-15, D-16)
  - Q1-Q4 integration test battery
affects: [phase-3-pagination-traps, phase-4-artifacts-ui]

tech-stack:
  added: []
  patterns:
    - submit_answer terminal tool with sources-based verticale fallback
    - CRM mixed granularity (pre-computed opportunities, thin list tools)
    - LLM retry with exponential backoff on 429

key-files:
  created:
    - backend/tests/test_phase2_q1_q4.py
  modified:
    - backend/agent/tools/crm.py
    - backend/agent/tools/__init__.py
    - backend/agent/loop.py
    - backend/agent/prompts.py

key-decisions:
  - "submit_answer tool in __init__.py as terminal step with validated verticale enum"
  - "Sources-based _infer_verticale fallback when LLM skips submit_answer"
  - "LLM retry with 2/4/8s backoff for rate limit errors during agent loop"

patterns-established:
  - "Terminal submit_answer: loop breaks on submit_answer call, no source added"
  - "CRM dispatch pattern: four list tools with pre-computed summaries"

requirements-completed: [CRM-01]

duration: 25min
completed: 2026-06-13
---

# Phase 2 Plan 04: Verticale Extraction & CRM Expansion Summary

**submit_answer terminal tool with validated verticale enum, expanded CRM list tools, and Q1-Q4 integration battery**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-06-13T00:00:00Z
- **Completed:** 2026-06-13T00:25:00Z
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments

- Parametrized Q1-Q4 integration test battery with unit test for CUST-0132 opportunities
- CRM module expanded with list_customers, list_orders, list_invoices (CRM-01)
- submit_answer tool replaces hardcoded verticale; MAX_ITERATIONS=8; full per-verticale routing in SYSTEM_PROMPT
- All four Q1-Q4 integration tests pass when run sequentially with env configured

## Task Commits

1. **Task 1: Failing Q1-Q4 integration test battery** - `662f8f5` (test)
2. **Task 2: Expand CRM tools** - `afe665b` (feat)
3. **Task 3: Verticale extraction and routing prompts** - `88f80d9` (feat)

## Files Created/Modified

- `backend/tests/test_phase2_q1_q4.py` - Q1-Q4 parametrized integration battery + Q1 unit test
- `backend/agent/tools/crm.py` - Four CRM tools with pre-computed summaries
- `backend/agent/tools/__init__.py` - submit_answer tool definition and dispatch
- `backend/agent/loop.py` - MAX_ITERATIONS=8, verticale extraction, LLM retry backoff
- `backend/agent/prompts.py` - Per-verticale routing hints and submit_answer instruction

## Decisions Made

- Centralized submit_answer in `__init__.py` rather than a separate answer.py module
- Added `_chat_completion` retry helper in loop.py for Mistral/Regolo rate limits (~1 req/s)
- Kept list_opportunities open-stage logic unchanged for Q1 compatibility

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] LLM retry with backoff on 429 rate limits**
- **Found during:** Task 3 verification
- **Issue:** Parallel integration tests hit provider rate limits; agent returned error answers
- **Fix:** Added `_chat_completion` with 3 retries and exponential backoff (2/4/8s)
- **Files modified:** backend/agent/loop.py
- **Verification:** Q1-Q4 pass when run sequentially with env loaded
- **Committed in:** 88f80d9

---

**Total deviations:** 1 auto-fixed (1 missing critical)
**Impact on plan:** Retry is required per AGENTS.md; no scope creep.

## Issues Encountered

- LLM provider rate limits cause failures when all integration tests run in one pytest invocation; tests pass individually or with ~15s gaps between calls. Unit tests (7) pass without env keys.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 2 goal met: all four verticali wired with correct verticale tagging
- Ready for Phase 3: pagination aggregation, trap handling, deploy

## Self-Check: PASSED

- FOUND: backend/tests/test_phase2_q1_q4.py
- FOUND: backend/agent/tools/crm.py
- FOUND: backend/agent/loop.py
- FOUND: backend/agent/tools/__init__.py
- FOUND: backend/agent/prompts.py
- FOUND: 662f8f5
- FOUND: afe665b
- FOUND: 88f80d9

---
*Phase: 02-all-4-verticali-kb*
*Completed: 2026-06-13*
