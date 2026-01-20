# Our A2A Project - 프로젝트 종합 정리

**최종 업데이트**: 2025-01-20
**버전**: 0.2.0 (Phase 2 Complete)
**상태**: Dashboard Phase 2 완료 - Brain/World Model 시각화 구현

---

## 1. 프로젝트 개요

### 1.1 목적
Google의 A2A(Agent-to-Agent) 프로토콜을 사용하여 **Claude 기반 멀티에이전트 시스템**을 구축합니다.

### 1.2 핵심 기술 스택

| 구분 | 기술 | 버전 |
|------|------|------|
| **LLM** | Claude API (Anthropic) | claude-sonnet-4-20250514 |
| **프로토콜** | A2A (Agent2Agent) | 0.3.x |
| **SDK** | a2a-sdk | ≥0.3.0 |
| **Python** | Python | ≥3.10 (권장 3.12) |
| **서버** | Starlette + Uvicorn | - |

### 1.3 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                    A2A MVP 시스템                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  [Terminal A: Server]              [Terminal B: Client]     │
│                                                             │
│  ┌─────────────────┐               ┌─────────────────┐      │
│  │  Coder Agent    │◄────A2A─────►│  CLI Client     │      │
│  │  (Port 9999)    │   HTTP/JSON   │                 │      │
│  │                 │               │  "코드 작성해줘" │      │
│  │  ┌───────────┐  │               │        ↓        │      │
│  │  │ Claude API│  │               │  결과 출력      │      │
│  │  │(Anthropic)│  │               │                 │      │
│  │  └───────────┘  │               └─────────────────┘      │
│  └─────────────────┘                                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. 프로젝트 구조

```
e:\A2A\our-a2a-project\
│
├── pyproject.toml              # 의존성 및 빌드 설정
├── .env.example                # 환경변수 템플릿
├── .env                        # 실제 환경변수 (Git 제외)
├── .gitignore                  # Git 제외 파일 목록
├── README.md                   # 빠른 시작 가이드
├── PROJECT_SUMMARY.md          # 이 파일 (종합 정리)
│
├── agents/                     # A2A 서버 에이전트
│   ├── __init__.py
│   └── coder/                  # Coder Agent
│       ├── __init__.py
│       ├── __main__.py         # 서버 진입점 (uvicorn)
│       ├── agent.py            # Claude API 호출 로직
│       └── agent_executor.py   # A2A AgentExecutor 구현
│
├── hosts/                      # A2A 클라이언트
│   ├── __init__.py
│   └── cli/                    # CLI 클라이언트
│       ├── __init__.py
│       └── __main__.py         # 클라이언트 진입점
│
├── common/                     # 공통 유틸리티
│   ├── __init__.py
│   └── config.py               # 환경변수 설정 관리
│
└── frontend/                   # 프론트엔드
    └── baby-dashboard/         # Baby AI 대시보드 (Next.js)
        ├── src/
        │   ├── app/            # Next.js App Router
        │   │   ├── page.tsx    # 메인 대시보드
        │   │   ├── brain/      # 뉴런 네트워크 3D 시각화
        │   │   ├── imagination/# World Model 페이지
        │   │   └── settings/   # 설정 페이지
        │   ├── components/     # React 컴포넌트
        │   └── hooks/          # Custom React Hooks
        └── package.json
```

---

## 3. 핵심 컴포넌트 설명

### 3.1 Coder Agent (Server)

**역할**: Claude API를 사용하여 Python 코드를 생성하는 A2A 서버

**파일별 역할**:

| 파일 | 역할 |
|------|------|
| `__main__.py` | 서버 진입점, AgentCard 정의, uvicorn 실행 |
| `agent.py` | Claude API 호출, 코드 생성 로직 |
| `agent_executor.py` | A2A AgentExecutor 구현, Task 상태 관리 |

**Agent Card 정보**:
- **이름**: Claude Coder Agent
- **설명**: Claude 기반 Python 코드 생성 에이전트
- **스킬**: write_python (Python 코드 생성)
- **포트**: 9999 (기본값)

### 3.2 CLI Client

**역할**: 사용자 입력을 받아 Coder Agent에 요청을 보내고 결과를 출력

**주요 기능**:
- Agent Card 자동 조회
- 스트리밍 응답 지원
- 대화형 인터페이스

### 3.3 Common (공통)

**config.py**: 환경변수 로드 및 검증
- `ANTHROPIC_API_KEY`: Claude API 키 (필수)
- `CODER_AGENT_HOST`: 서버 호스트 (기본: localhost)
- `CODER_AGENT_PORT`: 서버 포트 (기본: 9999)

---

## 4. 실행 가이드

### 4.1 사전 요구사항

- Python 3.10 이상 (권장: 3.12)
- Anthropic API 키

### 4.2 설치

```bash
cd e:\A2A\our-a2a-project

# 가상환경 생성 (Python 3.12 사용)
py -3.12 -m venv .venv

# 활성화 (Windows)
.\.venv\Scripts\activate

# 의존성 설치
pip install -e .
```

### 4.3 환경변수 설정

`.env` 파일에 Anthropic API 키 입력:
```
ANTHROPIC_API_KEY=sk-ant-your-actual-key-here
```

