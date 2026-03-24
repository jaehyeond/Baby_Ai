"""
DevelopmentStage - 발달 단계

아기 인지 발달 단계 모방:
- NEWBORN (신생아): 반사 반응
- INFANT (영아): 패턴 인식
- BABY (아기): 모방 학습
- TODDLER (걸음마): 언어 폭발, "왜?" 질문
- CHILD (어린이): 자아 인식, 마음 이론

발달 메커니즘:
- 경험 누적 → 마일스톤 달성
- 마일스톤 → 새로운 능력 해금
- 능력 → 새로운 행동 가능
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, List, Callable
from datetime import datetime


class DevelopmentStage(Enum):
    """발달 단계"""
    NEWBORN = 0      # 0-3개월: 반사, 기본 패턴
    INFANT = 1       # 3-6개월: 패턴 인식, 선호
    BABY = 2         # 6-12개월: 모방, 객체 영속성
    TODDLER = 3      # 1-2세: 언어, 탐구
    CHILD = 4        # 2-3세: 자아, 마음 이론

    @property
    def description(self) -> str:
        descriptions = {
            DevelopmentStage.NEWBORN: "반사 반응, 기본 패턴 인식",
            DevelopmentStage.INFANT: "패턴 학습, 선호 형성",
            DevelopmentStage.BABY: "모방 학습, 객체 영속성",
            DevelopmentStage.TODDLER: "언어 폭발, 왜? 질문",
            DevelopmentStage.CHILD: "자아 인식, 마음 이론",
        }
        return descriptions.get(self, "알 수 없음")

    @property
    def capabilities(self) -> list[str]:
        """해당 단계의 능력"""
        caps = {
            DevelopmentStage.NEWBORN: [
                "basic_response",
                "pattern_detection",
            ],
            DevelopmentStage.INFANT: [
                "basic_response",
                "pattern_detection",
                "preference_formation",
                "simple_memory",
            ],
            DevelopmentStage.BABY: [
                "basic_response",
                "pattern_detection",
                "preference_formation",
                "simple_memory",
                "imitation",
                "object_permanence",
            ],
            DevelopmentStage.TODDLER: [
                "basic_response",
                "pattern_detection",
                "preference_formation",
                "simple_memory",
                "imitation",
                "object_permanence",
                "language_production",
                "why_questioning",
                "hypothesis_testing",
            ],
            DevelopmentStage.CHILD: [
                "basic_response",
                "pattern_detection",
                "preference_formation",
                "simple_memory",
                "imitation",
                "object_permanence",
                "language_production",
                "why_questioning",
                "hypothesis_testing",
                "self_awareness",
                "theory_of_mind",
                "meta_cognition",
            ],
        }
        return caps.get(self, [])


@dataclass
class Milestone:
    """발달 마일스톤"""
    name: str
    description: str
    required_stage: DevelopmentStage
    requirement: dict  # 달성 조건
    achieved: bool = False
    achieved_at: Optional[datetime] = None

    def check(self, stats: dict) -> bool:
        """마일스톤 달성 여부 확인"""
        if self.achieved:
            return True

        for key, threshold in self.requirement.items():
            if stats.get(key, 0) < threshold:
                return False

        self.achieved = True
        self.achieved_at = datetime.now()
        return True


class DevelopmentTracker:
    """
    발달 추적기

    경험 누적 → 마일스톤 → 단계 진행
    """

    def __init__(self):
        self._stage = DevelopmentStage.NEWBORN
        self._experience_count = 0
        self._success_count = 0
        self._unique_tasks = set()
        self._stage_experience: dict[DevelopmentStage, int] = {
            stage: 0 for stage in DevelopmentStage
        }

        # 마일스톤 정의
        self._milestones = self._create_milestones()

        # 단계별 경험 요구량
        self._stage_requirements = {
            DevelopmentStage.NEWBORN: 0,
            DevelopmentStage.INFANT: 10,
            DevelopmentStage.BABY: 30,
            DevelopmentStage.TODDLER: 70,
            DevelopmentStage.CHILD: 150,
        }

    def _create_milestones(self) -> list[Milestone]:
        """마일스톤 생성"""
        return [
            # NEWBORN → INFANT
            Milestone(
                name="first_success",
                description="첫 번째 성공적인 작업 완료",
                required_stage=DevelopmentStage.NEWBORN,
                requirement={"success_count": 1},
            ),
            Milestone(
                name="pattern_recognition",
                description="3가지 다른 유형의 작업 경험",
                required_stage=DevelopmentStage.NEWBORN,
                requirement={"unique_tasks": 3},
            ),

            # INFANT → BABY
            Milestone(
                name="consistent_success",
                description="5번 연속 성공",
                required_stage=DevelopmentStage.INFANT,
                requirement={"success_count": 10},
            ),
            Milestone(
                name="memory_formation",
                description="20개 이상의 경험 축적",
                required_stage=DevelopmentStage.INFANT,
                requirement={"experience_count": 20},
            ),

            # BABY → TODDLER
            Milestone(
                name="imitation_mastery",
                description="성공 패턴 재현 능력",
                required_stage=DevelopmentStage.BABY,
                requirement={"success_count": 30},
            ),
            Milestone(
                name="diverse_experience",
                description="10가지 다른 유형의 작업 경험",
                required_stage=DevelopmentStage.BABY,
                requirement={"unique_tasks": 10},
            ),

            # TODDLER → CHILD
            Milestone(
                name="self_reflection",
                description="50번 이상의 경험과 높은 성공률",
                required_stage=DevelopmentStage.TODDLER,
                requirement={
                    "experience_count": 100,
                    "success_count": 70,
                },
            ),
            Milestone(
                name="task_mastery",
                description="다양한 영역에서 높은 성공률",
                required_stage=DevelopmentStage.TODDLER,
                requirement={
                    "unique_tasks": 20,
                    "success_count": 100,
                },
            ),
        ]

    @property
    def stage(self) -> DevelopmentStage:
        """현재 발달 단계"""
        return self._stage

    @property
    def capabilities(self) -> list[str]:
        """현재 능력 목록"""
        return self._stage.capabilities

    def has_capability(self, capability: str) -> bool:
        """특정 능력 보유 여부"""
        return capability in self.capabilities

    def record_experience(
        self,
        success: bool,
        task_type: str = "default",
    ) -> dict:
        """
        경험 기록 및 발달 업데이트

        Returns:
            발달 상태 변화 정보
        """
        self._experience_count += 1
        self._stage_experience[self._stage] += 1

        if success:
            self._success_count += 1

        self._unique_tasks.add(task_type)

        # 마일스톤 체크
        achieved_milestones = self._check_milestones()

        # 단계 진행 체크
        stage_advanced = self._check_stage_advance()

        return {
            "experience_count": self._experience_count,
            "success_count": self._success_count,
            "stage": self._stage.name,
            "achieved_milestones": achieved_milestones,
            "stage_advanced": stage_advanced,
        }

    def _check_milestones(self) -> list[str]:
        """마일스톤 달성 확인"""
        stats = {
            "experience_count": self._experience_count,
            "success_count": self._success_count,
            "unique_tasks": len(self._unique_tasks),
        }

        achieved = []
        for milestone in self._milestones:
            if not milestone.achieved and milestone.required_stage == self._stage:
                if milestone.check(stats):
                    achieved.append(milestone.name)

        return achieved

    def _check_stage_advance(self) -> bool:
        """단계 진행 확인"""
        current_idx = self._stage.value

        # 이미 최고 단계
        if current_idx >= len(DevelopmentStage) - 1:
            return False

        next_stage = DevelopmentStage(current_idx + 1)
        required = self._stage_requirements.get(next_stage, float('inf'))

        # 현재 단계의 모든 마일스톤 달성 확인
        stage_milestones = [
            m for m in self._milestones
            if m.required_stage == self._stage
        ]
        all_achieved = all(m.achieved for m in stage_milestones)

        # 경험 요구량 + 마일스톤 모두 충족
        if self._experience_count >= required and all_achieved:
            self._stage = next_stage
            return True

        return False

    def get_progress(self) -> dict:
        """발달 진행 상황"""
        current_idx = self._stage.value
        next_stage = (
            DevelopmentStage(current_idx + 1)
            if current_idx < len(DevelopmentStage) - 1
            else None
        )

        next_required = (
            self._stage_requirements.get(next_stage, 0)
            if next_stage
            else self._experience_count
        )

        progress = min(1.0, self._experience_count / max(1, next_required))

        return {
            "stage": self._stage.name,
            "stage_description": self._stage.description,
            "experience_count": self._experience_count,
            "success_rate": (
                self._success_count / self._experience_count
                if self._experience_count > 0
                else 0
            ),
            "unique_task_types": len(self._unique_tasks),
            "next_stage": next_stage.name if next_stage else None,
            "progress_to_next": progress,
            "milestones_achieved": [
                m.name for m in self._milestones if m.achieved
            ],
            "milestones_pending": [
                m.name for m in self._milestones
                if not m.achieved and m.required_stage == self._stage
            ],
            "capabilities": self.capabilities,
        }

    def get_learning_rate_modifier(self) -> float:
        """발달 단계에 따른 학습률 조정"""
        # 어릴수록 빠르게 학습 (뇌 가소성)
        modifiers = {
            DevelopmentStage.NEWBORN: 1.5,   # 빠른 초기 학습
            DevelopmentStage.INFANT: 1.3,
            DevelopmentStage.BABY: 1.2,
            DevelopmentStage.TODDLER: 1.1,
            DevelopmentStage.CHILD: 1.0,     # 기본 학습률
        }
        return modifiers.get(self._stage, 1.0)

    def can_do(self, action: str) -> bool:
        """특정 행동 가능 여부"""
        action_requirements = {
            "ask_why": "why_questioning",
            "reflect": "self_awareness",
            "predict_others": "theory_of_mind",
            "imitate": "imitation",
            "remember": "simple_memory",
            "form_hypothesis": "hypothesis_testing",
        }

        required_capability = action_requirements.get(action)
        if not required_capability:
            return True  # 기본 행동은 항상 가능

        return self.has_capability(required_capability)

    def reset(self) -> None:
        """초기화"""
        self._stage = DevelopmentStage.NEWBORN
        self._experience_count = 0
        self._success_count = 0
        self._unique_tasks.clear()
        for m in self._milestones:
            m.achieved = False
            m.achieved_at = None

    def __repr__(self) -> str:
        return (
            f"DevelopmentTracker("
            f"stage={self._stage.name}, "
            f"exp={self._experience_count}, "
            f"success_rate={self._success_count}/{self._experience_count})"
        )
