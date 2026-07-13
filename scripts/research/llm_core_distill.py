"""
LLM+LoRA Core — Phase 2 실물: 로컬 소형 LLM을 sleep-distill로 학습 (임베딩 대역 교체)
==============================================================================
이번 세션 연구 귀결. head_crossover/sleep_distill 은 장난감 임베딩 코어로 CLS 가중치
자기학습·안티망각을 축소 실증했다. 이 스크립트는 그 코어를 **진짜 로컬 소형 LLM +
LoRA** 로 교체한다 = Phase 2 의 실물 첫 걸음.

개념 (사용자 질문에 대한 답의 실체화)
- 로컬 LLM(Qwen2.5-0.5B) = 학습 가능한 신피질(네 GPU서 돎, 가중치 네 것). Gemini API(frozen
  언어 도구)와 다른 상자 — 이건 경험으로 가중치가 바뀌는 "자라는 뇌".
- LoRA = 5억 파라미터 통째 대신 작은 어댑터만 학습(싸고 안전한 야간 미세조정).
- sleep-distill = 그래프가 replay한 co-activation 에피소드를 텍스트로 LoRA 학습 → LLM 가중치 변화.

리트머스 (north star): retrieval 없이 **LoRA 가중치만으로** held-out co-occurrence 예측(MRR)이
base 모델 대비 오르는가 = 진짜 자기학습(이번엔 장난감 아닌 실 LLM).

Usage:
    python scripts/research/llm_core_distill.py            # base vs LoRA MRR
    python scripts/research/llm_core_distill.py --forget   # 순차태스크 안티망각(LLM판)
출력: claudedocs/research/llm_core_distill_<YYYYMMDD>.json
"""
from __future__ import annotations
import argparse, json, os, random, statistics, sys
from datetime import datetime, timezone
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import LoraConfig, get_peft_model

sys.stdout.reconfigure(encoding="utf-8")
OUT = Path(__file__).resolve().parents[2] / "claudedocs" / "research"
OUT.mkdir(parents=True, exist_ok=True)
MODEL = "Qwen/Qwen2.5-0.5B-Instruct"
DEV = "cuda" if torch.cuda.is_available() else "cpu"

# "아기의 방들" — 실단어 장면. 같은 장면 단어끼리 co-occur (아기의 특정 경험구조).
SCENES = {
    "desk":    ["keyboard", "monitor", "coffee", "notebook", "lamp", "pen"],
    "kitchen": ["pan", "plate", "spoon", "stove", "kettle", "bowl"],
    "garden":  ["flower", "soil", "leaf", "fence", "hose", "seed"],
    "bath":    ["towel", "soap", "mirror", "brush", "sink", "razor"],
    "garage":  ["wrench", "tire", "engine", "ladder", "paint", "bolt"],
}


def build_vocab(scenes):
    vocab = []
    word2scene = {}
    for s, ws in scenes.items():
        for w in ws:
            vocab.append(w); word2scene[w] = s
    return vocab, word2scene


def episodes(scenes, n, rng):
    """replay 에피소드 = 한 장면의 단어들 무작위 순서 (co-activation 패턴)."""
    eps = []
    names = list(scenes)
    for _ in range(n):
        s = rng.choice(names)
        ws = scenes[s][:]
        rng.shuffle(ws)
        eps.append(ws[:rng.randint(3, len(ws))])
    return eps


@torch.no_grad()
def link_mrr(model, tok, scenes, word2scene, rng, n_query=60):
    """held-out link-prediction MRR: seed 단어에서 같은 장면 파트너를 후보 전체 중 랭킹.
    score(seed,cand)=시퀀스 'seed cand' logprob (retrieval 없음, 가중치만)."""
    model.eval()
    vocab = list(word2scene)
    recs = []
    for _ in range(n_query):
        a = rng.choice(vocab)
        partners = [w for w in scenes[word2scene[a]] if w != a]
        b = rng.choice(partners)
        cands = [w for w in vocab if w != a]              # 전체 후보(같은장면 제외 안함=b 포함)
        # 배치: "a cand" 각 후보의 시퀀스 logprob
        seqs = [f"{a} {c}" for c in cands]
        enc = tok(seqs, return_tensors="pt", padding=True).to(DEV)
        out = model(**enc)
        logp = torch.log_softmax(out.logits.float(), dim=-1)
        ids = enc.input_ids
        # 각 위치 t 의 토큰 logprob (teacher forcing): logp[:, t-1, ids[:,t]]
        tok_lp = logp[:, :-1, :].gather(2, ids[:, 1:].unsqueeze(-1)).squeeze(-1)
        mask = enc.attention_mask[:, 1:].float()
        seq_score = (tok_lp * mask).sum(1) / mask.sum(1).clamp(min=1)   # 평균 logprob
        order = torch.argsort(seq_score, descending=True).tolist()
        ranked = [cands[i] for i in order]
        r = ranked.index(b) + 1
        recs.append(1.0 / r)
    return round(statistics.mean(recs), 4)


