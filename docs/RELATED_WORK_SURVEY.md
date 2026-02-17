# Post-Generative Agents Research Survey & BabyBrain Positioning

**Date**: 2026-02-11
**Purpose**: Generative Agents (Park et al., 2023) 이후 "LLM + Memory/Cognitive Architecture" 연구 landscape 조사 및 BabyBrain 포지셔닝

---

## CAVEAT: 검증 필요 사항

> 이 조사는 Claude의 학습 데이터(~2025.05)를 기반으로 합니다. 2025년 하반기~2026년 초 논문은 누락 가능성이 있습니다.
> **아래 웹 검색을 반드시 수행하세요** (Section 8 참조).

---

## 1. Generative Agents 직접 후속/확장 연구

### 1.1 Generative Agents (Park et al., 2023) - 기준점

| 항목 | 내용 |
|------|------|
| 학회 | UIST 2023 (Best Paper) |
| 핵심 | 25개 LLM 에이전트의 believable social simulation |
| Memory | Memory stream (자연어 기록) + Retrieval (recency/importance/relevance) |
| Reflection | 기억을 종합하여 higher-level insight 생성 |
| Planning | 일일 계획 + 이벤트 반응 |

### 1.2 GA 직접 확장 연구

| 논문 | 년도/학회 | 핵심 기여 | GA 대비 확장점 |
|------|----------|----------|---------------|
| **Humanoid Agents** (Wang et al.) | 2023 / arXiv | 기본 욕구(배고픔, 에너지, 사교, 재미, 위생) 모델링 | 감정/욕구가 행동에 영향 |
| **AgentSims** (Lin et al.) | 2023 / arXiv | 경제 활동이 포함된 sandbox | 사회경제 시뮬레이션 |
| **CAMEL** (Li et al.) | 2023 / NeurIPS | 역할 기반 2인 에이전트 대화 | 커뮤니케이션 프로토콜 |
| **MetaGPT** (Hong et al.) | 2023 / ICLR 2024 | SOP 기반 다중 에이전트 SW 개발 | 구조화된 협업 |
| **AgentVerse** (Chen et al.) | 2023 / arXiv | 다중 에이전트 협업 프레임워크 | 에이전트 조합 최적화 |
| **RAISE** (Shao et al.) | 2023 / arXiv | Retrieval-Augmented 에이전트 시뮬레이션 | 검색 강화 기억 |

---

## 2. "LLM + Cognitive Architecture" 주요 연구 (2023-2025)

### 2.1 CoALA: Cognitive Architectures for Language Agents

| 항목 | 내용 |
|------|------|
| 저자 | Sumers, Yao, Narasimhan, Griffiths |
| 학회 | COLM 2024 (arXiv: 2309.02427, 2023) |
| 핵심 기여 | LLM 에이전트를 인지 아키텍처 관점에서 체계적으로 분류하는 프레임워크 |

**CoALA 핵심 구조:**
- **Memory**: Working memory, Episodic memory, Semantic memory, Procedural memory
- **Decision Making**: Reasoning, Planning, Learning
- **Action Spaces**: Internal (retrieval, reasoning) vs External (tools, communication)
- 기존 시스템(ReAct, Reflexion, Voyager, GA)을 이 프레임워크로 매핑

**BabyBrain과의 관계:**
| 비교 항목 | CoALA | BabyBrain |
|----------|-------|-----------|
| 성격 | 이론적 프레임워크/분류 체계 | 작동하는 구현 시스템 |
| Memory 분류 | Episodic/Semantic/Procedural (이론) | Episodic/Semantic/Procedural (구현) |
| 발달 단계 | 없음 | 5단계 capability gating |
| 감정 | 없음 | 6기본+5복합, VA 공간 |
| 뇌 매핑 | 없음 | 9영역 해부학적 매핑 |
| 학습 메커니즘 | 분류만 제시 | LLM-free 내부 알고리즘 구현 |

### 2.2 MemGPT / Letta

