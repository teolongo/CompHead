# Deferred Items - Phase 03 (correctness-layer)

Out-of-scope discoveries logged during execution. These are NOT fixed in the
current plan because they are pre-existing agent behaviors (shipped in plans
03-01/02/03) and fall outside the scope boundary of the 03-04 deploy-prep plan.

## Live integration battery failures (found during 03-04 Task 2)

Live run on 2026-06-13 with real `.env` keys (Mistral + Al Dente mock API),
full network reachable. Command:

```
uv run pytest tests/test_sample_questions.py::test_sample_question[q05..q12] -q
```

Result: **5 passed (Q5, Q6, Q7, Q8, Q12), 2 failed (Q10, Q11)** in ~103s. Not
rate-limit / not network errors — genuine answer-correctness gaps.

### Q10 (q10_erp_bom_supplier_stock) - FAIL

- **Expected:** answer contains `RAW-SEM-003`, supplier "Molino San Giorgio",
  and a below-minimum stock determination (per 03-03 SUMMARY claims).
- **Actual:** agent answered supplier "Molino San Giorgio" correctly but used
  raw-material SKU `PAS-SEM-MSG` (not `RAW-SEM-003`) and said the stock level
  "is not available in the sources, so it cannot be determined whether it is
  below minimum stock." `sources=['erp/...']`, `verticale=erp`.
- **Signal:** the deterministic `resolve_bom_supplier_stock` preflight from
  03-03 did not fire for the SKU-shaped wording of Q10; the LLM path resolved a
  different raw-material SKU and could not read stock. Investigate whether the
  preflight should trigger on SKU-only (no LOT) multi-hop questions, and why the
  BOM raw-material SKU differs (`PAS-SEM-MSG` vs `RAW-SEM-003`).

### Q11 (q11_calls_broken_pasta_count) - FAIL

- **Expected:** count of `9` "broken pasta" quality complaints across all 80 calls.
- **Actual:** agent answered `11`. `sources=['calls']`, `verticale=calls`.
- **Signal:** off-by count on the full-call-log aggregation. Could be
  over-counting (e.g. matching "broken" loosely, or counting non-quality
  mentions) or an LLM counting/paging issue. Needs a deterministic count helper
  or tighter defect matching to land exactly 9.

### Disposition

- Assertions were NOT weakened (no hallucinated/looser thresholds added).
- These belong to the Phase 3 correctness verifier / a follow-up fix plan, not
  the 03-04 deploy-prep checkpoint.
