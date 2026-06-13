---
status: human_needed
phase: 01-agent-skeleton-first-answer
verified: 2026-06-13
score: 9/10
---

# Phase 1 Verification

**Goal:** Environment running, agent loop answering one simple CRM question end-to-end.

## Must-Haves

| Check | Status | Evidence |
|-------|--------|----------|
| Service layer with env validation | PASS | `backend/services/config.py` |
| Mock API Bearer auth | PASS | `backend/services/api_client.py` |
| LLM client factory | PASS | `backend/services/llm_client.py` |
| POST /ask not 501 | PASS | `backend/main.py` calls `run_agent` |
| Agent tool-calling loop | PASS | `backend/agent/loop.py` |
| CRM opportunities tool | PASS | `backend/agent/tools/crm.py` |
| HTTP 200 on errors | PASS | try/except in main.py and loop.py |
| Sample Q1 E2E (4 opps, 740k EUR) | PENDING | Requires filled `backend/.env` |

## Human Verification

1. Fill `backend/.env` with LLM_API_KEY, MODEL (tool-calling), MOCK_API_TOKEN
2. `cd backend && uv run uvicorn main:app --reload --port 8000`
3. POST sample Q1 to `/ask` — expect verticale=crm, sources includes crm/opportunities, answer mentions 4 and 740,000 EUR

## Gaps

None in code structure. E2E smoke test blocked on empty env keys at execution time.
