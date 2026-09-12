# Task.md - 작업 추적

> **2026-09-12 구현**: 별도 feature worktree에서 W1 복원/설치, W2 readiness/Redis/실행 결과 구분, E3·센서 offline 계약을 통합·검증했다. tests 473 passed/1 skipped. [구현 결과와 재실행](claudedocs/deployment/BIBI_FOUNDATION_IMPLEMENTATION_2026-09-12.md). 다음은 W3 세션 밖 회상 복구. E3 사용자 라벨, 실물 수집, 상시 host, 학습 승격은 아직 남아 있다.

**최종 업데이트**: 2026-02-23 (본문) · **2026-07-28 배너 갱신**

---

## ⚡ 2026-07-28 상태 배너 (아래 본문 상세는 2026-02 Supabase/Edge Function 시절 — STALE)

> **현 시스템 = FastAPI + Neo4j + Redis** (Edge Function 아님, 2026-03 마이그레이션 완료). 아래 "Edge Functions" 표 등은 역사 참고용.
> **2026-09-11 상세 R&D 우선순위(현행)**: `claudedocs/deployment/BIBI_RD_PRIORITY_PLAN_2026-09-11.md` W0 감사 완료. 다음 구현=W1 실제 백업·복원/설치 재현 + W2 local/TLS Redis·readiness·고정 성공 판정 제거, 이후 W3 새 프로세스의 오래된 개인 경험 회상. 대화 1,508건 벡터 0, gateway 기본 OFF, 벡터 인덱스 이름 불일치·최근 20건 후보 제한을 각각 해결한다. E5는 기존 E-cache 파일 검증 완료이며 아직 운영 연결 안 됨. W5 E3 사용자 review와 W6 몸/센서 계약은 독립 준비한다. 새 학습·DB write·전체 tests 실행은 이번 감사에서 0이다.
> **2026-09-11 실행 계획·worktree 배정**: `claudedocs/deployment/BIBI_HARDWARE_BRAIN_PLAN_2026-09-11.md`의 P0–P6을 따른다. 첫 구현은 백업·복원 준비와 UI 독립 runtime 최소 경계이며 기존 J1/B5 학습 제한을 유지한다. 영상 `u98cx_ZtPoY`는 별도 E worktree의 `gpt-5.6-sol/high` worker가 실제 파일·화면을 검토 완료했다. 원 실험 출처와 정확한 음성 내용은 미확인이다. 결과·해시는 계획 문서의 영상 수신 기록에 있다. 9월 16일까지 임시 worker 모델 규칙은 AGENTS R3가 정본이다. 계획·배정·영상 검토는 완료했지만 실제 runtime 구현·배포는 미완료다.
> **2026-09-11 상시 운영·이전 요구(하드웨어 목표 반영)**: 최종 목표는 로봇에 탑재하는 Physical AI의 뇌다. 현 PC 종료 중 활동에는 별도로 켜진 연산 장치가 필요하지만 소유 PC·로봇 내부 컴퓨터도 가능하며 외부 서버/유료 API를 필수로 두지 않는다. 현재 대화는 Gemini, 임베딩은 OpenAI 의존이 남아 있다. C 여유 2.46 GiB를 고려해 대형 빌드는 여유 공간을 확인한 장치·E/D에서만 수행한다. 2027년 2월 집 PC 이전을 위해 코드/비밀/기억/실행 상태/백업을 분리한다. Neo4j 인증·조회 정상(Experience 3,157 / Concept 1,122 / 관계 10,852), Redis DNS 실패. `claudedocs/deployment/ALWAYS_ON_2026-09-11.md`와 `GATES.md` 참고. 실제 배포·DB 이전·무인 활동·오프라인 모델 대체는 미실행. `LOCAL_CORE_DISTILL` OFF 유지.
> **2026-09-07 추가**: 브랜치 `feature/memory-gateway`(DB_Renewal 에 merge)에 답하기 전 회상+놀람 게이트(`MEMORY_GATEWAY=1` 옵트인)와 A0 :Person 시드. DB 실측 2026-09-07: Concept 1,111 / Experience 3,157 / UserModel 6 / Person 5. Upstash Redis 인스턴스 소멸(DNS 실패), OpenAI 크레딧 0. 상세는 CHANGELOG 최상단과 `claudedocs/research/MEMORY_GATEWAY_A0_A_2026-09-06.md`.
> **최신 세션 작업**: `CHANGELOG.md` 최상단. **전략·로드맵**: Claude auto-memory `program_roadmap_2026-07`(최상위 프로그램: 자기성장 아기 뇌 Phase 0~5, ~1.5~3년) + `self_learning_architecture_2026-07`(북극성: 진짜 자기학습 = 경험이 코어를 바꿈).
> **현재 진입점: [J1-R2-E3] primary 60행 agent 제안표 완료·사용자 review 대기** — 봉인 E2 결과에서 primary top-unjudged `60행`과 diagnostic-only positive-rank 이웃 `24행`을 분리해 packet `aec20a9d…`, audit `696fe080…`로 생성·재감사했다. 총 `84행/67 unique concepts`; 자동 label 지정은 0이다. agent 제안은 relevance `positive=1/context=52/hard_negative=4/unrelated=3`, vocabulary `canonical=36/alias=1/fragment=16/malformed=7`이며 아직 사용자 reviewed label/training data가 아니다. 24 deep-rank 이웃은 score-band 진단 전용으로 학습 negative에 넣지 않는다. 다음은 `claudedocs/research/J1_R2_E3_PRIMARY_REVIEW_AGENT_RECOMMENDATIONS_2026-07-28.md`의 승인·수정→별도 decision artifact→context를 binary negative에서 제외하는 학습 계약 순서다. learned head, graph cleanup, exact lockbox question, DB write, held-out/performance/production은 계속 false이며 `LOCAL_CORE_DISTILL`도 OFF다.
> **추가된 비차단 병렬 계획: [J1-R2-M0] Controlled Dream Audit** — E3 사용자 review와 별도 decision artifact가 만들어진 뒤, 그 reviewed vocabulary 판정과 고정 graph snapshot만 읽어 `alias/fragment/malformed/punctuation variant` 수정 후보를 제안한다. 이후 확장 후보는 contradiction/staleness/orphan/provenance-gap 탐지다. M0는 `detect→propose→human review`까지만 허용하며 E3→post-review 학습 계약→learned-head development 경로를 막지 않는다. 첫 반복의 DB write, 자동 label, merge/delete, graph cleanup 적용, model-weight 변경, `LOCAL_CORE_DISTILL`, 주기 실행은 금지한다. 실제 적용은 현재 평가 universe를 보존한 뒤 별도 승인·transaction·before/after snapshot·rollback 계약으로 분리한다. M0는 J3 verified sleep self-compile이 아니라 그 전 단계의 memory-integrity sidecar다.
> **이번 세션 추가 감사**: Phase 2 실그래프 row split에서 현재 그래프 기준 test pair `18/250(7.2%)`가 train에도 존재했고, 기존 야간 job은 test pair를 replay에 직접 포함했다. 기존 MRR은 fit/영속 탐색 증거로 강등했다. pair-disjoint split과 비퇴행 adapter save gate를 구현·단위검증했지만 GPU 재학습은 하지 않았다. 보호 handler는 무변경이다. 상세 `CHANGELOG.md` 최상단.
> **J-0 상세**: `claudedocs/research/JARVIS_GROUNDED_DEVELOPMENTAL_SELF_IMPROVEMENT_2026-07-16.md`. GDSI/DCSC는 구현 방향을 반증 가능한 단계로 줄인 가설이며 새 분야·AGI 달성 주장이 아니다.
> **UI/Ops 격리 결정**: Zoey OS Reel은 상위 program roadmap의 병렬 `관측/UI` 참고자료다. J1–J3 연구 critical path나 능력 주장에 포함하지 않으며, 실제 predictor provenance가 생기기 전 UI 구현·가짜 agent 상태 표시는 금지한다.
> **J-1.0 artifact**: `claudedocs/research/j1_question_as_experiment_readiness_20260716.json`. graph ranked ID를 확률로 변환하지 않았고 local-core GPU shadow inference도 실행하지 않았다.
> **J-1.1 artifacts**: `scripts/research/manifests/j1_1_train_calibration_a_20260716.json`, `scripts/research/inputs/j1_1_train_calibration_a_20260716_raw_scores_sealed.json`, `claudedocs/research/j1_1_train_calibration_capture_20260716.json`. raw score만 있으며 probability/calibrator는 아직 없다.
> **J-1.1A artifacts**: `scripts/research/inputs/j1_1_answer_source_amendment_20260716.json`, `scripts/research/inputs/j1_1_teacher_answers_20260716.json`, `scripts/research/inputs/j1_1_candidate_labels_draft_20260716.json`, `claudedocs/research/j1_1_answer_source_contract_20260716.json`. assistant draft라 calibration truth가 아니며, coverage/fairness gate도 false다.
> **J-1.1B/J-1.2 이후**: 95라벨 review와 train-only calibrator fit은 완료됐지만 79행/23양성, LOQO AUC `0.674689`로 held-out/performance/production은 false다. fresh-shadow는 train replay이며 J1.2 Engram은 definition-only, measurement count 0이다. J1-EXP-1 artifact는 `scripts/research/inputs/j1_exploratory_pre_answer_probe_b_20260721.json`이다.

