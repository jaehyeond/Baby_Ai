"""memory_gateway 단위 테스트 — Neo4j 없이 FakeStore 로 돈다."""
from __future__ import annotations

import asyncio
import os
import random
from datetime import datetime, timedelta, timezone

import pytest

from neural.baby import memory_gateway as mg
from neural.baby.memory_gateway import (
    MemoryGateway, SessionBuffer, SigmaTable, core_affect, format_block, jaccard,
    prediction_error, rrf_fuse, softmax_select, speaker_affect, stage_value, write_priority,
)


# ── 가짜 저장소 ─────────────────────────────────────────────────────────────
class FakeStore:
    def __init__(self):
        self.experiences: dict[str, dict] = {}
        self.concepts: dict[str, str] = {}          # name -> id
        self.relates: dict[str, set[str]] = {}      # name -> neighbor names
        self.feels: dict[tuple[str, str], dict] = {}
        self.hebb_calls: list[tuple] = []
        self.access: list[tuple] = []

    # 그래프 조작 (테스트 준비용)
    def add_concept(self, name: str) -> str:
        cid = self.concepts.setdefault(name, f"c_{name}")
        self.relates.setdefault(name, set())
        return cid

    def relate(self, a: str, b: str) -> None:
        self.add_concept(a); self.add_concept(b)
        self.relates[a].add(b); self.relates[b].add(a)

    def add_experience(self, eid: str, speaker: str, task: str, output: str, concepts: list[str],
                       created_at: str, strength: float = 0.6) -> None:
        for c in concepts:
            self.add_concept(c)
        self.experiences[eid] = {
            "id": eid, "speaker_id": speaker, "task": task, "output": output, "strength": strength,
            "created_at": created_at, "concept_names": list(concepts),
            "concept_ids": [self.concepts[c] for c in concepts], "access_ts": [],
        }

    # GatewayStore 구현
    async def clearance(self, speaker_id):
        return "owner" if speaker_id == "self" else "public"

    async def experiences_for_speaker(self, speaker_id, clearance, limit):
        rows = [e for e in self.experiences.values()
                if (speaker_id == "unknown" or e["speaker_id"] == speaker_id) and not e.get("valid_to")]
        rows.sort(key=lambda e: e["created_at"], reverse=True)
        return [dict(e) for e in rows[:limit]]

    async def spread(self, concept_names, depth, limit):
        frontier, seen, out = set(concept_names), set(concept_names), []
        for _ in range(depth):
            nxt = set()
            for n in frontier:
                for m in self.relates.get(n, ()):
                    if m not in seen:
                        seen.add(m); out.append(m); nxt.add(m)
            frontier = nxt
        return out[:limit]

    async def vector_search(self, text, limit):
        return []

    async def known_concepts(self, names):
        return {n for n in names if n in self.concepts}

    async def experience_concepts(self, experience_id):
        e = self.experiences[experience_id]
        return list(zip(e["concept_ids"], e["concept_names"]))

    async def update_experience(self, experience_id, props, strength_mult):
        e = self.experiences[experience_id]
        e.update(props)
        e["strength"] = min(1.0, e["strength"] * strength_mult)

    async def touch_access(self, experience_ids, concept_ids, ts):
        for eid in experience_ids:
            self.experiences[eid]["access_ts"].append(ts)
        self.access.append((tuple(sorted(experience_ids)), tuple(sorted(concept_ids)), ts))

    async def upsert_feels_about(self, speaker_id, concept_ids, valence, arousal, ts):
        for cid in concept_ids:
            f = self.feels.get((speaker_id, cid))
            if f is None:
                self.feels[(speaker_id, cid)] = {"valence": valence, "arousal": arousal, "count": 1}
            else:
                n = f["count"]
                f["valence"] = (f["valence"] * n + valence) / (n + 1)
                f["arousal"] = (f["arousal"] * n + arousal) / (n + 1)
                f["count"] = n + 1

    async def hebbian_update(self, pairs, strength_delta, source):
        self.hebb_calls.append((tuple(pairs), strength_delta, source))
        return len(pairs)

    async def recent_experiences(self, since_iso, exclude_id):
        return [{"id": e["id"], "concept_names": e["concept_names"]}
                for e in self.experiences.values() if e["created_at"] >= since_iso and e["id"] != exclude_id]

    async def boost_strength(self, experience_id, delta):
        e = self.experiences[experience_id]
        e["strength"] = min(1.0, e["strength"] + delta)


