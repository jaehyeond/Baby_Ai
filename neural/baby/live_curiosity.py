"""Learning-progress signals for the live Baby Brain curiosity loop.

Raw prediction error (surprise) is kept as an observation only.  The signal
that may affect consolidation or curiosity is the reduction in an
exponential moving average of that error.  This prevents permanently noisy
inputs from receiving priority simply because they remain unpredictable.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional


@dataclass(frozen=True)
class ProgressUpdate:
    """One scope's updated prediction-error state."""

    error_ema: float
    learning_progress: float
    observations: int


def _bounded(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, float(value)))


def compute_prediction_error(
    predicted_ids: Iterable[str],
    actual_ids: Iterable[str],
    cue_ids: Iterable[str] = (),
) -> Optional[float]:
    """Return ``1 - recall`` for non-cue concepts observed in one turn.

    ``None`` means that the turn supplied no outcome beyond its cue concepts,
    so it cannot honestly update the predictor.  An empty prediction against
    a non-empty outcome is a full error (1.0).
    """

    cues = {item for item in cue_ids if item}
    actual = {item for item in actual_ids if item} - cues
    if not actual:
        return None

    predicted = {item for item in predicted_ids if item} - cues
    hits = len(predicted & actual)
    return _bounded(1.0 - hits / len(actual))


def update_learning_progress(
    error: float,
    previous_error_ema: Optional[float],
    previous_observations: int,
    *,
    alpha: float = 0.4,
) -> ProgressUpdate:
    """Update error EMA and return only positive error reduction as progress."""

    error = _bounded(error)
    alpha = _bounded(alpha)
    previous_observations = max(0, int(previous_observations))

    if previous_error_ema is None or previous_observations == 0:
        return ProgressUpdate(error_ema=error, learning_progress=0.0, observations=1)

    previous = _bounded(previous_error_ema)
    current = (1.0 - alpha) * previous + alpha * error
    progress = max(0.0, previous - current)
    return ProgressUpdate(
        error_ema=round(_bounded(current), 6),
        learning_progress=round(_bounded(progress), 6),
        observations=previous_observations + 1,
    )


def compute_integration_priority(
    emotional_salience: float,
    learning_progress: float,
    *,
    progress_weight: float = 0.4,
) -> float:
    """Extend emotional salience with progress, never with raw surprise."""

    base = _bounded(emotional_salience)
    progress = _bounded(learning_progress)
    return round(_bounded(base + progress_weight * progress), 6)


def should_open_curiosity_gate(
    learning_progress: float,
    observations: int,
    *,
    threshold: float = 0.02,
    min_observations: int = 3,
) -> bool:
    """Require repeated evidence and meaningful progress before acting."""

    return int(observations) >= min_observations and float(learning_progress) >= threshold


def select_curiosity_target(
    cue_ids: Iterable[str],
    predicted_ids: Iterable[str],
    actual_ids: Iterable[str],
) -> Optional[str]:
    """Prefer a correctly predicted tractable target, then a missed outcome."""

    cues = {item for item in cue_ids if item}
    actual = [item for item in actual_ids if item and item not in cues]
    if not actual:
        return None

    actual_set = set(actual)
    for predicted in predicted_ids:
        if predicted in actual_set:
            return predicted
    return actual[0]
