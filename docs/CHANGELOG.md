# Changelog

All notable changes to the **structural_tree_app_foundation** repository are documented here.  
(Block 2 planning entries are foundation-only; they are not mirrored to the parent monorepo `workflow/` logs unless explicitly requested.)

## [Unreleased]

### Integrated case flow hardening (session + URL query continuity)

**Added**

- `workbench/case_flow_handoff.py` — thin helpers for `?q=` / session last-assist query, project bind/invalidate, and `case_nav` link map for primary + secondary surfaces.
- `workbench/templates/partials/case_flow_primary_nav.html` — shared nav across chat, evidence, canvas, corpus, workflow (secondary) with optional `q` handoff and short continuity disclaimer.
- `docs/implementation/PHASE_INTEGRATED_CASE_FLOW_STATUS.md`.

**Changed**

- `workbench/deps.py` — `SESSION_LAST_ASSIST_QUERY_KEY` for last successful assist query string.
- `workbench/pages.py`, `workbench/corpus_pages.py` — GET prefill on chat/evidence/canvas; POST assist stores last query; project create/open/close use `bind_new_session_project` / `invalidate_session_project`; workflow and evidence views pass `case_nav`.
- Templates: `chat_shell.html`, `evidence_panel.html`, `canvas_u5.html`, `corpus_bootstrap.html`, `evidence_source_view.html`, `simple_span_workflow.html`, `partials/u6_secondary_to_workflow.html` — integrated nav + handoff-aware links.

**Tests**

- `tests/test_integrated_case_flow.py` — continuity, override, workflow return path with `q`, project switch clears handoff, no-session redirects, helper unit checks.
- `tests/test_workbench_u6.py` — assert `case-flow-primary-nav` where workflow/corpus expose the shared nav.

### Evidence viewer — PDF.js iframe (reliable page-accurate in-app viewer)

**Added**

- `workbench/templates/evidence_pdf_viewer.html` — standalone HTML page using **PDF.js 3.11.174** (jsDelivr CDN). Renders the PDF to canvas at the exact physical page; prev/next navigation; CDN-failure fallback with direct-download link.
- Route `GET /workbench/project/evidence/source/{document_id}/viewer?page=N` — validates session + project + document + file integrity, then serves `evidence_pdf_viewer.html`. PDF.js fetches the file via the same-origin `/file` route (session cookie included automatically).

**Changed**

- `evidence_source_view.py` — adds `pdf_viewer_url` (`/viewer?page=N`) alongside the existing `pdf_open_url` (`/file#page=N`).
- `evidence_source_view.html` — PDF panel now uses a proper `<iframe src="{{ pdf_viewer_url }}">` (PDF.js, reliable) as the **primary** embed; "Open in new tab" fallback link retained; `<object>` removed.
- Iframe uses `sandbox="allow-scripts allow-same-origin"` to keep the viewer contained.

**Tests**

- `test_pdf_viewer_route_returns_html` — viewer route returns 200 HTML with PDF.js reference at correct page.
- `test_pdf_viewer_route_404_for_unknown_doc` — 404 on bad document ID.
- `test_pdf_viewer_route_requires_session` — 303 redirect without session.
- `test_evidence_source_view_embeds_viewer_iframe` — fragment detail page uses `<iframe … /viewer?page=…>`.
- `test_pdf_viewer_url_in_context` — `build_evidence_source_view_context` produces correct `pdf_viewer_url` and `pdf_open_url`.

### Evidence viewer hardening — PDF page alignment & embed fallback

**Changed**

- `workbench/evidence_pdf_pages.py` — documents **1-based physical page** storage vs **PDF Open Parameters** `#page=` (same integer; no silent offset).
- `evidence_source_view.html` — **primary** “Open PDF at cited page (new tab)” with full `pdf_open_url`; optional **collapsed** inline `<object>` preview; copy explains many browsers ignore `#page=` in embeds; physical vs printed page disclaimer.
- `evidence_source_view.py` — `pdf_open_url`, `pdf_viewer_target_page_1based`, `page_semantics_note`; clearer precision strings.

**Tests**

- `tests/test_evidence_pdf_pages.py`; extra cases in `tests/test_evidence_original_source_viewer.py`.

### Evidence UX — original source viewer (citation hardening)

**Added**

- `GET /workbench/project/evidence/source/{document_id}/file` — serves **verified** original bytes (`content_hash` match) for PDF/text embedding; `404` when missing or tampered.
- `workbench/evidence_source_view.py` — `build_evidence_source_view_context`: modes `pdf_side_by_side`, `text_side_by_side`, `fragment_only`; explicit **location precision** (`exact_page` / `page_range` / `unknown_page`) and **no fake coordinate highlight** (excerpt = stored fragment text).
- Template `evidence_source_view.html` — side-by-side original file iframe + cited fragment; honest fallbacks and hash ids for audit.

**Changed**

- `DocumentIngestionService.ingest_local_file` — copies source into `workspace/.../documents/{doc_id}/original{ext}` so paths remain valid after temp uploads.
- `document_service.verify_document_file_bytes` — helper for safe file serving.
- Citation links (evidence panel, chat, canvas U5): label **Open citation source view**; same `/evidence/fragment/...` URLs preserved.

**Tests**

- `tests/test_evidence_original_source_viewer.py`; `tests/fixtures/sample_text.pdf` (two-page text PDF for ingest + page mapping).
- Adjusted U1/U2 assertions for new link label.

### Phase U6 — Secondary tree/workflow integration (primary surfaces unchanged)

**Added**

- `workbench/templates/partials/u6_secondary_to_workflow.html` — strip on chat, evidence, canvas linking to `/workbench/project/workflow` with explicit “secondary trace” framing.
- `workbench/templates/partials/u6_primary_surfaces_nav.html` — return nav on workflow and corpus pages to chat, evidence, canvas, hub.
- Workflow page heading/framing: positions simple-span surface as **secondary trace**; corpus page notes governance vs Q&amp;A.

**Changed**

- `chat_shell.html`, `evidence_panel.html`, `canvas_u5.html` — include U6 secondary strip; workflow nav link labeled “(secondary)”.
- `simple_span_workflow.html` — primary-surfaces nav + secondary-surface copy at top.
- `workbench_hub.html` — session section splits **Primary surfaces** vs **Secondary — trace &amp; workflow**.

**Tests**

- `tests/test_workbench_u6.py`; `docs/implementation/PHASE_U6_STATUS.md`.

### Phase U5 — Visual case canvas (reasoning-bridge board)

**Added**

