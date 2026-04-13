"""
Persistent Learning Substrate for Baby AI - Phase 10

세션 간 학습 상태 영속화

핵심 기능:
1. 세션 관리 - 학습 세션 시작/종료/복원
2. 상태 스냅샷 - 주기적 학습 상태 저장
3. 핵심 학습 추출 - 장기 기억으로 요약
4. 연속성 추적 - 세션 간 학습 연속성 유지
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import json


class SnapshotType(Enum):
    """스냅샷 유형"""
    CHECKPOINT = "checkpoint"  # 자동 체크포인트
    MILESTONE = "milestone"    # 마일스톤 달성
    END_SESSION = "end_session"  # 세션 종료


class LearningType(Enum):
    """학습 유형"""
    PROMPT_RULE = "prompt_rule"
    STRATEGY_INSIGHT = "strategy_insight"
    TEAM_PATTERN = "team_pattern"
    FAILURE_LESSON = "failure_lesson"
    SUCCESS_FACTOR = "success_factor"
    DOMAIN_KNOWLEDGE = "domain_knowledge"


class RestoreType(Enum):
    """복원 유형"""
    AUTO = "auto"
    MANUAL = "manual"
    MILESTONE = "milestone"


@dataclass
class LearningSession:
    """학습 세션"""
    id: str
    name: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    stage_start: int = 0
    stage_end: int = 0
    experiences_created: int = 0
    concepts_learned: int = 0
    evolutions_tried: int = 0
    evolutions_adopted: int = 0
    success_rate: float = 0.0
    key_learnings: List[str] = field(default_factory=list)


@dataclass
class LearningSnapshot:
    """학습 상태 스냅샷"""
    session_id: str
    snapshot_type: SnapshotType
    development_stage: int
    emotional_state: Dict[str, float]
    active_rules: List[Dict]
    strategy_weights: Dict[str, float]
    team_preferences: Dict[str, float]
    concept_strengths: Dict[str, float]
    pattern_effectiveness: Dict[str, float]


@dataclass
class CoreLearning:
    """핵심 학습 (장기 기억)"""
    learning_type: LearningType
    summary: str
    detailed_content: Dict
    confidence: float
    effectiveness: float
    is_active: bool = True


@dataclass
class RestorePoint:
    """복원 포인트"""
    session_id: str
    restore_type: RestoreType
    baby_state: Dict
    active_rules: List[Dict]
    strategy_weights: Dict[str, float]


class SessionManager:
    """
    세션 관리자

    학습 세션의 생명주기 관리
    """

    def __init__(self, supabase_client=None):
        self.db = supabase_client
        self._current_session_id: Optional[str] = None

    async def start_session(self, name: str = None) -> str:
        """세션 시작"""
        if not self.db:
            return ""

        # 현재 상태 조회
        baby_state = await self._get_current_baby_state()

        session_name = name or f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        result = await self.db.table('learning_sessions').insert({
            'session_name': session_name,
            'development_stage_start': baby_state.get('development_stage', 0),
            'session_metadata': {
                'initial_curiosity': baby_state.get('curiosity', 0.5),
                'initial_experience_count': baby_state.get('experience_count', 0)
            }
        }).execute()

        self._current_session_id = result.data[0]['id'] if result.data else None

        # 초기 스냅샷 생성
        await self._create_snapshot(SnapshotType.CHECKPOINT, "Session start")

        return self._current_session_id or ""

    async def _get_current_baby_state(self) -> Dict:
        """현재 baby_state 조회"""
        if not self.db:
            return {}

        result = await self.db.table('baby_state').select('*').limit(1).execute()
        return result.data[0] if result.data else {}

    async def end_session(self, key_learnings: List[str] = None):
        """세션 종료"""
        if not self.db or not self._current_session_id:
            return

        # 종료 스냅샷 생성
        await self._create_snapshot(SnapshotType.END_SESSION, "Session end")

        # 세션 통계 계산
        stats = await self._calculate_session_stats()

        # 현재 상태
        baby_state = await self._get_current_baby_state()

        # 세션 종료 업데이트
        await self.db.table('learning_sessions').update({
            'ended_at': datetime.now().isoformat(),
            'duration_ms': stats.get('duration_ms', 0),
            'development_stage_end': baby_state.get('development_stage', 0),
            'experiences_created': stats.get('experiences_created', 0),
            'concepts_learned': stats.get('concepts_learned', 0),
            'evolutions_tried': stats.get('evolutions_tried', 0),
            'evolutions_adopted': stats.get('evolutions_adopted', 0),
            'overall_success_rate': stats.get('success_rate', 0),
            'key_learnings': key_learnings or []
        }).eq('id', self._current_session_id).execute()

        # 복원 포인트 생성
        await self._create_restore_point(RestoreType.AUTO)

        # 핵심 학습 추출
        await self._extract_core_learnings()

        self._current_session_id = None

    async def _calculate_session_stats(self) -> Dict:
        """세션 통계 계산"""
        if not self.db or not self._current_session_id:
            return {}

        # 세션 정보
        session = await self.db.table('learning_sessions').select(
            'started_at'
        ).eq('id', self._current_session_id).single().execute()

        if not session.data:
            return {}

        started_at = datetime.fromisoformat(
            session.data['started_at'].replace('Z', '+00:00')
        )
        duration_ms = int((datetime.now(started_at.tzinfo) - started_at).total_seconds() * 1000)

        # 세션 동안 생성된 경험 수
        exp_result = await self.db.table('experiences').select(
            'id, success', count='exact'
        ).gte('created_at', session.data['started_at']).execute()

        experiences = exp_result.data or []
        successes = sum(1 for e in experiences if e.get('success'))

        # 생성된 개념 수
        concept_result = await self.db.table('semantic_concepts').select(
            'id', count='exact'
        ).gte('created_at', session.data['started_at']).execute()

        # 진화 통계
        evo_result = await self.db.table('prompt_evolution').select(
            'was_adopted', count='exact'
        ).gte('created_at', session.data['started_at']).execute()

        evolutions = evo_result.data or []
        adopted = sum(1 for e in evolutions if e.get('was_adopted'))

        return {
            'duration_ms': duration_ms,
            'experiences_created': len(experiences),
            'concepts_learned': concept_result.count or 0,
            'evolutions_tried': len(evolutions),
            'evolutions_adopted': adopted,
            'success_rate': successes / len(experiences) if experiences else 0
        }

    async def _create_snapshot(
        self,
        snapshot_type: SnapshotType,
        note: str = ""
    ):
        """스냅샷 생성"""
        if not self.db or not self._current_session_id:
            return

        # 현재 상태들 수집
        baby_state = await self._get_current_baby_state()

        # 활성 규칙
        rules_result = await self.db.table('learned_prompt_rules').select(
            'rule_name, rule_text, priority'
        ).eq('is_active', True).execute()

        # 전략 가중치
        strategy_result = await self.db.table('strategy_effectiveness').select(
            'strategy_name, effectiveness_score'
        ).execute()

        # 상위 개념 강도
        concepts_result = await self.db.table('semantic_concepts').select(
            'name, strength'
        ).order('strength', desc=True).limit(20).execute()

        await self.db.table('learning_snapshots').insert({
            'session_id': self._current_session_id,
            'snapshot_type': snapshot_type.value,
            'development_stage': baby_state.get('development_stage', 0),
            'emotional_state': {
                'curiosity': baby_state.get('curiosity', 0.5),
                'joy': baby_state.get('joy', 0.3),
                'frustration': baby_state.get('frustration', 0.1)
            },
            'active_prompt_rules': rules_result.data or [],
            'strategy_weights': {
                s['strategy_name']: s['effectiveness_score']
                for s in strategy_result.data or []
            },
            'concept_strengths': {
                c['name']: c['strength']
                for c in concepts_result.data or []
            }
        }).execute()

    async def _create_restore_point(self, restore_type: RestoreType):
        """복원 포인트 생성"""
        if not self.db or not self._current_session_id:
            return

        baby_state = await self._get_current_baby_state()

        rules_result = await self.db.table('learned_prompt_rules').select(
            '*'
        ).eq('is_active', True).execute()

        strategy_result = await self.db.table('strategy_effectiveness').select(
            'strategy_name, effectiveness_score'
        ).execute()

        await self.db.table('session_restore_points').insert({
            'session_id': self._current_session_id,
            'restore_type': restore_type.value,
            'baby_state': baby_state,
            'active_rules': rules_result.data or [],
            'strategy_weights': {
                s['strategy_name']: s['effectiveness_score']
                for s in strategy_result.data or []
            },
            'expires_at': (datetime.now() + timedelta(days=30)).isoformat()
        }).execute()

    async def _extract_core_learnings(self):
        """핵심 학습 추출"""
        if not self.db or not self._current_session_id:
            return

        # 1. 채택된 진화에서 학습 추출
        evolutions = await self.db.table('prompt_evolution').select(
            'id, failure_pattern, improvement_hypothesis, post_evolution_success_rate'
        ).eq('was_adopted', True).gte(
            'adopted_at', (datetime.now() - timedelta(days=1)).isoformat()
        ).execute()

        for evo in evolutions.data or []:
            await self.db.table('core_learnings').insert({
                'learning_type': 'prompt_rule',
                'summary': evo.get('improvement_hypothesis', ''),
                'detailed_content': {
                    'failure_pattern': evo.get('failure_pattern'),
                    'success_rate': evo.get('post_evolution_success_rate')
                },
                'source_session_ids': [self._current_session_id],
                'confidence': evo.get('post_evolution_success_rate', 0.5)
            }).execute()

        # 2. 새로운 인사이트 추출
        insights = await self.db.table('self_reflection_insights').select(
            'insight_type, insight_text, confidence'
        ).eq('outcome_after_apply', 'improved').gte(
            'created_at', (datetime.now() - timedelta(days=1)).isoformat()
        ).execute()

        for insight in insights.data or []:
            learning_type = {
                'failure_pattern': 'failure_lesson',
                'success_pattern': 'success_factor',
                'improvement_idea': 'strategy_insight'
            }.get(insight.get('insight_type'), 'domain_knowledge')

            await self.db.table('core_learnings').insert({
                'learning_type': learning_type,
                'summary': insight.get('insight_text', ''),
                'detailed_content': {},
                'source_session_ids': [self._current_session_id],
                'confidence': insight.get('confidence', 0.5)
            }).execute()

    @property
    def current_session_id(self) -> Optional[str]:
        return self._current_session_id


class LearningRestorer:
    """
    학습 복원기

    이전 세션의 학습 상태 복원
    """

    def __init__(self, supabase_client=None):
        self.db = supabase_client

    async def get_latest_restore_point(self) -> Optional[Dict]:
        """가장 최근 복원 포인트"""
        if not self.db:
            return None

        result = await self.db.table('session_restore_points').select(
            '*'
        ).eq('is_valid', True).order(
            'created_at', desc=True
        ).limit(1).execute()

        return result.data[0] if result.data else None

    async def restore_from_point(self, restore_point_id: str) -> bool:
        """복원 포인트에서 복원"""
        if not self.db:
            return False

        # 복원 포인트 조회
        point = await self.db.table('session_restore_points').select(
            '*'
        ).eq('id', restore_point_id).single().execute()

        if not point.data:
            return False

        data = point.data

        # 1. baby_state 복원
        baby_state = data.get('baby_state', {})
        if baby_state:
            # 기존 상태 업데이트
            result = await self.db.table('baby_state').select('id').limit(1).execute()
            if result.data:
                await self.db.table('baby_state').update({
                    'curiosity': baby_state.get('curiosity', 0.5),
                    'joy': baby_state.get('joy', 0.3),
                    'fear': baby_state.get('fear', 0.1),
                    'frustration': baby_state.get('frustration', 0.1),
                    'development_stage': baby_state.get('development_stage', 0),
                    'updated_at': datetime.now().isoformat()
                }).eq('id', result.data[0]['id']).execute()

        # 2. 규칙 복원
        active_rules = data.get('active_rules', [])
        if active_rules:
            # 모든 규칙 비활성화
            await self.db.table('learned_prompt_rules').update({
                'is_active': False
            }).execute()

            # 저장된 규칙만 활성화
            for rule in active_rules:
                await self.db.table('learned_prompt_rules').update({
                    'is_active': True
                }).eq('id', rule.get('id')).execute()

        # 3. 전략 가중치 복원
        strategy_weights = data.get('strategy_weights', {})
        for strategy_name, weight in strategy_weights.items():
            await self.db.table('strategy_effectiveness').update({
                'effectiveness_score': weight
            }).eq('strategy_name', strategy_name).execute()

        return True

    async def restore_latest(self) -> bool:
        """가장 최근 상태로 복원"""
        point = await self.get_latest_restore_point()
        if not point:
            return False

        return await self.restore_from_point(point['id'])

    async def get_core_learnings(
        self,
        learning_type: Optional[LearningType] = None,
        min_effectiveness: float = 0.5,
        limit: int = 20
    ) -> List[CoreLearning]:
        """핵심 학습 조회"""
        if not self.db:
            return []

        query = self.db.table('core_learnings').select(
            '*'
        ).eq('is_active', True).gte('effectiveness', min_effectiveness)

        if learning_type:
            query = query.eq('learning_type', learning_type.value)

        result = await query.order('effectiveness', desc=True).limit(limit).execute()

        return [
            CoreLearning(
                learning_type=LearningType(r['learning_type']),
                summary=r['summary'],
                detailed_content=r.get('detailed_content', {}),
                confidence=r.get('confidence', 0.5),
                effectiveness=r.get('effectiveness', 0),
                is_active=r.get('is_active', True)
            )
            for r in result.data or []
        ]

    async def apply_learning(
        self,
        learning_id: str,
        success: bool
    ):
        """학습 적용 기록"""
        if not self.db:
            return

        learning = await self.db.table('core_learnings').select(
            'times_applied, times_successful'
        ).eq('id', learning_id).single().execute()

        if not learning.data:
            return

        new_applied = learning.data['times_applied'] + 1
        new_successful = learning.data['times_successful'] + (1 if success else 0)

        await self.db.table('core_learnings').update({
            'times_applied': new_applied,
            'times_successful': new_successful,
            'last_applied_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }).eq('id', learning_id).execute()


class ContinuityTracker:
    """
    학습 연속성 추적기

    세션 간 학습 연속성 분석
    """

    def __init__(self, supabase_client=None):
        self.db = supabase_client

    async def track_continuity(
        self,
        from_session_id: str,
        to_session_id: str
    ) -> Dict[str, Any]:
        """세션 간 연속성 추적"""
        if not self.db:
            return {}

        # 두 세션의 스냅샷 비교
        from_snapshot = await self._get_end_snapshot(from_session_id)
        to_snapshot = await self._get_start_snapshot(to_session_id)

        if not from_snapshot or not to_snapshot:
            return {}

        # 개념 강도 비교
        from_concepts = from_snapshot.get('concept_strengths', {})
        to_concepts = to_snapshot.get('concept_strengths', {})

        retained = {}
        lost = {}
        reinforced = {}

        for concept, strength in from_concepts.items():
            if concept in to_concepts:
                new_strength = to_concepts[concept]
                if new_strength >= strength:
                    reinforced[concept] = {'from': strength, 'to': new_strength}
                else:
                    retained[concept] = {'from': strength, 'to': new_strength}
            else:
                lost[concept] = strength

        # 연속성 점수 계산
        total_concepts = len(from_concepts)
        if total_concepts > 0:
            continuity_score = (len(retained) + len(reinforced)) / total_concepts
        else:
            continuity_score = 1.0

        # 세션 간 간격 계산
        from_session = await self.db.table('learning_sessions').select(
            'ended_at'
        ).eq('id', from_session_id).single().execute()

        to_session = await self.db.table('learning_sessions').select(
            'started_at'
        ).eq('id', to_session_id).single().execute()

        gap_hours = 0
        if from_session.data and to_session.data:
            from_time = datetime.fromisoformat(
                from_session.data['ended_at'].replace('Z', '+00:00')
            )
            to_time = datetime.fromisoformat(
                to_session.data['started_at'].replace('Z', '+00:00')
            )
            gap_hours = int((to_time - from_time).total_seconds() / 3600)

        # 기록 저장
        result = {
            'continuity_score': continuity_score,
            'knowledge_retained': retained,
            'knowledge_lost': lost,
            'knowledge_reinforced': reinforced,
            'gap_duration_hours': gap_hours,
            'recovery_success': continuity_score > 0.7
        }

        await self.db.table('learning_continuity').insert({
            'from_session_id': from_session_id,
            'to_session_id': to_session_id,
            **result
        }).execute()

        return result

    async def _get_end_snapshot(self, session_id: str) -> Optional[Dict]:
        """세션 종료 스냅샷"""
        if not self.db:
            return None

        result = await self.db.table('learning_snapshots').select(
            '*'
        ).eq('session_id', session_id).eq(
            'snapshot_type', 'end_session'
        ).single().execute()

        return result.data

    async def _get_start_snapshot(self, session_id: str) -> Optional[Dict]:
        """세션 시작 스냅샷"""
        if not self.db:
            return None

        result = await self.db.table('learning_snapshots').select(
            '*'
        ).eq('session_id', session_id).order(
            'created_at', asc=True
        ).limit(1).execute()

        return result.data[0] if result.data else None


class PersistentLearningSubstrate:
    """
    영속 학습 기반 (메인 클래스)

    세션 간 학습 상태 영속화 및 복원

    Usage:
        substrate = PersistentLearningSubstrate(supabase_client)

        # 세션 시작
        session_id = await substrate.start_session("Training Session 1")

        # 주기적 체크포인트
        await substrate.checkpoint()

        # 세션 종료
        await substrate.end_session(key_learnings=["Learned error handling"])

        # 다음 세션에서 복원
        await substrate.restore_latest()

        # 핵심 학습 조회
        learnings = await substrate.get_effective_learnings()
    """

    CHECKPOINT_INTERVAL_MINUTES = 30

    def __init__(self, supabase_client=None):
        self.db = supabase_client
        self.session_manager = SessionManager(supabase_client)
        self.restorer = LearningRestorer(supabase_client)
        self.continuity_tracker = ContinuityTracker(supabase_client)
        self._last_checkpoint = datetime.now()

    async def start_session(self, name: str = None) -> str:
        """세션 시작"""
        # 이전 세션 확인
        prev_session = await self._get_last_session()

        session_id = await self.session_manager.start_session(name)

        # 연속성 추적
        if prev_session and session_id:
            await self.continuity_tracker.track_continuity(
                prev_session['id'], session_id
            )

        self._last_checkpoint = datetime.now()
        return session_id

    async def _get_last_session(self) -> Optional[Dict]:
        """마지막 세션"""
        if not self.db:
            return None

        result = await self.db.table('learning_sessions').select(
            'id, ended_at'
        ).is_not('ended_at', 'null').order(
            'ended_at', desc=True
        ).limit(1).execute()

        return result.data[0] if result.data else None

    async def end_session(self, key_learnings: List[str] = None):
        """세션 종료"""
        await self.session_manager.end_session(key_learnings)

    async def checkpoint(self):
        """체크포인트 생성"""
        await self.session_manager._create_snapshot(
            SnapshotType.CHECKPOINT,
            "Manual checkpoint"
        )
        self._last_checkpoint = datetime.now()

    async def auto_checkpoint_if_needed(self):
        """필요시 자동 체크포인트"""
        elapsed = (datetime.now() - self._last_checkpoint).total_seconds() / 60

        if elapsed >= self.CHECKPOINT_INTERVAL_MINUTES:
            await self.checkpoint()

    async def restore_latest(self) -> bool:
        """최신 상태로 복원"""
        return await self.restorer.restore_latest()

    async def get_effective_learnings(
        self,
        min_effectiveness: float = 0.6,
        limit: int = 10
    ) -> List[CoreLearning]:
        """효과적인 학습 조회"""
        return await self.restorer.get_core_learnings(
            min_effectiveness=min_effectiveness,
            limit=limit
        )

    async def record_learning_applied(
        self,
        learning_id: str,
        success: bool
    ):
        """학습 적용 결과 기록"""
        await self.restorer.apply_learning(learning_id, success)

    async def get_persistence_stats(self) -> Dict[str, Any]:
        """영속 학습 통계"""
        if not self.db:
            return {}

        # 세션 수
        sessions = await self.db.table('learning_sessions').select(
            'id', count='exact'
        ).execute()

        # 스냅샷 수
        snapshots = await self.db.table('learning_snapshots').select(
            'id', count='exact'
        ).execute()

        # 핵심 학습 수
        learnings = await self.db.table('core_learnings').select(
            'id', count='exact'
        ).eq('is_active', True).execute()

        # 평균 연속성 점수
        continuity = await self.db.table('learning_continuity').select(
            'continuity_score'
        ).execute()

        avg_continuity = 0
        if continuity.data:
            avg_continuity = sum(
                c['continuity_score'] for c in continuity.data
            ) / len(continuity.data)

        # 복원 포인트 수
        restore_points = await self.db.table('session_restore_points').select(
            'id', count='exact'
        ).eq('is_valid', True).execute()

        return {
            'total_sessions': sessions.count or 0,
            'total_snapshots': snapshots.count or 0,
            'active_learnings': learnings.count or 0,
            'avg_continuity_score': avg_continuity,
            'valid_restore_points': restore_points.count or 0,
            'current_session_id': self.session_manager.current_session_id
        }
