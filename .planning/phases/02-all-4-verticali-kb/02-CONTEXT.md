# Phase 2: All 4 Verticali + KB - Context

**Gathered:** 2026-06-13
**Status:** Ready for planning

<domain>
## Phase Boundary

Wire the remaining three API verticali (ERP, calls) and KB retrieval into the existing agent loop, expanding CRM beyond opportunities. Phase 2 succeeds when sample questions Q1–Q4 pass locally:

- Q1: CRM aggregate (opportunities — already in Phase 1)
- Q2: ERP inventory lookup (below minimum for a SKU)
- Q3: Calls — last call complaint + lot via transcript search
- Q4: KB — shelf life + allergens for a SKU

Out of scope for this phase: full pagination aggregation (Phase 3), trap handling (Phase 3), multi-hop chains (Phase 3), artifacts (Phase 4), UI/knowledge graph (Phase 4), Railway deploy (Phase 3).

</domain>

<decisions>
## Implementation Decisions

### Tool Output Shape (accuracy-first)
- **D-01:** Tools return **pre-computed summaries** wherever possible — the LLM must not sum, compare, or interpret raw rows (extends Phase 1 pattern).
- **D-02:** Include **explicit answer fields** in tool JSON (e.g. `below_minimum: true`, `on_hand_qty`, `minimum_qty`) rather than leaving comparison to the LLM.
- **D-03:** When returning sample rows alongside computed fields, **cap at 100 rows** to balance evidence vs token cost.
- **D-04:** Tool results stay **structured JSON** in the backend; no mandatory natural-language summaries in tool payloads. Add a short note field only when it materially improves reliability without significant token/time cost. Final `/ask` answer must be fluent English.

### KB Retrieval
- **D-05:** Two-stage matching: **SKU exact match first** (scan doc content for SKU like `PAS-SPA-500`), then **BM25 fallback** over whole documents if no exact hit.
- **D-06:** Return the **full matched document text** to the LLM — no aggressive chunking (per PROJECT.md / AGENTS.md guidance for these 35 small spec sheets).
- **D-07:** Report source as **`DOC-###`** document ID (e.g. `DOC-001`), not file paths.
- **D-08:** **Add `rank-bm25`** dependency — user delegated library choice to Claude for best reliability within Phase 2 time budget.

### Calls Workflow
- **D-09:** **Two separate tools**: `list_calls` (with filters) and `search_transcript` (with `?search=`).
- **D-10:** `list_calls` **pre-computes the most recent call** when the question implies "last call" (sort by date desc, surface `call_id` + metadata).
- **D-11:** `search_transcript` returns a **hybrid payload**: pre-extracted complaint summary fields (complaint type, lot id if found) **plus** matched transcript segments.
- **D-12:** Cap transcript segments at **20** per search — never download full transcripts.

### Tool Routing & Agent Loop
- **D-13:** **LLM declares `verticale`** in the final answer step (crm | erp | calls | kb) — replace hardcoded `"crm"` in loop.py. Planner must define a reliable extraction mechanism (structured final message or dedicated metadata field).
- **D-14:** **Mixed tool granularity**: separate tools for complex/multi-step endpoints (calls transcript search, inventory with computed fields, KB search); grouped or simpler tools for straightforward list endpoints (customers, orders, invoices, suppliers).
- **D-15:** Routing guidance in **both** expanded `SYSTEM_PROMPT` (per-verticale hints) **and** rich tool descriptions (filters, ID formats, when to use each tool).
- **D-16:** Increase `MAX_ITERATIONS` from **5 to 8** to accommodate two-step calls workflows (list_calls → search_transcript) within the 30s ceiling.

### Claude's Discretion
- Exact tool naming and which CRM/ERP endpoints get standalone vs grouped tools (within D-14 mixed-granularity principle).
- Whether to add a short `note` field on specific tool payloads where it helps without token bloat (D-04).
- BM25 index build strategy (startup vs lazy) and SKU-scan implementation details.
- Mechanism for LLM verticale declaration — structured output, JSON block in final message, or auxiliary tool call — as long as D-13 is satisfied reliably.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project spec & challenge rules
- `AGENTS.md` — frozen `/ask` schema, 30s latency, honesty rules, whole-doc KB guidance, tool-calling requirements
- `API.md` — all mock API endpoints, filters, pagination envelope, transcript `?search=` pattern
- `SAMPLE_QUESTIONS.md` — Q1–Q4 reference answers (Phase 2 success target)

### Requirements & roadmap
- `.planning/REQUIREMENTS.md` — CRM-01, ERP-01, CALLS-01, KB-01
- `.planning/ROADMAP.md` — Phase 2 success criteria and scope boundary
- `.planning/PROJECT.md` — whole-document KB retrieval first, Python aggregation principle

### Phase 1 patterns (extend, do not reinvent)
- `.planning/phases/01-agent-skeleton-first-answer/01-02-SUMMARY.md` — agent loop, CRM tool pattern, sources tracking
- `.planning/phases/01-agent-skeleton-first-answer/SKELETON.md` — architectural decisions (services/ + agent/ layout)

### Implementation starting points
- `backend/agent/loop.py` — agent loop to extend (verticale, tool dispatch, iteration limit)
- `backend/agent/tools/crm.py` — reference tool pattern (pre-computed fields, source strings)
- `backend/services/api_client.py` — authenticated mock API client
- `backend/data/kb/` — 35 KB markdown documents (retrieval target)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `MockApiClient.get()` — Bearer-authenticated GET with error handling; use for all new API tools
- `list_opportunities` in `backend/agent/tools/crm.py` — template for pre-computed JSON tool results + `crm/opportunities` source string
- `run_agent()` in `backend/agent/loop.py` — tool-calling loop with sources accumulation, `reasoning_content` fallback, HTTP-200 error path
- `get_settings()` / `get_llm_client()` — env-validated clients ready for extended tool set

### Established Patterns
- One module per verticale under `backend/agent/tools/` (crm.py exists; add erp.py, calls.py, kb.py)
- Python-side aggregation and explicit computed fields before returning to LLM
- `sources` list deduplicated endpoint/doc IDs actually used
- `OPEN_STAGES` convention for CRM "open" opportunities (qualification + negotiation)

### Integration Points
- `loop.py` `_execute_tool()` — currently CRM-only; must dispatch to all verticali executors
- `get_tool_definitions()` — must merge tool schemas from crm + erp + calls + kb modules
- `SYSTEM_PROMPT` in `backend/agent/prompts.py` — expand with per-verticale routing guidance
- `pyproject.toml` — uncomment/add `rank-bm25` for KB retrieval

</code_context>

<specifics>
## Specific Ideas

- User priority: **anything impacting LLM answer accuracy** — pre-computation, explicit fields, and reliable doc/call matching over token-minimal raw dumps.
- Q4 target: `PAS-SPA-500` → shelf life 36 months, allergens gluten (+ may contain soy, mustard) from `DOC-001`.
- Q3 target: NordSpesa `CUST-0137` last call → broken pasta complaint, lot `LOT-2026-0658`, call `CALL-58020`.
- Q2 target: `PAS-PEN-500` below minimum — on-hand 462 vs minimum 2000.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope. Pagination aggregation, traps, multi-hop, artifacts, and UI remain in Phases 3–4 per roadmap.

</deferred>

---

*Phase: 2-All 4 Verticali + KB*
*Context gathered: 2026-06-13*
