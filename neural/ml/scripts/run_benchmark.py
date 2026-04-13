"""
VLM Benchmark Runner

사용법:
  python -m neural.ml.scripts.run_benchmark --model smolvlm-256m-q8   # 단일 모델
  python -m neural.ml.scripts.run_benchmark --all                       # 전체 모델
  python -m neural.ml.scripts.run_benchmark --all --skip-quality        # 품질 평가 스킵

결과: neural/ml/results_output/ 에 JSON 파일 생성
"""

import argparse
import json
import logging
import platform
import sys
from datetime import datetime
from pathlib import Path

import psutil

from neural.ml.config import (
    BenchmarkConfig, QuestConstraints,
    MODELS_CACHE_DIR, RESULTS_OUTPUT_DIR, TEST_IMAGES_DIR,
)
from neural.ml.models.registry import MODEL_REGISTRY, get_model
from neural.ml.models.downloader import download_model, get_model_paths, verify_model_exists
from neural.ml.runners.gguf_runner import GGUFRunner
from neural.ml.benchmarks.latency_profiler import run_latency_benchmark
from neural.ml.benchmarks.quality_evaluator import run_quality_evaluation
from neural.ml.results.schema import (
    BenchmarkSuite, ModelBenchmarkResult, PCSpecs,
    MemoryResult, LatencyResult, SampleOutput,
)
from neural.ml.results.comparator import apply_verdicts, print_comparison_table

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger(__name__)


def get_pc_specs() -> PCSpecs:
    """현재 PC 사양 수집"""
    return PCSpecs(
        cpu=platform.processor() or platform.machine(),
        ram_gb=psutil.virtual_memory().total / (1024**3),
        os=f"{platform.system()} {platform.release()}",
        python_version=platform.python_version(),
    )


def get_test_images() -> list[str]:
    """테스트 이미지 경로 목록 반환"""
    TEST_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    images = []
    for ext in ("*.jpg", "*.jpeg", "*.png", "*.webp"):
        images.extend(str(p) for p in TEST_IMAGES_DIR.glob(ext))

    if not images:
        logger.warning(
            f"[WARN] No test images found in {TEST_IMAGES_DIR}\n"
            f"  Please add 1-10 test images (jpg/png) to this directory.\n"
            f"  Creating a minimal test image for smoke testing..."
        )
        try:
            from PIL import Image
            test_img = TEST_IMAGES_DIR / "test_solid_orange.png"
            img = Image.new("RGB", (640, 480), color=(255, 128, 0))
            img.save(test_img)
            images.append(str(test_img))
            logger.info(f"  Created minimal test image: {test_img}")
        except ImportError:
            logger.error("  Pillow not installed. Cannot create test image.")

    return images


