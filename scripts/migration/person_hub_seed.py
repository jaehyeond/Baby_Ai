"""A0: :Person 허브 최소 구축 (설계 노트 7절 A0). 비파괴.

규칙
- 이미 어떤 :Person 이 IDENTIFIED_BY 로 식별하는 UserModel(예: 2026-07-10 시드에서 owner 의 별칭으로 묶인 mom·brother)은
  새 :Person 을 만들지 않는다. 그 :Person 에 빠진 속성만 채운다(있는 값은 덮지 않음).
- 아무 :Person 도 식별하지 않는 UserModel 은 :Person 을 하나 만들고 IDENTIFIED_BY 로 잇는다.
- role=family 인 새 :Person 은 owner 와 FAMILY_OF 로 잇는다.
- 제약은 만들지 않는다(person_pid 가 이미 person_id UNIQUE 를 건다).

새 속성 다섯과 초기값 (모두 추정, 설계 노트 5.1):
  familiarity     = 1 − exp(−interaction_count/10)   (별칭이 여럿이면 합산)
  closeness/power = relationship 문자열 사상표. 문자열이 unknown 이면 speaker_id·이름에서 가족 단서를 찾는다
  trust_valence   = 화자 정서 사상표로 recent_emotion 을 valence 로 바꾼 값의 부호
  social_salience = 1
  access_tier     = owner → 'owner_private', family → 'family', 그 외 'public'

사용:
  python scripts/migration/person_hub_seed.py --dry-run
  python scripts/migration/person_hub_seed.py --apply
"""
from __future__ import annotations

import argparse
import asyncio
import math
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from neural.baby.memory_gateway import speaker_affect  # noqa: E402

OWNER_ALIASES = {"self", "나", "박재현", "owner_pjh"}
RELATION_TABLE: dict[str, tuple[float, float, str]] = {
    "family": (0.8, 0.6, "family"), "mom": (0.8, 0.6, "family"), "엄마": (0.8, 0.6, "family"),
    "brother": (0.8, 0.5, "family"), "형": (0.8, 0.5, "family"), "dad": (0.8, 0.6, "family"), "아빠": (0.8, 0.6, "family"),
    "friend": (0.5, 0.5, "known"), "친구": (0.5, 0.5, "known"),
    "teacher": (0.4, 0.8, "known"), "선생님": (0.4, 0.8, "known"),
}
DEFAULT_RELATION = (0.1, 0.5, "stranger")
NEW_PROPS = ("familiarity", "closeness", "power", "trust_valence", "social_salience", "access_tier")


def _relation_key(u: dict) -> str:
    for cand in (u.get("relationship"), u.get("speaker_id"), u.get("name")):
        key = str(cand or "").strip().lower()
        if key in RELATION_TABLE:
            return key
        if key.startswith("형"):
            return "brother"
    return "unknown"


def person_props(u: dict) -> dict:
    sid = str(u.get("speaker_id") or "")
    closeness, power, role = RELATION_TABLE.get(_relation_key(u), DEFAULT_RELATION)
    if sid in OWNER_ALIASES:
        role, closeness, power = "owner", 1.0, 1.0
    count = int(u.get("interaction_count") or 0)
    v, _ = speaker_affect(str(u.get("recent_emotion") or "neutral"))
    trust = 1.0 if v > 0 else (-1.0 if v < 0 else 0.0)
    tier = {"owner": "owner_private", "family": "family"}.get(role, "public")
    return {
        "person_id": sid,
        "canonical_name": u.get("name") or sid,
        "role": role,
        "familiarity": round(1.0 - math.exp(-count / 10.0), 3),
        "closeness": closeness,
        "power": power,
        "trust_valence": trust,
        "social_salience": 1.0,
        "access_tier": tier,
        "access_clearance": "owner" if role == "owner" else ("family" if role == "family" else "public"),
        "created_by": "person_hub_seed_2026-09-07",
    }


def existing_person_fill(person: dict, identified_users: list[dict]) -> dict:
    """기존 :Person 에 빠진 속성만 채운다. familiarity 는 식별된 UserModel 의 대화 수 합으로 계산."""
    count = sum(int(u.get("interaction_count") or 0) for u in identified_users)
    role = person.get("role", "stranger")
    defaults = {
        "familiarity": round(1.0 - math.exp(-count / 10.0), 3),
        "closeness": 1.0 if role == "owner" else DEFAULT_RELATION[0],
        "power": 1.0 if role == "owner" else DEFAULT_RELATION[1],
        "trust_valence": 0.0,
        "social_salience": 1.0,
        "access_tier": {"owner": "owner_private", "family": "family"}.get(role, "public"),
    }
    return {k: v for k, v in defaults.items() if person.get(k) is None}


