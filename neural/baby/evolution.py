"""
Self-Evolution Engine for Baby AI - Phase 10

실수에서 배워서 프롬프트와 전략을 자동 개선하는 자기 진화 엔진

핵심 기능:
1. Failure Pattern Detection - 실패 패턴 탐지 (LLM 없이)
2. Prompt Evolution - 규칙 기반 프롬프트 개선
3. A/B Testing - 진화 실험 및 검증
4. Strategy Adaptation - 전략 가중치 조정
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
from collections import Counter
import json
import re


class FailureType(Enum):
    """실패 유형"""
    RECURRING = "recurring"        # 반복 실패 (같은 유형 3+ 번)
    NEW = "new"                    # 새로운 실패 (처음 보는 유형)
    REGRESSION = "regression"      # 퇴행 실패 (이전 성공 → 실패)
    EDGE_CASE = "edge_case"        # 엣지 케이스 실패
    TIMEOUT = "timeout"            # 시간 초과


class EvolutionType(Enum):
    """프롬프트 진화 유형"""
    RULE_ADDITION = "rule_addition"    # 규칙 추가
    REFINEMENT = "refinement"          # 기존 규칙 개선
    REWRITE = "rewrite"                # 전체 재작성
    REMOVAL = "removal"                # 불필요한 규칙 제거


class InsightType(Enum):
    """인사이트 유형"""
    FAILURE_PATTERN = "failure_pattern"
    SUCCESS_PATTERN = "success_pattern"
    IMPROVEMENT_IDEA = "improvement_idea"
    ANTI_PATTERN = "anti_pattern"
    STRATEGY_INSIGHT = "strategy_insight"


@dataclass
class FailurePattern:
    """실패 패턴"""
    type: FailureType
    task_type: str
    count: int
    severity: str  # 'low', 'medium', 'high', 'critical'
    description: str
    keywords: List[str] = field(default_factory=list)
    example_tasks: List[str] = field(default_factory=list)
    experience_ids: List[str] = field(default_factory=list)
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None


@dataclass
class PromptEvolution:
    """프롬프트 진화 제안"""
    agent_type: str
    original_prompt: str
    evolved_prompt: str
    evolution_type: EvolutionType
    failure_pattern: FailurePattern
    improvement_hypothesis: str
    additions: List[str] = field(default_factory=list)
    removals: List[str] = field(default_factory=list)


@dataclass
class ExperimentResult:
    """실험 결과"""
    experiment_id: str
    evolution_id: str
    variant: str  # 'control' or 'treatment'
    success: bool
    quality_score: float
    latency_ms: int
    feedback_rating: Optional[int] = None


# 프롬프트 진화 규칙 (LLM 없이 규칙 기반)
EVOLUTION_RULES: Dict[str, Dict[str, Any]] = {
    'error_handling': {
        'keywords': ['에러', 'error', 'exception', 'try', 'catch', '오류', 'fail', 'crash', 'throw'],
        'task_types': ['coding', 'bug_fix', 'implementation'],
        'addition': '반드시 적절한 에러 핸들링을 포함하세요. try-except 블록을 사용하고 의미 있는 에러 메시지를 제공하세요.',
        'priority': 90
    },
    'edge_cases': {
        'keywords': ['edge', '경계', 'null', 'empty', '빈', 'None', 'undefined', '0', '음수', 'negative'],
        'task_types': ['coding', 'validation', 'testing'],
        'addition': '엣지 케이스를 반드시 고려하세요: null/None, 빈 값, 0, 음수, 매우 큰 값, 특수 문자.',
        'priority': 85
    },
    'input_validation': {
        'keywords': ['validation', '검증', 'invalid', '잘못된', 'type', '타입', 'format'],
        'task_types': ['coding', 'api', 'form'],
        'addition': '입력값 검증을 먼저 수행하세요. 타입, 형식, 범위를 확인하세요.',
        'priority': 80
    },
    'clarity': {
        'keywords': ['이해', 'understand', '모르', 'confus', '복잡', 'complex', 'unclear'],
        'task_types': ['explanation', 'documentation', 'teaching'],
        'addition': '설명은 단계별로 명확하게 작성하세요. 복잡한 개념은 예시와 함께 설명하세요.',
        'priority': 75
    },
    'completeness': {
        'keywords': ['incomplete', '불완전', '빠진', 'missing', 'todo', '나중', 'later', 'finish'],
        'task_types': ['coding', 'documentation'],
        'addition': '모든 요구사항을 완전히 구현하세요. TODO나 placeholder를 남기지 마세요.',
        'priority': 88
    },
    'performance': {
        'keywords': ['slow', '느린', 'timeout', 'memory', 'efficiency', '성능', 'optimize'],
        'task_types': ['coding', 'optimization'],
        'addition': '성능을 고려하세요. 불필요한 반복, 중복 연산, 메모리 낭비를 피하세요.',
        'priority': 70
    },
    'security': {
        'keywords': ['security', '보안', 'injection', 'xss', 'auth', 'password', 'token', 'secret'],
        'task_types': ['coding', 'authentication', 'api'],
        'addition': '보안을 고려하세요. 입력 살균, 인증/인가, 민감 정보 보호에 주의하세요.',
        'priority': 95
    },
    'testing': {
        'keywords': ['test', '테스트', 'unit', 'mock', 'assert', 'coverage'],
        'task_types': ['coding', 'testing'],
        'addition': '테스트 가능한 코드를 작성하세요. 주요 로직에 대한 테스트 케이스를 고려하세요.',
        'priority': 65
    }
}


class FailurePatternDetector:
    """
    실패 패턴 탐지기 (LLM 없이 규칙 기반)

    경험 데이터를 분석하여 반복되는 실패 패턴을 찾음
    """

    def __init__(self, supabase_client=None):
        self.db = supabase_client

    async def analyze_failures(
        self,
        experiences: List[Dict[str, Any]],
        window_hours: int = 24
    ) -> List[FailurePattern]:
        """
        최근 실패 경험 분석

        Args:
            experiences: 분석할 경험 목록
            window_hours: 분석할 시간 범위 (시간)

        Returns:
            발견된 실패 패턴 목록
        """
        patterns = []

        # 실패한 경험만 필터링
        failures = [e for e in experiences if not e.get('success', True)]

        if not failures:
            return patterns

        # 1. 반복 실패 탐지 (같은 task_type에서 3+ 실패)
        recurring = self._detect_recurring_failures(failures)
        patterns.extend(recurring)

        # 2. 키워드 기반 패턴 탐지
        keyword_patterns = self._detect_keyword_patterns(failures)
        patterns.extend(keyword_patterns)

        # 3. 퇴행 실패 탐지 (이전 성공 → 현재 실패)
        if experiences:
            regression = self._detect_regression_failures(experiences)
            patterns.extend(regression)

        return patterns

    def _detect_recurring_failures(self, failures: List[Dict]) -> List[FailurePattern]:
        """반복 실패 탐지"""
        patterns = []
        task_type_counter = Counter()
        task_type_examples: Dict[str, List[str]] = {}
        task_type_ids: Dict[str, List[str]] = {}

        for f in failures:
            task_type = f.get('task_type', 'unknown')
            task_type_counter[task_type] += 1

            if task_type not in task_type_examples:
                task_type_examples[task_type] = []
                task_type_ids[task_type] = []

            if len(task_type_examples[task_type]) < 3:
                task_type_examples[task_type].append(f.get('task', '')[:100])
            task_type_ids[task_type].append(f.get('id', ''))

        for task_type, count in task_type_counter.items():
            if count >= 3:  # 3번 이상 실패
                severity = 'critical' if count >= 10 else 'high' if count >= 5 else 'medium'
                patterns.append(FailurePattern(
                    type=FailureType.RECURRING,
                    task_type=task_type,
                    count=count,
                    severity=severity,
                    description=f"'{task_type}' 유형에서 {count}번 반복 실패",
                    example_tasks=task_type_examples.get(task_type, []),
                    experience_ids=task_type_ids.get(task_type, [])
                ))

        return patterns

    def _detect_keyword_patterns(self, failures: List[Dict]) -> List[FailurePattern]:
        """키워드 기반 패턴 탐지"""
        patterns = []
        keyword_counts: Dict[str, int] = {}
        keyword_examples: Dict[str, List[str]] = {}

        for f in failures:
            task_text = (f.get('task', '') + ' ' + f.get('output', '')).lower()

            for rule_name, rule in EVOLUTION_RULES.items():
                for keyword in rule['keywords']:
                    if keyword.lower() in task_text:
                        if rule_name not in keyword_counts:
                            keyword_counts[rule_name] = 0
                            keyword_examples[rule_name] = []
                        keyword_counts[rule_name] += 1

                        if len(keyword_examples[rule_name]) < 3:
                            keyword_examples[rule_name].append(f.get('task', '')[:100])
                        break  # 같은 규칙에서 하나만 카운트

        for rule_name, count in keyword_counts.items():
            if count >= 2:  # 2번 이상 발견
                patterns.append(FailurePattern(
                    type=FailureType.RECURRING,
                    task_type=rule_name,
                    count=count,
                    severity='medium' if count < 5 else 'high',
                    description=f"'{rule_name}' 관련 키워드가 {count}번 실패에서 발견됨",
                    keywords=EVOLUTION_RULES[rule_name]['keywords'][:5],
                    example_tasks=keyword_examples.get(rule_name, [])
                ))

        return patterns

    def _detect_regression_failures(self, all_experiences: List[Dict]) -> List[FailurePattern]:
        """퇴행 실패 탐지 (이전 성공 → 현재 실패)"""
        patterns = []

        # task_type별로 그룹화
        by_task_type: Dict[str, List[Dict]] = {}
        for exp in all_experiences:
            task_type = exp.get('task_type', 'unknown')
            if task_type not in by_task_type:
                by_task_type[task_type] = []
            by_task_type[task_type].append(exp)

        for task_type, exps in by_task_type.items():
            # 시간순 정렬
            sorted_exps = sorted(exps, key=lambda x: x.get('created_at', ''))

            # 연속된 성공 후 실패 패턴 찾기
            success_streak = 0
            for i, exp in enumerate(sorted_exps):
                if exp.get('success'):
                    success_streak += 1
                else:
                    if success_streak >= 3:  # 3번 이상 성공 후 실패
                        patterns.append(FailurePattern(
                            type=FailureType.REGRESSION,
                            task_type=task_type,
                            count=1,
                            severity='high',
                            description=f"'{task_type}'에서 {success_streak}번 연속 성공 후 실패 (퇴행)",
                            example_tasks=[exp.get('task', '')[:100]],
                            experience_ids=[exp.get('id', '')]
                        ))
                    success_streak = 0

        return patterns


class PromptEvolver:
    """
    프롬프트 진화기 (규칙 기반)

    실패 패턴을 기반으로 프롬프트 개선안 생성
    """

    def __init__(self, supabase_client=None):
        self.db = supabase_client
        self._cached_rules: Dict[str, List[Dict]] = {}

    async def load_learned_rules(self, agent_type: str) -> List[Dict]:
        """학습된 규칙 로드"""
        if agent_type in self._cached_rules:
            return self._cached_rules[agent_type]

        if self.db:
            result = await self.db.table('learned_prompt_rules').select('*').eq(
                'agent_type', agent_type
            ).eq('is_active', True).order('priority', desc=True).execute()
            self._cached_rules[agent_type] = result.data or []
        else:
            self._cached_rules[agent_type] = []

        return self._cached_rules[agent_type]

    def evolve_prompt(
        self,
        original_prompt: str,
        failure_pattern: FailurePattern,
        agent_type: str = 'baby'
    ) -> Optional[PromptEvolution]:
        """
        실패 패턴 기반 프롬프트 진화

        Args:
            original_prompt: 원본 프롬프트
            failure_pattern: 발견된 실패 패턴
            agent_type: 에이전트 유형

        Returns:
            프롬프트 진화 제안 (개선점 없으면 None)
        """
        additions = []
        matched_rules = []

        # 1. 실패 패턴의 키워드와 매칭되는 규칙 찾기
        pattern_text = ' '.join([
            failure_pattern.description,
            failure_pattern.task_type,
            ' '.join(failure_pattern.keywords),
            ' '.join(failure_pattern.example_tasks)
        ]).lower()

        for rule_name, rule in EVOLUTION_RULES.items():
            # 키워드 매칭 점수 계산
            match_score = sum(
                1 for kw in rule['keywords']
                if kw.lower() in pattern_text
            )

            if match_score > 0:
                matched_rules.append((rule_name, rule, match_score))

        # 매칭 점수순 정렬
        matched_rules.sort(key=lambda x: (-x[2], -x[1]['priority']))

        # 2. 상위 규칙들의 추가사항 수집
        for rule_name, rule, score in matched_rules[:3]:  # 최대 3개
            addition = rule['addition']

            # 이미 프롬프트에 포함된 내용인지 확인
            if not self._is_already_covered(original_prompt, addition):
                additions.append(addition)

        if not additions:
            return None

        # 3. 진화된 프롬프트 생성
        evolved_prompt = self._build_evolved_prompt(original_prompt, additions)

        # 4. 개선 가설 생성
        hypothesis = self._generate_hypothesis(failure_pattern, matched_rules)

        return PromptEvolution(
            agent_type=agent_type,
            original_prompt=original_prompt,
            evolved_prompt=evolved_prompt,
            evolution_type=EvolutionType.RULE_ADDITION,
            failure_pattern=failure_pattern,
            improvement_hypothesis=hypothesis,
            additions=additions
        )

    def _is_already_covered(self, prompt: str, addition: str) -> bool:
        """프롬프트에 이미 해당 내용이 있는지 확인"""
        prompt_lower = prompt.lower()

        # 핵심 키워드 추출
        key_terms = ['에러', 'error', '검증', 'validation', '엣지', 'edge',
                     '보안', 'security', '성능', 'performance', '테스트', 'test']

        addition_lower = addition.lower()
        for term in key_terms:
            if term in addition_lower and term in prompt_lower:
                return True

        return False

    def _build_evolved_prompt(self, original: str, additions: List[str]) -> str:
        """진화된 프롬프트 구성"""
        if not additions:
            return original

        # 기존 프롬프트에 주의사항 섹션 추가
        additions_text = "\n".join(f"- {a}" for a in additions)

        evolved = f"""{original}

