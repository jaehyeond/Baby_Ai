"""
ICDL 2026 Paper Figure Generator
Baby AI Ablation Study Analysis

Generates publication-ready figures from Supabase ablation data.
Usage: python scripts/generate_paper_figures.py [--output-dir path]

Requires: matplotlib, pandas, scipy, supabase
"""

import os
import sys
import argparse
import json
from pathlib import Path
from datetime import datetime

import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import pandas as pd
from scipy import stats
from supabase import create_client

# ─── Configuration ────────────────────────────────────────────────────────────

SUPABASE_URL = os.environ.get("NEXT_PUBLIC_SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

CONDITIONS = ['C_full', 'C_nostage', 'C_noemo', 'C_nosleep']
CONDITION_LABELS = {
    'C_full': 'Full System',
    'C_nostage': 'No Stage Gates',
    'C_noemo': 'No Emotion',
    'C_nosleep': 'No Sleep'
}
CONDITION_COLORS = {
    'C_full': '#2563eb',      # blue
    'C_nostage': '#16a34a',   # green
    'C_noemo': '#dc2626',     # red
    'C_nosleep': '#f59e0b',   # amber
}
CONDITION_MARKERS = {
    'C_full': 'o',
    'C_nostage': 's',
    'C_noemo': '^',
    'C_nosleep': 'D',
}

CDI_CATEGORIES = [
    'ACTION', 'ANIMAL', 'COGNITION', 'EMOTION', 'FOOD', 'LIFE',
    'NARRATIVE', 'NATURE', 'OBJECT', 'OTHER', 'PROPERTY', 'SCIENCE',
    'SENSE', 'SOCIAL', 'SPATIAL', 'TECHNOLOGY', 'TEMPORAL', 'TRANSPORT'
]

# Paper figure style
plt.rcParams.update({
    'font.family': 'serif',
    'font.size': 10,
    'axes.labelsize': 11,
    'axes.titlesize': 12,
    'legend.fontsize': 9,
    'xtick.labelsize': 9,
    'ytick.labelsize': 9,
    'figure.dpi': 300,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
    'lines.linewidth': 1.5,
})


# ─── Data Loading ─────────────────────────────────────────────────────────────

def load_data(supabase):
    """Load all ablation data from Supabase."""
    print("Loading data from Supabase...")

    # Ablation runs
    runs = supabase.table('ablation_runs').select('*').eq('status', 'completed').execute()
    df_runs = pd.DataFrame(runs.data)
    print(f"  Loaded {len(df_runs)} completed runs")

    # Ablation metrics (per-turn)
    run_ids = df_runs['id'].tolist()
    all_metrics = []
    for rid in run_ids:
        m = supabase.table('ablation_metrics').select('*').eq('run_id', rid).order('turn_number').execute()
        all_metrics.extend(m.data)
    df_metrics = pd.DataFrame(all_metrics)
    print(f"  Loaded {len(df_metrics)} metric rows")

    # Concepts with CDI-normalized categories (via the view)
    # Since views may not be accessible via REST API, load raw + normalize
    all_concepts = []
    for rid in run_ids:
        c = supabase.table('semantic_concepts').select(
            'id, name, category, strength, ablation_run_id'
        ).eq('ablation_run_id', rid).execute()
        all_concepts.extend(c.data)
    df_concepts = pd.DataFrame(all_concepts) if all_concepts else pd.DataFrame()
    print(f"  Loaded {len(df_concepts)} concepts")

    # Normalize categories
    if not df_concepts.empty:
        df_concepts['cdi_category'] = df_concepts['category'].apply(normalize_category)

    return df_runs, df_metrics, df_concepts


def normalize_category(cat):
    """Map Gemini's free-form categories to CDI-aligned super-categories."""
    if cat is None:
        return 'OTHER'
    mapping = {
        '감정': 'EMOTION', 'emotion': 'EMOTION', '감정표현': 'EMOTION',
        '행위': 'ACTION', '행동': 'ACTION', '동작': 'ACTION', '활동': 'ACTION', '운동': 'ACTION',
        '속성': 'PROPERTY', '상태': 'PROPERTY', '색깔': 'PROPERTY', '색상': 'PROPERTY',
        '동물': 'ANIMAL', '생물': 'ANIMAL', '생물학': 'ANIMAL',
        '자연': 'NATURE', '날씨': 'NATURE', '계절': 'NATURE', '천체': 'NATURE', '행성': 'NATURE',
        '도구': 'OBJECT', '사물': 'OBJECT', 'object': 'OBJECT', '장난감': 'OBJECT', '악기': 'OBJECT',
        '음식': 'FOOD', '과일': 'FOOD',
        '감각': 'SENSE', '소리': 'SENSE',
        '인지': 'COGNITION', '인지 활동': 'COGNITION', '정신 활동': 'COGNITION',
        '개념': 'COGNITION', '추상적 개념': 'COGNITION',
        '인사': 'SOCIAL', 'relationship': 'SOCIAL', 'person': 'SOCIAL',
        '역할': 'SOCIAL', '나이': 'SOCIAL', '국가': 'SOCIAL',
        '물리': 'SCIENCE', '수학 연산': 'SCIENCE', '에너지': 'SCIENCE',
        '힘': 'SCIENCE', '물질': 'SCIENCE',
        '장소': 'SPATIAL', '방향': 'SPATIAL', '도형': 'SPATIAL',
        '시간': 'TEMPORAL',
        '교통수단': 'TRANSPORT',
        '이야기': 'NARRATIVE', '경험': 'NARRATIVE', '사건': 'NARRATIVE', '결과': 'NARRATIVE',
        '인공지능': 'TECHNOLOGY', 'AI': 'TECHNOLOGY', '오류/작동_불능': 'TECHNOLOGY',
        '생명': 'LIFE', '생명 현상': 'LIFE',
    }
    return mapping.get(cat, 'OTHER')


# ─── Statistical Functions ────────────────────────────────────────────────────

def cliffs_delta(x, y):
    """Calculate Cliff's delta effect size."""
    n_x, n_y = len(x), len(y)
    if n_x == 0 or n_y == 0:
        return 0.0
    dominance = sum(
        (1 if xi > yi else -1 if xi < yi else 0)
        for xi in x for yi in y
    )
    return dominance / (n_x * n_y)


def cliffs_delta_interpretation(d):
    """Interpret Cliff's delta magnitude."""
    d = abs(d)
    if d < 0.147:
        return 'negligible'
    elif d < 0.33:
        return 'small'
    elif d < 0.474:
        return 'medium'
    else:
        return 'large'


def shannon_diversity(counts):
    """Calculate Shannon diversity index H'."""
    total = sum(counts)
    if total == 0:
        return 0.0
    proportions = [c / total for c in counts if c > 0]
    return -sum(p * np.log(p) for p in proportions)


def pielou_evenness(counts):
    """Calculate Pielou evenness J = H' / ln(S)."""
    h = shannon_diversity(counts)
    s = sum(1 for c in counts if c > 0)
    if s <= 1:
        return 0.0
    return h / np.log(s)


# ─── Figure Generators ────────────────────────────────────────────────────────

def fig3a_vocab_growth(df_runs, df_metrics, output_dir):
    """Fig 3a: Vocabulary growth curves (median ± IQR) for 4 conditions."""
    fig, ax = plt.subplots(figsize=(7, 4.5))

    for cond in CONDITIONS:
        cond_runs = df_runs[df_runs['condition'] == cond]['id'].tolist()
        if not cond_runs:
            continue

        cond_metrics = df_metrics[df_metrics['run_id'].isin(cond_runs)]
        grouped = cond_metrics.groupby('turn_number')['vocabulary_size']

        turns = sorted(cond_metrics['turn_number'].unique())
        medians = [grouped.get_group(t).median() if t in grouped.groups else 0 for t in turns]
        q1s = [grouped.get_group(t).quantile(0.25) if t in grouped.groups else 0 for t in turns]
        q3s = [grouped.get_group(t).quantile(0.75) if t in grouped.groups else 0 for t in turns]

        color = CONDITION_COLORS[cond]
        ax.plot(turns, medians, color=color, label=CONDITION_LABELS[cond],
                marker=CONDITION_MARKERS[cond], markevery=10, markersize=5)
        ax.fill_between(turns, q1s, q3s, alpha=0.15, color=color)

    ax.set_xlabel('Conversation Turn')
    ax.set_ylabel('Cumulative Vocabulary Size')
    ax.set_title('Vocabulary Growth Trajectories by Condition')
    ax.legend(loc='upper left', framealpha=0.9)
    ax.set_xlim(1, 60)
    ax.set_ylim(bottom=0)
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_locator(ticker.MultipleLocator(10))

    path = output_dir / 'fig3a_vocab_growth.png'
    fig.savefig(path)
    plt.close(fig)
    print(f"  Saved {path}")


def fig3b_final_vocab_bar(df_runs, output_dir):
    """Fig 3b: Final vocabulary bar chart with individual data points."""
    fig, ax = plt.subplots(figsize=(6, 4))

    positions = []
    for i, cond in enumerate(CONDITIONS):
        cond_data = df_runs[df_runs['condition'] == cond]['final_concept_count']
        if cond_data.empty:
            continue

        median = cond_data.median()
        q1, q3 = cond_data.quantile(0.25), cond_data.quantile(0.75)

        color = CONDITION_COLORS[cond]
        ax.bar(i, median, color=color, alpha=0.7, width=0.6, edgecolor='black', linewidth=0.5)
        ax.errorbar(i, median, yerr=[[median - q1], [q3 - median]],
                    color='black', capsize=5, linewidth=1.5)

        # Individual data points (jittered)
        jitter = np.random.uniform(-0.15, 0.15, len(cond_data))
        ax.scatter(i + jitter, cond_data.values, color=color, s=25,
                   edgecolors='black', linewidths=0.5, zorder=5, alpha=0.8)

        positions.append(i)

    ax.set_xticks(range(len(CONDITIONS)))
    ax.set_xticklabels([CONDITION_LABELS[c] for c in CONDITIONS], rotation=15, ha='right')
    ax.set_ylabel('Final Vocabulary Size (concepts)')
    ax.set_title('Final Vocabulary by Condition (median + IQR)')
    ax.set_ylim(bottom=0)
    ax.grid(True, axis='y', alpha=0.3)

    path = output_dir / 'fig3b_final_vocab_bar.png'
    fig.savefig(path)
    plt.close(fig)
    print(f"  Saved {path}")


def fig3c_me_trajectory(df_runs, df_metrics, output_dir):
    """Fig 3c: M(e) emotional modulator trajectory per condition."""
    fig, ax = plt.subplots(figsize=(7, 4))

    for cond in CONDITIONS:
        cond_runs = df_runs[df_runs['condition'] == cond]['id'].tolist()
        if not cond_runs:
            continue

        cond_metrics = df_metrics[df_metrics['run_id'].isin(cond_runs)]
        grouped = cond_metrics.groupby('turn_number')['emotional_modulator']

        turns = sorted(cond_metrics['turn_number'].unique())
        means = [grouped.get_group(t).mean() if t in grouped.groups else 1.0 for t in turns]

        color = CONDITION_COLORS[cond]
        ax.plot(turns, means, color=color, label=CONDITION_LABELS[cond],
                marker=CONDITION_MARKERS[cond], markevery=10, markersize=5)

    # Reference lines
    ax.axhline(y=1.0, color='gray', linestyle='--', alpha=0.5, label='Baseline (M=1.0)')
    ax.axhline(y=1.237, color='blue', linestyle=':', alpha=0.3, label='Peak (σ=0.3)')

    ax.set_xlabel('Conversation Turn')
    ax.set_ylabel('Emotional Modulator M(e)')
    ax.set_title('LC-NE Adaptive Gain: Emotional Modulation Over Time')
    ax.legend(loc='lower right', framealpha=0.9, fontsize=8)
    ax.set_xlim(1, 60)
    ax.set_ylim(0.9, 1.35)
    ax.grid(True, alpha=0.3)

    path = output_dir / 'fig3c_me_trajectory.png'
    fig.savefig(path)
    plt.close(fig)
    print(f"  Saved {path}")


def fig3d_cdi_comparison(df_runs, df_metrics, output_dir):
    """Fig 3d: Normalized trajectory overlay with CDI norms."""
    fig, ax = plt.subplots(figsize=(7, 4.5))

    # CDI norms (Fenson et al. 2007, Frank et al. 2017) - normalized
    # Age 8-30 months, vocab 0-680 words (CDI-K production)
    cdi_months = np.array([8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30])
    cdi_median = np.array([0, 1, 6, 14, 30, 64, 120, 185, 272, 350, 420, 480])
    cdi_norm_x = (cdi_months - 8) / (30 - 8)  # normalize to [0, 1]
    cdi_norm_y = cdi_median / cdi_median.max()  # normalize to [0, 1]

    ax.plot(cdi_norm_x, cdi_norm_y, 'k-', linewidth=2.5, label='CDI Norms (median)',
            alpha=0.8, zorder=10)

    # BabyBrain conditions — normalize each condition's median trajectory to [0,1]
    for cond in CONDITIONS:
        cond_runs = df_runs[df_runs['condition'] == cond]
        if cond_runs.empty:
            continue

        cond_ids = cond_runs['id'].tolist()
        cond_metrics = df_metrics[df_metrics['run_id'].isin(cond_ids)]

        grouped = cond_metrics.groupby('turn_number')['vocabulary_size']
        turns = sorted(cond_metrics['turn_number'].unique())
        medians = np.array([grouped.get_group(t).median() if t in grouped.groups else 0 for t in turns])

        # Normalize by the final median value (not max across all reps)
        final_median = medians[-1] if len(medians) > 0 else 1
        if final_median == 0:
            continue

        norm_x = np.array([(t - 1) / 59.0 for t in turns])
        norm_y = medians / final_median

        color = CONDITION_COLORS[cond]
        ax.plot(norm_x, norm_y, color=color, label=CONDITION_LABELS[cond],
                linestyle='--', alpha=0.7)

    ax.set_xlabel('Normalized Time [0, 1]')
    ax.set_ylabel('Normalized Vocabulary [0, 1]')
    ax.set_title('Trajectory Shape Comparison: BabyBrain vs CDI Norms')
    ax.legend(loc='upper left', framealpha=0.9, fontsize=8)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1.05)
    ax.grid(True, alpha=0.3)

    path = output_dir / 'fig3d_cdi_comparison.png'
    fig.savefig(path)
    plt.close(fig)
    print(f"  Saved {path}")