- `workbench/u5_canvas_view.py` — `u5_canvas_board_from_result`, `evidence_fragment_href` (thin mapping for Jinja).
- `GET /workbench/project/canvas` — optional `q`; runs `ReasoningBridgeService.analyze` when `q` non-empty; renders `canvas_u5.html`.
- Chat, evidence, and project hub navigation to the canvas; `u5_canvas_href` in `_u1_template_context` when query text is present.

**Tests**

- `tests/test_workbench_u5.py`; `docs/implementation/PHASE_U5_STATUS.md`.

### Phase R2B — Reasoning / formula-selection bridge (pre–U5)

**Added**

- `domain/reasoning_bridge_contract.py` — `ReasoningBridgeRequest`, `ReasoningBridgeResult`, `ProblemInterpretation`, `EvidenceAnchor`, `CandidateProcessStep`, `CandidateFormulaOrCheck`, `SupportedExecutionStep`, `UnsupportedReasoningGap` (explicit authority / capability boundaries).
- `domain/reasoning_bridge_codec.py` — deterministic `reasoning_bridge_result_to_dict` / `from_dict`, `reasoning_bridge_request_to_dict`.
- `services/reasoning_bridge_service.py` — `ReasoningBridgeService.analyze`: governed `DocumentRetrievalService.search` + optional G5 derived bundle + deterministic tree scan; narrow keyword map for simple-span steel vertical slice; does **not** modify `LocalAssistOrchestrator`.
- `schemas/reasoning_bridge_result.schema.json`; `validate_reasoning_bridge_result_payload` in `validation/json_schema.py`.

**Tests**

- `tests/test_reasoning_bridge_r2b.py`; `docs/implementation/PHASE_R2B_STATUS.md`.

### Phase G5 — Derived knowledge layer (subordinate; pre–U5)

**Added**

- `domain/derived_knowledge_models.py`, `domain/derived_knowledge_codec.py` — versioned `DerivedKnowledgeBundle` with document/topic digests, navigation hints, formula/check registry (non-authoritative), governance signals; `SourceAnchorRef` links every derived row to `document_id` + `fragment_id` + content hashes.
- `schemas/derived_knowledge_bundle.schema.json` — JSON Schema for persisted bundles.
- `storage/derived_knowledge_store.py` — `{project_id}/derived_knowledge/bundle.json` with validation.
- `services/derived_knowledge_service.py` — deterministic `regenerate(project_id)`; content fingerprint for idempotent no-op; mirrors governed normative corpus selection (legacy allowed list vs explicit projection); preserves conflict/disposition signals without flattening.
- `validation/json_schema.py` — `validate_derived_knowledge_bundle_payload`.

**Tests**

- `tests/test_derived_knowledge_g5.py`; `docs/implementation/PHASE_G5_DERIVED_KNOWLEDGE_STATUS.md`.

**Notes**

- Does not wire derived artifacts into retrieval or `LocalAssistOrchestrator` (behavior unchanged by default). Consumed read-only by R2B and U5 canvas (see Phase U5).

### Phase U4 — Logic & audit panel (chat / evidence)

**Added**

- `workbench/u4_logic_audit.py` — `load_project_logic_audit_snapshot`: assumptions (project log), calculations and checks (tree store), M5 preliminary boundary + shared disclaimer string.
- `workbench/templates/partials/u4_logic_audit_panel.html` — sections for assumptions, deterministic calculations, checks; empty state; link to workflow; `u4-det-badge` / `preliminary M5` styling (not citation authority).
- Chat and evidence templates include U4 panel after assist output; `_u1_template_context` takes `ProjectService` and injects `u4_logic_audit`.

**Tests**

- `tests/test_workbench_u4.py`; `docs/implementation/PHASE_U4_STATUS.md`.

### U3 workbench UX — synthesis control always visible

**Changed**

- Chat and evidence query forms always include the U3 “Local answer synthesis” block: checkbox disabled (no submit name) when `STRUCTURAL_LOCAL_MODEL_ENABLED` is off, with copy to enable it; when on, checkbox is enabled with helper text for unchecked vs checked behavior (bounded `answer_text` only).
- Template partial `workbench/templates/partials/u3_synthesis_control.html`; duplicate status lines removed from `chat_shell.html` / `evidence_panel.html`.

**Tests**

- `tests/test_workbench_u3.py` — visibility, disabled/enabled states, POST passthrough, assist rendering unchanged.

### Phase U3 — Local model synthesis boundary (optional; subordinate to retrieval)

**Added**

- `services/local_model_config.py` — `STRUCTURAL_LOCAL_MODEL_ENABLED`, `STRUCTURAL_LOCAL_MODEL_PROVIDER` (`stub` | `unavailable`).
- `services/local_model_synthesis.py` — `LocalModelSynthesisPort`, deterministic `StubLocalModelSynthesizer`, `UnavailableLocalModelSynthesizer`.
- `LocalAssistOrchestrator` optional U3 step: replaces **only** `answer_text` when runtime enabled **and** `LocalAssistQuery.request_local_model_synthesis`; `response_authority_summary` may become `local_model_synthesis_bounded`; warnings disclose model restatement.
- `LocalAssistQuery.request_local_model_synthesis`; `ResponseAuthoritySummary.local_model_synthesis_bounded`.
- Workbench: U3 status + checkbox on chat and evidence forms.
- `tests/test_local_assist_u3.py`, `tests/test_workbench_u3.py`; `docs/implementation/PHASE_U3_STATUS.md`; deferred PDF viewer note: `docs/implementation/DEFERRED_EVIDENCE_UX.md`.

**Changed**

- `workbench/u1_evidence_display.py` — label for `local_model_synthesis_bounded`.
- `docs/TEST_STRATEGY.md` — U3 pointers; `README.md` — env vars for U3.

### Phase U2 — Chat-first workbench shell

**Added**

- `GET /workbench/project/chat`, `POST /workbench/project/chat/query` — primary assistant surface; same `LocalAssistOrchestrator` path as U1 (`_local_assist_run`, `_u1_template_context` in `workbench/pages.py`).
- Template `workbench/templates/chat_shell.html`; shared assist block `workbench/templates/partials/local_assist_result.html` (U1 evidence panel includes the partial).
- Project hub link order: Assistant (U2) first when a project is selected.

**Changed**

- `docs/TEST_STRATEGY.md` — U2 tests pointer; `README.md` — workbench routes paragraph mentions U2/U1.

**Tests**

- `tests/test_workbench_u2.py`; `docs/implementation/PHASE_U2_STATUS.md`.

