# Phase 2: All 4 Verticali + KB - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-13
**Phase:** 2-All 4 Verticali + KB
**Areas discussed:** Tool output shape, KB matching, Calls evidence, Tool routing & descriptions

---

## Tool Output Shape

| Option | Description | Selected |
|--------|-------------|----------|
| Pre-computed summaries | Tools return count/totals/flags computed in Python | ✓ |
| Raw API rows | Pass full API payloads for LLM interpretation | |
| Hybrid | Summary + sample rows | ✓ (implicit) |

**User's choice:** Pre-computed summaries with explicit answer fields; sample rows capped at **100**; JSON backend only (fluent English reserved for final `/ask` answer); optional short notes only if they help without token/time cost.

**Notes:** User's focus for the whole discussion was "anything impacting performance on the LLM's answer accuracy."

---

## KB Matching

| Option | Description | Selected |
|--------|-------------|----------|
| SKU exact + BM25 fallback | Exact SKU scan first, BM25 if no hit | ✓ |
| BM25 only | Lexical search over full docs | |
| Simple grep | Keyword/SKU scan without BM25 | |
| Whole document return | Return full matched doc text | ✓ |
| DOC-### source | Report document ID in sources | ✓ |

**User's choice:** SKU exact match → BM25 fallback; return whole document; source = `DOC-###`.

**Notes:** User delegated library choice ("you decide, best/most solid/reliable") — Claude discretion: add `rank-bm25`.

---

## Calls Evidence

| Option | Description | Selected |
|--------|-------------|----------|
| Two tools | list_calls + search_transcript | ✓ |
| Composite tool | Single tool chains both steps | |
| Pre-computed last call | list_calls identifies most recent call | ✓ |
| Hybrid search output | Complaint summary + matched segments | ✓ |
| 20 segment cap | Limit transcript segments returned | ✓ |

**User's choice:** Two tools; pre-computed last call; hybrid complaint summary + segments; cap at 20 segments.

---

## Tool Routing & Descriptions

| Option | Description | Selected |
|--------|-------------|----------|
| LLM declares verticale | Model sets crm/erp/calls/kb in final step | ✓ |
| Infer from tools | Code maps last/majority tool to verticale | |
| Mixed granularity | Separate complex tools, grouped simple lists | ✓ |
| Prompt + descriptions | Both SYSTEM_PROMPT and rich tool schemas | ✓ |
| 8 iterations | Bump MAX_ITERATIONS from 5 to 8 | ✓ |

**User's choice:** LLM declares verticale; mixed tool granularity; guidance in both prompt and tool descriptions; max 8 loop iterations.

---

## Claude's Discretion

- Add `rank-bm25` for KB retrieval reliability
- Exact tool split (standalone vs grouped) within mixed-granularity principle
- LLM verticale extraction mechanism (structured output vs metadata)
- Optional `note` fields on tool payloads when they help accuracy

## Deferred Ideas

None — scope stayed within Phase 2 boundary.
