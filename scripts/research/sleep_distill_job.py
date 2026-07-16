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
from graph_replay_split import build_edge_disjoint_split
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


def save_promoted_core(model) -> None:
    """Replace the adapter only after a complete candidate save.

    The previous adapter remains recoverable if candidate promotion fails.
    """

    candidate = MDIR / ".local_core_adapter_candidate"
    previous = MDIR / ".local_core_adapter_previous"
    if candidate.exists():
        shutil.rmtree(candidate)
    if previous.exists():
        shutil.rmtree(previous)
    model.save_pretrained(str(candidate))
    moved_previous = False
    try:
        if CKPT.exists():
            CKPT.rename(previous)
            moved_previous = True
        candidate.rename(CKPT)
    except Exception:
        if moved_previous and not CKPT.exists() and previous.exists():
            previous.rename(CKPT)
        raise
    finally:
        if candidate.exists():
            shutil.rmtree(candidate)
    if previous.exists():
        try:
            shutil.rmtree(previous)
        except OSError:
            print(f"[distill] 이전 adapter backup 정리 보류: {previous.name}")


# 마커/락은 models/ 에 (CKPT rmtree(--fresh)에 안 지워지게). adversarial review wf_42f17ed5 반영.
MDIR = ROOT / "models"
MARKER = MDIR / ".last_run_date"     # 성공 완료일 (하루 1회)
ATTEMPT = MDIR / ".last_attempt"     # 마지막 시도 시각 (실패 후 retry-storm 방지 backoff)
LOCK = MDIR / ".distill.lock"
STALE_SEC = 2 * 3600                 # hard-kill 잔존 락 stale 판정
BACKOFF_SEC = 30 * 60               # 시도 실패 후 재시도 최소 간격 (storm 방지)


def should_skip_daily():
    """--daily-gate: 오늘 이미 성공 or 최근 시도(backoff) 있으면 skip 사유 반환, 아니면 None."""
    today = datetime.now().strftime("%Y-%m-%d")
    if MARKER.exists() and MARKER.read_text(encoding="utf-8").strip() == today:
        return f"오늘({today}) 이미 완료"
    if ATTEMPT.exists():
        try:
            age = datetime.now().timestamp() - ATTEMPT.stat().st_mtime
            if age < BACKOFF_SEC:
                return f"최근 시도({int(age)}s<{BACKOFF_SEC}) backoff"
        except Exception:
            pass
    return None


def acquire_lock():
    """항상(수동/훅 무관) GPU 학습 동시실행 차단. stale TTL 자가치유. fd or None."""
    MDIR.mkdir(parents=True, exist_ok=True)
    if LOCK.exists():
        try:
            if datetime.now().timestamp() - LOCK.stat().st_mtime > STALE_SEC:
                print(f"[lock] stale 락 제거"); LOCK.unlink()
        except Exception:
            pass
    try:
        return os.open(str(LOCK), os.O_CREAT | os.O_EXCL | os.O_WRONLY)  # 원자적
    except FileExistsError:
        return None


def release_lock(fd):
    if fd is None:                       # 우리가 안 잡았으면 남의 락 건드리지 않음
        return
    try:
        os.close(fd)
        if LOCK.exists():
            LOCK.unlink()
    except Exception:
        pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", type=int, default=200)
    ap.add_argument("--fresh", action="store_true")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--daily-gate", action="store_true", help="하루 1회+backoff (라이브 훅용)")
    args = ap.parse_args()
    # 1) daily-gate: 오늘 완료/최근 시도면 모델 로드 전에 즉시 skip
    if args.daily_gate:
        reason = should_skip_daily()
        if reason:
            print(f"[gate] {reason} → skip"); return
    # 2) 락은 항상 획득 (수동 실행도 훅 실행과 GPU 충돌 방지)
    lock_fd = acquire_lock()
    if lock_fd is None:
        print("[lock] 다른 distill 실행 중 → skip"); return
    try:
        MDIR.mkdir(parents=True, exist_ok=True)
        ATTEMPT.write_text(datetime.now().isoformat(), encoding="utf-8")   # 시도 기록(backoff)
        ok = _main_run(args)
        if args.daily_gate and ok:       # 성공(학습 완료)했을 때만 오늘 완료 마킹
            MARKER.write_text(datetime.now().strftime("%Y-%m-%d"), encoding="utf-8")
    finally:
        release_lock(lock_fd)


