# Document governance and active truth — roadmap rebaseline

**Status:** Planning — architecture extension (no implementation in this document).  
**Date:** 2026-04-18  
**Extends:** `docs/11_product_rebaseline_local_ai_chat_first.md` (chat-first, evidence-mandatory).  
**Pairs with:** `docs/14_detailed_revised_execution_order_with_governed_knowledge.md` (phased execution).

This document introduces a **mandatory** product layer that was implicit in “approved corpus” language but not yet spelled out as **first-class architecture**: **document governance** and **active operational truth** over a **multi-document, potentially overlapping** knowledge base—without opaque merging, without silent “learning,” and **without hiding conflicts** from users who need traceability.

---

## A. Corrected final product hierarchy

| Layer | Role |
|-------|------|
| **Local AI + governed knowledge + evidence-backed analysis** | **Primary** — answers are grounded in an **active governed knowledge view**, not in “all text ever ingested.” |
| **Chat** | **Primary interface** — structured questions, clarification, continuity of case-based reasoning. |
| **Evidence panel** | **Mandatory** — exact citations, expandable excerpts, **direct links** to source fragments; explicit tiers (authoritative active, supporting, insufficient). |
| **Logic / formulas / assumptions / checks panel** | **Mandatory** — audit trail for deterministic engine vs narrative; units, substitutions, checks. |
| **Canvas / drawing / formula area** | **Mandatory core explanatory surface** — diagrams, sketches, rendered formulas for the **current case** (not decorative). |
| **Document governance interface** | **Mandatory** — upload, ingestion state, segmentation, classification, **overlap/conflict/supersession**, proposals for truth updates, approval, history. |
| **Alternatives tree** | **Secondary** — case-by-case trace and option exploration; **not** the primary navigation model. |

**Ordering principle:** The **AI layer is subordinate** to **governed active knowledge**. Retrieval (`DocumentRetrievalService` and successors) must ultimately draw from **explicit active truth + declared corpus policy**, not from ad-hoc “whatever was ingested last.”

---

## B. What already-built work remains valid (preserve)

| Area | What to keep | Why |
|------|----------------|-----|
| **Block 2** | `JsonRepository`, project lifecycle, document registration, **ingestion → fragments**, chunk persistence, `ActiveCodeContext`, `allowed_document_ids`, revision snapshots | Foundation for governance **state persistence** and **fragment-addressable** citations. |
| **Block 3** (frozen) | Simple-span workflow, M4 characterization provenance, M5 preliminary deterministics, M6 comparison field sources, revision replay | Vertical **domain** slice; **do not** throw away. Governance **feeds** retrieval/M4—not replaces domain rules without ADR. |
| **Block 4A workbench** | Thin FastAPI/Jinja exercise of Block 3 | **Validation and secondary** UI; not the product shell. |
| **Phase R1** | `LocalAssistOrchestrator`, `local_assist_contract` | Correct **orchestration boundary**: retrieval-only path, refusal, citation-shaped outputs, deterministic hooks separated. **Evolve** orchestrator to call **active governed corpus** once that layer exists—contract shape stays. |

**Explicit non-throwaway:** Citation payloads (`CitationPayload`), authority modes (`normative_active_primary` vs `approved_ingested`), and **explicit insufficient-evidence** behavior remain the **pattern** for governance-aware retrieval.

---

## C. What is under-prioritized or mis-prioritized (re-contextualize)

| Item | Issue | Correction |
|------|--------|------------|
| **R2 as “evidence panel only”** | Evidence UI without **governed corpus definition** risks training users on a **partial** story (pretty citations while ambiguity in “what is active” remains). | R2 must be **paired or preceded** by **minimum governance visibility** (what is active, what is pending, what conflicts)—see doc 14. |
| **Workbench / 4A-M7 polish** | Still **demoted**; governance + chat surfaces outrank workbench hardening. | Occasional bugfixes only. |
| **Tree-first milestones** | Any work that implies **branching ontology as product center**. | Remain **secondary** integration milestones. |
| **“Retrieval = solved”** | Lexical search over approved docs ≠ **multi-document truth management**. | Retrieval must become **policy-aware** and **active-truth-aware** (see §D). |

