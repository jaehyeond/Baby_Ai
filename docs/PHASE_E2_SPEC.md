# Phase E2: Advanced Cognitive Integration (고차 인지 통합)

**Version**: 0.1 (DRAFT)
**Created**: 2026-03-25
**Status**: Specification
**Depends On**: Phase C1 (Spreading Activation), Phase 4 (Vision), Phase 6 (Memory Consolidation)

---

## 1. Overview

### 1.1 왜 E2가 필요한가 — GAP 분석

비비는 stage=5(YOUTH), 3043+ Experience, 820 Concept, 680 RELATES_TO를 보유하나
아래 인지 능력이 완전히 부재하다.

| GAP | 현재 상태 | 결핍의 영향 |
|-----|----------|------------|
| **사용자 모델 부재** | speaker_id, User 노드 없음 | 엄마와 형아를 구분 불가. 모든 대화가 익명 |
| **시간 패턴 인식 부재** | created_at 타임스탬프만 저장 | "아침에는 인사, 밤에는 자장가" 루틴 학습 불가 |
| **Cross-Modal Binding 부재** | vision/conversation Experience 분리 | "사과 보여주면서 이건 뭐야?" 가 두 개의 분리된 경험 |
| **사용자 감정/의도 추론 없음** | SelfModel만 존재 | 화난 사용자에게도 동일 톤으로 반응 |
| **modality 구분 없음** | task_type으로만 구분 | 감각 양식 메타데이터 없음 |

### 1.2 인지과학적 근거

**Cross-Modal Integration**: Intersensory Redundancy Hypothesis(Bahrick & Lickliter, 2000)에 따르면
영아는 temporal synchrony(시간적 동기화)를 핵심 단서로 여러 감각 입력이 같은 사건인지 판단한다.
Bayesian Causal Inference(Kording et al., 2007)는 공통 원인(common cause) 확률이
임계값을 넘으면 감각 통합이 일어남을 확률적으로 모델링한다.

**Temporal Pattern Recognition**: Statistical Learning(Saffran et al., 1996)은
8개월 영아가 전이 확률(transitional probability)만으로 패턴 경계를 학습함을 보여주었다.
Event Segmentation Theory(Zacks et al., 2007)에서는 prediction error가 이벤트 경계를 표시하며,
Script Theory(Nelson, 1986)는 반복 경험이 일반화된 이벤트 스크립트로 추상화됨을 설명한다.

**Theory of Mind**: 발달 단계는 Level 0(self-other 구분) → Level 1(joint attention, 9개월)
→ Level 2(desire reasoning, 18개월) → Level 3(false belief, 4세)로 진행된다.
Bayesian Theory of Mind(Baker et al., 2017)은 inverse planning으로 타인의 목표를 추론:
`P(goal|actions, state) ∝ P(actions|goal, state) × P(goal)`

### 1.3 하위 Phase

| Sub-Phase | 목표 | 구현 순서 |
|-----------|------|----------|
| **E2-3: Theory of Mind** | 사용자(Caregiver) 모델링 + 감정/의도 추론 | **1st** (즉각적 체감 효과) |
| **E2-2: Temporal Pattern** | 시간 패턴 탐지 + prediction error 기반 surprise | **2nd** |
| **E2-1: Cross-Modal Binding** | 다중 감각 경험을 하나의 사건으로 통합 | **3rd** (시각 API 빈도 낮아 후순위) |

**구현 순서 근거**: 대화가 주 인터랙션이므로 UserModel(E2-3)이 즉각적 체감 효과가 가장 크다.
인지발달 순서(Cross-Modal→Temporal→ToM)와 다르나, 문서에서는 이론적 배경은 발달 순서로 기술하되
구현 우선순위는 실용성을 따른다.

---

## 2. 발달적 활성화 조건

### 2.1 인간 발달 ↔ 비비 Stage 매핑