### 4.4 실행

**Terminal A (서버)**:
```bash
cd e:\A2A\our-a2a-project
.\.venv\Scripts\activate
python -m agents.coder --port 9999
```

**Terminal B (클라이언트)**:
```bash
cd e:\A2A\our-a2a-project
.\.venv\Scripts\activate
python -m hosts.cli --agent http://localhost:9999
```

### 4.5 테스트

```
입력> 피보나치 함수 작성해줘
[작업 중] 코드 생성 중...
[완료]

def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

입력> :q  (종료)
```

---

## 5. A2A 프로토콜 개념

### 5.1 A2A란?

**Agent-to-Agent Protocol**: 서로 다른 AI 에이전트들이 표준화된 방식으로 통신하고 협업할 수 있게 해주는 프로토콜

### 5.2 핵심 용어

| 용어 | 설명 |
|------|------|
| **Agent Card** | 에이전트의 명함 (이름, 설명, 스킬, URL 등) |
| **Skill** | 에이전트가 수행할 수 있는 능력 |
| **Task** | 작업 단위, 상태(working, completed 등) 관리 |
| **Server** | 요청을 받아 처리하는 에이전트 |
| **Client** | 요청을 보내는 에이전트 또는 사용자 |

### 5.3 A2A vs MCP

| 구분 | A2A | MCP |
|------|-----|-----|
| **대상** | 에이전트 ↔ 에이전트 | 에이전트 ↔ 도구/데이터 |
| **관계** | 동등 (Peer-to-Peer) | 주종 (Master-Tool) |
| **비유** | 동료 | 손과 발 |

---

## 6. 트러블슈팅

### 6.1 "ANTHROPIC_API_KEY not set"

```bash
# .env 파일 존재 확인
dir .env

# .env 파일 내용 확인 (키가 제대로 입력되었는지)
type .env
```

### 6.2 "Connection refused"

```bash
# 서버가 실행 중인지 확인
curl http://localhost:9999/.well-known/agent-card.json

# 포트 사용 확인
netstat -ano | findstr :9999
```

### 6.3 Python 버전 오류

```bash
# 설치된 Python 버전 확인
py -0

# Python 3.12로 가상환경 재생성
rmdir /s /q .venv
py -3.12 -m venv .venv
```

### 6.4 a2a-sdk 설치 실패

a2a-sdk는 **Python 3.10 이상** 필수입니다.
```bash
python --version  # 3.10 이상인지 확인
```

---

## 7. 개발 진행 상황

### ✅ Phase 1: A2A MVP (완료)
- [x] Coder Agent: Claude 기반 Python 코드 생성
- [x] CLI Client: 대화형 인터페이스
- [x] A2A 프로토콜 기본 구현

### ✅ Phase 2: Baby AI Dashboard (완료)
- [x] Next.js 14 + TypeScript 기반 대시보드
- [x] Supabase 연동 (실시간 데이터)
- [x] BabyStateCard: AI 상태 모니터링
- [x] EmotionRadar: 감정 레이더 차트
- [x] ActivityLog: 활동 로그
- [x] GrowthChart: 성장 차트
- [x] EmotionTimeline: 감정 타임라인
- [x] **BrainVisualization**: 3D 뉴런 네트워크 (Three.js/React Three Fiber)
- [x] **BrainCard**: 뇌 구조 미리보기
- [x] **WorldModelCard**: World Model 카드
- [x] **PredictionCard**: 예측 시각화
- [x] **ImaginationVisualizer**: 상상 시각화
- [x] **CausalGraph**: 인과관계 그래프
- [x] MilestoneTimeline: 마일스톤 타임라인
- [x] PWA 지원 (오프라인, 설치)
- [x] 알림 시스템
- [x] Hydration 에러 수정

### 🔄 Phase 3: 에이전트 확장 (예정)
- [ ] Tester Agent: 생성된 코드 테스트
- [ ] Reviewer Agent: 코드 리뷰

### 🔄 Phase 4: 오케스트레이션 (예정)
- [ ] Orchestrator: 여러 에이전트 조율
- [ ] 작업 파이프라인 구축

### 🔄 Phase 5: 통합 (예정)
- [ ] MCP 서버 연동 (파일 시스템, DB 등)
- [ ] Baby AI 백엔드 연동

---

## 8. 참고 자료

- [A2A 공식 GitHub](https://github.com/google/a2a)
- [A2A Python SDK](https://github.com/a2aproject/a2a-python)
- [A2A 프로토콜 스펙](https://a2a-protocol.org)
- [Anthropic Claude API](https://docs.anthropic.com/)
- [A2A Samples](https://github.com/google-a2a/a2a-samples)

---

## 9. 의존성 목록

```toml
# pyproject.toml에서 발췌
dependencies = [
    "a2a-sdk>=0.3.0",
    "starlette>=0.40.0",
    "sse-starlette>=2.0.0",
    "anthropic>=0.40.0",
    "uvicorn>=0.34.0",
    "click>=8.1.0",
    "httpx>=0.28.0",
    "python-dotenv>=1.0.0",
    "pydantic>=2.10.0",
]
```
