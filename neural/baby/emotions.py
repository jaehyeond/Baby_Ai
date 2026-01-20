"""
EmotionalCore - 감정 시스템

아기 AI의 감정 핵심
- 4가지 기본 감정: 호기심, 기쁨, 두려움, 놀람
- 감정이 행동과 학습에 영향
- 감정 기억으로 중요한 경험 필터링

뇌 영역 매핑:
- 편도체 (Amygdala): 감정 처리, 두려움
- 측좌핵 (Nucleus Accumbens): 보상, 기쁨
- 전대상피질 (ACC): 갈등 모니터링
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from datetime import datetime
import math


class EmotionType(Enum):
    """기본 감정 유형"""
    CURIOSITY = "curiosity"      # 호기심 - 탐험 동기
    JOY = "joy"                  # 기쁨 - 성공 보상
    FEAR = "fear"                # 두려움 - 위험 회피
    SURPRISE = "surprise"        # 놀람 - 예측 오류
    FRUSTRATION = "frustration"  # 좌절 - 반복 실패
    BOREDOM = "boredom"          # 지루함 - 너무 쉬움


@dataclass
class Emotion:
    """개별 감정"""
    emotion_type: EmotionType
    intensity: float = 0.5      # 0.0 ~ 1.0
    decay_rate: float = 0.1     # 시간에 따른 감소율
    last_update: datetime = field(default_factory=datetime.now)

    def increase(self, amount: float) -> None:
        """감정 강도 증가"""
        self.intensity = min(1.0, self.intensity + amount)
        self.last_update = datetime.now()

    def decrease(self, amount: float) -> None:
        """감정 강도 감소"""
        self.intensity = max(0.0, self.intensity - amount)
        self.last_update = datetime.now()

    def decay(self) -> None:
        """시간에 따른 자연 감소 (평균으로 회귀)"""
        # 0.5 (중립)으로 회귀
        if self.intensity > 0.5:
            self.intensity = max(0.5, self.intensity - self.decay_rate)
        elif self.intensity < 0.5:
            self.intensity = min(0.5, self.intensity + self.decay_rate)

    @property
    def is_high(self) -> bool:
        """높은 강도인지"""
        return self.intensity > 0.7

    @property
    def is_low(self) -> bool:
        """낮은 강도인지"""
        return self.intensity < 0.3


@dataclass
class EmotionalState:
    """현재 감정 상태 스냅샷"""
    curiosity: float
    joy: float
    fear: float
    surprise: float
    frustration: float
    boredom: float
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def dominant_emotion(self) -> EmotionType:
        """가장 강한 감정"""
        emotions = {
            EmotionType.CURIOSITY: self.curiosity,
            EmotionType.JOY: self.joy,
            EmotionType.FEAR: self.fear,
            EmotionType.SURPRISE: self.surprise,
            EmotionType.FRUSTRATION: self.frustration,
            EmotionType.BOREDOM: self.boredom,
        }
        return max(emotions, key=emotions.get)

    @property
    def valence(self) -> float:
        """감정가 (긍정/부정): -1.0 ~ 1.0"""
        positive = (self.curiosity + self.joy) / 2
        negative = (self.fear + self.frustration) / 2
        return positive - negative

    @property
    def arousal(self) -> float:
        """각성 수준: 0.0 ~ 1.0"""
        high_arousal = (self.curiosity + self.surprise + self.fear) / 3
        low_arousal = self.boredom
        return high_arousal - low_arousal * 0.5

    def to_dict(self) -> dict:
        """딕셔너리 변환"""
        return {
            "curiosity": self.curiosity,
            "joy": self.joy,
            "fear": self.fear,
            "surprise": self.surprise,
            "frustration": self.frustration,
            "boredom": self.boredom,
            "dominant": self.dominant_emotion.value,
            "valence": self.valence,
            "arousal": self.arousal,
        }


class EmotionalCore:
    """
    감정 핵심 시스템

    아기 AI의 감정을 관리하고 행동에 영향을 줌
    - 경험에 따라 감정 업데이트
    - 감정이 의사결정에 영향
    - 감정 기억으로 중요 경험 필터링
    """

    def __init__(self):
        # 기본 감정 초기화
        self._emotions: dict[EmotionType, Emotion] = {
            EmotionType.CURIOSITY: Emotion(EmotionType.CURIOSITY, intensity=0.8),  # 아기는 호기심 높게 시작
            EmotionType.JOY: Emotion(EmotionType.JOY, intensity=0.5),
            EmotionType.FEAR: Emotion(EmotionType.FEAR, intensity=0.1),  # 두려움 낮게 시작
            EmotionType.SURPRISE: Emotion(EmotionType.SURPRISE, intensity=0.3),
            EmotionType.FRUSTRATION: Emotion(EmotionType.FRUSTRATION, intensity=0.0),
            EmotionType.BOREDOM: Emotion(EmotionType.BOREDOM, intensity=0.0),
        }

        # 감정 이력
        self._history: list[EmotionalState] = []
        self._max_history = 100

    def get_state(self) -> EmotionalState:
        """현재 감정 상태"""
        return EmotionalState(
            curiosity=self._emotions[EmotionType.CURIOSITY].intensity,
            joy=self._emotions[EmotionType.JOY].intensity,
            fear=self._emotions[EmotionType.FEAR].intensity,
            surprise=self._emotions[EmotionType.SURPRISE].intensity,
            frustration=self._emotions[EmotionType.FRUSTRATION].intensity,
            boredom=self._emotions[EmotionType.BOREDOM].intensity,
        )

    def get_emotion(self, emotion_type: EmotionType) -> float:
        """특정 감정 강도 조회"""
        return self._emotions[emotion_type].intensity

    # === 이벤트 핸들러 ===

    def on_success(self, magnitude: float = 0.3) -> None:
        """성공 시 감정 반응"""
        self._emotions[EmotionType.JOY].increase(magnitude)
        self._emotions[EmotionType.FEAR].decrease(magnitude * 0.5)
        self._emotions[EmotionType.FRUSTRATION].decrease(magnitude)
        self._emotions[EmotionType.CURIOSITY].increase(magnitude * 0.2)  # 성공하면 더 탐험하고 싶음
        self._record_state()

    def on_failure(self, magnitude: float = 0.3) -> None:
        """실패 시 감정 반응"""
        self._emotions[EmotionType.FRUSTRATION].increase(magnitude)
        self._emotions[EmotionType.JOY].decrease(magnitude * 0.5)

        # 반복 실패 시 두려움 증가
        if self._emotions[EmotionType.FRUSTRATION].is_high:
            self._emotions[EmotionType.FEAR].increase(magnitude * 0.3)
            self._emotions[EmotionType.CURIOSITY].decrease(magnitude * 0.2)

        self._record_state()

    def on_novelty(self, novelty_score: float) -> None:
        """새로운 것 발견 시"""
        # 놀람 = 예측 오류
        self._emotions[EmotionType.SURPRISE].intensity = novelty_score

        # 적당한 새로움 → 호기심 증가
        if 0.3 < novelty_score < 0.8:
            self._emotions[EmotionType.CURIOSITY].increase(novelty_score * 0.3)
            self._emotions[EmotionType.BOREDOM].decrease(0.2)
        # 너무 새로움 → 약간의 두려움
        elif novelty_score > 0.8:
            self._emotions[EmotionType.FEAR].increase(0.1)

        self._record_state()

    def on_repetition(self) -> None:
        """반복/지루함"""
        self._emotions[EmotionType.BOREDOM].increase(0.1)
        self._emotions[EmotionType.CURIOSITY].decrease(0.05)
        self._record_state()

    def on_prediction_error(self, error_magnitude: float) -> None:
        """예측 오류 발생 시"""
        # 예측 오류 = 학습 기회
        self._emotions[EmotionType.SURPRISE].intensity = error_magnitude

        # 적당한 오류 → 흥미로움
        if 0.2 < error_magnitude < 0.7:
            self._emotions[EmotionType.CURIOSITY].increase(error_magnitude * 0.2)
        # 큰 오류 → 혼란
        elif error_magnitude > 0.7:
            self._emotions[EmotionType.FRUSTRATION].increase(0.1)

        self._record_state()

    # === 행동 조절 ===

    def modulate_action(self, base_action: str) -> str:
        """감정에 따라 행동 조절"""
        state = self.get_state()

        # 두려움이 높으면 → 조심스럽게
        if state.fear > 0.7:
            return f"cautious_{base_action}"

        # 호기심이 높으면 → 탐험적으로
        if state.curiosity > 0.8:
            return f"explore_{base_action}"

        # 지루하면 → 변형 시도
        if state.boredom > 0.6:
            return f"vary_{base_action}"

        # 좌절하면 → 다른 방법 시도
        if state.frustration > 0.6:
            return f"alternative_{base_action}"

        return base_action

    def get_exploration_rate(self) -> float:
        """탐험 비율 (epsilon-greedy에서 epsilon)"""
        state = self.get_state()

        # 호기심 높음 + 두려움 낮음 → 탐험 많이
        exploration = state.curiosity * (1 - state.fear * 0.5)

        # 지루함 높으면 → 탐험 증가
        if state.boredom > 0.5:
            exploration += 0.2

        return min(1.0, exploration)

    def get_memory_weight(self) -> float:
        """경험의 기억 가중치 (감정이 강할수록 잘 기억)"""
        state = self.get_state()

        # 감정 강도의 평균
        emotional_intensity = (
            abs(state.curiosity - 0.5) +
            abs(state.joy - 0.5) +
            abs(state.fear - 0.5) +
            abs(state.surprise - 0.5)
        ) / 2  # 최대 2.0을 1.0으로

        return min(1.0, 0.3 + emotional_intensity * 0.7)

    # === 시간 경과 ===

    def tick(self) -> None:
        """시간 경과 처리 (감정 감쇠)"""
        for emotion in self._emotions.values():
            emotion.decay()

    def reset(self) -> None:
        """초기 상태로 리셋"""
        self._emotions[EmotionType.CURIOSITY].intensity = 0.8
        self._emotions[EmotionType.JOY].intensity = 0.5
        self._emotions[EmotionType.FEAR].intensity = 0.1
        self._emotions[EmotionType.SURPRISE].intensity = 0.3
        self._emotions[EmotionType.FRUSTRATION].intensity = 0.0
        self._emotions[EmotionType.BOREDOM].intensity = 0.0

    # === 내부 메서드 ===

    def _record_state(self) -> None:
        """상태 기록"""
        self._history.append(self.get_state())
        if len(self._history) > self._max_history:
            self._history.pop(0)

    def get_history(self, n: int = 10) -> list[EmotionalState]:
        """최근 감정 이력"""
        return self._history[-n:]

    def __repr__(self) -> str:
        state = self.get_state()
        return (
            f"EmotionalCore("
            f"curiosity={state.curiosity:.2f}, "
            f"joy={state.joy:.2f}, "
            f"fear={state.fear:.2f}, "
            f"dominant={state.dominant_emotion.value})"
        )
