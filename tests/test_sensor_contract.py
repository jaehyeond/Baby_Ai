from __future__ import annotations

import json
import math

import pytest

from neural.baby.sensor_contract import (
    SCHEMA_VERSION,
    ContractError,
    audit_records,
    compare_poses,
    validate_pose,
)
from scripts.research.sensor_contract_audit import main


def _provenance(source: str = "synthetic_test_fixture") -> dict[str, str]:
    return {"source": source, "producer": "tests/test_sensor_contract.py"}


def _pose(x: float = 0.0, quaternion: list[float] | None = None) -> dict:
    return {
        "position_m": [x, 0.0, 0.0],
        "orientation_xyzw": quaternion or [0.0, 0.0, 0.0, 1.0],
    }


def _record(record_type: str, record_id: str, **values: object) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "record_type": record_type,
        "record_id": record_id,
        "device_id": "device-test",
        "session_id": "session-test",
        "provenance": _provenance(),
        **values,
    }


def _valid_stream(
    *, actor: str = "bibi", depth_provenance: str = "measured"
) -> list[dict]:
    depth = (
        {"provenance": "missing", "bins": None}
        if depth_provenance == "missing"
        else {
            "provenance": depth_provenance,
            "method": "fixture_depth_sensor" if depth_provenance == "measured" else "fixture_screen_region",
            "units": "normalized_fraction",
            "bins": [0.2, 0.3, 0.5],
        }
    )
    action = _record(
        "action",
        "record-action-0",
        recorded_at="2026-09-12T00:00:00.120Z",
        action_id="action-0",
        actor=actor,
        source_observation_id="observation-0",
        motion={
            "coordinate_frame": "quest-stage",
            "translation_m": [0.1, 0.0, 0.0],
            "rotation_vector_rad": [0.0, 0.0, 0.0],
        },
    )
    if actor == "bibi":
        action["policy_decision_id"] = "policy-decision-0"
    return [
        _record("session_start", "record-start", recorded_at="2026-09-12T00:00:00.000Z"),
        _record(
            "observation",
            "record-observation-0",
            observation_id="observation-0",
            frame_id="frame-0",
            frame_index=0,
            captured_at="2026-09-12T00:00:00.100Z",
            received_at="2026-09-12T00:00:00.110Z",
            coordinate_frame="quest-stage",
            pose=_pose(),
            depth=depth,
        ),
        action,
        _record(
            "prediction",
            "record-prediction-0",
            recorded_at="2026-09-12T00:00:00.130Z",
            prediction_id="prediction-0",
            action_id="action-0",
            based_on_observation_id="observation-0",
            expected={"concepts_present": ["fixture-object"]},
        ),
        _record(
            "observation",
            "record-observation-1",
            observation_id="observation-1",
            frame_id="frame-1",
            frame_index=1,
            captured_at="2026-09-12T00:00:00.200Z",
            received_at="2026-09-12T00:00:00.210Z",
            coordinate_frame="quest-stage",
            pose=_pose(0.1),
            depth=depth,
        ),
        _record(
            "outcome",
            "record-outcome-0",
            recorded_at="2026-09-12T00:00:00.220Z",
            outcome_id="outcome-0",
            action_id="action-0",
            prediction_id="prediction-0",
            observation_id="observation-1",
        ),
        _record("session_end", "record-end", recorded_at="2026-09-12T00:00:00.300Z"),
    ]


def test_valid_bibi_chain_is_accepted_and_uses_separate_motion_units() -> None:
    result = audit_records(_valid_stream())

    assert result["record_validity_gate"] is True
    assert result["accepted_record_count"] == 7
    assert result["rejected_record_count"] == 0
    assert result["insufficient_evidence_count"] == 0
    assert result["complete_action_outcome_chain_count"] == 1
    assert result["bibi_agency_chain_count"] == 1
    assert result["bibi_agency_evidence_gate"] is True
    action_comparison = next(item for item in result["motion_comparisons"] if "action_id" in item)
    assert action_comparison["translation_m"] == pytest.approx(0.1)
    assert action_comparison["rotation_rad"] == pytest.approx(0.0)
    assert action_comparison["translation_error_m"] == pytest.approx(0.0)
    assert action_comparison["rotation_error_rad"] == pytest.approx(0.0)


@pytest.mark.parametrize("actor", ["human", "scripted"])
def test_non_bibi_actor_stays_valid_without_becoming_bibi_agency(actor: str) -> None:
    result = audit_records(_valid_stream(actor=actor))

    assert result["record_validity_gate"] is True
    assert result["complete_action_outcome_chain_count"] == 1
    assert result["bibi_agency_chain_count"] == 0
    assert result["bibi_agency_evidence_gate"] is False
    assert {item["reason"] for item in result["insufficient_evidence_reasons"]} == {
        f"agency.actor_{actor}",
        "agency.bibi_chain_missing",
    }


@pytest.mark.parametrize(
    ("provenance", "reason"),
    [("heuristic", "depth.heuristic_not_measured"), ("missing", "depth.missing")],
)
def test_depth_provenance_is_valid_but_limits_evidence(provenance: str, reason: str) -> None:
    result = audit_records(_valid_stream(depth_provenance=provenance))

    assert result["record_validity_gate"] is True
    assert {item["reason"] for item in result["insufficient_evidence_reasons"]} == {reason}


