"""
Memory Profiler — llama-server 프로세스 RSS 측정

llama-server가 별도 프로세스이므로 psutil로 해당 PID의 메모리를 직접 추적.
서브프로세스 격리가 자연스럽게 보장됨.
"""

import logging
import threading
import time
from dataclasses import dataclass, field

import psutil

logger = logging.getLogger(__name__)


@dataclass
class MemorySnapshot:
    """특정 시점의 메모리 상태"""
    timestamp_s: float
    rss_mb: float
    vms_mb: float  # virtual memory size
    label: str = ""


@dataclass
class MemoryProfile:
    """전체 메모리 프로파일 결과"""
    snapshots: list[MemorySnapshot] = field(default_factory=list)
    baseline_rss_mb: float = 0.0
    peak_rss_mb: float = 0.0
    model_load_rss_mb: float = 0.0       # 모델 로드 후 RSS - baseline
    peak_inference_rss_mb: float = 0.0    # 추론 중 최대 RSS - baseline
    error: str | None = None


class ProcessMemoryTracker:
    """특정 PID의 메모리를 주기적으로 샘플링"""

    def __init__(self, pid: int, sample_interval_ms: int = 50):
        self.pid = pid
        self.interval_s = sample_interval_ms / 1000
        self._snapshots: list[MemorySnapshot] = []
        self._running = False
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        """백그라운드 샘플링 시작"""
        self._running = True
        self._thread = threading.Thread(target=self._sample_loop, daemon=True)
        self._thread.start()

    def stop(self) -> list[MemorySnapshot]:
        """샘플링 중지 + 결과 반환"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        return list(self._snapshots)

    def take_snapshot(self, label: str = "") -> MemorySnapshot | None:
        """즉시 1회 스냅샷"""
        try:
            proc = psutil.Process(self.pid)
            mem = proc.memory_info()
            snap = MemorySnapshot(
                timestamp_s=time.time(),
                rss_mb=mem.rss / (1024 * 1024),
                vms_mb=mem.vms / (1024 * 1024),
                label=label,
            )
            self._snapshots.append(snap)
            return snap
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            logger.warning(f"[MEM] Cannot read PID {self.pid}: {e}")
            return None

    def _sample_loop(self) -> None:
        while self._running:
            self.take_snapshot()
            time.sleep(self.interval_s)

    def get_peak_rss_mb(self) -> float:
        if not self._snapshots:
            return 0.0
        return max(s.rss_mb for s in self._snapshots)

    def get_current_rss_mb(self) -> float | None:
        snap = self.take_snapshot()
        return snap.rss_mb if snap else None


def profile_server_memory(
    pid: int,
    sample_interval_ms: int = 50,
) -> ProcessMemoryTracker:
    """llama-server PID에 대한 메모리 트래커 생성 + 시작"""
    tracker = ProcessMemoryTracker(pid, sample_interval_ms)
    tracker.start()
    return tracker


def build_memory_profile(
    tracker: ProcessMemoryTracker,
    baseline_rss_mb: float,
    model_load_rss_mb: float,
) -> MemoryProfile:
    """트래커 결과를 MemoryProfile로 변환"""
    snapshots = tracker.stop()
    peak_rss = max((s.rss_mb for s in snapshots), default=0.0)

    return MemoryProfile(
        snapshots=snapshots,
        baseline_rss_mb=baseline_rss_mb,
        peak_rss_mb=peak_rss,
        model_load_rss_mb=model_load_rss_mb - baseline_rss_mb,
        peak_inference_rss_mb=peak_rss - baseline_rss_mb,
    )
