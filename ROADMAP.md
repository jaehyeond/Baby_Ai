# Baby AI Project Roadmap

> 아기의 인지 발달을 모방한 AI 시스템 개발 로드맵

## 프로젝트 개요

기존 AI 연구들의 한계를 극복하고 진정한 발달 AI를 구현:

| 기존 연구 한계 | 우리의 접근 |
|---------------|------------|
| 고정된 "나이" 또는 능력 수준 | 0부터 시작하는 발달 단계 (NEWBORN → CHILD) |
| 감정이 없거나 단순 시뮬레이션 | 감정 엔진 (호기심, 기쁨, 두려움, 좌절) |
| 실제 세계 상호작용 없음 | 뉴런/중추신경계 시뮬레이션 |
| 발달 "과정" 자체를 추적하지 않음 | 실시간 카메라/마이크 상호작용 (예정) |

---

## Phase 1: 대시보드 + 기본 학습 ✅ COMPLETED

### 핵심 컴포넌트
- [x] **EmotionalCore**: 기본 감정 (호기심, 기쁨, 두려움, 놀람)
- [x] **CuriosityEngine**: 내재적 동기 (예측 오류 기반)
- [x] **MemorySystem**: 기억 시스템 (에피소드/의미/절차)
- [x] **DevelopmentStage**: 발달 단계 (NEWBORN → TODDLER → CHILD)
- [x] **SelfModel**: 자아 모델 (능력, 선호, 한계 인식)

### 저장소
- [x] Primary: Supabase (pgvector) - Robot_Brain 프로젝트
- [x] Fallback: 로컬 JSON 파일 (.baby_memory/)

### Frontend Dashboard
- [x] 메인 대시보드 페이지
- [x] 감정 상태 시각화
- [x] 발달 단계 표시
- [x] 기억 통계

---

## Phase 2: World Model 통합 (상상/예측) ✅ COMPLETED

> Meta V-JEPA 2, Nvidia Cosmos 참고

### 백엔드 구현

#### 2.1 Prediction (예측) ✅
- [x] `make_prediction()` - 시나리오 기반 예측 생성
- [x] `verify_prediction()` - 예측 검증 및 정확도 추적
- [x] DB 테이블: `predictions`

#### 2.2 Simulation (시뮬레이션) ✅
- [x] `run_simulation()` - 가상 시나리오 단계별 실행
- [x] 성공 확률 계산
- [x] DB 테이블: `simulations`

#### 2.3 Imagination (상상) ✅
- [x] `start_imagination()` / `end_imagination()` - 세션 관리
- [x] `imagine_thought()` - 생각 생성
- [x] 인사이트 자동 추출
- [x] DB 테이블: `imagination_sessions`

#### 2.4 Causal Reasoning (인과 추론) ✅
- [x] `discover_causal_relation()` - 인과 관계 발견
- [x] 관계 유형: causes, enables, prevents, correlates
- [x] DB 테이블: `causal_models`

#### 2.5 Substrate 통합 ✅
- [x] `auto_generate_from_experience()` 자동 호출
- [x] 감정 상태 기반 상상 트리거 (호기심 > 0.7)
- [x] World Model 통계 추적

### Frontend 구현

#### 2.6 World Model 페이지 ✅
- [x] `/imagination` 페이지 생성
- [x] 탭 UI: Predictions, Simulations, Causal Graph
- [x] `ImaginationVisualizer` 컴포넌트
- [x] 실시간 상상 세션 표시

### 추가 고려 사항 (Optional)
- [ ] 행동 **전** 예측 → 최적 행동 선택 (CHILD 단계부터 활성화 예정)
- [x] **Causal Discovery 파이프라인 활성화** (2026-02-05)
  - `extract_causal_relations_from_experience()` 함수 추가
  - 경험 처리 시 자동으로 인과관계 발견
  - CausalGraph UI 컴포넌트와 연결됨
- [ ] Causal Graph D3.js/vis.js 시각화 (향후 개선)
- [ ] 예측 정확도 추이 대시보드

---

## Phase 3: 진짜 Emotion Engine (감정→행동) ✅ COMPLETED

> arXiv 논문 참고: Artificial Emotion

### 목표
현재: 감정 = 수치 (curiosity: 0.7)
개선: 감정이 학습에 실제 영향

### 핵심 컴포넌트

