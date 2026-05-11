"""
Baby AI Graph Baseline Measurement
===================================
현재 Concept/RELATES_TO 그래프의 구조적 baseline을 측정한다.
Agentic Deep Graph Reasoning 도입 전후 비교용.

Usage:
    python scripts/baseline/measure_baseline.py
    python scripts/baseline/measure_baseline.py --tag "before_adgr_v1"

출력:
    claudedocs/baseline/baseline_<tag>_<YYYYMMDD>.json   # 머신용
    claudedocs/baseline/baseline_<tag>_<YYYYMMDD>.md     # 사람용

설계 결정 (Step 3 분석 결과):
    - Neo4j GDS 미설치 → networkx로 modularity/betweenness 계산
    - shortest path: 100쌍 sampling (전체 N×N 비싸므로)
    - power-law: scipy linear regression (log-log fit)
"""
from __future__ import annotations

import argparse
import json
import os
import random
import statistics
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import networkx as nx
from dotenv import load_dotenv
from neo4j import GraphDatabase
from networkx.algorithms.community import louvain_communities, modularity
from scipy import stats


# ── Config ────────────────────────────────────────────────────────────────────
load_dotenv()
URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
AUTH = (os.getenv("NEO4J_USERNAME", "neo4j"), os.getenv("NEO4J_PASSWORD", ""))
DB = os.getenv("NEO4J_DATABASE", "neo4j")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = PROJECT_ROOT / "claudedocs" / "baseline"
OUT_DIR.mkdir(parents=True, exist_ok=True)

PATH_SAMPLE_PAIRS = 200    # Sample size for shortest-path
SEED = 42                  # Reproducibility


# ── Graph extraction ─────────────────────────────────────────────────────────
def fetch_graph(session, exclude_frozen: bool = False) -> tuple[nx.Graph, dict]:
    """Concept + RELATES_TO를 networkx Graph로 끌어온다 (방향 무시).

    의심 처리: RELATES_TO strength 속성명이 strength/weight 둘 다 있을 수 있음 → 둘 다 시도.

    exclude_frozen (B0.2): frozen_knowledge category Concept 제외.
        의도적 고립이라 baseline 건강성 측정에 noise. 활성 그래프만 보고 싶을 때 ON.
    """
    where_clause = "WHERE c.category <> 'frozen_knowledge'" if exclude_frozen else ""
    nodes = session.run(
        f"MATCH (c:Concept) {where_clause} "
        "RETURN id(c) AS id, c.name AS name, "
        "c.category AS category, "
        "coalesce(c.usage_count, 0) AS usage, "
        "coalesce(c.quest_observation_count, 0) AS qcnt, "
        "coalesce(c.strength, 0.0) AS strength"
    ).data()

    edge_where = ""
    if exclude_frozen:
        edge_where = "WHERE a.category <> 'frozen_knowledge' AND b.category <> 'frozen_knowledge'"
    edges = session.run(
        f"MATCH (a:Concept)-[r:RELATES_TO]->(b:Concept) {edge_where} "
        "RETURN id(a) AS s, id(b) AS t, "
        "coalesce(r.strength, r.weight, 1.0) AS w, "
        "coalesce(r.source, '<null>') AS source"
    ).data()

    g = nx.Graph()
    meta: dict[int, dict] = {}
    for n in nodes:
        g.add_node(n["id"])
        meta[n["id"]] = {
            "name": n["name"],
            "category": n["category"],
            "usage": n["usage"],
            "qcnt": n["qcnt"],
            "strength": n["strength"],
        }
    edge_source_counter: Counter = Counter()
    for e in edges:
        # 방향 다른 같은 쌍 → 같은 undirected edge로 통합 (weight 누적, source 합집합).
        # source가 다른 multi-edge 정보는 edge_source_counter에 별도 카운트.
        edge_source_counter[e["source"]] += 1
        if g.has_edge(e["s"], e["t"]):
            g[e["s"]][e["t"]]["weight"] += e["w"]
            existing = g[e["s"]][e["t"]].get("sources", set())
            existing.add(e["source"])
            g[e["s"]][e["t"]]["sources"] = existing
        else:
            g.add_edge(e["s"], e["t"], weight=e["w"], sources={e["source"]})

    g.graph["edge_source_counter"] = dict(edge_source_counter)
    return g, meta


