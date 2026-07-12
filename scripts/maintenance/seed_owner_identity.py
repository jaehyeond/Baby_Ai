"""
Seed Owner Identity (박재현) — entity resolution STEP 1-2
========================================================
docs/IDENTITY_ACCESS_CONTROL.md 참조.

owner 박재현의 파편화된 별칭(개발자/사용자/형/엄마 = 테스트 페르소나 확인됨)을
하나의 (:Person) 허브로 비파괴 통합한다. 원본 Concept/UserModel 노드는 보존하고
ALIAS_OF / IDENTIFIED_BY 엣지만 추가한다 (신경과학: ATL hub-and-spoke).

- idempotent: MERGE 기반, 재실행 안전
- 비파괴: 기존 노드/엣지 삭제·수정 없음 (엣지 추가만)
- 감사가능: 신규 노드·엣지에 created_by 스탬프
- 되돌림: --rollback 이 스탬프된 것만 정확히 제거

Usage:
    python scripts/maintenance/seed_owner_identity.py            # dry-run (기본)
    python scripts/maintenance/seed_owner_identity.py --apply
    python scripts/maintenance/seed_owner_identity.py --verify
    python scripts/maintenance/seed_owner_identity.py --rollback
"""
from __future__ import annotations
import argparse, os, sys
from datetime import datetime, timezone
from dotenv import load_dotenv
from neo4j import GraphDatabase

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv(".env")
URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
AUTH = (os.getenv("NEO4J_USERNAME", "neo4j"), os.getenv("NEO4J_PASSWORD", ""))
DB = os.getenv("NEO4J_DATABASE", "neo4j")

STAMP = "owner_seed_2026-07-10"
PERSON = {"person_id": "owner_pjh", "canonical_name": "박재현",
          "role": "owner", "access_clearance": "owner_private"}
ALIASES = ["개발자", "사용자", "형", "엄마"]          # 테스트 페르소나 = 전부 박재현
USERMODEL_SIDS = ["mom", "brother", "self", "나", "박재현"]  # 존재하는 것만 링크


def _drv():
    return GraphDatabase.driver(URI, auth=AUTH, notifications_min_severity="OFF")


def dry_run(s):
    print("=== DRY-RUN (변경 없음) ===")
    print(f"target Person: {PERSON}")
    print("\n[별칭 Concept 존재/차수]")
    for name in ALIASES:
        r = s.run("MATCH (c:Concept {name:$n}) OPTIONAL MATCH (c)-[e]-() "
                  "RETURN count(DISTINCT c) AS exists, count(e) AS deg", n=name).single()
        print(f"  {name:6s} exists={r['exists']} deg={r['deg']}"
              f"{'  <- 없음, skip' if not r['exists'] else ''}")
    print("\n[UserModel 존재]")
    for sid in USERMODEL_SIDS:
        r = s.run("MATCH (u:UserModel {speaker_id:$s}) RETURN count(u) AS n", s=sid).single()
        if r["n"]:
            print(f"  speaker_id={sid}  exists")
    p = s.run("MATCH (p:Person {person_id:$pid}) RETURN count(p) AS n", pid=PERSON["person_id"]).single()
    print(f"\n[owner Person 이미 존재?] {'YES (재실행 안전)' if p['n'] else 'NO (신규 생성 예정)'}")
    print("\n계획: (:Person owner) MERGE + 존재하는 별칭 Concept마다 (c)-[:ALIAS_OF]->(p),"
          " 존재하는 UserModel마다 (p)-[:IDENTIFIED_BY]->(u). 원본 노드/엣지 불변.")


