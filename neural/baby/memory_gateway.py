"""memory_gateway — 답하기 전 회상 + 놀람 게이트 (A단계).

설계 정본: Bandi 볼트 `A2A/비비 다음 뇌 설계 — VoiceMem 좌·우뇌를 넘어서 (2026-09-06).md` 5.3~5.5절.

원칙
- 옵트인: 환경변수 ``MEMORY_GATEWAY=1`` 일 때만 동작한다. 꺼져 있으면 모든 진입점이 아무것도 하지 않는다.
- ``conversation_handler.py`` 는 두 줄(import + augment 호출)만 건드린다. 나머지 사후 갱신은
  ``api_server`` 가 ``post_turn`` 을 호출해서 한다.
- 새 Cypher 는 전부 이 파일의 ``Neo4jGatewayStore`` 에 둔다. 테스트는 ``FakeStore`` 로 돌린다.
- 수치는 설계 노트의 추정값이다. 이름 옆에 (추정) 을 붙였다.

흐름 (한 턴)
  augment_system_prompt:
    1) 발화 Concept 추출(기존 규칙 기반 추출기 재사용)
    2) 예측 확산(시드 = 세션 버퍼) → 예상 Concept 집합
    3) 오차 = 1 − 자카드(예상, 관측) → σ_c(화자별) 로 나눠 z. 워밍업 동안은 게이트 없음
    4) 인출: 화자 라우팅 → 후보(어휘·벡터·확산) RRF 융합 → 점수 = strength × 관련성 → 소프트맥스(T_eff) 로 K=5
    5) conf·FOK 계산, 프롬프트 블록 생성(≈430토큰 예산), 세션 버퍼 갱신
  post_turn:
    6) write_priority = (1 + min(z,3)/3) × (1 + self_arousal)/2 → strength ×= write_priority
    7) self_/speaker_ valence·arousal, surprise_z, channel, access_ts 기록
    8) FEELS_ABOUT 갱신, 회상된 노드 access_ts 추가
    9) NE 버스트면 추가 Hebbian 증분(η_eff − 1)과 태깅 창(직전 M분) 강화
"""
from __future__ import annotations

import asyncio
import logging
import math
import os
import random
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Iterable, Optional, Protocol

logger = logging.getLogger("baby.memory_gateway")

# ── 설정 (설계 노트 추정값) ────────────────────────────────────────────────
GATEWAY_ENV = "MEMORY_GATEWAY"
K_INJECT = 5                      # 답에 주입하는 기억 수 (VoiceMem·HippoRAG top-5 기준)
THETA = 2.0                       # NE 버스트 문턱 (추정)
SIGMA_WARMUP_TURNS = 50           # σ_c 워밍업 턴 수 (추정)
SIGMA_FLOOR = 0.05                # σ_c 하한 (0 나눗셈 방지, 추정)
TAG_WINDOW_MIN = 60               # 태깅 창 M (분, 추정)
TAG_RELATEDNESS_MIN = 0.3         # 태깅 관련성 문턱 ρ (자카드, 추정)
TAG_BOOST = 0.1                   # 태깅 상향량 (× 관련성, 추정)
BURST_FACTOR = 1.5                # η·T 버스트 배수 (추정)
HEBB_DIRECT = 0.05                # 기존 직접 공출현 증분 (conversation_handler 와 동일)
HEBB_CROSS = 0.02                 # 기존 교차 증분
PROMPT_CHAR_BUDGET = 900          # ≈430 토큰 (한국어, 추정)
CONF_SCALE = 0.1                  # 확신도 온도 s (점수 범위 0~1 기준, 추정)
FOK_THRESHOLD = 0.2               # "모른다" 판정 τ_FOK (추정)
SPEAKER_BUDGET = 20               # 화자별 후보 예산 (× social_salience, 추정)
RRF_K = 60                        # 역순위 융합 상수 (통상값)
PROMPT_SNIPPET_CHARS = 60         # 회상 항목당 본문 글자 수 (추정)

# 발달 단계별 값 (5.9 표). 유아 열 = NEWBORN(0), 아동 열 = YOUTH(5), 사이는 선형 보간 (추정)
_STAGE_MIN, _STAGE_MAX = 0, 5
_STAGE_TABLE = {
    "eta": (1.5, 1.0),
    "temp": (1.5, 1.0),
    "w": (3, 5),
}

