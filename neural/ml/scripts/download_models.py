"""
Model Downloader Script

사용법:
  python -m neural.ml.scripts.download_models                    # 전체 모델
  python -m neural.ml.scripts.download_models --model smolvlm-256m-q8  # 특정 모델
  python -m neural.ml.scripts.download_models --list             # 목록 출력
"""

import argparse
import logging
import sys

from neural.ml.models.registry import MODEL_REGISTRY, get_model, list_models
from neural.ml.models.downloader import download_model, verify_model_exists

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="VLM 모델 다운로더")
    parser.add_argument("--model", type=str, help="특정 모델만 다운로드")
    parser.add_argument("--list", action="store_true", help="사용 가능한 모델 목록")
    parser.add_argument("--check", action="store_true", help="로컬 존재 여부만 확인")
    args = parser.parse_args()

    if args.list:
        print("\n=== Available Models ===\n")
        for name, spec in MODEL_REGISTRY.items():
            status = "LOCAL" if verify_model_exists(spec) else "REMOTE"
            total = spec.total_expected_size_mb
            print(f"  [{status}] {name:<25} {spec.architecture:<10} {spec.quantization:<6} ~{total:.0f}MB")
            if spec.notes:
                for note in spec.notes:
                    print(f"           {note}")
        print()
        return

    if args.model:
        models_to_download = [get_model(args.model)]
    else:
        models_to_download = list(MODEL_REGISTRY.values())

    if args.check:
        for spec in models_to_download:
            exists = verify_model_exists(spec)
            print(f"  {'OK' if exists else 'MISSING'}: {spec.name}")
        return

    print(f"\nDownloading {len(models_to_download)} model(s)...\n")
    for spec in models_to_download:
        try:
            model_path, mmproj_path = download_model(spec)
            total_mb = model_path.stat().st_size / (1024 * 1024)
            if mmproj_path:
                total_mb += mmproj_path.stat().st_size / (1024 * 1024)
            print(f"  OK: {spec.name} ({total_mb:.0f} MB total)")
        except Exception as e:
            print(f"  FAIL: {spec.name} — {e}", file=sys.stderr)

    print("\nDone.")


if __name__ == "__main__":
    main()