def fig4a_concept_strength(df_runs, df_concepts, output_dir):
    """Fig 4a: Concept strength distribution per condition (box plot)."""
    if df_concepts.empty:
        print("  Skipping fig4a: no concept data")
        return

    fig, ax = plt.subplots(figsize=(6, 4))

    data_by_cond = []
    labels = []
    colors = []

    for cond in CONDITIONS:
        cond_runs = df_runs[df_runs['condition'] == cond]['id'].tolist()
        cond_concepts = df_concepts[df_concepts['ablation_run_id'].isin(cond_runs)]
        if cond_concepts.empty:
            continue
        data_by_cond.append(cond_concepts['strength'].dropna().values)
        labels.append(CONDITION_LABELS[cond])
        colors.append(CONDITION_COLORS[cond])

    if not data_by_cond:
        print("  Skipping fig4a: no data")
        return

    bp = ax.boxplot(data_by_cond, tick_labels=labels, patch_artist=True, widths=0.6)
    for patch, color in zip(bp['boxes'], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.6)

    ax.set_ylabel('Concept Strength')
    ax.set_title('Concept Strength Distribution by Condition')
    ax.grid(True, axis='y', alpha=0.3)

    # Annotate expected values
    ax.axhline(y=0.6, color='blue', linestyle=':', alpha=0.3)
    ax.axhline(y=0.5, color='red', linestyle=':', alpha=0.3)
    ax.text(0.02, 0.61, 'M(e)≈1.2 → 0.60', transform=ax.get_yaxis_transform(),
            fontsize=7, color='blue', alpha=0.6)
    ax.text(0.02, 0.51, 'M(e)=1.0 → 0.50', transform=ax.get_yaxis_transform(),
            fontsize=7, color='red', alpha=0.6)

    path = output_dir / 'fig4a_concept_strength.png'
    fig.savefig(path)
    plt.close(fig)
    print(f"  Saved {path}")