# 화자 정서 사상표 (A0, 추정): 키워드 사전(happy, frustrated, sad, curious, angry, neutral) → (valence, arousal)
SPEAKER_AFFECT: dict[str, tuple[float, float]] = {
    "happy": (1.0, 0.6),
    "curious": (0.5, 0.6),
    "neutral": (0.0, 0.3),
    "sad": (-1.0, 0.3),
    "frustrated": (-1.0, 0.7),
    "angry": (-1.0, 0.9),
}

# Hebbian 공출현 관계에서 확산 활성화가 쓰는 깊이·개수 (z 로 정함, 추정)
_SPREAD_CALM = (2, 20)
_SPREAD_BURST = (3, 30)


def enabled() -> bool:
    return os.getenv(GATEWAY_ENV, "0") == "1"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


# ── 순수 함수 ──────────────────────────────────────────────────────────────
def stage_value(name: str, stage: int) -> float:
    """5.9 표의 선형 보간. stage 는 0(NEWBORN)~5(YOUTH)."""
    lo, hi = _STAGE_TABLE[name]
    t = (max(_STAGE_MIN, min(_STAGE_MAX, int(stage))) - _STAGE_MIN) / (_STAGE_MAX - _STAGE_MIN)
    return lo + (hi - lo) * t


def jaccard(a: Iterable[str], b: Iterable[str]) -> float:
    sa, sb = set(a), set(b)
    if not sa and not sb:
        return 1.0
    return len(sa & sb) / len(sa | sb)


def prediction_error(predicted: Iterable[str], observed: Iterable[str]) -> float:
    """오차 = 1 − 자카드(예상 Concept, 관측 Concept). 둘 다 비면 0."""
    sp, so = set(predicted), set(observed)
    if not sp and not so:
        return 0.0
    return 1.0 - jaccard(sp, so)


def core_affect(emotions: dict) -> tuple[float, float]:
    """비비 자신의 6감정 → 코어 어펙트 (valence ∈ [−1, 1], arousal ∈ [0, 1]).

    arousal 은 conversation_handler 의 emotional_salience 식 그대로.
    valence 는 (joy + curiosity − fear − frustration − boredom)/5 (계수 1, /5 로 척도 맞춤, 추정).
    """
    g = lambda k: float(emotions.get(k, 0.0) or 0.0)
    arousal = g("joy") * 0.3 + g("curiosity") * 0.3 + g("surprise") * 0.2 + g("fear") * 0.2
    valence = (g("joy") + g("curiosity") - g("fear") - g("frustration") - g("boredom")) / 5.0
    return max(-1.0, min(1.0, valence)), max(0.0, min(1.0, arousal))


def speaker_affect(word: Optional[str]) -> tuple[float, float]:
    return SPEAKER_AFFECT.get((word or "neutral").lower(), SPEAKER_AFFECT["neutral"])


def write_priority(z: float, self_arousal: float) -> float:
    """(1 + min(z, 3)/3) × (1 + self_arousal)/2, 범위 0.5~2 (추정 식)."""
    return (1.0 + min(max(z, 0.0), 3.0) / 3.0) * (1.0 + max(0.0, min(1.0, self_arousal))) / 2.0


def sigmoid(x: float) -> float:
    if x >= 0:
        ez = math.exp(-x)
        return 1.0 / (1.0 + ez)
    ez = math.exp(x)
    return ez / (1.0 + ez)


def rrf_fuse(ranked_lists: list[list[str]], k: int = RRF_K) -> dict[str, float]:
    """역순위 융합. 각 목록의 r번째(0부터) 항목에 1/(k+r+1) 을 더한다."""
    scores: dict[str, float] = {}
    for lst in ranked_lists:
        for r, item in enumerate(lst):
            scores[item] = scores.get(item, 0.0) + 1.0 / (k + r + 1)
    return scores


def normalize_tokens(text: str) -> set[str]:
    """conversation_handler 의 조사·어미 정규화를 재사용한다(순환 import 를 피하려 지연 import)."""
    from .conversation_handler import _normalize_token  # noqa: WPS433
    out: set[str] = set()
    for w in (text or "").split():
        tok = _normalize_token(w)
        if tok:
            out.add(tok)
    return out


def extract_cue_concepts(message: str) -> set[str]:
    from .conversation_handler import _extract_concepts_from_response  # noqa: WPS433
    return set(_extract_concepts_from_response("", message or ""))


def lexical_relevance(query_tokens: set[str], doc_text: str) -> float:
    """어휘 일치 점수(BM25 대용, 추정): |교집합| / sqrt(|q|·|d|)."""
    if not query_tokens:
        return 0.0
    d = normalize_tokens(doc_text)
    if not d:
        return 0.0
    return len(query_tokens & d) / math.sqrt(len(query_tokens) * len(d))


