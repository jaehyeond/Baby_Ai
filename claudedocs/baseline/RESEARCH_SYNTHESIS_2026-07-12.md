# WHAT TO ADD NEXT — Baby AI Brain Self-Learning Program

Synthesis of 6 research angles into an implementable roadmap. Anchored to current state: ~518 Concepts / ~2085 edges / 3114 timestamped Experiences; additive-capped Hebbian + PPR recall + multiplicative global decay; baseline lift-vs-random = 7.86× (offline, easy negatives — treated below as *inflated*, not settled).

---

## 1. Phase 1 plasticity rule — concrete spec (LLM-free, buildable now)

The rule fuses four mechanisms into ONE per-experience update. Compute it in Python (numpy) over an in-memory event array pulled with one Cypher `MATCH (e:Experience)-[:INVOLVES]->(c:Concept) RETURN ... ORDER BY e.created_at`, then bulk-write with `UNWIND + SET`. **Do not attempt the trace recursion inside Cypher.**

### 1.0 Structural prerequisite: make edges directional
Replace undirected `RELATES_TO` with two directed weights `w_fwd` (i→j) and `w_bwd` (j→i). This is required for STDP asymmetry AND makes per-node incoming normalization conflict-free (turns weights into conditional probabilities P(i|j)). Store per edge: `w_fwd, w_bwd, eligibility, evidence_count, last_update_ts`. **Blast radius: ~2085 → ~4170 edges and every Cypher query assuming undirected RELATES_TO must migrate.** (Miller & MacKay 1994 [peer-reviewed]; homeostasis-normalization angle.)

### 1.1 STDP timing kernel (directional signal)
For a directed pair (i→j) with `dt = t_j − t_i` (post minus pre):
```
if dt > 0:  K = +A_plus  * exp(−dt/tau)      # i preceded j → LTP on w(i→j)
if dt < 0:  K = −A_minus * exp(+dt/tau)      # i after j    → LTD on w(i→j)
A_plus  = 0.005 * w_max      (w_max = 1.0)
A_minus = 1.05  * A_plus     # net-depression ratio replaces separate global decay
```
`A_minus/A_plus = 1.05` (Song, Miller & Abbott, *Nat Neuroscience* 2000 [peer-reviewed-top-tier]) drives uncorrelated pairs → 0 while predictive pairs survive — this IS your decay, timing-selective instead of blanket. Kernel form from Bi & Poo, *J Neuroscience* 1998 [peer-reviewed-top-tier].

**tau is the dominant free hyperparameter — DO NOT reuse the biological 20 ms.** Sweep `tau ∈ {1 min, 10 min, 1 h, 6 h, 1 day, 3 day}`, pick `tau* = argmax(held-out link-prediction lift)`. A clear peak in the lift-vs-tau curve is your evidence that real timing structure exists; a flat curve means STDP has collapsed to plain co-occurrence (see risk register).

### 1.2 Streaming eligibility trace (one forward pass, O(experiences·|S|²))
Process experiences in `created_at` order. Keep per-concept `trace[c]`, `last_time[c]`. On firing set S at time t: decay each trace by `exp(−(t − last_time[c])/tau)`, apply the kernel to co-active/recently-traced pairs, then increment trace and set `last_time[c]=t`. **Use nearest-neighbor traces (reset to most-recent spike), not all-to-all** — all-to-all over-weights hub concepts appearing in hundreds of experiences (Morrison, Diesmann & Gerstner, *Biol Cybernetics* 2008 [peer-reviewed]).

### 1.3 Prediction-error gating (three-factor rule = the Phase-1 north star)
This is the piece the current additive rule is missing. Per directed pair (a→b), for every experience where a is active:
```
o_b     = 1 if b co-activated else 0        # observation
p_pred  = w_ab   (cheap tier)  OR  PPR-with-b-held-out, squashed (faithful tier)
delta   = o_b − p_pred                       # signed Rescorla-Wagner error
m_ab    = gamma * m_ab + delta               # surprise momentum (Titans), gamma~0.9
Δw_ab   = eta_eff * e_ab * m_ab * c_ab − lambda * w_ab
```
- `delta` supplies the **negative-evidence term**: when a fires and b does *not*, `o_b=0` → the edge is **depressed**. This makes `w_ab` converge to P(b active | a active) — a calibrated predictor, not a frequency counter. Without it there is nothing to "be wrong about." (Schultz/Dayan/Montague, *Science* 1997 [peer-reviewed-top-tier]: "no dopamine for predicted events.")
- `c_ab = 1/(1 + Var_a[delta])` (running variance per SOURCE concept) is the noisy-TV guard (Pathak et al. ICM, ICML 2017 [peer-reviewed-top-tier]): concepts whose co-activations are inherently random get their learning rate shrunk.
- `eta_eff = eta0 * (1 + beta * S_global)` where `S_global = mean|delta|` over the experience — dopamine-like third factor: surprising experiences get a plasticity burst. **`S_global` is also the exact scalar you log as the prediction-error curve.** (Frémaux & Gerstner, *Front Neural Circuits* 2016 [peer-reviewed].)
- `eta0 ~ 0.01–0.05`; clamp `w` to `[0, 1.0]` with soft bound `(w_max−w)^mu`, `mu ≈ 0.05` (unimodal histogram).

