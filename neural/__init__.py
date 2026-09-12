"""
Neural A2A Framework

Agentic Neural Network (ANN) 기반 멀티에이전트 시스템
- 에이전트 = 뉴런
- A2A 연결 = 시냅스
- 텍스트 피드백 = 그래디언트

참고: arXiv:2506.09046 - Agentic Neural Networks
"""

from importlib import import_module

# Baby's API must not initialize the unrelated Claude agent framework on import.
# Existing public imports remain available, loading their module on first use.
_EXPORTS = {
    **dict.fromkeys(("NeuralLayer", "LayerConfig", "LayerType", "LayerStatus", "AgentNode"), "layer"),
    **dict.fromkeys(("NeuralPipeline", "PipelineConfig", "ForwardResult", "PipelineStatus", "Neuromodulator", "FeedbackStrategy", "create_code_pipeline"), "pipeline"),
    **dict.fromkeys(("NeuralSubstrate", "SubstrateConfig", "AgentResult", "AgentRole", "run_substrate"), "substrate"),
}


def __getattr__(name):
    module = _EXPORTS.get(name)
    if module is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(f".{module}", __name__), name)
    globals()[name] = value
    return value

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
