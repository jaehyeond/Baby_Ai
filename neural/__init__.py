"""
Neural A2A Framework

Agentic Neural Network (ANN) 기반 멀티에이전트 시스템
- 에이전트 = 뉴런
- A2A 연결 = 시냅스
- 텍스트 피드백 = 그래디언트

참고: arXiv:2506.09046 - Agentic Neural Networks
"""

from .layer import (
    NeuralLayer,
    LayerConfig,
    LayerType,
    LayerStatus,
    AgentNode,
)
from .pipeline import (
    NeuralPipeline,
    PipelineConfig,
    ForwardResult,
    PipelineStatus,
    Neuromodulator,
    FeedbackStrategy,
    create_code_pipeline,
)
from .substrate import (
    NeuralSubstrate,
    SubstrateConfig,
    AgentResult,
    AgentRole,
    run_substrate,
)

__all__ = [
    # Layer
    "NeuralLayer",
    "LayerConfig",
    "LayerType",
    "LayerStatus",
    "AgentNode",
    # Pipeline
    "NeuralPipeline",
    "PipelineConfig",
    "ForwardResult",
    "PipelineStatus",
    "Neuromodulator",
    "FeedbackStrategy",
    "create_code_pipeline",
    # Substrate (In-Process Execution)
    "NeuralSubstrate",
    "SubstrateConfig",
    "AgentResult",
    "AgentRole",
    "run_substrate",
]
