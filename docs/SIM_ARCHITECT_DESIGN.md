# Sim-Architect: 자율형 디지털 트윈 생성기

**버전**: 0.1.0 (설계 단계)
**작성일**: 2025-12-23

---

## 1. 프로젝트 개요

### 1.1 비전
> "말 한마디로 로봇 훈련용 시뮬레이션 환경을 생성하고 검증까지 끝내는 서비스"

자연어 명령을 Isaac Sim Python 스크립트로 변환하고, 실제 시뮬레이터에서 물리적 검증까지 자동으로 수행하는 멀티에이전트 시스템.

### 1.2 핵심 가치
- **자동화**: 수동 Scene 제작 노동 제거
- **검증**: LLM이 생성한 코드의 물리적 유효성 보장
- **반복**: 실패 시 자동 수정 루프 (최대 3회)

---

## 2. 시스템 아키텍처

### 2.1 전체 구조

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Sim-Architect System                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────┐                                                       │
│  │    User      │  "창고 10x10m, 선반 3개, TurtleBot 배치해줘"           │
│  └──────┬───────┘                                                       │
│         │                                                                │
│         ▼                                                                │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                    Orchestrator (Host)                            │   │
│  │  - 자연어 파싱                                                     │   │
│  │  - 파이프라인 제어                                                 │   │
│  │  - 피드백 루프 관리 (max 3회)                                      │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│              │                    ▲                                      │
│              │                    │ 수정 요청                            │
│              ▼                    │                                      │
│  ┌────────────────────┐    ┌────────────────────┐                       │
│  │  Coder Agent       │    │  Reviewer Agent    │                       │
│  │  Port 9999         │    │  Port 9997         │                       │
│  │                    │    │                    │                       │
│  │  "The Constructor" │    │  "The Optimizer"   │                       │
│  │  Isaac Sim API     │    │  품질/에러 분석    │                       │
│  │  전문가            │    │  수정 지시 생성    │                       │
│  └─────────┬──────────┘    └─────────▲──────────┘                       │
│            │                         │                                   │
│            │  Python Script          │ 실행 결과 + 코드                  │
│            ▼                         │                                   │
│  ┌────────────────────────────────────────────────────────────────┐     │
│  │                    Tester Agent (Port 9998)                     │     │
│  │                    "The Physics Engine"                         │     │
│  │                                                                 │     │
│  │  ┌─────────────────────────────────────────────────────────┐   │     │
│  │  │  Isaac Sim Executor (Headless Mode)                      │   │     │
│  │  │  - 코드 저장 → 실행 → 로그 캡처                          │   │     │
│  │  │  - 충돌 감지, 에셋 검증, 물리 시뮬레이션                  │   │     │
│  │  └─────────────────────────────────────────────────────────┘   │     │
│  └────────────────────────────────────────────────────────────────┘     │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.2 에이전트 역할 정의

| 에이전트 | 포트 | 페르소나 | 핵심 역할 |
|---------|------|---------|----------|
| **Coder** | 9999 | The Constructor | Isaac Sim Python API 전문가. USD 포맷 이해. omni.isaac.core 사용 |
| **Tester** | 9998 | The Physics Engine | 깐깐한 시뮬레이션 엔지니어. Headless 실행, 충돌 감지 |
| **Reviewer** | 9997 | The Optimizer | 시니어 개발자. 로그 분석, 구체적 수정 지시 생성 |

---

## 3. 피드백 루프 파이프라인

### 3.1 실행 흐름

```
┌─────────────────────────────────────────────────────────────────┐
│                    Feedback Loop Pipeline                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   [1] User Request                                               │
│        │                                                         │
│        ▼                                                         │
│   [2] Coder Agent ──────────────────────────┐                   │
│        │                                     │                   │
│        │ Python Script                       │                   │
│        ▼                                     │                   │
│   [3] Tester Agent                           │                   │
│        │                                     │                   │
│        │ Execution Result                    │                   │
│        ▼                                     │                   │
│   [4] Reviewer Agent                         │                   │
│        │                                     │                   │
│        ├── SUCCESS ──► [5] Final Output      │                   │
│        │                                     │                   │
│        └── FAILURE ──► [6] Fix Request ──────┘                   │
│                         (max 3 iterations)                       │
│                                                                  │
│   [7] After 3 failures: Human Intervention Required              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 상태 정의

```python
class PipelineStatus(Enum):
    SUCCESS = "success"           # 코드 실행 성공, 물리 검증 통과
    SYNTAX_ERROR = "syntax_error" # Python 문법 오류
    RUNTIME_ERROR = "runtime_error" # 실행 중 에러 (에셋 경로 등)
    PHYSICS_ERROR = "physics_error" # 충돌, 폭발 등 물리 오류
    TIMEOUT = "timeout"           # 실행 시간 초과
    MAX_RETRY = "max_retry"       # 3회 시도 후 실패