### Corpus readiness / approval bridge (G1.5 follow-on)

**Added**

- `services/corpus_readiness.py` — `evaluate_document_readiness` (normative vs supporting vs blockers aligned with `DocumentRetrievalService` + G4 projection rules); `readiness_hint_html_for_evidence` for the evidence panel.
- Workbench: `POST /workbench/project/corpus/document/{id}/approve`, `POST .../readiness-metadata` (classification + `standard_family`); corpus list column **Readiness label**; document detail **Retrieval readiness** section + minimal approve/metadata forms.
- `workbench/u1_evidence_display.py` — `u1_readiness_hint_html`; `evidence_panel.html` renders readiness hint after refusals when normative retrieval yields no passages or governance blocks.
- `tests/test_corpus_readiness_bridge.py`; `docs/implementation/CORPUS_READINESS_BRIDGE_STATUS.md`.

### Phase G1.5 / U0 — Corpus bootstrap workbench (upload + manual governance bootstrap)

**Added**

- `services/corpus_bootstrap_service.py` — manual disposition + projection list alignment, retrieval binding update, optional legacy allow-list sync from authoritative projection; governance audit events.
- Workbench routes: `GET /workbench/project/corpus`, `POST /workbench/project/corpus/upload`, `GET /workbench/project/corpus/document/{document_id}`, `POST .../bootstrap`, `POST .../projection/binding`, `POST .../projection/sync-legacy-allowed`; templates `corpus_bootstrap.html`, `corpus_document.html`; hub link.
- `tests/test_workbench_corpus_bootstrap.py`; `docs/implementation/PHASE_G1_5_U0_STATUS.md`.

**Changed**

- `docs/TEST_STRATEGY.md` — corpus bootstrap tests pointer.

### Phase U1 — Workbench evidence panel + fragment source view

**Added**

- `LocalAssistResponse.normative_retrieval_binding` — mirrors governed normative retrieval source for UI (G4); `local_assist_response_to_dict` includes the field.
- Workbench routes: `GET/POST /workbench/project/evidence`, `GET /workbench/project/evidence/fragment/{document_id}/{fragment_id}`; templates `evidence_panel.html`, `evidence_fragment.html`; `workbench/u1_evidence_display.py` (label helpers only).
- `tests/test_workbench_u1.py`; `docs/implementation/PHASE_U1_STATUS.md`.

**Changed**

- `docs/TEST_STRATEGY.md` — U1 tests pointer.

### Phase G4 — Governed active knowledge projection in retrieval + local assist

**Added**

- `RetrievalResponse` fields: `normative_retrieval_source`, `governance_warnings`, `governance_normative_block` (`services/retrieval_service.py`).
- Normative retrieval branches: **`legacy_allowed_documents`** vs **`explicit_projection`** (from `ActiveKnowledgeProjection.retrieval_binding`); explicit path uses authoritative ids ± exclusions, validated against `DocumentGovernanceIndex`; refuses on missing index, empty authoritative set, or unresolved conflict on authoritative rows.
- `RefusalItem` codes `GOVERNANCE_CONFLICT_BLOCKS_NORMATIVE`, `GOVERNANCE_EXPLICIT_PROJECTION_UNAVAILABLE` (`domain/local_assist_contract.py`); `LocalAssistOrchestrator` maps retrieval blocks to these codes and appends governance warnings.
- `tests/test_governance_g4.py`; `docs/implementation/PHASE_G4_STATUS.md`.

**Changed**

- `docs/TEST_STRATEGY.md` — G4 test pointer.

### Phase G3 — Truth proposals, approval, active projection mutation, governance history

**Added**

- `TruthProposal`, `TruthProposalProjectionDelta`, `TruthProposalDispositionChange`, `TruthProposalDecision`, `TruthProposalStatus`; JSON Schema `truth_proposal.schema.json`; codec + `validate_truth_proposal_payload`; persistence under `governance/proposals/{proposal_id}.json`.
- `GovernanceEventType` extended with `truth_proposal_created`, `truth_proposal_approved`, `truth_proposal_rejected`; **`governance_event_log.schema.json`** event enum aligned with `governance_event.schema.json` for those types.
- `services/truth_proposal_service.py` — deterministic `build_truth_proposal` from G2 assessment + index + projection; `persist_new_truth_proposal`, `approve_truth_proposal`, `reject_truth_proposal` (stale disposition guard; approved path updates projection to `schema_version` **g3.1** and appends audit events).
- `tests/test_governance_g3.py`; `docs/implementation/PHASE_G3_STATUS.md`.

**Changed**

- `schemas/active_knowledge_projection.schema.json` — `schema_version` may be **g3.1** after an approved G3 proposal (default retrieval binding remains **legacy_allowed_documents** until explicitly set to **explicit_projection** in G4).
- `docs/TEST_STRATEGY.md` — G3 tests pointer.

### Phase G2 — Corpus assessment artifacts (overlap / contradiction / supersession **candidates**)

**Added**

- `CorpusAssessmentCandidateRelation`, `CorpusAssessmentCandidate`, `DocumentCorpusAssessment`; JSON Schema `document_corpus_assessment.schema.json`; codec + validation; persistence under `governance/assessments/{subject_document_id}.json`.
- `services/corpus_assessment_service.py` — deterministic heuristics (content hash, standard family, normative roles, title/fingerprint Jaccard, publication year / edition / version metadata); **not** final governance truth.
- Ingestion hook after G1: `_g2_assess_corpus_post_g1` in `document_service.py`.
- `tests/test_governance_g2.py`; `docs/implementation/PHASE_G2_STATUS.md`.

**Changed**

- `docs/TEST_STRATEGY.md` — G2 tests pointer.

### Phase G1 — Document governance pipeline (ingested → analyzed → classified)

**Added**

- `DocumentAnalysisSnapshot`, `DocumentClassificationSnapshot` on `DocumentGovernanceRecord`; index `schema_version` supports **g1.1** alongside **g0.1** (`schemas/document_governance_*.schema.json`).
- `services/governance_document_pipeline.py` — post-ingest governance upsert, deterministic “complete classification” rule, `promote_document_to_classified` for explicit promotion.
- `GovernanceStore.append_governance_events`.
- Ingestion hook: after successful persist, G1 updates governance index + pipeline `pipeline_stage_changed` events (`document_service.py`).
- `tests/test_governance_g1.py`; `docs/implementation/PHASE_G1_STATUS.md`.

**Changed**

- `docs/TEST_STRATEGY.md` — G1 tests pointer.

