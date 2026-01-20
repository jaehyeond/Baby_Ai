"""
BabySubstrate - 아기 뉴럴 기질

NeuralSubstrate를 확장하여 발달 AI 기능 추가:
- 감정 시스템
- 호기심 엔진
- 기억 시스템
- 발달 추적
- 자아 모델

모든 에이전트가 하나의 "아기 뇌"에서 동작
"""

import asyncio
import os
from dataclasses import dataclass, field
from typing import Optional, Any
from datetime import datetime

from .emotions import EmotionalCore, EmotionalState
from .curiosity import CuriosityEngine, CuriositySignal, LearningZone
from .memory import MemorySystem, Experience
from .development import DevelopmentTracker, DevelopmentStage
from .self_model import SelfModel
from .cognitive_router import (
    CognitiveRouter,
    TaskContext,
    DevelopmentStage as RouterDevelopmentStage,
    Urgency,
)
from .db import get_brain_db, BrainDatabase
from .world_model import WorldModel, PredictionType, SimulationType
from .llm_client import get_llm_client, LLMClient
from .emotional_modulator import EmotionalLearningModulator, Strategy, StrategyDecision
from .vision import VisionProcessor, VisualInput, VisualExperience, VisualSource


@dataclass
class BabyConfig:
    """Baby Substrate 설정"""
    # 실행 설정
    max_iterations: int = 3
    verbose: bool = True

    # 기억 저장 경로
    memory_path: str = ""

    # 발달 설정
    enable_development: bool = True
    enable_emotions: bool = True
    enable_curiosity: bool = True

    # 학습 설정
    consolidation_interval: int = 10  # N번 경험 후 기억 통합

    # Supabase 연동 설정
    enable_supabase: bool = True  # Supabase에 데이터 저장 여부

    # World Model 설정
    enable_world_model: bool = True  # World Model 활성화
    auto_generate_predictions: bool = True  # 자동 예측 생성

    # Phase 3: 감정 기반 학습 설정
    enable_emotional_modulation: bool = True  # 감정 기반 학습/행동 조절
    base_learning_rate: float = 0.1  # 기본 학습률

    # Phase 4: 멀티모달 설정
    enable_vision: bool = True       # 시각 처리 활성화
    enable_audio: bool = False       # 오디오 처리 활성화 (Phase 4.2)
    enable_speech: bool = False      # 음성 합성 활성화 (Phase 4.3)


@dataclass
class BabyResult:
    """Baby Substrate 실행 결과"""
    # 기본 결과
    success: bool
    output: str
    iterations: int
    execution_time_ms: float

    # Baby 특화 정보
    emotional_state: dict = field(default_factory=dict)
    curiosity_signal: dict = field(default_factory=dict)
    development_progress: dict = field(default_factory=dict)
    memory_stats: dict = field(default_factory=dict)

    # 학습 정보
    experience_id: str = ""
    learned: str = ""

    # Cognitive Router 정보
    routing_info: dict = field(default_factory=dict)

    # Phase 3: 감정 영향 정보
    emotional_influence: dict = field(default_factory=dict)
    strategy_used: dict = field(default_factory=dict)

    # World Model 정보
    world_model_stats: dict = field(default_factory=dict)
    prediction_made: dict = field(default_factory=dict)

    # Phase 4: 멀티모달 정보
    visual_experience: dict = field(default_factory=dict)  # 시각적 경험
    media_type: str = "text"  # text, image, audio


