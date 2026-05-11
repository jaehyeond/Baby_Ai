"""
Baby AI Graph Functional Baseline Tests
=========================================
구조 메트릭(measure_baseline.py)이 "건강한 그래프 형태"를 본다면,
이 스크립트는 "그래프가 의도된 기능을 수행하는가"를 본다.

테스트:
1. Identity reachability  — 정체성 concept이 hub로 작동하는가
2. Spreading activation reach — 임의 seed에서 K hop 도달 비율
3. Color binding precision — A4.4 색상 binding이 그래프에 반영됐는가

LLM 호출 없음. 순수 graph query만.

Usage:
    python scripts/baseline/functional_tests.py --tag before_adgr
"""
from __future__ import annotations

import argparse
import json
import os
import random
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from neo4j import GraphDatabase


load_dotenv()
URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
AUTH = (os.getenv("NEO4J_USERNAME", "neo4j"), os.getenv("NEO4J_PASSWORD", ""))
DB = os.getenv("NEO4J_DATABASE", "neo4j")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = PROJECT_ROOT / "claudedocs" / "baseline"
OUT_DIR.mkdir(parents=True, exist_ok=True)

SEED = 42
SAMPLE_SIZE_FOR_REACH = 30      # spreading activation seed sample size


# ── Test 1: Identity reachability ────────────────────────────────────────────
def test_identity_reach(session) -> dict:
    """비비/엄마 같은 정체성 concept이 임의 concept과 K hop 안에 연결되는가.

    가설: 정체성이 hub면, 무작위 concept에서 정체성으로 평균 path가 짧아야 한다.
    """
    # 2026-05-08 수정: '엄마/mom/dad/baby' 제거 — 사용 데이터 거의 없음, 양육자 역할은 사용자/개발자.
    # 미래 가족 시나리오에서 다시 추가할 수 있음 (제거 아닌 비활성).
    identity_names = ['비비', 'AI', '사용자', '개발자']

    results = {}
    for name in identity_names:
        row = session.run(
            """
            MATCH (target:Concept) WHERE target.name = $name
            OPTIONAL MATCH (target)-[r:RELATES_TO]-()
            RETURN id(target) AS id, count(r) AS degree
            """, name=name
        ).single()
        if not row or row["id"] is None:
            results[name] = {"exists": False}
            continue

        # 무작위 50개 concept에서 이 target까지 shortest path
        paths = session.run(
            """
            MATCH (target:Concept) WHERE target.name = $name
            MATCH (src:Concept) WHERE src <> target
            WITH target, src, rand() AS r ORDER BY r LIMIT 50
            OPTIONAL MATCH p = shortestPath((src)-[:RELATES_TO*..6]-(target))
            RETURN
                count(CASE WHEN p IS NOT NULL THEN 1 END) AS reachable,
                avg(length(p)) AS avg_len,
                max(length(p)) AS max_len,
                count(*) AS sampled
            """, name=name
        ).single()
        results[name] = {
            "exists": True,
            "degree": row["degree"],
            "reachable_in_6hop": paths["reachable"],
            "sampled": paths["sampled"],
            "reach_ratio": paths["reachable"] / paths["sampled"] if paths["sampled"] else 0,
            "avg_hop": paths["avg_len"],
            "max_hop": paths["max_len"],
        }
    return results


