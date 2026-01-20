"""코드 리뷰 에이전트 핵심 로직"""

from typing import AsyncIterator, Dict, Any
import anthropic

from common.config import Config


class ReviewerAgent:
    """Python 코드를 리뷰하고 개선점을 제안하는 에이전트"""

    SYSTEM_PROMPT = """당신은 시니어 Python 개발자이자 코드 리뷰 전문가입니다.

역할:
- 코드의 품질, 가독성, 유지보수성을 평가합니다.
- 잠재적인 버그와 보안 취약점을 식별합니다.
- PEP 8 스타일 가이드 준수 여부를 확인합니다.
- 성능 개선 포인트를 제안합니다.

리뷰 기준:
1. 코드 품질 (Clean Code 원칙)
2. 보안 (SQL Injection, XSS 등 취약점)
3. 성능 (시간/공간 복잡도)
4. 스타일 (PEP 8, 명명 규칙)
5. 테스트 용이성

응답 형식:
- 점수: 1-10 (10이 최고)
- 장점: 좋은 점들
- 개선점: 수정이 필요한 부분
- 제안: 구체적인 개선 코드 예시
"""

    SUPPORTED_CONTENT_TYPES = ["text", "text/plain"]

    def __init__(self):
        Config.validate()
        self.client = anthropic.Anthropic(api_key=Config.ANTHROPIC_API_KEY)

    async def review(self, code: str) -> str:
        """
        코드 리뷰 수행

        Args:
            code: 리뷰할 Python 코드

        Returns:
            리뷰 결과
        """
        review_prompt = f"""다음 Python 코드를 리뷰해주세요.

```python
{code}
```

위 기준에 따라 상세한 코드 리뷰를 작성해주세요.
"""

        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=3000,
            system=self.SYSTEM_PROMPT,
            messages=[{"role": "user", "content": review_prompt}],
        )

        return response.content[0].text

    async def stream(self, code: str) -> AsyncIterator[Dict[str, Any]]:
        """
        스트리밍 방식으로 코드 리뷰

        Args:
            code: 리뷰할 Python 코드

        Yields:
            상태 업데이트 딕셔너리
        """
        # 작업 시작 알림
        yield {
            "is_task_complete": False,
            "require_user_input": False,
            "content": "코드 리뷰 분석 중...",
        }

        try:
            # 코드 리뷰
            result = await self.review(code)

            # 완료
            yield {
                "is_task_complete": True,
                "require_user_input": False,
                "content": result,
            }
        except anthropic.APIError as e:
            # API 오류
            yield {
                "is_task_complete": False,
                "require_user_input": True,
                "content": f"리뷰 실패: {str(e)}",
            }