---

## 🎯 Project Vision: Developmental Cognitive Architecture

> **"Pre-trained Knowledge + Developmental Learning Mechanisms = Adaptive Intelligence"**

### 핵심 철학

**"Baby부터" vs "고등학생부터"는 잘못된 이분법입니다.**

| 기존 논쟁 | 우리의 해답 |
|-----------|-------------|
| LLM Scaling (OpenAI) vs World Models (LeCun) | **Both are right - Hybrid approach** |
| 아기처럼 무지하게 시작? | ❌ 아님 |
| 고등학생 수준 지식부터? | ❌ 이것도 부분적 |
| **우리의 접근** | **LLM 지식 + 발달적 학습 메커니즘** |

### "Baby"는 은유다

- ❌ 지식이 없다는 의미가 **아님**
- ✅ **학습하고 성장하는 방식**이 아기와 같다는 의미
- Gemini/GPT의 지식은 그대로 활용
- 그 위에 뇌과학 기반 **발달적 메커니즘** 추가

---

## 📊 현재 시스템 상태 (2026-02-23 / DB 통계 2026-04-24 부분 갱신)

> ⚠️ Edge Functions/Frontend Routes 섹션은 2026-02-23 기준. Neo4j 통계만 최신.
> 전체 갱신은 다음 큰 마일스톤 시 일괄 수행 예정.

