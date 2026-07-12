"""
Prequential Self-Learning Experiment — Phase 1 정직한 리트머스 (test-then-train)
==============================================================================
program_roadmap_2026-07 / RESEARCH_SYNTHESIS_2026-07-12 §2 참조.

왜 이 하니스인가 (plasticity_experiment.py 의 교훈)
---------------------------------------------------
정적 랜덤분할 link-prediction 은 **빈도**를 보상한다(그래프 밀집화만으로 lift가 오른다).
그래서 가산 Hebbian(빈도 카운터)이 천장이었다. 프런티어 리서치의 진단:
  1) **규칙**: 빠진 조각은 STDP가 아니라 **Rescorla-Wagner 음성증거(negative evidence)** —
     a가 켜졌는데 후보 b가 **함께 안 켜지면** w_ab를 **깎는다** → w_ab → P(b|a)
     (빈도가 아니라 보정된 조건부확률). "틀릴 것"이 생겨야 예측오차가 존재.
  2) **측정**: 정적 분할이 아니라 **prequential(예측→채점→학습)**. 스트림을 시간순으로
     흐르며 각 경험을 **학습 전에 먼저 예측**하고, 그 예측오차 곡선이 내려가는지를 본다.
     memorization baseline = **EdgeBank**(최근 본 쌍 그대로 예측). 이걸 못 이기면
     "학습"이 아니라 재현 암기다.

측정 (동일 스트림·동일 채점, arm만 다름 = 규칙 귀속 통제)
--------------------------------------------------------
- Arm `edgebank` : 최근 W개 경험서 본 공동활성 쌍만 예측 (순수 암기 baseline).
- Arm `additive` : 현 프로덕션 규칙 (가산 Hebbian, cap 1.0) — "데이터만 자란다" null.
- Arm `rw`       : Rescorla-Wagner 음성증거 (w_ab → P(b|a)). **핵심 신규 메커니즘.**
- Arm `rw_recency`: RW + 최근우선(비정상성) 감쇠.
채점: 각 경험 학습 **전에** 각 known concept a에서 후보를 스코어링→참 파트너 b의
filtered rank → MRR/hit@k. 스트림 위치별 windowed MRR = 예측오차 곡선.
추가: **ECE(보정오차)** RW의 w_ab가 진짜 확률인지, **time-shuffle** 반증통제.

Usage:
    python scripts/baseline/prequential_experiment.py
    python scripts/baseline/prequential_experiment.py --shuffle   # 시간셔플 반증
출력: claudedocs/baseline/prequential_<tag>_<YYYYMMDD>.json
"""
from __future__ import annotations
import argparse, json, math, os, random, statistics, sys
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from neo4j import GraphDatabase

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv(".env")
URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
AUTH = (os.getenv("NEO4J_USERNAME", "neo4j"), os.getenv("NEO4J_PASSWORD", ""))
DB = os.getenv("NEO4J_DATABASE", "neo4j")
OUT = Path(__file__).resolve().parents[2] / "claudedocs" / "baseline"
OUT.mkdir(parents=True, exist_ok=True)

SEED = 42
HITS = (1, 5, 10)
WARMUP = 40          # 이 경험수 이전은 채점 제외 (콜드스타트 워밍업)
WINDOW_BINS = 12     # 예측오차 곡선 구간 수
EDGEBANK_W = 60      # EdgeBank 최근 윈도 (경험 수)
NEG_K = 12           # RW 음성샘플 수/쿼리
ETA_RW = 0.15        # RW 학습률
RECENCY = 0.01       # rw_recency 전역감쇠/경험


