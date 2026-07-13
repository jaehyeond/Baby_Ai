"""
Scaling Study — 자기학습 스택의 데이터-스케일 거동 규명
==============================================================================
program_roadmap Phase 4. 데이터 밀도가 바인딩 제약(3회 확인)이므로, 합성 스트림
(synth_world, 실제 통계 캘리브레이션)을 **스케일 격자**에서 돌려 다음을 정량화한다:

  Q1. RW 음성증거의 빈도(additive) 대비 우위가 밀도(N)·다양성(scenes)에 따라 커지는가?
      (현재 실데이터선 +3.5%뿐 — 데이터가 늘면 결정적이 되는가?)
  Q2. 학습 파라미터 코어(trainable head)가 그래프를 어느 N에서 역전하는가?
      (=Phase 2 로컬코어가 정당해지는 지점. 현재 518노드선 그래프가 이김.)
  Q3. embodied next-frame 예측에서 그래프가 popularity를 언제 넘는가?
      (움직임/밀도가 감각운동 예측을 비자명하게 만드는가?)

기존 하니스 재사용: prequential_experiment.run_arm (edgebank/additive/rw),
trainable_head_experiment.run_head. 합성 events = synth_world.to_events (동일 포맷).

Usage:
    python scripts/research/scaling_study.py            # 기본 격자
    python scripts/research/scaling_study.py --quick    # 빠른 검증(작은 격자)
출력: claudedocs/research/scaling_<YYYYMMDD>.json
"""
from __future__ import annotations
import argparse, json, os, statistics, sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "baseline"))
import synth_world as SW
import prequential_experiment as PQ
import trainable_head_experiment as TH

OUT = Path(__file__).resolve().parents[2] / "claudedocs" / "research"
OUT.mkdir(parents=True, exist_ok=True)
SEED = 42


# ── Q3: embodied next-frame 예측 (graph vs popularity, pose 조건부) ──────────
def embodied_metric(frames, k=10):
    """online: 프레임 진행하며 누적 co-occurrence 그래프로 다음 프레임 NEW 객체 예측.
    graph_spread(2-hop) vs popularity(최빈) recall@k. pose_delta로 저/고움직임 층화."""
    W = defaultdict(lambda: defaultdict(float))
    freq = Counter()
    seen = set()
    gs_all, pop_all = [], []
    gs_hi, gs_lo = [], []       # 고/저 움직임 (pose_delta 기준)
    deltas = []
    for i in range(len(frames) - 1):
        cur = set(frames[i][1]); nxt = set(frames[i + 1][1])
        new = nxt - cur
        pose_a, pose_b = frames[i][2], frames[i + 1][2]
        pdelta = sum((x - y) ** 2 for x, y in zip(pose_a, pose_b)) ** 0.5
        if i >= 20 and new and cur:
            # popularity: 최빈 객체 top-k (현재 프레임 제외)
            pop = [n for n, _ in freq.most_common() if n not in cur][:k]
            r_pop = len(set(pop) & new) / len(new)
            # graph_spread: cur 에서 2-hop 확산 top-k (허브 폭주 방지 위해 상위가중 이웃만 확장)
            sc = defaultdict(float)
            for a in cur:
                nbrs = W.get(a, {})
                top_nbrs = sorted(nbrs.items(), key=lambda kv: -kv[1])[:40]
                for b, w in top_nbrs:
                    if b not in cur:
                        sc[b] += w
                    for c, w2 in sorted(W.get(b, {}).items(), key=lambda kv: -kv[1])[:40]:
                        if c not in cur:
                            sc[c] += 0.4 * w * w2
            gs = [n for n, _ in sorted(sc.items(), key=lambda kv: -kv[1])[:k]]
            r_gs = len(set(gs) & new) / len(new)
            gs_all.append(r_gs); pop_all.append(r_pop); deltas.append(pdelta)
        # learn: co-occurrence (additive) + freq
        cl = list(cur)
        for a in range(len(cl)):
            freq[cl[a]] += 1
            for b in range(a + 1, len(cl)):
                W[cl[a]][cl[b]] += 0.1
                W[cl[b]][cl[a]] += 0.1
        for n in cur:
            seen.add(n)
    # pose 층화 (중앙값 기준)
    if deltas:
        med = statistics.median(deltas)
        for r, dd in zip(gs_all, deltas):
            (gs_hi if dd > med else gs_lo).append(r)
    return {
        "graph_recall@10_new": round(statistics.mean(gs_all), 3) if gs_all else 0,
        "popularity_recall@10_new": round(statistics.mean(pop_all), 3) if pop_all else 0,
        "graph_minus_pop": round((statistics.mean(gs_all) - statistics.mean(pop_all)), 3) if gs_all else 0,
        "graph_hi_motion": round(statistics.mean(gs_hi), 3) if gs_hi else 0,
        "graph_lo_motion": round(statistics.mean(gs_lo), 3) if gs_lo else 0,
        "n": len(gs_all),
    }


