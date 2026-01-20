# Our A2A Project

Claude 기반 A2A(Agent-to-Agent) 멀티에이전트 시스템

## 빠른 시작

### 1. 환경 설정

```bash
cd e:\A2A\our-a2a-project

# 가상환경 생성 및 활성화
python -m venv .venv
.\.venv\Scripts\activate  # Windows

# 의존성 설치
pip install -e .

# 환경변수 설정
copy .env.example .env
# .env 파일을 열어 ANTHROPIC_API_KEY 입력
```

### 2. Coder Agent 실행 (Terminal A)

```bash
python -m agents.coder --port 9999
```

### 3. CLI Client 실행 (Terminal B)

```bash
python -m hosts.cli --agent http://localhost:9999
```

### 4. 대화 시작

```
입력> 피보나치 함수 작성해줘
[결과 출력]

입력> :q  (종료)
```

## 프로젝트 구조

```
our-a2a-project/
├── agents/           # A2A 서버 에이전트
│   └── coder/        # 코드 생성 에이전트
├── hosts/            # A2A 클라이언트
│   └── cli/          # CLI 클라이언트
└── common/           # 공통 유틸리티
```

## 라이선스

MIT