### Phase G0 — Governance foundations (domain + persistence)

**Added**

- `domain/governance_enums.py`, `domain/governance_models.py`, `domain/governance_codec.py` — lifecycle/disposition enums, active knowledge projection, per-document governance index, append-only governance events/log; deterministic dict key ordering.
- `schemas/active_knowledge_projection.schema.json`, `document_governance_record.schema.json`, `document_governance_index.schema.json`, `governance_event.schema.json`, `governance_event_log.schema.json`.
- `services/governance_store.py` — load/save validated JSON under `{project_id}/governance/`; `initialize_governance_baseline()` (legacy retrieval binding; optional explicit opt-in).
- `ProjectService.governance_store()`, `governance/` directory in project layout.
- `validation/json_schema.py` — governance payload validators.
- `tests/test_governance_g0.py`; `docs/implementation/PHASE_G0_STATUS.md`.

**Changed**

- `docs/TEST_STRATEGY.md` — G0 test pointer.

### Roadmap — document governance + active truth (planning only)

**Added**

- `docs/13_document_governance_and_active_truth_rebaseline.md` — mandatory governance/active-truth layer; lifecycle states; architecture components; knowledge authority model; UI implications; workbench positioning; blockers; risks of skipping governance.
- `docs/14_detailed_revised_execution_order_with_governed_knowledge.md` — phased plan (G0–G4 governance, U1–U6 product surfaces); per-phase objectives, dependencies, outputs, risks, out-of-scope; mapping from prior R2–R6 labels; **authoritative order** superseding naive R2→R3-only sequencing.

**Changed**

- `docs/12_revised_execution_order_after_rebaseline.md` — pointer to doc 14 for governed-knowledge execution order.
- `docs/implementation/PHASE_R1_STATUS.md`, `docs/implementation/BLOCK_4A_STATUS.md`, `docs/TEST_STRATEGY.md` — roadmap transition notes.

### Phase R1 — Local assist orchestration contract (backend)

**Added**

- `domain/local_assist_contract.py` — `LocalAssistQuery` / `LocalAssistResponse`, `OrchestrationCitation`, `EvidenceItem`, `AssumptionItem`, `DeterministicHookItem`, `RefusalItem`, `local_assist_response_to_dict()` (stable JSON keys).
- `services/local_assist_orchestrator.py` — `LocalAssistOrchestrator`: calls `DocumentRetrievalService` only for corpus text; optional project assumptions; optional read-only deterministic calculation hooks (M5 vs other); honest bounded `answer_text` (no LLM).
- `tests/test_local_assist_r1.py` — corpus path, refusal, citation completeness, authority separation, hooks vs citations, serialization stability, project/errors, read-only workspace proof.
- `docs/implementation/PHASE_R1_STATUS.md`.

**Changed**

- `docs/TEST_STRATEGY.md` — §2.x R1 orchestrator tests.

### Product rebaseline — chat-first local AI (planning only)

**Added**

- `docs/11_product_rebaseline_local_ai_chat_first.md` — corrected hierarchy: local AI + evidence-backed analysis primary; chat primary interface; mandatory citation and formula/logic audit panels; canvas as core explanatory surface; **alternatives tree secondary** (trace/exploration, case-based). Preserves Block 2/3/4A as infrastructure; demotes tree-first/workbench-as-product framing; defines exact-reference UI/data needs (§F), minimal blockers (§G), workbench implications (§E).
- `docs/12_revised_execution_order_after_rebaseline.md` — phased order after rebaseline (R1 orchestration → R2 evidence panel → R3 chat shell → R4 audit panel → R5 canvas → R6 secondary tree/workbench integration); **Block 4A-M7 demoted** pending R3+; optional future **Block 5** label for chat-first work.

**Changed**

- `docs/implementation/BLOCK_4A_STATUS.md` — transition note: rebaseline recorded; M7 paused/demoted strategically.
- `docs/TEST_STRATEGY.md` — rebaseline pointer; evidence/chat-first testing emphasis alongside existing tree integration tests.

### Block 4A — M6 — Branch comparison + revision snapshot (workbench)

**Added**

- `workbench/m6_workbench_view.py` — static legends for `comparison_field_sources` and `metric_provenance` (template-only labels).
- `workbench/m6_comparison_file.py` — persist last `BranchComparisonResult.to_dict()` at `{project_id}/workbench_m6_last_comparison.json` (session cookies cannot hold full JSON).
- `tests/test_workbench_m6.py` — compare live + revision replay, read-only branch file proof, error paths, unknown `?rev=`.

**Changed**

- `workbench/pages.py` — `POST /workbench/project/workflow/compare`, `POST /workbench/project/workflow/revision-create`; `GET .../workflow?rev=` loads revision snapshot context for comparison (read-only).
- `workbench/templates/simple_span_workflow.html` — M6 section: branch checkboxes, field-source / internal-trace banners, revision list links, last comparison JSON.
- `workbench/templates/base.html` — footer text (4A scope).
- `tests/test_workbench_m4.py` — footer assertion aligned with base template.
- `docs/implementation/BLOCK_4A_STATUS.md`, `docs/TEST_STRATEGY.md`.

### Block 4A — M5 — Materialize + M5 preliminary (workbench)

**Added**

- `services/simple_span_workflow_input_store.py` — persist/load `simple_span_workflow_input.json` at project root when M3 setup runs (enables M5 `SimpleSpanWorkflowInput` without recomputing from problem text).
- `workbench/m5_workbench_view.py` — read-only materialized-branch list + persisted M5 calc/check/assumption view for templates.
- `tests/test_workbench_m5.py` — materialize + M5 run + duplicate refusal + bad branch + reload persistence + preliminary copy.

**Changed**

- `services/simple_span_steel_workflow.py` — calls `save_simple_span_workflow_input` after successful `setup_initial_workflow`.
- `workbench/pages.py` — `POST /workbench/project/workflow/materialize`, `POST /workbench/project/workflow/m5-run`; GET workflow context includes M5 panel data.
- `workbench/templates/simple_span_workflow.html` — M5 section: preliminary disclaimers, per-alternative materialize, per-branch M5 run, persisted calculation/check/assumption JSON panels.
- `docs/implementation/BLOCK_4A_STATUS.md` — M5 complete; milestone order aligned with UI scope.
- `docs/TEST_STRATEGY.md` — §2.5 M5 workbench tests.

### Developer ergonomics — Windows workbench launcher

**Added**

