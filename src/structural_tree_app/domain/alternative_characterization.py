from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

Polarity = Literal["pro", "con"]


@dataclass(frozen=True)
class AlternativeCharacterizationItem:
    """
    One qualitative claim for an alternative. M4: explicit provenance only.
    ``suggestion_score`` on the parent Alternative (from M3.1 ranking) is unrelated —
    it is internal workflow ordering, not design adequacy.
    """

    text: str
    polarity: Polarity
    provenance: str
    reference_id: str | None = None
    retrieval_query: str | None = None
    citation_authority: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "polarity": self.polarity,
            "provenance": self.provenance,
            "reference_id": self.reference_id,
            "retrieval_query": self.retrieval_query,
            "citation_authority": self.citation_authority,
        }


def characterization_item_from_dict(data: dict[str, Any]) -> AlternativeCharacterizationItem:
    return AlternativeCharacterizationItem(
        text=data["text"],
        polarity=data["polarity"],
        provenance=data["provenance"],
        reference_id=data.get("reference_id"),
        retrieval_query=data.get("retrieval_query"),
        citation_authority=data.get("citation_authority"),
    )


__all__ = ["AlternativeCharacterizationItem", "Polarity", "characterization_item_from_dict"]
