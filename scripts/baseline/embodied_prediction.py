"""
Embodied Next-Frame Prediction — 북극성 지표 (감각운동 예측오차)
==============================================================================
RESEARCH_SYNTHESIS_2026-07-12 gap#5 / PHASE1_PLASTICITY_FINDINGS §5 참조.

왜 이 지표인가 (북극성)
-----------------------
지금까지의 예측오차는 **언어**(대화 concept 공동활성)에 대한 것이었다. 진짜 embodied
자기학습의 척도 = **세계(감각운동 스트림)를 예측하는가**. Quest passthrough는 프레임
시퀀스(연속 <10s 간격)를 준다 → **frame_t 를 보고 frame_t+1 의 객체를 예측**하는 것이
가장 직접적인 "세계 예측오차". 이게 내려가면 = 아기 뇌가 자기 시각경험을 예측하게 됨.

데이터 (measure_embodiment 확인)
--------------------------------
task_type='vision' Experience 45개 = Quest 프레임. >120s gap 으로 세션 분할(주 세션:
30프레임·193s 연속 데스크 장면). frame당 mean 5.4 객체, next-frame Jaccard 0.31(지속성).
frame_t+1 의 **새 객체(=frame_t 에 없던 것)** 예측 = 지속성으로 못 얻는 진짜 예측 신호.

예측기 비교 (동일 프레임 시퀀스)
--------------------------------
- persistence : 다음 프레임 = 현재 프레임 객체 (trivial baseline, Jaccard 0.31이 천장).
- popularity  : 전역 최빈 시각객체 (구조 없는 baseline).
- graph_spread: 현재 프레임 concept 에서 RELATES_TO spreading-activation(누적된 뇌) top-k.
평가: 다음 프레임 객체(전체 & NEW-only) recall@k + 예측집합 Jaccard. graph가 persistence·
popularity 를 (특히 NEW 객체에서) 이기면 = 뇌가 세계의 near-future 를 구조적으로 예측.

Usage:
    python scripts/baseline/embodied_prediction.py
출력: claudedocs/baseline/embodied_<tag>_<YYYYMMDD>.json
"""
from __future__ import annotations
import argparse, json, os, statistics, sys
from collections import defaultdict, Counter
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

SESSION_GAP = 120.0      # 초; 이보다 크면 다른 세션
PPR_ALPHA = 0.7
TOPK = (5, 10)


def load_frames(session):
    rows = session.run(
        "MATCH (e:Experience) WHERE e.task_type='vision' AND e.created_at IS NOT NULL "
        "OPTIONAL MATCH (e)-[:INVOLVES]->(c:Concept) "
        "WITH e, collect(c.name) AS names ORDER BY e.created_at "
        "RETURN e.created_at AS ts, names"
    ).data()
    frames = []
    for r in rows:
        names = [n for n in r["names"] if n]
        if names:
            frames.append((datetime.fromisoformat(r["ts"]).timestamp(), names))
    return frames


def split_sessions(frames):
    if not frames:
        return []
    sessions, cur = [], [frames[0]]
    for i in range(1, len(frames)):
        if frames[i][0] - frames[i - 1][0] > SESSION_GAP:
            sessions.append(cur); cur = []
        cur.append(frames[i])
    sessions.append(cur)
    return sessions


def load_graph(session):
    """전체 RELATES_TO (모든 source) 무향 가중 — 누적된 '뇌'."""
    rows = session.run(
        "MATCH (a:Concept)-[r:RELATES_TO]->(b:Concept) "
        "RETURN a.name AS s, b.name AS t, coalesce(r.strength, r.weight, 0.5) AS w"
    ).data()
    g = nx.Graph()
    for e in rows:
        s, t, w = e["s"], e["t"], e["w"]
        if not s or not t or s == t:
            continue
        if g.has_edge(s, t):
            g[s][t]["weight"] += w
        else:
            g.add_edge(s, t, weight=w)
    return g


def predict_graph(current, g, exclude, all_visual):
    """현재 프레임 concept 들에서 spreading-activation → 후보 점수 dict."""
    seeds = {c: 1.0 for c in current if c in g}
    if not seeds:
        return {}
    try:
        ppr = nx.pagerank(g, alpha=PPR_ALPHA, personalization=seeds, weight="weight",
                          max_iter=200, tol=1e-6)
    except nx.PowerIterationFailedConvergence:
        return {}
    return {n: ppr.get(n, 0.0) for n in all_visual if n not in exclude}


