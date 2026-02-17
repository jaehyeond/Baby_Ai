# ICDL 2026 Submission Roadmap: Agent Workflow & Deliverables
**Prepared**: 2026-02-11 | **For**: 4-Agent Team (Lead + brain-researcher + backend-dev + db-engineer)

---

## Executive Summary for Team Leads

**Goal**: Submit BabyBrain to ICDL 2026 (D-31: March 13, 2026) with 65-70% acceptance probability

**Critical Path Items** (no flexibility on timing):
1. C_raw baseline experiment (EXISTENTIAL)
2. Wordbank vocabulary comparison (EXISTENTIAL)
3. Code-paper formula alignment (credibility)

**Timeline**: 4 weeks (Feb 11 - Mar 13)

**Estimated Effort**:
- TIER 1 (critical): 16 hours (C_raw + Wordbank)
- TIER 2 (important): 12 hours (parameter taxonomy + alignment + sensitivity)
- TIER 3 (polish): 12 hours (emotion downstream + error patterns)
- Writing: 20 hours (Lead)
- **Total**: ~60 hours across 4 agents

---

## Week-by-Week Assignments

### WEEK 1 (Feb 11-16): Foundation & Setup

#### Lead's Role
- [ ] Confirm team commitment to 4-week sprint
- [ ] Assign roles (this document is the assignment)
- [ ] Create shared experiment log (Google Sheet or markdown)
- [ ] Decide: TIER 1 only vs. TIER 1+2 target
- **Deliverable by Feb 16**: Written confirmation of timeline + roles

#### brain-researcher's Role
- [ ] Review ICDL_REVIEWER_ASSESSMENT.md sections 1-3 (reviewer breakdown)
- [ ] Create literature-grounded parameter justifications document
  - Stage thresholds (10, 30, 70, 150): cite Piaget/developmental milestones
  - Decay factor (0.5): cite spreading activation literature
  - Emotion weights: cite Pekrun / Russell's Circumplex
- [ ] Prepare "Developmental Validity" section outline (1.5 pages)
- **Deliverable by Feb 16**: Parameter justifications doc + developmental section outline

#### backend-dev's Role
- [ ] Set up C_raw baseline harness:
  - [ ] Create `experiments/c_raw_baseline.py` script
  - [ ] Config: run bare Gemini on 100 conversations
  - [ ] Metrics: CAR, PA, EDI, AR, SSR (same as ablation study)
  - [ ] Output: CSV with per-conversation metrics
- [ ] Set up Wordbank data pipeline:
  - [ ] Install/test Wordbank API (`wordbank` Python library)
  - [ ] Extract vocabulary concepts from BabyBrain simulation log
  - [ ] Normalize to English receptive vocabulary (18-30 months)
- [ ] Code-formula alignment fix - START:
  - [ ] F2 (Spreading Activation): Compare `conversation-process.py` to PAPER_PLAN.md F2
  - [ ] Document any mismatches in `CODE_FORMULA_DISCREPANCIES.md`
- **Deliverable by Feb 16**: C_raw harness working, Wordbank pipeline code ready, discrepancies listed

#### db-engineer's Role
- [ ] Create experiment tracking tables (if not already done):
  - [ ] `experiment_runs` (experiment_id, condition, run_number, timestamp, status)
  - [ ] `ablation_metrics` (run_id, metric_name, value, timestamp)
  - [ ] `c_raw_metrics` (run_id, metric_name, value)
- [ ] Set up automated metric collection:
  - [ ] RPC function to log metrics per conversation
  - [ ] Ensure CAR, PA, EDI, AR, SSR are all tracked
- [ ] Create data export queries (for later analysis)
- **Deliverable by Feb 16**: DB schema ready + metric logging working + export queries written

---

### WEEK 2 (Feb 17-23): Critical Experiments + Writing Start

#### Lead's Role
- [ ] Start ICDL paper outline:
  - [ ] Abstract (100 words, tentative)
  - [ ] Introduction (1 page) - lead with question, not system
  - [ ] Bullet-point outline of all sections (helps team align)
