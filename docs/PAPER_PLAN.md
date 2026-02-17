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

## 9. 논문 검토 결과 (2026-02-10, 6-Agent Deep Review)

> 6개 병렬 에이전트로 학회/수식/시스템Gap/LLM방어/Ablation 심층 검토 완료

### 9.1 학회 평가 결과

| 학회 | 적합도 | 판정 | 이유 |
|------|--------|------|------|
| **ICDL 2026** | ★★★★☆ | 적합 (but D-31은 tight) | 발달 AI 최고 학회, 우리 주제와 정합 |
| **ISMAR 2026** | ★☆☆☆☆ | **부적합 → 변경 필요** | AR/MR 핵심 요구 → WebGL만으론 desk reject |
| **IEEE VIS 2026** | ★★★★☆ | **대안 추천** | 같은 TVCG 저널, WebGL 시각화 논문 수용, design study 가능 |

**결론**: Paper B 대상 학회를 **ISMAR → IEEE VIS 2026**으로 변경 검토

### 9.2 수식 검증 결과 (Code vs Paper 대조)

| 수식 | 심각도 | 문제 |
|------|--------|------|
| **F2 (Spreading Activation)** | 🔴 CRITICAL | 코드=BFS sum, 논문=recurrence+max. `σ` 네이밍 충돌 |
| **F4 (Learning Rate)** | 🟡 HIGH | 코드 범위 [0.65,1.50] ≠ 논문 [0.5,1.5], threshold 0.6 vs 0.5 |
| **F7 (Decay)** | 🟡 HIGH | 코드=정률 감쇠, 논문=mean-reversion |
| **F8 (Consolidation)** | 🟡 HIGH | "Hebbian-inspired" 라벨 오류 → 실제는 co-occurrence 기반 |
| **F9 (Exploration)** | 🟢 MEDIUM | 코드=+0.2, 논문=max(0,b-0.5)*0.4 |
| F1,F3,F5,F6,F10 | ✅ OK | 코드와 일치 |

**추가 필요 수식**: F11(온라인 가소성), F12(예측 오차), F13(정보 놀라움), F14(수렴), F15(유사도)

### 9.3 시스템-논문 Gap 분석

| 주장 | 구현 상태 | 심각도 |
|------|----------|--------|
| Stage-gated development | ✅ 구현+작동 | - |
| Emotion modulation | ⚠️ 계산되나 **downstream 미적용** | 🟡 |
| Spreading activation | ⚠️ EF에서 기록만, **피드백 루프 없음** | 🟡 |
| Memory consolidation | ✅ 작동 (553 로그) | - |
| LLM-free sleep | ✅ 작동 | - |

### 9.4 Ablation 실험 설계 수정

**현재 설계 문제:**
- ❌ `C_raw` (bare LLM) 베이스라인 없음 → 리뷰어 1순위 질문
- ❌ 3회 반복 부족 (최소 10-30회 필요)
- ❌ EDI, AR, SSR 메트릭이 trivially confounded
- ❌ spreading activation이 피드백 효과 없으므로 C_nospread 무의미

**수정 방향:**
- 7개 조건으로 확장 (C_raw, C_nofeedback 추가)
- 10회 이상 반복 + growth curve 모델링
- 8개 신규 메트릭 추가 (GCR, UR, etc.)

### 9.5 LLM 연구 방어 전략

**핵심 방어선**: "10개 구성요소 중 9개가 LLM-independent"
- Stage gates, emotion engine, memory consolidation, synapse plasticity 등 → LLM 교체 가능
- LLM = substrate, 연구 대상은 그 위의 발달 메커니즘

**금지 표현**: "이해한다", "의식", "발달을 복제"
**필수 표현**: operational definitions, "constrained LLM for developmental modeling"

### 9.6 최종 판정 및 로드맵