| 인간 발달 | 월령 | 비비 Stage | 활성화 조건 |
|-----------|------|-----------|-----------|
| Self-other 구분 | 0~3개월 | 1 (INFANT) | experience_count >= 10 |
| Cross-modal binding | 3~6개월 | 2 (BABY) | experience_count >= 30 AND vision Experience >= 5 |
| 루틴 기대 형성 | 4~6개월 | 2 (BABY) | experience_count >= 50 AND 고유 날짜 >= 3일 |
| 이벤트 경계 탐지 | 6~9개월 | 3 (TODDLER) | experience_count >= 70 |
| Joint attention | 9~12개월 | 3 (TODDLER) | experience_count >= 100 AND UserModel >= 1 |
| Desire reasoning | 18~24개월 | 4 (CHILD) | experience_count >= 150 AND UserModel 존재 |
| Script formation | 24~36개월 | 4 (CHILD) | TemporalPattern >= 3개 |

### 2.2 Stage Gate 정의

```python
E2_GATES = {
    "user_model_basic":          {"min_stage": 3, "min_experiences": 100},
    "user_emotion_inference":    {"min_stage": 3, "min_experiences": 100},
    "user_desire_reasoning":     {"min_stage": 4, "min_experiences": 150},
    "temporal_pattern_detection": {"min_stage": 2, "min_experiences": 50},
    "temporal_surprise":         {"min_stage": 3, "min_experiences": 70},
    "cross_modal_binding":       {"min_stage": 2, "min_experiences": 30},
}
```

현재 stage=5, experience=3043+이므로 **모든 gate를 즉시 통과**한다.
그러나 코드에 gate를 남겨 향후 "처음부터 성장" 시나리오를 지원한다.

---

## 3. Database Schema (Neo4j)

### 3.1 E2-3: Theory of Mind

#### 새 노드: `UserModel`

```cypher
(:UserModel {
    id: UUID,
    name: String,                      -- "엄마", "형아", "아빠"
    speaker_id: String,                -- 외부 식별자 (API 전달)
    relationship: String,              -- "caregiver", "sibling", "friend", "unknown"
    inferred_interests: [String],      -- ["동물", "요리"]
    inferred_communication_style: String, -- "gentle", "playful", "strict"
    avg_emotion_toward_baby: String,   -- "warm", "neutral", "frustrated"
    recent_emotion: String,            -- 최근 추론 감정
    interaction_count: Int,
    last_interaction: ISO8601,
    first_interaction: ISO8601,
    preferred_time_slot: String,       -- 가장 자주 대화하는 시간대
    created_at: ISO8601,
    development_stage: Int
})
```

#### 새 관계: `INTERACTED_WITH`

```cypher
(:Experience)-[:INTERACTED_WITH {
    inferred_user_emotion: String,     -- "happy", "frustrated", "neutral"
    inferred_user_intent: String,      -- "teaching", "playing", "comforting", "asking"
    created_at: ISO8601
}]->(:UserModel)
```

#### 새 관계: `INTERESTED_IN`

```cypher
(:UserModel)-[:INTERESTED_IN {
    mention_count: Int,
    last_mentioned: ISO8601,
    strength: Float                    -- 0.0~1.0
}]->(:Concept)
```

#### Experience 노드 확장 속성

```
speaker_id: String            -- 누가 말했는지
inferred_user_emotion: String -- 사용자 감정 추론 결과
inferred_user_intent: String  -- 사용자 의도 추론 결과
hour_of_day: Int              -- 0~23
time_of_day: String           -- "morning"/"afternoon"/"evening"/"night"
```

### 3.2 E2-2: Temporal Pattern Recognition

#### 새 노드: `TemporalPattern`

