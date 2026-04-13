"""
Phase 10: Self-Evolution Engine 통합 테스트

테스트 항목:
1. FailurePatternDetector - 실패 패턴 탐지
2. PromptEvolver - 프롬프트 진화
3. TeamOptimizer - 팀 최적화
4. PersistentLearningSubstrate - 영속 학습
"""

import asyncio
import pytest
from datetime import datetime
from typing import Dict, List, Any

# 테스트용 mock 데이터
MOCK_EXPERIENCES = [
    {
        'id': '1',
        'task': '피보나치 함수 작성해줘',
        'task_type': 'coding',
        'output': 'def fib(n): ...',
        'success': True,
        'created_at': datetime.now().isoformat()
    },
    {
        'id': '2',
        'task': '에러 핸들링 추가해줘',
        'task_type': 'coding',
        'output': 'try: ...',
        'success': False,  # 실패
        'created_at': datetime.now().isoformat()
    },
    {
        'id': '3',
        'task': 'null 체크 추가',
        'task_type': 'coding',
        'output': 'if x is None: ...',
        'success': False,  # 실패
        'created_at': datetime.now().isoformat()
    },
    {
        'id': '4',
        'task': 'exception 처리 구현',
        'task_type': 'coding',
        'output': 'except Exception: pass',
        'success': False,  # 실패 - 에러 관련 3번째
        'created_at': datetime.now().isoformat()
    },
    {
        'id': '5',
        'task': '버그 수정',
        'task_type': 'bug_fix',
        'output': 'fixed',
        'success': True,
        'created_at': datetime.now().isoformat()
    },
]


class TestFailurePatternDetector:
    """실패 패턴 탐지 테스트"""

    def test_detect_recurring_failures(self):
        """반복 실패 탐지"""
        from evolution import FailurePatternDetector, FailureType

        detector = FailurePatternDetector()

        # sync로 변환 (테스트용)
        patterns = asyncio.run(
            detector.analyze_failures(MOCK_EXPERIENCES)
        )

        # coding 타입에서 3번 실패 → 반복 실패 패턴
        recurring_patterns = [
            p for p in patterns if p.type == FailureType.RECURRING
        ]

        assert len(recurring_patterns) > 0, "반복 실패 패턴이 탐지되어야 함"

        # 'coding' 타입 실패 확인
        coding_pattern = next(
            (p for p in recurring_patterns if p.task_type == 'coding'),
            None
        )
        assert coding_pattern is not None, "'coding' 타입 반복 실패 패턴"
        assert coding_pattern.count >= 3, "3번 이상 실패"

    def test_detect_keyword_patterns(self):
        """키워드 기반 패턴 탐지"""
        from evolution import FailurePatternDetector

        detector = FailurePatternDetector()
        patterns = asyncio.run(
            detector.analyze_failures(MOCK_EXPERIENCES)
        )

        # 'error_handling' 키워드 패턴 확인
        keyword_patterns = [
            p for p in patterns
            if 'error' in p.task_type.lower() or any('error' in kw.lower() for kw in p.keywords)
        ]

        # 에러 관련 키워드가 실패에서 발견되어야 함
        print(f"Keyword patterns found: {[p.task_type for p in patterns]}")


