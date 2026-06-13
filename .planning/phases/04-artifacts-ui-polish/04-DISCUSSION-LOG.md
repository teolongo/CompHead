# Phase 4: Artifacts + UI + Polish - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-13T13:29:00Z
**Phase:** 4-Artifacts + UI + Polish
**Areas discussed:** Knowledge graph and agent paths, Three.js/motion, mobile strategy, binary artifact format

---

## Initial User Brief

The user requested a clean, modern, award-winning complete interface for the Company Brain. Required direction:

- AI chat as a core feature.
- Include the knowledge graph.
- Use Three.js for a visually captivating but minimalist professional experience.
- Use Lenis for buttery scrolling if it does not overcomplicate the implementation.
- Consistent spacing, strong hierarchy, hover transitions, scroll fade-ins, soft entrance animations.
- Highlight fundamental backend features.
- Explore interactive graph highlighting based on how the agent works and which tools it uses.
- Check with Chrome DevTools and make it mobile-friendly.
- Create a playful, polished bright-color logo merging pasta and AI.
- Good typography, contrast, accessibility, and no broken links.

---

## Gray Area Selection

| Option | Description | Selected |
|--------|-------------|----------|
| All of these | Discuss graph trace, visual/motion, mobile/performance, and artifacts | ✓ |
| Knowledge graph + highlighted agent/tool paths | Decide how graph highlighting maps to agent behavior | |
| Visual system, 3D/Three.js intensity, and motion rules | Decide how bold and expensive the visual layer should be | |
| Mobile experience and performance/accessibility guardrails | Decide mobile priority and fallbacks | |
| Artifact presentation: HTML deck + PDF/XLSX downloads | Decide artifact type and presentation emphasis | |

**User's choice:** All of these.
**Notes:** User wanted the full Phase 4 design surface captured before planning.

---

## Knowledge Graph + Highlighted Paths

| Option | Description | Selected |
|--------|-------------|----------|
| Sources-path highlighting | Highlight paths from latest `/ask` response sources + graph nodes, with UI-only trace panel when available | ✓ |
| Full tool trace | Add full per-tool instrumentation for every call and expose a trace endpoint | |
| Static graph | Keep graph interactive but only highlight source categories | |

**User's choice:** Sources-path highlighting.
**Notes:** This preserves the frozen `/ask` schema and keeps Phase 4 feasible while still showing how the agent uses backend sources.

---

## Three.js and Motion Intensity

| Option | Description | Selected |
|--------|-------------|----------|
| Ambient hero | Subtle ambient pasta/AI hero plus CSS graph/UI polish, static fallback on mobile | ✓ |
| Graph in Three.js | Build knowledge graph itself in Three.js | |
| No Three.js | SVG/CSS only | |

**User's choice:** Ambient hero.
**Notes:** Three.js should be captivating but not compromise reliability or professional minimalism.

---

## Mobile Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Full mobile parity | Full feature parity with simplified graph controls and reduced motion | |
| Chat-first mobile | Chat-first mobile, graph collapsed behind a button | ✓ |
| Desktop showcase | Optimize primarily for desktop judging | ✓ (with caveat) |

**User's choice:** "Optimize for desktop, but make sure mobile runs smoothly. Focus it more on chat and graph behind button."
**Notes:** Desktop is the judging showcase; mobile must remain smooth, accessible, and functional.

---

## Binary Artifact Format

| Option | Description | Selected |
|--------|-------------|----------|
| PDF | Easiest to verify and share | ✓ |
| XLSX | Better for tabular data | |
| Both | Try PDF plus XLSX if time allows | |

**User's choice:** PDF.
**Notes:** PDF is the first binary artifact target. XLSX remains nice-to-have only after PDF and HTML deck are complete.

---

## Claude's Discretion

- Exact visual composition, logo geometry, type pairing, graph visual encoding, and animation timing.
- Whether Lenis is loaded from CDN or replaced by native smooth scrolling fallback.
- Whether graph rendering uses SVG, Canvas, or DOM nodes, as long as interaction and responsiveness are solid.

## Deferred Ideas

- Full real-time tool-call tracing if it requires risky instrumentation or `/ask` schema changes.
- XLSX artifacts unless time remains after PDF and HTML artifact support.
