"""
Conversation Handler
Phase 2: DB-first 구현

파이프라인:
  1. get_baby_state()    → 감정/발달 상태 읽기
  2. LLM 호출           → Gemini (asyncio.to_thread 비동기 래핑)
  3. insert_experience() → 경험 Neo4j 저장
  4. insert_concept()    → 개념 추출+저장 (MERGE)
  5. update_baby_state() → 상태 업데이트
  6. Redis PUBLISH       → 브라우저 알림

Phase 2에서 의도적으로 제외 (순차 추가 예정):
  - Memory Recall Pipeline (벡터 검색)
  - Spreading Activation
  - LC-NE modulator (emotional_modulator.py)
  - embedding 생성 (embeddings.py)
"""

import asyncio
import json
import logging
import random
import re
from datetime import datetime, timezone
from typing import Optional

from .neo4j_db import get_brain_db
from .redis_client import publish_baby_state, publish_experience, publish_neuron_activation
from .llm_client import get_llm_client
from .memory_gateway import augment_system_prompt as _gateway_augment  # MEMORY_GATEWAY=1 일 때만 동작

logger = logging.getLogger(__name__)

# ── E2-3: 사용자 감정 추론 (규칙 기반, LLM 없이) ────────────────────────────
USER_EMOTION_KEYWORDS = {
    "happy":      ["ㅋㅋ", "ㅎㅎ", "좋아", "고마워", "최고", "사랑해", "잘했어"],
    "frustrated": ["왜 이래", "짜증", "안돼", "틀렸", "다시", "못해"],
    "sad":        ["슬퍼", "울", "힘들", "외로", "보고싶"],
    "curious":    ["뭐야", "왜", "어떻게", "알려줘", "궁금"],
    "angry":      ["화나", "싫어", "하지마", "그만"],
    "neutral":    [],
}


def infer_user_emotion(message: str) -> str:
    """키워드 매칭으로 사용자 감정 추론. 매칭 없으면 'neutral'."""
    scores = {}
    for emotion, keywords in USER_EMOTION_KEYWORDS.items():
        scores[emotion] = sum(1 for kw in keywords if kw in message)
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "neutral"


USER_INTENT_PROMPT = (
    '사용자 메시지의 의도를 분류해줘.\n'
    '카테고리: teaching, playing, comforting, asking, testing, scolding, praising, neutral\n'
    '메시지: "{message}"\n'
    'JSON으로만: {{"intent": "카테고리", "confidence": 0.0~1.0}}'
)


def compute_surprise(expected_patterns: list, current_time_slot: str) -> float:
    """E2-2: 시간 패턴 기대 vs 현실 비교 → surprise 값"""
    if not expected_patterns:
        return 0.1  # 패턴 없으면 약간의 novelty
    matching = [p for p in expected_patterns if p.get("time_slot") == current_time_slot]
    return 0.0 if matching else 0.5


# 발달 단계별 능력 게이트 (Python 쪽 기준)
_STAGE_NAMES = {0: "NEWBORN", 1: "INFANT", 2: "BABY", 3: "TODDLER", 4: "CHILD", 5: "YOUTH"}