def fig4b_shannon_diversity(df_runs, df_concepts, output_dir):
    """Fig 4b: Shannon diversity by condition with Pielou evenness."""
    if df_concepts.empty:
        print("  Skipping fig4b: no concept data")
        return

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))

    h_by_cond = {c: [] for c in CONDITIONS}
    j_by_cond = {c: [] for c in CONDITIONS}

    for cond in CONDITIONS:
        cond_runs = df_runs[df_runs['condition'] == cond]
        for _, run in cond_runs.iterrows():
            run_concepts = df_concepts[df_concepts['ablation_run_id'] == run['id']]
            if run_concepts.empty:
                continue
            cat_counts = run_concepts['cdi_category'].value_counts().values
            h_by_cond[cond].append(shannon_diversity(cat_counts))
            j_by_cond[cond].append(pielou_evenness(cat_counts))

    # Shannon H'
    for i, cond in enumerate(CONDITIONS):
        vals = h_by_cond[cond]
        if not vals:
            continue
        color = CONDITION_COLORS[cond]
        ax1.bar(i, np.median(vals), color=color, alpha=0.7, width=0.6,
                edgecolor='black', linewidth=0.5)
        jitter = np.random.uniform(-0.15, 0.15, len(vals))
        ax1.scatter(i + jitter, vals, color=color, s=20, edgecolors='black',
                    linewidths=0.5, zorder=5, alpha=0.8)

    ax1.set_xticks(range(len(CONDITIONS)))
    ax1.set_xticklabels([CONDITION_LABELS[c] for c in CONDITIONS], rotation=15, ha='right')
    ax1.set_ylabel("Shannon Diversity H'")
    ax1.set_title('Categorical Diversity')
    ax1.grid(True, axis='y', alpha=0.3)

    # Pielou J
    for i, cond in enumerate(CONDITIONS):
        vals = j_by_cond[cond]
        if not vals:
            continue
        color = CONDITION_COLORS[cond]
        ax2.bar(i, np.median(vals), color=color, alpha=0.7, width=0.6,
                edgecolor='black', linewidth=0.5)
        jitter = np.random.uniform(-0.15, 0.15, len(vals))
        ax2.scatter(i + jitter, vals, color=color, s=20, edgecolors='black',
                    linewidths=0.5, zorder=5, alpha=0.8)

    ax2.set_xticks(range(len(CONDITIONS)))
    ax2.set_xticklabels([CONDITION_LABELS[c] for c in CONDITIONS], rotation=15, ha='right')
    ax2.set_ylabel('Pielou Evenness J')
    ax2.set_title('Category Evenness')
    ax2.set_ylim(0, 1.1)
    ax2.grid(True, axis='y', alpha=0.3)

    fig.tight_layout()
    path = output_dir / 'fig4b_shannon_diversity.png'
    fig.savefig(path)
    plt.close(fig)
    print(f"  Saved {path}")