**Critical: you must explicitly enumerate candidate b's** (current neighbors + PPR top-k) and score their `o_b=0` cases, or the negative-evidence term never fires and weights still inflate.

### 1.4 Homeostasis — TWO timescales, mandatory
Zenke & Gerstner (*Phil Trans R Soc B* 2017 [peer-reviewed]) **prove sleep-only normalization is mathematically insufficient** to stabilize Hebbian growth. You need a fast per-update brake AND a slow sleep pass.

- **Fast (every update):** BCM sliding threshold. Keep `theta_j = EMA(a_j²)` per concept (half-life ~200 experiences); potentiate only when `a_j > theta_j`. Chronically-active hubs raise their own theta → their edges depress. Anti-hub brake + surprise gate in one. (Bienenstock, Cooper, Munro, *J Neuroscience* 1982 [peer-reviewed]; triplet-BCM equivalence, Pfister & Gerstner *J Neurosci* 2006 [peer-reviewed].) Alternatively an Oja decay term `−eta·a_j²·w_ij` (Oja 1982 [peer-reviewed]).
- **Slow (nightly sleep pass):** multiplicative synaptic scaling — for each node j, `w_ij ← w_ij · (T_j / Σ_i w_ij)`, L1 target `T_j = 1.0` → incoming weights become a probability distribution. Preserves relative structure. (Turrigiano et al., *Nature* 1998 [peer-reviewed-top-tier].)
- **Optional pruning:** after multiplicative scaling, subtractive pass `w_ij ← max(0, w_ij − lambda_j)`, delete zeros. Only this creates competition and caps hub fan-in; scaling alone never prunes. Set `lambda_j` to remove bottom 10–20% edge mass/night, guarded by a collapse monitor. (Miller & MacKay 1994 [peer-reviewed].)
- **Set the homeostatic timescale ≥ 10× slower than the STDP potentiation step** or the two oscillate/collapse. Validate the ratio by ablation.

### 1.5 Recall-time (cheap hub suppression, independent of learning)
In the PPR step use power-normalized transitions `p(i→j) = w_ij^gamma / Σ_k w_ik^gamma`, `gamma ≈ 0.5–0.75`. Cheapest single intervention against hub-dominated recall. (Carandini & Heeger, *Nat Rev Neuroscience* 2011 [peer-reviewed-top-tier].)

### 1.6 Protect rare-but-true edges
`A_minus/A_plus > 1` slowly erases real-but-rare associations (seen 2–3× far apart). Use the per-edge `evidence_count` to shield low-frequency edges from depression below a floor.

---

## 2. Evaluation protocol (how to honestly claim the PE curve went down)

The current 7.86× lift is **offline, post-hoc, on a static snapshot, with easy random negatives** — it rises from mere graph densification and is only *measured*, never *used*. Replace it.

**Split:** strictly chronological — train `t≤T1`, valid `T1<t≤T2`, test `t>T2`. Never random-edge splits. (xERTE, ICLR 2021 [peer-reviewed-top-tier].)

**Metric:** time-aware **filtered MRR + Hits@1/3/10** on next-step co-activation prediction. When filtering, remove only objects true AT time τ, never all-time (static filtering leaks future facts and inflates). Report raw AND filtered. Add **Expected Calibration Error** — since the RW rule claims `w_ab` is a probability, bin by `w_ab` and check empirical frequency. Falling ECE + rising AUC = genuinely learning a predictive model, not memorizing frequency. (Gastinger et al. ECML-PKDD 2023 [peer-reviewed].)

**Prequential (test-then-train):** at each of the 3114 experiences, PREDICT first, score (filtered MRR), THEN apply the update. The prequential curve over the stream IS your "prediction-error-goes-down" evidence; report its slope. (Gama et al., *Machine Learning* 2013 [peer-reviewed].)