def softmax_select(items: list[tuple[str, float]], k: int, temperature: float,
                   rng: Optional[random.Random] = None) -> list[tuple[str, float]]:
    """점수 소프트맥스(온도 T)로 k개 비복원 추출. rng 가 없으면 결정론적 상위 k."""
    if not items:
        return []
    if rng is None or len(items) <= k:
        return sorted(items, key=lambda x: x[1], reverse=True)[:k]
    pool = list(items)
    chosen: list[tuple[str, float]] = []
    scale = CONF_SCALE * max(temperature, 1e-6)
    while pool and len(chosen) < k:
        mx = max(s for _, s in pool)
        weights = [math.exp((s - mx) / scale) for _, s in pool]
        pick = rng.choices(range(len(pool)), weights=weights, k=1)[0]
        chosen.append(pool.pop(pick))
    return chosen


# ── σ_c 표와 세션 버퍼 ─────────────────────────────────────────────────────
class SigmaTable:
    """맥락(화자)별 오차의 평균·표준편차를 온라인으로 추적한다(Welford)."""

    def __init__(self, warmup_turns: int = SIGMA_WARMUP_TURNS, floor: float = SIGMA_FLOOR):
        self.warmup = warmup_turns
        self.floor = floor
        self._stats: dict[str, tuple[int, float, float]] = {}

    def observe(self, key: str, err: float) -> tuple[float, bool]:
        n, mean, m2 = self._stats.get(key, (0, 0.0, 0.0))
        n += 1
        delta = err - mean
        mean += delta / n
        m2 += delta * (err - mean)
        self._stats[key] = (n, mean, m2)
        return self.sigma(key), n <= self.warmup

    def sigma(self, key: str) -> float:
        n, _, m2 = self._stats.get(key, (0, 0.0, 0.0))
        if n < 2:
            return self.floor
        return max(self.floor, math.sqrt(m2 / (n - 1)))

    def z(self, key: str, err: float) -> float:
        n, _, _ = self._stats.get(key, (0, 0.0, 0.0))
        if n <= self.warmup:
            return 0.0
        return err / self.sigma(key)

    def count(self, key: str) -> int:
        return self._stats.get(key, (0, 0.0, 0.0))[0]


class SessionBuffer:
    """작업기억. 슬롯 하나 = 한 턴의 Concept 집합. z > θ 였던 턴은 축출을 한 번 건너뛴다(추정)."""

    def __init__(self, slots: int):
        self.slots = max(0, int(slots))
        self._q: deque[dict] = deque()

    def push(self, concepts: Iterable[str], burst: bool = False) -> None:
        if self.slots == 0:
            return
        self._q.append({"c": set(concepts), "pin": bool(burst)})
        while len(self._q) > self.slots:
            self._evict_one()

    def _evict_one(self) -> None:
        for i, slot in enumerate(self._q):
            if slot["pin"]:
                slot["pin"] = False   # 한 번 건너뛰고 다음엔 나간다
                continue
            del self._q[i]
            return
        self._q.popleft()

    def seeds(self) -> set[str]:
        out: set[str] = set()
        for slot in self._q:
            out |= slot["c"]
        return out

    def __len__(self) -> int:
        return len(self._q)


# ── 저장소 인터페이스 ──────────────────────────────────────────────────────
class GatewayStore(Protocol):
    async def clearance(self, speaker_id: str) -> str: ...
    async def experiences_for_speaker(self, speaker_id: str, clearance: str, limit: int) -> list[dict]: ...
    async def spread(self, concept_names: Iterable[str], depth: int, limit: int) -> list[str]: ...
    async def vector_search(self, text: str, limit: int) -> list[dict]: ...
    async def known_concepts(self, names: Iterable[str]) -> set[str]: ...
    async def experience_concepts(self, experience_id: str) -> list[tuple[str, str]]: ...
    async def update_experience(self, experience_id: str, props: dict, strength_mult: float) -> None: ...
    async def touch_access(self, experience_ids: Iterable[str], concept_ids: Iterable[str], ts: str) -> None: ...
    async def upsert_feels_about(self, speaker_id: str, concept_ids: Iterable[str], valence: float, arousal: float, ts: str) -> None: ...
    async def hebbian_update(self, pairs: list[tuple[str, str]], strength_delta: float, source: str) -> int: ...
    async def recent_experiences(self, since_iso: str, exclude_id: Optional[str]) -> list[dict]: ...
    async def boost_strength(self, experience_id: str, delta: float) -> None: ...


