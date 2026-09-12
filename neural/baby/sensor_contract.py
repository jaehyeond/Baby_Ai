"""Strict, offline sensor/action/outcome contract for W6 capture audits.

This module has no database or service dependencies.  The legacy Quest endpoint
remains permissive; callers opt into this versioned contract by validating a
captured JSON/JSONL stream with :func:`audit_records`.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
import math
from typing import Any, Iterable, Mapping, Sequence


SCHEMA_VERSION = "bibi.sensor-action-outcome/v1"
RECORD_TYPES = {
    "session_start",
    "observation",
    "action",
    "prediction",
    "outcome",
    "session_end",
}
ACTORS = {"human", "scripted", "bibi"}
DEPTH_PROVENANCE = {"measured", "heuristic", "missing"}
QUATERNION_NORM_TOLERANCE = 1e-3


class ContractError(ValueError):
    """Raised when a pose cannot be compared under the strict contract."""


def _is_nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _parse_timestamp(value: Any) -> datetime | None:
    if not _is_nonempty_string(value):
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed


def _require_string(record: Mapping[str, Any], field: str, errors: list[str]) -> None:
    if not _is_nonempty_string(record.get(field)):
        errors.append(f"{field}.required_string")


def _require_timestamp(record: Mapping[str, Any], field: str, errors: list[str]) -> datetime | None:
    parsed = _parse_timestamp(record.get(field))
    if parsed is None:
        errors.append(f"{field}.timezone_timestamp_required")
    return parsed


def _validate_vector(value: Any, length: int, field: str, errors: list[str]) -> list[float] | None:
    if not isinstance(value, list) or len(value) != length:
        errors.append(f"{field}.length_{length}_required")
        return None
    if not all(_is_finite_number(item) for item in value):
        errors.append(f"{field}.finite_numbers_required")
        return None
    return [float(item) for item in value]


def _validate_provenance(record: Mapping[str, Any], errors: list[str]) -> None:
    provenance = record.get("provenance")
    if not isinstance(provenance, Mapping):
        errors.append("provenance.object_required")
        return
    for field in ("source", "producer"):
        if not _is_nonempty_string(provenance.get(field)):
            errors.append(f"provenance.{field}.required_string")


def validate_pose(pose: Any, field: str = "pose") -> list[str]:
    """Return deterministic validation reasons for a metric position + xyzw pose."""

    errors: list[str] = []
    if not isinstance(pose, Mapping):
        return [f"{field}.object_required"]
    _validate_vector(pose.get("position_m"), 3, f"{field}.position_m", errors)
    quaternion = _validate_vector(
        pose.get("orientation_xyzw"), 4, f"{field}.orientation_xyzw", errors
    )
    if quaternion is not None:
        norm = math.sqrt(sum(component * component for component in quaternion))
        if abs(norm - 1.0) > QUATERNION_NORM_TOLERANCE:
            errors.append(f"{field}.orientation_xyzw.normalized_required")
    return errors


def _translation_vector(
    previous: Mapping[str, Any], current: Mapping[str, Any]
) -> list[float]:
    return [
        float(after) - float(before)
        for before, after in zip(previous["position_m"], current["position_m"])
    ]


def _quaternion_conjugate(quaternion: Sequence[float]) -> list[float]:
    x, y, z, w = quaternion
    return [-x, -y, -z, w]


def _quaternion_multiply(left: Sequence[float], right: Sequence[float]) -> list[float]:
    lx, ly, lz, lw = left
    rx, ry, rz, rw = right
    return [
        lw * rx + lx * rw + ly * rz - lz * ry,
        lw * ry - lx * rz + ly * rw + lz * rx,
        lw * rz + lx * ry - ly * rx + lz * rw,
        lw * rw - lx * rx - ly * ry - lz * rz,
    ]


def _relative_quaternion(previous: Mapping[str, Any], current: Mapping[str, Any]) -> list[float]:
    """Return stage-frame rotation from previous orientation to current orientation."""

    previous_quaternion = [float(value) for value in previous["orientation_xyzw"]]
    current_quaternion = [float(value) for value in current["orientation_xyzw"]]
    return _quaternion_multiply(
        current_quaternion, _quaternion_conjugate(previous_quaternion)
    )


def _rotation_vector_to_quaternion(rotation_vector_rad: Sequence[Any]) -> list[float]:
    vector = [float(value) for value in rotation_vector_rad]
    angle = _norm(vector)
    if angle == 0.0:
        return [0.0, 0.0, 0.0, 1.0]
    scale = math.sin(angle / 2.0) / angle
    return [vector[0] * scale, vector[1] * scale, vector[2] * scale, math.cos(angle / 2.0)]


def _quaternion_distance(left: Sequence[float], right: Sequence[float]) -> float:
    """Return shortest geodesic angle, invariant to either quaternion's sign."""

    dot = abs(sum(a * b for a, b in zip(left, right)))
    return 2.0 * math.acos(max(-1.0, min(1.0, dot)))