```cypher
(:TemporalPattern {
    id: UUID,
    pattern_type: String,         -- "routine", "sequence", "co-occurrence"
    name: String,                 -- "morning_greeting", "bedtime_story"
    description: String,
    time_slot: String,            -- "morning", "afternoon", "evening", "night"
    hour_range_start: Int,        -- 7
    hour_range_end: Int,          -- 9
    occurrence_count: Int,
    confidence: Float,            -- 0.0~1.0
    last_occurred: ISO8601,
    transition_probability: Float,
    created_at: ISO8601,
    development_stage: Int
})
```

#### 새 관계: `EXHIBITS_PATTERN`

```cypher
(:Experience)-[:EXHIBITS_PATTERN {created_at: ISO8601}]->(:TemporalPattern)
```

#### 새 관계: `FOLLOWED_BY` (패턴 간 전이)

```cypher
(:TemporalPattern)-[:FOLLOWED_BY {
    transition_count: Int,
    transition_probability: Float,   -- count_AB / count_A
    created_at: ISO8601
}]->(:TemporalPattern)
```

#### 새 관계: `PATTERN_INVOLVES`

```cypher
(:TemporalPattern)-[:PATTERN_INVOLVES {
    frequency: Float     -- 패턴 내 개념 등장 비율
}]->(:Concept)
```

### 3.3 E2-1: Cross-Modal Binding

#### 새 노드: `MultimodalEvent`

```cypher
(:MultimodalEvent {
    id: UUID,
    time_window_start: ISO8601,
    time_window_end: ISO8601,
    modalities: [String],          -- ["conversation", "vision"]
    binding_strength: Float,       -- 0.0~1.0
    description: String,           -- LLM 생성 통합 설명 (선택)
    development_stage: Int,
    created_at: ISO8601
})
```

#### 새 관계: `PART_OF_EVENT`

```cypher
(:Experience)-[:PART_OF_EVENT {
    role: String,              -- "visual_input", "verbal_input", "verbal_response"
    temporal_offset_ms: Int,
    created_at: ISO8601
}]->(:MultimodalEvent)
```

### 3.4 AuraDB Free 제약 대비

| 항목 | 추정 증가량 | 현재 | 한도 |
|------|-----------|------|------|
| 노드 추가 | ~550 (UserModel ~5, TemporalPattern ~40, MultimodalEvent ~500) | ~9,000 | 200K |
| 관계 추가 | ~7,150 | ~2,500 | 400K |
| **합계** | 노드 ~9,550, 관계 ~9,650 | | 충분한 여유 |

### 3.5 필요 인덱스

```cypher
CREATE INDEX exp_hour IF NOT EXISTS FOR (e:Experience) ON (e.hour_of_day);
CREATE INDEX exp_speaker IF NOT EXISTS FOR (e:Experience) ON (e.speaker_id);
CREATE INDEX exp_created IF NOT EXISTS FOR (e:Experience) ON (e.created_at);
CREATE INDEX um_speaker IF NOT EXISTS FOR (um:UserModel) ON (um.speaker_id);
CREATE INDEX tp_time_slot IF NOT EXISTS FOR (tp:TemporalPattern) ON (tp.time_slot);
CREATE INDEX me_created IF NOT EXISTS FOR (me:MultimodalEvent) ON (me.created_at);
```

---

## 4. E2-3: Theory of Mind 구현 설계

### 4.1 사용자 식별

`handle_conversation(message, context)`의 `context` dict에서 추출:

```python
speaker_id = context.get("speaker_id", "unknown")
speaker_name = context.get("speaker_name")  # 최초 1회만 필요
```

프론트엔드에서 전달하는 요청 구조:
```json
{
    "message": "안녕 비비!",
    "speaker_id": "mom",
    "speaker_name": "엄마"
}
```

### 4.2 neo4j_db.py 추가 메서드

