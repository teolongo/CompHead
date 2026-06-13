---
phase: 03-correctness-layer
plan: 03
subsystem: agent
tags: [multi-hop, chains, erp, bom, supplier, return-policy, price-authority, tdd, pytest]

requires:
  - phase: 03-correctness-layer
    plan: 02
    provides: try_answer_correctness_preflight deterministic hook + run_agent short-circuit
provides:
  - ERP resolve_bom_supplier_stock tool (lot -> finished SKU -> BOM -> supplier -> raw-material stock)
  - Return-policy preflight chain (last call complaint + KB returns policy DOC-011)
  - Price-authority preflight chain (official KB price list DOC-015 wins over a call figure)
affects: [phase-4-artifacts-ui]

tech-stack:
  added: []
  patterns:
    - LOT-shaped questions resolve lot->finished SKU via production orders before BOM traversal
    - Supplier resolved from BOM/inventory fields or targeted /erp/suppliers (category-filtered), never inferred
    - Return-policy chain uses targeted ?search= per covered defect, no full transcript download
    - Official KB document (price list) is authoritative over call transcript figures
    - Multi-hop deterministic answers returned by preflight before the LLM client is created

key-files:
  created: []
  modified:
    - backend/agent/tools/erp.py
    - backend/agent/correctness.py
    - backend/agent/prompts.py
    - backend/tests/test_phase3_multihop.py

key-decisions:
  - "resolve_bom_supplier_stock accepts sku OR lot_id (>=1 required); lot_id is resolved to the finished SKU via /erp/production-orders before BOM/supplier/inventory lookup"
  - "Supplier name is read from explicit supplier fields on BOM/inventory rows or a category-filtered /erp/suppliers lookup; a bare 'name' on a material/BOM row is never treated as a supplier"
  - "Return-policy preflight fires only when return + qualify/policy + complaint/call cues all match, a customer resolves, and a covered defect is found in the transcript; otherwise defers to the LLM"
  - "Price-authority preflight fires on SKU + price + official/price-list/authoritative cue, pulls DOC-015 via KB search, extracts the list price from the price table, verticale=kb"

metrics:
  duration: 18min
  tasks: 3
  files: 4
  completed: 2026-06-13
---

# Phase 3 Plan 03: Multi-Hop Correctness Chains Summary

**Deterministic multi-source chains for the three multi-hop sample shapes: an ERP `resolve_bom_supplier_stock` tool that resolves a `LOT-...` id to its finished SKU then traverses BOM -> raw material -> supplier -> stock (Q10/DATA-05), a return-policy preflight that combines the last complaint call with the KB returns policy (Q5), and a price-authority preflight where the official KB price list outranks a conflicting call figure (Q12).**

## Performance

