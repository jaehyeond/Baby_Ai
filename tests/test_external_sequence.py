import pytest

from neural.baby.external_sequence import (
    parse_external_sequence_context,
    validate_external_sequence_state,
)


HASH_A = "a" * 64
HASH_B = "b" * 64


def _context(**overrides):
    value = {
        "external_sequence_id": "b5_3_train_a",
        "external_turn_index": 0,
        "external_sequence_split": "train",
        "external_sequence_contract_sha256": HASH_A,
    }
    value.update(overrides)
    return value


def _turn(index: int, *, split: str = "train", contract_hash: str = HASH_A):
    return {
        "turn_index": index,
        "split": split,
        "contract_sha256": contract_hash,
    }


def test_parse_external_sequence_context_normalizes_safe_values() -> None:
    parsed = parse_external_sequence_context(_context(
        external_sequence_id=" B5_3.Train-A ",
        external_sequence_split=" TRAIN ",
        external_sequence_contract_sha256=HASH_A.upper(),
    ))

    assert parsed == {
        "sequence_id": "b5_3.train-a",
        "turn_index": 0,
        "split": "train",
        "contract_sha256": HASH_A,
    }


@pytest.mark.parametrize(
    "overrides",
    [
        {"external_sequence_id": "x"},
        {"external_sequence_id": "bad/id"},
        {"external_turn_index": True},
        {"external_turn_index": -1},
        {"external_sequence_split": "validation"},
        {"external_sequence_contract_sha256": "abc"},
    ],
)
def test_parse_external_sequence_context_rejects_invalid_values(overrides) -> None:
    with pytest.raises(ValueError):
        parse_external_sequence_context(_context(**overrides))


def test_sequence_state_accepts_only_the_next_contiguous_turn() -> None:
    contract = parse_external_sequence_context(_context(external_turn_index=2))

    result = validate_external_sequence_state(contract, [_turn(0), _turn(1)])

    assert result == {
        "status": "valid",
        "reason": None,
        "expected_turn_index": 2,
    }


def test_sequence_state_rejects_duplicate_and_gap() -> None:
    duplicate = validate_external_sequence_state(
        parse_external_sequence_context(_context(external_turn_index=1)),
        [_turn(0), _turn(1)],
    )
    gap = validate_external_sequence_state(
        parse_external_sequence_context(_context(external_turn_index=2)),
        [_turn(0)],
    )

    assert duplicate["reason"] == "duplicate_turn_index"
    assert gap == {
        "status": "rejected",
        "reason": "out_of_order_turn",
        "expected_turn_index": 1,
    }


def test_sequence_state_rejects_split_hash_and_cross_split_reuse() -> None:
    contract = parse_external_sequence_context(_context(external_turn_index=1))

    assert validate_external_sequence_state(
        contract,
        [_turn(0, split="heldout")],
    )["reason"] == "sequence_split_mismatch"
    assert validate_external_sequence_state(
        contract,
        [_turn(0, contract_hash=HASH_B)],
    )["reason"] == "sequence_contract_mismatch"
    assert validate_external_sequence_state(
        contract,
        [_turn(0)],
        conflicting_split_count=1,
    )["reason"] == "contract_reused_across_splits"


def test_sequence_state_rejects_corrupt_existing_history() -> None:
    contract = parse_external_sequence_context(_context(external_turn_index=2))

    assert validate_external_sequence_state(
        contract,
        [_turn(0), _turn(0)],
    )["reason"] == "invalid_existing_duplicate_turn"
    assert validate_external_sequence_state(
        contract,
        [_turn(0), _turn(2)],
    )["reason"] == "invalid_existing_sequence_gap"
