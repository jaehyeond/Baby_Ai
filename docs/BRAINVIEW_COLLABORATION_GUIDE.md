# BrainView ISMAR 2026 - 시스템 현황 및 협업 가이드

**작성일**: 2026-02-25
**목적**: 논문 초안 작성자에게 실제 Baby AI 시스템의 현황을 전달하고, 논문 각 섹션과 실제 구현을 정확히 매핑하기 위한 문서
**대상 독자**: ISMAR 2026 논문 공동 저자

---

## 목차

1. [시스템 개요](#1-시스템-개요)
2. [논문 섹션별 코드 매핑](#2-논문-섹션별-코드-매핑)
3. [논문 vs 실제 시스템 비교표](#3-논문-vs-실제-시스템-비교표)
4. [스크린샷 - 논문 Figure 매핑 제안](#4-스크린샷---논문-figure-매핑-제안)
5. [Unity XR 포팅 시 주의사항](#5-unity-xr-포팅-시-주의사항)
6. [실험 설계 관련 제안](#6-실험-설계-관련-제안)
7. [남은 TODO 및 일정](#7-남은-todo-및-일정)

---

## 1. 시스템 개요

### 1.1 Baby AI란

Baby AI는 인간 영아의 인지 발달 과정을 모방하는 **발달 인지 아키텍처(Developmental Cognitive Architecture)**이다. LLM(Gemini)이 가진 사전 지식 위에 뇌과학 기반의 발달 메커니즘을 추가한 하이브리드 구조로, "아기처럼 무지하게 시작"하는 것이 아니라 **"아기처럼 학습하고 성장하는 방식"**을 구현한다.

핵심 특징:

- **5단계 발달**: NEWBORN(0) -> INFANT(1) -> BABY(2) -> TODDLER(3) -> CHILD(4)
- **6가지 기본 감정**: 호기심, 기쁨, 두려움, 놀람, 좌절, 지루함 + 5가지 복합 감정
- **3가지 기억 유형**: 에피소드(해마), 의미(피질), 절차(소뇌)
- **수면 기억 통합**: Ebbinghaus 망각 곡선 + 감정 강화 + 시냅스 가지치기
- **내재적 동기**: ICM(Intrinsic Curiosity Module) 기반 호기심 + 자율 목표
- **현재 상태**: Stage 5 (TEEN), 경험 2175회, 488개 개념, 616개 관계

### 1.2 전체 아키텍처

```
[사용자] ──────────────────────────────────────────────────────────────────
    │                                                                    │
    ▼                                                                    ▼
[프론트엔드: Next.js 16 + React 19]                         [감각 입력]
    │  6개 페이지 + 38개 컴포넌트 + 16개 훅                    카메라, 마이크, 텍스트
    │                                                                    │
    ▼                                                                    ▼
[API Routes: 11개]                                                       │
    │                                                                    │
    ▼                                                                    │
[Edge Functions: 13개 (Supabase)]  ◄─────────────────────────────────────┘
    │  conversation-process (v30)    │  memory-consolidation (v6)
    │  vision-process (v4)           │  generate-curiosity (v4)
    │  audio-transcribe (v2)         │  autonomous-exploration (v5)
    │  speech-synthesize (v2)        │  self-evaluation (v2)
    │  world-understanding (v2)      │  imagination-engine (v1)
    │  autonomous-goals (v2)         │  textual-backpropagation (v1)
    │                                │  test-tts (v2)
    ▼
[Supabase DB: 57+ 테이블]
    │  semantic_concepts (488)   - 뉴런
    │  concept_relations (616)   - 시냅스
    │  experiences (965)         - 경험
    │  brain_regions (9)         - 뇌 영역
    │  neuron_activations        - 실시간 활성화 (Realtime)
    │  emotion_logs (211+)       - 감정 기록
    │  procedural_patterns (102) - 절차 기억
    │  ...
    ▼
[Supabase Realtime]
    │  neuron_activations INSERT 이벤트 구독
    ▼
[프론트엔드 3D 시각화]
    │  RealisticBrain.tsx (해부학 뷰) + BrainVisualization.tsx (추상 뷰)
    │  useNeuronActivations.ts (실시간 활성화)
    │  useBrainRegions.ts (9개 뇌 영역)
    │  useBrainData.ts (뉴런/시냅스 데이터)
    ▼
[향후: Unity XR 시각화 클라이언트]
    Supabase REST + Realtime WSS -> Quest 3S MR
```

### 1.3 백엔드 모듈 (Python, 13개)

| 모듈 | 파일 | 역할 | 뇌 영역 매핑 |
|------|------|------|-------------|
| **감정 코어** | `emotions.py` | 6가지 기본 + 5가지 복합 감정, 감정 상태 추적 | 편도체, 측좌핵, ACC |
| **감정 조절기** | `emotional_modulator.py` | 학습률 동적 조절, 전략 선택 (explore/exploit) | 전두엽, 기저핵, 해마 |
| **기억 시스템** | `memory.py` | 에피소드/의미/절차 3종 기억, Supabase pgvector | 해마, 피질, 소뇌 |
| **발달 단계** | `development.py` | 5단계 발달, 마일스톤, 능력 게이팅 | - |
| **세계 모델** | `world_model.py` | 예측, 시뮬레이션, 인과추론, 상상 | - |
| **호기심 엔진** | `curiosity.py` | ICM 기반, ZPD(근접발달영역), 내재적 보상 | - |
| **자아 모델** | `self_model.py` | 능력/선호/한계 자기인식, 메타인지 | 전전두엽 |
| **인지 라우터** | `cognitive_router.py` | System 1(Flash)/System 2(Thinking) 듀얼 프로세스 | - |
| **LLM 클라이언트** | `llm_client.py` | Gemini/GPT 멀티 모델 관리 | - |
| **임베딩** | `embeddings.py` | 벡터 임베딩 (pgvector) | - |
| **시각 처리** | `vision.py` | Gemini Vision 이미지 분석 | 시각피질 |
| **DB 인터페이스** | `db.py` | Supabase CRUD 래퍼 | - |
| **진화 엔진** | `evolution.py` | 프롬프트 자기 진화 | - |

### 1.4 프론트엔드 페이지 (Next.js, 6개)

| 페이지 | URL | 설명 | 주요 컴포넌트 |
|--------|-----|------|--------------|
| **홈 대시보드** | `/` | 상태 카드, 감정 레이더, 활동 로그, 고급 시각화 탭 | BabyStateCard, EmotionRadar, ActivityLog, GrowthChart, BrainCard, MilestoneTimeline, ImaginationVisualizer, EmotionalInfluenceCard, CuriosityCard, QuestionList |
| **뇌 시각화** | `/brain` | 3D 뉴런 네트워크 (해부학/추상 뷰 토글) | RealisticBrain, BrainVisualization, ImaginationPanel, PredictionVerifyPanel, ThoughtProcessPanel |
| **감각 입력** | `/sense` | 카메라/마이크/대화 3탭, TTS, 웨이크워드 | CameraCapture, AudioRecorder, ConversationView, SpeechOutput, WakeWordIndicator |
| **수면 통합** | `/sleep` | 기억 통합 로그, 절차 기억, 수동 트리거 | MemoryConsolidationCard |
| **상상 엔진** | `/imagination` | 세계 모델 상상/예측 | ImaginationPanel |
| **설정** | `/settings` | 시스템 설정 | - |

### 1.5 데이터베이스 핵심 테이블

| 테이블 | 레코드 수 | 논문 관련도 | 설명 |
|--------|----------|-----------|------|
| `semantic_concepts` | **488** | 핵심 | 의미 개념 = 뉴런. name, category, strength, usage_count, emotional_salience, memory_strength, last_accessed 등 |
| `concept_relations` | **616** | 핵심 | 개념 간 관계 = 시냅스. from/to_concept_id, relation_type, strength, evidence_count |
| `brain_regions` | **9** | 핵심 | 뇌 영역. 구 좌표계 (theta/phi/radius min/max), color, development_stage_min |
| `concept_brain_mapping` | **452** | 핵심 | 뉴런-영역 매핑 |
| `neuron_activations` | 동적 | 핵심 | 실시간 발화. concept_id, brain_region_id, intensity, trigger_type, experience_id |
| `experiences` | **965** | 중간 | 에피소드 기억. task, output, dominant_emotion, embedding |
| `emotion_logs` | **211+** | 중간 | 감정 기록. 6축 감정 값 |
| `memory_consolidation_logs` | **553** | 중간 | 수면 기억 통합 로그 |
| `procedural_patterns` | **102** | 낮음 | 절차 기억 (소뇌) |
| `imagination_sessions` | **9** | 낮음 | 세계 모델 상상 세션 |
| `predictions` | **8+** | 낮음 | 예측 기록 |
| `baby_state` | **1** | 중간 | 싱글톤. development_stage, experience_count 등 |

---

## 2. 논문 섹션별 코드 매핑

### 2.1 Section 3.2: Baby AI Architecture

논문 3.2절에서 기술하는 각 요소가 실제 코드의 어디에 구현되어 있는지를 정리한다.

#### 2.1.1 Semantic Concepts (뉴런)

**논문 기술**: memory_strength, emotional_salience, category, last_accessed 속성

**실제 구현 위치**:

| 속성 | DB 컬럼 | 실제 사용처 |
|------|---------|-----------|
| `memory_strength` | `semantic_concepts.strength` | 수면 통합 시 강화/감쇠 (`memory-consolidation` EF v6) |
| `emotional_salience` | `semantic_concepts.emotional_salience` | 수면 통합 시 salience > 0.3인 것만 감정 강화 |
| `category` | `semantic_concepts.category` | 뉴런 색상 결정 (`useBrainData.ts`의 `CATEGORY_COLORS`) |
| `last_accessed` | `semantic_concepts.last_accessed` | Ebbinghaus 망각 곡선에서 경과 시간 계산 |
| `usage_count` | `semantic_concepts.usage_count` | 뉴런 크기 결정, 상위 500개 정렬 기준 |

**핵심 파일**:
- DB 스키마: Supabase `semantic_concepts` 테이블
- 3D 시각화 데이터 로드: `frontend/baby-dashboard/src/hooks/useBrainData.ts`
- 개념 생성/업데이트: `conversation-process` Edge Function (v30)

#### 2.1.2 Concept Relations (시냅스)

**논문 기술**: weighted connections

**실제 구현**:

| 요소 | DB 구현 | 설명 |
|------|---------|------|
| 직접 관계 | `concept_relations` 테이블 | from_concept_id, to_concept_id, strength, evidence_count, relation_type |
| 간접 관계 (공활성화) | `experience_concepts` 테이블 | 같은 경험에 등장한 개념들 간 co_activation_count |
| 시냅스 가중치 | `concept_relations.strength` | 0.0~1.0, 반복 강화 시 증가 |
| 증거 강도 | `concept_relations.evidence_count` | 해당 관계가 관찰된 횟수 |

**핵심 파일**:
- 시냅스 빌딩: `useBrainData.ts` - 직접 관계 + 공활성화 관계를 합산하여 시냅스 구성
- 시냅스 생성: `conversation-process` EF - 대화 시 새 관계 자동 생성

#### 2.1.3 Brain Regions (뇌 영역)

**논문에서는 미기술** (논문 초안에 뇌 영역 매핑이 빠져 있을 수 있음)

**실제 구현 (9개 영역)**:

| 영역 | 역할 | 구 좌표 범위 | development_stage_min |
|------|------|------------|---------------------|
| 전두엽 (Prefrontal Cortex) | 의사결정, 계획 | theta/phi 좌표 정의됨 | 0 |
| 측두엽 (Temporal Lobe) | 언어, 기억 | 정의됨 | 0 |
| 두정엽 (Parietal Lobe) | 공간 인식 | 정의됨 | 0 |
| 후두엽 (Occipital Lobe) | 시각 처리 | 정의됨 | 0 |
| 변연계 (Limbic System) | 감정 | 정의됨 | 0 |
| 소뇌 (Cerebellum) | 절차 기억 | 정의됨 | 1 |
| 뇌간 (Brainstem) | 기본 반사 | 정의됨 | 0 |
| 해마 (Hippocampus) | 기억 형성 | 정의됨 | 0 |
| 전대상피질 (ACC) | 갈등 모니터링 | 정의됨 | 2 |

**핵심 파일**:
- DB 데이터: `brain_regions` 테이블 (구 좌표 범위 저장)
- 프론트엔드 로드: `hooks/useBrainRegions.ts`
- 3D 렌더링: `components/RealisticBrain.tsx` - 투명 구체로 영역 표시
- 뉴런-영역 매핑: `concept_brain_mapping` 테이블

#### 2.1.4 Sleep Mode (수면 기억 통합)

**논문 기술**: emotional strengthening (salience > 0.3), forgetting curve (Ebbinghaus), synaptic pruning (< 0.2)

**실제 구현**:

```
memory-consolidation Edge Function (v6) 실행 흐름:

1. 경험 처리 (experiences_processed)
   - 최근 미처리 경험 조회
   - 관련 개념 강화 (strength += adjustment)

2. 감정 강화 (memories_strengthened)
   - emotional_salience > 0.3인 개념의 strength 증가
   - 감정적으로 중요한 기억 우선 보존

3. 망각 (memories_decayed)
   - Ebbinghaus 망각 곡선: strength *= exp(-decay_rate * hours_since_access)
   - last_accessed 기반 경과 시간 계산

4. 시냅스 가지치기 (pruning)
   - strength < 0.2인 concept_relations 삭제
   - 약한 연결 제거 -> 효율적 네트워크

5. 패턴 승격 (patterns_promoted)
   - 반복 패턴 -> procedural_patterns 테이블로 승격
   - 절차 기억화 (소뇌)

6. 시맨틱 링크 생성 (semantic_links_created)
   - 공출현 기반 새 concept_relations 생성
```

**핵심 파일**:
- 수면 로직: `memory-consolidation` Edge Function (Supabase)
- 자동 트리거: `hooks/useIdleSleep.ts` - 30분 무활동 시 자동 수면
- UI: `components/MemoryConsolidationCard.tsx` + `/sleep` 페이지
- 수면 로그: `memory_consolidation_logs` 테이블 (553건의 통합 기록)

#### 2.1.5 Spreading Activation (확산 활성화)

**논문에서는 간접 언급만** (3.3에서 시각화 측면으로만 기술)

**실제 구현 (매우 상세)**:

```
conversation-process Edge Function (v30) 내부:

1. 사용자 입력 수신
2. 키워드 추출 (extractKeywords)
3. 기억 회상 (Memory Recall Pipeline)
   - loadRelevantConcepts() -> 관련 개념 10개 로드
   - loadRelevantExperiences() -> 관련 경험 5개 로드
   - formatMemoryContext() -> Gemini 프롬프트 주입
4. LC-NE 감정 조절 (Aston-Jones & Cohen 2005 모델)
5. Gemini LLM 호출 (기억 + 정체성 + 컨텍스트 주입)
6. 응답에서 개념 추출
7. **직접 뉴런 활성화** (trigger_type='conversation')
   - 추출된 개념들의 neuron_activations INSERT
   - concept_brain_mapping 참조하여 brain_region_id 결정
8. **확산 활성화** (trigger_type='spreading_activation')
   - BFS 기반 wave propagation
   - 직접 활성화된 뉴런에서 인접 뉴런으로 전파
   - intensity 감쇠: 거리에 따라 감소 (0.7배/hop)
```

**프론트엔드 시각화**:

| 단계 | 구현 | 시각 효과 |
|------|------|---------|
| 직접 활성화 | `useNeuronActivations.ts` - `activeNeurons` | 뉴런 발광 (emissive), 3초 감쇠 |
| 확산 활성화 | `useNeuronActivations.ts` - `spreadingRegions` | 리플 파동 (SpreadingRipple), 5초 감쇠 |
| 히트맵 | `useNeuronActivations.ts` - `heatmapRegions` | 누적 활성화 이력, 기저 발광 |
| 사고 과정 | `ThoughtStep[]` 배열 | ThoughtProcessPanel에 단계별 표시 |

**핵심 파일**:
- 활성화 로직: `conversation-process` EF (서버)
- 실시간 수신: `hooks/useNeuronActivations.ts` (Supabase Realtime)
- 리플 시각화: `components/RealisticBrain.tsx` - `SpreadingRipple` 컴포넌트
- 사고 경로: `components/RealisticBrain.tsx` - `ThoughtProcessPanel`

### 2.2 Section 3.3: MR Visualization (Unity XR 매핑)

논문 3.3절이 제안하는 Unity XR 시각화와 현재 웹 구현의 대응 관계이다.

| 논문 제안 (Unity XR) | 현재 웹 구현 (React Three Fiber) | 매핑 가능성 |
|---------------------|-------------------------------|-----------|
| 3D force-directed node-link network | `BrainVisualization.tsx` - 피보나치 구 배치 + Louvain 클러스터링 | 직접 포팅 가능 |
| 해부학적 뇌 구조 + 9영역 | `RealisticBrain.tsx` - 투명 구체 + 구 좌표계 뉴런 배치 | 직접 포팅 가능 |
| Node size = memory_strength | `useBrainData.ts` - `baseSize = 0.08 + node.strength * 0.12` | 수식 동일 |
| Color = emotional_salience (blue->red) | 현재: category 기반 색상. salience 기반 색상 추가 필요 | 부분 포팅 필요 |
| Emission = salience | `emissiveIntensity` 기반 발광 (선택/호버/활성 구분) | 포팅 가능 |
| Opacity = recency | 현재: 고정 opacity. last_accessed 기반 투명도 추가 가능 | 확장 필요 |
| 수면 20초 애니메이션 (4단계) | `/sleep` 페이지 + `useIdleSleep.ts` 실제 수면 로직 동작 | 시각화 추가 필요 |
| 확산 활성화 파동 | `SpreadingRipple` 컴포넌트 - 확장 링 애니메이션 | 직접 포팅 가능 |
| Hand tracking (Point+Tap, Pinch, Grab) | 마우스 OrbitControls (회전/줌/팬) | XR Interaction Toolkit 필요 |
| 뇌를 1.5m 거리 배치 | 카메라 초기 위치 설정 | MR 공간 배치로 변환 |

### 2.3 기타 논문 섹션 매핑

| 논문 섹션 | 실제 구현 참조 |
|----------|--------------|
| Section 3.1: 인지 아키텍처 요약 | ICDL 논문 참조 + 위 1.3절 백엔드 모듈 전체 |
| Section 3.2: 뇌 영역 매핑 | `brain_regions` 테이블 + `concept_brain_mapping` |
| Section 3.3: 확산 활성화 시각화 | `useNeuronActivations.ts` + `RealisticBrain.tsx` |
| Section 3.4: 실시간 파이프라인 | Supabase Realtime -> `useNeuronActivations` -> 3D 업데이트 |
| Section 4: User Study | `/brain` 페이지가 2D baseline 역할 (C1 조건) |
| Section 5: Results | 미완성 - 실험 후 작성 |

---

## 3. 논문 vs 실제 시스템 비교표

논문 초안이 기술하는 수치와 실제 시스템의 수치 사이에 상당한 차이가 있다. 논문을 실제 시스템에 맞게 수정하거나, 의도적으로 축소 기술한 부분을 명시해야 한다.

### 3.1 데이터 규모 비교

| 항목 | 논문 기술 | 실제 시스템 | 배수 | 조치 필요 |
|------|---------|-----------|------|---------|
| Semantic Concepts (뉴런) | **18개** (고정 JSON) | **488개** (DB, 실시간 증가) | 27배 | 논문 수정 필수 |
| Concept Relations (시냅스) | **22개** (고정 JSON) | **616개** (DB, 실시간 증가) | 28배 | 논문 수정 필수 |
| Brain Regions | 미기술 | **9개** (구 좌표계 정의) | - | 논문 추가 필요 |
| 뇌 영역 매핑 | 미기술 | **452개** concept-region 매핑 | - | 논문 추가 필요 |
| 데이터 소스 | 고정 JSON 파일 | Supabase DB + Realtime | - | 논문 수정 필수 |
| 경험 (에피소드 기억) | 미기술 | **965개** | - | 배경 설명에 추가 가능 |
| 감정 기록 | 미기술 | **211+건** (6축) | - | 배경 설명에 추가 가능 |
| 수면 통합 이력 | 미기술 | **553건** 로그 | - | 배경 설명에 추가 가능 |

### 3.2 기능 범위 비교

| 기능 | 논문 기술 | 실제 시스템 | 비고 |
|------|---------|-----------|------|
| 기억 시각화 | 정적 네트워크 렌더링 | **실시간** 뉴런 발화 + 확산 활성화 + 히트맵 + 사고 경로 | 실시간이 핵심 차별점 |
| 수면 모드 | 20초 애니메이션 제안 | **실제 수면 통합** 동작 (Ebbinghaus + 감정 강화 + 가지치기) + UI | 애니메이션이 아닌 실제 알고리즘 |
| 감정 시스템 | salience 속성 1개 | 6가지 기본 + 5가지 복합 감정, LC-NE 조절기, 감정 레이더, 감정 타임라인 | 논문보다 훨씬 정교 |
| 인지 모듈 | 기억(memory)만 | **13개 모듈**: 감정, 기억, 발달, 세계모델, 호기심, 자아, 인지라우터, 시각, 임베딩 등 | 논문은 기억에만 초점 |
| 인터랙션 | 제안: Point+Tap, Pinch Zoom, Grab | 구현: 마우스 회전/줌/팬, 뉴런 호버/클릭 선택, 정보 패널 | Unity XR에서 확장 |
| 발달 단계 | 미기술 | 5단계 (NEWBORN~CHILD) + 능력 게이팅 | 논문에 추가 가능 |
| 시각화 뷰 | 단일 네트워크 뷰 | **2가지**: 해부학 뷰 (9영역 + 뉴런) + 추상 뷰 (피보나치 + 클러스터) | 논문에 추가 가능 |
| 프론트엔드 | 미기술 (Unity만 제안) | **6개 페이지** 완성: 대시보드, 뇌, 감각, 수면, 상상, 설정 | 2D baseline으로 활용 |

### 3.3 시각화 기법 비교

| 시각화 기법 | 논문 제안 | 실제 구현 | 포팅 난이도 |
|-----------|---------|---------|-----------|
| 노드 배치 | Force-directed | **피보나치 구 배치** (golden ratio spiral) + 영역 내 랜덤 배치 | C# 재구현 (수학 공식 그대로) |
| 클러스터링 | 미기술 | **Louvain 알고리즘** (max 10 iterations) + Astrocyte 메타노드 | C# 재구현 (알고리즘 포팅) |
| 활성화 시각화 | 색상 변화 | **발광 강도** (emissive intensity) + **리플 파동** (확장 링) + **감쇠 타이머** | 셰이더 + 타이머 |
| 히트맵 | 미기술 | **누적 활성화 히스토리** - activation_count/max_count 정규화 | DB RPC -> 색상 매핑 |
| 사고 과정 | 미기술 | **ThoughtProcessPanel** - 대화 -> 직접활성화 -> 확산 단계별 표시 | UI 패널 구현 |
| 뇌 외형 | 미기술 | **BrainShell** - 반투명 타원체 + 호흡 애니메이션 | 투명 메시 |
| 시냅스 표시 | 선 연결 | **LineBasicMaterial** + 가중치 비례 opacity | 프로시저럴 메시 (600 draw call 방지) |

---

## 4. 스크린샷 - 논문 Figure 매핑 제안

18개의 스크린샷을 논문에 어떻게 활용할 수 있는지 제안한다.

### 4.1 필수 Figure 후보

#### Figure 1: 시스템 아키텍처 다이어그램 (새로 제작 필요)

- 새로 그려야 함 (스크린샷이 아닌 다이어그램)
- 구성: Baby AI (Supabase) -> REST + Realtime WSS -> Unity XR Client -> Quest 3S
- 기존 웹 대시보드도 병렬로 표시 (2D baseline)

#### Figure 2: 3D 뇌 시각화 - 해부학 뷰

**추천 이미지: 12번 (뉴런 네트워크 시각화_v2)**

| 스크린샷 | 파일명 | 활용 이유 |
|---------|--------|---------|
| **12번** | `뉴런 네트워크 시각화_v2(대화 흐름에 따른 시각화).png` | 9개 뇌 영역 + ThoughtProcessPanel + 확산 파동(wave 66) 표시. 논문의 핵심 기여를 한 장으로 보여줌 |

이 이미지에 포함된 요소:
- 9개 뇌 영역 (투명 구체, 색상 구분)
- 뉴런 노드 (영역 내 배치)
- 시냅스 연결선
- 확산 활성화 파동 카운터 ("Spreading Wave 66")
- ThoughtProcessPanel (대화 -> 직접 활성화 -> 확산 단계)
- 대화 컨텍스트 (사용자 메시지 + AI 응답)

#### Figure 3: 3D 뇌 시각화 - 추상 뷰

**추천 이미지: 11번 (뉴런 네트워크 시각화_v1)**

| 스크린샷 | 파일명 | 활용 이유 |
|---------|--------|---------|
| **11번** | `뉴런 네트워크 시각화_v1.png` | 488 뉴런 + 616 시냅스 3D 네트워크 전체 구조. Louvain 클러스터링 + 카테고리 색상 |

#### Figure 4: 3개 조건 비교 (2D / 3D Desktop / MR)

**구성 제안**:
- **(a) 2D Dashboard**: 1번 (`baby_ai관리 대시보드.png`) 또는 4번 (`대시보드 고급 시각화(뇌).png`)
- **(b) 3D Desktop (Web)**: 12번 (`뉴런 네트워크 시각화_v2`)
- **(c) MR (Quest 3S)**: Unity 구현 후 스크린샷 (향후)

논문의 User Study 3개 조건을 시각적으로 대비할 수 있음.

#### Figure 5: 확산 활성화 시퀀스 (시간축)

- 12번 이미지를 기반으로 t=0, t=1, t=2 시점의 연속 스크린샷 필요
- 또는 녹화 영상에서 프레임 추출

### 4.2 보조 Figure 후보

| 스크린샷 | 파일명 | 논문 활용 가능성 |
|---------|--------|---------------|
| **4번** | `대시보드 고급 시각화(뇌).png` | User Study의 2D baseline (C1) 조건 대표 이미지. "498 neurons / 755 synapses / 18 clusters" 통계 표시 |
| **17번** | `수면&기억 통합.png` | 수면 모드 UI - 수면 통합 기능의 실존 증거 |
| **18번** | `수면&기억 통합1.png` | 수면 통합 결과 - 실제 memories_strengthened/decayed 수치 |
| **3번** | `대시보드 고급 시각화(감정).png` | 감정 타임라인 - 6축 감정이 시간에 따라 변화하는 모습 |
| **6번** | `대시보드 고급 시각화(상상).png` | World Model - 8 predictions, 100% accuracy, 9 sessions |
| **13번** | `뉴런 네트워크 예측 검증.png` | 예측 검증 패널 - 메타인지 능력 시각화 |
| **16번** | `감각Input(대화).png` | 감각 입력 인터페이스 - 실제 대화 장면 |

### 4.3 Figure 수량 권고

ISMAR TVCG 논문은 9+2 페이지이므로 Figure 5~7개가 적절하다.

| Figure # | 내용 | 소스 | 제작 상태 |
|----------|------|------|---------|
| Fig. 1 | 시스템 아키텍처 다이어그램 | 새로 제작 | 미완성 |
| Fig. 2 | 해부학 뷰 (웹 3D) | 스크린샷 12번 | 완성 |
| Fig. 3 | MR 시연 사진 (Quest 3S) | Unity 구현 후 | 미완성 |
| Fig. 4 | 3개 조건 비교 (2D vs 3D vs MR) | 1/4 + 12 + Unity | 2/3 완성 |
| Fig. 5 | 확산 활성화 시퀀스 (t=0,1,2) | 연속 스크린샷 | 미완성 |
| Fig. 6 | 과제 결과 차트 (정확도/시간) | 실험 후 생성 | 미완성 |
| Fig. 7 | NASA-TLX 결과 | 실험 후 생성 | 미완성 |

---

## 5. Unity XR 포팅 시 주의사항

### 5.1 데이터 파이프라인

기존 웹 프론트엔드는 Supabase JavaScript SDK를 사용한다. Unity에서는 다른 접근이 필요하다.

#### 초기 데이터 로드 (REST)

```
웹 (현재):
  supabase.from('semantic_concepts').select('*').order('usage_count', {ascending: false}).limit(500)
  supabase.from('concept_relations').select('*').order('evidence_count', {ascending: false}).limit(500)
  supabase.from('brain_regions').select('*')
  supabase.rpc('get_brain_activation_summary')

Unity (포팅):
  UnityWebRequest.Get("https://{PROJECT_REF}.supabase.co/rest/v1/semantic_concepts?select=*&order=usage_count.desc&limit=500")
  Header: "apikey: {ANON_KEY}", "Authorization: Bearer {ANON_KEY}"
  JSON 파싱: Newtonsoft.Json (JsonUtility는 배열/중첩 불가)
```

#### 실시간 구독 (WebSocket)

```
웹 (현재):
  supabase.channel('brain-activity')
    .on('postgres_changes', { event: 'INSERT', table: 'neuron_activations' }, callback)
    .subscribe()

Unity (포팅):
  supabase-csharp Realtime 또는 NativeWebSocket으로 Phoenix Channel 연결
  주의: IL2CPP 빌드 시 link.xml에 System.Reactive, Websocket.Client preserve 필수
```

#### 데이터 흐름도

```
[대화 발생] -> [conversation-process EF] -> [neuron_activations INSERT]
                                                      |
                    ┌─────────────────────────────────┤
                    ▼                                  ▼
            [웹 프론트엔드]                      [Unity 클라이언트]
            Supabase JS SDK                   supabase-csharp / NativeWebSocket
            Realtime subscription             WebSocket subscription
                    ▼                                  ▼
            [React Three Fiber]               [Unity URP 렌더링]
            RealisticBrain.tsx                NeuronRenderer.cs
            SpreadingRipple                   Emissive + Timer
```

### 5.2 클라이언트 측 재구현 항목

웹에서 JavaScript로 구현된 다음 로직을 C#으로 포팅해야 한다.

| # | 로직 | 웹 소스 파일 | 포팅 복잡도 | 설명 |
|---|------|-----------|-----------|------|
| 1 | **피보나치 구 배치** | `useBrainData.ts` | 낮음 | 수학 공식 (golden ratio spiral) 그대로 |
| 2 | **구 좌표 -> 직교 좌표 변환** | `RealisticBrain.tsx` - `sphericalToCartesian()` | 낮음 | theta, phi, r -> x, y, z (타원체 스케일 포함) |
| 3 | **간이 Louvain 클러스터링** | `useBrainData.ts` | 중간 | max 10 iterations, 시냅스 가중치 기반 |
| 4 | **Astrocyte 메타노드 계산** | `useBrainData.ts` | 낮음 | 클러스터 중심점 + 멤버 목록 |
| 5 | **시냅스 빌딩 (직접+공활성화)** | `useBrainData.ts` | 중간 | concept_relations + experience_concepts 합산 |
| 6 | **활성화 감쇠 타이머** | `useNeuronActivations.ts` | 낮음 | direct 3초, spreading 5초 |
| 7 | **히트맵 정규화** | `useNeuronActivations.ts` | 낮음 | activation_count / max_count |
| 8 | **발달 단계별 뇌 크기** | `useBrainRegions.ts` - `STAGE_PARAMS` | 낮음 | stage -> scale/synapseDensity 매핑 |
| 9 | **카테고리 색상 매핑** | `useBrainData.ts` - `CATEGORY_COLORS` | 낮음 | 카테고리 문자열 -> hex 색상 |

### 5.3 성능 주의사항

| 항목 | 웹 (현재) | Unity Quest 3S | 주의점 |
|------|---------|---------------|--------|
| 뉴런 렌더링 | R3F `<sphereGeometry>` 500개 | SRP Batcher 500개 구체 | 아이코스피어(80-320 tris) 사용, Unity 기본 Sphere(768 tris) 금지 |
| 시냅스 렌더링 | `<lineSegments>` 600개 | **단일 프로시저럴 메시** | LineRenderer 600개 = 600 draw calls. 반드시 단일 메시로 합침 |
| 뇌 영역 | 투명 `<sphereGeometry>` 9개 | URP Transparent 9개 | 투명 오브젝트 정렬 주의 |
| 실시간 업데이트 | React state -> re-render | MaterialPropertyBlock | React 리렌더 대신 GPU 직접 프로퍼티 변경 |
| 텍스트 | HTML overlay (`<Html>`) | TextMeshPro | world-space UI 또는 billboard |
| 프레임레이트 | 60fps 브라우저 | **72fps 필수** (Quest 3S) | ASW(Application SpaceWarp)도 고려 |

### 5.4 데이터 타입 주의사항

Supabase에서 Unity로 데이터를 가져올 때 타입 변환에 주의가 필요하다.

| Supabase 타입 | C# 타입 | 주의사항 |
|--------------|---------|---------|
| `uuid` | `string` | GUID.Parse 가능하지만 string으로 다루는 것이 안전 |
| `jsonb` | `JObject` (Newtonsoft) | JsonUtility 사용 불가 (중첩 객체, 배열 지원 부족) |
| `jsonb[]` | `JArray` | 반드시 객체 배열이어야 함, plain string은 변환 불가 |
| `float8` | `double` | Unity에서는 `float`로 캐스팅 (정밀도 손실 미미) |
| `timestamptz` | `DateTimeOffset` | UTC 기준 파싱 |

---

## 6. 실험 설계 관련 제안

### 6.1 2D Baseline은 이미 존재한다

논문의 User Study에서 3개 조건(C1: 2D, C2: 3D Desktop, C3: MR)을 비교한다. **C1 조건은 현재 웹 대시보드가 그대로 활용 가능**하다.

| User Study 조건 | 구현 상태 | 소스 |
|----------------|---------|------|
| **C1: 2D Dashboard** | 완성 | `/brain` 페이지 (추상 뷰) + `/` 페이지 (대시보드 탭들) |
| **C2: 3D Desktop** | Unity 에디터 빌드 필요 | Unity 프로젝트 (모니터 + 마우스) |
| **C3: MR (Quest 3S)** | Unity Quest 빌드 필요 | Unity 프로젝트 (패스스루 + 손 추적) |

### 6.2 C1 조건에서 활용할 웹 페이지 구성

2D baseline으로 다음 조합을 권장한다:

- **주 화면**: `/brain` 페이지의 **추상 뷰** (BrainVisualization.tsx)
  - 488 뉴런 + 616 시냅스 2D 투영 네트워크 (OrbitControls 사용하지만 모니터 화면)
  - ThoughtProcessPanel 포함 (사고 경로 텍스트 표시)
- **보조 화면**: `/` 페이지의 **뇌 탭** (BrainCard)
  - 498 neurons / 755 synapses / 18 clusters 요약 통계

이유: C1 조건은 "2D 모니터에서 동일 데이터를 보는 것"이므로, 현재 웹 대시보드의 2D 투영 뷰가 정확히 이 역할을 한다.

### 6.3 실험 과제(Task)별 데이터 가용성

| Task | 설명 | 필요 데이터 | 현재 가용성 |
|------|------|-----------|-----------|
| T1: 영역 식별 | "가장 활성화된 뇌 영역은?" | 뇌 영역 히트맵 | `heatmapRegions` 데이터 존재 (누적 활성화). `get_brain_activation_summary` RPC로 영역별 activation_count 제공 |
| T2: 경로 추적 | "활성화 확산 경로를 추적하세요" | 확산 활성화 시퀀스 | `ThoughtStep[]` 배열로 단계별 기록. trigger_type='conversation' -> 'spreading_activation' 순서 |
| T3: 패턴 비교 | "두 대화의 활성화 패턴 차이는?" | 대화별 활성화 기록 | `neuron_activations` 테이블에 experience_id로 대화별 그룹핑 가능 |
| T4: 발달 추정 | "AI의 현재 발달 단계는?" | 발달 단계 시각적 단서 | `useBrainRegions.ts`의 STAGE_PARAMS - 단계별 뇌 크기(scale), 시냅스 밀도 차이. 비활성 영역(회색) 표시 |

### 6.4 실험 시나리오 스크립트 제안

참가자에게 보여줄 대화 시나리오를 사전에 준비해야 한다. 실제 시스템에서 대화를 실행하면 확산 활성화가 실시간으로 발생하므로, 다음과 같이 구성한다:

```
시나리오 A: 감정 중심 대화
  "비비야, 오늘 기분이 어때?"
  -> 변연계 + 측좌핵 활성화 예상
  -> 감정 관련 개념으로 확산

시나리오 B: 지식 탐구 대화
  "비비야, 공룡은 왜 멸종했어?"
  -> 측두엽 + 전두엽 활성화 예상
  -> 인과관계 개념으로 확산

시나리오 C: 창의적 질문
  "비비야, 하늘은 왜 파란색이야?"
  -> 두정엽 + 후두엽 활성화 예상
  -> 물리 개념으로 확산
```

각 시나리오에서 동일한 대화를 3개 조건 모두에서 실행하고, 참가자가 뇌 활동을 관찰한다.

### 6.5 측정 데이터 자동 수집

시스템에서 자동으로 수집 가능한 객관적 데이터:

| 측정 항목 | 수집 방법 | 비고 |
|---------|---------|------|
| 활성화된 뉴런 수 | `neuron_activations` COUNT | 대화별 자동 기록 |
| 확산 범위 (hop 수) | `trigger_type='spreading_activation'` COUNT | 확산 규모 |
| 활성 뇌 영역 수 | `neuron_activations` DISTINCT brain_region_id | 영역 분포 |
| 대화 시점 | `experiences.created_at` | 타임스탬프 |
| 감정 상태 | `emotion_logs` | 6축 감정 값 |
| 수면 통합 효과 | `memory_consolidation_logs` | 강화/감쇠 수치 |

---

## 7. 남은 TODO 및 일정

### 7.1 논문 수정 TODO

| # | 항목 | 우선도 | 담당 | 상태 |
|---|------|-------|------|------|
| 1 | **Section 3.2 데이터 규모 수정**: "18 concepts, 22 relations" -> 실제 수치 (488/616) | 필수 | 논문 저자 | 미완성 |
| 2 | **Section 3.2 뇌 영역 추가**: 9개 뇌 영역 + 구 좌표계 매핑 설명 | 필수 | 논문 저자 | 미완성 |
| 3 | **Section 3.3 확산 활성화 상세화**: BFS + wave propagation + 감쇠 모델 | 권장 | 논문 저자 | 미완성 |
| 4 | **Section 3.4 실시간 파이프라인 기술**: Supabase Realtime -> neuron_activations -> 3D 업데이트 | 필수 | 논문 저자 | 미완성 |
| 5 | **Figure 삽입**: 최소 Fig.1~5 확보 | 필수 | 공동 | 2/5 완성 |
| 6 | **Section 6 Results**: User Study 완료 후 작성 | 필수 | 공동 | 미완성 |
| 7 | **Table 1: 시스템 사양**: 뉴런 수, 시냅스 수, 영역 수, 발달 단계 등 정리 | 권장 | 논문 저자 | 미완성 |
| 8 | **데이터 소스 설명 수정**: "fixed JSON" -> "live Supabase DB with Realtime subscription" | 필수 | 논문 저자 | 미완성 |

### 7.2 Unity 구현 TODO

| # | 작업 | 예상 시간 | 의존성 | 상태 |
|---|------|---------|--------|------|
| 1 | Unity 6 LTS + MR Example 프로젝트 셋업 | 2h | 없음 | 미시작 |
| 2 | Supabase REST 로드 (6개 테이블) | 4h | #1 | 미시작 |
| 3 | BrainDataManager (피보나치 + 클러스터링 포팅) | 4h | #2 | 미시작 |
| 4 | NeuronRenderer (SRP Batcher 500 구체) | 3h | #3 | 미시작 |
| 5 | ConnectionRenderer (프로시저럴 메시 시냅스) | 3h | #3 | 미시작 |
| 6 | RegionRenderer (9 투명 구체 + 히트맵) | 2h | #3 | 미시작 |
| 7 | Supabase Realtime WebSocket | 6h | #4 | 미시작 |
| 8 | 활성화 이펙트 (발광, 감쇠, 리플) | 4h | #4, #7 | 미시작 |
| 9 | XR 인터랙션 (레이캐스트, 정보 패널) | 4h | #4 | 미시작 |
| 10 | MR 패스스루 + 공간 배치 | 3h | #1 | 미시작 |
| **합계** | | **~35h** | | |

### 7.3 실험 관련 TODO

| # | 항목 | 담당 | 마감 | 비고 |
|---|------|------|------|------|
| 1 | IRB 승인 신청 | 교수님 | 가능한 빨리 | 가장 큰 병목. 신속 심사도 2-4주 |
| 2 | 참여자 모집 (N=16-24) | 공동 | IRB 후 | 연구실/학과 내부 모집 현실적 |
| 3 | 실험 시나리오 확정 (3개 대화) | 공동 | 실험 전 | 위 6.4절 참조 |
| 4 | 설문지 준비 (SSQ, NASA-TLX, SUS, IPQ) | 논문 저자 | 실험 전 | 표준 설문 + Custom Likert |
| 5 | 파일럿 테스트 (2-3명) | 개발자 | Unity 완성 후 | 버그 확인 + 시간 측정 |
| 6 | 데모 영상 촬영 (30초-3분) | 개발자 | 실험 전 | Quest 3S MR 화면 녹화. ISMAR 사실상 필수 |

### 7.4 일정 요약

```
현재: 2026-02-25

[Week 1: 2/25 ~ 3/3]
  - Unity 프로젝트 셋업 + Supabase 연동 + 정적 뇌 렌더링
  - 논문 Section 3.2, 3.4 수치 수정
  - IRB 신청

[Week 2: 3/3 ~ 3/9]
  - 실시간 활성화 + MR 패스스루 + 인터랙션
  - 데모 영상 촬영 + 파일럿 테스트
  - **3/9: Abstract 제출 마감**

[Week 3: 3/9 ~ 3/16]
  - User Study 데이터 수집 시작
  - Results 초안 작성
  - **3/16: Paper 제출 마감**
```

---

## 부록 A: 핵심 코드 파일 경로

논문 내용과 직접 관련된 코드 파일의 절대 경로이다.

### 프론트엔드 (Next.js)

```
E:\A2A\our-a2a-project\frontend\baby-dashboard\src\

  hooks/
    useNeuronActivations.ts   -- 실시간 뉴런 활성화 (Realtime 구독, 히트맵, 사고과정)
    useBrainRegions.ts        -- 9개 뇌 영역 + 발달 단계별 파라미터
    useBrainData.ts           -- 뉴런/시냅스 로드, 피보나치 배치, Louvain 클러스터링
    useIdleSleep.ts           -- 자동 수면 (30분 무활동)
    useImaginationSessions.ts -- 상상 세션 데이터
    usePredictions.ts         -- 예측 데이터 + 검증

  components/
    RealisticBrain.tsx        -- 해부학 뷰 3D (9영역, SpreadingRipple, BrainShell, ThoughtProcessPanel)
    BrainVisualization.tsx    -- 추상 뷰 3D (피보나치, Louvain, Astrocyte)
    MemoryConsolidationCard.tsx -- 수면 기억 통합 UI
    EmotionRadar.tsx          -- 감정 레이더 차트
    ImaginationPanel.tsx      -- 상상 패널
    PredictionVerifyPanel.tsx -- 예측 검증 패널

  app/
    page.tsx                  -- 홈 대시보드
    brain/page.tsx            -- 뇌 시각화 (해부학/추상 토글)
    sense/page.tsx            -- 감각 입력 (카메라/마이크/대화)
    sleep/page.tsx            -- 수면 & 기억 통합
    imagination/page.tsx      -- 상상 엔진
    settings/page.tsx         -- 설정
```

### 백엔드 (Python)

```
E:\A2A\our-a2a-project\neural\baby\

  emotions.py                 -- 6 기본 + 5 복합 감정
  emotional_modulator.py      -- LC-NE 감정 학습 조절기
  memory.py                   -- 3종 기억 시스템
  development.py              -- 5단계 발달 + 능력 게이팅
  world_model.py              -- 예측/시뮬레이션/인과추론/상상
  curiosity.py                -- ICM 호기심 엔진
  self_model.py               -- 자아 모델 (능력/선호/한계)
  cognitive_router.py         -- System 1/2 듀얼 프로세스
  vision.py                   -- 시각 처리 (Gemini Vision)
  db.py                       -- Supabase 인터페이스
  embeddings.py               -- 벡터 임베딩
```

### 문서

```
E:\A2A\our-a2a-project\docs\

  ISMAR_2026_STRATEGY.md      -- ISMAR 투고 전략, User Study 설계, 일정
  PAPER_PLAN.md               -- ICDL 논문 마스터 플랜
  PARAMETER_TAXONOMY.md       -- 3-Tier 파라미터 분류
  PROJECT_VISION.md           -- 프로젝트 비전
```

---

## 부록 B: 논문에 인용 가능한 시스템 수치

논문의 Table이나 본문에 사용할 수 있는 검증된 수치이다. (2026-02-25 기준)

| 항목 | 수치 | 출처 |
|------|------|------|
| Semantic Concepts (뉴런) | 488 | `semantic_concepts` 테이블 COUNT |
| Concept Relations (시냅스) | 616 | `concept_relations` 테이블 COUNT |
| Brain Regions | 9 | `brain_regions` 테이블 COUNT |
| Concept-Region Mappings | 452 | `concept_brain_mapping` 테이블 COUNT |
| Total Experiences | 965 | `experiences` 테이블 COUNT |
| Emotion Logs | 211+ | `emotion_logs` 테이블 COUNT |
| Memory Consolidation Sessions | 553 | `memory_consolidation_logs` 테이블 COUNT |
| Procedural Patterns | 102 | `procedural_patterns` 테이블 COUNT |
| Development Stage | 5 (TEEN) | `baby_state.development_stage` |
| Total Experience Points | 2175 | `baby_state.experience_count` |
| Edge Functions | 13 | Supabase 배포 목록 |
| Frontend Pages | 6 | Next.js app router |
| Frontend Components | 38 | `src/components/` 디렉토리 |
| Frontend Hooks | 16 | `src/hooks/` 디렉토리 |
| Imagination Sessions | 9 | `imagination_sessions` 테이블 |
| Predictions | 8+ | `predictions` 테이블 |
| Prediction Accuracy | 100% (8/8) | `predictions` verified 기록 |
| Basic Emotions | 6 | curiosity, joy, fear, surprise, frustration, boredom |
| Compound Emotions | 5 | pride, anxiety, wonder, melancholy, determination |
| Neuron Categories | 15+ | `CATEGORY_COLORS` in `useBrainData.ts` |
| Spreading Activation Decay | 3s (direct), 5s (spreading) | `useNeuronActivations.ts` |
| Spreading Intensity Falloff | 0.7x per hop | `conversation-process` EF |
| Idle Sleep Trigger | 30분 | `useIdleSleep.ts` |
| Sleep Pruning Threshold | strength < 0.2 | `memory-consolidation` EF |
| Emotional Strengthening Threshold | salience > 0.3 | `memory-consolidation` EF |

---

## 부록 C: 용어 대조표

논문과 코드에서 같은 것을 다른 이름으로 부르는 경우를 정리한다.

| 논문 용어 | 코드 용어 | 설명 |
|---------|---------|------|
| Concept / Node | `semantic_concepts` 테이블, `NeuronNode` 타입 | 의미 개념 = 뉴런 |
| Connection / Edge / Link | `concept_relations` 테이블, `Synapse` 타입 | 개념 간 관계 = 시냅스 |
| Memory Strength | `semantic_concepts.strength` | 기억 강도 (0~1) |
| Emotional Salience | `semantic_concepts.emotional_salience` | 감정 현저성 (0~1) |
| Brain Region | `brain_regions` 테이블, `BrainRegion` 타입 | 뇌 영역 |
| Activation | `neuron_activations` 테이블, `NeuronActivation` 인터페이스 | 뉴런 발화 |
| Spreading Activation | `trigger_type = 'spreading_activation'` | 확산 활성화 |
| Direct Activation | `trigger_type = 'conversation'` | 직접 활성화 (대화 트리거) |
| Heatmap | `heatmapRegions` (Map), `RegionHeatmap` 타입 | 누적 활성화 히스토리 |
| Sleep Mode | `memory-consolidation` EF, `useIdleSleep` hook | 수면 기억 통합 |
| Forgetting Curve | Ebbinghaus decay in `memory-consolidation` EF | 망각 곡선 |
| Synaptic Pruning | `strength < 0.2` deletion in `memory-consolidation` EF | 시냅스 가지치기 |
| Development Stage | `baby_state.development_stage`, `DevelopmentStage` enum | 발달 단계 |
| Anatomical View | `RealisticBrain.tsx`, `viewMode='anatomical'` | 해부학적 뇌 뷰 |
| Abstract View | `BrainVisualization.tsx`, `viewMode='abstract'` | 추상 네트워크 뷰 |
| Thought Process | `ThoughtStep[]`, `ThoughtProcessPanel` | 사고 과정 (활성화 경로) |
| Ripple / Wave | `SpreadingRipple` 컴포넌트, `waveCount` | 확산 파동 시각 효과 |
| Astrocyte | `Astrocyte` 타입 (useBrainData) | Louvain 클러스터 메타노드 |

---

**문서 끝**

질문이나 추가 정보가 필요하면 언제든 요청 바랍니다.