class BabySubstrate:
    """
    아기 뉴럴 기질

    발달 AI 기능이 통합된 에이전트 실행 환경
    - 경험에서 학습
    - 감정으로 의사결정
    - 호기심으로 탐험
    - 스스로 발달
    """

    def __init__(self, config: Optional[BabyConfig] = None):
        self.config = config or BabyConfig()

        # 핵심 시스템 초기화
        self._emotions = EmotionalCore()
        self._curiosity = CuriosityEngine()
        self._memory = MemorySystem(
            storage_path=self.config.memory_path if self.config.memory_path else None
        )
        self._development = DevelopmentTracker()
        self._self = SelfModel()
        self._cognitive_router = CognitiveRouter()  # Cognitive Router 추가

        # Phase 3: 감정 기반 학습 조절기
        self._emotional_modulator: Optional[EmotionalLearningModulator] = None
        if self.config.enable_emotional_modulation:
            self._emotional_modulator = EmotionalLearningModulator(
                emotional_core=self._emotions,
                verbose=self.config.verbose,
            )
            if self.config.verbose:
                print("[BABY] Emotional Learning Modulator initialized")

        # Supabase DB 연동 (선택적)
        self._db: Optional[BrainDatabase] = None
        if self.config.enable_supabase:
            try:
                self._db = get_brain_db()
                if self.config.verbose:
                    print("[BABY] Supabase connection initialized")
            except Exception as e:
                if self.config.verbose:
                    print(f"[BABY] Supabase connection failed: {e}")
                self._db = None

        # World Model 초기화
        self._world_model: Optional[WorldModel] = None
        self._llm_client: Optional[LLMClient] = None
        if self.config.enable_world_model:
            try:
                self._llm_client = get_llm_client()
                self._world_model = WorldModel(
                    db=self._db,
                    llm_client=self._llm_client,
                    development_stage=self._development.stage.value,
                    verbose=self.config.verbose,
                )
                if self.config.verbose:
                    print("[BABY] World Model initialized")
            except Exception as e:
                if self.config.verbose:
                    print(f"[BABY] World Model initialization failed: {e}")
                self._world_model = None

        # Phase 4: Vision Processor 초기화
        self._vision_processor: Optional[VisionProcessor] = None
        if self.config.enable_vision:
            try:
                self._vision_processor = VisionProcessor(verbose=self.config.verbose)
                if self.config.verbose:
                    print("[BABY] Vision Processor initialized")
            except Exception as e:
                if self.config.verbose:
                    print(f"[BABY] Vision Processor initialization failed: {e}")

        # 에이전트 (lazy loading)
        self._agents: dict[str, Any] = {}
        self._initialized = False

        # 경험 카운터 (기억 통합용)
        self._experience_counter = 0

        # 세션 시작 시간
        self._session_start = datetime.now()

        # 기억 및 상태 로드 시도
        if self.config.memory_path:
            self._memory.load()
            self._load_state()

    def _initialize_agents(self) -> None:
        """에이전트 초기화 (lazy loading)"""
        if self._initialized:
            return

        from agents.coder.agent import CoderAgent
        from agents.tester.agent import TesterAgent
        from agents.reviewer.agent import ReviewerAgent

        if self.config.verbose:
            print("\n[BABY] Waking up... initializing neural systems")

        self._agents["coder"] = CoderAgent()
        self._agents["tester"] = TesterAgent()
        self._agents["reviewer"] = ReviewerAgent()

        # 능력 등록
        self._self.register_capability("code_generation", "코드 생성")
        self._self.register_capability("code_testing", "코드 테스트")
        self._self.register_capability("code_review", "코드 리뷰")

        self._initialized = True

        if self.config.verbose:
            stage = self._development.stage
            print(f"[BABY] Ready! Stage: {stage.name} - {stage.description}")
            print(f"[BABY] Emotional state: {self._emotions}")

    async def process(self, user_request: str) -> BabyResult:
        """
        요청 처리 (발달 AI 방식)

        1. 감정 상태 확인
        2. 관련 기억 회상
        3. 호기심 기반 접근 결정
        4. 에이전트 실행
        5. 결과에서 학습
        6. 발달 업데이트
        """
        import time
        start_time = time.time()

        # 에이전트 초기화
        self._initialize_agents()

        if self.config.verbose:
            self._print_header(user_request)

        # 1. 관련 기억 회상
        memories = self._memory.recall_for_task(user_request)
        if self.config.verbose and memories["similar_experiences"]:
            print(f"\n[MEMORY] Found {len(memories['similar_experiences'])} similar experiences")

        # 2. 감정 상태 확인 및 접근 방식 결정
        emotional_state = self._emotions.get_state()
        approach = self._emotions.modulate_action("generate")

        if self.config.verbose:
            print(f"[EMOTION] {emotional_state.dominant_emotion.value} "
                  f"(valence: {emotional_state.valence:.2f})")
            print(f"[APPROACH] {approach}")

        # 3. Phase 3: 감정 기반 전략 선택
        strategy_decision = None
        emotional_influence = {}
        if self._emotional_modulator:
            # 전략 선택
            strategy_decision = self._emotional_modulator.select_strategy(
                context={"previous_failures": 0}
            )

            # 학습률 조절
            learning_adjustment = self._emotional_modulator.adjust_learning_rate(
                base_rate=self.config.base_learning_rate
            )

            # 감정 영향 기록
            emotional_influence = self._emotions.get_emotional_influence()

            if self.config.verbose:
                print(f"[STRATEGY] {strategy_decision.strategy.value} "
                      f"(confidence: {strategy_decision.confidence:.2f})")
                print(f"[LEARNING] Rate modifier: {learning_adjustment.modifier:.2f}")

        # 4. 호기심 확인
        exploration_rate = self._emotions.get_exploration_rate()

        # 5. 에이전트 실행 (전략 기반)
        result = await self._execute_pipeline(
            user_request,
            memories,
            approach,
            strategy_decision,
        )

        # 6. 결과에서 학습 (감정 조절된 학습률 적용)
        experience = self._learn_from_result(
            user_request,
            result,
        )

        # 7. Phase 3: 패턴 결과 기록
        if self._emotional_modulator:
            task_type = self._categorize_task(user_request)
            self._emotional_modulator.record_pattern_outcome(
                pattern_id=task_type,
                success=result["success"],
            )

        # 8. 호기심 신호 계산
        curiosity_signal = self._curiosity.compute_simple_curiosity(
            success=result["success"],
            output=result.get("code", ""),
            task_type=self._categorize_task(user_request),
        )

        # 9. 감정 업데이트
        if result["success"]:
            self._emotions.on_success()
        else:
            self._emotions.on_failure()

        self._emotions.on_novelty(curiosity_signal.novelty)

        # 10. 발달 업데이트
        dev_result = self._development.record_experience(
            success=result["success"],
            task_type=self._categorize_task(user_request),
        )

        if dev_result.get("stage_advanced"):
            if self.config.verbose:
                new_stage = self._development.stage
                print(f"\n[DEVELOPMENT] Level up! Now: {new_stage.name}")
                print(f"  New capabilities: {new_stage.capabilities}")

        # 11. 자아 모델 업데이트
        self._self.update_capability("code_generation", result["success"])

        if self._development.has_capability("self_awareness"):
            reflection = self._self.reflect(
                experience={"request": user_request[:50]},
                outcome="success" if result["success"] else "failure",
                learned=f"Task type: {self._categorize_task(user_request)}",
            )

        # 12. 주기적 기억 통합
        self._experience_counter += 1
        if self._experience_counter % self.config.consolidation_interval == 0:
            self._memory.consolidate()
            if self.config.verbose:
                print("\n[MEMORY] Consolidating memories...")

        # 13. World Model 업데이트 및 예측 생성
        prediction_made = {}
        world_model_stats = {}
        if self._world_model and self.config.auto_generate_predictions:
            try:
                # 발달 단계 동기화
                self._world_model.set_development_stage(self._development.stage.value)

                # 경험에서 World Model 데이터 자동 생성
                emotional_state_dict = {
                    "curiosity": self._emotions.get_state().curiosity,
                    "joy": self._emotions.get_state().joy,
                    "fear": self._emotions.get_state().fear,
                    "frustration": self._emotions.get_state().frustration,
                }
                wm_results = self._world_model.auto_generate_from_experience(
                    experience={
                        "task": user_request,
                        "success": result["success"],
                        "task_type": self._categorize_task(user_request),
                    },
                    emotional_state=emotional_state_dict,
                )

                if wm_results.get("prediction"):
                    prediction_made = {
                        "id": wm_results["prediction"].prediction_id,
                        "prediction": wm_results["prediction"].prediction,
                        "confidence": wm_results["prediction"].confidence,
                    }
                    if self.config.verbose:
                        print(f"\n[WORLD_MODEL] Prediction: {prediction_made['prediction'][:50]}...")

                world_model_stats = self._world_model.get_stats()

            except Exception as e:
                if self.config.verbose:
                    print(f"\n[WORLD_MODEL] Error: {e}")

        execution_time = (time.time() - start_time) * 1000

        # 결과 구성
        baby_result = BabyResult(
            success=result["success"],
            output=result.get("code", ""),
            iterations=result.get("iterations", 1),
            execution_time_ms=execution_time,
            emotional_state=self._emotions.get_state().to_dict(),
            curiosity_signal=curiosity_signal.to_dict(),
            development_progress=self._development.get_progress(),
            memory_stats=self._memory.get_stats(),
            experience_id=experience.id if experience else "",
            routing_info=self._cognitive_router.get_routing_stats(),
            world_model_stats=world_model_stats,
            prediction_made=prediction_made,
            emotional_influence=emotional_influence,
            strategy_used=strategy_decision.__dict__ if strategy_decision else {},
        )

        if self.config.verbose:
            self._print_result(baby_result)

        return baby_result

    def _map_development_stage(self) -> RouterDevelopmentStage:
        """내부 발달 단계를 Cognitive Router 단계로 매핑"""
        stage_value = self._development.stage.value
        if stage_value == 0:
            return RouterDevelopmentStage.NEWBORN
        elif stage_value == 1:
            return RouterDevelopmentStage.INFANT
        elif stage_value == 2:
            return RouterDevelopmentStage.TODDLER
        elif stage_value == 3:
            return RouterDevelopmentStage.CHILD
        else:
            return RouterDevelopmentStage.ADOLESCENT

    def _get_emotional_state_dict(self) -> dict:
        """감정 상태를 dict로 변환"""
        state = self._emotions.get_state()
        return {
            "curiosity": getattr(state, "curiosity", 0.5),
            "joy": getattr(state, "joy", 0.5),
            "frustration": getattr(state, "frustration", 0.0),
            "valence": state.valence,
        }

    async def _execute_pipeline(
        self,
        user_request: str,
        memories: dict,
        approach: str,
        strategy_decision: Optional[StrategyDecision] = None,
    ) -> dict:
        """파이프라인 실행 (Cognitive Router + 감정 기반 전략 통합)"""
        import time

        results: dict[str, Any] = {}
        iteration = 1
        success = False
        feedback_context = ""

        # Phase 3: 전략에 따른 컨텍스트 설정
        strategy = strategy_decision.strategy if strategy_decision else Strategy.EXPLOIT
        strategy_params = strategy_decision.parameters if strategy_decision else {}

        # 유사 경험을 컨텍스트로 활용 (전략에 따라 다르게)
        context = ""

        # EXPLOIT: 성공 경험 많이 활용
        if strategy == Strategy.EXPLOIT and memories["successful_examples"]:
            examples = memories["successful_examples"][:3]  # 더 많은 예시
            context = "\n\n[Previous successful examples - USE THESE AS REFERENCE]\n"
            for ex in examples:
                context += f"- Request: {ex['request'][:50]}...\n"
                context += f"  Solution: {ex['action'][:100]}...\n"

        # EXPLORE: 최소한의 컨텍스트, 새로운 접근 장려
        elif strategy == Strategy.EXPLORE:
            context = "\n\n[Note: Try a NEW and DIFFERENT approach. Be creative!]\n"

        # CAUTIOUS: 단계별 접근 강조
        elif strategy == Strategy.CAUTIOUS:
            context = "\n\n[IMPORTANT: Be CAREFUL and THOROUGH. Validate each step.]\n"
            if memories["successful_examples"]:
                examples = memories["successful_examples"][:1]
                context += "[Safe reference]\n"
                for ex in examples:
                    context += f"- {ex['action'][:100]}...\n"

        # ALTERNATIVE: 이전과 다른 방법 요청
        elif strategy == Strategy.ALTERNATIVE:
            context = "\n\n[IMPORTANT: The previous approach FAILED. Use a COMPLETELY DIFFERENT method!]\n"
            if memories.get("recent_failures"):
                context += "[Avoid these patterns]\n"

        # CREATIVE: 조합/실험 허용
        elif strategy == Strategy.CREATIVE:
            context = "\n\n[CREATIVE MODE: Combine different techniques. Think outside the box!]\n"

        # 기본 fallback (EXPLOIT)
        elif memories["successful_examples"]:
            examples = memories["successful_examples"][:2]
            context = "\n\n[Previous successful examples]\n"
            for ex in examples:
                context += f"- Request: {ex['request'][:50]}...\n"
                context += f"  Solution: {ex['action'][:100]}...\n"

        # Cognitive Router용 컨텍스트 준비
        router_stage = self._map_development_stage()
        emotional_state = self._get_emotional_state_dict()

        while iteration <= self.config.max_iterations and not success:
            if self.config.verbose:
                print(f"\n[ITERATION {iteration}/{self.config.max_iterations}]")

            # Phase 3: 반복 실패 시 전략 재평가
            if iteration > 1 and self._emotional_modulator:
                new_strategy = self._emotional_modulator.select_strategy(
                    context={"previous_failures": iteration - 1}
                )
                strategy = new_strategy.strategy
                strategy_params = new_strategy.parameters

                if self.config.verbose:
                    print(f"  [STRATEGY CHANGE] → {strategy.value} ({new_strategy.reasoning})")

            # Cognitive Router로 최적 모델 선택
            task_context = TaskContext(
                task=user_request,
                task_type=self._categorize_task(user_request),
                development_stage=router_stage,
                emotional_state=emotional_state,
                urgency=Urgency.NORMAL,
                requires_code=True,
                previous_failures=iteration - 1,
            )
            routing_decision = self._cognitive_router.route(task_context)

            if self.config.verbose:
                print(f"  [ROUTER] {routing_decision.reasoning}")
                print(f"  [MODEL] {routing_decision.model_key} (thinking: {routing_decision.thinking_level})")

            # Coder 실행 (Cognitive Router 사용)
            coder_input = user_request + context
            if feedback_context:
                coder_input += f"\n\n[Feedback from previous attempt]\n{feedback_context}"

            if self.config.verbose:
                print("  [CODER] Generating code...", end="", flush=True)

            start = time.time()
            try:
                # Cognitive Router로 LLM 호출
                code = self._cognitive_router.generate(
                    task=coder_input,
                    system_prompt="You are a skilled programmer. Generate clean, working code. Respond with code only.",
                    context=task_context,
                )
                coder_time = (time.time() - start) * 1000
                if self.config.verbose:
                    print(f" done ({coder_time:.0f}ms)")
            except Exception as e:
                if self.config.verbose:
                    print(f" error: {e}")
                code = ""

            results["code"] = code

            if not code:
                iteration += 1
                continue

            # Tester 실행
            if self.config.verbose:
                print("  [TESTER] Testing code...", end="", flush=True)

            start = time.time()
            try:
                test_result = await self._agents["tester"].analyze_and_test(code)
                tester_time = (time.time() - start) * 1000
                if self.config.verbose:
                    print(f" done ({tester_time:.0f}ms)")
            except Exception as e:
                if self.config.verbose:
                    print(f" error: {e}")
                test_result = f"Error: {e}"

            results["test_result"] = test_result

            # Reviewer 실행
            if self.config.verbose:
                print("  [REVIEWER] Reviewing code...", end="", flush=True)

            start = time.time()
            try:
                review_result = await self._agents["reviewer"].review(code)
                reviewer_time = (time.time() - start) * 1000
                if self.config.verbose:
                    print(f" done ({reviewer_time:.0f}ms)")
            except Exception as e:
                if self.config.verbose:
                    print(f" error: {e}")
                review_result = f"Error: {e}"

            results["review_result"] = review_result

            # 평가
            success, feedback = self._evaluate_results(test_result, review_result)

            if success:
                if self.config.verbose:
                    print("  [RESULT] Success!")
            else:
                feedback_context = feedback
                if self.config.verbose:
                    print(f"  [RESULT] Needs improvement: {feedback[:100]}...")
                iteration += 1

        results["success"] = success
        results["iterations"] = iteration

        return results

    def _evaluate_results(
        self,
        test_result: str,
        review_result: str,
    ) -> tuple[bool, str]:
        """결과 평가"""
        test_lower = test_result.lower()
        review_lower = review_result.lower()

        failure_keywords = ["error", "fail", "bug", "issue", "problem"]
        success_keywords = ["pass", "success", "correct", "good"]

        has_failure = any(kw in test_lower for kw in failure_keywords)
        has_success = any(kw in test_lower for kw in success_keywords)

        # 리뷰 점수 추출
        import re
        score_match = re.search(r'(\d+)\s*/\s*10', review_lower)
        review_score = int(score_match.group(1)) if score_match else 7

        if has_failure and not has_success:
            return False, f"Test issues. Review: {review_score}/10\n{test_result[:200]}"

        if review_score < 6:
            return False, f"Low review score: {review_score}/10\n{review_result[:200]}"

        return True, ""

    def _learn_from_result(
        self,
        request: str,
        result: dict,
    ) -> Experience:
        """결과에서 학습"""
        emotional_weight = self._emotions.get_memory_weight()
        curiosity_signal = self._emotions.get_exploration_rate()
        task_type = self._categorize_task(request)

        experience = self._memory.record_experience(
            request=request,
            action=result.get("code", "")[:500],
            outcome="success" if result["success"] else "failure",
            success=result["success"],
            emotional_weight=emotional_weight,
            curiosity_signal=curiosity_signal,
            task_type=task_type,
        )

        # Supabase에도 경험 저장
        if self._db:
            try:
                emotional_state = self._emotions.get_state()
                self._db.insert_experience(
                    task=request[:500],
                    task_type=task_type,
                    output=result.get("code", "")[:1000],
                    success=result["success"],
                    emotional_salience=emotional_weight,
                    dominant_emotion=emotional_state.dominant_emotion.value,
                    emotion_snapshot={
                        "curiosity": emotional_state.curiosity,
                        "joy": emotional_state.joy,
                        "fear": emotional_state.fear,
                        "surprise": emotional_state.surprise,
                        "frustration": emotional_state.frustration,
                        "boredom": emotional_state.boredom,
                    },
                    development_stage=self._development.stage.value,
                    tags=[task_type],
                )
                if self.config.verbose:
                    print("[SUPABASE] Experience saved to cloud")
            except Exception as e:
                if self.config.verbose:
                    print(f"[SUPABASE] Failed to save experience: {e}")

        return experience

    def _categorize_task(self, request: str) -> str:
        """태스크 유형 분류"""
        request_lower = request.lower()

        if any(kw in request_lower for kw in ["함수", "function", "def"]):
            return "function"
        if any(kw in request_lower for kw in ["클래스", "class"]):
            return "class"
        if any(kw in request_lower for kw in ["알고리즘", "algorithm", "정렬", "sort"]):
            return "algorithm"
        if any(kw in request_lower for kw in ["api", "서버", "server"]):
            return "api"
        if any(kw in request_lower for kw in ["테스트", "test"]):
            return "test"

        return "general"

    def _print_header(self, request: str) -> None:
        """헤더 출력"""
        stage = self._development.stage
        print("\n" + "=" * 60)
        print("  BABY NEURAL SUBSTRATE")
        print("=" * 60)
        print(f"\n[STAGE] {stage.name}: {stage.description}")
        print(f"[REQUEST] {request[:60]}{'...' if len(request) > 60 else ''}")

    def _print_result(self, result: BabyResult) -> None:
        """결과 출력"""
        print("\n" + "-" * 60)
        print("  RESULT")
        print("-" * 60)

        status = "[OK]" if result.success else "[X]"
        print(f"\n{status} Completed in {result.execution_time_ms:.0f}ms")
        print(f"  Iterations: {result.iterations}")

        print(f"\n[EMOTIONAL STATE]")
        for key, val in result.emotional_state.items():
            if isinstance(val, float):
                print(f"  {key}: {val:.2f}")
            else:
                print(f"  {key}: {val}")

        print(f"\n[CURIOSITY]")
        print(f"  Zone: {result.curiosity_signal.get('zone', 'unknown')}")
        print(f"  Intrinsic reward: {result.curiosity_signal.get('intrinsic_reward', 0):.2f}")

        print(f"\n[DEVELOPMENT]")
        prog = result.development_progress
        print(f"  Stage: {prog.get('stage', 'unknown')}")
        print(f"  Experience: {prog.get('experience_count', 0)}")
        print(f"  Progress to next: {prog.get('progress_to_next', 0):.1%}")

        if result.success:
            print(f"\n[CODE PREVIEW]")
            preview = result.output[:200].replace('\n', '\n  ')
            print(f"  {preview}...")

        print("\n" + "=" * 60)

    def save(self) -> None:
        """상태 저장 (기억 + 발달 + 자아)"""
        import json

        self._memory.save()

        # 발달/자아 상태도 저장
        if self.config.memory_path:
            import os
            os.makedirs(self.config.memory_path, exist_ok=True)

            state_data = {
                "development": {
                    "stage": self._development.stage.value,
                    "experience_count": self._development._experience_count,
                    "success_count": self._development._success_count,
                    "milestones": [m.name for m in self._development._milestones],
                },
                "self_model": self._self.get_state(),
                "experience_counter": self._experience_counter,
            }

            state_path = os.path.join(self.config.memory_path, "state.json")
            with open(state_path, "w", encoding="utf-8") as f:
                json.dump(state_data, f, indent=2, ensure_ascii=False)

        # Supabase에 baby_state 저장
        if self._db:
            try:
                emotional_state = self._emotions.get_state()
                dev_progress = self._development.get_progress()

                self._db.update_baby_state(
                    development_stage=self._development.stage.value,
                    experience_count=self._development._experience_count,
                    success_count=self._development._success_count,
                    progress=dev_progress.get("progress_to_next", 0) * 100,
                    curiosity=emotional_state.curiosity,
                    joy=emotional_state.joy,
                    fear=emotional_state.fear,
                    surprise=emotional_state.surprise,
                    frustration=emotional_state.frustration,
                    boredom=emotional_state.boredom,
                    dominant_emotion=emotional_state.dominant_emotion.value,
                    milestones=[m.name for m in self._development._milestones if m.achieved],
                )
                if self.config.verbose:
                    print("[SUPABASE] Baby state saved to cloud")
            except Exception as e:
                if self.config.verbose:
                    print(f"[SUPABASE] Failed to save baby state: {e}")

    def _load_state(self) -> None:
        """저장된 상태 로드"""
        import json
        import os

        if not self.config.memory_path:
            return

        state_path = os.path.join(self.config.memory_path, "state.json")
        if not os.path.exists(state_path):
            return

        try:
            with open(state_path, "r", encoding="utf-8") as f:
                state_data = json.load(f)

            # 발달 상태 복원
            if "development" in state_data:
                dev = state_data["development"]
                self._development._experience_count = dev.get("experience_count", 0)
                self._development._success_count = dev.get("success_count", 0)
                # 저장된 단계 복원
                saved_stage = dev.get("stage", 0)
                from .development import DevelopmentStage
                self._development._stage = DevelopmentStage(saved_stage)
                # unique_tasks 복원 (episodic memory에서 추출)
                self._restore_unique_tasks()
                # 마일스톤 달성 상태 복원
                achieved_milestones = dev.get("milestones", [])
                for milestone in self._development._milestones:
                    if milestone.name in achieved_milestones:
                        milestone.achieved = True
                # 단계 진행 체크 (조건 충족 시 승급)
                self._development._check_stage_advance()

            # 경험 카운터 복원
            self._experience_counter = state_data.get("experience_counter", 0)

            if self.config.verbose:
                print(f"[BABY] Loaded previous state: {self._development._experience_count} experiences")

        except Exception as e:
            if self.config.verbose:
                print(f"[BABY] Could not load previous state: {e}")

    def _restore_unique_tasks(self) -> None:
        """episodic memory에서 unique task types 복원"""
        import json
        import os

        episodic_path = os.path.join(self.config.memory_path, "episodic.json")
        if not os.path.exists(episodic_path):
            return

        try:
            with open(episodic_path, "r", encoding="utf-8") as f:
                episodic_data = json.load(f)

            # short_term과 long_term에서 task_type 추출
            task_types = set()
            for exp in episodic_data.get("short_term", []):
                if "task_type" in exp:
                    task_types.add(exp["task_type"])
            for exp in episodic_data.get("long_term", []):
                if "task_type" in exp:
                    task_types.add(exp["task_type"])

            self._development._unique_tasks = task_types

            if self.config.verbose and task_types:
                print(f"[BABY] Restored {len(task_types)} unique task types: {task_types}")

        except Exception as e:
            if self.config.verbose:
                print(f"[BABY] Could not restore unique tasks: {e}")

    def get_state(self) -> dict:
        """전체 상태"""
        state = {
            "session_start": self._session_start.isoformat(),
            "experience_count": self._experience_counter,
            "emotional_state": self._emotions.get_state().to_dict(),
            "development": self._development.get_progress(),
            "self_model": self._self.get_state(),
            "memory": self._memory.get_stats(),
            "curiosity": self._curiosity.get_stats(),
            "cognitive_router": self._cognitive_router.get_routing_stats(),
        }

        # Phase 3: 감정 영향 정보 추가
        if self._emotional_modulator:
            state["emotional_influence"] = self._emotions.get_emotional_influence()
            state["emotional_modulator"] = self._emotional_modulator.get_stats()

        return state

    def __repr__(self) -> str:
        stage = self._development.stage
        return (
            f"BabySubstrate("
            f"stage={stage.name}, "
            f"experiences={self._experience_counter}, "
            f"emotions={self._emotions})"
        )

    # ==================== Phase 4: 멀티모달 처리 ====================

    async def process_multimodal(
        self,
        text: str = None,
        images: list[bytes] = None,
        audio: bytes = None,
    ) -> BabyResult:
        """
        멀티모달 입력 처리

        Phase 4: 텍스트 + 이미지 + 오디오를 통합 처리

        Args:
            text: 텍스트 입력 (질문, 명령 등)
            images: 이미지 바이너리 리스트
            audio: 오디오 바이너리 (Phase 4.2)

        Returns:
            BabyResult: 처리 결과
        """
        import time
        start_time = time.time()

        # 미디어 타입 결정
        media_type = "text"
        visual_experience_dict = {}

        if self.config.verbose:
            print("\n[BABY] Processing multimodal input...")
            if text:
                print(f"  - Text: {text[:50]}...")
            if images:
                print(f"  - Images: {len(images)} files")
            if audio:
                print(f"  - Audio: {len(audio)} bytes")

        # 1. 이미지 처리 (Phase 4.1)
        if images and self._vision_processor:
            media_type = "image"
            for i, img_data in enumerate(images):
                if self.config.verbose:
                    print(f"\n[VISION] Processing image {i+1}/{len(images)}...")

                # VisualInput 생성
                visual_input = VisualInput(
                    image_data=img_data,
                    mime_type=self._llm_client.detect_image_mime_type(img_data) if self._llm_client else "image/jpeg",
                    source=VisualSource.UPLOAD,
                )

                # 시각 처리
                try:
                    visual_exp = await self._vision_processor.process_image(
                        visual_input=visual_input,
                        development_stage=self._development.stage.value,
                        emotional_state=self._emotions.get_state().to_dict(),
                    )

                    # 감정 업데이트 (시각적 자극에 반응)
                    self._apply_visual_emotional_response(visual_exp.emotional_response)

                    # 시각적 경험 저장
                    visual_experience_dict = visual_exp.to_dict()

                    if self.config.verbose:
                        print(f"  Scene: {visual_exp.scene_type}")
                        print(f"  Objects: {[obj.name for obj in visual_exp.objects_detected]}")
                        print(f"  Description: {visual_exp.description[:100]}...")

                except Exception as e:
                    if self.config.verbose:
                        print(f"[VISION] Error processing image: {e}")

        # 2. 텍스트와 이미지 결합 처리
        combined_prompt = text or ""
        if images and visual_experience_dict:
            # 시각적 설명을 컨텍스트로 추가
            visual_context = f"\n[시각적 컨텍스트]\n{visual_experience_dict.get('description', '')}"
            if visual_experience_dict.get('objects_detected'):
                objects = [obj['name'] for obj in visual_experience_dict['objects_detected']]
                visual_context += f"\n감지된 객체: {', '.join(objects)}"
            combined_prompt = visual_context + "\n\n" + (text or "이 이미지에 대해 설명해주세요.")

        # 3. 기존 process() 로직과 통합
        if combined_prompt:
            # 텍스트 처리는 기존 process() 활용
            result = await self.process(combined_prompt)

            # 멀티모달 정보 추가
            result.visual_experience = visual_experience_dict
            result.media_type = media_type

            return result

        # 이미지만 있는 경우
        execution_time = (time.time() - start_time) * 1000

        return BabyResult(
            success=bool(visual_experience_dict),
            output=visual_experience_dict.get('description', '입력이 없습니다.'),
            iterations=1,
            execution_time_ms=execution_time,
            emotional_state=self._emotions.get_state().to_dict(),
            curiosity_signal=self._curiosity.get_stats(),
            development_progress=self._development.get_progress(),
            memory_stats=self._memory.get_stats(),
            visual_experience=visual_experience_dict,
            media_type=media_type,
        )

    def _apply_visual_emotional_response(self, emotional_response: dict) -> None:
        """시각적 자극에 대한 감정 반응 적용"""
        if not emotional_response:
            return

        # 호기심 변화
        if emotional_response.get("curiosity_change", 0) > 0:
            self._emotions.on_novelty(emotional_response["curiosity_change"])

        # 기쁨 변화 (사회적 자극)
        if emotional_response.get("joy_change", 0) > 0:
            self._emotions.on_success()

        # 두려움 변화
        if emotional_response.get("fear_change", 0) > 0:
            self._emotions.on_uncertainty()

        # 놀람 변화
        if emotional_response.get("surprise_change", 0) > 0:
            self._emotions.on_novelty(emotional_response["surprise_change"])

    async def process_image(self, image_data: bytes, prompt: str = None) -> BabyResult:
        """
        이미지 단일 처리 헬퍼

        Args:
            image_data: 이미지 바이너리
            prompt: 선택적 텍스트 프롬프트

        Returns:
            BabyResult
        """
        return await self.process_multimodal(
            text=prompt,
            images=[image_data],
        )


async def run_baby(user_request: str, config: BabyConfig = None) -> BabyResult:
    """Baby Substrate 실행 헬퍼"""
    baby = BabySubstrate(config or BabyConfig())
    return await baby.process(user_request)


# Singleton instance
_substrate: Optional[BabySubstrate] = None


def get_substrate(config: BabyConfig = None) -> BabySubstrate:
    """Get or create singleton BabySubstrate instance"""
    global _substrate
    if _substrate is None:
        _substrate = BabySubstrate(config or BabyConfig())
    return _substrate
