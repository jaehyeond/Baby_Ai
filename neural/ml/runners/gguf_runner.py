"""
GGUF Runner — llama-mtmd-cli 기반 멀티모달 추론

llama-server의 SmolVLM chat template이 이미지 마커를 삽입하지 못하는 문제로
("number of bitmaps (1) does not match number of markers (0)"),
llama-mtmd-cli를 서브프로세스로 실행하여 추론하는 방식 사용.

장점:
- llama.cpp 공식 multimodal CLI, SmolVLM idefics3 확인됨
- 서브프로세스 격리로 메모리 측정 정확
- 출력에 perf 통계 포함 (tokens/s, timing)
"""

import logging
import re
import shutil
import subprocess
import time
from pathlib import Path

from neural.ml.config import ModelSpec
from neural.ml.runners.base_runner import BaseRunner, InferenceResult, ModelLoadResult

logger = logging.getLogger(__name__)

INFERENCE_TIMEOUT = 120  # 초


class GGUFRunner(BaseRunner):
    """llama-mtmd-cli 서브프로세스 기반 GGUF VLM 러너

    매 추론마다 새 프로세스를 띄우는 것은 비효율적이지만,
    벤치마크 목적으로는 메모리 격리가 더 중요하다.
    latency 측정에서 프로세스 시작/모델 로드 시간은 별도 기록.
    """

    def __init__(self, spec: ModelSpec):
        super().__init__(spec)
        self._model_path: Path | None = None
        self._mmproj_path: Path | None = None
        self._cli_path: str | None = None
        self._last_pid: int | None = None

    def _find_mtmd_cli(self) -> str | None:
        """llama-mtmd-cli 바이너리 위치 탐색"""
        # 1. 프로젝트 내 번들된 바이너리
        bundled = Path(__file__).parent.parent / "tools" / "llama-cpp" / "llama-mtmd-cli.exe"
        if bundled.exists():
            return str(bundled)
        # Linux/Mac
        bundled_unix = Path(__file__).parent.parent / "tools" / "llama-cpp" / "llama-mtmd-cli"
        if bundled_unix.exists():
            return str(bundled_unix)
        # 2. PATH
        found = shutil.which("llama-mtmd-cli")
        return found

    def load_model(self, model_path: Path, mmproj_path: Path | None = None) -> ModelLoadResult:
        """모델 경로 설정 + CLI 바이너리 확인 (실제 로드는 infer 시)"""
        cli = self._find_mtmd_cli()
        if not cli:
            return ModelLoadResult(
                success=False, load_time_ms=0,
                error="llama-mtmd-cli not found. Download from llama.cpp releases.",
                notes=["Expected at: neural/ml/tools/llama-cpp/llama-mtmd-cli.exe"],
            )

        if not model_path.exists():
            return ModelLoadResult(success=False, load_time_ms=0,
                                   error=f"Model file not found: {model_path}")

        if mmproj_path and not mmproj_path.exists():
            return ModelLoadResult(success=False, load_time_ms=0,
                                   error=f"mmproj file not found: {mmproj_path}")

        self._cli_path = cli
        self._model_path = model_path
        self._mmproj_path = mmproj_path
        self._loaded = True

        # 실제 로드 시간은 첫 infer에서 측정 (cold start)
        return ModelLoadResult(success=True, load_time_ms=0,
                               notes=["Model path set, actual loading happens on first inference"])

    def infer(self, image_path: str, prompt: str) -> InferenceResult:
        """llama-mtmd-cli로 이미지 + 프롬프트 추론"""
        if not self._loaded or not self._cli_path:
            return InferenceResult(
                output_text="", prompt=prompt, image_path=image_path,
                inference_time_ms=0, error="Model not loaded"
            )

        img = Path(image_path)
        if not img.exists():
            return InferenceResult(
                output_text="", prompt=prompt, image_path=image_path,
                inference_time_ms=0, error=f"Image not found: {image_path}"
            )

        cmd = [
            self._cli_path,
            "-m", str(self._model_path),
            "--image", str(img),
            "-p", prompt,
            "-n", "128",
            "-c", "4096",
        ]
        if self._mmproj_path:
            cmd.extend(["--mmproj", str(self._mmproj_path)])

        start = time.perf_counter()
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                timeout=INFERENCE_TIMEOUT,
            )
            elapsed_ms = (time.perf_counter() - start) * 1000
            self._last_pid = None  # 프로세스 이미 종료

            # stdout = 모델 출력 텍스트, stderr = 로그 + perf 통계
            stdout = proc.stdout.decode(errors="replace")
            stderr = proc.stderr.decode(errors="replace")

            if proc.returncode != 0:
                return InferenceResult(
                    output_text="", prompt=prompt, image_path=image_path,
                    inference_time_ms=elapsed_ms,
                    error=f"Exit code {proc.returncode}: {(stdout + stderr)[:300]}"
                )

            # stdout에서 모델 출력 추출 (깨끗한 텍스트)
            output_text = stdout.strip()
            # stderr에서 perf 통계 추출
            perf = self._extract_perf(stderr)

            return InferenceResult(
                output_text=output_text,
                prompt=prompt,
                image_path=image_path,
                inference_time_ms=elapsed_ms,
                tokens_generated=perf.get("eval_tokens", 0),
                tokens_per_second=perf.get("eval_tps", 0.0),
            )

        except subprocess.TimeoutExpired:
            elapsed_ms = (time.perf_counter() - start) * 1000
            return InferenceResult(
                output_text="", prompt=prompt, image_path=image_path,
                inference_time_ms=elapsed_ms,
                error=f"Timeout after {INFERENCE_TIMEOUT}s"
            )
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start) * 1000
            return InferenceResult(
                output_text="", prompt=prompt, image_path=image_path,
                inference_time_ms=elapsed_ms, error=str(e)
            )

    def _extract_output(self, combined: str) -> str:
        """CLI 출력에서 모델의 실제 텍스트 응답 추출

        llama-mtmd-cli 출력 구조:
        ... 로그 ...
        image decoded ...
        (빈줄)
         실제 응답 텍스트
        (빈줄)
        llama_perf_context_print: ...
        """
        lines = combined.split("\n")
        output_lines = []
        in_output = False

        for line in lines:
            # 응답 시작 감지: "image decoded" 이후 텍스트
            if "image decoded" in line:
                in_output = True
                continue
            # 응답 끝 감지: perf 통계 시작
            if "llama_perf" in line:
                break
            if in_output:
                output_lines.append(line)

        # 앞뒤 빈줄 제거
        text = "\n".join(output_lines).strip()
        return text

    def _extract_perf(self, combined: str) -> dict:
        """CLI 출력에서 성능 통계 추출

        llama_perf_context_print: prompt eval time = 341.73 ms / 83 tokens (4.12 ms per token, 242.88 tokens per second)
        llama_perf_context_print: eval time = 214.18 ms / 63 runs (3.40 ms per token, 294.14 tokens per second)
        llama_perf_context_print: total time = 628.28 ms / 146 tokens
        """
        perf = {}

        # prompt eval
        m = re.search(r"prompt eval time\s*=\s*([\d.]+)\s*ms\s*/\s*(\d+)\s*tokens", combined)
        if m:
            perf["prompt_eval_ms"] = float(m.group(1))
            perf["prompt_tokens"] = int(m.group(2))

        # eval (generation)
        m = re.search(r"eval time\s*=\s*([\d.]+)\s*ms\s*/\s*(\d+)\s*runs\s*\(\s*([\d.]+)\s*ms", combined)
        if m:
            perf["eval_ms"] = float(m.group(1))
            perf["eval_tokens"] = int(m.group(2))
            perf["eval_ms_per_token"] = float(m.group(3))

        # tokens per second
        m = re.search(r"eval time.*?([\d.]+)\s*tokens per second\)", combined)
        if m:
            perf["eval_tps"] = float(m.group(1))

        # total
        m = re.search(r"total time\s*=\s*([\d.]+)\s*ms\s*/\s*(\d+)", combined)
        if m:
            perf["total_ms"] = float(m.group(1))
            perf["total_tokens"] = int(m.group(2))

        return perf

    def get_server_pid(self) -> int | None:
        """CLI는 매번 새 프로세스이므로 None (메모리 측정은 run_benchmark에서 별도)"""
        return self._last_pid

    def unload(self) -> None:
        """CLI 모드에서는 프로세스가 매 추론 후 종료되므로 no-op"""
        self._loaded = False
        self._model_path = None
        self._mmproj_path = None