def compare_poses(previous: Mapping[str, Any], current: Mapping[str, Any]) -> dict[str, float]:
    """Compare two valid poses without mixing translation and rotation units.

    Rotation is the shortest relative angle in radians.  The absolute quaternion
    dot product makes the result invariant to the equivalent ``q`` and ``-q``
    representations.
    """

    errors = validate_pose(previous, "previous_pose") + validate_pose(current, "current_pose")
    if errors:
        raise ContractError(", ".join(errors))

    translation_m = _norm(_translation_vector(previous, current))
    rotation_rad = _quaternion_distance(
        _relative_quaternion(previous, current), [0.0, 0.0, 0.0, 1.0]
    )
    return {"translation_m": translation_m, "rotation_rad": rotation_rad}


def _validate_depth(record: Mapping[str, Any], errors: list[str]) -> None:
    depth = record.get("depth")
    if not isinstance(depth, Mapping):
        errors.append("depth.object_required")
        return
    provenance = depth.get("provenance")
    if provenance not in DEPTH_PROVENANCE:
        errors.append("depth.provenance.invalid")
        return
    bins = depth.get("bins")
    method = depth.get("method")
    units = depth.get("units")
    if provenance == "missing":
        if bins is not None:
            errors.append("depth.missing_must_not_have_bins")
        return
    if not _is_nonempty_string(method):
        errors.append("depth.method.required_string")
    if units != "normalized_fraction":
        errors.append("depth.units.normalized_fraction_required")
    if not isinstance(bins, list) or not 3 <= len(bins) <= 5:
        errors.append("depth.bins.length_3_to_5_required")
        return
    if not all(_is_finite_number(value) and float(value) >= 0.0 for value in bins):
        errors.append("depth.bins.nonnegative_finite_required")
        return
    if abs(sum(float(value) for value in bins) - 1.0) > 1e-3:
        errors.append("depth.bins.normalized_required")


