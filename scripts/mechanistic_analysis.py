#!/usr/bin/env python3
"""
Mechanistic Analysis: WHY LLM Brand Preferences Arise
=====================================================

Four analyses quantifying the mechanisms behind specification resistance:

1. Semantic contamination: Why natural language fails but utility functions succeed
   - Brand-associated vs spec-associated vocabulary across specification levels

2. Familiarity-stratified confabulation: Why mid-frequency brands trigger more confabulation
   - Explicit brand reasoning rates by familiarity tier
   - Attribute-type differences between high-fam and mid-fam non-optimal choices

3. Anti-brand backfire mechanism: Why rejection increases brand preference
   - Brand substitution patterns in anti-brand conditions
   - Familiarity of chosen brands in anti-brand vs baseline

4. Cross-model convergence: If distributional, models should err on the same items
   - Per-assortment convergence on same wrong brand
   - Category-level brand ecosystem strength vs convergence

Reads: data/processed/spec_resistance_FULL.csv (148K trials)
       data/raw/*.json (for justification text)
Writes: results/12-mechanistic-analysis/
"""

import csv
import json
import glob
import os
import re
import sys
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
CSV_PATH = PROJECT / "data" / "processed" / "spec_resistance_FULL.csv"
RAW_DIR = PROJECT / "data" / "raw"
OUT_DIR = PROJECT / "nature-rr" / "results" / "12-mechanistic-analysis"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Insert project root so we can import assortments
sys.path.insert(0, str(PROJECT))
from experiment.assortments import ALL_ASSORTMENTS, CATEGORY_METADATA

# ---------------------------------------------------------------------------
# Matplotlib setup — Nature-quality
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

# Nature colour palette (adapted from their style guidelines)
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
# Build brand metadata lookup from assortments
# ---------------------------------------------------------------------------
print("Loading brand metadata from assortments...")
BRAND_META = {}
ASSORTMENT_BRANDS = {}  # assortment_id -> {brand: {familiarity, is_optimal, ...}}
for asm in ALL_ASSORTMENTS:
    aid = asm['id']
    ASSORTMENT_BRANDS[aid] = {}
    for p in asm['products']:
        brand = p.get('brand', '')
        fam = p.get('brand_familiarity', '')
        is_opt = p.get('is_optimal', False)
        BRAND_META[brand] = fam
        ASSORTMENT_BRANDS[aid][brand] = {
            'familiarity': fam,
            'is_optimal': is_opt,
        }

# Build high-familiarity and medium-familiarity brand sets
HIGH_FAM_BRANDS = {b for b, f in BRAND_META.items() if f == 'high'}
MED_FAM_BRANDS = {b for b, f in BRAND_META.items() if f == 'medium'}
LOW_FAM_BRANDS = {b for b, f in BRAND_META.items() if f == 'low'}

print(f"  Brands: {len(HIGH_FAM_BRANDS)} high, {len(MED_FAM_BRANDS)} medium, {len(LOW_FAM_BRANDS)} low")

# Build assortment product index for reliable brand decoding
ASM_PRODUCTS = {}
for asm in ALL_ASSORTMENTS:
    ASM_PRODUCTS[asm['id']] = asm['products']


