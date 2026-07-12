"""
Plasticity Rule Experiment — Phase 1 자기학습 리트머스 (controlled before/after)
==============================================================================
program_roadmap_2026-07 / self_learning_architecture_2026-07 참조.

목적
----
"co-occurrence 가산 Hebbian" → "진짜 가소성 규칙(STDP 타이밍 + 지수감쇠/적격흔적 +
항상성 정규화 + 예측오차 게이팅)" 으로 바꿨을 때, 그래프가 **미래 공동활성화를
더 잘 예측하는가** = 예측오차가 내려가는가를 측정한다.

핵심 = 통제 (roadmap 경고: "데이터 변화 ≠ 규칙 변화")
-------------------------------------------------------
동일한 경험 스트림(Experience.created_at + INVOLVES→Concept)을 **시간순으로 분할**
(과거 train / 미래 test) 한 뒤, **같은 train 이벤트**로 두 규칙이 각각 그래프를
구성한다. 입력(데이터)은 완전히 동일하고 **오직 학습 규칙만 다르다.** 따라서
lift_new > lift_old 이면 그 차이는 순수하게 규칙의 예측력 향상이다.

평가 (inductive temporal link-prediction)
-----------------------------------------
test 이벤트 안에서 함께 활성화된 concept 쌍 중 train 그래프에서 아직 이웃이 아닌
쌍을 held-out 타깃으로 삼는다. seed a 에서 (방향성) Personalized PageRank 확산 →
b 가 몇 위로 예측되는가 → MRR, hit@k, mean_rank, lift_vs_random.
타깃 집합은 두 규칙에서 **동일**(train/test 분할이 같으므로) → 공정 비교.

Usage:
    python scripts/baseline/plasticity_experiment.py
    python scripts/baseline/plasticity_experiment.py --sweep          # 파라미터 탐색
    python scripts/baseline/plasticity_experiment.py --tag phase1_v1
출력: claudedocs/baseline/plasticity_<tag>_<YYYYMMDD>.json
"""
from __future__ import annotations
import argparse
import json
import math
import os
import random
import statistics
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import networkx as nx
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
TRAIN_FRACTION = 0.8      # 시간순 앞 80% = train(과거), 뒤 20% = test(미래)
MAX_TEST_PAIRS = 300      # held-out 타깃 최대 (속도)
PPR_ALPHA = 0.85
HITS = (1, 5, 10)

# ── 가소성 규칙 기본 하이퍼파라미터 (STDP 표준 + 스트림 스케일 적응) ─────────
# 타이밍은 생물학의 ms 대신 이 스트림의 실제 시간 스케일(시간~일)로 tau 설정.
DEFAULTS = dict(
    a_co=0.06,        # 동시발화(Δt≈0) LTP 진폭
    a_plus=0.06,      # 순방향 STDP LTP 진폭 (pre→post, 인과)
    a_minus=0.03,     # 역방향 STDP LTD 진폭 (post→pre, 억제) — 항상성 역할
    tau_hours=12.0,   # 적격흔적 지수감쇠 시상수 (같은 세션/날 강결합, 주 단위 무시)
    w_sat=1.0,        # 예측오차 게이팅 포화점 (soft cap): surprise=1-min(1,w/w_sat)
    elig_eps=0.02,    # 이보다 작은 적격흔적은 무시 (window 컷)
    homeo_target=4.0, # 항상성: 노드별 out-strength 목표 (초과 시 divisive scaling)
    old_delta=0.05,   # 구 규칙(가산) delta — 프로덕션 hebbian_update와 동일
)


