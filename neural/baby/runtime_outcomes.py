"""Truthful execution/evaluation states for unavailable runtime actions."""

from __future__ import annotations

from typing import Any


def outcome_state(
    *,
    executed: bool,
    result_available: bool,
    verified: bool = False,
    correct: bool | None = None,
    reward: float | None = None,
) -> dict[str, Any]:
    """Keep execution, result availability, and evaluation independent."""
    if verified and (not executed or not result_available or correct is None):
        raise ValueError("verified outcomes require execution, a result, and correctness")
    return {
        "execution": {
            "status": "executed" if executed else "not_executed",
            "executed": executed,
        },
        "result": {
            "status": "available" if result_available else "unavailable",
            "available": result_available,
        },
        "evaluation": {
            "status": "evaluated" if verified else "not_evaluated",
            "verified": verified,
            "correct": correct if verified else None,
            "reward": reward if verified else None,
        },
    }


def awaiting_evidence_response(action: str, **shape: Any) -> dict[str, Any]:
    """Return a stable no-write response for an unavailable action."""
    return {
        "success": False,
        "action": action,
        "status": "awaiting_evidence",
        **outcome_state(executed=False, result_available=False),
        "persisted": False,
        "provenance": {
            "source": "runtime_contract",
            "evidence_id": None,
            "reason": "No implemented executor and no observed outcome evidence",
        },
        **shape,
    }
