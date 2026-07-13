"""
Sleep-Distill Job — 살아있는 로컬 코어 (연구 프로토타입 → 시스템 전환)
==============================================================================
Phase 2 실물. 지금까지 실험은 **일회성**(매번 fresh LoRA). 이 job은 LoRA 어댑터를
**디스크에 영속**시켜, 실행마다 직전 상태에서 이어 학습한다 = 경험이 쌓일수록 **코어가
계속 자라는** 야간 통합(sleep consolidation)의 실체.

동작 (야간 1회):
  1. 로컬 LLM(Qwen2.5-0.5B) + 어댑터 체크포인트 로드(없으면 fresh LoRA).
  2. 현재 실 Neo4j 그래프 → replay 에피소드.
  3. eval(학습 전 MRR = 직전 코어 상태) → distill(LoRA 학습) → eval(학습 후).
  4. 어댑터 저장(누적) + 성장 시계열 log append.
→ 실행2의 "학습 전 MRR" ≈ 실행1의 "학습 후 MRR" 이면 = 코어가 기억 유지(영속) 실증.

Usage:
    python scripts/research/sleep_distill_job.py --steps 200
    python scripts/research/sleep_distill_job.py --fresh   # 어댑터 초기화
출력: 어댑터 `models/local_core_adapter/` · 시계열 `claudedocs/monitoring/local_core_growth.jsonl`
"""
from __future__ import annotations
import argparse, json, os, random, shutil, statistics, sys
from datetime import datetime, timezone
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import LoraConfig, get_peft_model, PeftModel

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(__file__))
from llm_core_distill import MODEL, DEV, distill
from llm_real_distill import fetch_graph, episodes_from_graph, eval_pairs, mrr, K_NEG

ROOT = Path(__file__).resolve().parents[2]
CKPT = ROOT / "models" / "local_core_adapter"
LOG = ROOT / "claudedocs" / "monitoring" / "local_core_growth.jsonl"
LOG.parent.mkdir(parents=True, exist_ok=True)


def load_core(fresh=False):
    """어댑터 체크포인트 있으면 이어받고, 없으면 fresh LoRA. → 영속 누적 코어."""
    base = AutoModelForCausalLM.from_pretrained(MODEL, dtype=torch.float16).to(DEV)
    if CKPT.exists() and not fresh:
        model = PeftModel.from_pretrained(base, str(CKPT), is_trainable=True).to(DEV)
        return model, True
    cfg = LoraConfig(r=8, lora_alpha=16, lora_dropout=0.05, task_type="CAUSAL_LM",
                     target_modules=["q_proj", "k_proj", "v_proj", "o_proj"])
    return get_peft_model(base, cfg).to(DEV), False


def run_count():
    if not LOG.exists():
        return 0
    return sum(1 for l in LOG.read_text(encoding="utf-8").splitlines() if l.strip())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", type=int, default=200)
    ap.add_argument("--fresh", action="store_true")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    if args.fresh and CKPT.exists():
        shutil.rmtree(CKPT)

    rng = random.Random(args.seed)
    tok = AutoTokenizer.from_pretrained(MODEL)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token

    edges, adj, cat = fetch_graph()
    all_nodes = sorted(adj.keys())
    ev_rng = random.Random(1)
    test = edges[:250]
    test = [(a, b, w) for (a, b, w) in test if a in adj and b in adj]

    model, resumed = load_core(fresh=args.fresh)
    run_i = run_count() + 1
    print(f"=== SLEEP-DISTILL JOB (살아있는 로컬 코어) — run #{run_i} ===")
    print(f"  코어: {'✅ 어댑터 이어받음(누적)' if resumed else '🆕 fresh LoRA'} | "
          f"그래프 {len(all_nodes)} concept / {len(edges)} edge")

    before = eval_pairs(model, tok, test, all_nodes, random.Random(1))
    mrr_before = mrr(before)
    id_before = mrr([p for p in before if p["identity"]])
    print(f"  학습 전 link-MRR {mrr_before} (identity {id_before})  ← 직전 코어 상태")

    eps = episodes_from_graph(adj, [n for n in adj if adj[n]], 400, rng)
    losses = distill(model, tok, eps, args.steps)

    after = eval_pairs(model, tok, test, all_nodes, random.Random(1))
    mrr_after = mrr(after)
    id_after = mrr([p for p in after if p["identity"]])
    print(f"  학습 후 link-MRR {mrr_after} (identity {id_after})  Δ{round(mrr_after-mrr_before,4):+}")

    model.save_pretrained(str(CKPT))
    print(f"  💾 어댑터 저장 → {CKPT.relative_to(ROOT)}")

    row = {"run": run_i, "timestamp": datetime.now(timezone.utc).isoformat(),
           "resumed": resumed, "n_edges": len(edges),
           "mrr_before": mrr_before, "mrr_after": mrr_after,
           "identity_before": id_before, "identity_after": id_after,
           "loss_first": round(losses[0], 3), "loss_last": round(losses[-1], 3),
           "steps": args.steps}
    with LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    if run_i >= 2:
        prev = [json.loads(l) for l in LOG.read_text(encoding="utf-8").splitlines() if l.strip()][-2]
        print(f"\n  ♻️ 영속 확인: run#{run_i} 학습전 MRR {mrr_before} vs run#{run_i-1} 학습후 {prev['mrr_after']} "
              f"→ {'✅ 기억 유지(코어 누적)' if mrr_before >= prev['mrr_after']*0.9 else '⚠️ 유지 약함'}")
    print(f"\n[log] {LOG.relative_to(ROOT)} (누적 {run_i} runs)")


if __name__ == "__main__":
    main()