# ============================================================================
#  데이터 로딩: 시간순 공동활성화 이벤트 스트림
# ============================================================================
def fetch_events(session, exclude_frozen: bool = True) -> list[tuple[float, list[str]]]:
    """각 Experience → (epoch_seconds, [concept_id...]) . ≥2 concept 만 유효."""
    where = "WHERE c.category <> 'frozen_knowledge'" if exclude_frozen else ""
    rows = session.run(
        f"MATCH (e:Experience)-[:INVOLVES]->(c:Concept) {where} "
        "WITH e, e.created_at AS ts, collect(DISTINCT c.id) AS cids "
        "WHERE size(cids) >= 2 AND ts IS NOT NULL "
        "RETURN ts, cids ORDER BY ts"
    ).data()
    events: list[tuple[float, list[str]]] = []
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


def temporal_split(events, frac=TRAIN_FRACTION):
    n_train = int(len(events) * frac)
    return events[:n_train], events[n_train:]


# ============================================================================
#  규칙 A — 구 가산 co-occurrence Hebbian (프로덕션 hebbian_update 미러, 대칭)
# ============================================================================
def build_old(train_events, p) -> dict:
    W: dict = defaultdict(lambda: defaultdict(float))
    d = p["old_delta"]
    for _t, cids in train_events:
        for i in range(len(cids)):
            for j in range(i + 1, len(cids)):
                a, b = cids[i], cids[j]
                W[a][b] = min(1.0, W[a][b] + d)
                W[b][a] = min(1.0, W[b][a] + d)
    return W


# ============================================================================
#  규칙 B — 가소성: STDP 타이밍 + 적격흔적 지수감쇠 + PE 게이팅 + 항상성 정규화
# ============================================================================
def build_new(train_events, p) -> dict:
    """가소성 규칙 (ablation 가능). 각 메커니즘을 스위치로 분리해 기여를 통제한다.

    메커니즘 (p 플래그):
      pe_gate   : 예측오차 게이팅 (이미 예측되는 링크는 작게 갱신). 끄면 빈도신호 보존.
      recency   : 각 이벤트마다 기존 전체 가중치를 (1-recency) 배 — 최근 공동활성화가
                  과거보다 예측력 크다는 비정상(non-stationary) 가정. 미래예측 핵심 후보.
      stdp      : 교차이벤트 방향성 STDP (a 먼저 → a→b LTP, 적격흔적 exp 감쇠).
      ltd       : STDP 역방향 억제 (b→a LTD).
      homeo_target : 노드별 out-strength 상한 divisive scaling (999=off).
    """
    W: dict = defaultdict(lambda: defaultdict(float))
    last_fire: dict[str, float] = {}
    tau = p["tau_hours"] * 3600.0
    a_co, a_plus, a_minus = p["a_co"], p["a_plus"], p["a_minus"]
    w_sat, eps = p["w_sat"], p["elig_eps"]
    pe_gate = p.get("pe_gate", True)
    use_stdp = p.get("stdp", True)
    use_ltd = p.get("ltd", True)
    recency = p.get("recency", 0.0)

    def gate(a, b):
        return (1.0 - min(1.0, W[a][b] / w_sat)) if pe_gate else 1.0

    for t, cids in train_events:
        cset = set(cids)
        # 0) recency: 스트림 비정상성 — 과거 가중치 지수감쇠 (최근 우선)
        if recency > 0.0:
            keep = 1.0 - recency
            for a in W:
                for b in W[a]:
                    W[a][b] *= keep
        # 1) 동시발화 대칭 LTP (선택적 PE 게이팅)
        for i in range(len(cids)):
            for j in range(i + 1, len(cids)):
                a, b = cids[i], cids[j]
                W[a][b] += a_co * gate(a, b)
                W[b][a] += a_co * gate(b, a)
        # 2) 교차이벤트 방향성 STDP
        if use_stdp:
            for b in cids:
                for a, ta in last_fire.items():
                    if a in cset:
                        continue
                    dt = t - ta
                    if dt <= 0:
                        continue
                    elig = math.exp(-dt / tau)
                    if elig < eps:
                        continue
                    W[a][b] += a_plus * elig * gate(a, b)     # a 먼저(인과) → LTP
                    if use_ltd:
                        W[b][a] = max(0.0, W[b][a] - a_minus * elig)  # 역방향 LTD
        # 3) 발화시각 갱신
        for c in cids:
            last_fire[c] = t

    # 4) 항상성 시냅스 스케일링 (노드별 out-strength 상한)
    target = p["homeo_target"]
    if target < 900:
        for a in list(W.keys()):
            s = sum(W[a].values())
            if s > target and s > 0:
                scale = target / s
                for b in W[a]:
                    W[a][b] *= scale
    return W