def test_pose_comparison_is_invariant_to_quaternion_sign() -> None:
    first = _pose(quaternion=[0.0, 0.0, 0.0, 1.0])
    equivalent = _pose(quaternion=[0.0, 0.0, 0.0, -1.0])

    assert compare_poses(first, equivalent) == {"translation_m": 0.0, "rotation_rad": 0.0}


def test_pose_validation_rejects_nonfinite_and_non_normalized_values() -> None:
    invalid = _pose(quaternion=[0.0, 0.0, 0.0, 2.0])
    invalid["position_m"][0] = math.inf

    assert validate_pose(invalid) == [
        "pose.position_m.finite_numbers_required",
        "pose.orientation_xyzw.normalized_required",
    ]
    with pytest.raises(ContractError):
        compare_poses(_pose(), invalid)


def test_duplicate_and_out_of_order_frames_are_rejected() -> None:
    records = _valid_stream()
    records[4]["frame_id"] = "frame-0"
    records[4]["frame_index"] = 0

    result = audit_records(records)

    outcome = next(item for item in result["rejected_records"] if item["record_id"] == "record-observation-1")
    assert "frame_id.duplicate_in_session" in outcome["reasons"]
    assert "frame_index.not_strictly_increasing" in outcome["reasons"]
    assert result["record_validity_gate"] is False


def test_prediction_must_precede_a_distinct_observed_outcome() -> None:
    records = _valid_stream()
    records[3]["recorded_at"] = "2026-09-12T00:00:00.205Z"

    result = audit_records(records)

    outcome = next(item for item in result["rejected_records"] if item["record_id"] == "record-outcome-0")
    assert "outcome.prediction_not_before_observation" in outcome["reasons"]
    assert result["complete_action_outcome_chain_count"] == 0


def test_links_cannot_cross_device_or_session() -> None:
    records = _valid_stream()
    records[5]["session_id"] = "other-session"

    result = audit_records(records)

    outcome = next(item for item in result["rejected_records"] if item["record_id"] == "record-outcome-0")
    assert "outcome.device_or_session_mismatch" in outcome["reasons"]


def test_motion_and_pose_coordinate_frames_must_match() -> None:
    records = _valid_stream()
    records[2]["motion"]["coordinate_frame"] = "other-frame"

    result = audit_records(records)

    action = next(item for item in result["rejected_records"] if item["record_id"] == "record-action-0")
    assert "action.coordinate_frame_mismatch" in action["reasons"]


def test_translation_error_preserves_direction() -> None:
    records = _valid_stream()
    records[4]["pose"] = _pose(-0.1)

    result = audit_records(records)

    comparison = next(item for item in result["motion_comparisons"] if "action_id" in item)
    assert comparison["translation_m"] == pytest.approx(0.1)
    assert comparison["translation_vector_m"] == pytest.approx([-0.1, 0.0, 0.0])
    assert comparison["translation_error_m"] == pytest.approx(0.2)


def test_rotation_error_distinguishes_axis_with_equal_angle() -> None:
    records = _valid_stream()
    half_sqrt = math.sqrt(0.5)
    records[2]["motion"]["rotation_vector_rad"] = [math.pi / 2.0, 0.0, 0.0]
    records[4]["pose"] = _pose(0.1, [0.0, half_sqrt, 0.0, half_sqrt])

    result = audit_records(records)

    comparison = next(item for item in result["motion_comparisons"] if "action_id" in item)
    assert comparison["rotation_rad"] == pytest.approx(math.pi / 2.0)
    assert comparison["rotation_error_rad"] == pytest.approx(2.0 * math.pi / 3.0)


def test_consecutive_pose_comparison_skips_changed_coordinate_frame() -> None:
    records = _valid_stream()
    records[4]["coordinate_frame"] = "other-stage"

    result = audit_records(records)

    assert not any(
        comparison.get("from_observation_id") == "observation-0"
        and comparison.get("to_observation_id") == "observation-1"
        for comparison in result["motion_comparisons"]
    )
    assert "pose.coordinate_frame_change_unresolved" in {
        item["reason"] for item in result["insufficient_evidence_reasons"]
    }


def test_missing_session_boundaries_are_evidence_insufficiencies() -> None:
    result = audit_records(_valid_stream()[1:-1])

    assert result["record_validity_gate"] is True
    assert {item["reason"] for item in result["insufficient_evidence_reasons"]} >= {
        "session_boundary.start_missing",
        "session_boundary.end_missing",
    }


def test_cli_reads_jsonl_and_emits_deterministic_report(tmp_path, capsys) -> None:
    capture = tmp_path / "capture.jsonl"
    capture.write_text(
        "\n".join(json.dumps(record, sort_keys=True) for record in _valid_stream()) + "\n",
        encoding="utf-8",
    )

    assert main([str(capture), "--require-bibi-agency"]) == 0
    first = capsys.readouterr().out
    assert main([str(capture), "--require-bibi-agency"]) == 0
    second = capsys.readouterr().out
    assert first == second
    assert json.loads(first)["accepted_record_count"] == 7
