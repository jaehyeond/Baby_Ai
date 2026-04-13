"""
CuriosityEngine - 호기심 엔진

Intrinsic Curiosity Module (ICM) 기반
- 예측 오류 = 학습 신호 = 내재적 보상
- 너무 쉬우면 지루함, 너무 어려우면 좌절
- "학습 가능 영역" (Zone of Proximal Development)에서 최대 호기심

참고:
- Curiosity-driven Exploration by Self-supervised Prediction (arXiv:1705.05363)
- Learning Progress Hypothesis (Oudeyer & Kaplan)
"""

from dataclasses import dataclass, field
from typing import Optional, Any
from datetime import datetime
from enum import Enum
import math
import hashlib


class LearningZone(Enum):
    """학습 영역"""
    TOO_EASY = "too_easy"           # 지루함 영역
    PROXIMAL = "proximal"           # 학습 가능 영역 (최적)
    TOO_HARD = "too_hard"           # 좌절 영역


@dataclass
class CuriositySignal:
    """호기심 신호"""
    prediction_error: float      # 예측 오류 (0.0 ~ 1.0)
    learning_progress: float     # 학습 진전 (-1.0 ~ 1.0)
    novelty: float               # 새로움 (0.0 ~ 1.0)
    intrinsic_reward: float      # 내재적 보상 (최종)
    zone: LearningZone           # 현재 학습 영역
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def should_explore(self) -> bool:
        """탐험해야 하는지"""
        return self.zone == LearningZone.PROXIMAL and self.intrinsic_reward > 0.3

    def to_dict(self) -> dict:
        return {
            "prediction_error": self.prediction_error,
            "learning_progress": self.learning_progress,
            "novelty": self.novelty,
            "intrinsic_reward": self.intrinsic_reward,
            "zone": self.zone.value,
        }


@dataclass
class LearningProgress:
    """학습 진전 추적"""
    task_type: str
    error_history: list[float] = field(default_factory=list)
    max_history: int = 20

    def add_error(self, error: float) -> None:
        """예측 오류 기록"""
        self.error_history.append(error)
        if len(self.error_history) > self.max_history:
            self.error_history.pop(0)

    def get_progress(self) -> float:
        """
        학습 진전 계산

        Returns:
            양수: 개선 중 (오류 감소)
            0: 정체
            음수: 악화 (오류 증가)
        """
        if len(self.error_history) < 2:
            return 0.0

        # 최근 절반 vs 이전 절반 비교
        mid = len(self.error_history) // 2
        old_avg = sum(self.error_history[:mid]) / mid if mid > 0 else 0
        new_avg = sum(self.error_history[mid:]) / (len(self.error_history) - mid)

        # 오류가 줄었으면 진전
        progress = old_avg - new_avg

        # -1.0 ~ 1.0 범위로 정규화
        return max(-1.0, min(1.0, progress * 2))