def fig5_category_distribution(df_runs, df_concepts, output_dir):
    """Fig 5: CDI-aligned category distribution per condition (stacked bar)."""
    if df_concepts.empty:
        print("  Skipping fig5: no concept data")
        return

    fig, ax = plt.subplots(figsize=(8, 5))

    # Build mean category counts per condition
    cond_cat_means = {}
    for cond in CONDITIONS:
        cond_runs = df_runs[df_runs['condition'] == cond]
        if cond_runs.empty:
            continue
        all_cat_counts = []
        for _, run in cond_runs.iterrows():
            run_concepts = df_concepts[df_concepts['ablation_run_id'] == run['id']]
            cat_counts = run_concepts['cdi_category'].value_counts()
            all_cat_counts.append(cat_counts)

        if all_cat_counts:
            combined = pd.DataFrame(all_cat_counts).fillna(0)
            cond_cat_means[cond] = combined.mean()

    if not cond_cat_means:
        print("  Skipping fig5: no data")
        return

    # Get top categories across all conditions
    all_cats = set()
    for means in cond_cat_means.values():
        all_cats.update(means.index)
    all_cats = sorted(all_cats)

    # Color palette for categories
    cat_cmap = plt.cm.Set3(np.linspace(0, 1, len(all_cats)))

    x = np.arange(len(cond_cat_means))
    width = 0.6
    bottom = np.zeros(len(cond_cat_means))

    conds = list(cond_cat_means.keys())

    for j, cat in enumerate(all_cats):
        values = [cond_cat_means[c].get(cat, 0) for c in conds]
        ax.bar(x, values, width, bottom=bottom, label=cat, color=cat_cmap[j],
               edgecolor='white', linewidth=0.5)
        bottom += values

    ax.set_xticks(x)
    ax.set_xticklabels([CONDITION_LABELS[c] for c in conds], rotation=15, ha='right')
    ax.set_ylabel('Mean Concept Count')
    ax.set_title('CDI-Aligned Category Distribution by Condition')
    ax.legend(bbox_to_anchor=(1.02, 1), loc='upper left', fontsize=7, ncol=2)

    fig.tight_layout()
    path = output_dir / 'fig5_category_distribution.png'
    fig.savefig(path)
    plt.close(fig)
    print(f"  Saved {path}")