def _run(coro):
    return asyncio.run(coro)


@pytest.fixture(autouse=True)
def _enable_flag(monkeypatch):
    monkeypatch.setenv(mg.GATEWAY_ENV, "1")
    monkeypatch.delenv("MEMORY_GATEWAY_W", raising=False)
    yield


def _clock_at(t: datetime):
    return lambda: t


# ── 순수 함수 ──────────────────────────────────────────────────────────────
def test_jaccard_and_error():
    assert jaccard({"a", "b"}, {"b", "c"}) == pytest.approx(1 / 3)
    assert prediction_error(set(), set()) == 0.0
    assert prediction_error({"a"}, {"b"}) == 1.0
    assert prediction_error({"a", "b"}, {"a", "b"}) == 0.0


def test_core_affect_reuses_salience_formula_and_scales_valence():
    emo = {"joy": 1.0, "curiosity": 1.0, "surprise": 0.5, "fear": 0.0, "frustration": 0.0, "boredom": 0.0}
    v, a = core_affect(emo)
    assert a == pytest.approx(1.0 * 0.3 + 1.0 * 0.3 + 0.5 * 0.2)
    assert v == pytest.approx(0.4)
    v2, _ = core_affect({"fear": 1.0, "frustration": 1.0, "boredom": 1.0})
    assert v2 == pytest.approx(-0.6)


def test_speaker_affect_table_and_default():
    assert speaker_affect("happy") == (1.0, 0.6)
    assert speaker_affect("angry") == (-1.0, 0.9)
    assert speaker_affect("unknown-word") == speaker_affect("neutral")


def test_write_priority_range():
    assert write_priority(0.0, 0.0) == pytest.approx(0.5)
    assert write_priority(3.0, 1.0) == pytest.approx(2.0)
    assert write_priority(10.0, 1.0) == pytest.approx(2.0)   # z 상한 3


def test_stage_value_interpolates():
    assert stage_value("eta", 0) == 1.5 and stage_value("eta", 5) == 1.0
    assert stage_value("w", 0) == 3 and stage_value("w", 5) == 5
    assert 1.0 < stage_value("temp", 2) < 1.5


def test_rrf_fuse_and_softmax_select_deterministic():
    fused = rrf_fuse([["a", "b"], ["b", "c"]])
    assert fused["b"] > fused["a"] > 0 and fused["c"] > 0
    items = [("a", 0.9), ("b", 0.5), ("c", 0.1)]
    assert [i for i, _ in softmax_select(items, 2, 1.0)] == ["a", "b"]
    picked = softmax_select(items * 3, 2, 1.0, random.Random(0))
    assert len(picked) == 2


# ── σ_c 와 세션 버퍼 ────────────────────────────────────────────────────────
def test_sigma_table_warmup_then_z():
    t = SigmaTable(warmup_turns=3)
    for e in (0.2, 0.4, 0.3):
        sigma, warm = t.observe("s", e)
        assert warm
    assert t.z("s", 1.0) == 0.0            # 워밍업(3턴) 동안은 게이트 없음
    sigma, warm = t.observe("s", 0.3)
    assert not warm and sigma >= mg.SIGMA_FLOOR
    assert t.z("s", 1.0) > 0.0             # 워밍업이 끝나면 z 가 살아난다


def test_session_buffer_eviction_and_pin():
    b = SessionBuffer(2)
    b.push({"a"}); b.push({"b"}, burst=True); b.push({"c"})
    # a 가 가장 오래됐으므로 나가고, b 는 핀 → 남는다
    assert b.seeds() == {"b", "c"}
    b.push({"d"})
    # 이번엔 b 의 핀이 풀리며 한 번 건너뛰고 c 가 나간다
    assert b.seeds() == {"b", "d"}
    b.push({"e"})
    assert b.seeds() == {"d", "e"}
    assert SessionBuffer(0).seeds() == set()


