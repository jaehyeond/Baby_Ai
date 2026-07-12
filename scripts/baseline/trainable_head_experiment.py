"""
Trainable Head Experiment — Phase 1→2 브릿지 (gap #1: 진짜 학습 코어)
==============================================================================
RESEARCH_SYNTHESIS_2026-07-12 §3 gap#1 / §6 action#3 참조.

왜 이게 중요한가 (북극성 정합)
------------------------------
지금까지의 규칙(additive, Rescorla-Wagner)은 그래프 스칼라를 손으로 갱신하는 것 —
파라미터가 loss 하에서 backprop되지 않는다. 북극성 정의의 자기학습 = **경험이 코어
파라미터를 바꿈**. 이 실험은 **학습가능한 링크예측 head**(Concept 임베딩 + 내적 scorer)를
경험 스트림에 **온라인 SGD**로 학습시켜, "예측 개선이 그래프 누적이 아니라 **가중치
그래디언트**에서 나오는가"를 prequential로 측정한다. = Phase 2(로컬 trainable 코어)의
축소판 리허설. 규모(≈500 concept)에서 과적합 위험(리서치 scale caveat) 직접 확인.

모델: 방향성 링크예측. score(a→b) = <E_out[a], E_in[b]>. co-activation (a,b) 양성,
음성샘플 음성. BCE(logit) 온라인 SGD (순수 numpy, torch 불필요).

평가: prequential_experiment 와 **동일 프로토콜**(예측→채점→학습, 동일 warmup·후보·filtered
rank). additive/RW/EdgeBank arm 과 같은 스트림에서 직접 비교.

Usage:
    python scripts/baseline/trainable_head_experiment.py
    python scripts/baseline/trainable_head_experiment.py --shuffle
출력: claudedocs/baseline/trainable_<tag>_<YYYYMMDD>.json
"""
from __future__ import annotations
import argparse, json, os, statistics, sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from dotenv import load_dotenv
from neo4j import GraphDatabase

sys.path.insert(0, os.path.dirname(__file__))
import prequential_experiment as PQ    # fetch_events, run_arm, rank_partner, 상수 재사용

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv(".env")
URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
AUTH = (os.getenv("NEO4J_USERNAME", "neo4j"), os.getenv("NEO4J_PASSWORD", ""))
DB = os.getenv("NEO4J_DATABASE", "neo4j")
OUT = Path(__file__).resolve().parents[2] / "claudedocs" / "baseline"

SEED = 42
DIM = 32
LR = 0.2
L2 = 1e-4
NEG_K = 8
SGD_STEPS = 3          # 이벤트당 SGD 스텝
INIT_SCALE = 0.1
WARMUP = PQ.WARMUP
WINDOW_BINS = PQ.WINDOW_BINS
HITS = PQ.HITS


def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-np.clip(x, -30, 30)))


class TrainableHead:
    """방향성 링크예측 head + 온라인 SGD (경험이 파라미터를 바꾼다)."""
    def __init__(self, dim, rng):
        self.dim = dim
        self.rng = rng
        self.Eout: dict[str, np.ndarray] = {}
        self.Ein: dict[str, np.ndarray] = {}

    def _vec(self, store, c):
        v = store.get(c)
        if v is None:
            v = (self.rng.standard_normal(self.dim) * INIT_SCALE).astype(np.float64)
            store[c] = v
        return v

    def scores_from(self, a, nodes):
        """a→n 점수 dict (랭킹용, 시그모이드 불필요=단조)."""
        ea = self.Eout.get(a)
        if ea is None:
            return {}
        out = {}
        for n in nodes:
            ein = self.Ein.get(n)
            if ein is not None:
                out[n] = float(ea @ ein)
        return out

    def learn(self, cids, all_nodes, steps=SGD_STEPS, neg_k=NEG_K):
        cset = set(cids)
        for _ in range(steps):
            for a in cids:
                pos = [b for b in cids if b != a]
                # 음성샘플
                negs = []
                if all_nodes:
                    for _i in range(neg_k):
                        n = all_nodes[self.rng.integers(len(all_nodes))]
                        if n not in cset and n != a:
                            negs.append(n)
                ea = self._vec(self.Eout, a)
                for b in pos:
                    self._step(a, b, 1.0)
                for b in negs:
                    self._step(a, b, 0.0)

    def _step(self, a, b, y):
        ea = self._vec(self.Eout, a)
        eb = self._vec(self.Ein, b)
        g = float(ea @ eb)
        d = sigmoid(g) - y                      # dL/dg (BCE-logit)
        ga = d * eb + L2 * ea
        gb = d * ea + L2 * eb
        ea -= LR * ga
        eb -= LR * gb


