# CHANGELOG.md - 일별 작업 기록

> 매일 작업 내용, 성공/실패, 배운 점을 기록합니다.
> 새 세션 시작 시 이 파일을 확인하여 컨텍스트를 복구합니다.

---

## 2026-04-24 (Phase A4.4 — Color→Object Descriptor Binding)

### 핵심 성과 ✅

VLM 응답의 "yellow bottle" 같은 색상-객체 인접 패턴을 파싱하여 Neo4j에 `(yellow)-[:RELATES_TO {relation_type:"describes_color"}]->(bottle)` 관계로 저장. Baby AI가 색상과 객체를 분리된 개념으로 유지하면서도 **binding 관계로 연결**하는 뇌과학적 표상(V4 vs IT) 구조 확립.

### 설계 결정 — offline 검증 기반

A4.3에서 누적된 36개 quest_passthrough Experience의 `vlm_response`를 파서로 재처리하여 **구현 전 precision 측정**:
- 34 candidate pair, 12 unique
- Strict precision **94.1%** (32/34), recall ≈ 86%
- FP 1건(`white→square`) — decay로 자연 정리 수용

**제1원칙 정합성 검토**: 색상 concept을 삭제(필터링)하지 않고 **관계로 분리**. V4(색상) ⟷ IT(객체) 분리 표상 + binding problem (Treisman) 해결 방식과 일치.

### 채택한 구조

- **저장 위치**: 기존 `RELATES_TO` 라벨 재사용 + `relation_type="describes_<aspect>"` 속성
- **aspect 필드**: 미래 material/size/shape 확장 준비
- **방향성**: descriptor → object (형용사가 명사를 수식하는 feedforward)
- **ON CREATE/MATCH**: strength 0.5→cap 1.0 (Hebbian-style), evidence_count++, sources 배열 멱등 추가
- frontend 시각화(`/api/brain/concept-relations`)에 자동 포함 — 관찰 가능성 확보

### 변경 파일 (3개)

**PC 측**:
- `neural/baby/concept_binding.py` **신규** (86 LoC) — COLOR 셋(19) + stopword 셋 + `extract_color_bindings(text)` 순수 함수. DB 의존 0, 대화 경로 재사용 가능.
- `neural/baby/neo4j_db.py` — `link_descriptor_to_object()` 메서드 추가 (+70 LoC). RELATES_TO 멱등 MERGE + 방향성 보존 + sources/observation_count/evidence_count 관리.
- `neural/baby/api_server.py` — `post_quest_concepts` 에 2e) 블록 삽입: 파서 호출 → name_to_id 맵 lookup → `link_descriptor_to_object` 호출. `QuestConceptsResponse`에 `bindings_created/reinforced/skipped` 3 필드 추가.

### 검증 (3 POST smoke test)

| POST | 문장 | 결과 |
|---|---|---|
| #1 | "yellow bottle of yellow liquid" | bindings_created=**2** (yellow→bottle, yellow→liquid) |
| #2 | 동일 문장 재시도 | bindings_reinforced=**2**, strength 0.50→0.55, evidence 1→2 ✅ |
| #3 | "white keys and touchpad" | bindings_created=**1** (white→keys) ✅ |

최종 DB 상태: describes_color 관계 3개 (yellow→bottle, yellow→liquid, white→keys). Concept 오염 없음 (969→969). smoke_test source 태그는 Cypher로 정리.

### 파서 규칙 (MVP)

1. COLOR (19종) 토큰 뒤 바로 다음 단어가
2. STOPWORDS_AFTER_COLOR 아니고
3. COLOR 아니고
4. 길이 2+ (acronym `hp` 허용 — A4.3 대비 완화)
이면 `(color, noun, "color")` pair 생성.

**다층 방어**: Kotlin ConceptExtractor 길이 3+ 필터가 payload 단계에서 `hp` 같은 acronym을 차단 → Python 파서가 `white→hp` 후보를 뽑아도 `name_to_id` 맵에 없어 자동 skip. 실질 DB 오염률 FP 2.9%.

### 범위 밖 (A4.5 이후)

- be-copula 구조 (`"keyboard is white"`)
- 공접 처리 (`"blue and gray keys"` — blue 누락)
- material/size/shape 확장 (aspect 필드는 준비됨)
- POS tagger 도입 (연속 형용사 구분 — `white square keys` FP 해결)
- 사용자 ground truth 정정 기능 (VLM 환각 보정, 예: "yellow liquid"는 실제 고체)

### 주의

- 현 VLM(SmolVLM-500M)이 실제 고체(비타민 통)를 "liquid"로 환각 — Baby AI는 VLM 출력 그대로 학습 (철학적 일관성). ground truth 정정은 A4.5+.
- Kotlin ConceptExtractor 길이 필터를 2로 완화할 경우 FP 방어 재평가 필요.

### 관련 메모리

- `memory/a4.4_completed.md` **신규** — 검증 Cypher + 파서 규칙 + smoke test 결과
- `memory/a4.3_completed.md` — baseline (36 exp 실측, 969 concept)

---

## 2026-04-24 (Phase A4.3 — Quest → PC FastAPI → Neo4j E2E)

### 핵심 성과 ✅

Quest 3S APK가 SmolVLM-500M 추론 후 추출한 Concept을 PC FastAPI로 POST → Neo4j에 저장하는 전체 파이프라인이 1+5 rounds E2E로 검증 완료.

**Concept 909 → 925 (+16 신규), Experience 3062 → 3068 (+6 quest_passthrough)**

### 변경 파일

**PC 측** (`neural/baby/api_server.py`):
- 추가: Pydantic 모델 `QuestImageMeta`, `QuestConceptsRequest`, `QuestConceptsResponse`
- 추가: `POST /api/vision/quest-concepts` endpoint
  - `insert_experience(task_type="vision", tags=["quest_passthrough","vision"], extras={...})`
  - `insert_concept(category="visual")` 루프 — 자동으로 occipital region 매핑
  - 후처리 Cypher: `c.sources` 배열 (멱등 추가), `c.quest_observation_count++`, `c.last_quest_seen`
  - `link_experience_concept` (INVOLVES, confidence=0.5)
- emotional_salience=0.4 (수동 관찰 — 대화 0.5~0.6보다 낮음)

**Quest 측** (`quest-passthrough-test/`):
- `app/src/main/AndroidManifest.xml`: `INTERNET`, `ACCESS_NETWORK_STATE` 권한 + `usesCleartextTraffic="true"`
- `app/src/main/java/com/babyai/passthroughtest/QuestUploader.kt` 신규 — HttpURLConnection + org.json (의존성 0)
- `app/src/main/java/com/babyai/passthroughtest/MainActivity.kt`: `pc_url` intent extra + 캡처 메타 추적 + POST 호출

