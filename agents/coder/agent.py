"""Claude 기반 코드 생성 에이전트 핵심 로직"""

from typing import AsyncIterator, Dict, Any

from common.claude_runtime import ClaudeRuntimeError, ask


class CoderAgent:
    """Claude Agent SDK(구독 할당량)로 Python 코드를 생성하는 에이전트"""

    SYSTEM_PROMPT = """당신은 Python 코드 생성 전문가입니다.

역할:
- 사용자의 요청에 따라 Python 코드를 작성합니다.
- 코드는 깔끔하고 읽기 쉬우며, 적절한 주석을 포함합니다.
- 요청이 불명확하면 명확히 해달라고 요청하세요.

응답 형식:
- 코드만 반환하세요 (설명은 주석으로).
- 마크다운 코드 블록(```)은 사용하지 마세요.
- 바로 실행 가능한 Python 코드를 제공하세요.
"""

    SUPPORTED_CONTENT_TYPES = ["text", "text/plain"]

    def __init__(self):
        # API 키가 필요 없다 — Claude Agent SDK가 구독 인증(OAuth)으로 돈다.
        pass

    async def generate(self, query: str) -> str:
        """
        사용자 요청에 따라 코드 생성

        Args:
            query: 사용자의 코드 생성 요청

        Returns:
            생성된 Python 코드
        """
        return await ask(self.SYSTEM_PROMPT, query)

    async def stream(self, query: str) -> AsyncIterator[Dict[str, Any]]:
        """
        스트리밍 방식으로 코드 생성

        Args:
            query: 사용자의 코드 생성 요청

        Yields:
            상태 업데이트 딕셔너리
        """
        # 작업 시작 알림
        yield {
            "is_task_complete": False,
            "require_user_input": False,
            "content": "코드 생성 중...",
        }

        # Claude 호출
        try:
            generated_code = await self.generate(query)

            # 완료
            yield {
                "is_task_complete": True,
                "require_user_input": False,
                "content": generated_code,
            }
        except ClaudeRuntimeError as e:
            yield {
                "is_task_complete": False,
                "require_user_input": True,
                "content": f"코드 생성 실패: {str(e)}",
            }
