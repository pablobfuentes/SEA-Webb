# Phase G3 — Truth proposals, explicit approval, projection mutation, audit history

**Status:** Implemented (2026-04-18).

## Scope delivered

| Area | Implementation |
|------|----------------|
| Domain | `TruthProposal`, `TruthProposalProjectionDelta`, `TruthProposalDispositionChange`, `TruthProposalDecision`, `TruthProposalStatus` in `domain/governance_models.py` / `domain/governance_enums.py`. |
| Codec | `truth_proposal_to_dict` / `truth_proposal_from_dict` in `domain/governance_codec.py` (sorted `rules_applied`, stable disposition ordering). |
| Schema | `schemas/truth_proposal.schema.json`; `active_knowledge_projection.schema.json` allows `schema_version` **g0.1** \| **g3.1**; `governance_event.schema.json` + **`governance_event_log.schema.json`** include `truth_proposal_*` event types; `validate_truth_proposal_payload`. |
| Store | `GovernanceStore.try_load_truth_proposal`, `save_truth_proposal` → `{project_id}/governance/proposals/{proposal_id}.json`. |
| Service | `services/truth_proposal_service.py` — `build_truth_proposal`, `persist_new_truth_proposal`, `approve_truth_proposal`, `reject_truth_proposal`. |
| Tests | `tests/test_governance_g3.py`. |

## Deterministic proposal policy (narrow)

Priority: **duplicate** → **supersession** → **contradiction** → **supporting** → **overlap** → empty / unhandled.

| G2 signal | Proposed effect |
|-----------|-----------------|
| `duplicate_candidate` | Add subject to `excluded_from_authoritative_document_ids`; no disposition rows (advisory exclusion until G4). |
| `supersession_candidate` | Subject → authoritative add; prior primaries in candidate set → remove authoritative + disposition **superseded**; subject disposition **active**. |
| `contradiction_candidate` | All involved documents → **conflicting_unresolved**; no authoritative activation via projection lists. |
| `supporting_candidate` | Add subject to supporting list; disposition **supporting**. |
| `overlap_candidate` | Narrative-only manual review; no automatic list/disposition changes. |
| No candidates | No automatic changes; explicit `g3.no_g2_candidates` rule. |

## Product rules preserved

- No silent conflict resolution; contradictions stay visible as **conflicting_unresolved** until explicitly governed otherwise.
- Approval applies `projection_delta` + `disposition_changes` with **stale-index guard** (`from_disposition` must match live index).
- Append-only event log: `truth_proposal_created`, `truth_proposal_approved` / `truth_proposal_rejected`, and `projection_updated` on successful approve.
- **Retrieval** still uses `Project.active_code_context.allowed_document_ids` (legacy binding); tests assert unchanged hit sets after approval — **G4** will wire projection.

## Out of scope (G4+)

Retrieval consuming projection, proposal UI, automatic resolution, embeddings/ML, chat/evidence panels.
