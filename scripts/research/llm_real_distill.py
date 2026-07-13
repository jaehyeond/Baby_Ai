"""
LLM+LoRA on REAL Neo4j — Phase 2 결정적 검증 (base가 모르는 아기 특이연상 학습?)
==============================================================================
llm_core_distill(합성 실단어)의 한계: base MRR 0.176 = Qwen이 keyboard-monitor를 이미 앎
→ "사전지식 복구"지 "아기 경험 학습"이 아닐 수 있음. 진짜 리트머스 = **base가 모르는
특이 연상**(비비=이 아기 이름, 비비-형(brother), 엄마=박재현 테스트페르소나)을 LoRA가 배우는가.

이 스크립트: **실 Neo4j RELATES_TO 그래프**로 LoRA sleep-distill → held-out 엣지 link-MRR
base 대비 상승 측정 + **novelty 층화**(base가 틀린 쌍을 LoRA가 구제하는가 = 진짜 자기학습).

Usage: python scripts/research/llm_real_distill.py --steps 400
출력: claudedocs/research/llm_real_distill_<YYYYMMDD>.json
"""
from __future__ import annotations
import argparse, json, os, random, statistics, sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import torch
from dotenv import load_dotenv
from neo4j import GraphDatabase

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(__file__))
from llm_core_distill import MODEL, DEV, load_lora, distill   # 모델/LoRA/학습 재사용
from transformers import AutoTokenizer

load_dotenv(".env")
URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
AUTH = (os.getenv("NEO4J_USERNAME", "neo4j"), os.getenv("NEO4J_PASSWORD", ""))
DB = os.getenv("NEO4J_DATABASE", "neo4j")
OUT = Path(__file__).resolve().parents[2] / "claudedocs" / "research"
OUT.mkdir(parents=True, exist_ok=True)
IDENTITY = {"비비", "엄마", "박재현", "형", "아빠", "AI", "사용자", "AI (비비)"}
K_NEG = 40


def fetch_graph():
    d = GraphDatabase.driver(URI, auth=AUTH, notifications_min_severity="OFF")
    edges, adj, cat = [], defaultdict(dict), {}
    with d.session(database=DB) as s:
        rows = s.run(
            "MATCH (a:Concept)-[r:RELATES_TO]->(b:Concept) "
            "WHERE coalesce(a.category,'')<>'frozen_knowledge' AND coalesce(b.category,'')<>'frozen_knowledge' "
            "RETURN a.name AS a, b.name AS b, coalesce(r.strength,r.weight,0.5) AS w, "
            "a.category AS ca, b.category AS cb"
        ).data()
    d.close()
    for e in rows:
        a, b, w = e["a"], e["b"], e["w"]
        if not a or not b or a == b:
            continue
        edges.append((a, b, w)); cat[a] = e["ca"]; cat[b] = e["cb"]
        adj[a][b] = max(adj[a].get(b, 0), w); adj[b][a] = max(adj[b].get(a, 0), w)
    return edges, adj, cat


def episodes_from_graph(adj, seeds, n, rng, size=6):
    eps = []
    for _ in range(n):
        a = rng.choice(seeds)
        nbrs = [n for n, _ in sorted(adj[a].items(), key=lambda kv: -kv[1])[:size - 1]]
        ep = [a] + nbrs
        rng.shuffle(ep)
        if len(ep) >= 2:
            eps.append(ep)
    return eps


@torch.no_grad()
def eval_pairs(model, tok, test_edges, all_nodes, nrng, k=K_NEG):
    """held-out 엣지별 sampled-negative link-MRR + per-pair reciprocal rank(층화용)."""
    model.eval()
    per_pair = []
    for (a, b, _w) in test_edges:
        negs = []
        tries = 0
        while len(negs) < k and tries < k * 4:
            n = all_nodes[nrng.randint(0, len(all_nodes) - 1)]
            if n != a and n != b:
                negs.append(n)
            tries += 1
        if len(negs) < k // 2:
            continue
        cands = [b] + negs
        seqs = [f"{a} {c}" for c in cands]
        enc = tok(seqs, return_tensors="pt", padding=True).to(DEV)
        out = model(**enc)
        logp = torch.log_softmax(out.logits.float(), dim=-1)
        ids = enc.input_ids
        tok_lp = logp[:, :-1, :].gather(2, ids[:, 1:].unsqueeze(-1)).squeeze(-1)
        mask = enc.attention_mask[:, 1:].float()
        score = (tok_lp * mask).sum(1) / mask.sum(1).clamp(min=1)
        order = torch.argsort(score, descending=True).tolist()
        rank = order.index(0) + 1                       # cands[0]=b(참)
        per_pair.append({"a": a, "b": b, "rr": 1.0 / rank,
                         "identity": a in IDENTITY or b in IDENTITY})
    return per_pair


