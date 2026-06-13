---
phase: 03-correctness-layer
plan: 02
subsystem: agent
tags: [correctness, traps, premise-verification, abstention, tdd, pytest]

requires:
  - phase: 03-correctness-layer
    plan: 01
    provides: MockApiClient.get_all_pages for complete CRM premise searches
provides:
  - agent/correctness.py try_answer_correctness_preflight deterministic trap/premise hook
  - run_agent preflight short-circuit before the LLM tool-calling loop
  - Unsupported lot profit/cost metric abstention (Q7) with no invented numbers
  - Missing-customer order premise verification via /crm/customers (Q8)
affects: [phase-3-multihop, phase-4-artifacts-ui]

tech-stack:
  added: []
  patterns:
    - Deterministic preflight intercepts narrow, high-confidence traps before the LLM
    - Triggers are narrow (explicit lot id + metric keyword, or explicit order-for-name); ambiguous returns None
    - Premise checks verify entities against the live CRM before abstaining; CRM errors fall through to the LLM
    - Frozen /ask schema preserved (answer/sources/verticale/artifact_url=None), HTTP 200 on abstain

key-files:
  created:
    - backend/agent/correctness.py
    - backend/tests/test_phase3_traps.py
  modified:
    - backend/agent/loop.py
    - backend/agent/prompts.py
    - backend/tests/test_sample_questions.py

key-decisions:
  - "Lot profitability trap fires only when a LOT-####-#### id AND a cost/profit/margin keyword are both present"
  - "Missing-customer trap extracts the name from an explicit 'order ... for <Name>' premise, verifies via /crm/customers search with full pagination, and only abstains when zero rows match"
  - "Existing customers and unverifiable premises (no token / transient error) return None so the LLM loop handles them"
  - "Profit/margin abstention returns verticale=erp with empty sources (nothing queried); missing-customer returns verticale=crm with sources=[crm/customers]"

metrics:
  duration: 12min
  tasks: 3
  files: 5
  completed: 2026-06-13
---

# Phase 3 Plan 02: Trap & Premise Correctness Preflight Summary

**A deterministic `try_answer_correctness_preflight` that intercepts Q7/Q8-style traps before the LLM loop — abstaining honestly on unsupported lot profit/cost metrics and verifying missing-customer order premises against the CRM, all on the frozen `/ask` schema with HTTP 200.**

## Performance

- **Duration:** ~12 min
- **Tasks:** 3
- **Files modified:** 5 (2 created, 3 modified)

## Accomplishments

- `agent/correctness.py` adds `try_answer_correctness_preflight(question) -> dict | None` with two narrow branches:
  - **Unsupported lot metric (Q7):** when the question contains a `LOT-####-####` id *and* a profitability keyword (profit / margin / cost / COGS / markup), it returns a specific "cost and profit margin are not stored on production lots or anywhere in the sources" answer with `verticale="erp"`, empty `sources`, and no invented numbers.
  - **Missing-customer premise (Q8):** it extracts the customer name from an explicit "order(s) ... for/of/from/placed by `<Name>`" premise, searches `/crm/customers` with full pagination, and only when zero rows match returns `There is no customer named "<name>" in the CRM ...` with `verticale="crm"` and `sources=["crm/customers"]`. Existing customers and unverifiable premises return `None` so the normal LLM loop answers.
- `run_agent` now calls the preflight as its first step and returns immediately when non-`None`, short-circuiting the LLM loop for traps (faster, deterministic, latency-safe).
- `SYSTEM_PROMPT` gained explicit abstention rules aligning the LLM with the deterministic handling for hidden variants: verify named customers before order/status answers; never infer profit/cost/COGS/markup; prefer specific "not in the sources" over generic uncertainty.
- `test_phase3_traps.py` adds 8 offline unit tests (mocked CRM client) covering both traps, the existing-customer fall-through, ambiguous/blank no-ops, and `run_agent` wiring. Sample Q7/Q8 assertions were tightened (no `%` margin for Q7; a `crm` source for Q8).

## Task Commits

1. **Task 1: Failing trap preflight tests (RED)** — `eef8952` (test)
2. **Task 2: Deterministic trap/premise preflight + loop wiring (GREEN)** — `5a86fce` (feat)
3. **Task 3: Tighten prompt abstention rules (GREEN)** — `d027888` (feat)

## Verification

- `uv run pytest tests/test_phase3_traps.py -q` → 8 passed.
- `uv run pytest -m "not integration" -q` → 18 passed, 19 deselected.
- Live integration cases (`q07_erp_trap_profit_margin`, `q08_crm_trap_missing_customer`) and the Phase 2 `test_phase2_integration` battery require `MOCK_API_TOKEN`/`LLM_API_KEY` and outbound network; they were not exercised in this offline sandbox (they error on connection, not on logic).

## Deviations from Plan

### Auto-fixed Issues

None — plan executed as written.

### Notes

- The Task 2 `loop.py` commit also carried a small pre-existing, uncommitted hunk from a prior phase (LLM retry constants `LLM_MAX_RETRIES 3→5`, `LLM_RETRY_BASE_SECONDS 2.0→3.0`). It is benign and unrelated to this plan's logic; included only because it lives in the same file my task modifies.
- The plan listed `backend/tests/test_sample_questions.py` in Task 1; it needed only stricter Q7/Q8 assertions (it was already an untracked file from a prior phase and is now committed).

## Threat Surface

Threat model mitigations honoured:
- **T-03-04 (Tampering, parsing):** triggers use narrow regexes and exact unsupported-metric keywords; ambiguous questions (and bare `CUST-####` references) return `None`. Extracted customer names are cut at clause boundaries and length-capped before becoming the `search` query param.
- **T-03-05 (Repudiation, abstentions):** the missing-customer abstention includes `sources=["crm/customers"]` and names the verified-missing premise; the lot-metric abstention names the exact lot id.
- **T-03-06 / T-03-SC (accept):** prompt contains only challenge rules and no secrets; no package installs were performed.

`/ask` remains public, non-streaming, HTTP 200, and schema-compatible (`artifact_url=None` on all preflight answers).

## Self-Check: PASSED

- FOUND: backend/agent/correctness.py
- FOUND: backend/agent/loop.py
- FOUND: backend/agent/prompts.py
- FOUND: backend/tests/test_phase3_traps.py
- FOUND: backend/tests/test_sample_questions.py
- FOUND: eef8952
- FOUND: 5a86fce
- FOUND: d027888

---
*Phase: 03-correctness-layer*
*Completed: 2026-06-13*