| 옵션 | 내용 | 실현성 |
|------|------|--------|
| A | ICDL 2026 D-31 전력 질주 | ⚠️ 8-12주 분량, 4.5주 남음 |
| B | ICDL Workshop/Poster (4p) | ★★★ 가능하나 임팩트 ↓ |
| **C+D** | **ICDL 2027 + VIS 2026 + arXiv** | **★★★★★ 추천** |

**추천**: 옵션 C+D → 즉시 arXiv preprint → VIS 2026 (Oct) → ICDL 2027

### 9.7 즉시 해야 할 기술 작업 (논문 무관하게 시스템 개선)

1. Spreading Activation 피드백 루프 구현 (결과가 응답 생성에 영향)
2. Emotion modulation downstream 연결 (학습률 → 기억 통합)
3. 수식 F2, F4, F7, F8 코드-논문 일치시키기
4. C_raw 베이스라인 실험 스크립트

**⚠️ 사용자 결정 대기**: 옵션 A-D 중 선택 필요 (2026-02-10 시점)

---

## 10. Generative Agents 비교 분석 (2026-02-11)

> GA(Park et al., UIST 2023)와의 명확한 차이 정리. ICDL Related Work 및 리뷰어 방어용.

### 10.1 GA vs BabyBrain 15차원 비교

| 차원 | Generative Agents | BabyBrain | 차이 수준 |
|------|-------------------|-----------|----------|
| **목적** | 사회 행동 시뮬레이션 | 인지 발달 모델링 | 🟢 근본 다름 |
| **메모리 구조** | 단일 텍스트 스트림 | 3중 기억 (에피소드/의미/절차) | 🟢 근본 다름 |
| **검색 방식** | α·recency + β·importance + γ·relevance | Spreading Activation (BFS) | 🟢 근본 다름 |
| **감정 시스템** | 없음 | 6 기본 + 5 복합 + VA 공간 | 🟢 근본 다름 |
| **발달 단계** | 없음 (성인 고정) | 6단계 (NEWBORN→CHILD) | 🟢 근본 다름 |
| **능력 게이팅** | 없음 (모든 능력 즉시) | Stage-gated (predict/imagine/causal) | 🟢 근본 다름 |
| **뇌 구조** | 없음 | 9개 해부학적 영역 매핑 | 🟢 근본 다름 |
| **반성/통합** | LLM 기반 Reflection | LLM-free Memory Consolidation | 🟢 근본 다름 |
| **시냅스 가소성** | 없음 | Hebb's Law 기반 강화/약화 | 🟢 근본 다름 |
| **멀티모달** | 텍스트만 | 카메라/마이크/대화 | 🟢 근본 다름 |
| **수면 모드** | 없음 | 30분 주기 LLM-free 기억 정리 | 🟢 근본 다름 |
| **인과추론** | 없음 | Stage 4 게이팅 (causal_models) | 🟡 부분 다름 |
| **계획** | LLM hierarchical planning | 목표→전략 선택 (F5) | 🟡 부분 다름 |
| **사회적 상호작용** | 25개 에이전트 사회 시뮬레이션 | 1:1 양육자-아기 | 🟡 부분 다름 |
| **시각화** | Smallville 2D 맵 | 3D 해부학적 뇌 + Realtime | 🟡 부분 다름 |

**결론: 11 근본 다름 / 4 부분 다름 / 0 동일** → GA는 위협이 아닌 차별화 대상

### 10.2 핵심 포지셔닝 문장

> "Generative Agents show **what** agents do; we model **how** agents become."
> "GA agents are born fully capable—they do not develop. We ask: can we model how cognitive capabilities emerge?"

### 10.3 논문 intro 포함 문장 (안)

> Park et al. (2023) demonstrated that LLM-based agents can exhibit believable social behavior
> through memory streams and reflection. However, their architecture assumes adult-level
> cognition from initialization—agents do not develop, learn new capabilities over time, or
> exhibit the stage-gated emergence observed in human cognitive development. We address this
> gap by implementing developmental constraints inspired by neuroscience.