# ---------------------------------------------------------------------------
# Load CSV into memory
# ---------------------------------------------------------------------------
print("Loading CSV data...")
rows = []
with open(CSV_PATH, encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for r in reader:
        rows.append(r)
print(f"  Loaded {len(rows):,} rows")


# ---------------------------------------------------------------------------
# ANALYSIS 1: Semantic Contamination Across Specification Levels
# ---------------------------------------------------------------------------
print("\n" + "="*70)
print("ANALYSIS 1: Semantic contamination — why NL fails but utility succeeds")
print("="*70)

# Define vocabulary lists
BRAND_ASSOC_TERMS = {
    # Brand names (all real brands in the experiment)
    *HIGH_FAM_BRANDS, *MED_FAM_BRANDS,
    # Brand-associated quality language
    'trusted', 'reliable', 'reputable', 'popular', 'well-known', 'renowned',
    'established', 'leading', 'premium', 'flagship', 'iconic', 'legacy',
    'brand', 'reputation', 'heritage', 'craftsmanship', 'engineering',
    'german engineering', 'italian', 'japanese', 'american',
    'industry-leading', 'market leader', 'top-tier',
}

SPEC_ASSOC_TERMS = {
    # Numeric / quantitative terms
    'higher', 'faster', 'more', 'better', 'longest', 'best',
    'score', 'rating', 'rated', 'specification', 'specs',
    'mah', 'ghz', 'gb', 'tb', 'watts', 'lumens', 'hz', 'db',
    'hours', 'minutes', 'inch', 'inches', 'mm', 'kg', 'lbs',
    'percent', 'percentage', 'ratio',
    # Attribute names
    'battery', 'processor', 'ram', 'storage', 'display', 'screen',
    'resolution', 'brightness', 'contrast', 'refresh rate',
    'noise cancellation', 'driver', 'impedance', 'frequency response',
    'weight', 'capacity', 'power', 'wattage', 'temperature',
    'speed', 'throughput', 'bandwidth', 'latency',
    'value', 'price', 'cost', 'affordable', 'budget',
    'utility', 'optimal', 'maximize', 'score',
}

# Specification level mapping
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
        # Use word boundary matching for single words, substring for phrases
        if ' ' in term:
            if term.lower() in text_lower:
                count += 1
        else:
            # Match as whole word
            if re.search(r'\b' + re.escape(term.lower()) + r'\b', text_lower):
                count += 1
    return count


def has_number(text):
    """Check if text contains numeric values (specs are quantitative)."""
    return bool(re.search(r'\d+\.?\d*', text))


# We need justification text from raw JSON files for non-optimal choices
# across specification levels. Sample efficiently.
print("Loading justification texts from raw JSON files...")

# Build index of non-optimal trials by condition for spec gradient conditions
spec_gradient_conditions = set(SPEC_LEVELS.keys())

# Collect justification texts grouped by spec level
justifications_by_level = defaultdict(list)  # level -> [(text, chose_optimal), ...]
justifications_nonopt_by_level = defaultdict(list)  # level -> [text, ...]

# Process raw files matching spec gradient conditions
# For efficiency, use the CSV to identify non-optimal trials, then load their JSONs
print("  Indexing non-optimal trials by spec level...")
trial_spec_levels = {}
trial_optimality = {}
for r in rows:
    cond = r['condition']
    if cond in SPEC_LEVELS:
        trial_spec_levels[r['trial_id']] = SPEC_LEVELS[cond]
        trial_optimality[r['trial_id']] = r['chose_optimal'] == 'True'

# Sample: load up to 500 non-optimal justifications per level
SAMPLES_PER_LEVEL = 500
nonopt_count_by_level = Counter()
opt_count_by_level = Counter()

# Collect trial_ids to load
nonopt_trials_needed = defaultdict(list)
opt_trials_needed = defaultdict(list)
for tid, level in trial_spec_levels.items():
    if not trial_optimality[tid]:
        if nonopt_count_by_level[level] < SAMPLES_PER_LEVEL:
            nonopt_trials_needed[level].append(tid)
            nonopt_count_by_level[level] += 1
    else:
        if opt_count_by_level[level] < SAMPLES_PER_LEVEL:
            opt_trials_needed[level].append(tid)
            opt_count_by_level[level] += 1

print(f"  Loading {sum(len(v) for v in nonopt_trials_needed.values())} non-optimal + "
      f"{sum(len(v) for v in opt_trials_needed.values())} optimal justifications...")

# Build set of all trial IDs we need
all_needed_tids = set()
for tids in nonopt_trials_needed.values():
    all_needed_tids.update(tids)
for tids in opt_trials_needed.values():
    all_needed_tids.update(tids)

# Load from raw JSONs
loaded_texts = {}  # trial_id -> text
json_files = glob.glob(str(RAW_DIR / "specres_*.json"))
print(f"  Scanning {len(json_files):,} raw JSON files...")

# Build filename -> trial_id mapping from CSV for faster lookup
tid_to_file = {}
for r in rows:
    tid = r['trial_id']
    if tid in all_needed_tids:
        # trial_id IS the filename stem
        tid_to_file[tid] = RAW_DIR / f"{tid}.json"

loaded = 0
for tid, fpath in tid_to_file.items():
    if fpath.exists():
        try:
            with open(fpath, encoding='utf-8') as f:
                d = json.load(f)
            text = d.get('raw_response', '') or d.get('reasoning', '')
            if len(text) > 20:  # Skip near-empty responses
                loaded_texts[tid] = text
                loaded += 1
        except (json.JSONDecodeError, OSError):
            pass

print(f"  Loaded {loaded} justification texts")

# Compute vocabulary ratios by spec level
print("  Computing brand-vs-spec vocabulary ratios...")

analysis1_results = {}
for level in sorted(SPEC_LEVEL_LABELS.keys()):
    # Non-optimal
    nonopt_brand_counts = []
    nonopt_spec_counts = []
    nonopt_has_numbers = []
    for tid in nonopt_trials_needed.get(level, []):
        text = loaded_texts.get(tid, '')
        if text:
            bc = count_term_hits(text, BRAND_ASSOC_TERMS)
            sc = count_term_hits(text, SPEC_ASSOC_TERMS)
            nonopt_brand_counts.append(bc)
            nonopt_spec_counts.append(sc)
            nonopt_has_numbers.append(1 if has_number(text) else 0)

    # Optimal
    opt_brand_counts = []
    opt_spec_counts = []
    opt_has_numbers = []
    for tid in opt_trials_needed.get(level, []):
        text = loaded_texts.get(tid, '')
        if text:
            bc = count_term_hits(text, BRAND_ASSOC_TERMS)
            sc = count_term_hits(text, SPEC_ASSOC_TERMS)
            opt_brand_counts.append(bc)
            opt_spec_counts.append(sc)
            opt_has_numbers.append(1 if has_number(text) else 0)

    # Compute ratios (brand / (brand + spec)) to avoid division by zero
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
        'nonopt_brand_mean': np.mean(nonopt_brand_counts) if nonopt_brand_counts else 0,
        'nonopt_spec_mean': np.mean(nonopt_spec_counts) if nonopt_spec_counts else 0,
        'nonopt_ratio_mean': np.mean(nonopt_ratios) if nonopt_ratios else 0,
        'nonopt_ratio_se': np.std(nonopt_ratios) / np.sqrt(len(nonopt_ratios)) if len(nonopt_ratios) > 1 else 0,
        'opt_brand_mean': np.mean(opt_brand_counts) if opt_brand_counts else 0,
        'opt_spec_mean': np.mean(opt_spec_counts) if opt_spec_counts else 0,
        'opt_ratio_mean': np.mean(opt_ratios) if opt_ratios else 0,
        'opt_ratio_se': np.std(opt_ratios) / np.sqrt(len(opt_ratios)) if len(opt_ratios) > 1 else 0,
        'nonopt_numeric_pct': np.mean(nonopt_has_numbers) * 100 if nonopt_has_numbers else 0,
        'opt_numeric_pct': np.mean(opt_has_numbers) * 100 if opt_has_numbers else 0,
    }

    n_no = analysis1_results[level]['n_nonopt']
    n_o = analysis1_results[level]['n_opt']
    br_no = analysis1_results[level]['nonopt_brand_mean']
    sp_no = analysis1_results[level]['nonopt_spec_mean']
    ratio_no = analysis1_results[level]['nonopt_ratio_mean']
    ratio_o = analysis1_results[level]['opt_ratio_mean']
    print(f"  Level {level} ({SPEC_LEVEL_LABELS[level].strip()}): "
          f"non-opt n={n_no}, brand={br_no:.2f}, spec={sp_no:.2f}, "
          f"ratio={ratio_no:.3f} | opt ratio={ratio_o:.3f}")

