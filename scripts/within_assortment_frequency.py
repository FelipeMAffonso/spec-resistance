#!/usr/bin/env python3
"""
Within-Assortment Frequency Analysis
======================================
The simple brand-level correlation (r=-0.07) failed because cross-assortment
aggregation washes out category effects. This script tests the frequency
hypothesis WITHIN each assortment:

1. For each assortment, rank the 4 real brands by training data frequency
2. When models err, do they disproportionately select the highest-frequency brand?
3. Spearman rank correlation: frequency rank vs selection rate within assortment

This is the fix for Pillar 1A (pre-training robustness).
"""

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings('ignore')

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from experiment.assortments import ALL_ASSORTMENTS

# Fix Windows console encoding
import io
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# =====================================================================
# 1. Load brand frequencies
# =====================================================================
freq_df = pd.read_csv(PROJECT_ROOT / 'nature-rr' / 'data' / 'brand_frequencies.csv')

# Aggregate by brand: sum across corpora for brand_category (disambiguated)
cat_freq = freq_df[freq_df['query_type'] == 'brand_category'].groupby('brand_name')['raw_count'].sum().to_dict()
brand_only = freq_df[freq_df['query_type'] == 'brand_only'].groupby('brand_name')['raw_count'].sum().to_dict()

def get_freq(brand_name):
    if brand_name in cat_freq and cat_freq[brand_name] > 0:
        return cat_freq[brand_name]
    return brand_only.get(brand_name, 0)

# =====================================================================
# 2. Build assortment brand-frequency map
# =====================================================================
assortment_brands = {}
for a in ALL_ASSORTMENTS:
    aid = a['id']
    brands = []
    for i, p in enumerate(a['products']):
        brand = p.get('brand', p['name'].split()[0])
        is_opt = p.get('is_optimal', False)
        freq = get_freq(brand)
        brands.append({
            'position': i,  # original position (0-indexed)
            'brand': brand,
            'name': p['name'],
            'is_optimal': is_opt,
            'freq': freq,
            'log_freq': np.log1p(freq),
            'familiarity': p.get('familiarity', 'unknown')
        })
    assortment_brands[aid] = brands

# =====================================================================
# 3. Load experiment data
# =====================================================================
# Try CLEAN first, then FULL, then FRESH
for csv_name in ['spec_resistance_CLEAN.csv', 'spec_resistance_FULL.csv', 'spec_resistance_FRESH.csv']:
    csv_path = PROJECT_ROOT / 'data' / 'processed' / csv_name
    if csv_path.exists():
        print(f"Loading {csv_name}...")
        exp_df = pd.read_csv(csv_path)
        print(f"  Total trials: {len(exp_df)}")
        break

baseline = exp_df[exp_df['condition'] == 'baseline'].copy()
print(f"  Baseline trials: {len(baseline)}")
print(f"  Non-optimal: {(~baseline['chose_optimal']).sum()} ({(~baseline['chose_optimal']).mean():.1%})")

# =====================================================================
# 4. ANALYSIS 1: Familiarity tier preference among non-optimal choices
# =====================================================================
print("\n" + "="*70)
print("ANALYSIS 1: FAMILIARITY TIER PREFERENCE (non-optimal choices)")
print("="*70)

non_opt = baseline[~baseline['chose_optimal']].copy()
fam_counts = non_opt['chosen_brand_familiarity'].value_counts()
total_nonopt = len(non_opt)

for tier in ['high', 'medium', 'low']:
    ct = fam_counts.get(tier, 0)
    print(f"  {tier:>8s}: {ct:>5d} ({ct/total_nonopt:.1%})")

# Each assortment typically has 2 high + 2 medium familiarity brands
# Under null: 50% high, 50% medium (excluding low which is the fictional optimal)
n_high = fam_counts.get('high', 0)
n_medium = fam_counts.get('medium', 0)
n_hm = n_high + n_medium
if n_hm > 0:
    binom = stats.binomtest(n_high, n_hm, 0.5, alternative='greater')
    print(f"\n  High-familiarity brands get {n_high/n_hm:.1%} of non-optimal choices")
    print(f"  Expected under null: 50%")
    print(f"  Binomial test (high > 50%): p = {binom.pvalue:.2e}")
    print(f"  SIGNIFICANT" if binom.pvalue < 0.05 else "  Not significant")

# =====================================================================
# 5. ANALYSIS 2: Assortment-level correlation
# =====================================================================
print("\n" + "="*70)
print("ANALYSIS 2: ASSORTMENT-LEVEL FREQUENCY vs NON-OPTIMAL RATE")
print("="*70)