# ─── Summary Table Generator ─────────────────────────────────────────────────

def generate_summary_table(df_runs, df_concepts, output_dir):
    """Generate Table 2: Primary results summary."""
    rows = []
    full_data = df_runs[df_runs['condition'] == 'C_full']['final_concept_count'].values

    for cond in CONDITIONS:
        cond_data = df_runs[df_runs['condition'] == cond]['final_concept_count']
        if cond_data.empty:
            continue

        values = cond_data.values
        n = len(values)
        median = np.median(values)
        q1, q3 = np.percentile(values, 25), np.percentile(values, 75)
        iqr = q3 - q1
        mean = np.mean(values)
        sd = np.std(values, ddof=1) if n > 1 else 0

        # Effect size vs C_full
        if cond != 'C_full' and len(full_data) > 0:
            delta = cliffs_delta(full_data, values)
            delta_interp = cliffs_delta_interpretation(delta)
            try:
                _, p_val = stats.mannwhitneyu(full_data, values, alternative='two-sided')
            except ValueError:
                p_val = 1.0
        else:
            delta = None
            delta_interp = '-'
            p_val = None

        rows.append({
            'Condition': CONDITION_LABELS[cond],
            'n': n,
            'Median': median,
            'IQR': f"{q1:.0f}-{q3:.0f}",
            'Mean': f"{mean:.1f}",
            'SD': f"{sd:.1f}",
            "Cliff's δ": f"{delta:.3f}" if delta is not None else '-',
            'Effect': delta_interp,
            'p-value': f"{p_val:.3f}" if p_val is not None else '-',
        })

    df_table = pd.DataFrame(rows)
    path = output_dir / 'table2_primary_results.csv'
    df_table.to_csv(path, index=False)
    print(f"  Saved {path}")
    print("\n  Table 2: Primary Results")
    print(df_table.to_string(index=False))

    return df_table


