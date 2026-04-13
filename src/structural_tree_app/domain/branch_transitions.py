from __future__ import annotations

from structural_tree_app.domain.enums import BranchState


# Explicit allowed transitions (from, to); identity transitions always allowed.
_ALLOWED: set[tuple[BranchState, BranchState]] = {
    (BranchState.PENDING, BranchState.ACTIVE),
    (BranchState.ACTIVE, BranchState.DISCARDED),
    (BranchState.ACTIVE, BranchState.EXPLORED),
    (BranchState.ACTIVE, BranchState.FAILED),
    (BranchState.ACTIVE, BranchState.APPROVED),
    (BranchState.ACTIVE, BranchState.ARCHIVED),
    (BranchState.FAILED, BranchState.ACTIVE),
    (BranchState.EXPLORED, BranchState.ACTIVE),
    (BranchState.APPROVED, BranchState.ARCHIVED),
    (BranchState.PENDING, BranchState.DISCARDED),
}


class BranchTransitionError(ValueError):
    """Raised when a branch state change is not permitted."""


def assert_branch_transition(current: BranchState, new: BranchState) -> None:
    if current == new:
        return
    if (current, new) not in _ALLOWED:
        raise BranchTransitionError(
            f"Invalid branch transition {current.value!r} -> {new.value!r}"
        )


__all__ = ["BranchTransitionError", "assert_branch_transition"]
