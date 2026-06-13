---
phase: 01-agent-skeleton-first-answer
plan: 01-02
subsystem: api
tags: [openai, tool-calling, crm, fastapi]

requires:
  - phase: 01-01
    provides: MockApiClient and LLM client factories
provides:
  - CRM list_opportunities tool with Python-side aggregation
  - Tool-calling agent loop (max 5 iterations)
  - Working POST /ask endpoint (HTTP 200, frozen schema)
affects: [phase-2-verticali]

tech-stack:
  added: []
  patterns:
    - "backend/agent/ for orchestration, backend/agent/tools/ for LLM tools"
    - "HTTP 200 with honest error message on failures"

key-files:
  created:
    - backend/agent/__init__.py
    - backend/agent/prompts.py
    - backend/agent/loop.py
    - backend/agent/tools/__init__.py
    - backend/agent/tools/crm.py
  modified:
    - backend/main.py

key-decisions:
  - "Open opportunities = qualification + negotiation stages unless stage filter set"
  - "Summation of opportunity values done in Python, not by LLM"

patterns-established:
  - "run_agent() returns dict matching AskResponse schema"
  - "reasoning_content fallback when content is empty"

requirements-completed: [AGENT-01, AGENT-02, AGENT-03, AGENT-04, AGENT-05, AGENT-06]

duration: 20min
completed: 2026-06-13
---

# Plan 01-02 Summary

**Walking skeleton: POST /ask orchestrates LLM tool-calling with CRM opportunities tool**

## Performance

- **Duration:** 20 min
- **Tasks:** 3
- **Files modified:** 6

## Accomplishments

- list_opportunities tool with OpenAI function schema and Python count/total aggregation
- Agent loop with max 5 tool rounds, sources tracking, reasoning_content handling
- POST /ask wired to run_agent(); always returns HTTP 200

## Deviations from Plan

None - plan executed as written.

## User Setup Required

E2E smoke test blocked until `backend/.env` has real LLM_API_KEY, MODEL, and MOCK_API_TOKEN.

Verify with:
```bash
cd backend && uv run uvicorn main:app --reload --port 8000
curl -s -X POST http://localhost:8000/ask -H 'Content-Type: application/json' \
  -d '{"question":"How many open opportunities does CUST-0132 have and total value?"}'
```

Expected: 4 open opportunities, 740,000 EUR total, verticale=crm, sources includes crm/opportunities.

## Next Phase Readiness

Phase 2 can add ERP, calls, and KB tools following the same tool + loop pattern.

---
*Phase: 01-agent-skeleton-first-answer*
*Completed: 2026-06-13*