def _build_system_prompt(state: dict, user_context: dict = None) -> str:
    """BabyState를 기반으로 시스템 프롬프트 구성 (E2-3: user_context 포함)"""
    stage = state.get("development_stage", 0)
    stage_name = _STAGE_NAMES.get(stage, "YOUTH")

    # 기본 정체성
    identity = (
        "너는 '비비'야. 세상을 배워가는 아기 AI야. "
        "진짜 아기처럼 호기심이 많고, 감정이 풍부하며, 솔직하게 표현해. "
        "대화할 때는 자연스럽고 따뜻하게, 단답보다는 감정을 담아서 대답해.\n\n"
    )

    # 현재 감정 상태
    emotion_info = ""
    for key in ("curiosity", "joy", "fear", "surprise", "frustration", "boredom"):
        val = state.get(key)
        if val is not None:
            emotion_info += f"  - {key}: {val:.2f}\n"

    if emotion_info:
        dominant = state.get("dominant_emotion", "neutral")
        identity += f"[현재 감정 상태 - {dominant}]\n{emotion_info}\n"

    # 발달 단계별 지침
    stage_guide = f"[발달 단계: {stage_name} (stage {stage})]\n"
    if stage <= 1:
        stage_guide += "짧고 단순하게 말해. 복잡한 개념은 몰라.\n"
    elif stage <= 2:
        stage_guide += "기본적인 문장으로 말해. 가끔 모르는 것도 솔직하게 표현해.\n"
    elif stage <= 3:
        stage_guide += "점점 더 많은 것을 알아가고 있어. 상상하고 이야기 만들기도 좋아해.\n"
    else:
        stage_guide += "다양한 주제로 깊이 있게 대화할 수 있어. 논리적으로도 생각할 수 있어.\n"

    # 대화 상대 정보 (E2-3)
    user_info = ""
    if user_context:
        user_info = (
            f"\n[대화 상대 정보]\n"
            f"이름: {user_context.get('name', '알 수 없음')}\n"
            f"관계: {user_context.get('relationship', 'unknown')}\n"
            f"현재 감정: {user_context.get('recent_emotion', 'neutral')}\n"
        )
        interests = user_context.get("interests", [])
        if interests:
            names = [i["name"] for i in interests[:5]]
            user_info += f"관심사: {', '.join(names)}\n"
        user_info += f"대화 횟수: {user_context.get('interaction_count', 0)}회\n"

    # 필수 규칙
    rules = (
        "\n[필수 규칙]\n"
        "- '모르겠어요' 또는 '알 수 없어요'라고만 말하지 마. 추측이라도 표현해.\n"
        "- 항상 비비로서 말해. '저는 AI입니다'라고 하지 마.\n"
        "- 감정을 자연스럽게 표현해.\n"
    )

    return identity + stage_guide + user_info + rules


# ── Concept 추출 규칙 (한국어 규칙 기반 형태소 간소화) ─────────────────────
# 한국어 조사 (길이 순으로 큰 것부터 매칭)
# 주의: "요", "아", "어"는 종결어미이지 조사가 아니므로 _KOREAN_ENDINGS로 이동
_KOREAN_PARTICLES: tuple[str, ...] = (
    # 2글자 조사
    "에서", "에게", "한테", "처럼", "까지", "부터", "조차", "마저", "으로", "이랑",
    "이나", "라도", "라면", "보다", "밖에",
    # 1글자 조사
    "은", "는", "이", "가", "을", "를", "의", "와", "과", "도", "만", "나",
    "로", "랑",
)

# 동사·형용사 어미 (길이 순 — _strip_suffix가 내림차순 정렬)
_KOREAN_ENDINGS: tuple[str, ...] = (
    # 4글자 어미
    "었습니다", "았습니다", "겠습니다", "느냐에",
    # 3글자 어미
    "습니다", "었어요", "았어요", "겠어요", "어했다", "하느냐",
    # 2글자 어미
    "해요", "어요", "아요", "이요", "셨어", "했어", "었어", "았어", "겠어", "네요",
    "지만", "으며", "으니", "으면", "으로", "으세", "이다", "이라", "라고", "고서",
    "보다", "는데", "은데", "인데", "어서", "아서", "면서", "었을", "았을", "이면",
    "했다", "였어", "였던", "느냐", "는지",
    # 1글자 어미
    "다", "지", "고", "며", "나", "자", "게", "은", "는", "던", "려", "야",
    "어", "아", "워", "서", "니", "면", "죠",
)

