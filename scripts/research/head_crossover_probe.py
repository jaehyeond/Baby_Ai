"""
Head-Crossover Probe — 학습 파라미터 코어가 그래프를 언제 역전하는가 (Phase 2 go/no-go)
==============================================================================
scaling_study 후속. 핵심 질문 Q2: **trainable 코어가 어느 데이터 규모에서 그래프를 이기는가?**
= Phase 2(로컬 trainable 코어)가 정당해지는 지점. scaling_study는 N≤4096서 역전 없음 +
prequential PPR이 ghome 허브서 O(V²) 폭주로 대규모 미측정. 이 probe가 두 병목을 해결:

  병목1 (eval O(V)): **sampled-negative 랭킹** — 참 타깃을 K_neg개 샘플 음성 중 랭킹
    (표준 대규모 link-prediction, e.g. Bordes NeurIPS'13). O(K_neg)로 고정.
  병목2 (허브 O(V²)): **degree-cap** — 노드당 fan-out ≤ CAP (생물학적 시냅스 한계 정합) +
    direct-edge + bounded common-neighbor 스코어러. 모든 arm O(CAP) per candidate.

동일 스트림·동일 샘플음성으로 4 arm 완전 paired 비교:
  edgebank(암기) · additive(빈도 그래프) · rw(음성증거 그래프) · head(학습 파라미터 코어).
N 을 orders-of-magnitude 로 키우며(scenes ∝ N, 실제처럼 다양성 동반) head−graph 곡선을 본다.

Usage:
    python scripts/research/head_crossover_probe.py --quick
    python scripts/research/head_crossover_probe.py            # 대규모 격자
출력: claudedocs/research/head_crossover_<YYYYMMDD>.json
"""
from __future__ import annotations
import argparse, json, math, os, random, statistics, sys
from collections import defaultdict, deque, Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "baseline"))
import synth_world as SW

OUT = Path(__file__).resolve().parents[2] / "claudedocs" / "research"
OUT.mkdir(parents=True, exist_ok=True)

SEED = 42
WARMUP = 60
K_NEG = 60           # 샘플 음성 수 (랭킹 후보 = 1 참 + K_NEG 음성)
EVAL_FRAC = 0.25     # 쿼리 채점 비율 (학습은 100%, 채점만 샘플 → 대규모 tractable)
CAP = 48             # degree cap (노드당 fan-out 상한)
DIM = 48             # head 임베딩 차원
LR = 0.15
HEAD_L2 = 1e-4
MAX_NORM = 4.0       # 임베딩 L2 norm 상한 (항상성 — 발산 방지)
HEAD_STEPS = 3
HEAD_NEG = 8
EDGEBANK_W = 200
HITS = (1, 5, 10)


def sigmoid(x):
    return 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, x))))


# ── degree-capped 가중 그래프 (additive / rw 공용) ──────────────────────────
def cap_add(W, a, b, delta, cap=CAP):
    row = W[a]
    row[b] = row.get(b, 0.0) + delta
    if len(row) > cap:
        weak = min(row, key=row.get)
        if weak != b:
            del row[weak]


def graph_score(W, a, c):
    """direct edge + bounded common-neighbor (a,c 이웃 교집합, cap로 bounded)."""
    row = W.get(a, {})
    s = row.get(c, 0.0)
    crow = W.get(c, {})
    # common neighbors (작은 쪽 순회)
    small, big = (row, crow) if len(row) <= len(crow) else (crow, row)
    cn = 0.0
    for n in small:
        if n in big:
            cn += min(small[n], big[n])
    return s + 0.5 * cn