- `scripts/run_workbench.ps1` — resolves repo root, requires `.venv` + editable `structural_tree_app.workbench`, sets default `STRUCTURAL_TREE_WORKSPACE` to `<repo>/workspace`, optional `-Reload` / `-NoBrowser` / `-Port`, opens browser at `/workbench` after a short delay.
- `run_workbench.bat` — one-double-click wrapper calling the PowerShell script with `ExecutionPolicy Bypass`.

**Changed**

- `README.md` — Block 4A: first-time setup, daily launcher usage, `-Reload` / health reminder, «connection failed» troubleshooting.
- `docs/TEST_STRATEGY.md` — §2.5 note on Windows launcher vs automated workbench tests.

**Fixed**

- `pyproject.toml` — `workbench` extra now includes `itsdangerous` (required by Starlette `SessionMiddleware`; was not always installed transitively).

### Block 4A — M4 — Alternatives & characterization inspection

**Added**

- `workbench/provenance_display.py` — static headings for characterization provenance strings.
- `tests/test_workbench_m4.py` — provenance substrings, suggestion columns, section headings in HTML.

**Changed**

- `workbench/workflow_summary.py` — alternative rows include description, suggestion score/provenance, `characterization_items`; `suggested_top_k`; suggested vs other eligible groupings.
- `workbench/pages.py` — provenance legend for template (from `ALL_CHARACTERIZATION_PROVENANCES`).
- `workbench/templates/simple_span_workflow.html` — authority banner, legend, `<details>` per alternative, characterization table (polarity, raw provenance, reference/retrieval fields).
- `docs/09_block_4a_implementation_plan.md` — milestone table + traceability aligned with execution order (M3 setup vs M4 inspection).
- `docs/implementation/BLOCK_4A_STATUS.md` — M4 complete; M5–M7 descriptions clarified.
- `docs/FAIL_LOG.md` — entry for accidental `simple_span_workflow_input.schema.json` overwrite during M3 (restored from git).
- `PBS Structural Engineer App.txt` — new **§19 Block 4A** (M2–M4 delivered, pending M5–M7, manual UI test guide).

**Verification**

- `python -m pytest tests/ -q` — 77 passed.

### Block 4A — M3 — Project hub + simple-span workflow setup

**Added**

- `workbench/pages.py` — routes: `GET /workbench` (hub), `POST` create/open/close project, `GET|POST /workbench/project/workflow`; thin handlers calling `ProjectService` and `SimpleSpanSteelWorkflowService.setup_initial_workflow`.
- `workbench/deps.py` — `ProjectService` + session `project_id` pointer dependencies.
- `workbench/workflow_summary.py` — read-only snapshot from `TreeStore` for templates.
- `workbench/form_parsing.py` — form → `SimpleSpanWorkflowInput` coercion.
- `workbench/templates/workbench_hub.html`, `simple_span_workflow.html` — validation workbench framing; install line `pip install -e ".[dev,workbench]"`.
- `tests/test_workbench_m3.py` — create project, workflow POST, redirect, persisted snapshot HTML.

**Changed**

- `workbench/app.py` — `SessionMiddleware`; include workbench router; removed obsolete `workbench.html` shell.
- `workbench/config.py` — `get_templates_dir`, `get_session_secret` / `WORKBENCH_SESSION_SECRET`.
- `pyproject.toml` — `workbench` extra: `python-multipart` (form posts).

**Verification**

- `python -m pytest tests/ -q` — 74 passed.

### Block 4A — M2 — FastAPI + Jinja workbench shell

**Added**

- `src/structural_tree_app/workbench/` — `create_app()`, `/health`, `/` → `/workbench`, templates `base.html` / `workbench.html`, `STRUCTURAL_TREE_WORKSPACE` config, `python -m structural_tree_app.workbench` (uvicorn).
- `tests/test_workbench_m2.py` — health, redirect, workbench HTML, optional `project_id` query display.
- `pyproject.toml` — optional dependency group `workbench` (fastapi, uvicorn, jinja2), `httpx` in dev; `package-data` for templates.

**Changed**

- `README.md` — workbench run instructions.
- `docs/implementation/BLOCK_4A_STATUS.md` — M2 complete.

**Verification**

- `python -m pytest tests/ -q` — 72 passed (superseded by M3 verification count).

### Block 4A — Planning — Minimum validation workbench (frontend)

**Rationale**

- Define the first thin, local frontend layer to exercise the frozen Block 3 vertical flow through UI interactions — without implementing UI in this step.

**Added**

- `docs/09_block_4a_implementation_plan.md` — scope, architecture proposal (FastAPI + Jinja recommended), milestones 4A-M1–M7, traceability, testing, acceptance, deferred items.
- `docs/10_block_4a_acceptance_snapshot.md` — acceptance criteria and manual checklist placeholders.
- `docs/implementation/BLOCK_4A_STATUS.md` — milestone tracker (all pending until implementation).

**Changed**

- `docs/TEST_STRATEGY.md` — Block 4A planned testing subsection.
- `README.md` — pointer to Block 4A planning; next-step wording.
- `docs/implementation/BLOCK_3_STATUS.md` — Block 4A dependency note (frozen baseline).

**Verification**

- Documentation-only change; no runtime code added.

### Block 3 — M7 — E2E vertical flow validation + validation report

**Rationale**

- Close Block 3 with one automated scenario that exercises M3→M4→materialized working branch→M5→M6→revision snapshot replay, with explicit documentation of preliminary vs authoritative boundaries and deferred registry work.

**Added**

- `tests/test_block3_vertical_flow.py` — `test_block3_m7_vertical_e2e_simple_span_castellated_m5_m6_revision_replay` (15 m span, four alternatives including optional rolled, castellated path, live vs snapshot comparison equivalence for M5 fields).
- `docs/08_block_3_validation_report.md` — acceptance narrative, output classification table, check-discovery via `calculation_id`, `method_label` deferrals.

**Changed**

- `docs/implementation/BLOCK_3_STATUS.md` — M7 complete.
- `docs/TEST_STRATEGY.md` — Block 3 E2E section points to M7 test + validation report.
- `docs/07_block_3_acceptance_snapshot.md` — documentation deliverables checked; test name fixed.
- `PBS Structural Engineer App.txt` §18.4 — M5–M7 marked complete for foundation scope.

**Verification**

- `python -m pytest tests/test_block3_vertical_flow.py -q` — 1 passed.
- `python -m pytest tests/ -q` — 67 passed.

### Block 3 — M6 — Branch comparison enriched with explicit M5 boundaries

**Rationale**

