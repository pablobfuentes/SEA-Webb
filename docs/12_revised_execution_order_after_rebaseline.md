# Revised execution order — after product rebaseline (chat-first)

**Status:** Planning — sequencing only.  
**Date:** 2026-04-18  
**Depends on:** `docs/11_product_rebaseline_local_ai_chat_first.md`  
**Does not replace:** Block 3 freeze or Block 2/3 code validity; it **reorders forward work** toward the corrected primary product.

**Update (2026-04-18):** **Governed knowledge** is now **mandatory** in the roadmap. For **authoritative phased execution** (G0–G4 governance track + U1–U6 product surfaces), use **`docs/14_detailed_revised_execution_order_with_governed_knowledge.md`**. This file remains the **historical** R1–R6 sketch; doc 14 **supersedes** linear R2→R3 ordering where it conflicts with governance-first priorities.

---

## Principles for sequencing

1. **Evidence and orchestration before tree polish** — users must get **grounded Q&A** before we invest in **exploration UI** depth.  
2. **Reuse Block 2/3 services** — new UI calls existing retrieval, project, tree, and deterministic APIs; **no duplicate domain**.  
3. **Workbench stays thin** — existing Block 4A routes remain a **secondary** surface until explicitly integrated.  
4. **Iterative vertical slices** — each stage delivers a **demoable** increment (local-only).

---

## Recommended phases (high level)

### Phase R0 — Documentation transition (complete)

- Rebaseline docs (`docs/11_*`, `docs/12_*`), changelog, status trackers.  
- **No code** required for R0.

### Phase R1 — Orchestration + retrieval contract (complete)

- **Implemented:** `LocalAssistOrchestrator` + `local_assist_contract` models; tests `tests/test_local_assist_r1.py`; tracker `docs/implementation/PHASE_R1_STATUS.md`.  
- **Not done here:** chat UI, LLM runtime, evidence panel (R2).

### Phase R1 — Orchestration + retrieval UI contract

**Goal:** Define and stub (or minimally implement) the **local AI orchestration** boundary: request → approved corpus only → structured response slots for **citations**, **assumptions**, **deterministic hooks**, **refusal**.  
**Uses:** `DocumentRetrievalService`, project active code context, existing chunk models.  
**Out:** No requirement for full LLM integration on day one — **interfaces + fake/structured pipeline** acceptable if citations are wired honestly.

### Phase R2 — Evidence panel (mandatory UX)

**Goal:** UI panel that renders **expandable** citations with **exact excerpts** and **links to local source** (see doc 11 §F).  
**Depends on:** Stable citation payload from R1/R2 retrieval path.  
**Out:** Chat can be minimal if evidence panel works end-to-end on **retrieval-only** answers (proves gate before LLM eloquence).

### Phase R3 — Chat-first shell (primary surface)

**Goal:** Replace “tree page as home” with **conversation + evidence panel** as default project view.  
**Uses:** Same backend; **new** routes/templates or a **single** primary layout.  
**Out:** User can ask questions, see answers **only** with citation UI populated where claims are made (or explicit gaps).

### Phase R4 — Formula / logic / assumptions / checks panel

**Goal:** Dedicated audit strip: list assumptions, trace to deterministic **Calculation** / **Check** records when present, label M5 preliminary vs authoritative retrieval.  
**Uses:** Block 3 `TreeStore` artifacts, existing disclaimers.  
**Out:** No mixing of “LLM math” with deterministic output without labels.

### Phase R5 — Canvas / technical drawing area

**Goal:** Minimal surface for sketches, formula annotation, simple diagrams — **explanatory**, not BIM.  
**Out:** Integrates with chat/case context; **not** a full graph editor for the tree.

### Phase R6 — Secondary tree & workbench integration

**Goal:** Expose existing **simple-span workflow / branches / M5 / M6 / revision** from **linked** or **sidebar** “exploration” entry — **not** the default workflow.  
**Uses:** Current `structural_tree_app.workbench` routes and templates **as-is** or lightly wrapped.  
**Out:** Traceability story preserved without centering product on tree navigation.

### Phase R7 — Reporting & hardening (later)

**Goal:** Export, broader acceptance tests, polish — **after** R3–R6 prove the primary loop.

---

## What happens to Block 4A M7

| Item | Decision |
|------|----------|
| **4A-M7** (E2E workbench / acceptance hardening) | **Demoted** — do **not** treat as the next strategic milestone. Optional **small** fixes if blocking developers; no **product** investment until R3+ direction is underway. |
| **Existing M1–M6 workbench** | **Keep** — serves Phase R6 and ongoing Block 3 validation. |

---

## Mapping: old “next” vs new “next”

| Before rebaseline | After rebaseline |
|-------------------|------------------|
| Next: 4A-M7 workbench polish | Next: **R1–R3** (orchestration contract, evidence UI, chat shell) |
| Tree/workflow page as main validation story | **Chat + evidence** as main story; tree/workbench secondary |

---

## Suggested naming (optional, future)

Introduce a **new block label** for R1+ (e.g. **Block 5 — Chat-first & evidence UI**) in implementation trackers when coding starts — avoids conflating with **Block 4A** workbench milestones.
