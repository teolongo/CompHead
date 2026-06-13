# Phase 4: Artifacts + UI + Polish - Context

**Gathered:** 2026-06-13T13:29:00Z
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 4 delivers the judge-facing polish layer for Al Dente Company Brain: a complete, modern web interface around the existing `/ask` endpoint, an interactive knowledge graph that makes the company data and agent source usage legible, inline HTML deck generation for Q9-style prompts, at least one binary artifact type with absolute `artifact_url`, and self-test/submission readiness. The endpoint contract remains frozen; UI-only endpoints may be added if they do not change `/ask`.

</domain>

<decisions>
## Implementation Decisions

### Visual Direction
- **D-01:** The UI should feel clean, modern, polished, playful, and award-worthy while remaining a professional business tool.
- **D-02:** Use a minimalist foundation with bright, pasta-inspired accents and strong contrast: warm dark base, semolina/gold, tomato/orange, basil/green, and electric AI highlights where useful.
- **D-03:** Create a minimal but memorable logo merging pasta and AI. It should be effective at small sizes and usable as both header mark and favicon-style motif.
- **D-04:** Typography should feel sharp and distinctive. Avoid generic AI-dashboard aesthetics; use clear hierarchy, generous whitespace, consistent spacing, and accessible contrast.
- **D-05:** Include smooth hover transitions, scroll fade-ins, and soft entrance animations. Motion should feel premium and intentional, not noisy.

### Interface Scope
- **D-06:** The core surface is an AI chat for the company brain. It must be end-to-end functional: user submits a question to `POST /ask`, sees answer, sources, verticale, and any `artifact_url`.
- **D-07:** The UI should highlight fundamental backend capabilities: CRM, ERP, calls/transcripts, KB retrieval, deterministic correctness/trap handling, artifacts, and knowledge graph.
- **D-08:** Broken links are unacceptable. Any nav/action in the UI must either work or be represented as non-clickable UI copy.

### Knowledge Graph + Agent Path Highlighting
- **D-09:** Build an interactive knowledge graph fed by backend data showing customers, suppliers, products, and raw materials. It should reflect real relationships from API data where possible.
- **D-10:** For agent-path highlighting, use the latest `/ask` response `sources` and `verticale` to highlight relevant source categories and graph paths. Add a separate UI-only graph/trace endpoint if useful, but do not change the frozen `/ask` schema.
- **D-11:** Full per-tool instrumentation is optional and not required for Phase 4. If implemented, it must be exposed through a separate UI-only endpoint and must not affect evaluator behavior.

### Three.js, Lenis, and Motion
- **D-12:** Use Three.js for a subtle ambient hero element: a pasta/AI visual system, floating data strands, or neural/pasta motif. It should be visually captivating but not dominate the business tool.
- **D-13:** Do not implement the primary knowledge graph in Three.js unless it remains reliable. Prefer SVG/Canvas/CSS for graph interaction if that is faster and more stable.
- **D-14:** Use Lenis for buttery scrolling if it can be added safely without bloating or destabilizing the single static page. Native smooth scrolling is an acceptable fallback.
- **D-15:** On mobile and reduced-motion environments, reduce or disable heavy 3D/motion effects.

### Mobile and Responsiveness
- **D-16:** Optimize the showcase primarily for desktop judging, but mobile must run smoothly and remain usable.
- **D-17:** Mobile should be chat-first, with the graph accessible behind a clear button/toggle or collapsed panel.
- **D-18:** Ensure layout, contrast, touch targets, and scroll behavior are mobile-friendly.

### Artifacts
- **D-19:** Implement Q9-style 4-slide HTML deck generation inline in `answer`, using real CRM/call/order facts where possible.
- **D-20:** Implement PDF as the first binary artifact type. Save files under `backend/static/files/` and return an absolute `artifact_url` using `PUBLIC_BASE_URL`.
- **D-21:** XLSX or other binary artifact formats are nice-to-have only if time remains.