### Neo4j 통계 (2026-04-24 실측)
- Concept: **925** (820 → 925, +105 누적; 마지막 16개는 Quest 출처)
- Experience: **3068** (3039 → 3068, +29 누적; 마지막 6개 quest_passthrough)
- BrainRegion: 11 (occipital, thalamus, temporal, parietal, prefrontal, motor_cortex, hippocampus, amygdala, cerebellum, basal_ganglia, brain_stem)
- Quest 출처 메타: `c.sources=["quest_passthrough"]`, `c.quest_observation_count`, `c.last_quest_seen`


### Edge Functions (13개 - 모두 ACTIVE)

| Function | Version | JWT | 용도 | 상태 |
|----------|---------|-----|------|------|
| `conversation-process` | **v30** | ❌ | 대화 처리 (Gemini + 복합감정 + 자기평가 + neuron activations + spreading + maybeImagine + **Memory Recall Pipeline** + LC-NE modulator) | ✅ 정상 |
| `vision-process` | **v4** | ❌ | 이미지 분석 (Gemini Vision) | ✅ 정상 |
| `world-understanding` | v2 | ❌ | 물리 세계 이해 | ✅ 정상 |
| `audio-transcribe` | v2 | ❌ | STT (Gemini) | ✅ 정상 |
| `speech-synthesize` | v2 | ❌ | TTS (Google) | ✅ 정상 |
| `memory-consolidation` | v6 | ❌ | 수면 모드 기억 통합 (LLM 미사용) | ✅ 정상 |
| `generate-curiosity` | **v4** | ✅ | 호기심 생성 + 분류 (Phase A) | ✅ 정상 |
| `autonomous-exploration` | v5 | ✅ | 자율 탐색/학습 | ✅ 정상 |
| `self-evaluation` | v2 | ✅ | 메타인지 자기 평가 | ✅ 정상 |
| `autonomous-goals` | v2 | ❌ | 자율 목표 생성 | ✅ 정상 |
| `textual-backpropagation` | v1 | ✅ | 피드백 전파 | ✅ 정상 |
| `imagination-engine` | **v1** | ❌ | World Model 상상/예측 | ✅ 정상 |
| `test-tts` | v2 | ❌ | TTS 테스트용 | ✅ 정상 |

### Frontend API Routes (11개)

| Route | Edge Function | 상태 |
|-------|---------------|------|
| `/api/conversation` | conversation-process | ✅ 연결됨 |
| `/api/conversation/feedback` | textual-backpropagation | ✅ 연결됨 |
| `/api/vision/process` | vision-process + world-understanding | ✅ 연결됨 |
| `/api/audio/transcribe` | audio-transcribe | ✅ 연결됨 |
| `/api/speech/synthesize` | speech-synthesize | ✅ 연결됨 |
| `/api/memory/consolidate` | memory-consolidation | ✅ 연결됨 |
| `/api/curiosity` | generate-curiosity + autonomous-exploration | ✅ 연결됨 |
| `/api/metacognition` | self-evaluation | ✅ 연결됨 |
| `/api/goals/generate` | autonomous-goals | ✅ 연결됨 |
| `/api/world/understand` | world-understanding | ✅ 연결됨 |
| `/api/imagination` | imagination-engine | ✅ 연결됨 |

### Database 상태 (57개+ 테이블)

