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
- **ANTHROPIC_API_KEY**: `.env` 파일에 설정 필수

## Task Tracking

작업 진행 시 항상 `Task.md` 파일을 확인하고 업데이트하세요.
