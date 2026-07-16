from argparse import Namespace
from pathlib import Path

from scripts.research import b5_9_semantic_outcome_contract as b59


def test_repository_reviewed_report_stays_offline_and_blocked(tmp_path: Path) -> None:
    report = b59.run(Namespace(
        manifest=b59.DEFAULT_MANIFEST,
        answers=b59.DEFAULT_ANSWERS,
        b5_8_artifact=b59.DEFAULT_B5_8_ARTIFACT,
        labels=b59.DEFAULT_LABELS,
        output=tmp_path / "unused.json",
        compact=False,
    ))

    assert report["phase"] == "B5.9"
    assert report["review_status"] == "user_reviewed"
    assert report["question_count"] == 6
    assert report["semantic_label_count"] == 25
    assert report["relation_proposal"]["relation_proposal_count"] == 25
    assert report["semantic_target_validity_gate"] is True
    assert report["database_writes"] is False
    assert report["heldout_gate"] is False
    assert report["production_promotion_gate"] is False
    assert report["next_step"] == (
        "review_relation_schema_and_keep_train_only_until_clean_signal"
    )


def test_b5_9_module_has_no_database_write_query() -> None:
    source = b59.__file__ and Path(b59.__file__).read_text(encoding="utf-8").upper()

    for mutation in (" CREATE ", " MERGE ", " SET ", " DELETE ", " REMOVE "):
        assert mutation not in source