def apply(s):
    now = datetime.now(timezone.utc).isoformat()
    s.run("CREATE CONSTRAINT person_pid IF NOT EXISTS FOR (p:Person) REQUIRE p.person_id IS UNIQUE")
    s.run("""MERGE (p:Person {person_id:$pid})
             ON CREATE SET p.canonical_name=$cn, p.role=$role, p.access_clearance=$clr,
                           p.created_by=$stamp, p.created_at=$now
             ON MATCH SET p.role=$role, p.access_clearance=$clr""",
          pid=PERSON["person_id"], cn=PERSON["canonical_name"], role=PERSON["role"],
          clr=PERSON["access_clearance"], stamp=STAMP, now=now)
    a = s.run("""UNWIND $names AS nm
                 MATCH (c:Concept {name:nm}) MATCH (p:Person {person_id:$pid})
                 MERGE (c)-[r:ALIAS_OF]->(p)
                 ON CREATE SET r.created_by=$stamp, r.match_confidence=1.0, r.created_at=$now
                 RETURN count(r) AS n""",
              names=ALIASES, pid=PERSON["person_id"], stamp=STAMP, now=now).single()["n"]
    u = s.run("""UNWIND $sids AS sid
                 MATCH (um:UserModel {speaker_id:sid}) MATCH (p:Person {person_id:$pid})
                 MERGE (p)-[r:IDENTIFIED_BY]->(um)
                 ON CREATE SET r.created_by=$stamp, r.created_at=$now
                 RETURN count(r) AS n""",
              sids=USERMODEL_SIDS, pid=PERSON["person_id"], stamp=STAMP, now=now).single()["n"]
    print(f"=== APPLIED ===\n  Person owner_pjh MERGE 완료")
    print(f"  ALIAS_OF 엣지(별칭→owner): {a}")
    print(f"  IDENTIFIED_BY 엣지(owner→speaker): {u}")


def verify(s):
    print("=== VERIFY ===")
    r = s.run("""MATCH (p:Person {person_id:$pid})
                 OPTIONAL MATCH (c:Concept)-[:ALIAS_OF]->(p)
                 OPTIONAL MATCH (p)-[:IDENTIFIED_BY]->(u:UserModel)
                 RETURN p.canonical_name AS name, p.role AS role, p.access_clearance AS clr,
                        collect(DISTINCT c.name) AS aliases,
                        collect(DISTINCT u.speaker_id) AS speakers""",
              pid=PERSON["person_id"]).single()
    if not r or not r["name"]:
        print("  owner Person 없음 (아직 --apply 안 함?)"); return
    print(f"  Person: {r['name']} role={r['role']} clearance={r['clr']}")
    print(f"  ALIAS_OF concepts: {r['aliases']}")
    print(f"  IDENTIFIED_BY speakers: {r['speakers']}")
    # 별칭들이 이제 owner 통해 연결되는지 (파편화 해소 확인)
    reach = s.run("""MATCH (p:Person {person_id:$pid})<-[:ALIAS_OF]-(c:Concept)
                     RETURN count(c) AS unified,
                            sum(size([(c)-[x:RELATES_TO]-() | x])) AS total_alias_edges""",
                  pid=PERSON["person_id"]).single()
    print(f"  통합된 별칭 수: {reach['unified']}, 별칭들의 RELATES_TO 총합: {reach['total_alias_edges']}")


def rollback(s):
    e = s.run("MATCH ()-[r]->() WHERE r.created_by=$stamp DELETE r RETURN count(r) AS n",
              stamp=STAMP).single()["n"]
    n = s.run("MATCH (p:Person {person_id:$pid}) WHERE p.created_by=$stamp DELETE p RETURN count(p) AS n",
              pid=PERSON["person_id"], stamp=STAMP).single()["n"]
    print(f"=== ROLLBACK ===\n  삭제된 엣지(스탬프 {STAMP}): {e}\n  삭제된 Person: {n}\n  (원본 Concept/UserModel 불변)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--apply", action="store_true")
    g.add_argument("--verify", action="store_true")
    g.add_argument("--rollback", action="store_true")
    args = ap.parse_args()
    with _drv() as d:
        with d.session(database=DB) as s:
            if args.apply:   apply(s)
            elif args.verify: verify(s)
            elif args.rollback: rollback(s)
            else: dry_run(s)