def mrr(pairs):
    return round(statistics.mean(p["rr"] for p in pairs), 4) if pairs else 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", type=int, default=400)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    rng = random.Random(args.seed); nrng = random.Random(args.seed + 7)
    tok = AutoTokenizer.from_pretrained(MODEL)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token

    edges, adj, cat = fetch_graph()
    all_nodes = sorted(adj.keys())
    rng.shuffle(edges)
    # held-out: 양끝이 다른 엣지도 갖는 것만 (train서 고립 방지)
    n_test = min(250, int(len(edges) * 0.2))
    test, train_edges = edges[:n_test], edges[n_test:]
    # train 인접(held-out 엣지 제거)
    tadj = defaultdict(dict)
    for a, b, w in train_edges:
        tadj[a][b] = max(tadj[a].get(b, 0), w); tadj[b][a] = max(tadj[b].get(a, 0), w)
    seeds = [n for n in tadj if tadj[n]]
    print(f"=== LLM+LoRA on REAL Neo4j — {MODEL} ===")
    print(f"  concepts {len(all_nodes)} | edges {len(edges)} | test {len(test)} | train episodes seeds {len(seeds)}")

    model, n_tr, n_tot = load_lora()
    # test 엣지 중 양끝이 train에 있는 것만 평가
    test = [(a, b, w) for (a, b, w) in test if a in tadj and b in tadj]
    base = eval_pairs(model, tok, test, all_nodes, random.Random(1))
    base_mrr = mrr(base)
    id_base = mrr([p for p in base if p["identity"]])
    print(f"  base(사전학습만) link-MRR {base_mrr} | identity쌍 {id_base} | chance≈{round(1/(K_NEG+1),3)}")

    eps = episodes_from_graph(tadj, seeds, 400, rng)
    losses = distill(model, tok, eps, args.steps)
    after = eval_pairs(model, tok, test, all_nodes, random.Random(1))
    after_mrr = mrr(after)
    id_after = mrr([p for p in after if p["identity"]])
    print(f"  LoRA sleep-distill 후 link-MRR {after_mrr} | identity쌍 {id_after}")

    # novelty 층화: base가 틀린 쌍(base rr<0.2=rank>5)을 LoRA가 구제하는가
    base_rr = {(p["a"], p["b"]): p["rr"] for p in base}
    poor = [p for p in after if base_rr.get((p["a"], p["b"]), 0) < 0.2]
    poor_base = round(statistics.mean(base_rr[(p["a"], p["b"])] for p in poor), 4) if poor else 0
    poor_after = mrr(poor)
    print(f"\n  === novelty 층화 (진짜 자기학습 = base가 모르던 걸 배움) ===")
    print(f"  base가 틀린 쌍(rank>5) {len(poor)}개: base-MRR {poor_base} → LoRA후 {poor_after} "
          f"(Δ{round(poor_after-poor_base,4):+})")
    gain = round(after_mrr - base_mrr, 4); id_gain = round(id_after - id_base, 4)
    print(f"\n  리트머스: 전체 {base_mrr}→{after_mrr}(Δ{gain:+}) | identity {id_base}→{id_after}(Δ{id_gain:+})")
    verdict = ("✅ base가 모르던 아기 특이연상을 LoRA가 학습 = 진짜 자기학습(실 데이터)"
               if poor_after - poor_base > 0.05 and gain > 0.02 else "🟡 신호 약함/사전지식 복구 의심")
    print(f"  판정: {verdict}  (loss {round(losses[0],2)}→{round(losses[-1],2)})")

    out = {"model": MODEL, "n_concepts": len(all_nodes), "n_edges": len(edges), "n_test": len(test),
           "base_mrr": base_mrr, "after_mrr": after_mrr, "gain": gain,
           "identity_base": id_base, "identity_after": id_after, "identity_gain": id_gain,
           "base_poor_count": len(poor), "base_poor_mrr": poor_base, "base_poor_after": poor_after,
           "loss_first": round(losses[0], 3), "loss_last": round(losses[-1], 3),
           "lora_trainable_M": round(n_tr / 1e6, 3), "steps": args.steps, "seed": args.seed,
           "timestamp": datetime.now(timezone.utc).isoformat()}
    today = datetime.now().strftime("%Y%m%d")
    path = OUT / f"llm_real_distill_{today}.json"
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n[out] {path}")


if __name__ == "__main__":
    main()
