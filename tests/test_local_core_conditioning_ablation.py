from copy import deepcopy
import json
from pathlib import Path

import pytest

from neural.baby.exploratory_question_probe import (
    EXPLORATORY_EVIDENCE_SCOPE,
    EXPLORATORY_MANIFEST_STATUS,
    EXPLORATORY_PHASE,
    build_exploratory_pre_answer_capture,
)
from neural.baby.exploratory_signal_audit import seal_exploratory_answer_pack
from neural.baby.local_core_conditioning_ablation import (
    build_local_core_conditioning_ablation,
    validate_local_core_conditioning_ablation,
)


TIMESTAMP = "2026-07-22T00:00:00+00:00"
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _manifest() -> dict:
    return {
        "exploratory_question_manifest_version": 1,
        "phase": EXPLORATORY_PHASE,
        "status": EXPLORATORY_MANIFEST_STATUS,
        "manifest_id": "local_core_conditioning_test",
        "prepared_at": TIMESTAMP,
        "purpose": "diagnose_local_core_conditioning",
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
    names = [
        "촬영",
        "영상",
        "건물",
        "바람",
        "개념04",
        "개념05",
        "개념06",
        "개념07",
        "개념08",
        "개념09",
        "개념10",
        "개념11",
        "개념12",
        "개념13",
    ]
    return [
        {"id": f"c{index:02d}", "name": name}
        for index, name in enumerate(names)
    ]


def _scores(offset: float = 0.0) -> dict[int, list[dict]]:
    return {
        order: [
            {
                "concept_id": concept["id"],
                "concept_name": concept["name"],
                "raw_score": float(index) + offset,
            }
            for index, concept in enumerate(_concepts())
        ]
        for order in (0, 1)
    }


def _capture() -> dict:
    return build_exploratory_pre_answer_capture(
        _manifest(),
        _concepts(),
        _scores(0.25),
        _scores(),
        graph_predictor={
            "implementation_sha256": "a" * 64,
            "scoring_contract": "max_cue_edge_strength_full_vocabulary_v1",
        },
        local_core_predictor={
            "adapter_sha256": "b" * 64,
            "model_snapshot_sha256": "c" * 64,
            "trainable_parameter_count": 0,
            "device": "cuda:0",
            "batch_size": 16,
        },
        captured_at=TIMESTAMP,
    )


def _answer_spec() -> dict:
    return {
        "answer_source": "external_teacher",
        "exploratory_answer_spec_version": 1,
        "exploratory_only_not_ground_truth": True,
        "generated_before_prediction_reveal": True,
        "phase": EXPLORATORY_PHASE,
        "prepared_at": TIMESTAMP,
        "questions": [
            {
                "answer": "촬영과 영상이 영화 제작을 연결한다.",
                "order": 0,
                "question_id": "exp-00",
                "target_concepts": ["촬영", "영상"],
            },
            {
                "answer": "건물과 바람은 도시 날씨에 영향을 준다.",
                "order": 1,
                "question_id": "exp-01",
                "target_concepts": ["건물", "바람"],
            },
        ],
        "question_type": "public_knowledge",
        "status": "external_teacher_answers_fixed_before_prediction_review",
        "teacher_identity_scope": "conversation_assistant_not_model_snapshot",
        "user_review_required": False,
    }


def _answer_pack() -> dict:
    return seal_exploratory_answer_pack(
        _answer_spec(), _manifest(), _capture(), sealed_at=TIMESTAMP
    )


def _metadata() -> dict:
    return {
        "base_model_id": "test-model",
        "base_model_revision": "test-revision",
        "adapter_sha256": "b" * 64,
        "model_snapshot_sha256": "c" * 64,
        "scoring_contract": "mean_conditional_token_log_probability_v1",
        "score_implementation_sha256": "d" * 64,
        "ablation_implementation_sha256": "e" * 64,
        "device": "cuda:0",
        "batch_size": 16,
        "trainable_parameter_count": 0,
        "peak_cuda_memory_bytes": 123,
    }


def _ablation() -> dict:
    return build_local_core_conditioning_ablation(
        _manifest(),
        _capture(),
        _answer_pack(),
        _concepts(),
        _scores(),
        _scores(),
        _scores(),
        predictor_metadata=_metadata(),
        audited_at=TIMESTAMP,
    )


def test_ablation_reproduces_actual_scores_and_flags_prior_dominance() -> None:
    result = _ablation()

    assert result["actual_digest_match_count"] == 2
    assert result["actual_score_reproduction_gate"] is True
    assert result["diagnostic_warnings"]["content_free_prior_dominance"] is True
    assert result["diagnostic_warnings"]["question_shuffle_insensitivity"] is True
    assert result["ranking_summaries"]["actual"]["exact_target_hit_count"] == 0
    assert result["ranking_summaries"]["content_free_delta"][
        "exact_target_hit_count"
    ] == 4
    assert result["learning_enabled"] is False
    assert result["performance_claim_gate"] is False


def test_ablation_fails_closed_on_actual_score_digest_drift() -> None:
    actual = _scores()
    actual[0][0]["raw_score"] += 0.01

    with pytest.raises(ValueError, match="score digest drift"):
        build_local_core_conditioning_ablation(
            _manifest(),
            _capture(),
            _answer_pack(),
            _concepts(),
            actual,
            _scores(),
            _scores(),
            predictor_metadata=_metadata(),
            audited_at=TIMESTAMP,
        )


def test_ablation_fails_closed_on_adapter_drift() -> None:
    metadata = _metadata()
    metadata["adapter_sha256"] = "f" * 64

    with pytest.raises(ValueError, match="adapter"):
        build_local_core_conditioning_ablation(
            _manifest(),
            _capture(),
            _answer_pack(),
            _concepts(),
            _scores(),
            _scores(),
            _scores(),
            predictor_metadata=metadata,
            audited_at=TIMESTAMP,
        )


def test_ablation_requires_all_control_orders() -> None:
    shuffled = _scores()
    shuffled.pop(1)

    with pytest.raises(ValueError, match="score orders"):
        build_local_core_conditioning_ablation(
            _manifest(),
            _capture(),
            _answer_pack(),
            _concepts(),
            _scores(),
            _scores(),
            shuffled,
            predictor_metadata=_metadata(),
            audited_at=TIMESTAMP,
        )


def test_ablation_validator_rejects_control_contract_tamper() -> None:
    result = deepcopy(_ablation())
    result["control_contract"]["content_free_question_text"] = "중립"

    with pytest.raises(ValueError, match="must remain empty"):
        validate_local_core_conditioning_ablation(
            result, _manifest(), _capture(), _answer_pack()
        )


def test_ablation_validator_rejects_self_hash_tamper() -> None:
    result = deepcopy(_ablation())
    result["next_step"] = "fit_model"

    with pytest.raises(ValueError, match="sha256 mismatch"):
        validate_local_core_conditioning_ablation(
            result, _manifest(), _capture(), _answer_pack()
        )


def test_repository_local_core_conditioning_ablation_validates() -> None:
    manifest = json.loads((
        PROJECT_ROOT
        / "scripts/research/manifests/j1_1_fresh_selection_b_20260720_draft.json"
    ).read_text(encoding="utf-8"))
    capture = json.loads((
        PROJECT_ROOT
        / "scripts/research/inputs/j1_exploratory_pre_answer_probe_b_20260721.json"
    ).read_text(encoding="utf-8"))
    answer_pack = json.loads((
        PROJECT_ROOT
        / "scripts/research/inputs/j1_exploratory_external_teacher_answers_b_20260721.json"
    ).read_text(encoding="utf-8"))
    artifact = json.loads((
        PROJECT_ROOT
        / "claudedocs/research/j1_local_core_conditioning_ablation_b_20260722.json"
    ).read_text(encoding="utf-8"))

    validated = validate_local_core_conditioning_ablation(
        artifact, manifest, capture, answer_pack
    )

    assert validated["actual_digest_match_count"] == 6
    assert validated["ranking_summaries"]["actual"]["exact_target_hit_count"] == 1
    assert validated["ranking_summaries"]["content_free"][
        "exact_target_hit_count"
    ] == 2
    assert validated["ranking_summaries"]["content_free_delta"][
        "exact_target_hit_count"
    ] == 0
    assert validated["performance_claim_gate"] is False
