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
- [ ] Causal Graph D3.js/vis.js 시각화
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

## Phase 4: Mobile Embodied AI (카메라/마이크) ⏳ PLANNED

> Embodied AI Survey 참고

### 목표
모바일 앱 → 로봇/AR 글래스

### 계획된 기능
- [ ] 카메라로 세상을 봄
- [ ] 마이크로 대화
- [ ] 스피커로 질문/반박
- [ ] 실제 물리 세계 이해

### 구현 항목
- [ ] 카메라 입력 처리
- [ ] 음성 인식/합성
- [ ] 멀티모달 학습
- [ ] 물체 인식 및 추적

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
