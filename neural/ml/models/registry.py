"""
Model Registry

테스트할 모델의 정확한 HuggingFace repo, 파일명, 실제 크기 정의.
ggml-org 공식 GGUF 변환 사용.

2026-04-13 검증 결과:
- SmolVLM: Q8_0 + F16만 존재 (Q4_K_M 없음)
- SmolVLM은 모델 + mmproj (멀티모달 프로젝터) 2개 파일 필요
- Gemma 3n E2B GGUF: 멀티모달 미지원 ("still working on adding multimodal")
  → Q8_0=4.79GB, 텍스트 전용 → Quest VLM 용도 부적합 → 제외
"""

from neural.ml.config import ModelSpec


# --- SmolVLM 256M (검증된 파일 크기) ---

SMOLVLM_256M_Q8 = ModelSpec(
    name="smolvlm-256m-q8",
    repo_id="ggml-org/SmolVLM-256M-Instruct-GGUF",
    filename="SmolVLM-256M-Instruct-Q8_0.gguf",
    mmproj_filename="mmproj-SmolVLM-256M-Instruct-Q8_0.gguf",
    format="gguf",
    architecture="idefics3",
    expected_params_m=256,
    expected_file_size_mb=175,
    expected_mmproj_size_mb=104,
    quantization="Q8_0",
    license="apache-2.0",
    notes=[
        "최소 VLM, Critical Gate 테스트용",
        "총 RAM 예상: 모델 175MB + mmproj 104MB + 런타임 오버헤드",
    ],
)

SMOLVLM_256M_F16 = ModelSpec(
    name="smolvlm-256m-f16",
    repo_id="ggml-org/SmolVLM-256M-Instruct-GGUF",
    filename="SmolVLM-256M-Instruct-f16.gguf",
    mmproj_filename="mmproj-SmolVLM-256M-Instruct-f16.gguf",
    format="gguf",
    architecture="idefics3",
    expected_params_m=256,
    expected_file_size_mb=328,
    expected_mmproj_size_mb=190,
    quantization="F16",
    license="apache-2.0",
    notes=["Q8 대비 품질 비교용, Quest에선 Q8 권장"],
)

# --- SmolVLM 500M (검증된 파일 크기) ---

SMOLVLM_500M_Q8 = ModelSpec(
    name="smolvlm-500m-q8",
    repo_id="ggml-org/SmolVLM-500M-Instruct-GGUF",
    filename="SmolVLM-500M-Instruct-Q8_0.gguf",
    mmproj_filename="mmproj-SmolVLM-500M-Instruct-Q8_0.gguf",
    format="gguf",
    architecture="idefics3",
    expected_params_m=500,
    expected_file_size_mb=437,
    expected_mmproj_size_mb=109,
    quantization="Q8_0",
    license="apache-2.0",
    notes=["비디오 입력 지원 가능"],
)

SMOLVLM_500M_F16 = ModelSpec(
    name="smolvlm-500m-f16",
    repo_id="ggml-org/SmolVLM-500M-Instruct-GGUF",
    filename="SmolVLM-500M-Instruct-f16.gguf",
    mmproj_filename="mmproj-SmolVLM-500M-Instruct-f16.gguf",
    format="gguf",
    architecture="idefics3",
    expected_params_m=500,
    expected_file_size_mb=820,
    expected_mmproj_size_mb=199,
    quantization="F16",
    license="apache-2.0",
    notes=["Q8 대비 품질 비교용"],
)

# --- Gemma 3n E2B: 제외 사유 기록 ---
# ggml-org/gemma-3n-E2B-it-GGUF (2026-04-13 확인):
#   - "This version does not contain multimodal support. We are still working on adding multimodal."
#   - Q8_0 = 4.79GB, F16 = 8.92GB (텍스트 전용)
#   - 멀티모달 프로젝터(mmproj) 파일 없음
#   - MatFormer 선택적 활성화가 GGUF에서 보존되지 않음 → 4B 풀 로딩
#   - Quest 3S에서 텍스트 전용으로도 4.79GB는 RAM 초과
#   → VLM 벤치마크에서 완전 제외. 멀티모달 GGUF 출시 시 재평가.


# --- 전체 레지스트리 ---

MODEL_REGISTRY: dict[str, ModelSpec] = {
    spec.name: spec for spec in [
        SMOLVLM_256M_Q8,
        SMOLVLM_256M_F16,
        SMOLVLM_500M_Q8,
        SMOLVLM_500M_F16,
    ]
}


def get_model(name: str) -> ModelSpec:
    if name not in MODEL_REGISTRY:
        available = ", ".join(MODEL_REGISTRY.keys())
        raise ValueError(f"Unknown model: {name}. Available: {available}")
    return MODEL_REGISTRY[name]


def list_models() -> list[str]:
    return list(MODEL_REGISTRY.keys())
