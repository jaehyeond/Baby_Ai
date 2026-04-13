"""
Cognitive Router - 인지적 모델 라우팅 시스템

인간의 뇌처럼 작업 특성에 따라 적절한 LLM을 선택
- System 1 (빠른 직관): Gemini Flash - 단순 작업, 빠른 응답
- System 2 (느린 분석): GPT-5.2 Thinking - 복잡한 추론, 깊은 분석

라우팅 기준:
1. 발달 단계 (Development Stage)
2. 작업 복잡도 (Task Complexity)
3. 감정 상태 (Emotional State)
4. 응답 긴급도 (Urgency)
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Any, List
import re

from .llm_client import get_llm_client, ModelTier, AVAILABLE_MODELS


class DevelopmentStage(Enum):
    """발달 단계 (인간 뇌 발달 매핑)"""
    NEWBORN = 0      # 0-100 경험: 거의 System 1만 사용
    INFANT = 1       # 100-500 경험: System 1 위주
    TODDLER = 2      # 500-2000 경험: System 1 + 약간의 System 2
    CHILD = 3        # 2000-10000 경험: 균형잡힌 사용
    ADOLESCENT = 4   # 10000+ 경험: 전략적 System 2 활용


class TaskComplexity(Enum):
    """작업 복잡도"""
    TRIVIAL = 0      # 인사, 간단한 질문
    SIMPLE = 1       # 단순 코딩, 설명
    MODERATE = 2     # 중간 복잡도 작업
    COMPLEX = 3      # 다단계 추론, 설계
    CRITICAL = 4     # 중요한 결정, 깊은 분석


class Urgency(Enum):
    """응답 긴급도"""
    IMMEDIATE = 0    # 즉각 응답 필요
    NORMAL = 1       # 일반적인 응답
    RELAXED = 2      # 시간 여유 있음


@dataclass
class RoutingDecision:
    """라우팅 결정 결과"""
    model_key: str
    thinking_level: Optional[str]
    reasoning: str
    estimated_cost_factor: float  # 1.0 = baseline


@dataclass
class TaskContext:
    """작업 컨텍스트"""
    task: str
    task_type: Optional[str] = None
    development_stage: DevelopmentStage = DevelopmentStage.NEWBORN
    emotional_state: Optional[Dict[str, float]] = None
    urgency: Urgency = Urgency.NORMAL
    requires_code: bool = False
    requires_reasoning: bool = False
    previous_failures: int = 0


class CognitiveRouter:
    """
    인지적 모델 라우터

    인간의 이중 처리 시스템(Dual Process Theory)을 모방:
    - System 1: 빠르고, 자동적, 직관적 (Gemini Flash)
    - System 2: 느리고, 의도적, 분석적 (GPT-5.2 Thinking)
    """

    # 복잡한 작업을 나타내는 키워드
    COMPLEX_KEYWORDS = [
        "설계", "아키텍처", "분석", "최적화", "디버그", "버그",
        "왜", "어떻게", "비교", "장단점", "트레이드오프",
        "design", "architecture", "analyze", "optimize", "debug",
        "why", "how", "compare", "tradeoff", "complex",
        "알고리즘", "algorithm", "시스템", "system",
        "보안", "security", "성능", "performance",
    ]

    # 단순 작업을 나타내는 키워드
    SIMPLE_KEYWORDS = [
        "안녕", "hi", "hello", "감사", "thanks",
        "뭐야", "what is", "정의", "define",
        "간단", "simple", "빠르게", "quick",
        "예시", "example", "보여줘", "show",
    ]

    # 코드 관련 키워드
    CODE_KEYWORDS = [
        "코드", "code", "구현", "implement", "함수", "function",
        "클래스", "class", "파이썬", "python", "자바스크립트", "javascript",
        "프로그램", "program", "스크립트", "script",
    ]

    def __init__(self):
        self.llm_client = get_llm_client()
        self._routing_history: List[RoutingDecision] = []

    def analyze_complexity(self, task: str) -> TaskComplexity:
        """작업 복잡도 분석"""
        task_lower = task.lower()

        # 키워드 기반 점수 계산
        complex_score = sum(1 for kw in self.COMPLEX_KEYWORDS if kw in task_lower)
        simple_score = sum(1 for kw in self.SIMPLE_KEYWORDS if kw in task_lower)

        # 길이 기반 조정 (긴 요청 = 복잡할 가능성)
        length_factor = len(task) / 100  # 100자당 +0.1 복잡도

        # 코드 블록이나 특수 문자 포함 여부
        has_code_block = "```" in task or "def " in task or "class " in task

        # 최종 점수 계산
        score = complex_score - simple_score + length_factor
        if has_code_block:
            score += 1

        if score < 0:
            return TaskComplexity.TRIVIAL
        elif score < 1:
            return TaskComplexity.SIMPLE
        elif score < 2:
            return TaskComplexity.MODERATE
        elif score < 3:
            return TaskComplexity.COMPLEX
        else:
            return TaskComplexity.CRITICAL

    def requires_code_generation(self, task: str) -> bool:
        """코드 생성이 필요한지 판단"""
        task_lower = task.lower()
        return any(kw in task_lower for kw in self.CODE_KEYWORDS)

    def requires_deep_reasoning(self, task: str) -> bool:
        """깊은 추론이 필요한지 판단"""
        task_lower = task.lower()
        reasoning_indicators = [
            "왜", "why", "어떻게", "how",
            "비교", "compare", "분석", "analyze",
            "장단점", "pros and cons", "trade",
            "최적", "optimal", "best",
            "문제", "problem", "해결", "solve",
        ]
        return any(kw in task_lower for kw in reasoning_indicators)

    def get_stage_routing_weights(self, stage: DevelopmentStage) -> Dict[str, float]:
        """
        발달 단계별 모델 사용 가중치

        아기일수록 System 1 (빠른 학습) 위주
        성장할수록 System 2 (깊은 사고) 비중 증가
        """
        weights = {
            DevelopmentStage.NEWBORN: {
                "flash": 0.95,      # 95% Flash
                "standard": 0.04,   # 4% Standard
                "thinking": 0.01,   # 1% Thinking
            },
            DevelopmentStage.INFANT: {
                "flash": 0.85,
                "standard": 0.12,
                "thinking": 0.03,
            },
            DevelopmentStage.TODDLER: {
                "flash": 0.70,
                "standard": 0.22,
                "thinking": 0.08,
            },
            DevelopmentStage.CHILD: {
                "flash": 0.50,
                "standard": 0.30,
                "thinking": 0.20,
            },
            DevelopmentStage.ADOLESCENT: {
                "flash": 0.40,
                "standard": 0.35,
                "thinking": 0.25,
            },
        }
        return weights.get(stage, weights[DevelopmentStage.NEWBORN])

    def route(self, context: TaskContext) -> RoutingDecision:
        """
        작업 컨텍스트를 기반으로 최적의 모델 선택

        Args:
            context: 작업 컨텍스트 (작업, 발달단계, 감정상태 등)

        Returns:
            RoutingDecision: 선택된 모델과 설정
        """
        task = context.task
        stage = context.development_stage

        # 1. 복잡도 분석
        complexity = self.analyze_complexity(task)
        requires_code = context.requires_code or self.requires_code_generation(task)
        requires_reasoning = context.requires_reasoning or self.requires_deep_reasoning(task)

        # 2. 발달 단계별 가중치 가져오기
        weights = self.get_stage_routing_weights(stage)

        # 3. 긴급도 고려
        if context.urgency == Urgency.IMMEDIATE:
            # 즉시 응답 필요 → Flash 우선
            model_key = "gemini-2-flash"
            thinking_level = None
            reasoning = "긴급 응답 → Flash 사용"
            cost_factor = 0.1

        # 4. 이전 실패 고려
        elif context.previous_failures >= 2:
            # 2번 이상 실패 → Thinking 모드로 전환
            model_key = "gpt-5.2-thinking"
            thinking_level = "high"
            reasoning = f"이전 {context.previous_failures}회 실패 → 깊은 분석 필요"
            cost_factor = 5.0

        # 5. 복잡도 기반 라우팅
        elif complexity == TaskComplexity.TRIVIAL:
            model_key = "gemini-2-flash"
            thinking_level = None
            reasoning = "단순 작업 → Flash 사용"
            cost_factor = 0.1

        elif complexity == TaskComplexity.SIMPLE:
            model_key = "gemini-2-flash"
            thinking_level = None
            reasoning = "간단한 작업 → Flash 사용"
            cost_factor = 0.1

        elif complexity == TaskComplexity.MODERATE:
            # 중간 복잡도: 발달 단계에 따라 결정
            if weights["thinking"] > 0.15 and requires_reasoning:
                model_key = "gpt-4o-mini"  # 중간 수준
                thinking_level = None
                reasoning = f"중간 복잡도 + {stage.name} 단계 → GPT-4o-mini"
                cost_factor = 0.5
            else:
                model_key = "gemini-2-flash"
                thinking_level = None
                reasoning = f"중간 복잡도 + {stage.name} 단계 → Flash"
                cost_factor = 0.1

        elif complexity == TaskComplexity.COMPLEX:
            # 복잡한 작업: Thinking 고려
            if weights["thinking"] > 0.1:
                model_key = "gpt-5.2-thinking"
                thinking_level = "medium"
                reasoning = f"복잡한 작업 + {stage.name} 단계 → Thinking (medium)"
                cost_factor = 3.0
            else:
                model_key = "gpt-4o-mini"
                thinking_level = None
                reasoning = f"복잡한 작업이지만 {stage.name} 단계 → GPT-4o-mini"
                cost_factor = 0.5

        else:  # CRITICAL
            # 중요한 작업: Thinking 최대 활용
            model_key = "gpt-5.2-thinking"
            thinking_level = "high"
            reasoning = f"중요한 작업 → Thinking (high)"
            cost_factor = 5.0

        # 6. 감정 상태 조정
        if context.emotional_state:
            curiosity = context.emotional_state.get("curiosity", 0)
            frustration = context.emotional_state.get("frustration", 0)

            # 호기심이 높으면 더 깊은 분석 권장
            if curiosity > 0.8 and thinking_level is None:
                if model_key == "gemini-2-flash":
                    model_key = "gpt-4o-mini"
                    reasoning += " (높은 호기심 → 업그레이드)"
                    cost_factor *= 2

            # 좌절감이 높으면 더 신중한 처리
            if frustration > 0.7:
                if "thinking" not in model_key:
                    model_key = "gpt-5.2-thinking"
                    thinking_level = "medium"
                    reasoning += " (높은 좌절감 → Thinking 전환)"
                    cost_factor = 3.0

        decision = RoutingDecision(
            model_key=model_key,
            thinking_level=thinking_level,
            reasoning=reasoning,
            estimated_cost_factor=cost_factor,
        )

        # 히스토리 저장
        self._routing_history.append(decision)

        return decision

    def generate(
        self,
        task: str,
        system_prompt: str = None,
        context: TaskContext = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        """
        인지적 라우팅을 적용하여 응답 생성

        Args:
            task: 사용자 요청
            system_prompt: 시스템 프롬프트
            context: 작업 컨텍스트 (없으면 자동 생성)
            temperature: 창의성
            max_tokens: 최대 토큰

        Returns:
            생성된 응답
        """
        # 컨텍스트가 없으면 기본값으로 생성
        if context is None:
            context = TaskContext(task=task)
        else:
            context.task = task

        # 라우팅 결정
        decision = self.route(context)

        print(f"[CognitiveRouter] {decision.reasoning}")
        print(f"[CognitiveRouter] Model: {decision.model_key}, Thinking: {decision.thinking_level}")

        # LLM 호출
        try:
            response = self.llm_client.generate(
                prompt=task,
                model_key=decision.model_key,
                system_prompt=system_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                thinking_level=decision.thinking_level,
            )
            return response

        except Exception as e:
            print(f"[CognitiveRouter] Error with {decision.model_key}: {e}")

            # 폴백: Flash로 재시도
            if decision.model_key != "gemini-2-flash":
                print("[CognitiveRouter] Falling back to gemini-2-flash...")
                return self.llm_client.generate(
                    prompt=task,
                    model_key="gemini-2-flash",
                    system_prompt=system_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
            raise

    def get_routing_stats(self) -> Dict[str, Any]:
        """라우팅 통계"""
        if not self._routing_history:
            return {"total_routes": 0}

        model_counts = {}
        total_cost_factor = 0

        for decision in self._routing_history:
            model_counts[decision.model_key] = model_counts.get(decision.model_key, 0) + 1
            total_cost_factor += decision.estimated_cost_factor

        return {
            "total_routes": len(self._routing_history),
            "model_distribution": model_counts,
            "average_cost_factor": total_cost_factor / len(self._routing_history),
        }


# 싱글톤 인스턴스
_cognitive_router: Optional[CognitiveRouter] = None


def get_cognitive_router() -> CognitiveRouter:
    """CognitiveRouter 싱글톤"""
    global _cognitive_router
    if _cognitive_router is None:
        _cognitive_router = CognitiveRouter()
    return _cognitive_router


def route_and_generate(
    task: str,
    development_stage: int = 0,
    emotional_state: Dict[str, float] = None,
    system_prompt: str = None,
) -> str:
    """
    편의 함수: 작업을 라우팅하고 응답 생성

    Args:
        task: 사용자 요청
        development_stage: 발달 단계 (0-4)
        emotional_state: 감정 상태
        system_prompt: 시스템 프롬프트

    Returns:
        생성된 응답
    """
    router = get_cognitive_router()

    # 발달 단계 변환
    stage = DevelopmentStage(min(development_stage, 4))

    context = TaskContext(
        task=task,
        development_stage=stage,
        emotional_state=emotional_state,
    )

    return router.generate(
        task=task,
        system_prompt=system_prompt,
        context=context,
    )