```python
async def get_or_create_user_model(
    self,
    speaker_id: str,
    speaker_name: str = None,
    relationship: str = "unknown",
) -> dict:
    """UserModel MERGE — 없으면 생성, 있으면 interaction_count 증가"""
    # MERGE (u:UserModel {speaker_id: $sid})
    # ON CREATE SET u.id = randomUUID(), u.name = $name, ...
    # ON MATCH SET u.interaction_count = u.interaction_count + 1, u.last_interaction = $now
    # RETURN u

async def link_experience_user(
    self,
    experience_id: str,
    user_model_id: str,
    inferred_emotion: str = "neutral",
    inferred_intent: str = "neutral",
) -> None:
    """Experience -[:INTERACTED_WITH]-> UserModel 관계 생성"""

async def update_user_interests(
    self,
    user_model_id: str,
    concept_ids: list[str],
) -> int:
    """UserModel -[:INTERESTED_IN]-> Concept 관계 MERGE (mention_count 증가)"""
    # UNWIND $concept_ids AS cid
    # MATCH (u:UserModel {id: $uid}), (c:Concept {id: cid})
    # MERGE (u)-[r:INTERESTED_IN]->(c)
    # ON CREATE SET r.mention_count = 1, r.strength = 0.3, r.last_mentioned = $now
    # ON MATCH SET r.mention_count = r.mention_count + 1,
    #              r.strength = CASE WHEN r.strength + 0.1 > 1.0 THEN 1.0 ELSE r.strength + 0.1 END,
    #              r.last_mentioned = $now

async def get_user_context(
    self,
    speaker_id: str,
) -> dict:
    """UserModel + 최근 관심사 + 통계 조회 (system prompt 구성용)"""
    # MATCH (u:UserModel {speaker_id: $sid})
    # OPTIONAL MATCH (u)-[r:INTERESTED_IN]->(c:Concept)
    # RETURN u, collect({name: c.name, strength: r.strength}) AS interests
```

### 4.3 사용자 감정 추론 (규칙 기반, LLM 없이)

```python
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
```

Stage >= 4에서 LLM 보조 의도 추론 (비용 절감: neutral이 아닌 경우에만):

```python
USER_INTENT_PROMPT = """사용자 메시지의 의도를 분류해줘.
카테고리: teaching, playing, comforting, asking, testing, scolding, praising, neutral
메시지: "{message}"
JSON으로만: {{"intent": "카테고리", "confidence": 0.0~1.0}}"""
```

### 4.4 System Prompt 통합

`_build_system_prompt(state)` 수정 — 사용자 정보 섹션 추가:

```python
if user_context:
    user_info = (
        f"\n[대화 상대 정보]\n"
        f"이름: {user_context['name']}\n"
        f"관계: {user_context['relationship']}\n"
        f"현재 감정: {user_context['recent_emotion']}\n"
        f"관심사: {', '.join(user_context.get('interests', []))}\n"
        f"대화 횟수: {user_context['interaction_count']}회\n"
    )
```

### 4.5 conversation_handler.py 통합 지점

**Step 1.5 (새로 추가)**: BabyState 조회 후, LLM 호출 전.

```python
# ── Step 1.5: 사용자 식별 + 감정 추론 (E2-3) ──────────────────────────
speaker_id = context.get("speaker_id", "unknown")
speaker_name = context.get("speaker_name")
user_model = None
user_emotion = "neutral"
user_intent = "neutral"

if speaker_id != "unknown":
    user_model = await db.get_or_create_user_model(
        speaker_id=speaker_id,
        speaker_name=speaker_name,
    )
    user_emotion = infer_user_emotion(message)

    # Stage >= 4: LLM 의도 추론 (neutral이 아닌 경우만)
    if stage >= 4 and user_emotion != "neutral":
        try:
            intent_resp = await asyncio.to_thread(
                llm.generate,
                prompt=USER_INTENT_PROMPT.format(message=message),
                model_key="gemini-2-flash",
                temperature=0.1,
                max_tokens=64,
            )
            intent_data = json.loads(intent_resp)
            user_intent = intent_data.get("intent", "neutral")
        except Exception:
            pass

user_context = None
if user_model:
    user_context = await db.get_user_context(speaker_id)
```