# ── Metrics ──────────────────────────────────────────────────────────────────
def metric_counts(g: nx.Graph) -> dict:
    n = g.number_of_nodes()
    m = g.number_of_edges()
    isolated = sum(1 for _ in nx.isolates(g))
    return {
        "n_nodes": n,
        "n_edges": m,
        "avg_degree": (2 * m / n) if n else 0.0,
        "n_isolated": isolated,
        "density": nx.density(g),
    }


def metric_degree_distribution(g: nx.Graph) -> dict:
    degrees = [d for _, d in g.degree()]
    if not degrees:
        return {"empty": True}
    return {
        "min": min(degrees),
        "max": max(degrees),
        "mean": statistics.mean(degrees),
        "median": statistics.median(degrees),
        "p90": sorted(degrees)[int(0.9 * len(degrees))],
        "p99": sorted(degrees)[int(0.99 * len(degrees))],
        "histogram": dict(Counter(degrees)),
    }


def metric_powerlaw_fit(g: nx.Graph) -> dict:
    """Degree 분포가 power-law를 따르는지 log-log 선형회귀.

    주의: scale-free 검정의 정식 방법은 powerlaw 패키지의 Clauset KS test이지만,
    의존성 추가 없이 간단 추정으로 충분 (R² > 0.7 = 가능성 있음).
    """
    degrees = [d for _, d in g.degree() if d > 0]
    if len(degrees) < 10:
        return {"insufficient_data": True}
    counts = Counter(degrees)
    xs = sorted(counts)
    ys = [counts[x] for x in xs]
    import math
    log_x = [math.log(x) for x in xs]
    log_y = [math.log(y) for y in ys]
    slope, intercept, r, p, se = stats.linregress(log_x, log_y)
    return {
        "alpha_estimate": -slope,    # power-law exponent (positive)
        "r_squared": r * r,
        "p_value": p,
        "n_unique_degrees": len(xs),
        "interpretation": _interpret_powerlaw(-slope, r * r),
    }


def _interpret_powerlaw(alpha: float, r2: float) -> str:
    if r2 < 0.5:
        return "no clear power-law (R² too low) — graph may be too small or random-like"
    if 2.0 <= alpha <= 3.0:
        return f"likely scale-free (alpha={alpha:.2f} in [2,3], R²={r2:.2f})"
    if alpha < 2.0:
        return f"heavy-tailed but unstable mean (alpha={alpha:.2f} < 2)"
    return f"scale-free-ish but steep tail (alpha={alpha:.2f} > 3)"


def metric_hubs(g: nx.Graph, meta: dict, top_n: int = 30) -> list[dict]:
    sorted_nodes = sorted(g.degree(), key=lambda x: x[1], reverse=True)[:top_n]
    return [
        {
            "name": meta[nid]["name"],
            "category": meta[nid]["category"],
            "degree": deg,
            "usage": meta[nid]["usage"],
            "qcnt": meta[nid]["qcnt"],
        }
        for nid, deg in sorted_nodes
    ]


def metric_modularity(g: nx.Graph) -> dict:
    """Louvain community detection.

    의심: 고립 노드와 다중 컴포넌트가 있으면 modularity 의미 변함.
    → 가장 큰 connected component(GCC)에서 측정.
    """
    if g.number_of_edges() == 0:
        return {"empty": True}
    components = list(nx.connected_components(g))
    components.sort(key=len, reverse=True)
    gcc_nodes = components[0]
    gcc = g.subgraph(gcc_nodes).copy()

    communities = louvain_communities(gcc, seed=SEED, weight="weight")
    Q = modularity(gcc, communities, weight="weight")
    sizes = sorted([len(c) for c in communities], reverse=True)
    return {
        "modularity": Q,
        "n_communities": len(communities),
        "gcc_size": len(gcc_nodes),
        "gcc_ratio": len(gcc_nodes) / g.number_of_nodes(),
        "n_components": len(components),
        "community_sizes_top10": sizes[:10],
        "interpretation": _interpret_modularity(Q),
    }


def _interpret_modularity(Q: float) -> str:
    if Q < 0.3:
        return "low — graph is one big mush (under-differentiated)"
    if Q < 0.5:
        return "moderate — some structure but blurry boundaries"
    if Q <= 0.75:
        return "healthy — well-modularized like brain regions"
    return "very high — risk of disconnected silos (hyper-fragmented)"