| 테이블 | 레코드 수 | 용도 |
|--------|----------|------|
| `semantic_concepts` | 488 | 개념/지식 (뉴런) |
| `concept_relations` | 616 | 개념 간 관계 (시냅스) |
| `experiences` | 965 | 경험 기억 (해마) |
| `emotion_logs` | 211+ | 감정 기록 (편도체) |
| `brain_regions` | 9 | ✅ 뇌 영역 (Phase B) |
| `concept_brain_mapping` | 452 | ✅ 개념→영역 매핑 (Phase B) |
| `neuron_activations` | 0+ | ✅ 실시간 활성화 (Phase B, Realtime) |
| `curiosity_queue` | 9 | 호기심 대기열 (모두 learned) |
| `exploration_logs` | 9 | 탐색 기록 |
| `procedural_patterns` | 102 | 절차 기억 (소뇌) |
| `memory_consolidation_logs` | 553 | 기억 통합 로그 |
| `visual_experiences` | 13 | 시각 경험 |
| `autonomous_goals` | 24 | 자율 목표 |
| `baby_state` | 1 | Baby AI 상태 (싱글톤) |
| `self_evaluation_logs` | 1+ | 메타인지 로그 (v19 자동 트리거) |
| `emotion_goal_influences` | 1+ | 감정→목표 영향 (v19) |
| `imagination_sessions` | 9 | World Model 상상 세션 (v22 자동 트리거) |
| `predictions` | 8+ | 예측 기록 (자동 검증) |
| `causal_models` | 3 | 인과관계 모델 |
| `pending_questions` | 8 | 능동적 질문 (모두 answered) |

---

## ✅ 완료된 Phase

### Phase 1-6: 기본 A2A 아키텍처 ✅
- A2A 프로토콜 기반 에이전트 통신
- Coder, Tester, Reviewer Agent
- CLI Client, Orchestrator

### Phase 7: Neural Pipeline ✅
- NeuralLayer, NeuralPipeline 클래스
- Forward/Backward Pass 구조
- Baby AI 발달 시스템 (EmotionalCore, CuriosityEngine, MemorySystem)
- Supabase 연동 (pgvector 임베딩)
- Cognitive Router (System 1/2 듀얼 프로세스)

### Phase 7.9: Frontend Visualization ✅
- Next.js 14 + TypeScript 대시보드
- React Three Fiber 3D 뇌 시각화
- Astrocyte 클러스터링 (Louvain 알고리즘)
- 감정 레이더 차트, 발달 프로그레스
- Vercel 배포 완료

### Phase 8: Textual Backpropagation ✅
- response_feedback 테이블
- feedback_propagation_logs 테이블
- textual-backpropagation Edge Function

### Phase 9: Self-Evolution Engine ✅
- prompt_evolution 테이블
- evolution_experiments 테이블
- self_reflection_insights 테이블
- learned_prompt_rules 테이블

### Phase 10: Team Optimization ✅
- agent_teams, team_performance 테이블
- agent_cooperation_patterns 테이블
- team_experiments 테이블

### Phase 11: Persistent Substrate ✅
- learning_sessions, learning_snapshots 테이블
- core_learnings 테이블
- session_restore_points 테이블

### Phase W: World Model Integration ✅ (2026-02-04)
- `imagination-engine` Edge Function v1 배포
- `/api/imagination` API route 생성
- `useIdleSleep` Phase 4 추가 (수면 시 상상 세션)
- Brain 페이지에 `ImaginationPanel` 추가
- 상상 세션 connections_discovered 3D 하이라이트
- 관련 파일:
  - `src/hooks/useImaginationSessions.ts` - 상상 세션 데이터 페칭
  - `src/components/ImaginationPanel.tsx` - 상상 패널 UI
  - `src/app/brain/page.tsx` - Brain 페이지 레이아웃 (3D + 패널)
  - `src/components/BrainVisualization.tsx` - 3D 하이라이트 로직

### Phase A: Proactive Questions ✅ (2026-02-04)
- `pending_questions` 테이블 (15컬럼, RLS, Realtime)
- `generate-curiosity` v4 (Gemini 분류 + pending_questions 라우팅)
- Supabase Realtime 연동 (새 질문 알림)
- 관련 파일:
  - `src/hooks/usePendingQuestions.ts` - 질문 데이터 + Realtime 구독
  - `src/components/QuestionNotification.tsx` - 토스트 알림
  - `src/components/QuestionBubble.tsx` - 답변 입력 모달
  - `src/components/QuestionList.tsx` - 질문 목록 카드
  - `src/app/page.tsx` - 메인 페이지 통합 (질문 탭)

### Phase V: Prediction Verification UI ✅ (2026-02-04)
- World Model 예측 검증 UI 구현
- 사용자가 예측이 맞았는지/틀렸는지 피드백 제공
- 예측 정확도 통계 표시
- 관련 파일:
  - `src/hooks/usePredictions.ts` - 예측 데이터 페칭 + 검증 로직
  - `src/components/PredictionVerifyPanel.tsx` - 예측 검증 패널
  - `src/app/brain/page.tsx` - Brain 페이지에 패널 토글 추가 (상상/예측)

### Phase A4.3: Quest 3S 온디바이스 VLM → Neo4j 통합 ✅ (2026-04-24)

**목표**: Quest 3S APK가 SmolVLM-500M으로 패스스루 영상 실시간 분석 → Concept 추출 → PC FastAPI → Baby AI Neo4j 영구 저장.