- Integrate M5 preliminary deterministic outputs into branch comparison without upgrading authority: keep preliminary signals explicit, preserve document-authority separation, and surface discoverability path for checks (`calculation_id`).

**Changed**

- `src/structural_tree_app/services/branch_comparison.py`
  - Adds `m5_preliminary` and `m5_checks_via_calculation_id` to comparison rows.
  - Adds `comparison_field_sources` with explicit categories: `m5_deterministic_preliminary`, `branch_tree_derived`, `manual_placeholder`, `document_trace_pending`.
  - Keeps `citation_traces` authority as internal trace only.
  - Discovers M5 checks through persisted check rows linked by `calculation_id` (node direct check linkage still deferred).
- `tests/test_branch_comparison.py`
  - Adds M6 tests for explicit M5 field projection/source classification and for discarded + non-selected branch comparability in the same comparison set.

**Verification**

- `python -m pytest tests/test_branch_comparison.py -q` — 8 passed.
- `python -m pytest tests/ -q` — 66 passed.

### Block 3 — M5 — Preliminary deterministic simple-span slice (Calculation / Check)

**Rationale**

- Attach a small reproducible deterministic evaluation to the materialized working-branch path root: indicative depth demand vs optional `max_depth_m`, fabrication-complexity alignment vs stated preferences, with explicit assumptions and empty `reference_ids` (no retrieval bypass).

**Added**

- `src/structural_tree_app/services/deterministic/simple_span_preliminary_m5.py` — `compute_preliminary_m5`, version `m5_simple_span_preliminary_v1`, authority metadata in `result`.
- `src/structural_tree_app/services/simple_span_m5_service.py` — `run_simple_span_m5_preliminary` (refuses duplicate M5 on same path root; persists Calculation, two Checks, Assumptions; links calc + assumptions on node).

**Verification**

- `python -m pytest tests/ -q` — 64 passed.

### Block 3 — M3.1 — Catalog-driven alternatives and deterministic top-3 suggestions

**Rationale**

- Replace fixed default alternatives with an extensible deterministic catalog: keep all eligible alternatives persisted, mark top-3 suggestions as workflow guidance only, and add explicit branch-to-alternative linkage for later branch materialization.

**Added**

- `src/structural_tree_app/domain/simple_span_alternative_catalog.py` — catalog entries, deterministic eligibility, deterministic scoring/ranking, stable tie-breaking, top-3 suggestion marking.
- `Alternative` metadata: `catalog_key`, `suggested`, `suggestion_rank`, `suggestion_score`, `suggestion_provenance`.
- `Branch.origin_alternative_id` as explicit branch-to-alternative linkage.
- Tests in `tests/test_simple_span_steel_workflow_m3.py` for catalog ranking determinism, top-3 persistence flags, backward-compatible loading of legacy alternative payloads, and branch origin-alternative integrity checks.

**Changed**

- `SimpleSpanSteelWorkflowService.setup_initial_workflow` now uses catalog-driven ranking and persists all eligible alternatives with non-authoritative suggestion metadata.
- `schemas/alternative.schema.json`, `schemas/branch.schema.json`, `domain/tree_codec.py`, `domain/tree_integrity.py` updated for new fields with backward-compatible defaults/validation.
- `domain/simple_span_workflow.py` no longer hardcodes fixed default option definitions.

**Verification**

- `python -m pytest tests/ -q` — 51 passed.

### Block 3 — M3 — Simple-span primary steel member workflow (initial branch generation)

**Rationale**

- Orchestrate the first engineering workflow for **simple-span primary steel member**: structured inputs, root PROBLEM node, one decision (“select primary structural solution”), and persisted **Alternative** records (workflow-level labels only; no M4 pros/cons or M5 calcs).

**Added**

- `src/structural_tree_app/domain/simple_span_workflow.py` — `SimpleSpanWorkflowInput`, `SimpleSpanWorkflowResult`, stable paths/titles, `default_alternative_option_defs(include_rolled)`.
- `src/structural_tree_app/services/simple_span_steel_workflow.py` — `SimpleSpanSteelWorkflowService.setup_initial_workflow` (refuses duplicate setup when project already has `root_node_id`).
- `schemas/simple_span_workflow_input.schema.json`; `validation/json_schema.py` — `validate_simple_span_workflow_input_payload`.
- `tests/test_simple_span_steel_workflow_m3.py` — valid flow, persistence, deterministic `to_dict`, optional rolled flag, invalid input, revision bundle, discard/reopen, `validate_tree_integrity`.

**Changed**

- `src/structural_tree_app/domain/tree_integrity.py` — fix `validate_tree_integrity` decision/alternative dict comprehensions (`did` / `aid` keys; was a `NameError`).

**Verification**

- `python -m pytest tests/ -q` — 48 passed.

### Block 3 — M2 — Calculation / Check / Reference tree persistence

**Rationale**

- Persist first engineering-workflow technical records under `tree/` (not `project.json`), schema-validated and revision-safe, so later milestones can attach deterministic work to nodes without breaking snapshots.

**Added**

- `tree/calculations/{id}.json`, `tree/checks/{id}.json`, `tree/references/{id}.json` via `TreeStore` (`save_*` / `load_*` / `list_*`).
- `schemas/check.schema.json`, `schemas/reference.schema.json`; `schemas/calculation.schema.json` tightened (`additionalProperties: false`).
- `domain/tree_codec.py` — `calculation_*`, `check_*`, `reference_*`, `canonicalize_json` for deterministic nested dicts and sorted `reference_ids` on calc/check.
- `validation/json_schema.py` — `validate_calculation_payload`, `validate_check_payload`, `validate_reference_payload`.
- `tests/test_tree_calculation_check_persistence.py` — round-trip, schema rejection, deterministic dict equality, revision bundle load, `validate_tree_integrity` cross-refs.

**Changed**

- `storage/tree_store.py` — layout and persistence for calculations, checks, references.
- `services/project_service.py` — `_ensure_layout` creates new tree subdirectories.
- `domain/tree_integrity.py` — integrity rules for calc/check/ref links and node `linked_*_ids`.
- `docs/implementation/BLOCK_3_STATUS.md` — M2 complete.

**Verification**

- `python -m pytest tests/ -q` — 40 passed.

### Planning — Block 3 implementation plan & acceptance snapshot

**Rationale**

- Define the first **vertical engineering slice**: simple-span primary steel member alternatives (truss, castellated/cellular, tapered/variable inertia, optional conventional beam), integrating tree workflow, retrieval-backed vs manual provenance, branch comparison enrichment, deterministic preliminary calculation/check persistence, and revision-safe replay — without UI, OCR, BIM, or a general-purpose solver.