def fetch_events(session, exclude_frozen=True):
    where = "WHERE c.category <> 'frozen_knowledge'" if exclude_frozen else ""
    rows = session.run(
        f"MATCH (e:Experience)-[:INVOLVES]->(c:Concept) {where} "
        "WITH e, e.created_at AS ts, collect(DISTINCT c.id) AS cids "
        "WHERE size(cids) >= 2 AND ts IS NOT NULL "
        "RETURN ts, cids ORDER BY ts"
    ).data()
    events = []
    for r in rows:
        try:
            t = datetime.fromisoformat(r["ts"]).timestamp()
        except Exception:
            continue
        cids = [c for c in r["cids"] if c]
        if len(cids) >= 2:
            events.append((t, cids))
    events.sort(key=lambda x: x[0])
    return events


# ── 스코어러: 방향성 direct + 2-hop 확산 (가벼운 PPR 근사, 전 arm 공통) ─────────
def score_from(a, W):
    scores = defaultdict(float)
    row = W.get(a, {})
    for b, w in row.items():
        scores[b] += w
    for c, w_ac in row.items():
        for d, w_cd in W.get(c, {}).items():
            if d != a:
                scores[d] += 0.5 * w_ac * w_cd    # 2-hop 감쇠
    return scores


def rank_partner(scores, b, candidates):
    """b의 filtered rank (동점은 평균순위). candidates = 채점 후보 리스트."""
    sb = scores.get(b, 0.0)
    higher = sum(1 for n in candidates if scores.get(n, 0.0) > sb)
    equal = sum(1 for n in candidates if scores.get(n, 0.0) == sb)   # b 포함
    return higher + (equal + 1) / 2.0     # 평균순위(동점 보정)


# ── 학습 규칙 (arm별 update) ────────────────────────────────────────────────
def update_additive(W, cids, delta=0.05):
    for i in range(len(cids)):
        for j in range(i + 1, len(cids)):
            a, b = cids[i], cids[j]
            W[a][b] = min(1.0, W[a].get(b, 0.0) + delta)
            W[b][a] = min(1.0, W[b].get(a, 0.0) + delta)


def update_rw(W, cids, all_nodes, rng, eta=ETA_RW, neg_k=NEG_K):
    """Rescorla-Wagner 음성증거: w_ab += eta*(o_b - w_ab). o_b=1(공동활성)/0(음성샘플).
    → w_ab → P(b 공동활성 | a 활성). 방향성(a→b)."""
    cset = set(cids)
    for a in cids:
        # 양성: 같은 경험의 다른 concept
        for b in cids:
            if b == a:
                continue
            W[a][b] = W[a].get(b, 0.0) + eta * (1.0 - W[a].get(b, 0.0))
        # 음성: a의 현재 이웃 + 무작위 노드 중 이 경험에 없는 것
        cand = set(W.get(a, {}).keys())
        target = min(neg_k * 2, len(all_nodes))    # 가용 노드로 상한 (무한루프 방지)
        attempts = 0
        while len(cand) < target and attempts < target * 4:
            cand.add(rng.choice(all_nodes)); attempts += 1
        negs = [n for n in cand if n not in cset and n != a]
        rng.shuffle(negs)
        for b in negs[:neg_k]:
            W[a][b] = W[a].get(b, 0.0) + eta * (0.0 - W[a].get(b, 0.0))
            if W[a][b] < 1e-4:
                W[a].pop(b, None)      # 0 수렴 엣지 정리


def decay_all(W, rate):
    for a in W:
        for b in list(W[a].keys()):
            W[a][b] *= (1.0 - rate)


# ── EdgeBank: 최근 윈도서 본 쌍만 (암기 baseline) ───────────────────────────
class EdgeBank:
    def __init__(self, window):
        self.window = window
        self.buf = deque()               # (a,b) 최근 쌍
        self.count = defaultdict(int)
    def score_from(self, a):
        return {b: c for (x, b), c in self.count.items() if x == a and c > 0}
    def add(self, cids):
        pairs = []
        for i in range(len(cids)):
            for j in range(len(cids)):
                if i != j:
                    pairs.append((cids[i], cids[j]))
        self.buf.append(pairs)
        for p in pairs:
            self.count[p] += 1
        while len(self.buf) > self.window:
            old = self.buf.popleft()
            for p in old:
                self.count[p] -= 1
                if self.count[p] <= 0:
                    self.count.pop(p, None)