**전체 파이프라인** (검증 완료):
```
Quest 3S Camera 50 (1280×960 JPEG, 167ms)
  → SmolVLM-500M-Q8 추론 (5.5s avg, 35 TPS)
  → ConceptExtractor (~10 unique/round)
  → HttpURLConnection POST 127.0.0.1:8000  (USB 터널)
  → FastAPI /api/vision/quest-concepts
  → Neo4j: insert_experience + insert_concept(visual)×N + 후처리 Cypher
  → Concept 노드: c.sources=["quest_passthrough"], c.quest_observation_count, c.last_quest_seen
  → 자동 region 매핑: occipital (35%) + thalamus/temporal/parietal/prefrontal (분산 표상)
```

**핵심 결정**:
- **대안 B 채택**: 별도 라벨 X, 통합 `:Concept` + `c.sources` 필드 (대화에서 본 desk = Quest에서 본 desk 통합 학습)
- **adb reverse over USB**: 학교 EAP Wi-Fi 우회. PC `127.0.0.1:8000` ↔ Quest `127.0.0.1:8000` USB 터널.
- **HttpURLConnection 채택**: OkHttp 의존성 0 — APK 9.0MB 유지

**E2E 결과** (5 rounds):
- 누적 학습 검증: computer (qcnt 6, ucnt 5), monitor (5/4), text (4/3), keyboard (3/2)
- 같은 장면 반복 → R1 10 신규, R2~5 대부분 매치 (통합 학습 동작)
- 배터리 4% 소모, 온도 무변동

**관련 파일**:
- `neural/baby/api_server.py` — `POST /api/vision/quest-concepts` + Pydantic 모델
- `quest-passthrough-test/app/src/main/java/com/babyai/passthroughtest/QuestUploader.kt` — 신규 (HTTP client)
- `quest-passthrough-test/app/src/main/java/com/babyai/passthroughtest/MainActivity.kt` — `pc_url` intent extra + POST 호출
- `quest-passthrough-test/app/src/main/AndroidManifest.xml` — INTERNET + cleartext

**관련 메모리**: `memory/a4.3_completed.md`, `memory/passthrough_api_research.md`, `memory/dev_patterns.md`

### Phase A4.4: Color→Object Descriptor Binding ✅ (2026-04-24)

**목표**: VLM 응답에서 "yellow bottle" 같은 색상-객체 수식 관계를 Neo4j 관계로 저장. 색상 concept을 독립 유지하되 binding으로 연결 (V4+IT 분리표상 + binding problem 해결).

**offline precision 검증** (구현 전): A4.3에서 쌓인 36 quest_passthrough Experience의 vlm_response 재처리 → 34 pair, strict precision 94.1%, recall ~86%, FP 1건. GO 판정.

**구조**:
```
(yellow:Concept)-[:RELATES_TO {
    relation_type: "describes_color",
    aspect: "color",
    strength: 0.5→1.0 (+0.05/obs),
    evidence_count, observation_count,
    sources: ["quest_passthrough", ...],
    first_seen, last_seen
}]->(bottle:Concept)
```

- 기존 RELATES_TO 라벨 재사용 → frontend concept-relations API + sleep decay 자동 반영
- 방향성 보존 (descriptor → object), Hebbian canonical ordering 안 함
- aspect 필드로 미래 material/size/shape 확장 준비

**파서 규칙** (MVP):
- COLOR 셋 19종 + STOPWORDS_AFTER_COLOR 필터
- "COLOR + 바로 다음 단어(len≥2, non-stopword, non-color)" → pair
- 다층 방어: Kotlin len≥3 필터 + Python skip 전략으로 실질 FP 2.9%

**변경 파일**:
- `neural/baby/concept_binding.py` **신규** — 순수 함수 파서
- `neural/baby/neo4j_db.py` — `link_descriptor_to_object()` 메서드 추가
- `neural/baby/api_server.py` — `post_quest_concepts`에 binding 블록 + Response 필드 3개

**Smoke test 검증** (3 POST):
- created=2 (yellow→bottle, yellow→liquid)
- reinforced=2 (strength 0.5→0.55, evidence 1→2)  
- created=1 (white→keys)
- Concept 969→969 (오염 없음), smoke source 태그는 Cypher로 cleanup

**범위 밖 (A4.5+)**:
- be-copula ("keyboard is white")
- 공접 처리 ("blue and gray keys" 중 blue 누락)
- VLM 환각 사용자 정정 (예: 실제 고체를 "liquid"로 쓴 케이스)
- POS tagger 도입 — material/size/shape 동시 설계 시 통합 검토

**관련 메모리**: `memory/a4.4_completed.md`

### 🗺️ 로드맵 (2026-04-28 갱신)

교수님 피드백 (온디바이스 집착 지적) + 사용자 비전 (Quest XR 끝단) 반영. 아키텍처 결정: **Brain = backend, 모든 인터페이스 = clients**. 로봇도 client (transplant 아님).

