# SCI 논문 준비 마스터 플랜

**작성일**: 2026-02-10
**목표**: IEEE ICDL 2026 + IEEE ISMAR 2026 동시 투고
**D-Day**: ICDL Mar 13 (D-31) | ISMAR Abstract Mar 9 (D-27) / Paper Mar 16 (D-34)

---

## 1. 두 논문의 분리 전략 (연구 윤리 준수)

### Paper A: ICDL 2026
- **제목(안)**: "BabyBrain: A Stage-Gated Developmental Cognitive Architecture with Emotion-Modulated Learning"
- **RQ**: "How do biologically-inspired stage gates and emotional modulation affect cognitive capability emergence in LLM-augmented artificial agents?"
- **핵심 기여**: 발달적 인지 아키텍처 자체
- **실험**: Ablation study (정량적)
- **포맷**: 6-8 pages, IEEE format

### Paper B: ISMAR 2026
- **제목(안)**: "NeuroVis: Real-time 3D Visualization of Spreading Activation in Developmental Cognitive Architecture"
- **RQ**: "How does real-time 3D brain visualization with spreading activation waves enhance understanding of artificial cognitive processes?"
- **핵심 기여**: 시각화 기법과 인사이트
- **실험**: Expert evaluation + Task-based comparison (2D vs 3D)
- **포맷**: 4-9 pages + 2 refs, IEEE TVCG

### 윤리적 분리
| 항목 | ICDL | ISMAR |
|------|------|-------|
| 가설 | 발달 단계가 인지 능력에 영향 | 3D 시각화가 인지 과정 이해에 영향 |
| 독립변수 | 아키텍처 구성 (ablation) | 시각화 모달리티 (2D/3D) |
| 종속변수 | 개념 획득률, 예측 정확도 | 태스크 정확도, 완료 시간, 인지 부하 |
| 데이터 | 시스템 로그 | 사용자 실험 데이터 |
| 상호 인용 | ISMAR 참조 | ICDL 참조 |

---

## 2. SCI 논문 어셉 필수 요건 분석

### 2.1 독자적 기술 (Novelty)

**ICDL에서 주장할 독자성:**
1. **Stage-Gated Capability Emergence**: AI 시스템에 발달 단계 게이트를 적용한 최초 사례
   - 기존: BabyAI(MILA)는 고정 환경, 발달 단계 없음
   - 우리: 5단계 (NEWBORN→CHILD), 각 단계에서 새 능력 해금
2. **Emotion-Modulated Learning Strategy Selection**: 감정이 학습 전략을 실시간 선택
   - 기존: Affective Computing은 감정 인식에 집중
   - 우리: 감정 → 5가지 전략 (EXPLOIT/EXPLORE/CAUTIOUS/ALTERNATIVE/CREATIVE)
3. **LLM-Free Memory Consolidation**: 수면 모드에서 LLM 없이 기억 통합
   - 기존: 모든 과정에서 LLM 의존
   - 우리: 내부 알고리즘으로 시냅스 강화/약화

**ISMAR에서 주장할 독자성:**
1. **Anatomically-Mapped Artificial Brain Rendering**: AI 인지를 해부학적 뇌 구조로 매핑한 최초 사례
2. **Spreading Activation Wave Visualization**: BFS 기반 활성화 전파를 실시간 3D로 시각화
3. **Developmental Heatmap**: 누적 활성화 기록으로 "자주 쓰는 영역" 시각화

### 2.2 수식 (Mathematical Formalization)

#### F1: Concept Network as Weighted Graph
```
G = (V, E, W)
- V = {v₁, v₂, ..., vₙ} : 개념 노드 집합 (|V| = 452+)
- E ⊆ V × V × R : 관계 엣지 (|E| = 519+)
- R = {is_a, has_a, part_of, causes, used_for, ...} : 13종 관계 타입
- W: E → [0, 1] : 엣지 가중치 (strength)
```

