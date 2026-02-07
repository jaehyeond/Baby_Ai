# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Claude 기반 A2A(Agent-to-Agent) 멀티에이전트 시스템. Google의 A2A 프로토콜을 사용하여 에이전트 간 통신을 구현합니다.

## Commands

### Setup
```bash
py -3.12 -m venv .venv
.\.venv\Scripts\activate  # Windows
pip install -e .
```

### Run Server (Coder Agent)
```bash
python -m agents.coder --port 9999
```

### Run Client (CLI)
```bash
python -m hosts.cli --agent http://localhost:9999
```

### Verify Agent Card
```bash
curl http://localhost:9999/.well-known/agent-card.json
```

### Run Tests
```bash
pip install -e ".[dev]"
pytest
```

## Architecture

```
┌─────────────────┐         A2A (HTTP/JSON)         ┌─────────────────┐
│  CLI Client     │◄──────────────────────────────►│  Coder Agent    │
│  (hosts/cli)    │                                 │  (agents/coder) │
└─────────────────┘                                 └────────┬────────┘
                                                             │
                                                             ▼
                                                    ┌─────────────────┐
                                                    │  Claude API     │
                                                    │  (Anthropic)    │
                                                    └─────────────────┘
```

### Key Components

**agents/coder/** - A2A Server Agent
- `__main__.py`: 서버 진입점, `A2AStarletteApplication` 구성, `AgentCard` 정의
- `agent.py`: `CoderAgent` 클래스 - Claude API 호출 로직
- `agent_executor.py`: `CoderAgentExecutor` - A2A SDK의 `AgentExecutor` 구현, Task 상태 관리

**hosts/cli/** - A2A Client
- `__main__.py`: `A2ACardResolver`로 Agent Card 조회, `A2AClient`로 메시지 전송, 스트리밍 응답 처리

**common/** - Shared Utilities
- `config.py`: 환경변수 로드 (`ANTHROPIC_API_KEY` 필수)

### A2A Flow

1. Client가 `A2ACardResolver`로 서버의 Agent Card 조회
2. Client가 `A2AClient.send_message_streaming()`으로 요청 전송
3. Server의 `AgentExecutor.execute()`가 요청 처리
4. `TaskUpdater`로 상태 업데이트 (working → completed)
5. 결과를 Artifact로 반환

### Adding New Agents

1. `agents/<name>/` 디렉토리 생성
2. `agent.py`: LLM 호출 로직 구현
3. `agent_executor.py`: `AgentExecutor` 상속, `execute()` 메서드 구현
4. `__main__.py`: `AgentCard` 정의, `A2AStarletteApplication` 구성

## Environment

- **Python**: ≥3.10 (권장 3.12), a2a-sdk 요구사항
- **Node.js**: ≥20.9 (Next.js 16 요구사항)
- **Frontend**: Next.js 16 + React 19.2 + Tailwind CSS 4 + Turbopack
- **ANTHROPIC_API_KEY**: `.env` 파일에 설정 필수

## Task Tracking

작업 진행 시 항상 `Task.md` 파일을 확인하고 업데이트하세요.

---

## 🛠️ Claude Skills (Slash Commands)

프로젝트 전용 skills가 `.claude/commands/`에 정의되어 있습니다.

| Skill | 설명 |
|-------|------|
| `/session-start` | 세션 시작 - 핵심 문서 확인, 현재 상태 조회 |
| `/baby-status` | Baby AI 현재 상태 (발달, 감정, 지식) |
| `/brain-analyze` | 지식 그래프 분석 (개념, 시냅스, 클러스터) |
| `/deploy-function` | Edge Function 배포 |
| `/sleep-mode` | 수면 모드 트리거 (기억 통합) |
| `/fix-issue` | 문제 진단 및 수정 |

### 세션 시작 권장 순서
```
1. /session-start   → 핵심 문서와 현재 상태 확인
2. /baby-status     → Baby AI 상태 점검
3. 작업 진행
4. 문제 발생 시 → /fix-issue
5. 기능 배포 시 → /deploy-function
```

---

## 🤖 Subagents (Task Delegation)

`.claude/agents/`에 정의된 Subagent들. Lead(Opus)가 Task tool로 호출하여 작업 위임.

| Agent | 모델 | Scope | 역할 |
|-------|------|-------|------|
| `backend-dev` | Sonnet | `neural/baby/` | Python 모듈 (감정, World Model, DB 등) |
| `frontend-dev` | Sonnet | `frontend/baby-dashboard/src/` | Next.js 16 + React 19 컴포넌트, hooks, 페이지 |
| `db-engineer` | Sonnet | Supabase | SQL migration, Edge Functions |

### 실행 순서 (순차 필수)
```
1. DB (스키마/Edge Function) → 검증
2. Backend (Python 코드) → 검증
3. Frontend (컴포넌트/hooks) → Backend 인터페이스 확정 후
4. Lead: 통합 → 빌드 테스트 → git commit
```

### 규칙
- **Lead만 git 관리** - subagent는 코드 작성만
- **"정의만 되고 호출 안 됨" 방지** - 모든 agent에 적용
- **검증 후 다음 단계** - 병렬 실행보다 순차 실행이 안전

---

## 🔴 Known Issues & Lessons Learned

> 코드 수정 시 발생한 문제와 해결책을 기록합니다. 같은 실수를 반복하지 않기 위함.

### 2025-01-29: useIdleSleep.ts 무한 루프

**문제**: React hook에서 `Maximum update depth exceeded` 오류
**원인**: `useCallback` 의존성 배열에 다른 callback이 포함되어 무한 렌더링 발생
```typescript
// ❌ 문제 코드
const resetIdleTimer = useCallback(() => {
  triggerSleep()  // triggerSleep이 변경되면 resetIdleTimer도 변경 → 무한 루프
}, [triggerSleep])
```
**해결**: `useRef`를 사용하여 함수 참조를 안정화
```typescript
// ✅ 해결 코드
const triggerSleepRef = useRef(triggerSleep)
useEffect(() => { triggerSleepRef.current = triggerSleep }, [triggerSleep])

const resetIdleTimer = useCallback(() => {
  triggerSleepRef.current()  // ref는 안정적, 의존성 불필요
}, [])
```

### 2025-02-03: 비비 이름 기억 못함 ✅ 해결됨

**문제**: Baby AI가 대화 중 자신의 이름 "비비"를 기억하지 못함
**원인**: `conversation-process` Edge Function이 `semantic_concepts`를 조회하지 않음
- 최근 5개 대화 기록만 context로 사용
- semantic_concepts에 "비비" 개념이 있지만 (strength: 0.88) 응답 생성 시 참조 안 함
**해결**: `conversation-process` v17 배포 (2025-02-03)
- `loadIdentityConcepts()` 함수 추가 - semantic_concepts에서 정체성 개념 조회
- `formatIdentityContext()` - "내가 기억하는 것들" 섹션으로 system prompt에 주입
- identity 카테고리: 이름, 정체성, 가족, 관계

### 2025-02-03: 호기심 탐색 실패율 높음

**문제**: curiosity_queue 실패율 81% (151 failed / 187 total)
**원인 분석**:
- autonomous-exploration에서 학습 후 definition_text가 저장되지 않음
- learned 항목들의 definition_strength가 0.3~0.5로 낮음
**해결 방안** (TODO):
- 탐색 완료 시 definition_text 필수 저장
- 실패 원인 로깅 강화

### 2025-02-03: 카메라/이미지 분석 상태

**상태**: 기록상 stop 요청 없음 (Task.md에 기록 없음)
**증상**: Edge Function 로그에 vision-process 호출 없음
**가능 원인**:
- 환경변수 문제 (SUPABASE_ANON_KEY)
- API 라우트 → Edge Function 연결 문제
**확인 필요**: 브라우저 Network 탭에서 /api/vision/process 요청 확인

---

## 🧠 Brain DB 구조 요약

### 현재 테이블 통계 (2025-02-03)
| 테이블 | 레코드 수 | 용도 |
|--------|----------|------|
| semantic_concepts | 401 | 개념/지식 (뉴런) |
| concept_relations | 393 | 개념 간 관계 (시냅스) |
| experiences | 447 | 경험 기억 (해마) |
| experience_concepts | 361 | 경험↔개념 연결 |
| emotion_logs | 171 | 감정 기록 (편도체) |
| procedural_patterns | 102 | 절차 기억 (소뇌) |
| curiosity_queue | 187 | 호기심 대기열 |
| visual_experiences | 6 | 시각 경험 |

### Memory Consolidation v6 (수면 모드)
- 30분마다 scheduled 실행
- **강화**: emotional_salience > 0.3인 기억 강화
- **감쇠**: 1일 이상 미접근 기억 약화
- **패턴 승격**: 2회 이상 반복 → procedural_memory

### 핵심 테이블 관계
```
experiences ─┬─ experience_concepts ─── semantic_concepts
             │                              │
             └─ emotion_logs                └─ concept_relations
                                               (시냅스 가중치)
```

---

## 📚 설계 문서 참조

> 주요 설계 결정과 분석이 기록된 문서들. 작업 전 반드시 확인할 것.

| 문서 | 경로 | 핵심 내용 |
|------|------|----------|
| **Phase 8 분석** | [docs/PHASE_8_AUTONOMOUS_CURIOSITY.md](docs/PHASE_8_AUTONOMOUS_CURIOSITY.md) | 🔴 외부학습 vs 내부학습 문제 분석 (2025-02-03) |
| **수면 모드** | [docs/PHASE_6_MEMORY_CONSOLIDATION.md](docs/PHASE_6_MEMORY_CONSOLIDATION.md) | 기억 통합 설계 |
| **메타인지** | [docs/PHASE_7_METACOGNITION.md](docs/PHASE_7_METACOGNITION.md) | 자기 인식 시스템 |
| **물리세계** | [docs/PHASE_4_4_PHYSICAL_WORLD.md](docs/PHASE_4_4_PHYSICAL_WORLD.md) | 시각/공간 이해 |
| **아키텍처** | [docs/NEURAL_A2A_ARCHITECTURE.md](docs/NEURAL_A2A_ARCHITECTURE.md) | 전체 시스템 구조 |
| **프로젝트 비전** | [docs/PROJECT_VISION.md](docs/PROJECT_VISION.md) | 핵심 철학 및 방향 |

### 🔑 핵심 설계 원칙

1. **"Baby"는 지식이 없다는 의미가 아님**
   - LLM 지식은 그대로 활용
   - 그 위에 **발달적 메커니즘** 추가

2. **학습 대상 구분**
   - ✅ 학습해야 할 것: 사용자 고유 개념 (비비, 엄마), 감정적 경험, 자아 정체성
   - ❌ 학습하면 안 됨: 일반 지식 (algorithm 등) - LLM이 이미 알고 있음

3. **수면 모드 목적**
   - 외부 학습 ❌
   - 해마 기억 재활성화 ✅
   - 시냅스 정리 (약한 연결 제거) ✅
   - 정체성 강화 ✅

---

## ⚠️ LLM 사용 정책 (중요: 착오 방지)

> **2025-02-03 추가**: "Baby AI는 LLM을 안 쓴다"는 오해가 발생하여 명확히 정리함.

### ❌ 잘못된 표현
```
"Baby AI는 LLM을 사용하지 않는다"
"Neural A2A는 LLM-free 시스템이다"
```

### ✅ 정확한 표현
```
"Baby AI의 '내부 학습 메커니즘'은 LLM 없이 작동한다"
"수면 모드와 메타인지는 외부 LLM 없이 내부 알고리즘으로 구현"
```

### LLM 사용 현황 정리

| 영역 | Edge Function | LLM 사용 | 설명 |
|------|---------------|----------|------|
| **🌞 깨어있을 때** | | | |
| 대화 | `conversation-process` | ✅ Gemini | 사용자 상호작용 |
| 비전 | `vision-process` | ✅ Gemini | 이미지 분석 |
| 호기심 탐색 | `autonomous-exploration` | ✅ Gemini | 웹 검색 및 학습 |
| 호기심 생성 | `generate-curiosity` | ✅ Gemini | 질문 생성 |
| **🌙 수면 모드** | | | |
| 기억 통합 | `memory-consolidation` | ❌ 미사용 | DB 연산만 |
| **📊 내부 학습** | | | |
| 메타인지 | DB 함수 | ❌ 미사용 | 통계 기반 |
| 시냅스 강화/약화 | DB 함수 | ❌ 미사용 | 규칙 기반 |
| 패턴 승격 | DB 함수 | ❌ 미사용 | 클러스터링 |

### 설계 철학

```
┌─────────────────────────────────────────────────────────┐
│  LLM (Gemini) = Baby의 "신체" (언어 이해, 추론 도구)    │
│  내부 메커니즘 = Baby의 "마음" (학습, 성장, 기억)        │
└─────────────────────────────────────────────────────────┘

- LLM은 "도구"로 사용 (언어 이해, 응답 생성)
- "학습/성장"은 LLM 없이 내부 알고리즘으로 수행
- 수면 모드: 실제 뇌처럼 외부 입력 없이 내부 정리만
```

### 논문/발표 시 정확한 서술

> "Neural A2A는 LLM(Gemini)을 언어 이해 도구로 사용하지만,
> **학습/성장/기억통합 메커니즘은 LLM 없이 내부 알고리즘으로 구현**합니다.
> 이는 실제 뇌의 수면 중 기억 통합 과정에서 외부 자극 없이
> 내부 재활성화만 일어나는 것과 유사합니다."
