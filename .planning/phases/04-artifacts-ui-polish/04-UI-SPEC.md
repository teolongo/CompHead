# Phase 4 UI Design Contract

**Phase:** 04-artifacts-ui-polish  
**Status:** Ready for implementation  
**Source:** 04-CONTEXT.md (discuss-phase decisions D-01..D-23)

## Visual Identity

| Token | Value | Usage |
|-------|-------|-------|
| `--bg-base` | `#14120B` | Page background |
| `--bg-elevated` | `#1c1a12` | Cards, panels |
| `--border` | `#2e2b20` | Dividers |
| `--text-primary` | `#ece8dd` | Body text |
| `--text-muted` | `#9b9684` | Secondary copy |
| `--accent-tomato` | `#F54E00` | Primary CTA, verticale badges |
| `--accent-gold` | `#E8B84A` | Highlights, graph nodes |
| `--accent-basil` | `#4ADE80` | Success, KB source chips |
| `--accent-ai` | `#7DD3FC` | AI spark, graph active path |

**Typography:** Distinct pairing — display: `"DM Sans"` or `"Outfit"`; mono labels: `"IBM Plex Mono"`. Load via Google Fonts CDN in `index.html`.

**Logo:** Minimal SVG — curved pasta strand terminating in a neural node/spark. Header mark + inline favicon data-URI.

## Layout (Desktop)

```
┌─────────────────────────────────────────────────────────────┐
│ [Logo] Al Dente Company Brain          [Graph toggle]       │
├──────────────────────────┬──────────────────────────────────┤
│  Three.js hero (240px)   │  Knowledge graph panel (SVG)     │
│  ambient pasta/AI strands│  force-directed or layered DAG   │
├──────────────────────────┴──────────────────────────────────┤
│  Chat thread (scroll)     │  Sample prompts sidebar (md+)  │
│  Input + Ask button       │  Capability chips (CRM/ERP/…)  │
└─────────────────────────────────────────────────────────────┘
```

## Layout (Mobile ≤768px)

- Chat-first: hero height ≤120px or hidden under reduced-motion
- Graph behind **"Knowledge graph"** toggle button (full-width drawer/modal)
- Touch targets ≥44px; input sticky bottom

## Components

### Chat (`UI-01`)
- Single `POST /ask` per submit — no streaming, no auth headers
- Render: answer (HTML if starts with `<!doctype` or `<html`, else markdown-ish pre-wrap)
- Source chips from `sources[]`; verticale badge (crm/erp/calls/kb color-coded)
- Artifact card when `artifact_url` set — opens in new tab, absolute URL
- Loading state ≤30s timeout message; error from JSON still HTTP 200

### Knowledge Graph (`UI-02`, `UI-03`)
- Fetch `GET /api/graph` on load; cache client-side
- Node kinds: customer (circle), product (rounded rect), supplier (diamond), material (hex)
- Edge labels on hover: uses, supplies
- **Source highlight:** after each `/ask`, map `sources` + `verticale` to node/edge classes:
  - `crm/*` → customer nodes + CRM edges
  - `erp/*` → product/material/supplier subgraph
  - `calls` → customer nodes linked to complaint calls (if customer id in answer)
  - `DOC-*` → KB document pseudo-node or legend pulse
- Implementation: **SVG + vanilla JS** (or lightweight d3-force CDN). Not Three.js.

### Three.js Hero (`D-12`, `D-15`)
- Subtle floating torus-knot or tube curves (pasta strands) with low poly count
- `prefers-reduced-motion: reduce` → static frame or CSS gradient fallback
- Mobile: disable or replace with static SVG

### Motion (`D-05`, `D-14`)
- Lenis optional via CDN; fallback `scroll-behavior: smooth`
- Entrance: `opacity` + `translateY(8px)` on cards, 300ms ease
- Hover transitions on buttons/chips: 150ms

## Interaction States

| State | Behavior |
|-------|----------|
| Idle | Sample prompt cards clickable |
| Loading | Disable submit, spinner on button |
| Answer | Scroll to latest message; trigger graph highlight |
| Artifact | Show download card with external link icon |
| Graph error | Inline message "Graph unavailable" — chat still works |

## Accessibility

- Contrast ≥4.5:1 on text
- Focus rings on interactive elements
- `aria-live="polite"` on answer region
- Reduced motion respected globally

## Verification Checklist (`D-22`)

- [ ] Desktop 1280px: chat E2E, graph renders, no console errors
- [ ] Mobile 390px: chat usable, graph toggle works
- [ ] Q9 sample prompt returns inline HTML in answer panel
- [ ] PDF question returns working `artifact_url` on deployed host
- [ ] Source highlight visible after CRM and ERP questions
- [ ] `prefers-reduced-motion` disables Lenis/Three.js animation

## Out of Scope

- Per-tool real-time trace stream (D-11 deferred)
- XLSX/docx/pptx artifacts (D-21 deferred)
- `/ask` schema changes (frozen)
