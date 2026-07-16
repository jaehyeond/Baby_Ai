from scripts.research.graph_replay_split import (
    build_edge_disjoint_split,
    canonical_pair,
    collapse_undirected_pairs,
)


def test_parallel_and_reverse_relationships_collapse_before_split() -> None:
    edges = [
        ("비비", "형", 0.2),
        ("형", "비비", 0.7),
        ("비비", "형", 0.5),
        ("비비", "컴퓨터", 0.3),
    ]

    collapsed = collapse_undirected_pairs(edges)

    assert collapsed == [
        ("비비", "컴퓨터", 0.3),
        ("비비", "형", 0.7),
    ]


def test_split_is_deterministic_and_pair_disjoint() -> None:
    edges = [
        (f"개념{i}", f"개념{i + 1}", 0.1 + i / 100)
        for i in range(20)
    ]
    edges.extend([
        ("개념2", "개념1", 0.9),
        ("개념1", "개념2", 0.4),
    ])

    first = build_edge_disjoint_split(edges, seed=42, max_test=5)
    second = build_edge_disjoint_split(list(reversed(edges)), seed=42, max_test=5)
    train_pairs = {canonical_pair(a, b) for a, b, _ in first.train_edges}
    test_pairs = {canonical_pair(a, b) for a, b, _ in first.test_edges}

    assert first == second
    assert train_pairs.isdisjoint(test_pairs)
    assert first.diagnostics["duplicate_pair_row_count"] == 2
    assert first.diagnostics["train_test_pair_overlap_count"] == 0


def test_isolated_evaluation_endpoint_is_dropped_not_returned_to_training() -> None:
    split = build_edge_disjoint_split(
        [("a", "b", 1.0), ("b", "c", 1.0)],
        seed=1,
        max_test=1,
        test_fraction=0.5,
    )

    assert len(split.train_edges) == 1
    assert split.test_edges == []
    assert split.diagnostics["requested_test_pair_count"] == 1
    assert split.diagnostics["eligible_test_pair_count"] == 0