| 항목 | 내용 |
|------|------|
| 저자 | Packer, Wooders, Lin, Fang, Sahil, Lim |
| 학회 | ICLR 2024 (arXiv: 2310.08560, 2023) |
| 핵심 기여 | OS 영감 메모리 관리로 LLM 컨텍스트 윈도우 한계 극복 |

**MemGPT 구조:**
- Main context (working memory) + Recall storage + Archival storage
- LLM이 스스로 memory page-in/page-out 결정
- 무한 대화 지속 가능

**BabyBrain과의 관계:**
| 비교 항목 | MemGPT | BabyBrain |
|----------|--------|-----------|
| 설계 영감 | OS 가상 메모리 | 뇌과학 (해마/피질) |
| Memory 계층 | Main/Recall/Archival | Episodic/Semantic/Procedural + Consolidation |
| 통합 메커니즘 | LLM이 관리 | LLM-free 수면 모드 통합 |
| 감정 | 없음 | 감정 기반 기억 강화 |
| 발달 | 없음 | 5단계 |
| 강점 | 컨텍스트 윈도우 극복 실증 | 생물학적 영감 메커니즘 |

### 2.3 Voyager

| 항목 | 내용 |
|------|------|
| 저자 | Wang, Xian, Xie, et al. (NVIDIA) |
| 학회 | NeurIPS 2023 |
| 핵심 기여 | Minecraft에서 open-ended 학습하는 LLM 에이전트 |

**Voyager 구조:**
- **Skill Library**: 코드로 저장된 재사용 가능 기술 (절차적 기억과 유사)
- **Automatic Curriculum**: 점진적 난이도 (발달과 유사)
- **Iterative Prompting**: 실행 → 피드백 → 수정 반복

**BabyBrain과의 관계:**
| 비교 항목 | Voyager | BabyBrain |
|----------|---------|-----------|
| 점진적 학습 | Automatic curriculum (과제 난이도) | Stage gates (인지 능력 해금) |
| 기억 | Skill library (코드) | 3중 기억 (뇌과학 기반) |
| 감정 | 없음 | 6+5 감정, 전략 선택 |
| 환경 | Minecraft (명확한 성공 기준) | 대화 (평가 어려움) |
| 평가 | 기술 수, 맵 탐색량 등 정량적 | 개념 획득률, 예측 정확도 (미실행) |

### 2.4 Reflexion

| 항목 | 내용 |
|------|------|
| 저자 | Shinn, Cassano, Labash, et al. |
| 학회 | NeurIPS 2023 |
| 핵심 기여 | 언어적 자기 반성으로 에이전트 성능 향상 |

**Reflexion 구조:**
- 태스크 실패 → 자연어 반성문 생성 → 다음 시도에 활용
- "Verbal reinforcement learning"
- 에피소드 메모리에 반성 저장

**BabyBrain과의 관계:**
| 비교 항목 | Reflexion | BabyBrain |
|----------|-----------|-----------|
| 자기 반성 | 태스크 실패 기반 (LLM 생성) | 메타인지 Phase 7 (통계 기반, LLM-free) |
| 학습 | 반성문 재사용 | 시냅스 가소성, 전략 효과성 |
| 범위 | 특정 태스크 해결 | 범용 인지 발달 |
| 감정 | 없음 | 감정 조절 학습 |

### 2.5 LATS (Language Agent Tree Search)

| 항목 | 내용 |
|------|------|
| 저자 | Zhou, Pujara, Ren, et al. |
| 학회 | NeurIPS 2023 |
| 핵심 기여 | MCTS + LLM 에이전트 통합 |

- 탐색/계획 최적화 프레임워크
- BabyBrain과 초점이 크게 다름 (계획 최적화 vs 인지 발달)
- 겹치는 부분이 적어 직접 위협 낮음

### 2.6 추가 주목 연구