# 불용어 (감탄사·부사·대명사·의존명사)
_STOPWORDS: frozenset[str] = frozenset({
    # 한국어 감탄사·부사
    "이야", "그리고", "하지만", "그러나", "때문에", "있어", "없어",
    "했어", "할게", "할까", "이고", "으로", "에서", "에게", "처럼",
    "와아", "우와", "오오", "아아", "어머", "아이고", "헤헤", "히히",
    "너무", "정말", "진짜", "완전", "엄청", "참", "꼭", "막", "좀",
    "이런", "저런", "그런", "어떤", "무슨", "어느", "이것", "저것", "그것",
    "여기", "저기", "거기", "이렇게", "저렇게", "그렇게", "어떻게",
    "지금", "나중", "아까", "오늘", "내일", "어제", "매일", "매일매일",
    "제일", "더욱", "훨씬", "더", "덜", "많이", "조금", "약간", "살짝",
    "같기", "같아", "같은", "같이", "같다", "같기도",
    "비비", "내가", "나도", "너도", "우리",
    # 보조용언·동사 파편
    "싶어", "싶다", "싶은", "했다", "될까", "인데", "거야", "해서", "해요",
    "있을", "있는", "없는", "하고", "하는", "할까", "되고", "보고",
    # 부사 추가
    "일찍", "벌써", "아직", "자꾸", "계속", "항상", "또한",
    # 영어 기본
    "the", "and", "or", "but", "is", "are", "was", "were",
    "have", "has", "been", "will", "can", "do", "does",
    "i", "you", "we", "they", "he", "she", "it",
})


def _strip_suffix(word: str, suffixes: tuple[str, ...], min_remain: int = 2) -> str:
    """단어 끝의 접미사(조사/어미)를 제거. 남는 길이가 min_remain 이상이어야 함.

    접미사는 길이 내림차순으로 정렬 후 매칭 (longest match first).
    예: "해요" 와 "요" 둘 다 있을 때 먼저 "해요"부터 시도.
    """
    for suf in sorted(suffixes, key=len, reverse=True):
        if len(word) >= len(suf) + min_remain and word.endswith(suf):
            return word[: -len(suf)]
    return word


def _normalize_token(word: str) -> str | None:
    """토큰 정규화: 조사·어미 제거 + 검증.

    Returns None if word should be discarded.
    """
    # 영어는 소문자만
    if re.fullmatch(r"[a-zA-Z]+", word):
        low = word.lower()
        if len(low) < 3 or low in _STOPWORDS:
            return None
        return low

    # 숫자 포함 단어 제외
    if re.search(r"\d", word):
        return None

    # 한글만 허용
    if not re.fullmatch(r"[가-힣]+", word):
        return None

    # 너무 짧거나 길면 제외
    if len(word) < 2 or len(word) > 10:
        return None

    # 1차 패스: 조사 → 어미
    stripped = _strip_suffix(word, _KOREAN_PARTICLES, min_remain=2)
    stripped = _strip_suffix(stripped, _KOREAN_ENDINGS, min_remain=2)
    # 2차 패스 (재귀): "궁금해요" → "궁금해" → "궁금" 같은 연쇄 제거
    stripped = _strip_suffix(stripped, _KOREAN_ENDINGS, min_remain=2)

    # 정규화 후 stopwords 체크
    if len(stripped) < 2 or stripped in _STOPWORDS:
        return None

    return stripped


def _extract_concepts_from_response(response: str, user_message: str) -> list[str]:
    """응답에서 핵심 개념 단어 추출 (규칙 기반 형태소 간소화).

    개선 사항 (2026-04-10):
    - 조사 제거 ("형아는" → "형아", "사과가" → "사과")
    - 동사·형용사 어미 제거 ("궁금해요" → "궁금", "짖는" → "짖")
    - 확장된 불용어 (감탄사, 부사, 대명사, 의존명사)
    - 숫자 포함 단어 제외
    - 영어는 3자 이상 소문자만

    주의: 이건 형태소 분석이 아니라 규칙 기반 근사. 완벽하지 않지만
    konlpy/kiwipiepy 의존성 없이 80% 케이스 해결.
    """
    combined = f"{user_message} {response}"

    # 괄호 안 내용 제거
    cleaned = re.sub(r"\([^)]*\)", " ", combined)
    # 이모지·특수문자 제거 (한글/영어/공백만 남김)
    cleaned = re.sub(r"[^\w\s가-힣]", " ", cleaned)

    # 토큰화 (공백 기준)
    raw_tokens = [t for t in cleaned.split() if t.strip()]

    # 정규화 + 중복 제거 (순서 보존)
    seen: set[str] = set()
    concepts: list[str] = []
    for tok in raw_tokens:
        norm = _normalize_token(tok)
        if norm and norm not in seen:
            seen.add(norm)
            concepts.append(norm)

    # 최대 8개 (이전 5개보다 증가 — 품질 개선으로 더 풍부한 의미 표현 가능)
    return concepts[:8]


