"""
LLM Client - Multi-Model AI Client

여러 LLM 제공자를 통합하는 클라이언트
- OpenAI: GPT-5.2 Thinking (깊은 추론)
- Google: Gemini 3.0 Flash/Pro (빠른 처리)
- Anthropic: Claude (기존 에이전트)

뇌 영역 매핑:
- Gemini Flash = System 1 (빠른 직관)
- GPT-5.2 Thinking = System 2 (느린 분석)
"""

import os
from typing import Optional, Literal
from dataclasses import dataclass
from enum import Enum
from dotenv import load_dotenv

load_dotenv()


class ModelProvider(Enum):
    """LLM 제공자"""
    OPENAI = "openai"
    GOOGLE = "google"
    ANTHROPIC = "anthropic"


class ModelTier(Enum):
    """모델 티어 (비용/성능 기준)"""
    FLASH = "flash"      # 빠르고 저렴 (System 1)
    STANDARD = "standard"  # 균형잡힌 성능
    THINKING = "thinking"  # 깊은 추론 (System 2)


@dataclass
class ModelConfig:
    """모델 설정"""
    provider: ModelProvider
    model_id: str
    tier: ModelTier
    description: str
    input_cost_per_1m: float  # $/1M tokens
    output_cost_per_1m: float


# 사용 가능한 모델 정의
AVAILABLE_MODELS = {
    # Google Gemini
    "gemini-3-flash": ModelConfig(
        provider=ModelProvider.GOOGLE,
        model_id="gemini-3-flash-preview",
        tier=ModelTier.FLASH,
        description="Gemini 3 Flash - 빠른 처리, 기본 추론",
        input_cost_per_1m=0.50,
        output_cost_per_1m=3.00,
    ),
    "gemini-3-pro": ModelConfig(
        provider=ModelProvider.GOOGLE,
        model_id="gemini-3-pro-preview",
        tier=ModelTier.STANDARD,
        description="Gemini 3 Pro - 중간 복잡도 작업",
        input_cost_per_1m=1.25,
        output_cost_per_1m=10.00,
    ),
    # OpenAI GPT
    "gpt-5.2": ModelConfig(
        provider=ModelProvider.OPENAI,
        model_id="gpt-5.2",
        tier=ModelTier.STANDARD,
        description="GPT-5.2 - 균형잡힌 성능",
        input_cost_per_1m=1.75,
        output_cost_per_1m=14.00,
    ),
    "gpt-5.2-thinking": ModelConfig(
        provider=ModelProvider.OPENAI,
        model_id="gpt-5.2",
        tier=ModelTier.THINKING,
        description="GPT-5.2 Thinking - 깊은 추론 (System 2)",
        input_cost_per_1m=1.75,
        output_cost_per_1m=14.00,  # + thinking tokens
    ),
    # Fallback models (현재 실제 사용 가능)
    "gemini-2-flash": ModelConfig(
        provider=ModelProvider.GOOGLE,
        model_id="gemini-2.0-flash",
        tier=ModelTier.FLASH,
        description="Gemini 2.0 Flash - 빠른 처리 (Fallback)",
        input_cost_per_1m=0.10,
        output_cost_per_1m=0.40,
    ),
    "gpt-4o-mini": ModelConfig(
        provider=ModelProvider.OPENAI,
        model_id="gpt-4o-mini",
        tier=ModelTier.FLASH,
        description="GPT-4o Mini - 빠른 처리 (Fallback)",
        input_cost_per_1m=0.15,
        output_cost_per_1m=0.60,
    ),
}


