"""
Team Optimizer for Baby AI - Phase 10

에이전트 팀 구성 최적화

핵심 기능:
1. 협력 패턴 학습 - 어떤 에이전트 조합이 효과적인지
2. 동적 팀 구성 - 작업 유형에 따라 최적 팀 추천
3. 팀 성능 추적 - 팀별 성과 기록 및 분석
4. A/B 테스트 - 팀 구성 실험
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
import json


class CooperationType(Enum):
    """협력 유형"""
    SEQUENTIAL = "sequential"      # A → B 순차 실행
    PARALLEL = "parallel"          # A || B 병렬 실행
    ITERATIVE = "iterative"        # A ↔ B 반복 협업
    SUPERVISORY = "supervisory"    # A supervises B


class TeamType(Enum):
    """팀 유형"""
    STATIC = "static"       # 고정 팀
    DYNAMIC = "dynamic"     # 동적 팀 (작업에 따라 변경)
    ADAPTIVE = "adaptive"   # 적응형 팀 (성과에 따라 진화)


@dataclass
class AgentRole:
    """에이전트 역할"""
    role: str           # 역할 이름 (coder, reviewer, etc.)
    agent_type: str     # 에이전트 타입
    weight: float       # 팀 내 가중치 (0-1)


@dataclass
class Team:
    """에이전트 팀"""
    id: str
    name: str
    description: str
    roles: List[AgentRole]
    team_type: TeamType
    is_active: bool = True


@dataclass
class TeamPerformance:
    """팀 성과 기록"""
    team_id: str
    task_type: str
    success: bool
    quality_score: float
    total_latency_ms: int
    agent_contributions: Dict[str, Dict[str, Any]]
    coordination_score: float  # 협업 효율성


@dataclass
class CooperationPattern:
    """에이전트 협력 패턴"""
    agent_pair: str  # 'agent1:agent2' 형식
    task_type: str
    cooperation_type: CooperationType
    success_rate: float
    synergy_score: float  # > 0.5 = 시너지 효과


@dataclass
class TeamRecommendation:
    """팀 추천"""
    task_type: str
    recommended_team: Team
    alternatives: List[Team]
    confidence: float
    reason: str


class CooperationPatternLearner:
    """
    협력 패턴 학습기

    에이전트 쌍의 협력 효과를 분석하고 학습
    """

    def __init__(self, supabase_client=None):
        self.db = supabase_client

    async def record_cooperation(
        self,
        agent1: str,
        agent2: str,
        task_type: str,
        cooperation_type: CooperationType,
        success: bool,
        synergy_score: float
    ):
        """협력 결과 기록"""
        if not self.db:
            return

        agent_pair = f"{agent1}:{agent2}"

        # 기존 패턴 조회
        result = await self.db.table('agent_cooperation_patterns').select(
            '*'
        ).eq('agent_pair', agent_pair).eq('task_type', task_type).execute()

        if result.data:
            # 기존 패턴 업데이트
            pattern = result.data[0]
            new_success = pattern['success_count'] + (1 if success else 0)
            new_failure = pattern['failure_count'] + (0 if success else 1)

            # 이동 평균으로 synergy score 업데이트
            alpha = 0.3  # 학습률
            new_synergy = (
                pattern['avg_synergy_score'] * (1 - alpha) +
                synergy_score * alpha
            )

            await self.db.table('agent_cooperation_patterns').update({
                'success_count': new_success,
                'failure_count': new_failure,
                'avg_synergy_score': new_synergy,
                'last_used_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }).eq('id', pattern['id']).execute()
        else:
            # 새 패턴 생성
            await self.db.table('agent_cooperation_patterns').insert({
                'agent_pair': agent_pair,
                'task_type': task_type,
                'cooperation_type': cooperation_type.value,
                'success_count': 1 if success else 0,
                'failure_count': 0 if success else 1,
                'avg_synergy_score': synergy_score,
                'last_used_at': datetime.now().isoformat()
            }).execute()

    async def get_best_partner(
        self,
        agent: str,
        task_type: str,
        min_experiments: int = 3
    ) -> Optional[Tuple[str, float]]:
        """특정 에이전트의 최적 파트너 찾기"""
        if not self.db:
            return None

        # 해당 에이전트가 포함된 모든 협력 패턴 조회
        result = await self.db.table('agent_cooperation_patterns').select(
            '*'
        ).like('agent_pair', f'%{agent}%').execute()

        if not result.data:
            return None

        best_partner = None
        best_score = 0

        for pattern in result.data:
            total = pattern['success_count'] + pattern['failure_count']
            if total < min_experiments:
                continue

            # task_type 매칭 보너스
            type_bonus = 1.2 if pattern.get('task_type') == task_type else 1.0

            # 종합 점수 = 성공률 * 시너지 * 타입보너스
            success_rate = (
                pattern['success_count'] / total if total > 0 else 0
            )
            score = success_rate * pattern['avg_synergy_score'] * type_bonus

            if score > best_score:
                best_score = score
                # 파트너 추출
                pair = pattern['agent_pair']
                partner = pair.replace(f'{agent}:', '').replace(f':{agent}', '')
                best_partner = partner

        return (best_partner, best_score) if best_partner else None

    async def get_synergistic_pairs(
        self,
        min_synergy: float = 0.6,
        min_experiments: int = 5
    ) -> List[CooperationPattern]:
        """시너지 효과가 좋은 에이전트 쌍 조회"""
        if not self.db:
            return []

        result = await self.db.table('agent_cooperation_patterns').select(
            '*'
        ).gte('avg_synergy_score', min_synergy).execute()

        patterns = []
        for row in result.data or []:
            total = row['success_count'] + row['failure_count']
            if total < min_experiments:
                continue

            patterns.append(CooperationPattern(
                agent_pair=row['agent_pair'],
                task_type=row.get('task_type', 'general'),
                cooperation_type=CooperationType(row['cooperation_type']),
                success_rate=row['success_count'] / total if total > 0 else 0,
                synergy_score=row['avg_synergy_score']
            ))

        return sorted(patterns, key=lambda x: -x.synergy_score)


class TeamPerformanceTracker:
    """
    팀 성능 추적기

    팀별 성과를 기록하고 분석
    """

    def __init__(self, supabase_client=None):
        self.db = supabase_client

    async def record_performance(
        self,
        team_id: str,
        task_type: str,
        experience_id: str,
        success: bool,
        quality_score: float,
        latency_ms: int,
        agent_contributions: Dict[str, Dict[str, Any]],
        coordination_score: float
    ):
        """팀 성과 기록"""
        if not self.db:
            return

        await self.db.table('team_performance').insert({
            'team_id': team_id,
            'task_type': task_type,
            'experience_id': experience_id,
            'success': success,
            'quality_score': quality_score,
            'total_latency_ms': latency_ms,
            'agent_contributions': agent_contributions,
            'coordination_score': coordination_score
        }).execute()

    async def get_team_stats(
        self,
        team_id: str,
        task_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """팀 통계 조회"""
        if not self.db:
            return {}

        query = self.db.table('team_performance').select('*').eq('team_id', team_id)
        if task_type:
            query = query.eq('task_type', task_type)

        result = await query.execute()

        if not result.data:
            return {
                'total_tasks': 0,
                'success_rate': 0,
                'avg_quality': 0,
                'avg_latency_ms': 0,
                'avg_coordination': 0
            }

        performances = result.data
        total = len(performances)
        successes = sum(1 for p in performances if p['success'])

        return {
            'total_tasks': total,
            'success_rate': successes / total,
            'avg_quality': sum(p['quality_score'] for p in performances) / total,
            'avg_latency_ms': sum(p['total_latency_ms'] for p in performances) / total,
            'avg_coordination': sum(p['coordination_score'] for p in performances) / total
        }

    async def compare_teams(
        self,
        team1_id: str,
        team2_id: str,
        task_type: str
    ) -> Dict[str, Any]:
        """두 팀 성능 비교"""
        stats1 = await self.get_team_stats(team1_id, task_type)
        stats2 = await self.get_team_stats(team2_id, task_type)

        return {
            'team1': stats1,
            'team2': stats2,
            'winner': (
                'team1' if stats1.get('success_rate', 0) > stats2.get('success_rate', 0)
                else 'team2' if stats2.get('success_rate', 0) > stats1.get('success_rate', 0)
                else 'tie'
            ),
            'success_rate_diff': stats1.get('success_rate', 0) - stats2.get('success_rate', 0),
            'quality_diff': stats1.get('avg_quality', 0) - stats2.get('avg_quality', 0)
        }


class DynamicTeamBuilder:
    """
    동적 팀 구성기

    작업 유형과 맥락에 따라 최적의 팀 구성
    """

    def __init__(self, supabase_client=None):
        self.db = supabase_client
        self.pattern_learner = CooperationPatternLearner(supabase_client)

    async def build_team(
        self,
        task_type: str,
        complexity: float,  # 0-1
        available_agents: List[str],
        max_team_size: int = 4
    ) -> Team:
        """
        동적 팀 구성

        Args:
            task_type: 작업 유형
            complexity: 복잡도 (0=단순, 1=복잡)
            available_agents: 사용 가능한 에이전트 목록
            max_team_size: 최대 팀 크기

        Returns:
            구성된 팀
        """
        # 1. 기존 추천 확인
        recommendation = await self._get_existing_recommendation(task_type)
        if recommendation and recommendation['confidence'] > 0.7:
            team = await self._load_team(recommendation['recommended_team_id'])
            if team:
                return team

        # 2. 복잡도에 따른 팀 크기 결정
        team_size = min(
            max_team_size,
            max(1, int(1 + complexity * 3))  # 1-4명
        )

        # 3. 핵심 역할 결정
        roles = await self._determine_roles(task_type, team_size)

        # 4. 최적 에이전트 할당
        assigned_roles = await self._assign_agents(
            roles, available_agents, task_type
        )

        # 5. 팀 생성
        team = Team(
            id='dynamic_' + datetime.now().strftime('%Y%m%d%H%M%S'),
            name=f'Dynamic Team for {task_type}',
            description=f'Complexity: {complexity:.2f}, Size: {team_size}',
            roles=assigned_roles,
            team_type=TeamType.DYNAMIC,
            is_active=True
        )

        return team

    async def _get_existing_recommendation(self, task_type: str) -> Optional[Dict]:
        """기존 추천 조회"""
        if not self.db:
            return None

        result = await self.db.table('team_recommendations').select(
            '*'
        ).eq('task_type', task_type).eq('is_active', True).single().execute()

        return result.data if result.data else None

    async def _load_team(self, team_id: str) -> Optional[Team]:
        """팀 로드"""
        if not self.db:
            return None

        result = await self.db.table('agent_teams').select(
            '*'
        ).eq('id', team_id).single().execute()

        if not result.data:
            return None

        data = result.data
        roles = [
            AgentRole(
                role=r['role'],
                agent_type=r['agent_type'],
                weight=r['weight']
            )
            for r in data['agent_roles']
        ]

        return Team(
            id=data['id'],
            name=data['team_name'],
            description=data.get('description', ''),
            roles=roles,
            team_type=TeamType(data['team_type']),
            is_active=data['is_active']
        )

    async def _determine_roles(
        self,
        task_type: str,
        team_size: int
    ) -> List[str]:
        """작업 유형에 따른 역할 결정"""
        # 작업 유형별 권장 역할
        ROLE_MAPPINGS = {
            'coding': ['coder', 'reviewer', 'tester'],
            'bug_fix': ['debugger', 'coder', 'tester'],
            'feature': ['planner', 'coder', 'reviewer', 'tester'],
            'documentation': ['writer', 'reviewer'],
            'analysis': ['analyst', 'reviewer'],
            'design': ['architect', 'reviewer'],
            'default': ['baby', 'assistant']
        }

        roles = ROLE_MAPPINGS.get(task_type, ROLE_MAPPINGS['default'])
        return roles[:team_size]

    async def _assign_agents(
        self,
        roles: List[str],
        available_agents: List[str],
        task_type: str
    ) -> List[AgentRole]:
        """역할에 에이전트 할당"""
        assigned = []
        used_agents = set()

        for i, role in enumerate(roles):
            # 역할과 매칭되는 에이전트 찾기
            best_agent = None
            best_score = -1

            for agent in available_agents:
                if agent in used_agents:
                    continue

                # 매칭 점수 계산
                score = self._calculate_role_match(role, agent)

                # 협력 패턴 고려
                if assigned and self.db:
                    partner_bonus = await self._get_partner_bonus(
                        agent, [a.agent_type for a in assigned], task_type
                    )
                    score *= (1 + partner_bonus)

                if score > best_score:
                    best_score = score
                    best_agent = agent

            if best_agent:
                weight = 1.0 / len(roles)  # 균등 가중치
                assigned.append(AgentRole(
                    role=role,
                    agent_type=best_agent,
                    weight=weight
                ))
                used_agents.add(best_agent)

        return assigned

    def _calculate_role_match(self, role: str, agent: str) -> float:
        """역할-에이전트 매칭 점수"""
        # 역할과 에이전트 타입이 같으면 높은 점수
        if role == agent or role in agent or agent in role:
            return 1.0

        # 유사 역할 매칭
        SIMILAR_ROLES = {
            'coder': ['developer', 'programmer', 'engineer'],
            'reviewer': ['checker', 'validator'],
            'tester': ['qa', 'test'],
            'planner': ['architect', 'designer'],
            'writer': ['documenter', 'author'],
            'baby': ['assistant', 'helper']
        }

        for base_role, similar in SIMILAR_ROLES.items():
            if role == base_role and agent in similar:
                return 0.8
            if agent == base_role and role in similar:
                return 0.8

        return 0.5  # 기본 점수

    async def _get_partner_bonus(
        self,
        agent: str,
        existing_agents: List[str],
        task_type: str
    ) -> float:
        """기존 팀원과의 협력 보너스"""
        if not self.db or not existing_agents:
            return 0

        total_bonus = 0
        for partner in existing_agents:
            pair1 = f"{agent}:{partner}"
            pair2 = f"{partner}:{agent}"

            result = await self.db.table('agent_cooperation_patterns').select(
                'avg_synergy_score'
            ).or_(f'agent_pair.eq.{pair1},agent_pair.eq.{pair2}').execute()

            if result.data:
                # 시너지가 0.5 이상이면 보너스
                synergy = result.data[0].get('avg_synergy_score', 0.5)
                total_bonus += max(0, synergy - 0.5)

        return total_bonus / len(existing_agents) if existing_agents else 0


class TeamOptimizer:
    """
    팀 최적화 엔진 (메인 클래스)

    에이전트 팀 구성을 학습하고 최적화

    Usage:
        optimizer = TeamOptimizer(supabase_client)

        # 팀 추천
        recommendation = await optimizer.recommend_team('coding', complexity=0.7)

        # 성능 기록
        await optimizer.record_team_result(team_id, experience_id, success=True, ...)

        # 협력 패턴 학습
        await optimizer.learn_cooperation('coder', 'reviewer', task_type, success=True)

        # 팀 A/B 테스트
        await optimizer.run_team_experiment(team1_id, team2_id, task_type)
    """

    def __init__(self, supabase_client=None):
        self.db = supabase_client
        self.pattern_learner = CooperationPatternLearner(supabase_client)
        self.performance_tracker = TeamPerformanceTracker(supabase_client)
        self.team_builder = DynamicTeamBuilder(supabase_client)

    async def recommend_team(
        self,
        task_type: str,
        complexity: float = 0.5,
        available_agents: Optional[List[str]] = None
    ) -> TeamRecommendation:
        """
        작업에 대한 최적 팀 추천

        Args:
            task_type: 작업 유형
            complexity: 복잡도 (0-1)
            available_agents: 사용 가능한 에이전트 (None이면 모두)

        Returns:
            팀 추천
        """
        if available_agents is None:
            available_agents = await self._get_all_agents()

        # 1. 기존 추천 확인
        existing = await self._get_recommendation(task_type)
        if existing and existing.get('confidence', 0) > 0.8:
            team = await self.team_builder._load_team(
                existing['recommended_team_id']
            )
            if team:
                return TeamRecommendation(
                    task_type=task_type,
                    recommended_team=team,
                    alternatives=[],
                    confidence=existing['confidence'],
                    reason=existing.get('recommendation_reason', '')
                )

        # 2. 동적 팀 구성
        team = await self.team_builder.build_team(
            task_type, complexity, available_agents
        )

        # 3. 대안 팀 조회
        alternatives = await self._get_alternative_teams(task_type)

        return TeamRecommendation(
            task_type=task_type,
            recommended_team=team,
            alternatives=alternatives,
            confidence=0.5,  # 동적 구성은 낮은 신뢰도로 시작
            reason=f'Dynamic team for {task_type} (complexity: {complexity:.2f})'
        )

    async def _get_all_agents(self) -> List[str]:
        """사용 가능한 모든 에이전트"""
        return ['baby', 'coder', 'reviewer', 'tester', 'planner', 'writer']

    async def _get_recommendation(self, task_type: str) -> Optional[Dict]:
        """기존 추천 조회"""
        if not self.db:
            return None

        result = await self.db.table('team_recommendations').select(
            '*'
        ).eq('task_type', task_type).eq('is_active', True).single().execute()

        return result.data

    async def _get_alternative_teams(self, task_type: str) -> List[Team]:
        """대안 팀 조회"""
        if not self.db:
            return []

        # 성능 좋은 팀들 조회
        result = await self.db.table('team_performance').select(
            'team_id'
        ).eq('task_type', task_type).eq('success', True).limit(10).execute()

        if not result.data:
            return []

        team_ids = list(set(r['team_id'] for r in result.data))[:3]

        teams = []
        for team_id in team_ids:
            team = await self.team_builder._load_team(team_id)
            if team:
                teams.append(team)

        return teams

    async def record_team_result(
        self,
        team_id: str,
        experience_id: str,
        success: bool,
        quality_score: float,
        latency_ms: int,
        task_type: str,
        agent_contributions: Optional[Dict] = None,
        coordination_score: float = 0.5
    ):
        """팀 결과 기록"""
        await self.performance_tracker.record_performance(
            team_id=team_id,
            task_type=task_type,
            experience_id=experience_id,
            success=success,
            quality_score=quality_score,
            latency_ms=latency_ms,
            agent_contributions=agent_contributions or {},
            coordination_score=coordination_score
        )

        # 추천 업데이트 고려
        await self._update_recommendation(team_id, task_type)

    async def _update_recommendation(self, team_id: str, task_type: str):
        """추천 업데이트"""
        if not self.db:
            return

        # 팀 통계 조회
        stats = await self.performance_tracker.get_team_stats(team_id, task_type)

        if stats['total_tasks'] < 5:
            return  # 충분한 데이터 없음

        # 기존 추천과 비교
        existing = await self._get_recommendation(task_type)

        if existing:
            existing_stats = await self.performance_tracker.get_team_stats(
                existing['recommended_team_id'], task_type
            )

            # 새 팀이 더 좋으면 추천 업데이트
            if stats['success_rate'] > existing_stats.get('success_rate', 0) + 0.1:
                await self._save_recommendation(
                    task_type, team_id,
                    stats['success_rate'],
                    f"Better success rate: {stats['success_rate']:.2%}"
                )
        else:
            # 첫 추천
            if stats['success_rate'] >= 0.5:
                await self._save_recommendation(
                    task_type, team_id,
                    stats['success_rate'],
                    f"Initial recommendation with {stats['success_rate']:.2%} success"
                )

    async def _save_recommendation(
        self,
        task_type: str,
        team_id: str,
        confidence: float,
        reason: str
    ):
        """추천 저장"""
        if not self.db:
            return

        await self.db.table('team_recommendations').upsert({
            'task_type': task_type,
            'recommended_team_id': team_id,
            'confidence': confidence,
            'recommendation_reason': reason,
            'is_active': True,
            'updated_at': datetime.now().isoformat()
        }, on_conflict='task_type').execute()

    async def learn_cooperation(
        self,
        agent1: str,
        agent2: str,
        task_type: str,
        success: bool,
        synergy_score: float = 0.5,
        cooperation_type: CooperationType = CooperationType.SEQUENTIAL
    ):
        """협력 패턴 학습"""
        await self.pattern_learner.record_cooperation(
            agent1, agent2, task_type, cooperation_type, success, synergy_score
        )

    async def run_team_experiment(
        self,
        baseline_team_id: str,
        treatment_team_id: str,
        task_type: str,
        hypothesis: str
    ) -> str:
        """팀 A/B 테스트 시작"""
        if not self.db:
            return ""

        result = await self.db.table('team_experiments').insert({
            'experiment_name': f'{task_type}_experiment_{datetime.now().strftime("%Y%m%d")}',
            'baseline_team_id': baseline_team_id,
            'treatment_team_id': treatment_team_id,
            'task_type': task_type,
            'hypothesis': hypothesis,
            'conclusion': 'pending'
        }).execute()

        return result.data[0]['id'] if result.data else ""

    async def conclude_experiment(
        self,
        experiment_id: str,
        min_experiments: int = 10
    ) -> Dict[str, Any]:
        """실험 결론 도출"""
        if not self.db:
            return {'conclusion': 'pending'}

        # 실험 정보 조회
        exp_result = await self.db.table('team_experiments').select(
            '*'
        ).eq('id', experiment_id).single().execute()

        if not exp_result.data:
            return {'error': 'Experiment not found'}

        exp = exp_result.data

        # 각 팀 통계
        baseline_stats = await self.performance_tracker.get_team_stats(
            exp['baseline_team_id'], exp['task_type']
        )
        treatment_stats = await self.performance_tracker.get_team_stats(
            exp['treatment_team_id'], exp['task_type']
        )

        # 충분한 데이터 확인
        if (baseline_stats['total_tasks'] < min_experiments or
            treatment_stats['total_tasks'] < min_experiments):
            return {
                'conclusion': 'pending',
                'reason': f'Need more data (baseline: {baseline_stats["total_tasks"]}, treatment: {treatment_stats["total_tasks"]})'
            }

        # 결론 도출
        diff = treatment_stats['success_rate'] - baseline_stats['success_rate']

        if diff > 0.1:
            conclusion = 'treatment_better'
            was_adopted = True
        elif diff < -0.1:
            conclusion = 'baseline_better'
            was_adopted = False
        else:
            conclusion = 'no_difference'
            was_adopted = False

        # 업데이트
        await self.db.table('team_experiments').update({
            'baseline_metrics': baseline_stats,
            'treatment_metrics': treatment_stats,
            'baseline_experiments': baseline_stats['total_tasks'],
            'treatment_experiments': treatment_stats['total_tasks'],
            'conclusion': conclusion,
            'was_adopted': was_adopted,
            'concluded_at': datetime.now().isoformat()
        }).eq('id', experiment_id).execute()

        # treatment가 더 좋으면 추천 업데이트
        if was_adopted:
            await self._save_recommendation(
                exp['task_type'],
                exp['treatment_team_id'],
                treatment_stats['success_rate'],
                f'Experiment concluded: {diff:.2%} improvement'
            )

        return {
            'conclusion': conclusion,
            'baseline_success_rate': baseline_stats['success_rate'],
            'treatment_success_rate': treatment_stats['success_rate'],
            'improvement': diff,
            'was_adopted': was_adopted
        }

    async def get_optimization_stats(self) -> Dict[str, Any]:
        """최적화 통계"""
        if not self.db:
            return {}

        # 활성 팀 수
        teams = await self.db.table('agent_teams').select(
            'id', count='exact'
        ).eq('is_active', True).execute()

        # 협력 패턴 수
        patterns = await self.db.table('agent_cooperation_patterns').select(
            'id', count='exact'
        ).execute()

        # 추천 수
        recommendations = await self.db.table('team_recommendations').select(
            'id', count='exact'
        ).eq('is_active', True).execute()

        # 실험 수
        experiments = await self.db.table('team_experiments').select(
            'id', count='exact'
        ).execute()

        # 채택된 실험
        adopted = await self.db.table('team_experiments').select(
            'id', count='exact'
        ).eq('was_adopted', True).execute()

        return {
            'active_teams': teams.count or 0,
            'cooperation_patterns': patterns.count or 0,
            'active_recommendations': recommendations.count or 0,
            'total_experiments': experiments.count or 0,
            'adopted_experiments': adopted.count or 0,
            'adoption_rate': (
                (adopted.count or 0) / max(1, experiments.count or 1)
            )
        }