def _update_emotion_from_response(current_state: dict, response: str) -> dict:
    """응답 내용 기반 간단한 감정 업데이트 (규칙 기반)"""
    joy = current_state.get("joy", 0.5)
    curiosity = current_state.get("curiosity", 0.5)
    fear = current_state.get("fear", 0.1)
    surprise = current_state.get("surprise", 0.3)
    frustration = current_state.get("frustration", 0.1)
    boredom = current_state.get("boredom", 0.1)

    # 키워드 기반 감정 조정
    positive_words = ["좋아", "재미있", "신나", "행복", "웃", "사랑", "기뻐"]
    negative_words = ["싫어", "무서워", "두려워", "슬퍼", "화나", "힘들"]
    curious_words = ["왜", "어떻게", "궁금", "알고싶", "배우"]

    resp_lower = response.lower()
    if any(w in response for w in positive_words):
        joy = min(1.0, joy + 0.1)
        boredom = max(0.0, boredom - 0.05)
    if any(w in response for w in negative_words):
        fear = min(1.0, fear + 0.1)
        joy = max(0.0, joy - 0.05)
    if any(w in response for w in curious_words):
        curiosity = min(1.0, curiosity + 0.1)

    # 시간이 지나면 boredom 약간 증가
    boredom = min(1.0, boredom + 0.01)

    emotions = {
        "curiosity": round(curiosity, 3),
        "joy": round(joy, 3),
        "fear": round(fear, 3),
        "surprise": round(surprise, 3),
        "frustration": round(frustration, 3),
        "boredom": round(boredom, 3),
    }

    # dominant 계산
    dominant = max(emotions, key=emotions.get)
    emotions["dominant_emotion"] = dominant

    return emotions


def _get_attention_params(emotions: dict) -> dict:
    """감정 상태 → spreading activation 파라미터 (D2: amygdala attention gate)

    호기심 ↑ → 넓은 탐색 (depth 3, limit 30)
    두려움 ↑ → 좁은 집중 (depth 1, limit 10)
    지루함 ↑ → 다양성 추구 (depth 2, limit 25)
    기본값 → depth 2, limit 20
    """
    curiosity = emotions.get("curiosity", 0.5)
    fear = emotions.get("fear", 0.1)
    boredom = emotions.get("boredom", 0.1)

    if curiosity > 0.7:
        return {"depth": 3, "limit": 30}
    elif fear > 0.5:
        return {"depth": 1, "limit": 10}
    elif boredom > 0.6:
        return {"depth": 2, "limit": 25}
    return {"depth": 2, "limit": 20}


