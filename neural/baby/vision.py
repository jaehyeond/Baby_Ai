"""
VisionProcessor - 시각 처리 시스템

Phase 4.1: Camera Input
- 이미지 입력 처리
- 장면 설명 생성
- 객체 감지
- 시각적 경험 생성

Gemini Vision API를 사용하여 멀티모달 처리
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Any
from enum import Enum
import base64
import uuid


class VisualSource(Enum):
    """이미지 소스"""
    CAMERA = "camera"      # 실시간 카메라
    UPLOAD = "upload"      # 파일 업로드
    SCREENSHOT = "screenshot"  # 스크린샷
    GENERATED = "generated"    # AI 생성


@dataclass
class VisualInput:
    """시각 입력 데이터"""
    image_data: bytes           # 이미지 바이너리 데이터
    mime_type: str             # image/jpeg, image/png, image/webp
    source: VisualSource       # 이미지 소스
    timestamp: datetime = field(default_factory=datetime.now)

    # 메타데이터
    width: int = 0
    height: int = 0
    file_size: int = 0

    def __post_init__(self):
        if not self.file_size:
            self.file_size = len(self.image_data)

    def to_base64(self) -> str:
        """Base64 인코딩"""
        return base64.b64encode(self.image_data).decode('utf-8')

    @classmethod
    def from_base64(cls, data: str, mime_type: str, source: VisualSource = VisualSource.UPLOAD) -> "VisualInput":
        """Base64에서 생성"""
        return cls(
            image_data=base64.b64decode(data),
            mime_type=mime_type,
            source=source,
        )


@dataclass
class DetectedObject:
    """감지된 객체"""
    name: str                  # 객체 이름
    category: str             # 카테고리 (person, animal, object 등)
    confidence: float         # 신뢰도 (0.0 ~ 1.0)
    properties: dict = field(default_factory=dict)  # 추가 속성
    bounding_box: dict = None  # 바운딩 박스 (x, y, width, height)


@dataclass
class VisualExperience:
    """시각적 경험"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # 입력 정보
    image_url: str = ""           # Storage URL
    description: str = ""         # 장면 설명

    # 분석 결과
    objects_detected: list[DetectedObject] = field(default_factory=list)
    scene_type: str = ""          # indoor, outdoor, nature 등
    dominant_colors: list[str] = field(default_factory=list)

    # 감정 반응
    emotional_response: dict = field(default_factory=dict)
    curiosity_triggered: float = 0.0

    # 메타데이터
    development_stage: int = 0
    confidence: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)

    # DB 연동
    db_id: str = None
    experience_id: str = None     # experiences 테이블 참조
    media_file_id: str = None     # media_files 테이블 참조

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "image_url": self.image_url,
            "description": self.description,
            "objects_detected": [
                {
                    "name": obj.name,
                    "category": obj.category,
                    "confidence": obj.confidence,
                    "properties": obj.properties,
                }
                for obj in self.objects_detected
            ],
            "scene_type": self.scene_type,
            "dominant_colors": self.dominant_colors,
            "emotional_response": self.emotional_response,
            "curiosity_triggered": self.curiosity_triggered,
            "development_stage": self.development_stage,
            "confidence": self.confidence,
            "timestamp": self.timestamp.isoformat(),
        }


