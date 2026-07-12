"""
Brain Health Monitor — Gap#6 상시 모니터링 (CL 실패모드 조기경보)
==============================================================================
RESEARCH_SYNTHESIS_2026-07-12 §3 gap#6 참조.

왜 (리서치 처방)
----------------
"lift 숫자 하나로는 forgetting/collapse/plasticity-loss 를 못 본다." 자기학습 시스템은
개선처럼 보이면서 실제론 (a) 예측력 저하 (b) 허브 붕괴/가중치 collapse (c) 과거 지식 망각
(d) 새 연상 학습능력 상실(plasticity loss) 로 무너질 수 있다. → **4-지표 시계열을 정기적으로
append + 임계 알림.** 데이터가 쌓이기 시작하면 추세를 즉시 본다.

4 지표
------
1. prediction : held-out link-prediction lift/MRR (구조적 예측력) — measure_prediction 재사용.
2. collapse   : degree Gini + 가중치 엔트로피 + 고립률 + 최대허브 (허브지배/붕괴 감지).
3. forgetting : **고정 probe 집합**(첫 실행시 강한 엣지 표본 저장)의 recall@10 — 시간에 따라
                내려가면 망각. (decay/pruning 이 과거 연상을 지우는지 감시.)
4. plasticity : 신규 연상 즉시 학습·회상 가능한가 (synthetic 쌍 주입→PPR 상위 확인→rollback).
                *진짜 plasticity-loss(가중치)는 Phase 2 코어 이후. 여기선 그래프 메커니즘 헬스.*

출력: claudedocs/monitoring/brain_health.jsonl (append, 한 줄=한 실행) + 콘솔 요약(직전 대비 추세).
probe 집합: claudedocs/monitoring/forgetting_probe.json (첫 실행시 생성, 이후 고정).

Usage:
    python scripts/monitoring/brain_health_monitor.py
    python scripts/monitoring/brain_health_monitor.py --reset-probe   # probe 재생성
상시화: nightly cron / 스케줄 라우틴 / consolidate 후 호출 (README 참조).
"""
from __future__ import annotations
import argparse, json, math, os, random, statistics, sys
from datetime import datetime, timezone
from pathlib import Path

import networkx as nx
from dotenv import load_dotenv
from neo4j import GraphDatabase

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "baseline"))
import measure_prediction as MP     # fetch_graph, split, evaluate 재사용

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv(".env")
URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
AUTH = (os.getenv("NEO4J_USERNAME", "neo4j"), os.getenv("NEO4J_PASSWORD", ""))
DB = os.getenv("NEO4J_DATABASE", "neo4j")
OUT = Path(__file__).resolve().parents[2] / "claudedocs" / "monitoring"
OUT.mkdir(parents=True, exist_ok=True)
LOG = OUT / "brain_health.jsonl"
PROBE = OUT / "forgetting_probe.json"

SEED = 42
PROBE_SIZE = 30
PPR_ALPHA = 0.85

# 임계값 (breach 시 alert). 초기값 — 데이터 쌓이며 조정.
THRESH = {
    "isolated_ratio_max": 0.55,     # 고립 노드 비율 상한
    "degree_gini_max": 0.88,        # 허브지배 상한
    "weight_entropy_min": 0.35,     # 가중치 엔트로피 하한(붕괴)
    "prediction_lift_min": 2.0,     # 구조적 예측력 하한
    "forgetting_recall_drop_max": 0.20,  # baseline 대비 recall 하락 상한
}


# ── 2. collapse 지표 ────────────────────────────────────────────────────────
def gini(values):
    v = sorted(x for x in values if x >= 0)
    n = len(v)
    if n == 0 or sum(v) == 0:
        return 0.0
    cum = sum((i + 1) * x for i, x in enumerate(v))
    return (2 * cum) / (n * sum(v)) - (n + 1) / n


def collapse_metrics(g: nx.Graph, total_concepts: int) -> dict:
    degs = [d for _n, d in g.degree()]
    weights = [d["weight"] for _u, _v, d in g.edges(data=True)]
    connected = g.number_of_nodes()          # 엣지가 하나라도 있는 concept
    # 고립률 = 전체 Concept 중 엣지 없는 것 (fetch_graph는 엣지그래프라 별도 total 필요)
    isolated = max(0, total_concepts - connected)
    # 가중치 Shannon 엔트로피 정규화 [0,1]
    tot = sum(weights) or 1.0
    ps = [w / tot for w in weights if w > 0]
    H = -sum(p * math.log(p) for p in ps) if ps else 0.0
    Hn = H / math.log(len(ps)) if len(ps) > 1 else 0.0
    return {
        "total_concepts": total_concepts,
        "connected_nodes": connected, "n_edges": g.number_of_edges(),
        "isolated_ratio": round(isolated / total_concepts, 4) if total_concepts else 0.0,
        "degree_gini": round(gini(degs), 4),
        "weight_entropy": round(Hn, 4),
        "max_hub_degree": max(degs) if degs else 0,
        "mean_degree": round(statistics.mean(degs), 2) if degs else 0.0,
    }


