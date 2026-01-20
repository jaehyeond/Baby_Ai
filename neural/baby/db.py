"""
Supabase Database Client for Baby Brain

Robot_Brain 프로젝트 DB 연동
- experiences 테이블: 에피소드 기억
- semantic_concepts 테이블: 의미 기억
- procedural_patterns 테이블: 절차 기억
- baby_state 테이블: 현재 상태 (싱글톤)
- emotion_logs 테이블: 감정 히스토리
"""

import os
from typing import Optional, Any
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Lazy import for supabase
_supabase_client = None


@dataclass
class SupabaseConfig:
    """Supabase 연결 설정"""
    url: str
    anon_key: str

    @classmethod
    def from_env(cls) -> "SupabaseConfig":
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_ANON_KEY")

        if not url or not key:
            raise ValueError(
                "SUPABASE_URL and SUPABASE_ANON_KEY must be set in environment variables"
            )

        return cls(url=url, anon_key=key)


def get_supabase_client():
    """Supabase 클라이언트 싱글톤"""
    global _supabase_client

    if _supabase_client is None:
        from supabase import create_client
        config = SupabaseConfig.from_env()
        _supabase_client = create_client(config.url, config.anon_key)

    return _supabase_client


class BrainDatabase:
    """
    Baby Brain Database Operations

    모든 테이블에 대한 CRUD 작업 제공
    """

    def __init__(self):
        self._client = None

    @property
    def client(self):
        if self._client is None:
            self._client = get_supabase_client()
        return self._client

    # ==================== baby_state (싱글톤) ====================

    def get_baby_state(self) -> Optional[dict]:
        """현재 baby_state 조회 (싱글톤)"""
        response = self.client.table("baby_state").select("*").limit(1).execute()
        return response.data[0] if response.data else None

    def update_baby_state(self, **kwargs) -> dict:
        """baby_state 업데이트"""
        state = self.get_baby_state()
        if not state:
            # 초기 상태 생성
            response = self.client.table("baby_state").insert(kwargs).execute()
        else:
            # 기존 상태 업데이트
            response = self.client.table("baby_state").update(kwargs).eq("id", state["id"]).execute()
        return response.data[0] if response.data else {}

    # ==================== experiences ====================

    def insert_experience(
        self,
        task: str,
        task_type: str,
        output: str,
        success: bool,
        emotional_salience: float = 0.5,
        dominant_emotion: str = None,
        embedding: list[float] = None,
        emotion_snapshot: dict = None,
        development_stage: int = 0,
        tags: list[str] = None,
        extras: dict = None,
    ) -> dict:
        """경험 저장"""
        data = {
            "task": task,
            "task_type": task_type,
            "output": output,
            "success": success,
            "emotional_salience": emotional_salience,
            "development_stage": development_stage,
        }

        if dominant_emotion:
            data["dominant_emotion"] = dominant_emotion
        if embedding:
            data["embedding"] = embedding
        if emotion_snapshot:
            data["emotion_snapshot"] = emotion_snapshot
        if tags:
            data["tags"] = tags
        if extras:
            data["extras"] = extras

        response = self.client.table("experiences").insert(data).execute()
        return response.data[0] if response.data else {}

    def search_similar_experiences(
        self,
        embedding: list[float],
        threshold: float = 0.7,
        limit: int = 5,
    ) -> list[dict]:
        """벡터 유사도로 경험 검색 (RPC 함수 호출)"""
        response = self.client.rpc(
            "search_similar_experiences",
            {
                "query_embedding": embedding,
                "match_threshold": threshold,
                "match_count": limit,
            }
        ).execute()
        return response.data or []

    def get_recent_experiences(self, limit: int = 10) -> list[dict]:
        """최근 경험 조회"""
        response = (
            self.client.table("experiences")
            .select("*")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return response.data or []

    def get_successful_experiences(
        self,
        task_type: str = None,
        limit: int = 5,
    ) -> list[dict]:
        """성공한 경험 조회"""
        query = self.client.table("experiences").select("*").eq("success", True)

        if task_type:
            query = query.eq("task_type", task_type)

        response = query.order("emotional_salience", desc=True).limit(limit).execute()
        return response.data or []

    def reinforce_memory(self, experience_id: str) -> None:
        """기억 강화 (RPC 함수 호출)"""
        self.client.rpc("reinforce_memory", {"exp_id": experience_id}).execute()

    # ==================== semantic_concepts ====================

    def insert_concept(
        self,
        name: str,
        category: str = None,
        description: str = None,
        embedding: list[float] = None,
        acquired_at_stage: int = 0,
    ) -> dict:
        """개념 저장"""
        data = {
            "name": name,
            "acquired_at_stage": acquired_at_stage,
        }

        if category:
            data["category"] = category
        if description:
            data["description"] = description
        if embedding:
            data["embedding"] = embedding

        response = self.client.table("semantic_concepts").insert(data).execute()
        return response.data[0] if response.data else {}

    def get_concept_by_name(self, name: str) -> Optional[dict]:
        """이름으로 개념 조회"""
        response = (
            self.client.table("semantic_concepts")
            .select("*")
            .eq("name", name)
            .limit(1)
            .execute()
        )
        return response.data[0] if response.data else None

    def update_concept_strength(self, concept_id: str, delta: float = 0.1) -> None:
        """개념 강도 업데이트"""
        concept = self.client.table("semantic_concepts").select("strength, usage_count").eq("id", concept_id).single().execute()
        if concept.data:
            new_strength = min(1.0, concept.data["strength"] + delta)
            self.client.table("semantic_concepts").update({
                "strength": new_strength,
                "usage_count": concept.data["usage_count"] + 1,
            }).eq("id", concept_id).execute()

    def link_experience_concept(
        self,
        experience_id: str,
        concept_id: str,
        confidence: float = 0.5,
    ) -> None:
        """경험-개념 연결 (Hebb's Law)"""
        self.client.rpc(
            "strengthen_experience_concept_link",
            {
                "p_experience_id": experience_id,
                "p_concept_id": concept_id,
                "p_boost": confidence * 0.2,
            }
        ).execute()

    def get_associated_concepts(
        self,
        experience_id: str,
        min_confidence: float = 0.3,
        limit: int = 10,
    ) -> list[dict]:
        """경험에 연관된 개념 조회"""
        response = self.client.rpc(
            "find_associated_concepts",
            {
                "p_experience_id": experience_id,
                "p_min_confidence": min_confidence,
                "p_limit": limit,
            }
        ).execute()
        return response.data or []

    # ==================== procedural_patterns ====================

    def upsert_pattern(
        self,
        task_type: str,
        approach: str,
        success: bool,
    ) -> dict:
        """절차 패턴 저장/업데이트"""
        # 기존 패턴 확인
        existing = (
            self.client.table("procedural_patterns")
            .select("*")
            .eq("task_type", task_type)
            .eq("approach", approach)
            .limit(1)
            .execute()
        )

        if existing.data:
            # 업데이트
            pattern = existing.data[0]
            update_data = {
                "total_uses": pattern["total_uses"] + 1,
                "last_used": "now()",
            }
            if success:
                update_data["success_count"] = pattern["success_count"] + 1
            else:
                update_data["failure_count"] = pattern["failure_count"] + 1

            response = (
                self.client.table("procedural_patterns")
                .update(update_data)
                .eq("id", pattern["id"])
                .execute()
            )
        else:
            # 새로 생성
            data = {
                "task_type": task_type,
                "approach": approach,
                "success_count": 1 if success else 0,
                "failure_count": 0 if success else 1,
                "total_uses": 1,
            }
            response = self.client.table("procedural_patterns").insert(data).execute()

        return response.data[0] if response.data else {}

    def get_best_patterns(
        self,
        task_type: str,
        min_uses: int = 3,
        limit: int = 5,
    ) -> list[dict]:
        """최고 성공률 패턴 조회"""
        response = (
            self.client.table("procedural_patterns")
            .select("*")
            .eq("task_type", task_type)
            .gte("total_uses", min_uses)
            .order("success_rate", desc=True)
            .limit(limit)
            .execute()
        )
        return response.data or []

    def record_learning_event(
        self,
        pattern_id: str,
        experience_id: str,
        outcome: str,
        reward_signal: float = 0.0,
        prediction_error: float = 0.0,
    ) -> None:
        """학습 이벤트 기록"""
        self.client.table("pattern_learning_events").insert({
            "pattern_id": pattern_id,
            "experience_id": experience_id,
            "outcome": outcome,
            "reward_signal": reward_signal,
            "prediction_error": prediction_error,
        }).execute()

    # ==================== emotion_logs ====================

    def log_emotion(
        self,
        curiosity: float,
        joy: float,
        fear: float,
        surprise: float,
        frustration: float,
        boredom: float,
        dominant_emotion: str,
        trigger_task: str = None,
        trigger_type: str = None,
        experience_id: str = None,
        development_stage: int = 0,
    ) -> dict:
        """감정 로그 저장"""
        data = {
            "curiosity": curiosity,
            "joy": joy,
            "fear": fear,
            "surprise": surprise,
            "frustration": frustration,
            "boredom": boredom,
            "dominant_emotion": dominant_emotion,
            "development_stage": development_stage,
        }

        if trigger_task:
            data["trigger_task"] = trigger_task
        if trigger_type:
            data["trigger_type"] = trigger_type
        if experience_id:
            data["experience_id"] = experience_id

        response = self.client.table("emotion_logs").insert(data).execute()
        return response.data[0] if response.data else {}

    def boost_memory_by_emotion(
        self,
        experience_id: str,
        emotion_intensity: float,
    ) -> None:
        """감정 강도로 기억 강화"""
        self.client.rpc(
            "boost_memory_by_emotion",
            {
                "p_experience_id": experience_id,
                "p_emotion_intensity": emotion_intensity,
            }
        ).execute()

    # ==================== Utility ====================

    def decay_connections(self, decay_rate: float = 0.01) -> None:
        """모든 연결 강도 감쇠 (시간 기반 망각)"""
        self.client.rpc("decay_all_connections", {"p_decay_rate": decay_rate}).execute()

    def get_stats(self) -> dict:
        """전체 DB 통계"""
        experiences = self.client.table("experiences").select("id", count="exact").execute()
        concepts = self.client.table("semantic_concepts").select("id", count="exact").execute()
        patterns = self.client.table("procedural_patterns").select("id", count="exact").execute()

        return {
            "experiences_count": experiences.count or 0,
            "concepts_count": concepts.count or 0,
            "patterns_count": patterns.count or 0,
        }

    # ==================== World Model: Predictions ====================

    def insert_prediction(
        self,
        scenario: str,
        prediction: str,
        confidence: float = 0.5,
        reasoning: str = None,
        based_on_concepts: list[str] = None,
        based_on_experiences: list[str] = None,
        prediction_type: str = "outcome",
        domain: str = None,
        development_stage: int = 0,
    ) -> dict:
        """예측 저장"""
        data = {
            "scenario": scenario,
            "prediction": prediction,
            "confidence": confidence,
            "prediction_type": prediction_type,
            "development_stage": development_stage,
        }

        if reasoning:
            data["reasoning"] = reasoning
        # based_on_concepts와 based_on_experiences는 UUID 배열이어야 함
        # UUID 형식 검증 (36자리 + 하이픈 포함)
        if based_on_concepts:
            valid_uuids = [c for c in based_on_concepts if len(c) == 36 and c.count('-') == 4]
            if valid_uuids:
                data["based_on_concepts"] = valid_uuids
        if based_on_experiences:
            valid_uuids = [e for e in based_on_experiences if len(e) == 36 and e.count('-') == 4]
            if valid_uuids:
                data["based_on_experiences"] = valid_uuids
        if domain:
            data["domain"] = domain

        response = self.client.table("predictions").insert(data).execute()
        return response.data[0] if response.data else {}

    def verify_prediction(
        self,
        prediction_id: str,
        actual_outcome: str,
        was_correct: bool,
        prediction_error: float = 0.0,
        insight_gained: str = None,
    ) -> dict:
        """예측 검증 결과 업데이트"""
        from datetime import datetime

        data = {
            "actual_outcome": actual_outcome,
            "was_correct": was_correct,
            "prediction_error": prediction_error,
            "verified_at": datetime.utcnow().isoformat(),
        }

        if insight_gained:
            data["insight_gained"] = insight_gained

        response = (
            self.client.table("predictions")
            .update(data)
            .eq("id", prediction_id)
            .execute()
        )
        return response.data[0] if response.data else {}

    def get_recent_predictions(self, limit: int = 10) -> list[dict]:
        """최근 예측 조회"""
        response = (
            self.client.table("predictions")
            .select("*")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return response.data or []

    def get_unverified_predictions(self, limit: int = 10) -> list[dict]:
        """미검증 예측 조회"""
        response = (
            self.client.table("predictions")
            .select("*")
            .is_("verified_at", "null")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return response.data or []

    # ==================== World Model: Simulations ====================

    def insert_simulation(
        self,
        initial_state: dict,
        target_goal: str = None,
        simulation_type: str = "planning",
        steps: list[dict] = None,
        predicted_outcome: dict = None,
        success_probability: float = 0.5,
        complexity_level: int = 1,
        triggered_by_experience: str = None,
        development_stage: int = 0,
    ) -> dict:
        """시뮬레이션 저장"""
        data = {
            "initial_state": initial_state,
            "simulation_type": simulation_type,
            "success_probability": success_probability,
            "complexity_level": complexity_level,
            "development_stage": development_stage,
        }

        if target_goal:
            data["target_goal"] = target_goal
        if steps:
            data["steps"] = steps
        if predicted_outcome:
            data["predicted_outcome"] = predicted_outcome
        if triggered_by_experience:
            data["triggered_by_experience"] = triggered_by_experience

        response = self.client.table("simulations").insert(data).execute()
        return response.data[0] if response.data else {}

    def complete_simulation(
        self,
        simulation_id: str,
        actual_outcome: dict = None,
        was_validated: bool = False,
        accuracy_score: float = None,
    ) -> dict:
        """시뮬레이션 완료"""
        from datetime import datetime

        data = {
            "completed_at": datetime.utcnow().isoformat(),
        }

        if actual_outcome:
            data["actual_outcome"] = actual_outcome
        if was_validated is not None:
            data["was_validated"] = was_validated
        if accuracy_score is not None:
            data["accuracy_score"] = accuracy_score

        response = (
            self.client.table("simulations")
            .update(data)
            .eq("id", simulation_id)
            .execute()
        )
        return response.data[0] if response.data else {}

    def get_recent_simulations(self, limit: int = 10) -> list[dict]:
        """최근 시뮬레이션 조회"""
        response = (
            self.client.table("simulations")
            .select("*")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return response.data or []

    # ==================== World Model: Causal Models ====================

    def upsert_causal_model(
        self,
        cause_concept_id: str,
        effect_concept_id: str,
        relationship_type: str = "causes",
        causal_strength: float = 0.5,
        confidence: float = 0.5,
        domain: str = None,
        discovered_at_stage: int = 0,
    ) -> dict:
        """인과 모델 저장/업데이트"""
        # 기존 관계 확인
        existing = (
            self.client.table("causal_models")
            .select("*")
            .eq("cause_concept_id", cause_concept_id)
            .eq("effect_concept_id", effect_concept_id)
            .limit(1)
            .execute()
        )

        if existing.data:
            # 업데이트 - 강도 및 신뢰도 증가
            model = existing.data[0]
            new_strength = min(1.0, model["causal_strength"] + 0.05)
            new_confidence = min(1.0, model["confidence"] + 0.02)
            new_evidence = (model.get("evidence_count") or 0) + 1

            response = (
                self.client.table("causal_models")
                .update({
                    "causal_strength": new_strength,
                    "confidence": new_confidence,
                    "evidence_count": new_evidence,
                    "validation_count": (model.get("validation_count") or 0) + 1,
                })
                .eq("id", model["id"])
                .execute()
            )
        else:
            # 새로 생성
            data = {
                "cause_concept_id": cause_concept_id,
                "effect_concept_id": effect_concept_id,
                "relationship_type": relationship_type,
                "causal_strength": causal_strength,
                "confidence": confidence,
                "evidence_count": 1,
                "discovered_at_stage": discovered_at_stage,
            }
            if domain:
                data["domain"] = domain

            response = self.client.table("causal_models").insert(data).execute()

        return response.data[0] if response.data else {}

    def get_causal_models(self, min_confidence: float = 0.3, limit: int = 50) -> list[dict]:
        """인과 모델 조회"""
        response = (
            self.client.table("causal_models")
            .select("*")
            .gte("confidence", min_confidence)
            .order("causal_strength", desc=True)
            .limit(limit)
            .execute()
        )
        return response.data or []

    # ==================== World Model: Imagination Sessions ====================

    def start_imagination_session(
        self,
        topic: str,
        trigger: str = None,
        imagination_type: str = "exploration",
        curiosity_level: float = 0.5,
        emotional_state: dict = None,
        development_stage: int = 0,
    ) -> dict:
        """상상 세션 시작"""
        from datetime import datetime

        data = {
            "topic": topic,
            "imagination_type": imagination_type,
            "curiosity_level": curiosity_level,
            "development_stage": development_stage,
            "started_at": datetime.utcnow().isoformat(),
            "thoughts": [],
            "visualizations": [],
            "insights": [],
        }

        if trigger:
            data["trigger"] = trigger
        if emotional_state:
            data["emotional_state"] = emotional_state

        response = self.client.table("imagination_sessions").insert(data).execute()
        return response.data[0] if response.data else {}

    def add_imagination_thought(
        self,
        session_id: str,
        thought: dict,
    ) -> dict:
        """상상 세션에 생각 추가"""
        # 현재 세션 가져오기
        session = (
            self.client.table("imagination_sessions")
            .select("thoughts")
            .eq("id", session_id)
            .single()
            .execute()
        )

        if session.data:
            thoughts = session.data.get("thoughts") or []
            thoughts.append(thought)

            response = (
                self.client.table("imagination_sessions")
                .update({"thoughts": thoughts})
                .eq("id", session_id)
                .execute()
            )
            return response.data[0] if response.data else {}

        return {}

    def end_imagination_session(
        self,
        session_id: str,
        insights: list[str] = None,
        predictions_made: list[str] = None,
        simulations_run: list[str] = None,
        duration_ms: int = None,
    ) -> dict:
        """상상 세션 종료"""
        from datetime import datetime

        data = {
            "ended_at": datetime.utcnow().isoformat(),
        }

        if insights:
            data["insights"] = insights
        if predictions_made:
            data["predictions_made"] = predictions_made
        if simulations_run:
            data["simulations_run"] = simulations_run
        if duration_ms is not None:
            data["duration_ms"] = duration_ms

        response = (
            self.client.table("imagination_sessions")
            .update(data)
            .eq("id", session_id)
            .execute()
        )
        return response.data[0] if response.data else {}

    def get_active_imagination_session(self) -> Optional[dict]:
        """활성 상상 세션 조회"""
        response = (
            self.client.table("imagination_sessions")
            .select("*")
            .is_("ended_at", "null")
            .order("started_at", desc=True)
            .limit(1)
            .execute()
        )
        return response.data[0] if response.data else None

    def get_recent_imagination_sessions(self, limit: int = 10) -> list[dict]:
        """최근 상상 세션 조회"""
        response = (
            self.client.table("imagination_sessions")
            .select("*")
            .order("started_at", desc=True)
            .limit(limit)
            .execute()
        )
        return response.data or []

    # ==================== World Model: Experience-Concept Links ====================

    def get_all_concepts(self) -> list[dict]:
        """모든 개념 조회"""
        response = (
            self.client.table("semantic_concepts")
            .select("*")
            .order("strength", desc=True)
            .execute()
        )
        return response.data or []

    def get_experience_concept_links(self, limit: int = 100) -> list[dict]:
        """경험-개념 연결 조회 (시냅스 시각화용)"""
        response = (
            self.client.table("experience_concepts")
            .select("*")
            .order("relevance", desc=True)
            .limit(limit)
            .execute()
        )
        return response.data or []


# Singleton instance
_db_instance: Optional[BrainDatabase] = None


def get_brain_db() -> BrainDatabase:
    """BrainDatabase 싱글톤"""
    global _db_instance
    if _db_instance is None:
        _db_instance = BrainDatabase()
    return _db_instance
