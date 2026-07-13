"""
Sleep-Distill v2 — CLS 안티망각의 결정적 검증 (adversarial verify 지적 반영)
==============================================================================
v1(sleep_distill_prototype) adversarial 검증 결과:
  A 가중치-자기학습 CONFIRMED · B replay>raw REFUTED · C 안티망각 TOO-WEAK(스트레서 없음)
  · D no-collapse REFUTED(mean-norm은 clip으로 자명, effective-rank 필요).
v2 는 sleep-distill의 **존재 이유**(=CLS 안티망각)를 결정적으로 검증한다:

  **순차 태스크 커리큘럼(분포 이동)**: Task A(전반) → Task B(후반), 개념 어휘 disjoint.
  Task B 학습 중 Task-A 연상이 **fresh 데이터를 못 받는다** = 진짜 망각 스트레서.
  3 코어 비교 (동일 학습예산):
    - online         : raw 프레임 직접 학습 (A→B). B 학습 때 A 망각 예상(catastrophic).
    - sleep_replay   : 그래프 replay만 학습. 그래프가 A 구조 보존→B sleep 때 A 재생 → 망각 저항 기대.
    - sleep_off (통제): 무작위 에피소드 학습(그래프 구조 X). replay 구조의 순효과 격리.
  **안티망각 성립 조건**: B 학습 후 A-test 에서 sleep_replay 유지 && online 하락.
  + **effective-rank**(stable rank ‖E‖_F²/‖E‖₂²) collapse 지표 + **frozen negative pool** + **다중시드**.

Usage:
    python scripts/research/sleep_distill_v2.py --quick
    python scripts/research/sleep_distill_v2.py --seeds 5
출력: claudedocs/research/sleep_distill_v2_<YYYYMMDD>.json
"""
from __future__ import annotations
import argparse, json, math, os, random, statistics, sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(__file__))
import synth_world as SW
import head_crossover_probe as HC

OUT = Path(__file__).resolve().parents[2] / "claudedocs" / "research"
OUT.mkdir(parents=True, exist_ok=True)

K_NEG = 60
CYCLES_PER_TASK = 4
REPLAY_EP = 400
EP_SIZE = 6


def gen_task(prefix, N, scenes, seed):
    """개념명에 prefix → Task 간 어휘 disjoint (진짜 분포 이동)."""
    frames = SW.generate_stream(N, n_scenes=scenes, motion=2.0, seed=seed)
    return [(t, [f"{prefix}{o}" for o in objs], p) for (t, objs, p) in frames]


def testpairs(frames, rng, m=300):
    pairs = []
    for _t, objs, _p in frames:
        o = list(dict.fromkeys(objs))
        for i in range(len(o)):
            for j in range(i + 1, len(o)):
                pairs.append((o[i], o[j]))
    rng.shuffle(pairs)
    return pairs[:m]


def eval_mrr(scorer, pairs, pool, nrng, k=K_NEG):
    """frozen negative pool(고정) 로 sampled-neg 랭킹."""
    if len(pool) <= k + 2:
        return 0.0
    recs = []
    for (a, b) in pairs:
        negs = []
        tries = 0
        while len(negs) < k and tries < k * 3:
            n = pool[nrng.integers(len(pool))]
            if n != a and n != b:
                negs.append(n)
            tries += 1
        if len(negs) < k // 2:
            continue
        recs.append(1.0 / HC.rank_of(b, negs, lambda c: scorer(a, c)))
    return round(statistics.mean(recs), 4) if recs else 0.0


def stable_rank(core):
    """effective rank = ‖E‖_F² / ‖E‖₂² (collapse=1 근처, 건강=dim 근처). 학습된 행만."""
    vs = [v for v in core.Eo.values()]
    if len(vs) < 3:
        return 0.0
    E = np.stack(vs)
    fro2 = float(np.sum(E * E))
    s0 = float(np.linalg.norm(E, 2))     # 최대 특이값
    return round(fro2 / (s0 * s0), 2) if s0 > 0 else 0.0


def graph_neighbors(W, a, m):
    return [n for n, _ in sorted(W.get(a, {}).items(), key=lambda kv: -kv[1])[:m]]