# ── trainable head (numpy 임베딩, candidate 스코어링) ───────────────────────
class Head:
    def __init__(self, dim, rng):
        self.dim = dim; self.rng = rng
        self.Eo: dict[str, np.ndarray] = {}
        self.Ei: dict[str, np.ndarray] = {}

    def vec(self, store, c):
        v = store.get(c)
        if v is None:
            v = (self.rng.standard_normal(self.dim) * 0.1)
            store[c] = v
        return v

    def score(self, a, c):
        ea = self.Eo.get(a); ec = self.Ei.get(c)
        return float(ea @ ec) if ea is not None and ec is not None else 0.0

    def step(self, a, b, y):
        ea = self.vec(self.Eo, a); eb = self.vec(self.Ei, b)
        d = sigmoid(float(ea @ eb)) - y
        eb0 = eb.copy()                     # 대칭 갱신: 같은 eb 사용(순차오염 방지)
        ea -= LR * (d * eb0 + HEAD_L2 * ea)
        eb -= LR * (d * ea + HEAD_L2 * eb)
        # 임베딩 norm clipping = 항상성(그래프 degree-cap의 파라미터 판; 발산 방지, Zenke-Gerstner)
        na = math.sqrt(float(ea @ ea))
        if na > MAX_NORM:
            ea *= MAX_NORM / na
        nb = math.sqrt(float(eb @ eb))
        if nb > MAX_NORM:
            eb *= MAX_NORM / nb

    def learn(self, cids, all_nodes):
        cset = set(cids)
        for _ in range(HEAD_STEPS):
            for a in cids:
                for b in cids:
                    if b != a:
                        self.step(a, b, 1.0)
                for _i in range(HEAD_NEG):
                    if all_nodes:
                        n = all_nodes[self.rng.integers(len(all_nodes))]
                        if n not in cset and n != a:
                            self.step(a, n, 0.0)


def rank_of(true_b, negs, scorer):
    """참 타깃의 sampled-negative 랭킹 (동점은 평균순위). 최상=1."""
    sb = scorer(true_b)
    higher = sum(1 for n in negs if scorer(n) > sb)
    equal = sum(1 for n in negs if scorer(n) == sb)
    return higher + 1 + equal / 2.0     # 위 higher개 다음, 동점그룹(참+equal) 평균순위


def run_probe(frames, seed):
    rng = random.Random(seed)
    nrng = np.random.default_rng(seed)
    W_add = defaultdict(dict)
    W_rw = defaultdict(dict)
    head = Head(DIM, nrng)
    eb_recent = deque()
    eb_count = Counter()
    freq = Counter()
    seen = set(); all_nodes = []
    arms = ["edgebank", "additive", "rw", "head"]
    recs = {a: [] for a in arms}

    for idx, (t, objs, _pose) in enumerate(frames):
        cur = [c for c in objs if c]
        cset = set(cur)
        known = [c for c in cur if c in seen]
        # ── PREDICT (sampled-negative 랭킹) ──
        if idx >= WARMUP and len(all_nodes) > K_NEG + 5:
            for a in known:
                partners = [b for b in cur if b != a and b in seen]
                for b in partners:
                    if rng.random() > EVAL_FRAC:      # 채점 샘플 (학습은 아래서 100%)
                        continue
                    # 샘플 음성 (cur·a·b 제외)
                    negs = []
                    tries = 0
                    while len(negs) < K_NEG and tries < K_NEG * 3:
                        n = all_nodes[nrng.integers(len(all_nodes))]
                        if n not in cset and n != a and n != b:
                            negs.append(n)
                        tries += 1
                    if len(negs) < K_NEG // 2:
                        continue
                    scorers = {
                        "edgebank": lambda c: eb_count.get((a, c), 0),
                        "additive": lambda c: graph_score(W_add, a, c),
                        "rw": lambda c: graph_score(W_rw, a, c),
                        "head": lambda c: head.score(a, c),
                    }
                    for arm in arms:
                        r = rank_of(b, negs, scorers[arm])
                        recs[arm].append(1.0 / r if r >= 1 else 1.0)
        # ── LEARN ──
        # additive (co-occurrence, capped)
        for i in range(len(cur)):
            freq[cur[i]] += 1
            for j in range(i + 1, len(cur)):
                cap_add(W_add, cur[i], cur[j], 0.1)
                cap_add(W_add, cur[j], cur[i], 0.1)
        # rw (negative-evidence, capped) — w→P(b|a)
        eta = 0.15
        for a in cur:
            for b in cur:
                if b != a:
                    W_rw[a][b] = W_rw[a].get(b, 0.0) + eta * (1.0 - W_rw[a].get(b, 0.0))
            # 음성샘플 depress
            for _i in range(6):
                if all_nodes:
                    n = all_nodes[nrng.integers(len(all_nodes))]
                    if n not in cset and n != a:
                        W_rw[a][n] = W_rw[a].get(n, 0.0) + eta * (0.0 - W_rw[a].get(n, 0.0))
                        if W_rw[a][n] < 1e-3:
                            W_rw[a].pop(n, None)
            if len(W_rw[a]) > CAP:
                weak = min(W_rw[a], key=W_rw[a].get); del W_rw[a][weak]
        # head
        head.learn(cur, all_nodes)
        # edgebank
        pairs = [(cur[i], cur[j]) for i in range(len(cur)) for j in range(len(cur)) if i != j]
        eb_recent.append(pairs)
        for p in pairs:
            eb_count[p] += 1
        while len(eb_recent) > EDGEBANK_W:
            for p in eb_recent.popleft():
                eb_count[p] -= 1
                if eb_count[p] <= 0:
                    eb_count.pop(p, None)
        for c in cur:
            if c not in seen:
                seen.add(c); all_nodes.append(c)

    def mrr(a):
        return round(statistics.mean(recs[a]), 4) if recs[a] else 0.0
    return {a: mrr(a) for a in arms} | {"n_scored": len(recs["head"])}