class Neo4jGatewayStore:
    """BrainDatabase(neo4j_db.py) 위의 얇은 Cypher 층. 기존 함수는 그대로 재사용한다."""

    def __init__(self, db):
        self.db = db

    @property
    def _dbname(self):
        from . import neo4j_db  # noqa: WPS433
        return neo4j_db._DB_NAME

    async def clearance(self, speaker_id: str) -> str:
        return await self.db.resolve_speaker_clearance(speaker_id)

    async def experiences_for_speaker(self, speaker_id: str, clearance: str, limit: int) -> list[dict]:
        async with self.db.driver.session(database=self._dbname) as s:
            if speaker_id and speaker_id != "unknown":
                q = (
                    "MATCH (e:Experience)-[:INTERACTED_WITH]->(u:UserModel {speaker_id: $sid}) "
                    "WHERE e.valid_to IS NULL AND NOT e:Cold "
                    "WITH e ORDER BY e.created_at DESC LIMIT $limit "
                    "OPTIONAL MATCH (e)-[:INVOLVES]->(c:Concept) "
                    "WHERE coalesce(c.access_tier, 'public') = 'public' OR $clearance = 'owner' "
                    "RETURN e, collect(c.name) AS concept_names, collect(c.id) AS concept_ids"
                )
                params = {"sid": speaker_id, "limit": int(limit), "clearance": clearance}
            else:
                q = (
                    "MATCH (e:Experience) "
                    "WHERE e.task_type = 'conversation' AND e.valid_to IS NULL AND NOT e:Cold "
                    "WITH e ORDER BY e.created_at DESC LIMIT $limit "
                    "OPTIONAL MATCH (e)-[:INVOLVES]->(c:Concept) "
                    "WHERE coalesce(c.access_tier, 'public') = 'public' OR $clearance = 'owner' "
                    "RETURN e, collect(c.name) AS concept_names, collect(c.id) AS concept_ids"
                )
                params = {"limit": int(limit), "clearance": clearance}
            result = await s.run(q, **params)
            records = await result.fetch(int(limit))
            out = []
            for r in records:
                e = dict(r["e"])
                e["concept_names"] = [n for n in r["concept_names"] if n]
                e["concept_ids"] = [i for i in r["concept_ids"] if i]
                out.append(e)
            return out

    async def spread(self, concept_names: Iterable[str], depth: int, limit: int) -> list[str]:
        names = [n for n in set(concept_names) if n]
        if not names:
            return []
        async with self.db.driver.session(database=self._dbname) as s:
            result = await s.run("MATCH (c:Concept) WHERE c.name IN $names RETURN c.id AS id", names=names)
            ids = [r["id"] for r in await result.fetch(len(names))]
        if not ids:
            return []
        activated = await self.db.get_spreading_activation(ids, depth=depth, limit=limit)
        activated.sort(key=lambda a: float(a.get("activation_strength") or 0.0), reverse=True)
        # 기존 확산 쿼리는 경로마다 한 행을 돌려줘 같은 개념이 여러 번 온다. 순서를 지키며 중복을 없앤다.
        seen: set[str] = set()
        out: list[str] = []
        for a in activated:
            name = a.get("name")
            if name and name not in seen:
                seen.add(name)
                out.append(name)
        return out

    async def vector_search(self, text: str, limit: int) -> list[dict]:
        try:
            from .embeddings import safe_create_embedding  # noqa: WPS433
            emb = safe_create_embedding(text)
        except Exception as e:  # pragma: no cover - 외부 의존
            logger.debug(f"embedding unavailable: {e}")
            emb = None
        if not emb:
            return []
        try:
            return await self.db.search_similar_experiences(emb, threshold=0.5, limit=limit)
        except Exception as e:  # pragma: no cover - 인덱스 부재 등
            logger.debug(f"vector search unavailable: {e}")
            return []

    async def known_concepts(self, names: Iterable[str]) -> set[str]:
        names = [n for n in set(names) if n]
        if not names:
            return set()
        async with self.db.driver.session(database=self._dbname) as s:
            result = await s.run("MATCH (c:Concept) WHERE c.name IN $names RETURN c.name AS name", names=names)
            return {r["name"] for r in await result.fetch(len(names))}

    async def experience_concepts(self, experience_id: str) -> list[tuple[str, str]]:
        async with self.db.driver.session(database=self._dbname) as s:
            result = await s.run(
                "MATCH (e:Experience {id: $eid})-[:INVOLVES]->(c:Concept) RETURN c.id AS id, c.name AS name",
                eid=experience_id,
            )
            return [(r["id"], r["name"]) for r in await result.fetch(200)]

    async def update_experience(self, experience_id: str, props: dict, strength_mult: float) -> None:
        async with self.db.driver.session(database=self._dbname) as s:
            await s.run(
                "MATCH (e:Experience {id: $eid}) SET e += $props "
                "SET e.strength = CASE WHEN coalesce(e.strength, 0.5) * $mult > 1.0 THEN 1.0 "
                "                      ELSE coalesce(e.strength, 0.5) * $mult END "
                "SET e.access_ts = coalesce(e.access_ts, [])",
                eid=experience_id, props=props, mult=float(strength_mult),
            )

    async def touch_access(self, experience_ids: Iterable[str], concept_ids: Iterable[str], ts: str) -> None:
        eids, cids = [i for i in set(experience_ids) if i], [i for i in set(concept_ids) if i]
        async with self.db.driver.session(database=self._dbname) as s:
            if eids:
                await s.run(
                    "MATCH (e:Experience) WHERE e.id IN $ids "
                    "SET e.access_ts = coalesce(e.access_ts, []) + [$ts]", ids=eids, ts=ts,
                )
            if cids:
                await s.run(
                    "MATCH (c:Concept) WHERE c.id IN $ids "
                    "SET c.access_ts = coalesce(c.access_ts, []) + [$ts]", ids=cids, ts=ts,
                )

    async def upsert_feels_about(self, speaker_id: str, concept_ids: Iterable[str],
                                 valence: float, arousal: float, ts: str) -> None:
        cids = [i for i in set(concept_ids) if i]
        if not cids or not speaker_id or speaker_id == "unknown":
            return
        async with self.db.driver.session(database=self._dbname) as s:
            await s.run(
                "MATCH (u:UserModel {speaker_id: $sid}) "
                "MATCH (c:Concept) WHERE c.id IN $cids "
                "MERGE (u)-[f:FEELS_ABOUT]->(c) "
                "ON CREATE SET f.valence = $v, f.arousal = $a, f.count = 1, f.last_seen = $ts, f.source = 'speaker' "
                "ON MATCH SET f.valence = (f.valence * f.count + $v) / (f.count + 1), "
                "             f.arousal = (f.arousal * f.count + $a) / (f.count + 1), "
                "             f.count = f.count + 1, f.last_seen = $ts",
                sid=speaker_id, cids=cids, v=float(valence), a=float(arousal), ts=ts,
            )

    async def hebbian_update(self, pairs: list[tuple[str, str]], strength_delta: float, source: str) -> int:
        if not pairs:
            return 0
        return await self.db.hebbian_update(pairs, strength_delta=strength_delta, source=source)

    async def recent_experiences(self, since_iso: str, exclude_id: Optional[str]) -> list[dict]:
        async with self.db.driver.session(database=self._dbname) as s:
            result = await s.run(
                "MATCH (e:Experience) WHERE e.created_at >= $since AND e.id <> coalesce($ex, '') "
                "OPTIONAL MATCH (e)-[:INVOLVES]->(c:Concept) "
                "RETURN e.id AS id, collect(c.name) AS concept_names",
                since=since_iso, ex=exclude_id,
            )
            return [{"id": r["id"], "concept_names": [n for n in r["concept_names"] if n]}
                    for r in await result.fetch(500)]

    async def boost_strength(self, experience_id: str, delta: float) -> None:
        async with self.db.driver.session(database=self._dbname) as s:
            await s.run(
                "MATCH (e:Experience {id: $eid}) "
                "SET e.strength = CASE WHEN coalesce(e.strength, 0.5) + $d > 1.0 THEN 1.0 "
                "                      ELSE coalesce(e.strength, 0.5) + $d END",
                eid=experience_id, d=float(delta),
            )