# 통제된 ablation 변이 (모두 동일 CV·동일 fold 로 OLD 대비 검정)
VARIANTS = {
    # 전체 규칙 (원 설계)
    "stdp_full":     dict(pe_gate=True,  stdp=True,  ltd=True,  recency=0.0,  homeo_target=4.0),
    # PE 게이팅만 제거 (빈도신호 보존 가설)
    "no_pe":         dict(pe_gate=False, stdp=True,  ltd=True,  recency=0.0,  homeo_target=4.0),
    # 항상성만 제거 (허브 보존 가설)
    "no_homeo":      dict(pe_gate=True,  stdp=True,  ltd=True,  recency=0.0,  homeo_target=999.0),
    # PE·항상성·LTD 모두 제거 = 순수 빈도 + 방향성 STDP
    "stdp_freq":     dict(pe_gate=False, stdp=True,  ltd=False, recency=0.0,  homeo_target=999.0),
    # 순수 recency (비정상성) — STDP 없음, 최근 공동활성화 우선
    "recency_only":  dict(pe_gate=False, stdp=False, ltd=False, recency=0.03, homeo_target=999.0),
    # recency + 방향성 STDP (빈도+최근+타이밍, 게이팅/플래튼 없음) — 유력 후보
    "recency_stdp":  dict(pe_gate=False, stdp=True,  ltd=False, recency=0.03, homeo_target=999.0),
    # 순수 무제한 빈도 (OLD 의 1.0 cap 제거) — 빈도해상도 가설
    "freq_nocap":    dict(pe_gate=False, stdp=False, ltd=False, recency=0.0,  homeo_target=999.0),
    # 무제한 빈도 + 약한 recency (미세 비정상성)
    "freq_recency1": dict(pe_gate=False, stdp=False, ltd=False, recency=0.01, homeo_target=999.0),
    # 무제한 빈도 + 매우약한 recency
    "freq_recency05":dict(pe_gate=False, stdp=False, ltd=False, recency=0.005, homeo_target=999.0),
}


# ============================================================================
#  평가: 방향성 PPR 로 held-out 공동활성화 예측
# ============================================================================
def to_digraph(W: dict) -> nx.DiGraph:
    g = nx.DiGraph()
    for a, nbrs in W.items():
        for b, w in nbrs.items():
            if w > 0:
                g.add_edge(a, b, weight=w)
    return g


def build_test_pairs(train_events, test_events, W_train, rng) -> list[tuple[str, str]]:
    """test 이벤트의 공동활성화 쌍 중 train 그래프에서 아직 이웃이 아닌 쌍만.
    두 규칙에 **동일** 타깃을 쓰기 위해 train 노드집합 + '엣지 존재' 기준은
    구 규칙 그래프(W_old)로 고정한다(가장 보수적: 새 규칙이 만든 엣지로 타깃을
    제거하면 유리해지므로, 구 규칙 이웃 기준으로 held-out 판정)."""
    train_nodes = set(W_train.keys())
    for a in W_train:
        train_nodes.update(W_train[a].keys())
    def is_neighbor(a, b):
        return b in W_train.get(a, {}) or a in W_train.get(b, {})
    seen = set()
    pairs = []
    for _t, cids in test_events:
        for i in range(len(cids)):
            for j in range(i + 1, len(cids)):
                a, b = cids[i], cids[j]
                if a == b or a not in train_nodes or b not in train_nodes:
                    continue
                if is_neighbor(a, b):
                    continue  # train 에서 이미 직접 연결 = held-out 아님
                key = (min(a, b), max(a, b))
                if key in seen:
                    continue
                seen.add(key)
                pairs.append((a, b))
    rng.shuffle(pairs)
    return pairs[:MAX_TEST_PAIRS]