def run_cell(N, scenes, seed):
    frames = SW.generate_stream(N, n_scenes=scenes, motion=2.0, seed=seed)
    r = run_probe(frames, seed)
    best_graph = max(r["additive"], r["rw"])
    return {
        "N": N, "scenes": scenes, "n_scored": r["n_scored"],
        "edgebank": r["edgebank"], "additive": r["additive"], "rw": r["rw"], "head": r["head"],
        "best_graph": round(best_graph, 4),
        "head_minus_graph": round(r["head"] - best_graph, 4),
        "head_vs_graph_pct": round(100 * (r["head"] - best_graph) / best_graph, 1) if best_graph else 0,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()
    if args.quick:
        grid = [(1000, 4), (4000, 8)]
    else:
        # N orders-of-magnitude, scenes ∝ N (frames/scene ~800, 실제처럼 다양성 동반)
        grid = [(N, max(4, N // 800)) for N in (1000, 4000, 16000, 48000, 100000)]

    print(f"=== HEAD-CROSSOVER PROBE — {len(grid)} cells (sampled-neg K={K_NEG}, cap={CAP}, dim={DIM}) ===")
    print(f"  {'N':>7}{'scenes':>7}{'scored':>8}  {'EB':>7}{'add':>7}{'rw':>7}{'head':>7}"
          f"  {'head-gph':>9}{'head-gph%':>10}")
    today = datetime.now().strftime("%Y%m%d")
    path = OUT / f"head_crossover_{today}.json"
    rows = []
    for (N, sc) in grid:
        r = run_cell(N, sc, SEED)
        rows.append(r)
        print(f"  {N:>7}{sc:>7}{r['n_scored']:>8}  {r['edgebank']:>7}{r['additive']:>7}"
              f"{r['rw']:>7}{r['head']:>7}  {r['head_minus_graph']:>9}{r['head_vs_graph_pct']:>9}%",
              flush=True)
        # 셀마다 증분 저장 (대규모 셀 timeout 시에도 완료분 보존)
        path.write_text(json.dumps({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "config": {"K_neg": K_NEG, "cap": CAP, "dim": DIM, "warmup": WARMUP,
                       "eval_frac": EVAL_FRAC, "note": "bounded-capacity: graph cap=48 vs head dim=48"},
            "cells": rows, "complete": False,
        }, indent=2, ensure_ascii=False), encoding="utf-8")

    print("\n=== Q2 판정: head가 그래프를 역전하는가 (N별) ===")
    crossover = None
    for r in rows:
        sign = "✅ 코어 우위" if r["head_minus_graph"] > 0 else "❌ 그래프 우위"
        print(f"  N={r['N']:<7} head-graph {r['head_minus_graph']:+.4f} ({r['head_vs_graph_pct']:+.1f}%)  {sign}")
        if r["head_minus_graph"] > 0 and crossover is None:
            crossover = r["N"]
    if crossover:
        print(f"\n  → 역전점 발견: N≈{crossover} 부터 학습 코어가 그래프 초과 = Phase 2 정당화 규모.")
    else:
        trend = [r["head_minus_graph"] for r in rows]
        improving = len(trend) >= 2 and trend[-1] > trend[0]
        print(f"\n  → 측정 범위(N≤{rows[-1]['N']})서 역전 없음. "
              f"격차 추세 {'축소(수렴 방향) → 더 큰 N서 역전 가능' if improving else '정체/확대 → 코어 근본 열위'}.")

    out = {"timestamp": datetime.now(timezone.utc).isoformat(),
           "config": {"K_neg": K_NEG, "cap": CAP, "dim": DIM, "warmup": WARMUP,
                      "eval_frac": EVAL_FRAC, "note": "bounded-capacity: graph cap=48 vs head dim=48"},
           "cells": rows, "crossover_N": crossover, "complete": True}
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n[out] {path}")


if __name__ == "__main__":
    main()
