"""
Neural Pipeline Visualizer

ANN 파이프라인의 실시간 시각화 및 보고서 생성
- ASCII 흐름도
- 실시간 진행 상황
- 상세 결과 보고서
"""

import sys
import time
from dataclasses import dataclass
from typing import Optional
from enum import Enum

from .layer import LayerType, LayerStatus, NeuralLayer


class Colors:
    """ANSI 색상 코드 (Windows 터미널 지원)"""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    # 전경색
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"

    # 배경색
    BG_GREEN = "\033[42m"
    BG_RED = "\033[41m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"

    @classmethod
    def disable(cls):
        """색상 비활성화 (리다이렉션 등)"""
        cls.RESET = ""
        cls.BOLD = ""
        cls.DIM = ""
        cls.RED = ""
        cls.GREEN = ""
        cls.YELLOW = ""
        cls.BLUE = ""
        cls.MAGENTA = ""
        cls.CYAN = ""
        cls.WHITE = ""
        cls.BG_GREEN = ""
        cls.BG_RED = ""
        cls.BG_YELLOW = ""
        cls.BG_BLUE = ""


# Windows 터미널 ANSI 지원 활성화
def enable_windows_ansi():
    """Windows에서 ANSI 이스케이프 시퀀스 활성화"""
    if sys.platform == "win32":
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
        except Exception:
            Colors.disable()


enable_windows_ansi()