def _ppr(g: nx.DiGraph, src: str, cache: dict) -> dict:
    if src not in cache:
        if src not in g:
            cache[src] = {}
        else:
            try:
                cache[src] = nx.pagerank(g, alpha=PPR_ALPHA,
                                         personalization={src: 1.0}, weight="weight",
                                         max_iter=200, tol=1e-6)
            except nx.PowerIterationFailedConvergence:
                cache[src] = {}
    return cache[src]


def evaluate_joint(W_old, W_new, test_pairs, train_nodes) -> tuple[list, list]:
    """두 규칙을 **동일 후보집합**으로 채점 (공정한 paired 비교의 핵심).

    후보집합·제외집합은 OLD 참조그래프의 이웃으로 고정한다. held-out 쌍은 정의상
    OLD 에서 a-b 비이웃이므로 b 는 항상 후보에 포함된다. NEW 가 교차이벤트 STDP 로
    a→b 직접엣지를 학습했으면 그건 정당한 예측 → 후보 안에서 rank 1 로 반영된다
    (기존 방식처럼 '직접이웃이라 skip' 하지 않는다 = NEW 의 학습을 벌하지 않음)."""
    g_old, g_new = to_digraph(W_old), to_digraph(W_new)
    nodes = list(train_nodes)
    old_recs, new_recs = [], []
    co, cn = {}, {}
    def old_nbrs(x):
        return set(g_old.successors(x)) | set(g_old.predecessors(x)) if x in g_old else set()
    for (a, b) in test_pairs:
        if a not in train_nodes or b not in train_nodes:
            continue
        ro_rank, rn_rank, cc = [], [], []
        for src, dst in ((a, b), (b, a)):
            exclude = old_nbrs(src) | {src}          # OLD 기준 고정 (양 규칙 공통)
            cands = [n for n in nodes if n not in exclude]
            if dst not in cands:
                continue
            po, pn = _ppr(g_old, src, co), _ppr(g_new, src, cn)
            ranked_o = sorted(cands, key=lambda n: po.get(n, 0.0), reverse=True)
            ranked_n = sorted(cands, key=lambda n: pn.get(n, 0.0), reverse=True)
            ro_rank.append(ranked_o.index(dst) + 1)
            rn_rank.append(ranked_n.index(dst) + 1)
            cc.append(len(cands))
        if not cc:
            continue
        key = (min(a, b), max(a, b))
        mc = statistics.mean(cc)
        old_recs.append({"pair": key, "rank": statistics.mean(ro_rank),
                         "recip": statistics.mean(1.0 / r for r in ro_rank), "cands": mc})
        new_recs.append({"pair": key, "rank": statistics.mean(rn_rank),
                         "recip": statistics.mean(1.0 / r for r in rn_rank), "cands": mc})
    return old_recs, new_recs


def summarize(records: list[dict]) -> dict:
    if not records:
        return {"n": 0, "MRR": 0, "hit@1": 0, "hit@5": 0, "hit@10": 0,
                "mean_rank": 0, "median_rank": 0, "avg_candidates": 0,
                "random_expected_rank": 0, "lift_vs_random": 0}
    ranks = [r["rank"] for r in records]
    recip = [r["recip"] for r in records]
    cc = [r["cands"] for r in records]
    m = len(records)
    hitk = {k: sum(1 for r in ranks if r <= k) / m for k in HITS}
    mean_rank = statistics.mean(ranks)
    rand_rank = (statistics.mean(cc) + 1) / 2
    return {
        "n": m,
        "MRR": round(statistics.mean(recip), 4),
        "hit@1": round(hitk[1], 4),
        "hit@5": round(hitk[5], 4),
        "hit@10": round(hitk[10], 4),
        "mean_rank": round(mean_rank, 1),
        "median_rank": round(statistics.median(ranks), 1),
        "avg_candidates": round(statistics.mean(cc), 0),
        "random_expected_rank": round(rand_rank, 1),
        "lift_vs_random": round(rand_rank / mean_rank, 2) if mean_rank else 0.0,
    }


