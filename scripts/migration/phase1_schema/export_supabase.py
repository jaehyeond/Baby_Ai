"""
Phase 1: Supabase → JSON 내보내기

실행: python scripts/migration/phase1_schema/export_supabase.py

출력: scripts/migration/migration_data/{table}.json (18개 파일)

검증된 사실:
  - embedding 컬럼: REST API가 JSON 문자열 반환 ("[-0.023, ...]") → 그대로 저장
  - embedding 차원: 1536 (OpenAI text-embedding-3-small)
  - 내보내기 순서: 부모 테이블 → 자식 테이블 (관계 무결성 보장)
"""

import os
import json
import time
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")
OUTPUT_DIR = Path(__file__).parent.parent / "migration_data"
OUTPUT_DIR.mkdir(exist_ok=True)

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
}

# 내보내기 순서: 부모 테이블 → 자식 테이블
# experience_concepts는 양 끝(experiences, semantic_concepts) 이후
EXPORT_ORDER = [
    "brain_regions",           # 9행
    "semantic_concepts",       # 820행 (embedding string 포함)
    "concept_relations",       # 680행
    "concept_brain_mapping",   # 820행
    "experiences",             # 3,039행 (embedding string 포함)
    "experience_concepts",     # 1,060행 (junction → Neo4j 관계)
    "emotion_logs",            # 1,503행
    "baby_state",              # 1행
    "predictions",             # 8행
    "imagination_sessions",    # 15행
    "causal_models",           # 3행
    "procedural_patterns",     # 102행
    "memory_consolidation_logs",  # 2,716행
    "visual_experiences",      # 16행 (embedding 포함)
    "pending_questions",       # 17행
    "curiosity_queue",         # 811행
    "autonomous_goals",        # 146행
    "ablation_runs",           # 20행
]


def fetch_table(table: str, page_size: int = 1000) -> list[dict]:
    """Supabase REST API로 전체 테이블 내보내기 (페이지네이션 포함)"""
    all_rows = []
    offset = 0

    while True:
        url = f"{SUPABASE_URL}/rest/v1/{table}?select=*&limit={page_size}&offset={offset}"
        resp = httpx.get(url, headers={**HEADERS, "Prefer": "count=exact"}, timeout=30)

        # 200 = full response, 206 = partial content (both valid)
        if resp.status_code not in (200, 206):
            print(f"  [ERROR] {table} at offset={offset}: HTTP {resp.status_code}")
            print(f"  {resp.text[:200]}")
            break

        rows = resp.json()
        total = resp.headers.get("content-range", "?/?").split("/")[-1]

        if not rows:
            break

        all_rows.extend(rows)
        print(f"  [{table}] {len(all_rows)}/{total} rows fetched...")

        if len(rows) < page_size:
            break
        offset += page_size
        time.sleep(0.1)  # Rate limit 방지

    return all_rows


def export_all():
    print(f"=== Supabase Export Start ===")
    print(f"Source: {SUPABASE_URL}")
    print(f"Output: {OUTPUT_DIR}")
    print()

    summary = {}

    for table in EXPORT_ORDER:
        out_path = OUTPUT_DIR / f"{table}.json"

        if out_path.exists():
            existing = json.loads(out_path.read_text(encoding="utf-8"))
            print(f"[SKIP] {table}: already exported ({len(existing)} rows)")
            summary[table] = len(existing)
            continue

        print(f"[EXPORT] {table}...")
        rows = fetch_table(table)

        out_path.write_text(
            json.dumps(rows, ensure_ascii=False, indent=None),
            encoding="utf-8",
        )
        summary[table] = len(rows)
        print(f"  [OK] {table}: {len(rows)} rows → {out_path.name}")
        print()

    print("=== Export Summary ===")
    total_rows = 0
    for table, count in summary.items():
        print(f"  {table}: {count}")
        total_rows += count
    print(f"  TOTAL: {total_rows} rows across {len(summary)} tables")

    # 요약 파일 저장
    summary_path = OUTPUT_DIR / "_export_summary.json"
    summary_path.write_text(
        json.dumps({"tables": summary, "total": total_rows}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"\nSummary saved: {summary_path}")


if __name__ == "__main__":
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("[FAIL] SUPABASE_URL or SUPABASE_ANON_KEY not set in .env")
        sys.exit(1)
    export_all()
