#!/usr/bin/env python3
"""
Mechanistic Analysis: WHY LLM Brand Preferences Arise (382K dataset)
====================================================================

Rerun of all 4 analyses on the CORRECT authoritative dataset:
  OSF/data/spec_resistance_CLEAN.csv (382K rows, 18 models, 77 columns)

Previous run used data/processed/spec_resistance_FULL.csv (148K rows).

Four analyses:
  1. Semantic contamination across specification levels
  2. Familiarity-stratified confabulation
  3. Anti-brand backfire mechanism
  4. Cross-model convergence on same wrong brand

All text analysis uses the `reasoning` column from the CSV directly
(no JSON loading needed). Brand decoding uses product_A_brand..product_E_brand
columns + choice column.

Writes: results/12-mechanistic-analysis/382k/
"""

import csv
import json
import os
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

import numpy as np
from scipy import stats

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT = Path(__file__).resolve().parent.parent.parent  # spec-resistance/
CSV_PATH = PROJECT / "OSF" / "data" / "spec_resistance_CLEAN.csv"
OUT_DIR = PROJECT / "nature-rr" / "results" / "12-mechanistic-analysis" / "382k"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Previous run results for comparison
PREV_JSON = PROJECT / "nature-rr" / "results" / "12-mechanistic-analysis" / "mechanistic_analysis_summary.json"

# ---------------------------------------------------------------------------
# Matplotlib setup -- Nature-quality
# ---------------------------------------------------------------------------
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

plt.rcParams.update({
    'font.family': 'sans-serif',
    'font.sans-serif': ['Arial', 'Helvetica', 'DejaVu Sans'],
    'font.size': 9,
    'axes.labelsize': 10,
    'axes.titlesize': 11,
    'xtick.labelsize': 8,
    'ytick.labelsize': 8,
    'legend.fontsize': 8,
    'figure.dpi': 300,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
    'axes.spines.top': False,
    'axes.spines.right': False,
    'axes.linewidth': 0.8,
    'xtick.major.width': 0.8,
    'ytick.major.width': 0.8,
})

NATURE_BLUE = '#0072B2'
NATURE_RED = '#D55E00'
NATURE_GREEN = '#009E73'
NATURE_PURPLE = '#7B2D8E'
NATURE_ORANGE = '#E69F00'
NATURE_GREY = '#999999'
NATURE_CYAN = '#56B4E9'
NATURE_PINK = '#CC79A7'


def save_fig(fig, name):
    """Save as both PNG and PDF."""
    fig.savefig(OUT_DIR / f"{name}.png", dpi=300, bbox_inches='tight')
    fig.savefig(OUT_DIR / f"{name}.pdf", bbox_inches='tight')
    plt.close(fig)
    print(f"  Saved {name}.png + .pdf")


# ---------------------------------------------------------------------------
# Load previous 148K results for comparison
# ---------------------------------------------------------------------------
prev_results = None
if PREV_JSON.exists():
    with open(PREV_JSON, encoding='utf-8') as f:
        prev_results = json.load(f)
    print(f"Loaded previous 148K results from {PREV_JSON.name}")


