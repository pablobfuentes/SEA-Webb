from __future__ import annotations

from dataclasses import asdict, replace

from structural_tree_app.domain.models import Project
from structural_tree_app.domain.simple_span_alternative_catalog import rank_eligible_alternatives
from structural_tree_app.domain.simple_span_workflow import (
    DECISION_PROMPT,
    SUGGESTED_TOP_K,
    WORKFLOW_ID,
    SimpleSpanWorkflowInput,
    SimpleSpanWorkflowResult,
    format_problem_description,
    format_problem_title,
)
from structural_tree_app.services.project_service import ProjectService
from structural_tree_app.services.simple_span_alternative_characterization import apply_simple_span_m4_characterization
from structural_tree_app.services.tree_workspace import TreeWorkspace
from structural_tree_app.validation.json_schema import validate_simple_span_workflow_input_payload


class SimpleSpanSteelWorkflowError(RuntimeError):
    """Invalid workflow setup (e.g. tree already exists)."""


class SimpleSpanSteelWorkflowService:
    """
    Block 3 M3–M4: persist the simple-span primary steel member decision workflow (M3)
    and lightweight alternative characterization with explicit provenance (M4).
    M3.1 ranking remains an internal workflow heuristic (not design adequacy).
    Deterministic preliminary Calculation/Check on a materialized branch: see ``simple_span_m5_service.run_simple_span_m5_preliminary`` (M5).
    """

    @staticmethod
    def setup_initial_workflow(
        project_service: ProjectService,
        project: Project,
        inp: SimpleSpanWorkflowInput,
    ) -> SimpleSpanWorkflowResult:
        validate_simple_span_workflow_input_payload(asdict(inp))

        live = project_service.load_project(project.id)
        if live.root_node_id is not None:
            raise SimpleSpanSteelWorkflowError(
                "Project already has a root problem; refuse duplicate M3 workflow setup"
            )

        tw = TreeWorkspace(project_service, live)
        title = format_problem_title(inp)
        description = format_problem_description(inp)
        branch, root = tw.create_root_problem(title, description)

        branch = tw.load_branch(branch.id)
        tags = sorted(
            [
                f"span_m:{float(inp.span_m):g}",
                f"support:{inp.support_condition}",
                WORKFLOW_ID,
            ]
        )
        branch = replace(
            branch,
            title="Simple span — primary member (M3 trunk)",
            description="Single trunk branch for the simple-span steel workflow; alternatives are sibling options under the decision node.",
            comparison_tags=tags,
        )
        tw.store.save_branch(branch)
        tw.ps.save_project(tw.project)

        ranked = rank_eligible_alternatives(inp)
        if not ranked:
            raise SimpleSpanSteelWorkflowError("No eligible alternatives available for this workflow input")
        option_defs = [(r.entry.title, r.entry.description, [], []) for r in ranked]
        tags.extend(
            [
                f"eligible_options:{len(ranked)}",
                f"suggested_top_k:{SUGGESTED_TOP_K}",
            ]
        )
        tags.sort()
        branch = replace(branch, comparison_tags=tags)
        tw.store.save_branch(branch)

        dec_node, decision, alts = tw.add_decision_with_options(
            branch.id,
            root.id,
            DECISION_PROMPT,
            option_defs,
        )
        for alt, ranked_alt in zip(alts, ranked):
            updated = replace(
                alt,
                catalog_key=ranked_alt.entry.key,
                suggested=ranked_alt.suggested,
                suggestion_rank=ranked_alt.rank if ranked_alt.suggested else None,
                suggestion_score=ranked_alt.score,
                suggestion_provenance=ranked_alt.entry.suggestion_provenance,
            )
            tw.store.save_alternative(updated)
        alts = [tw.store.load_alternative(a.id) for a in alts]

        apply_simple_span_m4_characterization(tw, decision.id)

        titles = [tw.store.load_alternative(aid).title for aid in decision.alternative_ids]
        return SimpleSpanWorkflowResult(
            workflow_id=WORKFLOW_ID,
            main_branch_id=branch.id,
            root_problem_node_id=root.id,
            decision_node_id=dec_node.id,
            decision_id=decision.id,
            alternative_ids=[a.id for a in alts],
            alternative_titles=titles,
        )


__all__ = ["SimpleSpanSteelWorkflowError", "SimpleSpanSteelWorkflowService"]
