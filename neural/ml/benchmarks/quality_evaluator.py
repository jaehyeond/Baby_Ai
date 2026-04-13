"""
Quality Evaluator — 동일 이미지/프롬프트로 모델 출력 품질 비교

수동 비교를 위해 원문을 구조화 저장.
"""

import logging
from dataclasses import dataclass, field

from neural.ml.runners.base_runner import BaseRunner

logger = logging.getLogger(__name__)


@dataclass
class QualitySample:
    """단일 이미지-프롬프트 쌍의 출력"""
    image_path: str
    prompt: str
    output_text: str
    inference_time_ms: float
    error: str | None = None


@dataclass
class QualityProfile:
    """전체 품질 평가 결과"""
    model_name: str
    samples: list[QualitySample] = field(default_factory=list)
    total_images: int = 0
    total_prompts: int = 0
    successful: int = 0
    failed: int = 0


def run_quality_evaluation(
    runner: BaseRunner,
    image_paths: list[str],
    prompts: list[str],
) -> QualityProfile:
    """모든 이미지 × 프롬프트 조합으로 품질 평가"""
    profile = QualityProfile(
        model_name=runner.spec.name,
        total_images=len(image_paths),
        total_prompts=len(prompts),
    )

    for img_path in image_paths:
        for prompt in prompts:
            logger.info(f"[QUALITY] {runner.spec.name}: {img_path} / {prompt[:40]}...")
            result = runner.infer(img_path, prompt)

            sample = QualitySample(
                image_path=img_path,
                prompt=prompt,
                output_text=result.output_text,
                inference_time_ms=result.inference_time_ms,
                error=result.error,
            )
            profile.samples.append(sample)

            if result.error:
                profile.failed += 1
                logger.warning(f"[QUALITY] Failed: {result.error}")
            else:
                profile.successful += 1
                logger.info(f"[QUALITY] Output: {result.output_text[:100]}...")

    return profile
