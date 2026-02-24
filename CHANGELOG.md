# CHANGELOG.md - 일별 작업 기록

> 매일 작업 내용, 성공/실패, 배운 점을 기록합니다.
> 새 세션 시작 시 이 파일을 확인하여 컨텍스트를 복구합니다.

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
- [x] **Concept isolation bug 수정**: ablation runs 간 개념 오염 방지
  - 원인: `extractAndSaveConcepts()`이 concept 이름으로 글로벌 검색 → 프로덕션/다른 run의 concept 재사용
  - 결과: rep=1은 86 concepts, rep=2-5는 16-22 concepts (프로덕션 452개와 name 충돌)
  - 수정: concept/relation lookup에 `.eq("ablation_run_id", ablationRunId)` 스코핑 추가
  - `.single()` → `.maybeSingle()` (no-match 시 graceful handling)
- [x] 기존 ablation 데이터 전량 삭제 (5 runs + 모든 FK 참조)
- [x] Dry-run 검증 통과 (concept 격리 확인)
- [x] 20-run ablation 재실행 시작 (background task)

### ICDL 2026 논문 진행 ✅
- [x] §9.2 수식 정렬 갱신 (F7 이전 분석 오류 수정 - 실제로 이미 일치!)
- [x] §16 Wordbank CDI 비교 분석 추가
  - Fenson (2007), McMurray (2007), Day et al. (2025) 참고
  - BabyBrain vs CDI norms 정규화 비교 프레임워크
- [x] PARAMETER_TAXONOMY.md 생성 (3-Tier 파라미터 분류)
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

### SCI 논문 Deep Review ✅
- [x] 6개 병렬 에이전트 실행: ICDL 학회, ISMAR 학회, 수식 검증, Gap 분석, LLM 방어, Ablation 비판
- [x] PAPER_PLAN.md에 Section 9 (검토 결과) 추가
- [x] 핵심 발견:
  - ISMAR 부적합 (AR/MR 필수) → IEEE VIS 2026 대안
  - 수식 F2 CRITICAL (코드 BFS ≠ 논문 recurrence)
  - Emotion downstream 미적용, Spreading 피드백 없음
  - C_raw 베이스라인 필수
  - 추천: arXiv → VIS 2026 → ICDL 2027
- [x] 경쟁 논문 확인: Vygotskian Autotelic AI (Colas, Nature MI 2022), CoALA, Voyager, Reflexion

### 문서 정비 ✅
- [x] PAPER_PLAN.md: Section 9 추가 (6-Agent Review 결과)
- [x] MEMORY.md: 논문 검토 결과, v23 상태 반영
- [x] Task.md: v23 버전, 논문 준비 상태 섹션 추가
- [x] CHANGELOG.md: 2026-02-10 기록
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