**Step 5.3 (새로 추가)**: 개념 추출 후, 사용자 관심사 업데이트.

```python
# ── Step 5.3: 사용자 관심사 업데이트 (E2-3) ────────────────────────────
if user_model and saved_concept_ids:
    try:
        await db.update_user_interests(user_model["id"], saved_concept_ids)
    except Exception as e:
        logger.warning(f"user interest update error: {e}")
```

**Step 4 수정**: insert_experience에 speaker_id, hour_of_day 등 추가.

```python
from datetime import datetime, timezone

now = datetime.now(timezone.utc)
hour = now.hour
time_of_day = (
    "morning" if 6 <= hour < 12 else
    "afternoon" if 12 <= hour < 17 else
    "evening" if 17 <= hour < 21 else
    "night"
)

experience = await db.insert_experience(
    task=message,
    task_type="conversation",
    output=response_text,
    success=success,
    emotional_salience=emotional_salience,
    dominant_emotion=new_emotions["dominant_emotion"],
    emotion_snapshot=new_emotions,
    development_stage=stage,
    tags=["conversation"],
    extras={
        "speaker_id": speaker_id,
        "inferred_user_emotion": user_emotion,
        "inferred_user_intent": user_intent,
        "hour_of_day": hour,
        "time_of_day": time_of_day,
    },
)
```

---

## 5. E2-2: Temporal Pattern Recognition 구현 설계

### 5.1 Experience 확장 (실시간)

Experience 저장 시 `hour_of_day`와 `time_of_day`를 extras에 추가 (4.5절 참조).
향후 `insert_experience()`에 정식 파라미터로 승격 가능.

### 5.2 패턴 탐지 (배치 — 수면 모드)

Phase 6 Memory Consolidation의 `replay_recent_memories()` 호출 시 함께 실행.

```python
async def detect_temporal_patterns(self) -> list[dict]:
    """시간대별 반복 개념 조합 탐지. 수면 모드에서 배치 실행."""
```

#### 탐지 Cypher

```cypher
MATCH (e:Experience)-[:INVOLVES]->(c:Concept)
WHERE e.task_type = 'conversation'
  AND e.extras IS NOT NULL
WITH e, c,
    CASE
        WHEN e.extras.hour_of_day >= 6 AND e.extras.hour_of_day < 12 THEN 'morning'
        WHEN e.extras.hour_of_day >= 12 AND e.extras.hour_of_day < 17 THEN 'afternoon'
        WHEN e.extras.hour_of_day >= 17 AND e.extras.hour_of_day < 21 THEN 'evening'
        ELSE 'night'
    END AS time_slot
WITH time_slot, c.name AS concept_name, c.id AS concept_id,
     count(DISTINCT e) AS occurrence_count,
     collect(DISTINCT date(datetime(e.created_at))) AS dates
WHERE occurrence_count >= 3
  AND size(dates) >= 2
RETURN time_slot, concept_name, concept_id, occurrence_count, size(dates) AS unique_days
ORDER BY occurrence_count DESC
LIMIT 20
```

#### TemporalPattern MERGE

```cypher
MERGE (tp:TemporalPattern {name: $name, time_slot: $time_slot})
ON CREATE SET
    tp.id = randomUUID(),
    tp.pattern_type = 'routine',
    tp.occurrence_count = $count,
    tp.confidence = $confidence,
    tp.created_at = datetime(),
    tp.development_stage = $stage
ON MATCH SET
    tp.occurrence_count = $count,
    tp.confidence = $confidence,
    tp.last_occurred = datetime()
```

### 5.3 Surprise 반응 (실시간 — Step 1.5)

대화 시작 시 현재 시간대에 예상되는 패턴을 조회하고, 실제와 비교:

```python
async def check_temporal_expectations(
    self,
    current_hour: int,
) -> dict:
    """현재 시간대 예상 패턴 조회"""
    # MATCH (tp:TemporalPattern {time_slot: $slot})
    # WHERE tp.confidence > 0.3
    # RETURN tp ORDER BY tp.confidence DESC LIMIT 5
```

