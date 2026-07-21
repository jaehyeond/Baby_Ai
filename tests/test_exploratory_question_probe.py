import copy
import json
from pathlib import Path

import pytest

from neural.baby.exploratory_question_probe import (
    EXPLORATORY_CAPTURE_STATUS,
    EXPLORATORY_EVIDENCE_SCOPE,
    EXPLORATORY_MANIFEST_STATUS,
    EXPLORATORY_NEXT_STEP,
    EXPLORATORY_PHASE,
    build_exploratory_pre_answer_capture,
    validate_exploratory_pre_answer_capture,
    validate_exploratory_question_manifest,
)


CAPTURED_AT = "2026-07-21T08:00:00+00:00"
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _manifest() -> dict:
    return {
        "exploratory_question_manifest_version": 1,
        "phase": EXPLORATORY_PHASE,
        "status": EXPLORATORY_MANIFEST_STATUS,
        "manifest_id": "j1_exploratory_probe_test",
        "prepared_at": CAPTURED_AT,
        "purpose": "diagnose_prediction_signal_before_confirmatory_work",
        "evidence_scope": EXPLORATORY_EVIDENCE_SCOPE,
        "questions_public_before_raw_capture": True,
        "answers_available_before_capture": False,
        "confirmatory_reuse_allowed": False,
        "constraints": {
            "database_writes": False,
            "learning_enabled": False,
            "calibrator_fit": False,
            "probabilities_computed": False,
            "heldout_collection": False,
            "performance_claim": False,
            "production_promotion": False,
        },
        "question_count": 2,
        "questions": [
            {
                "order": 0,
                "question_id": "exp-00",
                "question": "카메라와 영화는 어떻게 이어져?",
                "cue_terms": ["카메라", "영화"],
            },
            {
                "order": 1,
                "question_id": "exp-01",
                "question": "도시와 날씨는 어떤 관계야?",
                "cue_terms": ["도시", "날씨"],
            },
        ],
    }


def _concepts() -> list[dict]:
    return [
        {"id": f"c{index:02d}", "name": f"개념{index:02d}"}
        for index in range(12)
    ]


def _scores(offset: float = 0.0) -> dict[int, list[dict]]:
    return {
        order: [
            {
                "concept_id": item["id"],
                "concept_name": item["name"],
                "raw_score": offset + index + (order / 10),
            }
            for index, item in enumerate(_concepts())
        ]
        for order in (0, 1)
    }


def _capture() -> dict:
    return build_exploratory_pre_answer_capture(
        _manifest(),
        _concepts(),
        _scores(),
        _scores(0.5),
        graph_predictor={
            "implementation_sha256": "a" * 64,
            "scoring_contract": "max_cue_edge_strength_full_vocabulary_v1",
        },
        local_core_predictor={
            "adapter_sha256": "b" * 64,
            "model_snapshot_sha256": "c" * 64,
            "trainable_parameter_count": 0,
            "device": "cuda:0",
        },
        captured_at=CAPTURED_AT,
    )


def test_manifest_is_explicitly_exploratory_and_unsealed():
    manifest = validate_exploratory_question_manifest(_manifest())
    assert manifest["questions_public_before_raw_capture"] is True
    assert manifest["answers_available_before_capture"] is False
    assert manifest["confirmatory_reuse_allowed"] is False
    assert "contract_sha256" not in manifest
    assert len(manifest["manifest_snapshot_sha256"]) == 64
    assert all(len(item["question_sha256"]) == 64 for item in manifest["questions"])


@pytest.mark.parametrize(
    "field",
    ["contract_sha256", "approval_recorded_at", "user_approval_scope"],
)
def test_manifest_rejects_confirmatory_sealing_fields(field):
    manifest = _manifest()
    manifest[field] = "x"
    with pytest.raises(ValueError, match="must not carry sealing fields"):
        validate_exploratory_question_manifest(manifest)


def test_manifest_requires_disclosure_that_questions_were_public():
    manifest = _manifest()
    manifest["questions_public_before_raw_capture"] = False
    with pytest.raises(ValueError, match="disclose public questions"):
        validate_exploratory_question_manifest(manifest)