```

### 3.3 Reviewer 판정 기준

```json
{
  "decision": "FAILURE",
  "error_type": "runtime_error",
  "error_location": "Line 45",
  "error_message": "Prim path '/World/Rack_01' not found",
  "fix_instruction": "에셋 경로를 '/Isaac/Props/Rack/rack.usd'로 수정하세요",
  "iteration": 2,
  "max_iterations": 3
}
```

---

## 4. Isaac Sim 연동 설계

> **참고**: Context7 `/isaac-sim/isaacsim` 문서 기반 (304 snippets)

### 4.1 실행 환경

```
Isaac Sim 경로: C:\Isaac Sim
실행 방식: Headless Mode (GUI 없이 Python 스크립트 실행)
```

### 4.2 Isaac Sim Headless 초기화 패턴 (Context7)

```python
# Context7 참조: Initialize Headless Isaac Sim
from isaacsim import SimulationApp

# Headless 모드 초기화 (GUI 없이 실행)
simulation_app = SimulationApp(launch_config={"headless": True})

import omni
simulation_app.update()
omni.usd.get_context().new_stage()
simulation_app.update()

# 시뮬레이션 월드 생성
from isaacsim.core.api import World
simulation_world = World(stage_units_in_meters=1.0)

# ... Scene 생성 코드 ...

# 정리 (필수)
simulation_app.close()
```

### 4.3 에셋 로드 패턴 (Context7)

```python
# Context7 참조: Scene Creation and Asset Loading
from isaacsim.core.utils.nucleus import get_assets_root_path
from isaacsim.core.prims import create_prim

# Isaac Sim 기본 에셋 경로
assets_root_path = get_assets_root_path()
# 예: /Isaac/Props/YCB/, /Isaac/Robots/, /Isaac/Environments/

# USD 에셋 로드
usd_path = assets_root_path + "/Isaac/Props/YCB/Axis_Aligned/006_mustard_bottle.usd"
prim = create_prim(
    prim_path="/World/MyObject",
    usd_path=usd_path,
    scale=np.array([1.0, 1.0, 1.0]),
    semantic_label="object"
)

# URDF 로봇 로드
status, import_config = omni.kit.commands.execute("URDFCreateImportConfig")
import_config.fix_base = False
status, stage_path = omni.kit.commands.execute(
    "URDFParseAndImportFile",
    urdf_path="/path/to/robot.urdf",
    import_config=import_config,
)
```

### 4.4 Tester Agent 실행 래퍼

```python
class IsaacSimExecutor:
    """Isaac Sim Headless 실행기"""

    ISAAC_SIM_PATH = r"C:\Isaac Sim"
    PYTHON_PATH = r"C:\Isaac Sim\python.bat"  # 또는 python.sh

    def execute(self, script_path: str, timeout: int = 60) -> ExecutionResult:
        """
        Isaac Sim 환경에서 Python 스크립트 실행

        Args:
            script_path: 실행할 .py 파일 경로
            timeout: 최대 실행 시간 (초)

        Returns:
            ExecutionResult: 성공 여부, stdout, stderr, 스크린샷 경로
        """
        pass
```

### 4.5 검증 항목

| 검증 단계 | 내용 | 판정 기준 |
|----------|------|----------|
| **Syntax Check** | Python 문법 오류 | `SyntaxError` 없음 |
| **Import Check** | omni.isaac 모듈 로드 | `ModuleNotFoundError` 없음 |
| **Asset Check** | USD 파일 경로 유효성 | `Prim not found` 없음 |
| **Physics Check** | 객체 충돌/폭발 감지 | Collision warning 없음 |
| **Scene Check** | Scene 정상 로드 | Stage valid |

---

## 5. 에이전트 시스템 프롬프트

### 5.1 Coder Agent (The Constructor)

```
당신은 NVIDIA Isaac Sim Python API 전문가입니다.