class LLMClient:
    """
    통합 LLM 클라이언트

    여러 제공자의 모델을 일관된 인터페이스로 호출
    - 텍스트 생성
    - 멀티모달 생성 (이미지 + 텍스트)
    - 오디오 처리 (Phase 4.2)
    """

    def __init__(self):
        self._openai_client = None
        self._google_client = None
        self._anthropic_client = None

    def _get_openai_client(self):
        """OpenAI 클라이언트 (lazy init)"""
        if self._openai_client is None:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY not set")
            from openai import OpenAI
            self._openai_client = OpenAI(api_key=api_key)
        return self._openai_client

    def _get_google_client(self):
        """Google Gemini 클라이언트 (lazy init)"""
        if self._google_client is None:
            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key:
                raise ValueError("GOOGLE_API_KEY not set")
            try:
                # 새로운 SDK (google-genai)
                from google import genai
                self._google_client = genai.Client(api_key=api_key)
            except ImportError:
                # 구버전 SDK (google-generativeai)
                import google.generativeai as genai
                genai.configure(api_key=api_key)
                self._google_client = genai
        return self._google_client

    def generate(
        self,
        prompt: str,
        model_key: str = "gemini-2-flash",
        system_prompt: str = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        thinking_level: Literal["minimal", "low", "medium", "high"] = None,
    ) -> str:
        """
        텍스트 생성

        Args:
            prompt: 사용자 프롬프트
            model_key: 모델 키 (AVAILABLE_MODELS 참조)
            system_prompt: 시스템 프롬프트
            temperature: 창의성 (0.0 ~ 1.0)
            max_tokens: 최대 출력 토큰
            thinking_level: Thinking 모델용 사고 깊이

        Returns:
            생성된 텍스트
        """
        if model_key not in AVAILABLE_MODELS:
            raise ValueError(f"Unknown model: {model_key}")

        config = AVAILABLE_MODELS[model_key]

        if config.provider == ModelProvider.GOOGLE:
            return self._generate_google(
                prompt, config, system_prompt, temperature, max_tokens, thinking_level
            )
        elif config.provider == ModelProvider.OPENAI:
            return self._generate_openai(
                prompt, config, system_prompt, temperature, max_tokens, thinking_level
            )
        else:
            raise ValueError(f"Unsupported provider: {config.provider}")

    def _generate_google(
        self,
        prompt: str,
        config: ModelConfig,
        system_prompt: str,
        temperature: float,
        max_tokens: int,
        thinking_level: str,
    ) -> str:
        """Google Gemini 생성"""
        client = self._get_google_client()

        try:
            # 새로운 SDK (google-genai)
            if hasattr(client, 'models'):
                generation_config = {
                    "temperature": temperature,
                    "max_output_tokens": max_tokens,
                }

                # Thinking level (Gemini 3 전용)
                if thinking_level and "gemini-3" in config.model_id:
                    generation_config["thinking_level"] = thinking_level

                contents = prompt
                if system_prompt:
                    contents = f"{system_prompt}\n\n{prompt}"

                response = client.models.generate_content(
                    model=config.model_id,
                    contents=contents,
                    config=generation_config,
                )
                return response.text
            else:
                # 구버전 SDK
                model = client.GenerativeModel(config.model_id)

                generation_config = {
                    "temperature": temperature,
                    "max_output_tokens": max_tokens,
                }

                full_prompt = prompt
                if system_prompt:
                    full_prompt = f"{system_prompt}\n\n{prompt}"

                response = model.generate_content(
                    full_prompt,
                    generation_config=generation_config,
                )
                return response.text

        except Exception as e:
            # Fallback to OpenAI if Google fails
            print(f"[LLMClient] Gemini error: {e}, falling back to OpenAI...")
            return self._generate_openai_fallback(prompt, system_prompt, temperature, max_tokens)

    def _generate_google_fallback(
        self,
        prompt: str,
        system_prompt: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        """Gemini 폴백 (2.0 Flash)"""
        client = self._get_google_client()

        if hasattr(client, 'GenerativeModel'):
            model = client.GenerativeModel("gemini-2.0-flash")
        else:
            model = client.models

        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"

        if hasattr(model, 'generate_content'):
            response = model.generate_content(
                full_prompt,
                generation_config={"temperature": temperature, "max_output_tokens": max_tokens},
            )
            return response.text
        else:
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=full_prompt,
            )
            return response.text

    def _generate_openai_fallback(
        self,
        prompt: str,
        system_prompt: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        """OpenAI 폴백 (gpt-4o-mini)"""
        client = self._get_openai_client()

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content

    def _generate_openai(
        self,
        prompt: str,
        config: ModelConfig,
        system_prompt: str,
        temperature: float,
        max_tokens: int,
        thinking_level: str,
    ) -> str:
        """OpenAI 생성"""
        client = self._get_openai_client()

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            # GPT-5.2 Thinking 모드
            if config.tier == ModelTier.THINKING and thinking_level:
                # thinking_level을 OpenAI의 reasoning effort로 매핑
                reasoning_effort = {
                    "minimal": "low",
                    "low": "low",
                    "medium": "medium",
                    "high": "high",
                }.get(thinking_level, "medium")

                response = client.chat.completions.create(
                    model=config.model_id,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    reasoning_effort=reasoning_effort,
                )
            else:
                response = client.chat.completions.create(
                    model=config.model_id,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )

            return response.choices[0].message.content

        except Exception as e:
            # Fallback
            print(f"[LLMClient] OpenAI error: {e}, falling back to gpt-4o-mini...")
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content

    def generate_multimodal(
        self,
        prompt: str,
        images: list[bytes] = None,
        model_key: str = "gemini-2-flash",
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        """
        멀티모달 생성 (이미지 + 텍스트)

        Gemini Vision API를 사용하여 이미지와 텍스트를 함께 처리

        Args:
            prompt: 텍스트 프롬프트
            images: 이미지 바이너리 데이터 리스트
            model_key: 모델 키 (gemini-2-flash, gemini-3-flash 등)
            temperature: 창의성 (0.0 ~ 1.0)
            max_tokens: 최대 출력 토큰

        Returns:
            생성된 텍스트
        """
        if not images:
            # 이미지가 없으면 일반 텍스트 생성
            return self.generate(prompt, model_key, temperature=temperature, max_tokens=max_tokens)

        # Gemini만 지원 (현재)
        client = self._get_google_client()
        config = AVAILABLE_MODELS.get(model_key, AVAILABLE_MODELS["gemini-2-flash"])

        try:
            import base64

            # 새로운 SDK (google-genai)
            if hasattr(client, 'models'):
                from google.genai import types

                # 이미지 파트 생성
                parts = []
                for img_data in images:
                    # base64 인코딩
                    img_b64 = base64.b64encode(img_data).decode('utf-8')
                    parts.append(types.Part.from_bytes(
                        data=img_data,
                        mime_type="image/jpeg",  # 기본값, 실제로는 감지해야 함
                    ))

                # 텍스트 파트 추가
                parts.append(types.Part.from_text(prompt))

                # 생성 설정
                generation_config = types.GenerateContentConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                )

                response = client.models.generate_content(
                    model=config.model_id,
                    contents=parts,
                    config=generation_config,
                )
                return response.text

            else:
                # 구버전 SDK (google-generativeai)
                import google.generativeai as genai

                model = client.GenerativeModel(config.model_id)

                # 콘텐츠 구성
                contents = []
                for img_data in images:
                    # PIL Image로 변환
                    try:
                        from PIL import Image
                        import io
                        img = Image.open(io.BytesIO(img_data))
                        contents.append(img)
                    except ImportError:
                        # PIL 없으면 base64로
                        img_b64 = base64.b64encode(img_data).decode('utf-8')
                        contents.append({
                            "mime_type": "image/jpeg",
                            "data": img_b64,
                        })

                contents.append(prompt)

                response = model.generate_content(
                    contents,
                    generation_config={
                        "temperature": temperature,
                        "max_output_tokens": max_tokens,
                    },
                )
                return response.text

        except Exception as e:
            print(f"[LLMClient] Multimodal generation failed: {e}")
            # 폴백: 이미지 없이 텍스트만 처리
            return self.generate(
                prompt=f"[이미지가 있다고 가정하고 답변해주세요]\n\n{prompt}",
                model_key=model_key,
                temperature=temperature,
                max_tokens=max_tokens,
            )

    def detect_image_mime_type(self, image_data: bytes) -> str:
        """이미지 MIME 타입 감지"""
        # 매직 바이트로 감지
        if image_data[:3] == b'\xff\xd8\xff':
            return "image/jpeg"
        elif image_data[:8] == b'\x89PNG\r\n\x1a\n':
            return "image/png"
        elif image_data[:6] in (b'GIF87a', b'GIF89a'):
            return "image/gif"
        elif image_data[:4] == b'RIFF' and image_data[8:12] == b'WEBP':
            return "image/webp"
        else:
            return "image/jpeg"  # 기본값


# 싱글톤 인스턴스
_llm_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """LLMClient 싱글톤"""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client
