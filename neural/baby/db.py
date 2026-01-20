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


# Singleton instance
_db_instance: Optional[BrainDatabase] = None


def get_brain_db() -> BrainDatabase:
    """BrainDatabase 싱글톤"""
    global _db_instance
    if _db_instance is None:
        _db_instance = BrainDatabase()
    return _db_instance