```
A4.5α ✅ Hebbian / describes 격리 (2026-04-27)
A4.5C ✅ 파서 개선 — 공접 + be-copula (2026-04-27)
A4.5D 🆕 클라우드 VLM 옵션 추가 + 비교 실험
       └ Gemini Vision 백엔드, Quest는 JPEG 업로드만
       └ 온디바이스(SmolVLM) 모드는 폐기 X, optional 보존
A4.6   Live UI Phase 1~4 (PC dashboard orb)
       └ Phase 1 (백엔드 SSE) — 별도 세션 진행 예정
       └ Phase 2~4 — R3F orb + state hook + particle
A5     클라우드 backend (Railway/Fly.io + AuraDB Free)
A5.5   Quest spatial — Hand tracking + MRUK
       └ 검지 raycast → attention 신호
       └ MRUK 객체 dimensions → describes_size 관계
A6     Quest XR 공간 UI (passthrough 위 floating orb/파티클)
       └ A4.6의 R3F orb를 prototype 삼음 (shader 컨셉 공유)
A7+    로봇 client / 발달인지 연구 / 논문
       └ 로봇 = 또 다른 client (Brain backend 그대로 재사용)
```

**관련 메모리** (새 세션 필수 읽기):
- `memory/architecture_brain_clients.md` — Brain=backend 원칙
- `memory/roadmap_2026-04-28.md` — 위 로드맵 상세 + 미해결 결정

### Phase A4.5C: 파서 개선 — 공접 + be-copula ✅ (2026-04-27)

**목표**: A4.4 인접 규칙(precision 94%, recall 86%)의 FN 3건 해결.

**변경**: `concept_binding.py::extract_color_bindings()` 에 두 규칙 추가
- 공접: `COLOR1 + "and" + COLOR2 + NOUN`
- be-copula: `NOUN + (is|are|was|were) + COLOR`

**검증** (36 exp re-run + 3 smoke POST):
- precision 94.1% → ~95%
- recall ~86% → **~97.5%** (+11%p)
- 신규 binding: blue→keys (공접), white→keyboard ×4 (be-copula)
- 회귀 0

**관련 메모리**: `memory/a4.5c_parser_extension.md`

### Phase A4.5α: Hebbian / describes 관계 격리 ✅ (2026-04-27)

**목표**: A4.4의 `describes_color` 관계가 향후 `hebbian_update()` 호출 시 의미 충돌 없이 보존되도록 격리.

**발견 (controlled experiment, 2026-04-27)**:
속성 없는 `MERGE (a)-[r:RELATES_TO]->(b)` 는 같은 쌍의 임의 RELATES_TO 와 매치 → 다른 의미 관계의 속성을 덮어쓰는 동작 실측 확인. 현재 충돌 0건이지만 잠재 위험.

**변경**:
```diff
neural/baby/neo4j_db.py — hebbian_update()
- MERGE (a)-[r:RELATES_TO]->(b)
+ MERGE (a)-[r:RELATES_TO {source: 'hebbian'}]->(b)
```

ON CREATE 의 `r.source = 'hebbian'` SET 은 제거 (MERGE 패턴에 포함됨).

**검증**:
- describes_color 관계 보존 ✅ (str=0.55 변동 없음)
- Hebbian 관계 별도 신규 생성 ✅ (str=0.05, src='hebbian')
- 기존 Hebbian 1087개 ON MATCH 정상 누적 ✅ (회귀 없음)
- decay_connections() 는 모든 RELATES_TO 대상 → describes_color 도 자동 감쇠 ✅

**관련 메모리**: `memory/a4.5_alpha_isolation.md`

---

## 🔄 현재 기능 흐름 (End-to-End)

### 1. 대화 흐름 ✅
```
사용자 입력 → /api/conversation → conversation-process (v30)
                                      ↓
                              [키워드 추출 - extractKeywords()]
                              [기억 회상 - loadRelevantConcepts() + loadRelevantExperiences()]
                              [정체성 개념 조회 - semantic_concepts]
                              [대화 컨텍스트 - audio_conversations]
                                      ↓
                              [Gemini LLM 호출 (기억 + 정체성 + 컨텍스트 주입)]
                              [LC-NE 감정 조절 - computeEmotionalModulator()]
                                      ↓
                              응답 + 감정 + 개념 추출 + 기억 recall 통계
                                      ↓
                              experiences (extras: recall stats),
                              emotion_logs, semantic_concepts,
                              neuron_activations, spreading 저장
```

### 2. 비전 흐름 ✅
```
카메라 캡처 → /api/vision/process → vision-process
                                       ↓
                               [Gemini Vision]
                                       ↓
                               world-understanding
                                       ↓
                               물리 객체, 공간 관계 분석
                                       ↓
                               visual_experiences,
                               physical_objects 저장
```

### 3. 수면 모드 흐름 ✅ (LLM 미사용)
```
30분 스케줄 → memory-consolidation (v6)
                    ↓
            [DB 연산만 - LLM 없음]
            - 감정적 기억 강화 (emotional_salience > 0.3)
            - 오래된 기억 약화 (1일+ 미접근)
            - 패턴 승격 (2회+ 반복 → procedural_memory)
                    ↓
            memory_consolidation_logs 저장
```