def benchmark_single_model(
    model_name: str,
    config: BenchmarkConfig,
    test_images: list[str],
    skip_quality: bool = False,
) -> ModelBenchmarkResult:
    """단일 모델 벤치마크"""
    spec = get_model(model_name)
    logger.info(f"\n{'='*60}")
    logger.info(f"BENCHMARKING: {spec.name} ({spec.architecture} {spec.quantization})")
    logger.info(f"{'='*60}")

    # 모델 파일 확인/다운로드
    if not verify_model_exists(spec):
        logger.info(f"[DOWNLOAD] Downloading {spec.name}...")
        download_model(spec)

    model_path, mmproj_path = get_model_paths(spec)
    if not model_path.exists():
        return ModelBenchmarkResult(
            model_name=spec.name, architecture=spec.architecture,
            quantization=spec.quantization or "", format=spec.format,
            file_size_mb=0, total_disk_mb=0,
            load_success=False, load_error="Model file not found after download",
        )

    file_size_mb = model_path.stat().st_size / (1024 * 1024)
    mmproj_size_mb = (mmproj_path.stat().st_size / (1024 * 1024)) if mmproj_path and mmproj_path.exists() else 0

    result = ModelBenchmarkResult(
        model_name=spec.name,
        architecture=spec.architecture,
        quantization=spec.quantization or "",
        format=spec.format,
        file_size_mb=file_size_mb,
        mmproj_size_mb=mmproj_size_mb,
        total_disk_mb=file_size_mb + mmproj_size_mb,
        notes=list(spec.notes),
    )

    # --- 러너 시작 ---
    runner = GGUFRunner(spec)
    load_result = runner.load_model(model_path, mmproj_path)

    if not load_result.success:
        result.load_success = False
        result.load_error = load_result.error
        result.notes.extend(load_result.notes)
        logger.error(f"[FAIL] {spec.name}: {load_result.error}")
        return result

    result.load_success = True

    try:
        # --- 지연 시간 벤치마크 ---
        if test_images:
            primary_image = test_images[0]
            primary_prompt = config.test_prompts[0] if config.test_prompts else "Describe this image."

            latency = run_latency_benchmark(
                runner, primary_image, primary_prompt,
                num_warmup=config.num_warmup_runs,
                num_timed=config.num_timed_runs,
            )

            result.latency = LatencyResult(
                cold_start_ms=latency.cold_start_ms,
                warm_avg_ms=latency.avg_ms,
                warm_median_ms=latency.median_ms,
                warm_p95_ms=latency.p95_ms,
                warm_p99_ms=latency.p99_ms,
                warm_min_ms=latency.min_ms,
                warm_max_ms=latency.max_ms,
                avg_tokens_per_second=latency.avg_tokens_per_second,
                num_timed_runs=len(latency.timed_runs_ms),
                num_errors=len(latency.errors),
            )

            if latency.errors:
                result.notes.extend(latency.errors[:3])

        # --- 메모리 추정 (CLI 모드: 파일 크기 기반) ---
        # llama-mtmd-cli는 매번 종료되므로 psutil로 실시간 측정 불가
        # 추정: 모델 + mmproj + 런타임 오버헤드 (~1.5x 파일 크기)
        estimated_rss = (file_size_mb + mmproj_size_mb) * 1.5
        result.memory = MemoryResult(
            baseline_rss_mb=0,
            model_load_rss_mb=estimated_rss,
            peak_rss_mb=estimated_rss,
            peak_delta_mb=estimated_rss,
            num_snapshots=0,
        )
        result.notes.append(
            f"Memory is estimated (file_size * 1.5 = {estimated_rss:.0f}MB). "
            f"Actual RSS requires llama-server fix or persistent process."
        )

        # --- 품질 평가 ---
        if not skip_quality and test_images:
            quality = run_quality_evaluation(
                runner, test_images[:3], config.test_prompts[:2],
            )
            for sample in quality.samples:
                result.sample_outputs.append(SampleOutput(
                    image_path=sample.image_path,
                    prompt=sample.prompt,
                    output_text=sample.output_text,
                    inference_time_ms=sample.inference_time_ms,
                    error=sample.error,
                ))

    finally:
        runner.unload()

    return result


def main():
    parser = argparse.ArgumentParser(description="VLM Benchmark Runner")
    parser.add_argument("--model", type=str, help="Benchmark specific model")
    parser.add_argument("--all", action="store_true", help="Benchmark all models")
    parser.add_argument("--skip-quality", action="store_true", help="Skip quality evaluation")
    parser.add_argument("--warmup", type=int, default=2, help="Warmup runs")
    parser.add_argument("--runs", type=int, default=5, help="Timed runs")
    args = parser.parse_args()

    if not args.model and not args.all:
        parser.print_help()
        print("\nExample: python -m neural.ml.scripts.run_benchmark --model smolvlm-256m-q8")
        return

    config = BenchmarkConfig(
        num_warmup_runs=args.warmup,
        num_timed_runs=args.runs,
    )

    test_images = get_test_images()
    if not test_images:
        logger.error("No test images available. Exiting.")
        sys.exit(1)

    suite = BenchmarkSuite(
        pc_specs=get_pc_specs(),
        quest_constraints=QuestConstraints(),
    )

    if args.model:
        models_to_test = [args.model]
    else:
        models_to_test = list(MODEL_REGISTRY.keys())

    for model_name in models_to_test:
        result = benchmark_single_model(model_name, config, test_images, args.skip_quality)
        suite.add_result(result)

    # Quest 판정 적용
    apply_verdicts(suite)

    # 결과 출력
    table = print_comparison_table(suite)
    # cp949 안전 출력
    try:
        print(table)
    except UnicodeEncodeError:
        print(table.encode("ascii", errors="replace").decode())

    # JSON 저장
    RESULTS_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = RESULTS_OUTPUT_DIR / f"benchmark_{ts}.json"
    output_path.write_text(suite.model_dump_json(indent=2), encoding="utf-8")
    logger.info(f"\nResults saved to: {output_path}")


if __name__ == "__main__":
    main()