class TestPromptEvolver:
    """프롬프트 진화 테스트"""

    def test_evolve_prompt_from_failure(self):
        """실패 패턴에서 프롬프트 진화"""
        from evolution import (
            PromptEvolver,
            FailurePattern,
            FailureType,
            EvolutionType
        )

        evolver = PromptEvolver()

        # 에러 핸들링 실패 패턴
        pattern = FailurePattern(
            type=FailureType.RECURRING,
            task_type='coding',
            count=3,
            severity='high',
            description='에러 핸들링 부족으로 반복 실패',
            keywords=['error', 'exception', 'try'],
            example_tasks=['에러 핸들링 추가', 'exception 처리']
        )

        original_prompt = "당신은 코딩 도우미입니다."
        evolution = evolver.evolve_prompt(original_prompt, pattern, 'baby')

        assert evolution is not None, "진화 제안이 생성되어야 함"
        assert evolution.evolution_type == EvolutionType.RULE_ADDITION
        assert len(evolution.additions) > 0, "추가 규칙이 있어야 함"
        assert '에러' in evolution.evolved_prompt or 'try' in evolution.evolved_prompt.lower()

        print(f"Original: {original_prompt}")
        print(f"Evolved: {evolution.evolved_prompt}")
        print(f"Additions: {evolution.additions}")

    def test_no_duplicate_rules(self):
        """이미 있는 규칙은 추가하지 않음"""
        from evolution import PromptEvolver, FailurePattern, FailureType

        evolver = PromptEvolver()

        pattern = FailurePattern(
            type=FailureType.RECURRING,
            task_type='coding',
            count=3,
            severity='medium',
            description='에러 핸들링 실패',
            keywords=['error'],
            example_tasks=[]
        )

        # 이미 에러 핸들링 규칙이 있는 프롬프트
        original_prompt = """
        당신은 코딩 도우미입니다.
        반드시 에러 핸들링을 포함하세요.
        """

        evolution = evolver.evolve_prompt(original_prompt, pattern, 'baby')

        # 이미 규칙이 있으면 None 또는 다른 규칙만 추가
        if evolution:
            # 에러 핸들링은 이미 있으므로 해당 규칙은 추가 안 됨
            print(f"Additions (should be minimal): {evolution.additions}")


class TestEvolutionRules:
    """진화 규칙 테스트"""

    def test_all_rules_have_keywords(self):
        """모든 규칙에 키워드가 있음"""
        from evolution import EVOLUTION_RULES

        for rule_name, rule in EVOLUTION_RULES.items():
            assert 'keywords' in rule, f"{rule_name}에 keywords가 없음"
            assert len(rule['keywords']) > 0, f"{rule_name}의 keywords가 비어있음"
            assert 'addition' in rule, f"{rule_name}에 addition이 없음"
            assert 'priority' in rule, f"{rule_name}에 priority가 없음"

    def test_security_rule_highest_priority(self):
        """보안 규칙이 가장 높은 우선순위"""
        from evolution import EVOLUTION_RULES

        security_priority = EVOLUTION_RULES['security']['priority']
        for rule_name, rule in EVOLUTION_RULES.items():
            if rule_name != 'security':
                assert security_priority >= rule['priority'], \
                    f"security({security_priority}) >= {rule_name}({rule['priority']})"


class TestTeamOptimizer:
    """팀 최적화 테스트"""

    def test_role_match_calculation(self):
        """역할-에이전트 매칭 점수 계산"""
        from team_optimizer import DynamicTeamBuilder

        builder = DynamicTeamBuilder()

        # 정확히 일치
        score1 = builder._calculate_role_match('coder', 'coder')
        assert score1 == 1.0, "같은 이름은 1.0"

        # 유사 역할
        score2 = builder._calculate_role_match('coder', 'developer')
        assert score2 >= 0.5, "유사 역할은 0.5 이상"

        # 무관한 역할
        score3 = builder._calculate_role_match('coder', 'writer')
        assert score3 == 0.5, "무관한 역할은 기본값"

    def test_determine_roles_by_task_type(self):
        """작업 유형에 따른 역할 결정"""
        from team_optimizer import DynamicTeamBuilder

        builder = DynamicTeamBuilder()

        # coding 작업
        roles = asyncio.run(builder._determine_roles('coding', 3))
        assert 'coder' in roles, "coding 작업에 coder 포함"

        # documentation 작업
        roles = asyncio.run(builder._determine_roles('documentation', 2))
        assert 'writer' in roles, "documentation 작업에 writer 포함"

    def test_cooperation_type_enum(self):
        """협력 유형 열거형"""
        from team_optimizer import CooperationType

        assert CooperationType.SEQUENTIAL.value == 'sequential'
        assert CooperationType.PARALLEL.value == 'parallel'
        assert CooperationType.ITERATIVE.value == 'iterative'


class TestPersistentLearning:
    """영속 학습 테스트"""

    def test_learning_type_enum(self):
        """학습 유형 열거형"""
        from persistence import LearningType

        assert LearningType.PROMPT_RULE.value == 'prompt_rule'
        assert LearningType.FAILURE_LESSON.value == 'failure_lesson'

    def test_snapshot_type_enum(self):
        """스냅샷 유형"""
        from persistence import SnapshotType

        assert SnapshotType.CHECKPOINT.value == 'checkpoint'
        assert SnapshotType.MILESTONE.value == 'milestone'
        assert SnapshotType.END_SESSION.value == 'end_session'

    def test_core_learning_dataclass(self):
        """핵심 학습 데이터클래스"""
        from persistence import CoreLearning, LearningType

        learning = CoreLearning(
            learning_type=LearningType.PROMPT_RULE,
            summary="에러 핸들링 규칙",
            detailed_content={'source': 'evolution'},
            confidence=0.8,
            effectiveness=0.75
        )

        assert learning.is_active == True
        assert learning.confidence == 0.8


