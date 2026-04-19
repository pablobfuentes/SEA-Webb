# Detailed revised execution order — governed knowledge + chat-first product

**Status:** Planning — phased roadmap (no implementation in this document).  
**Date:** 2026-04-18  
**Depends on:** `docs/11_product_rebaseline_local_ai_chat_first.md`, `docs/13_document_governance_and_active_truth_rebaseline.md`  
**Supersedes in part:** Linear-only sequencing in `docs/12_revised_execution_order_after_rebaseline.md` where it implied **R2 evidence UI before** explicit **governance** foundations. Doc 12 remains valid for **historical context**; **this document is the authoritative order** going forward.

---

## Executive sequencing principle

1. **Governed active knowledge** and **retrieval alignment** are **not optional late add-ons**.  
2. **Chat-first UI** and **evidence panel** remain primary surfaces—but they must attach to a **defined active corpus**, not to “all ingested blobs.”  
3. **Block 2 / 3 / 4A / R1** code is **preserved** and **extended**, not replaced.  
4. **Workbench** stays **secondary**; **4A-M7** stays **demoted**.

---

## Phase map (overview)

| Phase | Name | One-line objective |
|-------|------|-------------------|
| **G0** | Governance foundations (data model + states) | Define disposition enums, events, active projection contract. |
| **G1** | Ingestion → analysis → classification pipeline (extended) | Strengthen explicit states from doc 13 §A; persist transitions. |
| **G2** | Overlap / conflict / supersession assessment | Compare new/updated docs to active corpus; structured reports. |
| **G3** | Truth proposals + approval + history | Human-gated changes to active truth; append-only audit. |
| **G4** | Active corpus re-index + retrieval alignment | Retrieval and R1 orchestrator consume **active projection** only. |
| **U1** | Evidence panel + source links (UI) | Expandable citations, local fragment links, authority badges. |
| **U2** | Chat-first shell | Primary layout; threads; uses orchestrator + governance state. |
| **U3** | Local AI integration (non-runtime first optional) | Pluggable synthesis **under** contract; refusal preserved. |
| **U4** | Logic / formula / assumptions / checks panel | Deep link to Block 3 artifacts; M5 disclaimers. |
| **U5** | Canvas / drawing / formula surface | Case-scoped diagrams; export optional later. |
| **U6** | Secondary tree + workbench integration | Link-out; optional “open trace.” |

Phases **G*** may overlap **engineering time** with early **U*** prototypes **only** if **mocked** active projection is replaced before any “production narrative” claim—prefer **G0–G2** before **U1** ship-ready.

---

## G0 — Governance foundations (data model + states)

**Objective:** Introduce **versioned governance domain concepts**: document disposition, governance events, **active knowledge projection** schema (which `document_id`s + optional scopes are authoritative for AI retrieval).

**Why it matters:** Without shared vocabulary and persistence shapes, later phases duplicate state in ad-hoc JSON.

**Dependencies:** Block 2 project/document storage patterns; existing `Document`, `ActiveCodeContext`.

**Expected outputs:** ADR or schema notes; **enum**-level definitions; migration strategy for `allowed_document_ids` → **projection** (may wrap existing field initially).

**Risks:** Over-modeling before first conflict workflow—mitigate by **minimal** event log + disposition on `Document` or sidecar.

**Explicitly out of scope:** Full UI; ML-based contradiction detection; automatic merge.

---

## G1 — Ingestion, analysis, classification (pipeline extension)

**Objective:** Make **ingested → analyzed → classified** **explicit** and queryable; tie classification to **topics**, **normative class**, **standard family** (existing fields) plus **review status**.

**Why it matters:** Governance cannot compare documents that lack comparable metadata.

**Dependencies:** G0; `DocumentIngestionService`.

**Expected outputs:** State machine or status fields; tests for transitions; **no** change to Block 3 domain semantics without ADR.

**Risks:** Backfill for old projects—mitigate with defaults + “legacy unreviewed” flag.

**Out of scope:** OCR; cloud ingestion.

---

## G2 — Overlap, conflict, supersession assessment

**Objective:** Generate **structured assessment artifacts** when a document enters or updates: lexical/embedding overlap, metadata-based supersession hints (e.g. publication year), **contradiction candidates** (rule-based first).

**Why it matters:** Users must **see** tension before choosing truth.

**Dependencies:** G1; fragment store.

**Expected outputs:** `AssessmentReport` (name TBD) per document pair or per batch; **no auto-resolution**.

**Risks:** False positives—mitigate with **confidence** + user override; never auto-activate conflicting normative without approval.

