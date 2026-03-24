"""
Baby Neural Substrate - Developmental AI

아기의 인지 발달을 모방한 AI 시스템
- 백지 상태에서 시작
- 호기심 기반 탐험
- 감정으로 중요성 판단
- 경험에서 학습
- 발달 단계 거침

핵심 컴포넌트:
- CuriosityEngine: 내재적 동기 (예측 오류 기반)
- MemorySystem: 기억 시스템 (에피소드/의미/절차)
- SelfModel: 자아 모델 (능력, 선호, 한계 인식)

저장소:
- Primary: Neo4j AuraDB (neo4j_db.py)
- Legacy: Supabase (archive/ 디렉토리)
"""

from .curiosity import (
    CuriosityEngine,
    CuriositySignal,
    LearningProgress,
    LearningZone,
)
from .memory import (
    MemorySystem,
    EpisodicMemory,
    SemanticMemory,
    ProceduralMemory,
    Experience,
)
from .self_model import (
    SelfModel,
    Capability,
    Preference,
)
# Phase 4: Vision
from .vision import (
    VisionProcessor,
    VisualInput,
    VisualExperience,
    VisualSource,
    DetectedObject,
    get_vision_processor,
)
# Phase 10: Self-Evolution
from .evolution import (
    EvolutionEngine,
    FailurePatternDetector,
    PromptEvolver,
    StrategyAdapter,
    FailureType,
    EvolutionType,
    InsightType,
    FailurePattern,
    PromptEvolution,
    EVOLUTION_RULES,
)
from .team_optimizer import (
    TeamOptimizer,
    CooperationPatternLearner,
    TeamPerformanceTracker,
    DynamicTeamBuilder,
    CooperationType,
    TeamType,
    AgentRole,
    Team,
    TeamRecommendation,
)
from .persistence import (
    PersistentLearningSubstrate,
    SessionManager,
    LearningRestorer,
    ContinuityTracker,
    LearningType,
    SnapshotType,
    RestoreType,
    LearningSession,
    LearningSnapshot,
    CoreLearning,
    RestorePoint,
)

__all__ = [
    # Curiosity
    "CuriosityEngine",
    "CuriositySignal",
    "LearningProgress",
    "LearningZone",
    # Memory
    "MemorySystem",
    "EpisodicMemory",
    "SemanticMemory",
    "ProceduralMemory",
    "Experience",
    # Self Model
    "SelfModel",
    "Capability",
    "Preference",
    # Phase 4: Vision
    "VisionProcessor",
    "VisualInput",
    "VisualExperience",
    "VisualSource",
    "DetectedObject",
    "get_vision_processor",
    # Phase 10: Self-Evolution
    "EvolutionEngine",
    "FailurePatternDetector",
    "PromptEvolver",
    "StrategyAdapter",
    "FailureType",
    "EvolutionType",
    "InsightType",
    "FailurePattern",
    "PromptEvolution",
    "EVOLUTION_RULES",
    # Phase 10: Team Optimizer
    "TeamOptimizer",
    "CooperationPatternLearner",
    "TeamPerformanceTracker",
    "DynamicTeamBuilder",
    "CooperationType",
    "TeamType",
    "AgentRole",
    "Team",
    "TeamRecommendation",
    # Phase 10: Persistent Learning
    "PersistentLearningSubstrate",
    "SessionManager",
    "LearningRestorer",
    "ContinuityTracker",
    "LearningType",
    "SnapshotType",
    "RestoreType",
    "LearningSession",
    "LearningSnapshot",
    "CoreLearning",
    "RestorePoint",
]
