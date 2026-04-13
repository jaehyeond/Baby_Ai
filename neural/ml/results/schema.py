"""
Results Schema — 벤치마크 결과 구조화

JSON 직렬화/역직렬화 + Quest 적합성 자동 판정.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

from neural.ml.config import QuestConstraints


class SampleOutput(BaseModel):
    """개별 추론 샘플"""
    image_path: str
    prompt: str
    output_text: str
    inference_time_ms: float
    error: Optional[str] = None


class MemoryResult(BaseModel):
    """메모리 측정 결과"""
    baseline_rss_mb: float = 0.0
    model_load_rss_mb: float = Field(0.0, description="모델 로드로 인한 RSS 증가")
    peak_rss_mb: float = Field(0.0, description="추론 중 최대 RSS")
    peak_delta_mb: float = Field(0.0, description="peak - baseline")
    num_snapshots: int = 0


class LatencyResult(BaseModel):
    """지연 시간 측정 결과"""
    cold_start_ms: float = 0.0
    warm_avg_ms: float = 0.0
    warm_median_ms: float = 0.0
    warm_p95_ms: float = 0.0
    warm_p99_ms: float = 0.0
    warm_min_ms: float = 0.0
    warm_max_ms: float = 0.0
    avg_tokens_per_second: float = 0.0
    num_timed_runs: int = 0
    num_errors: int = 0


class ModelBenchmarkResult(BaseModel):
    """단일 모델의 전체 벤치마크 결과"""
    model_name: str
    architecture: str
    quantization: str
    format: str
    file_size_mb: float = Field(description="메인 모델 파일 크기")
    mmproj_size_mb: float = Field(0.0, description="mmproj 파일 크기")
    total_disk_mb: float = Field(description="총 디스크 사용량")

    memory: MemoryResult = Field(default_factory=MemoryResult)
    latency: LatencyResult = Field(default_factory=LatencyResult)
    sample_outputs: list[SampleOutput] = Field(default_factory=list)

    quest_verdict: str = Field("UNKNOWN", description="GREEN/YELLOW/RED/FAIL")
    quest_reasons: list[str] = Field(default_factory=list)
    estimated_arm_latency_ms: float = Field(0.0, description="예상 Quest ARM 지연")

    load_success: bool = False
    load_error: Optional[str] = None
    notes: list[str] = Field(default_factory=list)


class PCSpecs(BaseModel):
    """테스트 PC 사양"""
    cpu: str = ""
    ram_gb: float = 0.0
    os: str = ""
    python_version: str = ""


class BenchmarkSuite(BaseModel):
    """전체 벤치마크 스위트"""
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    pc_specs: PCSpecs = Field(default_factory=PCSpecs)
    quest_constraints: QuestConstraints = Field(default_factory=QuestConstraints)
    models: list[ModelBenchmarkResult] = Field(default_factory=list)

    def add_result(self, result: ModelBenchmarkResult) -> None:
        self.models.append(result)

    def get_passing_models(self) -> list[ModelBenchmarkResult]:
        return [m for m in self.models if m.quest_verdict in ("GREEN", "YELLOW")]
