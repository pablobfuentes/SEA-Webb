from __future__ import annotations

from typing import Final, Literal

# Explicit provenance for qualitative alternative claims (M4). Not normative authority labels.
PROVENANCE_RETRIEVAL_BACKED: Final[str] = "retrieval_backed"
PROVENANCE_WORKFLOW_HEURISTIC: Final[str] = "workflow_heuristic"
PROVENANCE_MANUAL_PLACEHOLDER: Final[str] = "manual_placeholder"
PROVENANCE_NOT_YET_EVIDENCED: Final[str] = "not_yet_evidenced"

CharacterizationProvenance = Literal[
    "retrieval_backed",
    "workflow_heuristic",
    "manual_placeholder",
    "not_yet_evidenced",
]

ALL_CHARACTERIZATION_PROVENANCES: tuple[str, ...] = (
    PROVENANCE_RETRIEVAL_BACKED,
    PROVENANCE_WORKFLOW_HEURISTIC,
    PROVENANCE_MANUAL_PLACEHOLDER,
    PROVENANCE_NOT_YET_EVIDENCED,
)


def is_valid_characterization_provenance(value: str) -> bool:
    return value in ALL_CHARACTERIZATION_PROVENANCES


__all__ = [
    "ALL_CHARACTERIZATION_PROVENANCES",
    "CharacterizationProvenance",
    "PROVENANCE_MANUAL_PLACEHOLDER",
    "PROVENANCE_NOT_YET_EVIDENCED",
    "PROVENANCE_RETRIEVAL_BACKED",
    "PROVENANCE_WORKFLOW_HEURISTIC",
    "is_valid_characterization_provenance",
]