| 논문 | 년도 | 핵심 | BabyBrain 관련성 |
|------|------|------|-----------------|
| **RecurrentGPT** (Zhou et al.) | 2023 | 순환 생성 + 장기 기억 | 기억 관리 측면 유사 |
| **GITM** (Zhu et al.) | 2023 | Minecraft LLM + 구조화 지식 | 지식 그래프 사용 유사 |
| **AutoGen** (Wu et al., MS) | 2023 | 다중 에이전트 대화 프레임워크 | 엔지니어링 초점, 관련성 낮음 |
| **Self-RAG** (Asai et al.) | 2023 | 자기 반성적 RAG | 자기 평가 측면 유사 |
| **EmotionPrompt** (Li et al.) | 2023 | 감정 자극이 LLM 성능 향상 | 감정 사용하지만 아키텍처 아님 |
| **ADAS** (Hu et al.) | 2024 | 에이전트 시스템 자동 설계 | 메타 수준, 직접 비교 어려움 |

---

## 3. "발달적 AI" + LLM 조합 연구

### 3.1 Pre-LLM 발달 AI (BabyBrain의 이론적 선조)

| 시스템 | 년도 | 핵심 특징 | LLM 사용 |
|--------|------|----------|----------|
| **BabyAI** (MILA) | 2019 | Grid world, 교육과정 학습, 지시 따르기 | 없음 (RL) |
| **Developmental Robotics** | 2015~ | 물리적 embodiment에서 인지 발달 | 없음 |
| **OpenCog** | 2014 | AGI 프레임워크, 발달적 측면 | 없음 (자체 추론) |
| **CLARION** (Sun) | 2003 | 인지 아키텍처, 암묵/명시 학습 | 없음 |
| **ACT-R** (Anderson) | 1993~ | Production rule 기반 인지 모델 | 없음 |
| **SOAR** (Laird) | 1987~ | Goal-driven 인지 아키텍처 | 없음 |

### 3.2 핵심 질문: "발달 단계를 가진 LLM 에이전트가 있는가?"

**내 조사 결과 (2025.05 학습 데이터 기준): 없다.**

- Voyager의 automatic curriculum은 "과제 난이도 증가"이지, "인지 능력 해금"이 아님
- BabyAI는 LLM을 사용하지 않음
- GA, MemGPT, Reflexion 등은 모두 "flat" 아키텍처 (처음부터 모든 능력 사용 가능)
- CoALA 프레임워크에서도 "developmental" 차원은 명시적으로 다루지 않음

**이것이 BabyBrain의 가장 강력한 novelty claim이다.**

### 3.3 감정 시스템을 가진 LLM 에이전트

| 시스템 | 감정 모델 | 학습 영향 | BabyBrain 대비 |
|--------|----------|----------|---------------|
| **Humanoid Agents** | 5가지 기본 욕구 (배고픔 등) | 행동 선택에 영향 | 훨씬 단순, Russell's Circumplex 없음 |
| **EmotionPrompt** | 감정적 프롬프트 자극 | 프롬프트만 변경 | 아키텍처가 아닌 프롬프트 기법 |
| **Affective Computing** 전통 | 감정 인식 중심 | 인식만, 생성/조절 없음 | 방향 자체가 다름 |
| **BabyBrain** | 6기본+5복합, VA 공간, 감쇠 모델 | 전략 선택, 학습률, 탐색률 | -- |

**BabyBrain의 감정 시스템은 현저히 정교하다.** Russell's Circumplex Model을 사용하고, 감정이 학습 전략 선택(5가지), 학습률 조절, 탐색률 조절에 직접 영향을 미치는 시스템은 LLM 에이전트 문헌에서 확인되지 않았다.

### 3.4 뇌 구조를 모방한 LLM 에이전트

**조사 결과: 없다 (LLM 에이전트 영역에서).**

- Neuromorphic computing (Intel Loihi, IBM TrueNorth) → 하드웨어 수준, LLM과 무관
- Brain-Computer Interface 연구 → 다른 분야
- CoALA가 cognitive architecture를 다루지만 anatomical mapping은 없음
- **BabyBrain의 9영역 해부학적 뇌 매핑 + spreading activation 시각화는 독자적**

---

## 4. 연구 비교 종합 테이블

