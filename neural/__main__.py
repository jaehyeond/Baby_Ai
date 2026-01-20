"""
Neural A2A Pipeline CLI

사용법 (단일 명령 - Substrate 모드):
    python -m neural "피보나치 함수를 작성해줘"

옵션:
    --iterations N    최대 반복 횟수 (기본: 3)
    --quiet, -q       상세 출력 비활성화
    --a2a             A2A 모드 (외부 에이전트 연결 필요)
    --baby            Baby AI 모드 (발달 AI - 감정/호기심/기억/발달)

Substrate 모드 (기본):
    - 터미널 하나로 모든 에이전트 실행
    - HTTP 통신 없이 직접 함수 호출
    - 진짜 뇌처럼 통합된 시스템

Baby AI 모드 (--baby 플래그):
    - 발달 AI 기능 활성화
    - 감정 시스템 (호기심, 기쁨, 두려움, 놀람, 좌절, 지루함)
    - 호기심 엔진 (ICM 기반 내재적 동기)
    - 기억 시스템 (에피소드/의미/절차)
    - 발달 추적 (NEWBORN → CHILD)
    - 자아 모델 (능력, 선호, 한계)

A2A 모드 (--a2a 플래그):
    - 외부 에이전트 서버 연결
    - 분산 실행 가능
    - 사전에 에이전트 서버 실행 필요:
        python -m agents.coder --port 9999
        python -m agents.tester --port 9998
        python -m agents.reviewer --port 9997
"""

import asyncio
import sys

from .substrate import NeuralSubstrate, SubstrateConfig
from .visualizer import NeuralVisualizer
from .baby import BabySubstrate, BabyConfig


async def run_substrate_mode(
    user_request: str,
    max_iterations: int = 3,
    verbose: bool = True,
) -> None:
    """
    Substrate 모드 실행 (기본)

    모든 에이전트가 단일 프로세스에서 실행됨
    - 터미널 여러 개 필요 없음
    - HTTP 통신 오버헤드 없음
    """
    viz = NeuralVisualizer(use_colors=True)

    viz.print_header("NEURAL SUBSTRATE MODE")
    print("\n  Single-process execution (no separate servers needed)")
    print("  All neurons run in unified substrate")

    substrate = NeuralSubstrate(SubstrateConfig(
        max_iterations=max_iterations,
        verbose=verbose,
    ))

    result = await substrate.process(user_request)

    # 최종 결과 반환 (이미 substrate.process에서 출력됨)
    return result


async def run_baby_mode(
    user_request: str,
    max_iterations: int = 3,
    verbose: bool = True,
) -> None:
    """
    Baby AI 모드 실행

    발달 AI 기능이 통합된 실행:
    - 감정으로 의사결정
    - 호기심으로 탐험
    - 경험에서 학습
    - 스스로 발달
    """
    import os

    # 기억 저장 경로 설정 (프로젝트 루트의 .baby_memory/)
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    memory_path = os.path.join(project_root, ".baby_memory")

    baby = BabySubstrate(BabyConfig(
        max_iterations=max_iterations,
        verbose=verbose,
        memory_path=memory_path,
    ))

    result = await baby.process(user_request)

    # 기억 저장
    baby.save()

    # 세션 종료 시 상태 요약
    if verbose:
        print("\n" + "=" * 60)
        print("  BABY AI SESSION SUMMARY")
        print("=" * 60)
        state = baby.get_state()
        print(f"\n  Experiences this session: {state['experience_count']}")
        print(f"  Development stage: {state['development']['stage']}")
        print(f"  Dominant emotion: {state['emotional_state']['dominant']}")

    return result


async def run_a2a_mode(
    user_request: str,
    max_iterations: int = 3,
    verbose: bool = True,
) -> None:
    """
    A2A 모드 실행 (외부 에이전트)

    사전에 에이전트 서버가 실행되어 있어야 함
    """
    # 기존 pipeline 기반 코드
    from hosts.orchestrator.agent_client import AgentPool
    from .pipeline import create_code_pipeline

    viz = NeuralVisualizer(use_colors=True)

    viz.print_header("NEURAL A2A MODE")
    print("\n  Connecting to external agent servers...")

    pipeline = create_code_pipeline()
    pipeline.config.max_iterations = max_iterations
    pipeline.config.verbose = verbose

    async with AgentPool() as pool:
        try:
            viz.print_subheader("CONNECTING TO AGENTS")

            agents = [
                ("coder", "http://localhost:9999"),
                ("tester", "http://localhost:9998"),
                ("reviewer", "http://localhost:9997"),
            ]

            connected_count = 0
            for agent_id, url in agents:
                try:
                    card = await pool.register(agent_id, url)
                    print(f"  [OK] {card.name} ({agent_id}) @ {url}")
                    connected_count += 1
                except Exception as e:
                    print(f"  [X] {agent_id} failed: {e}")

            if connected_count < len(agents):
                print(f"\n  [!] Warning: Only {connected_count}/{len(agents)} agents connected")

            if connected_count == 0:
                print("\n  [ERROR] No agents connected!")
                print("  Make sure to start agent servers first:")
                print("    python -m agents.coder --port 9999")
                print("    python -m agents.tester --port 9998")
                print("    python -m agents.reviewer --port 9997")
                return

            result = await pipeline.forward(user_request, pool)

        except Exception as e:
            print(f"\n[ERROR] Pipeline error: {e}")
            raise


def main():
    """CLI 진입점"""
    if len(sys.argv) < 2:
        print(__doc__)
        print("\n사용 예:")
        print('  python -m neural "피보나치 함수를 작성해줘"')
        print('  python -m neural "퀵소트 알고리즘을 구현해줘" --iterations 5')
        print('  python -m neural "버블소트 구현" --baby   # Baby AI 모드 (발달 AI)')
        print('  python -m neural "버블소트 구현" --a2a    # 외부 에이전트 사용')
        sys.exit(1)

    user_request = sys.argv[1]
    max_iterations = 3
    verbose = True
    use_a2a = False
    use_baby = False

    # --iterations 옵션 파싱
    if "--iterations" in sys.argv:
        idx = sys.argv.index("--iterations")
        if idx + 1 < len(sys.argv):
            try:
                max_iterations = int(sys.argv[idx + 1])
            except ValueError:
                print("Error: --iterations must be an integer")
                sys.exit(1)

    # --quiet 옵션
    if "--quiet" in sys.argv or "-q" in sys.argv:
        verbose = False

    # --a2a 옵션 (외부 에이전트 모드)
    if "--a2a" in sys.argv:
        use_a2a = True

    # --baby 옵션 (Baby AI 모드)
    if "--baby" in sys.argv:
        use_baby = True

    # 실행
    if use_baby:
        asyncio.run(run_baby_mode(user_request, max_iterations, verbose))
    elif use_a2a:
        asyncio.run(run_a2a_mode(user_request, max_iterations, verbose))
    else:
        asyncio.run(run_substrate_mode(user_request, max_iterations, verbose))


if __name__ == "__main__":
    main()
