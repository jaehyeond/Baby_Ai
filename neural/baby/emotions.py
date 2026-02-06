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


# 복합 감정 정의 (기본 감정의 조합)
COMPOUND_EMOTIONS = {
    "pride": {
        "description": "자부심 - 성공 후 기쁨",
        "requires": {"joy": 0.6},
        "boosts": {"curiosity": 0.1},
        "conditions": lambda state: state.joy > 0.6 and state.fear < 0.3,
    },
    "anxiety": {
        "description": "불안 - 두려움과 좌절의 결합",
        "requires": {"fear": 0.4, "frustration": 0.4},
        "boosts": {},
        "conditions": lambda state: state.fear > 0.4 and state.frustration > 0.4,
    },
    "wonder": {
        "description": "경이 - 호기심과 놀람의 결합",
        "requires": {"curiosity": 0.5, "surprise": 0.4},
        "boosts": {"curiosity": 0.15},
        "conditions": lambda state: state.curiosity > 0.5 and state.surprise > 0.4,
    },
    "melancholy": {
        "description": "우울 - 지루함에 좌절이 더해짐",
        "requires": {"boredom": 0.5},
        "boosts": {},
        "conditions": lambda state: state.boredom > 0.5 and state.frustration > 0.3,
    },
    "determination": {
        "description": "결의 - 좌절을 딛고 호기심으로",
        "requires": {"frustration": 0.4, "curiosity": 0.5},
        "boosts": {"curiosity": 0.1},
        "conditions": lambda state: state.frustration > 0.4 and state.curiosity > 0.5 and state.fear < 0.4,
    },
}