def test_manifest_permanently_disallows_confirmatory_reuse():
    manifest = _manifest()
    manifest["confirmatory_reuse_allowed"] = True
    with pytest.raises(ValueError, match="cannot be reused"):
        validate_exploratory_question_manifest(manifest)


def test_capture_is_compact_but_binds_full_score_digests():
    capture = _capture()
    assert capture["status"] == EXPLORATORY_CAPTURE_STATUS
    assert capture["question_count"] == 2
    assert capture["exploratory_not_for_claim"] is True
    assert capture["confirmatory_reuse_allowed"] is False
    assert capture["performance_claim_gate"] is False
    assert capture["next_step"] == EXPLORATORY_NEXT_STEP
    for question in capture["questions"]:
        assert question["graph_full_score_count"] == 12
        assert question["local_core_full_score_count"] == 12
        assert len(question["graph_top_k"]) == 8
        assert len(question["local_core_top_k"]) == 8
        assert "graph_raw_scores" not in question
        assert "local_core_raw_scores" not in question


def test_capture_rejects_missing_question_scores():
    graph_scores = _scores()
    graph_scores.pop(1)
    with pytest.raises(ValueError, match="orders do not match"):
        build_exploratory_pre_answer_capture(
            _manifest(),
            _concepts(),
            graph_scores,
            _scores(),
            graph_predictor={"implementation_sha256": "a" * 64},
            local_core_predictor={
                "adapter_sha256": "b" * 64,
                "model_snapshot_sha256": "c" * 64,
                "trainable_parameter_count": 0,
            },
            captured_at=CAPTURED_AT,
        )


def test_capture_rejects_manifest_question_binding_drift():
    capture = _capture()
    changed_manifest = _manifest()
    changed_manifest["questions"][0]["question"] = "완전히 다른 질문이야?"
    with pytest.raises(ValueError, match="manifest binding mismatch"):
        validate_exploratory_pre_answer_capture(capture, changed_manifest)


def test_capture_rejects_question_id_tamper_even_when_order_matches():
    capture = copy.deepcopy(_capture())
    capture["questions"][0]["question_id"] = "different-id"
    capture.pop("exploratory_pre_answer_capture_sha256")
    from neural.baby.pending_question_semantics import canonical_json_sha256

    capture["exploratory_pre_answer_capture_sha256"] = canonical_json_sha256(capture)
    with pytest.raises(ValueError, match="question question_id mismatch"):
        validate_exploratory_pre_answer_capture(capture, _manifest())


def test_capture_rejects_performance_claim_gate_tamper():
    capture = copy.deepcopy(_capture())
    capture["performance_claim_gate"] = True
    with pytest.raises(ValueError, match="must remain false"):
        validate_exploratory_pre_answer_capture(capture, _manifest())


def test_capture_rejects_any_embedded_answer():
    capture = copy.deepcopy(_capture())
    capture["questions"][0]["answer"] = "사후 답변"
    with pytest.raises(ValueError, match="forbids field"):
        validate_exploratory_pre_answer_capture(capture, _manifest())


def test_capture_rejects_trainable_local_core():
    capture = copy.deepcopy(_capture())
    capture["local_core_predictor"]["trainable_parameter_count"] = 1
    with pytest.raises(ValueError, match="remain frozen"):
        validate_exploratory_pre_answer_capture(capture, _manifest())


def test_repository_exploratory_capture_validates():
    manifest_path = (
        PROJECT_ROOT
        / "scripts"
        / "research"
        / "manifests"
        / "j1_1_fresh_selection_b_20260720_draft.json"
    )
    capture_path = (
        PROJECT_ROOT
        / "scripts"
        / "research"
        / "inputs"
        / "j1_exploratory_pre_answer_probe_b_20260721.json"
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    capture = json.loads(capture_path.read_text(encoding="utf-8"))
    validated = validate_exploratory_pre_answer_capture(capture, manifest)
    assert validated["captured_before_answers"] is True
    assert validated["confirmatory_reuse_allowed"] is False