# ── 1. prediction 지표 (measure_prediction 재사용) ──────────────────────────
def prediction_metric(g: nx.Graph) -> dict:
    rng = random.Random(SEED)
    train, test = MP.split(g, rng)
    if not test:
        return {"lift_vs_random": 0.0, "MRR": 0.0, "n_test": 0}
    res = MP.evaluate(train, test)
    return {"lift_vs_random": res["lift_vs_random"], "MRR": res["MRR"],
            "hit@10": res["hit@10"], "n_test": res["n_test_evaluated"]}


# ── 3. forgetting 지표 (고정 probe) ─────────────────────────────────────────
def load_or_make_probe(g: nx.Graph, reset=False) -> list:
    if PROBE.exists() and not reset:
        return json.loads(PROBE.read_text(encoding="utf-8"))["pairs"]
    # 강한 엣지 표본 (strength 상위) 을 고정 probe 로
    edges = sorted(g.edges(data=True), key=lambda e: -e[2].get("weight", 0))
    rng = random.Random(SEED)
    strong = [(u, v) for u, v, _d in edges[:PROBE_SIZE * 3]]
    rng.shuffle(strong)
    pairs = strong[:PROBE_SIZE]
    PROBE.write_text(json.dumps({"created": datetime.now(timezone.utc).isoformat(),
                                 "pairs": pairs}, ensure_ascii=False, indent=2),
                     encoding="utf-8")
    return pairs


def forgetting_metric(g: nx.Graph, pairs: list) -> dict:
    nodes = set(g.nodes())
    hits, evald = 0, 0
    for (a, b) in pairs:
        if a not in nodes or b not in nodes:
            continue    # 노드 자체가 사라짐 = 강한 망각
        evald += 1
        ppr = nx.pagerank(g, alpha=PPR_ALPHA, personalization={a: 1.0}, weight="weight")
        top = [n for n, _ in sorted(ppr.items(), key=lambda kv: -kv[1])[:11] if n != a][:10]
        if b in top:
            hits += 1
    return {"probe_size": len(pairs), "probe_evaluable": evald,
            "recall@10": round(hits / len(pairs), 4) if pairs else 0.0,
            "nodes_missing": len(pairs) - evald}


# ── 4. plasticity 지표 (주입→회상→rollback, 비파괴) ─────────────────────────
def plasticity_probe(session) -> dict:
    ok = False
    rank = None
    try:
        session.run("MATCH (c:Concept) WHERE c.id STARTS WITH '__health_' DETACH DELETE c")
        session.run(
            "CREATE (a:Concept {id:'__health_A', name:'__health_A', category:'probe'}) "
            "CREATE (b:Concept {id:'__health_B', name:'__health_B', category:'probe'}) "
            "CREATE (a)-[:RELATES_TO {strength:0.8, source:'health_probe'}]->(b)"
        )
        # 신규 연상이 즉시 회상되는가: A 이웃에 B 있는가 + strength
        rec = session.run(
            "MATCH (a:Concept {id:'__health_A'})-[r:RELATES_TO]->(b:Concept {id:'__health_B'}) "
            "RETURN r.strength AS s"
        ).single()
        ok = bool(rec and rec["s"] and rec["s"] >= 0.8)
        rank = 1 if ok else None
    except Exception as e:
        ok = False
        rank = f"error: {e}"
    finally:
        session.run("MATCH (c:Concept) WHERE c.id STARTS WITH '__health_' DETACH DELETE c")
    return {"can_learn_new_assoc": ok, "recall_rank": rank}