# ---------------------------------------------------------------------------
# Load CSV into memory
# ---------------------------------------------------------------------------
print(f"\nLoading CSV: {CSV_PATH}")
t0 = time.time()
rows = []
with open(CSV_PATH, encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for r in reader:
        rows.append(r)
elapsed = time.time() - t0
print(f"  Loaded {len(rows):,} rows in {elapsed:.1f}s")

# Quick stats
models = set(r['model_key'] for r in rows)
categories = set(r['category'] for r in rows)
conditions = set(r['condition'] for r in rows)
print(f"  Models: {len(models)}, Categories: {len(categories)}, Conditions: {len(conditions)}")


# ---------------------------------------------------------------------------
# Build brand familiarity lookup from CSV product columns
# ---------------------------------------------------------------------------
# We need a brand -> familiarity map. Build it from the data itself by using
# the assortment module (already available) for familiarity metadata.
sys.path.insert(0, str(PROJECT))
from experiment.assortments import ALL_ASSORTMENTS, CATEGORY_METADATA

BRAND_META = {}
for asm in ALL_ASSORTMENTS:
    for p in asm['products']:
        brand = p.get('brand', '')
        fam = p.get('brand_familiarity', '')
        BRAND_META[brand] = fam

HIGH_FAM_BRANDS = {b for b, f in BRAND_META.items() if f == 'high'}
MED_FAM_BRANDS = {b for b, f in BRAND_META.items() if f == 'medium'}
LOW_FAM_BRANDS = {b for b, f in BRAND_META.items() if f == 'low'}
print(f"  Brand familiarity: {len(HIGH_FAM_BRANDS)} high, {len(MED_FAM_BRANDS)} medium, {len(LOW_FAM_BRANDS)} low")


# ---------------------------------------------------------------------------
# Helper: decode chosen brand from CSV product columns
# ---------------------------------------------------------------------------
def decode_chosen_brand(row):
    """Get the brand name of the chosen product using product_X_brand columns."""
    choice = row.get('choice', '')
    if not choice or len(choice) != 1 or choice not in 'ABCDE':
        return None
    brand_col = f'product_{choice}_brand'
    return row.get(brand_col, None)


# ===========================================================================
# ANALYSIS 1: Semantic Contamination Across Specification Levels
# ===========================================================================
print("\n" + "="*70)
print("ANALYSIS 1: Semantic contamination -- why NL fails but utility succeeds")
print("="*70)

# Vocabulary lists
BRAND_ASSOC_TERMS = {
    *HIGH_FAM_BRANDS, *MED_FAM_BRANDS,
    'trusted', 'reliable', 'reputable', 'popular', 'well-known', 'renowned',
    'established', 'leading', 'premium', 'flagship', 'iconic', 'legacy',
    'brand', 'reputation', 'heritage', 'craftsmanship', 'engineering',
    'german engineering', 'italian', 'japanese', 'american',
    'industry-leading', 'market leader', 'top-tier',
}

SPEC_ASSOC_TERMS = {
    'higher', 'faster', 'more', 'better', 'longest', 'best',
    'score', 'rating', 'rated', 'specification', 'specs',
    'mah', 'ghz', 'gb', 'tb', 'watts', 'lumens', 'hz', 'db',
    'hours', 'minutes', 'inch', 'inches', 'mm', 'kg', 'lbs',
    'percent', 'percentage', 'ratio',
    'battery', 'processor', 'ram', 'storage', 'display', 'screen',
    'resolution', 'brightness', 'contrast', 'refresh rate',
    'noise cancellation', 'driver', 'impedance', 'frequency response',
    'weight', 'capacity', 'power', 'wattage', 'temperature',
    'speed', 'throughput', 'bandwidth', 'latency',
    'value', 'price', 'cost', 'affordable', 'budget',
    'utility', 'optimal', 'maximize', 'score',
}

SPEC_LEVELS = {
    'baseline': 0,
    'utility_vague': 1, 'preference_vague': 1,
    'utility_weighted': 2, 'preference_weighted': 2,
    'utility_explicit': 3, 'preference_explicit': 3,
    'utility_override': 4, 'preference_override': 4,
    'utility_constrained': 5, 'preference_constrained': 5,
}

SPEC_LEVEL_LABELS = {
    0: 'Baseline\n(none)',
    1: 'Vague',
    2: 'Weighted',
    3: 'Explicit',
    4: 'Override',
    5: 'Constrained',
}


def count_term_hits(text, term_set):
    """Count how many terms from term_set appear in text (case-insensitive)."""
    text_lower = text.lower()
    count = 0
    for term in term_set:
        if ' ' in term:
            if term.lower() in text_lower:
                count += 1
        else:
            if re.search(r'\b' + re.escape(term.lower()) + r'\b', text_lower):
                count += 1
    return count


def has_number(text):
    """Check if text contains numeric values."""
    return bool(re.search(r'\d+\.?\d*', text))


# Collect justification texts from CSV reasoning column, grouped by spec level
# Sample up to 500 per level per outcome for efficiency
print("  Collecting justification texts from CSV reasoning column...")
SAMPLES_PER_LEVEL = 500

justifications = defaultdict(lambda: {'nonopt': [], 'opt': []})

nonopt_count = Counter()
opt_count = Counter()

for r in rows:
    cond = r['condition']
    if cond not in SPEC_LEVELS:
        continue
    level = SPEC_LEVELS[cond]
    text = r.get('reasoning', '') or r.get('raw_response', '') or ''
    if len(text) < 20:
        continue

    is_opt = r['chose_optimal'] == 'True'
    if is_opt:
        if opt_count[level] < SAMPLES_PER_LEVEL:
            justifications[level]['opt'].append(text)
            opt_count[level] += 1
    else:
        if nonopt_count[level] < SAMPLES_PER_LEVEL:
            justifications[level]['nonopt'].append(text)
            nonopt_count[level] += 1

total_collected = sum(opt_count.values()) + sum(nonopt_count.values())
print(f"  Collected {total_collected:,} justification texts "
      f"({sum(nonopt_count.values())} non-opt, {sum(opt_count.values())} opt)")

# Compute vocabulary ratios by spec level
print("  Computing brand-vs-spec vocabulary ratios...")

analysis1_results = {}
for level in sorted(SPEC_LEVEL_LABELS.keys()):
    # Non-optimal
    nonopt_brand_counts = []
    nonopt_spec_counts = []
    nonopt_has_numbers = []
    for text in justifications[level]['nonopt']:
        bc = count_term_hits(text, BRAND_ASSOC_TERMS)
        sc = count_term_hits(text, SPEC_ASSOC_TERMS)
        nonopt_brand_counts.append(bc)
        nonopt_spec_counts.append(sc)
        nonopt_has_numbers.append(1 if has_number(text) else 0)

    # Optimal
    opt_brand_counts = []
    opt_spec_counts = []
    opt_has_numbers = []
    for text in justifications[level]['opt']:
        bc = count_term_hits(text, BRAND_ASSOC_TERMS)
        sc = count_term_hits(text, SPEC_ASSOC_TERMS)
        opt_brand_counts.append(bc)
        opt_spec_counts.append(sc)
        opt_has_numbers.append(1 if has_number(text) else 0)

    def ratio(brand_counts, spec_counts):
        ratios = []
        for b, s in zip(brand_counts, spec_counts):
            total = b + s
            if total > 0:
                ratios.append(b / total)
        return ratios

    nonopt_ratios = ratio(nonopt_brand_counts, nonopt_spec_counts)
    opt_ratios = ratio(opt_brand_counts, opt_spec_counts)

    analysis1_results[level] = {
        'label': SPEC_LEVEL_LABELS[level],
        'n_nonopt': len(nonopt_brand_counts),
        'n_opt': len(opt_brand_counts),
        'nonopt_brand_mean': float(np.mean(nonopt_brand_counts)) if nonopt_brand_counts else 0,
        'nonopt_spec_mean': float(np.mean(nonopt_spec_counts)) if nonopt_spec_counts else 0,
        'nonopt_ratio_mean': float(np.mean(nonopt_ratios)) if nonopt_ratios else 0,
        'nonopt_ratio_se': float(np.std(nonopt_ratios) / np.sqrt(len(nonopt_ratios))) if len(nonopt_ratios) > 1 else 0,
        'opt_brand_mean': float(np.mean(opt_brand_counts)) if opt_brand_counts else 0,
        'opt_spec_mean': float(np.mean(opt_spec_counts)) if opt_spec_counts else 0,
        'opt_ratio_mean': float(np.mean(opt_ratios)) if opt_ratios else 0,
        'opt_ratio_se': float(np.std(opt_ratios) / np.sqrt(len(opt_ratios))) if len(opt_ratios) > 1 else 0,
        'nonopt_numeric_pct': float(np.mean(nonopt_has_numbers) * 100) if nonopt_has_numbers else 0,
        'opt_numeric_pct': float(np.mean(opt_has_numbers) * 100) if opt_has_numbers else 0,
    }

    n_no = analysis1_results[level]['n_nonopt']
    n_o = analysis1_results[level]['n_opt']
    ratio_no = analysis1_results[level]['nonopt_ratio_mean']
    ratio_o = analysis1_results[level]['opt_ratio_mean']
    br_no = analysis1_results[level]['nonopt_brand_mean']
    sp_no = analysis1_results[level]['nonopt_spec_mean']
    print(f"  Level {level} ({SPEC_LEVEL_LABELS[level].strip()}): "
          f"non-opt n={n_no}, brand={br_no:.2f}, spec={sp_no:.2f}, "
          f"ratio={ratio_no:.3f} | opt ratio={ratio_o:.3f}")

# --- Figure 1: Semantic contamination ---
fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.5))

levels_sorted = sorted(analysis1_results.keys())
labels = [SPEC_LEVEL_LABELS[l].replace('\n', ' ') for l in levels_sorted]
x = np.arange(len(levels_sorted))

nonopt_means = [analysis1_results[l]['nonopt_ratio_mean'] for l in levels_sorted]
nonopt_ses = [analysis1_results[l]['nonopt_ratio_se'] for l in levels_sorted]
opt_means = [analysis1_results[l]['opt_ratio_mean'] for l in levels_sorted]
opt_ses = [analysis1_results[l]['opt_ratio_se'] for l in levels_sorted]

ax = axes[0]
width = 0.35
ax.bar(x - width/2, nonopt_means, width, yerr=nonopt_ses,
       color=NATURE_RED, alpha=0.85, label='Non-optimal choices',
       capsize=3, error_kw={'linewidth': 0.8})
ax.bar(x + width/2, opt_means, width, yerr=opt_ses,
       color=NATURE_BLUE, alpha=0.85, label='Optimal choices',
       capsize=3, error_kw={'linewidth': 0.8})
ax.set_ylabel('Brand-association ratio\n(brand / [brand + spec] terms)')
ax.set_xlabel('Specification level')
ax.set_xticks(x)
ax.set_xticklabels(labels, fontsize=7)
ax.legend(frameon=False, fontsize=7)
ax.set_title('a', fontweight='bold', loc='left', fontsize=12)
ax.set_ylim(0, None)

# Panel B: Term counts for non-optimal
nonopt_brand = [analysis1_results[l]['nonopt_brand_mean'] for l in levels_sorted]
nonopt_spec = [analysis1_results[l]['nonopt_spec_mean'] for l in levels_sorted]

ax = axes[1]
ax.plot(x, nonopt_brand, 'o-', color=NATURE_RED, label='Brand-associated terms',
        markersize=6, linewidth=1.5)
ax.plot(x, nonopt_spec, 's-', color=NATURE_BLUE, label='Spec-associated terms',
        markersize=6, linewidth=1.5)
ax.set_ylabel('Mean term count per justification')
ax.set_xlabel('Specification level')
ax.set_xticks(x)
ax.set_xticklabels(labels, fontsize=7)
ax.legend(frameon=False, fontsize=7)
ax.set_title('b', fontweight='bold', loc='left', fontsize=12)

