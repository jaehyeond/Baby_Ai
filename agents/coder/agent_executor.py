"""A2A AgentExecutor 구현 - Coder Agent"""

import logging

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import (
    InternalError,
    Part,
    TaskState,
    TextPart,
    UnsupportedOperationError,
)
from a2a.utils import new_agent_text_message, new_task
from a2a.utils.errors import ServerError

from .agent import CoderAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CoderAgentExecutor(AgentExecutor):
    """Claude 기반 코드 생성 AgentExecutor

    A2A 프로토콜에 맞게 CoderAgent를 래핑합니다.
    """

    def __init__(self):
        self.agent = CoderAgent()

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        """
        A2A 요청을 처리하고 코드를 생성합니다.

        Args:
            context: 요청 컨텍스트 (메시지, 태스크 정보 등)
            event_queue: 이벤트 전송 큐
        """
        # 사용자 입력 추출
        query = context.get_user_input()
        if not query:
            raise ServerError(error=InternalError(message="입력이 없습니다"))

        # 태스크 생성 또는 기존 태스크 사용
        task = context.current_task
        if not task:
            task = new_task(context.message)
            await event_queue.enqueue_event(task)

        updater = TaskUpdater(event_queue, task.id, task.context_id)

        try:
            # 스트리밍으로 코드 생성
            async for item in self.agent.stream(query):
                is_complete = item["is_task_complete"]
                need_input = item["require_user_input"]
                content = item["content"]

                if not is_complete and not need_input:
                    # 작업 중 상태 업데이트
                    await updater.update_status(
                        TaskState.working,
                        new_agent_text_message(content, task.context_id, task.id),
                    )
                elif need_input:
                    # 추가 입력 필요
                    await updater.update_status(
                        TaskState.input_required,
                        new_agent_text_message(content, task.context_id, task.id),
                        final=True,
                    )
                    break
                else:
                    # 완료 - 결과물(Artifact) 추가
                    await updater.add_artifact(
                        [Part(root=TextPart(text=content))],
                        name="generated_code",
                    )
                    await updater.complete()
                    break

        except Exception as e:
            logger.error(f"코드 생성 중 오류: {e}")
            raise ServerError(error=InternalError(message=str(e))) from e

    async def cancel(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        """태스크 취소 처리"""
        raise ServerError(error=UnsupportedOperationError())
