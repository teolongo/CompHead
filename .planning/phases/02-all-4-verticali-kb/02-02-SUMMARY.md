---
phase: 02-all-4-verticali-kb
plan: 02
subsystem: api
tags: [calls, transcript-search, agent-tools, pytest]

requires:
  - phase: 02-all-4-verticali-kb
    provides: CRM/ERP barrel pattern from 02-01
provides:
  - list_calls and search_transcript tools with pre-computed fields
  - Q3 unit and integration tests
  - Calls routing in SYSTEM_PROMPT and barrel dispatch
affects: [02-03, 02-04]

tech-stack:
  added: []
  patterns:
    - Two-step calls workflow list_calls then search_transcript
    - Hybrid transcript payload with Python-extracted complaint_type and lot_id
    - 20-segment cap on transcript search results

key-files:
  created:
    - backend/agent/tools/calls.py
    - backend/tests/test_calls_q3.py
  modified:
    - backend/agent/tools/__init__.py
    - backend/agent/prompts.py

key-decisions:
  - "Two separate tools list_calls and search_transcript per D-09"
  - "Pre-compute most_recent_call_id sorted by date desc per D-10"
  - "Extract complaint_type via keyword heuristics and lot_id via LOT-YYYY-NNNN regex per D-11"
  - "Cap matched_segments at 20 per D-12; validate call_id CALL-\\d+ before API call"

requirements-completed: [CALLS-01]

duration: 8min
completed: 2026-06-13
---

# Phase 2 Plan 02: Calls Vertical Slice Summary

**Two-tool calls workflow with surgical transcript search, pre-computed complaint/lot extraction, and Q3 E2E passing**

## Performance

- **Duration:** 8 min
- **Started:** 2026-06-13T10:37:43Z
- **Completed:** 2026-06-13T10:45:00Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments

- `list_calls` pre-computes `most_recent_call_id` sorted by date descending
- `search_transcript` returns hybrid payload with `complaint_type`, `lot_id`, and capped segments
- Barrel and SYSTEM_PROMPT wired for two-step calls workflow
- All Q3 tests pass including live integration with configured `.env`

## Task Commits

Each task was committed atomically:

1. **Task 1: Failing Q3 tests for calls tools** - `133fa43` (test)
2. **Task 2: Implement list_calls and search_transcript tools** - `4011b8a` (feat)
3. **Task 3: Wire calls into barrel and prompts** - `2dac20f` (feat)

## Files Created/Modified

- `backend/agent/tools/calls.py` - list_calls and search_transcript with pre-computed fields
- `backend/tests/test_calls_q3.py` - Unit tests + Q3 integration test
- `backend/agent/tools/__init__.py` - CALLS_TOOLS dispatch via run_tool
- `backend/agent/prompts.py` - Calls two-step workflow guidance in SYSTEM_PROMPT

## Decisions Made

- Followed crm.py/erp.py module pattern with single `run_calls_tool` dispatcher
- Complaint extraction uses keyword heuristics (broken → "broken pasta", quality, complaint)
- Lot ID extracted via `LOT-\d{4}-\d{4}` regex on matched segment text
- call_id validated with `^CALL-\d+$` before transcript API call (T-02-05)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required beyond existing `.env` (MOCK_API_TOKEN, LLM_API_KEY for integration test).

## Verification

```bash
cd backend && uv run pytest tests/test_calls_q3.py -q
# 4 passed (3 unit + 1 integration with .env)
```

## Next Phase Readiness

- Calls vertical slice complete; ready for 02-03 (KB) and 02-04 (verticale extraction + loop MAX_ITERATIONS)
- Q3 answer path verified: NordSpesa CUST-0137 → CALL-58020 → broken pasta on LOT-2026-0658

## Self-Check: PASSED

- FOUND: backend/agent/tools/calls.py
- FOUND: backend/tests/test_calls_q3.py
- FOUND: commit 133fa43
- FOUND: commit 4011b8a
- FOUND: commit 2dac20f
- pytest tests/test_calls_q3.py: 4 passed

---
*Phase: 02-all-4-verticali-kb*
*Completed: 2026-06-13*
