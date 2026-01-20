"""
Baby Neural Substrate - Developmental AI

아기의 인지 발달을 모방한 AI 시스템
- 백지 상태에서 시작
- 호기심 기반 탐험
- 감정으로 중요성 판단
- 경험에서 학습
- 발달 단계 거침

핵심 컴포넌트:
- EmotionalCore: 기본 감정 (호기심, 기쁨, 두려움, 놀람)
- CuriosityEngine: 내재적 동기 (예측 오류 기반)
- MemorySystem: 기억 시스템 (에피소드/의미/절차)
- DevelopmentStage: 발달 단계 (신생아 → 유아 → 아기 → 걸음마 → 어린이)
- SelfModel: 자아 모델 (능력, 선호, 한계 인식)

저장소:
- Primary: Supabase (pgvector) - Robot_Brain 프로젝트
- Fallback: 로컬 JSON 파일 (.baby_memory/)
"""

from .emotions import (
    EmotionalCore,
    EmotionalState,
    Emotion,
    EmotionType,
)
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
from .development import (
    DevelopmentStage,
    DevelopmentTracker,
    Milestone,
)
from .self_model import (
    SelfModel,
    Capability,
    Preference,
)
from .substrate import (
    BabySubstrate,
    BabyConfig,
)
from .world_model import (
    WorldModel,
    PredictionType,
    SimulationType,
    ImaginationType,
    PredictionResult,
    SimulationResult,
    ImaginationResult,
)
from .emotional_modulator import (
    EmotionalLearningModulator,
    Strategy,
    StrategyDecision,
    LearningAdjustment,
    PatternEvaluation,
)

__all__ = [
    # Emotions
    "EmotionalCore",
    "EmotionalState",
    "Emotion",
    "EmotionType",
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
    # Development
    "DevelopmentStage",
    "DevelopmentTracker",
    "Milestone",
    # Self Model
    "SelfModel",
    "Capability",
    "Preference",
    # Substrate
    "BabySubstrate",
    "BabyConfig",
    # World Model
    "WorldModel",
    "PredictionType",
    "SimulationType",
    "ImaginationType",
    "PredictionResult",
    "SimulationResult",
    "ImaginationResult",
    # Phase 3: Emotional Modulator
    "EmotionalLearningModulator",
    "Strategy",
    "StrategyDecision",
    "LearningAdjustment",
    "PatternEvaluation",
]
