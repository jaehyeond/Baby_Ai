import copy
import json
from pathlib import Path

import pytest

from neural.baby.calibrator_design import CALIBRATOR_DESIGN_FEATURE_NAMES
from neural.baby.fresh_snapshot_contract import (
    seal_fresh_pre_question_snapshot_input_pack,
)
from neural.baby.fresh_question_capture import (
    FRESH_MANIFEST_PURPOSE,
    FRESH_MANIFEST_SPLIT,
    REAL_FRESH_SOURCE_SCOPE,
    assert_fresh_questions_never_labeled,
    seal_fresh_question_manifest,
    validate_fresh_preregistered_manifest,
    build_fresh_candidate_vocabulary,
    build_real_fresh_pre_question_snapshot_input_pack,
    validate_fresh_candidate_vocabulary,
    validate_real_fresh_pre_question_snapshot_input_pack,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = (
    PROJECT_ROOT
    / "scripts"
    / "research"
    / "inputs"
    / "j1_1_fresh_pre_question_snapshot_input_contract_20260718.json"
)
TRAIN_MANIFEST_PATH = (
    PROJECT_ROOT
    / "scripts"
    / "research"
    / "manifests"
    / "j1_1_train_calibration_a_20260716.json"
)

CAPTURED_AT = "2026-07-20T04:00:00+00:00"


def _question(order: int, ident: str, digest: str, cues: list[str]) -> dict:
    return {
        "order": order,
        "question_id": ident,
        "question_sha256": digest,
        "cue_terms": cues,
    }


def _fresh_manifest() -> dict:
    return {
        "manifest_id": "j1_1_fresh_b_20260720",
        "contract_sha256": "a" * 64,
        "questions": [
            _question(0, "j1-1-fresh-b-00", "1" * 64, ["카메라", "영화"]),
            _question(1, "j1-1-fresh-b-01", "2" * 64, ["도시", "날씨"]),
        ],
    }


def _train_manifest() -> dict:
    return json.loads(TRAIN_MANIFEST_PATH.read_text(encoding="utf-8"))


def _evidence() -> dict:
    return assert_fresh_questions_never_labeled(_fresh_manifest(), _train_manifest())


def _concepts(count: int) -> list[dict]:
    return [
        {"id": f"c{index:03d}", "name": f"concept-{index}"} for index in range(count)
    ]


def _scopes() -> list[dict]:
    return [
        {
            "order": 0,
            "question_id": "j1-1-fresh-b-00",
            "question_sha256": "1" * 64,
            "cue_terms": ["카메라", "영화"],
            "cue_exclusions": [],
            "eligible_concept_count": 18,
        },
        {
            "order": 1,
            "question_id": "j1-1-fresh-b-01",
            "question_sha256": "2" * 64,
            "cue_terms": ["도시", "날씨"],
            "cue_exclusions": [],
            "eligible_concept_count": 18,
        },
    ]


def _vocabulary() -> dict:
    concepts = _concepts(20)
    eligible = [
        {"concept_id": item["id"], "concept_name": item["name"]}
        for item in concepts[:18]
    ]
    rejected = [
        {"concept_id": item["id"], "concept_name": item["name"], "reason": "too_short"}
        for item in concepts[18:]
    ]
    return build_fresh_candidate_vocabulary(
        _fresh_manifest(),
        concepts,
        eligible,
        rejected,
        _scopes(),
        created_at=CAPTURED_AT,
        never_labeled_evidence=_evidence(),
    )


def _features(seed: float) -> dict:
    return {name: seed + index for index, name in enumerate(CALIBRATOR_DESIGN_FEATURE_NAMES)}


def _scored() -> list[dict]:
    return [
        {
            "order": order,
            "question_id": f"j1-1-fresh-b-0{order}",
            "question_sha256": str(order + 1) * 64,
            "candidate_rows": [
                {"concept_id": f"c{index:03d}", "feature_values": _features(index)}
                for index in range(9)
            ],
        }
        for order in (0, 1)
    ]


@pytest.fixture(scope="module")
def contract() -> dict:
    if not CONTRACT_PATH.exists():
        pytest.skip("sealed fresh input contract unavailable")
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------
# never-labeled guard
# --------------------------------------------------------------------------


def test_fresh_questions_pass_the_never_labeled_gate():
    evidence = _evidence()
    assert evidence["never_labeled_gate"] is True
    assert evidence["shared_question_ids"] == []
    assert evidence["shared_question_sha256"] == []
    assert evidence["shared_cue_terms"] == []
    assert evidence["train_question_count"] == 6


def test_reusing_a_train_question_id_is_rejected():
    manifest = _fresh_manifest()
    manifest["questions"][0]["question_id"] = "j1-1-cal-a-05"
    with pytest.raises(ValueError, match="reuses train question IDs"):
        assert_fresh_questions_never_labeled(manifest, _train_manifest())


def test_reusing_a_train_question_hash_is_rejected():
    train = _train_manifest()
    manifest = _fresh_manifest()
    manifest["questions"][0]["question_sha256"] = train["questions"][0][
        "question_sha256"
    ]
    with pytest.raises(ValueError, match="reuses train question hashes"):
        assert_fresh_questions_never_labeled(manifest, train)


@pytest.mark.parametrize("cue", ["학습", "컴퓨터", "사람", "세상", "기억"])
def test_reusing_any_train_cue_term_is_rejected(cue):
    manifest = _fresh_manifest()
    manifest["questions"][0]["cue_terms"] = [cue, "영화"]
    with pytest.raises(ValueError, match="reuses train cue terms"):
        assert_fresh_questions_never_labeled(manifest, _train_manifest())


def test_already_labeled_question_hash_is_rejected():
    label_pack = {"entries": [{"question_sha256": "1" * 64, "decision": "approved"}]}
    with pytest.raises(ValueError, match="reuses already-labeled questions"):
        assert_fresh_questions_never_labeled(
            _fresh_manifest(), _train_manifest(), label_pack
        )


def test_reusing_the_train_contract_hash_is_rejected():
    train = _train_manifest()
    manifest = _fresh_manifest()
    manifest["contract_sha256"] = train["contract_sha256"]
    with pytest.raises(ValueError, match="must not reuse the train contract hash"):
        assert_fresh_questions_never_labeled(manifest, train)


def test_duplicate_fresh_question_ids_are_rejected():
    manifest = _fresh_manifest()
    manifest["questions"][1]["question_id"] = manifest["questions"][0]["question_id"]
    with pytest.raises(ValueError, match="must be unique"):
        assert_fresh_questions_never_labeled(manifest, _train_manifest())


# --------------------------------------------------------------------------
# fresh vocabulary
# --------------------------------------------------------------------------


def test_fresh_vocabulary_does_not_bind_reviewed_packs():
    vocabulary = _vocabulary()
    assert "reviewed_reference_answer_pack_sha256" not in vocabulary
    assert "reviewed_candidate_label_pack_sha256" not in vocabulary
    assert vocabulary["reviewed_packs_absent_because_questions_are_unanswered"] is True
    assert vocabulary["never_labeled_evidence"]["never_labeled_gate"] is True
    assert validate_fresh_candidate_vocabulary(vocabulary, _fresh_manifest()) == (
        vocabulary
    )


def test_fresh_vocabulary_keeps_every_preflight_gate_false():
    vocabulary = _vocabulary()
    for field in (
        "database_writes",
        "learning_enabled",
        "gpu_inference_executed",
        "probabilities_computed",
        "calibrator_fit_allowed",
        "heldout_gate",
        "performance_claim_gate",
        "production_promotion_gate",
    ):
        assert vocabulary[field] is False


def test_binding_a_reviewed_pack_into_fresh_vocabulary_is_rejected():
    vocabulary = copy.deepcopy(_vocabulary())
    vocabulary["reviewed_candidate_label_pack_sha256"] = "c" * 64
    with pytest.raises(ValueError, match="must not bind reviewed packs"):
        validate_fresh_candidate_vocabulary(vocabulary)


def test_fresh_vocabulary_requires_passing_never_labeled_evidence():
    evidence = _evidence()
    evidence["never_labeled_gate"] = False
    with pytest.raises(ValueError, match="requires a passing never-labeled gate"):
        build_fresh_candidate_vocabulary(
            _fresh_manifest(),
            _concepts(20),
            [],
            [],
            _scopes(),
            created_at=CAPTURED_AT,
            never_labeled_evidence=evidence,
        )


def test_fresh_vocabulary_scopes_must_cover_the_manifest():
    vocabulary = _vocabulary()
    trimmed = copy.deepcopy(vocabulary)
    trimmed["question_scopes"] = trimmed["question_scopes"][:1]
    with pytest.raises(ValueError):
        validate_fresh_candidate_vocabulary(trimmed, _fresh_manifest())


# --------------------------------------------------------------------------
# real fresh input pack
# --------------------------------------------------------------------------


def test_real_fresh_pack_is_marked_captured_not_replayed(contract):
    vocabulary = _vocabulary()
    pack = build_real_fresh_pre_question_snapshot_input_pack(
        contract, vocabulary, _scored(), captured_at=CAPTURED_AT
    )
    assert pack["source_scope"] == REAL_FRESH_SOURCE_SCOPE
    assert pack["source_scope"] != "sealed_train_capture_shadow_not_runtime_fresh"
    assert pack["captured_not_replayed"] is True
    assert pack["never_labeled_gate"] is True
    assert pack["question_count"] == 2
    assert pack["candidate_row_count"] == 18


def test_real_fresh_pack_stays_bound_to_the_sealed_contract(contract):
    pack = build_real_fresh_pre_question_snapshot_input_pack(
        contract, _vocabulary(), _scored(), captured_at=CAPTURED_AT
    )
    # input_pack_scope must stay contract-bound so downstream validators apply
    assert pack["input_pack_scope"] == contract["input_pack_scope"]
    assert pack["feature_schema_sha256"] == contract["feature_schema_sha256"]
    assert pack["feature_names"] == contract["feature_names"]
    assert pack["fresh_pre_question_snapshot_input_contract_sha256"] == contract[
        "fresh_pre_question_snapshot_input_contract_sha256"
    ]


def test_real_fresh_pack_keeps_runtime_gates_false(contract):
    pack = build_real_fresh_pre_question_snapshot_input_pack(
        contract, _vocabulary(), _scored(), captured_at=CAPTURED_AT
    )
    for field in (
        "fresh_snapshot_runtime_gate",
        "question_selection_runtime_gate",
        "runtime_probability_snapshot_gate",
        "database_writes",
        "learning_enabled",
        "heldout_gate",
        "performance_claim_gate",
        "production_promotion_gate",
    ):
        assert pack[field] is False


def test_real_fresh_pack_binds_vocabulary_and_graph_snapshot(contract):
    vocabulary = _vocabulary()
    pack = build_real_fresh_pre_question_snapshot_input_pack(
        contract, vocabulary, _scored(), captured_at=CAPTURED_AT
    )
    assert pack["fresh_candidate_vocabulary_sha256"] == vocabulary[
        "fresh_candidate_vocabulary_sha256"
    ]
    assert pack["graph_snapshot_sha256"] == vocabulary["graph_snapshot_sha256"]
    assert validate_real_fresh_pre_question_snapshot_input_pack(
        pack, contract, vocabulary
    ) == pack


def test_a_replayed_source_scope_is_rejected(contract):
    vocabulary = _vocabulary()
    pack = build_real_fresh_pre_question_snapshot_input_pack(
        contract, vocabulary, _scored(), captured_at=CAPTURED_AT
    )
    tampered = copy.deepcopy(pack)
    tampered["source_scope"] = "sealed_train_capture_shadow_not_runtime_fresh"
    tampered.pop("fresh_pre_question_input_pack_sha256", None)
    tampered = seal_fresh_pre_question_snapshot_input_pack(tampered)
    with pytest.raises(ValueError, match="must not be a replay"):
        validate_real_fresh_pre_question_snapshot_input_pack(
            tampered, contract, vocabulary
        )


def test_vocabulary_mismatch_is_rejected(contract):
    vocabulary = _vocabulary()
    pack = build_real_fresh_pre_question_snapshot_input_pack(
        contract, vocabulary, _scored(), captured_at=CAPTURED_AT
    )
    other = copy.deepcopy(vocabulary)
    other["graph_snapshot_sha256"] = "d" * 64
    with pytest.raises(ValueError):
        validate_real_fresh_pre_question_snapshot_input_pack(pack, contract, other)


def test_single_question_pack_is_rejected(contract):
    with pytest.raises(ValueError, match="at least two questions"):
        build_real_fresh_pre_question_snapshot_input_pack(
            contract, _vocabulary(), _scored()[:1], captured_at=CAPTURED_AT
        )


def test_naive_timestamp_is_rejected(contract):
    with pytest.raises(ValueError, match="timezone"):
        build_real_fresh_pre_question_snapshot_input_pack(
            contract, _vocabulary(), _scored(), captured_at="2026-07-20T04:00:00"
        )


# --------------------------------------------------------------------------
# fresh manifest validator (question_calibration.py stays untouched)
# --------------------------------------------------------------------------


def _approved_draft() -> dict:
    return {
        "question_calibration_manifest_version": 1,
        "phase": "J1.1",
        "split": FRESH_MANIFEST_SPLIT,
        "purpose": FRESH_MANIFEST_PURPOSE,
        "manifest_id": "j1_1_fresh_selection_b_20260720",
        "created_at": CAPTURED_AT,
        "approval_recorded_at": CAPTURED_AT,
        "user_approval_scope": [
            "local_core_gpu_read_only_inference",
            "new_question_answer_collection",
        ],
        "constraints": {
            "calibrator_fit_before_reviewed_answers": False,
            "database_writes": False,
            "heldout_collection": False,
            "learning_enabled": False,
            "production_promotion": False,
            "questions_revealed_before_raw_capture": False,
        },
        "question_count": 2,
        "questions": [
            {
                "order": 0,
                "question_id": "j1-1-fresh-b-00",
                "question": "카메라와 영화는 서로 어떻게 이어져 있어?",
                "cue_terms": ["카메라", "영화"],
            },
            {
                "order": 1,
                "question_id": "j1-1-fresh-b-01",
                "question": "도시와 날씨는 서로에게 어떤 영향을 줘?",
                "cue_terms": ["도시", "날씨"],
            },
        ],
    }


def test_fresh_manifest_seals_and_validates_when_approved():
    sealed = seal_fresh_question_manifest(_approved_draft())
    assert sealed["split"] == FRESH_MANIFEST_SPLIT
    assert sealed["purpose"] == FRESH_MANIFEST_PURPOSE
    assert len(sealed["contract_sha256"]) == 64
    assert all(len(q["question_sha256"]) == 64 for q in sealed["questions"])
    assert validate_fresh_preregistered_manifest(sealed) == sealed


def test_a_draft_without_user_approval_cannot_be_sealed():
    """Pre-registration must not be performable on the user's behalf."""

    draft = _approved_draft()
    draft.pop("user_approval_scope")
    with pytest.raises(ValueError, match="missing explicit user approval scope"):
        seal_fresh_question_manifest(draft)


def test_partial_user_approval_is_rejected():
    draft = _approved_draft()
    draft["user_approval_scope"] = ["local_core_gpu_read_only_inference"]
    with pytest.raises(ValueError, match="new_question_answer_collection"):
        seal_fresh_question_manifest(draft)


def test_fresh_manifest_rejects_the_train_split_and_purpose():
    draft = _approved_draft()
    draft["split"] = "train_calibration"
    with pytest.raises(ValueError, match="split must be fresh_selection"):
        seal_fresh_question_manifest(draft)
    draft = _approved_draft()
    draft["purpose"] = "probability_calibration_only"
    with pytest.raises(ValueError, match="purpose must be"):
        seal_fresh_question_manifest(draft)


@pytest.mark.parametrize(
    "field",
    [
        "database_writes",
        "learning_enabled",
        "heldout_collection",
        "production_promotion",
        "questions_revealed_before_raw_capture",
        "calibrator_fit_before_reviewed_answers",
    ],
)
def test_fresh_manifest_constraints_must_stay_false(field):
    draft = _approved_draft()
    draft["constraints"][field] = True
    with pytest.raises(ValueError, match="constraints must stay false"):
        seal_fresh_question_manifest(draft)


def test_fresh_manifest_uses_the_same_question_hash_as_the_train_manifest():
    """Hash drift would make a train-collision undetectable."""

    from neural.baby.question_calibration import _question_sha256

    sealed = seal_fresh_question_manifest(_approved_draft())
    for question in sealed["questions"]:
        assert question["question_sha256"] == _question_sha256(question["question"])


def test_tampered_fresh_manifest_contract_hash_is_rejected():
    sealed = seal_fresh_question_manifest(_approved_draft())
    tampered = copy.deepcopy(sealed)
    tampered["questions"][0]["question"] = "다른 질문이야?"
    with pytest.raises(ValueError):
        validate_fresh_preregistered_manifest(tampered)


def test_sealed_fresh_manifest_still_passes_the_never_labeled_gate():
    sealed = seal_fresh_question_manifest(_approved_draft())
    evidence = assert_fresh_questions_never_labeled(sealed, _train_manifest())
    assert evidence["never_labeled_gate"] is True


def test_train_manifest_is_rejected_by_the_fresh_validator():
    """The two validators must not accept each other's manifests."""

    with pytest.raises(ValueError, match="split must be fresh_selection"):
        validate_fresh_preregistered_manifest(_train_manifest())


def test_fresh_manifest_is_rejected_by_the_train_validator():
    from neural.baby.question_calibration import validate_preregistered_manifest

    sealed = seal_fresh_question_manifest(_approved_draft())
    with pytest.raises(ValueError, match="train_calibration"):
        validate_preregistered_manifest(sealed)
