# Product rebaseline — local AI, chat-first, evidence-authoritative

**Status:** Planning — architecture and development-order correction (no implementation in this document).  
**Date:** 2026-04-18  
**Supersedes (for primary UX and product narrative):** The **tree-as-primary** framing in early product docs (e.g. `docs/00_product_definition.md` purpose section, `docs/01_architecture_v1.md` “núcleo conceptual”). **Domain and code delivered under Block 2 / Block 3 / Block 4A remain valid as infrastructure** (see §B). This document does **not** revoke Block 3 freeze; it reorders **what we build next** and **what the main surface is**.

---

## A. Corrected product hierarchy

| Layer | Role |
|-------|------|
| **Local AI orchestration** | Primary — routes questions through **approved local documents only**, structured outputs, refusal when evidence is insufficient, separation from deterministic calculation. |
| **Chat / question input** | Primary interface — iterative, case-based problem solving, not navigation of a universal ontology. |
| **Evidence / citation panel** | **Mandatory** — every technical claim must expose **exact** source references (document, section/fragment, expandable excerpt). |
| **Formula / logic / assumptions / checks panel** | **Mandatory** — auditable path: assumptions → formulas → deterministic results (where applicable) vs LLM narration (clearly labeled). |
| **Canvas / drawing / formula area** | **Core explanatory surface** — sketches, annotated formulas, load diagrams; not optional “nice-to-have” for the main product story. |
| **Alternatives tree** | **Secondary** — traceability and exploration, **generated case by case**, branching options and decision record, **not** the default mental model for all structural analysis. |

**Non-negotiable rules (unchanged in intent, reinforced in priority):**

1. AI analysis uses **only** user-approved documents in the local repository (active normative context respected).  
2. Every answer must expose **exact** source references in **expandable** form.  
3. User can **follow logic** and **audit** formulas (deterministic layer separate from LLM).  
4. **Retrieval** remains the **authority gate** for document-backed claims.  
5. **Deterministic calculation** remains **separate** from the LLM layer.  
6. The **tree is not** the main product surface.  
7. The system is **iterative and case-based**, not a single universal branching structure for all work.

---

## B. What current work remains valid (preserve)

### Block 2 (infrastructure)

- Local project lifecycle, JSON workspace, document registration and ingestion, chunking, **retrieval with citation-shaped results**, revision snapshots, `TreeStore` / `TreeWorkspace`, branch lifecycle (materialize, discard, reopen, clone) as **persistence and exploration mechanics**.

### Block 3 (frozen domain baseline)

- `SimpleSpanSteelWorkflowService`, catalog-driven alternatives, M4 **characterization with provenance**, M5 **preliminary deterministic slice** (explicitly non-authoritative for “final” adequacy), M6 **branch comparison** with field-source maps, revision replay via snapshot stores — all remain **correct backend contracts** for the steel simple-span vertical slice.  
- **Tests and validation reports** remain the evidence that domain behavior is sound.  
- **No feature redesign** of Block 3 except justified bugfixes (existing policy).

### Block 4A (workbench)

- Thin FastAPI + Jinja workbench that **exercises** Block 3 through HTTP is **valid** as a **developer/validation** and **secondary exploration** UI.  
- Routes, provenance legends, M5/M6 disclaimers, and read-only comparison behavior align with **authority boundaries** and should be **reused**, not thrown away — but **must not** be mistaken for the long-term **primary** product shell.

---

## C. What is now mis-prioritized (secondary or delayed)

| Item | Previous risk | Correction |
|------|----------------|------------|
| **Tree-first UX and flows** | Treated as the main way users “do” structural analysis | Demoted to **secondary** — optional when exploration/traceability helps. |
| **Workbench-as-product** | Expanding panels, workflow page as “the app” | **Validation / slice explorer** only until chat-first shell exists; **do not** overbuild styling, dashboards, or universal navigation here. |
| **Block 4A M7** (E2E workbench polish) | Could absorb effort before primary UX exists | **Paused / demoted** as a product milestone — see `docs/12_revised_execution_order_after_rebaseline.md`. Small bugfixes to existing workbench remain acceptable. |
| **Further tree-centric milestones** before chat/citation | Delivers exploration without primary Q&A loop | **Delayed** until orchestration + evidence UI foundations exist (staged order in doc 12). |

---

## D. Revised execution order (summary)

Detailed staging is in **`docs/12_revised_execution_order_after_rebaseline.md`**. In short, after this rebaseline:

1. **Local AI orchestration** contracts (inputs/outputs, grounding policy, refusal).  
2. **Evidence-linked retrieval output** in the UI (exact fragments, expandable citations, local source links).  
3. **Chat-first** conversation shell (primary).  
4. **Formula / logic / assumptions / checks** audit surface (wired to deterministic + explicit labels).  
5. **Canvas / formula** explanatory area.  
6. **Secondary** integration of the **existing tree/workbench** (link-out or side panel, not the default home).

---

## E. Implications for the current workbench

| Question | Answer |
|----------|--------|
| **What it becomes** | A **secondary** tool: validate Block 3 behavior, inspect alternatives/branches/M5/M6, compare revisions — **engineering trace view**, not the main entry point. |
| **What stays** | Thin routes, server-rendered forms, explicit provenance copy, **no client-side business logic**, same service calls as tests. |
| **What should not happen** | Treating the workflow page as the **product home**, heavy JS/dashboards, polishing the workbench **instead of** building chat + evidence + audit + canvas for the primary journey. |

---

## F. Data and UI requirements for exact references

To satisfy “exact evidence” in the primary UI (future implementation; requirements definition here):

| Requirement | Meaning |
|-------------|---------|
| **Stable citation payload** | Document id, fragment/chunk id, character or byte span (or equivalent), excerpt text, optional section label from corpus metadata. |
| **Expandable citation UI** | Collapsed summary (e.g. code + clause id); expanded full excerpt; **no** merging of multiple sources into one undifferentiated blob. |
| **Direct local link** | In-app route or `file:` / workspace-relative open to the **same** stored fragment (security: only within approved project paths). |
| **Authority tiers (visual + data)** | **Authoritative** (retrieval-backed, active normative context) vs **supporting** vs **no evidence** vs **preliminary deterministic** vs **internal trace only** — **never** merged into a single “recommended answer” without explicit labels. |
| **LLM outputs** | Must carry **per-claim** linkage to citation ids or explicit “ungrounded / hypothetical” flags — orchestration contract TBD in implementation block, not in this doc. |

---

## G. Minimal blockers (true prerequisites)

Only these **block** a credible chat-first, evidence-mandatory product slice:

1. **Retrieval pipeline** returns **stable, addressable** fragments for UI binding (existing Block 2/3 pieces are close; may need **contract hardening** for UI, not a rewrite).  
2. **Policy** that **forbids** presenting ungrounded technical claims as authoritative (orchestration + UI copy).  
3. **Separation** of **deterministic** results from **LLM** narrative in the **same screen** (panels or clear sections).  
4. **Local document access path** for “open source” from a citation (route or controlled file opener).

Nice-to-have but **not** blockers for a first vertical slice: full canvas polish, full tree integration, workbench M7 polish.

---

## Cross-references

- Execution order: `docs/12_revised_execution_order_after_rebaseline.md`  
- Frozen domain: `docs/implementation/BLOCK_3_STATUS.md`, `docs/08_block_3_validation_report.md`  
- Current workbench scope: `docs/09_block_4a_implementation_plan.md`, `docs/implementation/BLOCK_4A_STATUS.md`