# --- Figure 1: Semantic contamination across spec levels ---
fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.5))

levels_sorted = sorted(analysis1_results.keys())
labels = [SPEC_LEVEL_LABELS[l].replace('\n', ' ') for l in levels_sorted]
x = np.arange(len(levels_sorted))

# Panel A: Brand-association ratio for non-optimal vs optimal
nonopt_means = [analysis1_results[l]['nonopt_ratio_mean'] for l in levels_sorted]
nonopt_ses = [analysis1_results[l]['nonopt_ratio_se'] for l in levels_sorted]
opt_means = [analysis1_results[l]['opt_ratio_mean'] for l in levels_sorted]
opt_ses = [analysis1_results[l]['opt_ratio_se'] for l in levels_sorted]

ax = axes[0]
width = 0.35
bars1 = ax.bar(x - width/2, nonopt_means, width, yerr=nonopt_ses,
               color=NATURE_RED, alpha=0.85, label='Non-optimal choices',
               capsize=3, error_kw={'linewidth': 0.8})
bars2 = ax.bar(x + width/2, opt_means, width, yerr=opt_ses,
               color=NATURE_BLUE, alpha=0.85, label='Optimal choices',
               capsize=3, error_kw={'linewidth': 0.8})
ax.set_ylabel('Brand-association ratio\n(brand / [brand + spec] terms)')
ax.set_xlabel('Specification level')
ax.set_xticks(x)
ax.set_xticklabels(labels, fontsize=7)
ax.legend(frameon=False, fontsize=7)
ax.set_title('a', fontweight='bold', loc='left', fontsize=12)
ax.set_ylim(0, None)

# Panel B: Mean brand term count and spec term count for non-optimal
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


# ---------------------------------------------------------------------------
# ANALYSIS 2: Familiarity-Stratified Confabulation
# ---------------------------------------------------------------------------
print("\n" + "="*70)
print("ANALYSIS 2: Familiarity-stratified confabulation")
print("="*70)

# For non-optimal choices, compare brand_reasoning rates by familiarity
fam_brand_reasoning = defaultdict(lambda: {'brand_yes': 0, 'brand_no': 0, 'total': 0})
fam_attributes = defaultdict(lambda: Counter())  # familiarity -> Counter of attribute mentions

# Also track which specific brands are chosen
brand_choice_counts = defaultdict(lambda: Counter())  # familiarity -> Counter of brand names

for r in rows:
    if r['chose_optimal'] == 'True':
        continue
    fam = r.get('chosen_brand_familiarity', '')
    if fam not in ('high', 'medium'):
        continue

    # Brand reasoning (judge verdict)
    judge_br = r.get('judge_brand_reasoning', '')
    if judge_br == 'True':
        fam_brand_reasoning[fam]['brand_yes'] += 1
    elif judge_br == 'False':
        fam_brand_reasoning[fam]['brand_no'] += 1
    fam_brand_reasoning[fam]['total'] += 1

# Compute explicit brand reasoning rates
print("\n  Explicit brand reasoning rates (non-optimal choices):")
for fam in ['high', 'medium']:
    d = fam_brand_reasoning[fam]
    total_judged = d['brand_yes'] + d['brand_no']
    rate = d['brand_yes'] / total_judged * 100 if total_judged > 0 else 0
    print(f"    {fam:>8s}: {d['brand_yes']}/{total_judged} = {rate:.1f}%  "
          f"(total non-opt: {d['total']})")

