"""
Test Image Preparation

Baby AI Quest 3S 물리세계 학습에 적합한 테스트 이미지 세트 준비.
COCO 2017 validation set에서 물리세계 학습 관련 이미지 다운로드.

각 이미지는 특정 능력을 테스트:
1. 물체 인식 (object recognition)
2. 공간 관계 (spatial relations)
3. 사람-물체 상호작용 (person-object interaction / affordance)
4. 물리 직관 (physics intuition)
5. 저조도/열악한 조건 (challenging conditions)
"""

import logging
import hashlib
from pathlib import Path

import httpx

from neural.ml.config import TEST_IMAGES_DIR

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# COCO 2017 validation images — 물리세계 학습 관련 선별
# 각 이미지는 특정 테스트 목적이 있음
TEST_IMAGE_SPECS = [
    {
        "filename": "01_table_objects.jpg",
        "url": "http://images.cocodataset.org/val2017/000000039769.jpg",
        "purpose": "실내 탁자 위 물체들 (고양이 2마리 + 리모컨)",
        "tests": ["object_recognition", "spatial_relation", "counting"],
    },
    {
        "filename": "02_person_laptop.jpg",
        "url": "http://images.cocodataset.org/val2017/000000037777.jpg",
        "purpose": "사람이 노트북 사용 (person-object interaction)",
        "tests": ["person_interaction", "affordance", "activity_recognition"],
    },
    {
        "filename": "03_kitchen_scene.jpg",
        "url": "http://images.cocodataset.org/val2017/000000087038.jpg",
        "purpose": "주방 장면 (다양한 물체, 공간 관계)",
        "tests": ["complex_scene", "spatial_relation", "object_recognition"],
    },
    {
        "filename": "04_person_food.jpg",
        "url": "http://images.cocodataset.org/val2017/000000174482.jpg",
        "purpose": "사람과 음식 (먹기 affordance)",
        "tests": ["person_interaction", "affordance", "food_recognition"],
    },
    {
        "filename": "05_street_scene.jpg",
        "url": "http://images.cocodataset.org/val2017/000000289343.jpg",
        "purpose": "거리 장면 (차량, 사람, 건물 — 실외 공간)",
        "tests": ["outdoor_scene", "depth_perception", "spatial_relation"],
    },
    {
        "filename": "06_dog_person.jpg",
        "url": "http://images.cocodataset.org/val2017/000000579321.jpg",
        "purpose": "사람과 동물 (동물 인식, 상호작용)",
        "tests": ["animal_interaction", "person_interaction", "activity_recognition"],
    },
    {
        "filename": "07_living_room.jpg",
        "url": "http://images.cocodataset.org/val2017/000000050326.jpg",
        "purpose": "거실 소파 (가구 배치, 실내 공간 이해)",
        "tests": ["indoor_layout", "furniture_recognition", "spatial_relation"],
    },
    {
        "filename": "08_person_sports.jpg",
        "url": "http://images.cocodataset.org/val2017/000000018150.jpg",
        "purpose": "스포츠 동작 (물리적 동작, 신체 자세)",
        "tests": ["physics_motion", "body_pose", "activity_recognition"],
    },
    {
        "filename": "09_food_table.jpg",
        "url": "http://images.cocodataset.org/val2017/000000397133.jpg",
        "purpose": "음식이 놓인 테이블 (물체 속성, 공간 배치)",
        "tests": ["object_attributes", "spatial_relation", "food_recognition"],
    },
    {
        "filename": "10_bathroom.jpg",
        "url": "http://images.cocodataset.org/val2017/000000087144.jpg",
        "purpose": "욕실 장면 (일상 공간, 물체 용도 이해)",
        "tests": ["indoor_layout", "object_function", "spatial_relation"],
    },
]


def download_test_images(force: bool = False) -> list[str]:
    """테스트 이미지 다운로드. 이미 있으면 스킵."""
    TEST_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    downloaded = []

    for spec in TEST_IMAGE_SPECS:
        filepath = TEST_IMAGES_DIR / spec["filename"]

        if filepath.exists() and not force:
            size_kb = filepath.stat().st_size / 1024
            logger.info(f"  [SKIP] {spec['filename']} ({size_kb:.0f} KB)")
            downloaded.append(str(filepath))
            continue

        logger.info(f"  [DOWNLOAD] {spec['filename']} — {spec['purpose']}")
        try:
            resp = httpx.get(spec["url"], timeout=30, follow_redirects=True)
            resp.raise_for_status()

            filepath.write_bytes(resp.content)
            size_kb = len(resp.content) / 1024
            logger.info(f"    OK: {size_kb:.0f} KB")
            downloaded.append(str(filepath))

        except Exception as e:
            logger.error(f"    FAIL: {e}")

    return downloaded


def list_test_images() -> list[dict]:
    """테스트 이미지 목록 + 메타데이터"""
    result = []
    for spec in TEST_IMAGE_SPECS:
        filepath = TEST_IMAGES_DIR / spec["filename"]
        exists = filepath.exists()
        result.append({
            "filename": spec["filename"],
            "path": str(filepath),
            "exists": exists,
            "size_kb": filepath.stat().st_size / 1024 if exists else 0,
            "purpose": spec["purpose"],
            "tests": spec["tests"],
        })
    return result


if __name__ == "__main__":
    print("\n=== Preparing Physical World Test Images ===\n")
    paths = download_test_images()
    print(f"\n{len(paths)}/{len(TEST_IMAGE_SPECS)} images ready.\n")

    # 기존 단색 테스트 이미지 정리
    old_test = TEST_IMAGES_DIR / "test_solid_red.png"
    if old_test.exists():
        old_test.unlink()
        print("Removed old test_solid_red.png")

    old_test2 = TEST_IMAGES_DIR / "test_solid_orange.png"
    if old_test2.exists():
        old_test2.unlink()
        print("Removed old test_solid_orange.png")

    old_test3 = TEST_IMAGES_DIR / "test.png"
    if old_test3.exists():
        old_test3.unlink()
        print("Removed old test.png")
