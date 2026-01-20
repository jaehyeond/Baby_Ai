"""코드 테스트 에이전트 핵심 로직"""

import subprocess
import sys
import tempfile
import os
from typing import AsyncIterator, Dict, Any
import anthropic

from common.config import Config


class TesterAgent:
    """Python 코드를 실행하고 테스트하는 에이전트"""

    SYSTEM_PROMPT = """당신은 Python 코드 테스트 전문가입니다.

역할:
- 주어진 Python 코드를 분석하고 테스트합니다.
- 코드의 문법 오류, 런타임 오류를 감지합니다.
- 간단한 테스트 케이스를 생성하고 실행합니다.

응답 형식:
- 테스트 결과를 명확하게 보고합니다.
- 발견된 문제점과 수정 제안을 포함합니다.
- 코드가 정상이면 "테스트 통과"라고 표시합니다.
"""

    SUPPORTED_CONTENT_TYPES = ["text", "text/plain"]

    def __init__(self):
        Config.validate()
        self.client = anthropic.Anthropic(api_key=Config.ANTHROPIC_API_KEY)

    def _execute_code(self, code: str) -> Dict[str, Any]:
        """
        코드를 임시 파일에 저장하고 실행

        Args:
            code: 실행할 Python 코드

        Returns:
            실행 결과 (success, output, error)
        """
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.py',
            delete=False,
            encoding='utf-8'
        ) as f:
            f.write(code)
            temp_path = f.name

        try:
            result = subprocess.run(
                [sys.executable, temp_path],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=tempfile.gettempdir()
            )
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr,
                "returncode": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "output": "",
                "error": "실행 시간 초과 (10초)",
                "returncode": -1
            }
        except Exception as e:
            return {
                "success": False,
                "output": "",
                "error": str(e),
                "returncode": -1
            }
        finally:
            try:
                os.unlink(temp_path)
            except:
                pass

    async def analyze_and_test(self, code: str) -> str:
        """
        Claude를 사용하여 코드 분석 및 테스트 케이스 생성

        Args:
            code: 테스트할 Python 코드

        Returns:
            분석 및 테스트 결과
        """
        # 먼저 코드 실행 테스트
        exec_result = self._execute_code(code)

        # Claude에게 분석 요청
        analysis_prompt = f"""다음 Python 코드를 분석하고 테스트해주세요.

## 코드:
```python
{code}
```

## 실행 결과:
- 성공 여부: {exec_result['success']}
- 출력: {exec_result['output'] or '(없음)'}
- 에러: {exec_result['error'] or '(없음)'}

## 요청:
1. 코드의 기능을 설명해주세요.
2. 발견된 문제점이 있다면 알려주세요.
3. 테스트 결과를 요약해주세요.
4. 개선 제안이 있다면 알려주세요.

간결하게 답변해주세요.
"""

        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
            system=self.SYSTEM_PROMPT,
            messages=[{"role": "user", "content": analysis_prompt}],
        )

        return response.content[0].text

    async def stream(self, code: str) -> AsyncIterator[Dict[str, Any]]:
        """
        스트리밍 방식으로 코드 테스트

        Args:
            code: 테스트할 Python 코드

        Yields:
            상태 업데이트 딕셔너리
        """
        # 작업 시작 알림
        yield {
            "is_task_complete": False,
            "require_user_input": False,
            "content": "코드 분석 및 테스트 중...",
        }

        try:
            # 코드 분석 및 테스트
            result = await self.analyze_and_test(code)

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
                "content": f"테스트 실패: {str(e)}",
            }
