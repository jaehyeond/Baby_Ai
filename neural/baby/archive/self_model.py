"""
SelfModel - 자아 모델

아기 AI의 자기 인식:
- 나는 무엇을 할 수 있는가? (능력)
- 나는 무엇을 좋아하는가? (선호)
- 나는 무엇을 못하는가? (한계)
- 나는 어떤 상태인가? (내적 상태)

자기 성찰:
- 성공/실패 분석
- 패턴 인식
- 개선점 도출
"""

from dataclasses import dataclass, field
from typing import Optional, Any
from datetime import datetime
from enum import Enum


@dataclass
class Capability:
    """능력"""
    name: str
    description: str
    confidence: float = 0.5     # 0.0 ~ 1.0
    success_count: int = 0
    failure_count: int = 0
    last_used: Optional[datetime] = None

    @property
    def success_rate(self) -> float:
        total = self.success_count + self.failure_count
        return self.success_count / total if total > 0 else 0.5

    def update(self, success: bool) -> None:
        """능력 업데이트"""
        if success:
            self.success_count += 1
            self.confidence = min(1.0, self.confidence + 0.05)
        else:
            self.failure_count += 1
            self.confidence = max(0.0, self.confidence - 0.03)
        self.last_used = datetime.now()


@dataclass
class Preference:
    """선호"""
    name: str
    category: str               # task_type, approach, style
    strength: float = 0.5       # -1.0 (싫음) ~ 1.0 (좋아함)
    experience_count: int = 0

    def update(self, outcome_positive: bool) -> None:
        """선호 업데이트"""
        self.experience_count += 1
        if outcome_positive:
            self.strength = min(1.0, self.strength + 0.1)
        else:
            self.strength = max(-1.0, self.strength - 0.05)

    @property
    def is_liked(self) -> bool:
        return self.strength > 0.3

    @property
    def is_disliked(self) -> bool:
        return self.strength < -0.3


