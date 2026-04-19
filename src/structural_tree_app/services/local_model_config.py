"""U3 — runtime configuration for optional local model synthesis (bounded; subordinate to retrieval)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal

ENV_LOCAL_MODEL_ENABLED = "STRUCTURAL_LOCAL_MODEL_ENABLED"
ENV_LOCAL_MODEL_PROVIDER = "STRUCTURAL_LOCAL_MODEL_PROVIDER"

LocalModelProviderId = Literal["stub", "unavailable"]


@dataclass(frozen=True)
class LocalModelRuntimeConfig:
    """
    Global enablement for U3 synthesis. Per-request opt-in still required via
    ``LocalAssistQuery.request_local_model_synthesis``.
    """

    enabled: bool
    """When False, orchestrator never calls synthesis (R1 behavior)."""

    provider: LocalModelProviderId
    """``stub`` = deterministic formatter; ``unavailable`` = always fallback (tests / placeholder)."""


def _truthy(raw: str | None) -> bool:
    if raw is None:
        return False
    return raw.strip().lower() in ("1", "true", "yes", "on")


def load_local_model_runtime_config() -> LocalModelRuntimeConfig:
    """Load from environment (local-first; no network)."""
    enabled = _truthy(os.environ.get(ENV_LOCAL_MODEL_ENABLED))
    prov_raw = (os.environ.get(ENV_LOCAL_MODEL_PROVIDER) or "stub").strip().lower()
    if prov_raw not in ("stub", "unavailable"):
        prov_raw = "stub"
    return LocalModelRuntimeConfig(enabled=enabled, provider=prov_raw)  # type: ignore[arg-type]


__all__ = [
    "ENV_LOCAL_MODEL_ENABLED",
    "ENV_LOCAL_MODEL_PROVIDER",
    "LocalModelProviderId",
    "LocalModelRuntimeConfig",
    "load_local_model_runtime_config",
]