def paired_stats(old_recs: list[dict], new_recs: list[dict]) -> dict:
    """동일 fold·동일 쌍 기준 paired 비교 (규칙만 다르므로 pairing 유효)."""
    om = {r["pair"]: r["rank"] for r in old_recs}
    nm = {r["pair"]: r["rank"] for r in new_recs}
    common = [k for k in om if k in nm]
    wins = sum(1 for k in common if nm[k] < om[k])   # new 가 더 낮은 rank(=더 좋음)
    losses = sum(1 for k in common if nm[k] > om[k])
    ties = len(common) - wins - losses
    out = {"n_paired": len(common), "new_better": wins, "new_worse": losses, "ties": ties}
    # 부호검정 (binomial, ties 제외) + 가능하면 Wilcoxon
    dec = wins + losses
    if dec > 0:
        try:
            from scipy.stats import binomtest, wilcoxon
            out["sign_test_p"] = round(binomtest(wins, dec, 0.5).pvalue, 4)
            diffs = [om[k] - nm[k] for k in common if om[k] != nm[k]]
            if len(diffs) >= 6:
                out["wilcoxon_p"] = round(wilcoxon(diffs).pvalue, 4)
        except Exception:
            # scipy 없으면 정규근사 부호검정
            import math as _m
            z = (wins - dec / 2) / (_m.sqrt(dec) / 2)
            out["sign_test_z"] = round(z, 2)
    return out