def run_cell(N, n_scenes, motion, seed):
    frames = SW.generate_stream(N, n_scenes=n_scenes, motion=motion, seed=seed)
    events = SW.to_events(frames)
    st = SW.stats(frames)
    eb = PQ.run_arm(events, "edgebank", seed)
    add = PQ.run_arm(events, "additive", seed)
    rw = PQ.run_arm(events, "rw", seed)
    head = TH.run_head(events, seed)
    emb = embodied_metric(frames)
    best_graph = max(add["MRR"], rw["MRR"])
    return {
        "N": N, "n_scenes": n_scenes, "motion": motion,
        "vocab": st["vocab"], "objs_per_frame": st["objs_per_frame"],
        "singleton_frac": st["singleton_frac"],
        "edgebank_mrr": eb["MRR"], "additive_mrr": add["MRR"], "rw_mrr": rw["MRR"],
        "head_mrr": head["MRR"],
        "rw_vs_additive": round(rw["MRR"] - add["MRR"], 4),
        "rw_vs_additive_pct": round(100 * (rw["MRR"] - add["MRR"]) / add["MRR"], 1) if add["MRR"] else 0,
        "head_vs_graph": round(head["MRR"] - best_graph, 4),
        "embodied": emb,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()

    if args.quick:
        grid = [(256, 1, 2.0), (256, 8, 2.0), (1024, 1, 2.0), (1024, 8, 2.0)]
    else:
        # 축1: N 추세(다양 scenes=8 고정) — Q1 밀도·Q2 head역전. N=4096 상한
        #   (N=12000은 prequential PPR 채점이 ghome 허브서 O(V^2) 폭주 → 불가; 별도 probe 필요)
        trend_n = [(N, 8, 2.0) for N in (256, 1024, 4096)]
        # 축2: 다양성 추세(N=2048 고정) — Q1 다양성이 RW우위 원천인가
        trend_sc = [(2048, sc, 2.0) for sc in (1, 4, 16, 32)]
        grid = trend_n + trend_sc
    print(f"=== SCALING STUDY — {len(grid)} cells ===")
    print("  (합성 스트림, 실제 통계 캘리브레이션 ~13% dev. Q1 RW우위·Q2 head역전·Q3 embodied)")
    print(f"\n  {'N':>5}{'scenes':>7}{'vocab':>6}  {'EB':>6}{'add':>6}{'rw':>6}{'head':>6}"
          f"  {'RW-add%':>8}{'head-gph':>9}  {'gph-pop':>8}")
    rows = []
    for (N, sc, mo) in grid:
        r = run_cell(N, sc, mo, SEED)
        rows.append(r)
        print(f"  {N:>5}{sc:>7}{r['vocab']:>6}  {r['edgebank_mrr']:>6}{r['additive_mrr']:>6}"
              f"{r['rw_mrr']:>6}{r['head_mrr']:>6}  {r['rw_vs_additive_pct']:>7}%"
              f"{r['head_vs_graph']:>9}  {r['embodied']['graph_minus_pop']:>8}")

    # ── 요약: 스케일링 추세 ──
    print("\n=== 스케일링 추세 (핵심 질문) ===")
    by_n = defaultdict(list)
    for r in rows:
        by_n[r["N"]].append(r)
    print("  Q1 RW우위(rw-add%) — N별 평균:")
    for N in sorted(by_n):
        v = statistics.mean(x["rw_vs_additive_pct"] for x in by_n[N])
        print(f"    N={N:<6} {v:+.1f}%")
    print("  Q2 head역전(head-graph MRR) — N별 평균 (양수=코어가 그래프 이김):")
    for N in sorted(by_n):
        v = statistics.mean(x["head_vs_graph"] for x in by_n[N])
        print(f"    N={N:<6} {v:+.4f}  {'✅ 코어 우위' if v > 0 else '❌ 그래프 우위'}")
    print("  Q3 embodied(graph-popularity) — N별 평균 (양수=구조가 popularity 이김):")
    for N in sorted(by_n):
        v = statistics.mean(x["embodied"]["graph_minus_pop"] for x in by_n[N])
        print(f"    N={N:<6} {v:+.3f}")
    # 움직임 조건부 (전체 평균)
    hi = statistics.mean(r["embodied"]["graph_hi_motion"] for r in rows)
    lo = statistics.mean(r["embodied"]["graph_lo_motion"] for r in rows)
    print(f"  Q3b pose조건부: graph recall 고움직임 {hi:.3f} vs 저움직임 {lo:.3f}")

    out = {"timestamp": datetime.now(timezone.utc).isoformat(),
           "calibration_note": "synth_world ~13% mean-dev vs real 45-frame stats",
           "grid": grid, "cells": rows}
    today = datetime.now().strftime("%Y%m%d")
    path = OUT / f"scaling_{today}.json"
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n[out] {path}")


if __name__ == "__main__":
    main()