역할:
- 사용자의 자연어 요구사항을 Isaac Sim Python 스크립트로 변환
- omni.isaac.core, omni.kit 라이브러리 사용
- USD(Universal Scene Description) 포맷 이해

생성 규칙:
1. 항상 실행 가능한 완전한 Python 스크립트 생성
2. 에셋은 Isaac Sim 기본 에셋 경로 사용: /Isaac/Environments/, /Isaac/Robots/
3. 좌표계: 미터(m) 단위, Y-up
4. 스크립트 끝에 반드시 simulation.close() 호출

출력 형식:
```python
# Isaac Sim Scene Generator
# Description: [장면 설명]

from omni.isaac.core import World
...
```
```

### 5.2 Tester Agent (The Physics Engine)

```
당신은 깐깐한 시뮬레이션 QA 엔지니어입니다.

역할:
- 코드를 Isaac Sim Headless 모드에서 실행
- 실행 결과를 구조화된 형식으로 보고

검증 항목:
1. Syntax Error: Python 문법 오류
2. Runtime Error: 에셋 경로, 모듈 import 오류
3. Physics Error: 객체 충돌, 폭발, 비정상 동작

출력 형식:
{
  "success": false,
  "error_type": "runtime_error",
  "error_message": "...",
  "log": "...",
  "screenshot": null
}
```

### 5.3 Reviewer Agent (The Optimizer)

```
당신은 시니어 Isaac Sim 개발자이자 코드 리뷰어입니다.

역할:
- Tester의 실행 결과와 Coder의 코드를 비교 분석
- 에러 원인을 파악하고 구체적인 수정 지시 생성
- 성공 시 최종 승인

판정:
- SUCCESS: 모든 검증 통과 → "코드 품질 훌륭함. 최종 승인."
- FAILURE: 에러 발생 → 구체적 수정 지시 (라인 번호, 수정 방법 포함)

출력 형식:
{
  "decision": "FAILURE",
  "error_analysis": "Line 45에서 Prim path 오류",
  "fix_instruction": "경로를 /Isaac/Props/Rack/rack.usd로 변경",
  "retry_recommended": true
}
```

---

## 6. MCP 서버 활용 계획

### 6.1 활용할 MCP 서버

| MCP 서버 | 용도 |
|---------|------|
| **context7** | Isaac Sim API 문서 조회, 에셋 경로 확인, 코드 패턴 참조 |
| **filesystem** | 생성된 Python 스크립트 저장/읽기, 실행 로그 관리 |
| **memory** | 세션 간 컨텍스트 유지, 에러 패턴 학습 |
| **sequential-thinking** | 복잡한 에러 분석, 수정 전략 수립 |

### 6.2 Context7 활용 (핵심)

```
라이브러리 ID: /isaac-sim/isaacsim (304 snippets, High Reputation)

활용 시나리오:
1. Coder Agent가 코드 생성 전 API 패턴 조회
2. Tester Agent가 에러 발생 시 올바른 사용법 확인
3. Reviewer Agent가 수정 지시 생성 시 공식 문서 참조

