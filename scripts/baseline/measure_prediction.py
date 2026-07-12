"""
Prediction Quality Measurement — Phase 1 자기학습 계측 (self-learning metric)
============================================================================
program_roadmap_2026-07 / self_learning_architecture_2026-07 참조.

자기학습의 척도는 "성능"이 아니라 "그래프가 자기 연상구조로 held-out 연결을
얼마나 잘 예측하는가(= 예측오차가 낮아지는가)"이다. 예측기 = spreading-activation
(Personalized PageRank, HippoRAG식). 가소성 규칙(STDP+감쇠+항상성+PE게이팅)을
바꾸기 전/후 이 수치를 비교하면 "그래프가 실제로 더 잘 예측하게 됐는가"를 측정할 수 있다.

방법(standard link-prediction eval):
  Concept–RELATES_TO 무향 가중 그래프 → 엣지 일부를 held-out(test) →
  각 test 엣지 (a,b)에서 a를 seed로 PPR 확산 → b가 a의 비-이웃 후보 중 몇 위로
  예측되는가 → MRR, hit@k, mean_rank, 무작위 대비 lift.

Usage:
    python scripts/baseline/measure_prediction.py --tag before_plasticity
출력: claudedocs/baseline/prediction_<tag>_<YYYYMMDD>.json
"""
from __future__ import annotations
import argparse, json, os, random, statistics, sys
from datetime import datetime, timezone
from pathlib import Path

import networkx as nx
from dotenv import load_dotenv
from neo4j import GraphDatabase

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv(".env")
URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
AUTH = (os.getenv("NEO4J_USERNAME", "neo4j"), os.getenv("NEO4J_PASSWORD", ""))
DB = os.getenv("NEO4J_DATABASE", "neo4j")
OUT = Path(__file__).resolve().parents[2] / "claudedocs" / "baseline"
OUT.mkdir(parents=True, exist_ok=True)

SEED = 42
TEST_FRACTION = 0.2
MAX_TEST = 300          # test 엣지 최대 표본 (속도)
PPR_ALPHA = 0.85
HITS = (1, 5, 10)


def fetch_graph(session, exclude_frozen: bool = True) -> nx.Graph:
    where = ("WHERE a.category <> 'frozen_knowledge' AND b.category <> 'frozen_knowledge'"
             if exclude_frozen else "")
    rows = session.run(
        f"MATCH (a:Concept)-[r:RELATES_TO]->(b:Concept) {where} "
        "RETURN a.name AS s, b.name AS t, coalesce(r.strength, r.weight, 1.0) AS w"
    ).data()
    g = nx.Graph()
    for e in rows:
        if e["s"] == e["t"] or e["s"] is None or e["t"] is None:
            continue
        if g.has_edge(e["s"], e["t"]):
            g[e["s"]][e["t"]]["weight"] += e["w"]
        else:
            g.add_edge(e["s"], e["t"], weight=e["w"])
    return g


def split(g: nx.Graph, rng: random.Random):
    """양끝이 train에서 고립되지 않는 엣지만 held-out."""
    edges = list(g.edges())
    rng.shuffle(edges)
    n_test = min(MAX_TEST, int(len(edges) * TEST_FRACTION))
    train = g.copy()
    test = []
    for (u, v) in edges:
        if len(test) >= n_test:
            break
        if train.degree(u) > 1 and train.degree(v) > 1:
            train.remove_edge(u, v)
            test.append((u, v))
    return train, test


def evaluate(train: nx.Graph, test: list) -> dict:
    nodes = list(train.nodes())
    ranks, recip, cand_counts = [], [], []
    hitk = {k: 0 for k in HITS}
    for (a, b) in test:
        if a not in train or b not in train:
            continue
        ppr = nx.pagerank(train, alpha=PPR_ALPHA, personalization={a: 1.0}, weight="weight")
        exclude = set(train.neighbors(a)); exclude.add(a)
        cands = [n for n in nodes if n not in exclude]
        if b not in cands:
            continue
        ranked = sorted(cands, key=lambda n: ppr.get(n, 0.0), reverse=True)
        r = ranked.index(b) + 1
        ranks.append(r); recip.append(1.0 / r); cand_counts.append(len(cands))
        for k in HITS:
            if r <= k:
                hitk[k] += 1
    m = len(ranks) or 1
    mean_rank = statistics.mean(ranks) if ranks else 0.0
    rand_rank = (statistics.mean(cand_counts) + 1) / 2 if cand_counts else 0.0
    return {
        "n_test_evaluated": len(ranks),
        "MRR": round(statistics.mean(recip), 4) if recip else 0.0,
        "hit@1": round(hitk[1] / m, 4),
        "hit@5": round(hitk[5] / m, 4),
        "hit@10": round(hitk[10] / m, 4),
        "mean_rank": round(mean_rank, 1),
        "median_rank": statistics.median(ranks) if ranks else 0,
        "avg_candidates": round(statistics.mean(cand_counts), 0) if cand_counts else 0,
        "random_expected_rank": round(rand_rank, 1),
        "lift_vs_random": round(rand_rank / mean_rank, 2) if mean_rank else 0.0,
    }


def run(tag: str) -> dict:
    ts = datetime.now(timezone.utc).isoformat()
    rng = random.Random(SEED)
    with GraphDatabase.driver(URI, auth=AUTH, notifications_min_severity="OFF") as d:
        with d.session(database=DB) as s:
            g = fetch_graph(s, exclude_frozen=True)
    print(f"[pred] graph: {g.number_of_nodes()} nodes, {g.number_of_edges()} edges (frozen 제외)")
    train, test = split(g, rng)
    print(f"[pred] split: train {train.number_of_edges()} edges, test {len(test)} edges")
    res = evaluate(train, test)
    res.update({
        "tag": tag, "timestamp": ts,
        "n_nodes": g.number_of_nodes(), "n_edges": g.number_of_edges(),
        "predictor": "Personalized PageRank spreading-activation (HippoRAG식)",
        "seed": SEED, "test_fraction": TEST_FRACTION, "ppr_alpha": PPR_ALPHA,
    })
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="before_plasticity")
    args = ap.parse_args()
    res = run(args.tag)
    print("\n=== PREDICTION QUALITY (Phase 1 자기학습 baseline) ===")
    for k in ["n_test_evaluated", "MRR", "hit@1", "hit@5", "hit@10",
              "mean_rank", "median_rank", "avg_candidates",
              "random_expected_rank", "lift_vs_random"]:
        print(f"  {k}: {res[k]}")
    print(f"\n  해석: 그래프가 참 이웃을 무작위 대비 평균 {res['lift_vs_random']}배 상위로 예측 "
          f"(1.0=무작위, 클수록 구조적 예측력↑). 이 값이 가소성 규칙 개선 후 오르면 = 자기학습.")
    today = datetime.now().strftime("%Y%m%d")
    path = OUT / f"prediction_{args.tag}_{today}.json"
    path.write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n[out] {path}")


if __name__ == "__main__":
    main()
