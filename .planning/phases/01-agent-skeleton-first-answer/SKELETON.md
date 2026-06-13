# Walking Skeleton — Al Dente Company Brain

**Phase:** 1
**Generated:** 2026-06-13

## Capability Proven End-to-End

A POST to `/ask` with a simple CRM question returns HTTP 200 JSON with a factual answer sourced from the mock API, correct `verticale` and `sources`.

Example: *"How many open opportunities does Primato Supermercati (CUST-0132) have, and what is their total value?"* → `4 open opportunities worth 740,000 EUR`.

## Architectural Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Framework | FastAPI (starter) | Frozen `/ask` contract already wired |
| Agent pattern | OpenAI SDK tool-calling loop | Challenge requires orchestration; Regolo/Mistral are OpenAI-compatible |
| HTTP client | httpx | Already in starter deps |
| LLM access | `OpenAI(api_key, base_url)` from env | Required by AGENTS.md |
| Directory layout | `backend/services/` + `backend/agent/` | Separates transport from orchestration |
| Phase 1 tools | CRM opportunities only | Smallest slice that proves loop + API auth |
| Error handling | HTTP 200 + honest answer | Evaluator penalizes 5xx; frozen contract |

## Stack Touched in Phase 1

- [x] Project scaffold (uv, FastAPI, existing starter)
- [ ] Routing — `POST /ask` returns real JSON (not 501)
- [ ] External API — authenticated call to mock CRM
- [ ] Agent — LLM tool-calling loop with one CRM tool
- [ ] Local run — `uv run uvicorn main:app --reload --port 8000`

## Out of Scope (Deferred to Phase 2+)

- ERP, calls, KB tools
- Pagination aggregation helper (Phase 3)
- RAG / KB retrieval
- Artifact generation
- UI / knowledge graph
- Railway deploy (Phase 3)

## Subsequent Slice Plan

- **Phase 2:** All 4 verticali + KB retrieval tools
- **Phase 3:** Pagination, traps, multi-hop + Railway deploy
- **Phase 4:** Artifacts, UI, knowledge graph, self-test polish