**Baselines (mandatory):** an **EdgeBank memorization baseline** (predict any pair seen in a recent window). If you don't clearly beat it, your "learning" is recurrence memorization. Switch to **hard negatives** — historical (pairs co-active earlier, not now) + inductive (unseen pairs). Expect the 7.86× to shrink; the residual over EdgeBank is the honest signal. (Poursafaei et al., NeurIPS 2022 D&B [peer-reviewed-top-tier].)

**THE attribution control (the crux):** two arms on the IDENTICAL, identically-ordered stream + identical held-out test + fixed seed + identical graph-growth order.
- **Arm A** = current additive-capped Hebbian (the "data grows, rule trivial" null).
- **Arm B** = new STDP + decay + homeostasis + PE-gating rule.
- Compare prequential curves **point-by-point at MATCHED stream position**. Any gap at equal data = the RULE's contribution. **Never compare new-rule-at-end vs old-rule-at-start** — that confounds rule and data.

**Two falsification controls:**
- **Time-shuffle:** permute timestamps, re-run Arm B. If its advantage collapses toward Arm A, temporal structure (not co-occurrence) carries the signal — proves the STDP component works AND catches coarse/batched timestamps making the asymmetry spurious.
- **Data-freeze:** stop adding nodes/edges at a checkpoint, keep applying the rule. Continued error decrease = weight learning; flat = you were only benefiting from data growth.

**Inductive split + degree stratification:** hold out concepts first seen after cutoff; stratify MRR by degree. If lift only exists transductively on well-connected old concepts, you're measuring memorization + degree bias. (GraIL, ICML 2020 [peer-reviewed-top-tier].)

**Freeze ONE protocol** (single-step, filtered, time-aware, fixed negative set) across all variants (Gastinger). **Unit-test the filter** against known timestamped facts — all-time filtering is a common silent MRR-inflating bug.

---

## 3. Missing components ranked by leverage (from gap analysis)

| # | Gap | Smallest buildable step | Depends on |
|---|-----|------------------------|-----------|
| **1** | **No trainable core** — Neo4j scalars are a hand-tuned retrieval cache, not parameters under a loss; frozen Gemini cannot be edited. Disqualifying under the north star. | Add a small trainable head over the graph: D-dim Concept embeddings + link-prediction scorer (DistMult/TransE or 2-layer GNN) in PyTorch, self-supervised to predict held-out co-activations. Trivial compute at 518 nodes. Replaces PPR-on-scalars in `measure_prediction.py` with a LEARNED predictor. De-risks the eventual Gemini→local-model swap. | root |
| **2** | **No online causal PE** — PE is measured offline, never fed back. | At ingestion, BEFORE writing edges for a new Experience, predict its concept set, compute surprise `s = 1 − Jaccard(pred_topk, actual)`, (a) append to a PE timeseries, (b) scale the plasticity update by `s`. Freeze graph between rule variants. | Gap 1 (richer PE); startable on PPR today |
| **3** | **Additive-saturating Hebbian** — no selectivity/competition/timing/error. | The §1 rule. Re-run eval on the SAME frozen data to isolate rule effect. | Gap 2 (surprise term) |
| **4** | **No homeostasis** — hubs dominate, rare concepts decay uniformly. | Nightly per-node synaptic normalization (§1.4) + BCM fast brake. | Gap 3 (shares consolidation write path) |
| **5** | **No embodied grounding** — all Experience is linguistic; Quest depth/pose unused. PE is about WORDS, not the world. | Ingest per-frame detected objects + coarse depth bins + head-pose deltas as Experience nodes (reuse `visual_cooc` source); add one sensorimotor task (given Δpose, predict next-frame object). Start read-only to build dataset. | Gaps 2,3; heavier, high leverage for embodiment |
| **6** | **Monitoring blind to CL failure modes** — one lift number can't see forgetting/collapse/plasticity-loss. | Nightly 4-metric JSON timeseries: online PE curve; forgetting (recall@k on a permanent held-out probe set); collapse (edge-weight entropy + degree Gini + embedding effective rank); plasticity (can it learn a freshly injected association in N updates). Alert on breach. | Gap 1 for effective-rank |
| **7** | **No safety gates + rollback** — Phase-2 nightly LoRA can inject bad updates irreversibly. | Version every checkpoint; run Gap-6 harness post-update; auto-rollback on threshold breach; continual-backprop reinit of dormant units. | Gaps 1, 6 |

---

## 4. Phase 2 decisive lever — minimal local-core + sleep-distill

