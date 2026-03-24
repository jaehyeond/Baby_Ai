"""
World Model - Baby AI의 세계 모델

세계를 이해하고 예측하는 인지 시스템:
- Prediction: 미래 상황 예측
- Simulation: 가상 시나리오 시뮬레이션
- Causal Reasoning: 인과관계 추론
- Imagination: 창의적 사고

발달 단계에 따라 능력이 확장됨
"""

import time
from dataclasses import dataclass, field
from typing import Optional, Any
from datetime import datetime
from enum import Enum
import json


class PredictionType(Enum):
    """예측 유형"""
    OUTCOME = "outcome"           # 결과 예측 (성공/실패)
    BEHAVIOR = "behavior"         # 행동 예측
    CONSEQUENCE = "consequence"   # 결과 예측
    PATTERN = "pattern"           # 패턴 기반 예측


class SimulationType(Enum):
    """시뮬레이션 유형"""
    PLANNING = "planning"         # 계획 시뮬레이션
    COUNTERFACTUAL = "counterfactual"  # 반사실적 시뮬레이션
    EXPLORATION = "exploration"   # 탐색 시뮬레이션
    REHEARSAL = "rehearsal"       # 연습 시뮬레이션


class ImaginationType(Enum):
    """상상 유형"""
    EXPLORATION = "exploration"   # 탐색적 상상
    CREATIVE = "creative"         # 창의적 상상
    PROBLEM_SOLVING = "problem_solving"  # 문제 해결 상상
    RECOMBINATION = "recombination"  # 재조합 상상


@dataclass
class PredictionResult:
    """예측 결과"""
    prediction_id: str
    scenario: str
    prediction: str
    confidence: float
    reasoning: str
    based_on_concepts: list[str] = field(default_factory=list)


@dataclass
class SimulationResult:
    """시뮬레이션 결과"""
    simulation_id: str
    steps: list[dict] = field(default_factory=list)
    predicted_outcome: dict = field(default_factory=dict)
    success_probability: float = 0.5
    insights: list[str] = field(default_factory=list)


@dataclass
class ImaginationResult:
    """상상 결과"""
    session_id: str
    topic: str
    thoughts: list[dict] = field(default_factory=list)
    insights: list[str] = field(default_factory=list)
    predictions_made: list[str] = field(default_factory=list)
    connections_discovered: list[dict] = field(default_factory=list)


