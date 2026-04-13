"""
VLM Benchmark Configuration

모든 벤치마크 파라미터, 모델 스펙, Quest 제약 조건 정의.
"""

from typing import Optional, Literal
from pydantic import BaseModel, Field
from pathlib import Path


# --- 경로 ---
ML_ROOT = Path(__file__).parent
MODELS_CACHE_DIR = ML_ROOT / "models_cache"
TEST_IMAGES_DIR = ML_ROOT / "test_images"
RESULTS_OUTPUT_DIR = ML_ROOT / "results_output"


class ModelSpec(BaseModel):
    """개별 모델 스펙"""
    name: str = Field(description="벤치마크용 식별자 (예: smolvlm-256m-q8)")
    repo_id: str = Field(description="HuggingFace repo ID")
    filename: str = Field(description="메인 모델 파일명")
    mmproj_filename: Optional[str] = Field(None, description="멀티모달 프로젝터 파일명 (VLM 필수)")
    format: Literal["gguf", "onnx"] = "gguf"
    architecture: str = Field(description="모델 아키텍처 (idefics3, gemma3n)")
    expected_params_m: Optional[int] = Field(None, description="예상 파라미터 수 (백만)")
    expected_file_size_mb: Optional[float] = Field(None, description="메인 모델 파일 크기 MB")
    expected_mmproj_size_mb: Optional[float] = Field(None, description="mmproj 파일 크기 MB")
    quantization: Optional[str] = Field(None, description="양자화 방식 (Q8_0, F16)")
    license: str = "apache-2.0"
    multimodal: bool = True
    notes: list[str] = Field(default_factory=list)

    @property
    def total_expected_size_mb(self) -> float:
        model = self.expected_file_size_mb or 0
        mmproj = self.expected_mmproj_size_mb or 0
        return model + mmproj


class QuestConstraints(BaseModel):
    """Quest 3S 하드웨어 제약

    LoXR 논문 기준: dev-available = 5750MB (OS 오버헤드 이미 차감됨)
    여기서 추가 차감: passthrough(500) + YOLO(400) + headroom(500) = 1400MB
    → VLM 가용: 5750 - 1400 = 4350MB (보수적 추정)
    → 더 보수적: ~2850MB (passthrough 실측 전까지)
    """
    dev_available_mb: int = 5750       # LoXR: Quest 3S 개발자 가용 RAM
    passthrough_overhead_mb: int = 500  # 패스스루 카메라 (추정, 실측 필요)
    yolo_overhead_mb: int = 400         # YOLO 동시 실행
    safety_headroom_mb: int = 500       # 안전 여유

    @property
    def available_for_vlm_mb(self) -> int:
        return (self.dev_available_mb
                - self.passthrough_overhead_mb
                - self.yolo_overhead_mb
                - self.safety_headroom_mb)

    # 추론 지연 기준
    max_acceptable_latency_ms: float = 5000.0
    warning_latency_ms: float = 2000.0

    # ARM 스케일링 팩터 (x86 대비)
    arm_cpu_scaling_factor_low: float = 0.3
    arm_cpu_scaling_factor_high: float = 0.5


class BenchmarkConfig(BaseModel):
    """벤치마크 실행 설정"""
    models: list[str] = Field(
        default_factory=list,
        description="실행할 모델 name 목록. 비어있으면 전체"
    )
    num_warmup_runs: int = 3
    num_timed_runs: int = 10
    memory_sample_interval_ms: int = 50
    output_dir: str = str(RESULTS_OUTPUT_DIR)

    test_prompts: list[str] = Field(default_factory=lambda: [
        "Describe what you see in this image in one sentence.",
        "What objects are in this image? List them.",
        "What is the spatial relationship between the main objects?",
        "Is there a person in this image? What are they doing?",
    ])


class GoNoGoResult(BaseModel):
    """Quest 적합성 판정"""
    model_name: str
    verdict: Literal["GREEN", "YELLOW", "RED"]
    peak_rss_mb: float
    quest_ram_budget_mb: float
    estimated_arm_latency_ms: float
    reasons: list[str]