Surprise 계산:
```python
def compute_surprise(expected_patterns: list, current_time_slot: str, is_first_today: bool) -> float:
    """
    예상 패턴이 있는데 다른 시간대에 대화 → surprise 높음
    예상 패턴대로 대화 → surprise 낮음 (comfort)
    """
    if not expected_patterns:
        return 0.1  # 패턴 없으면 약간의 novelty

    matching = [p for p in expected_patterns if p["time_slot"] == current_time_slot]
    if matching:
        return 0.0  # 예상대로
    else:
        return 0.5  # 예상 외 시간
```

감정 피드백:
- `surprise > 0.3` → surprise 감정 +0.15, curiosity +0.05
- `surprise == 0.0` → joy +0.03 (예상대로의 편안함)

### 5.4 Transitional Probability (배치)

```python
async def compute_transition_probabilities(self) -> int:
    """같은 날 연속 대화의 개념 전이 확률 계산 → FOLLOWED_BY 관계 MERGE"""
```

```cypher
MATCH (tp1:TemporalPattern)-[:PATTERN_INVOLVES]->(c1:Concept)
      <-[:INVOLVES]-(e1:Experience)
MATCH (e2:Experience)-[:INVOLVES]->(c2:Concept)
      <-[:PATTERN_INVOLVES]-(tp2:TemporalPattern)
WHERE tp1.id <> tp2.id
  AND date(datetime(e1.created_at)) = date(datetime(e2.created_at))
  AND datetime(e2.created_at) > datetime(e1.created_at)
  AND duration.between(datetime(e1.created_at), datetime(e2.created_at)).minutes <= 60
WITH tp1, tp2, count(*) AS pair_count
MATCH (e:Experience)-[:EXHIBITS_PATTERN]->(tp1)
WITH tp1, tp2, pair_count, count(e) AS tp1_total
MERGE (tp1)-[r:FOLLOWED_BY]->(tp2)
SET r.transition_count = pair_count,
    r.transition_probability = toFloat(pair_count) / tp1_total,
    r.created_at = datetime()
RETURN count(r) AS updated
```

---

## 6. E2-1: Cross-Modal Binding 구현 설계

### 6.1 시간 근접성 기반 그룹핑

두 Experience의 `created_at` 차이가 **60초 이내**이고 서로 다른 modality이면,
같은 MultimodalEvent로 묶는다.

### 6.2 neo4j_db.py 추가 메서드

```python
BINDING_TIME_WINDOW_SEC = 60

async def attempt_cross_modal_binding(
    self,
    experience_id: str,
    task_type: str,
) -> Optional[str]:
    """시간 창 내 다른 modality Experience가 있으면 MultimodalEvent로 묶기"""
```

#### 시간 근접 Experience 탐색 Cypher

```cypher
MATCH (new:Experience {id: $exp_id})
MATCH (other:Experience)
WHERE other.id <> new.id
  AND other.task_type <> new.task_type
  AND other.task_type IN ['conversation', 'vision']
  AND abs(duration.between(datetime(other.created_at), datetime(new.created_at)).seconds) <= $window
  AND NOT EXISTS {
      MATCH (other)-[:PART_OF_EVENT]->(:MultimodalEvent)<-[:PART_OF_EVENT]-(new)
  }
RETURN other
ORDER BY abs(duration.between(datetime(other.created_at), datetime(new.created_at)).seconds) ASC
LIMIT 5
```

### 6.3 Binding Strength 계산

```python
def compute_binding_strength(
    temporal_gap_sec: float,
    shared_concepts: int,
    emotional_similarity: float,
) -> float:
    """
    Bayesian Causal Inference 단순화:
    P(common_cause) ∝ temporal_proximity × concept_overlap × emotional_coherence
    """
    temporal = max(0, 1.0 - temporal_gap_sec / BINDING_TIME_WINDOW_SEC)
    concept_factor = min(1.0, shared_concepts / 3.0)
    strength = 0.5 * temporal + 0.3 * concept_factor + 0.2 * emotional_similarity
    return round(min(1.0, strength), 3)
```