### 10.4 ICDL 리뷰어 예상 질문 + 방어

| 질문 | 위험도 | 방어 |
|------|--------|------|
| "GA + 감정 추가 아닌가?" | 5/5 | 목적/구조/메커니즘 모두 다름 (10.1 표) |
| "Stage gates 근거는?" | 5/5 | 신경발달학 문헌 (Piaget, Johnson) + C_nostage ablation |
| "감정이 downstream 안 됨" | 4/5 | F4 구현 필요 (v24) |
| "bare LLM보다 나은가?" | 5/5 | C_raw baseline 필수 |
| "GA reflection vs BB consolidation" | 4/5 | LLM-based vs LLM-free, 재현성 차이 |

---

## 11. 경쟁 논문 랜드스케이프 (2026-02-11)

### 11.1 Top 위협 논문

| 논문 | 저자/년도 | 위협도 | 겹침 | BabyBrain 차별점 |
|------|----------|--------|------|-----------------|
| **Generative Agents** | Park et al., UIST 2023 | 3/5 | 메모리+에이전트 | 발달 없음, 감정 없음, LLM 전의존 |
| **CoALA** | Sumers et al., COLM 2024 | 3/5 | 같은 기억 분류 (E/S/P) | 이론만, 구현 없음 |
| **Humanoid Agents** | Wang et al., arXiv 2023 | 2/5 | 감정+욕구 | 5 기본욕구 vs 우리 11감정+발달 |
| **Vygotskian AI** | Colas et al., Nature MI 2022 | 2/5 | 발달 AI 프레이밍 | 사회적 스캐폴딩 초점, 뇌구조 없음 |
| **Voyager** | Wang et al., NeurIPS 2023 | 1/5 | 자율 학습 | Minecraft 한정, 발달 없음 |
| **MemGPT** | Packer et al., NeurIPS 2023 | 1/5 | 기억 관리 | OS 메타포, 인지발달 무관 |

### 11.2 BabyBrain만의 고유 기여 (경쟁 논문에 없는 것)

1. **Stage-Gated Development**: 능력이 발달 단계별 해금 → 어떤 LLM 에이전트도 없음
2. **Emotion-Modulated Learning**: 감정이 학습 전략 선택에 영향 → Humanoid Agents는 행동만
3. **LLM-Free Consolidation**: 수면 모드 기억 통합 → 모든 경쟁자는 LLM 의존
4. **Brain-Mapped Visualization**: AI 인지를 해부학적 뇌로 매핑 → 완전히 새로운 접근
5. **Spreading Activation**: 그래프 기반 연상 전파 → GA의 weighted sum과 근본적으로 다름

### 11.3 "정적 페르소나" vs "발달적 페르소나" 패러다임

| 속성 | 정적 (GA/Humanoid) | 발달적 (BabyBrain) |
|------|--------------------|--------------------|
| 페르소나 | 부여(assignment) | 발생(emergence) |
| 메모리 | 텍스트 스트림 | 뉴런 네트워크 |
| 능력 | 고정 | 단계별 해금 |
| 감정 | 부수적/없음 | 핵심 메커니즘 |
| 시간 | 일정 반복 | 발달 진행 |
| 목표 | 사실적 행동 시뮬레이션 | 인지 발달 과정 시뮬레이션 |

---

## 12. 검증 전략 (2026-02-11)

### 12.1 ICDL 검증: 뇌과학 데이터 필요 여부

**결론: fMRI/EEG 검증 불필요. 행동/발달 데이터 비교로 충분.**

| 검증 방법 | ICDL 사용 빈도 | 추천 |
|-----------|---------------|------|
| 발달 궤적 비교 | 70% | ✅ 필수 |
| 발달 이정표 비교 | 60% | ✅ 필수 |
| 아키텍처 정당화 | 40% | ✅ 이미 완료 |
| 행동 오류 패턴 비교 | 50% | ⬜ 가능 |
| fMRI/EEG 비교 | <10% | ❌ 불필요 |

