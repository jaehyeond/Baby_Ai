"""
Baby AI API Server

FastAPI 서버로 Baby AI의 기능을 외부에 노출합니다.
Phase 4: Vision, Audio, Speech endpoints
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import base64
import uvicorn

from .substrate import get_substrate
from .vision import VisualInput, VisualSource, get_vision_processor


app = FastAPI(
    title="Baby AI API",
    description="Baby AI Backend API for multimodal processing",
    version="0.4.0",
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 개발 환경용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# === Request/Response Models ===

class VisionProcessRequest(BaseModel):
    """이미지 처리 요청"""
    image_data: str  # Base64 encoded
    mime_type: str = "image/jpeg"
    prompt: Optional[str] = None


class VisionProcessResponse(BaseModel):
    """이미지 처리 응답"""
    visual_experience: dict
    emotional_changes: dict
    success: bool
    message: Optional[str] = None


class ProcessRequest(BaseModel):
    """일반 처리 요청"""
    task: str
    context: Optional[dict] = None


class ProcessResponse(BaseModel):
    """일반 처리 응답"""
    output: str
    success: bool
    emotional_state: dict
    development_stage: int


class StateResponse(BaseModel):
    """상태 조회 응답"""
    emotional_state: dict
    development_stage: int
    experience_count: int
    capabilities: list[str]


# === Health Check ===

@app.get("/health")
async def health_check():
    """서버 상태 확인"""
    return {"status": "healthy", "version": "0.4.0"}


# === Vision Endpoints (Phase 4.1) ===

@app.post("/api/vision/process", response_model=VisionProcessResponse)
async def process_vision(request: VisionProcessRequest):
    """
    이미지 처리 엔드포인트

    - Base64 인코딩된 이미지 수신
    - VisionProcessor로 장면 분석
    - VisualExperience 반환
    """
    try:
        # Base64 디코딩
        image_data = base64.b64decode(request.image_data)

        # VisualInput 생성
        visual_input = VisualInput(
            image_data=image_data,
            mime_type=request.mime_type,
            source=VisualSource.UPLOAD,
        )

        # Substrate로 처리
        substrate = get_substrate()
        result = await substrate.process_image(image_data, request.prompt)

        if result.visual_experience:
            return VisionProcessResponse(
                visual_experience=result.visual_experience.to_dict(),
                emotional_changes=result.visual_experience.emotional_response,
                success=result.success,
                message="Image processed successfully",
            )
        else:
            return VisionProcessResponse(
                visual_experience={},
                emotional_changes={},
                success=False,
                message=result.output or "Failed to process image",
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/vision/stats")
async def get_vision_stats():
    """시각 처리 통계"""
    try:
        processor = get_vision_processor()
        stats = processor.get_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# === General Processing Endpoints ===

@app.post("/api/process", response_model=ProcessResponse)
async def process_task(request: ProcessRequest):
    """
    일반 작업 처리 엔드포인트
    """
    try:
        substrate = get_substrate()
        result = await substrate.process(request.task, request.context)

        return ProcessResponse(
            output=result.output,
            success=result.success,
            emotional_state=result.emotional_state,
            development_stage=result.development_stage,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/state", response_model=StateResponse)
async def get_state():
    """
    Baby AI 상태 조회
    """
    try:
        substrate = get_substrate()
        state = substrate.get_state()

        return StateResponse(
            emotional_state=state.get("emotional_state", {}),
            development_stage=state.get("development_stage", 0),
            experience_count=state.get("experience_count", 0),
            capabilities=state.get("capabilities", []),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# === Server Entry Point ===

def run_server(host: str = "0.0.0.0", port: int = 8000):
    """서버 실행"""
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Baby AI API Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host address")
    parser.add_argument("--port", type=int, default=8000, help="Port number")

    args = parser.parse_args()
    run_server(args.host, args.port)