"Escaping the frozen API" and "switching to self-learning" are the **same single move**: replace frozen Gemini with a small LOCAL trainable core, unlocking SEAL/STaR/TTT self-editing.

**Model:** start at **Qwen2.5-0.5B-Instruct** or **Llama-3.2-1B-Instruct** (GGUF for llama.cpp inference; QLoRA 4-bit NF4 for training). Trains in <6 GB VRAM with batch=1 + grad-accum 4–8 + gradient checkpointing → fast nightly cycles, cheap rollback, most "infant-like." Gemma-2-2B / Phi-3-mini as scale-ups **only after the loop is stable**. No B200 needed. (Qwen2.5, Llama-3, Gemma-2, Phi-3 technical reports 2024 [peer-reviewed]; LoRA ICLR 2022 + QLoRA NeurIPS 2023 [peer-reviewed-top-tier].)

**Architecture = Complementary Learning Systems:** graph = fast hippocampal store (keep §1 running as the always-on fast learner); local core weights = slow neocortical store; nightly loop = consolidation. The graph remains ground truth if the core drifts.

**Data pipeline (most important recipe):** DO NOT finetune on raw triples. Use **EntiGraph-style synthetic expansion** (Yang et al., ICLR 2025 [peer-reviewed-top-tier]): each night sample high-activation entity subsets from PPR neighborhoods → prompt the core (or a teacher) to write DIVERSE natural-language passages about their relations, grounded in linked Experience nodes → **STaR-style filter** each passage by verifying claims against the graph → LoRA-SFT on survivors. Fixes one-shot sparsity and the reversal curse. (STaR, NeurIPS 2022 [peer-reviewed-top-tier].)

**Outer loop = ReST-EM, NOT PPO.** SEAL found PPO/GRPO unstable for exactly this setup; use rejection-sampling SFT (sample edits, keep only reward-positive, SFT). (SEAL, NeurIPS 2025 [peer-reviewed but 45 cites, ~1yr]; ReST-EM, TMLR 2023 [peer-reviewed] — warns rounds are NOT monotonically better, cap and validate each.)

**Reward = your held-out co-activation link-prediction lift**, computed ONLY on a truly future/unseen split. This makes it verifiable and effectively unhackable. Do NOT use the model as its own judge — a 0.5–2B core is too weak (Self-Rewarding LMs, ICML 2024 [peer-reviewed-top-tier]); the graph/environment is the judge.

**Anti-collapse:** every nightly batch = fresh synthetic passages + a persistent interleaved buffer of REAL Experience episodes (accumulate, never fully replace). (Shumailov et al. *Nature* 2024 collapse [peer-reviewed-top-tier]; Gerstgrasser et al. 2024 accumulation fix [peer-reviewed].)

**Anti-forgetting (two-pronged):** interleaved real replay + an anchor penalty toward the pre-sleep checkpoint (EWC Fisher-weighted L2 or KL-to-previous on a probe set). Prefer LoRA over full-FT — it "forgets less." (EWC, PNAS 2017 [peer-reviewed-top-tier]; LoRA Learns Less and Forgets Less, TMLR 2024 [peer-reviewed].)

**Plasticity safeguard:** contribution-utility running avg (decay 0.99) over LoRA columns; reinit lowest-utility fraction (start rate ~1e-5, maturity threshold, outgoing weights → 0) + weight decay on adapters. The neural twin of §1 homeostasis. (Continual Backprop / Dohare et al. *Nature* 2024 [peer-reviewed-top-tier].)

**Four mandatory gates before fusing any adapter:**
1. **Retention** — held-out prior-facts benchmark drops ≤ ε (~2–3% abs) vs pre-sleep checkpoint.
2. **Acquisition** — target episodes' link-prediction lift strictly increases.
3. **Collapse** — output diversity/perplexity on a fixed probe stays in band.
4. **Free-form recall** — model can RECALL injected facts in open generation, not merely recognize them in MCQ (documented recognition-vs-recall dissociation).

Fail any gate → discard adapter, roll back. Keep adapters UNMERGED during eval (rollback = drop adapter, instant). Narrow LR search — PoCs report a razor-thin window ~1e-5 to 2e-4 for small 4-bit models.

---

## 5. Honest risk register

**SOLID (peer-reviewed-top-tier, safe to build on):**
- STDP functional form, competitive Hebbian, synaptic scaling, BCM, three-factor rules, Rescorla-Wagner/RPE, predictive coding — all foundational, heavily replicated.
- Two-timescale stability requirement (Zenke & Gerstner) — a *proof*, not a heuristic: sleep-only homeostasis WILL let the graph blow up/collapse between sleeps.
- Continual backprop, model collapse, EWC, LoRA/QLoRA feasibility — all top-tier and directly applicable.
- Eval methodology (chronological split, filtered MRR, EdgeBank, hard negatives, prequential) — field-standard.