### 핸드오프 계획 → 실제 구현 정정

| 계획 (2026-04-20) | 실제 (2026-04-24) | 사유 |
|---|---|---|
| `upsert_vision_concept()` 신규 메서드 | 추가 안 함, `insert_concept(category="visual")` 재사용 | 기존 메서드가 MERGE+멱등+region mapping 모두 수행 |
| `source` (단수) | `c.sources` (배열) | 같은 Concept이 대화+Quest 양쪽 출처 가능 |
| OkHttp 의존성 | HttpURLConnection 표준 라이브러리 | APK 크기 최소화 |
| 별도 라벨 `:VisionConcept` | 통합 `:Concept` + `c.sources` 필드 (대안 B 채택) | 사용자 결정 — Baby AI 통합 학습 |

### E2E 결과 (5 rounds)

성능: avg 5509ms (min 4525, max 5831, std 493), 배터리 100%→96% (4% drop), 온도 35°C 무변동

누적 학습 (같은 책상+컴퓨터 장면):
- R1: 10 신규
- R2: 0 신규 + 4 매치
- R3: 0 신규 + 5 매치
- R4: 2 신규 + 2 매치
- R5: 0 신규 + 4 매치

가장 많이 본: computer (qcnt 6), monitor (5), text (4), keyboard (3), webpage (3)
모든 Quest concept이 `:MAPPED_TO occipital` (해부학적으로 정확)

### 핵심 결정 — adb reverse over USB

학교망 `sgwlan_secure` (WPA2-Enterprise EAP)에서 Quest 인증 실패 반복 → EAP 디버깅 비효율.

**해결**: `adb reverse tcp:8000 tcp:8000` → Quest는 `http://127.0.0.1:8000` 호출 → USB 터널로 PC localhost 도달.

장점: Wi-Fi/방화벽/NAT 모두 우회. PC 방화벽 인바운드 설정 불필요. 가장 안정.
한계: USB 케이블 길이 한계 (이동 학습은 A4.4 이후 핫스팟 또는 EAP 인증서 필요)

### 검증된 사실 / 새 함정

- `usesCleartextTraffic="true"` 필수 (Android 14 기본 차단)
- APK 재설치 후 권한 재부여 필수 (`pm grant ... CAMERA`, `pm grant ... HEADSET_CAMERA`)
- `usage_count`는 신규 시 0 초기화, ON MATCH에서만 증가 (qcnt 6 / ucnt 5는 정상)
- FastAPI `extras`는 `json.dumps`로 직렬화 — 조회 시 deserialize 필요

### 관련 메모리

- `memory/a4.3_completed.md` — 운영 명령 + 검증 Cypher (재현용)
- `memory/dev_patterns.md` — adb reverse 황금 패턴, 권한 재부여 함정
- `memory/passthrough_api_research.md` — A4.0~A4.3 연속 일지

---

## 2026-03-23~24 (Phase C2 + Step 3 PendingQuestion)

### Phase C2: Hebbian Learning 구현 ✅

**핵심**: 함께 활성화된 개념 쌍의 RELATES_TO 관계를 강화/생성하는 Hebbian 학습

**변경 파일**:
- [x] `neural/baby/neo4j_db.py` — `hebbian_update()`, `get_hebb_stats()` 추가
  - UNWIND pairs, strength + hebb_strength 동시 갱신 (cap 1.0)
  - canonical ordering (min,max)으로 방향성 중복 방지
- [x] `neural/baby/conversation_handler.py` — Step 5.6 Hebbian 블록 삽입
  - 직접 공출현(delta=0.05) + 간접 공활성화(delta=0.02)
  - `activations = []` 초기화 추가 (try 블록 밖 안전 처리)
- [x] `neural/baby/api_server.py` — `GET /api/brain/hebb-stats` 엔드포인트

**설계 결정**: `strength` + `hebb_strength` 둘 다 갱신
- spreading activation에 즉시 반영 (strength)
- Hebbian 기여분 감사 추적 (hebb_strength)
- decay_connections()와 자연스럽게 경쟁 (강화 vs 망각)

### Step 3: PendingQuestion Neo4j 노드 + API ✅

**핵심**: CuriosityLog와 구조적으로 다른 PendingQuestion 노드 신규 생성

**변경 파일**:
- [x] `neural/baby/neo4j_db.py` — 4개 메서드 (insert/get/update/answer)
  - `(:CuriosityLog)-[:GENERATED]->(:PendingQuestion)` 관계 지원
- [x] `neural/baby/api_server.py` — 4개 엔드포인트 + Pydantic 모델
  - `publish_pending_question()` 활성화 (기존 미사용 → 호출 연결)
  - GET/POST /api/pending-questions, PATCH /{id}, POST /{id}/answer

**호출 지점 검증**: 6개 새 메서드 모두 엔드포인트에서 호출 확인 ✅

### Vision Neo4j 마이그레이션 — substrate.py 의존 제거 ✅

**핵심**: api_server.py에서 substrate.py(Supabase) 의존 완전 제거

**변경**:
- [x] `POST /api/vision/process` → Gemini Vision API 직접 호출 + Neo4j Experience 저장
- [x] `GET /api/vision/stats` → Neo4j Experience(task_type='vision') 카운트
- [x] `POST /api/process` → conversation_handler.handle_conversation() 위임
- [x] substrate.py import 0건 확인 (grep 검증 완료)

**검증**: `python -c "from neural.baby.api_server import app"` → Import OK, 46 endpoints

### Phase D1: 내적 시뮬레이션 ✅ + Phase D2: 감정 기반 주의 ✅

**D2 변경**:
- [x] `neural/baby/neo4j_db.py` — `get_spreading_activation()` depth 하드코딩 버그 수정
  - `*1..2` → `*1..{safe_depth}` (f-string, 1~5 범위 제한)
- [x] `neural/baby/conversation_handler.py` — `_get_attention_params()` 함수 추가
  - 호기심 > 0.7 → depth=3, limit=30 / 두려움 > 0.5 → depth=1, limit=10
  - Step 5.5에서 감정 기반 동적 spreading activation 파라미터 사용

**D1 변경**:
- [x] `neural/baby/conversation_handler.py` — Step 5.7 내적 시뮬레이션
  - stage >= 3 + activations >= 3 + 30% 확률 게이트
  - 상위 2개 활성화 개념으로 "만약 X와 Y가 연결된다면?" 자동 Prediction 생성
  - prediction_type="hypothetical", based_on_concepts 포함

