"""Orchestrator 메인 진입점"""

import asyncio
import sys
import io

# Windows 콘솔 인코딩 문제 해결
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import click

from .agent_client import AgentPool
from .pipeline import CodePipeline


# 기본 에이전트 URL
DEFAULT_AGENTS = {
    "coder": "http://localhost:9999",
    "tester": "http://localhost:9998",
    "reviewer": "http://localhost:9997",
}


async def run_orchestrator(
    request: str,
    coder_url: str,
    tester_url: str,
    reviewer_url: str,
):
    """오케스트레이터 실행"""
    print("\n" + "=" * 60)
    print("       A2A 멀티에이전트 오케스트레이터")
    print("=" * 60)
    print(f"\n[요청] {request}\n")

    async with AgentPool() as pool:
        # 에이전트 등록
        print("[초기화] 에이전트 연결 중...")

        try:
            card = await pool.register("coder", coder_url)
            print(f"  - Coder: {card.name} ({coder_url})")
        except Exception as e:
            print(f"  - Coder 연결 실패: {e}")
            print("\n[오류] Coder Agent가 실행 중인지 확인하세요.")
            print(f"  실행 명령: python -m agents.coder --port 9999")
            return

        try:
            card = await pool.register("tester", tester_url)
            print(f"  - Tester: {card.name} ({tester_url})")
        except Exception as e:
            print(f"  - Tester 연결 실패: {e}")
            print("\n[오류] Tester Agent가 실행 중인지 확인하세요.")
            print(f"  실행 명령: python -m agents.tester --port 9998")
            return

        try:
            card = await pool.register("reviewer", reviewer_url)
            print(f"  - Reviewer: {card.name} ({reviewer_url})")
        except Exception as e:
            print(f"  - Reviewer 연결 실패: {e}")
            print("\n[오류] Reviewer Agent가 실행 중인지 확인하세요.")
            print(f"  실행 명령: python -m agents.reviewer --port 9997")
            return

        print("\n[준비 완료] 파이프라인 시작...")

        # 파이프라인 실행
        pipeline = CodePipeline(pool)
        await pipeline.run(request)

        # 결과 보고서 출력
        print(pipeline.format_report())


@click.command()
@click.argument("request", required=False)
@click.option("--coder", default=DEFAULT_AGENTS["coder"], help="Coder Agent URL")
@click.option("--tester", default=DEFAULT_AGENTS["tester"], help="Tester Agent URL")
@click.option("--reviewer", default=DEFAULT_AGENTS["reviewer"], help="Reviewer Agent URL")
@click.option("--interactive", "-i", is_flag=True, help="대화형 모드")
def main(
    request: str,
    coder: str,
    tester: str,
    reviewer: str,
    interactive: bool,
):
    """
    멀티에이전트 오케스트레이터

    여러 A2A 에이전트를 조율하여 코드 생성 → 테스트 → 리뷰 파이프라인을 실행합니다.

    Example:
        python -m hosts.orchestrator "피보나치 함수를 작성해줘"
        python -m hosts.orchestrator -i  # 대화형 모드
    """
    if interactive:
        # 대화형 모드
        print("\n" + "=" * 60)
        print("       A2A 멀티에이전트 오케스트레이터 (대화형)")
        print("=" * 60)
        print("종료하려면 ':q' 또는 'exit'를 입력하세요.\n")

        while True:
            try:
                user_input = input("요청> ").strip()
                if not user_input:
                    continue
                if user_input.lower() in [":q", "quit", "exit"]:
                    print("종료합니다.")
                    break
                asyncio.run(run_orchestrator(user_input, coder, tester, reviewer))
            except KeyboardInterrupt:
                print("\n중단됨.")
                break
            except Exception as e:
                print(f"오류: {e}")
    else:
        if not request:
            print("사용법: python -m hosts.orchestrator <request>")
            print("예시: python -m hosts.orchestrator \"피보나치 함수를 작성해줘\"")
            print("\n대화형 모드: python -m hosts.orchestrator -i")
            sys.exit(1)

        try:
            asyncio.run(run_orchestrator(request, coder, tester, reviewer))
        except KeyboardInterrupt:
            print("\n중단됨.")
        except Exception as e:
            print(f"오류: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()
