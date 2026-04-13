"""
Results Comparator Script

사용법:
  python -m neural.ml.scripts.compare_results                    # 최신 결과 파일
  python -m neural.ml.scripts.compare_results --file path/to.json  # 특정 파일
"""

import argparse
import json
import logging
from pathlib import Path

from neural.ml.config import RESULTS_OUTPUT_DIR
from neural.ml.results.schema import BenchmarkSuite
from neural.ml.results.comparator import apply_verdicts, print_comparison_table

logging.basicConfig(level=logging.INFO, format="%(message)s")


def find_latest_result() -> Path | None:
    """최신 벤치마크 결과 파일 찾기"""
    if not RESULTS_OUTPUT_DIR.exists():
        return None
    files = sorted(RESULTS_OUTPUT_DIR.glob("benchmark_*.json"), reverse=True)
    return files[0] if files else None


def main():
    parser = argparse.ArgumentParser(description="벤치마크 결과 비교")
    parser.add_argument("--file", type=str, help="결과 JSON 파일 경로")
    args = parser.parse_args()

    if args.file:
        result_path = Path(args.file)
    else:
        result_path = find_latest_result()

    if not result_path or not result_path.exists():
        print("No benchmark results found.")
        print(f"Run: python -m neural.ml.scripts.run_benchmark --model smolvlm-256m-q8")
        return

    print(f"Loading: {result_path}\n")
    data = json.loads(result_path.read_text(encoding="utf-8"))
    suite = BenchmarkSuite.model_validate(data)

    # 판정 재계산
    apply_verdicts(suite)

    # 비교 테이블 출력
    table = print_comparison_table(suite)
    print(table)

    # 통과 모델 요약
    passing = suite.get_passing_models()
    if passing:
        print(f"\n=== QUEST CANDIDATES ({len(passing)} models) ===")
        for m in passing:
            print(f"  [{m.quest_verdict}] {m.model_name}: "
                  f"RSS={m.memory.peak_rss_mb:.0f}MB, "
                  f"ARM~{m.estimated_arm_latency_ms:.0f}ms")
    else:
        print("\n=== NO MODELS PASSED Quest screening ===")
        print("  Consider: SmolVLM2 variants, ONNX Runtime path, or PC-only inference")


if __name__ == "__main__":
    main()