**SPECULATIVE / NOVEL (your contribution, unvalidated):**
- **STDP-on-a-symbolic-KG with day-scale timestamps** — NO peer-reviewed work does this. Only the functional form transfers; ms-scale biological params are meaningless here. All credibility rests on the tau-refit lift curve actually peaking. **The time-shuffle control is mandatory, not optional.**
- **PPR-spreading-activation = "the brain's prediction"** — your own construction, no paper validates it. The 7.86× is the only anchor and must be re-measured after every change under hard negatives (expect it to shrink substantially).
- **Within-experience co-activations have dt=0** → only symmetric potentiation. ALL directional signal comes from cross-experience ordering. **Verify the fraction of informative cross-experience ordered pairs before investing** — if most structure lives inside single experiences, the asymmetric part carries little signal, and it should be called "temporal-proximity gating," not STDP.

**EARLY-STAGE (directional, do not commit architecture to):**
- **SEAL** — NeurIPS 2025 but 45 cites, <1 yr. STaR (NeurIPS 2022, 971 cites) is the safer self-improvement reference.
- **All "sleep-distill into local-LLM-weights" systems** (Titans-adjacent 2026 preprints, "Sleeping LLM," Qwen2.5-7B SLEEP) — every one is an unrefereed 2026 preprint / PoC. Steal their engineering (spaced-repetition replay, benchmark-gate-then-fuse, narrow-LR search) but **run Phase 2 as an instrumented experiment with kill-switches, not a believed-correct design.**

**FIRST-PRINCIPLE TENSION (document explicitly):** learned embeddings, LoRA, DistMult, continual-backprop are ML optimization, not biologically literal — conflicts with "neuroscientific plausibility > code optimization." Decide and record where you accept the deviation.

**SCALE CAVEAT:** at 518 concepts / 2085 edges, learned embeddings (Gap 1) may overfit and not beat hand-tuned scalars until embodied ingestion (Gap 5) grows the stream by orders of magnitude. Gap 1's payoff is partly gated on Gap 5.

**CITATION GAPS to close:** semantic-scholar `get_paper` was rate-limited/circuit-broken during research — several exact citation counts (Frémaux & Gerstner 2016, Chaudhry NeurIPS 2023, GraIL, Poursafaei, HippoRAG) are unverified by magnitude (venue/year confirmed). HippoRAG venue entirely unverified. Re-run the cross-check before quoting citation numbers externally.

---

## 6. Recommended immediate next 3 actions (after the §1 plasticity rule lands)

1. **Build the honest evaluation harness FIRST — before trusting any rule gain.** Implement the §2 prequential test-then-train loop with time-aware filtered MRR, the EdgeBank baseline, hard negatives, and the Arm-A-vs-Arm-B matched-position control. Run the time-shuffle and data-freeze falsification controls. Deliverable: a plot of Arm B's advantage over Arm A at equal data, plus the tau-vs-lift curve. **If the time-shuffle advantage doesn't collapse and the tau curve doesn't peak, the STDP claim is dead and you rename the mechanism** — this decides everything downstream.

2. **Run the four ablations to attribute the gain** (against the honest baseline, not 7.86×): (a) symmetric additive [current] → (b) directional pair-STDP → (c) +triplet/BCM homeostasis → (d) +prediction-error gating. Separately measure **directional accuracy** (does `w_fwd > w_bwd` predict which concept came first?) — that is the specific new signal STDP buys that plain co-occurrence cannot. Wire the Gap-6 monitoring JSON (entropy, degree Gini, forgetting probe) so you can see collapse vs improvement.

3. **Prototype Gap 1 (the trainable head) as a Phase-1→Phase-2 bridge** — a 2-layer GNN / DistMult scorer over the graph, self-supervised on held-out co-activations, dropped in behind `measure_prediction.py`'s predictor interface. This is a genuine trainable core (backprop + loss) buildable this week WITHOUT swapping Gemini, and it de-risks the local-model swap while giving §1's prediction-error gate a *learned* `p_pred` instead of a raw PPR score.

---

Key files referenced: `scripts/baseline/measure_prediction.py` (predictor to replace), `neo4j_db.py` (`hebbian_update`, replay/consolidate write path), `conversation_handler` (Gemini interface for eventual local-core swap).