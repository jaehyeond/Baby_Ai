"""
Backfill NEXT_FRAME edges — 기존 Quest vision 프레임을 감각운동 시퀀스로 연결
==============================================================================
Phase 4 embodiment. `neo4j_db.link_vision_frame_sequence` 와 동일 규칙(≤gap초 인접
vision 프레임만 연결)을 **기존 45개 프레임**에 소급 적용한다. 신규 엣지 생성만 하는
비파괴·멱등·가역 작업 (기존 노드/엣지 미변경).

근거: embodied_prediction.py(2026-07-12) — vision 프레임이 그래프상 고립된 관찰이라
프레임 시퀀스 구조가 없었다. NEXT_FRAME 으로 시간 순서를 새겨 (a) 감각운동 예측 하니스가
세션/시퀀스를 그래프에서 직접 읽고 (b) 신규 엣지 타입이 실데이터에서 즉시 exercise 됨
("정의만 되고 호출 안 됨" 방지).

Usage:
    python scripts/maintenance/backfill_frame_sequence.py            # 실행
    python scripts/maintenance/backfill_frame_sequence.py --dry-run  # 미리보기
    python scripts/maintenance/backfill_frame_sequence.py --rollback # NEXT_FRAME 전체 삭제
"""
from __future__ import annotations
import argparse, os, sys
from datetime import datetime, timezone
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv(".env")
URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
AUTH = (os.getenv("NEO4J_USERNAME", "neo4j"), os.getenv("NEO4J_PASSWORD", ""))
DB = os.getenv("NEO4J_DATABASE", "neo4j")
MAX_GAP = 30.0     # link_vision_frame_sequence 기본값과 일치


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--rollback", action="store_true")
    ap.add_argument("--gap", type=float, default=MAX_GAP)
    args = ap.parse_args()

    with GraphDatabase.driver(URI, auth=AUTH, notifications_min_severity="OFF") as d:
        with d.session(database=DB) as s:
            if args.rollback:
                n = s.run("MATCH ()-[r:NEXT_FRAME]->() DELETE r RETURN count(r) AS n").single()["n"]
                print(f"[rollback] NEXT_FRAME 엣지 {n}개 삭제")
                return

            rows = s.run(
                "MATCH (e:Experience) WHERE e.task_type='vision' AND e.created_at IS NOT NULL "
                "RETURN e.id AS id, e.created_at AS ts ORDER BY ts"
            ).data()
            frames = [(r["id"], datetime.fromisoformat(r["ts"]).timestamp()) for r in rows]
            print(f"[backfill] vision 프레임 {len(frames)}개")

            pairs = []
            for i in range(len(frames) - 1):
                dt = frames[i + 1][1] - frames[i][1]
                if 0 < dt <= args.gap:
                    pairs.append((frames[i][0], frames[i + 1][0], int(dt)))
            print(f"[backfill] ≤{args.gap:.0f}s 인접쌍(=연결대상): {len(pairs)}")

            if args.dry_run:
                for a, b, dt in pairs[:8]:
                    print(f"  {a[:8]}→{b[:8]}  dt={dt}s")
                print("  ... (dry-run, 미적용)" if len(pairs) > 8 else "  (dry-run, 미적용)")
                return

            now = datetime.now(timezone.utc).isoformat()
            created = 0
            for a, b, dt in pairs:
                r = s.run(
                    "MATCH (p:Experience {id:$a}), (c:Experience {id:$b}) "
                    "MERGE (p)-[r:NEXT_FRAME]->(c) "
                    "ON CREATE SET r.created_at=$now, r.dt_sec=$dt, r.backfilled=true "
                    "RETURN r.backfilled AS bf",
                    a=a, b=b, dt=dt, now=now,
                ).single()
                if r:
                    created += 1
            total = s.run("MATCH ()-[r:NEXT_FRAME]->() RETURN count(r) AS n").single()["n"]
            # 세션(연결성분) 수 = 프레임 - 엣지 (선형 체인 가정)
            print(f"[backfill] NEXT_FRAME upsert {created}쌍 → 전체 {total}개 엣지")
            print(f"[backfill] 45 고립 프레임 → {len(frames)-total}개 시퀀스(세션)로 연결됨")
            print("  (기존 프레임엔 head_pose 없음 → pose_delta=null. 향후 Quest 세션부터 기록됨.)")


if __name__ == "__main__":
    main()