# Statistical test: chi-squared for brand reasoning by familiarity
high_d = fam_brand_reasoning['high']
med_d = fam_brand_reasoning['medium']
high_yes = high_d['brand_yes']
high_no = high_d['brand_no']
med_yes = med_d['brand_yes']
med_no = med_d['brand_no']

if high_yes + high_no > 0 and med_yes + med_no > 0:
    contingency = np.array([[high_yes, high_no], [med_yes, med_no]])
    a2_chi2, a2_p_val, a2_dof, a2_expected = stats.chi2_contingency(contingency)
    # Odds ratio
    or_val = (high_yes * med_no) / (high_no * med_yes) if (high_no * med_yes) > 0 else float('inf')
    print(f"\n  Chi-squared: {a2_chi2:.2f}, p = {a2_p_val:.2e}")
    print(f"  Odds ratio (high/medium brand reasoning): {or_val:.2f}")
else:
    a2_chi2, a2_p_val, or_val = 0, 1, 1

# Now load attribute mentions from justification texts
# For high-fam vs mid-fam non-optimal, what attributes are cited?
print("\n  Loading attribute analysis from justification texts...")

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

fam_attr_counts = defaultdict(lambda: defaultdict(list))  # fam -> attr_cat -> [counts per trial]

# Load a sample of non-optimal trials per familiarity
ATTR_SAMPLE = 1000
fam_trial_ids = defaultdict(list)
for r in rows:
    if r['chose_optimal'] == 'True':
        continue
    fam = r.get('chosen_brand_familiarity', '')
    if fam in ('high', 'medium') and len(fam_trial_ids[fam]) < ATTR_SAMPLE:
        fam_trial_ids[fam].append(r['trial_id'])

for fam in ['high', 'medium']:
    loaded_count = 0
    for tid in fam_trial_ids[fam]:
        fpath = RAW_DIR / f"{tid}.json"
        if fpath.exists():
            try:
                with open(fpath, encoding='utf-8') as f:
                    d = json.load(f)
                text = (d.get('raw_response', '') or d.get('reasoning', '')).lower()
                if len(text) > 20:
                    for cat, terms in ATTRIBUTE_CATEGORIES.items():
                        count = sum(1 for t in terms if re.search(r'\b' + re.escape(t) + r'\b', text))
                        fam_attr_counts[fam][cat].append(count)
                    loaded_count += 1
            except (json.JSONDecodeError, OSError):
                pass
    print(f"    Loaded {loaded_count} justifications for {fam}-fam")

# Compute mean attribute mentions
print("\n  Mean attribute mentions per justification (non-optimal):")
print(f"  {'Category':<20s} {'High-fam':>10s} {'Med-fam':>10s} {'Diff':>8s} {'p-value':>10s}")
print("  " + "-"*62)

attr_comparison = {}
for cat in ATTRIBUTE_CATEGORIES:
    high_vals = fam_attr_counts['high'].get(cat, [])
    med_vals = fam_attr_counts['medium'].get(cat, [])
    high_mean = np.mean(high_vals) if high_vals else 0
    med_mean = np.mean(med_vals) if med_vals else 0
    diff = high_mean - med_mean

    if len(high_vals) > 1 and len(med_vals) > 1:
        t_stat, p = stats.mannwhitneyu(high_vals, med_vals, alternative='two-sided')
    else:
        t_stat, p = 0, 1

    attr_comparison[cat] = {
        'high_mean': high_mean, 'med_mean': med_mean,
        'diff': diff, 'p': p,
        'high_n': len(high_vals), 'med_n': len(med_vals),
    }
    print(f"  {cat:<20s} {high_mean:>10.3f} {med_mean:>10.3f} {diff:>+8.3f} {p:>10.4f}")

# --- Figure 2: Familiarity-stratified confabulation ---
fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.5))

# Panel A: Brand reasoning rates by familiarity
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
    # Wilson confidence interval
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

# Add significance bracket
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

# Panel B: Attribute profile comparison
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

# Mark significant differences
for i, cat in enumerate(cats):
    if attr_comparison[cat]['p'] < 0.05:
        max_val = max(attr_comparison[cat]['high_mean'], attr_comparison[cat]['med_mean'])
        ax.text(max_val + 0.02, i, '*', fontsize=10, va='center', color=NATURE_RED)

plt.tight_layout()
save_fig(fig, 'fig2_familiarity_confabulation')


# ---------------------------------------------------------------------------
# ANALYSIS 3: Anti-Brand Backfire Mechanism
# ---------------------------------------------------------------------------
print("\n" + "="*70)
print("ANALYSIS 3: Anti-brand backfire — brand substitution patterns")
print("="*70)

# Anti-brand conditions
ANTI_BRAND_CONDS = {
    'anti_brand_rejection', 'anti_brand_negative_experience', 'anti_brand_prefer_unknown'
}