| 논문 | 년도/학회 | Memory 유형 | 발달 단계 | 감정 | 뇌 매핑 | LLM-free 학습 | 평가 수준 |
|------|----------|------------|----------|------|---------|-------------|----------|
| **Generative Agents** | 2023/UIST | Stream+Retrieval+Reflection | 없음 | 없음 | 없음 | 없음 | Human eval (believability) |
| **CoALA** | 2024/COLM | Epi/Sem/Proc (분류) | 없음 | 없음 | 없음 | 분류만 | 프레임워크 (실험 없음) |
| **MemGPT** | 2024/ICLR | Main/Recall/Archival | 없음 | 없음 | 없음 | 없음 | 대화 지속성, QA 정확도 |
| **Voyager** | 2023/NeurIPS | Skill library | Curriculum (과제) | 없음 | 없음 | 없음 | 기술 수, 맵 탐색, 아이템 |
| **Reflexion** | 2023/NeurIPS | 반성문 에피소드 | 없음 | 없음 | 없음 | 없음 | HumanEval, AlfWorld 등 |
| **Humanoid Agents** | 2023/arXiv | GA + 욕구 시스템 | 없음 | 5가지 욕구 | 없음 | 없음 | 사회 시뮬레이션 |
| **LATS** | 2023/NeurIPS | MCTS rollout 기억 | 없음 | 없음 | 없음 | 없음 | HumanEval, WebShop 등 |
| **BabyAI** | 2019/ICLR | RL state | Curriculum (고정) | 없음 | 없음 | RL 기반 | Grid world 성공률 |
| **BabyBrain** | 2026 (준비중) | Epi/Sem/Proc (구현) | 5단계 gate | 6+5종, VA | 9영역 | 수면 통합 등 | **Ablation 미실행** |

---

## 5. BabyBrain 위협 분석 (TOP 3)

### Threat #1: CoALA (위협도: HIGH)

**왜 위협적인가:**
- BabyBrain이 사용하는 Memory 분류 체계(Episodic/Semantic/Procedural)를 이미 프레임워크로 제시
- 인지과학에서 LLM 에이전트로의 매핑을 학술적으로 체계화
- COLM이라는 좋은 학회에 게재

**BabyBrain이 우위인 부분:**
- CoALA는 분류 체계이고, BabyBrain은 **작동하는 구현체**
- CoALA에는 발달 단계, 감정, 뇌 매핑이 전혀 없음
- BabyBrain은 CoALA 프레임워크에 **발달적 차원을 추가**한 것으로 포지셔닝 가능

**BabyBrain이 열위인 부분:**
- CoALA의 이론적 엄밀성, 기존 시스템 매핑의 포괄성
- CoALA는 수십 개의 기존 시스템을 비교 분석, BabyBrain은 자체 시스템만
- 학술적 인용이 이미 많음

**대응 전략:** "CoALA 프레임워크를 developmental dimension으로 확장한 구현"으로 포지셔닝. CoALA를 적으로 만들지 말고 foundation으로 활용.

---

### Threat #2: Humanoid Agents (위협도: MEDIUM-HIGH)

**왜 위협적인가:**
- GA에 "인간적 욕구/감정"을 추가한 최초 연구
- BabyBrain의 감정 시스템과 개념적으로 유사한 접근

**BabyBrain이 우위인 부분:**
- Humanoid Agents의 욕구 모델 (5가지)은 매우 단순 (hunger, energy 등)
- BabyBrain의 감정은 **Russell's Circumplex** 기반으로 이론적 근거가 강함
- BabyBrain은 감정 → 전략 선택 → 학습률 조절의 **cascading effect**가 있음
- Humanoid Agents에는 발달 단계가 없음

**BabyBrain이 열위인 부분:**
- Humanoid Agents는 다중 에이전트 사회적 시뮬레이션에서 평가
- BabyBrain은 단일 에이전트 대화 시스템
- Humanoid Agents는 이미 발표됨, BabyBrain은 준비 중

**대응 전략:** "Humanoid Agents가 basic needs를 도입했다면, BabyBrain은 formal emotion model로 확장하고 학습 전략에 연결"로 포지셔닝.