# 감정 → 목표 타입 매핑
EMOTION_GOAL_MAP = {
    "pride": "skill_deepening",          # 잘하는 것 더 깊이 학습
    "anxiety": "safety_seeking",          # 안전한 영역에서 연습
    "wonder": "exploration",              # 새로운 영역 탐색
    "melancholy": "social_connection",    # 사용자와 대화 추구
    "determination": "challenge_seeking",  # 어려운 과제 도전
    # 기본 감정 매핑
    "curiosity": "exploration",
    "joy": "skill_deepening",
    "fear": "safety_seeking",
    "surprise": "exploration",
    "frustration": "challenge_seeking",
    "boredom": "novelty_seeking",
}


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

    def detect_compound_emotion(self) -> Optional[str]:
        """
        현재 감정 상태에서 복합 감정 감지

        Returns:
            Optional[str]: 감지된 복합 감정 이름, 없으면 None
        """
        for name, config in COMPOUND_EMOTIONS.items():
            if config["conditions"](self):
                return name
        return None

    def to_dict(self) -> dict:
        """딕셔너리 변환 (compound emotion 포함)"""
        compound = self.detect_compound_emotion()
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
            "compound_emotion": compound,
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

    # === Phase 3: 감정 기반 학습 조절 ===

    def get_learning_rate_modifier(self) -> float:
        """
        감정 기반 학습률 조절자

        - 기쁨(Joy) 높음 → 학습률 증가 (강화 학습)
        - 호기심(Curiosity) 높음 → 학습률 약간 증가
        - 두려움(Fear) 높음 → 학습률 감소 (보수적)
        - 좌절(Frustration) 높음 → 학습률 약간 증가 (다른 방법 시도)
        - 지루함(Boredom) 높음 → 학습률 감소 (주의력 저하)

        Returns:
            float: 0.5 ~ 1.5 범위의 학습률 조절자
        """
        state = self.get_state()

        # 기본 학습률
        modifier = 1.0

        # 긍정적 감정 → 학습 촉진
        if state.joy > 0.6:
            modifier += (state.joy - 0.5) * 0.5  # 최대 +0.25

        if state.curiosity > 0.6:
            modifier += (state.curiosity - 0.5) * 0.3  # 최대 +0.15

        # 부정적 감정 → 학습 억제 또는 전략 변경
        if state.fear > 0.6:
            modifier -= (state.fear - 0.5) * 0.4  # 최대 -0.2 (보수적)

        if state.boredom > 0.5:
            modifier -= (state.boredom - 0.5) * 0.3  # 최대 -0.15

        # 좌절은 특별: 약간 증가 (다른 접근법 탐색)
        if state.frustration > 0.5:
            modifier += (state.frustration - 0.5) * 0.2  # 최대 +0.1

        return max(0.5, min(1.5, modifier))

    def get_strategy_change_probability(self) -> float:
        """
        전략 변경 확률

        좌절이 높으면 현재 전략을 버리고 새로운 접근법 시도

        Returns:
            float: 0.0 ~ 1.0 전략 변경 확률
        """
        state = self.get_state()

        # 기본 확률
        prob = 0.1

        # 좌절 → 전략 변경 촉진
        if state.frustration > 0.5:
            prob += (state.frustration - 0.5) * 0.8  # 최대 +0.4

        # 지루함 → 변화 추구
        if state.boredom > 0.5:
            prob += (state.boredom - 0.5) * 0.6  # 최대 +0.3

        # 호기심 → 새로운 것 시도
        if state.curiosity > 0.7:
            prob += (state.curiosity - 0.7) * 0.5  # 최대 +0.15

        # 기쁨이 높으면 현재 전략 유지
        if state.joy > 0.7:
            prob -= 0.2

        return max(0.0, min(1.0, prob))

    def get_risk_tolerance(self) -> float:
        """
        위험 감수 수준

        - 두려움 높음 → 보수적 (낮은 위험 감수)
        - 호기심 높음 → 적극적 (높은 위험 감수)
        - 기쁨 높음 → 약간 적극적

        Returns:
            float: 0.0 (매우 보수적) ~ 1.0 (매우 적극적)
        """
        state = self.get_state()

        # 기본 위험 감수
        tolerance = 0.5

        # 두려움 → 위험 회피
        if state.fear > 0.3:
            tolerance -= (state.fear - 0.3) * 0.7  # 최대 -0.49

        # 호기심 → 위험 감수
        if state.curiosity > 0.5:
            tolerance += (state.curiosity - 0.5) * 0.5  # 최대 +0.25

        # 기쁨 → 약간 적극적
        if state.joy > 0.6:
            tolerance += (state.joy - 0.6) * 0.3  # 최대 +0.12

        # 좌절 → 더 과감해짐 (절박함)
        if state.frustration > 0.6:
            tolerance += (state.frustration - 0.6) * 0.4  # 최대 +0.16

        return max(0.0, min(1.0, tolerance))

    def should_avoid_pattern(self, pattern_id: str, failure_count: int) -> bool:
        """
        특정 패턴 회피 여부

        두려움이 높고 해당 패턴에서 실패가 많으면 회피

        Args:
            pattern_id: 패턴 식별자
            failure_count: 해당 패턴 실패 횟수

        Returns:
            bool: 회피 여부
        """
        state = self.get_state()

        # 두려움 기반 회피 임계값
        fear_threshold = 0.5 - (failure_count * 0.1)  # 실패 많을수록 임계값 낮아짐

        return state.fear > max(0.2, fear_threshold)

    def get_attention_focus(self) -> dict:
        """
        감정 기반 주의 집중 영역

        Returns:
            dict: 주의 집중 가중치
        """
        state = self.get_state()

        return {
            "exploration": state.curiosity,  # 새로운 것 탐색
            "exploitation": state.joy * 0.8,  # 알려진 성공 패턴 활용
            "avoidance": state.fear,  # 위험 회피
            "change": state.frustration + state.boredom * 0.5,  # 변화 추구
            "detail": 1.0 - state.boredom,  # 세부사항 주의 (지루하면 감소)
        }

    def get_emotional_influence(self) -> dict:
        """
        현재 감정이 행동에 미치는 영향 요약

        Returns:
            dict: 각종 영향 지표
        """
        return {
            "learning_rate_modifier": self.get_learning_rate_modifier(),
            "exploration_rate": self.get_exploration_rate(),
            "memory_weight": self.get_memory_weight(),
            "strategy_change_prob": self.get_strategy_change_probability(),
            "risk_tolerance": self.get_risk_tolerance(),
            "attention_focus": self.get_attention_focus(),
        }

    def detect_compound_emotion(self) -> Optional[str]:
        """현재 감정 상태에서 복합 감정 감지"""
        return self.get_state().detect_compound_emotion()

    def suggest_goal_from_emotion(self) -> Optional[dict]:
        """
        감정 상태 기반 목표 타입 제안

        Returns:
            Optional[dict]: {goal_type, emotional_basis, confidence}
        """
        state = self.get_state()
        compound = state.detect_compound_emotion()

        # 복합 감정 우선
        if compound and compound in EMOTION_GOAL_MAP:
            return {
                "goal_type": EMOTION_GOAL_MAP[compound],
                "emotional_basis": {
                    "dominant": state.dominant_emotion.value,
                    "compound": compound,
                    "valence": state.valence,
                    "arousal": state.arousal,
                },
                "confidence": 0.7,
                "reasoning": COMPOUND_EMOTIONS[compound]["description"],
            }

        # 기본 감정 기반
        dominant = state.dominant_emotion.value
        if dominant in EMOTION_GOAL_MAP:
            return {
                "goal_type": EMOTION_GOAL_MAP[dominant],
                "emotional_basis": {
                    "dominant": dominant,
                    "compound": None,
                    "valence": state.valence,
                    "arousal": state.arousal,
                },
                "confidence": 0.5,
                "reasoning": f"주요 감정 '{dominant}' 기반 제안",
            }

        return None

    def __repr__(self) -> str:
        state = self.get_state()
        return (
            f"EmotionalCore("
            f"curiosity={state.curiosity:.2f}, "
            f"joy={state.joy:.2f}, "
            f"fear={state.fear:.2f}, "
            f"dominant={state.dominant_emotion.value})"
        )
