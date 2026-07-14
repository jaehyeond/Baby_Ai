"""
Curiosity Loop — Phase 3 첫 조각: 예측오차 루프 닫기 (active inference / ICM 검증)
==============================================================================
program_roadmap Phase 3 / self_learning_architecture (A)(D). 지금까지 뇌는 "배우지만
무기력" — 코어가 예측오차를 계산하나 그걸로 **아무 행동도 안 한다**. 루프를 닫는다 =
자기 예측오차(surprise)로 **무엇을 볼지(주의·탐색·호기심)를 스스로 정한다**.

검증 질문 (measure-first): **자기 예측오차로 행동을 정하는 뇌가 무작위보다 빨리 배우는가?**
= active inference / ICM 의 핵심 주장. 통과해야 라이브 배선(conversation 파이프라인)이 정당.

설계
----
- 환경: K개 학습가능 장면(구조 O) + 노이즈 장면 1개(무작위=예측불가, noisy-TV 함정).
- 뇌: degree-capped co-occurrence 그래프 (head_crossover 재사용).
- 정책(매 스텝 어느 장면 볼지):
    random   : 균등 (기준선)
    surprise : 현재 예측오차 최대 장면 (raw ICM — 노이즈 쫓을 위험)
    progress : 최근 예측오차 감소율 최대 (learning progress, Oudeyer — 노이즈-강건)
- 측정: held-out 예측 MRR vs 스텝 (학습곡선) + 노이즈 장면 방문율.
가설: progress > random(호기심이 학습 가속) & surprise는 노이즈에 갇힘.

Usage: python scripts/research/curiosity_loop.py
출력: claudedocs/research/curiosity_loop_<YYYYMMDD>.json
"""
from __future__ import annotations
import argparse, json, os, random, statistics, sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(__file__))
from head_crossover_probe import cap_add, graph_score, rank_of, CAP

OUT = Path(__file__).resolve().parents[2] / "claudedocs" / "research"
OUT.mkdir(parents=True, exist_ok=True)
SEED = 42
# 노이즈-지배 세계(현실 근사): 볼 수 있는 것의 대부분이 예측불가. 호기심의 임무 =
# 학습가능한 구조를 '찾아' 예산을 거기 쓰는 것. random은 예산 대부분을 노이즈에 허비.
K_SCENES = 20           # 학습가능 장면
N_NOISE = 40            # 노이즈 장면 (전체의 2/3 = 노이즈 지배)
OBJ_MIN, OBJ_MAX = 6, 14
NOISE_VOCAB = 400
STEPS = 1200            # 예산: 노이즈 피하면 학습가능 장면 충분학습, 못 피하면 부족
EVAL_EVERY = 60
K_NEG = 40
EXP_SIZE = (3, 6)


def build_world(rng):
    scenes = {}
    for s in range(K_SCENES):
        n = rng.randint(OBJ_MIN, OBJ_MAX)
        scenes[f"s{s}"] = [f"s{s}_o{i}" for i in range(n)]
    noise_pool = [f"z{i}" for i in range(NOISE_VOCAB)]
    return scenes, noise_pool


def sample_exp(scene, scenes, noise_pool, rng):
    if scene.startswith("NOISE"):
        k = rng.randint(*EXP_SIZE)
        return rng.sample(noise_pool, k)          # 매번 무작위 = 구조 없음(학습 불가)
    objs = scenes[scene][:]
    rng.shuffle(objs)
    k = rng.randint(*EXP_SIZE)
    return objs[:min(k, len(objs))]


def predict_error(W, exp, nrng, pool):
    """경험 학습 '전' 예측오차 = 1 - mean(공동활성 쌍 recall). 높을수록 surprise."""
    rr = []
    for i in range(len(exp)):
        for j in range(len(exp)):
            if i == j:
                continue
            a, b = exp[i], exp[j]
            negs = [pool[nrng.randrange(len(pool))] for _ in range(K_NEG)]
            negs = [n for n in negs if n != a and n != b]
            if len(negs) < K_NEG // 2:
                continue
            rr.append(1.0 / rank_of(b, negs, lambda c: graph_score(W, a, c)))
    return 1.0 - (statistics.mean(rr) if rr else 0.0)


def learn(W, exp):
    for i in range(len(exp)):
        for j in range(i + 1, len(exp)):
            cap_add(W, exp[i], exp[j], 0.1); cap_add(W, exp[j], exp[i], 0.1)


def eval_mrr(W, holdout, pool, nrng):
    rr = []
    for (a, b) in holdout:
        negs = [pool[nrng.randrange(len(pool))] for _ in range(K_NEG)]
        negs = [n for n in negs if n != a and n != b]
        if len(negs) < K_NEG // 2:
            continue
        rr.append(1.0 / rank_of(b, negs, lambda c: graph_score(W, a, c)))
    return round(statistics.mean(rr), 4) if rr else 0.0


