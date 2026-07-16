from neural.baby.question_experiment import audit_legacy_j1_readiness


def test_legacy_audit_does_not_invent_probabilities() -> None:
    manifest = {
        "contract_sha256": "a" * 64,
        "questions": [
            {"order": 0, "question": "컴퓨터를 설명해줘"},
            {"order": 1, "question": "이야기를 설명해줘"},
        ],
    }
    b5_7 = {"learning_state_updates": False}
    b5_8 = {
        "questions": [
            {"order": 0, "baseline_predicted_ids": ["information"]},
            {"order": 1, "baseline_predicted_ids": ["story"]},
        ]
    }
    labels = {
        "review_status": "user_reviewed",
        "entries": [
            {
                "order": 0,
                "question_id": "question-0",
                "labels": [{"concept_id": "information", "decision": "approved"}],
            },
            {
                "order": 1,
                "question_id": "question-1",
                "labels": [{"concept_id": "story", "decision": "approved"}],
            },
        ],
    }

    report = audit_legacy_j1_readiness(manifest, b5_7, b5_8, labels)

    assert report["status"] == "blocked"
    assert report["readiness_gates"]["historical_ranked_graph_ids_present"] is True
    assert report["readiness_gates"]["calibrated_graph_probability_snapshots"] is False
    assert report["readiness_gates"]["local_core_probability_snapshots"] is False
    assert report["readiness_gates"]["sealed_probability_calibrators"] is False
    assert report["contract_gate"] is False
    assert report["learning_enabled"] is False
    assert report["database_writes"] is False