plt.tight_layout()
save_fig(fig, 'fig1_semantic_contamination')


# ===========================================================================
# ANALYSIS 2: Familiarity-Stratified Confabulation
# ===========================================================================
print("\n" + "="*70)
print("ANALYSIS 2: Familiarity-stratified confabulation")
print("="*70)

fam_brand_reasoning = defaultdict(lambda: {'brand_yes': 0, 'brand_no': 0, 'total': 0})

for r in rows:
    if r['chose_optimal'] == 'True':
        continue
    fam = r.get('chosen_brand_familiarity', '')
    if fam not in ('high', 'medium'):
        continue

    judge_br = r.get('judge_brand_reasoning', '')
    if judge_br == 'True':
        fam_brand_reasoning[fam]['brand_yes'] += 1
    elif judge_br == 'False':
        fam_brand_reasoning[fam]['brand_no'] += 1
    fam_brand_reasoning[fam]['total'] += 1

print("\n  Explicit brand reasoning rates (non-optimal choices):")
for fam in ['high', 'medium']:
    d = fam_brand_reasoning[fam]
    total_judged = d['brand_yes'] + d['brand_no']
    rate = d['brand_yes'] / total_judged * 100 if total_judged > 0 else 0
    print(f"    {fam:>8s}: {d['brand_yes']}/{total_judged} = {rate:.1f}%  "
          f"(total non-opt: {d['total']})")

# Chi-squared test
high_d = fam_brand_reasoning['high']
med_d = fam_brand_reasoning['medium']
high_yes = high_d['brand_yes']
high_no = high_d['brand_no']
med_yes = med_d['brand_yes']
med_no = med_d['brand_no']

if high_yes + high_no > 0 and med_yes + med_no > 0:
    contingency = np.array([[high_yes, high_no], [med_yes, med_no]])
    a2_chi2, a2_p_val, a2_dof, a2_expected = stats.chi2_contingency(contingency)
    or_val = (high_yes * med_no) / (high_no * med_yes) if (high_no * med_yes) > 0 else float('inf')
    print(f"\n  Chi-squared: {a2_chi2:.2f}, p = {a2_p_val:.2e}")
    print(f"  Odds ratio (high/medium brand reasoning): {or_val:.2f}")
else:
    a2_chi2, a2_p_val, or_val = 0, 1, 1

# Attribute analysis from reasoning column
print("\n  Loading attribute analysis from reasoning column...")

ATTRIBUTE_CATEGORIES = {
    'quality_build': ['quality', 'build', 'durable', 'durability', 'construction',
                      'material', 'premium', 'solid', 'robust', 'well-built',
                      'craftsmanship', 'finish', 'design'],
    'performance': ['performance', 'powerful', 'fast', 'speed', 'processor',
                    'efficient', 'responsive'],
    'brand_reputation': ['brand', 'reputation', 'trusted', 'reliable', 'well-known',
                         'reputable', 'established', 'renowned', 'popular',
                         'industry', 'leader', 'heritage'],
    'value_price': ['value', 'price', 'affordable', 'budget', 'cost',
                    'money', 'expensive', 'cheap', 'deal'],
    'features': ['feature', 'features', 'technology', 'innovation', 'advanced',
                 'smart', 'connectivity', 'compatible'],
    'reviews_social': ['review', 'reviews', 'rated', 'rating', 'users',
                       'customers', 'recommended', 'favorite', 'popular'],
    'country_origin': ['german', 'japanese', 'italian', 'american', 'swiss',
                       'korean', 'european', 'engineering'],
}

fam_attr_counts = defaultdict(lambda: defaultdict(list))
ATTR_SAMPLE = 1000
fam_sample_count = Counter()

for r in rows:
    if r['chose_optimal'] == 'True':
        continue
    fam = r.get('chosen_brand_familiarity', '')
    if fam not in ('high', 'medium'):
        continue
    if fam_sample_count[fam] >= ATTR_SAMPLE:
        continue

    text = (r.get('reasoning', '') or r.get('raw_response', '') or '').lower()
    if len(text) < 20:
        continue

    for cat, terms in ATTRIBUTE_CATEGORIES.items():
        count = sum(1 for t in terms if re.search(r'\b' + re.escape(t) + r'\b', text))
        fam_attr_counts[fam][cat].append(count)
    fam_sample_count[fam] += 1

for fam in ['high', 'medium']:
    print(f"    Loaded {fam_sample_count[fam]} justifications for {fam}-fam")

# Compute mean attribute mentions
print("\n  Mean attribute mentions per justification (non-optimal):")
print(f"  {'Category':<20s} {'High-fam':>10s} {'Med-fam':>10s} {'Diff':>8s} {'p-value':>10s}")
print("  " + "-"*62)

attr_comparison = {}
for cat in ATTRIBUTE_CATEGORIES:
    high_vals = fam_attr_counts['high'].get(cat, [])
    med_vals = fam_attr_counts['medium'].get(cat, [])
    high_mean = float(np.mean(high_vals)) if high_vals else 0
    med_mean = float(np.mean(med_vals)) if med_vals else 0
    diff = high_mean - med_mean

    if len(high_vals) > 1 and len(med_vals) > 1:
        t_stat, p = stats.mannwhitneyu(high_vals, med_vals, alternative='two-sided')
    else:
        t_stat, p = 0, 1

    attr_comparison[cat] = {
        'high_mean': high_mean, 'med_mean': med_mean,
        'diff': diff, 'p': float(p),
        'high_n': len(high_vals), 'med_n': len(med_vals),
    }
    print(f"  {cat:<20s} {high_mean:>10.3f} {med_mean:>10.3f} {diff:>+8.3f} {p:>10.4f}")

# --- Figure 2: Familiarity-stratified confabulation ---
fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.5))

# Panel A: Brand reasoning rates
ax = axes[0]
fams = ['high', 'medium']
rates = []
ns = []
cis = []
for fam in fams:
    d = fam_brand_reasoning[fam]
    total_j = d['brand_yes'] + d['brand_no']
    rate = d['brand_yes'] / total_j if total_j > 0 else 0
    rates.append(rate * 100)
    ns.append(total_j)
    if total_j > 0:
        se = np.sqrt(rate * (1 - rate) / total_j)
        cis.append(1.96 * se * 100)
    else:
        cis.append(0)

bars = ax.bar(fams, rates, yerr=cis, color=[NATURE_RED, NATURE_ORANGE],
              alpha=0.85, capsize=5, error_kw={'linewidth': 0.8}, width=0.5)
for i, (bar, n) in enumerate(zip(bars, ns)):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + cis[i] + 0.5,
            f'n={n:,}', ha='center', va='bottom', fontsize=7)
ax.set_ylabel('Explicit brand reasoning (%)')
ax.set_xlabel('Chosen brand familiarity')
ax.set_title('a', fontweight='bold', loc='left', fontsize=12)

if a2_p_val < 0.001:
    sig_text = '***'
elif a2_p_val < 0.01:
    sig_text = '**'
elif a2_p_val < 0.05:
    sig_text = '*'
else:
    sig_text = 'n.s.'

max_y = max(r + c for r, c in zip(rates, cis))
bracket_y = max_y + 3
ax.plot([0, 0, 1, 1], [bracket_y - 1, bracket_y, bracket_y, bracket_y - 1],
        color='black', linewidth=0.8)
ax.text(0.5, bracket_y + 0.5, f'{sig_text}\nOR={or_val:.2f}',
        ha='center', va='bottom', fontsize=7)
ax.set_ylim(0, bracket_y + 8)