def metric_path_length(g: nx.Graph, sample_pairs: int = PATH_SAMPLE_PAIRS) -> dict:
    """무작위 sample쌍 shortest path. 전체는 너무 비쌈."""
    if g.number_of_edges() == 0:
        return {"empty": True}
    components = list(nx.connected_components(g))
    components.sort(key=len, reverse=True)
    gcc = g.subgraph(components[0]).copy()
    nodes = list(gcc.nodes())
    if len(nodes) < 2:
        return {"insufficient_nodes": True}

    rng = random.Random(SEED)
    lengths = []
    attempted = 0
    for _ in range(sample_pairs):
        a, b = rng.sample(nodes, 2)
        try:
            lengths.append(nx.shortest_path_length(gcc, a, b))
            attempted += 1
        except nx.NetworkXNoPath:
            attempted += 1

    if not lengths:
        return {"no_paths_found": True}
    return {
        "samples": attempted,
        "reachable": len(lengths),
        "avg": statistics.mean(lengths),
        "median": statistics.median(lengths),
        "max": max(lengths),
        "interpretation": _interpret_path(statistics.mean(lengths)),
    }


def _interpret_path(avg: float) -> str:
    if avg < 3:
        return "very tight (small-world strong)"
    if avg <= 6:
        return "small-world range (healthy)"
    if avg <= 10:
        return "loose — connections sparse"
    return "very loose — graph poorly connected"


def metric_betweenness(g: nx.Graph, meta: dict, top_n: int = 20) -> list[dict]:
    """networkx betweenness는 O(VE) — 970/1773이면 견딜 만 (수십초).

    의심: 더 큰 그래프(>5k node)면 k-sample 근사 필요.
    """
    if g.number_of_edges() == 0:
        return []
    components = list(nx.connected_components(g))
    components.sort(key=len, reverse=True)
    gcc = g.subgraph(components[0]).copy()

    # 970 nodes — full 가능. 더 커지면 k=200 sample로.
    if gcc.number_of_nodes() > 5000:
        bc = nx.betweenness_centrality(gcc, k=200, seed=SEED, weight=None, normalized=True)
    else:
        bc = nx.betweenness_centrality(gcc, weight=None, normalized=True)

    top = sorted(bc.items(), key=lambda x: x[1], reverse=True)[:top_n]
    return [
        {
            "name": meta[nid]["name"],
            "category": meta[nid]["category"],
            "betweenness": round(score, 6),
            "degree": gcc.degree(nid),
        }
        for nid, score in top
    ]


def metric_identity_check(session) -> list[dict]:
    """정체성 concept (비비, baby, 엄마 등)이 hub인지 직접 확인."""
    rows = session.run(
        """
        MATCH (c:Concept)
        WHERE c.name IN ['비비', 'baby', '엄마', 'mom', '아빠', 'dad']
           OR c.category = 'identity'
        OPTIONAL MATCH (c)-[r:RELATES_TO]-()
        RETURN c.name AS name, c.category AS category,
               count(r) AS degree, c.strength AS strength
        ORDER BY degree DESC
        """
    ).data()
    return rows


def metric_quest_breakdown(session) -> dict:
    """A4.3/A4.4 Quest passthrough 출처 concept 통계."""
    row = session.run(
        """
        MATCH (c:Concept)
        WHERE 'quest_passthrough' IN coalesce(c.sources, [])
        OPTIONAL MATCH (c)-[r:RELATES_TO]-()
        WITH c, count(r) AS deg
        RETURN count(c) AS n_quest_concepts,
               avg(deg) AS avg_degree,
               collect({name: c.name, deg: deg, qcnt: c.quest_observation_count})[..15] AS samples
        """
    ).single()
    return dict(row) if row else {}


def metric_category_distribution(session) -> dict:
    rows = session.run(
        "MATCH (c:Concept) RETURN coalesce(c.category, '<null>') AS cat, "
        "count(c) AS n ORDER BY n DESC"
    ).data()
    return {r["cat"]: r["n"] for r in rows}


def metric_region_distribution(session) -> dict:
    rows = session.run(
        "MATCH (c:Concept)-[:MAPPED_TO]->(br:BrainRegion) "
        "RETURN br.name AS region, count(c) AS n ORDER BY n DESC"
    ).data()
    return {r["region"]: r["n"] for r in rows}


