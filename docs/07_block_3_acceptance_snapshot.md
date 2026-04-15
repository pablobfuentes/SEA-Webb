# Block 3 — Acceptance snapshot (planning)

**Purpose:** Define what “Block 3 complete” means for **acceptance and testing**, aligned with `docs/06_block_3_implementation_plan.md`.  
**Status:** Planning baseline — update after implementation with actual test names and commit references.

---

## 1. Product outcome (user-visible capability)

After Block 3, a user or integrator can run a **single coherent engineering workflow** on a local project:

1. Create/load a project with normative context.  
2. Instantiate a **simple-span steel member** problem with **multiple structural alternatives** (truss, castellated/cellular, tapered/variable inertia, and optionally conventional beam — per approved plan).  
3. Record **assumptions** (span, loading intent, limits).  
4. Attach **characterizations** to alternatives: pros/cons with **explicit provenance** (retrieval-backed vs manual vs placeholder).  
5. **Retrieve** supporting passages where the corpus allows; receive structured **insufficient_evidence** when it does not.  
6. **Compare** branches with **enriched technical metrics** (including deterministic artifacts where implemented).  
7. **Select** one branch and run **preliminary deterministic calculations and checks** on that path.  
8. **Discard** other branches without losing them; **reopen** or keep them for comparison.  
9. Create a **revision** and verify that **tree + assumptions + calculations/checks** state is consistent when read back from the revision snapshot.

---

## 2. Technical acceptance checks

| # | Criterion | Verification |
|---|-----------|----------------|
| A | **E2E test** covers the full vertical flow (live + revision) | `tests/test_block3_*.py` (exact name TBD in implementation) passes |
| B | **Deterministic core** — same stored inputs → same calc/check outputs | Unit tests for deterministic module(s) |
| C | **Retrieval authority** — no user-facing normative claim without retrieval path or explicit refusal | Tests use corpus fixture; assert `CitationPayload` or `insufficient_evidence` |
| D | **Provenance** — non-corpus pros/cons are labeled | Schema + unit tests |
| E | **Comparison** — deterministic JSON ordering preserved | Extend existing comparison tests |
| F | **Internal traces** — `citation_trace_authority` remains `internal_trace_only` unless product explicitly upgrades | Assert in E2E |
| G | **Regression** — full pytest suite green | `python -m pytest tests/ -q` |

---

## 3. Example scenario (test narrative)

**Given** a temporary workspace and a small ingested text document approved for normative retrieval,  
**When** the Block 3 workflow creates a simple-span problem with four alternatives, attaches assumptions, runs retrieval for a characterization query, compares all branches, selects the castellated path, runs a simple-span deterministic check, and creates a revision,  
**Then** reloading from the revision snapshot reproduces comparable tree structure, assumption counts, calculation/check presence, and branch comparison row counts **for the same branch ids**.

(Exact assertions will mirror implementation — this snapshot requires **at least one** scenario of this class.)

---

## 4. Explicit non-goals (must remain false at Block 3 close)

- [ ] Full code-compliant design for all alternatives  
- [ ] Graphical tree UI  
- [ ] LLM produces numeric utilization or pass/fail  
- [ ] OCR pipeline  
- [ ] BIM/CAD  

---

## 5. Documentation deliverables at Block 3 close

- [ ] `docs/08_block_3_validation_report.md` (or equivalent) summarizing E2E + boundaries  
- [ ] `docs/CHANGELOG.md` — Block 3 implementation entry  
- [ ] `docs/TEST_STRATEGY.md` — Block 3 E2E pointer  

---

**Last updated:** 2026-04-12 (planning phase).