### Phase D3: 발달 자동 전이 ✅

**핵심**: 대화 파이프라인 내에서 경험 수 기반 자동 stage 전이

**변경 파일**:
- [x] `neural/baby/conversation_handler.py` — Step 7.5 stage check 블록
  - `_STAGE_THRESHOLDS = {1: 10, 2: 30, 3: 70, 4: 150, 5: 300}`
  - 경험 수 초과 시 `update_baby_state(development_stage=next_stage)` + SSE 알림

**비판적 발견**: world_model.py, substrate.py, development.py, emotions.py의 핵심 로직이
Neo4j 마이그레이션 이후 conversation_handler.py에서 **단절됨** (6번째 "정의만 되고 호출 안 됨" 패턴)
→ D3는 development.py 의존 없이 Neo4j 기반으로 직접 구현

### Phase C3: 기억 재생 (Memory Replay) ✅

**핵심**: 수면 중 고감정 경험의 개념 네트워크를 재활성화 + offline Hebbian learning

**변경 파일**:
- [x] `neural/baby/neo4j_db.py` — `replay_recent_memories()` + `create_sleep_log()`
  - 고감정 경험 → INVOLVES → 개념 수집 → spreading activation → hebbian_update(delta=0.02)
  - SleepLog 노드 생성 (기존에 조회만 있고 생성 없었음 → 해결)
- [x] `neural/baby/api_server.py` — `POST /api/memory/replay` + `ReplayRequest` 모델
  - `publish_neuron_activation()` import 추가 → SSE로 sleep_replay 이벤트 전송
- [x] `frontend/baby-dashboard/src/hooks/useIdleSleep.ts` — Phase 1.5에 replay 호출 추가
  - consolidation 직후, curiosity 생성 전에 실행

**설계 결정**:
- 수면 중 Hebbian delta=0.02 (대화 중 0.05보다 약한 강화)
- `trigger_type: "sleep_replay"`로 대화 중 활성화와 구분
- SleepLog 생성 코드 없음 버그 해결

---

## 2026-03-19 (Phase 3)

### DB Migration Phase 3: SSE + Redis Pub/Sub 프론트엔드 연결 완료 ✅

**완료 항목**:
- [x] `neural/baby/conversation_handler.py` — Spreading Activation 추가 (Step 5.5)
  - `get_spreading_activation(concept_ids)` 호출 후 `publish_neuron_activation()` 발행
  - `saved_concept_ids` 수집 패턴으로 기존 루프 비파괴적 수정
- [x] `neural/baby/api_server.py` — `GET /api/brain/activation-summary` 엔드포인트 추가
  - Neo4j INVOLVES 관계 기반 heatmap + replay 데이터 반환
  - `useNeuronActivations` 초기 로드용
- [x] `frontend/baby-dashboard/src/hooks/SSEContext.tsx` — SSEProvider + Context (신규)
  - 단일 EventSource 앱 전체 공유
  - 지수 백오프 재연결 (3s → 6s → 12s → max 60s)
- [x] `frontend/baby-dashboard/src/hooks/useSSESubscription.ts` — SSE 구독 hook
  - `useSSESubscription(handler)` — SSEContext에서 구독/해제
  - handler ref 패턴으로 불필요한 재구독 방지
- [x] `frontend/baby-dashboard/src/hooks/useNeuronActivations.ts` — Supabase Realtime 제거
  - Supabase `channel('brain-activity')` 구독 → `useSSESubscription` 교체
  - 초기 heatmap: `supabase.rpc(...)` → `GET /api/brain/activation-summary` 교체
- [x] `frontend/baby-dashboard/src/components/Providers.tsx` — SSEProvider 래퍼 (신규)
- [x] `frontend/baby-dashboard/src/app/layout.tsx` — `<Providers>` 추가
- [x] `frontend/baby-dashboard/.env.local` — `NEXT_PUBLIC_FASTAPI_URL=http://localhost:8000` 추가
- [x] `scripts/migration/phase3_realtime/test_sse_stream.py` — 검증 스크립트

**비판적 검토로 수정된 원래 계획**:
- ioredis + Next.js `/api/events/route.ts`: 삭제 (FastAPI CORS로 브라우저 직접 연결 가능)
- pending_question / imagination 채널: Phase 4 이연 (발행자 미이식)
- useNeuronActivations의 concept/region name 조회 (Supabase): Phase 4 이연

**TypeScript 타입 검사**: `npx tsc --noEmit` → 오류 0개 ✅

**Go/No-Go 기준** (서버 실행 후 검증):
- [ ] `GET /api/brain/activation-summary` → heatmap + replay 반환
- [ ] `POST /api/conversation` → Redis `baby-ai:neuron_activation` 채널 발행
- [ ] 브라우저 EventSource → `baby_state` 이벤트 수신

---

## 2026-03-19 (Phase 2)

### DB Migration Phase 2: Neo4j Backend + FastAPI 기본 구조 완료 ✅

**완료 항목**:
- [x] `neural/baby/neo4j_db.py` — db.py BrainDatabase 완전 대체 (40개 async 메서드)
- [x] `neural/baby/redis_client.py` — Redis Pub/Sub + 캐시 래퍼
- [x] `neural/baby/api_server.py` — lifespan 패턴 + 기본 엔드포인트 추가
- [x] `neural/baby/conversation_handler.py` — DB-first 대화 파이프라인 구현
- [x] `scripts/migration/phase2_backend/test_fastapi_endpoints.py` — Phase 2 검증 스크립트

**비판적 검증으로 발견한 수정 사항**:
- Cypher SET에서 `min()` / `max()` 사용 불가 (집계 함수로 인식됨) → `CASE WHEN`으로 대체
- MERGE ON CREATE 시 `id: randomUUID()` 별도 SET 필요 (props 딕셔너리 포함 불가)
- `LLMClient.generate()`는 동기 함수 → `asyncio.to_thread()` 래핑으로 비동기화

**conversation_handler.py 파이프라인**:
1. `get_baby_state()` → 감정/발달 상태
2. Gemini 호출 (`asyncio.to_thread`)
3. `insert_experience()` → Neo4j 저장
4. `insert_concept()` + `link_experience_concept()` → 개념 연결
5. `log_emotion()` → EmotionLog 저장
6. `update_baby_state()` → 상태 업데이트
7. Redis `PUBLISH` → baby_state + experience 이벤트