class VisionProcessor:
    """
    시각 처리기

    Gemini Vision API를 사용하여:
    1. 이미지 설명 생성
    2. 객체 감지
    3. 장면 분류
    4. 감정 반응 생성
    """

    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self._llm_client = None
        self._db = None
        self._storage = None

    def _get_llm_client(self):
        """LLM 클라이언트 (lazy init)"""
        if self._llm_client is None:
            from .llm_client import get_llm_client
            self._llm_client = get_llm_client()
        return self._llm_client

    def _get_db(self):
        """DB 클라이언트 (lazy init)"""
        if self._db is None:
            try:
                from .db import get_brain_db
                self._db = get_brain_db()
            except Exception as e:
                if self.verbose:
                    print(f"[Vision] DB 연결 실패: {e}")
        return self._db

    def _get_storage(self):
        """Supabase Storage 클라이언트 (lazy init)"""
        if self._storage is None:
            try:
                from .db import get_supabase_client
                client = get_supabase_client()
                self._storage = client.storage
            except Exception as e:
                if self.verbose:
                    print(f"[Vision] Storage 연결 실패: {e}")
        return self._storage

    async def process_image(
        self,
        visual_input: VisualInput,
        development_stage: int = 0,
        emotional_state: dict = None,
    ) -> VisualExperience:
        """
        이미지 처리 메인 파이프라인

        1. 이미지 → Storage 업로드
        2. Gemini Vision으로 장면 설명
        3. 객체 감지
        4. 시각적 경험 생성
        5. DB 저장
        """
        if self.verbose:
            print(f"[Vision] Processing image ({visual_input.file_size} bytes, {visual_input.mime_type})")

        # 1. Storage 업로드
        image_url = await self._upload_to_storage(visual_input)

        # 2. 장면 설명 생성
        description = await self.describe_scene(visual_input.image_data)

        # 3. 객체 감지
        objects = await self.detect_objects(visual_input.image_data)

        # 4. 장면 유형 분류
        scene_type = self._classify_scene(description, objects)

        # 5. 감정 반응 생성 (발달 단계에 따라 다름)
        emotional_response = self._generate_emotional_response(
            description=description,
            objects=objects,
            development_stage=development_stage,
            current_emotions=emotional_state,
        )

        # 6. 시각적 경험 생성
        visual_exp = VisualExperience(
            image_url=image_url,
            description=description,
            objects_detected=objects,
            scene_type=scene_type,
            emotional_response=emotional_response,
            curiosity_triggered=emotional_response.get("curiosity_change", 0.0),
            development_stage=development_stage,
            confidence=self._calculate_confidence(objects),
        )

        # 7. DB 저장
        visual_exp = await self._save_to_db(visual_exp, visual_input)

        if self.verbose:
            print(f"[Vision] Processed: {scene_type} scene, {len(objects)} objects detected")

        return visual_exp

    async def describe_scene(self, image_data: bytes) -> str:
        """
        이미지 장면 설명 생성

        Gemini Vision API로 자연어 설명 생성
        """
        client = self._get_llm_client()

        prompt = """이 이미지를 보고 아기가 이해할 수 있을 정도로 간단하게 설명해주세요.

다음 내용을 포함해주세요:
1. 전체적인 장면 (무엇이 보이는지)
2. 주요 객체들 (사람, 동물, 물건 등)
3. 분위기나 느낌 (밝은지, 어두운지, 즐거운지 등)

설명은 2-3문장으로 간결하게 작성해주세요."""

        try:
            # 멀티모달 생성 호출
            description = client.generate_multimodal(
                prompt=prompt,
                images=[image_data],
                model_key="gemini-2-flash",
            )
            return description.strip()
        except Exception as e:
            if self.verbose:
                print(f"[Vision] Scene description failed: {e}")
            return "이미지를 설명할 수 없습니다."

    async def detect_objects(self, image_data: bytes) -> list[DetectedObject]:
        """
        이미지에서 객체 감지

        Gemini Vision API로 객체 목록 추출
        """
        client = self._get_llm_client()

        prompt = """이 이미지에서 보이는 모든 객체를 나열해주세요.

각 객체에 대해 다음 형식으로 작성해주세요:
- 이름: [객체 이름]
- 카테고리: [person/animal/object/nature/vehicle/food/other]
- 확신도: [high/medium/low]

예시:
- 이름: 강아지
- 카테고리: animal
- 확신도: high

최대 10개의 객체까지만 나열해주세요."""

        try:
            response = client.generate_multimodal(
                prompt=prompt,
                images=[image_data],
                model_key="gemini-2-flash",
            )

            # 응답 파싱
            objects = self._parse_objects_response(response)
            return objects

        except Exception as e:
            if self.verbose:
                print(f"[Vision] Object detection failed: {e}")
            return []

    def _parse_objects_response(self, response: str) -> list[DetectedObject]:
        """객체 감지 응답 파싱"""
        objects = []

        # 간단한 파싱 로직
        lines = response.strip().split('\n')
        current_obj = {}

        for line in lines:
            line = line.strip()
            if line.startswith('- 이름:'):
                if current_obj.get('name'):
                    objects.append(self._create_detected_object(current_obj))
                    current_obj = {}
                current_obj['name'] = line.replace('- 이름:', '').strip()
            elif line.startswith('- 카테고리:'):
                current_obj['category'] = line.replace('- 카테고리:', '').strip()
            elif line.startswith('- 확신도:'):
                confidence_text = line.replace('- 확신도:', '').strip().lower()
                current_obj['confidence'] = {
                    'high': 0.9,
                    'medium': 0.7,
                    'low': 0.4,
                }.get(confidence_text, 0.5)

        # 마지막 객체 추가
        if current_obj.get('name'):
            objects.append(self._create_detected_object(current_obj))

        return objects

    def _create_detected_object(self, obj_dict: dict) -> DetectedObject:
        """DetectedObject 생성"""
        return DetectedObject(
            name=obj_dict.get('name', 'unknown'),
            category=obj_dict.get('category', 'other'),
            confidence=obj_dict.get('confidence', 0.5),
            properties={},
        )

    def _classify_scene(self, description: str, objects: list[DetectedObject]) -> str:
        """장면 유형 분류"""
        description_lower = description.lower()

        # 키워드 기반 분류
        if any(word in description_lower for word in ['실내', '방', '집', 'indoor', 'room', 'house']):
            return 'indoor'
        elif any(word in description_lower for word in ['실외', '밖', '공원', 'outdoor', 'park', 'street']):
            return 'outdoor'
        elif any(word in description_lower for word in ['자연', '나무', '숲', 'nature', 'tree', 'forest']):
            return 'nature'
        elif any(word in description_lower for word in ['사람', '얼굴', 'person', 'face', 'people']):
            return 'social'
        else:
            return 'unknown'

    def _generate_emotional_response(
        self,
        description: str,
        objects: list[DetectedObject],
        development_stage: int,
        current_emotions: dict = None,
    ) -> dict:
        """감정 반응 생성"""
        response = {
            "curiosity_change": 0.0,
            "joy_change": 0.0,
            "fear_change": 0.0,
            "surprise_change": 0.0,
        }

        # 새로운 객체 → 호기심 증가
        num_objects = len(objects)
        if num_objects > 0:
            response["curiosity_change"] = min(0.3, num_objects * 0.05)

        # 사람/동물 → 기쁨 증가 (사회적 자극)
        has_person = any(obj.category == 'person' for obj in objects)
        has_animal = any(obj.category == 'animal' for obj in objects)
        if has_person or has_animal:
            response["joy_change"] = 0.15

        # 발달 단계가 높을수록 복잡한 반응
        if development_stage >= 2:
            # 새로운 것에 대한 놀람
            response["surprise_change"] = min(0.2, num_objects * 0.03)

        return response

    def _calculate_confidence(self, objects: list[DetectedObject]) -> float:
        """전체 신뢰도 계산"""
        if not objects:
            return 0.5

        avg_confidence = sum(obj.confidence for obj in objects) / len(objects)
        return round(avg_confidence, 2)

    async def _upload_to_storage(self, visual_input: VisualInput) -> str:
        """이미지를 Supabase Storage에 업로드"""
        storage = self._get_storage()
        if not storage:
            return ""

        try:
            # 파일명 생성
            ext = visual_input.mime_type.split('/')[-1]
            filename = f"visual/{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.{ext}"

            # 업로드
            storage.from_("media").upload(
                file=visual_input.image_data,
                path=filename,
                file_options={"content-type": visual_input.mime_type}
            )

            # Public URL 생성
            url_response = storage.from_("media").get_public_url(filename)
            return url_response

        except Exception as e:
            if self.verbose:
                print(f"[Vision] Storage upload failed: {e}")
            return ""

    async def _save_to_db(self, visual_exp: VisualExperience, visual_input: VisualInput) -> VisualExperience:
        """시각적 경험을 DB에 저장"""
        db = self._get_db()
        if not db:
            return visual_exp

        try:
            # media_files 테이블에 저장
            media_result = db.client.table("media_files").insert({
                "storage_path": visual_exp.image_url,
                "bucket_name": "media",
                "mime_type": visual_input.mime_type,
                "file_size": visual_input.file_size,
            }).execute()

            if media_result.data:
                visual_exp.media_file_id = media_result.data[0]["id"]

            # visual_experiences 테이블에 저장
            visual_result = db.client.table("visual_experiences").insert({
                "image_url": visual_exp.image_url,
                "description": visual_exp.description,
                "objects_detected": [obj.__dict__ for obj in visual_exp.objects_detected],
                "scene_type": visual_exp.scene_type,
                "emotional_response": visual_exp.emotional_response,
                "development_stage": visual_exp.development_stage,
                "confidence": visual_exp.confidence,
                "media_file_id": visual_exp.media_file_id,
            }).execute()

            if visual_result.data:
                visual_exp.db_id = visual_result.data[0]["id"]

        except Exception as e:
            if self.verbose:
                print(f"[Vision] DB save failed: {e}")

        return visual_exp

    def get_stats(self) -> dict:
        """통계 조회"""
        db = self._get_db()
        if not db:
            return {"visual_experiences": 0}

        try:
            result = db.client.table("visual_experiences").select("id", count="exact").execute()
            return {"visual_experiences": result.count or 0}
        except:
            return {"visual_experiences": 0}


# 싱글톤 인스턴스
_vision_processor: Optional[VisionProcessor] = None


def get_vision_processor() -> VisionProcessor:
    """VisionProcessor 싱글톤"""
    global _vision_processor
    if _vision_processor is None:
        _vision_processor = VisionProcessor()
    return _vision_processor