**Added**

- `docs/06_block_3_implementation_plan.md` — executive summary, use case, scope, milestones M1–M7, file targets, traceability matrix, deterministic boundary, acceptance criteria, deferrals, blocking questions.
- `docs/07_block_3_acceptance_snapshot.md` — acceptance checks and example E2E narrative for Block 3 closure.

**Changed**

- `docs/implementation/BLOCK_2_STATUS.md` — Block 2 frozen as baseline dependency for Block 3.
- `docs/TEST_STRATEGY.md` — §2.4 Block 3 planned E2E pointer.

**Verification**

- Documentation reviewed for consistency with `docs/00–03`, `docs/05_block_2_validation_report.md`, and current codebase (tree store: branches/nodes/decisions/alternatives; `Calculation`/`Check` models exist; persistence for calcs/checks to be added in Block 3 implementation).

### M7 — Validation & integration (`cursor_prompts/08`)

**Rationale**

- Close Block 2 by proving M2–M6 work together: project/revision persistence, tree, ingestion, retrieval with citations, branch comparison (live + revision snapshot), deterministic ordering.

**M7 report (explicit)**

- **a) End-to-end scenario:** Documented in `docs/05_block_2_validation_report.md` — project → tree (two branches) → ingest → approve/activate → `normative_active_primary` retrieval → `create_revision` → `BranchComparisonService.for_live` and `for_revision_snapshot` (`tests/test_block2_integration.py`).
- **b) Internal vs authoritative:** Retrieval + `CitationPayload` remains the **authoritative** path for evidence-backed output. Branch comparison metrics/provenance are **engineering comparison v1**. `citation_traces` with `resolution_status="ids_only"` and `citation_trace_authority="internal_trace_only"` are **not** full authoritative citations (see validation report §2(b)).
- **c) Deferred after Block 2:** UI/visual tree; OCR; full Reference resolution for traces; richer retrieval tie-breaking; optional “compare two revisions” / golden regression workflows — listed in the validation report §2(c).

**Constraints (non-blocking, explicit in report)**

- Citation traces vs authoritative citations; reproducibility via revision snapshots + follow-ups; `metric_provenance`; deterministic ordering for branches, rows, and `to_dict()` serialization.

**Added**

- `tests/test_block2_integration.py` — integrated flow + deterministic ordering test.
- `docs/05_block_2_validation_report.md`.

**Changed**

- `README.md` — Block 2 completion note and realistic walkthrough.

**Verification**

- `python -m pytest tests/ -q` — 34 passed.

### M6 — Branch comparison v1 (`cursor_prompts/07`)

**Rationale**

- Compare two or more branches as structured decision alternatives without mutating branch state; support discarded branches side-by-side with active ones.

**Product rules (carry forward)**

- Any future answer or explanation layer must consume **only** `RetrievalResponse` + `CitationPayload` from `DocumentRetrievalService`, not raw corpus text.
- Design-authoritative paths keep default **normative_active_primary** unless explicitly overridden for audit/support views.

**M6 report (explicit)**

- **a) Criteria storage:** Metrics are read from persisted tree data under `tree/` (`Branch`, `Node`, `Decision`, `Alternative` via `TreeStore`) and from `assumptions.json` filtered by node ids belonging to each branch. Qualitative pros/cons are aggregated from `Alternative.pros` / `cons`. Optional engineering placeholders (`estimated_depth_or_height`, weight, fabrication, erection) are derived from `Branch.comparison_tags` when tags use the `key:value` convention (e.g. `depth:12m`, `weight:heavy`).
- **b) Quantitative vs qualitative:** *Quantitative* — `assumptions_count`, `calculations_count` (calculation-typed nodes plus `linked_calculation_ids`), `pending_checks_count`, `linked_reference_ids_count`, `max_subtree_depth`, `node_count`. *Qualitative* — `qualitative_advantages` / `qualitative_disadvantages`, `unresolved_blockers` (blocked node titles), and optional placeholder strings from tags.
- **c) Discarded branches:** Remain readable from `tree/branches/*.json`; comparison loads them like any branch and **does not** activate or reopen them, so they stay non-active for design while remaining comparable.
- **d) Document-derived references:** `reference_ids` lists node `linked_reference_ids`; each id is echoed in `citation_traces` as `DocumentCitationTrace` with `resolution_status: "ids_only"` until a dedicated Reference store resolves `document_id` / `fragment_id`.

**Future hardening (tracked, not in this milestone)**

- Conflict handling across multiple active authoritative document sources.
- Retrieval ranking thresholds and deterministic tie-breaking.

**Added**

- `BranchComparisonService`, `BranchComparisonResult`, `BranchComparisonRow`, `DocumentCitationTrace` in `services/branch_comparison.py`.
- `tests/test_branch_comparison.py`.

**Verification**

- `python -m pytest tests -q` — all tests pass.

### M5 — Document retrieval & citation (`cursor_prompts/06`)

**Rationale**

- Lexical retrieval over a filtered local corpus with explicit `CitationPayload` objects; structured `insufficient_evidence` when no qualifying passages exist (no LLM layer).

**Added**

- `DocumentRetrievalService` in `services/retrieval_service.py` — lexical scoring, filters (language, `document_ids`, topic, project primary `standard_family`), modes `normative_active_primary` vs `approved_ingested`.
- `tests/test_retrieval.py` — hits, filters, insufficient evidence, unknown classification excluded from normative mode.

**Verification**

- `python -m pytest tests -q` — all tests pass.

### M4b — Corpus authorization & classification (document-first)

**Changed**

- **Ingestion ≠ normative:** `ingested_document_ids` tracks catalog; `active_code_context.allowed_document_ids` is the normative/active pool and is **not** populated on ingest. `approve_document`, `activate_for_normative_corpus`, `document_corpus_policy` (`strict` vs `approve_also_activates`).
- **Normative classification:** `Document.normative_classification` (`unknown` | `primary_standard` | `supporting_document` | `reference_document`); `standard_family` is **not** defaulted from the project primary standard when omitted.
- **Fragments:** `fragment_content_hash`, `material_content_hash` (byte-identity), `ingestion_method`, snapshot approval/classification, PDF page range when extractable.
- **Project JSON migration:** `ingested_document_ids` / `document_corpus_policy` backfilled on load when missing.

### M4 — Local document ingestion (`cursor_prompts/05`)

**Rationale**

- Authoritative corpus registration with chunked fragments and citation-oriented metadata; offline, no cloud APIs.