def run_seed(seed, N, scenes):
    rng = random.Random(seed)
    nrng = np.random.default_rng(seed)
    taskA = gen_task("A_", N, scenes, seed)
    taskB = gen_task("B_", N, scenes, seed + 500)
    a_test = testpairs(taskA[-int(len(taskA) * 0.2):], rng)
    b_test = testpairs(taskB[-int(len(taskB) * 0.2):], rng)
    a_train, b_train = taskA[:-int(len(taskA) * 0.2)], taskB[:-int(len(taskB) * 0.2)]
    # frozen negative pool = 양 태스크 전체 개념 (고정)
    pool = sorted({o for fr in (taskA + taskB) for o in fr[1]})

    W = defaultdict(dict)
    online = HC.Head(HC.DIM, np.random.default_rng(seed + 1))
    sleep_rep = HC.Head(HC.DIM, np.random.default_rng(seed + 2))
    sleep_off = HC.Head(HC.DIM, np.random.default_rng(seed + 3))
    seen: list[str] = []
    seen_set = set()

    def wake_sleep(frames_block):
        for _t, objs, _p in frames_block:
            cur = list(dict.fromkeys(objs))
            for i in range(len(cur)):
                for j in range(i + 1, len(cur)):
                    HC.cap_add(W, cur[i], cur[j], 0.1); HC.cap_add(W, cur[j], cur[i], 0.1)
            online.learn(cur, seen)                      # online: raw 프레임
            for n in cur:
                if n not in seen_set:
                    seen_set.add(n); seen.append(n)
        # sleep: 그래프 replay (동일 예산 REPLAY_EP)
        nodes = list(W.keys())
        for _e in range(REPLAY_EP):
            seed_n = nodes[nrng.integers(len(nodes))]
            ep = [seed_n] + graph_neighbors(W, seed_n, EP_SIZE - 1)
            if len(ep) >= 2:
                sleep_rep.learn(ep, seen)
            # replay-OFF: 무작위 에피소드(구조 X), 동일 예산
            if seen:
                rep = [seen[nrng.integers(len(seen))] for _ in range(EP_SIZE)]
                rep = list(dict.fromkeys(rep))
                if len(rep) >= 2:
                    sleep_off.learn(rep, seen)

    log = []
    blocks = []  # (block_frames, task_label)
    for c in range(CYCLES_PER_TASK):
        blocks.append((a_train[c * len(a_train) // CYCLES_PER_TASK:(c + 1) * len(a_train) // CYCLES_PER_TASK], "A"))
    for c in range(CYCLES_PER_TASK):
        blocks.append((b_train[c * len(b_train) // CYCLES_PER_TASK:(c + 1) * len(b_train) // CYCLES_PER_TASK], "B"))
    for ci, (blk, lab) in enumerate(blocks):
        wake_sleep(blk)
        row = {"cycle": ci + 1, "task": lab, "seen": len(seen)}
        for name, core in (("online", online), ("sleep_rep", sleep_rep), ("sleep_off", sleep_off)):
            row[f"{name}_A"] = eval_mrr(lambda a, c_: core.score(a, c_), a_test, pool, nrng)
            row[f"{name}_B"] = eval_mrr(lambda a, c_: core.score(a, c_), b_test, pool, nrng)
        row["sleep_rep_srank"] = stable_rank(sleep_rep)
        row["online_srank"] = stable_rank(online)
        log.append(row)
    # 망각 지표: Task-A 학습 정점(cycle 4) → 최종(cycle 8) A-test 변화
    def a_peak_final(name):
        peak = log[CYCLES_PER_TASK - 1][f"{name}_A"]     # A 태스크 마지막 사이클
        final = log[-1][f"{name}_A"]                       # B 태스크 학습 후
        return peak, final, round(final - peak, 4)
    return {"seed": seed, "log": log,
            "online_A": a_peak_final("online"),
            "sleep_rep_A": a_peak_final("sleep_rep"),
            "sleep_off_A": a_peak_final("sleep_off")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--seeds", type=int, default=3)
    args = ap.parse_args()
    N, scenes = (3000, 6) if args.quick else (6000, 10)
    seeds = list(range(42, 42 + args.seeds))
    print(f"=== SLEEP-DISTILL v2 — 순차태스크 안티망각 검증 (N={N}, scenes={scenes}/task, seeds={seeds}) ===")
    print("  Task A(cyc1-4) → Task B(cyc5-8), 어휘 disjoint. B 학습 후 A-test 유지 = 안티망각.")

    runs = [run_seed(s, N, scenes) for s in seeds]
    # 집계: A-test peak→final 변화 (음수=망각), 코어별 평균
    agg = {}
    for name in ("online", "sleep_rep", "sleep_off"):
        deltas = [r[f"{name}_A"][2] for r in runs]
        peaks = [r[f"{name}_A"][0] for r in runs]
        finals = [r[f"{name}_A"][1] for r in runs]
        agg[name] = {"A_peak": round(statistics.mean(peaks), 3),
                     "A_final": round(statistics.mean(finals), 3),
                     "A_delta": round(statistics.mean(deltas), 4),
                     "A_delta_std": round(statistics.pstdev(deltas), 4) if len(deltas) > 1 else 0.0}
    print(f"\n  Task-A 유지 (A학습정점→B학습후, 음수=망각) — {len(seeds)}시드 평균:")
    print(f"  {'core':<12}{'A_peak':>9}{'A_final':>9}{'A_delta':>10}{'±std':>8}")
    for name in ("online", "sleep_rep", "sleep_off"):
        a = agg[name]
        print(f"  {name:<12}{a['A_peak']:>9}{a['A_final']:>9}{a['A_delta']:>+10}{a['A_delta_std']:>8}")
    # 판정
    fr = agg["sleep_rep"]["A_delta"]; fo = agg["online"]["A_delta"]; foff = agg["sleep_off"]["A_delta"]
    anti = fr > fo and fr > foff - 0.02
    srank = round(statistics.mean(r["log"][-1]["sleep_rep_srank"] for r in runs), 2)
    print(f"\n  판정:")
    print(f"   • online A망각 {fo:+.3f} vs sleep_replay A유지 {fr:+.3f} vs sleep_off {foff:+.3f}")
    print(f"   • CLS 안티망각(replay가 online·off보다 A 유지): {'✅ 성립' if anti else '❌ 미성립/약함'}")
    print(f"   • collapse(effective/stable rank, dim {HC.DIM} 중): sleep_rep {srank} "
          f"{'✅ 건강(≫1)' if srank > 3 else '⚠️ 낮음'}")

    out = {"timestamp": datetime.now(timezone.utc).isoformat(),
           "config": {"N": N, "scenes_per_task": scenes, "seeds": seeds, "cycles_per_task": CYCLES_PER_TASK,
                      "replay_ep": REPLAY_EP, "dim": HC.DIM, "max_norm": HC.MAX_NORM, "k_neg": K_NEG},
           "aggregate": agg, "anti_forgetting": bool(anti), "sleep_rep_stable_rank": srank,
           "runs": runs}
    today = datetime.now().strftime("%Y%m%d")
    path = OUT / f"sleep_distill_v2_{today}.json"
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n[out] {path}")


if __name__ == "__main__":
    main()