def load_project_env() -> str:
    """repo 루트의 .env 를 읽는다. git worktree 라 .env 가 없으면 본 체크아웃(.git 파일의 gitdir)의 .env 를 읽는다.
    neo4j_db 는 import 시점에 환경변수를 읽으므로 이 함수를 import 보다 먼저 부른다."""
    from dotenv import load_dotenv  # noqa: WPS433
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    candidates = [os.path.join(root, ".env")]
    gitfile = os.path.join(root, ".git")
    if os.path.isfile(gitfile):
        with open(gitfile, encoding="utf-8") as f:
            line = f.readline().strip()
        if line.startswith("gitdir:"):
            gitdir = line.split(":", 1)[1].strip()
            main_root = os.path.abspath(os.path.join(gitdir, "..", "..", ".."))
            candidates.append(os.path.join(main_root, ".env"))
    for path in candidates:
        if os.path.isfile(path):
            load_dotenv(path)
            return path
    return ""


async def run(apply: bool) -> int:
    env_path = load_project_env()
    print(f"env: {env_path or '(none found)'}")
    from neural.baby.neo4j_db import get_brain_db, init_driver, close_driver, _DB_NAME  # noqa: WPS433
    await init_driver()
    try:
        return await _run_with_driver(apply, get_brain_db(), _DB_NAME)
    finally:
        await close_driver()


async def _run_with_driver(apply: bool, db, _DB_NAME: str) -> int:
    async with db.driver.session(database=_DB_NAME) as s:
        r = await s.run("MATCH (u:UserModel) RETURN u")
        users = [dict(x["u"]) for x in await r.fetch(1000)]
        r = await s.run(
            "MATCH (p:Person) OPTIONAL MATCH (p)-[:IDENTIFIED_BY]->(u:UserModel) "
            "RETURN p, collect(u.speaker_id) AS sids"
        )
        persons = [(dict(x["p"]), [sid for sid in x["sids"] if sid]) for x in await r.fetch(1000)]

    identified: dict[str, str] = {sid: p["person_id"] for p, sids in persons for sid in sids}
    by_sid = {u.get("speaker_id"): u for u in users if u.get("speaker_id")}

    creates = [person_props(u) for sid, u in by_sid.items() if sid not in identified]
    fills = []
    for p, sids in persons:
        add = existing_person_fill(p, [by_sid[s] for s in sids if s in by_sid])
        fills.append((p["person_id"], sids, add))

    tag = "APPLY" if apply else "PLAN "
    for pid, sids, add in fills:
        print(f"{tag} keep :Person {pid} (identifies {sids}) fill={add or '(nothing missing)'}")
    for p in creates:
        print(f"{tag} new  :Person {p['person_id']} role={p['role']} fam={p['familiarity']} "
              f"close={p['closeness']} power={p['power']} trust={p['trust_valence']} tier={p['access_tier']}")
    owner = next((p for p, _ in persons if p.get("role") == "owner"), None)
    if not apply:
        return len(creates)

    async with db.driver.session(database=_DB_NAME) as s:
        for pid, _, add in fills:
            if add:
                await s.run("MATCH (p:Person {person_id: $pid}) SET p += $props", pid=pid, props=add)
        for p in creates:
            await s.run(
                "MERGE (p:Person {person_id: $pid}) ON CREATE SET p += $props "
                "WITH p MATCH (u:UserModel {speaker_id: $pid}) MERGE (p)-[:IDENTIFIED_BY]->(u)",
                pid=p["person_id"], props=p,
            )
            if p["role"] == "family" and owner:
                await s.run(
                    "MATCH (a:Person {person_id: $a}), (b:Person {person_id: $b}) MERGE (a)-[:FAMILY_OF]->(b)",
                    a=p["person_id"], b=owner["person_id"],
                )
    return len(creates)


def main() -> None:
    ap = argparse.ArgumentParser(description="A0 :Person 허브 시드 (비파괴)")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry-run", action="store_true")
    g.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    n = asyncio.run(run(apply=args.apply))
    print(f"{'applied' if args.apply else 'planned'}: {n} new person(s)")


if __name__ == "__main__":
    main()
