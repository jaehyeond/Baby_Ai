"""
Phase 0: Neo4j AuraDB Free 연결 테스트

[AuraDB Free 연결 패턴 - 검증 완료 2026-03-18]

문제:
  - neo4j+s:// → 라우팅 테이블 조회 실패 (단일노드 Free tier 구조적 한계)
  - bolt+s://[instance].databases.neo4j.io → writer 노드로 일관되게 라우팅 안 됨
  - database_='b76cbc85' → system DB에서는 보이지만 bolt 직접 연결 시 not found

해결책:
  1. system DB로 연결 → SHOW DATABASES로 writer 주소 조회
  2. writer 주소로 직접 bolt+s:// 연결 → database_ 파라미터 불필요

참고: Neo4j Community #74376, GitHub neo4j-python-driver #628
"""
import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()

ENTRY_URI = os.getenv("NEO4J_URI")   # bolt+s://b76cbc85.databases.neo4j.io
USERNAME  = os.getenv("NEO4J_USERNAME")
PASSWORD  = os.getenv("NEO4J_PASSWORD")
DB_NAME   = os.getenv("NEO4J_DATABASE")  # b76cbc85

print(f"Entry URI: {ENTRY_URI}")
print(f"Username:  {USERNAME}")
print(f"Database:  {DB_NAME}")
print()

AUTH = (USERNAME, PASSWORD)

try:
    # Step 1: system DB로 writer 주소 조회
    print("[Step 1] Querying system DB for writer address...")
    with GraphDatabase.driver(ENTRY_URI, auth=AUTH) as d:
        res = d.execute_query(
            f'SHOW DATABASES YIELD name, address, writer WHERE name = "{DB_NAME}" AND writer = true',
            database_="system"
        )
        if not res.records:
            raise RuntimeError(f"No writer found for database '{DB_NAME}'")
        writer_host = res.records[0]["address"]  # e.g. p-mt-xxx.neo4j.io:7687
        print(f"[OK] Writer address: {writer_host}")

    # Step 2: writer 노드로 직접 연결
    writer_uri = f"bolt+s://{writer_host.split(':')[0]}"
    print(f"\n[Step 2] Connecting to writer: {writer_uri}")

    with GraphDatabase.driver(writer_uri, auth=AUTH) as d:
        with d.session() as s:
            # Ping
            ping = s.run("RETURN 1 AS ping").single()["ping"]
            print(f"[OK] Ping: {ping}")

            # Neo4j 버전
            for rec in s.run("CALL dbms.components() YIELD name, versions"):
                print(f"[OK] {rec['name']}: {rec['versions']}")

            # 노드 수
            total = s.run("MATCH (n) RETURN count(n) AS total").single()["total"]
            print(f"[OK] Nodes: {total} ({'empty - ready for Phase 1' if total == 0 else 'has data'})")

            # 인덱스
            indexes = list(s.run("SHOW INDEXES"))
            print(f"[OK] Indexes: {len(indexes)}")

    print()
    print("[PHASE 0 COMPLETE] Neo4j AuraDB Free connection verified")
    print(f"  Writer URI: {writer_uri}")
    print("  Ready for Phase 1: Schema creation")

except Exception as e:
    print(f"[FAIL] {e}")
