"""
Sleep-Distill Prototype — Phase 2 결정적 메커니즘 축소 검증 (CLS wake-sleep)
==============================================================================
program_roadmap Phase 2 / self_learning_architecture. head_crossover가 "항상성 있는
파라미터 코어가 그래프를 이긴다"를 보인 뒤의 자연 후속. Phase 2의 **결정적 주장**:
  "retrieval(그래프) 고정한 채 **코어 가중치만으로** 예측오차가 하강한다" = genuine
  self-learning. 로컬 LLM 없이 임베딩 코어를 대역으로 이 메커니즘을 축소 검증한다.

CLS 구조 (상보학습계, McClelland 1995)
--------------------------------------
- **그래프 = 빠른 해마**: wake에 경험 스트림을 degree-capped co-occurrence로 즉시 흡수.
- **코어 = 느린 신피질**: 학습가능 임베딩(norm-clipped=항상성). **wake엔 frozen**,
  **sleep에만** 그래프가 replay한 에피소드로 gradient 학습(=distillation). 로컬 LLM+LoRA의 대역.

wake-sleep 루프
---------------
스트림을 C 사이클로 분할. 각 사이클: (wake) 블록 프레임을 그래프에 흡수(코어 frozen) →
(sleep) 그래프서 R개 에피소드 replay(seed + top 이웃) → 코어에 gradient step. 매 사이클 후
**고정 held-out 테스트**로 3자 MRR 측정: graph · sleep-distill 코어 · online 코어(상한 참조).

리트머스: sleep-distill 코어 MRR이 사이클마다 **오르는가**(그래프 frozen, 가중치만) = 자기학습.
+ 안전장치 측정: forgetting(초기 연상 유지) · collapse(코어 임베딩 norm/유효랭크).

Usage:
    python scripts/research/sleep_distill_prototype.py --quick
출력: claudedocs/research/sleep_distill_<YYYYMMDD>.json
"""
from __future__ import annotations
import argparse, json, math, os, random, statistics, sys
from collections import defaultdict, Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(__file__))
import synth_world as SW
import head_crossover_probe as HC     # Head, cap_add, graph_score, rank_of, 상수 재사용

OUT = Path(__file__).resolve().parents[2] / "claudedocs" / "research"
OUT.mkdir(parents=True, exist_ok=True)

SEED = 42
K_NEG_EVAL = 60          # held-out 랭킹 음성 수
CAP = HC.CAP             # 그래프 degree cap (48)
CYCLES = 8               # wake-sleep 사이클 수
REPLAY_EPISODES = 400    # 사이클당 sleep replay 에피소드 수
EPISODE_SIZE = 6         # replay 에피소드 크기 (seed + 이웃)
DISTILL_STEPS = 2        # 에피소드당 SGD 반복


def build_testset(frames, rng, max_pairs=400):
    """held-out 프레임의 공동활성 쌍 (고정 테스트). (a,b) + seed 그룹."""
    pairs = []
    for _t, objs, _p in frames:
        objs = list(dict.fromkeys(objs))
        for i in range(len(objs)):
            for j in range(i + 1, len(objs)):
                pairs.append((objs[i], objs[j]))
    rng.shuffle(pairs)
    return pairs[:max_pairs]


def eval_mrr(scorer, testset, node_pool, nrng, k=K_NEG_EVAL):
    """sampled-negative 랭킹 MRR. scorer(a,c)->float. node_pool=음성 샘플원."""
    if len(node_pool) <= k + 2:
        return 0.0
    recs = []
    pool = list(node_pool)
    for (a, b) in testset:
        if a not in node_pool or b not in node_pool:
            continue
        negs = []
        tries = 0
        while len(negs) < k and tries < k * 3:
            n = pool[nrng.integers(len(pool))]
            if n != a and n != b:
                negs.append(n)
            tries += 1
        if len(negs) < k // 2:
            continue
        sc = lambda c: scorer(a, c)
        r = HC.rank_of(b, negs, sc)
        recs.append(1.0 / r)
    return round(statistics.mean(recs), 4) if recs else 0.0


def graph_neighbors(W, a, m):
    return [n for n, _ in sorted(W.get(a, {}).items(), key=lambda kv: -kv[1])[:m]]


