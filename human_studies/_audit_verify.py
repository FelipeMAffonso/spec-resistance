"""Audit human studies claims against actual data."""
import pandas as pd
import numpy as np
from scipy import stats

base = r"C:/Users/fmarine/Dropbox/Felipe/CLAUDE CODE/academic-research/projects/spec-resistance/OSF/human_studies"

def fisher_or_ci(a, b, c, d):
    """OR with Wald 95% CI on log scale."""
    table = np.array([[a, b], [c, d]])
    odds_ratio, p = stats.fisher_exact(table)
    # Wald CI
    if min(a,b,c,d) == 0:
        return odds_ratio, p, (np.nan, np.nan)
    se = np.sqrt(1/a + 1/b + 1/c + 1/d)
    log_or = np.log(odds_ratio)
    return odds_ratio, p, (np.exp(log_or - 1.96*se), np.exp(log_or + 1.96*se))

# ====== STUDY 1A ======
print("=" * 70)
print("STUDY 1A — coffee makers")
print("=" * 70)
d = pd.read_csv(f"{base}/study1a-coffee/anonymised.csv")
# filter: pass attention check (==4) — common protocol
d = d[d['attn_check'] == 4].copy()
print(f"N after attn_check==4: {len(d)}")
# Map condition: 1=NoAI, 2=BiasedAI, 3=DebiasedAI (typical)
print("Condition vc:", d['Condition'].value_counts().to_dict())
# QID17==2 branded, QID17==4 optimal
d['branded'] = (d['QID17'] == 2).astype(int)
d['optimal'] = (d['QID17'] == 4).astype(int)

for cond_val in sorted(d['Condition'].dropna().unique()):
    sub = d[d['Condition'] == cond_val]
    print(f"  Cond={cond_val}: N={len(sub)}, branded={sub['branded'].mean()*100:.1f}%, optimal={sub['optimal'].mean()*100:.1f}%")

# Identify which is which
# Claim: BiasedAI vs NoAI: branded 64.4% vs 31.1%, +33.3pp
# Claim: DebiasedAI vs NoAI optimal: +24.3pp
# Try cond==2 = BiasedAI
print("\n-- Pairwise tests for branded --")
for biased_c, noai_c in [(1,2),(1,3),(2,1),(2,3),(3,1),(3,2)]:
    s_b = d[d['Condition']==biased_c]
    s_n = d[d['Condition']==noai_c]
    a = s_b['branded'].sum(); b = len(s_b)-a
    c = s_n['branded'].sum(); dd = len(s_n)-c
    OR, p, ci = fisher_or_ci(a,b,c,dd)
    pp = (a/len(s_b) - c/len(s_n))*100
    print(f"  Cond {biased_c} vs {noai_c}: branded {a/len(s_b)*100:.1f}% vs {c/len(s_n)*100:.1f}% diff={pp:+.1f}pp  OR={OR:.2f} CI=[{ci[0]:.2f},{ci[1]:.2f}] p={p:.2e}")

print("\n-- Pairwise tests for optimal --")
for biased_c, noai_c in [(1,2),(1,3),(2,1),(2,3),(3,1),(3,2)]:
    s_b = d[d['Condition']==biased_c]
    s_n = d[d['Condition']==noai_c]
    a = s_b['optimal'].sum(); b = len(s_b)-a
    c = s_n['optimal'].sum(); dd = len(s_n)-c
    OR, p, ci = fisher_or_ci(a,b,c,dd)
    pp = (a/len(s_b) - c/len(s_n))*100
    print(f"  Cond {biased_c} vs {noai_c}: optimal {a/len(s_b)*100:.1f}% vs {c/len(s_n)*100:.1f}% diff={pp:+.1f}pp  OR={OR:.2f} p={p:.2e}")

# ====== STUDY 1B ======
print("\n" + "=" * 70)
print("STUDY 1B — wireless earbuds")
print("=" * 70)
d = pd.read_csv(f"{base}/study1b-earbuds/anonymised.csv")
print(f"All rows: {len(d)}")
print("Cols sample:", [c for c in d.columns if 'attn' in c.lower() or c in ['Condition','QID17','attn_check']])
if 'attn_check' in d.columns:
    print(f"attn_check vc: {d['attn_check'].value_counts(dropna=False).to_dict()}")
    d = d[d['attn_check'] == 4].copy()