---

### Threat #3: Voyager (위협도: MEDIUM)

**왜 위협적인가:**
- NeurIPS에 게재된 고인용 논문
- "Open-ended learning"과 "progressive skill acquisition"이 발달과 표면적으로 유사
- Skill library가 절차적 기억과 유사

**BabyBrain이 우위인 부분:**
- Voyager의 curriculum은 과제 난이도이지, 인지 능력 해금이 아님
- Voyager에는 감정, 수면 통합, 뇌 매핑 없음
- BabyBrain의 발달은 생물학적으로 동기부여됨 (Piaget 이론)

**BabyBrain이 열위인 부분:**
- Voyager의 평가는 정량적이고 명확 (기술 수, 마인크래프트 진행도)
- BabyBrain의 평가는 아직 설계 단계
- Voyager는 NeurIPS, 높은 인용

**대응 전략:** Voyager를 "task-level curriculum"으로, BabyBrain을 "cognitive-level development"로 구분. 상호보완적으로 프레이밍.

---

## 6. BabyBrain의 독자적 기여 (Novelty Claims)

조사 결과, 아래 기여는 기존 문헌에서 확인되지 않은 BabyBrain 고유의 것이다:

### Claim 1: Stage-Gated Developmental Architecture for LLM Agents (강도: STRONG)

**어떤 기존 연구도 LLM 에이전트에 명시적 발달 단계 게이팅을 적용하지 않았다.**

- BabyAI → LLM 미사용
- Voyager → task curriculum, capability gating 아님
- GA/MemGPT/Reflexion → flat architecture
- CoALA → development 차원 미포함

이것은 BabyBrain의 **가장 강력한 novelty claim**이다.

### Claim 2: Emotion-Modulated Learning Strategy Selection (강도: STRONG)

**Russell's Circumplex Model 기반 감정이 학습 전략을 선택하는 시스템은 없다.**

- Humanoid Agents → 단순 욕구, 전략 선택 없음
- EmotionPrompt → 프롬프트 기법, 아키텍처 아님
- 전통 Affective Computing → 인식 중심, 에이전트 학습 조절 아님

### Claim 3: LLM-Free Memory Consolidation (강도: MEDIUM-STRONG)

**수면 유사 과정에서 LLM 없이 기억 통합을 수행하는 시스템은 없다.**

- MemGPT → LLM이 메모리 관리
- GA → LLM이 reflection 생성
- Reflexion → LLM이 반성문 생성
- 모든 주요 시스템이 메모리 관리에 LLM 사용

**주의**: 이 claim의 강도는 "LLM-free가 왜 중요한가"를 생물학적으로 정당화해야 유지됨.

### Claim 4: Anatomical Brain Region Mapping + Spreading Activation Visualization (강도: STRONG, VIS 논문용)

**LLM 에이전트의 인지 과정을 해부학적 뇌 영역에 매핑하고 시각화한 시스템은 없다.**

- 기존 뇌 시각화 → fMRI 실제 데이터
- 기존 AI 시각화 → attention map, activation map (neural network 내부)
- BabyBrain → 인공 인지 과정을 해부학적 뇌 구조에 매핑

---

## 7. BabyBrain이 채우는 연구 빈자리 (Gap)

### 7.1 Landscape Map

```
                        이론적 ◄────────────────► 구현
                           │                        │
인지과학 프레이밍 ────── CoALA                   BabyBrain ◄── ★ 여기
                           │                        │
태스크 중심 ──────────── Reflexion/LATS          Voyager
                           │                        │
사회 시뮬레이션 ────── Gen. Agents            Humanoid Agents
                           │                        │
메모리 관리 ──────────── (이론)                 MemGPT/Letta
                           │                        │
발달적 AI ──────────── Piaget/Vygotsky이론     BabyAI(pre-LLM)
+ LLM                     │                        │
                           └───── BabyBrain ────────┘ ◄── ★ 유일한 교차점
```

### 7.2 BabyBrain의 빈 자리