#### F2: Spreading Activation Model
```
A_j(t+1) = σ( Σᵢ∈N(j) wᵢⱼ · A_i(t) · d^k + Σᵢ∈N⁻¹(j) wⱼᵢ · γ · A_i(t) · d^k )

where:
- A_j(t) : 노드 j의 시각 t에서 활성화 강도 ∈ [0, 1]
- N(j) : j의 순방향 이웃 (outgoing relations)
- N⁻¹(j) : j의 역방향 이웃 (incoming relations)
- wᵢⱼ : 엣지 가중치 (relation strength)
- d = 0.5 : 감쇠 계수 (decay factor)
- k : 홉 거리 (hop distance from source)
- γ = 0.7 : 역방향 감쇠 계수
- σ(x) = min(1, max(0, x)) : 클리핑 함수

초기 조건: A_source(0) = 0.6 for source concepts
종료 조건: A_j < τ_min = 0.05 (minimum intensity threshold)
최대 깊이: k_max = 2
```

#### F3: Emotional State Space (Russell's Circumplex)
```
E(t) = (v(t), a(t)) ∈ [-1, 1]²

v(t) = (curiosity + joy) / 2 - (fear + frustration) / 2    (valence)
a(t) = (curiosity + surprise + fear) / 3 - boredom · 0.5   (arousal)

6 기본 감정: e = (e_cur, e_joy, e_fear, e_sur, e_fru, e_bor) ∈ [0,1]⁶
5 복합 감정: compound(e) → {pride, anxiety, wonder, melancholy, determination}

compound detection rules:
  pride:        joy > 0.6 ∧ fear < 0.3
  anxiety:      fear > 0.4 ∧ frustration > 0.4
  wonder:       curiosity > 0.5 ∧ surprise > 0.4
  melancholy:   boredom > 0.5 ∧ frustration > 0.3
  determination: frustration > 0.4 ∧ curiosity > 0.5 ∧ fear < 0.4
```

#### F4: Emotion-Modulated Learning Rate
```
η'(t) = η₀ · M(e(t))

M(e) = 1.0
  + max(0, joy - 0.5) · 0.5        (기쁨 → +학습)
  + max(0, curiosity - 0.5) · 0.3   (호기심 → +학습)
  - max(0, fear - 0.5) · 0.4        (두려움 → -학습)
  - max(0, boredom - 0.5) · 0.3     (지루함 → -학습)
  + max(0, frustration - 0.5) · 0.2  (좌절 → +전략탐색)

M(e) ∈ [0.5, 1.5]
```

#### F5: Strategy Selection Function
```
σ* = argmax_{σ∈S} Score(σ, e(t), ctx)

S = {EXPLOIT, EXPLORE, CAUTIOUS, ALTERNATIVE, CREATIVE}

Score(EXPLOIT, e, ctx) = 1 + joy·0.5 + fear·0.3 - failures·0.2
Score(EXPLORE, e, ctx) = 1 + curiosity·0.6 + boredom·0.4 - fear·0.3
Score(CAUTIOUS, e, ctx) = 1 + fear·0.7 + failures·0.3 - curiosity·0.2
Score(ALTERNATIVE, e, ctx) = 1 + frustration·0.8 + failures·0.4 - joy·0.3
Score(CREATIVE, e, ctx) = 1 + curiosity·0.4 + frustration·0.3 + surprise·0.3 - fear·0.4

Inertia: if σ_prev exists and rand() > P_change(e):
  Score(σ_prev) *= 1.3

P_change(e) = 0.1 + max(0, frustration-0.5)·0.8 + max(0, boredom-0.5)·0.6
  + max(0, curiosity-0.7)·0.5 - max(0, joy-0.7)·0.2
```

#### F6: Developmental Stage Transition
```
S = {s₀, s₁, s₂, s₃, s₄} = {NEWBORN, INFANT, BABY, TODDLER, CHILD}

Transition: sᵢ → sᵢ₊₁ iff:
  (1) experience_count ≥ θ_exp(sᵢ₊₁)    AND
  (2) ∀m ∈ Milestones(sᵢ): achieved(m) = true

θ_exp = {INFANT: 10, BABY: 30, TODDLER: 70, CHILD: 150}

Milestones(NEWBORN) = {success_count≥1, unique_tasks≥3}
Milestones(INFANT)  = {success_count≥10, experience_count≥20}
Milestones(BABY)    = {success_count≥30, unique_tasks≥10}
Milestones(TODDLER) = {experience_count≥100 ∧ success_count≥70, unique_tasks≥20 ∧ success_count≥100}

Capability(sᵢ) ⊂ Capability(sᵢ₊₁)  (포함 관계)

Stage-gated functions:
  can_predict():        stage ≥ 2 (BABY)
  can_simulate():       stage ≥ 3 (TODDLER)
  can_imagine():        stage ≥ 3 (TODDLER)
  can_reason_causally(): stage ≥ 4 (CHILD)
```

