"""
MemorySystem - 기억 시스템

세 가지 기억 유형:
1. Episodic (에피소드 기억) - 해마: 구체적 경험
2. Semantic (의미 기억) - 피질: 일반 지식
3. Procedural (절차 기억) - 소뇌: 기술/절차

저장소:
- Primary: Supabase (pgvector)
- Fallback: 로컬 JSON 파일 (.baby_memory/)

기억 통합:
- 중요한 경험 → 장기 기억
- 반복 경험 → 절차화
- 패턴 추출 → 의미 지식
"""

from dataclasses import dataclass, field
from typing import Optional, Any, List
from datetime import datetime
from enum import Enum
import json
import hashlib
import os


class MemoryType(Enum):
    """기억 유형"""
    EPISODIC = "episodic"       # 경험 기억
    SEMANTIC = "semantic"       # 지식 기억
    PROCEDURAL = "procedural"   # 기술 기억


class StorageBackend(Enum):
    """저장소 백엔드"""
    SUPABASE = "supabase"   # Supabase pgvector
    LOCAL = "local"         # 로컬 JSON


@dataclass
class Experience:
    """경험 (에피소드 기억의 단위)"""
    # 핵심 정보
    request: str                # 입력 요청
    action: str                 # 수행한 행동
    outcome: str                # 결과
    success: bool               # 성공 여부

    # 컨텍스트
    task_type: str = "default"
    context: dict = field(default_factory=dict)

    # 감정 상태
    emotional_weight: float = 0.5   # 감정 가중치 (중요도)
    curiosity_signal: float = 0.0   # 호기심 신호

    # 메타데이터
    timestamp: datetime = field(default_factory=datetime.now)
    id: str = field(default_factory=lambda: "")

    # Supabase 연동용
    db_id: str = None           # Supabase UUID
    embedding: list = None      # 벡터 임베딩

    def __post_init__(self):
        if not self.id:
            # 고유 ID 생성
            content = f"{self.request}:{self.action}:{self.timestamp.isoformat()}"
            self.id = hashlib.md5(content.encode()).hexdigest()[:12]

    @property
    def importance(self) -> float:
        """경험의 중요도"""
        base = self.emotional_weight

        # 성공/실패 모두 중요 (극단값이 중요)
        if self.success:
            base += 0.2
        else:
            base += 0.3  # 실패는 더 기억에 남음

        # 새로운 것은 더 중요
        base += self.curiosity_signal * 0.2

        return min(1.0, base)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "request": self.request,
            "action": self.action,
            "outcome": self.outcome,
            "success": self.success,
            "task_type": self.task_type,
            "emotional_weight": self.emotional_weight,
            "importance": self.importance,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Experience":
        return cls(
            id=data.get("id", ""),
            request=data["request"],
            action=data["action"],
            outcome=data["outcome"],
            success=data["success"],
            task_type=data.get("task_type", "default"),
            emotional_weight=data.get("emotional_weight", 0.5),
            curiosity_signal=data.get("curiosity_signal", 0.0),
            timestamp=datetime.fromisoformat(data["timestamp"]),
        )

    @classmethod
    def from_supabase(cls, data: dict) -> "Experience":
        """Supabase experiences 테이블에서 변환"""
        return cls(
            id=data.get("id", "")[:12],
            db_id=data.get("id"),
            request=data.get("task", ""),
            action=data.get("output", ""),
            outcome="success" if data.get("success") else "failure",
            success=data.get("success", False),
            task_type=data.get("task_type", "default"),
            emotional_weight=data.get("emotional_salience", 0.5),
            curiosity_signal=0.0,
            timestamp=datetime.fromisoformat(data["created_at"].replace("Z", "+00:00")) if data.get("created_at") else datetime.now(),
        )