**"LLM 위에 생물학적으로 영감받은 발달적 인지 메커니즘을 구현한 시스템"**

이 교차점을 차지하는 연구가 없다:
- 인지 아키텍처 (CoALA) + 발달 심리학 (Piaget) + 정서 심리학 (Russell) + 뇌과학 (spreading activation) + LLM 에이전트

### 7.3 BabyBrain 포지셔닝 한 문장

> "While CoALA (2024) provides a theoretical framework for cognitive architectures in language agents, and Voyager (2023) demonstrates progressive capability acquisition, no existing work combines explicit developmental stage-gating, emotion-modulated learning strategy selection, LLM-independent memory consolidation, and anatomically-mapped brain visualization. BabyBrain occupies this uncharted intersection."

---

## 8. 정직한 약점 분석

### 8.1 평가 부재 (CRITICAL)

| 기존 연구 | 평가 방법 | BabyBrain 현재 |
|----------|----------|---------------|
| GA | 인간 평가 (believability) | 없음 |
| Voyager | 정량적 (기술수, 진행도) | 없음 |
| Reflexion | 벤치마크 (HumanEval 등) | 없음 |
| MemGPT | 대화 지속성, QA 정확도 | 없음 |
| BabyBrain | Ablation 설계됨 | **미실행** |

**이것이 가장 큰 약점이다.** 452개 개념, 583개 경험은 descriptive statistics이지 experimental evidence가 아니다.

### 8.2 C_raw 베이스라인 부재 (CRITICAL)

리뷰어의 1순위 질문: "BabyBrain의 행동이 그냥 Gemini의 능력이 아닌가?"
→ 순수 LLM 대비 BabyBrain의 부가가치를 정량적으로 증명해야 함

### 8.3 일반화 한계

- 한국어 단일 사용자 대화 시스템
- Supabase + 특정 API에 의존
- 다른 LLM(GPT, Claude)으로 대체 시 동일 결과 보장 불가

### 8.4 이론적 엄밀성

- CoALA는 인지과학 문헌을 체계적으로 매핑
- BabyBrain의 "생물학적 영감"은 informal (수식은 있지만 formal model 부족)
- 특히 F2(Spreading Activation) 코드/논문 불일치 문제 (PAPER_PLAN.md 참조)

### 8.5 재현성

- Edge Function + Supabase 아키텍처 → 다른 연구자가 재현하기 어려움
- 오픈소스 여부?

---

## 9. 반드시 수행해야 할 웹 검색 (CRITICAL)

내 학습 데이터는 ~2025.05까지이므로, 아래 검색을 반드시 수행하여 최신 연구 누락이 없는지 확인해야 합니다.

### 9.1 최우선 검색 (novelty 위협)

| # | 검색어 | 목적 |
|---|--------|------|
| 1 | `"developmental LLM agent" OR "developmental cognitive architecture LLM" 2025 2026` | **BabyBrain의 핵심 novelty가 선점되었는지** |
| 2 | `"emotion modulated LLM agent" OR "affective LLM agent architecture" 2024 2025 2026` | 감정 시스템 novelty 확인 |
| 3 | `"brain-inspired LLM agent" OR "neuromorphic LLM agent" 2024 2025 2026` | 뇌 매핑 novelty 확인 |
| 4 | `"stage-gated" OR "capability gating" LLM agent 2024 2025` | 단계별 능력 해금 선행 연구 |

### 9.2 학회별 검색

| # | 검색어 | 목적 |
|---|--------|------|
| 5 | `ICDL 2024 2025 proceedings "language model"` | 타겟 학회 최근 동향 |
| 6 | `IEEE VIS 2024 2025 "AI visualization" OR "brain visualization"` | VIS 논문 타겟 확인 |
| 7 | `COLM 2024 2025 cognitive architecture` | CoALA 후속 연구 |

### 9.3 특정 시스템 최신 상태

| # | 검색어 | 목적 |
|---|--------|------|
| 8 | `Letta MemGPT 2025 2026 latest` | MemGPT 진화 상태 |
| 9 | `AgentSociety 2025 paper` | 이 연구의 실체 확인 |
| 10 | `"cognitive architecture" "language agent" survey 2025` | 종합 서베이 논문 확인 |