class SelfModel:
    """
    자아 모델

    "나"에 대한 이해
    - 능력 추적
    - 선호 형성
    - 한계 인식
    - 자기 성찰
    """

    def __init__(self):
        # 능력 맵
        self._capabilities: dict[str, Capability] = {}

        # 선호 맵
        self._preferences: dict[str, Preference] = {}

        # 알려진 한계
        self._limitations: list[str] = []

        # 성찰 기록
        self._reflections: list[dict] = []
        self._max_reflections = 50

        # 자기 인식 레벨 (0.0 ~ 1.0)
        self._self_awareness = 0.1  # 낮게 시작

    # === 능력 관리 ===

    def register_capability(
        self,
        name: str,
        description: str = "",
        initial_confidence: float = 0.5,
    ) -> None:
        """능력 등록"""
        if name not in self._capabilities:
            self._capabilities[name] = Capability(
                name=name,
                description=description,
                confidence=initial_confidence,
            )

    def update_capability(self, name: str, success: bool) -> None:
        """능력 업데이트"""
        if name not in self._capabilities:
            self.register_capability(name)
        self._capabilities[name].update(success)

    def get_capability(self, name: str) -> Optional[Capability]:
        """능력 조회"""
        return self._capabilities.get(name)

    def get_strongest_capabilities(self, n: int = 5) -> list[Capability]:
        """가장 자신있는 능력"""
        sorted_caps = sorted(
            self._capabilities.values(),
            key=lambda c: c.confidence,
            reverse=True
        )
        return sorted_caps[:n]

    def get_weakest_capabilities(self, n: int = 5) -> list[Capability]:
        """가장 약한 능력"""
        sorted_caps = sorted(
            self._capabilities.values(),
            key=lambda c: c.confidence
        )
        return sorted_caps[:n]

    def can_do_confidently(self, capability: str, threshold: float = 0.6) -> bool:
        """자신있게 할 수 있는지"""
        cap = self._capabilities.get(capability)
        return cap is not None and cap.confidence >= threshold

    # === 선호 관리 ===

    def update_preference(
        self,
        name: str,
        category: str,
        positive_outcome: bool,
    ) -> None:
        """선호 업데이트"""
        key = f"{category}:{name}"
        if key not in self._preferences:
            self._preferences[key] = Preference(
                name=name,
                category=category,
            )
        self._preferences[key].update(positive_outcome)

    def get_preferences(self, category: str = None) -> list[Preference]:
        """선호 조회"""
        prefs = list(self._preferences.values())
        if category:
            prefs = [p for p in prefs if p.category == category]
        return sorted(prefs, key=lambda p: p.strength, reverse=True)

    def likes(self, name: str, category: str = None) -> bool:
        """좋아하는지"""
        for key, pref in self._preferences.items():
            if pref.name == name:
                if category is None or pref.category == category:
                    return pref.is_liked
        return False  # 모르면 중립

    def dislikes(self, name: str, category: str = None) -> bool:
        """싫어하는지"""
        for key, pref in self._preferences.items():
            if pref.name == name:
                if category is None or pref.category == category:
                    return pref.is_disliked
        return False

    # === 한계 관리 ===

    def add_limitation(self, limitation: str) -> None:
        """한계 추가"""
        if limitation not in self._limitations:
            self._limitations.append(limitation)

    def remove_limitation(self, limitation: str) -> None:
        """한계 제거 (극복)"""
        if limitation in self._limitations:
            self._limitations.remove(limitation)

    def has_limitation(self, limitation: str) -> bool:
        """특정 한계가 있는지"""
        return limitation in self._limitations

    def get_limitations(self) -> list[str]:
        """모든 한계"""
        return list(self._limitations)

    # === 자기 성찰 ===

    def reflect(
        self,
        experience: dict,
        outcome: str,
        learned: str = "",
    ) -> dict:
        """
        경험에 대한 자기 성찰

        Args:
            experience: 경험 정보
            outcome: 결과 ("success", "failure", "partial")
            learned: 배운 것

        Returns:
            성찰 결과
        """
        reflection = {
            "timestamp": datetime.now().isoformat(),
            "experience_summary": str(experience)[:100],
            "outcome": outcome,
            "learned": learned,
            "self_assessment": self._assess_self(),
        }

        # 자기 인식 레벨 증가
        self._self_awareness = min(1.0, self._self_awareness + 0.01)

        # 성찰 기록
        self._reflections.append(reflection)
        if len(self._reflections) > self._max_reflections:
            self._reflections.pop(0)

        return reflection

    def _assess_self(self) -> dict:
        """자기 평가"""
        strengths = [c.name for c in self.get_strongest_capabilities(3)]
        weaknesses = [c.name for c in self.get_weakest_capabilities(3)]
        liked = [p.name for p in self.get_preferences() if p.is_liked][:3]
        disliked = [p.name for p in self.get_preferences() if p.is_disliked][:3]

        return {
            "strengths": strengths,
            "weaknesses": weaknesses,
            "likes": liked,
            "dislikes": disliked,
            "limitations": self._limitations[:3],
            "self_awareness_level": self._self_awareness,
        }

    def generate_self_description(self) -> str:
        """자기 설명 생성"""
        assessment = self._assess_self()

        parts = ["나는 "]

        # 강점
        if assessment["strengths"]:
            parts.append(f"{', '.join(assessment['strengths'])}을(를) 잘하고, ")

        # 약점
        if assessment["weaknesses"]:
            parts.append(f"{', '.join(assessment['weaknesses'])}은(는) 아직 연습이 필요해. ")

        # 선호
        if assessment["likes"]:
            parts.append(f"{', '.join(assessment['likes'])}을(를) 좋아하고, ")

        if assessment["dislikes"]:
            parts.append(f"{', '.join(assessment['dislikes'])}은(는) 좀 어려워해. ")

        # 한계
        if assessment["limitations"]:
            parts.append(f"아직 {', '.join(assessment['limitations'])}은(는) 못해.")

        return "".join(parts)

    def should_ask_for_help(self, task: str) -> bool:
        """도움을 요청해야 하는지"""
        # 해당 능력의 자신감이 낮으면 도움 요청
        cap = self._capabilities.get(task)
        if cap and cap.confidence < 0.3:
            return True

        # 알려진 한계이면 도움 요청
        for limitation in self._limitations:
            if limitation.lower() in task.lower():
                return True

        return False

    def suggest_approach(self, task: str) -> str:
        """접근 방식 제안"""
        cap = self._capabilities.get(task)

        if cap is None:
            return "explore"  # 새로운 것 → 탐험

        if cap.confidence > 0.7:
            return "confident"  # 자신있음 → 확신 있게

        if cap.confidence > 0.4:
            return "careful"  # 중간 → 조심스럽게

        return "cautious"  # 낮음 → 매우 조심스럽게

    # === 상태 ===

    def get_state(self) -> dict:
        """현재 자아 모델 상태"""
        return {
            "self_awareness": self._self_awareness,
            "capabilities_count": len(self._capabilities),
            "preferences_count": len(self._preferences),
            "limitations_count": len(self._limitations),
            "reflections_count": len(self._reflections),
            "assessment": self._assess_self(),
        }

    def reset(self) -> None:
        """초기화"""
        self._capabilities.clear()
        self._preferences.clear()
        self._limitations.clear()
        self._reflections.clear()
        self._self_awareness = 0.1

    def __repr__(self) -> str:
        return (
            f"SelfModel("
            f"awareness={self._self_awareness:.2f}, "
            f"capabilities={len(self._capabilities)}, "
            f"preferences={len(self._preferences)})"
        )