#### F7: Emotion Decay (Mean Reversion)
```
eᵢ(t + Δt) = eᵢ(t) + (μ - eᵢ(t)) · min(δ · Δt, 0.5)

where:
- μ = 0.5 : 균형점 (homeostatic set point)
- δ = 0.05 : 감쇠 속도 (per hour)
- Δt : 경과 시간 (hours)
```

#### F8: Memory Consolidation (LLM-Free, Sleep Mode)
```
기억 통합 알고리즘 (memory-consolidation v6):

1. Replay Selection:
   P(replay_i) ∝ importance(i) · recency(i)
   importance(i) = emotional_weight + (failure ? 0.3 : 0.2) + curiosity_signal · 0.2

2. Pattern Extraction:
   For co-occurring concepts (cᵢ, cⱼ) in replayed experiences:
   Δwᵢⱼ = α · freq(cᵢ, cⱼ) / max_freq    (Hebbian-inspired)

3. Strength Update:
   strength'(v) = min(1.0, strength(v) + Σ_replays Δstrength)

4. Decay (forgetting):
   If last_accessed(v) > T_forget:
     strength'(v) = strength(v) · (1 - λ_forget)
```

#### F9: Exploration Rate (Emotion-Driven ε-Greedy)
```
ε(e) = min(1.0, curiosity · (1 - fear · 0.5) + max(0, boredom - 0.5) · 0.4)

Override rules:
  if boredom > 0.6: ε = 1.0  (강제 탐험)
  if fear > 0.7 and known_options > 0: ε = 0  (안전 선택)
```

#### F10: Neuron Activation Intensity (Brain Region Mapping)
```
I(concept_c, region_r) = min(1.0, 0.3 + 0.15 · count(concepts_in_r))

where count(concepts_in_r) = |{c' : R(c') = r, c' ∈ active_concepts}|

Region assignment: R: V → {prefrontal, temporal, motor_cortex, amygdala,
                           occipital, parietal, cerebellum, brain_stem, hippocampus}
```

### 2.3 실험 설계

#### ICDL Ablation Study