# Panel B: Attribute profile
ax = axes[1]
cats = list(ATTRIBUTE_CATEGORIES.keys())
cat_labels = [c.replace('_', '\n') for c in cats]
high_means = [attr_comparison[c]['high_mean'] for c in cats]
med_means = [attr_comparison[c]['med_mean'] for c in cats]

x = np.arange(len(cats))
width = 0.35
ax.barh(x - width/2, high_means, width, color=NATURE_RED, alpha=0.85, label='High-familiarity')
ax.barh(x + width/2, med_means, width, color=NATURE_ORANGE, alpha=0.85, label='Medium-familiarity')
ax.set_yticks(x)
ax.set_yticklabels(cat_labels, fontsize=7)
ax.set_xlabel('Mean mentions per justification')
ax.legend(frameon=False, fontsize=7, loc='lower right')
ax.set_title('b', fontweight='bold', loc='left', fontsize=12)

for i, cat in enumerate(cats):
    if attr_comparison[cat]['p'] < 0.05:
        max_val = max(attr_comparison[cat]['high_mean'], attr_comparison[cat]['med_mean'])
        ax.text(max_val + 0.02, i, '*', fontsize=10, va='center', color=NATURE_RED)

plt.tight_layout()
save_fig(fig, 'fig2_familiarity_confabulation')


# ===========================================================================
# ANALYSIS 3: Anti-Brand Backfire Mechanism
# ===========================================================================
print("\n" + "="*70)
print("ANALYSIS 3: Anti-brand backfire -- brand substitution patterns")
print("="*70)

ANTI_BRAND_CONDS = {
    'anti_brand_rejection', 'anti_brand_negative_experience', 'anti_brand_prefer_unknown'
}

cond_fam_dist = defaultdict(lambda: Counter())
cond_nonopt_rate = defaultdict(lambda: {'nonopt': 0, 'total': 0})

for r in rows:
    cond = r['condition']
    if cond not in ANTI_BRAND_CONDS and cond != 'baseline':
        continue

    cond_nonopt_rate[cond]['total'] += 1
    if r['chose_optimal'] == 'False':
        cond_nonopt_rate[cond]['nonopt'] += 1
        fam = r.get('chosen_brand_familiarity', 'unknown')
        cond_fam_dist[cond][fam] += 1

print("\n  Non-optimal rates and familiarity of chosen brand:")
print(f"  {'Condition':<35s} {'Non-opt %':>10s} {'High':>8s} {'Med':>8s} {'Low':>8s}")
print("  " + "-"*65)

anti_brand_summary = {}
for cond in ['baseline', 'anti_brand_rejection', 'anti_brand_negative_experience',
             'anti_brand_prefer_unknown']:
    d = cond_nonopt_rate[cond]
    rate = d['nonopt'] / d['total'] * 100 if d['total'] > 0 else 0
    total_nonopt = sum(cond_fam_dist[cond].values())

    fam_pcts = {}
    for fam in ['high', 'medium', 'low']:
        cnt = cond_fam_dist[cond].get(fam, 0)
        pct = cnt / total_nonopt * 100 if total_nonopt > 0 else 0
        fam_pcts[fam] = pct

    anti_brand_summary[cond] = {
        'nonopt_rate': rate,
        'n_total': d['total'],
        'n_nonopt': d['nonopt'],
        'high_pct': fam_pcts.get('high', 0),
        'medium_pct': fam_pcts.get('medium', 0),
        'low_pct': fam_pcts.get('low', 0),
    }

    print(f"  {cond:<35s} {rate:>9.1f}% {fam_pcts.get('high',0):>7.1f}% "
          f"{fam_pcts.get('medium',0):>7.1f}% {fam_pcts.get('low',0):>7.1f}%")

# Chi-squared tests
print("\n  Familiarity distribution tests (vs baseline):")
baseline_dist = cond_fam_dist['baseline']
baseline_total = sum(baseline_dist.values())

for cond in ['anti_brand_rejection', 'anti_brand_negative_experience']:
    cond_dist = cond_fam_dist[cond]
    cond_total = sum(cond_dist.values())
    if baseline_total > 0 and cond_total > 0:
        obs = np.array([
            [baseline_dist.get('high', 0), baseline_dist.get('medium', 0), baseline_dist.get('low', 0)],
            [cond_dist.get('high', 0), cond_dist.get('medium', 0), cond_dist.get('low', 0)],
        ])
        chi2, p, dof, exp = stats.chi2_contingency(obs)
        print(f"    {cond} vs baseline: chi2={chi2:.2f}, p={p:.2e}")

# Per-assortment substitution tracking
substitution_by_assortment = defaultdict(lambda: {'substitution_to_highfam': 0,
                                                    'substitution_to_medfam': 0,
                                                    'total_nonopt': 0})

for r in rows:
    cond = r['condition']
    if cond not in ('anti_brand_rejection', 'anti_brand_negative_experience'):
        continue
    if r['chose_optimal'] == 'True':
        continue

    aid = r['assortment_id']
    fam = r.get('chosen_brand_familiarity', '')
    substitution_by_assortment[aid]['total_nonopt'] += 1
    if fam == 'high':
        substitution_by_assortment[aid]['substitution_to_highfam'] += 1
    elif fam == 'medium':
        substitution_by_assortment[aid]['substitution_to_medfam'] += 1

sub_rates_high = []
for aid, d in substitution_by_assortment.items():
    if d['total_nonopt'] >= 5:
        rate = d['substitution_to_highfam'] / d['total_nonopt']
        sub_rates_high.append(rate)

if sub_rates_high:
    print(f"\n  Per-assortment substitution to high-fam brands in anti-brand conditions:")
    print(f"    Mean: {np.mean(sub_rates_high)*100:.1f}%, "
          f"Median: {np.median(sub_rates_high)*100:.1f}%, "
          f"n={len(sub_rates_high)} assortments")

# Decode actual brand names chosen
cond_decoded_brands = defaultdict(lambda: Counter())
for r in rows:
    cond = r['condition']
    if cond not in ANTI_BRAND_CONDS and cond != 'baseline':
        continue
    if r['chose_optimal'] == 'True':
        continue
    brand = decode_chosen_brand(r)
    if brand:
        cond_decoded_brands[cond][brand] += 1

print(f"\n  Top 10 non-optimal brand choices per condition:")
for cond in ['baseline', 'anti_brand_rejection', 'anti_brand_negative_experience']:
    print(f"\n    {cond}:")
    for brand, cnt in cond_decoded_brands[cond].most_common(10):
        fam = BRAND_META.get(brand, '?')
        print(f"      {brand:20s} ({fam:6s}): {cnt}")

# --- Figure 3: Anti-brand backfire ---
fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.5))

ax = axes[0]
conds_order = ['baseline', 'anti_brand_rejection', 'anti_brand_negative_experience',
               'anti_brand_prefer_unknown']
cond_labels_short = ['Baseline', 'Rejection', 'Negative\nexperience', 'Prefer\nunknown']
colors_a = [NATURE_GREY, NATURE_RED, NATURE_RED, NATURE_GREEN]

nonopt_rates_plot = [anti_brand_summary[c]['nonopt_rate'] for c in conds_order]
n_totals = [anti_brand_summary[c]['n_total'] for c in conds_order]

cis_a = []
for c in conds_order:
    d = anti_brand_summary[c]
    p_hat = d['nonopt_rate'] / 100
    se = np.sqrt(p_hat * (1 - p_hat) / d['n_total']) if d['n_total'] > 0 else 0
    cis_a.append(1.96 * se * 100)

