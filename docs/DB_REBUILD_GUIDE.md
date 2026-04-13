# DB 재구축 가이드 (Neo4j + Redis 신규 인스턴스)

**작성일**: 2026-04-09
**상태**: 코드 준비 완료 (P1-P8), 사용자 액션 대기 (P9-P11)

## 왜 이 문서가 필요한가

Neo4j AuraDB Free `b76cbc85`와 Upstash Redis `clean-polecat-38197` 인스턴스가 **DNS에서 사라졌다** (NXDOMAIN 확정). AuraDB Free 정책(72h 미사용 PAUSED → 30일 후 DELETE)에 의한 것으로 추정. **기존 데이터 전부 소실**, 하지만 스키마·코드·마이그레이션 스크립트·JSON 백업은 git에 그대로 남아있다.

사용자 결정: **빈 DB + 최소 시드로 Baby를 새로 키운다** (과거 데이터 복원 안 함).

## 코드 준비 완료 (2026-04-09)

### P1-P3: 레거시 정리
- `memory.py`, `vision.py`, `evolution.py`, `team_optimizer.py`, `persistence.py`, `curiosity.py`, `self_model.py`, `cognitive_router.py` → `neural/baby/archive/`
- `test_memory_integration.py`, `test_cognitive_router.py`, `test_evolution.py` → `archive/`
- `scripts/test_world_model.py` → `archive/`
- `neural/baby/__init__.py` 빈 상태로 정리

**검증 결과**: `from neural.baby import api_server` 실행 시 로드되는 모듈은 `api_server`, `neo4j_db`, `redis_client` 3개뿐 (레거시 0개).

### P4: `ensure_indexes()` 확장
`neo4j_db.py:147` 메서드가 이제 전체 스키마를 한 번에 보장:
- **13 UNIQUE CONSTRAINT**: Concept/Experience/BrainRegion/BabyState 등 + UserModel(speaker_id)
- **9 LOOKUP INDEX**: concept_category, experience_stage, exp_hour 등
- **3 VECTOR INDEX**: concept_embeddings, experience_embeddings, visual_embeddings (dim=1536, cosine)

### P5: BrainRegion 시드
`neo4j_db.py:seed_brain_regions()`가 9개 뇌 영역 MERGE (brain_regions.json의 실제 좌표/색상/development_stage 보존).

### P6: 정체성 Concept 시드
`neo4j_db.py:seed_identity_concepts()`가 5개 Concept 시드:
- **비비** (identity) → temporal/prefrontal/amygdala
- **형아** (identity), **엄마** (identity)
- **안녕** (language), **좋아** (emotion)

멱등 보장: `was_created` 가드로 기존이면 MAPPED_TO 재생성 안 함 → EMA drift 없음.

### P7: `insert_concept()` Hub-and-Spoke 자동 매핑
Concept 생성 시 category→region 자동 매핑:
- **MAPPED_TO** (1개, dominant region): 기존 쿼리 호환 100% (Cartesian product 없음)
- **ALSO_REPRESENTED_IN** (0~N개, secondary regions): 분산 표상 (Huth 2016)
- EMA 업데이트 (learning rate 0.1)로 기존 concept의 region weight 점진적 학습

**근거 논문**:
- Huth et al. 2016 (Nature) — 분산 표상, 연속 gradient
- Patterson, Nestor, Rogers 2007 (Nature Reviews Neuroscience) — Hub-and-Spoke, temporal lobe amodal hub
- Binder et al. 2009 (Cerebral Cortex) — multi-region semantic network

### P8: 수면 모드 CLS reweighting
`replay_recent_memories()`에 추가: replay된 concept들의 region weight를 재조정
- **hippocampus**: -0.05 (cap at 0)
- **cortical (temporal, prefrontal, parietal)**: +0.02 (cap at 1.0)

**근거**: McClelland, McNaughton, O'Reilly 1995 (Psych Review) — Complementary Learning Systems. 기억은 hippocampus에서 빠르게 encoding 후, 수면 중 replay를 통해 점진적으로 cortex로 이동.

