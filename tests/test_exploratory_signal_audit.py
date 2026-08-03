from copy import deepcopy
import json
from pathlib import Path

import pytest

from neural.baby.exploratory_question_probe import (
    EXPLORATORY_CAPTURE_STATUS,
    EXPLORATORY_EVIDENCE_SCOPE,
    EXPLORATORY_MANIFEST_STATUS,
    EXPLORATORY_PHASE,
    build_exploratory_pre_answer_capture,
)
from neural.baby.exploratory_signal_audit import (
    build_exploratory_signal_audit,
    seal_exploratory_answer_pack,
    validate_exploratory_answer_pack,
    validate_exploratory_answer_spec,
    validate_exploratory_signal_audit,
)


TIMESTAMP = "2026-07-21T10:00:00+00:00"
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _manifest() -> dict:
    return {
        "exploratory_question_manifest_version": 1,
        "phase": EXPLORATORY_PHASE,
        "status": EXPLORATORY_MANIFEST_STATUS,
        "manifest_id": "j1_exploratory_signal_test",
        "prepared_at": TIMESTAMP,
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


def _score_rows(order: int, predictor: str) -> list[dict]:
    rows = []
    for index, concept in enumerate(_concepts()):
        score = float(index)
        if predictor == "graph":
            if order == 0 and concept["name"] in {"촬영", "영상"}:
                score = 100.0 - index
            if order == 1 and concept["name"] == "건물":
                score = 100.0
        else:
            if concept["name"] in {"촬영", "영상", "건물", "바람"}:
                score = -100.0 - index
        rows.append({
            "concept_id": concept["id"],
            "concept_name": concept["name"],
            "raw_score": score,
        })
    return rows


def _capture() -> dict:
    capture = build_exploratory_pre_answer_capture(
        _manifest(),
        _concepts(),
        {order: _score_rows(order, "graph") for order in (0, 1)},
        {order: _score_rows(order, "local") for order in (0, 1)},
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
        captured_at=TIMESTAMP,
    )
    assert capture["status"] == EXPLORATORY_CAPTURE_STATUS
    return capture


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
                "answer": "카메라는 촬영한 영상으로 영화 제작의 재료를 제공한다.",
                "order": 0,
                "question_id": "exp-00",
                "target_concepts": ["촬영", "영상"],
            },
            {
                "answer": "건물과 바람은 도시의 날씨 조건에 서로 영향을 준다.",
                "order": 1,
                "question_id": "exp-01",
                "target_concepts": ["건물", "없는개념"],
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


def _audit() -> dict:
    return build_exploratory_signal_audit(
        _answer_pack(),
        _manifest(),
        _capture(),
        _concepts(),
        audited_at=TIMESTAMP,
    )


def test_answer_spec_routes_public_knowledge_to_external_teacher() -> None:
    validated = validate_exploratory_answer_spec(_answer_spec(), _manifest())

    assert len(validated["exploratory_answer_spec_sha256"]) == 64
    assert validated["answer_source"] == "external_teacher"
    assert validated["user_review_required"] is False


def test_answer_spec_rejects_question_cue_as_target() -> None:
    payload = _answer_spec()
    payload["questions"][0]["target_concepts"] = ["카메라", "영상"]

    with pytest.raises(ValueError, match="exclude question cue"):
        validate_exploratory_answer_spec(payload, _manifest())


def test_answer_pack_binds_capture_without_consuming_predictions() -> None:
    capture = _capture()
    answer_pack = seal_exploratory_answer_pack(
        _answer_spec(), _manifest(), capture, sealed_at=TIMESTAMP
    )

    assert answer_pack["exploratory_pre_answer_capture_sha256"] == capture[
        "exploratory_pre_answer_capture_sha256"
    ]
    assert answer_pack["prediction_fields_consumed_for_answer_generation"] is False
    assert answer_pack["answer_pack_mutation_after_prediction_reveal_allowed"] is False
    assert answer_pack["performance_claim_gate"] is False


def test_answer_pack_rejects_hash_tamper() -> None:
    answer_pack = _answer_pack()
    answer_pack["questions"][0]["answer"] = "사후 변경"

    with pytest.raises(ValueError, match="sha256 mismatch"):
        validate_exploratory_answer_pack(
            answer_pack, _manifest(), _capture()
        )


def test_signal_audit_reports_exact_hits_availability_and_repetition() -> None:
    audit = _audit()

    assert audit["declared_target_count"] == 4
    assert audit["available_target_count"] == 3
    assert audit["missing_target_count"] == 1
    assert audit["graph_summary"]["exact_target_hit_count"] == 3
    assert audit["local_core_summary"]["exact_target_hit_count"] == 0
    assert audit["signal_status"] == "graph_only_predeclared_exact_target_hits"
    assert audit["semantic_equivalence_review_performed"] is False
    assert audit["performance_claim_gate"] is False


def test_signal_audit_fails_closed_on_graph_snapshot_drift() -> None:
    concepts = _concepts()
    concepts.append({"id": "new", "name": "새개념"})

    with pytest.raises(ValueError, match="graph snapshot"):
        build_exploratory_signal_audit(
            _answer_pack(),
            _manifest(),
            _capture(),
            concepts,
            audited_at=TIMESTAMP,
        )


def test_signal_audit_rejects_post_hoc_semantic_relabeling() -> None:
    audit = deepcopy(_audit())
    audit["semantic_equivalence_review_performed"] = True

    with pytest.raises(ValueError, match="semantic relabeling"):
        validate_exploratory_signal_audit(
            audit, _answer_pack(), _manifest(), _capture()
        )


def test_repository_external_teacher_pack_and_signal_audit_validate() -> None:
    manifest = json.loads((
        PROJECT_ROOT
        / "scripts/research/manifests/j1_1_fresh_selection_b_20260720_draft.json"
    ).read_text(encoding="utf-8"))
    capture = json.loads((
        PROJECT_ROOT
        / "scripts/research/inputs/j1_exploratory_pre_answer_probe_b_20260721.json"
    ).read_text(encoding="utf-8"))
    answer_spec = json.loads((
        PROJECT_ROOT
        / "scripts/research/manifests/j1_exploratory_external_teacher_answers_b_20260721.json"
    ).read_text(encoding="utf-8"))
    answer_pack = json.loads((
        PROJECT_ROOT
        / "scripts/research/inputs/j1_exploratory_external_teacher_answers_b_20260721.json"
    ).read_text(encoding="utf-8"))
    audit = json.loads((
        PROJECT_ROOT
        / "claudedocs/research/j1_exploratory_signal_audit_b_20260721.json"
    ).read_text(encoding="utf-8"))

    validate_exploratory_answer_spec(answer_spec, manifest)
    validate_exploratory_answer_pack(answer_pack, manifest, capture)
    validated_audit = validate_exploratory_signal_audit(
        audit, answer_pack, manifest, capture
    )

    assert validated_audit["graph_summary"]["exact_target_hit_count"] == 0
    assert validated_audit["local_core_summary"]["exact_target_hit_count"] == 1
    assert validated_audit["available_target_count"] == 13
    assert validated_audit["missing_target_count"] == 19
