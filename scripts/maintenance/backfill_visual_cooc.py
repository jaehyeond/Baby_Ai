"""
Phase Q1 — Visual Co-occurrence Hebbian Backfill
=================================================
기존 Quest passthrough Experience(42건) 에 retroactively visual_cooc Hebbian 적용.

배경:
    api_server.py /api/vision/quest-concepts 가 2026-04-15~2026-05-08 동안
    같은 frame 객체 쌍을 RELATES_TO 로 연결하지 않음. 새 endpoint 패치는
    이후 Quest 호출에만 적용되므로, 기존 데이터는 별도 backfill 필요.

설계 결정 (가드):
    1) --dry-run 기본 ON. --commit 명시해야 실제 쓰기.
    2) backfilled=true 마크. 라이브 데이터와 구분.
    3) source='visual_cooc' 격리 (conv 'hebbian'과 분리).
    4) noise filter: concept_binding.select_visual_cooc_concepts 재사용.
    5) Idempotent: MERGE 패턴이라 재실행해도 strength만 증가 (cap 1.0).

사용:
    python scripts/maintenance/backfill_visual_cooc.py            # dry-run
    python scripts/maintenance/backfill_visual_cooc.py --commit   # 실제 적용
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path

from dotenv import load_dotenv
from neo4j import GraphDatabase

# 프로젝트 루트를 path에 추가 (concept_binding import 위함)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from neural.baby.concept_binding import select_visual_cooc_concepts  # noqa: E402

load_dotenv()
URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
AUTH = (os.getenv("NEO4J_USERNAME", "neo4j"), os.getenv("NEO4J_PASSWORD", ""))
DB = os.getenv("NEO4J_DATABASE", "neo4j")

DELTA = 0.03
SOURCE = "visual_cooc"


def fetch_quest_experiences(session) -> list[dict]:
    """quest_passthrough Experience와 그에 연결된 Concept 목록."""
    rows = session.run(
        """
        MATCH (e:Experience)
        WHERE 'quest_passthrough' IN coalesce(e.tags, [])
        OPTIONAL MATCH (e)-[:INVOLVES]->(c:Concept)
        WITH e, collect({id: c.id, name: c.name}) AS concepts
        RETURN e.id AS exp_id, e.created_at AS created, concepts
        ORDER BY e.created_at
        """
    ).data()
    return rows


def backfill(session, dry_run: bool) -> dict:
    exps = fetch_quest_experiences(session)
    print(f"[Backfill] {len(exps)} Quest experiences found")

    total_pairs = 0
    total_concepts = 0
    skipped_too_few = 0
    by_exp = []

    now_iso = datetime.now(timezone.utc).isoformat()

    for e in exps:
        concepts = [c for c in e["concepts"] if c["id"] and c["name"]]
        # filter via select_visual_cooc_concepts (name → id 맵 만들고 호출)
        name_to_id = {c["name"]: c["id"] for c in concepts}
        cooc_ids = select_visual_cooc_concepts(name_to_id)

        if len(cooc_ids) < 2:
            skipped_too_few += 1
            by_exp.append({"exp_id": e["exp_id"], "n_concepts": len(concepts),
                           "n_cooc": len(cooc_ids), "n_pairs": 0, "skipped": True})
            continue

        pairs = list(combinations(cooc_ids, 2))
        total_pairs += len(pairs)
        total_concepts += len(cooc_ids)

        if not dry_run:
            # canonical ordering
            unique_pairs = list({(min(a, b), max(a, b)) for a, b in pairs if a != b})
            pairs_list = [list(p) for p in unique_pairs]
            session.run(
                "UNWIND $pairs AS pair "
                "MATCH (a:Concept {id: pair[0]}), (b:Concept {id: pair[1]}) "
                "MERGE (a)-[r:RELATES_TO {source: $source}]->(b) "
                "ON CREATE SET r.strength = $delta, r.hebb_strength = $delta, "
                "  r.created_at = $now, r.backfilled = true "
                "ON MATCH SET "
                "  r.strength = CASE WHEN coalesce(r.strength, 0.5) + $delta > 1.0 "
                "    THEN 1.0 ELSE coalesce(r.strength, 0.5) + $delta END, "
                "  r.hebb_strength = CASE WHEN coalesce(r.hebb_strength, 0) + $delta > 1.0 "
                "    THEN 1.0 ELSE coalesce(r.hebb_strength, 0) + $delta END, "
                "  r.backfilled = coalesce(r.backfilled, false) ",
                pairs=pairs_list,
                delta=DELTA,
                source=SOURCE,
                now=now_iso,
            )
        by_exp.append({
            "exp_id": e["exp_id"],
            "n_concepts": len(concepts),
            "n_cooc": len(cooc_ids),
            "n_pairs": len(pairs),
            "skipped": False,
        })

    return {
        "n_experiences": len(exps),
        "skipped_too_few": skipped_too_few,
        "total_pairs": total_pairs,
        "total_cooc_concepts": total_concepts,
        "dry_run": dry_run,
        "by_exp_top5": by_exp[:5],
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--commit", action="store_true",
                   help="실제 쓰기. 미지정 시 dry-run.")
    args = p.parse_args()
    dry_run = not args.commit

    print(f"[Backfill] mode={'COMMIT' if not dry_run else 'DRY-RUN'}")
    print(f"[Backfill] DB={URI}/{DB}, source='{SOURCE}', delta={DELTA}")

    with GraphDatabase.driver(URI, auth=AUTH) as driver:
        # Pre-state
        with driver.session(database=DB) as s:
            pre = s.run(
                "MATCH ()-[r:RELATES_TO]->() WITH r.source AS src, count(r) AS n "
                "RETURN src, n ORDER BY n DESC"
            ).data()
            print(f"\n[Pre-state] RELATES_TO source distribution:")
            for r in pre:
                print(f"  {str(r['src']):20s}  {r['n']}")

        # Backfill
        with driver.session(database=DB) as s:
            result = backfill(s, dry_run=dry_run)

        print(f"\n[Result]")
        print(f"  experiences scanned : {result['n_experiences']}")
        print(f"  skipped (<2 cooc)   : {result['skipped_too_few']}")
        print(f"  total pairs         : {result['total_pairs']}")
        print(f"  total cooc concepts : {result['total_cooc_concepts']}")

        # Post-state (if committed)
        if not dry_run:
            with driver.session(database=DB) as s:
                post = s.run(
                    "MATCH ()-[r:RELATES_TO]->() WITH r.source AS src, count(r) AS n "
                    "RETURN src, n ORDER BY n DESC"
                ).data()
                print(f"\n[Post-state] RELATES_TO source distribution:")
                for r in post:
                    print(f"  {str(r['src']):20s}  {r['n']}")

                vc = s.run(
                    "MATCH ()-[r:RELATES_TO {source: 'visual_cooc'}]->() "
                    "RETURN count(r) AS n, "
                    "       count(CASE WHEN r.backfilled THEN 1 END) AS bf"
                ).single()
                print(f"\n[visual_cooc edges] total={vc['n']}, backfilled={vc['bf']}")
        else:
            print("\n[DRY-RUN] No writes. Use --commit to apply.")


if __name__ == "__main__":
    main()