### Verification
- **D-22:** Check the UI with Chrome DevTools after implementation. Verify desktop and mobile responsiveness, no console errors, graph usability, chat flow, artifact links, and reduced-motion behavior.
- **D-23:** Keep backend response latency under the challenge limit. UI polish must not slow `/ask` or introduce auth/streaming/job patterns.

### Claude's Discretion
- Claude may choose the exact logo geometry, typeface pairing, layout composition, graph visual encoding, and animation timings as long as they satisfy the locked direction above.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Rules
- `AGENTS.md` — Frozen `/ask` contract, allowed data sources, latency, artifact rules, UI/knowledge graph requirement.
- `.planning/PROJECT.md` — Project purpose, active requirements, constraints, and evaluation context.
- `.planning/REQUIREMENTS.md` — Requirement IDs for ART-01..03, UI-01..03, OPS-03.
- `.planning/ROADMAP.md` — Phase 4 goal and success criteria.

### Existing Implementation
- `backend/main.py` — Serves `/`, `/files`, `/health`, and frozen `POST /ask`.
- `backend/static/index.html` — Current placeholder UI to replace.
- `backend/agent/loop.py` — Agent loop and sources tracking used for source/path highlighting.
- `backend/agent/tools/__init__.py` — Tool dispatch registry and verticali.
- `backend/agent/tools/crm.py` — CRM data available for UI/artifact facts.
- `backend/agent/tools/erp.py` — ERP/BOM/supplier/inventory data for graph and artifacts.
- `backend/agent/tools/calls.py` — Calls/transcript tools for complaints and graph/source display.
- `backend/agent/tools/kb.py` — KB retrieval and document sources.

### Deployment / Artifacts
- `backend/.env.example` — Environment variables, including `PUBLIC_BASE_URL`.
- `backend/static/files/.gitkeep` — Binary artifact output directory anchor.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `POST /ask` already returns `answer`, `sources`, `verticale`, and `artifact_url`; the UI can render these without backend schema changes.
- `/files` static mount already serves generated binary artifacts from `backend/static/files/`.
- Existing tool modules expose the source strings needed to map responses into graph/source highlights.

### Established Patterns
- Backend is FastAPI with a single static HTML frontend. A high-quality single-file `index.html` with embedded CSS/JS is acceptable and fast for the hackathon.
- No auth, no streaming, no jobs. The UI should call `/ask` once per user question and render the returned JSON.
- The only permitted data sources are mock APIs and local KB docs; graph data must come from those sources or deterministic summaries of them.

### Integration Points
- Replace `backend/static/index.html` with the complete UI.
- Add UI-only routes such as `/api/graph` or `/api/trace` if needed; do not alter `/ask`.
- Wire artifact preflight into `agent.loop.run_agent` before the LLM loop if deterministic artifact generation is used.
- Use `services/graph.py` or equivalent to produce graph nodes/edges from CRM/ERP/calls/KB-backed data.

</code_context>

<specifics>
## Specific Ideas

- The experience should feel like a professional Company Brain cockpit, not a generic chat app.
- Logo concept: pasta strand/noodle form merged with a neural node or AI spark, minimal enough for the header.
- Visual idea: ambient Three.js hero with pasta/noodle strands behaving like a neural network.
- Graph idea: latest answer highlights the relevant vertical/source path, helping judges see how the agent found the answer.
- Interaction idea: chat, source chips, verticale badge, graph, sample prompt cards, and artifact cards should all reinforce the backend's core capabilities.

</specifics>

<deferred>
## Deferred Ideas

- Full real-time streaming visualization of every tool call is deferred unless it can be implemented safely through UI-only tracing without touching `/ask`.
- XLSX artifacts are deferred unless PDF and HTML artifacts are complete and verified.

</deferred>

---

*Phase: 4-Artifacts + UI + Polish*
*Context gathered: 2026-06-13T13:29:00Z*
