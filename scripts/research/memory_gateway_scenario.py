"""설계 노트 8절 8항 시나리오 재현 (A단계 완료 기준).

형이 "알고리즘 중간고사 때문에 힘들어"라고 말한 뒤 "요즘 너무 피곤해"라고 했을 때,
답하기 전 프롬프트에 그 경험이 회상되어 들어가고 답변이 중간고사를 언급하는지 본다.

두 가지 모드
  --same-process : 두 턴을 한 프로세스에서 (세션 버퍼가 살아 있음)
  --second-only  : "요즘 너무 피곤해" 한 턴만 (새 프로세스 = 버퍼 비어 있음, 그래프 경로만으로 회상)

실행 조건: Neo4j 가동, .env 의 Gemini 키, MEMORY_GATEWAY 는 이 스크립트가 1 로 켠다.
게이트웨이가 만든 Experience 속성과 회상 목록을 DB 에서 다시 읽어 검증한다.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts", "migration"))

from person_hub_seed import load_project_env  # noqa: E402

SPEAKER = {"speaker_id": "brother", "speaker_name": "형아"}
MSG1 = "알고리즘 중간고사 때문에 너무 힘들어"
MSG2 = "요즘 너무 피곤해"


async def one_turn(message: str, gw, handle_conversation, post_turn):
    result = await handle_conversation(message=message, context=SPEAKER)
    summary = await post_turn(result, message, SPEAKER)
    turn = gw.turns.get(SPEAKER["speaker_id"])
    return result, summary, turn


async def read_experience(neo4j_db, exp_id: str) -> dict:
    db = neo4j_db.get_brain_db()
    async with db.driver.session(database=neo4j_db._DB_NAME) as s:
        r = await s.run(
            "MATCH (e:Experience {id: $id}) OPTIONAL MATCH (e)-[:INVOLVES]->(c:Concept) "
            "RETURN e {.strength, .write_priority, .surprise_z, .self_arousal, .self_valence, .speaker_word, "
            "  .speaker_valence, .channel, .recall_conf, .recall_fok, .recalled_ids, .access_ts} AS e, collect(c.name) AS concepts",
            id=exp_id,
        )
        rec = await r.single()
        return {"props": dict(rec["e"]), "concepts": rec["concepts"]} if rec else {}


async def main(mode: str) -> int:
    os.environ["MEMORY_GATEWAY"] = "1"
    env_path = load_project_env()
    print(f"env: {env_path}")
    from neural.baby import neo4j_db  # noqa: WPS433
    from neural.baby.conversation_handler import handle_conversation  # noqa: WPS433
    from neural.baby.memory_gateway import get_gateway, post_turn  # noqa: WPS433

    await neo4j_db.init_driver()
    try:  # api_server 의 lifespan 처럼 Redis 를 초기화한다(인스턴스가 없으면 publish 가 실패하지만 대화는 계속된다)
        from neural.baby.redis_client import init_redis  # noqa: WPS433
        init_redis()
    except Exception as e:
        print("redis init skipped:", e)
    gw = get_gateway()
    ok = True
    try:
        turns = [MSG1, MSG2] if mode == "same-process" else [MSG2]
        for i, msg in enumerate(turns, 1):
            print(f"\n=== 턴 {i}: {SPEAKER['speaker_name']}: {msg}")
            result, summary, turn = await one_turn(msg, gw, handle_conversation, post_turn)
            print("비비:", (result.get("output") or "")[:300])
            print("success:", result.get("success"), "experience_id:", result.get("experience_id"))
            if turn:
                print(f"z={turn.z:.3f} warm={turn.warm} burst={turn.burst} conf={turn.conf:.2f} fok={turn.fok:.2f} "
                      f"cue={sorted(turn.cue)} recalled={[(e.get('id'), (e.get('task') or '')[:30]) for e in turn.recalled]}")
            if summary:
                print("post_turn:", {k: (round(v, 3) if isinstance(v, float) else v) for k, v in summary.items()})
            if result.get("experience_id"):
                stored = await read_experience(neo4j_db, result["experience_id"])
                print("stored:", json.dumps(stored, ensure_ascii=False)[:600])
                if "write_priority" not in stored.get("props", {}):
                    ok = False
                    print("!! write_priority 가 저장되지 않음")
            if msg == MSG2:
                # 회상 블록에는 task 와 output 조각이 함께 들어가므로 둘 다 본다
                recalled_tasks = " ".join(
                    f"{e.get('task') or ''} {(e.get('output') or '')[:60]}" for e in (turn.recalled if turn else [])
                )
                hit_recall = "중간고사" in recalled_tasks
                hit_answer = "중간고사" in (result.get("output") or "") or "시험" in (result.get("output") or "")
                print(f"판정: 회상에 중간고사 포함={hit_recall}, 답변이 시험/중간고사 언급={hit_answer}")
                ok = ok and hit_recall
    finally:
        await neo4j_db.close_driver()
    print("\nRESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--same-process", action="store_true")
    g.add_argument("--second-only", action="store_true")
    args = ap.parse_args()
    sys.exit(asyncio.run(main("same-process" if args.same_process else "second-only")))