# For each anti-brand condition and baseline, track:
# - which brand familiarity was chosen
# - which specific brands were chosen
cond_fam_dist = defaultdict(lambda: Counter())  # condition -> Counter of familiarity
cond_brand_dist = defaultdict(lambda: Counter())  # condition -> Counter of brand names
cond_nonopt_rate = defaultdict(lambda: {'nonopt': 0, 'total': 0})

# Also need to know which brand was "rejected" in anti_brand conditions
# This requires checking assortment structure — the rejected brand is typically
# the highest-familiarity non-optimal brand

for r in rows:
    cond = r['condition']
    if cond not in ANTI_BRAND_CONDS and cond != 'baseline':
        continue

    cond_nonopt_rate[cond]['total'] += 1
    if r['chose_optimal'] == 'False':
        cond_nonopt_rate[cond]['nonopt'] += 1
        fam = r.get('chosen_brand_familiarity', 'unknown')
        cond_fam_dist[cond][fam] += 1

# Compute non-optimal rates and familiarity distributions
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

# Statistical tests: chi-squared for familiarity distribution
# Compare rejection vs baseline familiarity of non-optimal choices
print("\n  Familiarity distribution tests (vs baseline):")
baseline_dist = cond_fam_dist['baseline']
baseline_total = sum(baseline_dist.values())

for cond in ['anti_brand_rejection', 'anti_brand_negative_experience']:
    cond_dist = cond_fam_dist[cond]
    cond_total = sum(cond_dist.values())
    if baseline_total > 0 and cond_total > 0:
        # Build contingency: rows = [baseline, condition], cols = [high, medium, low]
        obs = np.array([
            [baseline_dist.get('high', 0), baseline_dist.get('medium', 0), baseline_dist.get('low', 0)],
            [cond_dist.get('high', 0), cond_dist.get('medium', 0), cond_dist.get('low', 0)],
        ])
        chi2, p, dof, exp = stats.chi2_contingency(obs)
        print(f"    {cond} vs baseline: chi2={chi2:.2f}, p={p:.2e}")

# Track which assortments have anti-brand backfire
# For each assortment in anti_brand conditions, check if the chosen brand
# is a different high-fam brand (substitution) vs medium/low
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

# Compute average substitution rate to high-fam brands
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

# Deeper: decode actual brand names chosen in anti-brand vs baseline
cond_decoded_brands = defaultdict(lambda: Counter())
for r in rows:
    cond = r['condition']
    if cond not in ANTI_BRAND_CONDS and cond != 'baseline':
        continue
    if r['chose_optimal'] == 'True':
        continue
    aid = r['assortment_id']
    orig_choice = r.get('original_choice', '')
    if not orig_choice or len(orig_choice) != 1:
        continue
    idx = ord(orig_choice) - ord('A')
    prods = ASM_PRODUCTS.get(aid, [])
    if 0 <= idx < len(prods) and not prods[idx].get('is_optimal', False):
        brand = prods[idx]['brand']
        cond_decoded_brands[cond][brand] += 1

print(f"\n  Top 10 non-optimal brand choices per condition:")
for cond in ['baseline', 'anti_brand_rejection', 'anti_brand_negative_experience']:
    print(f"\n    {cond}:")
    for brand, cnt in cond_decoded_brands[cond].most_common(10):
        fam = BRAND_META.get(brand, '?')
        print(f"      {brand:20s} ({fam:6s}): {cnt}")

# --- Figure 3: Anti-brand backfire mechanism ---
fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.5))

# Panel A: Non-optimal rate by condition
ax = axes[0]
conds_order = ['baseline', 'anti_brand_rejection', 'anti_brand_negative_experience',
               'anti_brand_prefer_unknown']
cond_labels_short = ['Baseline', 'Rejection', 'Negative\nexperience', 'Prefer\nunknown']
colors_a = [NATURE_GREY, NATURE_RED, NATURE_RED, NATURE_GREEN]

nonopt_rates = [anti_brand_summary[c]['nonopt_rate'] for c in conds_order]
n_totals = [anti_brand_summary[c]['n_total'] for c in conds_order]

# Compute confidence intervals
cis_a = []
for c in conds_order:
    d = anti_brand_summary[c]
    p_hat = d['nonopt_rate'] / 100
    se = np.sqrt(p_hat * (1 - p_hat) / d['n_total']) if d['n_total'] > 0 else 0
    cis_a.append(1.96 * se * 100)

bars = ax.bar(range(len(conds_order)), nonopt_rates, yerr=cis_a,
              color=colors_a, alpha=0.85, capsize=4, error_kw={'linewidth': 0.8})
for i, (bar, n) in enumerate(zip(bars, n_totals)):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + cis_a[i] + 0.5,
            f'n={n:,}', ha='center', va='bottom', fontsize=6)
ax.set_ylabel('Non-optimal rate (%)')
ax.set_xticks(range(len(conds_order)))
ax.set_xticklabels(cond_labels_short, fontsize=7)
ax.set_title('a', fontweight='bold', loc='left', fontsize=12)

# Add baseline reference line
ax.axhline(y=nonopt_rates[0], color=NATURE_GREY, linestyle='--',
           linewidth=0.8, alpha=0.5)