class CuriosityEngine:
    """
    호기심 엔진

    예측 오류 기반 내재적 동기 시스템
    - Forward Model: 현재 상태 + 행동 → 다음 상태 예측
    - Inverse Model: 두 상태 → 행동 예측
    - 예측 오류 = 배울 것이 있다 = 호기심!
    """

    def __init__(self):
        # 태스크별 학습 진전 추적
        self._progress_trackers: dict[str, LearningProgress] = {}

        # 본 적 있는 상태 해시
        self._seen_states: set[str] = set()
        self._max_seen = 10000

        # 호기심 파라미터
        self._novelty_weight = 0.3      # 새로움 가중치
        self._progress_weight = 0.4     # 학습 진전 가중치
        self._error_weight = 0.3        # 예측 오류 가중치

        # 최적 학습 영역 경계
        self._easy_threshold = 0.15     # 이 이하면 너무 쉬움
        self._hard_threshold = 0.85     # 이 이상이면 너무 어려움

    def compute_curiosity(
        self,
        state: str,
        action: str,
        predicted_outcome: str,
        actual_outcome: str,
        task_type: str = "default",
    ) -> CuriositySignal:
        """
        호기심 신호 계산

        Args:
            state: 현재 상태 (예: 사용자 요청)
            action: 수행한 행동 (예: 생성한 코드)
            predicted_outcome: 예측한 결과
            actual_outcome: 실제 결과
            task_type: 태스크 유형 (학습 진전 추적용)

        Returns:
            CuriositySignal
        """
        # 1. 예측 오류 계산
        prediction_error = self._compute_prediction_error(
            predicted_outcome, actual_outcome
        )

        # 2. 새로움 계산
        novelty = self._compute_novelty(state, action)

        # 3. 학습 진전 계산
        if task_type not in self._progress_trackers:
            self._progress_trackers[task_type] = LearningProgress(task_type)

        tracker = self._progress_trackers[task_type]
        tracker.add_error(prediction_error)
        learning_progress = tracker.get_progress()

        # 4. 학습 영역 판단
        zone = self._determine_zone(prediction_error)

        # 5. 내재적 보상 계산
        intrinsic_reward = self._compute_intrinsic_reward(
            prediction_error, novelty, learning_progress, zone
        )

        return CuriositySignal(
            prediction_error=prediction_error,
            learning_progress=learning_progress,
            novelty=novelty,
            intrinsic_reward=intrinsic_reward,
            zone=zone,
        )

    def compute_simple_curiosity(
        self,
        success: bool,
        output: str,
        task_type: str = "default",
    ) -> CuriositySignal:
        """
        간단한 호기심 계산 (예측 모델 없이)

        Args:
            success: 성공 여부
            output: 출력 결과
            task_type: 태스크 유형
        """
        # 성공 = 예측 오류 낮음, 실패 = 예측 오류 높음
        prediction_error = 0.2 if success else 0.7

        # 출력 기반 새로움
        novelty = self._compute_novelty(output, task_type)

        # 학습 진전
        if task_type not in self._progress_trackers:
            self._progress_trackers[task_type] = LearningProgress(task_type)

        tracker = self._progress_trackers[task_type]
        tracker.add_error(prediction_error)
        learning_progress = tracker.get_progress()

        zone = self._determine_zone(prediction_error)

        intrinsic_reward = self._compute_intrinsic_reward(
            prediction_error, novelty, learning_progress, zone
        )

        return CuriositySignal(
            prediction_error=prediction_error,
            learning_progress=learning_progress,
            novelty=novelty,
            intrinsic_reward=intrinsic_reward,
            zone=zone,
        )

    def _compute_prediction_error(
        self,
        predicted: str,
        actual: str,
    ) -> float:
        """
        예측 오류 계산 (텍스트 유사도 기반)

        실제로는 임베딩 거리를 사용하지만,
        여기서는 간단한 문자열 비교 사용
        """
        if not predicted or not actual:
            return 1.0

        # Jaccard 유사도 기반
        pred_words = set(predicted.lower().split())
        actual_words = set(actual.lower().split())

        if not pred_words or not actual_words:
            return 1.0

        intersection = len(pred_words & actual_words)
        union = len(pred_words | actual_words)

        similarity = intersection / union if union > 0 else 0

        # 오류 = 1 - 유사도
        return 1.0 - similarity

    def _compute_novelty(self, state: str, action: str = "") -> float:
        """새로움 계산"""
        # 상태+행동 해시
        combined = f"{state}:{action}"
        state_hash = hashlib.md5(combined.encode()).hexdigest()[:16]

        if state_hash in self._seen_states:
            # 본 적 있음 → 새롭지 않음
            return 0.0

        # 새로운 상태 기록
        self._seen_states.add(state_hash)
        if len(self._seen_states) > self._max_seen:
            # 오래된 것 제거 (간단히 절반 제거)
            self._seen_states = set(list(self._seen_states)[self._max_seen // 2:])

        # 새로움 정도 (비슷한 것이 있으면 낮게)
        # 간단히: 완전히 새로우면 1.0
        return 1.0

    def _determine_zone(self, prediction_error: float) -> LearningZone:
        """학습 영역 판단"""
        if prediction_error < self._easy_threshold:
            return LearningZone.TOO_EASY
        elif prediction_error > self._hard_threshold:
            return LearningZone.TOO_HARD
        else:
            return LearningZone.PROXIMAL

    def _compute_intrinsic_reward(
        self,
        prediction_error: float,
        novelty: float,
        learning_progress: float,
        zone: LearningZone,
    ) -> float:
        """
        내재적 보상 계산

        Zone of Proximal Development에서 최대 보상
        """
        # 기본 보상 = 가중 합
        base_reward = (
            self._error_weight * prediction_error +
            self._novelty_weight * novelty +
            self._progress_weight * max(0, learning_progress)  # 진전이 있을 때만
        )

        # 영역에 따른 조정
        if zone == LearningZone.PROXIMAL:
            # 최적 영역 → 보상 유지
            return base_reward
        elif zone == LearningZone.TOO_EASY:
            # 너무 쉬움 → 지루함 (보상 감소)
            return base_reward * 0.3
        else:  # TOO_HARD
            # 너무 어려움 → 좌절 (보상 크게 감소)
            return base_reward * 0.1

    def get_exploration_bonus(self, state: str) -> float:
        """탐험 보너스 (새로운 상태일수록 높음)"""
        state_hash = hashlib.md5(state.encode()).hexdigest()[:16]
        return 1.0 if state_hash not in self._seen_states else 0.0

    def reset_progress(self, task_type: str = None) -> None:
        """학습 진전 리셋"""
        if task_type:
            if task_type in self._progress_trackers:
                del self._progress_trackers[task_type]
        else:
            self._progress_trackers.clear()

    def get_stats(self) -> dict:
        """통계"""
        return {
            "seen_states": len(self._seen_states),
            "task_types": list(self._progress_trackers.keys()),
            "progress_by_task": {
                k: v.get_progress()
                for k, v in self._progress_trackers.items()
            },
        }

    def __repr__(self) -> str:
        return f"CuriosityEngine(seen={len(self._seen_states)}, tasks={len(self._progress_trackers)})"