- **Duration:** ~18 min
- **Tasks:** 3
- **Files modified:** 4 (0 created, 4 modified — the test file was created in Task 1's commit)

## Accomplishments

- **ERP lot-to-stock chain (`resolve_bom_supplier_stock`):** one tool that accepts `sku` or `lot_id` (at least one required) plus optional `material_category`. When given a `lot_id` it pages `/erp/production-orders` and matches the lot across common lot fields to recover the finished SKU *before* any BOM work, then fetches `/erp/bom?sku=...`, selects the right component row (category match / SKU-prefix / name), resolves the supplier from BOM or inventory fields or a category-filtered `/erp/suppliers` lookup, and reads `/erp/inventory?search=<raw>&type=raw_material` for the pre-computed `below_minimum`/`on_hand_qty`/`minimum_qty`. Returns all linked facts (`lot_id`, `finished_sku`, `raw_material_sku`, `raw_material_name`, `supplier_id`, `supplier_name`, stock comparison). Auto-registers via the existing `get_tool_definitions()` aggregation.
- **Return-policy preflight (Q5):** narrowly triggered (return + qualify/policy + complaint/call), it resolves the customer (CUST id or capitalized name before "call" verified against `/crm/customers`), finds the latest call, runs targeted `?search=` transcript queries for each covered defect (broken/bloated/foreign body/mislabeling) extracting the defect and lot, then pulls the KB returns policy (DOC-011) and answers with the policy's covered-defect, evidence, window, outcome (replacement/credit note) and lot blocking. Defers to the LLM when any premise is missing.
- **Price-authority preflight (Q12):** on a SKU + price + official/authoritative/price-list cue, it pulls the official 2026 wholesale price list (DOC-015) via KB search, extracts the SKU's list price from the price table, and states the official document is authoritative over any conflicting call figure (`verticale=kb`, source `DOC-015`).
- **Prompt updates:** the system prompt now steers the LLM to `resolve_bom_supplier_stock` for BOM/supplier/stock chains (pass `lot_id` for `LOT-...` ids, do not guess the SKU) and to treat official KB documents (price list / policy) as authoritative over phone calls.

## Task Commits

1. **Task 1: Failing multi-hop chain tests (RED)** — `6223b21` (test)
2. **Task 2: ERP lot-to-BOM supplier stock chain (GREEN)** — `3db4dd4` (feat)
3. **Task 3: Return-policy + price-authority preflight chains + prompt (GREEN)** — `23cfefe` (feat)

## Verification

- `uv run pytest tests/test_phase3_multihop.py tests/test_phase3_traps.py -q -m "not integration"` → 14 passed.
- `uv run pytest -m "not integration" -q` → 24 passed, 19 deselected.
- KB chains were exercised against the real local documents: DOC-011 (returns policy) and DOC-015 (price list, list price 8.07 for PAS-FUS-500) are resolved offline.
- Live integration cases (`q05_calls_kb_return_policy`, `q10_erp_bom_supplier_stock`, `q12_kb_price_authority`) and `test_erp_q2.py::test_q2_agent_integration` require `MOCK_API_TOKEN`/`LLM_API_KEY` and outbound network; in this sandbox they error on connection, not on logic.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Supplier name misread from a material row**
- **Found during:** Task 2 verification
- **Issue:** The first supplier-resolution pass treated a bare `name` field on the matched inventory/BOM row as the supplier name, so `resolve_bom_supplier_stock` returned the raw-material name ("Durum semolina - premium") instead of the supplier.
- **Fix:** Split supplier-name field lists — BOM/inventory rows use strict supplier-only fields (`supplier_name`/`supplier`/`vendor_name`/`vendor`), while only `/erp/suppliers` rows allow a bare `name`.
- **Files modified:** backend/agent/tools/erp.py
- **Commit:** 3db4dd4

### Notes

- `backend/agent/loop.py` was listed in the plan's file set but needed no change: `run_agent` already calls `try_answer_correctness_preflight` as its first step and returns before constructing the LLM client, so the two new preflight branches are short-circuited automatically (latency win for these shapes).
- `backend/tests/test_sample_questions.py` was also listed but its existing Q5/Q10/Q12 assertions are already correct and strict; left unchanged.

## Threat Surface

Threat model mitigations honoured:
- **T-03-07 (Tampering, answer composition):** tests assert exact linked facts and source IDs (RAW-SEM-003, Molino San Giorgio, LOT-2026-0658, DOC-011, 8.07, DOC-015); official KB price list wins price conflicts.
- **T-03-08 (DoS, return-policy call chain):** filtered list calls plus targeted transcript `?search=` per covered defect; never iterates full transcripts.
- **T-03-09 (Spoofing, supplier/material resolution):** supplier resolved from BOM/API fields or a targeted category-filtered supplier lookup, never from model inference; the strict-field fix removed a material-name spoofing path.
- **T-03-SC (accept):** no package installs.

`/ask` remains public, non-streaming, HTTP 200, and schema-compatible (`artifact_url=None` on all preflight answers).

## Self-Check: PASSED

- FOUND: backend/agent/tools/erp.py
- FOUND: backend/agent/correctness.py
- FOUND: backend/agent/prompts.py
- FOUND: backend/tests/test_phase3_multihop.py
- FOUND: 6223b21
- FOUND: 3db4dd4
- FOUND: 23cfefe

---
*Phase: 03-correctness-layer*
*Completed: 2026-06-13*
