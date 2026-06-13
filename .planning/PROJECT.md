# Al Dente Company Brain

## What This Is

A hackathon project for the Cursor-sponsored Company Brain challenge: an AI agent that answers questions about Al Dente S.r.l. (pasta manufacturer) by orchestrating CRM, ERP, call-log APIs and a local knowledge base. Delivers answers via a frozen `POST /ask` endpoint plus a working UI with a knowledge graph.

## Core Value

The agent loop must fetch the **right facts from the right sources** and answer honestly within 30 seconds — correctness and orchestration beat polish.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Agent loop with tool calling over 4 verticali (crm, erp, calls, kb)
- [ ] RAG over 35 KB documents in `backend/data/kb/`
- [ ] `POST /ask` frozen schema, public, HTTP 200 always, <30s
- [ ] Pagination-aware aggregation (check `pagination.total`, page through)
- [ ] Arithmetic in Python, not in LLM
- [ ] Trap handling: verify entities exist, honest "not available"
- [ ] Artifact generation (inline HTML + binary files via `artifact_url`)
- [ ] Working UI with knowledge graph (customers, suppliers, products, materials)
- [ ] Railway deploy with endpoint check passing

### Out of Scope

- External data sources — challenge rules forbid it
- Changing `/ask` schema — evaluator is locked
- Auth on `/ask` — must be public
- Streaming/async job patterns — evaluator reads one JSON response

## Context

- **Event**: Yellow Tech hackathon, June 13 2026, ~5 hours remaining
- **Company**: Al Dente S.r.l. — dry pasta to GDO, distributors, horeca
- **Data sources**: Mock APIs at `aldente.yellowtest.it` (metered per token) + 35 local KB markdown files
- **LLM**: Regolo.ai or Mistral (OpenAI-compatible, tool-calling required)
- **Evaluation**: L1 automated (~40 hidden questions), L2 human (UI/graph/artifacts), L3 pitch
- **Starter**: FastAPI backend with `/ask` returning 501, placeholder UI, artifact serving wired

## Constraints

- **Timeline**: ~5 hours to working deploy + self-test iteration
- **Latency**: 30s hard cap per question
- **Efficiency**: API calls metered server-side — targeted filtered calls win
- **Honesty**: Trap questions penalize hallucination heavily
- **Deploy**: Railway, European region, first deploy by hour ~2

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Vertical MVP phases | Hackathon time pressure — ship end-to-end slices fast | — Pending |
| Whole-document KB retrieval first | Docs are small and similar; chunking hurts | — Pending |
| Python aggregation helpers | LLMs sum wrong; pagination.total is the #1 failure mode | — Pending |
| Coarse GSD granularity | 5 hours → 4-5 focused phases | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

---
*Last updated: 2026-06-13 after initialization*