def sleep_distill(core, W, node_pool, nrng, episodes, ep_size, steps):
    """sleep: 그래프서 에피소드 replay → 코어 gradient. 그래프→코어 distillation."""
    if not node_pool:
        return
    nodes = list(W.keys())
    if not nodes:
        return
    for _e in range(episodes):
        seed = nodes[nrng.integers(len(nodes))]
        nbrs = graph_neighbors(W, seed, ep_size - 1)
        episode = [seed] + nbrs
        if len(episode) < 2:
            continue
        # 에피소드 = replay된 공동활성 패턴 → 코어에 학습 (all_nodes=node_pool로 음성샘플)
        core.learn(episode, node_pool)


def core_effective_norm(core):
    """collapse 감시: 코어 임베딩 평균 norm."""
    vs = list(core.Eo.values()) + list(core.Ei.values())
    if not vs:
        return 0.0
    return round(float(np.mean([np.linalg.norm(v) for v in vs])), 3)


def run(N, scenes, seed):
    rng = random.Random(seed)
    nrng = np.random.default_rng(seed)
    frames = SW.generate_stream(N, n_scenes=scenes, motion=2.0, seed=seed)
    n_test = int(len(frames) * 0.15)
    train_frames, test_frames = frames[:-n_test], frames[-n_test:]
    testset = build_testset(test_frames, rng)

    # 상태: 그래프(fast) + sleep-distill 코어 + online 코어(상한 참조)
    W = defaultdict(dict)
    core_sleep = HC.Head(HC.DIM, np.random.default_rng(seed + 1))
    core_online = HC.Head(HC.DIM, np.random.default_rng(seed + 2))
    node_pool: list[str] = []
    seen = set()
    # 초기(early) 연상 forgetting probe: 첫 사이클 프레임의 테스트쌍
    early_probe = None

    block = len(train_frames) // CYCLES
    cycle_log = []
    for c in range(CYCLES):
        blk = train_frames[c * block:(c + 1) * block] if c < CYCLES - 1 else train_frames[c * block:]
        # ── WAKE: 그래프 흡수 (코어 frozen) + online 코어는 실시간 학습(참조) ──
        for _t, objs, _p in blk:
            cur = list(dict.fromkeys(objs))
            for i in range(len(cur)):
                for j in range(i + 1, len(cur)):
                    HC.cap_add(W, cur[i], cur[j], 0.1); HC.cap_add(W, cur[j], cur[i], 0.1)
            core_online.learn(cur, node_pool)          # online 참조 (raw 프레임)
            for n in cur:
                if n not in seen:
                    seen.add(n); node_pool.append(n)
        if c == 0:
            early_probe = [(a, b) for (a, b) in testset if a in seen and b in seen][:200]
        # ── SLEEP: 그래프 replay로 sleep 코어만 학습 (raw 프레임 안 봄) ──
        sleep_distill(core_sleep, W, node_pool, nrng, REPLAY_EPISODES, EPISODE_SIZE, DISTILL_STEPS)
        # ── 측정 (retrieval=그래프 frozen; 각 예측기로 held-out MRR) ──
        g_mrr = eval_mrr(lambda a, c_: HC.graph_score(W, a, c_), testset, seen, nrng)
        s_mrr = eval_mrr(lambda a, c_: core_sleep.score(a, c_), testset, seen, nrng)
        o_mrr = eval_mrr(lambda a, c_: core_online.score(a, c_), testset, seen, nrng)
        # forgetting: sleep 코어의 초기 연상 유지
        f_mrr = eval_mrr(lambda a, c_: core_sleep.score(a, c_), early_probe, seen, nrng) if early_probe else 0.0
        cycle_log.append({
            "cycle": c + 1, "seen": len(seen),
            "graph_mrr": g_mrr, "sleep_core_mrr": s_mrr, "online_core_mrr": o_mrr,
            "forgetting_early_mrr": f_mrr, "core_norm": core_effective_norm(core_sleep),
        })
    return {"N": N, "scenes": scenes, "n_test": len(testset), "cycles": cycle_log}