---

## 10. ICDL 논문 Related Work 섹션 구조 제안

```
2. Related Work

2.1 Classical and Modern Cognitive Architectures
    - ACT-R (Anderson, 2007), SOAR (Laird, 2012): 규칙 기반 인지 모델
    - CoALA (Sumers et al., 2024): LLM 에이전트용 인지 아키텍처 프레임워크
    → "CoALA provides a taxonomy; we provide an implementation with developmental dimension"

2.2 Memory Systems in LLM Agents
    - Generative Agents (Park et al., 2023): memory stream + retrieval + reflection
    - MemGPT (Packer et al., 2024): OS-inspired hierarchical memory
    - Voyager (Wang et al., 2023): skill library as procedural memory
    - Reflexion (Shinn et al., 2023): episodic reflection memory
    → "Existing systems use LLM for memory management; we use biologically-inspired
       LLM-free consolidation"

2.3 Developmental AI and Curriculum Learning
    - BabyAI (Chevalier-Boisvert et al., 2019): grid world curriculum
    - Developmental Robotics (Cangelosi & Schlesinger, 2015): embodied development
    - Voyager's automatic curriculum (Wang et al., 2023)
    → "No existing work applies developmental stage-gating to LLM agent capabilities"

2.4 Affective Computing in AI Agents
    - Humanoid Agents (Wang et al., 2023): basic needs model
    - EmotionPrompt (Li et al., 2023): emotional stimuli for LLMs
    - Russell's Circumplex Model (1980): theoretical foundation
    → "We go beyond basic needs to formal emotion-strategy mapping"
```

---

## 11. 결론 및 권고

### 11.1 BabyBrain의 연구 landscape 내 위치

BabyBrain은 다음 연구 흐름의 **교차점**에 위치한다:
1. LLM 에이전트 인지 아키텍처 (CoALA 흐름)
2. 발달 AI (BabyAI, developmental robotics 흐름)
3. Affective computing (감정 + AI 흐름)
4. 뇌 영감 컴퓨팅 (neuromorphic 흐름)

이 교차점은 현재 **비어 있다** (2025.05 기준).

### 11.2 가장 강한 Novelty Claims (순서대로)

1. **Stage-gated developmental architecture** for LLM agents (가장 강력)
2. **Emotion → learning strategy** cascading mechanism (강력)
3. **LLM-free memory consolidation** inspired by sleep neuroscience (중간-강)
4. **Anatomical brain mapping + spreading activation visualization** (VIS 논문용, 강력)

### 11.3 가장 시급한 실행 과제

| 우선순위 | 과제 | 이유 |
|---------|------|------|
| 1 | **C_raw 베이스라인 실험** | 모든 novelty claim의 전제 조건 |
| 2 | **5조건 Ablation 실행** | 논문 submission의 필수 조건 |
| 3 | **웹 검색으로 최신 연구 확인** (Section 9) | Novelty 선점 여부 반드시 확인 |
| 4 | **F2 수식/코드 일치** | 리뷰어가 발견하면 reject 사유 |
| 5 | **Related Work 30편 확보** | ICDL 제출 기본 요건 |

### 11.4 전략적 권고

- **CoALA를 적이 아닌 foundation으로** 사용할 것. "CoALA framework + developmental extension"
- **Humanoid Agents와 직접 비교** 하여 감정 시스템의 정교함을 부각할 것
- **Voyager와 차별화**: task curriculum vs cognitive development
- **BabyAI와 연결**: pre-LLM developmental AI의 LLM 시대 계승자로 프레이밍
- **"10개 구성요소 중 9개가 LLM-independent"** 방어선 유지 (PAPER_PLAN.md 9.5)

---

## 변경 이력

| 날짜 | 변경 |
|------|------|
| 2026-02-11 | 초안 작성 (학습 데이터 ~2025.05 기반, 웹 검색 미수행) |