def validate_record(record: Any) -> list[str]:
    """Validate one record without considering links to other records."""

    if not isinstance(record, Mapping):
        return ["record.object_required"]
    errors: list[str] = []
    if record.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version.invalid")
    record_type = record.get("record_type")
    if record_type not in RECORD_TYPES:
        errors.append("record_type.invalid")
    for field in ("record_id", "device_id", "session_id"):
        _require_string(record, field, errors)
    _validate_provenance(record, errors)

    if record_type in {"session_start", "session_end", "action", "prediction", "outcome"}:
        _require_timestamp(record, "recorded_at", errors)

    if record_type == "observation":
        for field in ("observation_id", "frame_id", "coordinate_frame"):
            _require_string(record, field, errors)
        frame_index = record.get("frame_index")
        if not _is_int(frame_index) or frame_index < 0:
            errors.append("frame_index.nonnegative_integer_required")
        captured_at = _require_timestamp(record, "captured_at", errors)
        received_at = _require_timestamp(record, "received_at", errors)
        if captured_at is not None and received_at is not None and captured_at > received_at:
            errors.append("observation.capture_after_receive")
        errors.extend(validate_pose(record.get("pose")))
        _validate_depth(record, errors)

    elif record_type == "action":
        for field in ("action_id", "source_observation_id"):
            _require_string(record, field, errors)
        actor = record.get("actor")
        if actor not in ACTORS:
            errors.append("actor.invalid")
        if actor == "bibi" and not _is_nonempty_string(record.get("policy_decision_id")):
            errors.append("policy_decision_id.required_for_bibi")
        motion = record.get("motion")
        if not isinstance(motion, Mapping):
            errors.append("motion.object_required")
        else:
            _require_string(motion, "coordinate_frame", errors)
            _validate_vector(motion.get("translation_m"), 3, "motion.translation_m", errors)
            rotation_vector = _validate_vector(
                motion.get("rotation_vector_rad"),
                3,
                "motion.rotation_vector_rad",
                errors,
            )
            if rotation_vector is not None and _norm(rotation_vector) > math.pi + 1e-9:
                errors.append("motion.rotation_vector_rad.shortest_axis_angle_required")

    elif record_type == "prediction":
        for field in ("prediction_id", "action_id", "based_on_observation_id"):
            _require_string(record, field, errors)
        expected = record.get("expected")
        if not isinstance(expected, Mapping) or not expected:
            errors.append("expected.nonempty_object_required")

    elif record_type == "outcome":
        for field in ("outcome_id", "action_id", "prediction_id", "observation_id"):
            _require_string(record, field, errors)

    return sorted(set(errors))


def _record_time(record: Mapping[str, Any]) -> datetime | None:
    field = "captured_at" if record.get("record_type") == "observation" else "recorded_at"
    return _parse_timestamp(record.get(field))


def _norm(vector: Sequence[Any]) -> float:
    return math.sqrt(sum(float(value) ** 2 for value in vector))