# ── 턴 상태와 게이트웨이 ───────────────────────────────────────────────────
@dataclass
class TurnState:
    speaker_id: str
    stage: int
    cue: set[str]
    predicted: set[str]
    error: float
    sigma: float
    z: float
    burst: bool
    warm: bool
    recalled: list[dict] = field(default_factory=list)
    conf: float = 0.0
    fok: float = 0.0
    created_at: str = ""


@dataclass
class RecallResult:
    ranked: list[dict]
    conf: float
    fok: float
    block: str


class MemoryGateway:
    def __init__(self, store: GatewayStore, rng: Optional[random.Random] = None,
                 clock=None, theta: float = THETA, warmup_turns: int = SIGMA_WARMUP_TURNS):
        self.store = store
        self.rng = rng
        self.clock = clock or _now
        self.theta = theta
        self.sigma = SigmaTable(warmup_turns=warmup_turns)
        self.buffers: dict[str, SessionBuffer] = {}
        self.turns: dict[str, TurnState] = {}
        self.affect_state: dict[str, dict] = {}
        self.last_depth: dict[str, tuple[int, int]] = {}

    # ---- 보조 ----
    def _buffer(self, speaker_id: str, stage: int) -> SessionBuffer:
        w = int(round(stage_value("w", stage)))
        w = int(os.getenv("MEMORY_GATEWAY_W", w))
        buf = self.buffers.get(speaker_id)
        if buf is None or buf.slots != w:
            new = SessionBuffer(w)
            if buf is not None:
                for slot in list(buf._q):
                    new.push(slot["c"], slot["pin"])
            buf = self.buffers[speaker_id] = new
        return buf

    async def _recall(self, message: str, cue: set[str], seeds: set[str], speaker_id: str,
                      stage: int, z: float, burst: bool) -> RecallResult:
        clearance = await self.store.clearance(speaker_id)
        pool = await self.store.experiences_for_speaker(speaker_id, clearance, SPEAKER_BUDGET)
        by_id = {e.get("id"): e for e in pool if e.get("id")}
        if not by_id:
            return RecallResult([], 0.0, 0.0, "")

        # (a) 어휘 일치
        qtok = normalize_tokens(message) | set(cue)
        lex = sorted(
            ((eid, lexical_relevance(qtok, f"{e.get('task', '')} {e.get('output', '')}"))
             for eid, e in by_id.items()),
            key=lambda x: x[1], reverse=True,
        )
        lex_list = [eid for eid, sc in lex if sc > 0]

        # (b) 벡터 (임베딩이 있을 때만 결과가 온다)
        vec_hits = await self.store.vector_search(message, limit=10)
        vec_list = [h.get("id") for h in vec_hits if h.get("id") in by_id]

        # (c) 인출 확산: 시드 = 발화 + 세션 버퍼. 시드 자체가 직접 일치(패턴 완성의 0순위)이고
        #     그 뒤에 확산 이웃이 온다. 시드를 빼면 방금 전 턴의 경험이 약한 새 엣지 때문에 상위 이웃에 못 든다.
        depth, limit = _SPREAD_BURST if burst else _SPREAD_CALM
        seed_names = cue | seeds
        neighbors = await self.store.spread(seed_names, depth=depth, limit=limit)
        activated = sorted(seed_names) + [n for n in neighbors if n not in seed_names]
        act_rank = {name: r for r, name in enumerate(activated)}
        spread_scores = []
        for eid, e in by_id.items():
            names = set(e.get("concept_names") or [])
            hit = names & set(act_rank)
            if hit:
                spread_scores.append((eid, sum(1.0 / (1 + act_rank[n]) for n in hit)))
        spread_list = [eid for eid, _ in sorted(spread_scores, key=lambda x: x[1], reverse=True)]

        fused = rrf_fuse([lex_list, vec_list, spread_list])
        if not fused:
            return RecallResult([], 0.0, 0.0, "")
        mx = max(fused.values())
        scored = []
        for eid, rel in fused.items():
            e = by_id[eid]
            strength = float(e.get("strength") if e.get("strength") is not None else 0.5)
            scored.append((eid, strength * (rel / mx)))
        temp = stage_value("temp", stage) * (BURST_FACTOR if burst else 1.0)
        chosen = softmax_select(scored, K_INJECT, temp, self.rng)
        ordered = sorted(scored, key=lambda x: x[1], reverse=True)
        s1 = ordered[0][1]
        s2 = ordered[1][1] if len(ordered) > 1 else 0.0
        conf = sigmoid((s1 - s2) / CONF_SCALE)
        known = await self.store.known_concepts(cue)
        fok = (len(known) / len(cue)) if cue else 0.0
        ranked = [{**by_id[eid], "score": sc} for eid, sc in chosen]
        block = format_block(ranked, conf, fok)
        return RecallResult(ranked, conf, fok, block)

    # ---- 진입점 1: 답하기 전 ----
    async def augment_system_prompt(self, system_prompt: str, message: str,
                                    context: Optional[dict], state: Optional[dict]) -> str:
        if not enabled():
            return system_prompt
        try:
            return await self._augment(system_prompt, message, context or {}, state or {})
        except Exception as e:  # 게이트웨이 오류는 대화를 막지 않는다
            logger.warning(f"memory_gateway augment error: {e}")
            return system_prompt

    async def _augment(self, system_prompt: str, message: str, context: dict, state: dict) -> str:
        speaker_id = context.get("speaker_id", "unknown") or "unknown"
        stage = int(state.get("development_stage", 0) or 0)
        cue = extract_cue_concepts(message)
        buf = self._buffer(speaker_id, stage)

        # 예측 확산: 시드 = 세션 버퍼, 깊이·개수 = 직전 턴의 z
        prev_depth = self.last_depth.get(speaker_id, _SPREAD_CALM)
        predicted = set(await self.store.spread(buf.seeds(), depth=prev_depth[0], limit=prev_depth[1])) if len(buf) else set()
        err = prediction_error(predicted, cue)
        sigma, warm = self.sigma.observe(speaker_id, err)
        z = 0.0 if warm else err / sigma
        burst = z > self.theta
        self.last_depth[speaker_id] = _SPREAD_BURST if burst else _SPREAD_CALM

        recall = await self._recall(message, cue, buf.seeds(), speaker_id, stage, z, burst)
        buf.push(cue, burst)
        self.turns[speaker_id] = TurnState(
            speaker_id=speaker_id, stage=stage, cue=cue, predicted=predicted, error=err,
            sigma=sigma, z=z, burst=burst, warm=warm, recalled=recall.ranked,
            conf=recall.conf, fok=recall.fok, created_at=_iso(self.clock()),
        )
        if burst:
            await self._publish_burst(speaker_id, z, err)
        if not recall.block:
            return system_prompt
        return system_prompt + "\n" + recall.block

    async def _publish_burst(self, speaker_id: str, z: float, err: float) -> None:
        try:
            from .redis_client import publish  # noqa: WPS433
            await publish("baby-ai:ne_burst", {"speaker_id": speaker_id, "z": round(z, 3), "error": round(err, 3),
                                               "at": _iso(self.clock())})
        except Exception as e:  # Redis 가 없어도 대화는 계속
            logger.debug(f"ne_burst publish skipped: {e}")

    # ---- 진입점 2: 답한 뒤 ----
    async def post_turn(self, result: Optional[dict], message: str, context: Optional[dict]) -> Optional[dict]:
        if not enabled() or not result:
            return None
        try:
            return await self._post(result, message, context or {})
        except Exception as e:
            logger.warning(f"memory_gateway post_turn error: {e}")
            return None

    async def _post(self, result: dict, message: str, context: dict) -> dict:
        from .conversation_handler import infer_user_emotion  # noqa: WPS433
        speaker_id = context.get("speaker_id", "unknown") or "unknown"
        ts_dt = self.clock()
        ts = _iso(ts_dt)
        turn = self.turns.get(speaker_id)
        z = turn.z if turn else 0.0
        burst = turn.burst if turn else False
        stage = turn.stage if turn else int(result.get("development_stage", 0) or 0)

        emotions = result.get("emotional_state") or {}
        self_v, self_a = core_affect(emotions)
        word = infer_user_emotion(message)
        spk_v, spk_a = speaker_affect(word)
        wp = write_priority(z, self_a)
        self.affect_state[speaker_id] = {"valence": self_v, "arousal": self_a, "at": ts}
        await self._cache_affect(speaker_id)

        summary = {"speaker_id": speaker_id, "z": z, "burst": burst, "write_priority": wp,
                   "self_valence": self_v, "self_arousal": self_a,
                   "speaker_valence": spk_v, "speaker_arousal": spk_a, "speaker_word": word}

        exp_id = result.get("experience_id")
        if not exp_id:
            return summary

        props = {
            "self_valence": round(self_v, 3), "self_arousal": round(self_a, 3),
            "speaker_valence": spk_v, "speaker_arousal": spk_a, "speaker_word": word,
            "surprise_z": round(z, 3), "write_priority": round(wp, 3), "channel": "대화",
            # 회상 통계(extras 는 보호 핸들러가 쓰므로 여기 남긴다)
            "recall_conf": round(turn.conf, 3) if turn else 0.0,
            "recall_fok": round(turn.fok, 3) if turn else 0.0,
            "recalled_ids": [e.get("id") for e in (turn.recalled if turn else []) if e.get("id")],
        }
        await self.store.update_experience(exp_id, props, wp)

        concepts = await self.store.experience_concepts(exp_id)
        cids = [cid for cid, _ in concepts]
        await self.store.upsert_feels_about(speaker_id, cids, spk_v, spk_a, ts)

        if turn and turn.recalled:
            rec_ids = [e.get("id") for e in turn.recalled if e.get("id")]
            rec_cids = [c for e in turn.recalled for c in (e.get("concept_ids") or [])]
            await self.store.touch_access(rec_ids, rec_cids, ts)

        if burst:
            eta_eff = stage_value("eta", stage) * BURST_FACTOR
            extra_direct = HEBB_DIRECT * (eta_eff - 1.0)
            if len(cids) >= 2 and extra_direct > 0:
                from itertools import combinations
                pairs = list(combinations(sorted(cids), 2))
                summary["extra_hebbian_pairs"] = await self.store.hebbian_update(pairs, extra_direct, "gateway")
            summary["tagged"] = await self._tag_window(exp_id, {n for _, n in concepts}, ts_dt)
        return summary

    async def _tag_window(self, exp_id: str, concept_names: set[str], now: datetime) -> int:
        """시냅스 태깅·포획: 직전 M분의 관련(자카드 ≥ ρ) 경험의 strength 를 0.1×관련성 만큼 올린다."""
        since = _iso(now - timedelta(minutes=TAG_WINDOW_MIN))
        recent = await self.store.recent_experiences(since, exclude_id=exp_id)
        n = 0
        for e in recent:
            j = jaccard(concept_names, e.get("concept_names") or [])
            if j >= TAG_RELATEDNESS_MIN:
                await self.store.boost_strength(e["id"], TAG_BOOST * j)
                n += 1
        return n

    async def _cache_affect(self, speaker_id: str) -> None:
        try:
            from .redis_client import cache_set  # noqa: WPS433
            await cache_set(f"affect_state:{speaker_id}", self.affect_state[speaker_id], ttl_seconds=3600)
        except Exception as e:
            logger.debug(f"affect_state cache skipped: {e}")


