# Phase G2 — Corpus overlap / conflict / supersession **candidate** assessment

**Status:** Implemented (2026-04-18).

## Scope delivered

| Area | Implementation |
|------|------------------|
| Domain | `CorpusAssessmentCandidateRelation`, `CorpusAssessmentCandidate`, `DocumentCorpusAssessment` in `domain/governance_models.py`; enum in `domain/governance_enums.py`. |
| Codec | `document_corpus_assessment_to_dict` / `_from_dict` in `domain/governance_codec.py` (deterministic key ordering and sorted candidates). |
| Schema | `schemas/document_corpus_assessment.schema.json`; `validate_document_corpus_assessment_payload`. |
| Store | `GovernanceStore.try_load_document_corpus_assessment`, `save_document_corpus_assessment` → `{project_id}/governance/assessments/{subject_document_id}.json`. |
| Service | `services/corpus_assessment_service.py` — `build_document_corpus_assessment`, `assess_and_persist_document_corpus_assessment`. |
| Ingestion | `DocumentIngestionService` calls G2 after G1 (`_g2_assess_corpus_post_g1`). |
| Tests | `tests/test_governance_g2.py`. |

## Product rules

- Assessments are **candidate** signals only (`assessment_framing` = `candidate_assessment_not_governance_decision`).
- No automatic conflict resolution, no active-truth switch, **no retrieval behavior change** (G4+).

## Out of scope (G3+)

Approval workflow, projection mutation, policy-based switching, entailment/embeddings mandate, UI.