def run_head(events, rng_seed):
    rng = np.random.default_rng(rng_seed)
    head = TrainableHead(DIM, rng)
    seen_nodes = set()
    all_nodes = []
    n = len(events)
    bin_size = max(1, (n - WARMUP) // WINDOW_BINS)
    curve = defaultdict(lambda: [0.0, 0])
    recs = []
    by_key = {}

    for idx, (t, cids) in enumerate(events):
        known = [c for c in cids if c in seen_nodes]
        # PREDICT (학습 전)
        if idx >= WARMUP and known:
            for a in known:
                partners = [b for b in cids if b != a]
                if not partners:
                    continue
                scores = head.scores_from(a, seen_nodes)
                for b in partners:
                    others = set(partners) - {b}
                    candidates = [x for x in seen_nodes if x != a and x not in others]
                    if b not in seen_nodes or len(candidates) < 2:
                        continue
                    r = PQ.rank_partner(scores, b, candidates)
                    recip = 1.0 / r
                    recs.append((recip, r, len(candidates)))
                    by_key[(idx, a, b)] = recip
                    bi = min(WINDOW_BINS - 1, (idx - WARMUP) // bin_size)
                    curve[bi][0] += recip; curve[bi][1] += 1
        # TRAIN (온라인 SGD = 파라미터 갱신)
        head.learn(cids, all_nodes)
        for c in cids:
            if c not in seen_nodes:
                seen_nodes.add(c); all_nodes.append(c)

    m = len(recs) or 1
    mrr = sum(r[0] for r in recs) / m
    hit = {k: sum(1 for r in recs if r[1] <= k) / m for k in HITS}
    mean_rank = sum(r[1] for r in recs) / m
    avg_cand = sum(r[2] for r in recs) / m
    lift = ((avg_cand + 1) / 2) / mean_rank if mean_rank else 0.0
    curve_pts = [round(curve[b][0] / curve[b][1], 4) if curve[b][1] else None
                 for b in range(WINDOW_BINS)]
    valid = [(b, curve[b][0] / curve[b][1]) for b in range(WINDOW_BINS) if curve[b][1]]
    slope = None
    if len(valid) >= 4:
        half = len(valid) // 2
        slope = round(statistics.mean(v for _b, v in valid[half:])
                      - statistics.mean(v for _b, v in valid[:half]), 4)
    return {"arm": "trainable_head", "n_scored": m, "MRR": round(mrr, 4),
            "hit@1": round(hit[1], 4), "hit@5": round(hit[5], 4), "hit@10": round(hit[10], 4),
            "mean_rank": round(mean_rank, 1), "lift_vs_random": round(lift, 2),
            "prequential_curve": curve_pts, "curve_slope_late_minus_early": slope,
            "_by_key": by_key}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="phase1_head")
    ap.add_argument("--shuffle", action="store_true")
    args = ap.parse_args()

    with GraphDatabase.driver(URI, auth=AUTH, notifications_min_severity="OFF") as d:
        with d.session(database=DB) as s:
            events = PQ.fetch_events(s, exclude_frozen=True)
    if args.shuffle:
        import random
        rr = random.Random(SEED)
        cs = [c for _t, c in events]; rr.shuffle(cs)
        events = [(i, c) for i, c in enumerate(cs)]
    print(f"[head] events: {len(events)} | dim={DIM} lr={LR} neg_k={NEG_K} steps={SGD_STEPS}"
          f"{' [TIME-SHUFFLE]' if args.shuffle else ''}")

    # 참조 arm (동일 스트림)
    ref = {a: PQ.run_arm(events, a, SEED) for a in ["edgebank", "additive", "rw"]}
    # 학습 head 다중시드
    head_runs = [run_head(events, SEED + i) for i in range(4)]
    head = head_runs[0]
    head_mrrs = [h["MRR"] for h in head_runs]

    print(f"\n=== TRAINABLE HEAD vs 규칙 arm (prequential, 동일 스트림) ===")
    print(f"  {'arm':<16}{'MRR':>8}{'hit@1':>8}{'hit@10':>8}{'lift':>7}{'slope':>8}")
    for name, r in [("edgebank", ref["edgebank"]), ("additive", ref["additive"]),
                    ("rw", ref["rw"]), ("trainable_head", head)]:
        print(f"  {name:<16}{r['MRR']:>8}{r['hit@1']:>8}{r['hit@10']:>8}"
              f"{r['lift_vs_random']:>7}{str(r['curve_slope_late_minus_early']):>8}")
    print(f"\n  head 다중시드(4): MRR {round(statistics.mean(head_mrrs),4)} "
          f"± {round(statistics.pstdev(head_mrrs),4)} (min {round(min(head_mrrs),4)})")
    pt = PQ.paired_test(ref["additive"]["_by_key"], head["_by_key"])
    pt_rw = PQ.paired_test(ref["rw"]["_by_key"], head["_by_key"])
    print(f"  paired head vs additive: win/lose {pt['b_better']}/{pt['b_worse']} "
          f"p={pt.get('sign_p', pt.get('sign_z'))}")
    print(f"  paired head vs rw:       win/lose {pt_rw['b_better']}/{pt_rw['b_worse']} "
          f"p={pt_rw.get('sign_p', pt_rw.get('sign_z'))}")
    print(f"  head 곡선: {head['prequential_curve']}")

    hm = statistics.mean(head_mrrs)
    verdict = ("✅ 학습 head가 규칙 초과 (파라미터 학습이 이김)" if hm > ref["rw"]["MRR"]
               else "🟡 additive는 이기나 RW 미달" if hm > ref["additive"]["MRR"]
               else "❌ 규칙 미달 (518노드 과적합 = 리서치 scale caveat 확인)")
    print(f"\n  판정: {verdict}")
    print(f"  (해석: 규모 작을 땐 학습 head가 손튜닝 스칼라를 못 이길 수 있음 — 리서치 예측."
          f" 진짜 이득은 embodiment로 스트림 커진 뒤. 이건 Phase2 코어의 축소 리허설.)")

    out = {"tag": args.tag, "timestamp": datetime.now(timezone.utc).isoformat(),
           "n_events": len(events), "shuffle": args.shuffle,
           "config": {"dim": DIM, "lr": LR, "neg_k": NEG_K, "sgd_steps": SGD_STEPS, "l2": L2},
           "head": {k: v for k, v in head.items() if k != "_by_key"},
           "head_multiseed": {"mean": round(hm, 4), "std": round(statistics.pstdev(head_mrrs), 4),
                              "seeds": [round(x, 4) for x in head_mrrs]},
           "reference": {a: {k: v for k, v in ref[a].items() if k != "_by_key"} for a in ref},
           "paired_head_vs_additive": pt, "paired_head_vs_rw": pt_rw,
           "verdict_head_beats_rw": bool(hm > ref["rw"]["MRR"]),
           "verdict_head_beats_additive": bool(hm > ref["additive"]["MRR"])}
    OUT.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y%m%d")
    tag = args.tag + ("_shuffle" if args.shuffle else "")
    path = OUT / f"trainable_{tag}_{today}.json"
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n[out] {path}")


if __name__ == "__main__":
    main()