**Out of scope:** Full NLP entailment; automatic legal interpretation.

---

## G3 — Truth proposals, approval, historical traceability

**Objective:** **Propose** changes to active truth (which documents/fragments govern); **approve** in explicit workflow; **log** immutable history (who/when/what link).

**Why it matters:** Satisfies audit and “why is this active?” questions.

**Dependencies:** G2; project revision concepts (reuse `create_revision` patterns where appropriate for **snapshots**, separate **governance event log**).

**Expected outputs:** Approval UI/API spec; event log format; rollback story (activate prior snapshot).

**Risks:** UX complexity—start with **engineer-first** approval path.

**Out of scope:** Multi-user roles (optional later); blockchain.

---

## G4 — Active corpus re-index + retrieval / R1 alignment

**Objective:** **Materialize** “active governed knowledge” for fast retrieval; update `DocumentRetrievalService` (or successor) to **only** search authoritative projection for **normative** path; keep `approved_ingested` as **explicit** secondary mode.

**Why it matters:** AI orchestration (**R1**) must call **one** authoritative path.

**Dependencies:** G3; R1 contract (`LocalAssistOrchestrator`).

**Expected outputs:** Retrieval tests updated; feature flag or project setting for “strict active projection.”

**Risks:** Performance—mitigate incremental re-index.

**Out of scope:** Vector DB mandate (optional).

---

## U1 — Evidence panel + direct source links

**Objective:** Minimal UI: list citations from orchestrator response; expandable excerpts; **open file/fragment** (local security rules).

**Why it matters:** First user-visible **trust** surface.

**Dependencies:** G4 **or** G4 mocked with current retrieval for prototype—**ship** only with G4 real path.

**Expected outputs:** Dedicated routes or SPA section; accessibility basics.

**Risks:** File URL security—use app-sandboxed viewer route.

**Out of scope:** Full PDF viewer with annotations.

---

## U2 — Chat-first shell

**Objective:** Primary layout: conversation + evidence strip; **thread** persistence.

**Why it matters:** Product center of gravity.

**Dependencies:** R1 + G4; U1 components reusable.

**Risks:** Session state duplication—**thin** server state, orchestrator as SoT for each turn.

**Out of scope:** Voice; mobile.

---

## U3 — Local AI integration layer

**Objective:** Optional **synthesis** of natural language **inside** `LocalAssistResponse` slots, **without** bypassing citations; model runs **local** when integrated.

**Why it matters:** Usability; not required for **audit** of governance.

**Dependencies:** U2; contract stability.

**Risks:** Hallucination—mitigate with **forced citation ids** per sentence (future constraint).

**Out of scope:** Agent swarms; tool plugins beyond retrieval/calc.

---

## U4 — Logic / formula / assumptions / checks panel

**Objective:** Surface Block 3 **Calculation** / **Check** / assumptions with same disclaimers as workbench.

**Dependencies:** Block 3 frozen APIs; chat case linkage.

**Out of scope:** New solvers.

---

## U5 — Canvas / drawing / formula area

**Objective:** Case-scoped diagrams; formula render; optional export.

**Dependencies:** U2 case id.

**Out of scope:** BIM; full CAD.

---

## U6 — Secondary tree + workbench

**Objective:** Integrate existing **Block 4A** routes as **linked** exploration; no navigation takeover.

**Dependencies:** Stable workbench routes.

**Out of scope:** 4A-M7 polish unless blocking.

---

## Relationship to prior R-phase labels (R2–R6)

| Old label (doc 12) | New mapping |
|--------------------|-------------|
| R2 evidence UI | **U1**, gated on **G4** for authoritative story |
| R3 chat shell | **U2** |
| R4 audit panel | **U4** |
| R5 canvas | **U5** |
| R6 tree/workbench | **U6** |

**Governance track** (**G0–G4**) is **inserted** as **parallel priority** to early UI; minimum **G0+G1+slice of G4** before claiming **normative** evidence UI is honest.

---

## J. Blockers (minimum, reiterated)

1. Stable **fragment addressing**.  
2. **Explicit** active projection **after** approval (G3/G4).  
3. **Refusal** paths when governance incomplete (extend R1).  

---

## K. Risks if roadmap is ignored

(See doc 13 §K; same themes: hidden conflict, stale truth, rework, compliance.)

---

## Cross-references

- Governance rebaseline narrative: `docs/13_document_governance_and_active_truth_rebaseline.md`  
- Chat-first rebaseline: `docs/11_product_rebaseline_local_ai_chat_first.md`  
- R1 status: `docs/implementation/PHASE_R1_STATUS.md`
