# Requirements — Al Dente Company Brain

## v1 Requirements

### Agent & Orchestration

- [ ] **AGENT-01**: `POST /ask` accepts `{"question": str}` and returns frozen schema
- [ ] **AGENT-02**: Agent loop uses LLM tool calling to select and invoke tools
- [ ] **AGENT-03**: Agent sets `verticale` to dominant source (crm | erp | calls | kb)
- [ ] **AGENT-04**: Agent populates `sources` with endpoints/doc IDs actually used
- [ ] **AGENT-05**: Responses always HTTP 200 (including errors/abstentions)
- [ ] **AGENT-06**: Full response within 30 seconds

### API Tools (4 verticali)

- [ ] **CRM-01**: Search/list customers, opportunities, orders, invoices with filters
- [x] **ERP-01**: Query production, inventory, suppliers, BOM, shipments
- [x] **CALLS-01**: List calls; search transcripts surgically (not full download)
- [x] **KB-01**: Retrieve relevant KB documents by query

### Data Correctness

- [ ] **DATA-01**: Pagination-aware aggregation — use `pagination.total`, page through
- [ ] **DATA-02**: Arithmetic (sums, counts, group-bys) computed in Python
- [ ] **DATA-03**: Entity premise verification before answering (trap handling)
- [ ] **DATA-04**: Honest "not available" when data doesn't exist in sources
- [ ] **DATA-05**: Multi-hop chains (customer → order → lot → BOM → supplier)

### Artifacts

- [ ] **ART-01**: Inline HTML/markdown artifacts returned in `answer`
- [ ] **ART-02**: Binary artifacts (docx/pptx/pdf/xlsx) saved to `static/files/`
- [ ] **ART-03**: `artifact_url` uses absolute `PUBLIC_BASE_URL` path

### UI & Knowledge Graph

- [ ] **UI-01**: Working end-to-end UI — user asks, gets answer
- [ ] **UI-02**: Knowledge graph showing customers, suppliers, products, materials
- [ ] **UI-03**: Graph reflects real relationships from API data

### Deploy & Ops

- [ ] **OPS-01**: Railway deploy in EU region
- [ ] **OPS-02**: Platform endpoint check passes
- [ ] **OPS-03**: Self-test loop used to iterate on failures

## v2 (deferred)

- Hybrid BM25 + embeddings retrieval
- Response caching for repeated self-test questions
- Advanced artifact templates (polished docx/pptx)
- Query decomposition planner for complex multi-source questions

## Out of Scope

- External/web data — challenge rules
- `/ask` schema changes — evaluator locked
- Authentication on `/ask` — must be public
- Streaming responses — evaluator reads one JSON

## Traceability

| Requirement | Phase |
|-------------|-------|
| AGENT-01..06 | 1 |
| CRM-01, ERP-01, CALLS-01 | 2 |
| KB-01 | 2 |
| DATA-01..05 | 3 |
| ART-01..03 | 4 |
| UI-01..03 | 4 |
| OPS-01..03 | 4 |