# ── Main ─────────────────────────────────────────────────────────────────────
def run(tag: str, exclude_frozen: bool = False) -> dict:
    timestamp = datetime.now(timezone.utc).isoformat()
    print(f"[Baseline] tag={tag}  timestamp={timestamp}  exclude_frozen={exclude_frozen}")
    print(f"[Baseline] Connecting to {URI} (db={DB})")

    with GraphDatabase.driver(URI, auth=AUTH) as driver:
        with driver.session(database=DB) as session:
            print("[1/9] Fetching graph...")
            g, meta = fetch_graph(session, exclude_frozen=exclude_frozen)
            print(f"      → {g.number_of_nodes()} nodes, {g.number_of_edges()} edges")
            es = g.graph.get("edge_source_counter", {})
            print(f"      → edge sources: {es}")

            print("[2/9] Counts...")
            counts = metric_counts(g)
            print(f"      → avg_degree={counts['avg_degree']:.2f}  isolated={counts['n_isolated']}")

            print("[3/9] Degree distribution...")
            degdist = metric_degree_distribution(g)

            print("[4/9] Power-law fit...")
            pl = metric_powerlaw_fit(g)
            print(f"      → {pl.get('interpretation', 'n/a')}")

            print("[5/9] Hubs (top 30)...")
            hubs = metric_hubs(g, meta)
            print(f"      → top hub: {hubs[0]['name']} (deg={hubs[0]['degree']})" if hubs else "      → none")

            print("[6/9] Modularity (Louvain)...")
            mod = metric_modularity(g)
            print(f"      → Q={mod.get('modularity', 'n/a')}, communities={mod.get('n_communities', 'n/a')}")

            print(f"[7/9] Sampled shortest paths (n={PATH_SAMPLE_PAIRS})...")
            path = metric_path_length(g)
            print(f"      → {path.get('interpretation', 'n/a')}")

            print("[8/9] Betweenness centrality (top 20)...")
            bc = metric_betweenness(g, meta)
            print(f"      → top bridge: {bc[0]['name']}" if bc else "      → none")

            print("[9/9] Identity / Quest / Category / Region...")
            identity = metric_identity_check(session)
            quest = metric_quest_breakdown(session)
            cats = metric_category_distribution(session)
            regions = metric_region_distribution(session)

    return {
        "tag": tag,
        "timestamp": timestamp,
        "neo4j_uri": URI,
        "neo4j_db": DB,
        "exclude_frozen": exclude_frozen,
        "edge_source_distribution": g.graph.get("edge_source_counter", {}),
        "structural": {
            "counts": counts,
            "degree_distribution": degdist,
            "power_law": pl,
            "hubs_top30": hubs,
            "modularity": mod,
            "path_length": path,
            "betweenness_top20": bc,
        },
        "semantic": {
            "identity_concepts": identity,
            "quest_breakdown": quest,
            "category_distribution": cats,
            "region_distribution": regions,
        },
    }