def format_block(ranked: list[dict], conf: float, fok: float, budget: int = PROMPT_CHAR_BUDGET) -> str:
    """시스템 프롬프트에 붙일 회상 블록. 글자 예산 안에서 자른다."""
    if not ranked:
        return ""
    head = f"[회상된 기억] (확신도 {conf:.2f}, 앎-느낌 {fok:.2f})"
    lines = [head]
    used = len(head)
    for e in ranked:
        when = (e.get("created_at") or "")[:10]
        task = (e.get("task") or "").replace("\n", " ")[:PROMPT_SNIPPET_CHARS]
        out = (e.get("output") or "").replace("\n", " ")[:PROMPT_SNIPPET_CHARS]
        line = f"- {when} 상대: \"{task}\" → 비비: \"{out}\""
        if used + len(line) + 1 > budget:
            break
        lines.append(line)
        used += len(line) + 1
    # [필수 규칙]의 "모르겠어요 금지"를 지킨다: 모른다고 끝내지 말고, 추측임을 밝히고 답한다.
    tail = ("[회상 지침] 확신도가 낮으면 추측임을 밝히고 답해라. "
            + ("앎-느낌이 낮으니 '기억은 안 나지만 추측하면'처럼 말하고 답해라."
               if fok < FOK_THRESHOLD else "기억을 자연스럽게 답에 녹여라."))
    lines.append(tail)
    return "\n".join(lines)


# ── 프로세스 단일 인스턴스 ─────────────────────────────────────────────────
_GATEWAY: Optional[MemoryGateway] = None


def get_gateway() -> MemoryGateway:
    global _GATEWAY
    if _GATEWAY is None:
        from .neo4j_db import get_brain_db  # noqa: WPS433
        _GATEWAY = MemoryGateway(Neo4jGatewayStore(get_brain_db()))
    return _GATEWAY


async def augment_system_prompt(system_prompt: str, message: str, context: Optional[dict], state: Optional[dict]) -> str:
    """conversation_handler 가 부르는 한 줄용 진입점."""
    if not enabled():
        return system_prompt
    return await get_gateway().augment_system_prompt(system_prompt, message, context, state)


async def post_turn(result: Optional[dict], message: str, context: Optional[dict]) -> Optional[dict]:
    """api_server 가 답한 뒤에 부르는 진입점."""
    if not enabled():
        return None
    return await get_gateway().post_turn(result, message, context)