def _main_run(args) -> bool:
    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)

    # Neo4j 그래프 먼저 (없으면 학습할 게 없음). 다운 시 traceback 없이 clean skip.
    try:
        edges, adj, cat = fetch_graph()
    except Exception as e:
        print(f"[distill] Neo4j 연결 실패 → skip (야간 학습엔 Neo4j 켜져 있어야 함): "
              f"{type(e).__name__}")
        return False
    if not edges:
        print("[distill] 그래프에 엣지 없음 → skip"); return False

    # VRAM 프리플라이트: 여유 부족하면 OOM 전에 clean defer (retriable; backoff가 storm 방지)
    try:
        if DEV == "cuda":
            free, _tot = torch.cuda.mem_get_info()
            if free < 2.5e9:
                print(f"[distill] VRAM 여유 {free/1e9:.1f}GB<2.5 → 이번 defer"); return False
    except Exception:
        pass

    rng = random.Random(args.seed)
    tok = AutoTokenizer.from_pretrained(MODEL)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    all_nodes = sorted(adj.keys())
    split = build_edge_disjoint_split(edges, seed=args.seed)
    test = split.test_edges
    train_adj = split.train_adjacency
    if not test:
        print("[distill] pair-disjoint 평가쌍 없음 → skip")
        return False

    try:   # GPU 학습: OOM/CUDA 오류도 clean skip (Neo4j 경로와 동형; DEVNULL로 traceback 숨는 것 방지)
        model, resumed = load_core(fresh=args.fresh)
        run_i = run_count() + 1
        print(f"=== SLEEP-DISTILL JOB (살아있는 로컬 코어) — run #{run_i} ===")
        print(f"  코어: {'✅ 어댑터 이어받음(누적)' if resumed else '🆕 fresh LoRA'} | "
              f"그래프 {len(all_nodes)} concept / {len(edges)} raw edge / "
              f"{split.diagnostics['unique_pair_count']} unique pair")
        before = eval_pairs(model, tok, test, all_nodes, random.Random(1))
        mrr_before = mrr(before); id_before = mrr([p for p in before if p["identity"]])
        print(f"  학습 전 link-MRR {mrr_before} (identity {id_before})  ← 직전 코어 상태")
        eps = episodes_from_graph(
            train_adj,
            [n for n in train_adj if train_adj[n]],
            400,
            rng,
        )
        losses = distill(model, tok, eps, args.steps)
        after = eval_pairs(model, tok, test, all_nodes, random.Random(1))
        mrr_after = mrr(after); id_after = mrr([p for p in after if p["identity"]])
        print(f"  학습 후 link-MRR {mrr_after} (identity {id_after})  Δ{round(mrr_after-mrr_before,4):+}")
        identity_pairs_present = any(p["identity"] for p in before)
        promotion_gate = (
            mrr_after >= mrr_before
            and (not identity_pairs_present or id_after >= id_before)
        )
        if promotion_gate:
            save_promoted_core(model)
            print(f"  💾 비퇴행 게이트 통과, 어댑터 저장 → {CKPT.relative_to(ROOT)}")
        else:
            print("  🛑 비퇴행 게이트 실패, 기존 어댑터를 덮어쓰지 않음")
        row = {"run": run_i, "timestamp": datetime.now(timezone.utc).isoformat(),
               "resumed": resumed, "n_edges": len(edges),
               "evaluation_split": "canonical_undirected_pair_disjoint_current_run",
               "resumed_adapter_prior_graph_exposure_possible": resumed,
               "split_diagnostics": split.diagnostics,
               "mrr_before": mrr_before, "mrr_after": mrr_after,
               "identity_before": id_before, "identity_after": id_after,
               "loss_first": round(losses[0], 3), "loss_last": round(losses[-1], 3),
               "steps": args.steps, "promotion_gate": promotion_gate,
               "adapter_saved": promotion_gate}
        with LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        if run_i >= 2:
            prev = [json.loads(l) for l in LOG.read_text(encoding="utf-8").splitlines() if l.strip()][-2]
            if prev.get("adapter_saved", True):
                print(f"\n  ♻️ 영속 확인: run#{run_i} 학습전 MRR {mrr_before} vs run#{run_i-1} 학습후 "
                      f"{prev['mrr_after']} → {'✅ 저장 상태 유지' if mrr_before >= prev['mrr_after']*0.9 else '⚠️ 유지 약함'}")
            else:
                print("\n  ℹ️ 직전 run은 promotion 실패로 저장되지 않아 persistence 비교 제외")
        print(f"\n[log] {LOG.relative_to(ROOT)} (누적 {run_i} runs)")
        return True
    except torch.cuda.OutOfMemoryError:
        torch.cuda.empty_cache()
        print("[distill] CUDA OOM → skip (GPU 여유 생기면 backoff 후 재시도)"); return False
    except Exception as e:
        print(f"[distill] 학습 오류 → skip: {type(e).__name__}: {e}"); return False


if __name__ == "__main__":
    main()