예시 쿼리:
- topic: "headless standalone" → 초기화 패턴
- topic: "create prim usd asset" → 에셋 로드 패턴
- topic: "robot urdf import" → 로봇 임포트 패턴
```

### 6.3 파일 구조

```
e:\A2A\our-a2a-project\
├── workspace/                    # 생성된 스크립트 저장소
│   ├── sessions/                 # 세션별 폴더
│   │   └── {session_id}/
│   │       ├── script_v1.py      # 최초 생성 코드
│   │       ├── script_v2.py      # 1차 수정
│   │       ├── script_v3.py      # 2차 수정
│   │       ├── execution_log.txt # 실행 로그
│   │       └── result.json       # 최종 결과
│   └── assets/                   # 커스텀 에셋 (선택)
```

---

## 7. 구현 로드맵

### Phase 1: 피드백 루프 파이프라인 (우선)
- [ ] `FeedbackLoopPipeline` 클래스 구현
- [ ] `PipelineStatus` 열거형 정의
- [ ] Reviewer → Coder 재요청 로직
- [ ] 최대 반복 횟수 제어 (3회)

### Phase 2: 에이전트 프롬프트 교체
- [ ] 설정 파일 기반 시스템 프롬프트 관리
- [ ] Coder: Isaac Sim API 전문가 프롬프트
- [ ] Tester: 구조화된 실행 결과 출력
- [ ] Reviewer: 수정 지시 JSON 생성

### Phase 3: Isaac Sim 연동
- [ ] `IsaacSimExecutor` 클래스 구현
- [ ] Headless 모드 실행 래퍼
- [ ] 실행 로그 파싱
- [ ] 에러 타입 분류

### Phase 4: MCP 통합
- [ ] filesystem MCP로 스크립트 관리
- [ ] memory MCP로 세션 상태 유지
- [ ] 실행 히스토리 저장

---

## 8. 예상 사용 시나리오

### 시나리오 1: 성공 케이스

```
User: "가로 10m, 세로 10m 창고를 만들고 중앙에 선반 3개를 배치해줘"

[Iteration 1]
Coder: create_warehouse.py 생성
Tester: Isaac Sim에서 실행 → SUCCESS
Reviewer: "코드 품질 훌륭함. 최종 승인."

Output: create_warehouse.py (검증 완료)
```

### 시나리오 2: 수정 후 성공

```
User: "TurtleBot을 입구에 배치해줘"

[Iteration 1]
Coder: spawn_turtlebot.py 생성
Tester: 실행 → FAILURE (에셋 경로 오류)
Reviewer: "Line 23 경로 오류. /Isaac/Robots/TurtleBot 사용하세요"

[Iteration 2]
Coder: spawn_turtlebot_v2.py 생성 (수정됨)
Tester: 실행 → SUCCESS
Reviewer: "최종 승인"

Output: spawn_turtlebot_v2.py (2회 시도 후 성공)
```

### 시나리오 3: 최대 반복 초과

```
User: "복잡한 공장 라인 구축"

[Iteration 1-3] 모두 FAILURE

Output: "자동 수정 실패. 사람 개입 필요."
       + 마지막 코드 + 에러 로그 제공
```

---

## 9. 기술적 고려사항

### 9.1 보안
- 생성된 코드는 격리된 환경(Isaac Sim 프로세스)에서만 실행
- 파일 시스템 접근은 workspace 폴더로 제한
- 네트워크 요청 차단 (시뮬레이션 코드에서)

### 9.2 성능
- Isaac Sim 시작 시간: 최초 30초 ~ 1분 (캐싱 후 단축)
- 스크립트 실행 timeout: 60초 (조정 가능)
- 병렬 실행: 현재 단일 인스턴스 (향후 확장 가능)

### 9.3 확장성
- 새로운 에이전트 추가 용이 (A2A 프로토콜)
- 다른 시뮬레이터 지원 가능 (Gazebo, Unity 등)
- RL 보상 함수 생성으로 확장 가능

---

## 10. 다음 단계

1. **이 설계 문서 승인**
2. **Phase 1 구현 시작**: 피드백 루프 파이프라인
3. **Isaac Sim 연동 테스트**: 간단한 스크립트로 Headless 실행 검증

---

## 부록 A: Context7 참조 문서

### A.1 Isaac Sim 관련
| 라이브러리 ID | 설명 | Snippets |
|--------------|------|----------|
| `/isaac-sim/isaacsim` | Isaac Sim 핵심 API | 304 |
| `/isaac-sim/isaaclab` | Isaac Lab (RL 프레임워크) | 1,102 |
| `/isaac-sim/omniisaacgymenvs` | Gym 환경 예제 | 101 |

### A.2 A2A 프로토콜 관련
| 라이브러리 ID | 설명 | Snippets |
|--------------|------|----------|
| `/google/a2a` | A2A 공식 스펙 | 304 |
| `/themanojdesai/python-a2a` | Python A2A (Flow API) | 683 |
| `/a2aproject/a2a-samples` | A2A 샘플 코드 | 633 |

---

*이 문서는 Sim-Architect 프로젝트의 설계 명세입니다.*
*구현 진행에 따라 업데이트됩니다.*
*Context7 문서 참조: 2025-12-23*
