"""
Quality Comparison: SmolVLM-256M vs 500M

동일 이미지 + 동일 프롬프트로 두 모델의 출력을 비교.
Baby AI 물리세계 학습에 필요한 4가지 능력을 테스트:
  1. 물체 인식 (What objects?)
  2. 공간 관계 (Spatial relationships?)
  3. 행동/affordance 이해 (What is happening? What can be done?)
  4. 물리 직관 (Physical properties?)

사용법:
  python -m neural.ml.scripts.run_quality_comparison
"""

import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

from neural.ml.config import TEST_IMAGES_DIR, RESULTS_OUTPUT_DIR
from neural.ml.models.registry import get_model
from neural.ml.models.downloader import verify_model_exists, download_model, get_model_paths
from neural.ml.runners.gguf_runner import GGUFRunner

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger(__name__)


# Baby AI 물리세계 학습 관련 프롬프트
QUALITY_PROMPTS = [
    {
        "id": "objects",
        "prompt": "List all objects you can see in this image.",
        "tests": "물체 인식 — 얼마나 많은 물체를 정확히 식별하는가",
    },
    {
        "id": "spatial",
        "prompt": "Describe the spatial layout. Where are the objects relative to each other?",
        "tests": "공간 관계 — 위/아래/안/옆 등 관계 이해",
    },
    {
        "id": "action",
        "prompt": "What is happening in this image? What actions or activities can you identify?",
        "tests": "행동/affordance — 동작 인식, 물체 용도 이해",
    },
    {
        "id": "physical",
        "prompt": "Describe the physical properties of the main objects (size, material, weight estimate, texture).",
        "tests": "물리 속성 — 직관적 물리 이해 (크기, 재질, 무게감, 질감)",
    },
]


def get_test_images() -> list[tuple[str, str]]:
    """(경로, 파일명) 쌍 반환"""
    images = []
    for p in sorted(TEST_IMAGES_DIR.glob("*.jpg")):
        images.append((str(p), p.name))
    return images


def run_model_evaluation(model_name: str, images: list[tuple[str, str]]) -> list[dict]:
    """단일 모델로 전체 이미지 x 프롬프트 평가"""
    spec = get_model(model_name)

    if not verify_model_exists(spec):
        logger.info(f"Downloading {model_name}...")
        download_model(spec)

    model_path, mmproj_path = get_model_paths(spec)
    runner = GGUFRunner(spec)
    load_result = runner.load_model(model_path, mmproj_path)

    if not load_result.success:
        logger.error(f"Failed to load {model_name}: {load_result.error}")
        return []

    results = []
    total = len(images) * len(QUALITY_PROMPTS)
    done = 0

    for img_path, img_name in images:
        for pspec in QUALITY_PROMPTS:
            done += 1
            logger.info(f"[{done}/{total}] {model_name} | {img_name} | {pspec['id']}")

            result = runner.infer(img_path, pspec["prompt"])

            results.append({
                "model": model_name,
                "image": img_name,
                "prompt_id": pspec["id"],
                "prompt": pspec["prompt"],
                "output": result.output_text,
                "inference_ms": result.inference_time_ms,
                "tokens": result.tokens_generated,
                "tps": result.tokens_per_second,
                "error": result.error,
            })

            if result.error:
                logger.warning(f"  ERROR: {result.error}")
            else:
                # 첫 80자만 미리보기
                preview = result.output_text[:80].replace("\n", " ")
                logger.info(f"  -> {preview}...")

    runner.unload()
    return results


def print_comparison(results_256m: list[dict], results_500m: list[dict]):
    """두 모델 결과를 나란히 비교 출력"""
    # 인덱싱
    idx_256 = {(r["image"], r["prompt_id"]): r for r in results_256m}
    idx_500 = {(r["image"], r["prompt_id"]): r for r in results_500m}

    images = sorted(set(r["image"] for r in results_256m))

    lines = []
    lines.append("=" * 120)
    lines.append("QUALITY COMPARISON: SmolVLM-256M Q8 vs SmolVLM-500M Q8")
    lines.append("=" * 120)

    for img in images:
        lines.append(f"\n--- {img} ---")
        for pspec in QUALITY_PROMPTS:
            pid = pspec["id"]
            r256 = idx_256.get((img, pid), {})
            r500 = idx_500.get((img, pid), {})

            out256 = r256.get("output", "N/A")
            out500 = r500.get("output", "N/A")
            ms256 = r256.get("inference_ms", 0)
            ms500 = r500.get("inference_ms", 0)

            lines.append(f"\n  [{pid}] {pspec['prompt']}")
            lines.append(f"  256M ({ms256:.0f}ms): {out256[:200]}")
            lines.append(f"  500M ({ms500:.0f}ms): {out500[:200]}")

    lines.append("\n" + "=" * 120)
    return "\n".join(lines)


def main():
    images = get_test_images()
    if not images:
        logger.error("No test images. Run: python -m neural.ml.scripts.prepare_test_images")
        sys.exit(1)

    logger.info(f"Found {len(images)} test images, {len(QUALITY_PROMPTS)} prompts")
    logger.info(f"Total evaluations per model: {len(images) * len(QUALITY_PROMPTS)}")

    # --- SmolVLM-256M ---
    logger.info(f"\n{'='*60}")
    logger.info("EVALUATING: SmolVLM-256M Q8")
    logger.info(f"{'='*60}")
    results_256m = run_model_evaluation("smolvlm-256m-q8", images)

    # --- SmolVLM-500M ---
    logger.info(f"\n{'='*60}")
    logger.info("EVALUATING: SmolVLM-500M Q8")
    logger.info(f"{'='*60}")
    results_500m = run_model_evaluation("smolvlm-500m-q8", images)

    # --- 비교 출력 ---
    comparison = print_comparison(results_256m, results_500m)
    try:
        print(comparison)
    except UnicodeEncodeError:
        print(comparison.encode("ascii", errors="replace").decode())

    # --- JSON 저장 ---
    RESULTS_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    output = {
        "timestamp": ts,
        "images": len(images),
        "prompts": len(QUALITY_PROMPTS),
        "results_256m": results_256m,
        "results_500m": results_500m,
    }
    output_path = RESULTS_OUTPUT_DIR / f"quality_comparison_{ts}.json"
    output_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info(f"\nResults saved to: {output_path}")


if __name__ == "__main__":
    main()