# Panel B: Familiarity composition of non-optimal choices (stacked bars)
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


# ---------------------------------------------------------------------------
# ANALYSIS 4: Cross-Model Convergence on Same Wrong Brand
# ---------------------------------------------------------------------------
print("\n" + "="*70)
print("ANALYSIS 4: Cross-model convergence — distributional mechanism test")
print("="*70)

# For baseline condition only, for each assortment and model,
# identify which WRONG brand the model chose.
# Use original_choice (A/B/C/D/E) to index into assortment product list.
assortment_model_choices = defaultdict(lambda: defaultdict(lambda: Counter()))
# assortment_id -> model_key -> Counter of chosen brands (non-optimal only)

decoded_total = 0
for r in rows:
    if r['condition'] != 'baseline':
        continue
    if r['chose_optimal'] == 'True':
        continue
    aid = r['assortment_id']
    model = r['model_key']
    orig_choice = r.get('original_choice', '')
    if not orig_choice or len(orig_choice) != 1:
        continue
    idx = ord(orig_choice) - ord('A')
    prods = ASM_PRODUCTS.get(aid, [])
    if 0 <= idx < len(prods):
        brand = prods[idx]['brand']
        # Double-check this is NOT the optimal brand
        if not prods[idx].get('is_optimal', False):
            assortment_model_choices[aid][model][brand] += 1
            decoded_total += 1

print(f"  Decoded {decoded_total} non-optimal brand choices across baseline trials")

# For each assortment, compute convergence: what fraction of models agree
# on the same wrong brand?
print("\n  Per-assortment cross-model convergence (baseline, non-optimal only):")
print(f"  {'Assortment':<30s} {'N models':>10s} {'Top brand':>20s} {'Share':>8s} {'Top2':>8s}")
print("  " + "-"*80)

convergence_data = []

for aid in sorted(assortment_model_choices.keys()):
    model_choices = assortment_model_choices[aid]
    # For each model, get its most-chosen wrong brand
    model_top_brands = {}
    for model, brand_counter in model_choices.items():
        if brand_counter:
            top_brand = brand_counter.most_common(1)[0][0]
            model_top_brands[model] = top_brand

    if len(model_top_brands) < 3:
        continue

    # Count how many models converge on the same top brand
    top_brand_counter = Counter(model_top_brands.values())
    most_common_brand, most_common_count = top_brand_counter.most_common(1)[0]
    convergence_rate = most_common_count / len(model_top_brands)

    # Get the top 2 brands
    top2 = top_brand_counter.most_common(2)
    top2_count = sum(c for _, c in top2)
    top2_rate = top2_count / len(model_top_brands)

    # Category
    cat = aid.split('_')
    cat_name = '_'.join(cat[1:-1]) if len(cat) > 2 else aid

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

# Compute category-level averages
cat_convergence = defaultdict(list)
for d in convergence_data:
    cat_convergence[d['category']].append(d['convergence_rate'])

print(f"\n  Category-level convergence rates:")
cat_conv_sorted = []
for cat, rates in sorted(cat_convergence.items(), key=lambda x: -np.mean(x[1])):
    mean_rate = np.mean(rates)
    se = np.std(rates) / np.sqrt(len(rates)) if len(rates) > 1 else 0
    cat_conv_sorted.append((cat, mean_rate, se, len(rates)))
    print(f"    {cat:<25s} {mean_rate:.1%} +/- {se:.1%}  (n={len(rates)} assortments)")

# Category non-optimal rates from main data for correlation
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

# Correlate convergence with non-optimal rate
conv_rates_for_corr = []
nonopt_rates_for_corr = []
cat_names_for_corr = []
for cat, mean_rate, se, n in cat_conv_sorted:
    if cat in cat_nonopt_pcts:
        conv_rates_for_corr.append(mean_rate)
        nonopt_rates_for_corr.append(cat_nonopt_pcts[cat])
        cat_names_for_corr.append(cat)

if len(conv_rates_for_corr) > 3:
    r_conv, p_conv = stats.pearsonr(conv_rates_for_corr, nonopt_rates_for_corr)
    print(f"\n  Correlation (convergence vs non-optimal rate): r={r_conv:.3f}, p={p_conv:.4f}")

# --- Figure 4: Cross-model convergence ---
fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.5))

# Panel A: Per-assortment convergence rate, colored by category
ax = axes[0]
if convergence_data:
    # Sort by convergence rate
    sorted_conv = sorted(convergence_data, key=lambda x: -x['convergence_rate'])
    y_vals = [d['convergence_rate'] * 100 for d in sorted_conv]

    # Assign colors by category
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
    ax.set_yticks([])  # Too many labels
    # Chance level: if models pick randomly among ~4 non-optimal brands,
    # convergence on one brand is 1/4 = 25%
    ax.axvline(x=25, color=NATURE_GREY, linestyle=':', linewidth=0.8)
    ax.set_xlim(0, 105)
    ax.set_title('a', fontweight='bold', loc='left', fontsize=12)
    ax.text(27, len(y_vals)*0.1, 'Chance\n(1/4 brands)', fontsize=7,
            color=NATURE_GREY, va='center')

