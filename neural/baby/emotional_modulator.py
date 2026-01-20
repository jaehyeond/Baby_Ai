"""
EmotionalLearningModulator - 감정 기반 학습/행동 조절기

Phase 3: 감정이 실제로 학습과 행동에 영향을 미치도록 함

주요 기능:
1. 학습률 동적 조절
2. 전략 선택 및 변경
3. 패턴 회피/강화
4. 탐험/활용 균형 조절

뇌 영역 매핑:
- 전두엽 (Prefrontal Cortex): 의사결정, 계획
- 기저핵 (Basal Ganglia): 강화 학습, 습관 형성
- 해마 (Hippocampus): 기억 형성 조절
"""

from dataclasses import dataclass, field
from typing import Optional, Any
from datetime import datetime
from enum import Enum
import random

from .emotions import EmotionalCore, EmotionalState


class Strategy(Enum):
    """학습/행동 전략"""
    EXPLOIT = "exploit"          # 알려진 성공 패턴 활용
    EXPLORE = "explore"          # 새로운 방법 탐색
    CAUTIOUS = "cautious"        # 조심스러운 접근
    ALTERNATIVE = "alternative"  # 대안적 접근
    CREATIVE = "creative"        # 창의적 시도


@dataclass
class StrategyDecision:
    """전략 결정 결과"""
    strategy: Strategy
    confidence: float           # 이 전략에 대한 확신
    reasoning: str              # 결정 이유
    parameters: dict = field(default_factory=dict)  # 전략 관련 파라미터


@dataclass
class LearningAdjustment:
    """학습 조절 결과"""
    base_learning_rate: float
    adjusted_learning_rate: float
    modifier: float
    emotional_factors: dict      # 어떤 감정이 영향을 미쳤는지


@dataclass
class PatternEvaluation:
    """패턴 평가 결과"""
    pattern_id: str
    should_use: bool
    confidence: float
    risk_level: float
    emotional_bias: str          # 감정이 어떤 편향을 주었는지