bars = ax.bar(range(len(conds_order)), nonopt_rates_plot, yerr=cis_a,
              color=colors_a, alpha=0.85, capsize=4, error_kw={'linewidth': 0.8})
for i, (bar, n) in enumerate(zip(bars, n_totals)):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + cis_a[i] + 0.5,
            f'n={n:,}', ha='center', va='bottom', fontsize=6)
ax.set_ylabel('Non-optimal rate (%)')
ax.set_xticks(range(len(conds_order)))
ax.set_xticklabels(cond_labels_short, fontsize=7)
ax.set_title('a', fontweight='bold', loc='left', fontsize=12)
ax.axhline(y=nonopt_rates_plot[0], color=NATURE_GREY, linestyle='--',
           linewidth=0.8, alpha=0.5)

# Panel B: Familiarity composition
ax = axes[1]
conds_ab = ['baseline', 'anti_brand_rejection', 'anti_brand_negative_experience',
            'anti_brand_prefer_unknown']
labels_ab = ['Baseline', 'Rejection', 'Negative\nexperience', 'Prefer\nunknown']

high_pcts = [anti_brand_summary[c]['high_pct'] for c in conds_ab]
med_pcts = [anti_brand_summary[c]['medium_pct'] for c in conds_ab]
low_pcts = [anti_brand_summary[c]['low_pct'] for c in conds_ab]

x_ab = np.arange(len(conds_ab))
ax.bar(x_ab, high_pcts, color=NATURE_RED, alpha=0.85, label='High-familiarity')
ax.bar(x_ab, med_pcts, bottom=high_pcts, color=NATURE_ORANGE, alpha=0.85, label='Medium-familiarity')
bottom2 = [h + m for h, m in zip(high_pcts, med_pcts)]
ax.bar(x_ab, low_pcts, bottom=bottom2, color=NATURE_CYAN, alpha=0.85, label='Low-familiarity')

ax.set_ylabel('Share of non-optimal choices (%)')
ax.set_xticks(x_ab)
ax.set_xticklabels(labels_ab, fontsize=7)
ax.legend(frameon=False, fontsize=7, loc='upper right')
ax.set_title('b', fontweight='bold', loc='left', fontsize=12)
ax.set_ylim(0, 105)

plt.tight_layout()
save_fig(fig, 'fig3_anti_brand_backfire')


# ===========================================================================
# ANALYSIS 4: Cross-Model Convergence on Same Wrong Brand
# ===========================================================================
print("\n" + "="*70)
print("ANALYSIS 4: Cross-model convergence -- distributional mechanism test")
print("="*70)

# For baseline condition, for each assortment and model,
# identify which WRONG brand was chosen using product_X_brand columns.
assortment_model_choices = defaultdict(lambda: defaultdict(lambda: Counter()))

decoded_total = 0
for r in rows:
    if r['condition'] != 'baseline':
        continue
    if r['chose_optimal'] == 'True':
        continue
    aid = r['assortment_id']
    model = r['model_key']
    brand = decode_chosen_brand(r)
    if brand:
        assortment_model_choices[aid][model][brand] += 1
        decoded_total += 1

print(f"  Decoded {decoded_total:,} non-optimal brand choices across baseline trials")

# Per-assortment convergence
print("\n  Per-assortment cross-model convergence (baseline, non-optimal only):")
print(f"  {'Assortment':<30s} {'N models':>10s} {'Top brand':>20s} {'Share':>8s} {'Top2':>8s}")
print("  " + "-"*80)

convergence_data = []

for aid in sorted(assortment_model_choices.keys()):
    model_choices = assortment_model_choices[aid]
    model_top_brands = {}
    for model, brand_counter in model_choices.items():
        if brand_counter:
            top_brand = brand_counter.most_common(1)[0][0]
            model_top_brands[model] = top_brand

    if len(model_top_brands) < 3:
        continue

    top_brand_counter = Counter(model_top_brands.values())
    most_common_brand, most_common_count = top_brand_counter.most_common(1)[0]
    convergence_rate = most_common_count / len(model_top_brands)

    top2 = top_brand_counter.most_common(2)
    top2_count = sum(c for _, c in top2)
    top2_rate = top2_count / len(model_top_brands)

    cat_parts = aid.split('_')
    cat_name = '_'.join(cat_parts[1:-1]) if len(cat_parts) > 2 else aid

    convergence_data.append({
        'assortment_id': aid,
        'category': cat_name,
        'n_models': len(model_top_brands),
        'top_brand': most_common_brand,
        'top_brand_fam': BRAND_META.get(most_common_brand, '?'),
        'convergence_rate': convergence_rate,
        'top2_rate': top2_rate,
        'n_top_brand': most_common_count,
    })

    print(f"  {aid:<30s} {len(model_top_brands):>10d} {most_common_brand:>20s} "
          f"{convergence_rate:>7.1%} {top2_rate:>7.1%}")

# Category-level averages
cat_convergence = defaultdict(list)
for d in convergence_data:
    cat_convergence[d['category']].append(d['convergence_rate'])

print(f"\n  Category-level convergence rates:")
cat_conv_sorted = []
for cat, rates_list in sorted(cat_convergence.items(), key=lambda x: -np.mean(x[1])):
    mean_rate = float(np.mean(rates_list))
    se = float(np.std(rates_list) / np.sqrt(len(rates_list))) if len(rates_list) > 1 else 0
    cat_conv_sorted.append((cat, mean_rate, se, len(rates_list)))
    print(f"    {cat:<25s} {mean_rate:.1%} +/- {se:.1%}  (n={len(rates_list)} assortments)")

# 100% convergence assortments
full_conv = [d for d in convergence_data if d['convergence_rate'] >= 0.999]
print(f"\n  100% convergence assortments: {len(full_conv)}")
for d in full_conv:
    print(f"    {d['assortment_id']}: all {d['n_models']} models -> {d['top_brand']}")

# Category non-optimal rates for correlation
cat_nonopt_rates = defaultdict(lambda: {'nonopt': 0, 'total': 0})
for r in rows:
    if r['condition'] != 'baseline':
        continue
    cat = r['category']
    cat_nonopt_rates[cat]['total'] += 1
    if r['chose_optimal'] == 'False':
        cat_nonopt_rates[cat]['nonopt'] += 1

cat_nonopt_pcts = {}
for cat, d in cat_nonopt_rates.items():
    cat_nonopt_pcts[cat] = d['nonopt'] / d['total'] * 100 if d['total'] > 0 else 0

conv_rates_for_corr = []
nonopt_rates_for_corr = []
cat_names_for_corr = []
for cat, mean_rate, se, n in cat_conv_sorted:
    if cat in cat_nonopt_pcts:
        conv_rates_for_corr.append(mean_rate)
        nonopt_rates_for_corr.append(cat_nonopt_pcts[cat])
        cat_names_for_corr.append(cat)

r_conv = None
p_conv = None
if len(conv_rates_for_corr) > 3:
    r_conv, p_conv = stats.pearsonr(conv_rates_for_corr, nonopt_rates_for_corr)
    print(f"\n  Correlation (convergence vs non-optimal rate): r={r_conv:.3f}, p={p_conv:.4f}")

# --- Figure 4: Cross-model convergence ---
fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.5))