- [ ] Monitor experiment progress (daily check-in)
- [ ] Begin literature review for Related Work section
- **Deliverable by Feb 23**: Paper outline + Introduction draft + 20+ literature sources

#### brain-researcher's Role
- [ ] Complete Developmental Validity section (draft):
  - [ ] Explain how each mechanism maps to developmental theory
  - [ ] 2-3 citations per mechanism justifying parameter choices
  - [ ] Explain what "stage-gating" means developmentally (Piaget reference)
  - [ ] Explain emotion-learning connection (Pekrun reference)
- [ ] Prepare "Related Work" section draft (1 page):
  - [ ] 2.1 Developmental AI (BabyAI, developmental robotics)
  - [ ] 2.2 Affective Computing in Learning (Picard, Pekrun, Russell)
  - [ ] 2.3 Cognitive Architecture (CoALA, ACT-R, SOAR)
  - [ ] 2.4 LLM+Development (BabyLM, CoALA, Generative Agents comparison)
- **Deliverable by Feb 23**: Related Work section draft + Developmental Validity section draft

#### backend-dev's Role
- [ ] **CRITICAL: Run full C_raw baseline**
  - [ ] 100 conversations with bare Gemini
  - [ ] Collect CAR, PA, EDI, AR, SSR metrics
  - [ ] Runtime: ~24 hours (parallelize if possible)
  - [ ] **Check result: Is BabyBrain > C_raw?** (If not, STOP and debug)
- [ ] **CRITICAL: Run Wordbank pipeline**
  - [ ] Extract concepts from 100 conversation simulation
  - [ ] Plot sigmoid curve vs. Wordbank norms
  - [ ] Compute correlation (target: r ≥ 0.75)
  - [ ] **Check result: Does curve match Wordbank?** (If not, investigate)
- [ ] Complete code-formula alignment:
  - [ ] Fix F2, F4, F7, F8 in code to match PAPER_PLAN.md formulas
  - [ ] Create `FORMULA_CORRECTIONS.md` documenting all fixes
  - [ ] Verify no logic changes, only documentation
- [ ] Run preliminary ablation (2 conditions × 1 replicate):
  - [ ] C_full vs. C_noemo (quick feasibility check)
- **Deliverable by Feb 23**: C_raw results + Wordbank plots + Code fixes + Ablation preliminary

#### db-engineer's Role
- [ ] Configure automated C_raw metric logging
- [ ] Create analysis queries:
  - [ ] Query 1: CAR comparison (BabyBrain vs C_raw)
  - [ ] Query 2: PA comparison
  - [ ] Query 3: Milestone timing comparison
- [ ] Export Wordbank data for visualization
- [ ] Create results summary SQL:
  - [ ] Mean ± SD for each metric per condition
  - [ ] Statistical test setup (ANOVA, t-test)
- [ ] Backup all experimental data to secondary location
- **Deliverable by Feb 23**: Analysis queries working + results summaries + backup complete

---

### WEEK 3 (Feb 24-Mar 2): Experiments Completion + Paper Writing

#### Lead's Role
- [ ] Full paper draft (aim for 6-8 pages):
  - [ ] Integrate Introduction + Related Work + Methods
  - [ ] Add results (C_raw + Wordbank + ablation)
  - [ ] Write Discussion section
  - [ ] Draft Conclusion
- [ ] Create all figures:
  - [ ] Fig 1: Architecture diagram (3 core mechanisms)
  - [ ] Fig 2: Wordbank comparison (sigmoid curves)
  - [ ] Fig 3: C_raw comparison (metric bars)
  - [ ] Fig 4: Ablation results (heat map or bars)
  - [ ] Fig 5: Strategy distribution (pie/bar chart)
  - [ ] Fig 6: Stage transition timeline
  - [ ] Fig 7: Emotion-strategy mapping (qualitative example)
  - [ ] Fig 8: Spreading activation example (optional)