class WorldModel:
    """
    세계 모델 엔진

    Baby AI가 세계를 이해하고 예측하는 핵심 시스템
    """

    def __init__(
        self,
        db=None,
        llm_client=None,
        development_stage: int = 0,
        verbose: bool = True,
    ):
        self._db = db
        self._llm_client = llm_client
        self._development_stage = development_stage
        self._verbose = verbose

        # 활성 상상 세션
        self._active_imagination: Optional[str] = None

        # 예측 통계
        self._prediction_count = 0
        self._correct_predictions = 0

    def set_development_stage(self, stage: int) -> None:
        """발달 단계 설정"""
        self._development_stage = stage

    def can_predict(self) -> bool:
        """예측 가능 여부 (발달 단계 기반)"""
        return self._development_stage >= 2  # BABY 단계부터

    def can_simulate(self) -> bool:
        """시뮬레이션 가능 여부"""
        return self._development_stage >= 3  # TODDLER 단계부터

    def can_imagine(self) -> bool:
        """상상 가능 여부"""
        return self._development_stage >= 3  # TODDLER 단계부터

    def can_reason_causally(self) -> bool:
        """인과 추론 가능 여부"""
        return self._development_stage >= 4  # CHILD 단계부터

    # ==================== Prediction ====================

    def make_prediction(
        self,
        scenario: str,
        context: dict = None,
        prediction_type: PredictionType = PredictionType.OUTCOME,
    ) -> Optional[PredictionResult]:
        """
        시나리오에 대한 예측 생성
        """
        if not self.can_predict():
            if self._verbose:
                print("[WORLD_MODEL] 예측 능력이 아직 발달하지 않았습니다")
            return None

        if not self._llm_client:
            if self._verbose:
                print("[WORLD_MODEL] LLM 클라이언트가 없습니다")
            return None

        # 관련 개념 수집
        related_concepts = []
        if self._db:
            try:
                concepts = self._db.get_all_concepts()
                # 시나리오와 관련된 개념 필터링 (간단한 키워드 매칭)
                scenario_lower = scenario.lower()
                for concept in concepts[:20]:  # 상위 20개만 검사
                    if concept["name"].lower() in scenario_lower:
                        related_concepts.append(concept["name"])
            except Exception as e:
                if self._verbose:
                    print(f"[WORLD_MODEL] 개념 수집 실패: {e}")

        # LLM으로 예측 생성
        prompt = f"""당신은 예측 AI입니다. 주어진 시나리오에 대해 예측을 생성하세요.

시나리오: {scenario}

관련 개념: {', '.join(related_concepts) if related_concepts else '없음'}

다음 형식으로 응답하세요:
예측: [예측 내용]
신뢰도: [0.0-1.0 사이 숫자]
근거: [예측 근거]"""

        try:
            response = self._llm_client.generate(
                prompt=prompt,
                max_tokens=500,
            )

            # 응답 파싱
            prediction_text = ""
            confidence = 0.5
            reasoning = ""

            lines = response.strip().split('\n')
            for line in lines:
                if line.startswith("예측:"):
                    prediction_text = line.replace("예측:", "").strip()
                elif line.startswith("신뢰도:"):
                    try:
                        confidence = float(line.replace("신뢰도:", "").strip())
                    except:
                        confidence = 0.5
                elif line.startswith("근거:"):
                    reasoning = line.replace("근거:", "").strip()

            if not prediction_text:
                prediction_text = response[:200]

            # DB에 저장
            prediction_id = ""
            if self._db:
                try:
                    result = self._db.insert_prediction(
                        scenario=scenario,
                        prediction=prediction_text,
                        confidence=confidence,
                        reasoning=reasoning,
                        based_on_concepts=related_concepts,
                        prediction_type=prediction_type.value,
                        development_stage=self._development_stage,
                    )
                    prediction_id = result.get("id", "")
                except Exception as e:
                    if self._verbose:
                        print(f"[WORLD_MODEL] 예측 저장 실패: {e}")

            self._prediction_count += 1

            if self._verbose:
                print(f"[WORLD_MODEL] 예측 생성: {prediction_text[:50]}... (신뢰도: {confidence:.2f})")

            return PredictionResult(
                prediction_id=prediction_id,
                scenario=scenario,
                prediction=prediction_text,
                confidence=confidence,
                reasoning=reasoning,
                based_on_concepts=related_concepts,
            )

        except Exception as e:
            if self._verbose:
                print(f"[WORLD_MODEL] 예측 생성 실패: {e}")
            return None

    def verify_prediction(
        self,
        prediction_id: str,
        actual_outcome: str,
    ) -> bool:
        """예측 검증"""
        if not self._db or not self._llm_client:
            return False

        # 원래 예측 조회
        predictions = self._db.get_recent_predictions(limit=50)
        original = None
        for p in predictions:
            if p.get("id") == prediction_id:
                original = p
                break

        if not original:
            return False

        # LLM으로 정확도 판단
        prompt = f"""예측의 정확성을 판단하세요.

원래 예측: {original.get('prediction', '')}
실제 결과: {actual_outcome}

예측이 맞았나요? "correct" 또는 "incorrect"로 답하세요."""

        try:
            response = self._llm_client.generate(prompt=prompt, max_tokens=50)
            was_correct = "correct" in response.lower() and "incorrect" not in response.lower()

            # DB 업데이트
            self._db.verify_prediction(
                prediction_id=prediction_id,
                actual_outcome=actual_outcome,
                was_correct=was_correct,
                prediction_error=0.0 if was_correct else 1.0,
            )

            if was_correct:
                self._correct_predictions += 1

            if self._verbose:
                result = "정확" if was_correct else "부정확"
                print(f"[WORLD_MODEL] 예측 검증: {result}")

            return was_correct

        except Exception as e:
            if self._verbose:
                print(f"[WORLD_MODEL] 예측 검증 실패: {e}")
            return False

    # ==================== Simulation ====================

    def run_simulation(
        self,
        initial_state: dict,
        goal: str,
        simulation_type: SimulationType = SimulationType.PLANNING,
        max_steps: int = 5,
    ) -> Optional[SimulationResult]:
        """
        시뮬레이션 실행
        """
        if not self.can_simulate():
            if self._verbose:
                print("[WORLD_MODEL] 시뮬레이션 능력이 아직 발달하지 않았습니다")
            return None

        if not self._llm_client:
            return None

        steps = []
        current_state = initial_state.copy()

        # 시뮬레이션 시작 (DB 저장)
        simulation_id = ""
        if self._db:
            try:
                result = self._db.insert_simulation(
                    initial_state=initial_state,
                    target_goal=goal,
                    simulation_type=simulation_type.value,
                    development_stage=self._development_stage,
                )
                simulation_id = result.get("id", "")
            except Exception as e:
                if self._verbose:
                    print(f"[WORLD_MODEL] 시뮬레이션 저장 실패: {e}")

        # 단계별 시뮬레이션
        for step_num in range(1, max_steps + 1):
            prompt = f"""시뮬레이션 단계 {step_num}

현재 상태: {current_state}
목표: {goal}

다음 행동과 예상 결과를 JSON 형식으로 제공하세요:
{{"action": "행동", "outcome": "결과", "new_state": {{"key": "value"}}}}"""

            try:
                response = self._llm_client.generate(prompt=prompt, max_tokens=300)

                # JSON 파싱 시도
                try:
                    # JSON 부분 추출
                    start = response.find('{')
                    end = response.rfind('}') + 1
                    if start >= 0 and end > start:
                        step_data = json.loads(response[start:end])
                    else:
                        step_data = {
                            "action": response[:100],
                            "outcome": "unknown",
                            "new_state": current_state,
                        }
                except json.JSONDecodeError:
                    step_data = {
                        "action": response[:100],
                        "outcome": "unknown",
                        "new_state": current_state,
                    }

                step_data["step"] = step_num
                steps.append(step_data)

                # 상태 업데이트
                if "new_state" in step_data and isinstance(step_data["new_state"], dict):
                    current_state.update(step_data["new_state"])

            except Exception as e:
                if self._verbose:
                    print(f"[WORLD_MODEL] 시뮬레이션 단계 {step_num} 실패: {e}")
                break

        # 성공 확률 계산
        success_probability = 0.5
        if steps:
            successful_steps = sum(1 for s in steps if s.get("outcome") != "failure")
            success_probability = successful_steps / len(steps)

        # DB 업데이트
        if self._db and simulation_id:
            try:
                self._db.complete_simulation(
                    simulation_id=simulation_id,
                    actual_outcome=current_state,
                    was_validated=False,
                    accuracy_score=success_probability,
                )
            except Exception as e:
                if self._verbose:
                    print(f"[WORLD_MODEL] 시뮬레이션 완료 저장 실패: {e}")

        if self._verbose:
            print(f"[WORLD_MODEL] 시뮬레이션 완료: {len(steps)} 단계, 성공 확률: {success_probability:.2f}")

        return SimulationResult(
            simulation_id=simulation_id,
            steps=steps,
            predicted_outcome=current_state,
            success_probability=success_probability,
        )

    # ==================== Imagination ====================

    def start_imagination(
        self,
        topic: str,
        trigger: str = None,
        imagination_type: ImaginationType = ImaginationType.EXPLORATION,
        emotional_state: dict = None,
        curiosity_level: float = 0.5,
    ) -> Optional[str]:
        """
        상상 세션 시작
        """
        if not self.can_imagine():
            if self._verbose:
                print("[WORLD_MODEL] 상상 능력이 아직 발달하지 않았습니다")
            return None

        if self._active_imagination:
            if self._verbose:
                print("[WORLD_MODEL] 이미 활성 상상 세션이 있습니다")
            return self._active_imagination

        session_id = ""
        if self._db:
            try:
                result = self._db.start_imagination_session(
                    topic=topic,
                    trigger=trigger,
                    imagination_type=imagination_type.value,
                    curiosity_level=curiosity_level,
                    emotional_state=emotional_state,
                    development_stage=self._development_stage,
                )
                session_id = result.get("id", "")
                self._active_imagination = session_id
            except Exception as e:
                if self._verbose:
                    print(f"[WORLD_MODEL] 상상 세션 시작 실패: {e}")
                return None

        if self._verbose:
            print(f"[WORLD_MODEL] 상상 시작: {topic}")

        return session_id

    def imagine_thought(
        self,
        thought_type: str = "exploration",
    ) -> Optional[dict]:
        """
        상상 중 생각 생성
        """
        if not self._active_imagination or not self._llm_client:
            return None

        # 현재 세션 정보 가져오기
        session = None
        if self._db:
            session = self._db.get_active_imagination_session()

        if not session:
            return None

        topic = session.get("topic", "")
        previous_thoughts = session.get("thoughts", [])

        prompt = f"""상상 세션 - 주제: {topic}

이전 생각들: {previous_thoughts[-3:] if previous_thoughts else '없음'}

새로운 생각을 하나 생성하세요. 유형: {thought_type}

JSON 형식으로 응답:
{{"content": "생각 내용", "type": "{thought_type}", "connections": ["관련 개념1", "관련 개념2"]}}"""

        try:
            response = self._llm_client.generate(prompt=prompt, max_tokens=200)

            try:
                start = response.find('{')
                end = response.rfind('}') + 1
                if start >= 0 and end > start:
                    thought = json.loads(response[start:end])
                else:
                    thought = {
                        "content": response[:150],
                        "type": thought_type,
                        "connections": [],
                    }
            except json.JSONDecodeError:
                thought = {
                    "content": response[:150],
                    "type": thought_type,
                    "connections": [],
                }

            thought["timestamp"] = datetime.utcnow().isoformat()

            # DB에 추가
            if self._db:
                self._db.add_imagination_thought(self._active_imagination, thought)

            if self._verbose:
                print(f"[WORLD_MODEL] 상상: {thought.get('content', '')[:50]}...")

            return thought

        except Exception as e:
            if self._verbose:
                print(f"[WORLD_MODEL] 생각 생성 실패: {e}")
            return None

    def end_imagination(self) -> Optional[ImaginationResult]:
        """
        상상 세션 종료
        """
        if not self._active_imagination:
            return None

        session_id = self._active_imagination
        session = None

        if self._db:
            session = self._db.get_active_imagination_session()

        if not session:
            self._active_imagination = None
            return None

        # 인사이트 추출
        insights = []
        thoughts = session.get("thoughts", [])

        if thoughts and self._llm_client:
            prompt = f"""다음 생각들에서 핵심 인사이트를 추출하세요:

{thoughts}

JSON 배열로 인사이트 3개를 제공하세요:
["인사이트1", "인사이트2", "인사이트3"]"""

            try:
                response = self._llm_client.generate(prompt=prompt, max_tokens=200)
                try:
                    start = response.find('[')
                    end = response.rfind(']') + 1
                    if start >= 0 and end > start:
                        insights = json.loads(response[start:end])
                except:
                    insights = [response[:100]]
            except:
                pass

        # 세션 종료
        start_time = session.get("started_at")
        duration_ms = None
        if start_time:
            try:
                start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                duration_ms = int((datetime.utcnow() - start_dt.replace(tzinfo=None)).total_seconds() * 1000)
            except:
                pass

        if self._db:
            self._db.end_imagination_session(
                session_id=session_id,
                insights=insights,
                duration_ms=duration_ms,
            )

        self._active_imagination = None

        if self._verbose:
            print(f"[WORLD_MODEL] 상상 종료: {len(insights)} 인사이트")

        return ImaginationResult(
            session_id=session_id,
            topic=session.get("topic", ""),
            thoughts=thoughts,
            insights=insights,
        )

    # ==================== Causal Reasoning ====================

    def discover_causal_relation(
        self,
        cause_concept: str,
        effect_concept: str,
        evidence: str = None,
    ) -> Optional[dict]:
        """
        인과 관계 발견
        """
        if not self.can_reason_causally():
            if self._verbose:
                print("[WORLD_MODEL] 인과 추론 능력이 아직 발달하지 않았습니다")
            return None

        if not self._db:
            return None

        # 개념 ID 조회
        cause = self._db.get_concept_by_name(cause_concept)
        effect = self._db.get_concept_by_name(effect_concept)

        if not cause or not effect:
            if self._verbose:
                print(f"[WORLD_MODEL] 개념을 찾을 수 없음: {cause_concept}, {effect_concept}")
            return None

        # 관계 유형 결정
        relationship_type = "causes"
        if self._llm_client:
            prompt = f"""'{cause_concept}'과(와) '{effect_concept}'의 관계 유형을 하나만 선택하세요:
- causes (원인-결과)
- enables (가능하게 함)
- prevents (방지)
- correlates (상관관계)

한 단어로만 응답: """

            try:
                response = self._llm_client.generate(prompt=prompt, max_tokens=20)
                response_lower = response.lower().strip()
                if "enables" in response_lower:
                    relationship_type = "enables"
                elif "prevents" in response_lower:
                    relationship_type = "prevents"
                elif "correlates" in response_lower:
                    relationship_type = "correlates"
            except:
                pass

        # DB에 저장
        try:
            result = self._db.upsert_causal_model(
                cause_concept_id=cause["id"],
                effect_concept_id=effect["id"],
                relationship_type=relationship_type,
                discovered_at_stage=self._development_stage,
            )

            if self._verbose:
                print(f"[WORLD_MODEL] 인과 관계 발견: {cause_concept} {relationship_type} {effect_concept}")

            return result

        except Exception as e:
            if self._verbose:
                print(f"[WORLD_MODEL] 인과 관계 저장 실패: {e}")
            return None

    def extract_causal_relations_from_experience(
        self,
        experience: dict,
        emotional_state: dict = None,
    ) -> list[dict]:
        """
        경험에서 인과관계 자동 추출

        전략:
        1. 경험의 감정 변화에서 인과관계 추출 (행동 → 감정)
        2. 성공/실패와 관련된 인과관계 추출
        3. 관련 개념들 사이의 인과관계 탐색
        """
        if not self.can_reason_causally():
            return []

        if not self._db or not self._llm_client:
            return []

        discovered_relations = []
        task = experience.get("task", "")
        success = experience.get("success", False)
        task_type = experience.get("task_type", "general")

        # 1. 감정 기반 인과관계 (행동 → 감정)
        if emotional_state:
            emotion_causal_pairs = self._extract_emotion_based_causality(
                task, task_type, success, emotional_state
            )
            discovered_relations.extend(emotion_causal_pairs)

        # 2. 성공/실패 기반 인과관계
        outcome_causal_pairs = self._extract_outcome_based_causality(
            task, task_type, success
        )
        discovered_relations.extend(outcome_causal_pairs)

        # 3. 개념 관계에서 인과관계 추론 (LLM 기반)
        if len(discovered_relations) < 3:  # 충분한 관계가 없을 때만
            concept_causal_pairs = self._extract_concept_based_causality(task)
            discovered_relations.extend(concept_causal_pairs)

        if self._verbose and discovered_relations:
            print(f"[WORLD_MODEL] 인과관계 {len(discovered_relations)}개 발견")

        return discovered_relations

    def _extract_emotion_based_causality(
        self,
        task: str,
        task_type: str,
        success: bool,
        emotional_state: dict,
    ) -> list[dict]:
        """감정 변화에서 인과관계 추출"""
        relations = []

        # 감정-원인 매핑
        emotion_triggers = {
            "curiosity": ("질문", "호기심"),
            "joy": ("성공", "기쁨") if success else None,
            "frustration": ("실패", "좌절") if not success else None,
            "fear": ("위험", "두려움"),
            "surprise": ("새로움", "놀람"),
        }

        for emotion, trigger_pair in emotion_triggers.items():
            if trigger_pair and emotional_state.get(emotion, 0) > 0.6:
                cause_name, effect_name = trigger_pair
                relation = self.discover_causal_relation(
                    cause_concept=cause_name,
                    effect_concept=effect_name,
                    evidence=f"경험: {task[:50]}...",
                )
                if relation:
                    relations.append(relation)

        # 작업 유형별 인과관계
        task_type_emotions = {
            "learning": ("학습", "이해"),
            "conversation": ("대화", "연결"),
            "exploration": ("탐험", "발견"),
        }

        if task_type in task_type_emotions:
            cause, effect = task_type_emotions[task_type]
            relation = self.discover_causal_relation(
                cause_concept=cause,
                effect_concept=effect,
                evidence=f"작업 유형: {task_type}",
            )
            if relation:
                relations.append(relation)

        return relations

    def _extract_outcome_based_causality(
        self,
        task: str,
        task_type: str,
        success: bool,
    ) -> list[dict]:
        """성공/실패에서 인과관계 추출"""
        relations = []

        if success:
            # 성공 패턴
            success_pairs = [
                ("노력", "성공"),
                ("이해", "성공"),
                ("연습", "향상"),
            ]
            for cause, effect in success_pairs[:1]:  # 한 번에 하나씩만
                relation = self.discover_causal_relation(
                    cause_concept=cause,
                    effect_concept=effect,
                    evidence=f"성공 경험: {task[:30]}",
                )
                if relation:
                    relations.append(relation)
        else:
            # 실패 패턴
            failure_pairs = [
                ("실수", "실패"),
                ("서두름", "실수"),
            ]
            for cause, effect in failure_pairs[:1]:
                relation = self.discover_causal_relation(
                    cause_concept=cause,
                    effect_concept=effect,
                    evidence=f"실패 경험: {task[:30]}",
                )
                if relation:
                    relations.append(relation)

        return relations

    def _extract_concept_based_causality(self, task: str) -> list[dict]:
        """
        LLM을 사용해 task에서 인과관계 추출
        """
        relations = []

        if not self._llm_client:
            return relations

        try:
            prompt = f"""다음 경험에서 인과관계를 찾아주세요.

경험: "{task}"

인과관계를 JSON 배열로 응답하세요. 각 항목은 {{"cause": "원인개념", "effect": "결과개념"}} 형식입니다.
- 최대 2개까지만
- 일반적인 개념 사용 (예: 질문, 학습, 호기심, 이해 등)
- 관계가 없으면 빈 배열 []

JSON만 응답:"""

            response = self._llm_client.generate(prompt=prompt, max_tokens=150)

            # JSON 파싱
            import re
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                causal_pairs = json.loads(json_match.group())

                for pair in causal_pairs[:2]:
                    if "cause" in pair and "effect" in pair:
                        relation = self.discover_causal_relation(
                            cause_concept=pair["cause"],
                            effect_concept=pair["effect"],
                            evidence=f"LLM 추출: {task[:30]}",
                        )
                        if relation:
                            relations.append(relation)

        except Exception as e:
            if self._verbose:
                print(f"[WORLD_MODEL] LLM 인과관계 추출 실패: {e}")

        return relations

    # ==================== Auto-Verification ====================

    def auto_verify_predictions(
        self,
        current_experience: dict,
    ) -> list[dict]:
        """
        현재 경험을 기반으로 이전 예측들을 자동 검증

        전략:
        1. 미검증 예측 중 현재 경험과 관련된 것 찾기
        2. 예측 시나리오와 실제 결과 비교
        3. auto_verified = true로 표시
        """
        if not self._db or not self._llm_client:
            return []

        verified_predictions = []
        task = current_experience.get("task", "")
        task_type = current_experience.get("task_type", "general")
        success = current_experience.get("success", False)

        # 미검증 예측 조회
        try:
            unverified = self._db.get_unverified_predictions(limit=20)
        except Exception as e:
            if self._verbose:
                print(f"[WORLD_MODEL] 미검증 예측 조회 실패: {e}")
            return []

        if not unverified:
            return []

        # 각 예측에 대해 관련성 확인 및 검증
        for prediction in unverified:
            scenario = prediction.get("scenario", "")
            prediction_text = prediction.get("prediction", "")
            prediction_id = prediction.get("id", "")

            # 관련성 확인 (시나리오에 task_type이 포함되어 있는지)
            is_related = (
                task_type.lower() in scenario.lower() or
                any(keyword in scenario.lower() for keyword in task.lower().split()[:3])
            )

            if not is_related:
                continue

            # LLM으로 예측 정확성 판단
            actual_outcome = f"task_type: {task_type}, success: {success}, task: {task[:100]}"

            try:
                prompt = f"""예측의 정확성을 판단하세요.

원래 예측: {prediction_text}
시나리오: {scenario}

실제 결과: {actual_outcome}

이 예측이 맞았나요?
- "correct": 예측과 실제 결과가 대체로 일치
- "incorrect": 예측과 실제 결과가 다름
- "uncertain": 판단 불가

한 단어로만 응답:"""

                response = self._llm_client.generate(prompt=prompt, max_tokens=30)
                response_lower = response.lower().strip()

                # 판단 불가면 건너뛰기
                if "uncertain" in response_lower:
                    continue

                was_correct = "correct" in response_lower and "incorrect" not in response_lower

                # DB 업데이트 (auto_verified 플래그 포함)
                update_data = {
                    "actual_outcome": actual_outcome,
                    "was_correct": was_correct,
                    "prediction_error": 0.0 if was_correct else 1.0,
                    "verified_at": datetime.utcnow().isoformat(),
                    "auto_verified": True,
                    "verification_context": {
                        "verified_by": "auto_verify_predictions",
                        "related_task": task[:100],
                        "task_type": task_type,
                        "task_success": success,
                    },
                }

                self._db.client.table("predictions").update(update_data).eq("id", prediction_id).execute()

                verified_predictions.append({
                    "prediction_id": prediction_id,
                    "was_correct": was_correct,
                    "scenario": scenario[:50],
                })

                if was_correct:
                    self._correct_predictions += 1

                if self._verbose:
                    result = "[O] 정확" if was_correct else "[X] 부정확"
                    print(f"[WORLD_MODEL] 예측 자동검증: {result} - {scenario[:30]}...")

            except Exception as e:
                if self._verbose:
                    print(f"[WORLD_MODEL] 예측 검증 실패 ({prediction_id}): {e}")
                continue

        if self._verbose and verified_predictions:
            correct_count = sum(1 for p in verified_predictions if p["was_correct"])
            print(f"[WORLD_MODEL] 자동 검증 완료: {len(verified_predictions)}개 중 {correct_count}개 정확")

        return verified_predictions

    # ==================== Auto-Generation ====================

    def auto_generate_from_experience(
        self,
        experience: dict,
        emotional_state: dict = None,
    ) -> dict:
        """
        경험에서 자동으로 World Model 데이터 생성

        - 예측 검증 (이전 예측들 자동 검증)
        - 예측 생성 (성공/실패 예측)
        - 간단한 시뮬레이션
        - 상상 세션 (호기심이 높을 때)
        - 인과관계 발견 (CHILD 단계부터)
        """
        results = {
            "verified_predictions": [],
            "prediction": None,
            "simulation": None,
            "imagination": None,
            "causal_relations": [],
        }

        task = experience.get("task", "")
        success = experience.get("success", False)
        task_type = experience.get("task_type", "general")

        # 0. 이전 예측 자동 검증 (예측 능력이 있을 때)
        if self.can_predict():
            try:
                verified = self.auto_verify_predictions(experience)
                results["verified_predictions"] = verified

                if self._verbose and verified:
                    print(f"[WORLD_MODEL] 이전 예측 {len(verified)}개 자동 검증 완료")

            except Exception as e:
                if self._verbose:
                    print(f"[WORLD_MODEL] 예측 자동 검증 오류: {e}")

        # 1. 예측 생성 (다음 유사 작업 결과 예측)
        if self.can_predict():
            scenario = f"다음 '{task_type}' 유형의 작업을 수행할 때"
            results["prediction"] = self.make_prediction(
                scenario=scenario,
                context={"previous_success": success},
                prediction_type=PredictionType.OUTCOME,
            )

        # 2. 시뮬레이션 (문제 해결 계획)
        if self.can_simulate() and not success:
            # 실패한 경우 다른 접근 방식 시뮬레이션
            results["simulation"] = self.run_simulation(
                initial_state={"task": task, "approach": "alternative"},
                goal="성공적인 완료",
                simulation_type=SimulationType.PLANNING,
                max_steps=3,
            )

        # 3. 상상 세션 (호기심이 높을 때)
        curiosity = 0.5
        if emotional_state:
            curiosity = emotional_state.get("curiosity", 0.5)

        if self.can_imagine() and curiosity > 0.7:
            session_id = self.start_imagination(
                topic=f"{task_type} 관련 탐색",
                trigger="high_curiosity",
                curiosity_level=curiosity,
                emotional_state=emotional_state,
            )

            if session_id:
                # 몇 가지 생각 생성
                for _ in range(2):
                    self.imagine_thought(thought_type="exploration")

                results["imagination"] = self.end_imagination()

        # 4. 인과관계 발견 (CHILD 단계부터)
        if self.can_reason_causally():
            try:
                causal_relations = self.extract_causal_relations_from_experience(
                    experience=experience,
                    emotional_state=emotional_state,
                )
                results["causal_relations"] = causal_relations

                if self._verbose and causal_relations:
                    print(f"[WORLD_MODEL] 인과관계 {len(causal_relations)}개 저장됨")

            except Exception as e:
                if self._verbose:
                    print(f"[WORLD_MODEL] 인과관계 추출 오류: {e}")

        return results

    # ==================== Stats ====================

    def get_stats(self) -> dict:
        """World Model 통계"""
        accuracy = 0.0
        if self._prediction_count > 0:
            accuracy = self._correct_predictions / self._prediction_count

        return {
            "prediction_count": self._prediction_count,
            "correct_predictions": self._correct_predictions,
            "accuracy": accuracy,
            "can_predict": self.can_predict(),
            "can_simulate": self.can_simulate(),
            "can_imagine": self.can_imagine(),
            "can_reason_causally": self.can_reason_causally(),
            "development_stage": self._development_stage,
            "active_imagination": self._active_imagination is not None,
        }