ax = axes[0]
if convergence_data:
    sorted_conv = sorted(convergence_data, key=lambda x: -x['convergence_rate'])
    y_vals = [d['convergence_rate'] * 100 for d in sorted_conv]

    unique_cats = sorted(set(d['category'] for d in sorted_conv))
    cat_color_map = {}
    palette = [NATURE_BLUE, NATURE_RED, NATURE_GREEN, NATURE_ORANGE, NATURE_PURPLE,
               NATURE_CYAN, NATURE_PINK, NATURE_GREY]
    for i, cat in enumerate(unique_cats):
        cat_color_map[cat] = palette[i % len(palette)]

    colors = [cat_color_map[d['category']] for d in sorted_conv]
    ax.barh(range(len(y_vals)), y_vals, color=colors, alpha=0.85)
    ax.set_xlabel('Cross-model convergence (%)')
    ax.set_ylabel('Assortment (sorted)')
    ax.set_yticks([])
    ax.axvline(x=25, color=NATURE_GREY, linestyle=':', linewidth=0.8)
    ax.set_xlim(0, 105)
    ax.set_title('a', fontweight='bold', loc='left', fontsize=12)
    ax.text(27, len(y_vals)*0.1, 'Chance\n(1/4 brands)', fontsize=7,
            color=NATURE_GREY, va='center')

ax = axes[1]
if len(conv_rates_for_corr) > 0:
    ax.scatter([r * 100 for r in conv_rates_for_corr], nonopt_rates_for_corr,
               s=60, color=NATURE_BLUE, alpha=0.8, edgecolors='white', linewidth=0.5)

    for i, cat in enumerate(cat_names_for_corr):
        label = cat.replace('_', ' ').title()
        ax.annotate(label, (conv_rates_for_corr[i] * 100, nonopt_rates_for_corr[i]),
                    fontsize=6, xytext=(5, 3), textcoords='offset points',
                    alpha=0.8)

    if r_conv is not None and len(conv_rates_for_corr) > 2:
        z = np.polyfit([r * 100 for r in conv_rates_for_corr], nonopt_rates_for_corr, 1)
        x_line = np.linspace(min(conv_rates_for_corr) * 100, max(conv_rates_for_corr) * 100, 100)
        ax.plot(x_line, np.polyval(z, x_line), '--', color=NATURE_RED, linewidth=1, alpha=0.7)
        ax.text(0.05, 0.95, f'r = {r_conv:.2f}\np = {p_conv:.3f}',
                transform=ax.transAxes, fontsize=8, va='top',
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

ax.set_xlabel('Cross-model convergence on same brand (%)')
ax.set_ylabel('Baseline non-optimal rate (%)')
ax.set_title('b', fontweight='bold', loc='left', fontsize=12)

plt.tight_layout()
save_fig(fig, 'fig4_cross_model_convergence')


# ===========================================================================
# Combined 4-panel figure
# ===========================================================================
print("\n" + "="*70)
print("Creating combined 4-panel figure...")
print("="*70)

fig, axes = plt.subplots(2, 2, figsize=(7.2, 7.0))

# Panel A: Semantic contamination
ax = axes[0, 0]
x = np.arange(len(levels_sorted))
labels_comb = [SPEC_LEVEL_LABELS[l].replace('\n', ' ') for l in levels_sorted]
nonopt_means = [analysis1_results[l]['nonopt_ratio_mean'] for l in levels_sorted]
nonopt_ses = [analysis1_results[l]['nonopt_ratio_se'] for l in levels_sorted]
opt_means = [analysis1_results[l]['opt_ratio_mean'] for l in levels_sorted]
opt_ses = [analysis1_results[l]['opt_ratio_se'] for l in levels_sorted]

width = 0.35
ax.bar(x - width/2, nonopt_means, width, yerr=nonopt_ses,
       color=NATURE_RED, alpha=0.85, label='Non-optimal', capsize=3,
       error_kw={'linewidth': 0.8})
ax.bar(x + width/2, opt_means, width, yerr=opt_ses,
       color=NATURE_BLUE, alpha=0.85, label='Optimal', capsize=3,
       error_kw={'linewidth': 0.8})
ax.set_ylabel('Brand-association ratio')
ax.set_xticks(x)
ax.set_xticklabels(labels_comb, fontsize=6.5, rotation=20)
ax.legend(frameon=False, fontsize=7)
ax.set_title('a  Semantic contamination', fontweight='bold', loc='left', fontsize=9)

# Panel B: Confabulation asymmetry
ax = axes[0, 1]
fams_b = ['high', 'medium']
rates_b = []
cis_b = []
for fam in fams_b:
    d = fam_brand_reasoning[fam]
    total_j = d['brand_yes'] + d['brand_no']
    rate = d['brand_yes'] / total_j * 100 if total_j > 0 else 0
    rates_b.append(rate)
    se = np.sqrt((rate/100) * (1 - rate/100) / total_j) * 100 if total_j > 0 else 0
    cis_b.append(1.96 * se)

bars = ax.bar(['High\nfamiliarity', 'Medium\nfamiliarity'], rates_b, yerr=cis_b,
              color=[NATURE_RED, NATURE_ORANGE], alpha=0.85, capsize=5,
              error_kw={'linewidth': 0.8}, width=0.45)
ax.set_ylabel('Explicit brand reasoning (%)')
ax.set_title('b  Confabulation asymmetry', fontweight='bold', loc='left', fontsize=9)

max_y_b = max(r + c for r, c in zip(rates_b, cis_b))
ax.plot([0, 0, 1, 1], [max_y_b + 1, max_y_b + 2, max_y_b + 2, max_y_b + 1],
        color='black', linewidth=0.8)
if a2_p_val < 0.001:
    p_text = f'p < 0.001\nOR = {or_val:.2f}'
else:
    p_text = f'p = {a2_p_val:.3f}\nOR = {or_val:.2f}'
ax.text(0.5, max_y_b + 2.5, p_text, ha='center', va='bottom', fontsize=7)
ax.set_ylim(0, max_y_b + 8)

# Panel C: Anti-brand substitution
ax = axes[1, 0]
conds_c = ['baseline', 'anti_brand_rejection', 'anti_brand_negative_experience',
           'anti_brand_prefer_unknown']
labels_c = ['Baseline', 'Rejection', 'Negative\nexperience', 'Prefer\nunknown']

high_pcts_c = [anti_brand_summary[c]['high_pct'] for c in conds_c]
med_pcts_c = [anti_brand_summary[c]['medium_pct'] for c in conds_c]
low_pcts_c = [anti_brand_summary[c]['low_pct'] for c in conds_c]

x_c = np.arange(len(conds_c))
ax.bar(x_c, high_pcts_c, color=NATURE_RED, alpha=0.85, label='High-fam')
ax.bar(x_c, med_pcts_c, bottom=high_pcts_c, color=NATURE_ORANGE, alpha=0.85, label='Med-fam')
bottom2_c = [h + m for h, m in zip(high_pcts_c, med_pcts_c)]
ax.bar(x_c, low_pcts_c, bottom=bottom2_c, color=NATURE_CYAN, alpha=0.85, label='Low-fam')
ax.set_ylabel('Share of non-optimal choices (%)')
ax.set_xticks(x_c)
ax.set_xticklabels(labels_c, fontsize=6.5)
ax.legend(frameon=False, fontsize=7, loc='upper right')
ax.set_title('c  Anti-brand substitution', fontweight='bold', loc='left', fontsize=9)
ax.set_ylim(0, 105)

for i, cond in enumerate(conds_c):
    rate = anti_brand_summary[cond]['nonopt_rate']
    ax.text(i, 102, f'{rate:.1f}%', ha='center', va='bottom', fontsize=7,
            fontweight='bold', color=NATURE_PURPLE)

# Panel D: Convergence
ax = axes[1, 1]
if len(conv_rates_for_corr) > 0:
    ax.scatter([r * 100 for r in conv_rates_for_corr], nonopt_rates_for_corr,
               s=50, color=NATURE_BLUE, alpha=0.8, edgecolors='white', linewidth=0.5)
    for i, cat in enumerate(cat_names_for_corr):
        label = cat.replace('_', ' ').title()
        if len(label) > 15:
            label = label[:13] + '..'
        ax.annotate(label, (conv_rates_for_corr[i] * 100, nonopt_rates_for_corr[i]),
                    fontsize=5.5, xytext=(4, 2), textcoords='offset points', alpha=0.8)

    if r_conv is not None and len(conv_rates_for_corr) > 2:
        z = np.polyfit([r * 100 for r in conv_rates_for_corr], nonopt_rates_for_corr, 1)
        x_line = np.linspace(min(conv_rates_for_corr) * 100, max(conv_rates_for_corr) * 100, 100)
        ax.plot(x_line, np.polyval(z, x_line), '--', color=NATURE_RED, linewidth=1, alpha=0.7)
        ax.text(0.05, 0.95, f'r = {r_conv:.2f}, p = {p_conv:.3f}',
                transform=ax.transAxes, fontsize=7, va='top',
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.8, edgecolor='none'))