### Lifespan 자동 실행
`api_server.py:54-67`에서 서버 시작 시 자동으로 순차 실행:
1. `init_driver()` — Neo4j 2-step writer lookup
2. `init_redis()` — Upstash Redis 연결
3. `ensure_indexes()` — 전체 스키마 멱등 생성
4. `seed_brain_regions()` — 9개 BrainRegion
5. `seed_identity_concepts()` — 5개 Concept + MAPPED_TO

---

## 사용자 액션 (P9): 신규 인스턴스 생성

### A. Neo4j AuraDB 신규 인스턴스

1. **콘솔 접속**: https://console.neo4j.io 로그인
2. **Create Instance**:
   - Plan: **AuraDB Free** (무료, 200K 노드 / 400K 관계, 단 72h 미사용 → PAUSED)
   - 또는 **AuraDB Professional** (월 $65~, 자동 정지 없음, 권장 — 같은 일 반복 방지)
   - Region: **Asia-Pacific (Singapore)** 또는 **Tokyo** (한국 근접)
   - Instance name: `baby-ai-v2`
3. **Credentials 다운로드**: 인스턴스 생성 후 나오는 `.txt` 파일을 반드시 저장
   - `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD` 포함
   - Database name은 Free에서 보통 인스턴스 ID 8글자 (예: `abc12345`)
4. **연결 테스트**: AuraDB Browser에서 `MATCH (n) RETURN count(n)` 실행 → 0 반환 정상

### B. Upstash Redis 신규 인스턴스

1. **콘솔 접속**: https://console.upstash.com
2. **Create Database**:
   - Type: **Regional** (글로벌보다 저렴, 충분)
   - Region: **Tokyo** (asia-northeast1)
   - Name: `baby-ai-redis-v2`
   - TLS: **Enabled** (필수 — `rediss://`)
3. **Connection URL**: "Connect" → "Redis TLS URL" 복사
   - 형식: `rediss://default:PASSWORD@HOST:PORT`

### C. `.env` 업데이트

`/e/A2A/our-a2a-project/.env` 파일을 열고 다음 4줄 업데이트:

```env
# Neo4j AuraDB (baby-ai-v2, 2026-04-09 재생성)
NEO4J_URI=bolt+s://XXXXXXXX.databases.neo4j.io
NEO4J_USERNAME=XXXXXXXX
NEO4J_PASSWORD=<새 password>
NEO4J_DATABASE=XXXXXXXX

# Upstash Redis (baby-ai-redis-v2, 2026-04-09 재생성)
REDIS_URL=rediss://default:<새 password>@<새 호스트>:6379
```

**절대 기존 키 그대로 두지 말 것** — `.env`는 `.gitignore`되지만 실수 방지.

---

## 사용자 액션 (P10): 서버 시작 + 자동 시드 검증

```bash
cd /e/A2A/our-a2a-project

# 1. 서버 시작
.venv/Scripts/python -m uvicorn neural.baby.api_server:app --reload --port 8000
```

**예상 로그** (성공 시):
```
INFO:     Started server process
INFO:     Starting up: initializing Neo4j and Redis...
INFO:     Schema ensured: 13 constraints, 9 lookup indexes, 3 vector indexes
INFO:     BrainRegions seeded: 9 new, 0 already existed
INFO:     Identity concepts seeded: 5 new, 0 already existed
INFO:     Neo4j + Redis ready
INFO:     Application startup complete.
```

**실패 시 체크**:
- DNS 실패: `.env` 호스트 오타 확인
- auth 실패: password 특수문자 escape 확인
- constraint 실패: AuraDB 버전이 2026 이상인지 확인

---

## 사용자 액션 (P11): 동작 검증

### 1. BabyState 초기 상태
```bash
curl http://localhost:8000/api/state
```
- 예상: `null` 또는 `{}` (아직 대화 없음, state 생성 전)

### 2. BrainRegion 9개 확인
```bash
curl http://localhost:8000/api/brain/regions
```
- 예상: 9개 region 반환 (brain_stem, cerebellum, amygdala, hippocampus, occipital, temporal, parietal, motor_cortex, prefrontal)

### 3. 정체성 Concept 5개 확인
```bash
curl "http://localhost:8000/api/brain/concepts?limit=10"
```
- 예상: 비비, 형아, 엄마, 안녕, 좋아 + is_seed=true, strength=0.8