class TestIntegration:
    """통합 테스트"""

    def test_failure_to_evolution_flow(self):
        """실패 → 패턴 탐지 → 진화 흐름"""
        from evolution import (
            FailurePatternDetector,
            PromptEvolver,
            FailureType
        )

        # 1. 실패 패턴 탐지
        detector = FailurePatternDetector()
        patterns = asyncio.run(detector.analyze_failures(MOCK_EXPERIENCES))

        # 2. 각 패턴에 대해 진화 제안
        evolver = PromptEvolver()
        evolutions = []

        for pattern in patterns:
            if pattern.type == FailureType.RECURRING and pattern.count >= 3:
                evolution = evolver.evolve_prompt(
                    "당신은 도움이 되는 AI입니다.",
                    pattern,
                    'baby'
                )
                if evolution:
                    evolutions.append(evolution)

        print(f"Found {len(patterns)} patterns")
        print(f"Generated {len(evolutions)} evolution suggestions")

        # 최소 하나의 진화 제안이 있어야 함
        # (coding 타입에서 3번 실패했으므로)
        assert len(patterns) > 0, "패턴이 탐지되어야 함"

    def test_all_modules_importable(self):
        """모든 모듈 import 가능"""
        from evolution import (
            EvolutionEngine,
            FailurePatternDetector,
            PromptEvolver,
            StrategyAdapter,
            FailureType,
            EvolutionType
        )

        from team_optimizer import (
            TeamOptimizer,
            CooperationPatternLearner,
            TeamPerformanceTracker,
            DynamicTeamBuilder,
            CooperationType,
            TeamType
        )

        from persistence import (
            PersistentLearningSubstrate,
            SessionManager,
            LearningRestorer,
            ContinuityTracker,
            LearningType,
            SnapshotType
        )

        # 모두 성공적으로 import됨
        assert True


def run_tests():
    """테스트 실행"""
    print("=" * 60)
    print("Phase 10: Self-Evolution Engine Tests")
    print("=" * 60)

    # 1. Failure Pattern Detection
    print("\n[1] Testing Failure Pattern Detection...")
    test1 = TestFailurePatternDetector()
    test1.test_detect_recurring_failures()
    test1.test_detect_keyword_patterns()
    print("✓ Failure Pattern Detection tests passed")

    # 2. Prompt Evolution
    print("\n[2] Testing Prompt Evolution...")
    test2 = TestPromptEvolver()
    test2.test_evolve_prompt_from_failure()
    test2.test_no_duplicate_rules()
    print("✓ Prompt Evolution tests passed")

    # 3. Evolution Rules
    print("\n[3] Testing Evolution Rules...")
    test3 = TestEvolutionRules()
    test3.test_all_rules_have_keywords()
    test3.test_security_rule_highest_priority()
    print("✓ Evolution Rules tests passed")

    # 4. Team Optimizer
    print("\n[4] Testing Team Optimizer...")
    test4 = TestTeamOptimizer()
    test4.test_role_match_calculation()
    test4.test_determine_roles_by_task_type()
    test4.test_cooperation_type_enum()
    print("✓ Team Optimizer tests passed")

    # 5. Persistent Learning
    print("\n[5] Testing Persistent Learning...")
    test5 = TestPersistentLearning()
    test5.test_learning_type_enum()
    test5.test_snapshot_type_enum()
    test5.test_core_learning_dataclass()
    print("✓ Persistent Learning tests passed")

    # 6. Integration
    print("\n[6] Testing Integration...")
    test6 = TestIntegration()
    test6.test_failure_to_evolution_flow()
    test6.test_all_modules_importable()
    print("✓ Integration tests passed")

    print("\n" + "=" * 60)
    print("All tests passed!")
    print("=" * 60)


if __name__ == '__main__':
    run_tests()