ax.set_xlabel('Cross-model convergence (%)')
ax.set_ylabel('Non-optimal rate (%)')
ax.set_title('d  Distributional convergence', fontweight='bold', loc='left', fontsize=9)

plt.tight_layout(h_pad=1.5, w_pad=1.5)
save_fig(fig, 'fig_combined_mechanistic')


# ===========================================================================
# Save summary JSON
# ===========================================================================
print("\n" + "="*70)
print("Saving summary JSON...")
print("="*70)

summary = {
    'analysis_date': '2026-04-04',
    'data_source': str(CSV_PATH),
    'total_trials': len(rows),
    'n_models': len(models),
    'n_categories': len(categories),
    'n_conditions': len(conditions),
    'analysis_1_semantic_contamination': {
        'description': 'Brand-association vocabulary ratio across specification levels in justification texts',
        'hypothesis': 'Natural language activates the same distributional associations that encode brand preferences. Utility functions bypass this semantic space.',
        'results': {str(k): {
            'label': v['label'].strip() if isinstance(v['label'], str) else v['label'],
            'n_nonopt': v['n_nonopt'],
            'n_opt': v['n_opt'],
            'nonopt_brand_ratio': round(v['nonopt_ratio_mean'], 4),
            'opt_brand_ratio': round(v['opt_ratio_mean'], 4),
            'nonopt_brand_mean': round(v['nonopt_brand_mean'], 3),
            'nonopt_spec_mean': round(v['nonopt_spec_mean'], 3),
        } for k, v in analysis1_results.items()},
    },
    'analysis_2_familiarity_confabulation': {
        'description': 'Explicit brand reasoning rates by chosen brand familiarity tier',
        'hypothesis': 'High-fam brands have explicit brand-quality associations; models sometimes honestly cite brand. Mid-fam brands have associations but models lack the "brand is the reason" representation, so they confabulate.',
        'high_fam_brand_reasoning_pct': round(fam_brand_reasoning['high']['brand_yes'] / max(1, fam_brand_reasoning['high']['brand_yes'] + fam_brand_reasoning['high']['brand_no']) * 100, 2),
        'med_fam_brand_reasoning_pct': round(fam_brand_reasoning['medium']['brand_yes'] / max(1, fam_brand_reasoning['medium']['brand_yes'] + fam_brand_reasoning['medium']['brand_no']) * 100, 2),
        'high_fam_n_judged': high_yes + high_no,
        'med_fam_n_judged': med_yes + med_no,
        'chi2': round(float(a2_chi2), 3) if a2_chi2 else None,
        'p_value': float(a2_p_val) if a2_p_val else None,
        'odds_ratio': round(float(or_val), 3) if or_val != float('inf') else 'inf',
        'attribute_comparison': {k: {
            'high_mean': round(v['high_mean'], 4),
            'med_mean': round(v['med_mean'], 4),
            'diff': round(v['diff'], 4),
            'p': round(v['p'], 6),
        } for k, v in attr_comparison.items()},
    },
    'analysis_3_anti_brand_backfire': {
        'description': 'Brand substitution patterns in anti-brand conditions',
        'hypothesis': 'Rejection activates the rejected brand, increasing salience of similar alternatives. Models substitute one familiar brand for another.',
        'conditions': {k: {
            'nonopt_rate_pct': round(v['nonopt_rate'], 2),
            'n_total': v['n_total'],
            'n_nonopt': v['n_nonopt'],
            'high_fam_pct_of_nonopt': round(v['high_pct'], 2),
            'med_fam_pct_of_nonopt': round(v['medium_pct'], 2),
            'low_fam_pct_of_nonopt': round(v['low_pct'], 2),
        } for k, v in anti_brand_summary.items()},
        'substitution_to_highfam_mean': round(float(np.mean(sub_rates_high)) * 100, 2) if sub_rates_high else None,
    },
    'analysis_4_cross_model_convergence': {
        'description': 'Per-assortment convergence rate on the same non-optimal brand across models',
        'hypothesis': 'If mechanism is distributional, models trained on similar corpora should err on the same assortments and choose the same branded alternatives.',
        'n_assortments_analyzed': len(convergence_data),
        'mean_convergence_rate': round(float(np.mean([d['convergence_rate'] for d in convergence_data])) * 100, 2) if convergence_data else None,
        'median_convergence_rate': round(float(np.median([d['convergence_rate'] for d in convergence_data])) * 100, 2) if convergence_data else None,
        'full_convergence_assortments': len(full_conv),
        'per_assortment': [{
            'assortment_id': d['assortment_id'],
            'category': d['category'],
            'n_models': d['n_models'],
            'top_brand': d['top_brand'],
            'top_brand_fam': d['top_brand_fam'],
            'convergence_rate': round(d['convergence_rate'] * 100, 1),
        } for d in sorted(convergence_data, key=lambda x: -x['convergence_rate'])],
        'category_convergence': {cat: round(float(np.mean(rates_list)) * 100, 2) for cat, rates_list in cat_convergence.items()},
        'convergence_nonopt_correlation': {
            'r': round(float(r_conv), 4) if r_conv is not None else None,
            'p': round(float(p_conv), 6) if p_conv is not None else None,
        },
    },
}

json_path = OUT_DIR / "mechanistic_analysis_summary.json"
with open(json_path, 'w', encoding='utf-8') as f:
    json.dump(summary, f, indent=2, default=str)
print(f"  Saved {json_path}")


# ===========================================================================
# COMPARISON: 148K vs 382K
# ===========================================================================
print("\n" + "="*70)
print("COMPARISON: 148K (previous) vs 382K (current)")
print("="*70)

