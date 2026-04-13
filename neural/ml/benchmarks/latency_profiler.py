"""
Latency Profiler — 추론 지연 시간 측정

cold start + warmup + timed runs → 통계 (avg, p50, p95, p99)
"""

import logging
import statistics
from dataclasses import dataclass, field

from neural.ml.runners.base_runner import BaseRunner, InferenceResult

logger = logging.getLogger(__name__)


@dataclass
class LatencyProfile:
    """지연 시간 프로파일 결과"""
    cold_start_ms: float = 0.0
    warmup_times_ms: list[float] = field(default_factory=list)
    timed_runs_ms: list[float] = field(default_factory=list)
    avg_ms: float = 0.0
    median_ms: float = 0.0
    p95_ms: float = 0.0
    p99_ms: float = 0.0
    min_ms: float = 0.0
    max_ms: float = 0.0
    avg_tokens_per_second: float = 0.0
    errors: list[str] = field(default_factory=list)


def run_latency_benchmark(
    runner: BaseRunner,
    image_path: str,
    prompt: str,
    num_warmup: int = 3,
    num_timed: int = 10,
) -> LatencyProfile:
    """지연 시간 벤치마크 실행"""
    profile = LatencyProfile()

    # Cold start (첫 추론)
    logger.info(f"[LATENCY] Cold start inference...")
    result = runner.infer(image_path, prompt)
    if result.error:
        profile.errors.append(f"Cold start failed: {result.error}")
        return profile
    profile.cold_start_ms = result.inference_time_ms
    logger.info(f"[LATENCY] Cold start: {profile.cold_start_ms:.0f}ms")

    # Warmup
    logger.info(f"[LATENCY] Warmup: {num_warmup} runs...")
    for i in range(num_warmup):
        result = runner.infer(image_path, prompt)
        if result.error:
            profile.errors.append(f"Warmup {i} failed: {result.error}")
        else:
            profile.warmup_times_ms.append(result.inference_time_ms)

    # Timed runs
    logger.info(f"[LATENCY] Timed: {num_timed} runs...")
    tps_values = []
    for i in range(num_timed):
        result = runner.infer(image_path, prompt)
        if result.error:
            profile.errors.append(f"Run {i} failed: {result.error}")
        else:
            profile.timed_runs_ms.append(result.inference_time_ms)
            if result.tokens_per_second > 0:
                tps_values.append(result.tokens_per_second)

    if not profile.timed_runs_ms:
        profile.errors.append("All timed runs failed")
        return profile

    # 통계 계산
    times = sorted(profile.timed_runs_ms)
    profile.avg_ms = statistics.mean(times)
    profile.median_ms = statistics.median(times)
    profile.min_ms = times[0]
    profile.max_ms = times[-1]

    # 퍼센타일
    n = len(times)
    profile.p95_ms = times[int(n * 0.95)] if n >= 2 else times[-1]
    profile.p99_ms = times[int(n * 0.99)] if n >= 2 else times[-1]

    if tps_values:
        profile.avg_tokens_per_second = statistics.mean(tps_values)

    logger.info(
        f"[LATENCY] Results: avg={profile.avg_ms:.0f}ms, "
        f"p95={profile.p95_ms:.0f}ms, tps={profile.avg_tokens_per_second:.1f}"
    )
    return profile