def write_outputs(result: dict, tag: str) -> tuple[Path, Path]:
    today = datetime.now().strftime("%Y%m%d")
    json_path = OUT_DIR / f"baseline_{tag}_{today}.json"
    md_path = OUT_DIR / f"baseline_{tag}_{today}.md"

    with json_path.open("w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False, default=str)

    md_path.write_text(_render_markdown(result), encoding="utf-8")
    return json_path, md_path


def _render_markdown(r: dict) -> str:
    s = r["structural"]
    sem = r["semantic"]
    counts = s["counts"]
    pl = s["power_law"]
    mod = s["modularity"]
    path = s["path_length"]

    lines = [
        f"# Baby AI Graph Baseline — {r['tag']}",
        "",
        f"- **Timestamp**: {r['timestamp']}",
        f"- **DB**: `{r['neo4j_uri']}` / `{r['neo4j_db']}`",
        "",
        "## 1. Counts",
        f"- Concept: **{counts['n_nodes']}**",
        f"- RELATES_TO: **{counts['n_edges']}**",
        f"- Avg degree: **{counts['avg_degree']:.2f}**",
        f"- Isolated nodes: **{counts['n_isolated']}**  ({counts['n_isolated']/counts['n_nodes']*100:.1f}%)",
        f"- Density: {counts['density']:.5f}",
        "",
        "## 2. Degree distribution",
        f"- min/median/p90/p99/max: {s['degree_distribution']['min']} / "
        f"{s['degree_distribution']['median']:.0f} / "
        f"{s['degree_distribution']['p90']} / {s['degree_distribution']['p99']} / "
        f"{s['degree_distribution']['max']}",
        "",
        "## 3. Power-law fit",
        f"- alpha (exponent): **{pl.get('alpha_estimate', 'n/a'):.3f}**" if 'alpha_estimate' in pl else "- insufficient data",
        f"- R²: **{pl.get('r_squared', 0):.3f}**" if 'r_squared' in pl else "",
        f"- → {pl.get('interpretation', '')}",
        "",
        "## 4. Hubs (top 10)",
        "| name | category | degree | usage | qcnt |",
        "|---|---|---|---|---|",
    ]
    for h in s["hubs_top30"][:10]:
        lines.append(f"| {h['name']} | {h['category']} | {h['degree']} | {h['usage']} | {h['qcnt']} |")

    lines += [
        "",
        "## 5. Modularity",
        f"- Q = **{mod.get('modularity', 'n/a')}**" if 'modularity' in mod else "- empty",
        f"- communities: {mod.get('n_communities', 'n/a')}",
        f"- GCC: {mod.get('gcc_size', 'n/a')} nodes ({mod.get('gcc_ratio', 0)*100:.1f}% of graph)",
        f"- → {mod.get('interpretation', '')}",
        "",
        "## 6. Path length (sampled)",
        f"- reachable: {path.get('reachable', 0)}/{path.get('samples', 0)}",
        f"- avg: **{path.get('avg', 'n/a')}**" if 'avg' in path else "",
        f"- → {path.get('interpretation', '')}",
        "",
        "## 7. Betweenness (top 10 bridges)",
        "| name | category | betweenness | degree |",
        "|---|---|---|---|",
    ]
    for b in s["betweenness_top20"][:10]:
        lines.append(f"| {b['name']} | {b['category']} | {b['betweenness']} | {b['degree']} |")

    lines += [
        "",
        "## 8. Identity concepts",
        "| name | category | degree | strength |",
        "|---|---|---|---|",
    ]
    for i in sem["identity_concepts"]:
        lines.append(f"| {i['name']} | {i['category']} | {i['degree']} | {i.get('strength', '-')} |")

    lines += ["", "## 9. Category distribution"]
    for cat, n in list(sem["category_distribution"].items())[:15]:
        lines.append(f"- {cat}: {n}")

    lines += ["", "## 10. Region distribution (MAPPED_TO)"]
    for region, n in list(sem["region_distribution"].items()):
        lines.append(f"- {region}: {n}")

    lines += ["", "## 11. Quest passthrough"]
    qb = sem["quest_breakdown"]
    if qb:
        lines.append(f"- n_quest_concepts: {qb.get('n_quest_concepts', 0)}")
        lines.append(f"- avg_degree: {qb.get('avg_degree', 0)}")

    lines += [
        "",
        "---",
        "## Health verdict (auto-derived)",
        _verdict(s),
    ]
    return "\n".join(lines)


def _verdict(s: dict) -> str:
    bullets = []
    pl = s["power_law"]
    mod = s["modularity"]
    path = s["path_length"]
    counts = s["counts"]

    iso_ratio = counts["n_isolated"] / max(counts["n_nodes"], 1)
    if iso_ratio > 0.1:
        bullets.append(f"⚠️  isolated nodes {iso_ratio*100:.1f}% — concept generation outpacing edge formation")
    else:
        bullets.append(f"✅ isolated nodes {iso_ratio*100:.1f}% (healthy)")

    if 'r_squared' in pl and pl['r_squared'] >= 0.7:
        bullets.append(f"✅ scale-free likely (R²={pl['r_squared']:.2f}, alpha={pl.get('alpha_estimate', 0):.2f})")
    else:
        bullets.append(f"⚠️  power-law fit weak (R²={pl.get('r_squared', 0):.2f}) — graph may be too small or random")

    Q = mod.get('modularity')
    if Q is not None:
        if 0.3 <= Q <= 0.75:
            bullets.append(f"✅ modularity Q={Q:.2f} in healthy range")
        else:
            bullets.append(f"⚠️  modularity Q={Q:.2f} outside healthy range [0.3, 0.75]")

    avg = path.get('avg')
    if avg is not None:
        if 3 <= avg <= 6:
            bullets.append(f"✅ small-world avg path={avg:.2f}")
        else:
            bullets.append(f"⚠️  avg path={avg:.2f} outside small-world range [3, 6]")

    return "\n".join(f"- {b}" for b in bullets)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", default="initial",
                        help="label for this measurement (e.g. 'before_adgr', 'after_adgr_v1')")
    parser.add_argument("--exclude-frozen", action="store_true",
                        help="frozen_knowledge category 제외 (활성 그래프만 측정)")
    args = parser.parse_args()

    result = run(args.tag, exclude_frozen=args.exclude_frozen)
    json_path, md_path = write_outputs(result, args.tag)
    print()
    print(f"[Output] {json_path}")
    print(f"[Output] {md_path}")
