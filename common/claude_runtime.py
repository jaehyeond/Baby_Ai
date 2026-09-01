"""Claude 호출 런타임 — Claude Agent SDK 경유 (구독 할당량 사용, API 종량 과금 아님).

왜 이 파일이 있나
-----------------
에이전트 3개(coder/tester/reviewer)가 똑같이 "시스템 프롬프트 + 사용자 요청 → 텍스트 한 덩이"를
필요로 한다. 그 호출을 한 곳에 모은다.

두 가지 함정을 여기서 막는다:

1. **API 키가 환경에 남아 있으면 구독이 아니라 API로 과금된다.**
   Claude Agent SDK는 `os.environ`을 자식 프로세스에 그대로 상속시킨다
   (`options.env`는 덮어쓰기가 아니라 그 위에 병합된다 — SDK subprocess_cli.py 확인).
   그리고 Claude Code는 `ANTHROPIC_API_KEY`가 있으면 OAuth 대신 그 키를 쓴다
   (실측: 일부러 틀린 키를 심으면 OAuth로 넘어가지 않고 401로 죽는다).
   `common/config.py`가 import 시점에 `load_dotenv()`로 키를 올려두므로,
   호출 직전에 반드시 지운다. 지우지 않으면 조용히 계속 과금된다.

2. **`response.content[0]`을 맹목적으로 찍으면 터진다.**
   adaptive thinking이 켜진 모델은 첫 블록이 ThinkingBlock일 수 있다
   (실측: 15회 중 5회 `'ThinkingBlock' object has no attribute 'text'`).
   여기서는 TextBlock만 골라 모으므로 구조적으로 안 터진다.
"""
from __future__ import annotations

import os
import tempfile

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    TextBlock,
    query,
)

# 기본 모델. 바꾸려면 .env 에 CLAUDE_AGENT_MODEL=... 를 넣는다.
DEFAULT_MODEL = os.getenv("CLAUDE_AGENT_MODEL", "claude-sonnet-5")

# 자식 프로세스에 상속되면 구독 대신 API로 과금되는 변수들
_BILLING_ENV_KEYS = ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")

# 호출마다 usage 를 여기 쌓는다. 구독에서는 달러가 아니라 '할당량'이 비용이라 이걸 봐야 한다.
# (호출 한 번이 claude CLI 세션 하나 = 하네스 프롬프트가 매번 새로 캐시된다)
USAGE_LOG: list[dict] = []


def usage_totals() -> dict:
    """USAGE_LOG 합계. 호출 수와 토큰 종류별 합."""
    keys = ("input_tokens", "output_tokens", "cache_creation_input_tokens",
            "cache_read_input_tokens")
    out = {"calls": len(USAGE_LOG)}
    for k in keys:
        out[k] = sum(int(u.get(k) or 0) for u in USAGE_LOG)
    out["billable_total"] = out["input_tokens"] + out["output_tokens"] + \
        out["cache_creation_input_tokens"] + out["cache_read_input_tokens"]
    return out


class ClaudeRuntimeError(RuntimeError):
    """Claude 호출이 실패했다 (인증·한도·CLI 문제 포함)."""


def use_subscription() -> list[str]:
    """API 키를 현재 프로세스 환경에서 제거한다. 제거한 키 이름을 돌려준다.

    import 순서에 상관없이 동작하도록 호출 때마다 실행한다 (비용 없음).
    """
    removed = []
    for k in _BILLING_ENV_KEYS:
        if os.environ.pop(k, None) is not None:
            removed.append(k)
    return removed


async def ask(system_prompt: str, user_prompt: str, *, model: str | None = None,
              cwd: str | None = None) -> str:
    """시스템 프롬프트 + 사용자 요청을 보내고 텍스트 응답을 돌려준다.

    도구는 전부 끈다(`allowed_tools=[]`) — 이 에이전트들은 파일을 만지지 않는 순수 생성기다.
    프로젝트 설정도 안 읽는다(`setting_sources=[]`) — CLAUDE.md 등이 응답에 섞이면 안 된다.
    """
    use_subscription()

    options = ClaudeAgentOptions(
        model=model or DEFAULT_MODEL,
        system_prompt=system_prompt,
        # tools=[] 가 도구를 실제로 끄는 필드다 (--tools "" 로 매핑, 기본 도구 집합을 비운다).
        # allowed_tools 는 '승인 허용목록'일 뿐이라 [] 로 둬도 도구가 살아 있다 — 실측:
        # tester 프롬프트("코드를 테스트해줘")에 Claude Code 가 Bash/PowerShell 로 실제 실행을
        # 시도하며 턴을 전부 소진하고 error_max_turns 로 죽었다.
        tools=[],
        allowed_tools=[],
        setting_sources=[],
        max_turns=4,
        cwd=cwd or tempfile.gettempdir(),
    )

    parts: list[str] = []
    result: ResultMessage | None = None
    try:
        async for message in query(prompt=user_prompt, options=options):
            if isinstance(message, AssistantMessage):
                # TextBlock 만 모은다 — ThinkingBlock 등 다른 블록은 건너뛴다
                parts.extend(b.text for b in message.content if isinstance(b, TextBlock))
            elif isinstance(message, ResultMessage):
                result = message
                if isinstance(getattr(message, "usage", None), dict):
                    USAGE_LOG.append(dict(message.usage))
    except Exception as e:                      # SDK 예외를 한 종류로 좁힌다
        raise ClaudeRuntimeError(str(e)) from e

    if result is not None and result.is_error:
        raise ClaudeRuntimeError(
            f"Claude 오류 (status={result.api_error_status}, subtype={result.subtype})")

    text = "".join(parts).strip()
    if not text:
        # 빈 응답을 성공으로 넘기지 않는다 — 기준선에서 이걸로 한 번 당했다
        raise ClaudeRuntimeError("빈 응답을 받았다 (TextBlock 없음)")
    return text
