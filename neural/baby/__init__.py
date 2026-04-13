"""
Baby Neural Substrate — Developmental AI (Neo4j + Redis)

아기의 인지 발달을 모방한 AI 시스템
- 백지 상태에서 시작 (stage=0 NEWBORN)
- 대화 기반 학습 + 수면 모드 기억 통합
- 감정 기반 주의 + 자발적 사고
- 해부학적 뇌 시각화 (9 BrainRegions)

Active modules (Phase 2 migration, 2026-04):
  - neo4j_db.py        — Neo4j DB 추상화 (74 methods)
  - redis_client.py    — Redis Pub/Sub (5 channels)
  - conversation_handler.py — 대화 파이프라인 (Step 1~8, E2-3/E2-2 포함)
  - api_server.py      — FastAPI 서버 (45+ endpoints)
  - llm_client.py      — Gemini/Claude client
  - embeddings.py      — OpenAI embedding helpers

Legacy modules moved to archive/ on 2026-04-09.
"""
