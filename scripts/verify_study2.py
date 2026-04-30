"""Verify Study 2 effect sizes against paper claims."""
import pandas as pd
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
p = PROJECT / "OSF" / "data" / "human_studies" / "study2_inoculation_anonymised.csv"

df = pd.read_csv(p, low_memory=False)
print(f"Raw N: {len(df)}")
print(f"ConditionD counts: {df['ConditionD'].value_counts().to_dict()}")

# Prereg exclusions: consent=1, Finished=1, attn_check=4, duration 120-1200
d = df.copy()
d["duration_s"] = pd.to_numeric(d["Duration (in seconds)"], errors="coerce")
d["consent"] = pd.to_numeric(d["consent"], errors="coerce")
d["attn_check"] = pd.to_numeric(d["attn_check"], errors="coerce")
d["Finished"] = pd.to_numeric(d["Finished"], errors="coerce")
flt = d[(d["consent"] == 1) & (d["Finished"] == 1) & (d["attn_check"] == 4) &
        (d["duration_s"] >= 120) & (d["duration_s"] <= 1200) &
        d["QID17"].notna()].copy()
print(f"Post prereg exclusions: {len(flt)}")

# Decode choice
def decode(row):
    try:
        qid = int(float(row["QID17"]))
        order = str(row["ProductDisplayOrder"])
        branded = str(row.get("BrandedTarget", "") or "")
        optimal = str(row.get("OptimalProduct", "") or "")
    except Exception:
        return pd.Series([None, None, None])
    # ProductDisplayOrder might be "Brand|Brand|..." or "Brand,Brand,..."
    if "|" in order: products = order.split("|")
    else:            products = order.split(",")
    products = [p.strip() for p in products]
    if not (1 <= qid <= len(products)): return pd.Series([None, None, None])
    chosen = products[qid - 1]
    return pd.Series([chosen, chosen == branded, chosen == optimal])

flt[["chosen", "chose_branded", "chose_optimal"]] = flt.apply(decode, axis=1)
flt = flt.dropna(subset=["chose_branded"]).copy()
flt["chose_branded"] = flt["chose_branded"].astype(bool)
flt["chose_optimal"] = flt["chose_optimal"].astype(bool)
print(f"With decoded choice: {len(flt)}")
print()

print("Per-condition rates:")
for cond, sub in flt.groupby("ConditionD"):
    print(f"  {cond}: N={len(sub)}, "
          f"branded={sub['chose_branded'].mean()*100:.1f}%, "
          f"optimal={sub['chose_optimal'].mean()*100:.1f}%")

# Fisher's exact for each contrast
from scipy.stats import fisher_exact
cond_names = list(flt["ConditionD"].unique())
for c1, c2 in [("BiasedAI", "BiasedAI_Inoc"), ("BiasedAI", "BiasedAI_SpecExp"),
               ("BiasedAI_Inoc", "BiasedAI_SpecExp")]:
    # try matching alternative names
    name_map = {}
    for n in cond_names:
        low = n.lower()
        if "inoc" in low: name_map["BiasedAI_Inoc"] = n
        elif "spec" in low and "exp" in low: name_map["BiasedAI_SpecExp"] = n
        elif "biased" in low and "inoc" not in low and "spec" not in low: name_map["BiasedAI"] = n
    c1n = name_map.get(c1, c1); c2n = name_map.get(c2, c2)
    if c1n not in cond_names or c2n not in cond_names: continue
    a = flt[flt["ConditionD"] == c1n]
    b = flt[flt["ConditionD"] == c2n]
    ka, na = int(a["chose_branded"].sum()), len(a)
    kb, nb = int(b["chose_branded"].sum()), len(b)
    tab = [[ka, na - ka], [kb, nb - kb]]
    try:
        or_, p = fisher_exact(tab, alternative="two-sided")
    except Exception:
        or_, p = float("nan"), float("nan")
    print(f"  {c1n} vs {c2n} on branded: "
          f"{ka/na*100:.1f}% vs {kb/nb*100:.1f}% "
          f"(Δ={ka/na*100 - kb/nb*100:+.1f}pp, OR={or_:.2f}, P={p:.2e})")