# ── prequential 실행 (한 arm) ───────────────────────────────────────────────
def run_arm(events, arm, rng_seed):
    rng = random.Random(rng_seed)
    W = defaultdict(dict)
    eb = EdgeBank(EDGEBANK_W) if arm == "edgebank" else None
    seen_nodes = set()
    all_nodes = []
    n = len(events)
    bin_size = max(1, (n - WARMUP) // WINDOW_BINS)
    curve = defaultdict(lambda: [0.0, 0])     # bin_idx -> [sum_recip, count]
    recs = []                                  # 전체 (recip, rank, cands)
    by_key = {}                                # (idx,a,b) -> recip (arm 간 paired)
    calib = []                                 # (pred_prob, actual) for ECE (rw만)

    for idx, (t, cids) in enumerate(events):
        known = [c for c in cids if c in seen_nodes]
        # ── PREDICT (학습 전) ──
        if idx >= WARMUP and len(known) >= 1:
            cand_universe = seen_nodes
            for a in known:
                partners = [b for b in cids if b != a]
                if not partners:
                    continue
                if arm == "edgebank":
                    scores = eb.score_from(a)
                else:
                    scores = score_from(a, W)
                for b in partners:
                    # filtered: a와 다른 참파트너 제외한 후보
                    others = set(partners) - {b}
                    candidates = [x for x in cand_universe if x != a and x not in others]
                    if b not in seen_nodes or len(candidates) < 2:
                        continue
                    r = rank_partner(scores, b, candidates)
                    recip = 1.0 / r
                    recs.append((recip, r, len(candidates)))
                    by_key[(idx, a, b)] = recip           # arm 간 paired 비교용
                    bi = min(WINDOW_BINS - 1, (idx - WARMUP) // bin_size)
                    curve[bi][0] += recip; curve[bi][1] += 1
                # ECE 표본 (rw 계열): a의 상위 후보들의 예측확률 vs 실제
                if arm.startswith("rw") and W.get(a):
                    cset = set(cids)
                    top = sorted(W[a].items(), key=lambda kv: -kv[1])[:NEG_K]
                    for b, wab in top:
                        calib.append((min(1.0, wab), 1.0 if b in cset else 0.0))
        # ── TRAIN (학습) ──
        if arm == "edgebank":
            eb.add(cids)
        elif arm == "additive":
            update_additive(W, cids)
        elif arm == "rw":
            update_rw(W, cids, all_nodes, rng)
        elif arm == "rw_recency":
            if all_nodes:
                decay_all(W, RECENCY)
            update_rw(W, cids, all_nodes, rng)
        for c in cids:
            if c not in seen_nodes:
                seen_nodes.add(c); all_nodes.append(c)

    # 집계
    m = len(recs) or 1
    mrr = sum(r[0] for r in recs) / m
    hit = {k: sum(1 for r in recs if r[1] <= k) / m for k in HITS}
    mean_rank = sum(r[1] for r in recs) / m
    avg_cand = sum(r[2] for r in recs) / m
    lift = ((avg_cand + 1) / 2) / mean_rank if mean_rank else 0.0
    curve_pts = [round(curve[b][0] / curve[b][1], 4) if curve[b][1] else None
                 for b in range(WINDOW_BINS)]
    # 곡선 기울기 (전반부 vs 후반부 MRR)
    valid = [(b, curve[b][0] / curve[b][1]) for b in range(WINDOW_BINS) if curve[b][1]]
    slope = None
    if len(valid) >= 4:
        half = len(valid) // 2
        early = statistics.mean(v for _b, v in valid[:half])
        late = statistics.mean(v for _b, v in valid[half:])
        slope = round(late - early, 4)
    ece = None
    if calib:
        bins = defaultdict(lambda: [0.0, 0.0, 0])
        for pr, ac in calib:
            bi = min(9, int(pr * 10))
            bins[bi][0] += pr; bins[bi][1] += ac; bins[bi][2] += 1
        tot = len(calib)
        ece = round(sum(b[2] / tot * abs(b[0] / b[2] - b[1] / b[2]) for b in bins.values() if b[2]), 4)
    return {
        "arm": arm, "n_scored": m, "MRR": round(mrr, 4),
        "hit@1": round(hit[1], 4), "hit@5": round(hit[5], 4), "hit@10": round(hit[10], 4),
        "mean_rank": round(mean_rank, 1), "avg_candidates": round(avg_cand, 0),
        "lift_vs_random": round(lift, 2), "prequential_curve": curve_pts,
        "curve_slope_late_minus_early": slope, "ECE": ece,
        "_by_key": by_key,
    }


def paired_test(a_keyed, b_keyed):
    """동일 (idx,a,b) 쿼리에서 b_arm 이 a_arm 보다 recip 높은가 (부호검정)."""
    common = [k for k in a_keyed if k in b_keyed]
    wins = sum(1 for k in common if b_keyed[k] > a_keyed[k] + 1e-9)
    losses = sum(1 for k in common if b_keyed[k] < a_keyed[k] - 1e-9)
    dec = wins + losses
    out = {"n": len(common), "b_better": wins, "b_worse": losses, "ties": len(common) - dec}
    if dec > 0:
        try:
            from scipy.stats import binomtest
            out["sign_p"] = round(binomtest(wins, dec, 0.5).pvalue, 5)
        except Exception:
            out["sign_z"] = round((wins - dec / 2) / (math.sqrt(dec) / 2), 2)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="phase1_prequential")
    ap.add_argument("--shuffle", action="store_true", help="time-shuffle 반증통제")
    args = ap.parse_args()

    with GraphDatabase.driver(URI, auth=AUTH, notifications_min_severity="OFF") as d:
        with d.session(database=DB) as s:
            events = fetch_events(s, exclude_frozen=True)
    print(f"[preq] events: {len(events)} (chronological, ≥2 concept) | warmup={WARMUP} bins={WINDOW_BINS}")

    if args.shuffle:
        rng = random.Random(SEED)
        csets = [c for _t, c in events]
        rng.shuffle(csets)
        events = [(i, cs) for i, cs in enumerate(csets)]   # 타임스탬프 무의미화
        print("[preq] TIME-SHUFFLE 반증통제 활성 (순서 무작위화)\n")

    arms = ["edgebank", "additive", "rw", "rw_recency"]
    results = {a: run_arm(events, a, SEED) for a in arms}

    eb_mrr = results["edgebank"]["MRR"] or 1e-9
    print(f"=== PREQUENTIAL (test-then-train) — 동일 스트림, arm만 다름 ===")
    print(f"  {'arm':<12}{'MRR':>8}{'hit@1':>8}{'hit@10':>8}{'lift':>7}{'slope':>8}{'ECE':>7}{'vsEdgeBank':>12}")
    for a in arms:
        r = results[a]
        vseb = round(r["MRR"] / eb_mrr, 2)
        print(f"  {a:<12}{r['MRR']:>8}{r['hit@1']:>8}{r['hit@10']:>8}{r['lift_vs_random']:>7}"
              f"{str(r['curve_slope_late_minus_early']):>8}{str(r['ECE']):>7}{vseb:>12}")

    rw, add, eb = results["rw"], results["additive"], results["edgebank"]
    print(f"\n  예측오차 곡선 (windowed MRR, 스트림 진행순):")
    for a in ["additive", "rw"]:
        print(f"    {a:<11} {results[a]['prequential_curve']}")

    # ── paired 유의성 (동일 쿼리에서 arm 대결) ──
    pt_rw_add = paired_test(add["_by_key"], rw["_by_key"])
    pt_rw_eb = paired_test(eb["_by_key"], rw["_by_key"])
    pt_add_eb = paired_test(eb["_by_key"], add["_by_key"])
    print(f"\n  paired 부호검정 (동일 쿼리):")
    print(f"    RW  vs additive: win/lose {pt_rw_add['b_better']}/{pt_rw_add['b_worse']} "
          f"p={pt_rw_add.get('sign_p', pt_rw_add.get('sign_z'))}")
    print(f"    RW  vs EdgeBank: win/lose {pt_rw_eb['b_better']}/{pt_rw_eb['b_worse']} "
          f"p={pt_rw_eb.get('sign_p', pt_rw_eb.get('sign_z'))}")
    print(f"    add vs EdgeBank: win/lose {pt_add_eb['b_better']}/{pt_add_eb['b_worse']} "
          f"p={pt_add_eb.get('sign_p', pt_add_eb.get('sign_z'))}")

    # ── RW 다중시드 강건성 (음성샘플 확률성 통제) ──
    seed_mrrs = []
    for sd in range(SEED, SEED + 6):
        r = run_arm(events, "rw", sd)
        seed_mrrs.append(r["MRR"])
    rw_mean = round(statistics.mean(seed_mrrs), 4)
    rw_std = round(statistics.pstdev(seed_mrrs), 4)
    add_mrr = add["MRR"]
    robust = (rw_mean - rw_std) > add_mrr    # 최악 시드도 additive 초과?
    print(f"\n  RW 다중시드(6): MRR {rw_mean} ± {rw_std} (min {round(min(seed_mrrs),4)}) "
          f"vs additive {add_mrr} → {'✅ 강건하게 우세' if robust else '🟡 시드편차 내'}")

    beats_eb = bool(rw_mean > eb["MRR"] and pt_rw_eb.get("sign_p", 1) < 0.05)
    beats_add = bool(rw_mean > add_mrr and pt_rw_add.get("sign_p", 1) < 0.05)
    up = bool((rw["curve_slope_late_minus_early"] or 0) > 0)
    robust = bool(robust)
    print(f"\n  판정: RW vs EdgeBank(암기) {'✅ 유의하게 이김' if beats_eb else '🟡/❌'}"
          f" | RW vs additive(빈도) {'✅ 유의하게 이김' if beats_add else '🟡 약함'}"
          f" | 곡선 상승(예측오차↓) {'✅' if up else '❌'}"
          f" | RW 보정 ECE={rw['ECE']}(additive는 확률아님)")

    out = {"tag": args.tag, "timestamp": datetime.now(timezone.utc).isoformat(),
           "n_events": len(events), "shuffle": args.shuffle,
           "config": {"warmup": WARMUP, "edgebank_window": EDGEBANK_W,
                      "neg_k": NEG_K, "eta_rw": ETA_RW, "recency": RECENCY},
           "results": {a: {k: v for k, v in results[a].items() if k != "_by_key"} for a in arms},
           "paired": {"rw_vs_additive": pt_rw_add, "rw_vs_edgebank": pt_rw_eb,
                      "additive_vs_edgebank": pt_add_eb},
           "rw_multiseed": {"mean": rw_mean, "std": rw_std, "min": round(min(seed_mrrs), 4),
                            "seeds": [round(x, 4) for x in seed_mrrs], "robust_over_additive": robust},
           "verdict": {"rw_beats_edgebank": beats_eb, "rw_beats_additive": beats_add,
                       "rw_curve_rising": up}}
    today = datetime.now().strftime("%Y%m%d")
    tag = args.tag + ("_shuffle" if args.shuffle else "")
    path = OUT / f"prequential_{tag}_{today}.json"
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n[out] {path}")


if __name__ == "__main__":
    main()