## 주의사항 (학습된 규칙)
{additions_text}"""

        return evolved

    def _generate_hypothesis(
        self,
        pattern: FailurePattern,
        matched_rules: List[Tuple]
    ) -> str:
        """개선 가설 생성"""
        rule_names = [r[0] for r in matched_rules[:3]]

        hypothesis = (
            f"'{pattern.task_type}' 유형에서 {pattern.count}번 실패 발생. "
            f"분석 결과 {', '.join(rule_names)} 관련 문제로 추정. "
            f"해당 주의사항을 프롬프트에 추가하면 성공률 개선 예상."
        )

        return hypothesis


class StrategyAdapter:
    """
    전략 적응기

    전략별 효과성을 분석하고 가중치 조정
    """

    def __init__(self, supabase_client=None):
        self.db = supabase_client

    async def analyze_strategy_effectiveness(self) -> Dict[str, float]:
        """전략별 효과성 분석"""
        if not self.db:
            return {}

        result = await self.db.table('strategy_effectiveness').select('*').execute()

        effectiveness = {}
        for strategy in result.data or []:
            name = strategy['strategy_name']
            score = strategy.get('effectiveness_score', 0.5)
            effectiveness[name] = score

        return effectiveness

    async def suggest_weight_adjustments(self) -> List[Dict[str, Any]]:
        """가중치 조정 제안"""
        effectiveness = await self.analyze_strategy_effectiveness()

        adjustments = []
        for strategy_name, score in effectiveness.items():
            if score > 0.7:
                # 효과적인 전략: 가중치 증가 제안
                adjustments.append({
                    'strategy_name': strategy_name,
                    'current_score': score,
                    'recommendation': 'increase_weight',
                    'reason': f'효과성 점수 {score:.2f}로 높음'
                })
            elif score < 0.3:
                # 비효과적인 전략: 가중치 감소 제안
                adjustments.append({
                    'strategy_name': strategy_name,
                    'current_score': score,
                    'recommendation': 'decrease_weight',
                    'reason': f'효과성 점수 {score:.2f}로 낮음'
                })

        return adjustments

    async def apply_weight_adjustment(
        self,
        strategy_name: str,
        adjustment: float,
        reason: str
    ) -> bool:
        """가중치 조정 적용"""
        if not self.db:
            return False

        # 현재 가중치 조회 (effectiveness_score 사용)
        result = await self.db.table('strategy_effectiveness').select(
            'effectiveness_score'
        ).eq('strategy_name', strategy_name).single().execute()

        if not result.data:
            return False

        current_weight = result.data['effectiveness_score']
        new_weight = max(0.0, min(1.0, current_weight + adjustment))

        # 조정 이력 기록
        await self.db.table('strategy_weight_history').insert({
            'strategy_name': strategy_name,
            'weight_before': current_weight,
            'weight_after': new_weight,
            'adjustment_reason': reason
        }).execute()

        # 새 가중치 적용
        await self.db.table('strategy_effectiveness').update({
            'effectiveness_score': new_weight,
            'updated_at': datetime.now().isoformat()
        }).eq('strategy_name', strategy_name).execute()

        return True


class EvolutionEngine:
    """
    Self-Evolution Engine (메인 클래스)

    실수에서 배워서 프롬프트와 전략을 자동 개선

    Usage:
        engine = EvolutionEngine(supabase_client)

        # 실패 분석
        patterns = await engine.analyze_recent_failures()

        # 프롬프트 진화 제안
        for pattern in patterns:
            evolution = await engine.suggest_prompt_improvement(pattern)
            if evolution:
                await engine.save_evolution(evolution)

        # 실험 실행 및 결과 기록
        result = await engine.run_experiment(evolution_id, experience)

        # 채택/롤백 결정
        await engine.evaluate_and_decide(evolution_id)
    """

    EXPERIMENT_THRESHOLD = 5  # 결정에 필요한 최소 실험 수
    SUCCESS_RATE_THRESHOLD = 0.6  # 채택을 위한 최소 성공률
    IMPROVEMENT_THRESHOLD = 0.1  # 채택을 위한 최소 개선율

    def __init__(self, supabase_client=None):
        self.db = supabase_client
        self.failure_detector = FailurePatternDetector(supabase_client)
        self.prompt_evolver = PromptEvolver(supabase_client)
        self.strategy_adapter = StrategyAdapter(supabase_client)

    async def analyze_recent_failures(
        self,
        window_hours: int = 24
    ) -> List[FailurePattern]:
        """
        최근 실패 분석

        Args:
            window_hours: 분석할 시간 범위

        Returns:
            발견된 실패 패턴 목록
        """
        if not self.db:
            return []

        # 최근 경험 조회
        cutoff = (datetime.now() - timedelta(hours=window_hours)).isoformat()
        result = await self.db.table('experiences').select(
            'id, task, task_type, output, success, created_at'
        ).gte('created_at', cutoff).execute()

        experiences = result.data or []

        # 패턴 분석
        patterns = await self.failure_detector.analyze_failures(
            experiences, window_hours
        )

        # 인사이트 저장
        for pattern in patterns:
            await self._save_insight(pattern)

        return patterns

    async def _save_insight(self, pattern: FailurePattern):
        """인사이트 저장"""
        if not self.db:
            return

        await self.db.table('self_reflection_insights').insert({
            'insight_type': 'failure_pattern',
            'insight_text': pattern.description,
            'supporting_experiences': pattern.experience_ids,
            'confidence': min(0.9, 0.3 + pattern.count * 0.1),  # 횟수에 따라 신뢰도 증가
        }).execute()

    async def suggest_prompt_improvement(
        self,
        pattern: FailurePattern,
        agent_type: str = 'baby',
        current_prompt: str = ""
    ) -> Optional[PromptEvolution]:
        """
        실패 패턴 기반 프롬프트 개선 제안

        Args:
            pattern: 실패 패턴
            agent_type: 에이전트 유형
            current_prompt: 현재 프롬프트

        Returns:
            프롬프트 진화 제안
        """
        if not current_prompt:
            current_prompt = await self._get_current_prompt(agent_type)

        evolution = self.prompt_evolver.evolve_prompt(
            current_prompt, pattern, agent_type
        )

        return evolution

    async def _get_current_prompt(self, agent_type: str) -> str:
        """현재 활성 프롬프트 조회"""
        # 학습된 규칙들을 조합하여 현재 프롬프트 구성
        if not self.db:
            return ""

        result = await self.db.table('learned_prompt_rules').select(
            'rule_text'
        ).eq('agent_type', agent_type).eq('is_active', True).order(
            'priority', desc=True
        ).execute()

        rules = [r['rule_text'] for r in result.data or []]

        if not rules:
            return ""

        prompt = "## 기본 지침\n" + "\n".join(f"- {r}" for r in rules)
        return prompt

    async def save_evolution(self, evolution: PromptEvolution) -> Optional[str]:
        """진화 제안 저장"""
        if not self.db:
            return None

        # 기존 baseline 성공률 계산
        baseline = await self._calculate_baseline_success_rate(
            evolution.agent_type,
            evolution.failure_pattern.task_type
        )

        result = await self.db.table('prompt_evolution').insert({
            'agent_type': evolution.agent_type,
            'original_prompt': evolution.original_prompt,
            'evolved_prompt': evolution.evolved_prompt,
            'evolution_type': evolution.evolution_type.value,
            'trigger_experience_id': (
                evolution.failure_pattern.experience_ids[0]
                if evolution.failure_pattern.experience_ids else None
            ),
            'failure_pattern': evolution.failure_pattern.description,
            'improvement_hypothesis': evolution.improvement_hypothesis,
            'baseline_success_rate': baseline,
        }).execute()

        return result.data[0]['id'] if result.data else None

    async def _calculate_baseline_success_rate(
        self,
        agent_type: str,
        task_type: str
    ) -> float:
        """baseline 성공률 계산"""
        if not self.db:
            return 0.5

        # 최근 100개 경험에서 성공률 계산
        result = await self.db.table('experiences').select(
            'success'
        ).eq('task_type', task_type).order(
            'created_at', desc=True
        ).limit(100).execute()

        if not result.data:
            return 0.5

        successes = sum(1 for e in result.data if e.get('success'))
        return successes / len(result.data)

    async def run_experiment(
        self,
        evolution_id: str,
        experience_id: str,
        success: bool,
        variant: str = 'treatment',  # 'control' or 'treatment'
        quality_score: float = 0.5,
        latency_ms: int = 0
    ) -> Dict[str, Any]:
        """
        진화 실험 실행 및 결과 기록

        Args:
            evolution_id: 진화 ID
            experience_id: 경험 ID
            success: 성공 여부
            variant: 실험 변형 ('control'=원본, 'treatment'=진화)
            quality_score: 품질 점수
            latency_ms: 응답 시간

        Returns:
            실험 결과
        """
        if not self.db:
            return {'success': False, 'error': 'No database connection'}

        # 실험 결과 기록
        result = await self.db.table('evolution_experiments').insert({
            'evolution_id': evolution_id,
            'experiment_type': 'a_b_test',
            'variant': variant,
            'experience_id': experience_id,
            'success': success,
            'quality_score': quality_score,
            'latency_ms': latency_ms,
        }).execute()

        # 진화의 실험 카운트 증가
        await self.db.rpc('increment_experiment_count', {
            'evo_id': evolution_id
        }).execute()

        # 또는 직접 업데이트
        evolution = await self.db.table('prompt_evolution').select(
            'experiment_count'
        ).eq('id', evolution_id).single().execute()

        if evolution.data:
            new_count = evolution.data['experiment_count'] + 1
            await self.db.table('prompt_evolution').update({
                'experiment_count': new_count
            }).eq('id', evolution_id).execute()

        return {
            'success': True,
            'experiment_id': result.data[0]['id'] if result.data else None,
            'variant': variant
        }

    async def evaluate_and_decide(self, evolution_id: str) -> Dict[str, Any]:
        """
        진화 평가 및 채택/롤백 결정

        Args:
            evolution_id: 진화 ID

        Returns:
            결정 결과 {'decision': 'adopt'|'rollback'|'continue', 'reason': ...}
        """
        if not self.db:
            return {'decision': 'continue', 'reason': 'No database connection'}

        # 실험 결과 조회
        experiments = await self.db.table('evolution_experiments').select(
            '*'
        ).eq('evolution_id', evolution_id).execute()

        if not experiments.data:
            return {'decision': 'continue', 'reason': 'No experiments yet'}

        # treatment 그룹 통계
        treatment_exps = [e for e in experiments.data if e['variant'] == 'treatment']
        control_exps = [e for e in experiments.data if e['variant'] == 'control']

        if len(treatment_exps) < self.EXPERIMENT_THRESHOLD:
            return {
                'decision': 'continue',
                'reason': f'Need more experiments ({len(treatment_exps)}/{self.EXPERIMENT_THRESHOLD})'
            }

        # 성공률 계산
        treatment_success_rate = (
            sum(1 for e in treatment_exps if e['success']) / len(treatment_exps)
        )

        control_success_rate = (
            sum(1 for e in control_exps if e['success']) / len(control_exps)
            if control_exps else 0.5
        )

        # 결정
        improvement = treatment_success_rate - control_success_rate

        if treatment_success_rate >= self.SUCCESS_RATE_THRESHOLD and improvement >= self.IMPROVEMENT_THRESHOLD:
            # 채택
            await self._adopt_evolution(evolution_id, treatment_success_rate, improvement)
            return {
                'decision': 'adopt',
                'reason': f'Treatment success rate: {treatment_success_rate:.2%}, improvement: {improvement:.2%}',
                'treatment_success_rate': treatment_success_rate,
                'improvement': improvement
            }
        elif treatment_success_rate < 0.3 or improvement < -0.1:
            # 롤백
            await self._rollback_evolution(
                evolution_id,
                f'Poor performance: {treatment_success_rate:.2%} success, {improvement:.2%} change'
            )
            return {
                'decision': 'rollback',
                'reason': f'Treatment underperformed: {treatment_success_rate:.2%} success',
                'treatment_success_rate': treatment_success_rate,
                'improvement': improvement
            }
        else:
            # 더 많은 실험 필요
            return {
                'decision': 'continue',
                'reason': f'Inconclusive: {treatment_success_rate:.2%} success, {improvement:.2%} change',
                'treatment_success_rate': treatment_success_rate,
                'improvement': improvement
            }

    async def _adopt_evolution(
        self,
        evolution_id: str,
        success_rate: float,
        improvement: float
    ):
        """진화 채택"""
        if not self.db:
            return

        # 진화 정보 조회
        evolution = await self.db.table('prompt_evolution').select(
            '*'
        ).eq('id', evolution_id).single().execute()

        if not evolution.data:
            return

        evo_data = evolution.data

        # 진화 테이블 업데이트
        await self.db.table('prompt_evolution').update({
            'was_adopted': True,
            'post_evolution_success_rate': success_rate,
            'adoption_reason': f'Improvement of {improvement:.2%} over baseline',
            'adopted_at': datetime.now().isoformat()
        }).eq('id', evolution_id).execute()

        # 학습된 규칙으로 저장
        # 진화된 프롬프트에서 추가된 규칙 추출 및 저장
        await self._save_learned_rules(evo_data, evolution_id)

        # 인사이트 업데이트
        await self.db.table('self_reflection_insights').update({
            'applied_to_prompt_id': evolution_id,
            'outcome_after_apply': 'improved',
            'action_taken': f'Adopted with {success_rate:.2%} success rate'
        }).eq('insight_text', evo_data['failure_pattern']).execute()

    async def _save_learned_rules(self, evolution_data: Dict, evolution_id: str):
        """학습된 규칙 저장"""
        if not self.db:
            return

        # 진화된 프롬프트에서 새 규칙 추출
        evolved_prompt = evolution_data['evolved_prompt']
        agent_type = evolution_data['agent_type']

        # "주의사항" 섹션에서 규칙 추출
        match = re.search(r'## 주의사항.*?\n([\s\S]*?)(?=\n##|$)', evolved_prompt)
        if not match:
            return

        rules_text = match.group(1)
        rules = re.findall(r'- (.+)', rules_text)

        for i, rule_text in enumerate(rules):
            rule_name = f"evolved_{evolution_id[:8]}_{i}"

            try:
                await self.db.table('learned_prompt_rules').upsert({
                    'agent_type': agent_type,
                    'rule_name': rule_name,
                    'rule_type': 'always',
                    'rule_text': rule_text.strip(),
                    'priority': 75,
                    'source_evolution_id': evolution_id,
                    'is_active': True
                }, on_conflict='agent_type,rule_name').execute()
            except Exception:
                pass  # 중복 규칙 무시

    async def _rollback_evolution(self, evolution_id: str, reason: str):
        """진화 롤백"""
        if not self.db:
            return

        await self.db.table('prompt_evolution').update({
            'was_adopted': False,
            'rollback_reason': reason
        }).eq('id', evolution_id).execute()

        # 관련 규칙 비활성화
        await self.db.table('learned_prompt_rules').update({
            'is_active': False
        }).eq('source_evolution_id', evolution_id).execute()

    async def get_evolution_stats(self) -> Dict[str, Any]:
        """진화 통계 조회"""
        if not self.db:
            return {}

        # 전체 진화 수
        total = await self.db.table('prompt_evolution').select(
            'id', count='exact'
        ).execute()

        # 채택된 진화 수
        adopted = await self.db.table('prompt_evolution').select(
            'id', count='exact'
        ).eq('was_adopted', True).execute()

        # 롤백된 진화 수
        rollback = await self.db.table('prompt_evolution').select(
            'id', count='exact'
        ).is_('rollback_reason', 'not.null').execute()

        # 활성 규칙 수
        active_rules = await self.db.table('learned_prompt_rules').select(
            'id', count='exact'
        ).eq('is_active', True).execute()

        return {
            'total_evolutions': total.count or 0,
            'adopted_evolutions': adopted.count or 0,
            'rollback_evolutions': rollback.count or 0,
            'active_learned_rules': active_rules.count or 0,
            'adoption_rate': (
                (adopted.count or 0) / max(1, total.count or 1)
            )
        }

    async def get_active_prompt(self, agent_type: str) -> str:
        """현재 활성 프롬프트 조합"""
        if not self.db:
            return ""

        # 활성 규칙 조회 (우선순위순)
        result = await self.db.table('learned_prompt_rules').select(
            'rule_name, rule_text, rule_type, priority'
        ).eq('agent_type', agent_type).eq('is_active', True).order(
            'priority', desc=True
        ).execute()

        if not result.data:
            return ""

        always_rules = [r for r in result.data if r['rule_type'] == 'always']
        conditional_rules = [r for r in result.data if r['rule_type'] == 'conditional']

        prompt_parts = []

        if always_rules:
            prompt_parts.append("## 필수 규칙")
            for rule in always_rules:
                prompt_parts.append(f"- {rule['rule_text']}")

        if conditional_rules:
            prompt_parts.append("\n## 상황별 규칙")
            for rule in conditional_rules:
                prompt_parts.append(f"- {rule['rule_text']}")

        return "\n".join(prompt_parts)


# 편의 함수
async def create_evolution_engine(supabase_url: str = None, supabase_key: str = None):
    """EvolutionEngine 생성 헬퍼"""
    from supabase import create_client, Client
    import os

    url = supabase_url or os.getenv('SUPABASE_URL')
    key = supabase_key or os.getenv('SUPABASE_ANON_KEY')

    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_ANON_KEY required")

    client: Client = create_client(url, key)
    return EvolutionEngine(client)