if prev_results:
    print(f"\n  Dataset size: {prev_results.get('total_trials', '?'):,} -> {len(rows):,}")

    # Analysis 1
    print("\n  --- Analysis 1: Semantic Contamination ---")
    prev_a1 = prev_results.get('analysis_1_semantic_contamination', {}).get('results', {})
    for level in ['0', '1', '2', '3', '4', '5']:
        prev_d = prev_a1.get(level, {})
        curr_d = analysis1_results.get(int(level), {})
        prev_ratio = prev_d.get('nonopt_brand_ratio', '?')
        curr_ratio = round(curr_d.get('nonopt_ratio_mean', 0), 4) if curr_d else '?'
        prev_n = prev_d.get('n_nonopt', '?')
        curr_n = curr_d.get('n_nonopt', '?') if curr_d else '?'
        label = curr_d.get('label', f'Level {level}').strip() if curr_d else f'Level {level}'
        print(f"    {label:<12s}: ratio {prev_ratio} -> {curr_ratio}  "
              f"(n_nonopt: {prev_n} -> {curr_n})")

    # Analysis 2
    print("\n  --- Analysis 2: Familiarity Confabulation ---")
    prev_a2 = prev_results.get('analysis_2_familiarity_confabulation', {})
    curr_high = summary['analysis_2_familiarity_confabulation']['high_fam_brand_reasoning_pct']
    curr_med = summary['analysis_2_familiarity_confabulation']['med_fam_brand_reasoning_pct']
    prev_high = prev_a2.get('high_fam_brand_reasoning_pct', '?')
    prev_med = prev_a2.get('med_fam_brand_reasoning_pct', '?')
    prev_or = prev_a2.get('odds_ratio', '?')
    curr_or = summary['analysis_2_familiarity_confabulation']['odds_ratio']
    print(f"    High-fam brand reasoning: {prev_high}% -> {curr_high}%")
    print(f"    Med-fam brand reasoning:  {prev_med}% -> {curr_med}%")
    print(f"    Odds ratio:               {prev_or} -> {curr_or}")
    print(f"    Chi2:                      {prev_a2.get('chi2', '?')} -> {summary['analysis_2_familiarity_confabulation']['chi2']}")

    # Analysis 3
    print("\n  --- Analysis 3: Anti-Brand Backfire ---")
    prev_a3 = prev_results.get('analysis_3_anti_brand_backfire', {}).get('conditions', {})
    curr_a3 = summary['analysis_3_anti_brand_backfire']['conditions']
    for cond in ['baseline', 'anti_brand_rejection', 'anti_brand_negative_experience', 'anti_brand_prefer_unknown']:
        prev_d = prev_a3.get(cond, {})
        curr_d = curr_a3.get(cond, {})
        prev_rate = prev_d.get('nonopt_rate_pct', '?')
        curr_rate = curr_d.get('nonopt_rate_pct', '?')
        prev_n = prev_d.get('n_total', '?')
        curr_n = curr_d.get('n_total', '?')
        prev_high = prev_d.get('high_fam_pct_of_nonopt', '?')
        curr_high = curr_d.get('high_fam_pct_of_nonopt', '?')
        cond_short = cond.replace('anti_brand_', 'ab_')
        print(f"    {cond_short:<25s}: rate {prev_rate}% -> {curr_rate}% "
              f"(n: {prev_n} -> {curr_n})  high-fam: {prev_high}% -> {curr_high}%")
    prev_sub = prev_results.get('analysis_3_anti_brand_backfire', {}).get('substitution_to_highfam_mean', '?')
    curr_sub = summary['analysis_3_anti_brand_backfire']['substitution_to_highfam_mean']
    print(f"    Substitution to high-fam:  {prev_sub}% -> {curr_sub}%")

    # Analysis 4
    print("\n  --- Analysis 4: Cross-Model Convergence ---")
    prev_a4 = prev_results.get('analysis_4_cross_model_convergence', {})
    curr_a4 = summary['analysis_4_cross_model_convergence']
    print(f"    N assortments:        {prev_a4.get('n_assortments_analyzed', '?')} -> {curr_a4['n_assortments_analyzed']}")
    print(f"    Mean convergence:     {prev_a4.get('mean_convergence_rate', '?')}% -> {curr_a4['mean_convergence_rate']}%")
    print(f"    Median convergence:   {prev_a4.get('median_convergence_rate', '?')}% -> {curr_a4['median_convergence_rate']}%")
    prev_corr = prev_a4.get('convergence_nonopt_correlation', {})
    curr_corr = curr_a4.get('convergence_nonopt_correlation', {})
    print(f"    Correlation r:        {prev_corr.get('r', '?')} -> {curr_corr.get('r', '?')}")
    print(f"    Correlation p:        {prev_corr.get('p', '?')} -> {curr_corr.get('p', '?')}")
    print(f"    100% convergence:     ? -> {curr_a4.get('full_convergence_assortments', 0)} assortments")

    # Category convergence comparison
    print("\n    Category convergence (148K -> 382K):")
    prev_cats = prev_a4.get('category_convergence', {})
    curr_cats = curr_a4.get('category_convergence', {})
    all_cats = sorted(set(list(prev_cats.keys()) + list(curr_cats.keys())))
    for cat in all_cats:
        prev_v = prev_cats.get(cat, '?')
        curr_v = curr_cats.get(cat, '?')
        print(f"      {cat:<25s}: {prev_v}% -> {curr_v}%")
else:
    print("  No previous 148K results found for comparison.")


# ===========================================================================
# Headline findings
# ===========================================================================
print("\n" + "="*70)
print("HEADLINE FINDINGS (382K dataset)")
print("="*70)

print("\n1. SEMANTIC CONTAMINATION:")
if 0 in analysis1_results and 3 in analysis1_results:
    baseline_ratio = analysis1_results[0]['nonopt_ratio_mean']
    explicit_ratio = analysis1_results[3]['nonopt_ratio_mean']
    print(f"   Brand-association ratio in non-optimal justifications:")
    print(f"   Baseline: {baseline_ratio:.3f} vs Explicit: {explicit_ratio:.3f}")
    if baseline_ratio > 0 and explicit_ratio > 0:
        print(f"   Ratio drops {((baseline_ratio - explicit_ratio) / baseline_ratio * 100):.1f}% "
              f"from baseline to explicit specification")

print("\n2. FAMILIARITY-STRATIFIED CONFABULATION:")
h_rate = fam_brand_reasoning['high']['brand_yes'] / max(1, fam_brand_reasoning['high']['brand_yes'] + fam_brand_reasoning['high']['brand_no']) * 100
m_rate = fam_brand_reasoning['medium']['brand_yes'] / max(1, fam_brand_reasoning['medium']['brand_yes'] + fam_brand_reasoning['medium']['brand_no']) * 100
print(f"   Explicit brand reasoning: high-fam={h_rate:.1f}% vs med-fam={m_rate:.1f}%")
print(f"   OR={or_val:.2f}, p={a2_p_val:.2e}")

print("\n3. ANTI-BRAND BACKFIRE:")
for cond in ['baseline', 'anti_brand_rejection', 'anti_brand_negative_experience']:
    d = anti_brand_summary[cond]
    print(f"   {cond}: {d['nonopt_rate']:.1f}% non-opt, "
          f"{d['high_pct']:.1f}% high-fam among errors")
if sub_rates_high:
    print(f"   Mean substitution to high-fam brands: {np.mean(sub_rates_high)*100:.1f}%")

print("\n4. CROSS-MODEL CONVERGENCE:")
if convergence_data:
    conv_rates_all = [d['convergence_rate'] for d in convergence_data]
    print(f"   Mean convergence: {np.mean(conv_rates_all)*100:.1f}%")
    print(f"   Median convergence: {np.median(conv_rates_all)*100:.1f}%")
    print(f"   100% convergence: {len(full_conv)} assortments")
    if r_conv is not None:
        print(f"   Convergence-nonoptimal correlation: r={r_conv:.3f}, p={p_conv:.4f}")
    top3 = sorted(convergence_data, key=lambda x: -x['convergence_rate'])[:3]
    for d in top3:
        print(f"   Top: {d['assortment_id']} -> {d['top_brand']} ({d['convergence_rate']:.0%} of models)")

print("\n" + "="*70)
print(f"DONE. All results saved to: {OUT_DIR}")
print("="*70)