class EpisodicMemory:
    """
    에피소드 기억 (해마)

    구체적인 경험 저장
    - Supabase experiences 테이블 연동
    - 벡터 유사도 검색 지원
    - 로컬 폴백
    """

    def __init__(
        self,
        max_short_term: int = 50,
        max_long_term: int = 500,
        use_supabase: bool = True,
    ):
        self._short_term: list[Experience] = []   # 단기 기억
        self._long_term: list[Experience] = []    # 장기 기억
        self._max_short_term = max_short_term
        self._max_long_term = max_long_term
        self._use_supabase = use_supabase

        # 중요도 임계값
        self._importance_threshold = 0.6

        # Supabase 연동 (lazy init)
        self._db = None
        self._embedder = None

    def _get_db(self):
        """Supabase DB 클라이언트 (lazy)"""
        if self._db is None and self._use_supabase:
            try:
                from .db import get_brain_db
                self._db = get_brain_db()
            except Exception as e:
                print(f"[EpisodicMemory] Supabase 연결 실패, 로컬 모드: {e}")
                self._use_supabase = False
        return self._db

    def _get_embedding(self, text: str) -> Optional[list]:
        """임베딩 생성 (lazy)"""
        if self._embedder is None:
            try:
                from .embeddings import safe_create_embedding
                self._embedder = safe_create_embedding
            except Exception as e:
                print(f"[EpisodicMemory] 임베딩 모듈 로드 실패: {e}")
                return None

        return self._embedder(text)

    def store(self, experience: Experience, emotion_snapshot: dict = None) -> str:
        """
        경험 저장

        Returns:
            저장된 경험의 DB ID (Supabase) 또는 로컬 ID
        """
        # 단기 기억에 추가
        self._short_term.append(experience)

        # Supabase에 저장
        db = self._get_db()
        if db:
            try:
                # 임베딩 생성
                embed_text = f"{experience.request} {experience.action[:500]}"
                embedding = self._get_embedding(embed_text)

                # DB 저장
                result = db.insert_experience(
                    task=experience.request,
                    task_type=experience.task_type,
                    output=experience.action,
                    success=experience.success,
                    emotional_salience=experience.emotional_weight,
                    dominant_emotion=emotion_snapshot.get("dominant") if emotion_snapshot else None,
                    embedding=embedding,
                    emotion_snapshot=emotion_snapshot,
                    tags=[experience.task_type],
                )

                if result:
                    experience.db_id = result.get("id")
                    return experience.db_id

            except Exception as e:
                print(f"[EpisodicMemory] Supabase 저장 실패: {e}")

        # 단기 기억 초과 시 통합
        if len(self._short_term) > self._max_short_term:
            self._consolidate()

        return experience.id

    def _consolidate(self) -> None:
        """기억 통합 (단기 → 장기)"""
        # 중요한 경험만 장기 기억으로
        important = [
            exp for exp in self._short_term
            if exp.importance >= self._importance_threshold
        ]

        self._long_term.extend(important)

        # 장기 기억 초과 시 오래된 것 제거
        if len(self._long_term) > self._max_long_term:
            # 중요도 순으로 정렬 후 상위만 유지
            self._long_term.sort(key=lambda x: x.importance, reverse=True)
            self._long_term = self._long_term[:self._max_long_term]

        # 단기 기억 비우기
        self._short_term = []

    def recall_recent(self, n: int = 5) -> list[Experience]:
        """최근 경험 회상"""
        # Supabase에서 조회 시도
        db = self._get_db()
        if db:
            try:
                results = db.get_recent_experiences(limit=n)
                if results:
                    return [Experience.from_supabase(r) for r in results]
            except Exception as e:
                print(f"[EpisodicMemory] Supabase 조회 실패: {e}")

        # 로컬 폴백
        all_memories = self._short_term + self._long_term
        all_memories.sort(key=lambda x: x.timestamp, reverse=True)
        return all_memories[:n]

    def recall_similar(self, request: str, n: int = 3) -> list[Experience]:
        """유사한 경험 회상"""
        # Supabase 벡터 검색 시도
        db = self._get_db()
        if db:
            try:
                embedding = self._get_embedding(request)
                if embedding:
                    results = db.search_similar_experiences(
                        embedding=embedding,
                        threshold=0.5,
                        limit=n,
                    )
                    if results:
                        # 검색 결과에서 Experience로 변환
                        experiences = []
                        for r in results:
                            exp = Experience(
                                id=str(r.get("id", ""))[:12],
                                db_id=str(r.get("id", "")),
                                request=r.get("task", ""),
                                action=r.get("output", ""),
                                outcome="success" if r.get("success") else "failure",
                                success=r.get("success", False),
                                task_type=r.get("task_type", "default"),
                                emotional_weight=r.get("emotional_salience", 0.5),
                            )
                            experiences.append(exp)
                        return experiences

            except Exception as e:
                print(f"[EpisodicMemory] 벡터 검색 실패: {e}")

        # 로컬 키워드 매칭 폴백
        keywords = set(request.lower().split())
        all_memories = self._short_term + self._long_term

        scored = []
        for exp in all_memories:
            exp_keywords = set(exp.request.lower().split())
            overlap = len(keywords & exp_keywords)
            if overlap > 0:
                scored.append((overlap, exp))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [exp for _, exp in scored[:n]]

    def recall_successful(self, task_type: str = None, n: int = 5) -> list[Experience]:
        """성공한 경험 회상"""
        # Supabase에서 조회 시도
        db = self._get_db()
        if db:
            try:
                results = db.get_successful_experiences(task_type=task_type, limit=n)
                if results:
                    return [Experience.from_supabase(r) for r in results]
            except Exception as e:
                print(f"[EpisodicMemory] Supabase 조회 실패: {e}")

        # 로컬 폴백
        all_memories = self._short_term + self._long_term
        successful = [
            exp for exp in all_memories
            if exp.success and (task_type is None or exp.task_type == task_type)
        ]
        successful.sort(key=lambda x: x.importance, reverse=True)
        return successful[:n]

    def reinforce(self, experience_id: str) -> None:
        """기억 강화"""
        db = self._get_db()
        if db and experience_id:
            try:
                db.reinforce_memory(experience_id)
            except Exception as e:
                print(f"[EpisodicMemory] 기억 강화 실패: {e}")

    def get_stats(self) -> dict:
        db = self._get_db()
        supabase_count = 0
        if db:
            try:
                stats = db.get_stats()
                supabase_count = stats.get("experiences_count", 0)
            except:
                pass

        return {
            "short_term_count": len(self._short_term),
            "long_term_count": len(self._long_term),
            "total_local": len(self._short_term) + len(self._long_term),
            "total_supabase": supabase_count,
            "success_rate": self._calculate_success_rate(),
            "backend": "supabase" if self._use_supabase and self._db else "local",
        }

    def _calculate_success_rate(self) -> float:
        all_memories = self._short_term + self._long_term
        if not all_memories:
            return 0.0
        successes = sum(1 for exp in all_memories if exp.success)
        return successes / len(all_memories)