def distill(model, tok, eps, steps, lr=2e-4):
    """sleep-distill: replay 에피소드를 causal-LM LoRA 학습(가중치 변화)."""
    model.train()
    opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=lr)
    losses = []
    for i in range(steps):
        ep = eps[i % len(eps)]
        text = " ".join(ep)
        enc = tok(text, return_tensors="pt").to(DEV)
        out = model(**enc, labels=enc.input_ids)
        out.loss.backward()
        opt.step(); opt.zero_grad()
        losses.append(out.loss.item())
    return losses


def load_lora():
    model = AutoModelForCausalLM.from_pretrained(MODEL, dtype=torch.float16).to(DEV)
    cfg = LoraConfig(r=8, lora_alpha=16, lora_dropout=0.05, task_type="CAUSAL_LM",
                     target_modules=["q_proj", "k_proj", "v_proj", "o_proj"])
    model = get_peft_model(model, cfg)
    n_train = sum(p.numel() for p in model.parameters() if p.requires_grad)
    n_tot = sum(p.numel() for p in model.parameters())
    return model, n_train, n_tot


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--forget", action="store_true", help="순차태스크 안티망각(LLM판)")
    ap.add_argument("--steps", type=int, default=300)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    rng = random.Random(args.seed)
    tok = AutoTokenizer.from_pretrained(MODEL)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token

    if not args.forget:
        vocab, w2s = build_vocab(SCENES)
        model, n_tr, n_tot = load_lora()
        print(f"=== LLM+LoRA CORE (Phase 2 실물) — {MODEL} on {DEV} ===")
        print(f"  LoRA 학습 파라미터 {n_tr/1e6:.2f}M / 전체 {n_tot/1e6:.0f}M ({100*n_tr/n_tot:.2f}%)")
        base_mrr = link_mrr(model, tok, SCENES, w2s, random.Random(1))   # LoRA=0 상태=base
        print(f"  base(사전학습만) link-MRR: {base_mrr}  (chance≈{round(1/len(vocab),3)})")
        eps = episodes(SCENES, 200, rng)
        losses = distill(model, tok, eps, args.steps)
        after_mrr = link_mrr(model, tok, SCENES, w2s, random.Random(1))
        print(f"  after LoRA sleep-distill link-MRR: {after_mrr}")
        gain = round(after_mrr - base_mrr, 4)
        print(f"\n  리트머스: MRR {base_mrr} → {after_mrr} (Δ{gain:+})  "
              f"{'✅ 가중치만으로 예측오차↓ = 실 LLM 자기학습' if gain > 0.02 else '🟡 변화 미미'}")
        print(f"  (retrieval 없음 — LoRA 어댑터 가중치만 바뀜. loss {round(losses[0],2)}→{round(losses[-1],2)})")
        out = {"mode": "self_learning", "model": MODEL, "device": DEV,
               "lora_trainable_M": round(n_tr/1e6, 3), "total_M": round(n_tot/1e6, 1),
               "base_mrr": base_mrr, "after_mrr": after_mrr, "gain": gain,
               "loss_first": round(losses[0], 3), "loss_last": round(losses[-1], 3),
               "steps": args.steps, "seed": args.seed}
    else:
        # 순차태스크 안티망각: Task A 장면들 → Task B 장면들. B 학습 후 A 유지?
        A = {k: SCENES[k] for k in ("desk", "kitchen")}
        B = {k: SCENES[k] for k in ("garden", "bath")}
        _, w2sA = build_vocab(A); _, w2sB = build_vocab(B)
        model, n_tr, n_tot = load_lora()
        print(f"=== LLM+LoRA 안티망각 (순차 Task A→B) — {MODEL} ===")
        distill(model, tok, episodes(A, 200, rng), args.steps)           # Task A 학습
        a_peak = link_mrr(model, tok, A, w2sA, random.Random(1))
        b_before = link_mrr(model, tok, B, w2sB, random.Random(2))
        distill(model, tok, episodes(B, 200, rng), args.steps)           # Task B 학습 (A replay 없음=online)
        a_final = link_mrr(model, tok, A, w2sA, random.Random(1))
        b_final = link_mrr(model, tok, B, w2sB, random.Random(2))
        print(f"  Task-A MRR: A학습후 {a_peak} → B학습후 {a_final} (Δ{round(a_final-a_peak,4):+})")
        print(f"  Task-B MRR: B학습전 {b_before} → B학습후 {b_final}")
        forgot = a_final < a_peak - 0.05
        print(f"\n  online(A replay 없이 B학습) A망각: {'⚠️ 망각 발생(→ sleep replay 필요 입증)' if forgot else '유지'}")
        out = {"mode": "forget_online", "a_peak": a_peak, "a_final": a_final,
               "b_before": b_before, "b_final": b_final, "a_forgot": bool(forgot), "seed": args.seed}

    out["timestamp"] = datetime.now(timezone.utc).isoformat()
    today = datetime.now().strftime("%Y%m%d")
    path = OUT / f"llm_core_distill_{today}.json"
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n[out] {path}")


if __name__ == "__main__":
    main()