#### 3.1 EmotionalCore 확장 ✅
- [x] `get_learning_rate_modifier()` - 감정 기반 학습률 조절 (0.5~1.5)
- [x] `get_strategy_change_probability()` - 전략 변경 확률
- [x] `get_risk_tolerance()` - 위험 감수 수준
- [x] `should_avoid_pattern()` - 패턴 회피 결정
- [x] `get_attention_focus()` - 주의 집중 영역
- [x] `get_emotional_influence()` - 감정 영향 요약

#### 3.2 EmotionalLearningModulator 클래스 ✅
- [x] 5가지 전략 유형: EXPLOIT, EXPLORE, CAUTIOUS, ALTERNATIVE, CREATIVE
- [x] `adjust_learning_rate()` - 학습률 동적 조절
- [x] `select_strategy()` - 감정 기반 전략 선택
- [x] `evaluate_pattern()` - 패턴 사용 여부 평가
- [x] `get_exploration_decision()` - 탐험/활용 균형 결정
- [x] 패턴별 성공/실패 기록 및 추적

#### 3.3 BabySubstrate 통합 ✅
- [x] 전략 기반 컨텍스트 설정 (EXPLOIT/EXPLORE/CAUTIOUS/ALTERNATIVE/CREATIVE)
- [x] 반복 실패 시 전략 자동 재평가
- [x] 패턴 결과 기록 (성공/실패)
- [x] 감정 영향 정보를 BabyResult에 포함

#### 3.4 감정 → 행동 매핑 ✅
- [x] **기쁨(Joy)** → 학습률 +50% 증가, 성공 패턴 활용 (EXPLOIT)
- [x] **좌절(Frustration)** → 전략 변경 확률 증가, 대안 탐색 (ALTERNATIVE)
- [x] **두려움(Fear)** → 위험 회피, 보수적 접근 (CAUTIOUS)
- [x] **호기심(Curiosity)** → 탐험 촉진, 새로운 시도 (EXPLORE)
- [x] **지루함(Boredom)** → 변화 추구, 학습률 감소

### Frontend 구현 ✅
- [x] `EmotionalInfluenceCard` 컴포넌트
- [x] 학습률 조절 시각화
- [x] 전략 변경 확률 표시
- [x] 주의 집중 영역 레이더 차트
- [x] 현재 추천 전략 표시
- [x] 대시보드 "영향" 탭 추가

---

## Phase 4: Mobile Embodied AI (카메라/마이크) ✅ COMPLETED

> Embodied AI Survey 참고

### 목표
모바일 앱 → 로봇/AR 글래스

### 구현된 기능
- [x] 카메라로 세상을 봄 (Phase 4.1 - Camera Input)
- [x] 마이크로 대화 (Phase 4.2 - Microphone Input + STT)
- [x] 스피커로 질문/반박 (Phase 4.3 - Google Cloud TTS)
- [x] 실제 물리 세계 이해 (Phase 4.4 - Physical World Understanding)
- [x] 도구 사용 및 에이전시 (Phase 4.5 - Gemini Function Calling)

### 구현 항목
- [x] 카메라 입력 처리 (`vision-process` Edge Function, `/sense` 페이지)
- [x] 음성 인식/합성 (`audio-transcribe`, `speech-synthesize` Edge Functions)
- [x] 멀티모달 학습 (Gemini Vision + STT)
- [x] 물체 인식 및 추적 (`world-understanding` Edge Function)

---

## Phase 5: 자율 목표 설정 ✅ COMPLETED

> ICAIR 2025 논문 참고: CDALNs (Curiosity-Driven Autonomous Learning Networks)

### 목표
스스로 뭘 배울지 결정

### 구현된 기능
- [x] **Epistemic curiosity**: 지식 탐구 ("무엇을 배울까?")
- [x] **Diversive curiosity**: 다양성 추구 ("새로운 것을 시도할까?")
- [x] **Empowerment drive**: 영향력 추구 ("더 많은 것을 할 수 있게 될까?")
- [x] 자발적 탐구 목표 생성

### 구현 완료 항목
- [x] 내재적 동기 엔진 강화 (`calculateCuriosityScores()`)
- [x] 목표 생성 시스템 (`autonomous-goals` Edge Function v1)
- [x] 자기 평가 메커니즘 (`evaluateGoal()`)
- [x] 탐구 전략 학습 (12개 목표 템플릿)