### 12.2 선례 논문 (신경 데이터 없이 발표)

- Elman (1990): SRN → U자 과잉일반화 곡선 = 아동 발달 매칭 (Cognitive Science)
- iCub 시리즈: 발달 로봇, 행동 시연만 (ICDL)
- BabyLM Challenge (2023-24): 언어 벤치마크 + milestone만 (CoNLL)
- Twomey & Westermann (2018): 영아 선호주시만 비교 (Developmental Science)

### 12.3 추천: Wordbank 비교 (가성비 최고)

- **Wordbank** (wordbank.stanford.edu): 크로스언어 어휘 발달 규준, 무료 API
- BabyBrain `semantic_concepts` 습득 곡선 vs Wordbank 어휘 성장 곡선
- 둘 다 sigmoid이면 → "발달적으로 타당한 학습 곡선" 주장 가능

### 12.4 3-Tier 검증 실행 계획

| Tier | 항목 | 노력 | 효과 |
|------|------|------|------|
| **TIER 1 (필수)** | Ablation 4가지 + 발달 문헌 15포인트 + 궤적 시각화 | 중 | reject 방지 |
| **TIER 2 (권장)** | Wordbank 비교 + CDI milestone 매핑 | 낮음 | 경쟁력 크게 향상 |
| **TIER 3 (불필요)** | fMRI/EEG 직접 비교 | 매우 높음 | 의미 없음 |

---

## 13. CDT (Cognitive Digital Twin) 프레이밍 (2026-02-11)

### 13.1 CDT 개념

- Digital Twin: 물리적 상태 복제
- **Cognitive** Digital Twin: 물리 + **인지 상태** (기억/추론/의사결정) 모델링
- 사례: SimBioSys (유방암 3D), Dassault Living Heart (심장 시뮬레이션)

### 13.2 BabyBrain as CDT

| CDT 요소 | BabyBrain 대응 |
|----------|---------------|
| 물리 상태 복제 | 9개 뇌영역 3D 시각화 |
| 인지 모델링 | 3중 기억 + spreading activation + 감정→목표 |
| 시뮬레이션 | "경험하면 뇌가 어떻게 변할까?" |
| **발달 추적** | 6단계 성장 (기존 CDT에 없는 기여) |

프레이밍: "Cognitive Digital Twin of Infant Brain Development"

### 13.3 학회별 적합도

| 학회 | CDT 프레이밍 | 필요 추가 작업 |
|------|------------|---------------|
| IEEE Digital Twin | ⭐⭐⭐ | CDT 논의 강화 |
| IEEE VIS | ⭐⭐⭐ | 시각화 focus |
| ISMAR | ⭐⭐ | Quest 3S AR 구현 필요 |
| CHI | ⭐⭐ | 사용자 연구 필요 |

---

## 14. ISMAR 2026 구체적 실행 플랜 (2026-02-11 확정)

> **마감: Abstract 3/9, Paper 3/16 | 장소: Bari, Italy, 10월 5-9일**
> **장비: Meta Quest 3S 보유 | 기술: WebXR (@react-three/xr)**

### 14.1 논문 정보

**제목**: "BrainXR: Mixed Reality Visualization of Real-Time Cognitive Development in LLM-Based Agents"

**초록 (Draft)**:
> Understanding the internal cognitive processes of AI systems remains a fundamental challenge.
> We present BrainXR, a mixed reality system that enables real-time observation of cognitive
> development in an LLM-based artificial agent through an anatomically-mapped 3D brain
> visualization. Our system maps 452+ semantic concepts across 9 brain regions and visualizes
> spreading activation waves, emotional states, and developmental stage progression in real-time
> using Meta Quest's passthrough AR. Through a within-subjects study (N=12-15) comparing
> 2D dashboard, 3D web, and AR conditions, we evaluate how immersive visualization modalities
> affect users' understanding of artificial cognitive processes. Results show that AR visualization
> significantly improves region identification accuracy and activation tracing while reducing
> cognitive load compared to 2D alternatives. Our work contributes the first mixed reality system
> for observing AI cognitive development, demonstrating the potential of spatial computing for
> explainable AI.