def recall_at_k(scores, targets, k):
    if not targets:
        return None
    ranked = [n for n, _ in sorted(scores.items(), key=lambda kv: -kv[1])[:k]]
    return len(set(ranked) & set(targets)) / len(targets)


def run(tag):
    with GraphDatabase.driver(URI, auth=AUTH, notifications_min_severity="OFF") as d:
        with d.session(database=DB) as s:
            frames = load_frames(s)
            g = load_graph(s)
    sessions = split_sessions(frames)
    usable = [ss for ss in sessions if len(ss) >= 3]
    # 전역 시각 객체 어휘 + 빈도
    vocab = Counter()
    for _t, ns in frames:
        for n in set(ns):
            vocab[n] += 1
    all_visual = list(vocab.keys())

    metrics = defaultdict(lambda: defaultdict(list))   # predictor -> metric -> [vals]
    n_trans = 0
    for sess in usable:
        for i in range(len(sess) - 1):
            cur = set(sess[i][1]); nxt = set(sess[i + 1][1])
            if not cur or not nxt:
                continue
            new = nxt - cur              # 지속성으로 못 얻는 예측대상
            n_trans += 1
            # 예측기별 점수
            persistence = {c: 1.0 for c in cur}
            popularity = {n: vocab[n] for n in all_visual if n not in cur}
            gs = predict_graph(cur, g, exclude=cur, all_visual=all_visual)
            preds = {"persistence": persistence, "popularity": popularity, "graph_spread": gs}
            for name, sc in preds.items():
                for k in TOPK:
                    r_all = recall_at_k({**sc}, nxt, k)
                    r_new = recall_at_k(sc, new, k) if new else None
                    if r_all is not None:
                        metrics[name][f"recall@{k}_all"].append(r_all)
                    if r_new is not None:
                        metrics[name][f"recall@{k}_new"].append(r_new)

    def agg(name):
        return {m: round(statistics.mean(v), 3) for m, v in metrics[name].items() if v}

    result = {
        "tag": tag, "timestamp": datetime.now(timezone.utc).isoformat(),
        "n_frames": len(frames), "n_sessions": len(sessions),
        "n_usable_sessions": len(usable), "n_transitions": n_trans,
        "vocab_size": len(vocab), "graph_nodes": g.number_of_nodes(),
        "predictors": {name: agg(name) for name in ["persistence", "popularity", "graph_spread"]},
    }
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="vision_v1")
    args = ap.parse_args()
    res = run(args.tag)
    print(f"=== EMBODIED NEXT-FRAME PREDICTION (북극성: 세계 예측오차) ===")
    print(f"  frames {res['n_frames']} | usable sessions {res['n_usable_sessions']} "
          f"| transitions {res['n_transitions']} | vocab {res['vocab_size']}")
    print(f"\n  {'predictor':<14}{'R@5_all':>9}{'R@10_all':>10}{'R@5_new':>9}{'R@10_new':>10}")
    for name in ["persistence", "popularity", "graph_spread"]:
        m = res["predictors"][name]
        print(f"  {name:<14}{str(m.get('recall@5_all','-')):>9}{str(m.get('recall@10_all','-')):>10}"
              f"{str(m.get('recall@5_new','-')):>9}{str(m.get('recall@10_new','-')):>10}")
    gs = res["predictors"]["graph_spread"]; pers = res["predictors"]["persistence"]
    pop = res["predictors"]["popularity"]
    new_signal = gs.get("recall@10_new", 0) or 0
    print(f"\n  해석: NEW 객체(지속성이 못 얻는 진짜 예측)에서 graph_spread R@10_new={new_signal}")
    print(f"        vs popularity {pop.get('recall@10_new','-')} — 뇌 구조가 세계 near-future를 "
          f"{'예측함 ✅' if new_signal > (pop.get('recall@10_new',0) or 0) else '아직 약함 🟡'}")
    today = datetime.now().strftime("%Y%m%d")
    path = OUT / f"embodied_{args.tag}_{today}.json"
    path.write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n[out] {path}")


if __name__ == "__main__":
    main()