### 4. 호기심 흐름 ✅
```
/api/curiosity (action: generate) → generate-curiosity
                                         ↓
                                 curiosity_queue에 질문 추가

/api/curiosity (action: explore) → autonomous-exploration
                                         ↓
                                 [Gemini 웹 검색]
                                         ↓
                                 exploration_logs,
                                 semantic_concepts 저장
```

### 5. 뇌 시각화 흐름 ✅
```
/brain 페이지 → useBrainData hook → Supabase 직접 조회
                                         ↓
                               semantic_concepts (뉴런)
                               concept_relations (시냅스)
                                         ↓
                               Louvain 클러스터링
                                         ↓
                               React Three Fiber 3D 렌더링
                                         ↓
                               + ImaginationPanel (상상 세션 시각화)
                               + PredictionVerifyPanel (예측 검증)
```

### 6. World Model 흐름 ✅
```
수면 모드 → useIdleSleep Phase 4 → /api/imagination
                                         ↓
                               imagination-engine
                                         ↓
                               [Gemini LLM: 상상/예측]
                                         ↓
                               imagination_sessions,
                               predictions 저장
                                         ↓
                               /brain 페이지에서 시각화
```

### 7. 능동적 질문 흐름 ✅ (Phase A)
```
호기심 생성 → generate-curiosity v4 → [Gemini: 질문 유형 분류]
                                         ↓
                               factual → autonomous-exploration (웹 검색)
                               personal/preference/experience → pending_questions
                                         ↓
                               Supabase Realtime INSERT 이벤트
                                         ↓
                               usePendingQuestions hook → 새 질문 감지
                                         ↓
                               QuestionNotification 토스트 알림
                                         ↓
                               QuestionBubble 모달 → 사용자 답변 입력
                                         ↓
                               submitAnswer → pending_questions 업데이트
                                          + semantic_concepts 저장
                                          + experiences 저장
```

### 8. 예측 검증 흐름 ✅ (Phase V)
```
/brain 페이지 → PredictionVerifyPanel
                     ↓
               usePredictions hook → predictions 테이블 조회
                     ↓
               검증 대기 목록 표시 (was_correct = null)
                     ↓
               사용자 검증 클릭 → VerifyModal
                     ↓
               맞았다/틀렸다 + 실제 결과 + 배운 점 입력
                     ↓
               verifyPrediction → predictions UPDATE
               (was_correct, verified_at, actual_outcome, insight_gained)
                     ↓
               정확도 통계 실시간 업데이트
```

---

## ⚠️ Known Issues (2026-02-23)

### 1. ~~self_evaluation_logs 비어있음~~ ✅ 해결됨 (2026-02-06)
- **상태**: ~~0개 레코드~~ → 자동 생성 중
- **원인**: self-evaluation Edge Function을 아무도 호출하지 않았음
- **해결**: conversation-process v19에 `triggerSelfEvaluation()` 통합

### 2. 호기심 탐색 기록 적음
- **상태**: curiosity_queue 9개, exploration_logs 9개
- **원인**: 이전에 81% 실패율 문제 → v5에서 수정됨
- **현재**: 모두 "learned" 상태로 정상

### 3. visual_experiences 적음
- **상태**: 13개 레코드
- **원인**: 카메라 기능 사용 빈도 낮음
- **우선순위**: 낮음

### 4. useBrainRegions.ts stage 5+ 미정의 (BUG)
- **증상**: DB stage=5인데 뇌 시각화에서 "BABY" 표시
- **원인**: `STAGE_PARAMS`에 0-4만 정의, 5 이상은 fallback → STAGE_PARAMS[2] (BABY)
- **추가**: BabyStateCard(1-based) vs useBrainRegions(0-based) 번호 체계 불일치
- **우선순위**: 높음 (즉시 수정 가능)

### 5. 발달 단계 자동 전이 미구현 (ARCHITECTURE GAP)
- **증상**: 대화를 아무리 해도 stage가 자동으로 올라가지 않음
- **원인**: `_check_stage_advance()`는 Python `development.py`에만 존재, Edge Function에 없음
- **현재**: DB stage=5는 이전 수동 설정 추정
- **패턴**: "정의만 되고 호출 안 됨" 5번째 사례
- **우선순위**: 중간

### 6. 기억 회상 깊이 부족 (v30)
- **증상**: 10개 concept이 recall되지만 Gemini가 2-3개만 피상적 사용
- **원인**: (a) concept description이 1줄짜리 (b) "1-3문장" 제약 (c) 현재 날짜 미제공
- **우선순위**: 중간 (프롬프트 강화로 개선 가능)

---

## ✅ 최근 완료된 Phase

### Phase A: 비비의 능동적 질문 시스템 ✅ (2026-02-04)

> **목표**: 비비가 사용자에게 먼저 질문할 수 있는 구조 구현
>
> **핵심 아이디어**: 호기심 중 "사실적 지식"은 웹 검색, "개인적/선호/경험" 관련은 사용자에게 직접 질문