# ── 프롬프트 블록 ───────────────────────────────────────────────────────────
def test_format_block_respects_budget_and_fok_guidance():
    ranked = [{"created_at": "2026-09-05T10:00:00+00:00", "task": "알고리즘 중간고사 때문에 힘들어" * 5,
               "output": "괜찮아 형" * 20} for _ in range(20)]
    block = format_block(ranked, conf=0.8, fok=0.1, budget=400)
    assert block.startswith("[회상된 기억]")
    assert len(block) <= 400 + 80  # 지침 한 줄은 예산 밖
    assert "추측하면" in block                     # 필수 규칙: "모르겠어요"로 끝내지 않는다
    assert "모른다고" not in block
    assert format_block([], 0.5, 0.5) == ""


# ── 흐름: 답하기 전 회상 + 답한 뒤 갱신 ─────────────────────────────────────
def _scenario_store() -> FakeStore:
    st = FakeStore()
    # Concept 이름은 기존 규칙 기반 추출기가 만드는 그대로다("피곤해"는 어미가 안 잘린다).
    st.relate("피곤해", "힘들")
    st.relate("힘들", "중간고사")
    st.relate("중간고사", "알고리즘")
    yesterday = "2026-09-05T09:00:00+00:00"
    st.add_experience("e1", "brother", "알고리즘 중간고사 때문에 힘들어", "형, 시험 준비 힘들지. 잘 될 거야",
                      ["알고리즘", "중간고사", "힘들"], yesterday, strength=0.7)
    st.add_experience("e2", "brother", "오늘 점심 뭐 먹지", "김밥 어때?", ["점심", "김밥"], yesterday, strength=0.5)
    st.add_experience("e3", "mom", "비비야 잘 잤니", "네 엄마", ["잠"], yesterday, strength=0.5)
    return st


def test_video_scenario_recall_and_speaker_routing():
    st = _scenario_store()
    gw = MemoryGateway(st, clock=_clock_at(datetime(2026, 9, 6, 9, 0, tzinfo=timezone.utc)))
    ctx = {"speaker_id": "brother", "speaker_name": "형"}
    state = {"development_stage": 2}
    prompt = _run(gw.augment_system_prompt("[base]", "요즘 너무 피곤해", ctx, state))
    assert prompt.startswith("[base]")
    assert "[회상된 기억]" in prompt
    assert "알고리즘 중간고사" in prompt         # 확산으로 회상됨 (피곤→힘들→중간고사)
    assert "비비야 잘 잤니" not in prompt        # 다른 화자(mom)는 라우팅에서 제외
    turn = gw.turns["brother"]
    assert turn.warm and turn.z == 0.0            # 워밍업 동안은 게이트 없음
    assert any(e["id"] == "e1" for e in turn.recalled)


def test_session_buffer_direct_hit_recalls_previous_turn_without_edges():
    """실측(2026-09-07)에서 발견한 결함의 회귀 테스트: 새 엣지가 약해 확산 이웃에 못 들어도,
    직전 턴의 Concept(세션 버퍼)이 직접 일치로 그 경험을 되살려야 한다."""
    st = FakeStore()   # 엣지 없음
    now = datetime(2026, 9, 7, 9, 0, tzinfo=timezone.utc)
    gw = MemoryGateway(st, clock=_clock_at(now))
    ctx = {"speaker_id": "brother"}
    _run(gw.augment_system_prompt("[base]", "알고리즘 중간고사 때문에 힘들어", ctx, {"development_stage": 2}))
    st.add_experience("e_mid", "brother", "알고리즘 중간고사 때문에 힘들어", "힘내",
                      ["알고리즘", "중간고사", "힘들"], now.isoformat(), strength=0.5)
    prompt = _run(gw.augment_system_prompt("[base]", "요즘 너무 피곤해", ctx, {"development_stage": 2}))
    assert "알고리즘 중간고사" in prompt


def test_flag_off_is_noop(monkeypatch):
    monkeypatch.setenv(mg.GATEWAY_ENV, "0")
    st = _scenario_store()
    gw = MemoryGateway(st)
    assert _run(gw.augment_system_prompt("[base]", "요즘 너무 피곤해", {"speaker_id": "brother"}, {})) == "[base]"
    assert _run(gw.post_turn({"experience_id": "e1"}, "x", {"speaker_id": "brother"})) is None


