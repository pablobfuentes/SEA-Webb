from __future__ import annotations

from dataclasses import dataclass

from structural_tree_app.domain.simple_span_workflow import SimpleSpanWorkflowInput


@dataclass(frozen=True)
class SimpleSpanAlternativeCatalogEntry:
    key: str
    title: str
    description: str
    enabled: bool = True
    base_priority: int = 0
    suggestion_provenance: str = "workflow_heuristic"


@dataclass(frozen=True)
class RankedAlternative:
    entry: SimpleSpanAlternativeCatalogEntry
    score: float
    rank: int
    suggested: bool


SIMPLE_SPAN_ALTERNATIVE_CATALOG: tuple[SimpleSpanAlternativeCatalogEntry, ...] = (
    SimpleSpanAlternativeCatalogEntry(
        key="truss",
        title="Truss (celosía)",
        description="Triangulated steel system between supports. Workflow guidance only.",
        base_priority=60,
    ),
    SimpleSpanAlternativeCatalogEntry(
        key="castellated",
        title="Castellated / cellular beam",
        description="Castellated or cellular profile along the span. Workflow guidance only.",
        base_priority=55,
    ),
    SimpleSpanAlternativeCatalogEntry(
        key="tapered",
        title="Tapered beam (variable inertia)",
        description="Member with varying depth or inertia along the span. Workflow guidance only.",
        base_priority=54,
    ),
    SimpleSpanAlternativeCatalogEntry(
        key="rolled",
        title="Rolled or built-up beam (conventional)",
        description="Standard rolled section or built-up plate girder. Workflow guidance only.",
        base_priority=50,
    ),
)


def is_entry_eligible(entry: SimpleSpanAlternativeCatalogEntry, inp: SimpleSpanWorkflowInput) -> bool:
    if not entry.enabled:
        return False
    if entry.key == "rolled" and not inp.include_optional_rolled_beam:
        return False
    return True


def score_entry(entry: SimpleSpanAlternativeCatalogEntry, inp: SimpleSpanWorkflowInput) -> float:
    score = float(entry.base_priority)
    if inp.lightweight_preference and entry.key in {"truss", "castellated"}:
        score += 5.0
    if inp.fabrication_simplicity_preference and entry.key == "rolled":
        score += 6.0
    if inp.max_depth_m is not None and entry.key in {"truss", "castellated"}:
        score += 2.0
    if inp.architectural_restriction and entry.key in {"truss", "tapered"}:
        score += 1.0
    return score


def rank_eligible_alternatives(inp: SimpleSpanWorkflowInput) -> list[RankedAlternative]:
    eligible = [entry for entry in SIMPLE_SPAN_ALTERNATIVE_CATALOG if is_entry_eligible(entry, inp)]
    scored = [(entry, score_entry(entry, inp)) for entry in eligible]
    scored.sort(key=lambda x: (-x[1], -x[0].base_priority, x[0].key))
    ranked: list[RankedAlternative] = []
    for idx, (entry, score) in enumerate(scored, start=1):
        ranked.append(
            RankedAlternative(
                entry=entry,
                score=score,
                rank=idx,
                suggested=idx <= 3,
            )
        )
    return ranked


__all__ = [
    "RankedAlternative",
    "SIMPLE_SPAN_ALTERNATIVE_CATALOG",
    "SimpleSpanAlternativeCatalogEntry",
    "is_entry_eligible",
    "rank_eligible_alternatives",
    "score_entry",
]