def run_policy(policy, scenes, noise_pool, holdout, pool, seed):
    rng = random.Random(seed); nrng = random.Random(seed + 1)
    W = defaultdict(dict)
    all_scenes = list(scenes) + [f"NOISE{i}" for i in range(N_NOISE)]
    err = {s: 1.0 for s in all_scenes}         # optimistic init (미방문=최대우선)
    prev_err = dict(err)
    progress = {s: 1.0 for s in all_scenes}
    visits = defaultdict(int)
    curve = []
    for step in range(STEPS):
        # 정책: 장면 선택
        if policy == "random":
            scene = rng.choice(all_scenes)
        elif policy == "surprise":
            m = max(err.values()); scene = rng.choice([s for s in all_scenes if err[s] >= m - 1e-9])
        elif policy == "progress":
            m = max(progress.values()); scene = rng.choice([s for s in all_scenes if progress[s] >= m - 1e-9])
        visits[scene] += 1
        exp = sample_exp(scene, scenes, noise_pool, rng)
        e = predict_error(W, exp, nrng, pool)          # 학습 전 surprise
        # 장면별 오차 EMA + learning progress(감소율)
        prev = err[scene]
        err[scene] = 0.7 * err[scene] + 0.3 * e
        progress[scene] = max(0.0, prev - err[scene])  # 오차가 줄면 진전↑ (노이즈=안 줄어 progress≈0)
        learn(W, exp)
        if (step + 1) % EVAL_EVERY == 0:
            curve.append(eval_mrr(W, holdout, pool, nrng))
    noise_frac = round(sum(v for s, v in visits.items() if s.startswith("NOISE")) / STEPS, 3)
    return {"policy": policy, "curve": curve, "final_mrr": curve[-1] if curve else 0,
            "noise_visit_frac": noise_frac,
            "auc": round(sum(curve) / len(curve), 4) if curve else 0}   # 학습속도 대리(곡선 아래면적)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--seeds", type=int, default=3); args = ap.parse_args()
    rng = random.Random(SEED)
    scenes, noise_pool = build_world(rng)
    pool = [o for objs in scenes.values() for o in objs] + noise_pool  # 음성샘플 전체 어휘
    # held-out: 각 학습장면의 공동활성 쌍 일부 (고정 테스트)
    holdout = []
    for s, objs in scenes.items():
        for i in range(len(objs)):
            for j in range(i + 1, len(objs)):
                holdout.append((objs[i], objs[j]))
    random.Random(7).shuffle(holdout); holdout = holdout[:250]

    print(f"=== CURIOSITY LOOP (Phase 3: 예측오차 루프 닫기) — {K_SCENES}학습장면+노이즈, {STEPS}스텝 ===")
    print("  질문: 자기 예측오차로 어디 볼지 정하는 뇌가 무작위보다 빨리 배우나?\n")
    results = {}
    for policy in ("random", "surprise", "progress"):
        runs = [run_policy(policy, scenes, noise_pool, holdout, pool, SEED + i) for i in range(args.seeds)]
        curve = [round(statistics.mean(c), 4) for c in zip(*[r["curve"] for r in runs])]
        results[policy] = {
            "final_mrr": round(statistics.mean(r["final_mrr"] for r in runs), 4),
            "auc": round(statistics.mean(r["auc"] for r in runs), 4),
            "noise_visit_frac": round(statistics.mean(r["noise_visit_frac"] for r in runs), 3),
            "curve_mean": curve,
        }
    print(f"  {'policy':<10}{'final MRR':>11}{'AUC(학습속도)':>16}{'노이즈방문%':>13}")
    for p in ("random", "surprise", "progress"):
        r = results[p]
        print(f"  {p:<10}{r['final_mrr']:>11}{r['auc']:>16}{r['noise_visit_frac']*100:>11.1f}%")
    print(f"\n  학습곡선(MRR, {EVAL_EVERY}스텝 간격):")
    for p in ("random", "surprise", "progress"):
        print(f"    {p:<10} {results[p]['curve_mean']}")

    rnd, sur, pro = results["random"], results["surprise"], results["progress"]
    print(f"\n=== 판정 (Phase 3 루프가 학습을 가속하는가) ===")
    print(f"  progress vs random (AUC): {pro['auc']} vs {rnd['auc']} → "
          f"{'✅ 호기심(learning-progress)이 학습 가속' if pro['auc'] > rnd['auc'] else '❌ 이득 없음'}")
    print(f"  surprise 노이즈 함정: 노이즈 방문 {sur['noise_visit_frac']*100:.0f}% "
          f"vs progress {pro['noise_visit_frac']*100:.0f}% → "
          f"{'✅ raw surprise는 noisy-TV에 갇힘(learning-progress가 정답)' if sur['noise_visit_frac'] > pro['noise_visit_frac']*1.5 else '🟡 차이 약함'}")

    out = {"timestamp": datetime.now(timezone.utc).isoformat(),
           "config": {"k_scenes": K_SCENES, "steps": STEPS, "noise_vocab": NOISE_VOCAB, "seeds": args.seeds},
           "results": results,
           "verdict": {"curiosity_accelerates": bool(pro["auc"] > rnd["auc"]),
                       "surprise_noise_trap": bool(sur["noise_visit_frac"] > pro["noise_visit_frac"] * 1.5)}}
    today = datetime.now().strftime("%Y%m%d")
    path = OUT / f"curiosity_loop_{today}.json"
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n[out] {path}")


if __name__ == "__main__":
    main()