- [ ] Create supplementary materials folder structure
- **Deliverable by Mar 2**: Full paper draft (6-8 pages) + all 8 figures

#### brain-researcher's Role
- [ ] Analyze ablation results:
  - [ ] For each ablation condition, explain WHY that component matters for development
  - [ ] "C_noemo reduces strategy diversity because..." (narrative interpretation)
  - [ ] "C_nostage eliminates milestone emergence because..." (etc.)
- [ ] Create Methods section (1 page):
  - [ ] C_raw baseline description
  - [ ] Ablation conditions (C_full, C_noemo, C_nostage, C_nospread, C_flat)
  - [ ] Metric definitions (CAR, PA, EDI, AR, RD, SSR)
  - [ ] Statistical analysis method
- [ ] Create Results section (1 page):
  - [ ] Summarize C_raw findings
  - [ ] Summarize Wordbank findings
  - [ ] Summarize ablation findings (table format)
- [ ] Review paper draft for developmental accuracy
- **Deliverable by Mar 2**: Methods section + Results section + Ablation narrative + Paper review

#### backend-dev's Role
- [ ] Complete full ablation study:
  - [ ] 5 conditions (C_full, C_noemo, C_nostage, C_nospread, C_flat)
  - [ ] 3 replicates per condition (15 total runs)
  - [ ] Collect all metrics
  - [ ] Verify statistical power (effect sizes)
- [ ] Generate ablation summary statistics:
  - [ ] Mean ± SD per condition
  - [ ] 95% CI for each metric
  - [ ] ANOVA or Kruskal-Wallis test results
  - [ ] Post-hoc pairwise comparisons (if significant)
- [ ] Sensitivity analysis (top 5 parameters):
  - [ ] For each parameter, vary ±10%, ±20%
  - [ ] Measure impact on 2-3 key metrics
  - [ ] Create sensitivity table
- [ ] Generate figure-ready data files (CSV)
- **Deliverable by Mar 2**: Full ablation results + sensitivity analysis + figure data + statistical tests

#### db-engineer's Role
- [ ] Create comprehensive results database:
  - [ ] All runs logged with condition, replicate, metrics
  - [ ] Timestamp, status, any errors