---

## D. Document governance / active truth — architecture (target)

This section describes **target** capabilities. **Not all exist in code today**; doc 14 sequences implementation.

### D.1 Lifecycle states (conceptual minimum)

The roadmap must support the following **or equivalent** naming:

1. **Ingested** — bytes stored, extractable text available (or explicit failure state).  
2. **Analyzed** — segmentation/index metadata stable (chunks/fragments, basic stats).  
3. **Classified** — authority / scope / topic / normative class assigned (may be draft).  
4. **Compared** — assessed against **current active corpus** (overlap, duplication, contradiction, supersession, complementarity).  
5. **Assessed** — conflict/overlap/supersession report produced (machine-assisted + user-visible).  
6. **Proposed** — structured proposal for how **active truth** should change (which clauses/fragments govern, what is demoted).  
7. **Dispositioned** — status such as: **active**, **supporting**, **superseded**, **conflicting (unresolved)**, **rejected**, **pending review** (exact enum TBD in implementation).  
8. **Indexed** — **active governed knowledge view** regenerated for retrieval/AI consumption.  
9. **Traceable** — append-only (or versioned) **history**: what changed, when, by what decision, linking to document versions and fragment sets.

### D.2 Components (logical)

| Component | Responsibility |
|-----------|----------------|
| **Ingestion service** (extends existing) | Idempotent ingest, extract text, write fragments, **version** document identity. |
| **Segmentation store** | Stable fragment ids (already chunk-oriented; may need section/heading enrichment later). |
| **Classification service** | Assign normative class, topics, language, standard family—aligned with existing `Document` / project policy. |
| **Corpus diff / compare** | Detect overlap (embedding or lexical + metadata), flag contradiction candidates, supersession chains (e.g. code year), complementary scopes. |
| **Truth proposal engine** | Produces **human-reviewable** packages: “if you accept, active set becomes X; Y becomes supporting; Z superseded.” **No auto-merge** without explicit rule + user approval (policy TBD). |
| **Approval / workflow** | Transitions only through **explicit** user/engineer approval (audit log). |
| **Active knowledge projection** | Materialized view: **which document ids + optional fragment scopes** participate in **authoritative retrieval** for the AI. This is stricter than “all ingested.” |
| **Re-index job** | Rebuild search structures / caches from active projection. |
| **History store** | Project-scoped governance events, links to revision ids where applicable. |

### D.3 Relationship to retrieval today

Today, `DocumentRetrievalService` filters by **approval**, **active_code_context.allowed_document_ids**, **primary_standard**, etc. **Governance extends this**:

- **Active truth** may further **restrict** or **order** fragments (e.g. clause precedence within a standard family).  
- **Conflicting** documents may remain **visible in governance** but **excluded or quarantined** from authoritative retrieval until resolved.  
- **Superseded** content may remain **addressable for audit** but not for **normative design authority** unless explicitly reactivated.

---

## E. Knowledge authority model

### E.1 Categories (for AI behavior)

| Category | Meaning for retrieval / AI |
|----------|----------------------------|
| **Authoritative active** | May ground **normative** design statements when fragments match query; citations required. |
| **Supporting** | Context, commentary, examples—may appear labeled as supporting; **must not** override active standard unless policy allows. |
| **Superseded** | Historical; **not** used for active normative answers unless user explicitly runs “historical replay” mode (future). |
| **Conflicting (unresolved)** | **Must not** be silently resolved by the AI. Responses: refuse authoritative conclusion, present **governance action** + conflict summary. |
| **Non-authorized / rejected** | **Invisible** to retrieval for authoritative path; may appear in governance UI only. |
| **Preliminary deterministic (M5, etc.)** | **Engine output**, not document evidence—**unchanged** from Block 3 rules. |

