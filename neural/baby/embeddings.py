"""
Embeddings Module for Baby Brain

OpenAI text-embedding-3-small 모델을 사용한 벡터 임베딩 생성
- 1536 차원 벡터
- 경험, 개념의 의미적 유사도 계산에 사용
"""

import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Lazy import for OpenAI
_openai_client = None

# 모델 설정
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536


def get_openai_client():
    """OpenAI 클라이언트 싱글톤"""
    global _openai_client

    if _openai_client is None:
        from openai import OpenAI

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key or api_key == "your-openai-api-key-here":
            raise ValueError(
                "OPENAI_API_KEY must be set in environment variables. "
                "Get your key from https://platform.openai.com/api-keys"
            )

        _openai_client = OpenAI(api_key=api_key)

    return _openai_client


def create_embedding(text: str) -> list[float]:
    """
    텍스트에 대한 임베딩 벡터 생성

    Args:
        text: 임베딩할 텍스트

    Returns:
        1536 차원의 float 리스트

    Raises:
        ValueError: 텍스트가 비어있거나 OpenAI API 키가 없는 경우
    """
    if not text or not text.strip():
        raise ValueError("Text cannot be empty")

    # 텍스트 정규화 (너무 긴 경우 잘라내기)
    text = text.strip()
    if len(text) > 8000:  # 토큰 제한 대비
        text = text[:8000]

    client = get_openai_client()
    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text,
    )

    return response.data[0].embedding


def create_embeddings_batch(texts: list[str]) -> list[list[float]]:
    """
    여러 텍스트에 대한 임베딩 벡터 일괄 생성

    Args:
        texts: 임베딩할 텍스트 리스트

    Returns:
        각 텍스트에 대한 임베딩 벡터 리스트
    """
    if not texts:
        return []

    # 텍스트 정규화
    normalized = []
    for text in texts:
        text = text.strip() if text else ""
        if len(text) > 8000:
            text = text[:8000]
        normalized.append(text if text else " ")  # 빈 문자열 방지

    client = get_openai_client()
    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=normalized,
    )

    # 인덱스 순서대로 정렬하여 반환
    embeddings = [None] * len(texts)
    for item in response.data:
        embeddings[item.index] = item.embedding

    return embeddings


def cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    """
    두 벡터의 코사인 유사도 계산

    Args:
        vec1: 첫 번째 벡터
        vec2: 두 번째 벡터

    Returns:
        -1.0 ~ 1.0 사이의 유사도 값 (1.0이 가장 유사)
    """
    if len(vec1) != len(vec2):
        raise ValueError(f"Vector dimensions must match: {len(vec1)} != {len(vec2)}")

    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = sum(a * a for a in vec1) ** 0.5
    norm2 = sum(b * b for b in vec2) ** 0.5

    if norm1 == 0 or norm2 == 0:
        return 0.0

    return dot_product / (norm1 * norm2)


class EmbeddingCache:
    """
    간단한 인메모리 임베딩 캐시

    API 호출 비용 절감을 위해 동일 텍스트 재사용
    """

    def __init__(self, max_size: int = 100):
        self._cache: dict[str, list[float]] = {}
        self._max_size = max_size
        self._access_order: list[str] = []  # LRU 구현

    def get(self, text: str) -> Optional[list[float]]:
        """캐시에서 임베딩 조회"""
        key = text.strip()[:200]  # 키 길이 제한
        if key in self._cache:
            # LRU 갱신
            self._access_order.remove(key)
            self._access_order.append(key)
            return self._cache[key]
        return None

    def set(self, text: str, embedding: list[float]) -> None:
        """임베딩 캐시에 저장"""
        key = text.strip()[:200]

        # 크기 초과 시 가장 오래된 항목 제거 (LRU)
        while len(self._cache) >= self._max_size and self._access_order:
            oldest_key = self._access_order.pop(0)
            self._cache.pop(oldest_key, None)

        self._cache[key] = embedding
        self._access_order.append(key)

    def clear(self) -> None:
        """캐시 비우기"""
        self._cache.clear()
        self._access_order.clear()


# 전역 캐시 인스턴스
_embedding_cache = EmbeddingCache()


def get_embedding_cached(text: str) -> list[float]:
    """
    캐시를 활용한 임베딩 생성

    동일 텍스트는 캐시에서 반환하여 API 호출 절감
    """
    cached = _embedding_cache.get(text)
    if cached is not None:
        return cached

    embedding = create_embedding(text)
    _embedding_cache.set(text, embedding)
    return embedding


def create_experience_embedding(
    task: str,
    task_type: str,
    output: str,
    success: bool,
) -> list[float]:
    """
    경험에 대한 임베딩 생성

    태스크, 출력 결과, 성공 여부를 종합한 텍스트로 임베딩
    """
    # 성공/실패 레이블 추가
    status = "성공" if success else "실패"

    # 출력이 너무 길면 요약
    output_summary = output[:500] if len(output) > 500 else output

    # 임베딩용 텍스트 구성
    text = f"[{task_type}] {task}\n결과: {status}\n출력: {output_summary}"

    return get_embedding_cached(text)


def create_concept_embedding(
    name: str,
    category: str = None,
    description: str = None,
) -> list[float]:
    """
    개념에 대한 임베딩 생성
    """
    parts = [name]
    if category:
        parts.append(f"카테고리: {category}")
    if description:
        parts.append(description)

    text = " | ".join(parts)
    return get_embedding_cached(text)


# 임베딩 없이도 동작하도록 폴백
def safe_create_embedding(text: str) -> Optional[list[float]]:
    """
    안전한 임베딩 생성 (실패 시 None 반환)

    OpenAI API 키가 없거나 에러 발생 시에도 시스템이 동작하도록
    """
    try:
        return create_embedding(text)
    except Exception as e:
        print(f"[Embedding] Warning: Failed to create embedding: {e}")
        return None