def generate_diversity_table(df_runs, df_concepts, output_dir):
    """Generate Table 3: Categorical diversity."""
    if df_concepts.empty:
        print("  Skipping diversity table: no concept data")
        return

    rows = []
    for cond in CONDITIONS:
        cond_runs = df_runs[df_runs['condition'] == cond]
        if cond_runs.empty:
            continue

        h_vals, j_vals, cat_counts = [], [], []
        for _, run in cond_runs.iterrows():
            run_concepts = df_concepts[df_concepts['ablation_run_id'] == run['id']]
            if run_concepts.empty:
                continue
            cc = run_concepts['cdi_category'].value_counts()
            h_vals.append(shannon_diversity(cc.values))
            j_vals.append(pielou_evenness(cc.values))
            cat_counts.append(len(cc))

        if not h_vals:
            continue

        # Top 3 categories
        all_concepts = df_concepts[df_concepts['ablation_run_id'].isin(cond_runs['id'])]
        top3 = all_concepts['cdi_category'].value_counts().head(3).index.tolist()

        rows.append({
            'Condition': CONDITION_LABELS[cond],
            'n': len(h_vals),
            'Categories (median)': f"{np.median(cat_counts):.0f}",
            "Shannon H' (median)": f"{np.median(h_vals):.3f}",
            'Pielou J (median)': f"{np.median(j_vals):.3f}",
            'Top-3 Categories': ', '.join(top3),
        })

    df_table = pd.DataFrame(rows)
    path = output_dir / 'table3_diversity.csv'
    df_table.to_csv(path, index=False)
    print(f"  Saved {path}")
    print("\n  Table 3: Categorical Diversity")
    print(df_table.to_string(index=False))


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Generate ICDL 2026 paper figures')
    parser.add_argument('--output-dir', type=str, default='docs/figures',
                        help='Output directory for figures')
    args = parser.parse_args()

    # Load env from .env.local if available
    env_path = Path(__file__).parent.parent / 'frontend' / 'baby-dashboard' / '.env.local'
    if env_path.exists():
        print(f"Loading env from {env_path}")
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, _, value = line.partition('=')
                os.environ.setdefault(key.strip(), value.strip())

    url = os.environ.get("NEXT_PUBLIC_SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "") or os.environ.get("NEXT_PUBLIC_SUPABASE_ANON_KEY", "")
    if not url or not key:
        print("ERROR: Set NEXT_PUBLIC_SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY (or NEXT_PUBLIC_SUPABASE_ANON_KEY)")
        sys.exit(1)

    supabase = create_client(url, key)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Output directory: {output_dir}")

    # Load data
    df_runs, df_metrics, df_concepts = load_data(supabase)

    if df_runs.empty:
        print("ERROR: No completed ablation runs found")
        sys.exit(1)

    print(f"\nCompleted runs by condition:")
    for cond in CONDITIONS:
        n = len(df_runs[df_runs['condition'] == cond])
        if n > 0:
            vocab = df_runs[df_runs['condition'] == cond]['final_concept_count']
            print(f"  {cond}: n={n}, median={vocab.median():.0f}, range=[{vocab.min()}, {vocab.max()}]")

    # Generate figures
    print("\nGenerating figures...")
    fig3a_vocab_growth(df_runs, df_metrics, output_dir)
    fig3b_final_vocab_bar(df_runs, output_dir)
    fig3c_me_trajectory(df_runs, df_metrics, output_dir)
    fig3d_cdi_comparison(df_runs, df_metrics, output_dir)
    fig4a_concept_strength(df_runs, df_concepts, output_dir)
    fig4b_shannon_diversity(df_runs, df_concepts, output_dir)
    fig5_category_distribution(df_runs, df_concepts, output_dir)

    # Generate tables
    print("\nGenerating tables...")
    generate_summary_table(df_runs, df_concepts, output_dir)
    generate_diversity_table(df_runs, df_concepts, output_dir)

    print(f"\nDone! {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"All outputs saved to {output_dir}/")


if __name__ == '__main__':
    main()