**검증 결과 (4/4 PASS)**:
| 검증 | 결과 |
|-----|------|
| POST /api/conversation → Neo4j Experience 생성 | PASS |
| GET /api/state → BabyState 반환 | PASS |
| GET /api/brain/concepts → 835개 Concept 반환 | PASS |
| POST /api/memory/consolidate → 2151개 Experience 강화 | PASS |

---

## 2026-03-19 (Phase 1)

### DB Migration Phase 1: Neo4j 스키마 + 데이터 마이그레이션 완료 ✅

**비판적 검증으로 발견한 수정 사항**:
- embedding 차원: 계획의 768 → 실측 **1536** (OpenAI text-embedding-3-small)
- embedding REST 반환 형식: float[] 예상 → 실제 **JSON 문자열** (json.loads 파싱 필수)
- 실제 데이터 규모: MEMORY.md 기록(~3,577행) → 실측 **11,786행** (Baby AI가 성장함)
- `concept_brain_mapping` 테이블: `id` 컬럼 없음 (composite key만 존재)
- HTTP 206 = Partial Content = 정상 (처음에 에러로 오인, 수정)
- MCP Supabase가 다른 프로젝트(사주 앱) 연결 → REST API 직접 사용으로 우회

**완료 항목**:
- [x] `scripts/migration/phase1_schema/neo4j_schema.cypher` — DDL (제약조건 12개 + 인덱스 6개 + 벡터 3개)
- [x] `scripts/migration/phase1_schema/export_supabase.py` — Supabase → JSON (11,786행)
- [x] `scripts/migration/phase1_schema/import_to_neo4j.py` — JSON → Neo4j MERGE
- [x] `scripts/migration/phase1_schema/validate_migration.py` — 정합성 검증
- [x] `.gitignore` — `scripts/migration/migration_data/` 추가
- [x] **Neo4j 스키마 적용**: 20개 인덱스/제약조건 모두 ONLINE
- [x] **데이터 임포트 완료**: 11개 노드 레이블 + 4개 관계 타입
- [x] **벡터 인덱스 3개 ONLINE**: concept_embeddings, experience_embeddings, visual_embeddings

**검증 결과 (5/5 PASS)**:
| 검증 | 결과 |
|-----|------|
| 노드 수 일치 (11개 레이블) | PASS |
| 관계 수 일치 (4개 타입) | PASS |
| 임베딩 무결성 (148개 Concept) | PASS |
| 벡터 인덱스 상태 (3개 ONLINE) | PASS |
| 벡터 검색 동작 (score=1.0000) | PASS |

**Neo4j 최종 상태**:
- Nodes: BrainRegion(9) + Concept(820) + Experience(3039) + EmotionLog(1503) + ... = ~8,313
- Relationships: RELATES_TO(680) + MAPPED_TO(820) + INVOLVES(1060) + CAUSES(3) = 2,563
- Vector indexes: 1536-dim cosine, 148 concepts + 106 experiences embedded

**다음**: Phase 2 — `neo4j_db.py` + FastAPI 백엔드

---

## 2026-03-19

### DB Migration Phase 0: Neo4j AuraDB Free 연결 ✅