### 6.4 conversation_handler.py 통합 지점

**Step 4.5**: Experience 저장(Step 4) 직후, 개념 추출(Step 5) 이전.
`asyncio.create_task()`로 fire-and-forget 가능 (응답 차단 없음).

```python
# ── Step 4.5: Cross-Modal Binding (E2-1) ────────────────────────────────
if stage >= 2:
    asyncio.create_task(
        db.attempt_cross_modal_binding(experience_id, "conversation")
    )
```

---

## 7. 파이프라인 통합 요약

### 7.1 수정된 conversation_handler.py 파이프라인

```
Step 1    : get_baby_state()                                    [기존]
Step 1.5  : identify_user + infer_emotion + temporal_check      [NEW: E2-3, E2-2]
Step 2    : LLM 호출 (system prompt에 사용자 정보 포함)           [수정]
Step 3    : 감정 업데이트 (surprise 반영)                         [수정]
Step 4    : insert_experience (speaker_id, hour_of_day 추가)     [수정]
Step 4.5  : cross_modal_binding (fire-and-forget)               [NEW: E2-1]
Step 5    : 개념 추출 + 저장                                     [기존]
Step 5.3  : update_user_interests                               [NEW: E2-3]
Step 5.5  : spreading activation                                [기존]
Step 5.6  : hebbian learning                                    [기존]
Step 5.7  : internal simulation (D1)                            [기존]
Step 6    : emotion log                                         [기존]
Step 7    : baby state update                                   [기존]
Step 7.5  : development stage check (D3)                        [기존]
Step 8    : Redis publish + return                              [기존]
```

### 7.2 성능 영향

| 새 Step | 추가 쿼리 | 예상 지연 | 비동기 |
|---------|----------|----------|-------|
| Step 1.5 사용자 MERGE | 1 | ~20ms | No (Step 2 필요) |
| Step 1.5 감정 추론 | 0 (규칙) | ~1ms | N/A |
| Step 1.5 시간 기대 | 1 | ~15ms | No (Step 3 필요) |
| Step 4.5 cross-modal | 1~2 | ~30ms | Yes (fire-and-forget) |
| Step 5.3 관심사 | ~5 (개념당) | ~25ms | Yes (fire-and-forget) |
| **총 추가** | **4~9** | **~90ms** | |

현재 응답 시간은 LLM(~500-1500ms) 지배적이므로 ~90ms 추가는 수용 가능.

---

## 8. Frontend 확장 (개요)

| 시각화 | 위치 | 설명 |
|--------|------|------|
| User Model Cards | Settings 또는 "People" 탭 | 이름, 관심사 태그 클라우드, 감정 추이, 마지막 대화 |
| Temporal Pattern Panel | Brain Dashboard 내 탭 | 탐지된 루틴, confidence, "예상 vs 실제" indicator |
| Multimodal Timeline | Brain Dashboard 하단 | vision/conversation 이벤트 컬러 코딩, 연결선 |
| Surprise Indicator | 대화 UI 감정 영역 | 예상치 못한 시간/패턴 시 짧은 애니메이션 |

### API 엔드포인트 추가

```
GET  /api/users                    -- UserModel 목록
GET  /api/users/{speaker_id}       -- 특정 사용자 상세 + 관심사
GET  /api/temporal-patterns        -- TemporalPattern 목록
GET  /api/multimodal-events        -- MultimodalEvent 목록
POST /api/conversation (수정)      -- speaker_id, speaker_name 파라미터 추가
```

---

## 9. 검증 계획

### 9.1 E2-3 (ToM) 성공 지표

