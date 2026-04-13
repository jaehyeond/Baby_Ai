"""
Comparator — Quest 적합성 판정 + 모델 비교 테이블

Go/No-Go 기준:
- GREEN: peak_rss < 2500MB AND estimated_arm_latency < 2000ms
- YELLOW: peak_rss < 3000MB AND estimated_arm_latency < 5000ms
- RED: 초과
"""

import logging

from neural.ml.config import QuestConstraints, GoNoGoResult
from neural.ml.results.schema import ModelBenchmarkResult, BenchmarkSuite

logger = logging.getLogger(__name__)


def compute_quest_verdict(
    result: ModelBenchmarkResult,
    constraints: QuestConstraints | None = None,
) -> GoNoGoResult:
    """단일 모델에 대한 Quest 적합성 판정"""
    if constraints is None:
        constraints = QuestConstraints()

    budget = constraints.available_for_vlm_mb
    reasons = []

    # 로드 실패
    if not result.load_success:
        return GoNoGoResult(
            model_name=result.model_name,
            verdict="RED",
            peak_rss_mb=0,
            quest_ram_budget_mb=budget,
            estimated_arm_latency_ms=0,
            reasons=[f"Model failed to load: {result.load_error}"],
        )

    peak = result.memory.peak_rss_mb

    # ARM 지연 추정 (x86 대비 0.3~0.5x 성능)
    arm_latency_low = result.latency.warm_avg_ms / constraints.arm_cpu_scaling_factor_high
    arm_latency_high = result.latency.warm_avg_ms / constraints.arm_cpu_scaling_factor_low
    estimated_arm = (arm_latency_low + arm_latency_high) / 2
    result.estimated_arm_latency_ms = estimated_arm

    # RAM 판정
    if peak > budget:
        reasons.append(f"Peak RSS {peak:.0f}MB > budget {budget}MB")
    elif peak > budget * 0.85:
        reasons.append(f"Peak RSS {peak:.0f}MB is tight (>{budget * 0.85:.0f}MB)")
    else:
        reasons.append(f"Peak RSS {peak:.0f}MB fits in budget {budget}MB")

    # 지연 판정
    if estimated_arm > constraints.max_acceptable_latency_ms:
        reasons.append(
            f"Est. ARM latency {estimated_arm:.0f}ms > max {constraints.max_acceptable_latency_ms:.0f}ms"
        )
    elif estimated_arm > constraints.warning_latency_ms:
        reasons.append(
            f"Est. ARM latency {estimated_arm:.0f}ms > warning {constraints.warning_latency_ms:.0f}ms"
        )
    else:
        reasons.append(f"Est. ARM latency {estimated_arm:.0f}ms is acceptable")

    # 종합 판정
    ram_ok = peak <= budget
    ram_tight = peak <= budget * 0.85
    latency_ok = estimated_arm <= constraints.max_acceptable_latency_ms
    latency_good = estimated_arm <= constraints.warning_latency_ms

    if ram_tight and latency_good:
        verdict = "GREEN"
    elif ram_ok and latency_ok:
        verdict = "YELLOW"
    else:
        verdict = "RED"

    return GoNoGoResult(
        model_name=result.model_name,
        verdict=verdict,
        peak_rss_mb=peak,
        quest_ram_budget_mb=budget,
        estimated_arm_latency_ms=estimated_arm,
        reasons=reasons,
    )


def apply_verdicts(suite: BenchmarkSuite) -> list[GoNoGoResult]:
    """스위트의 모든 모델에 판정 적용"""
    verdicts = []
    for model in suite.models:
        v = compute_quest_verdict(model, suite.quest_constraints)
        model.quest_verdict = v.verdict
        model.quest_reasons = v.reasons
        verdicts.append(v)
    return verdicts


def print_comparison_table(suite: BenchmarkSuite) -> str:
    """비교 테이블 텍스트 생성"""
    lines = []
    lines.append("=" * 100)
    lines.append("VLM BENCHMARK COMPARISON — Quest 3S Screening")
    lines.append(f"RAM Budget: {suite.quest_constraints.available_for_vlm_mb}MB")
    lines.append("=" * 100)
    lines.append("")

    header = f"{'Model':<25} {'Disk MB':>8} {'Est RSS':>9} {'Avg ms':>8} {'P95 ms':>8} {'TPS':>6} {'ARM ms':>8} {'Verdict':>8}"
    lines.append(header)
    lines.append("-" * 100)

    for m in suite.models:
        if not m.load_success:
            lines.append(f"{m.model_name:<25} {'FAIL':>8} {'---':>9} {'---':>8} {'---':>8} {'---':>6} {'---':>8} {'RED':>8}")
            continue

        lines.append(
            f"{m.model_name:<25} "
            f"{m.total_disk_mb:>7.0f} "
            f"{m.memory.peak_rss_mb:>8.0f} "
            f"{m.latency.warm_avg_ms:>7.0f} "
            f"{m.latency.warm_p95_ms:>7.0f} "
            f"{m.latency.avg_tokens_per_second:>5.1f} "
            f"{m.estimated_arm_latency_ms:>7.0f} "
            f"{m.quest_verdict:>8}"
        )

    lines.append("-" * 100)
    lines.append("")

    # 상세 사유
    for m in suite.models:
        lines.append(f"  [{m.quest_verdict}] {m.model_name}:")
        for reason in m.quest_reasons:
            lines.append(f"    - {reason}")
        if m.notes:
            for note in m.notes:
                lines.append(f"    ! {note}")
        lines.append("")

    # Gemma 3n 제외 사유
    lines.append("NOTE: Gemma 3n E2B excluded — GGUF multimodal not yet supported")
    lines.append("      (ggml-org: 'still working on adding multimodal')")
    lines.append("      Text-only Q8_0 = 4.79GB → exceeds Quest RAM budget")
    lines.append("")

    return "\n".join(lines)