### E.2 “One truth” clarification

**One operational truth** means: **one explicit, governed selection** of what counts as **active** for answering and for compliance—not **one sentence** that hides disagreement. **Conflicts remain visible** in governance and, when unresolved, in **user-facing refusal or structured conflict disclosure**—never silent blending.

---

## F. UI/UX implications (future product)

| Surface | Must expose |
|---------|-------------|
| **Chat** | Primary entry; clarifying questions; continuity; **never** implies authoritative engineering sign-off without evidence panel populated. |
| **Evidence** | Expandable citations; **open local source** to fragment; badges for authority tier. |
| **Logic / audit** | Formulas, substitutions, assumptions, checks—same authority rules as today’s Block 3 disclaimers. |
| **Governance** | Pipeline status per document; diff/conflict views; approve/reject/supersede; **history timeline**. |
| **Canvas** | Case/problem diagrams; formula render; **linked** to same case id as chat thread where possible. |
| **Tree** | Linked from chat or case—“explore alternatives”—not the home page. |

---

## G. Implications for the current workbench

| Topic | Guidance |
|-------|----------|
| **Role** | **Secondary validation** of Block 3 mechanics (workflow, M5, M6, revisions). |
| **Useful** | Honest provenance labels, read-only comparison, developer tests via HTTP. |
| **Pause** | **4A-M7** product polish; no governance features here until primary surfaces exist. |
| **Evolve later** | Optional **deep link** from governance (“open in trace workbench”) for power users—not a dependency for governance MVP. |
| **Do not** | Build governance workflows, conflict dashboards, or “product” navigation in the workbench shell. |

---

## H. Revised execution order (summary pointer)

**Detailed phased plan:** `docs/14_detailed_revised_execution_order_with_governed_knowledge.md`.

**Headline:** Introduce **governance and active-truth projection** **before or in tight parallel with** chat/evidence UI, so the **first** user-visible evidence experience does not cement the wrong mental model (“everything ingested is fair game”).

---

## I. Phase definitions

See **doc 14** for full per-phase objectives, dependencies, outputs, risks, and explicit **out-of-scope** items. Doc 14 replaces naive ordering “R2 → R3” where it conflicts with governance-first priorities.

---

## J. Minimal blockers (true prerequisites)

1. **Addressable fragments** with stable ids (already largely true via ingestion).  
2. **Project-scoped policy** for what “active” means (`ActiveCodeContext` extensible).  
3. **Explicit approval / disposition** path—cannot rely on “ingest = usable for normative AI.”  
4. **Orchestration contract** (R1) that **refuses** when evidence is missing—extend to **refuse when governance state is inconsistent** (e.g. unresolved blocking conflict on topic).

**Not** blockers for early governance **design**: full LLM, full canvas, workbench M7.

---

## K. Risks of not adjusting the roadmap

1. **Hidden conflicts** — AI or retrieval appears authoritative while corpus contains **unreconciled** contradictory clauses.  
2. **Silent staleness** — New standard uploaded but **old** fragments remain “active” in practice.  
3. **User distrust** — Pretty citations without **governed** lineage feel like theater.  
4. **Rework** — Chat UI built on “all approved text” requires **expensive retrofit** when governance lands.  
5. **Compliance risk** — Auditable engineering requires **traceable truth changes**, not just chat logs.

---

## Cross-references

- Product hierarchy (earlier): `docs/11_product_rebaseline_local_ai_chat_first.md`  
- Prior R-phase list (superseded in part by doc 14): `docs/12_revised_execution_order_after_rebaseline.md`  
- R1 implementation status: `docs/implementation/PHASE_R1_STATUS.md`  
- Block 3 freeze: `docs/implementation/BLOCK_3_STATUS.md`