| 지표 | 목표 | 측정 |
|------|------|------|
| UserModel 생성 | speaker_id 첫 등장 시 100% | API 호출 → Neo4j 확인 |
| 감정 추론 정확도 | > 70% | 20개 샘플 수동 라벨링 대비 비교 |
| 관심사 추적 | 3회+ 언급 주제가 INTERESTED_IN에 존재 | Neo4j 쿼리 |
| 응답 적응 | 사용자별 다른 톤 | 같은 질문을 엄마/형아로 보내어 비교 |

### 9.2 E2-2 (Temporal) 성공 지표

| 지표 | 목표 | 측정 |
|------|------|------|
| 패턴 탐지 precision | > 80% | 3일간 같은 시간 대화 후 탐지 확인 |
| Surprise 적절성 | 예상 외 시간 → surprise 증가 | 평소와 다른 시간에 대화 시도 |
| TemporalPattern 수 | 1주 운용 후 5~15개 | Neo4j count |

### 9.3 E2-1 (Cross-Modal) 성공 지표

| 지표 | 목표 | 측정 |
|------|------|------|
| Binding 생성률 | 시각+대화 60초 내 → 100% | 이미지 분석 직후 대화 |
| 오결합 | < 5% | 60초+ 차이 경험이 묶이지 않음 확인 |
| binding_strength | 평균 > 0.5 | Neo4j 집계 |

### 9.4 통합 시나리오

| 시나리오 | 기대 결과 |
|---------|----------|
| 엄마가 사과 사진 + "이건 뭐야?" | MultimodalEvent binding + UserModel 엄마 + Concept 사과 INTERESTED_IN |
| 매일 오전 9시 "안녕" 3일 반복 | TemporalPattern "morning_greeting" 생성 |
| 4일째 오후 3시 "안녕" | surprise 증가, 비비 "어? 오늘은 늦게 왔네?" 반영 |
| 형아가 게임 얘기 후 갑자기 "슬퍼" | UserModel 형아 recent_emotion 변경, 비비 톤 변화 |

---

## Appendix A: 설계 결정 기록

| 결정 | 선택 | 대안 | 근거 |
|------|------|------|------|
| Cross-modal을 별도 노드? | 별도 MultimodalEvent | Experience에 event_group_id | 그래프 DB 장점. 이벤트 자체에 속성(binding_strength) 부여 가능 |
| 패턴 탐지 실시간 vs 배치? | 배치 (수면 모드) | 매 대화마다 | 충분한 데이터 축적 후 의미 있음. surprise 체크만 실시간 |
| 사용자 감정 LLM vs 규칙? | 하이브리드 | LLM only / 규칙 only | 규칙은 빠르고 비용 없음. 복잡한 의도만 LLM. 프로젝트 철학에 부합 |
| speaker_id 자동 vs 명시? | 명시 (API 파라미터) | 대화에서 추론 | 정확도 보장. 자동 추론은 보조적 |
| 구현 순서 | E2-3→2→1 (실용) | E2-1→2→3 (발달) | 대화가 주 인터랙션, UserModel 체감 효과 최대 |

## Appendix B: 참고 문헌

- Bahrick, L. E., & Lickliter, R. (2000). Intersensory redundancy guides attentional selectivity. *Dev. Psychology*, 36(2).
- Baker, C. L. et al. (2017). Rational quantitative attribution of beliefs, desires and percepts. *Nature Human Behaviour*, 1.
- Kording, K. P. et al. (2007). Causal inference in multisensory perception. *PLoS ONE*, 2(9).
- Nelson, K. (1986). *Event Knowledge: Structure and Function in Development*. Erlbaum.
- Saffran, J. R. et al. (1996). Statistical learning by 8-month-old infants. *Science*, 274(5294).
- Wellman, H. M. (1990). *The Child's Theory of Mind*. MIT Press.
- Zacks, J. M. et al. (2007). Event perception: A mind-brain perspective. *Psychological Bulletin*, 133(2).