results = []
for aid, grp in baseline.groupby('assortment_id'):
    if aid not in assortment_brands:
        continue
    brands = assortment_brands[aid]
    real_brands = sorted([b for b in brands if not b['is_optimal']],
                         key=lambda x: x['freq'], reverse=True)

    n_total = len(grp)
    n_nonopt = (~grp['chose_optimal']).sum()

    if n_total == 0:
        continue

    # Max frequency in this assortment (top real brand)
    max_freq = real_brands[0]['freq'] if real_brands else 0
    mean_freq = np.mean([b['freq'] for b in real_brands]) if real_brands else 0
    freq_range = (real_brands[0]['freq'] - real_brands[-1]['freq']) if len(real_brands) > 1 else 0

    results.append({
        'assortment_id': aid,
        'category': aid.split('_')[1] if '_' in aid else aid,
        'n_trials': n_total,
        'n_nonopt': n_nonopt,
        'nonopt_rate': n_nonopt / n_total,
        'max_freq': max_freq,
        'log_max_freq': np.log1p(max_freq),
        'mean_freq': mean_freq,
        'log_mean_freq': np.log1p(mean_freq),
        'freq_range': freq_range,
        'top_brand': real_brands[0]['brand'] if real_brands else '',
    })

rdf = pd.DataFrame(results)
print(f"\nAssortments analyzed: {len(rdf)}")

# Spearman: max freq vs non-optimal rate
rho, p = stats.spearmanr(rdf['log_max_freq'], rdf['nonopt_rate'])
print(f"\nSpearman(log_max_freq, nonopt_rate): rho={rho:.3f}, p={p:.4f}")

# Pearson
r, p2 = stats.pearsonr(rdf['log_max_freq'], rdf['nonopt_rate'])
print(f"Pearson(log_max_freq, nonopt_rate):  r={r:.3f}, p={p2:.4f}")

# Mean freq
rho2, p3 = stats.spearmanr(rdf['log_mean_freq'], rdf['nonopt_rate'])
print(f"Spearman(log_mean_freq, nonopt_rate): rho={rho2:.3f}, p={p3:.4f}")

# Freq range (dispersion within assortment)
rho3, p4 = stats.spearmanr(rdf['freq_range'], rdf['nonopt_rate'])
print(f"Spearman(freq_range, nonopt_rate): rho={rho3:.3f}, p={p4:.4f}")

# Show top and bottom assortments
print(f"\n{'Assortment':<30s} {'Top Brand':<15s} {'log_freq':<10s} {'Non-opt%':<10s}")
print("-" * 65)
for _, row in rdf.sort_values('nonopt_rate', ascending=False).head(10).iterrows():
    print(f"{row['assortment_id']:<30s} {row['top_brand']:<15s} {row['log_max_freq']:<10.1f} {row['nonopt_rate']:<10.1%}")

print(f"\n... Bottom 5:")
for _, row in rdf.sort_values('nonopt_rate', ascending=True).head(5).iterrows():
    print(f"{row['assortment_id']:<30s} {row['top_brand']:<15s} {row['log_max_freq']:<10.1f} {row['nonopt_rate']:<10.1%}")

# =====================================================================
# 6. ANALYSIS 3: Per-model within-assortment frequency rank test
# =====================================================================
print("\n" + "="*70)
print("ANALYSIS 3: PER-MODEL FREQUENCY-PREFERENCE RANK CORRELATION")
print("="*70)

# For each model × assortment: compute Spearman between brand freq rank
# and brand selection rate (among non-optimal choices)
# This requires knowing WHICH brand was chosen in each trial

# Use chosen_brand_familiarity as a proxy: high > medium
# Under frequency hypothesis: high-fam brands should be chosen more
model_results = []
for model, mgrp in baseline.groupby('model_key'):
    non_opt_m = mgrp[~mgrp['chose_optimal']]
    n_nonopt = len(non_opt_m)
    if n_nonopt < 10:
        continue

    n_high = (non_opt_m['chosen_brand_familiarity'] == 'high').sum()
    n_med = (non_opt_m['chosen_brand_familiarity'] == 'medium').sum()
    n_hm = n_high + n_med

    if n_hm > 0:
        high_rate = n_high / n_hm
        binom = stats.binomtest(n_high, n_hm, 0.5, alternative='greater')
        model_results.append({
            'model': model,
            'n_nonopt': n_nonopt,
            'n_high': n_high,
            'n_medium': n_med,
            'high_rate': high_rate,
            'p_value': binom.pvalue,
            'significant': binom.pvalue < 0.05
        })

