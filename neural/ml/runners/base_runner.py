"""
Base Runner - 모델 추론 인터페이스

모든 러너(GGUF, ONNX 등)가 구현해야 할 인터페이스 정의.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

from neural.ml.config import ModelSpec


@dataclass
class InferenceResult:
    """단일 추론 결과"""
    output_text: str
    prompt: str
    image_path: str
    inference_time_ms: float
    tokens_generated: int = 0
    tokens_per_second: float = 0.0
    error: str | None = None


@dataclass
class ModelLoadResult:
    """모델 로드 결과"""
    success: bool
    load_time_ms: float
    error: str | None = None
    notes: list[str] = field(default_factory=list)


class BaseRunner(ABC):
    """모델 추론 러너 인터페이스"""

    def __init__(self, spec: ModelSpec):
        self.spec = spec
        self._loaded = False

    @abstractmethod
    def load_model(self, model_path: Path, mmproj_path: Path | None = None) -> ModelLoadResult:
        """모델 로드. 성공/실패 + 로드 시간 반환."""
        ...

    @abstractmethod
    def infer(self, image_path: str, prompt: str) -> InferenceResult:
        """이미지 + 프롬프트로 추론. 결과 텍스트 + 지연 시간 반환."""
        ...

    @abstractmethod
    def unload(self) -> None:
        """모델 언로드. 메모리 해제."""
        ...

    @property
    def is_loaded(self) -> bool:
        return self._loaded
