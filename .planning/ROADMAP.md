# Roadmap — Al Dente Company Brain

**5-hour hackathon plan** | 4 phases | Vertical MVP slices

## Phases

### Phase 1: Agent Skeleton + First Answer
**Goal:** Environment running, agent loop answering one simple CRM question end-to-end.
**Mode:** mvp
**Success Criteria:**
1. `uv sync`, `.env` configured, backend runs locally
2. `POST /ask` returns valid JSON (not 501) for a sample CRM question
3. Agent calls mock API with auth token and returns correct answer
4. `verticale` and `sources` populated correctly

**Requirements:** AGENT-01..06

---

### Phase 2: All 4 Verticali + KB
**Goal:** Agent handles crm, erp, calls, and kb questions with proper tools.
**Mode:** mvp
**Plans:** 4 plans
**Success Criteria:**
1. CRM tools: customers, opportunities, orders, invoices
2. ERP tools: inventory, production, BOM, suppliers, shipments
3. Calls tool: transcript search with `?search=` (not full download)
4. KB retrieval over `data/kb/` (whole-doc retrieval acceptable)
5. Sample questions 1-4 pass locally

**Requirements:** CRM-01, ERP-01, CALLS-01, KB-01

Plans:
- [ ] 02-01-PLAN.md — ERP vertical slice: get_inventory + barrel foundation (Q2)
- [ ] 02-02-PLAN.md — Calls vertical slice: list_calls + search_transcript (Q3)
- [ ] 02-03-PLAN.md — KB vertical slice: SKU scan + BM25 retrieval (Q4)
- [ ] 02-04-PLAN.md — CRM expansion + verticale extraction + Q1-Q4 battery

---

### Phase 3: Correctness Layer
**Goal:** Fix the failure modes that kill L1 scores — pagination, traps, multi-hop.
**Mode:** mvp
**Success Criteria:**
1. Aggregation helper pages through all results using `pagination.total`
2. Trap questions return honest "not available" / "customer not found"
3. Multi-hop chains work (e.g. lot → SKU → BOM → supplier → stock)
4. Sample questions 5-8, 10-12 pass locally
5. **First Railway deploy** + endpoint check passes

**Requirements:** DATA-01..05, OPS-01..02

---

### Phase 4: Artifacts + UI + Polish
**Goal:** Ship artifacts, knowledge graph UI, self-test iteration, submission ready.
**Mode:** mvp
**Success Criteria:**
1. HTML deck generation inline in `answer` (sample Q9)
2. At least one binary artifact type working (pdf or xlsx)
3. UI with chat + knowledge graph visualization
4. Self-test run on platform, iterate on top failures
5. Submission: URL + repo + description

**Requirements:** ART-01..03, UI-01..03, OPS-03

---

## Coverage

| Phase | Requirements | Est. Time |
|-------|-------------|-----------|
| 1 | AGENT-01..06 | 60 min |
| 2 | CRM-01, ERP-01, CALLS-01, KB-01 | 75 min |
| 3 | DATA-01..05, OPS-01..02 | 75 min |
| 4 | ART-01..03, UI-01..03, OPS-03 | 90 min |

**Total:** ~5 hours

## Build Order Rationale

1. **Agent skeleton first** — proves the loop works before adding complexity
2. **Tools second** — each verticale is independent, can wire in parallel
3. **Correctness third** — pagination/traps are the #1 L1 killers; deploy mid-phase
4. **UI/artifacts last** — L2 points but L1 automated score matters more for advancing