### 4. 첫 대화 (speaker_id 포함)
```bash
curl -X POST http://localhost:8000/api/conversation \
  -H "Content-Type: application/json" \
  -d '{"message": "비비야 안녕! 오늘 기분이 어때?", "context": {"speaker_id": "brother", "speaker_name": "형아"}}'
```
- 예상: `{"output": "...", "success": true, "development_stage": 0, ...}`

### 5. UserModel 자동 생성 확인
```bash
curl http://localhost:8000/api/users
```
- 예상: `brother` UserModel 1개 (interaction_count=1)

### 6. Neo4j Browser에서 Hub-and-Spoke 검증
AuraDB Browser (`console.neo4j.io` → Query)에서:
```cypher
// 비비 concept의 MAPPED_TO weight
MATCH (c:Concept {name: '비비'})-[r:MAPPED_TO]->(br:BrainRegion)
RETURN c.name, br.name, r.weight

// 비비 concept의 ALSO_REPRESENTED_IN (분산 표상)
MATCH (c:Concept {name: '비비'})-[r:ALSO_REPRESENTED_IN]->(br:BrainRegion)
RETURN c.name, br.name, r.weight
ORDER BY r.weight DESC
```

**예상 결과**:
- MAPPED_TO: `비비 → temporal (weight: 0.5)`
- ALSO_REPRESENTED_IN:
  - `비비 → prefrontal (0.3)`
  - `비비 → amygdala (0.2)`

### 7. 수면 모드 CLS 검증 (선택)
몇 번의 대화 후:
```bash
curl -X POST http://localhost:8000/api/memory/replay \
  -H "Content-Type: application/json" \
  -d '{"salience_threshold": 0.3, "max_experiences": 5}'
```
- 응답에 `cls_reweights: <n>` 포함 → 성공

---

## 위험 요소 & 장기 운영

### AuraDB Free 자동 삭제 재발 방지
AuraDB Free는 **72시간 미사용 → PAUSED → 30일 후 DELETE**. 이번 같은 일 재발 방지 방법:

1. **유료 전환 (가장 안전)**: AuraDB Professional ($65/월~)
2. **주기적 ping cron**: 로컬 또는 GitHub Actions에서 6시간마다 `MATCH (n) RETURN count(n)` 실행
3. **Docker 로컬 전환**: `docker run neo4j:latest`로 완전 로컬화 — 무료, 정지 없음, 단 시각화·공유 불가

### Supabase 레거시 제거 (선택)
`.env`에 남아있는 `SUPABASE_URL`, `SUPABASE_ANON_KEY`는 **사용 안 됨** (활성 코드 0건 grep 검증). 안심하고 삭제 가능. Supabase 프로젝트 자체도 삭제해서 계정 정리 권장.

### 기존 백업 활용 (원하면)
`scripts/migration/migration_data/*.json`의 11,786 레코드 백업은 여전히 사용 가능. 만약 나중에 "820 Concept을 다시 불러오고 싶다" 생각이 들면:
```bash
.venv/Scripts/python scripts/migration/phase1_schema/import_to_neo4j.py
```
단 이 스크립트는 `MAPPED_TO` 관계에 weight 속성을 포함하지 않으므로, 복원 후 `ensure_indexes` → 수면 모드 1회 돌려서 weight 초기화 필요.

---

## 요약 체크리스트

- [ ] Neo4j AuraDB 신규 인스턴스 생성 + credentials 저장
- [ ] Upstash Redis 신규 인스턴스 생성 + TLS URL 확보
- [ ] `.env` 4~5줄 업데이트 (NEO4J_*, REDIS_URL)
- [ ] `uvicorn ... api_server:app --reload` 실행
- [ ] 로그에서 "Schema ensured" + "BrainRegions seeded: 9 new" + "Identity concepts seeded: 5 new" 확인
- [ ] `curl /api/brain/regions` 9개 반환 확인
- [ ] `curl /api/brain/concepts` 5개 시드 확인
- [ ] 첫 대화 시도 → UserModel + Experience + Concept 자동 생성 확인
- [ ] Neo4j Browser에서 비비 concept의 Hub-and-Spoke 매핑 확인