### DB 테이블
- `autonomous_goals` - 자율 생성된 목표
- `goal_progress` - 목표 진행 상황
- `autonomy_metrics` - 자율성 지표 시계열
- `goal_templates` - 발달 단계별 목표 템플릿

### Frontend
- `AutonomousGoalsCard` 컴포넌트 (Goals/Metrics/History 탭)
- `/api/goals/generate` API 라우트

---

## Phase W: World Model Frontend Integration ✅ COMPLETED (2026-02-04)

> 수면 모드에서 자동 상상 세션 실행 및 Brain 페이지 시각화

### 구현된 기능
- [x] `imagination-engine` Edge Function v1 배포
- [x] `/api/imagination` API route 생성
- [x] `useIdleSleep` Phase 4 추가 (수면 시 상상 세션)
- [x] Brain 페이지에 `ImaginationPanel` 추가
- [x] 상상 세션 connections_discovered 3D 하이라이트

### 관련 파일
- `src/hooks/useImaginationSessions.ts` - 상상 세션 데이터 페칭
- `src/components/ImaginationPanel.tsx` - 상상 패널 UI
- `src/app/brain/page.tsx` - Brain 페이지 레이아웃 (3D + 패널)
- `src/components/BrainVisualization.tsx` - 3D 하이라이트 로직

---

## Phase A: Proactive Questions ✅ COMPLETED (2026-02-04)

> 비비가 사용자에게 먼저 질문하는 능동적 질문 시스템

### 구현된 기능
- [x] `pending_questions` 테이블 (15컬럼, RLS, Realtime)
- [x] `generate-curiosity` v4 (Gemini 분류 + pending_questions 라우팅)
- [x] Supabase Realtime 연동 (새 질문 알림)
- [x] `QuestionBubble` 모달 + `QuestionList` UI
- [x] 답변 → `semantic_concepts` 자동 저장

### 호기심 분류 로직
```
호기심 → Gemini 분류 → factual? → curiosity_queue → 웹 검색 (autonomous-exploration)
                     → personal/preference/experience? → pending_questions → 사용자에게 질문
```

---

## Phase V: Prediction Verification UI ✅ COMPLETED (2026-02-04)

> World Model 예측을 사용자가 검증할 수 있는 UI

### 구현된 기능
- [x] 예측 검증 패널 (`PredictionVerifyPanel`)
- [x] 예측 정확도 통계 표시
- [x] 사용자 검증 (맞았다/틀렸다 + 실제 결과 + 배운 점)

---

## Prediction Auto-Verification Pipeline ✅ COMPLETED (2026-02-05)

> 사용자 검증 없이 자동으로 예측 검증하는 파이프라인

### 구현된 기능
- [x] `auto_verify_predictions()` 함수 추가 (world_model.py)
- [x] `auto_generate_from_experience()`에서 자동 호출
- [x] 미검증 예측 조회 → 관련성 확인 → LLM으로 정확성 판단 → DB 업데이트
- [x] 5개 예측 자동 검증 완료 (`auto_verified=true`, `was_correct=true`)

---

## Phase E: Emotion Engine 강화 ✅ COMPLETED (2026-02-06)

> 5개 복합감정 + Valence/Arousal + 감정→목표 파이프라인