# ── Test 2: Spreading activation reach ──────────────────────────────────────
def test_spreading_reach(session, k_hop: int = 3) -> dict:
    """무작위 seed concept에서 K hop 안에 도달 가능한 concept 수.

    spreading activation의 effective reach 측정. 작으면 그래프가 너무 sparse.
    """
    rng = random.Random(SEED)

    # 1. 전체 concept count
    total = session.run("MATCH (c:Concept) RETURN count(c) AS n").single()["n"]

    # 2. 무작위 seed concept 샘플
    seeds = session.run(
        """
        MATCH (c:Concept) WITH c, rand() AS r ORDER BY r LIMIT $n
        RETURN c.name AS name, id(c) AS id
        """, n=SAMPLE_SIZE_FOR_REACH
    ).data()

    reaches = []
    for s in seeds:
        row = session.run(
            f"""
            MATCH (seed:Concept) WHERE id(seed) = $sid
            MATCH (seed)-[:RELATES_TO*1..{k_hop}]-(reached:Concept)
            RETURN count(DISTINCT reached) AS n
            """, sid=s["id"]
        ).single()
        reaches.append({"seed": s["name"], "reach": row["n"]})

    if not reaches:
        return {"empty": True}

    rs = [r["reach"] for r in reaches]
    return {
        "k_hop": k_hop,
        "total_concepts": total,
        "samples": len(reaches),
        "avg_reach": sum(rs) / len(rs),
        "median_reach": sorted(rs)[len(rs) // 2],
        "max_reach": max(rs),
        "min_reach": min(rs),
        "avg_reach_ratio": (sum(rs) / len(rs)) / total,
        "samples_top5": sorted(reaches, key=lambda x: x["reach"], reverse=True)[:5],
        "samples_bottom5": sorted(reaches, key=lambda x: x["reach"])[:5],
    }


# ── Test 3: Color binding precision (A4.4 검증) ──────────────────────────────
def test_color_binding(session) -> dict:
    """A4.4 색상 binding이 그래프에 어떻게 반영됐는지 확인.

    경로 1: c.color 속성으로 직접 binding (인접 규칙)
    경로 2: 색상 concept이 별도로 남아 RELATES_TO로 연결

    질문: 색상 단어가 hub 상위에 있다 = binding 실패 (별 concept으로 폭증)
          색상 단어가 적다 = binding 성공
    """
    color_words = ['red', 'blue', 'green', 'yellow', 'white', 'black', 'orange',
                   'purple', 'pink', '빨강', '파랑', '노랑', '초록', '하양']

    standalone = session.run(
        """
        MATCH (c:Concept) WHERE c.name IN $cw
        OPTIONAL MATCH (c)-[r:RELATES_TO]-()
        RETURN c.name AS name, count(r) AS degree, c.usage_count AS usage,
               coalesce(c.quest_observation_count, 0) AS qcnt
        ORDER BY degree DESC
        """, cw=color_words
    ).data()

    # A4.4 binding: relation_type='describes_color' 인 RELATES_TO edge
    # (수정 2026-05-08: 이전 버전은 c.color 속성을 봤는데 실제론 edge 구현이라 항상 0이 나왔음)
    bound = session.run(
        """
        MATCH (d:Concept)-[r:RELATES_TO {relation_type: 'describes_color'}]->(o:Concept)
        RETURN count(r) AS n_bindings,
               count(DISTINCT o) AS n_bound_objects,
               collect({color: d.name, obj: o.name, count: r.observation_count})[..15] AS samples
        """
    ).single()

    return {
        "standalone_color_concepts": standalone,
        "n_describes_color_edges": bound["n_bindings"],
        "n_bound_objects": bound["n_bound_objects"],
        "binding_samples": bound["samples"],
        "verdict": _color_verdict(standalone, bound["n_bindings"], bound["n_bound_objects"]),
    }


def _color_verdict(standalone: list, n_bindings: int, n_bound_objects: int) -> str:
    high_deg = [s for s in standalone if s["degree"] > 20]
    if n_bindings == 0:
        if high_deg:
            return f"NO BINDING - {len(high_deg)} color words operate as standalone hubs (binding pipeline broken or unused)"
        return "no color data - either insufficient color exposure or VLM not producing color tokens"
    if n_bindings >= len(high_deg):
        return f"binding working - {n_bindings} describes_color edges across {n_bound_objects} objects, {len(high_deg)} standalone color hubs (acceptable)"
    return f"binding partial - {n_bindings} edges but {len(high_deg)} color hubs still high-degree (possible parser misses)"


# ── Main ────────────────────────────────────────────────────────────────────
def run(tag: str) -> dict:
    timestamp = datetime.now(timezone.utc).isoformat()
    print(f"[Functional] tag={tag}")
    with GraphDatabase.driver(URI, auth=AUTH) as driver:
        with driver.session(database=DB) as session:
            print("[1/3] Identity reachability...")
            t1 = test_identity_reach(session)
            for name, r in t1.items():
                if r.get("exists"):
                    print(f"      {name}: deg={r['degree']}, reach={r['reach_ratio']*100:.0f}% in 6hop, avg_hop={r.get('avg_hop')}")
                else:
                    print(f"      {name}: NOT FOUND")

            print("[2/3] Spreading activation reach (k=3)...")
            t2 = test_spreading_reach(session, k_hop=3)
            print(f"      avg_reach={t2.get('avg_reach', 0):.1f} ({t2.get('avg_reach_ratio', 0)*100:.1f}% of graph)")

            print("[3/3] Color binding (A4.4)...")
            t3 = test_color_binding(session)
            print(f"      describes_color_edges={t3['n_describes_color_edges']}, "
                  f"bound_objects={t3['n_bound_objects']}, "
                  f"standalone_colors={len(t3['standalone_color_concepts'])}")
            print(f"      → {t3['verdict']}")

    return {
        "tag": tag,
        "timestamp": timestamp,
        "tests": {
            "identity_reach": t1,
            "spreading_reach_k3": t2,
            "color_binding": t3,
        },
    }


def write_output(result: dict, tag: str) -> Path:
    today = datetime.now().strftime("%Y%m%d")
    p = OUT_DIR / f"functional_{tag}_{today}.json"
    with p.open("w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False, default=str)
    return p


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", default="initial")
    args = parser.parse_args()

    result = run(args.tag)
    p = write_output(result, args.tag)
    print(f"\n[Output] {p}")