print(f"N after filter: {len(d)}")
print("Condition vc:", d['Condition'].value_counts(dropna=False).to_dict())
print("QID17 vc:", d['QID17'].value_counts(dropna=False).to_dict())
d['branded'] = (d['QID17'] == 2).astype(int)
d['optimal'] = (d['QID17'] == 4).astype(int)

# overpaid: chose anything except optimal? or specifically branded? — claim is 79.5 → 89.7 overpaid
# overpaid likely = chose product priced above optimal
print("\n-- Pairwise branded --")
for c1, c2 in [(1,2),(1,3),(2,1),(2,3),(3,1),(3,2)]:
    s_b = d[d['Condition']==c1]
    s_n = d[d['Condition']==c2]
    if len(s_b)==0 or len(s_n)==0: continue
    a = s_b['branded'].sum(); b = len(s_b)-a
    c = s_n['branded'].sum(); dd = len(s_n)-c
    OR, p, ci = fisher_or_ci(a,b,c,dd)
    pp = (a/len(s_b) - c/len(s_n))*100
    print(f"  C{c1} vs C{c2}: branded {a/len(s_b)*100:.1f}% vs {c/len(s_n)*100:.1f}% diff={pp:+.1f}pp OR={OR:.2f} p={p:.2e}")

print("\n-- Pairwise optimal --")
for c1, c2 in [(1,2),(1,3),(2,1),(2,3),(3,1),(3,2)]:
    s_b = d[d['Condition']==c1]
    s_n = d[d['Condition']==c2]
    if len(s_b)==0 or len(s_n)==0: continue
    a = s_b['optimal'].sum(); b = len(s_b)-a
    c = s_n['optimal'].sum(); dd = len(s_n)-c
    OR, p, ci = fisher_or_ci(a,b,c,dd)
    pp = (a/len(s_b) - c/len(s_n))*100
    print(f"  C{c1} vs C{c2}: optimal {a/len(s_b)*100:.1f}% vs {c/len(s_n)*100:.1f}% diff={pp:+.1f}pp OR={OR:.2f} p={p:.2e}")

# ====== STUDY 2 ======
print("\n" + "=" * 70)
print("STUDY 2 — inoculation")
print("=" * 70)
d = pd.read_csv(f"{base}/study2-inoculation/anonymised.csv")
print(f"All rows: {len(d)}")
print("Cols sample:", [c for c in d.columns if c in ['Condition','QID17','attn_check'] or 'cond' in c.lower()])
if 'attn_check' in d.columns:
    print(f"attn_check vc: {d['attn_check'].value_counts(dropna=False).to_dict()}")
    d = d[d['attn_check'] == 4].copy()
print(f"N after filter: {len(d)}")
print("Condition vc:", d['Condition'].value_counts(dropna=False).to_dict())
print("QID17 vc:", d['QID17'].value_counts(dropna=False).to_dict())
d['branded'] = (d['QID17'] == 2).astype(int)

# Conditions: BiasedAI control, Inoculation, SpecExposed (typically 3 conds)
# Claim: Inoculation: -12.2pp vs control p=3.5e-3; SpecExposed: -17.4pp p=3.3e-5
print("\n-- Pairwise branded (Study 2) --")
for c1, c2 in [(1,2),(1,3),(2,1),(2,3),(3,1),(3,2)]:
    s_b = d[d['Condition']==c1]
    s_n = d[d['Condition']==c2]
    if len(s_b)==0 or len(s_n)==0: continue
    a = s_b['branded'].sum(); b = len(s_b)-a
    c = s_n['branded'].sum(); dd = len(s_n)-c
    OR, p, ci = fisher_or_ci(a,b,c,dd)
    pp = (a/len(s_b) - c/len(s_n))*100
    print(f"  C{c1} vs C{c2}: branded {a/len(s_b)*100:.1f}% vs {c/len(s_n)*100:.1f}% diff={pp:+.1f}pp p={p:.2e}")

# ====== STUDY 3 ======
print("\n" + "=" * 70)
print("STUDY 3 — chatbot")
print("=" * 70)
import os
s3_files = ['anonymised.csv', 'analysis/output/pilot_data_usable.csv']
for f in s3_files:
    p = f"{base}/study3-chatbot/{f}"
    if os.path.exists(p):
        dd = pd.read_csv(p)
        print(f"  {f}: rows={len(dd)}, cols={len(dd.columns)}")