class SemanticMemory:
    """
    의미 기억 (피질)

    일반 지식 저장
    - Supabase semantic_concepts + experience_concepts 연동
    - 개념 간 관계 그래프 (concept_relations)
    """

    def __init__(self, use_supabase: bool = True):
        self._knowledge: dict[str, Any] = {}
        self._patterns: dict[str, list[str]] = {}  # 패턴 저장
        self._rules: list[dict] = []               # 학습된 규칙
        self._use_supabase = use_supabase
        self._db = None
        self._embedder = None

    def _get_db(self):
        if self._db is None and self._use_supabase:
            try:
                from .db import get_brain_db
                self._db = get_brain_db()
            except Exception as e:
                print(f"[SemanticMemory] Supabase 연결 실패: {e}")
                self._use_supabase = False
        return self._db

    def _get_embedding(self, text: str) -> Optional[list]:
        if self._embedder is None:
            try:
                from .embeddings import safe_create_embedding
                self._embedder = safe_create_embedding
            except:
                return None
        return self._embedder(text)

    def add_concept(
        self,
        name: str,
        category: str = None,
        description: str = None,
        development_stage: int = 0,
    ) -> Optional[str]:
        """개념 추가"""
        # 로컬 저장
        self._knowledge[name] = {
            "category": category,
            "description": description,
            "stage": development_stage,
        }

        # Supabase 저장
        db = self._get_db()
        if db:
            try:
                # 임베딩 생성
                embed_text = f"{name} {category or ''} {description or ''}"
                embedding = self._get_embedding(embed_text)

                result = db.insert_concept(
                    name=name,
                    category=category,
                    description=description,
                    embedding=embedding,
                    acquired_at_stage=development_stage,
                )
                return result.get("id") if result else None
            except Exception as e:
                # 중복 키 등 에러 무시
                if "duplicate" not in str(e).lower():
                    print(f"[SemanticMemory] 개념 저장 실패: {e}")

        return None

    def get_concept(self, name: str) -> Optional[dict]:
        """개념 조회"""
        # Supabase에서 조회 시도
        db = self._get_db()
        if db:
            try:
                result = db.get_concept_by_name(name)
                if result:
                    return result
            except:
                pass

        # 로컬 폴백
        return self._knowledge.get(name)

    def link_to_experience(
        self,
        concept_name: str,
        experience_id: str,
        confidence: float = 0.5,
    ) -> None:
        """개념과 경험 연결 (Hebb's Law)"""
        db = self._get_db()
        if db and experience_id:
            try:
                concept = db.get_concept_by_name(concept_name)
                if concept:
                    db.link_experience_concept(
                        experience_id=experience_id,
                        concept_id=concept["id"],
                        confidence=confidence,
                    )
            except Exception as e:
                print(f"[SemanticMemory] 연결 실패: {e}")

    def store_knowledge(self, key: str, value: Any) -> None:
        """지식 저장"""
        self._knowledge[key] = value

    def retrieve_knowledge(self, key: str) -> Optional[Any]:
        """지식 검색"""
        return self._knowledge.get(key)

    def store_pattern(self, task_type: str, pattern: str) -> None:
        """패턴 저장"""
        if task_type not in self._patterns:
            self._patterns[task_type] = []

        if pattern not in self._patterns[task_type]:
            self._patterns[task_type].append(pattern)

            # 최대 패턴 수 제한
            if len(self._patterns[task_type]) > 20:
                self._patterns[task_type].pop(0)

    def get_patterns(self, task_type: str) -> list[str]:
        """패턴 검색"""
        return self._patterns.get(task_type, [])

    def learn_rule(self, condition: str, action: str, confidence: float) -> None:
        """규칙 학습"""
        rule = {
            "condition": condition,
            "action": action,
            "confidence": confidence,
            "uses": 0,
        }

        # 중복 확인
        for existing in self._rules:
            if existing["condition"] == condition:
                # 기존 규칙 업데이트
                existing["confidence"] = (existing["confidence"] + confidence) / 2
                return

        self._rules.append(rule)

    def apply_rule(self, condition: str) -> Optional[str]:
        """규칙 적용"""
        for rule in self._rules:
            if condition in rule["condition"] or rule["condition"] in condition:
                rule["uses"] += 1
                return rule["action"]
        return None

    def extract_from_experiences(self, experiences: list[Experience]) -> None:
        """경험에서 지식 추출"""
        # 태스크 유형별 성공 패턴 추출
        for exp in experiences:
            if exp.success:
                self.store_pattern(exp.task_type, exp.action[:100])

                # 조건-행동 규칙 학습
                self.learn_rule(
                    condition=exp.request[:50],
                    action=exp.action[:100],
                    confidence=exp.importance,
                )

    def get_stats(self) -> dict:
        db = self._get_db()
        supabase_count = 0
        if db:
            try:
                stats = db.get_stats()
                supabase_count = stats.get("concepts_count", 0)
            except:
                pass

        return {
            "knowledge_count": len(self._knowledge),
            "pattern_types": list(self._patterns.keys()),
            "rule_count": len(self._rules),
            "supabase_concepts": supabase_count,
            "backend": "supabase" if self._use_supabase and self._db else "local",
        }


