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

# Phase Q1 (visual co-occurrence Hebbian) — 시각 동시발생 시 RELATES_TO 대상에서 제외할 토큰.
# 근거 (2026-05-08 진단): Quest 42 Experience TOP-25 분석에서 색상/위치/속성 부사가 noise 후보.
# - 색상은 별도 describes_color 관계로 처리됨 → visual_cooc에 포함하면 의미 중복.
# - "next/left/standard/layout/branded" 등은 객체 아닌 메타 서술.
VISUAL_COOC_EXCLUDE: frozenset[str] = frozenset({
    # 위치/방향 부사
    "next", "left", "right", "up", "down", "above", "below", "near", "far",
    # 일반 속성/상태
    "standard", "layout", "branded", "background", "close", "open",
    # 메타 (이미지 표현 자체)
    "text", "symbol", "symbols", "image", "picture", "scene", "view",
})


def select_visual_cooc_concepts(name_to_id: dict[str, str]) -> list[str]:
    """visual co-occurrence Hebbian 대상 concept_id 리스트.

    Filter:
    1) 색상 단어 제외 (COLOR_WORDS — describes_color로 별도 처리됨)
    2) noise 단어 제외 (VISUAL_COOC_EXCLUDE)
    3) 길이 < 2 토큰 제외

    name_to_id: 같은 frame에 추출된 {name: concept_id} 매핑.
    """
    selected: list[str] = []
    for name, cid in name_to_id.items():
        n = name.strip().lower()
        if len(n) < 2:
            continue
        if n in COLOR_WORDS:
            continue
        if n in VISUAL_COOC_EXCLUDE:
            continue
        selected.append(cid)
    return selected

_PUNCT_RE = re.compile(r"[.,!?;:\"'()\[\]]")
_WS_RE = re.compile(r"\s+")


def _tokenize(text: str) -> list[str]:
    """lowercase + 문장부호 공백화 + 공백 분리."""
    lowered = text.lower()
    cleaned = _PUNCT_RE.sub(" ", lowered)
    return [t for t in _WS_RE.split(cleaned) if t]


def extract_color_bindings(text: str) -> list[tuple[str, str, str]]:
    """문장에서 color→object binding 후보를 추출.

    적용 규칙 (A4.5C):
      1. **인접** (A4.4 기본): ``COLOR + NOUN`` — 가장 확실, precision 우선
      2. **공접** (A4.5C): ``COLOR1 + "and" + COLOR2 + NOUN`` — COLOR1도 NOUN 수식
      3. **be-copula** (A4.5C): ``NOUN + (is|are|was|were) + COLOR`` — COLOR가 NOUN 수식

    제외 케이스 (MVP 범위 밖):
      - 3단 공접 ``red, blue, and green keys`` (현재 데이터 0건)
      - 거리-2 ``bottle of yellow liquid`` 의 bottle 추정 (의도적 보수)
      - 형용사 + COLOR ``big and yellow ball`` (POS tagger 필요)

    Returns:
        ``(descriptor, obj_name, aspect)`` 튜플 리스트. 중복 가능(호출자가 집계).
    """
    tokens = _tokenize(text)
    pairs: list[tuple[str, str, str]] = []
    n = len(tokens)

    def _is_valid_object(tok: str) -> bool:
        """수식 대상 명사 후보로 적격한지."""
        return (
            tok not in STOPWORDS_AFTER_COLOR
            and tok not in COLOR_WORDS
            and len(tok) >= 2
        )

    for i, tok in enumerate(tokens):
        if tok not in COLOR_WORDS:
            continue

        # 규칙 1: 인접 COLOR + NOUN
        if i + 1 < n:
            nxt = tokens[i + 1]
            if _is_valid_object(nxt):
                pairs.append((tok, nxt, "color"))

        # 규칙 2: 공접 COLOR1 + "and" + COLOR2 + NOUN
        # 첫 COLOR(tok) 입장에서 "and COLOR2 NOUN" 패턴 검사.
        if i + 3 < n and tokens[i + 1] == "and" and tokens[i + 2] in COLOR_WORDS:
            shared = tokens[i + 3]
            if _is_valid_object(shared):
                pairs.append((tok, shared, "color"))

    # 규칙 3: be-copula NOUN + (is|are|was|were) + COLOR
    # COLOR 위치에서 거꾸로 보기.
    COPULAS = {"is", "are", "was", "were"}
    for i, tok in enumerate(tokens):
        if tok not in COLOR_WORDS:
            continue
        if i < 2:
            continue
        if tokens[i - 1] not in COPULAS:
            continue
        # i-1 = copula, i-2 부터 거슬러 올라가 첫 비-stopword 명사 후보
        for j in range(i - 2, -1, -1):
            cand = tokens[j]
            if cand in STOPWORDS_AFTER_COLOR:
                continue  # the/a/an/this 등은 건너뜀
            if cand in COLOR_WORDS:
                break  # 다른 색상이면 중단 ("blue and red are colors" 같은 메타 문장)
            if len(cand) < 2:
                continue
            pairs.append((tok, cand, "color"))
            break

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