# ============================================================================
#  실행 — 반복 랜덤분할 교차검증 (통계적 검정력 확보; 타임스탬프는 train 내 보존)
# ============================================================================
def run_cv(events, params, k_folds: int, base_seed: int, frac=TRAIN_FRACTION):
    """K fold 랜덤분할. 각 fold: 동일 이벤트분할로 old/new 그래프 구성 → 동일 held-out
    쌍 평가 → fold 간 raw 랭크 pooling. 규칙만 변수(입력 이벤트 동일)."""
    old_all, new_all = [], []
    fold_deltas = []
    for f in range(k_folds):
        rng = random.Random(base_seed + f)
        ev = events[:]; rng.shuffle(ev)
        n = int(len(ev) * frac)
        tr, te = ev[:n], ev[n:]
        tr = sorted(tr, key=lambda x: x[0])   # STDP: train 내부는 실제 시간순
        W_old = build_old(tr, params)
        W_new = build_new(tr, params)
        train_nodes = set(W_old.keys())
        for a in W_old: train_nodes.update(W_old[a].keys())
        pairs = build_test_pairs(tr, te, W_old, rng)   # 타깃은 old 이웃기준 고정(공정)
        if not pairs:
            continue
        ro, rn = evaluate_joint(W_old, W_new, pairs, train_nodes)
        # fold 태깅 (pair 중복 pooling 시 fold 구분)
        for r in ro: r["pair"] = (f,) + r["pair"]
        for r in rn: r["pair"] = (f,) + r["pair"]
        old_all += ro; new_all += rn
        so, sn = summarize(ro), summarize(rn)
        if so["lift_vs_random"] and sn["lift_vs_random"]:
            fold_deltas.append(sn["lift_vs_random"] - so["lift_vs_random"])
    old_s, new_s = summarize(old_all), summarize(new_all)
    return {
        "k_folds": k_folds, "n_pooled_pairs": old_s["n"],
        "old_rule": old_s, "new_rule": new_s,
        "lift_old": old_s["lift_vs_random"], "lift_new": new_s["lift_vs_random"],
        "delta_lift": round(new_s["lift_vs_random"] - old_s["lift_vs_random"], 2),
        "delta_mrr": round(new_s["MRR"] - old_s["MRR"], 4),
        "fold_delta_lift_mean": round(statistics.mean(fold_deltas), 3) if fold_deltas else 0.0,
        "fold_delta_lift_std": round(statistics.pstdev(fold_deltas), 3) if len(fold_deltas) > 1 else 0.0,
        "paired": paired_stats(old_all, new_all),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="phase1")
    ap.add_argument("--folds", type=int, default=15, help="랜덤분할 교차검증 fold 수")
    ap.add_argument("--sweep", action="store_true", help="tau/A+/homeostasis 파라미터 탐색")
    ap.add_argument("--variants", action="store_true", help="메커니즘 ablation 변이 통제 비교")
    args = ap.parse_args()

    with GraphDatabase.driver(URI, auth=AUTH, notifications_min_severity="OFF") as d:
        with d.session(database=DB) as s:
            events = fetch_events(s, exclude_frozen=True)
    n_concepts = len({c for _t, cs in events for c in cs})
    from collections import Counter
    cc = Counter(c for _t, cs in events for c in set(cs))
    recurring = sum(1 for v in cc.values() if v >= 2)
    print(f"[plast] events: {len(events)} (≥2 concept) | distinct concepts: {n_concepts} "
          f"| recurring(≥2 events): {recurring}")

    # 정직성 체크: 시간순 미래분할은 콜드스타트 지배 → 측정불가 여부 리포트
    tr, te = temporal_split(events)
    W_tmp = build_old(tr, DEFAULTS)
    tn = set(W_tmp.keys())
    for a in W_tmp: tn.update(W_tmp[a].keys())
    temp_both = sum(1 for _t, cs in te for i in range(len(cs)) for j in range(i + 1, len(cs))
                    if cs[i] in tn and cs[j] in tn and cs[i] != cs[j])
    print(f"[plast] temporal past-{TRAIN_FRACTION:.0%}/future: 평가가능 쌍 {temp_both} "
          f"(콜드스타트 지배 → CV로 검정력 확보)\n")

    print(f"=== PLASTICITY EXPERIMENT — {args.folds}-fold 랜덤분할 CV ===")
    base = run_cv(events, DEFAULTS, args.folds, SEED)
    print(f"  pooled held-out pairs: {base['n_pooled_pairs']}  (paired {base['paired']['n_paired']})")
    print(f"  {'metric':<16}{'OLD(가산)':>13}{'NEW(가소성)':>15}{'Δ':>10}")
    for k in ["lift_vs_random", "MRR", "hit@1", "hit@5", "hit@10", "mean_rank"]:
        o, n = base["old_rule"][k], base["new_rule"][k]
        print(f"  {k:<16}{o:>13}{n:>15}{round(n - o, 4):>10}")
    p = base["paired"]
    print(f"\n  paired: new_better={p['new_better']} new_worse={p['new_worse']} ties={p['ties']}"
          f"  sign_p={p.get('sign_test_p', p.get('sign_test_z', 'n/a'))}"
          f"  wilcoxon_p={p.get('wilcoxon_p', 'n/a')}")
    print(f"  fold Δlift: mean={base['fold_delta_lift_mean']} ± {base['fold_delta_lift_std']}")
    sig = p.get("sign_test_p", 1.0)
    verdict = ("✅ 자기학습 신호 (규칙만 바꿔 held-out 예측력↑, 통계적 유의)"
               if base["delta_lift"] > 0 and isinstance(sig, float) and sig < 0.05
               else "🟡 개선 방향이나 유의성 약함" if base["delta_lift"] > 0
               else "❌ 개선 없음/반증 — 규칙 재설계 필요")
    print(f"\n  판정: lift {base['lift_old']} → {base['lift_new']} (Δ{base['delta_lift']:+})  {verdict}")

    out = {
        "tag": args.tag, "timestamp": datetime.now(timezone.utc).isoformat(),
        "n_events": len(events), "n_concepts": n_concepts, "recurring_concepts": recurring,
        "temporal_split_evaluable_pairs": temp_both,
        "predictor": "directed Personalized PageRank (양방향 평균)",
        "eval": f"{args.folds}-fold repeated random-split CV, held-out co-activation pairs",
        "seed": SEED, "default_params": DEFAULTS, "result": base,
    }

    if args.variants:
        print("\n=== 메커니즘 ABLATION (동일 CV·fold, 각 변이 vs OLD) ===")
        print(f"  OLD(가산) baseline lift={base['lift_old']} MRR={base['old_rule']['MRR']}\n")
        vrows = []
        for name, flags in VARIANTS.items():
            vp = dict(DEFAULTS, **flags)
            r = run_cv(events, vp, args.folds, SEED)
            p2 = r["paired"]
            vrows.append({"variant": name, "flags": flags,
                          "lift_new": r["lift_new"], "mrr_new": r["new_rule"]["MRR"],
                          "hit@10": r["new_rule"]["hit@10"], "delta_lift": r["delta_lift"],
                          "new_better": p2["new_better"], "new_worse": p2["new_worse"],
                          "sign_p": p2.get("sign_test_p")})
            beats = "✅" if r["lift_new"] > base["lift_old"] and p2["new_better"] > p2["new_worse"] else "  "
            print(f"  {beats}{name:<14} lift={r['lift_new']:>5} MRR={r['new_rule']['MRR']:.3f} "
                  f"hit@10={r['new_rule']['hit@10']:.3f} win/lose={p2['new_better']}/{p2['new_worse']} "
                  f"p={p2.get('sign_test_p')}")
        vrows.sort(key=lambda x: -x["lift_new"])
        out["variants"] = vrows
        winner = vrows[0]
        print(f"\n  최상 변이: {winner['variant']} lift={winner['lift_new']} "
              f"(OLD {base['lift_old']}) → "
              f"{'OLD 초과 ✅' if winner['lift_new'] > base['lift_old'] else 'OLD 미달 — 규칙 재설계 계속'}")

    if args.sweep:
        print("\n=== 파라미터 스윕 (CV 기반 최적 규칙 탐색) ===")
        grid = []
        for tau in (3.0, 12.0, 48.0, 168.0):
            for ap_ in (0.04, 0.08):
                for homeo in (2.0, 4.0, 999.0):
                    grid.append(dict(DEFAULTS, tau_hours=tau, a_plus=ap_, a_co=ap_, homeo_target=homeo))
        sweep_res = []
        best = {"lift_new": base["lift_new"], "params": dict(DEFAULTS)}
        for gp in grid:
            r = run_cv(events, gp, max(8, args.folds // 2), SEED)
            row = {"params": {k: gp[k] for k in ("tau_hours", "a_plus", "homeo_target")},
                   "lift_new": r["lift_new"], "mrr_new": r["new_rule"]["MRR"],
                   "delta_lift": r["delta_lift"], "sign_p": r["paired"].get("sign_test_p")}
            sweep_res.append(row)
            print(f"  tau={gp['tau_hours']:<5} A+={gp['a_plus']} homeo={gp['homeo_target']:<5}"
                  f" lift_new={r['lift_new']:>6} Δ={r['delta_lift']:+} p={row['sign_p']}")
            if r["lift_new"] > best["lift_new"]:
                best = {"lift_new": r["lift_new"], "params": gp, "delta_lift": r["delta_lift"]}
        out["sweep"] = sorted(sweep_res, key=lambda x: -x["lift_new"])
        out["best"] = {k: best[k] for k in best if k != "params"} | {"params": {kk: best["params"][kk] for kk in ("tau_hours", "a_plus", "a_co", "homeo_target", "a_minus", "w_sat")}}
        print(f"\n  최적 lift_new = {best['lift_new']} (default new {base['lift_new']}, old {base['lift_old']})")

    today = datetime.now().strftime("%Y%m%d")
    path = OUT / f"plasticity_{args.tag}_{today}.json"
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n[out] {path}")


if __name__ == "__main__":
    main()
