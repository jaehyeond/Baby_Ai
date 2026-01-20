"""Tester Agent 서버 진입점"""

import logging
import sys

import click
import uvicorn

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill

from common.config import Config
from .agent import TesterAgent
from .agent_executor import TesterAgentExecutor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@click.command()
@click.option("--host", default="localhost", help="서버 호스트")
@click.option("--port", default=9998, help="서버 포트")
def main(host: str, port: int):
    """코드 테스트 Agent 서버를 시작합니다."""
    try:
        # 환경변수 검증
        Config.validate()
        logger.info("환경변수 검증 완료")

        # Agent Card 정의
        agent_card = AgentCard(
            name="Claude Tester Agent",
            description="Claude 기반 Python 코드 테스트 에이전트",
            url=f"http://{host}:{port}/",
            version="1.0.0",
            capabilities=AgentCapabilities(streaming=True),
            skills=[
                AgentSkill(
                    id="test_python",
                    name="Python Code Tester",
                    description="Python 코드를 실행하고 테스트합니다",
                    tags=["python", "testing", "code-analysis"],
                    examples=[
                        "이 코드를 테스트해줘",
                        "코드가 잘 작동하는지 확인해줘",
                        "버그가 있는지 분석해줘",
                    ],
                )
            ],
            default_input_modes=TesterAgent.SUPPORTED_CONTENT_TYPES,
            default_output_modes=TesterAgent.SUPPORTED_CONTENT_TYPES,
        )

        # Request Handler 구성
        request_handler = DefaultRequestHandler(
            agent_executor=TesterAgentExecutor(),
            task_store=InMemoryTaskStore(),
        )

        # A2A 서버 생성
        server = A2AStarletteApplication(
            agent_card=agent_card,
            http_handler=request_handler,
        )

        logger.info(f"Tester Agent 서버 시작: http://{host}:{port}")
        logger.info(f"Agent Card: http://{host}:{port}/.well-known/agent-card.json")

        # 서버 실행
        uvicorn.run(server.build(), host=host, port=port)

    except ValueError as e:
        logger.error(f"설정 오류: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"서버 시작 실패: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