class ProceduralMemory:
    """
    절차 기억 (소뇌)

    기술과 절차 저장
    - Supabase procedural_patterns + pattern_learning_events 연동
    - 강화 학습 기반 패턴 최적화
    """

    def __init__(self, use_supabase: bool = True):
        self._procedures: dict[str, dict] = {}  # 절차 저장
        self._habits: dict[str, int] = {}       # 습관 (빈도)
        self._use_supabase = use_supabase
        self._db = None

    def _get_db(self):
        if self._db is None and self._use_supabase:
            try:
                from .db import get_brain_db
                self._db = get_brain_db()
            except Exception as e:
                print(f"[ProceduralMemory] Supabase 연결 실패: {e}")
                self._use_supabase = False
        return self._db

    def record_step(
        self,
        task_type: str,
        approach: str,
        success: bool,
        experience_id: str = None,
        reward_signal: float = 0.0,
        prediction_error: float = 0.0,
    ) -> Optional[str]:
        """절차 단계 기록"""
        # Supabase 저장
        db = self._get_db()
        pattern_id = None
        if db:
            try:
                result = db.upsert_pattern(
                    task_type=task_type,
                    approach=approach,
                    success=success,
                )
                pattern_id = result.get("id") if result else None

                # 학습 이벤트 기록
                if pattern_id and experience_id:
                    db.record_learning_event(
                        pattern_id=pattern_id,
                        experience_id=experience_id,
                        outcome="success" if success else "failure",
                        reward_signal=reward_signal,
                        prediction_error=prediction_error,
                    )
            except Exception as e:
                print(f"[ProceduralMemory] 패턴 저장 실패: {e}")

        # 로컬 저장
        key = f"{task_type}:{approach}"
        if key in self._procedures:
            old = self._procedures[key]
            old["uses"] += 1
            if success:
                old["success_count"] = old.get("success_count", 0) + 1
            else:
                old["failure_count"] = old.get("failure_count", 0) + 1
        else:
            self._procedures[key] = {
                "task_type": task_type,
                "approach": approach,
                "success_count": 1 if success else 0,
                "failure_count": 0 if success else 1,
                "uses": 1,
            }

        return pattern_id

    def get_best_approach(self, task_type: str, min_uses: int = 2) -> Optional[str]:
        """최적 접근법 조회"""
        # Supabase에서 조회 시도
        db = self._get_db()
        if db:
            try:
                results = db.get_best_patterns(
                    task_type=task_type,
                    min_uses=min_uses,
                    limit=1,
                )
                if results:
                    return results[0].get("approach")
            except:
                pass

        # 로컬 폴백
        best = None
        best_rate = 0.0
        for key, proc in self._procedures.items():
            if proc["task_type"] == task_type and proc["uses"] >= min_uses:
                rate = proc["success_count"] / proc["uses"]
                if rate > best_rate:
                    best_rate = rate
                    best = proc["approach"]

        return best

    def learn_procedure(
        self,
        name: str,
        steps: list[str],
        success_rate: float = 0.0,
    ) -> None:
        """절차 학습 (레거시 호환) - 새 포맷으로 저장"""
        # 새 포맷: task_type 필드 필수
        key = f"{name}_learned"
        if key in self._procedures:
            # 기존 절차 개선
            old = self._procedures[key]
            old["uses"] = old.get("uses", 0) + 1
            if success_rate > 0:
                old["success_count"] = old.get("success_count", 0) + 1
        else:
            self._procedures[key] = {
                "task_type": name,  # name을 task_type으로 사용
                "approach": steps[0] if steps else "",
                "success_count": 1 if success_rate > 0 else 0,
                "failure_count": 0 if success_rate > 0 else 1,
                "uses": 1,
            }

    def get_procedure(self, name: str) -> Optional[dict]:
        """절차 검색"""
        return self._procedures.get(name)

    def record_habit(self, action: str) -> None:
        """습관 기록"""
        self._habits[action] = self._habits.get(action, 0) + 1

    def get_habit_strength(self, action: str) -> float:
        """습관 강도 (0.0 ~ 1.0)"""
        count = self._habits.get(action, 0)
        # 10번 이상이면 강한 습관
        return min(1.0, count / 10)

    def get_common_habits(self, n: int = 5) -> list[tuple[str, int]]:
        """자주 하는 행동"""
        sorted_habits = sorted(
            self._habits.items(),
            key=lambda x: x[1],
            reverse=True
        )
        return sorted_habits[:n]

    def get_stats(self) -> dict:
        db = self._get_db()
        supabase_count = 0
        if db:
            try:
                stats = db.get_stats()
                supabase_count = stats.get("patterns_count", 0)
            except:
                pass

        return {
            "procedure_count": len(self._procedures),
            "habit_count": len(self._habits),
            "strongest_habits": self.get_common_habits(3),
            "supabase_patterns": supabase_count,
            "backend": "supabase" if self._use_supabase and self._db else "local",
        }