**Added**

- `DocumentIngestionService` in `services/document_service.py` — pipeline import → normalize → segment → persist under `documents/{document_id}/`.
- `domain/document_codec.py`; JSON Schemas `document.schema.json`, `document_fragment.schema.json`.
- Stable fragment ids: `frag_` + SHA-256(`document_id|chunk_index|text`) prefix.
- Dependency: `pypdf` for text-layer PDF extraction.

**Persistence hardening (tracked)**

- Revision write-once guard; `RevisionBundle` + `load_revision_bundle` for snapshot-only tree/project/assumptions (`docs/implementation/PERSISTENCE_HARDENING.md`).
- `TreeStore` refactor: `relative_root` supports live `…/tree` vs revision `…/revisions/{id}/tree`.
- `domain/tree_integrity.py` — `validate_tree_integrity`.

**Verification**

- `python -m pytest tests -q` — all tests pass.

### M3 — Tree expansion & branch state (`cursor_prompts/04`)

**Rationale**

- Persist the decision tree under `tree/` (not embedded in `project.json`), with explicit branch lifecycle and auditable timestamps.

**Added**

- `src/structural_tree_app/domain/tree_codec.py` — JSON-safe branch/node/decision/alternative mapping.
- `src/structural_tree_app/domain/branch_transitions.py` — allowed branch state transitions.
- `src/structural_tree_app/storage/tree_store.py` — `TreeStore`, `copy_tree_directory` for revision snapshots.
- `src/structural_tree_app/services/tree_workspace.py` — persisted tree operations (root problem, children, decision options, activate/discard/reopen/clone, subtree, branch paths).
- Strict JSON Schemas: `branch.schema.json`, `node.schema.json`, `decision.schema.json`, `alternative.schema.json`; stricter `project.schema.json`, `revision.schema.json`, `assumption_record.schema.json`.

**Changed**

- `JsonRepository.write` — atomic write via temp file + `os.replace`.
- `ProjectService` — each revision stores `assumptions_snapshot.json` and a full copy of `tree/` under `revisions/{rev_id}/`; `load_revision_snapshot_assumptions`.
- `validation/json_schema.py` — validators for tree entities and assumptions list.

**Verification**

- `python -m pytest tests -q` — all tests pass (project + tree).

### M2 — Project persistence & versioning (`cursor_prompts/03`)

**Rationale**

- Reliable on-disk projects with revision history separate from project identity; prepare `tree/`, `documents/`, `exports/` for later milestones.

**Added**

- `src/structural_tree_app/paths.py` — repository root for schema loading.
- `src/structural_tree_app/validation/json_schema.py` — validate `project.json` and revision `meta.json` (Draft 2020-12).
- `src/structural_tree_app/domain/project_codec.py` — `project_to_dict` / `project_from_dict`; assumptions list helpers.
- `schemas/revision.schema.json` — revision metadata.
- `tests/test_project_persistence.py` — create/load/save, revisions, snapshots, invalid payload, `examples/example_project.json` mapping, assumptions.

**Changed**

- `Project.head_revision_id`; `RevisionMetadata` dataclass in `domain/models.py`.
- `schemas/project.schema.json` — optional `head_revision_id`.
- `ProjectService` — layout `workspace/{project_id}/`, `create_project`, `load_project`, `save_project`, `create_revision`, `list_revisions`, `load_revision_snapshot_project`, `load_assumptions` / `save_assumptions`.
- `JsonRepository.exists`.
- `main.py` — `save_project` after bootstrap tree mutation so `project.json` reflects `root_node_id` / `branch_ids`.
- `requirements.txt` / `pyproject.toml` — runtime dependency `jsonschema`.

**Verification**

- Superseded by full suite under M3; `tests/test_project_persistence.py` remains part of regression.

### M1 — Repository workflow & governance (`cursor_prompts/02`)

**Rationale**

- Establish predictable development workflow, minimal engineering artifacts, and auditable Block 2 progress without implementing persistence, ingestion, retrieval, or comparison logic.

**Added**

- `docs/implementation/BLOCK_2_STATUS.md` — milestone tracker (M1 complete).
- Root `CONTRIBUTING.md` — execution order of `cursor_prompts/02–08`, engineering rules (tree-first, document/citation-first, no OCR in Block 2 for ingestion), logging policy, local checks.
- Root `.gitignore` — Python, tooling caches, `workspace/`, virtualenvs.
- Root `pyproject.toml` — package metadata, `src` layout, optional `dev` extras (`pytest`), pytest `pythonpath`.
- Root `Makefile` — `import-check` target (`PYTHONPATH=src`).

**Changed**

- `README.md` — Block 2 execution table, pointers to plan/status/tests/contributing, development/local check notes.

**Verification**

- `python -c "import structural_tree_app; from structural_tree_app.main import bootstrap_example; print('ok')"` with `PYTHONPATH=src` (or `pip install -e .`) succeeds.
- `make import-check` succeeds where GNU Make is available.

### Planning — Block 2 implementation plan package

**Rationale**

- Execute the approved Block 2 **planning phase only**: implementation-ready roadmap, test strategy, and failure log scaffold aligned with `docs/00–03`, ADR-001, and the master data model.

**Added**

- `docs/04_block_2_implementation_plan.md` — Milestones M1–M7 mapped to `cursor_prompts/02–08`, traceability matrix (MVP → milestone → files → test intent), vision guardrails, rollback notes, and blocker-level open questions.
- `docs/TEST_STRATEGY.md` — Testing approach for Block 2 and beyond (local-first, deterministic vs LLM, citation completeness).
- `docs/FAIL_LOG.md` — Failure log template for Block 2 execution (no failures recorded for this planning-only step).
- `docs/CHANGELOG.md` — This file.

**Verification**

- Documentation reviewed for consistency with `docs/00_product_definition.md`, `docs/01_architecture_v1.md`, `docs/02_master_data_model.md`, `docs/03_mvp_scope.md`, and `docs/adr/ADR-001-local-first-architecture.md`.
- No application source code was modified as part of this planning-only deliverable.

### Documentation — Block 2 OCR policy & traceability (post-planning)

**Changed**

- `docs/04_block_2_implementation_plan.md` — **No OCR in Block 2**; M4 text-extractable PDFs only; structured statuses for non-extractable PDFs; A1/A2 approved; traceability row for corpus registration **M4 only**; **abrir referencia** remains **M5 only** (single row).
- `docs/TEST_STRATEGY.md` — M4 ingestion expectations aligned with no-OCR policy.
