# Task.md - 작업 추적

**최종 업데이트**: 2026-02-04

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

## 📊 현재 시스템 상태 (2026-02-04)

### Edge Functions (12개 - 모두 ACTIVE)

| Function | Version | JWT | 용도 | 상태 |
|----------|---------|-----|------|------|
| `conversation-process` | v17 | ❌ | 대화 처리 (Gemini + 정체성 기억) | ✅ 정상 |
| `vision-process` | v3 | ❌ | 이미지 분석 (Gemini Vision) | ✅ 정상 |
| `world-understanding` | v2 | ❌ | 물리 세계 이해 | ✅ 정상 |
| `audio-transcribe` | v2 | ❌ | STT (Gemini) | ✅ 정상 |
| `speech-synthesize` | v2 | ❌ | TTS (Google) | ✅ 정상 |
| `memory-consolidation` | v6 | ❌ | 수면 모드 기억 통합 (LLM 미사용) | ✅ 정상 |
| `generate-curiosity` | **v4** | ✅ | 호기심 생성 + 분류 (Phase A) | ✅ 정상 |
| `autonomous-exploration` | v5 | ✅ | 자율 탐색/학습 | ✅ 정상 |
| `self-evaluation` | v2 | ✅ | 메타인지 자기 평가 | ✅ 정상 |
| `autonomous-goals` | v2 | ❌ | 자율 목표 생성 | ✅ 정상 |
| `textual-backpropagation` | v1 | ✅ | 피드백 전파 | ✅ 정상 |
| `test-tts` | v2 | ❌ | TTS 테스트용 | ✅ 정상 |

### Frontend API Routes (10개)

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

### Database 상태 (54개 테이블)

| 테이블 | 레코드 수 | 용도 |
|--------|----------|------|
| `semantic_concepts` | 413 | 개념/지식 (뉴런) |
| `concept_relations` | 429 | 개념 간 관계 (시냅스) |
| `experiences` | 460 | 경험 기억 (해마) |
| `emotion_logs` | 184 | 감정 기록 (편도체) |
| `curiosity_queue` | 9 | 호기심 대기열 (모두 learned) |
| `exploration_logs` | 9 | 탐색 기록 |
| `procedural_patterns` | 102 | 절차 기억 (소뇌) |
| `memory_consolidation_logs` | 553 | 기억 통합 로그 |
| `visual_experiences` | 8 | 시각 경험 |
| `autonomous_goals` | 24 | 자율 목표 |
| `baby_state` | 1 | Baby AI 상태 (싱글톤) |
| `self_evaluation_logs` | 0 | 메타인지 로그 |

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

---

## 🔄 현재 기능 흐름 (End-to-End)

### 1. 대화 흐름 ✅
```
사용자 입력 → /api/conversation → conversation-process (v17)
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
```

---

## ⚠️ Known Issues (2026-02-03)

### 1. self_evaluation_logs 비어있음
- **상태**: 0개 레코드
- **원인**: self-evaluation Edge Function 호출은 있으나 (로그 확인됨) 기록 안 됨
- **우선순위**: 낮음 (기능에 영향 없음)

### 2. 호기심 탐색 기록 적음
- **상태**: curiosity_queue 9개, exploration_logs 9개
- **원인**: 이전에 81% 실패율 문제 → v5에서 수정됨
- **현재**: 모두 "learned" 상태로 정상

### 3. visual_experiences 적음
- **상태**: 8개 레코드
- **원인**: 카메라 기능 사용 빈도 낮음
- **우선순위**: 낮음

---

## 🚀 현재 진행 중인 Phase

### Phase A: 비비의 능동적 질문 시스템 (2026-02-04~)

> **목표**: 비비가 사용자에게 먼저 질문할 수 있는 구조 구현
>
> **핵심 아이디어**: 호기심 중 "사실적 지식"은 웹 검색, "개인적/선호/경험" 관련은 사용자에게 직접 질문

| Day | 작업 | 상태 | 비고 |
|-----|------|------|------|
| 1 | `pending_questions` 테이블 생성 | ✅ 완료 | 15컬럼, RLS, Realtime 활성화 |
| 2 | `generate-curiosity` v4 수정 | ✅ 완료 | Gemini 분류 + pending_questions 라우팅 |
| 3 | Supabase Realtime 연동 | ✅ 완료 | usePendingQuestions hook + QuestionNotification |
| 4 | 질문 UI 컴포넌트 | ⬜ 예정 | QuestionBubble 모달, 답변 저장 |
| 5 | 통합 테스트 | ⬜ 예정 | End-to-end 검증 |

**관련 문서**: [docs/PHASE_A_PROACTIVE_QUESTIONS.md](docs/PHASE_A_PROACTIVE_QUESTIONS.md)

---

## 🎯 다음 단계 후보

### Option A: World Model 통합 (상상/예측)
- 현재 `imagination_sessions`, `simulations`, `predictions` 테이블 존재
- 사용되지 않는 상태
- 내부 시뮬레이션 기능 구현 필요

### Option B: Emotion Engine 강화
- 현재 기본 감정 (6가지) 구현됨
- 감정→행동 매핑 강화
- 감정 기반 목표 생성 개선

### Option C: 자율 탐색 개선
- 호기심 생성 로직 개선
- 탐색 성공률 모니터링
- 학습 결과 정체성 통합

### Option D: Mobile/Embodied AI
- 카메라/마이크 상시 활용
- 물리 세계 이해 강화
- 실시간 환경 인식

---

## 📁 프로젝트 구조

```
our-a2a-project/
├── frontend/baby-dashboard/     # Next.js 대시보드
│   ├── src/
│   │   ├── app/                 # 페이지 (/, /brain, /sense, /sleep)
│   │   ├── components/          # React 컴포넌트
│   │   ├── hooks/               # useBrainData, useCamera, etc.
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