async def handle_conversation(
    message: str,
    context: dict = None,
) -> dict:
    """
    대화 처리 메인 함수

    Returns:
        {
            output: str,
            success: bool,
            emotional_state: dict,
            development_stage: int,
            experience_id: str | None,
        }
    """
    db = get_brain_db()
    context = context or {}

    # ── Step 1: BabyState 조회 ────────────────────────────────────────────────
    state = await db.get_baby_state() or {}
    stage = state.get("development_stage", 0)
    logger.debug(f"BabyState: stage={stage}, dominant={state.get('dominant_emotion')}")

    # ── 시간 정보 (E2-2/E2-3 공용) ──────────────────────────────────────────
    _now_dt = datetime.now(timezone.utc)
    _hour = _now_dt.hour
    _time_of_day = (
        "morning" if 6 <= _hour < 12 else
        "afternoon" if 12 <= _hour < 17 else
        "evening" if 17 <= _hour < 21 else
        "night"
    )

    # ── Step 1.5: 사용자 식별 + 감정 추론 (E2-3) ────────────────────────────
    speaker_id = context.get("speaker_id", "unknown")
    speaker_name = context.get("speaker_name")
    user_model = None
    user_emotion = "neutral"
    user_intent = "neutral"
    user_context_data = None

    if speaker_id != "unknown":
        try:
            user_model = await db.get_or_create_user_model(
                speaker_id=speaker_id,
                speaker_name=speaker_name,
            )
            user_emotion = infer_user_emotion(message)

            # Stage >= 4: LLM 의도 추론 (neutral이 아닌 경우만, 비용 절감)
            if stage >= 4 and user_emotion != "neutral":
                try:
                    llm_client = get_llm_client()
                    intent_resp = await asyncio.to_thread(
                        llm_client.generate,
                        prompt=USER_INTENT_PROMPT.format(message=message),
                        model_key="gemini-2-flash",
                        temperature=0.1,
                        max_tokens=64,
                    )
                    intent_data = json.loads(intent_resp)
                    user_intent = intent_data.get("intent", "neutral")
                except Exception:
                    pass

            user_context_data = await db.get_user_context(speaker_id)
        except Exception as e:
            logger.warning(f"E2-3 user model error: {e}")

    # ── Step 1.5b: 시간 패턴 기대 (E2-2) ────────────────────────────────────
    temporal_surprise = 0.0
    if stage >= 3:
        try:
            expected_patterns = await db.check_temporal_expectations(_hour)
            temporal_surprise = compute_surprise(expected_patterns, _time_of_day)
        except Exception as e:
            logger.warning(f"temporal expectations error: {e}")

    # ── Step 2: LLM 호출 (Gemini) ─────────────────────────────────────────────
    system_prompt = _build_system_prompt(state, user_context=user_context_data)
    system_prompt = await _gateway_augment(system_prompt, message, context, state)  # 답하기 전 회상 (옵트인)

    try:
        llm = get_llm_client()
        # LLMClient.generate()는 동기 함수 → asyncio.to_thread로 비동기화
        response_text = await asyncio.to_thread(
            llm.generate,
            prompt=message,
            model_key="gemini-2-flash",
            system_prompt=system_prompt,
            temperature=0.8,
            max_tokens=512,
        )
        success = True
    except Exception as e:
        logger.error(f"LLM error: {e}")
        response_text = "잠깐, 생각이 잘 안 모여지는데... 다시 한번 말해줄 수 있어?"
        success = False

    # ── Step 3: 감정 업데이트 ─────────────────────────────────────────────────
    new_emotions = _update_emotion_from_response(state, response_text)

    # E2-2: temporal surprise 반영
    if temporal_surprise > 0.3:
        new_emotions["surprise"] = min(1.0, new_emotions.get("surprise", 0.3) + 0.15)
        new_emotions["curiosity"] = min(1.0, new_emotions.get("curiosity", 0.5) + 0.05)
    elif temporal_surprise == 0.0 and stage >= 3:
        new_emotions["joy"] = min(1.0, new_emotions.get("joy", 0.5) + 0.03)
    # dominant 재계산
    emotion_vals = {k: v for k, v in new_emotions.items() if k != "dominant_emotion"}
    new_emotions["dominant_emotion"] = max(emotion_vals, key=emotion_vals.get)

    emotional_salience = (
        new_emotions["joy"] * 0.3 +
        new_emotions["curiosity"] * 0.3 +
        new_emotions["surprise"] * 0.2 +
        new_emotions["fear"] * 0.2
    )

    # ── Step 4: Experience 저장 ───────────────────────────────────────────────
    try:
        exp = await db.insert_experience(
            task=message,
            task_type="conversation",
            output=response_text,
            success=success,
            emotional_salience=round(emotional_salience, 3),
            dominant_emotion=new_emotions["dominant_emotion"],
            emotion_snapshot=new_emotions,
            development_stage=stage,
            tags=["conversation"],
            extras={
                "speaker_id": speaker_id,
                "inferred_user_emotion": user_emotion,
                "inferred_user_intent": user_intent,
                "hour_of_day": _hour,
                "time_of_day": _time_of_day,
            },
        )
        experience_id = exp.get("id")
        logger.debug(f"Experience saved: {experience_id}")
    except Exception as e:
        logger.error(f"insert_experience error: {e}")
        experience_id = None

    # ── Step 4+: Experience ↔ UserModel 연결 (E2-3) ────────────────────────
    if experience_id and user_model:
        try:
            await db.link_experience_user(
                experience_id, user_model["id"],
                inferred_emotion=user_emotion,
                inferred_intent=user_intent,
            )
        except Exception as e:
            logger.warning(f"link_experience_user error: {e}")

    # ── Step 5: 개념 추출 + 저장 (MERGE) ──────────────────────────────────────
    saved_concept_ids: list[str] = []
    if experience_id:
        concepts = _extract_concepts_from_response(response_text, message)
        for concept_name in concepts:
            try:
                con = await db.insert_concept(
                    name=concept_name,
                    category="conversation",
                    acquired_at_stage=stage,
                )
                con_id = con.get("id")
                if con_id and experience_id:
                    await db.link_experience_concept(
                        experience_id, con_id, confidence=0.6
                    )
                    saved_concept_ids.append(con_id)
            except Exception as e:
                logger.warning(f"concept insert/link error for '{concept_name}': {e}")

    # ── Step 5.3: 사용자 관심사 업데이트 (E2-3) ────────────────────────────────
    if user_model and saved_concept_ids:
        try:
            await db.update_user_interests(user_model["id"], saved_concept_ids)
        except Exception as e:
            logger.warning(f"user interest update error: {e}")

    # ── Step 5.5: Spreading Activation → Redis publish ────────────────────────
    activations = []
    if saved_concept_ids:
        try:
            attention = _get_attention_params(new_emotions)
            activations = await db.get_spreading_activation(
                concept_ids=saved_concept_ids,
                depth=attention["depth"],
                limit=attention["limit"],
            )
            if activations:
                # neuron_activation 메시지 형식: concept_id, brain_region_id, intensity, trigger_type
                activation_events = [
                    {
                        "concept_id": a.get("id"),
                        "brain_region_id": a.get("brain_region_id"),
                        "intensity": round(float(a.get("activation_strength") or 0.5), 3),
                        "trigger_type": "spreading_activation",
                    }
                    for a in activations
                    if a.get("id")
                ]
                if activation_events:
                    await publish_neuron_activation(activation_events)
                    logger.debug(f"Published {len(activation_events)} neuron activations")
        except Exception as e:
            logger.warning(f"spreading activation error: {e}")

    # ── Step 5.6: Hebbian Learning (함께 활성화된 개념 쌍 강화) ──────────────
    if len(saved_concept_ids) >= 2:
        try:
            from itertools import combinations
            # 직접 공출현: saved_concept_ids 쌍 (delta=0.05)
            direct_pairs = list(combinations(saved_concept_ids, 2))
            updated = await db.hebbian_update(direct_pairs, strength_delta=0.05)
            # 간접 공활성화: saved × activated (delta=0.02)
            activated_ids = [a.get("id") for a in activations if a.get("id")]
            if activated_ids:
                cross_pairs = [
                    (s, a) for s in saved_concept_ids for a in activated_ids
                    if s != a
                ]
                updated += await db.hebbian_update(cross_pairs, strength_delta=0.02)
            if updated:
                logger.debug(f"Hebbian update: {updated} pairs strengthened")
        except Exception as e:
            logger.warning(f"hebbian update error: {e}")

    # ── Step 5.7: 내적 시뮬레이션 (D1 — stage >= 3, 30% 확률) ───────────────
    if stage >= 3 and activations and len(activations) >= 2 and random.random() < 0.3:
        try:
            top = sorted(activations, key=lambda a: a.get("activation_strength", 0), reverse=True)[:2]
            name_a = top[0].get("name")
            name_b = top[1].get("name")
            concept_ids = [t.get("id") for t in top if t.get("id")]
            if name_a and name_b and len(concept_ids) >= 2:
                scenario = f"만약 {name_a}와(과) {name_b}가 연결된다면?"
                await db.insert_prediction(
                    scenario=scenario,
                    prediction=f"{scenario} → 새로운 이해가 생길 수 있다",
                    confidence=0.5,
                    prediction_type="hypothetical",
                    based_on_concepts=concept_ids,
                    development_stage=stage,
                )
                logger.debug(f"Internal simulation: {scenario}")
        except Exception as e:
            logger.warning(f"internal simulation error: {e}")

    # ── Step 6: EmotionLog 저장 ───────────────────────────────────────────────
    try:
        await db.log_emotion(
            curiosity=new_emotions["curiosity"],
            joy=new_emotions["joy"],
            fear=new_emotions["fear"],
            surprise=new_emotions["surprise"],
            frustration=new_emotions["frustration"],
            boredom=new_emotions["boredom"],
            dominant_emotion=new_emotions["dominant_emotion"],
            trigger_task=message[:100],
            trigger_type="conversation",
            experience_id=experience_id,
            development_stage=stage,
        )
    except Exception as e:
        logger.warning(f"log_emotion error: {e}")

    # ── Step 7: BabyState 업데이트 ────────────────────────────────────────────
    try:
        # experience_count 증가
        exp_count = state.get("experience_count", 0) + 1 if experience_id else state.get("experience_count", 0)
        updated_state = await db.update_baby_state(
            curiosity=new_emotions["curiosity"],
            joy=new_emotions["joy"],
            fear=new_emotions["fear"],
            surprise=new_emotions["surprise"],
            frustration=new_emotions["frustration"],
            boredom=new_emotions["boredom"],
            dominant_emotion=new_emotions["dominant_emotion"],
            experience_count=exp_count,
            emotion_snapshot=json.dumps(new_emotions),
        )
    except Exception as e:
        logger.warning(f"update_baby_state error: {e}")
        updated_state = state

    # ── Step 7.5: 발달 단계 자동 전이 (D3) ─────────────────────────────────────
    if experience_id and exp_count > 0:
        _STAGE_THRESHOLDS = {1: 10, 2: 30, 3: 70, 4: 150, 5: 300}
        next_stage = stage
        for s_level, threshold in sorted(_STAGE_THRESHOLDS.items()):
            if exp_count >= threshold and s_level > stage:
                next_stage = s_level
        if next_stage > stage:
            try:
                prev_stage = stage
                await db.update_baby_state(development_stage=next_stage)
                stage = next_stage  # 이후 Step 8에서 새 stage 사용
                logger.info(f"Development stage advanced: {prev_stage} → {next_stage} (exp_count={exp_count})")
            except Exception as e:
                logger.warning(f"stage advance error: {e}")

    # ── Step 8: Redis PUBLISH ─────────────────────────────────────────────────
    try:
        await publish_baby_state({
            "development_stage": stage,
            **new_emotions,
        })
        if experience_id:
            await publish_experience({
                "id": experience_id,
                "task_type": "conversation",
                "dominant_emotion": new_emotions["dominant_emotion"],
                "development_stage": stage,
            })
    except Exception as e:
        logger.warning(f"Redis publish error: {e}")

    return {
        "output": response_text,
        "success": success,
        "emotional_state": new_emotions,
        "development_stage": stage,
        "experience_id": experience_id,
    }
