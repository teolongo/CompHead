---
phase: 02-all-4-verticali-kb
plan: 01
subsystem: api
tags: [erp, inventory, pytest, tool-calling, barrel-pattern]

requires:
  - phase: 01-agent-skeleton-first-answer
    provides: CRM tool pattern, agent loop, api_client
provides:
  - get_inventory ERP tool with Python-side stock comparison
  - Thin ERP list tools (BOM, suppliers, production orders, shipments)
  - Barrel dispatch in agent.tools for CRM + ERP
  - Q2 unit test scaffold with integration skip gate
affects: [02-02-calls, 02-03-kb, 02-04-crm-expansion]

tech-stack:
  added: []
  patterns:
    - "Barrel dispatch: run_tool routes to run_crm_tool or run_erp_tool"
    - "Pre-computed inventory fields: below_minimum, on_hand_qty, minimum_qty"
    - "Thin list tools: count + sample[:100] pass-through"

key-files:
  created:
    - backend/agent/tools/erp.py
    - backend/tests/test_erp_q2.py
    - backend/tests/conftest.py
  modified:
    - backend/agent/tools/__init__.py
    - backend/agent/loop.py
    - backend/agent/prompts.py

key-decisions:
  - "Inventory is standalone get_inventory with computed fields; other ERP endpoints use thin list wrappers (D-14)"
  - "Sample rows capped at 100 across all ERP tools (D-03)"
  - "verticale extraction deferred to plan 02-04; loop still defaults to crm"

patterns-established:
  - "ERP tool module mirrors CRM: get_tool_definitions + run_erp_tool returning (json, source)"
  - "TDD RED/GREEN: unit test mocks get_client before erp.py implementation"

requirements-completed: [ERP-01]

duration: 15min
completed: 2026-06-13
---

# Phase 2 Plan 01: ERP Inventory Vertical Slice Summary

**get_inventory with Python-computed below_minimum/on_hand_qty/minimum_qty, barrel dispatch for CRM+ERP, and Q2 unit tests passing**

## Performance

- **Duration:** 15 min
- **Started:** 2026-06-13T10:20:00Z
- **Completed:** 2026-06-13T10:36:57Z
- **Tasks:** 3
- **Files modified:** 6

## Accomplishments

- `get_inventory` returns pre-computed `below_minimum`, `on_hand_qty`, `minimum_qty` for PAS-PEN-500 (462 vs 2000 → below minimum)
- Thin ERP list tools for BOM, suppliers, production orders, shipments (count + sample capped at 100)
- Barrel `run_tool` in `agent.tools` aggregates CRM and ERP definitions; loop routes all tool calls through it
- SYSTEM_PROMPT extended with ERP routing hints for stock/below-minimum questions

## Task Commits

Each task was committed atomically:

1. **Task 1: Failing Q2 tests for ERP inventory tool** - `a7aae51` (test)
2. **Task 2: Implement get_inventory ERP tool** - `07cc330` (feat)
3. **Task 3: Wire ERP slice into barrel, loop, and prompts** - `6055049` (feat)

## Files Created/Modified

- `backend/agent/tools/erp.py` - get_inventory + thin list tools with pre-computed stock fields
- `backend/agent/tools/__init__.py` - Barrel dispatch for CRM + ERP tool definitions
- `backend/agent/loop.py` - Imports and calls unified `run_tool`
- `backend/agent/prompts.py` - ERP routing hints for get_inventory and list tools
- `backend/tests/conftest.py` - Pytest path setup for backend imports
- `backend/tests/test_erp_q2.py` - Unit test (mocked) + integration test (skipif no env)

## Decisions Made

- Inventory uses standalone `get_inventory` with computed fields; other ERP endpoints are thin pass-through wrappers (D-14)
- `verticale` remains hardcoded `crm` until plan 02-04 (acceptable per plan)
- Integration test skipped when `MOCK_API_TOKEN` or `LLM_API_KEY` unset

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- Pytest warns about unregistered `@pytest.mark.integration` — cosmetic only; does not affect test execution

## User Setup Required

None - no external service configuration required beyond existing `.env` for integration test.

## Next Phase Readiness

- Ready for 02-02 (Calls vertical slice) — barrel pattern established
- Q2 unit test GREEN; integration test ready when `.env` configured
- verticale=erp and full Q1-Q4 battery deferred to 02-04

## Self-Check: PASSED

- FOUND: backend/agent/tools/erp.py
- FOUND: backend/agent/tools/__init__.py
- FOUND: backend/tests/test_erp_q2.py
- FOUND: backend/tests/conftest.py
- FOUND: a7aae51, 07cc330, 6055049
- pytest: 1 passed, 1 skipped (integration)

---
*Phase: 02-all-4-verticali-kb*
*Completed: 2026-06-13*