def summarize(res):
    log = res["cycles"]
    s = [c["sleep_core_mrr"] for c in log]
    g = [c["graph_mrr"] for c in log]
    o = [c["online_core_mrr"] for c in log]
    f = [c["forgetting_early_mrr"] for c in log]
    # 리트머스: sleep 코어 MRR 상승 기울기 (전반 vs 후반)
    h = len(s) // 2
    slope = round(statistics.mean(s[h:]) - statistics.mean(s[:h]), 4) if len(s) >= 4 else 0.0
    return {
        "sleep_core_first": s[0], "sleep_core_last": s[-1], "sleep_core_slope": slope,
        "graph_last": g[-1], "online_last": o[-1],
        "sleep_beats_graph_last": bool(s[-1] > g[-1]),
        "sleep_vs_online_gap": round(o[-1] - s[-1], 4),
        "forgetting_first": f[0] if f else 0, "forgetting_last": f[-1] if f else 0,
        "core_norm_last": log[-1]["core_norm"],
    }


def main():
    global CYCLES, REPLAY_EPISODES, EPISODE_SIZE
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("-N", type=int, default=None)
    ap.add_argument("--scenes", type=int, default=None)
    ap.add_argument("--cycles", type=int, default=None)
    ap.add_argument("--episodes", type=int, default=None)
    ap.add_argument("--dim", type=int, default=None)
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--json-only", action="store_true", help="SUMMARY_JSON 한 줄만(워크플로용)")
    args = ap.parse_args()
    N, scenes = (4000, 6) if args.quick else (12000, 15)
    if args.N: N = args.N
    if args.scenes: scenes = args.scenes
    if args.cycles: CYCLES = args.cycles
    if args.episodes: REPLAY_EPISODES = args.episodes
    if args.dim: HC.DIM = args.dim
    if args.json_only:
        res = run(N, scenes, args.seed)
        s = summarize(res)
        print("SUMMARY_JSON: " + json.dumps(
            {"N": N, "scenes": scenes, "cycles": CYCLES, "episodes": REPLAY_EPISODES,
             "dim": HC.DIM, "seed": args.seed, **s}, ensure_ascii=False))
        return
    print(f"=== SLEEP-DISTILL PROTOTYPE (CLS wake-sleep) — N={N}, scenes={scenes}, cycles={CYCLES} ===")
    print("  그래프=fast 해마(wake) / 코어=느린 신피질(sleep에 그래프 replay로만 학습)")
    res = run(N, scenes, args.seed)
    print(f"\n  {'cycle':>6}{'seen':>7}  {'graph':>7}{'sleep✦':>8}{'online':>8}{'forget':>8}{'coreNorm':>9}")
    for c in res["cycles"]:
        print(f"  {c['cycle']:>6}{c['seen']:>7}  {c['graph_mrr']:>7}{c['sleep_core_mrr']:>8}"
              f"{c['online_core_mrr']:>8}{c['forgetting_early_mrr']:>8}{c['core_norm']:>9}")
    s = summarize(res)
    print(f"\n=== 리트머스 (retrieval=그래프 frozen; 코어 가중치만) ===")
    print(f"  sleep-distill 코어 MRR: {s['sleep_core_first']} → {s['sleep_core_last']} "
          f"(기울기 {s['sleep_core_slope']:+})  {'✅ 상승=자기학습' if s['sleep_core_slope'] > 0 else '❌ 미상승'}")
    print(f"  sleep 코어 vs 그래프(마지막): {s['sleep_core_last']} vs {s['graph_last']}  "
          f"{'✅ 코어 초과' if s['sleep_beats_graph_last'] else '🟡 그래프 이하'}")
    print(f"  sleep vs online 격차: {s['sleep_vs_online_gap']:+} (0에 가까울수록 그래프 replay만으로 raw 근접)")
    print(f"  forgetting(초기연상): {s['forgetting_first']} → {s['forgetting_last']} "
          f"{'✅ 유지' if s['forgetting_last'] >= s['forgetting_first'] * 0.85 else '⚠️ 망각'}")
    print(f"  collapse(코어 norm): {s['core_norm_last']} (clip {HC.MAX_NORM} 이내=안정)")

    out = {"timestamp": datetime.now(timezone.utc).isoformat(),
           "config": {"N": N, "scenes": scenes, "cycles": CYCLES, "replay_episodes": REPLAY_EPISODES,
                      "episode_size": EPISODE_SIZE, "cap": CAP, "dim": HC.DIM, "max_norm": HC.MAX_NORM},
           "result": res, "summary": s}
    today = datetime.now().strftime("%Y%m%d")
    path = OUT / f"sleep_distill_{today}.json"
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n[out] {path}")


if __name__ == "__main__":
    main()
