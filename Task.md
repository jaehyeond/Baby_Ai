# Task.md - 작업 추적

**최종 업데이트**: 2026-02-10

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

## 📊 현재 시스템 상태 (2026-02-10)

### Edge Functions (13개 - 모두 ACTIVE)

| Function | Version | JWT | 용도 | 상태 |
|----------|---------|-----|------|------|
| `conversation-process` | **v23** | ❌ | 대화 처리 (Gemini + 복합감정 + 자기평가 + neuron activations + spreading activation + **maybeImagine** + ThoughtProcess) | ✅ 정상 |
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
| `semantic_concepts` | 452+ | 개념/지식 (뉴런) |
| `concept_relations` | 519+ | 개념 간 관계 (시냅스) |
| `experiences` | 583+ | 경험 기억 (해마) |
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

---

## 🔄 현재 기능 흐름 (End-to-End)

### 1. 대화 흐름 ✅
```
사용자 입력 → /api/conversation → conversation-process (v23)
                                      ↓
                              [Gemini LLM 호출]
                              [정체성 개념 조회 - semantic_concepts]
                              [대화 컨텍스트 - audio_conversations]
                                      ↓
                              응답 + 감정 + 개념 추출
                                      ↓
                              experiences, emotion_logs,
                              semantic_concepts 저장
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

## ⚠️ Known Issues (2026-02-03)

### 1. ~~self_evaluation_logs 비어있음~~ ✅ 해결됨 (2026-02-06)
- **상태**: ~~0개 레코드~~ → 자동 생성 중
- **원인**: self-evaluation Edge Function을 아무도 호출하지 않았음
- **해결**: conversation-process v19에 `triggerSelfEvaluation()` 통합

### 2. 호기심 탐색 기록 적음
- **상태**: curiosity_queue 9개, exploration_logs 9개
- **원인**: 이전에 81% 실패율 문제 → v5에서 수정됨
- **현재**: 모두 "learned" 상태로 정상

### 3. visual_experiences 적음
- **상태**: 8개 레코드
- **원인**: 카메라 기능 사용 빈도 낮음
- **우선순위**: 낮음

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

## 📝 논문 준비 상태 (2026-02-10)

> 상세: [docs/PAPER_PLAN.md](docs/PAPER_PLAN.md) Section 9 참조

### 6-Agent Deep Review 결과 요약
- **ICDL 2026**: 적합하나 D-31 기한 tight (8-12주 분량)
- **ISMAR 2026**: 부적합 (AR/MR 필수) → **IEEE VIS 2026** 대안 추천
- **수식 F2 (Spreading)**: 코드 vs 논문 불일치 (CRITICAL)
- **Emotion modulation**: 계산되나 downstream 미적용
- **C_raw 베이스라인**: 미구현 (ablation 필수)
- **추천 로드맵**: arXiv preprint → VIS 2026 → ICDL 2027
- **현재 상태**: 사용자 방향 결정 대기 중

### 논문 전 기술 우선순위 (시스템 개선)
1. Spreading Activation 피드백 루프 (결과 → 응답 생성 영향)
2. Emotion modulation downstream 연결
3. 수식 F2, F4, F7, F8 코드-논문 일치
4. C_raw 베이스라인 실험 스크립트

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