class EmotionalLearningModulator:
    """
    감정 기반 학습 조절기

    감정 상태를 바탕으로 학습과 행동을 실시간 조절
    """

    def __init__(self, emotional_core: EmotionalCore, verbose: bool = False):
        self._emotions = emotional_core
        self._verbose = verbose

        # 패턴별 성공/실패 기록
        self._pattern_history: dict[str, dict] = {}

        # 전략 이력
        self._strategy_history: list[StrategyDecision] = []
        self._max_history = 50

        # 학습 이력
        self._learning_history: list[LearningAdjustment] = []

    # === 학습률 조절 ===

    def adjust_learning_rate(self, base_rate: float = 0.1) -> LearningAdjustment:
        """
        감정 기반 학습률 조절

        Args:
            base_rate: 기본 학습률

        Returns:
            LearningAdjustment: 조절된 학습률 정보
        """
        modifier = self._emotions.get_learning_rate_modifier()
        adjusted_rate = base_rate * modifier

        state = self._emotions.get_state()
        factors = {}

        # 어떤 감정이 영향을 미쳤는지 기록
        if state.joy > 0.6:
            factors["joy"] = f"+{(state.joy - 0.5) * 0.5:.2f} (강화 학습)"
        if state.curiosity > 0.6:
            factors["curiosity"] = f"+{(state.curiosity - 0.5) * 0.3:.2f} (탐구 동기)"
        if state.fear > 0.6:
            factors["fear"] = f"-{(state.fear - 0.5) * 0.4:.2f} (보수적 학습)"
        if state.frustration > 0.5:
            factors["frustration"] = f"+{(state.frustration - 0.5) * 0.2:.2f} (전략 탐색)"
        if state.boredom > 0.5:
            factors["boredom"] = f"-{(state.boredom - 0.5) * 0.3:.2f} (주의력 저하)"

        adjustment = LearningAdjustment(
            base_learning_rate=base_rate,
            adjusted_learning_rate=adjusted_rate,
            modifier=modifier,
            emotional_factors=factors,
        )

        self._learning_history.append(adjustment)
        if len(self._learning_history) > self._max_history:
            self._learning_history.pop(0)

        if self._verbose:
            print(f"[MODULATOR] Learning rate: {base_rate:.3f} → {adjusted_rate:.3f} (x{modifier:.2f})")
            for emotion, effect in factors.items():
                print(f"  - {emotion}: {effect}")

        return adjustment

    # === 전략 선택 ===

    def select_strategy(
        self,
        available_strategies: list[Strategy] = None,
        context: dict = None,
    ) -> StrategyDecision:
        """
        감정 기반 전략 선택

        Args:
            available_strategies: 사용 가능한 전략들 (기본: 모든 전략)
            context: 추가 컨텍스트 (과거 실패 횟수 등)

        Returns:
            StrategyDecision: 선택된 전략
        """
        if available_strategies is None:
            available_strategies = list(Strategy)

        context = context or {}
        state = self._emotions.get_state()

        # 각 전략의 점수 계산
        scores: dict[Strategy, float] = {}

        for strategy in available_strategies:
            scores[strategy] = self._calculate_strategy_score(strategy, state, context)

        # 전략 변경 확률 고려
        strategy_change_prob = self._emotions.get_strategy_change_probability()

        # 이전 전략이 있고, 변경 확률이 낮으면 이전 전략 유지 경향
        if self._strategy_history and random.random() > strategy_change_prob:
            last_strategy = self._strategy_history[-1].strategy
            if last_strategy in scores:
                scores[last_strategy] *= 1.3  # 기존 전략 선호

        # 최고 점수 전략 선택
        selected = max(scores, key=scores.get)
        confidence = scores[selected] / sum(scores.values()) if scores.values() else 0.5

        # 결정 이유 생성
        reasoning = self._generate_strategy_reasoning(selected, state, context)

        # 전략별 파라미터 설정
        parameters = self._get_strategy_parameters(selected, state)

        decision = StrategyDecision(
            strategy=selected,
            confidence=confidence,
            reasoning=reasoning,
            parameters=parameters,
        )

        self._strategy_history.append(decision)
        if len(self._strategy_history) > self._max_history:
            self._strategy_history.pop(0)

        if self._verbose:
            print(f"[MODULATOR] Strategy: {selected.value} (confidence: {confidence:.2f})")
            print(f"  Reason: {reasoning}")

        return decision

    def _calculate_strategy_score(
        self,
        strategy: Strategy,
        state: EmotionalState,
        context: dict,
    ) -> float:
        """전략별 점수 계산"""
        score = 1.0  # 기본 점수
        prev_failures = context.get("previous_failures", 0)

        if strategy == Strategy.EXPLOIT:
            # 기쁨 높으면 → 성공 패턴 활용
            score += state.joy * 0.5
            # 두려움 높으면 → 안전한 방법 선호
            score += state.fear * 0.3
            # 실패 많으면 감소
            score -= prev_failures * 0.2

        elif strategy == Strategy.EXPLORE:
            # 호기심 높으면 → 탐험
            score += state.curiosity * 0.6
            # 지루함 높으면 → 새로운 것 시도
            score += state.boredom * 0.4
            # 두려움 높으면 → 탐험 회피
            score -= state.fear * 0.3

        elif strategy == Strategy.CAUTIOUS:
            # 두려움 높으면 → 조심
            score += state.fear * 0.7
            # 실패 많으면 조심
            score += prev_failures * 0.3
            # 호기심 높으면 감소
            score -= state.curiosity * 0.2

        elif strategy == Strategy.ALTERNATIVE:
            # 좌절 높으면 → 대안 찾기
            score += state.frustration * 0.8
            # 실패 많으면 대안 필요
            score += prev_failures * 0.4
            # 기쁨 높으면 굳이 바꿀 필요 없음
            score -= state.joy * 0.3

        elif strategy == Strategy.CREATIVE:
            # 호기심 + 약간의 좌절 → 창의적 시도
            score += state.curiosity * 0.4
            score += state.frustration * 0.3
            score += state.surprise * 0.3
            # 두려움 높으면 위험한 시도 회피
            score -= state.fear * 0.4

        return max(0.1, score)

    def _generate_strategy_reasoning(
        self,
        strategy: Strategy,
        state: EmotionalState,
        context: dict,
    ) -> str:
        """전략 선택 이유 생성"""
        prev_failures = context.get("previous_failures", 0)

        reasons = []

        if strategy == Strategy.EXPLOIT:
            if state.joy > 0.6:
                reasons.append(f"성공 경험의 기쁨(joy={state.joy:.2f})이 높아 검증된 방법 활용")
            if state.fear > 0.5:
                reasons.append(f"두려움(fear={state.fear:.2f})으로 안전한 접근 선호")

        elif strategy == Strategy.EXPLORE:
            if state.curiosity > 0.6:
                reasons.append(f"호기심(curiosity={state.curiosity:.2f})이 높아 새로운 방법 탐색")
            if state.boredom > 0.5:
                reasons.append(f"지루함(boredom={state.boredom:.2f})으로 변화 추구")

        elif strategy == Strategy.CAUTIOUS:
            if state.fear > 0.5:
                reasons.append(f"두려움(fear={state.fear:.2f})이 높아 조심스럽게 접근")
            if prev_failures > 0:
                reasons.append(f"이전 {prev_failures}번 실패로 신중한 접근")

        elif strategy == Strategy.ALTERNATIVE:
            if state.frustration > 0.5:
                reasons.append(f"좌절(frustration={state.frustration:.2f})로 다른 방법 모색")
            if prev_failures > 1:
                reasons.append(f"반복 실패({prev_failures}번)로 대안 전략 필요")

        elif strategy == Strategy.CREATIVE:
            if state.curiosity > 0.5 and state.frustration > 0.3:
                reasons.append("호기심과 좌절이 결합하여 창의적 접근 시도")

        return "; ".join(reasons) if reasons else f"{strategy.value} 전략 선택"

    def _get_strategy_parameters(self, strategy: Strategy, state: EmotionalState) -> dict:
        """전략별 파라미터 설정"""
        risk_tolerance = self._emotions.get_risk_tolerance()
        exploration_rate = self._emotions.get_exploration_rate()

        params = {
            "risk_tolerance": risk_tolerance,
            "exploration_rate": exploration_rate,
        }

        if strategy == Strategy.EXPLOIT:
            params["use_cached_solutions"] = True
            params["variation_level"] = 0.1

        elif strategy == Strategy.EXPLORE:
            params["use_cached_solutions"] = False
            params["variation_level"] = 0.7
            params["try_new_approaches"] = True

        elif strategy == Strategy.CAUTIOUS:
            params["validation_level"] = "high"
            params["step_by_step"] = True
            params["rollback_enabled"] = True

        elif strategy == Strategy.ALTERNATIVE:
            params["avoid_previous_patterns"] = True
            params["seek_different_approach"] = True

        elif strategy == Strategy.CREATIVE:
            params["combination_allowed"] = True
            params["unconventional_allowed"] = True

        return params

    # === 패턴 평가 ===

    def evaluate_pattern(
        self,
        pattern_id: str,
        pattern_success_rate: float = 0.5,
        pattern_risk_level: float = 0.5,
    ) -> PatternEvaluation:
        """
        특정 패턴 사용 여부 평가

        Args:
            pattern_id: 패턴 식별자
            pattern_success_rate: 이 패턴의 성공률
            pattern_risk_level: 이 패턴의 위험 수준

        Returns:
            PatternEvaluation: 패턴 사용 권장 여부
        """
        state = self._emotions.get_state()
        risk_tolerance = self._emotions.get_risk_tolerance()

        # 패턴 이력 확인
        history = self._pattern_history.get(pattern_id, {"success": 0, "failure": 0})
        failure_count = history.get("failure", 0)

        # 두려움 기반 회피 체크
        should_avoid = self._emotions.should_avoid_pattern(pattern_id, failure_count)

        # 위험 수준 vs 위험 감수 수준
        risk_acceptable = pattern_risk_level <= risk_tolerance + 0.1

        # 최종 결정
        should_use = not should_avoid and risk_acceptable

        # 감정 편향 분석
        bias = "neutral"
        if state.fear > 0.6:
            bias = "risk_averse"
        elif state.curiosity > 0.7:
            bias = "risk_seeking"
        elif state.joy > 0.7 and pattern_success_rate > 0.7:
            bias = "success_seeking"

        # 신뢰도 계산
        confidence = 0.5
        if should_use:
            confidence = (pattern_success_rate + risk_tolerance) / 2
        else:
            confidence = ((1 - pattern_success_rate) + state.fear) / 2

        evaluation = PatternEvaluation(
            pattern_id=pattern_id,
            should_use=should_use,
            confidence=confidence,
            risk_level=pattern_risk_level,
            emotional_bias=bias,
        )

        if self._verbose:
            print(f"[MODULATOR] Pattern '{pattern_id}': {'USE' if should_use else 'AVOID'}")
            print(f"  Risk: {pattern_risk_level:.2f}, Tolerance: {risk_tolerance:.2f}")
            print(f"  Emotional bias: {bias}")

        return evaluation

    def record_pattern_outcome(
        self,
        pattern_id: str,
        success: bool,
    ) -> None:
        """패턴 사용 결과 기록"""
        if pattern_id not in self._pattern_history:
            self._pattern_history[pattern_id] = {"success": 0, "failure": 0}

        if success:
            self._pattern_history[pattern_id]["success"] += 1
        else:
            self._pattern_history[pattern_id]["failure"] += 1

    # === 탐험/활용 균형 ===

    def get_exploration_decision(self, known_options: int, new_options: int) -> dict:
        """
        탐험 vs 활용 결정

        Args:
            known_options: 알려진 옵션 수
            new_options: 새로운 옵션 수

        Returns:
            dict: 탐험/활용 결정 정보
        """
        state = self._emotions.get_state()
        exploration_rate = self._emotions.get_exploration_rate()

        # 탐험 결정
        should_explore = random.random() < exploration_rate

        # 감정 기반 조정
        if state.boredom > 0.6:
            should_explore = True  # 지루하면 강제 탐험
        elif state.fear > 0.7 and known_options > 0:
            should_explore = False  # 두려우면 안전한 선택

        decision = {
            "should_explore": should_explore,
            "exploration_rate": exploration_rate,
            "reasoning": "",
            "known_options": known_options,
            "new_options": new_options,
        }

        if should_explore:
            decision["reasoning"] = f"탐험 선택 (exploration_rate={exploration_rate:.2f})"
            if state.curiosity > 0.7:
                decision["reasoning"] += f", 높은 호기심({state.curiosity:.2f})"
        else:
            decision["reasoning"] = f"활용 선택 (exploitation)"
            if state.joy > 0.6:
                decision["reasoning"] += f", 성공 패턴 활용({state.joy:.2f})"

        if self._verbose:
            print(f"[MODULATOR] {'EXPLORE' if should_explore else 'EXPLOIT'}")
            print(f"  {decision['reasoning']}")

        return decision

    # === 통계 ===

    def get_stats(self) -> dict:
        """조절기 통계"""
        recent_learning = self._learning_history[-10:] if self._learning_history else []
        recent_strategies = self._strategy_history[-10:] if self._strategy_history else []

        avg_modifier = (
            sum(adj.modifier for adj in recent_learning) / len(recent_learning)
            if recent_learning else 1.0
        )

        strategy_counts = {}
        for decision in recent_strategies:
            strategy_counts[decision.strategy.value] = (
                strategy_counts.get(decision.strategy.value, 0) + 1
            )

        return {
            "total_adjustments": len(self._learning_history),
            "total_strategy_decisions": len(self._strategy_history),
            "avg_learning_modifier": avg_modifier,
            "recent_strategies": strategy_counts,
            "tracked_patterns": len(self._pattern_history),
            "current_influence": self._emotions.get_emotional_influence(),
        }

    def __repr__(self) -> str:
        stats = self.get_stats()
        return (
            f"EmotionalLearningModulator("
            f"adjustments={stats['total_adjustments']}, "
            f"avg_modifier={stats['avg_learning_modifier']:.2f})"
        )