**조건 (Conditions):**
| ID | 조건 | 설명 |
|----|------|------|
| C_full | Full System | 모든 모듈 활성 |
| C_noemo | No Emotion | 감정 모듈 비활성 (η' = η₀ 고정, σ = EXPLORE 고정) |
| C_nostage | No Stage Gate | 모든 능력 처음부터 활성 (flat architecture) |
| C_nospread | No Spreading | 직접 활성화만, 전파 없음 |
| C_flat | Flat Baseline | 감정 없음 + 단계 없음 + 전파 없음 |

**메트릭 (Metrics):**
| 메트릭 | 수식 | 의미 |
|--------|------|------|
| CAR (Concept Acquisition Rate) | Δ\|V\| / Δconversations | 대화당 새 개념 획득 수 |
| PA (Prediction Accuracy) | correct_predictions / total_predictions | 예측 정확도 |
| EDI (Emotional Diversity Index) | H(emotion_distribution) = -Σ pᵢ log pᵢ | 감정 다양성 (Shannon entropy) |
| AR (Association Recall) | successful_spread / total_spread_attempts | 연관 개념 활성화 성공률 |
| RD (Relation Density) | \|E\| / \|V\| | 개념당 관계 밀도 |
| SSR (Strategy Selection Rate) | strategy_usage / total_decisions per strategy | 전략 선택 분포 |

**프로토콜:**
1. 각 조건에서 동일한 100개 대화 입력 수행
2. 각 조건 3회 반복 (variance 측정)
3. 결과: 조건별 메트릭 비교 (t-test, ANOVA)
4. 시각화: 발달 궤적 그래프, ablation bar chart

#### ISMAR Expert Evaluation + Task Study

**Expert Evaluation (N=5 HCI/VIS 전문가):**
- Heuristic evaluation: Nielsen's 10 usability heuristics
- Cognitive walkthrough: 3가지 시나리오
- 5점 Likert scale 설문

**Task-Based Comparison (N=10-15 참가자):**
| Task | 설명 | 측정 |
|------|------|------|
| T1: Region Identification | "가장 활성화된 뇌 영역은?" | 정확도, 시간 |
| T2: Activation Tracing | "사과→빨간색 전파 경로 추적" | 정확도, 시간 |
| T3: Development Assessment | "현재 발달 단계와 다음 단계 예측" | 정확도 |
| T4: Emotion-Brain Mapping | "현재 감정이 어떤 영역에 영향?" | 정확도 |

**조건:**
- 2D Dashboard (현재 메인 페이지 그래프)
- 3D Interactive Brain (현재 /brain 페이지)

**메트릭:**
- Task Completion Accuracy (%)
- Task Completion Time (seconds)
- NASA-TLX (cognitive load, 6 subscales)
- SUS (System Usability Scale, 10 items)

---

## 3. 팀 구조 및 역할

### 현재 Agent Team (변경 불필요)

```
Lead (Opus) - PM / Chief Scientist / Paper Writer
├── Research Division
│   └── brain-researcher (Opus) - 신경과학 기반, 수식 검증, 문헌 조사
├── Engineering Division
│   ├── backend-dev (Sonnet) - 실험 인프라, 메트릭 수집, 자동화
│   ├── frontend-dev (Sonnet) - 3D 시각화 강화, 스크린샷, 데모
│   └── db-engineer (Sonnet) - 실험 데이터 테이블, 분석 쿼리
└── Lead (겸임): 논문 집필, 통합 조율
```

### 역할 확장 (기존 4 agent로 충분)

| Agent | 기존 역할 | 추가 역할 |
|-------|----------|----------|
| brain-researcher | 신경과학 연구 | + 수식 검증 + Related Work 조사 |
| backend-dev | Python 모듈 | + 실험 자동화 스크립트 + 메트릭 로깅 |
| frontend-dev | React 컴포넌트 | + 논문 Figure용 스크린샷 + 시각화 개선 |
| db-engineer | DB + EF | + 실험 데이터 테이블 + 분석 RPC |
| Lead (나) | 총괄 | + 논문 집필 + 실험 설계 + 통합 |

---

## 4. 주간 일정 (5주 스프린트)

### Week 1: Foundation (Feb 10-16) — 모든 Agent 병렬

| Day | Lead | brain-researcher | backend-dev | frontend-dev | db-engineer |
|-----|------|-----------------|-------------|--------------|-------------|
| 1-2 | 수식 초안 작성 | 문헌 조사 시작 | 실험 프레임워크 설계 | 논문 Figure 목록 정리 | 실험 테이블 설계 |
| 3-4 | ICDL 아웃라인 | Related Work 30편+ | 메트릭 로깅 시스템 | 3D 뇌 스크린샷 도구 | experiment_runs 마이그레이션 |
| 5-7 | ISMAR 아웃라인 | 수식 검증 및 보완 | 100개 테스트 대화 생성 | Figure 초안 (아키텍처 다이어그램) | 분석 쿼리 (RPC) |

**Week 1 산출물:**
- [ ] 10개 수식 완성 (F1~F10)
- [ ] Related Work 목록 30편+ (ICDL 20 + ISMAR 10)
- [ ] 실험 프레임워크 코드
- [ ] 실험 데이터 테이블 (migration)
- [ ] 두 논문 아웃라인 (섹션별 bullet points)

### Week 2: Experiments + Implementation (Feb 17-23)

| Day | Lead | brain-researcher | backend-dev | frontend-dev | db-engineer |
|-----|------|-----------------|-------------|--------------|-------------|
| 8-10 | Ablation 실험 실행 감독 | 실험 결과 해석 | 5개 조건 × 3반복 실험 실행 | 2D vs 3D 비교 스크린샷 | 실험 결과 집계 쿼리 |
| 11-12 | ISMAR 평가 도구 설계 | 실험 결과 통계 분석 | 메트릭 CSV 추출 | Figure: 발달 궤적 그래프 | 데이터 내보내기 |
| 13-14 | Introduction 초안 | 통계 검증 (t-test) | 추가 실험 (필요시) | Figure: ablation 차트 | 최종 데이터 정리 |

**Week 2 산출물:**
- [ ] Ablation 실험 완료 (5조건 × 3반복 = 15runs)
- [ ] 통계 분석 결과 (ANOVA, post-hoc)
- [ ] 모든 Figure 초안 (6-8개)
- [ ] Introduction 초안 (두 논문 모두)

### Week 3: Paper Writing (Feb 24-Mar 2)

| Day | Lead | brain-researcher | frontend-dev |
|-----|------|-----------------|--------------|
| 15-17 | **ICDL 전체 초안** | 수식/기술 섹션 검토 | Figure 최종 버전 |
| 18-20 | **ISMAR 전체 초안** | Related Work 정밀화 | 데모 비디오 촬영 |
| 21 | 두 논문 교차 검토 | 일관성 확인 | 보충 자료 정리 |

**Week 3 산출물:**
- [ ] ICDL 논문 완전 초안 (6-8 pages)
- [ ] ISMAR 논문 완전 초안 (4-9 pages)
- [ ] 모든 Figure 최종 버전
- [ ] 데모 비디오 (ISMAR용)

### Week 4: Revision + ISMAR Abstract (Mar 3-9)

| Day | Task |
|-----|------|
| Mar 3-5 | 자체 리뷰 + 수정 (내용, 논리, 문법) |
| Mar 6-7 | Figure/Table 최종 정리, 참고문헌 정리 |
| Mar 8 | ISMAR abstract 최종 확인 |
| **Mar 9** | **ISMAR Abstract 제출** |

### Week 5: Final Submission (Mar 10-16)

| Day | Task |
|-----|------|
| Mar 10-12 | 최종 교정, 포맷 확인 |
| **Mar 13** | **ICDL Full Paper 제출** |
| Mar 14-15 | ISMAR 최종 수정 |
| **Mar 16** | **ISMAR Full Paper 제출** |

---

## 5. 각 논문 상세 구조

### Paper A: ICDL 2026 (6-8 pages)

```
1. Introduction (1 page)
   - 문제: LLM 기반 AI에 발달적 학습 메커니즘 부재
   - 동기: 인간 유아의 인지 발달에서 영감
   - 기여: 3가지 (stage gates, emotion modulation, LLM-free consolidation)

2. Related Work (1 page)
   - 2.1 Developmental AI (BabyAI, CDALNs)
   - 2.2 Affective Computing in Learning (Picard, emotion-cognition link)
   - 2.3 Cognitive Architecture (ACT-R, SOAR, OpenCog)

3. Architecture (2 pages)
   - 3.1 System Overview (Fig. 1: architecture diagram)
   - 3.2 Concept Network G = (V, E, W) — F1
   - 3.3 Spreading Activation — F2
   - 3.4 Emotional State Space — F3, F7
   - 3.5 Emotion-Modulated Learning — F4, F5
   - 3.6 Developmental Stage Gates — F6
   - 3.7 Memory Consolidation — F8

4. Experiments (1.5 pages)
   - 4.1 Experimental Setup (conditions, protocol)
   - 4.2 Results (Table + Figures)
   - 4.3 Ablation Analysis

5. Discussion (0.5 page)
   - 발견 해석, 한계점, 생물학적 타당성

6. Conclusion (0.5 page)
   - 요약, 향후 연구 (Hebbian learning, 감각 통합)
```

### Paper B: ISMAR 2026 (4-9 pages)

```
1. Introduction (1 page)
   - 문제: AI 내부 인지 과정 이해 어려움
   - 동기: 인지 과학 시각화 + XR 잠재력
   - 기여: 3가지 (anatomical mapping, spreading waves, developmental heatmap)

2. Related Work (1 page)
   - 2.1 Brain Visualization (connectome viewers, fMRI viz)
   - 2.2 AI Explainability Visualization (attention viz, activation maps)
   - 2.3 Immersive Analytics (VR for data analysis)

3. System Design (2 pages)
   - 3.1 Underlying Cognitive Architecture (brief, cite ICDL paper)
   - 3.2 Brain Region Mapping (9 regions, anatomical layout) — F10
   - 3.3 Spreading Activation Visualization — F2 (시각화 관점)
   - 3.4 Real-time Rendering Pipeline (React Three Fiber)
   - 3.5 Interaction Design (rotation, zoom, region selection, replay)
   - 3.6 Developmental Heatmap (cumulative activation)

4. Evaluation (2 pages)
   - 4.1 Expert Evaluation (N=5, heuristic + cognitive walkthrough)
   - 4.2 Task-Based Comparison (2D vs 3D, N=10-15)
   - 4.3 Results
   - 4.4 Qualitative Findings

5. Discussion (0.5 page)
   - 인사이트, 한계, WebXR 확장 가능성

6. Conclusion (0.5 page)
   - 요약, VR/AR 확장 로드맵
```

---

## 6. 필요한 Figure 목록

### ICDL Figures (6-7개)
1. **System Architecture Diagram** — 전체 아키텍처 블록 다이어그램
2. **Emotional State Space** — VA 2D plot with strategy regions + compound emotions
3. **Developmental Trajectory** — concept count over conversations (5 conditions)
4. **Ablation Results** — bar chart: CAR, PA, EDI, AR per condition
5. **Strategy Distribution** — pie/bar: 전략 선택 분포 per condition
6. **Spreading Activation Example** — "사과" → 전파 경로 그래프
7. **Stage Transition Timeline** — milestone 달성 시점 비교

### ISMAR Figures (5-6개)
1. **3D Brain Rendering** — RealisticBrain 스크린샷 (활성화 상태)
2. **Spreading Wave Visualization** — 파동 전파 시퀀스 (t=0, t=1, t=2)
3. **Heatmap Comparison** — 누적 활성화 히트맵 (before/after)
4. **2D vs 3D Comparison** — 동일 데이터의 2D 대시보드 vs 3D 뇌 뷰
5. **Task Results** — accuracy/time bar chart per condition
6. **Activation Context Panel** — "파동의 원인" UI 스크린샷

---

## 7. 리스크 및 대응

| 리스크 | 확률 | 심각도 | 대응 |
|--------|------|--------|------|
| ISMAR 사용자 실험 참가자 부족 | 높음 | 높음 | Expert evaluation (5명) + 소규모 pilot (10명) |
| Ablation 결과 유의미하지 않음 | 중간 | 높음 | effect size 보고, qualitative 분석 보완 |
| 시간 부족 (두 논문 동시) | 높음 | 중간 | ICDL 우선, ISMAR는 Work-in-Progress 트랙 고려 |
| WebXR 개발 지연 | 중간 | 낮음 | Web 3D로 충분 (ISMAR는 VR 필수 아님) |
| 수식 검증 오류 | 낮음 | 높음 | brain-researcher 이중 검증 |

### 우선순위 결정
1. **ICDL이 최우선** — 마감이 먼저이고, ablation이 핵심
2. **ISMAR은 ICDL 위에 빌드** — 시스템 설명 공유, 시각화에 집중
3. **사용자 실험은 최소 실행 가능 버전** — 5명 전문가 + 10명 task

---

## 8. 당장 시작할 작업 (Today, Feb 10)

### 즉시 실행 (병렬)
1. **Lead**: 이 문서 확정 + ICDL 아웃라인 작성
2. **db-engineer**: `experiment_runs`, `ablation_metrics` 테이블 마이그레이션
3. **backend-dev**: 실험 자동화 스크립트 골격 (`scripts/run_ablation.py`)
4. **brain-researcher**: ICDL related work 문헌 조사 시작
5. **frontend-dev**: 논문 Figure용 스크린샷 세팅

### 내일까지 완료
- [ ] 실험 테이블 DB 마이그레이션 완료
- [ ] 100개 테스트 대화 목록 작성
- [ ] Related Work 논문 10편+ 수집
- [ ] 수식 F1~F10 brain-researcher 검증

---

## 변경 이력

| 날짜 | 변경 |
|------|------|
| 2026-02-10 | 초안 작성 |
