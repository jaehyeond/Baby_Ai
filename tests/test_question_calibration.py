import copy

import pytest

from neural.baby.question_calibration import (
    rank_raw_scores,
    seal_question_manifest,
    seal_raw_score_pack,
    validate_preregistered_manifest,
    validate_raw_score_pack,
)


def _manifest() -> dict:
    return seal_question_manifest({
        "question_calibration_manifest_version": 1,
        "phase": "J1.1",
        "manifest_id": "j1_1_test",
        "split": "train_calibration",
        "purpose": "probability_calibration_only",
        "created_at": "2026-07-16T10:00:00+09:00",
        "approval_recorded_at": "2026-07-16T10:00:00+09:00",
        "user_approval_scope": [
            "local_core_gpu_read_only_inference",
            "new_question_answer_collection",
        ],
        "question_count": 2,
        "constraints": {
            "database_writes": False,
            "learning_enabled": False,
            "heldout_collection": False,
            "production_promotion": False,
            "questions_revealed_before_raw_capture": False,
            "calibrator_fit_before_reviewed_answers": False,
        },
        "questions": [
            {
                "order": 0,
                "question_id": "question-0",
                "question": "기억과 학습은 어떻게 연결돼?",
                "cue_terms": ["기억", "학습"],
            },
            {
                "order": 1,
                "question_id": "question-1",
                "question": "컴퓨터와 로봇은 어떻게 연결돼?",
                "cue_terms": ["컴퓨터", "로봇"],
            },
        ],
    })


def _scores(offset: float = 0.0) -> list[dict]:
    return rank_raw_scores([
        {"concept_id": f"c{index}", "concept_name": f"개념{index}", "raw_score": offset + index / 10}
        for index in range(4)
    ])


def _pack(manifest: dict) -> dict:
    questions = []
    for item in manifest["questions"]:
        concepts = [
            {"concept_id": f"c{index}", "concept_name": f"개념{index}"}
            for index in range(4)
        ]
        questions.append({
            "order": item["order"],
            "question_id": item["question_id"],
            "question": item["question"],
            "question_sha256": item["question_sha256"],
            "cue_terms": item["cue_terms"],
            "cue_concepts": [],
            "concept_universe": concepts,
            "predictors": {
                "graph": {
                    "predictor": "graph",
                    "model_snapshot_sha256": "a" * 64,
                    "captured_at": "2026-07-16T10:01:00+09:00",
                    "raw_score_type": "graph_max_relationship_strength",
                    "raw_scores": _scores(),
                },
                "local_core": {
                    "predictor": "local_core",
                    "model_snapshot_sha256": "b" * 64,
                    "captured_at": "2026-07-16T10:02:00+09:00",
                    "raw_score_type": "mean_conditional_token_log_probability",
                    "raw_scores": _scores(-1.0),
                },
            },
        })
    return seal_raw_score_pack({
        "raw_score_pack_version": 1,
        "phase": "J1.1",
        "mode": "offline_shadow_read_only",
        "manifest_id": manifest["manifest_id"],
        "contract_sha256": manifest["contract_sha256"],
        "split": "train_calibration",
        "created_at": "2026-07-16T10:01:00+09:00",
        "sealed_at": "2026-07-16T10:03:00+09:00",
        "question_count": 2,
        "raw_score_count_per_predictor": 8,
        "learning_enabled": False,
        "database_writes": False,
        "gradients_enabled": False,
        "optimizer_created": False,
        "gpu_inference_read_only": True,
        "questions_revealed_before_capture": False,
        "probabilities_created": False,
        "calibrator_fitted": False,
        "heldout_gate": False,
        "performance_claim_gate": False,
        "production_promotion_gate": False,
        "graph_implementation_sha256": "c" * 64,
        "graph_model_snapshot_sha256": "a" * 64,
        "graph_snapshot_scope": "query_scoped_not_full_database",
        "local_core_base_model_id": "Qwen/Qwen2.5-0.5B-Instruct",
        "local_core_base_model_revision": "revision",
        "local_core_adapter_sha256": "d" * 64,
        "local_core_model_snapshot_sha256": "b" * 64,
        "local_core_device": "cuda:0",
        "local_core_trainable_parameter_count": 0,
        "local_core_peak_cuda_memory_bytes": 100,
        "questions": questions,
    })


def test_manifest_and_raw_scores_validate_without_inventing_probabilities() -> None:
    manifest = _manifest()
    pack = _pack(manifest)

    assert validate_preregistered_manifest(manifest)["question_count"] == 2
    validated = validate_raw_score_pack(manifest, pack)

    assert validated["probabilities_created"] is False
    assert validated["calibrator_fitted"] is False
    assert validated["database_writes"] is False
    assert validated["learning_enabled"] is False
    assert validated["local_core_trainable_parameter_count"] == 0


@pytest.mark.parametrize(
    ("mutator", "message"),
    [
        (
            lambda manifest, pack: pack["questions"][0].update({"question": "바뀐 질문"}),
            "question mismatch",
        ),
        (
            lambda manifest, pack: pack["questions"][0]["predictors"]["local_core"]["raw_scores"].pop(),
            "exact concept universe",
        ),
        (
            lambda manifest, pack: pack.update({"questions_revealed_before_capture": True}),
            "no-learning/no-write/no-claim",
        ),
        (
            lambda manifest, pack: pack["questions"][0]["predictors"]["graph"].update({"concept_probabilities": []}),
            "probability fields",
        ),
        (
            lambda manifest, pack: pack.update({"local_core_trainable_parameter_count": 1}),
            "zero trainable",
        ),
    ],
)
def test_raw_pack_fails_closed(mutator, message: str) -> None:
    manifest = _manifest()
    pack = _pack(manifest)
    invalid = copy.deepcopy(pack)
    mutator(manifest, invalid)
    invalid = seal_raw_score_pack(invalid)

    with pytest.raises(ValueError, match=message):
        validate_raw_score_pack(manifest, invalid)


def test_manifest_hash_detects_post_registration_question_change() -> None:
    manifest = _manifest()
    manifest["questions"][0]["question"] = "등록 뒤 바뀐 질문"

    with pytest.raises(ValueError, match="question_sha256 mismatch"):
        validate_preregistered_manifest(manifest)