# Panel B: Category convergence vs non-optimal rate
ax = axes[1]
if len(conv_rates_for_corr) > 0:
    ax.scatter([r * 100 for r in conv_rates_for_corr], nonopt_rates_for_corr,
               s=60, color=NATURE_BLUE, alpha=0.8, edgecolors='white', linewidth=0.5)

    # Add category labels
    for i, cat in enumerate(cat_names_for_corr):
        label = cat.replace('_', ' ').title()
        ax.annotate(label, (conv_rates_for_corr[i] * 100, nonopt_rates_for_corr[i]),
                    fontsize=6, xytext=(5, 3), textcoords='offset points',
                    alpha=0.8)

    # Add regression line
    if len(conv_rates_for_corr) > 2:
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


# ---------------------------------------------------------------------------
# SUPPLEMENTARY: Non-optimal rate by spec level (with CI) — data for Fig 1
# ---------------------------------------------------------------------------
print("\n" + "="*70)
print("SUPPLEMENTARY: Specification gradient non-optimal rates")
print("="*70)

spec_level_rates = defaultdict(lambda: {'nonopt': 0, 'total': 0})
for r in rows:
    cond = r['condition']
    if cond in SPEC_LEVELS:
        level = SPEC_LEVELS[cond]
        spec_level_rates[level]['total'] += 1
        if r['chose_optimal'] == 'False':
            spec_level_rates[level]['nonopt'] += 1

print(f"  {'Level':<15s} {'Non-opt %':>10s} {'n':>8s}")
for level in sorted(spec_level_rates.keys()):
    d = spec_level_rates[level]
    rate = d['nonopt'] / d['total'] * 100 if d['total'] > 0 else 0
    print(f"  {SPEC_LEVEL_LABELS[level].strip():<15s} {rate:>9.1f}% {d['total']:>8,}")


# ---------------------------------------------------------------------------
# Combined summary figure (2x2 layout for Nature)
# ---------------------------------------------------------------------------
print("\n" + "="*70)
print("Creating combined 4-panel figure...")
print("="*70)

fig, axes = plt.subplots(2, 2, figsize=(7.2, 7.0))

# Panel A (top-left): Semantic contamination — brand ratio by spec level
ax = axes[0, 0]
x = np.arange(len(levels_sorted))
labels = [SPEC_LEVEL_LABELS[l].replace('\n', ' ') for l in levels_sorted]
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
ax.set_xticklabels(labels, fontsize=6.5, rotation=20)
ax.legend(frameon=False, fontsize=7)
ax.set_title('a  Semantic contamination', fontweight='bold', loc='left', fontsize=9)

# Panel B (top-right): Familiarity-stratified brand reasoning
ax = axes[0, 1]
fams = ['high', 'medium']
rates = []
cis_b = []
for fam in fams:
    d = fam_brand_reasoning[fam]
    total_j = d['brand_yes'] + d['brand_no']
    rate = d['brand_yes'] / total_j * 100 if total_j > 0 else 0
    rates.append(rate)
    se = np.sqrt((rate/100) * (1 - rate/100) / total_j) * 100 if total_j > 0 else 0
    cis_b.append(1.96 * se)

bars = ax.bar(['High\nfamiliarity', 'Medium\nfamiliarity'], rates, yerr=cis_b,
              color=[NATURE_RED, NATURE_ORANGE], alpha=0.85, capsize=5,
              error_kw={'linewidth': 0.8}, width=0.45)
ax.set_ylabel('Explicit brand reasoning (%)')
ax.set_title('b  Confabulation asymmetry', fontweight='bold', loc='left', fontsize=9)

# Add p-value annotation
max_y_b = max(r + c for r, c in zip(rates, cis_b))
ax.plot([0, 0, 1, 1], [max_y_b + 1, max_y_b + 2, max_y_b + 2, max_y_b + 1],
        color='black', linewidth=0.8)
if a2_p_val < 0.001:
    p_text = f'p < 0.001\nOR = {or_val:.2f}'
else:
    p_text = f'p = {a2_p_val:.3f}\nOR = {or_val:.2f}'
ax.text(0.5, max_y_b + 2.5, p_text, ha='center', va='bottom', fontsize=7)
ax.set_ylim(0, max_y_b + 8)

# Panel C (bottom-left): Anti-brand backfire — familiarity composition
ax = axes[1, 0]
conds_c = ['baseline', 'anti_brand_rejection', 'anti_brand_negative_experience',
           'anti_brand_prefer_unknown']
labels_c = ['Baseline', 'Rejection', 'Negative\nexperience', 'Prefer\nunknown']

high_pcts = [anti_brand_summary[c]['high_pct'] for c in conds_c]
med_pcts = [anti_brand_summary[c]['medium_pct'] for c in conds_c]
low_pcts = [anti_brand_summary[c]['low_pct'] for c in conds_c]

