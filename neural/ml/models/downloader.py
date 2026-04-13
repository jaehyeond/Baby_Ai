"""
Model Downloader

HuggingFace Hub에서 GGUF 모델 + mmproj 자동 다운로드.
"""

import logging
from pathlib import Path

from huggingface_hub import hf_hub_download, HfApi

from neural.ml.config import ModelSpec, MODELS_CACHE_DIR

logger = logging.getLogger(__name__)


def _download_file(repo_id: str, filename: str, cache_dir: Path, label: str) -> Path:
    """단일 파일 다운로드. 이미 있으면 스킵."""
    local_path = cache_dir / filename
    if local_path.exists():
        size_mb = local_path.stat().st_size / (1024 * 1024)
        logger.info(f"[SKIP] {label} already exists: {local_path} ({size_mb:.1f} MB)")
        return local_path

    logger.info(f"[DOWNLOAD] {label} from {repo_id}/{filename}")
    downloaded_path = hf_hub_download(
        repo_id=repo_id,
        filename=filename,
        local_dir=str(cache_dir),
        local_dir_use_symlinks=False,
    )
    result = Path(downloaded_path)
    size_mb = result.stat().st_size / (1024 * 1024)
    logger.info(f"[DONE] {label}: {size_mb:.1f} MB")
    return result


def download_model(spec: ModelSpec, cache_dir: Path = MODELS_CACHE_DIR) -> tuple[Path, Path | None]:
    """모델 + mmproj 다운로드. (model_path, mmproj_path) 반환."""
    cache_dir.mkdir(parents=True, exist_ok=True)

    model_path = _download_file(
        spec.repo_id, spec.filename, cache_dir, f"{spec.name}/model"
    )

    # 파일 크기 검증
    actual_mb = model_path.stat().st_size / (1024 * 1024)
    if spec.expected_file_size_mb:
        ratio = actual_mb / spec.expected_file_size_mb
        if ratio < 0.5 or ratio > 2.0:
            logger.warning(
                f"[WARN] {spec.name} model size {actual_mb:.0f}MB vs "
                f"expected {spec.expected_file_size_mb:.0f}MB (ratio {ratio:.2f})"
            )

    mmproj_path = None
    if spec.mmproj_filename:
        mmproj_path = _download_file(
            spec.repo_id, spec.mmproj_filename, cache_dir, f"{spec.name}/mmproj"
        )

    total_mb = actual_mb + (mmproj_path.stat().st_size / (1024 * 1024) if mmproj_path else 0)
    logger.info(f"[TOTAL] {spec.name}: {total_mb:.1f} MB on disk")
    return model_path, mmproj_path


def verify_model_exists(spec: ModelSpec, cache_dir: Path = MODELS_CACHE_DIR) -> bool:
    """모델(+mmproj) 파일이 로컬에 모두 있는지 확인."""
    model_ok = (cache_dir / spec.filename).exists()
    mmproj_ok = True
    if spec.mmproj_filename:
        mmproj_ok = (cache_dir / spec.mmproj_filename).exists()
    return model_ok and mmproj_ok


def get_model_paths(spec: ModelSpec, cache_dir: Path = MODELS_CACHE_DIR) -> tuple[Path, Path | None]:
    """로컬 파일 경로 반환 (존재 확인 안 함)."""
    model_path = cache_dir / spec.filename
    mmproj_path = (cache_dir / spec.mmproj_filename) if spec.mmproj_filename else None
    return model_path, mmproj_path


def list_available_gguf_files(repo_id: str) -> list[str]:
    """HF repo에서 사용 가능한 GGUF 파일 목록 조회."""
    api = HfApi()
    files = api.list_repo_files(repo_id)
    return [f for f in files if f.endswith(".gguf")]
