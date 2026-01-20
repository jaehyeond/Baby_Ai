"""프로젝트 공통 설정"""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """환경변수 기반 설정 관리"""

    # Anthropic API
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")

    # Coder Agent 설정
    CODER_AGENT_HOST: str = os.getenv("CODER_AGENT_HOST", "localhost")
    CODER_AGENT_PORT: int = int(os.getenv("CODER_AGENT_PORT", "9999"))

    @classmethod
    def validate(cls) -> None:
        """필수 환경변수 검증"""
        if not cls.ANTHROPIC_API_KEY:
            raise ValueError(
                "ANTHROPIC_API_KEY가 설정되지 않았습니다.\n"
                ".env 파일에 ANTHROPIC_API_KEY=sk-ant-... 형식으로 추가하세요."
            )