def evaluate_alerts(snap: dict, baseline_recall: float | None) -> list:
    a = []
    c, p, f = snap["collapse"], snap["prediction"], snap["forgetting"]
    if c["isolated_ratio"] > THRESH["isolated_ratio_max"]:
        a.append(f"isolated_ratio {c['isolated_ratio']} > {THRESH['isolated_ratio_max']}")
    if c["degree_gini"] > THRESH["degree_gini_max"]:
        a.append(f"degree_gini {c['degree_gini']} > {THRESH['degree_gini_max']} (허브지배)")
    if c["weight_entropy"] < THRESH["weight_entropy_min"]:
        a.append(f"weight_entropy {c['weight_entropy']} < {THRESH['weight_entropy_min']} (붕괴)")
    if p["lift_vs_random"] < THRESH["prediction_lift_min"]:
        a.append(f"prediction_lift {p['lift_vs_random']} < {THRESH['prediction_lift_min']}")
    if baseline_recall is not None:
        drop = baseline_recall - f["recall@10"]
        if drop > THRESH["forgetting_recall_drop_max"]:
            a.append(f"forgetting: recall {f['recall@10']} vs baseline {baseline_recall} (drop {round(drop,3)})")
    if not snap["plasticity"]["can_learn_new_assoc"]:
        a.append("plasticity: 신규 연상 학습/회상 실패!")
    return a


def read_last_log() -> dict | None:
    if not LOG.exists():
        return None
    lines = [l for l in LOG.read_text(encoding="utf-8").splitlines() if l.strip()]
    return json.loads(lines[-1]) if lines else None


def read_first_recall() -> float | None:
    if not LOG.exists():
        return None
    for l in LOG.read_text(encoding="utf-8").splitlines():
        if l.strip():
            try:
                return json.loads(l)["forgetting"]["recall@10"]
            except Exception:
                continue
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reset-probe", action="store_true")
    args = ap.parse_args()

    with GraphDatabase.driver(URI, auth=AUTH, notifications_min_severity="OFF") as d:
        with d.session(database=DB) as s:
            g = MP.fetch_graph(s, exclude_frozen=True)
            tc_rec = s.run(
                "MATCH (c:Concept) WHERE coalesce(c.category,'') <> 'frozen_knowledge' "
                "RETURN count(c) AS n"
            ).single()
            total_concepts = tc_rec["n"] if tc_rec else g.number_of_nodes()
            probe = load_or_make_probe(g, reset=args.reset_probe)
            snap = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "prediction": prediction_metric(g),
                "collapse": collapse_metrics(g, total_concepts),
                "forgetting": forgetting_metric(g, probe),
                "plasticity": plasticity_probe(s),
            }

    baseline_recall = read_first_recall()
    prev = read_last_log()
    snap["alerts"] = evaluate_alerts(snap, baseline_recall)
    snap["health"] = "🔴 ALERT" if snap["alerts"] else "🟢 OK"

    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(snap, ensure_ascii=False) + "\n")

    # ── 콘솔 요약 (직전 대비 추세) ──
    def trend(cur, key_path):
        if not prev:
            return ""
        try:
            p = prev
            for k in key_path:
                p = p[k]
            c = snap
            for k in key_path:
                c = c[k]
            if isinstance(c, (int, float)) and isinstance(p, (int, float)):
                dd = round(c - p, 4)
                return f" ({'+' if dd >= 0 else ''}{dd})"
        except Exception:
            pass
        return ""

    p, c, f, pl = snap["prediction"], snap["collapse"], snap["forgetting"], snap["plasticity"]
    print(f"=== BRAIN HEALTH MONITOR (Gap#6) — {snap['health']} ===")
    print(f"  graph: {c['total_concepts']} concepts ({c['connected_nodes']} connected) / {c['n_edges']} edges")
    print(f"  [1 예측력]  lift={p['lift_vs_random']}{trend(snap,['prediction','lift_vs_random'])}  "
          f"MRR={p['MRR']}  hit@10={p.get('hit@10')}")
    print(f"  [2 붕괴]    isolated={c['isolated_ratio']}{trend(snap,['collapse','isolated_ratio'])}  "
          f"gini={c['degree_gini']}{trend(snap,['collapse','degree_gini'])}  "
          f"W-entropy={c['weight_entropy']}  maxhub={c['max_hub_degree']}")
    print(f"  [3 망각]    recall@10={f['recall@10']}{trend(snap,['forgetting','recall@10'])}  "
          f"(probe {f['probe_evaluable']}/{f['probe_size']}, missing {f['nodes_missing']}"
          f"{', baseline '+str(baseline_recall) if baseline_recall is not None else ''})")
    print(f"  [4 가소성]  신규연상 학습·회상: {'✅' if pl['can_learn_new_assoc'] else '❌'}")
    if snap["alerts"]:
        print("\n  🔴 경보:")
        for al in snap["alerts"]:
            print(f"    - {al}")
    else:
        print("\n  🟢 모든 지표 정상 범위")
    n_runs = sum(1 for _l in LOG.read_text(encoding='utf-8').splitlines() if _l.strip())
    print(f"\n[log] {LOG}  (누적 {n_runs} runs)")


if __name__ == "__main__":
    main()
