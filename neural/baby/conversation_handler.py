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
import re
from typing import Optional

from .neo4j_db import get_brain_db
from .redis_client import publish_baby_state, publish_experience, publish_neuron_activation
from .llm_client import get_llm_client

logger = logging.getLogger(__name__)

# 발달 단계별 능력 게이트 (Python 쪽 기준)
_STAGE_NAMES = {0: "NEWBORN", 1: "INFANT", 2: "BABY", 3: "TODDLER", 4: "CHILD", 5: "YOUTH"}


def _build_system_prompt(state: dict) -> str:
    """BabyState를 기반으로 시스템 프롬프트 구성"""
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

    # 필수 규칙
    rules = (
        "\n[필수 규칙]\n"
        "- '모르겠어요' 또는 '알 수 없어요'라고만 말하지 마. 추측이라도 표현해.\n"
        "- 항상 비비로서 말해. '저는 AI입니다'라고 하지 마.\n"
        "- 감정을 자연스럽게 표현해.\n"
    )

    return identity + stage_guide + rules


def _extract_concepts_from_response(response: str, user_message: str) -> list[str]:
    """응답에서 핵심 개념 단어 추출 (간단한 규칙 기반)"""
    # 명사구/핵심어 추출 (LLM 없이 간단하게)
    combined = f"{user_message} {response}"

    # 괄호 안 내용 제거, 특수문자 제거
    cleaned = re.sub(r'\([^)]*\)', '', combined)
    cleaned = re.sub(r'[^\w\s가-힣]', ' ', cleaned)

    # 2자 이상 단어 추출 (한글 포함)
    words = [w for w in cleaned.split() if len(w) >= 2]

    # 불용어 제거 (간단한 목록)
    stopwords = {
        "이야", "그리고", "하지만", "그러나", "때문에", "있어", "없어",
        "했어", "할게", "할까", "이고", "으로", "에서", "에게", "처럼",
        "the", "and", "or", "but", "is", "are", "was", "were",
        "have", "has", "been", "will", "can", "do", "does",
    }

    concepts = list({w for w in words if w.lower() not in stopwords})

    # 최대 5개
    return concepts[:5]


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

    # ── Step 2: LLM 호출 (Gemini) ─────────────────────────────────────────────
    system_prompt = _build_system_prompt(state)

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
        )
        experience_id = exp.get("id")
        logger.debug(f"Experience saved: {experience_id}")
    except Exception as e:
        logger.error(f"insert_experience error: {e}")
        experience_id = None

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

    # ── Step 5.5: Spreading Activation → Redis publish ────────────────────────
    if saved_concept_ids:
        try:
            activations = await db.get_spreading_activation(
                concept_ids=saved_concept_ids,
                depth=2,
                limit=20,
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