### 구현된 기능
- [x] 5개 복합 감정: pride, anxiety, wonder, melancholy, determination
- [x] Valence/Arousal 2D 감정 공간 (Russell's circumplex model)
- [x] `emotion_goal_influences` 테이블 + 자동 기록
- [x] `self_evaluation_logs` 자동 트리거 (conversation-process v19)
- [x] Frontend: EmotionRadar VA plot + compound badge + 추천 목표

---

## Phase W2: Wake Word 대화 흐름 개선 ✅ COMPLETED (2026-02-07)

> "비비야" wake word → 즉시 인사 + 연속 대화 모드

### 구현된 기능
- [x] `useWakeWord.ts` 7-state 머신: OFF/LISTENING/GREETING/CONVERSING/CAPTURING/PROCESSING/SPEAKING
- [x] "비비야"만 → 즉시 인사 ("네, 형아!") 후 연속 대화 모드
- [x] 연속 대화 모드에서 wake word 없이 자유롭게 대화
- [x] "대화 끝" / "그만" / "잘 가" / "바이" → 대화 종료
- [x] `/api/wake-greeting` API route
- [x] `WakeWordIndicator.tsx` GREETING/CONVERSING 상태 시각화

---

## Phase B: 해부학적 뇌 시각화 ✅ COMPLETED (2026-02-07)

> 9개 뇌 영역 + 구 좌표계 기반 3D Procedural Brain + Realtime 활성화

### DB
- [x] `brain_regions` (9개), `concept_brain_mapping` (452개), `neuron_activations` (Realtime)
- [x] `auto_map_concept_to_region()` 트리거
- [x] `conversation-process` v20: neuron_activations 자동 기록

### Frontend
- [x] `RealisticBrain.tsx` - React Three Fiber 3D 해부학적 뇌
- [x] `useNeuronActivations.ts` - Supabase Realtime 구독
- [x] `useBrainRegions.ts` - 영역 + 발달 단계 파라미터
- [x] `brain/page.tsx` - 해부학 ↔ 추상 뷰 토글

---

## Phase C1: Spreading Activation + ThoughtProcess ✅ COMPLETED (2026-02-09~10)

> 대화 시 뉴런 활성화 전파 + 사고 과정 시각화

### 구현된 기능
- [x] `conversation-process` v21→v23: spreading activation (BFS), neuron_activations에 experience_id
- [x] `maybeImagine()`: stage >= 3일 때 imagination_sessions 자동 생성 (v22 추가, v23 수정)
- [x] ThoughtProcessPanel: 대화 컨텍스트, 직접 활성화 경로, 연상 확산 그룹 시각화
- [x] brain/page.tsx: 파동 재생 + 누적 히트맵 + 사고 과정 패널
- [x] DB: brain_region_id 인덱스, trigger_type+created_at 복합 인덱스, get_brain_activation_summary RPC

### 논문 준비 상태 (2026-02-10)
- [x] PAPER_PLAN.md Section 9: 6-agent SCI deep review 완료
- 주요 발견: F2 spreading activation 수식-코드 불일치 (CRITICAL), ISMAR 부적합 → VIS 2026 대안
- 다음: 코드-수식 정합성 확보 → 데이터 수집 → 논문 작성

---

## 궁극적 프로젝트 비전: "살아있는 인지 발달 시뮬레이터"

> AGI가 아니라, 아기의 뇌가 어떻게 개념을 형성하고, 감정이 사고에 어떻게 영향 주고, 기억이 어떻게 조직되는지를 **실시간 3D로 시각화하면서 직접 키울 수 있는 인터랙티브 시스템**.

### Future Roadmap

#### Phase C: 뇌에 생명 불어넣기 (1-2주)
| 단계 | 핵심 | 효과 |
|------|------|------|
| C1: 활성화 전파 ✅ | 파동 전파 + A+C 재생/히트맵 + ThoughtProcess | /brain 진입 시 자동 파동 재생 + 사고 과정 패널 |
| C2: 헵 학습 | 함께 활성화된 뉴런 간 시냅스 강화 | 쓸수록 강해지는 뇌 |
| C3: 기억 재생 | 주기적 최근 경험 뉴런 재활성화 | 쉴 때도 뇌가 반짝임 |

#### Phase D: 자발적 사고 (3-4주)
| 단계 | 핵심 | 효과 |
|------|------|------|
| D1: 내적 시뮬레이션 | "만약 ~하면?" 자동 예측 | prefrontal 자발 활성 |
| D2: 감정 기반 주의 | amygdala가 attention 게이트 | 감정에 따라 집중 영역 변화 |
| D3: 발달 자동 전이 | 조건 충족 시 자동 단계 업 | 새 영역 "깨어남" |

#### Phase E2: 세상 이해 (1-2개월)
- 감각 통합 (cross-modal), 환경 패턴 인식, 사회적 인지 (Theory of Mind)

#### Phase F: 창발적 지능 (2-3개월+)
- 자기강화 호기심 루프, 메타인지, 꿈/창의성

---

## 관련 연구

| 프로젝트/연구 | 주요 내용 | 우리와의 차이점 |
|--------------|----------|---------------|
| [BabyAI (MILA)](https://github.com/mila-iqia/babyai) | 언어 학습 + Human-in-loop | 감정 없음, 고정 환경 |
| [Johns Hopkins (2025)](https://www.sciencedaily.com/releases/2025/12/251228074457.htm) | 생물학적 뇌 구조 → 훈련 없이 뇌 활동 | 발달 단계 없음 |
| [BrainCog](https://www.sciencedirect.com/science/article/pii/S2666389923001447) | 스파이킹 신경망 + 인지 기능 | 감정 엔진 없음 |
| [CDALNs (2025)](https://papers.academic-conferences.org/index.php/icair/article/view/4375) | 호기심 기반 자율 학습 | 267% 향상, 하지만 발달 단계 없음 |

---

## 변경 이력

| 날짜 | Phase | 변경 내용 |
|------|-------|----------|
| 2026-02-10 | C1 | conversation-process v23: maybeImagine() 수정, ThoughtProcess 패널, experience_id 추적 |
| 2026-02-10 | - | SCI 논문 6-agent deep review (PAPER_PLAN.md Section 9) |
| 2026-02-10 | - | 전체 문서 업데이트 (Task/CHANGELOG/CLAUDE/SQL_task/ROADMAP/PROJECT_VISION) |
| 2026-02-09 | C1 | Phase C1 완료: Spreading Activation + A+C (인덱스, RPC, replay, heatmap) |
| 2026-02-07 | B | Phase B: 해부학적 뇌 시각화 완료 (9영역, 452매핑, Realtime) |
| 2026-02-07 | W2 | Phase W2: Wake Word 연속 대화 모드 완료 (7-state) |
| 2026-02-06 | E | Phase E: Emotion Engine 강화 (복합감정, VA, 감정→목표) |
| 2026-02-06 | - | MD 파일 재구성: task_baby_brain.md 아카이브, ROADMAP 최신화 |
| 2026-02-05 | - | Prediction Auto-Verification 파이프라인 활성화 |
| 2026-02-05 | 2 | Causal Discovery 파이프라인 활성화 |
| 2026-02-05 | 2 | extract_causal_relations_from_experience() 함수 추가 |
| 2026-02-04 | V | Phase V: Prediction Verification UI 완료 |
| 2026-02-04 | A | Phase A: Proactive Questions 완료 (5일간 구현) |
| 2026-02-04 | W | Phase W: World Model Frontend Integration 완료 |
| 2026-01-21 | 5 | Phase 5 Autonomous Goal Setting 완료 |
| 2026-01-21 | 5 | autonomous-goals Edge Function v1 배포 |
| 2026-01-21 | 5 | AutonomousGoalsCard 컴포넌트 추가 |
| 2026-01-21 | 4.4 | Phase 4.4 Physical World Understanding 완료 |
| 2026-01-21 | 3 | Phase 3 Emotion Engine 백엔드/프론트엔드 완료 |
| 2026-01-21 | 3 | EmotionalLearningModulator 클래스 추가 |
| 2026-01-21 | 3 | EmotionalInfluenceCard 컴포넌트 추가 |
| 2025-01-21 | 2 | Phase 2 World Model 백엔드/프론트엔드 완료 |
| 2025-01-21 | 2 | ImaginationVisualizer 아이콘 클리핑 수정 |
| 2025-01-21 | - | ROADMAP.md 문서 생성 |

---

## 파일 구조

```
our-a2a-project/
├── neural/baby/
│   ├── __init__.py              # 모듈 exports
│   ├── emotions.py              # EmotionalCore (Phase 3 확장)
│   ├── emotional_modulator.py   # EmotionalLearningModulator (Phase 3)
│   ├── curiosity.py             # CuriosityEngine
│   ├── memory.py                # MemorySystem
│   ├── development.py           # DevelopmentTracker
│   ├── self_model.py            # SelfModel
│   ├── substrate.py             # BabySubstrate (메인, Phase 3 통합)
│   ├── world_model.py           # WorldModel (Phase 2)
│   ├── db.py                    # Supabase 연동
│   └── llm_client.py            # LLM 클라이언트
├── frontend/baby-dashboard/
│   ├── src/app/
│   │   ├── page.tsx             # 메인 대시보드 (Phase 3 탭 추가)
│   │   └── imagination/         # World Model 페이지
│   ├── src/components/
│   │   ├── ImaginationVisualizer.tsx
│   │   └── EmotionalInfluenceCard.tsx  # Phase 3 시각화
│   └── src/hooks/
│       └── useWorldModel.ts
└── scripts/
    └── test_world_model.py      # World Model 테스트
```