def test_post_turn_updates_experience_feels_and_access():
    st = _scenario_store()
    now = datetime(2026, 9, 6, 9, 0, tzinfo=timezone.utc)
    gw = MemoryGateway(st, clock=_clock_at(now))
    ctx = {"speaker_id": "brother"}
    _run(gw.augment_system_prompt("[base]", "요즘 너무 피곤해", ctx, {"development_stage": 2}))
    st.add_experience("e_new", "brother", "요즘 너무 피곤해", "형, 중간고사 끝나고도 피곤하구나",
                      ["피곤해", "중간고사"], now.isoformat(), strength=0.5)
    result = {"experience_id": "e_new", "development_stage": 2,
              "emotional_state": {"joy": 0.5, "curiosity": 0.5, "surprise": 0.2, "fear": 0.1, "frustration": 0.1, "boredom": 0.1}}
    summary = _run(gw.post_turn(result, "요즘 너무 피곤해서 슬퍼", ctx))
    e = st.experiences["e_new"]
    assert summary["speaker_word"] == "sad" and e["speaker_valence"] == -1.0
    assert e["write_priority"] == pytest.approx(write_priority(0.0, summary["self_arousal"]), abs=1e-3)
    assert e["strength"] == pytest.approx(0.5 * e["write_priority"], abs=1e-3)
    assert e["channel"] == "대화" and "surprise_z" in e
    assert "e1" in e["recalled_ids"] and 0.0 <= e["recall_conf"] <= 1.0
    # FEELS_ABOUT: 화자→개념
    assert st.feels[("brother", "c_피곤해")]["valence"] == -1.0
    # 회상된 e1 에 access_ts 가 붙음
    assert st.experiences["e1"]["access_ts"] == [now.isoformat()]
    assert gw.affect_state["brother"]["arousal"] == pytest.approx(summary["self_arousal"])


def test_burst_triggers_extra_hebbian_and_tagging():
    st = _scenario_store()
    now = datetime(2026, 9, 6, 9, 0, tzinfo=timezone.utc)
    gw = MemoryGateway(st, clock=_clock_at(now), warmup_turns=0, theta=0.5)
    ctx = {"speaker_id": "brother"}
    # 첫 턴: 버퍼가 비어 예측이 없음 → 오차 0. 두 번째 턴에서 큰 오차를 만든다.
    _run(gw.augment_system_prompt("[base]", "점심 김밥 먹자", ctx, {"development_stage": 0}))
    _run(gw.augment_system_prompt("[base]", "로봇 팔 제어 이론 알아?", ctx, {"development_stage": 0}))
    turn = gw.turns["brother"]
    assert turn.burst and turn.z > 0.5
    recent = (now - timedelta(minutes=10)).isoformat()
    st.add_experience("e_prev", "brother", "로봇 이야기", "로봇 좋아", ["로봇", "제어"], recent, strength=0.4)
    st.add_experience("e_new", "brother", "로봇 팔 제어 이론 알아?", "조금 알아", ["로봇", "제어", "이론"], now.isoformat(), strength=0.5)
    result = {"experience_id": "e_new", "development_stage": 0, "emotional_state": {"joy": 0.2, "curiosity": 0.9}}
    summary = _run(gw.post_turn(result, "로봇 팔 제어 이론 알아?", ctx))
    assert summary["burst"] is True
    assert st.hebb_calls and st.hebb_calls[0][2] == "gateway"
    eta_eff = stage_value("eta", 0) * mg.BURST_FACTOR
    assert st.hebb_calls[0][1] == pytest.approx(mg.HEBB_DIRECT * (eta_eff - 1.0))
    assert summary["tagged"] == 1
    assert st.experiences["e_prev"]["strength"] > 0.4       # 태깅 창으로 소급 강화


def test_gateway_errors_never_break_conversation():
    class BrokenStore(FakeStore):
        async def experiences_for_speaker(self, *a, **k):
            raise RuntimeError("db down")
    gw = MemoryGateway(BrokenStore())
    assert _run(gw.augment_system_prompt("[base]", "안녕", {"speaker_id": "brother"}, {})) == "[base]"
    assert _run(gw.post_turn({"experience_id": "x"}, "안녕", {"speaker_id": "brother"})) is None
