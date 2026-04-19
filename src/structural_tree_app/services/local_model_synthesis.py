"""
U3 — Pluggable local model synthesis boundary.

Implementations may only rewrite ``answer_text`` when the orchestrator passes a response
that already has governed citations; they must not invent citations, refusals, or hooks.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from structural_tree_app.domain.local_assist_contract import LocalAssistQuery, LocalAssistResponse


@runtime_checkable
class LocalModelSynthesisPort(Protocol):
    """Adapter for a local runtime (stub, Ollama, etc.)."""

    def synthesize_answer(self, query: LocalAssistQuery, base: LocalAssistResponse) -> str | None:
        """
        Return replacement ``answer_text`` or ``None`` to keep retrieval-only assembly.

        Must return ``None`` when synthesis is not applicable or runtime fails.
        """


class StubLocalModelSynthesizer:
    """
    Deterministic U3 stand-in — formats retrieved citation snippets only.

    Does not call external models; proves wiring and keeps tests hermetic.
    """

    PREFIX = (
        "[U3 stub — bounded local restatement from retrieved passages only; "
        "not a merged engineering conclusion or normative interpretation]\n\n"
    )

    def synthesize_answer(self, query: LocalAssistQuery, base: LocalAssistResponse) -> str | None:
        if base.answer_status != "evidence_passages_assembled":
            return None
        if base.refusal_reasons:
            return None
        if not base.citations:
            return None
        lines = [
            self.PREFIX + f"Retrieval query (lexical): {query.retrieval_query_text.strip()!r}\n",
            "Passages (see citation rows below for authority and identifiers):",
        ]
        for i, c in enumerate(base.citations[:50], 1):
            snip = c.snippet.replace("\n", " ")
            if len(snip) > 500:
                snip = snip[:500] + "…"
            lines.append(f"{i}. [{c.document_title}] ({c.citation_id}): {snip}")
        return "\n".join(lines)


class UnavailableLocalModelSynthesizer:
    """Always declines — exercises graceful fallback to retrieval-only ``answer_text``."""

    def synthesize_answer(self, query: LocalAssistQuery, base: LocalAssistResponse) -> str | None:
        return None


def synthesis_adapter_for_provider(provider: str) -> LocalModelSynthesisPort:
    if provider == "unavailable":
        return UnavailableLocalModelSynthesizer()
    return StubLocalModelSynthesizer()


__all__ = [
    "LocalModelSynthesisPort",
    "StubLocalModelSynthesizer",
    "UnavailableLocalModelSynthesizer",
    "synthesis_adapter_for_provider",
]