**RQ**: "How does mixed reality visualization of AI brain activity affect users' understanding of artificial cognitive processes compared to 2D and 3D desktop alternatives?"

**핵심 기여 3가지**:
1. **First MR system for AI cognitive visualization**: AI 인지 발달을 해부학적 뇌 구조로 매핑하고 AR로 시각화한 최초 시스템
2. **Real-time spreading activation in AR**: BFS 기반 활성화 전파를 passthrough AR에서 실시간 관찰
3. **Empirical evaluation of visualization modalities**: 2D vs 3D-web vs AR 3조건 비교 사용자 실험

**CFP 토픽 매칭**:
- 1순위: "Perception, Cognition, and Representation in AR/MR/VR"
- 2순위: "Applications of AR/MR/VR - Education and training"

### 14.2 선행 논문 Gap (핵심 novelty 근거)

기존 연구 영역들이 **개별적으로는 존재하지만 교차점이 없음**:

```
CDT (Cognitive Digital Twin) ← 100% 제조/건축 분야만
Brain Visualization in VR   ← 100% 해부학/의학만
Immersive Analytics          ← 데이터 시각화 (AI 인지 아님)
XAI Visualization            ← attention map/gradient (뇌 구조 아님)
```

**BabyBrain = 이 4개 분야의 교차점** → 선행 논문 0편 = 강력한 novelty

### 14.3 논문 구조 (9 pages + 2 refs)

```
1. Introduction (1p)
   - AI 블랙박스 문제 → XR이 해결 가능
   - 인지 발달 과정은 시공간적 → 3D/AR이 자연스러움
   - 기여 3가지 명시

2. Related Work (1.5p)
   2.1 Brain Visualization in VR/AR
       - 의학적 뇌 시각화 (수술, 교육)
       - 한계: 실제 뇌만, AI 인지 시각화 없음
   2.2 Explainable AI Visualization
       - Attention maps, activation visualization
       - 한계: 2D, 정적, 뇌 구조 매핑 없음
   2.3 Immersive Analytics
       - STREAM, RagRug, 시공간 데이터 VR
       - 한계: 일반 데이터, AI 특화 아님
   2.4 Cognitive Digital Twin
       - 제조/건축 CDT
       - 한계: 산업 분야만, 인지 발달 CDT 없음

3. System Design (2.5p)
   3.1 Underlying Cognitive Architecture (brief, cite ICDL paper)
       - 개념 네트워크 G=(V,E,W), 9 brain regions
       - 발달 단계, 감정 시스템 (요약만)
   3.2 Visualization Design
       - Design rationale: 왜 해부학적 뇌 매핑인가
       - 3가지 뷰 모드: 2D Dashboard / 3D Web / AR
       - 시각 인코딩: 색상(영역), 크기(활성도), 발광(실시간), 파동(전파)
   3.3 AR-Specific Features
       - Passthrough AR: 실제 환경에 뇌 오버레이
       - Hand tracking: 손으로 뇌영역 선택/회전
       - Plane detection: 테이블 위 자동 배치
       - Spatial anchoring: 위치 고정
   3.4 Real-time Pipeline
       - 음성→LLM→뉴런활성화→WebSocket→AR 렌더링 (1-3초)
   3.5 Implementation
       - React Three Fiber + @react-three/xr
       - Supabase Realtime (WebSocket)
       - Quest 3S (WebXR, 설치 불필요)

4. Evaluation (2p)
   4.1 Study Design
       - Within-subjects, 3 conditions (2D / 3D-Web / AR)
       - N=12-15, counterbalanced
       - 4 tasks (아래 상세)
   4.2 Tasks
       T1: Region Identification ("가장 활성화된 영역은?")
       T2: Activation Tracing ("사과→빨간색 전파 경로 추적")
       T3: Development Assessment ("현재 발달 단계와 다음 단계 예측")
       T4: Emotion-Brain Mapping ("현재 감정이 어떤 영역에 영향?")
   4.3 Metrics
       - Task Completion Accuracy (%)
       - Task Completion Time (s)
       - NASA-TLX (cognitive load)
       - SUS (usability)
       - 주관적 선호도 (7-point Likert)
   4.4 Results
       - 표 + 그래프 (조건별 비교)
       - 통계: Friedman test + post-hoc Wilcoxon
   4.5 Qualitative Findings
       - 참가자 인터뷰 주요 인사이트

5. Discussion (0.5p)
   - AR이 region identification에서 우위인 이유
   - 3D 공간 인지의 장점
   - 한계: 참가자 수, Quest 해상도, 학습 효과

6. Conclusion (0.5p)
   - 요약 + 향후: 다중 에이전트 AR, 교육 응용
```

