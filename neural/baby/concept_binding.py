"""Phase A4.4 — Descriptor→Object binding parser.

현 단계는 color→object 인접 바인딩만 처리한다. 향후 material/size/shape 등을
같은 메커니즘으로 확장할 수 있도록 ``aspect`` 필드를 반환한다.

설계 원칙:
- DB 의존 0. 순수 함수 → 단위 테스트 및 대화 경로 재사용 가능.
- 규칙: COLOR 토큰 바로 뒤의 첫 단어를 "수식 대상"으로 간주.
  - stopword 아니고, COLOR 아니고, 길이 2+ 인 토큰.
- be-copula ("keyboard is white") 등 어순 전환은 A4.5 이후.

offline 평가 근거 (2026-04-24, 36 quest_passthrough Experience):
- strict precision 94% (32/34), recall ≈ 86%
- FP 1건 ("white square keys" → white→square): 수면 decay로 자연 정리 수용
"""

from __future__ import annotations

import re
from typing import Iterable

# 색상 어휘 — 영어 기본 COLOR. 추가 필요 시 이 셋만 확장.
COLOR_WORDS: frozenset[str] = frozenset({
    "red", "blue", "green", "yellow", "white", "black",
    "gray", "grey", "brown", "orange", "purple", "pink",
    "violet", "cyan", "magenta", "beige", "tan", "gold", "silver",
})

# COLOR 뒤에 오면 pair 생성하지 않는 단어.
# 주의: "hp" 같은 고유명사 acronym(len 2)은 살리되, 기능어는 배제.
STOPWORDS_AFTER_COLOR: frozenset[str] = frozenset({
    "and", "or", "but", "the", "a", "an",
    "is", "are", "was", "were", "be", "been", "being",
    "of", "on", "in", "at", "with", "to", "from", "by", "for", "as",
    "it", "this", "that", "these", "those", "its",
    "has", "have", "had",
})

_PUNCT_RE = re.compile(r"[.,!?;:\"'()\[\]]")
_WS_RE = re.compile(r"\s+")


def _tokenize(text: str) -> list[str]:
    """lowercase + 문장부호 공백화 + 공백 분리."""
    lowered = text.lower()
    cleaned = _PUNCT_RE.sub(" ", lowered)
    return [t for t in _WS_RE.split(cleaned) if t]


def extract_color_bindings(text: str) -> list[tuple[str, str, str]]:
    """문장에서 color→object 인접 binding 후보를 추출.

    Returns:
        ``(descriptor, obj_name, aspect)`` 튜플 리스트. 중복 가능(호출자가 집계).
    """
    tokens = _tokenize(text)
    pairs: list[tuple[str, str, str]] = []
    n = len(tokens)
    for i, tok in enumerate(tokens):
        if tok not in COLOR_WORDS:
            continue
        if i + 1 >= n:
            continue
        nxt = tokens[i + 1]
        if nxt in STOPWORDS_AFTER_COLOR:
            continue
        if nxt in COLOR_WORDS:
            continue
        if len(nxt) < 2:
            continue
        pairs.append((tok, nxt, "color"))
    return pairs


def aggregate_bindings(
    texts: Iterable[str],
) -> dict[tuple[str, str, str], int]:
    """여러 문장에서 (descriptor, obj, aspect)별 출현 횟수 집계."""
    counts: dict[tuple[str, str, str], int] = {}
    for t in texts:
        for pair in extract_color_bindings(t):
            counts[pair] = counts.get(pair, 0) + 1
    return counts