class NeuralVisualizer:
    """Neural Pipeline 시각화 도구"""

    # 레이어 타입별 아이콘
    LAYER_ICONS = {
        LayerType.INPUT: "[IN]",
        LayerType.EXECUTIVE: "[EX]",
        LayerType.PROCESSING: "[PR]",
        LayerType.EVALUATION: "[EV]",
        LayerType.OUTPUT: "[OUT]",
    }

    # 상태별 아이콘
    STATUS_ICONS = {
        LayerStatus.IDLE: "[ ]",
        LayerStatus.PROCESSING: "[~]",
        LayerStatus.COMPLETED: "[OK]",
        LayerStatus.FAILED: "[X]",
        LayerStatus.SKIPPED: "[-]",
    }

    def __init__(self, use_colors: bool = True):
        self.use_colors = use_colors
        if not use_colors:
            Colors.disable()

    def print_header(self, title: str, width: int = 70):
        """헤더 출력"""
        c = Colors
        border = "=" * width
        padding = (width - len(title) - 2) // 2

        print(f"\n{c.CYAN}{border}{c.RESET}")
        print(f"{c.CYAN}={c.RESET}{' ' * padding}{c.BOLD}{c.WHITE}{title}{c.RESET}{' ' * padding}{c.CYAN}={c.RESET}")
        print(f"{c.CYAN}{border}{c.RESET}")

    def print_subheader(self, title: str, width: int = 50):
        """서브헤더 출력"""
        c = Colors
        print(f"\n{c.YELLOW}{'-' * width}{c.RESET}")
        print(f"{c.BOLD}{title}{c.RESET}")
        print(f"{c.YELLOW}{'-' * width}{c.RESET}")

    def print_network_diagram(self, layers: dict[int, NeuralLayer], current_layer: int = -1):
        """
        네트워크 구조 다이어그램 출력

        Args:
            layers: 레이어 딕셔너리
            current_layer: 현재 실행 중인 레이어 인덱스 (-1이면 없음)
        """
        c = Colors

        print(f"\n{c.BOLD}  NEURAL NETWORK ARCHITECTURE{c.RESET}")
        print(f"  {'='*45}")

        sorted_indices = sorted(layers.keys())

        for i, idx in enumerate(sorted_indices):
            layer = layers[idx]
            is_current = idx == current_layer

            # 현재 레이어 하이라이트
            if is_current:
                prefix = f"{c.BG_BLUE}{c.WHITE} >> "
                suffix = f" << {c.RESET}"
            else:
                prefix = "    "
                suffix = ""

            # 레이어 박스
            icon = self.LAYER_ICONS.get(layer.layer_type, "[?]")
            status_icon = self.STATUS_ICONS.get(layer.status, "[ ]")

            # 색상 결정
            if layer.status == LayerStatus.COMPLETED:
                color = c.GREEN
            elif layer.status == LayerStatus.FAILED:
                color = c.RED
            elif layer.status == LayerStatus.PROCESSING:
                color = c.YELLOW
            else:
                color = c.DIM

            # 노드 정보
            nodes_str = ", ".join(n.agent_id for n in layer.active_nodes)
            if not nodes_str:
                nodes_str = "(no agents)"

            print(f"{prefix}{color}+{'-'*35}+{c.RESET}{suffix}")
            print(f"{prefix}{color}| {icon} Layer {idx}: {layer.name:<18} |{c.RESET}{suffix}")
            print(f"{prefix}{color}| {status_icon} Agents: {nodes_str:<20} |{c.RESET}{suffix}")
            print(f"{prefix}{color}+{'-'*35}+{c.RESET}{suffix}")

            # 연결선 (마지막이 아니면)
            if i < len(sorted_indices) - 1:
                print(f"              {c.DIM}|{c.RESET}")
                print(f"              {c.DIM}v{c.RESET}")

    def print_forward_pass_start(self, input_text: str, max_iterations: int):
        """Forward Pass 시작 출력"""
        c = Colors

        self.print_header("NEURAL A2A PIPELINE - Forward Pass")

        print(f"\n{c.CYAN}[INPUT]{c.RESET}")
        # 입력 텍스트 줄바꿈 처리
        if len(input_text) > 60:
            print(f"  {input_text[:60]}...")
        else:
            print(f"  {input_text}")

        print(f"\n{c.CYAN}[CONFIG]{c.RESET}")
        print(f"  Max Iterations: {max_iterations}")
        print(f"  Feedback Loop: Enabled")

    def print_iteration_start(self, iteration: int, max_iter: int, strategy: str):
        """반복 시작 출력"""
        c = Colors

        print(f"\n{c.MAGENTA}{'#'*60}{c.RESET}")
        print(f"{c.MAGENTA}#  ITERATION {iteration}/{max_iter}  |  Strategy: {strategy.upper():<20}#{c.RESET}")
        print(f"{c.MAGENTA}{'#'*60}{c.RESET}")

    def print_layer_start(self, layer: NeuralLayer):
        """레이어 실행 시작"""
        c = Colors
        icon = self.LAYER_ICONS.get(layer.layer_type, "[?]")

        print(f"\n{c.BLUE}>>> {icon} {layer.name} (Layer {layer.layer_index}){c.RESET}")
        print(f"    Type: {layer.layer_type.value}")
        print(f"    Agents: {', '.join(n.agent_id for n in layer.active_nodes)}")
        print(f"    {c.DIM}Processing...{c.RESET}", end="", flush=True)

    def print_layer_complete(self, layer: NeuralLayer, success: bool, time_ms: float):
        """레이어 실행 완료"""
        c = Colors

        if success:
            status = f"{c.GREEN}[OK]{c.RESET}"
        else:
            status = f"{c.RED}[FAILED]{c.RESET}"

        # 이전 "Processing..." 덮어쓰기
        print(f"\r    {status} Completed in {time_ms:.0f}ms" + " " * 20)

    def print_agent_output(self, agent_id: str, output: str, max_lines: int = 5):
        """에이전트 출력 표시"""
        c = Colors

        print(f"\n    {c.CYAN}[{agent_id}]{c.RESET}")

        lines = output.strip().split("\n")
        for i, line in enumerate(lines[:max_lines]):
            # 긴 줄 자르기
            if len(line) > 70:
                line = line[:67] + "..."
            print(f"      {c.DIM}{line}{c.RESET}")

        if len(lines) > max_lines:
            print(f"      {c.DIM}... ({len(lines) - max_lines} more lines){c.RESET}")

    def print_feedback(self, feedback: str, iteration: int):
        """피드백 출력"""
        c = Colors

        print(f"\n{c.YELLOW}[!] FEEDBACK (will retry){c.RESET}")
        print(f"    {c.DIM}{feedback[:200]}{'...' if len(feedback) > 200 else ''}{c.RESET}")

    def print_flow_diagram(
        self,
        layers: dict[int, NeuralLayer],
        iteration: int,
        status: str
    ):
        """
        실시간 흐름 다이어그램
        """
        c = Colors

        print(f"\n{c.BOLD}  FORWARD PASS FLOW (Iteration {iteration}){c.RESET}")
        print(f"  {'='*50}")

        # 레이어 흐름 한 줄로
        flow_parts = []
        for idx in sorted(layers.keys()):
            layer = layers[idx]

            if layer.status == LayerStatus.COMPLETED:
                part = f"{c.GREEN}[L{idx}:OK]{c.RESET}"
            elif layer.status == LayerStatus.FAILED:
                part = f"{c.RED}[L{idx}:X]{c.RESET}"
            elif layer.status == LayerStatus.PROCESSING:
                part = f"{c.YELLOW}[L{idx}:~]{c.RESET}"
            else:
                part = f"{c.DIM}[L{idx}]{c.RESET}"

            flow_parts.append(part)

        flow_str = f" {c.DIM}->{c.RESET} ".join(flow_parts)
        print(f"\n  INPUT -> {flow_str} -> OUTPUT")
        print(f"\n  Status: {status}")

    def print_final_report(
        self,
        success: bool,
        iterations: int,
        max_iterations: int,
        total_time_ms: float,
        final_output: str,
        layer_outputs: list,
        feedback_history: list[str],
        layers: dict[int, NeuralLayer],
    ):
        """최종 결과 보고서"""
        c = Colors

        # 헤더
        if success:
            self.print_header("PIPELINE COMPLETED SUCCESSFULLY")
            status_line = f"{c.GREEN}[SUCCESS]{c.RESET} All layers passed"
        else:
            self.print_header("PIPELINE FAILED")
            status_line = f"{c.RED}[FAILED]{c.RESET} Max iterations reached"

        # 요약 정보
        print(f"\n{c.BOLD}EXECUTION SUMMARY{c.RESET}")
        print(f"  {status_line}")
        print(f"  Iterations: {iterations}/{max_iterations}")
        print(f"  Total Time: {total_time_ms:.0f}ms ({total_time_ms/1000:.1f}s)")

        # 레이어별 결과
        self.print_subheader("LAYER RESULTS")

        # 현재 iteration의 레이어 출력만 표시
        current_iteration_outputs = layer_outputs[-(len(layers)):]

        for layer_output in current_iteration_outputs:
            layer = layers.get(layer_output.layer_index)
            if not layer:
                continue

            if layer_output.is_success:
                status = f"{c.GREEN}[OK]{c.RESET}"
            else:
                status = f"{c.RED}[X]{c.RESET}"

            print(f"\n  {status} Layer {layer_output.layer_index}: {layer.name}")

            for agent_id, output in layer_output.outputs.items():
                lines = output.strip().split("\n")
                preview = lines[0][:60] + "..." if len(lines[0]) > 60 else lines[0]
                print(f"       {c.CYAN}{agent_id}{c.RESET}: {preview}")

        # 피드백 이력 (있으면)
        if feedback_history:
            self.print_subheader("FEEDBACK HISTORY")
            for i, fb in enumerate(feedback_history, 1):
                print(f"  [{i}] {fb[:100]}...")

        # 최종 출력
        self.print_subheader("FINAL OUTPUT")

        if final_output:
            print()
            # 코드 블록처럼 표시
            for line in final_output.split("\n"):
                print(f"  {c.WHITE}{line}{c.RESET}")
        else:
            print(f"  {c.DIM}(No output){c.RESET}")

        # 푸터
        print(f"\n{c.CYAN}{'='*70}{c.RESET}")

        if success:
            print(f"{c.GREEN}{c.BOLD}Pipeline completed successfully!{c.RESET}")
        else:
            print(f"{c.RED}{c.BOLD}Pipeline failed after {iterations} iterations.{c.RESET}")

    def print_progress_bar(self, current: int, total: int, width: int = 40, label: str = ""):
        """진행률 바"""
        c = Colors

        filled = int(width * current / total)
        bar = "=" * filled + "-" * (width - filled)
        percent = current / total * 100

        print(f"\r  [{bar}] {percent:.0f}% {label}", end="", flush=True)


def create_visualizer(use_colors: bool = True) -> NeuralVisualizer:
    """Visualizer 팩토리"""
    return NeuralVisualizer(use_colors=use_colors)