### 14.4 Figure 목록 (6-7개)

| Fig | 내용 | 소스 |
|-----|------|------|
| 1 | System Architecture (파이프라인) | 다이어그램 새로 제작 |
| 2 | 3가지 시각화 모드 비교 (2D/3D/AR 스크린샷) | 실제 캡처 |
| 3 | AR에서 뇌 시각화 (Quest passthrough 캡처) | Quest 녹화 |
| 4 | Spreading Activation 파동 시퀀스 (t=0,1,2) | 실제 캡처 |
| 5 | Hand interaction (뇌영역 선택, 회전) | Quest 녹화 |
| 6 | Task accuracy/time 비교 차트 | 실험 결과 |
| 7 | NASA-TLX 비교 + 선호도 | 실험 결과 |

### 14.5 기술 구현 계획

**핵심: 기존 코드 85% 재사용, @react-three/xr 래핑**

| 작업 | 파일 | 난이도 | 시간 |
|------|------|--------|------|
| @react-three/xr 설치 + XR Store | package.json, brain/xr/page.tsx | 낮음 | 2h |
| RealisticBrain XR 래핑 | RealisticBrainXR.tsx | 낮음 | 3h |
| OrbitControls 제거 + XR 카메라 | brain/xr/page.tsx | 낮음 | 1h |
| InstancedMesh 최적화 (뉴런) | RegionNeurons.tsx | 중간 | 4h |
| Geometry 세그먼트 감소 | BrainShell, BrainRegionMesh | 낮음 | 2h |
| Hand tracking + 터치 | HandInteraction.tsx | 중간 | 4h |
| Plane detection + 배치 | BrainPlacement.tsx | 중간 | 3h |
| XRDomOverlay (ThoughtProcess) | ThoughtProcessXR.tsx | 중간 | 3h |
| Quest 실기기 테스트 + 디버깅 | - | 중간 | 6h |
| **합계** | | | **~28h** |

### 14.6 사용자 실험 계획

**참가자**: 12-15명 (연구실 동료, HCI 대학원생)
**시간**: 1인당 45-60분
**보상**: 간식/음료

**실험 프로토콜**:
1. 동의서 + 인구통계 설문 (5분)
2. 시스템 소개 + 연습 (10분)
3. 조건 1: Task T1-T4 수행 (10분)
4. NASA-TLX + SUS 작성 (5분)
5. 조건 2: Task T1-T4 수행 (10분)
6. NASA-TLX + SUS 작성 (5분)
7. 조건 3: Task T1-T4 수행 (10분)
8. NASA-TLX + SUS + 선호도 + 인터뷰 (10분)

**Counterbalancing**: Latin square (6 order × 2-3 참가자)

### 14.7 주간 일정 (D-33)

