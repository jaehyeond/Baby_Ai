import copy

import pytest

from neural.baby.pending_question_semantics import canonical_json_sha256
from neural.baby.question_experiment import (
    evaluate_question_experiment_pack,
    jensen_shannon_divergence,
    score_multilabel_probabilities,
    select_question_by_disagreement,
    validate_question_experiment_pack,
)


HASH = "a" * 64


def _snapshot(predictor: str, probabilities: dict[str, float]) -> dict:
    return {
        "predictor": predictor,
        "snapshot_id": f"{predictor}-snapshot",
        "model_snapshot_sha256": ("b" if predictor == "graph" else "c") * 64,
        "captured_at": "2026-07-16T15:00:00+09:00",
        "calibration": {
            "method": "platt",
            "dataset_sha256": "d" * 64,
            "calibrator_sha256": ("e" if predictor == "graph" else "f") * 64,
            "sample_count": 4,
            "positive_count": 2,
            "negative_count": 2,
            "fitted_at": "2026-07-16T14:00:00+09:00",
        },
        "concept_probabilities": [
            {"concept_id": concept_id, "probability": probability}
            for concept_id, probability in probabilities.items()
        ],
    }


def _fixtures() -> tuple[dict, dict, dict]:
    manifest = {
        "contract_sha256": HASH,
        "questions": [
            {"order": 0, "question": "컴퓨터를 설명해줘"},
            {"order": 1, "question": "이야기를 설명해줘"},
        ],
    }
    labels = {
        "semantic_label_pack_version": 1,
        "contract_sha256": HASH,
        "review_status": "user_reviewed",
        "reviewer_role": "user",
        "reviewed_at": "2026-07-16T16:00:00+09:00",
        "entries": [
            {
                "order": 0,
                "question_id": "question-0",
                "labels": [
                    {"concept_id": "information", "decision": "approved"},
                    {"concept_id": "story", "decision": "rejected"},
                ],
            },
            {
                "order": 1,
                "question_id": "question-1",
                "labels": [
                    {"concept_id": "information", "decision": "rejected"},
                    {"concept_id": "story", "decision": "approved"},
                ],
            },
        ],
    }
    experiment = {
        "question_experiment_pack_version": 1,
        "contract_sha256": HASH,
        "semantic_label_pack_sha256": canonical_json_sha256(labels),
        "mode": "offline_shadow_no_learning",
        "learning_enabled": False,
        "split": "train",
        "created_at": "2026-07-16T15:02:00+09:00",
        "decisions": [{
            "decision_id": "decision-0",
            "selection_policy": "max_jensen_shannon_disagreement",
            "selection_captured_at": "2026-07-16T15:01:00+09:00",
            "asked_at": "2026-07-16T15:03:00+09:00",
            "selected_order": 1,
            "selected_question_id": "question-1",
            "candidate_questions": [
                {
                    "order": 0,
                    "question": "컴퓨터를 설명해줘",
                    "predictors": {
                        "graph": _snapshot("graph", {"information": 0.8, "story": 0.2}),
                        "local_core": _snapshot("local_core", {"information": 0.75, "story": 0.25}),
                    },
                },
                {
                    "order": 1,
                    "question": "이야기를 설명해줘",
                    "predictors": {
                        "graph": _snapshot("graph", {"information": 0.9, "story": 0.1}),
                        "local_core": _snapshot("local_core", {"information": 0.1, "story": 0.9}),
                    },
                },
            ],
        }],
    }
    return manifest, labels, experiment


def test_disagreement_selection_is_deterministic() -> None:
    manifest, labels, experiment = _fixtures()
    candidates = experiment["decisions"][0]["candidate_questions"]

    selection = select_question_by_disagreement(candidates)
    same = jensen_shannon_divergence(
        {"a": 0.8, "b": 0.2},
        {"a": 0.8, "b": 0.2},
    )

    assert selection["selected_order"] == 1
    assert selection["selected_disagreement"] > selection["runner_up_disagreement"]
    assert same == pytest.approx(0.0)
    validate_question_experiment_pack(manifest, labels, experiment)


def test_multilabel_scores_and_valid_pack_remain_train_only() -> None:
    manifest, labels, experiment = _fixtures()
    perfect = score_multilabel_probabilities(
        {"a": 1.0, "b": 0.0, "c": 1.0},
        {"a", "c"},
    )
    report = evaluate_question_experiment_pack(manifest, labels, experiment)

    assert perfect["brier"] == 0.0
    assert perfect["top_k_recall"] == 1.0
    assert report["contract_gate"] is True
    assert report["decision_count"] == 1
    assert report["learning_enabled"] is False
    assert report["heldout_gate"] is False
    assert report["performance_claim_gate"] is False
    assert report["production_promotion_gate"] is False


@pytest.mark.parametrize(
    ("mutator", "message"),
    [
        (
            lambda pack: pack["decisions"][0]["candidate_questions"][0]["predictors"].pop("local_core"),
            "graph and local_core",
        ),
        (
            lambda pack: pack["decisions"][0]["candidate_questions"][0]["predictors"]["local_core"]["concept_probabilities"].pop(),
            "same concept universe",
        ),
        (
            lambda pack: pack["decisions"][0].update({"selected_order": 0, "selected_question_id": "question-0"}),
            "deterministic disagreement",
        ),
        (
            lambda pack: pack["decisions"][0].update({"asked_at": "2026-07-16T14:59:00+09:00"}),
            "selection must precede",
        ),
        (
            lambda pack: pack["decisions"][0]["candidate_questions"][0]["predictors"]["graph"].pop("calibration"),
            "calibration method",
        ),
    ],
)
def test_pack_fails_closed_on_incomparable_or_post_question_data(
    mutator,
    message: str,
) -> None:
    manifest, labels, experiment = _fixtures()
    invalid = copy.deepcopy(experiment)
    mutator(invalid)

    with pytest.raises(ValueError, match=message):
        validate_question_experiment_pack(manifest, labels, invalid)
