"""Leakage-resistant graph split helpers for sleep-distillation research.

Neo4j can contain several ``RELATES_TO`` relationships for the same concept
pair (different sources or relation types).  Splitting relationship rows lets
one copy of a pair enter evaluation while another copy remains in training.
This module collapses undirected pairs before making a deterministic split.
"""

from __future__ import annotations

import random
from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable


Edge = tuple[str, str, float]


@dataclass(frozen=True)
class GraphReplaySplit:
    train_edges: list[Edge]
    test_edges: list[Edge]
    train_adjacency: dict[str, dict[str, float]]
    diagnostics: dict[str, int]


def canonical_pair(a: str, b: str) -> tuple[str, str]:
    """Return an order-independent, deterministic concept-pair key."""

    return (a, b) if a <= b else (b, a)


def collapse_undirected_pairs(edges: Iterable[Edge]) -> list[Edge]:
    """Keep one maximum-weight edge per undirected concept pair."""

    strongest: dict[tuple[str, str], float] = {}
    for raw_a, raw_b, raw_weight in edges:
        a = str(raw_a).strip()
        b = str(raw_b).strip()
        if not a or not b or a == b:
            continue
        key = canonical_pair(a, b)
        weight = float(raw_weight)
        strongest[key] = max(strongest.get(key, weight), weight)
    return [(a, b, strongest[(a, b)]) for a, b in sorted(strongest)]


def build_edge_disjoint_split(
    edges: Iterable[Edge],
    *,
    seed: int,
    max_test: int = 250,
    test_fraction: float = 0.2,
) -> GraphReplaySplit:
    """Create a deterministic pair-disjoint train/evaluation split.

    Evaluation pairs whose endpoints become isolated after removal are dropped.
    They are not returned to training because that would reintroduce leakage.
    """

    raw_edges = list(edges)
    unique_edges = collapse_undirected_pairs(raw_edges)
    shuffled = list(unique_edges)
    random.Random(seed).shuffle(shuffled)

    if len(shuffled) < 2:
        requested_test_count = 0
    else:
        requested_test_count = min(
            max(0, int(max_test)),
            max(1, int(len(shuffled) * test_fraction)),
        )
        requested_test_count = min(requested_test_count, len(shuffled) - 1)

    requested_test = shuffled[:requested_test_count]
    train_edges = shuffled[requested_test_count:]
    train_adjacency: defaultdict[str, dict[str, float]] = defaultdict(dict)
    for a, b, weight in train_edges:
        train_adjacency[a][b] = max(train_adjacency[a].get(b, weight), weight)
        train_adjacency[b][a] = max(train_adjacency[b].get(a, weight), weight)

    test_edges = [
        edge
        for edge in requested_test
        if edge[0] in train_adjacency and edge[1] in train_adjacency
    ]
    train_pairs = {canonical_pair(a, b) for a, b, _ in train_edges}
    test_pairs = {canonical_pair(a, b) for a, b, _ in test_edges}
    overlap_count = len(train_pairs & test_pairs)
    if overlap_count:
        raise AssertionError("train/evaluation concept pairs overlap")

    return GraphReplaySplit(
        train_edges=train_edges,
        test_edges=test_edges,
        train_adjacency={
            name: dict(neighbors) for name, neighbors in train_adjacency.items()
        },
        diagnostics={
            "raw_edge_count": len(raw_edges),
            "unique_pair_count": len(unique_edges),
            "duplicate_pair_row_count": len(raw_edges) - len(unique_edges),
            "train_pair_count": len(train_pairs),
            "requested_test_pair_count": requested_test_count,
            "eligible_test_pair_count": len(test_edges),
            "train_test_pair_overlap_count": overlap_count,
        },
    )