- [x] **Neo4j AuraDB Free 인스턴스 생성** — baby-ai (ID: b76cbc85)
- [x] **Python neo4j 드라이버 설치** — v6.1.0
- [x] **연결 문제 진단 및 해결** (3가지 함정 발견)
  1. `neo4j+s://` → AuraDB Free 단일노드에서 라우팅 테이블 조회 실패 (Windows 11 + AuraDB Free 구조적 한계, Community #74376)
  2. `bolt+s://[instance].databases.neo4j.io` → writer 노드로 일관되게 라우팅 안 됨
  3. `database_='b76cbc85'` 직접 지정 → "Database not found" (bolt+s 직접 연결 시)
- [x] **최종 해결책**: system DB → `SHOW DATABASES WHERE writer=true` → writer 주소 동적 조회 → 직접 연결
- [x] **검증 완료**: Neo4j 5.27-aura, Cypher 5, Nodes: 0, Indexes: 2
- [x] **.env 업데이트**: NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD, NEO4J_DATABASE 추가
- [x] **scripts/test_neo4j_connection.py** 작성 (연결 패턴 문서화 포함)

### DB Migration Phase 0: Upstash Redis 연결 ✅

- [x] **Upstash Redis 인스턴스 생성** — baby-ai-redis, GCP Tokyo (asia-northeast1)
- [x] **설정**: Eviction OFF, TLS ON, 500K commands/month, 256MB, 50GB bandwidth
- [x] **Python redis-py 설치** — redis[hiredis]
- [x] **연결 검증 완료** (3개 테스트 통과)
  1. SET/GET/DEL: `hello-baby-ai` 정상
  2. Pub/Sub: `baby-ai:test-channel` → 1 listener, 메시지 수신 성공
  3. Server INFO: Redis 8.2.0, standalone mode
- [x] **.env 업데이트**: `REDIS_URL=rediss://...` 추가 (TLS 필수)
- [x] **scripts/test_redis_connection.py** 작성 (asyncio + Pub/Sub 패턴 포함)

### Phase 0 완료 ✅✅

| 항목 | 상태 | 세부 |
|------|------|------|
| Neo4j AuraDB Free | ✅ | b76cbc85, v5.27-aura, Cypher 5 |
| Upstash Redis | ✅ | baby-ai-redis, v8.2.0, GCP Tokyo |

**다음 (Phase 1)**: Neo4j 스키마 생성 (Cypher DDL, vector indexes, constraints)

---

## 2026-02-23

### v30 기억 회상 라이브 테스트 + 전체 진단 ✅
- [x] **v30 테스트 결과**: 기억 회상 파이프라인 작동 확인
  - "날짜에 대해 공부 했어?" → concepts_recalled: 10, experiences_recalled: 5
  - v28 대비: "비비는 잘 몰라요!" → "날짜 박사가 될 거라서 잘 알고 있어요!" (확실한 개선)
  - DB description 직접 인용: "특정한 시점을 가리키는 단위"
  - 이전 대화 참조: "전에 형이랑도 이야기했잖아요!"
- [x] **한계 발견**: 10개 concept 중 2-3개만 피상적 활용 → 프롬프트 강화 필요

### 발견된 버그 3건
1. **useBrainRegions.ts stage 5 미정의** — STAGE_PARAMS에 5 없음 → fallback으로 BABY 표시 (DB는 stage=5)
2. **stage 번호 체계 불일치** — BabyStateCard(1-based) vs useBrainRegions(0-based)
3. **발달 단계 전이 미구현** — `_check_stage_advance()`는 Python에만 존재, EF에서 stage 올리는 로직 없음
   - "정의만 되고 호출 안 됨" 패턴 5번째 발견!

### DB 현재 통계 (2026-02-23)
| 테이블 | 수량 |
|--------|------|
| semantic_concepts | 488 (prod) |
| concept_relations | 616 |
| experiences | 965 |
| baby_state | stage=5, exp=2175 |

---

## 2026-02-20

### conversation-process v29/v30 배포 ✅
- [x] **v29**: Memory Recall Pipeline 구현
  - `extractKeywords()` — 한국어 조사 제거 + 불용어 필터링
  - `loadRelevantConcepts()` — ILIKE 기반 concept 검색
  - `loadRelevantExperiences()` — 과거 대화 경험 검색
  - `formatMemoryContext()` — 프롬프트에 기억 컨텍스트 주입
- [x] **v30 (v29b)**: 프롬프트 강화
  - `[필수 규칙]` 섹션 추가 — "모르겠어요/기억 안 나요/까먹었어요" 금지
  - `[기억 강도: X%]` 표시 추가
  - extras에 `concepts_recalled`, `experiences_recalled` 저장
  - 디버그 로그: keyword 추출, recall 결과 로깅

---

## 2026-02-18

### conversation-process v27 배포 ✅ (CRITICAL BUG FIX)
- [x] **Concept isolation bug 수정**: concept 이름으로 글로벌 검색 → 프로덕션 concept 재사용 문제
  - 수정: concept/relation lookup에 `ablation_run_id` 스코핑 추가
  - `.single()` → `.maybeSingle()` (no-match 시 graceful handling)
- [x] F4 emotion downstream 구현 (v24→v25→v26→v27)

---

## 2026-02-10

### conversation-process v23 배포 ✅
- [x] `maybeImagine()` 400 에러 수정 (jsonb[]/uuid[] 타입 불일치)
  - thoughts: string[] → {type, content, timestamp, connections}[] (jsonb[])
  - connections_discovered: string[] → {content, discovered_at}[] (jsonb[])
  - predictions_made: string[] → [] (uuid[]이므로 텍스트 예측 제외)
- [x] ThoughtProcess 패널 데이터 강화
  - RPC `get_brain_activation_summary()`에 concept_name, concept_category, region_name JOIN 추가
  - Realtime 구독에서 concept/region 조회 추가
  - ThoughtStep 인터페이스: conceptName, conceptCategory, regionName, triggerType, intensity
- [x] `RealisticBrain.tsx` + `brain/page.tsx` ThoughtProcessPanel 구현
  - "파동의 원인" (대화 컨텍스트) + "생각 경로" (direct) + "연상 확산" (spreading) 3섹션
  - 영역별 그룹화 + 접기/펼치기

### 문서 정비 ✅
- [x] MEMORY.md: v23 상태 반영
- [x] Task.md: v23 버전 업데이트
- [x] CLAUDE.md: brain-researcher agent, DB 통계 최신화
- [x] SQL_task.md: Phase B/C1 마이그레이션 기록
- [x] ROADMAP.md: Phase C1 완료 + v23 반영
- [x] PROJECT_VISION.md: Phase C1 완료 반영

---

## 2026-02-09

### Phase C1: 활성화 전파 (Spreading Activation) ✅
- [x] `conversation-process` v21: `spreadActivation()` BFS 함수 (maxDepth=2, decay=0.5)
  - 양방향 전파 (from/to, 역방향 0.7x)
  - trigger_type: 'spreading_activation'
- [x] `useNeuronActivations.ts`: spreadingRegions + waveCount 상태 추가 (5s decay)
- [x] `RealisticBrain.tsx`: SpreadingRipple 컴포넌트 (확장 링 + amber glow)
  - spreading 영역: 느린 맥동, 넓은 glow, amber 발광
  - 활성 영역 범례에 wave count + spreading 표시
- [x] MD 파일 업데이트 (ROADMAP, PROJECT_VISION, Task, CHANGELOG)
- [x] 빌드 성공 (TypeScript 에러 없음)

### Phase C1-A+C: 파동 재생 + 누적 히트맵 ✅
- [x] DB 마이그레이션: `brain_region_id` 인덱스 + `trigger_type, created_at` 복합 인덱스
- [x] RPC 함수 `get_brain_activation_summary()`: replay + heatmap 단일 호출
  - replay: 최근 대화 턴의 활성화 200개 (시간순)
  - heatmap: 영역별 누적 활성화 횟수 + 평균 강도
- [x] `useNeuronActivations.ts`: mount 시 RPC 호출 → 3초 staggered replay + heatmap state
- [x] `RealisticBrain.tsx`: heatmapIntensity → base glow (자주 쓴 영역 은은히 빛남)
  - replay 중 "마지막 대화 파동 재생 중..." UI 표시
  - 누적 활성화 기록 범례 (비활성 시)
- [x] 빌드 성공 (TypeScript 에러 없음)

### Phase C2: 대화 컨텍스트 + 상상 자동화 ✅
- [x] DB 마이그레이션: `neuron_activations`에 `experience_id` 컬럼 추가 + 인덱스
- [x] RPC `get_brain_activation_summary()` 업데이트: replay에 experience context (user_message, ai_response, dominant_emotion) 포함
- [x] `conversation-process` v22:
  - `logNeuronActivations()`에 `experienceId` 파라미터 추가
  - `spreadActivation()`에 `experienceId` 파라미터 추가
  - `maybeImagine()` 함수 추가 (4번째 "호출 안 됨" 패턴 수정!)
    - 조건: stage >= 3, curiosity > 0.6, 40% 확률
    - Gemini가 대화 기반 상상 토픽/thoughts/connections 생성
    - trigger: 'conversation_curiosity'
  - 응답에 `imagination_triggered` 필드 추가
- [x] `useNeuronActivations.ts`: `activationContext` 상태 추가 (experienceId, userMessage, aiResponse, emotion)
  - RPC replay에서 experience context 자동 추출
  - Realtime 구독에서 conversation 활성화 시 experience 조회
- [x] `RealisticBrain.tsx`: "파동의 원인" 패널 추가
  - 활성 영역 + replay 중 하단에 표시
  - 형아의 메시지 + 비비의 응답 + 감정 표시
- [x] 빌드 성공 (TypeScript 에러 없음)

---

## 2026-02-07

### Phase W2: Wake Word 대화 흐름 개선 ✅
- [x] `useWakeWord.ts` 7-state 머신 (OFF/LISTENING/GREETING/CONVERSING/CAPTURING/PROCESSING/SPEAKING)
- [x] "비비야" → 인사 → 연속 대화 (wake word 없이)
- [x] `/api/wake-greeting` API route + `WakeWordIndicator.tsx` 상태 추가
- [x] `sense/page.tsx` 통합

### Phase B: 해부학적 뇌 시각화 ✅
- [x] DB: `brain_regions`(9), `concept_brain_mapping`(452), `neuron_activations`(Realtime)
- [x] `conversation-process` v20: neuron activations 자동 기록
- [x] `RealisticBrain.tsx` + `useNeuronActivations.ts` + `useBrainRegions.ts`
- [x] `brain/page.tsx` 해부학/추상 뷰 토글
- [x] 빌드 + Vercel 배포

---

## 2026-02-06

### Emotion→Goal Pipeline + Self-Evaluation Fix ✅

**문제 발견:**
- `emotion_goal_influences` 테이블이 0건 (방금 만든 테이블인데 호출 안 됨 - 3번째 "정의만 되고 호출 안 됨" 패턴!)
- `self_evaluation_logs` 0건 (Edge Function 존재하지만 아무도 호출하지 않음 - 같은 패턴!)

**구현 내용:**
- [x] `conversation-process` v19 배포 (두 문제 한 번에 해결)
  - 복합 감정 감지 (`detectCompoundEmotion()`) + valence/arousal 계산 추가
  - `saveEmotionLog()` 업데이트: valence, arousal, compound_emotion 컬럼 채움
  - `saveEmotionGoalInfluence()` 함수 추가: 감정→목표 매핑 자동 기록
  - `triggerSelfEvaluation()` 함수 추가: 경험별 자기평가 자동 기록 (LLM 없이, 규칙 기반)
- [x] Frontend: EmotionRadar에 "감정 기반 추천 목표" 섹션 추가
  - GOAL_TYPE_CONFIG (6개 목표 타입 한국어 레이블/아이콘/설명)
  - EMOTION_GOAL_MAP (복합+기본 감정 → 목표 타입 매핑)
  - framer-motion 애니메이션
- [x] 빌드 테스트 통과 (20/20 페이지)
- [x] 실제 대화 테스트로 파이프라인 검증 완료

**검증 결과:**
| 테이블 | 이전 | 이후 |
|--------|------|------|
| emotion_goal_influences | 0 | 1+ (자동 생성) |
| self_evaluation_logs | 0 | 1+ (자동 생성) |
| emotion_logs (새 필드) | null | valence/arousal/compound 채워짐 |

**팀 분배:**
- Lead (Opus): Edge Function 분석 + v19 작성/배포 + 테스트/검증
- Frontend Agent (Sonnet): EmotionRadar.tsx 시각화 추가
- 순차 실행: 분석 → Edge Function → 검증 → Frontend → 빌드

**교훈:**
- "정의만 되고 호출 안 됨" 패턴 3번째 반복 → MEMORY에 "새 테이블/함수 추가 시 호출 지점 반드시 확인" 강화
- 두 개의 독립적 문제가 같은 근본 원인 (conversation-process에서 호출 부재) → 한 번의 업데이트로 동시 해결

**파일 변경 목록:**
| 파일 | 변경 |
|------|------|
| Supabase `conversation-process` | v18 → v19 (compound detect + VA + goal influence + self-eval) |
| `frontend/.../EmotionRadar.tsx` | GOAL_TYPE_CONFIG + EMOTION_GOAL_MAP + 추천 목표 섹션 |

---

### Emotion Engine Upgrade (Phase E) ✅

**작업 내용:**
- [x] DB Migration: emotion_logs에 `valence`, `arousal`, `compound_emotion` 컬럼 추가
- [x] DB Migration: `emotion_goal_influences` 테이블 생성 (감정→목표 영향 기록)
- [x] DB Migration: `recent_emotion_stats`, `daily_emotion_summary` view에 VA/compound 추가
- [x] DB: 기존 211개 emotion_logs 레코드 valence/arousal 백필 완료
- [x] Backend: `emotions.py`에 5개 복합 감정 추가 (pride, anxiety, wonder, melancholy, determination)
- [x] Backend: `COMPOUND_EMOTIONS` dict + `EMOTION_GOAL_MAP` dict 추가
- [x] Backend: `EmotionalState.detect_compound_emotion()` 메서드 추가
- [x] Backend: `EmotionalCore.suggest_goal_from_emotion()` 메서드 추가
- [x] Backend: `EmotionalState.to_dict()` 업데이트 (compound_emotion 필드 추가)
- [x] Frontend: `EmotionRadar.tsx` 탭 시스템 추가 (감정 레이더 / 감정 지도)
- [x] Frontend: Valence-Arousal 2D ScatterChart (Russell's circumplex model)
- [x] Frontend: Compound emotion badge (헤더 우측, framer-motion 애니메이션)
- [x] Frontend: `database.types.ts`에 새 컬럼/테이블 타입 추가
- [x] 빌드 테스트 통과 (TypeScript 에러 1건 수정)

**팀 분배 전략:**
- Lead (Opus): DB migration 직접 + 통합/빌드/검증
- Backend Agent (Sonnet): emotions.py 코드 작성
- Frontend Agent (Sonnet): EmotionRadar.tsx + database.types.ts 코드 작성
- 순차 실행: DB → Backend (검증) → Frontend (Backend 인터페이스 확정 후) → 통합

**파일 변경 목록:**
| 파일 | 변경 |
|------|------|
| `neural/baby/emotions.py` | COMPOUND_EMOTIONS, EMOTION_GOAL_MAP, detect/suggest 메서드 추가 |
| `frontend/.../EmotionRadar.tsx` | 탭 시스템 + VA plot + compound badge |
| `frontend/.../database.types.ts` | emotion_logs 새 컬럼 + emotion_goal_influences 타입 |
| Supabase | 4개 migration (컬럼추가, 테이블생성, 백필, view 재생성) |

---

### MD 파일 재구성 및 최신화 ✅

**작업 내용:**
- [x] `task_baby_brain.md` → `docs/archive/` 아카이브 (2026-01-20 이후 미업데이트, Task.md와 역할 중복)
- [x] `ROADMAP.md` → Phase A/V/W, Causal Discovery, Prediction Auto-Verification 추가
- [x] `PROJECT_VISION.md` → Phase 10/11/W/A/V 및 최신 파이프라인 추가 (v1.4)
- [x] `Task.md` → DB 통계 최신화 (447 뉴런, 519 시냅스, 583 경험)
- [x] `CHANGELOG.md` → 누락된 Prediction Auto-Verification 엔트리 추가

**DB 최신 통계 (2026-02-06):**
| 항목 | 수량 | 변화 |
|------|------|------|
| semantic_concepts | 447 | +34 (from 413) |
| concept_relations | 519 | +90 (from 429) |
| experiences | 583 | +123 (from 460) |
| emotion_logs | 211 | +27 (from 184) |
| visual_experiences | 13 | +5 (from 8) |
| causal_models | 3 | 신규 |
| predictions | 8 (5 verified) | +2 (from 6) |
| pending_questions | 8 (all answered) | 신규 |
| imagination_sessions | 9 | +5 (from 4) |

---

## 2026-02-05

### Prediction Auto-Verification 파이프라인 ✅

**문제 발견:**
- `verify_prediction()` 함수가 정의만 되어있고 호출되지 않음 (Causal Discovery와 동일 패턴)
- 미검증 예측 5개가 `was_correct = null`로 방치

**구현 내용:**
- [x] `world_model.py`에 `auto_verify_predictions()` 함수 추가
  - 미검증 예측 조회 → 관련 경험 확인 → LLM으로 정확성 판단 → DB 업데이트
- [x] `auto_generate_from_experience()`에서 자동 호출 통합
- [x] 5개 예측 자동 검증 완료 (`auto_verified=true`, `was_correct=true`)

---

### Causal Discovery 파이프라인 활성화 ✅

**문제 발견:**
- `causal_models` 테이블이 0건 (인과관계 데이터 없음)
- `discover_causal_relation()` 함수가 정의만 되어있고 호출되지 않음
- CausalGraph UI 컴포넌트는 이미 구현되어 있었지만 데이터 없이 빈 화면

**구현 내용:**
- [x] `world_model.py`에 `extract_causal_relations_from_experience()` 함수 추가
  - 감정 기반 인과관계 추출 (`_extract_emotion_based_causality`)
  - 성공/실패 기반 인과관계 추출 (`_extract_outcome_based_causality`)
  - LLM 기반 개념 인과관계 추출 (`_extract_concept_based_causality`)
- [x] `auto_generate_from_experience()`에 causal discovery 통합
  - 경험 처리 시 자동으로 인과관계 발견
  - `causal_relations` 결과 필드 추가
- [x] `test_world_model.py` 테스트 추가
  - `test_causal_discovery()` 함수
  - DB stats에 causal_models 조회 추가

**테스트 결과:**
```
Causal Models: 3
- 질문 → 호기심 (enables, strength: 0.60)
- 학습 → 이해 (enables, strength: 0.50)
- 질문 → 이해 (enables, strength: 0.50)
```

**파일 변경 목록:**
| 파일 | 변경 |
|------|------|
| `neural/baby/world_model.py` | extract_causal_relations_from_experience() 함수 추가 |
| `scripts/test_world_model.py` | test_causal_discovery() 테스트 추가 |
| `ROADMAP.md` | Causal Discovery 파이프라인 완료 표시 |
| `CHANGELOG.md` | 작업 기록 |

**기대 효과:**
- 대화할 때마다 인과관계 자동 축적
- CausalGraph 탭에서 시각화 가능해짐
- Baby AI의 인과 추론 능력 실제 작동

---

## 2026-02-04

### 작업 내용
- [x] MD 파일 구조 정리
  - Task.md에 "현재 진행 중인 Phase" 섹션 추가
  - CHANGELOG.md 생성 (이 파일)
  - `docs/PHASE_A_PROACTIVE_QUESTIONS.md` 생성

### Phase A Day 1 완료 ✅
- [x] `pending_questions` 테이블 생성
  - 15개 컬럼: question, question_type, context, priority, status, answer 등
  - question_type: personal, preference, experience, relationship
  - status: pending, asked, answered, skipped, expired
- [x] RLS 정책 설정 (Allow all access)
- [x] Supabase Realtime 활성화 (Day 3에서 사용)
- [x] 테스트 데이터로 CRUD 검증 완료

### 마이그레이션 기록
1. `create_pending_questions_table` - 테이블 + 인덱스 + 트리거
2. `add_rls_pending_questions` - RLS + Realtime

### 배운 점 / 메모
- Task.md에 "현재 진행 중인 Phase" 섹션이 없어서 작업 추적이 어려웠음
- CHANGELOG.md로 일별 기록을 분리하면 세션 간 컨텍스트 복구가 쉬움
- 기존 `curiosity_queue`와 일관된 스타일로 테이블 설계함

### Phase A Day 2 완료 ✅
- [x] `generate-curiosity` v3 코드 분석
  - 4가지 호기심 소스: concept_gap, failure, pattern, similarity
  - 모든 호기심 → curiosity_queue → autonomous-exploration (웹 검색)
- [x] 호기심 분류 로직 설계
  - Gemini LLM으로 factual vs personal/preference/experience/relationship 분류
  - 분류 프롬프트 설계 (CLASSIFICATION_PROMPT)
- [x] `generate-curiosity` v4 배포
  - `classifyCuriosity()`: Gemini로 호기심 분류
  - `saveToPendingQuestions()`: 개인적 질문 저장
  - `curiosityToQuestion()`: 개념 → 자연스러운 질문 변환
  - 새 action: `get_pending_questions`
- [x] v4 테스트 검증
  - 30개 호기심 생성 → 29 factual + 1 experience
  - factual → curiosity_queue ✅
  - experience → pending_questions ✅

### v4 변경 요약
```
v3: 호기심 → curiosity_queue → 웹 검색
v4: 호기심 → 분류(Gemini) → factual? → curiosity_queue → 웹 검색
                           → personal? → pending_questions → 사용자에게 질문
```

### Phase A Day 3 완료 ✅
- [x] `pending_questions` 타입 추가 (`database.types.ts`)
  - Row, Insert, Update 타입 정의
  - PendingQuestion, QuestionType, QuestionStatus 헬퍼 타입
- [x] `usePendingQuestions` hook 생성 (`hooks/usePendingQuestions.ts`)
  - Supabase Realtime INSERT 이벤트 구독
  - 질문 목록 fetch (priority 정렬)
  - `markAsAsked()`, `submitAnswer()`, `skipQuestion()` 메서드
  - `newQuestionAlert` 상태로 새 질문 알림
- [x] `QuestionNotification` 컴포넌트 생성 (`components/QuestionNotification.tsx`)
  - 슬라이드-인 토스트 알림 UI
  - 질문 타입별 색상/이모지 (personal, preference, experience, relationship)
  - "답변하기" / "나중에" 버튼
  - 15초 자동 dismiss
- [x] 메인 페이지 통합 (`app/page.tsx`)
  - usePendingQuestions hook 연결
  - QuestionNotification 렌더링
  - 브라우저 알림 연동 (sendNotification)
  - window.prompt로 임시 답변 UI (Day 4에서 모달로 개선)
- [x] 빌드 테스트 통과

### Day 3 파일 변경 목록
| 파일 | 변경 |
|------|------|
| `src/lib/database.types.ts` | pending_questions 타입 추가 |
| `src/hooks/usePendingQuestions.ts` | 새 파일 생성 |
| `src/hooks/index.ts` | usePendingQuestions export 추가 |
| `src/components/QuestionNotification.tsx` | 새 파일 생성 |
| `src/components/index.ts` | QuestionNotification export 추가 |
| `src/app/page.tsx` | Realtime 구독 + 알림 UI 통합 |

### Phase A Day 4 완료 ✅
- [x] `QuestionBubble` 모달 컴포넌트 생성 (`components/QuestionBubble.tsx`)
  - Full-screen 모달 오버레이
  - Textarea로 답변 입력
  - 확신도 선택 (💯확실해요 / 👍대체로 / 🤔잘 모르겠어요)
  - Ctrl+Enter로 빠른 제출
  - "나중에 답변할게요" 스킵 옵션
- [x] 답변 → semantic_concepts 저장 로직 (`usePendingQuestions.ts`)
  - `saveAnswerAsConcept()`: 답변을 semantic_concepts 테이블에 저장
  - 질문 타입별 카테고리 매핑 (personal→user_info, preference→user_preference 등)
  - `extras`에 질문 메타데이터 저장 (source, question_id, question_text 등)
  - `learned_concept_id`로 pending_questions와 연결
- [x] `QuestionList` 컴포넌트 생성 (`components/QuestionList.tsx`)
  - 여러 질문 목록 표시 (priority 정렬)
  - 확장/축소 가능한 카드 UI
  - 첫 번째 질문에 "우선" 뱃지 표시
  - 빈 상태 UI (궁금한 게 없을 때)
- [x] 메인 페이지 통합 (`app/page.tsx`)
  - window.prompt → QuestionBubble 모달로 교체
  - "질문" 탭 추가 (pending questions 개수 뱃지)
  - QuestionList 컴포넌트 렌더링
- [x] 빌드 테스트 통과

### Day 4 파일 변경 목록
| 파일 | 변경 |
|------|------|
| `src/components/QuestionBubble.tsx` | 새 파일 생성 |
| `src/components/QuestionList.tsx` | 새 파일 생성 |
| `src/components/index.ts` | QuestionBubble, QuestionList export 추가 |
| `src/hooks/usePendingQuestions.ts` | saveAnswerAsConcept 로직 추가 |
| `src/app/page.tsx` | QuestionBubble 모달 + questions 탭 통합 |

### Day 4 핵심 변경
```
Day 3: 알림 → window.prompt → 답변 저장
Day 4: 알림 → QuestionBubble 모달 → 답변 저장 + semantic_concepts 연동
       + questions 탭에서 전체 질문 목록 관리
```

### Phase A Day 5 완료 ✅ - E2E 통합 테스트
- [x] 테스트 환경 확인
  - Supabase URL: `https://extbfhoktzozgqddjcps.supabase.co`
  - `generate-curiosity` v4 Edge Function ACTIVE
  - `pending_questions` 테이블 Realtime 활성화 확인
- [x] generate-curiosity 호출 테스트
  - 21개 호기심 생성 → 20 factual + 1 experience
  - 분류 로직 정상 동작 (Gemini 2.0 Flash)
  - factual → curiosity_queue, personal → pending_questions
- [x] pending_questions INSERT 테스트
  - 테스트 질문: "아빠가 제일 좋아하는 노래가 뭐야?" (preference, priority 0.9)
  - Realtime INSERT 이벤트 발생 확인
- [x] 답변 → semantic_concepts 저장 flow 검증
  - 답변: "아빠는 김광석의 서른 즈음에를 제일 좋아해요"
  - semantic_concepts 저장 완료 (category: user_preference)
  - pending_questions.learned_concept_id 연결 확인
  - pending_questions.status → 'answered' 전환 확인

### Day 5 E2E Flow 검증 결과
```
generate-curiosity (v4)
    ↓ Gemini 분류
    ↓ personal/preference/experience/relationship
    ↓
pending_questions INSERT
    ↓ Realtime 이벤트
    ↓
Frontend usePendingQuestions
    ↓ newQuestionAlert
    ↓
QuestionNotification → QuestionBubble
    ↓ 사용자 답변 입력
    ↓
semantic_concepts INSERT (user_preference)
    ↓
pending_questions UPDATE (answered + learned_concept_id)
```

### 테스트 데이터
| 항목 | 값 |
|------|-----|
| question_id | aab0fd73-05fc-44bf-80b6-f79bb7d6466c |
| question | 아빠가 제일 좋아하는 노래가 뭐야? |
| answer | 아빠는 김광석의 "서른 즈음에"를 제일 좋아해요 |
| concept_id | 005f02d3-7290-4c1f-8397-1fc698fd0f9b |
| concept_category | user_preference |
| concept_source | proactive_question |

### Phase A 완료 요약 🎉
**Day 1**: `pending_questions` 테이블 설계 + Realtime 활성화
**Day 2**: `generate-curiosity` v4 - Gemini 분류 로직
**Day 3**: `usePendingQuestions` hook + `QuestionNotification` 알림
**Day 4**: `QuestionBubble` 모달 + `QuestionList` + semantic_concepts 저장
**Day 5**: End-to-end 통합 테스트 완료

### 다음 단계 제안
- [ ] 실제 프론트엔드 배포 후 브라우저에서 라이브 테스트
- [ ] 추가 질문 타입 (personal, relationship) 테스트
- [ ] 질문 만료 로직 구현 (status: expired)
- [ ] 답변 품질에 따른 concept strength 조정 로직

---

## 템플릿

```markdown
## YYYY-MM-DD

### 작업 내용
- [ ] 작업 1
- [ ] 작업 2

### 성공
- 무엇이 잘 됐는지

### 실패 / 문제
- 무엇이 안 됐는지
- **원인**:
- **해결**:

### 배운 점 / 메모
- 기억해야 할 것

### 다음 세션 TODO
- [ ] 다음에 할 것
```
