"""Reviewer Agent 서버 진입점"""

import logging
import sys

import click
import uvicorn

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill

from common.config import Config
from .agent import ReviewerAgent
from .agent_executor import ReviewerAgentExecutor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@click.command()
@click.option("--host", default="localhost", help="서버 호스트")
@click.option("--port", default=9996, help="서버 포트")
def main(host: str, port: int):
    """코드 리뷰 Agent 서버를 시작합니다."""
    try:
        # 환경변수 검증
        Config.validate()
        logger.info("환경변수 검증 완료")

        # Agent Card 정의
        agent_card = AgentCard(
            name="Claude Reviewer Agent",
            description="Claude 기반 Python 코드 리뷰 에이전트",
            url=f"http://{host}:{port}/",
            version="1.0.0",
            capabilities=AgentCapabilities(streaming=True),
            skills=[
                AgentSkill(
                    id="review_python",
                    name="Python Code Reviewer",
                    description="Python 코드의 품질, 보안, 스타일을 리뷰합니다",
                    tags=["python", "review", "code-quality", "security"],
                    examples=[
                        "이 코드를 리뷰해줘",
                        "코드 품질을 평가해줘",
                        "보안 취약점이 있는지 확인해줘",
                    ],
                )
            ],
            default_input_modes=ReviewerAgent.SUPPORTED_CONTENT_TYPES,
            default_output_modes=ReviewerAgent.SUPPORTED_CONTENT_TYPES,
        )

        # Request Handler 구성
        request_handler = DefaultRequestHandler(
            agent_executor=ReviewerAgentExecutor(),
            task_store=InMemoryTaskStore(),
        )

        # A2A 서버 생성
        server = A2AStarletteApplication(
            agent_card=agent_card,
            http_handler=request_handler,
        )

        logger.info(f"Reviewer Agent 서버 시작: http://{host}:{port}")
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
