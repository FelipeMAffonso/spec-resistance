"""Verify welfare USD claims in main_v3.md against Study 3 raw data."""
import pandas as pd
import numpy as np
from scipy import stats

base = r"C:/Users/fmarine/Dropbox/Felipe/CLAUDE CODE/academic-research/projects/spec-resistance/OSF/human_studies"
d = pd.read_csv(f"{base}/study3-chatbot/analysis/output/pilot_data_usable.csv")
print(f"N usable: {len(d)}")

# Map condition - already coded
print(f"study3_condition vc: {d['study3_condition'].value_counts(dropna=False).to_dict()}")

# Compute per-participant overpayment vs spec-optimal product
# study3_product_choice_price is what they paid; dom_price_num is the spec-optimal price
d['paid'] = pd.to_numeric(d['study3_product_choice_price'].astype(str).str.replace('$','').str.replace(',',''), errors='coerce')
d['optimal_price'] = pd.to_numeric(d['dom_price_num'], errors='coerce')
d['overpay'] = d['paid'] - d['optimal_price']
d['rec_price_n'] = pd.to_numeric(d['rec_price_num'], errors='coerce')

# Structural gap = rec_price - optimal_price
d['structural_gap'] = d['rec_price_n'] - d['optimal_price']

print("\n--- Conditions ---")
for cond in d['study3_condition'].dropna().unique():
    sub = d[d['study3_condition']==cond]
    print(f"  {cond}: N={len(sub)}, median overpay=${sub['overpay'].median():.2f}, mean=${sub['overpay'].mean():.2f}")

# Mann-Whitney biased vs honest on overpay
biased = d[d['study3_condition']=='biased']['overpay'].dropna()
honest = d[d['study3_condition']=='honest']['overpay'].dropna()
neutral = d[d['study3_condition']=='neutral']['overpay'].dropna()

# Try multiple comparisons
print("\n--- Mann-Whitney tests on overpay ---")
for label, a, b in [('biased vs honest', biased, honest), ('biased vs neutral', biased, neutral), ('honest vs neutral', honest, neutral)]:
    U, p = stats.mannwhitneyu(a, b, alternative='two-sided')
    print(f"  {label}: U={U:.0f}, P={p:.2e}, N1={len(a)} N2={len(b)}")

# Hodges-Lehmann (median of pairwise differences) for biased vs honest
def hodges_lehmann(a, b):
    a = np.asarray(a); b = np.asarray(b)
    diffs = a[:,None] - b[None,:]
    return np.median(diffs.flatten())

print(f"\nHodges-Lehmann (biased - honest): ${hodges_lehmann(biased, honest):.2f}")

# Trimmed mean (5%)
def trim_mean(x, alpha=0.05):
    x = np.sort(np.asarray(x))
    k = int(np.floor(len(x)*alpha))
    if k==0: return np.mean(x)
    return np.mean(x[k:-k])

# Per-participant overpayment swing — biased - honest median difference
print(f"5%-trimmed mean (biased - honest swing): ${trim_mean(biased) - trim_mean(honest):.2f}")
print(f"Median per-participant overpayment swing biased-honest: ${biased.median() - honest.median():.2f}")

# Among 132 Biased who took AI: overpayment
took_ai = d[(d['study3_condition']=='biased') & (d['chose_recommended_bool']==1)]
print(f"\nBiased who took AI rec: N={len(took_ai)}")
op = took_ai['overpay'].dropna()
print(f"  median overpayment: ${op.median():.2f}")
print(f"  10th pct: ${op.quantile(0.10):.2f}, 90th pct: ${op.quantile(0.90):.2f}")

# Structural gap median + mean across Study 3
sg = d['structural_gap'].dropna()
print(f"\nStructural gap (rec - optimal): N={len(sg)}, median=${sg.median():.2f}, mean=${sg.mean():.2f}")

# Compliance shift x structural gap
# 18.7% compliance shift × structural gap
shift = 0.187
print(f"\n0.187 × median gap = ${0.187 * sg.median():.2f}")
print(f"0.187 × mean gap = ${0.187 * sg.mean():.2f}")