def audit_records(records: Iterable[Any]) -> dict[str, Any]:
    """Audit an ordered strict-capture stream without external effects.

    Invalid records are rejected.  Evidence limitations are reported separately
    and never turn a valid human/scripted observation into a Bibi agency claim.
    """

    items = list(records)
    errors_by_index: dict[int, set[str]] = {
        index: set(validate_record(record)) for index, record in enumerate(items)
    }
    intrinsically_valid = {index: not reasons for index, reasons in errors_by_index.items()}

    seen_record_ids: dict[str, int] = {}
    seen_frames: dict[tuple[str, str, str], int] = {}
    seen_observations: dict[str, int] = {}
    seen_actions: dict[str, int] = {}
    seen_predictions: dict[str, int] = {}
    seen_outcomes: dict[str, int] = {}
    sessions: dict[tuple[str, str], list[int]] = defaultdict(list)

    def register_unique(index: int, key: Any, seen: dict[Any, int], reason: str) -> None:
        if key in seen:
            errors_by_index[index].add(reason)
        else:
            seen[key] = index

    for index, item in enumerate(items):
        if not isinstance(item, Mapping):
            continue
        record_id = item.get("record_id")
        if _is_nonempty_string(record_id):
            register_unique(index, record_id, seen_record_ids, "record_id.duplicate")
        device_id = item.get("device_id")
        session_id = item.get("session_id")
        if _is_nonempty_string(device_id) and _is_nonempty_string(session_id):
            sessions[(device_id, session_id)].append(index)
        record_type = item.get("record_type")
        if record_type == "observation":
            observation_id = item.get("observation_id")
            frame_id = item.get("frame_id")
            if _is_nonempty_string(observation_id):
                register_unique(index, observation_id, seen_observations, "observation_id.duplicate")
            if all(_is_nonempty_string(v) for v in (device_id, session_id, frame_id)):
                register_unique(
                    index,
                    (device_id, session_id, frame_id),
                    seen_frames,
                    "frame_id.duplicate_in_session",
                )
        elif record_type == "action" and _is_nonempty_string(item.get("action_id")):
            register_unique(index, item["action_id"], seen_actions, "action_id.duplicate")
        elif record_type == "prediction" and _is_nonempty_string(item.get("prediction_id")):
            register_unique(index, item["prediction_id"], seen_predictions, "prediction_id.duplicate")
        elif record_type == "outcome" and _is_nonempty_string(item.get("outcome_id")):
            register_unique(index, item["outcome_id"], seen_outcomes, "outcome_id.duplicate")

    insufficiencies: Counter[str] = Counter()
    motion_comparisons: list[dict[str, Any]] = []
    complete_chains = 0
    bibi_agency_chains = 0

    for session_key, indexes in sorted(sessions.items()):
        session_items = [(index, items[index]) for index in indexes if isinstance(items[index], Mapping)]
        starts = [index for index, item in session_items if item.get("record_type") == "session_start"]
        ends = [index for index, item in session_items if item.get("record_type") == "session_end"]
        if not starts:
            insufficiencies["session_boundary.start_missing"] += 1
        if not ends:
            insufficiencies["session_boundary.end_missing"] += 1
        for duplicate_start in starts[1:]:
            errors_by_index[duplicate_start].add("session_boundary.duplicate_start")
        for duplicate_end in ends[1:]:
            errors_by_index[duplicate_end].add("session_boundary.duplicate_end")
        if starts and starts[0] != indexes[0]:
            errors_by_index[starts[0]].add("session_boundary.start_not_first")
        if ends and ends[0] != indexes[-1]:
            errors_by_index[ends[0]].add("session_boundary.end_not_last")
        if starts and ends:
            start_time = _record_time(items[starts[0]])
            end_time = _record_time(items[ends[0]])
            if start_time is not None and end_time is not None and start_time >= end_time:
                errors_by_index[ends[0]].add("session_boundary.nonpositive_duration")
            elif start_time is not None and end_time is not None:
                for event_index, event in session_items:
                    if event_index in {starts[0], ends[0]}:
                        continue
                    event_time = _record_time(event)
                    if event_time is not None and not start_time < event_time < end_time:
                        errors_by_index[event_index].add("session_boundary.record_outside_interval")

        observations = [
            (index, item)
            for index, item in session_items
            if item.get("record_type") == "observation" and intrinsically_valid[index]
        ]
        previous_index: int | None = None
        previous_capture: datetime | None = None
        previous_observation: Mapping[str, Any] | None = None
        for index, observation in observations:
            frame_index = observation.get("frame_index")
            captured_at = _parse_timestamp(observation.get("captured_at"))
            if previous_index is not None and _is_int(frame_index):
                if frame_index <= previous_index:
                    errors_by_index[index].add("frame_index.not_strictly_increasing")
                elif frame_index > previous_index + 1:
                    insufficiencies["frame_index.gap"] += frame_index - previous_index - 1
            if previous_capture is not None and captured_at is not None and captured_at <= previous_capture:
                errors_by_index[index].add("captured_at.not_strictly_increasing")
            if previous_observation is not None and not errors_by_index[index]:
                if previous_observation["coordinate_frame"] != observation["coordinate_frame"]:
                    insufficiencies["pose.coordinate_frame_change_unresolved"] += 1
                else:
                    delta = compare_poses(previous_observation["pose"], observation["pose"])
                    motion_comparisons.append(
                        {
                            "from_observation_id": previous_observation["observation_id"],
                            "to_observation_id": observation["observation_id"],
                            "coordinate_frame": observation["coordinate_frame"],
                            **delta,
                        }
                    )
            if not errors_by_index[index]:
                previous_index = frame_index
                previous_capture = captured_at
                previous_observation = observation
            depth = observation.get("depth")
            if isinstance(depth, Mapping):
                if depth.get("provenance") == "missing":
                    insufficiencies["depth.missing"] += 1
                elif depth.get("provenance") == "heuristic":
                    insufficiencies["depth.heuristic_not_measured"] += 1

    # Lookups include only records that remain structurally valid at this point.
    def lookup(seen: Mapping[str, int], key: Any) -> tuple[int, Mapping[str, Any]] | None:
        index = seen.get(key) if _is_nonempty_string(key) else None
        if index is None or errors_by_index[index] or not isinstance(items[index], Mapping):
            return None
        return index, items[index]

    for index, item in enumerate(items):
        if not isinstance(item, Mapping) or errors_by_index[index]:
            continue
        record_type = item.get("record_type")
        session_key = (item.get("device_id"), item.get("session_id"))
        if record_type == "action":
            source = lookup(seen_observations, item.get("source_observation_id"))
            if source is None:
                errors_by_index[index].add("action.source_observation_missing_or_invalid")
            else:
                source_index, source_record = source
                if (source_record.get("device_id"), source_record.get("session_id")) != session_key:
                    errors_by_index[index].add("action.source_observation_session_mismatch")
                if source_record.get("coordinate_frame") != item["motion"].get("coordinate_frame"):
                    errors_by_index[index].add("action.coordinate_frame_mismatch")
                if source_index >= index or _record_time(source_record) >= _record_time(item):
                    errors_by_index[index].add("action.not_after_source_observation")

        elif record_type == "prediction":
            action = lookup(seen_actions, item.get("action_id"))
            source = lookup(seen_observations, item.get("based_on_observation_id"))
            if action is None:
                errors_by_index[index].add("prediction.action_missing_or_invalid")
            if source is None:
                errors_by_index[index].add("prediction.based_on_observation_missing_or_invalid")
            if action is not None and source is not None:
                action_index, action_record = action
                _, source_record = source
                if (action_record.get("device_id"), action_record.get("session_id")) != session_key:
                    errors_by_index[index].add("prediction.action_session_mismatch")
                if (source_record.get("device_id"), source_record.get("session_id")) != session_key:
                    errors_by_index[index].add("prediction.observation_session_mismatch")
                if action_record.get("source_observation_id") != item.get("based_on_observation_id"):
                    errors_by_index[index].add("prediction.source_observation_mismatch")
                if action_index >= index or _record_time(action_record) > _record_time(item):
                    errors_by_index[index].add("prediction.not_after_action")

        elif record_type == "outcome":
            action = lookup(seen_actions, item.get("action_id"))
            prediction = lookup(seen_predictions, item.get("prediction_id"))
            observation = lookup(seen_observations, item.get("observation_id"))
            if action is None:
                errors_by_index[index].add("outcome.action_missing_or_invalid")
            if prediction is None:
                errors_by_index[index].add("outcome.prediction_missing_or_invalid")
            if observation is None:
                errors_by_index[index].add("outcome.observation_missing_or_invalid")
            if action is None or prediction is None or observation is None:
                continue
            _, action_record = action
            prediction_index, prediction_record = prediction
            observation_index, observation_record = observation
            linked_records = (action_record, prediction_record, observation_record)
            if any((r.get("device_id"), r.get("session_id")) != session_key for r in linked_records):
                errors_by_index[index].add("outcome.device_or_session_mismatch")
            if prediction_record.get("action_id") != item.get("action_id"):
                errors_by_index[index].add("outcome.prediction_action_mismatch")
            source = lookup(seen_observations, action_record.get("source_observation_id"))
            if source is None:
                errors_by_index[index].add("outcome.source_observation_missing_or_invalid")
                continue
            source_index, source_record = source
            if source_record.get("observation_id") == observation_record.get("observation_id"):
                errors_by_index[index].add("outcome.observation_must_differ_from_source")
            coordinate_frames = {
                source_record.get("coordinate_frame"),
                observation_record.get("coordinate_frame"),
                action_record["motion"].get("coordinate_frame"),
            }
            if len(coordinate_frames) != 1:
                errors_by_index[index].add("outcome.coordinate_frame_mismatch")
            prediction_time = _record_time(prediction_record)
            observation_time = _record_time(observation_record)
            outcome_time = _record_time(item)
            if prediction_index >= observation_index or prediction_time >= observation_time:
                errors_by_index[index].add("outcome.prediction_not_before_observation")
            if observation_index >= index or observation_time > outcome_time:
                errors_by_index[index].add("outcome.not_after_observation")
            if errors_by_index[index]:
                continue
            complete_chains += 1
            actor = action_record.get("actor")
            if actor == "bibi":
                bibi_agency_chains += 1
            else:
                insufficiencies[f"agency.actor_{actor}"] += 1
            actual = compare_poses(source_record["pose"], observation_record["pose"])
            actual_translation_vector = _translation_vector(
                source_record["pose"], observation_record["pose"]
            )
            commanded_translation_vector = [
                float(value) for value in action_record["motion"]["translation_m"]
            ]
            translation_residual = [
                observed - commanded
                for observed, commanded in zip(
                    actual_translation_vector, commanded_translation_vector
                )
            ]
            actual_relative_quaternion = _relative_quaternion(
                source_record["pose"], observation_record["pose"]
            )
            commanded_rotation_vector = [
                float(value)
                for value in action_record["motion"]["rotation_vector_rad"]
            ]
            commanded_relative_quaternion = _rotation_vector_to_quaternion(
                commanded_rotation_vector
            )
            motion_comparisons.append(
                {
                    "action_id": action_record["action_id"],
                    "outcome_id": item["outcome_id"],
                    "actor": actor,
                    "coordinate_frame": observation_record["coordinate_frame"],
                    "translation_vector_m": actual_translation_vector,
                    "commanded_translation_vector_m": commanded_translation_vector,
                    "translation_m": actual["translation_m"],
                    "rotation_rad": actual["rotation_rad"],
                    "commanded_rotation_vector_rad": commanded_rotation_vector,
                    "translation_error_m": _norm(translation_residual),
                    "rotation_error_rad": _quaternion_distance(
                        actual_relative_quaternion, commanded_relative_quaternion
                    ),
                }
            )

    if complete_chains == 0:
        insufficiencies["action_outcome.complete_chain_missing"] += 1
    if bibi_agency_chains == 0:
        insufficiencies["agency.bibi_chain_missing"] += 1

    rejected = []
    accepted = []
    rejection_counts: Counter[str] = Counter()
    for index, item in enumerate(items):
        record_id = item.get("record_id") if isinstance(item, Mapping) else None
        reasons = sorted(errors_by_index[index])
        if reasons:
            rejected.append({"index": index, "record_id": record_id, "reasons": reasons})
            rejection_counts.update(reasons)
        else:
            accepted.append({"index": index, "record_id": record_id})

    return {
        "schema_version": SCHEMA_VERSION,
        "input_record_count": len(items),
        "accepted_record_count": len(accepted),
        "rejected_record_count": len(rejected),
        "accepted_records": accepted,
        "rejected_records": rejected,
        "rejection_reasons": [
            {"reason": reason, "count": count} for reason, count in sorted(rejection_counts.items())
        ],
        "insufficient_evidence_count": sum(insufficiencies.values()),
        "insufficient_evidence_reasons": [
            {"reason": reason, "count": count} for reason, count in sorted(insufficiencies.items())
        ],
        "complete_action_outcome_chain_count": complete_chains,
        "bibi_agency_chain_count": bibi_agency_chains,
        "motion_comparisons": motion_comparisons,
        "record_validity_gate": not rejected,
        "bibi_agency_evidence_gate": (
            not rejected
            and bibi_agency_chains > 0
            and not any(reason.startswith("session_boundary.") for reason in insufficiencies)
        ),
    }