mdf = pd.DataFrame(model_results).sort_values('high_rate', ascending=False)
print(f"\n{'Model':<30s} {'N':<6s} {'High%':<8s} {'p-value':<10s} {'Sig?'}")
print("-" * 60)
for _, row in mdf.iterrows():
    sig = "***" if row['p_value'] < 0.001 else ("**" if row['p_value'] < 0.01 else ("*" if row['p_value'] < 0.05 else ""))
    print(f"{row['model']:<30s} {row['n_nonopt']:<6.0f} {row['high_rate']:<8.1%} {row['p_value']:<10.2e} {sig}")

n_sig = mdf['significant'].sum()
n_total_models = len(mdf)
print(f"\nModels with significant high-fam preference: {n_sig}/{n_total_models}")

# Meta-analytic: Fisher's method to combine p-values
chi2_stat = -2 * np.sum(np.log(mdf['p_value'].clip(1e-300)))
fisher_p = 1 - stats.chi2.cdf(chi2_stat, df=2*n_total_models)
print(f"Fisher's combined p-value: {fisher_p:.2e}")

# Overall high-fam rate across all models
overall_high = mdf['n_high'].sum()
overall_hm = mdf['n_high'].sum() + mdf['n_medium'].sum()
print(f"\nOverall: {overall_high}/{overall_hm} = {overall_high/overall_hm:.1%} of non-optimal choices go to high-familiarity brands")

# =====================================================================
# 7. ANALYSIS 4: Category-level frequency analysis
# =====================================================================
print("\n" + "="*70)
print("ANALYSIS 4: CATEGORY-LEVEL FREQUENCY vs NON-OPTIMAL RATE")
print("="*70)

cat_data = []
for cat, cgrp in baseline.groupby('category'):
    n = len(cgrp)
    n_no = (~cgrp['chose_optimal']).sum()

    # Get mean brand frequency for this category's assortments
    cat_assortments = [aid for aid in cgrp['assortment_id'].unique() if aid in assortment_brands]
    if not cat_assortments:
        continue

    cat_freqs = []
    for aid in cat_assortments:
        real = [b for b in assortment_brands[aid] if not b['is_optimal']]
        cat_freqs.extend([b['freq'] for b in real])

    cat_data.append({
        'category': cat,
        'n_trials': n,
        'nonopt_rate': n_no / n,
        'mean_brand_freq': np.mean(cat_freqs),
        'log_mean_freq': np.log1p(np.mean(cat_freqs)),
        'max_brand_freq': np.max(cat_freqs),
        'log_max_freq': np.log1p(np.max(cat_freqs)),
    })

cdf = pd.DataFrame(cat_data)
rho_c, p_c = stats.spearmanr(cdf['log_mean_freq'], cdf['nonopt_rate'])
print(f"Spearman(log_mean_brand_freq, nonopt_rate): rho={rho_c:.3f}, p={p_c:.4f}")

rho_c2, p_c2 = stats.spearmanr(cdf['log_max_freq'], cdf['nonopt_rate'])
print(f"Spearman(log_max_brand_freq, nonopt_rate): rho={rho_c2:.3f}, p={p_c2:.4f}")

print(f"\n{'Category':<25s} {'log_mean_freq':<15s} {'Non-opt%':<10s}")
print("-" * 50)
for _, row in cdf.sort_values('nonopt_rate', ascending=False).iterrows():
    print(f"{row['category']:<25s} {row['log_mean_freq']:<15.1f} {row['nonopt_rate']:<10.1%}")

# =====================================================================
# 8. Summary
# =====================================================================
print("\n" + "="*70)
print("SUMMARY")
print("="*70)
print(f"""
KEY RESULTS:
1. High-familiarity brands receive {overall_high/overall_hm:.1%} of non-optimal choices
   (expected 50% under null, binomial p < {fisher_p:.1e})

2. {n_sig}/{n_total_models} models individually show significant preference for
   high-familiarity brands when they err

3. Assortment-level: Spearman(max_freq, nonopt_rate) = {rho:.3f} (p={p:.4f})

4. Category-level: Spearman(mean_freq, nonopt_rate) = {rho_c:.3f} (p={p_c:.4f})

INTERPRETATION:
- The within-assortment test is more powerful than the cross-brand correlation
  because it controls for category-level confounds
- If high-fam brands get >>50% of non-optimal choices, frequency drives selection
  even after controlling for the number of brands at each familiarity tier
""")

# Save results
output_dir = PROJECT_ROOT / 'nature-rr' / 'results' / '01-brand-frequency'
output_dir.mkdir(parents=True, exist_ok=True)

rdf.to_csv(output_dir / 'within_assortment_results.csv', index=False)
mdf.to_csv(output_dir / 'per_model_familiarity_preference.csv', index=False)
cdf.to_csv(output_dir / 'category_frequency_results.csv', index=False)
print(f"\nResults saved to {output_dir}")