x_c = np.arange(len(conds_c))
ax.bar(x_c, high_pcts, color=NATURE_RED, alpha=0.85, label='High-fam')
ax.bar(x_c, med_pcts, bottom=high_pcts, color=NATURE_ORANGE, alpha=0.85, label='Med-fam')
bottom2 = [h + m for h, m in zip(high_pcts, med_pcts)]
ax.bar(x_c, low_pcts, bottom=bottom2, color=NATURE_CYAN, alpha=0.85, label='Low-fam')
ax.set_ylabel('Share of non-optimal choices (%)')
ax.set_xticks(x_c)
ax.set_xticklabels(labels_c, fontsize=6.5)
ax.legend(frameon=False, fontsize=7, loc='upper right')
ax.set_title('c  Anti-brand substitution', fontweight='bold', loc='left', fontsize=9)
ax.set_ylim(0, 105)

# Non-optimal rate annotations on top
for i, cond in enumerate(conds_c):
    rate = anti_brand_summary[cond]['nonopt_rate']
    ax.text(i, 102, f'{rate:.1f}%', ha='center', va='bottom', fontsize=7,
            fontweight='bold', color=NATURE_PURPLE)

# Panel D (bottom-right): Cross-model convergence vs non-optimal rate
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

    if len(conv_rates_for_corr) > 2:
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


# ---------------------------------------------------------------------------
# Save summary JSON
# ---------------------------------------------------------------------------
print("\n" + "="*70)
print("Saving summary JSON...")
print("="*70)

summary = {
    'analysis_date': '2026-04-04',
    'data_source': str(CSV_PATH),
    'total_trials': len(rows),
    'analysis_1_semantic_contamination': {
        'description': 'Brand-association vocabulary ratio across specification levels in justification texts',
        'hypothesis': 'Natural language activates the same distributional associations that encode brand preferences. Utility functions bypass this semantic space.',
        'results': {str(k): {
            'label': v['label'].strip(),
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
        'chi2': round(a2_chi2, 3) if a2_chi2 else None,
        'p_value': a2_p_val if a2_p_val else None,
        'odds_ratio': round(or_val, 3) if or_val != float('inf') else 'inf',
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
        'substitution_to_highfam_mean': round(np.mean(sub_rates_high) * 100, 2) if sub_rates_high else None,
    },
    'analysis_4_cross_model_convergence': {
        'description': 'Per-assortment convergence rate on the same non-optimal brand across 18 models',
        'hypothesis': 'If mechanism is distributional, models trained on similar corpora should err on the same assortments and choose the same branded alternatives.',
        'n_assortments_analyzed': len(convergence_data),
        'mean_convergence_rate': round(np.mean([d['convergence_rate'] for d in convergence_data]) * 100, 2) if convergence_data else None,
        'median_convergence_rate': round(np.median([d['convergence_rate'] for d in convergence_data]) * 100, 2) if convergence_data else None,
        'category_convergence': {cat: round(np.mean(rates) * 100, 2) for cat, rates in cat_convergence.items()},
        'convergence_nonopt_correlation': {
            'r': round(r_conv, 4) if 'r_conv' in dir() else None,
            'p': round(p_conv, 6) if 'p_conv' in dir() else None,
        } if len(conv_rates_for_corr) > 3 else None,
    },
}

json_path = OUT_DIR / "mechanistic_analysis_summary.json"
with open(json_path, 'w', encoding='utf-8') as f:
    json.dump(summary, f, indent=2, default=str)
print(f"  Saved {json_path}")


# ---------------------------------------------------------------------------
# Print headline findings
# ---------------------------------------------------------------------------
print("\n" + "="*70)
print("HEADLINE FINDINGS")
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
print(f"   High-fam brands have {or_val:.1f}x more honest brand citations.")
print(f"   Mid-fam brands confabulate more: they have associations but not")
print(f"   the explicit 'this is a brand choice' representation.")

print("\n3. ANTI-BRAND BACKFIRE:")
for cond in ['baseline', 'anti_brand_rejection', 'anti_brand_negative_experience']:
    d = anti_brand_summary[cond]
    print(f"   {cond}: {d['nonopt_rate']:.1f}% non-opt, "
          f"{d['high_pct']:.1f}% high-fam among errors")
if sub_rates_high:
    print(f"   Mean substitution to high-fam brands: {np.mean(sub_rates_high)*100:.1f}%")

print("\n4. CROSS-MODEL CONVERGENCE:")
if convergence_data:
    rates = [d['convergence_rate'] for d in convergence_data]
    print(f"   Mean convergence: {np.mean(rates)*100:.1f}%")
    print(f"   Median convergence: {np.median(rates)*100:.1f}%")
    if len(conv_rates_for_corr) > 3:
        print(f"   Convergence-nonoptimal correlation: r={r_conv:.3f}, p={p_conv:.4f}")
    # Highest convergence assortments
    top3 = sorted(convergence_data, key=lambda x: -x['convergence_rate'])[:3]
    for d in top3:
        print(f"   Top: {d['assortment_id']} -> {d['top_brand']} ({d['convergence_rate']:.0%} of models)")

print("\n" + "="*70)
print("DONE. All results saved to:")
print(f"  {OUT_DIR}")
print("="*70)
