from copy import deepcopy
import json
from pathlib import Path

import pytest

from neural.baby.pending_question_semantics import canonical_json_sha256
from neural.baby.relevance_scorer_contract import (
    BASELINE_ORDER,
    build_relevance_scorer_contract,
    graph_vocabulary_partition,
    validate_relevance_scorer_contract,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TIMESTAMP = "2026-07-22T03:00:00+00:00"


def _load(relative_path: str) -> dict:
    return json.loads(
        (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")
    )


def _inputs() -> tuple[dict, dict, dict, dict]:
    return (
        _load(
            "scripts/research/inputs/"
            "j1_1_candidate_vocabulary_v2_20260716.json"
        ),
        _load(
            "scripts/research/inputs/"
            "j1_1_candidate_universe_v2_raw_scores_20260716.json"
        ),
        _load(
            "scripts/research/inputs/"
            "j1_1_teacher_answers_reviewed_20260716.json"
        ),
        _load(
            "scripts/research/inputs/"
            "j1_1_candidate_universe_v2_labels_reviewed_20260718.json"
        ),
    )


def _contract() -> dict:
    vocabulary, capture, answers, labels = _inputs()
    return build_relevance_scorer_contract(
        vocabulary,
        capture,
        answers,
        labels,
        created_at=TIMESTAMP,
    )


def _reseal(payload: dict) -> dict:
    payload = deepcopy(payload)
    payload.pop("relevance_scorer_contract_sha256", None)
    payload["relevance_scorer_contract_sha256"] = canonical_json_sha256(payload)
    return payload


def test_contract_maps_only_reviewed_binary_labels_and_excludes_uncertain() -> None:
    contract = _contract()

    assert contract["legacy_data"]["question_count"] == 6
    assert contract["legacy_data"]["label_row_count"] == 95
    assert contract["legacy_data"]["binary_row_count"] == 79
    assert contract["legacy_data"]["positive_count"] == 23
    assert contract["legacy_data"]["negative_count"] == 56
    assert contract["legacy_data"]["excluded_uncertain_count"] == 16
    assert contract["legacy_data"]["unique_labeled_concept_count"] == 48
    assert contract["legacy_data"]["concepts_repeated_across_questions"] == 17
    assert contract["objective_contract"]["unlabeled_graph_concept_policy"] == (
        "never_assume_negative"
    )
    assert contract["objective_contract"][
        "automatic_random_negative_labeling_allowed"
    ] is False


def test_contract_partitions_full_vocabulary_before_model_scoring() -> None:
    contract = _contract()
    split = contract["graph_vocabulary_split"]
    counts = [item["concept_count"] for item in split["partitions"]]

    assert sum(counts) == 1069
    assert split["assignment_precedes_labels_and_model_scores"] is True
    assert split["candidate_universe_filtered_by_partition_at_inference"] is False
    assert split["question_split_and_concept_split_are_separate_axes"] is True
    assert split["semantic_disjoint_claim_gate"] is False


def test_contract_separates_future_development_and_lockbox() -> None:
    contract = _contract()
    split = contract["split_contract"]

    assert split["row_random_split_allowed"] is False
    assert split["future_development"]["model_selection_allowed"] is True
    assert split["future_development"]["performance_claim_allowed"] is False
    assert split["future_lockbox"]["model_selection_allowed"] is False
    assert split["future_lockbox"]["one_time_open_required"] is True
    assert split["future_lockbox"][
        "manifest_required_before_any_baseline_execution"
    ] is True
    assert split["future_lockbox"][
        "manifest_required_before_first_supervised_relevance_fit"
    ] is True


def test_contract_enforces_lexical_embedding_head_order() -> None:
    contract = _contract()

    assert contract["baseline_ladder"]["execution_order"] == list(BASELINE_ORDER)
    assert contract["readiness"]["lexical_baseline_implementation_gate"] is True
    assert contract["readiness"]["lexical_baseline_execution_gate"] is False
    assert contract["readiness"]["embedding_baseline_execution_gate"] is False
    assert contract["readiness"]["learned_head_fit_gate"] is False
    assert contract["database_writes"] is False
    assert contract["learning_enabled"] is False


def test_partition_assignment_is_deterministic_and_requires_identity() -> None:
    assert graph_vocabulary_partition("concept-123") == graph_vocabulary_partition(
        "concept-123"
    )
    with pytest.raises(ValueError, match="concept_id"):
        graph_vocabulary_partition("")


def test_validator_rejects_resealed_row_random_split() -> None:
    contract = _contract()
    contract["split_contract"]["row_random_split_allowed"] = True
    contract = _reseal(contract)
    vocabulary, capture, answers, labels = _inputs()

    with pytest.raises(ValueError, match="does not match bound inputs"):
        validate_relevance_scorer_contract(
            contract, vocabulary, capture, answers, labels
        )


def test_validator_rejects_resealed_baseline_reordering() -> None:
    contract = _contract()
    contract["baseline_ladder"]["execution_order"] = list(reversed(BASELINE_ORDER))
    contract = _reseal(contract)
    vocabulary, capture, answers, labels = _inputs()

    with pytest.raises(ValueError, match="does not match bound inputs"):
        validate_relevance_scorer_contract(
            contract, vocabulary, capture, answers, labels
        )


def test_validator_rejects_self_hash_tamper() -> None:
    contract = _contract()
    contract["next_step"] = "fit_now"
    vocabulary, capture, answers, labels = _inputs()

    with pytest.raises(ValueError, match="sha256 mismatch"):
        validate_relevance_scorer_contract(
            contract, vocabulary, capture, answers, labels
        )


def test_repository_relevance_scorer_contract_validates() -> None:
    artifact = _load(
        "claudedocs/research/j1_r1_relevance_scorer_contract_20260722.json"
    )
    vocabulary, capture, answers, labels = _inputs()

    validated = validate_relevance_scorer_contract(
        artifact, vocabulary, capture, answers, labels
    )

    assert validated["relevance_scorer_contract_sha256"] == (
        "918183cbb9450c5f2932ce8d11434937c62210f4ea0b0633a4aa43f529f16a3d"
    )
    assert validated["legacy_data"]["supervised_fit_pool"] == {
        "negative_count": 43,
        "positive_count": 15,
        "row_count": 58,
    }
    assert [
        item["concept_count"]
        for item in validated["graph_vocabulary_split"]["partitions"]
    ] == [856, 117, 96]
    assert validated["readiness"]["heldout_gate"] is False