class MemorySystem:
    """
    통합 기억 시스템

    세 가지 기억 유형을 통합 관리
    - Supabase pgvector 연동
    - 로컬 JSON 폴백
    - 에피소드 → 의미 변환
    - 반복 → 절차화
    - 감정 기반 필터링
    """

    def __init__(self, storage_path: str = None, use_supabase: bool = True):
        self._use_supabase = use_supabase
        self.episodic = EpisodicMemory(use_supabase=use_supabase)
        self.semantic = SemanticMemory(use_supabase=use_supabase)
        self.procedural = ProceduralMemory(use_supabase=use_supabase)

        self._storage_path = storage_path

    def record_experience(
        self,
        request: str,
        action: str,
        outcome: str,
        success: bool,
        emotional_weight: float = 0.5,
        curiosity_signal: float = 0.0,
        task_type: str = "default",
        emotion_snapshot: dict = None,
    ) -> Experience:
        """경험 기록"""
        exp = Experience(
            request=request,
            action=action,
            outcome=outcome,
            success=success,
            task_type=task_type,
            emotional_weight=emotional_weight,
            curiosity_signal=curiosity_signal,
        )

        # 에피소드 기억에 저장
        db_id = self.episodic.store(exp, emotion_snapshot=emotion_snapshot)
        exp.db_id = db_id

        # 절차 기억에 기록
        pattern_id = self.procedural.record_step(
            task_type=task_type,
            approach=action[:100],
            success=success,
            experience_id=db_id if db_id and len(db_id) > 20 else None,
            reward_signal=1.0 if success else -0.5,
        )

        # 습관 기록
        self.procedural.record_habit(action[:50])

        # 개념 추출 및 연결 (간단한 키워드 기반)
        if success:
            keywords = set(request.lower().split())
            for kw in keywords:
                if len(kw) > 2:  # 짧은 단어 제외
                    concept_id = self.semantic.add_concept(
                        name=kw,
                        category=task_type,
                    )
                    if concept_id and db_id:
                        self.semantic.link_to_experience(
                            concept_name=kw,
                            experience_id=db_id,
                            confidence=exp.importance,
                        )

        return exp

    def consolidate(self) -> None:
        """기억 통합 (주기적 호출)"""
        # 에피소드 → 의미 기억
        recent = self.episodic.recall_recent(20)
        self.semantic.extract_from_experiences(recent)

        # 성공한 경험 → 절차화
        successful = self.episodic.recall_successful(n=10)
        for exp in successful:
            self.procedural.learn_procedure(
                name=exp.task_type,
                steps=[exp.action],
                success_rate=1.0 if exp.success else 0.0,
            )

    def recall_for_task(self, request: str, task_type: str = None) -> dict:
        """태스크를 위한 관련 기억 회상"""
        return {
            "similar_experiences": [
                exp.to_dict() for exp in self.episodic.recall_similar(request, 3)
            ],
            "successful_examples": [
                exp.to_dict() for exp in self.episodic.recall_successful(task_type, 3)
            ],
            "patterns": self.semantic.get_patterns(task_type or "default"),
            "procedure": self.procedural.get_procedure(task_type or "default"),
            "best_approach": self.procedural.get_best_approach(task_type or "default"),
        }

    def save(self) -> None:
        """기억 저장 (로컬 JSON)"""
        if not self._storage_path:
            return

        os.makedirs(self._storage_path, exist_ok=True)

        # 에피소드 기억 저장
        episodic_data = {
            "short_term": [exp.to_dict() for exp in self.episodic._short_term],
            "long_term": [exp.to_dict() for exp in self.episodic._long_term],
        }
        with open(os.path.join(self._storage_path, "episodic.json"), "w", encoding="utf-8") as f:
            json.dump(episodic_data, f, indent=2, ensure_ascii=False)

        # 의미 기억 저장
        semantic_data = {
            "knowledge": self.semantic._knowledge,
            "patterns": self.semantic._patterns,
            "rules": self.semantic._rules,
        }
        with open(os.path.join(self._storage_path, "semantic.json"), "w", encoding="utf-8") as f:
            json.dump(semantic_data, f, indent=2, ensure_ascii=False)

        # 절차 기억 저장
        procedural_data = {
            "procedures": self.procedural._procedures,
            "habits": self.procedural._habits,
        }
        with open(os.path.join(self._storage_path, "procedural.json"), "w", encoding="utf-8") as f:
            json.dump(procedural_data, f, indent=2, ensure_ascii=False)

    def load(self) -> bool:
        """기억 로드 (로컬 JSON)"""
        if not self._storage_path:
            return False

        try:
            # 에피소드 기억 로드
            episodic_path = os.path.join(self._storage_path, "episodic.json")
            if os.path.exists(episodic_path):
                with open(episodic_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.episodic._short_term = [
                    Experience.from_dict(d) for d in data.get("short_term", [])
                ]
                self.episodic._long_term = [
                    Experience.from_dict(d) for d in data.get("long_term", [])
                ]

            # 의미 기억 로드
            semantic_path = os.path.join(self._storage_path, "semantic.json")
            if os.path.exists(semantic_path):
                with open(semantic_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.semantic._knowledge = data.get("knowledge", {})
                self.semantic._patterns = data.get("patterns", {})
                self.semantic._rules = data.get("rules", [])

            # 절차 기억 로드
            procedural_path = os.path.join(self._storage_path, "procedural.json")
            if os.path.exists(procedural_path):
                with open(procedural_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.procedural._procedures = data.get("procedures", {})
                self.procedural._habits = data.get("habits", {})

            return True

        except Exception as e:
            print(f"Memory load failed: {e}")
            return False

    def get_stats(self) -> dict:
        return {
            "episodic": self.episodic.get_stats(),
            "semantic": self.semantic.get_stats(),
            "procedural": self.procedural.get_stats(),
            "use_supabase": self._use_supabase,
        }

    def __repr__(self) -> str:
        stats = self.get_stats()
        backend = "Supabase" if self._use_supabase else "Local"
        return (
            f"MemorySystem[{backend}]("
            f"episodes={stats['episodic']['total_local']}, "
            f"knowledge={stats['semantic']['knowledge_count']}, "
            f"procedures={stats['procedural']['procedure_count']})"
        )