- [ ] Create statistical summary queries:
  - [ ] Mean/SD/CI per condition × metric
  - [ ] ANOVA F-values + p-values
  - [ ] Effect size calculations (Cohen's d)
- [ ] Prepare milestone timing analysis:
  - [ ] Extract stage transition timing from data
  - [ ] Compare to CDI milestone norms (if available)
- [ ] Export all results to research-ready formats
- [ ] Create data dictionary documenting all metrics
- **Deliverable by Mar 2**: Statistical summaries + milestone analysis + data exports + data dictionary

---

### WEEK 4 (Mar 3-7): Revision & Finalization

#### Lead's Role
- [ ] Self-review as skeptical ICDL reviewer:
  - [ ] Read paper as if you're Reviewer #1 (developmental psych)
  - [ ] Read as Reviewer #2 (computational modeler)
  - [ ] Read as Reviewer #3 (roboticist)
  - [ ] Note objections for each reviewer type
- [ ] Revise paper addressing anticipated objections:
  - [ ] Add Wordbank interpretation
  - [ ] Add parameter justification callouts
  - [ ] Add developmental theory citations
  - [ ] Add embodiment discussion
- [ ] Final polish:
  - [ ] Grammar/spelling check
  - [ ] Reference formatting
  - [ ] Figure captions
  - [ ] Supplementary materials compilation
- [ ] Create submission package:
  - [ ] Main paper (PDF, IEEE format, <8 pages)
  - [ ] Supplementary (parameter details, code, raw data)
  - [ ] References (bibtex)
- **Deliverable by Mar 7**: Final paper (revision 3) + supplementary package ready

#### brain-researcher's Role
- [ ] Create parameter justification supplementary:
  - [ ] Honest parameter taxonomy table (literature / empirical / design-choice)
  - [ ] For top 5 parameters, detailed justification
  - [ ] Literature citations for each justified parameter
- [ ] Verify all terminology is precise:
  - [ ] "Hebbian-inspired" not "Hebbian" ✓
  - [ ] "Semantic regions" not "brain regions" ✓
  - [ ] "Association strengthening" not "synaptic plasticity" ✓
- [ ] Create "Developmental Plausibility" supplementary section:
  - [ ] Explicit mapping of mechanisms to developmental psychology
  - [ ] Cited evidence from Piaget, Vygotsky, Erikson, etc.
- [ ] Final check: Does paper answer all 5 killer questions?
  - [ ] Q1: C_raw shows BabyBrain > baseline ✓
  - [ ] Q2: Parameters justified in parameter table ✓
  - [ ] Q3: Wordbank comparison shows developmental validity ✓
  - [ ] Q4: Ablation shows emergent behavior ✓
  - [ ] Q5: Terminology is precise ✓
- **Deliverable by Mar 7**: Parameter justification supplementary + terminology audit + killer-question checklist

#### backend-dev's Role
- [ ] Code supplementary:
  - [ ] Clean up experiment scripts
  - [ ] Create `run_all_experiments.sh` that reproduces all results
  - [ ] Document parameters and configuration
  - [ ] Verify reproducibility on sample data
- [ ] Create figure supplementary:
  - [ ] High-resolution versions of all 8 figures
  - [ ] Figure generation scripts (reproducible)
  - [ ] Data files for each figure
- [ ] Prepare code release:
  - [ ] Add docstrings to key functions
  - [ ] Create README with setup instructions
  - [ ] Ensure no hardcoded paths
- **Deliverable by Mar 7**: Code reproducibility verified + supplementary code clean + README + figures high-res

#### db-engineer's Role
- [ ] Create analysis supplementary:
  - [ ] Detailed statistical results (all ANOVA, t-tests, etc.)
  - [ ] Raw data tables (condition × replicate × metric)
  - [ ] Sensitivity analysis plots (±10%, ±20%)
- [ ] Final data backup:
  - [ ] All experiment results backed up
  - [ ] Version control all analysis scripts
  - [ ] Document database schema
- [ ] Create data availability statement:
  - [ ] "Code and data available at [URL]"
  - [ ] Specify what's public vs. private
- **Deliverable by Mar 7**: Statistical supplementary + data backup + data availability statement

---

### WEEK 5 (Mar 7-13): Submission

#### Lead's Role
- [ ] Final submission assembly:
  - [ ] Main paper (check format compliance: IEEE 2-column, <8 pages)
  - [ ] Supplementary materials (organized, clear naming)
  - [ ] References (complete, properly formatted)
  - [ ] Abstract (polished, 100-150 words)
- [ ] Compliance check:
  - [ ] Page limit? ✓
  - [ ] Author anonymity preserved? ✓
  - [ ] Citations complete? ✓
  - [ ] Figures legible? ✓
  - [ ] PDF not corrupted? ✓
- [ ] Generate final PDF
- [ ] Submit via [OpenReview/CMT/whatever ICDL uses for 2026]
- [ ] Confirm receipt email received
- **Deliverable by Mar 13**: Submitted paper + confirmation

---

## Role-Specific Checklists

### Lead's Checklist (Chief Scientist + Paper Writer)

**Overall**:
- [ ] Confirm team composition and commitment (Week 1)
- [ ] Define success criteria (65-70% probability, based on this document)
- [ ] Create shared experiment log (Week 1)

**Weeks 1-2**:
- [ ] Paper outline + Introduction draft
- [ ] Monitor experiment progress (daily)
- [ ] Make go/no-go decision on TIER 1 results (Week 2, Feb 23)

**Weeks 3-4**:
- [ ] Full paper draft (6-8 pages)
- [ ] All 8 figures
- [ ] Address anticipated objections
- [ ] Final revision

**Week 5**:
- [ ] Compliance check
- [ ] Submit

### brain-researcher's Checklist

**Week 1**:
- [ ] Review reviewer profiles (ICDL_REVIEWER_ASSESSMENT.md)
- [ ] Document parameter justifications
- [ ] Developmental Validity section outline

**Weeks 2-3**:
- [ ] Related Work section (draft → final)
- [ ] Methods section (draft → final)
- [ ] Ablation narrative interpretation
- [ ] Sensitivity analysis interpretation

**Week 4**:
- [ ] Parameter justification supplementary
- [ ] Terminology audit
- [ ] Killer-question checklist

### backend-dev's Checklist

**Week 1**:
- [ ] C_raw harness setup
- [ ] Wordbank pipeline code
- [ ] Code-formula alignment documentation

**Week 2**:
- [ ] Full C_raw baseline (100 conversations)
- [ ] Full Wordbank pipeline
- [ ] Code fixes (F2, F4, F7, F8)
- [ ] Preliminary ablation

**Week 3**:
- [ ] Full ablation (5 conditions × 3 replicates)
- [ ] Sensitivity analysis
- [ ] Figure data generation

**Week 4**:
- [ ] Code supplementary (clean, documented)
- [ ] Figure reproducibility
- [ ] README for reproduction

### db-engineer's Checklist

**Week 1**:
- [ ] Experiment tracking DB schema
- [ ] Metric logging infrastructure
- [ ] Export queries

**Week 2**:
- [ ] Automated metric logging verification
- [ ] Statistical analysis queries setup
- [ ] Results summary queries

**Week 3**:
- [ ] Statistical summaries (ANOVA, etc.)
- [ ] Milestone timing analysis
- [ ] Figure data exports

**Week 4**:
- [ ] Analysis supplementary (detailed stats)
- [ ] Data backup + version control
- [ ] Data availability statement

---

## Critical Decision Points

### Decision Point 1: C_raw Results (Week 2, Feb 23)
**Question**: Is BabyBrain > C_raw on ≥2 metrics?

**If YES** (expected):
- Continue to full ablation
- Proceed to TIER 2 work
- Confidence in submission increases to 55-60%

**If NO** (unexpected):
- STOP development, debug system
- Reconsider whether BabyBrain adds value
- Consider reframing as "exploration of mechanisms" not "improvement"
- May need to pivot strategy (arXiv preprint vs. conference submission)

### Decision Point 2: Wordbank Results (Week 2, Feb 23)
**Question**: Does curve match Wordbank norms (r ≥ 0.70)?

**If YES** (expected):
- Strong developmental validation signal
- Include as primary Figure 2
- Add to abstract
- Confidence increases to 55-60%

**If NO** (suboptimal but not fatal):
- Investigate: why doesn't natural vocabulary acquisition occur?
- Reframe: "Why do developmental mechanisms matter? We show..."
- Use as negative result (still publishable)
- Could become paper strength (unexpected finding)

### Decision Point 3: Ablation Results (Week 3, Mar 2)
**Question**: Does C_noemo or C_nostage significantly degrade metrics?

**If YES** (expected):
- Each mechanism clearly contributes
- Strong support for paper claims
- Allows confident discussion of emergent behavior

**If NO** (unexpected):
- Mechanisms are somewhat redundant
- Could argue for simpler model
- Still OK if C_raw was strong (mechanisms enable system beyond LLM capability)

### Decision Point 4: Timeline Slip (Ongoing)
**If falling behind schedule**:
- **Priority 1 (non-negotiable)**: C_raw + Wordbank (existential)
- **Priority 2 (important)**: Ablation + Code alignment (credibility)
- **Priority 3 (nice)**: Parameter taxonomy + Sensitivity + Emotion downstream
- **Fallback**: Submit TIER 1 only (55-60% probability) rather than miss deadline

---

## Team Communication Protocol

### Daily Standup (5 min, async preferred)
**Format**: Slack message with format:
```
[AGENT NAME] Daily Update [DATE]
- Yesterday: [2-3 bullet points]
- Today: [2-3 bullet points]
- Blockers: [if any]
- Decision needed: [if any]
```

### Weekly Sync (optional, only if needed)
- **Time**: [TBD, coordinate with team]
- **Attendees**: Lead + all agents (or by role)
- **Agenda**: Review deliverables, resolve blockers, confirm next week plan

### Result Escalation
- **Go/No-Go C_raw** (Feb 23, EOD): Lead notifies team if BabyBrain > C_raw
  - If NO: emergency meeting to decide path forward
  - If YES: proceed to full experiments

- **Go/No-Go Wordbank** (Feb 23, EOD): Lead notifies team if r ≥ 0.70
  - If NO: team discusses framing strategy
  - If YES: flag as major success

### Decision Documentation
- All major decisions documented in `ICDL_SUBMISSION_LOG.md`
- Include: decision date, rationale, decision maker, impact

---

## Success Metrics

### TIER 1 (Existential)
- [ ] C_raw baseline proves BabyBrain > bare LLM on ≥2 metrics
- [ ] Wordbank comparison shows sigmoid curve match (r ≥ 0.70)
- [ ] Code-formula alignment complete (no discrepancies)
- **Result if all pass**: 55-60% acceptance probability

### TIER 2 (Important)
- [ ] Full ablation shows each mechanism contributes (statistical significance)
- [ ] Parameter justification table shows >50% defended parameters
- [ ] Sensitivity analysis shows robustness (±20% parameter change → <5% metric degradation)
- **Result if above + TIER 1**: 65-70% acceptance probability

### TIER 3 (Polish)
- [ ] Emotion modulation applied downstream to learning rate
- [ ] Error pattern analysis shows overregularization-like errors
- [ ] Cross-environment robustness demonstrated
- **Result if all three tiers**: 70-75% acceptance probability

---

## Resource Allocation Summary

| Task | Agent | Hours | Week | Dependency |
|------|-------|-------|------|-----------|
| C_raw baseline | backend-dev | 12 | 2 | Code cleanup |
| Wordbank pipeline | backend-dev | 4 | 2 | DB export ready |
| Paper writing | Lead | 20 | 3-4 | Experiment results |
| Related Work | brain-researcher | 4 | 2 | Literature sources |
| Ablation analysis | brain-researcher | 4 | 3 | Ablation complete |
| Methods/Results | brain-researcher | 4 | 3 | Data ready |
| DB schema setup | db-engineer | 2 | 1 | Spec ready |
| Statistical analysis | db-engineer | 4 | 3 | Ablation data |
| Code supplementary | backend-dev | 2 | 4 | Cleanup complete |
| Parameter justification | brain-researcher | 3 | 4 | All parameters defined |
| Final revision | Lead | 4 | 4 | Draft complete |
| **TOTAL** | | **~63 hours** | | |

---

## Appendix: Quick Reference Commands

### C_raw Baseline
```bash
python experiments/c_raw_baseline.py \
  --num_conversations 100 \
  --model gemini-2.0-pro \
  --output results/c_raw_baseline.csv
```

### Wordbank Analysis
```bash
python analysis/wordbank_comparison.py \
  --simulation_log results/babybrain_simulation.log \
  --wordbank_api true \
  --output_plot results/wordbank_comparison.png
```

### Full Ablation
```bash
python experiments/run_ablation.py \
  --conditions all \
  --replicates 3 \
  --output_dir results/ablation_week3
```

### Statistical Summary
```sql
-- Query: Ablation results summary
SELECT condition, metric, ROUND(AVG(value), 3) as mean, ROUND(STDDEV(value), 3) as sd
FROM ablation_metrics
GROUP BY condition, metric
ORDER BY condition, metric;
```

---

**Document prepared**: 2026-02-11
**Status**: Ready for team distribution
**Next action**: Assign to team + confirm week 1 deliverables