```
Week 1: 2/11-2/16 (이번 주) — 플랜 + 프로토타입 + 협업자 설명
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
2/11 (화): ISMAR 플랜 확정 ✅ + @react-three/xr 설치
2/12 (수): RealisticBrainXR 기본 래핑 + Quest 테스트
2/13 (목): InstancedMesh 최적화 + 72fps 달성
2/14 (금): Hand tracking + plane detection
2/15 (토): 협업자 설명 문서 작성 + 미팅 준비
2/16 (일): 협업자 미팅 & 설명

Week 2: 2/17-2/23 — AR 인터랙션 완성 + ICDL 병행
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
2/17-18: XRDomOverlay + ThoughtProcess AR
2/19-20: 실시간 파이프라인 테스트 (음성→뇌→AR)
2/21-22: 2D dashboard 비교 뷰 구현 (실험용)
2/23: AR 프로토타입 완성 + 비디오 초안 촬영

Week 3: 2/24-3/2 — 사용자 실험 + 논문 작성 시작
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
2/24-25: IRB/동의서 준비 + 참가자 모집
2/26-28: 사용자 실험 진행 (12-15명)
3/1-2: 데이터 분석 + 통계 (Friedman test)

Week 4: 3/3-3/9 — Abstract 제출 + 논문 초안
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
3/3-5: Introduction + Related Work + System Design 작성
3/6-7: Evaluation + Results 작성
3/8: Abstract 최종 확인 + Figure 정리
3/9: ★ ISMAR Abstract 제출 ★

Week 5: 3/10-3/16 — 최종 제출
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
3/10-12: Discussion + Conclusion + 전체 교정
3/13: ★ ICDL Full Paper 제출 ★ (병행)
3/14-15: ISMAR 최종 수정 + 비디오 편집
3/16: ★ ISMAR Full Paper 제출 ★
```

### 14.8 협업자 전달 사항 (이번 주)

**협업자에게 설명할 핵심 포인트:**

1. **BabyBrain이 뭔가**: "LLM 기반 아기 AI의 뇌를 3D로 시각화하는 시스템"
2. **ISMAR에 왜 적합한가**: "Quest 3S로 AI의 뇌를 AR로 관찰 → XAI + AR 교차"
3. **선행 연구 Gap**: "AI 인지를 AR로 시각화한 논문이 0편"
4. **기술적 가능성**: "기존 코드 85% 재사용, WebXR로 2-3주 구현"
5. **실험 계획**: "2D vs 3D vs AR 비교, 12-15명"
6. **마감**: "Abstract 3/9, Paper 3/16"
7. **역할 분담**: (아래 표)

**역할 분담 (안)**:

| 역할 | 담당 | 작업 |
|------|------|------|
| Lead / 1st Author | 본인 | 시스템 설계, AR 구현, 논문 집필 |
| 공동 연구자 | 협업자 | 사용자 실험 설계/진행, 데이터 분석, Related Work |
| (선택) | 지도교수 | 교신저자, 논문 검토 |

### 14.9 "왜 LLM을 빼야 하나?" 대한 협업자 설명 요약

> LLM을 빼는 게 아닙니다. **어디에 쓰고 어디에 안 쓰는지**가 논문의 기여입니다.
>
> - LLM = 감각기관 (언어 이해, 개념 추출)
> - 자체 알고리즘 = 뇌 내부 (기억 통합, 시냅스 강화, 발달 전이)
> - 실제 뇌도 이렇게 작동 (수면 중 기억 통합에 외부 입력 없음)
> - 이것이 Generative Agents와의 결정적 차이

---

## 변경 이력

| 날짜 | 변경 |
|------|------|
| 2026-02-11 | Section 14 추가: ISMAR 2026 구체적 실행 플랜 (제목/구조/실험/일정) |
| 2026-02-11 | Section 10-13 추가 (GA 비교, 경쟁 랜드스케이프, 검증 전략, CDT 프레이밍) |
| 2026-02-10 | 6-Agent Deep Review 결과 추가 (Section 9) |
| 2026-02-10 | 초안 작성 |