| Day | 작업 | 상태 | 비고 |
|-----|------|------|------|
| 1 | `pending_questions` 테이블 생성 | ✅ 완료 | 15컬럼, RLS, Realtime 활성화 |
| 2 | `generate-curiosity` v4 수정 | ✅ 완료 | Gemini 분류 + pending_questions 라우팅 |
| 3 | Supabase Realtime 연동 | ✅ 완료 | usePendingQuestions hook + QuestionNotification |
| 4 | 질문 UI 컴포넌트 | ✅ 완료 | QuestionBubble 모달, QuestionList, 답변 저장 |
| 5 | 통합 및 배포 | ✅ 완료 | End-to-end 검증, Vercel 배포 |

**관련 문서**: [docs/PHASE_A_PROACTIVE_QUESTIONS.md](docs/PHASE_A_PROACTIVE_QUESTIONS.md)

---

## 🎯 궁극적 비전: "살아있는 인지 발달 시뮬레이터"

> AGI가 아니라, 아기의 뇌가 어떻게 개념을 형성하고, 감정이 사고에 어떻게 영향 주고,
> 기억이 어떻게 조직되는지를 **실시간 3D로 시각화하면서 직접 키울 수 있는 인터랙티브 시스템**.

### ✅ Phase C1 완료 - 활성화 전파 (Spreading Activation)

"사과" 활성화 → 시냅스 따라 "빨간색", "과일"로 파동 전파 → /brain에서 파동 시각화
+ A+C: 페이지 진입 시 마지막 대화 파동 자동 재생 + 누적 히트맵 base glow

### 다음 로드맵

| Phase | 기간 | 핵심 | 상태 |
|-------|------|------|------|
| C1: 활성화 전파 | 1주 | 시냅스 기반 파동 전파 + A+C 재생/히트맵 | ✅ 완료 |
| C2: 헵 학습 | 1주 | 함께 활성화 → 시냅스 강화 | ⏳ 대기 |
| C3: 기억 재생 | 1주 | 수면 시 뉴런 재활성화 | ⏳ 대기 |
| D1-3: 자발적 사고 | 3-4주 | 내적 시뮬레이션, 감정 주의, 자동 전이 | ⏳ 대기 |
| E2: 세상 이해 | 1-2개월 | 감각 통합, 환경 패턴, 사회적 인지 | ⏳ 대기 |
| F: 창발적 지능 | 2-3개월+ | 호기심 루프, 메타인지, 꿈 | ⏳ 대기 |

### 완료된 Phase 목록 (역순)
- ✅ Phase C1: 활성화 전파 + A+C 재생/히트맵 (2026-02-09)
- ✅ Phase B: 해부학적 뇌 시각화 (2026-02-07)
- ✅ Phase W2: Wake Word 연속 대화 (2026-02-07)
- ✅ Phase E: Emotion Engine 강화 (2026-02-06)
- ✅ Phase A/V/W: 능동적 질문/예측 검증/상상 엔진 (2026-02-04)
- ✅ Phase 1-11: Core Architecture (~ 2026-01-21)

---

## 📁 프로젝트 구조

```
our-a2a-project/
├── frontend/baby-dashboard/     # Next.js 대시보드
│   ├── src/
│   │   ├── app/                 # 페이지 (/, /brain, /sense, /sleep)
│   │   ├── components/          # React 컴포넌트
│   │   ├── hooks/               # useBrainData, useCamera, useImaginationSessions, etc.
│   │   └── lib/                 # Supabase client
│   └── package.json
│
├── supabase/                    # Edge Functions
│   └── functions/
│       ├── conversation-process/
│       ├── vision-process/
│       ├── memory-consolidation/
│       ├── generate-curiosity/
│       ├── autonomous-exploration/
│       ├── imagination-engine/
│       └── ...
│
├── agents/                      # A2A 서버 에이전트
├── neural/baby/                 # Python Baby AI 모듈
├── docs/                        # 설계 문서
│   ├── PHASE_6_MEMORY_CONSOLIDATION.md
│   ├── PHASE_7_METACOGNITION.md
│   ├── PHASE_8_AUTONOMOUS_CURIOSITY.md
│   └── PROJECT_VISION.md
│
├── CLAUDE.md                    # Claude Code 가이드
└── Task.md                      # 이 파일
```

---

## 📋 참고: LLM 사용 정책

> 자세한 내용은 CLAUDE.md 참조

| 영역 | LLM 사용 | 설명 |
|------|----------|------|
| **🌞 깨어있을 때** | | |
| 대화, 비전, 호기심 탐색 | ✅ Gemini | 사용자 상호작용 |
| **🌙 수면 모드** | | |
| 기억 통합, 메타인지, 시냅스 조정 | ❌ 미사용 | DB 연산만 |

**설계 철학**: LLM은 "도구", 학습/성장은 "내부 알고리즘"으로 수행
