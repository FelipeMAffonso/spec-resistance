"""
Compute ALL statistics for the spec-resistance manuscript.
Single self-contained script. Run once, prints everything.
"""
import pandas as pd
import numpy as np
from scipy import stats
from pathlib import Path
from itertools import combinations
import warnings
warnings.filterwarnings("ignore")


def wilson_ci(k, n, z=1.96):
    if n == 0:
        return (np.nan, np.nan)
    p = k / n
    denom = 1 + z**2 / n
    centre = p + z**2 / (2 * n)
    spread = z * np.sqrt((p * (1 - p) + z**2 / (4 * n)) / n)
    lo = (centre - spread) / denom
    hi = (centre + spread) / denom
    return (max(0, lo), min(1, hi))


def fp(x, d=2):
    if pd.isna(x):
        return "N/A"
    return f"{x*100:.{d}f}%"


def fci(lo, hi, d=2):
    if pd.isna(lo) or pd.isna(hi):
        return "[N/A]"
    return f"[{lo*100:.{d}f}%, {hi*100:.{d}f}%]"


def cohens_h(p1, p2):
    return 2 * np.arcsin(np.sqrt(p1)) - 2 * np.arcsin(np.sqrt(p2))


def fisher_or(k1, n1, k2, n2):
    table = np.array([[k1, n1 - k1], [k2, n2 - k2]])
    oddsratio, pvalue = stats.fisher_exact(table, alternative="two-sided")
    a, b, c, d = k1, n1 - k1, k2, n2 - k2
    if a == 0 or b == 0 or c == 0 or d == 0:
        a, b, c, d = a + 0.5, b + 0.5, c + 0.5, d + 0.5
    log_or = np.log(a * d / (b * c))
    se = np.sqrt(1 / a + 1 / b + 1 / c + 1 / d)
    ci_lo = np.exp(log_or - 1.96 * se)
    ci_hi = np.exp(log_or + 1.96 * se)
    return oddsratio, (ci_lo, ci_hi), pvalue


def hdr(title, level=1):
    if level == 1:
        print("\n" + "=" * 80)
        print(f"  {title}")
        print("=" * 80)
    else:
        print(f"\n--- {title} ---")


DATA = str(Path(__file__).resolve().parent.parent / "data" / "spec_resistance_CLEAN.csv")
df_all = pd.read_csv(DATA, low_memory=False)
df_all["chose_optimal"] = df_all["chose_optimal"].astype(bool)
df_all["chose_branded"] = df_all["chose_branded"].astype(bool)
df_all["judge_brand_reasoning"] = df_all["judge_brand_reasoning"].map(
    {True: True, "True": True, False: False, "False": False}
)

# All 18 models included in analysis. Gemini 2.5 Pro fails control conditions
# (22% non-optimal) but control_all_familiar = 0%, confirming this reflects
# extreme training-prior resistance rather than instruction-following failure.
# Reported with full detail in Supplementary Note 17.
df = df_all.copy()

# =================================================================
hdr("1. BASICS")
print(f"Total rows (all 18 models): {len(df):,}")
models = sorted(df["model_key"].unique())
print(f"\nUnique models ({len(models)}):")
for m in models:
    print(f"  - {m}")

providers = sorted(df["provider"].unique())
print(f"\nUnique providers ({len(providers)}):")
mbp = df.groupby("provider")["model_key"].unique()
for prov in sorted(mbp.index):
    ml = sorted(mbp[prov])
    print(f"  {prov} ({len(ml)}): {', '.join(ml)}")

conditions = sorted(df["condition"].unique())
print(f"\nUnique conditions ({len(conditions)}):")
for c in conditions:
    n = len(df[df["condition"] == c])
    print(f"  - {c} (N={n:,})")

categories = sorted(df["category"].unique())
print(f"\nUnique categories ({len(categories)}):")
for c in categories:
    print(f"  - {c}")

assortments = sorted(df["assortment_id"].unique())
print(f"\nUnique assortments ({len(assortments)}):")
for a in assortments:
    print(f"  - {a}")

# =================================================================
hdr("2. BASELINE STATISTICS")
bl = df[df["condition"] == "baseline"]
n_bl = len(bl)
k_nb = int((~bl["chose_optimal"]).sum())
r_nb = k_nb / n_bl
ci_bl = wilson_ci(k_nb, n_bl)
print(f"Total baseline trials: {n_bl:,}")
print(f"Non-optimal choices: {k_nb:,}")
print(f"Overall baseline non-optimal rate: {fp(r_nb)}")
print(f"95% Wilson CI: {fci(*ci_bl)}")

hdr("Per-model baseline non-optimal rates (sorted low->high)", 2)
mbl = []
for m in models:
    mb = bl[bl["model_key"] == m]
    n = len(mb)
    k = int((~mb["chose_optimal"]).sum())
    r = k / n if n > 0 else np.nan
    ci = wilson_ci(k, n)
    mbl.append((m, n, k, r, ci))
mbl.sort(key=lambda x: x[3] if not np.isnan(x[3]) else 999)
print(f"{'Model':<25} {'N':>7} {'k':>7} {'Non-opt%':>10} {'95% CI':>25}")
for m, n, k, r, ci in mbl:
    print(f"{m:<25} {n:>7,} {k:>7,} {fp(r):>10} {fci(*ci):>25}")

# =================================================================
hdr("3. CONTROL CONDITIONS")
ctrls = [
    "control_all_familiar",
    "control_brand_reversal",
    "control_comprehension",
    "control_fictional_brands",
]
for cond in ctrls:
    sub = df[df["condition"] == cond]
    n = len(sub)
    ko = int(sub["chose_optimal"].sum())
    kn = n - ko
    ci = wilson_ci(kn, n)
    odr, cior, pv = fisher_or(kn, n, k_nb, n_bl)
    print(f"\n{cond}:")
    print(f"  N={n:,}, Opt={fp(ko / n)}, Non-opt={fp(kn / n)}, CI={fci(*ci)}")
    print(f"  OR vs baseline: {odr:.3f}, CI [{cior[0]:.3f},{cior[1]:.3f}], p={pv:.2e}")

# =================================================================
hdr("4. SPECIFICATION GRADIENT")
pref_lev = [
    "baseline",
    "preference_vague",
    "preference_weighted",
    "preference_explicit",
    "preference_override",
    "preference_constrained",
]
util_lev = [
    "baseline",
    "utility_vague",
    "utility_weighted",
    "utility_explicit",
    "utility_override",
    "utility_constrained",
]

for pname, levs in [("PREFERENCE", pref_lev), ("UTILITY", util_lev)]:
    hdr(f"{pname} pathway", 2)
    pd_ = {}
    print(f"{'Level':<28} {'N':>7} {'k':>7} {'Non-opt%':>10} {'95% CI':>25}")
    for lev in levs:
        sub = df[df["condition"] == lev]
        n = len(sub)
        k = int((~sub["chose_optimal"]).sum())
        r = k / n if n > 0 else np.nan
        ci = wilson_ci(k, n)
        pd_[lev] = (n, k, r, ci)
        print(f"{lev:<28} {n:>7,} {k:>7,} {fp(r):>10} {fci(*ci):>25}")
    if pname == "PREFERENCE":
        wk, ek = "preference_weighted", "preference_explicit"
    else:
        wk, ek = "utility_weighted", "utility_explicit"
    nw, kw, rw, _ = pd_[wk]
    ne, ke, re, _ = pd_[ek]
    odr, cior, pv = fisher_or(kw, nw, ke, ne)
    gap = rw - re
    print(f"\n  Spec gap ({wk} vs {ek}): {gap * 100:+.2f}pp")
    print(f"  OR={odr:.3f}, CI [{cior[0]:.3f},{cior[1]:.3f}], p={pv:.2e}")

# =================================================================
hdr("5. MECHANISM ISOLATION (baseline_* conditions)")
mech = [
    "baseline_brand_blind",
    "baseline_description_minimal",
    "baseline_expert_persona",
    "baseline_price_premium",
    "baseline_badges_removed",
    "baseline_review_equalized",
    "baseline_price_equalized",
    "baseline_review_inverted",
    "baseline_optimal_first",
]
print(f"Ref: baseline N={n_bl:,}, rate={fp(r_nb)}")
print(
    f"\n{'Condition':<35} {'N':>7} {'Non-opt%':>10} {'95% CI':>25} {'OR':>7} {'OR CI':>22} {'P':>12}"
)
for cond in mech:
    sub = df[df["condition"] == cond]
    n = len(sub)
    k = int((~sub["chose_optimal"]).sum())
    r = k / n if n > 0 else np.nan
    ci = wilson_ci(k, n)
    odr, cior, pv = fisher_or(k, n, k_nb, n_bl)
    print(
        f"{cond:<35} {n:>7,} {fp(r):>10} {fci(*ci):>25} {odr:>7.3f} [{cior[0]:.3f},{cior[1]:.3f}] {pv:>12.2e}"
    )

# =================================================================
hdr("6. CONJOINT (mechanism_attribute_swap)")
mas = df[df["condition"] == "mechanism_attribute_swap"]
nm = len(mas)
km = int((~mas["chose_optimal"]).sum())
rm = km / nm if nm > 0 else np.nan
cim = wilson_ci(km, nm)
print(f"N={nm:,}, Non-opt rate={fp(rm)}, CI={fci(*cim)}")
nom = mas[~mas["chose_optimal"]]
if len(nom) > 0:
    fc = nom["chosen_brand_familiarity"].value_counts(normalize=True)
    fr = nom["chosen_brand_familiarity"].value_counts()
    print(f"\nBrand familiarity of non-optimal choices (N={len(nom)}):")
    for fam in ["high", "medium", "low"]:
        print(f"  {fam}: {fc.get(fam, 0) * 100:.1f}% (n={fr.get(fam, 0)})")

# =================================================================
hdr("7. CONFABULATION")
# Confabulation = non-optimal choice where justification cites ATTRIBUTES, not brand.
# brand_reasoning=True means the model DID cite brand (transparent, not confabulating).
# brand_reasoning=False means the model cited only attributes (confabulating).
bln = bl[~bl["chose_optimal"]]
nbn = len(bln)
nanc = int(bln["judge_brand_reasoning"].isna().sum())
bln_valid = bln[bln["judge_brand_reasoning"].notna()]
nbn_valid = len(bln_valid)
brand_cited = int(bln_valid["judge_brand_reasoning"].sum())  # True = cited brand
confab_count = nbn_valid - brand_cited  # False = attribute-only justification = confabulation
confab_rate = confab_count / nbn_valid if nbn_valid > 0 else np.nan
cicf = wilson_ci(confab_count, nbn_valid)
print(f"Baseline non-optimal choices: {nbn:,}")
print(f"  With judge data: {nbn_valid:,} (NaN: {nanc:,})")
print(f"  Brand reasoning cited (transparent): {brand_cited:,} ({fp(brand_cited / nbn_valid if nbn_valid > 0 else np.nan)})")
print(f"  Attribute-only justification (confabulation): {confab_count:,}")
print(f"Confabulation rate: {fp(confab_rate)}, CI={fci(*cicf)}")

hdr("Per-model confabulation rates (baseline non-optimal)", 2)
mcfl = []
for m in models:
    mno = bln_valid[bln_valid["model_key"] == m]
    n = len(mno)
    if n == 0:
        mcfl.append((m, 0, 0, np.nan))
        continue
    br = int(mno["judge_brand_reasoning"].sum())
    cf = n - br  # confabulation = attribute-only
    mcfl.append((m, n, cf, cf / n))
mcfl.sort(key=lambda x: -x[3] if not np.isnan(x[3]) else 0)
print(f"{'Model':<30} {'N':>7} {'Confab':>8} {'Rate':>10}")
for m, n, k, r in mcfl:
    print(f"{m:<30} {n:>7,} {k:>8,} {fp(r):>10}")

hdr("Per-condition confabulation rates (among non-optimal)", 2)
print(f"{'Condition':<40} {'N':>7} {'Valid':>7} {'Confab':>7} {'Rate':>10}")
for cond in sorted(df["condition"].unique()):
    sub = df[(df["condition"] == cond) & (~df["chose_optimal"])]
    n = len(sub)
    if n == 0:
        print(f"{cond:<40} {0:>7} {0:>7} {0:>7} {'N/A':>10}")
        continue
    sub_v = sub[sub["judge_brand_reasoning"].notna()]
    nv = len(sub_v)
    br = int(sub_v["judge_brand_reasoning"].sum())
    cf = nv - br
    print(f"{cond:<40} {n:>7,} {nv:>7,} {cf:>7,} {fp(cf / nv if nv > 0 else np.nan):>10}")

hdr("Spearman: non-opt rate vs confab rate across models", 2)
mri = []
for m in models:
    mb = bl[bl["model_key"] == m]
    n = len(mb)
    no = int((~mb["chose_optimal"]).sum())
    nr_ = no / n if n > 0 else np.nan
    mno = mb[(~mb["chose_optimal"]) & (mb["judge_brand_reasoning"].notna())]
    nn = len(mno)
    br = int(mno["judge_brand_reasoning"].sum()) if nn > 0 else 0
    cf = nn - br  # confabulation = attribute-only
    cr = cf / nn if nn > 0 else np.nan
    mri.append((m, nr_, cr))
vld = [(m, nr_, cr) for m, nr_, cr in mri if not np.isnan(nr_) and not np.isnan(cr)]
if len(vld) >= 3:
    rho, pv = stats.spearmanr([x[1] for x in vld], [x[2] for x in vld])
    print(f"Spearman rho={rho:.4f}, p={pv:.4e} (N={len(vld)} models)")

# =================================================================
hdr("8. ANTI-BRAND CONDITIONS")
abconds = [
    "anti_brand_negative_experience",
    "anti_brand_prefer_unknown",
    "anti_brand_rejection",
]
print(
    f"\n{'Condition':<35} {'N':>7} {'Non-opt%':>10} {'95% CI':>25} {'OR':>10} {'OR CI':>22} {'P':>12}"
)
for cond in abconds:
    sub = df[df["condition"] == cond]
    n = len(sub)
    k = int((~sub["chose_optimal"]).sum())
    r = k / n if n > 0 else np.nan
    ci = wilson_ci(k, n)
    odr, cior, pv = fisher_or(k, n, k_nb, n_bl)
    print(
        f"{cond:<35} {n:>7,} {fp(r):>10} {fci(*ci):>25} {odr:>10.3f} [{cior[0]:.3f},{cior[1]:.3f}] {pv:>12.2e}"
    )

# =================================================================
hdr("9. CROSS-MODEL CORRELATIONS (assortment-level baseline)")
bla = (
    bl.groupby(["model_key", "assortment_id"])["chose_optimal"]
    .apply(lambda x: 1 - x.mean())
    .unstack(level="assortment_id")
)
bla = bla.dropna(axis=1)
print(f"Models: {bla.shape[0]}, Assortments: {bla.shape[1]}")
corr_m = bla.T.corr(method="pearson")
pairs = list(combinations(bla.index, 2))
ars = []
wip = []
crp = []
# Use developer (not API routing provider) for within/cross decomposition
mprov = {
    'claude-haiku-4.5': 'anthropic', 'claude-sonnet-4.6': 'anthropic',
    'gpt-4.1-mini': 'openai', 'gpt-4.1-nano': 'openai', 'gpt-4o': 'openai',
    'gpt-4o-mini': 'openai', 'gpt-5-mini': 'openai',
    'gemini-2.0-flash': 'google', 'gemini-2.5-flash': 'google',
    'gemini-2.5-flash-lite': 'google', 'gemini-2.5-pro': 'google',
    'gemini-3-flash': 'google', 'gemma-3-27b': 'google',
    'deepseek-r1': 'deepseek', 'deepseek-v3': 'deepseek',
    'kimi-k2': 'moonshot', 'llama-3.3-70b': 'meta', 'qwen-2.5-72b': 'alibaba',
}
for m1, m2 in pairs:
    r = corr_m.loc[m1, m2]
    ars.append((m1, m2, r))
    if mprov.get(m1) == mprov.get(m2):
        wip.append(r)
    else:
        crp.append(r)
rv = [x[2] for x in ars]
print(f"\nAll pairs: N={len(rv)}, Mean r={np.mean(rv):.4f}, Median={np.median(rv):.4f}")
print(f"  Min={np.min(rv):.4f}, Max={np.max(rv):.4f}, SD={np.std(rv):.4f}")
if wip:
    print(f"\nWithin-provider: N={len(wip)}, Mean r={np.mean(wip):.4f}")
if crp:
    print(f"Cross-provider: N={len(crp)}, Mean r={np.mean(crp):.4f}")
hk = "claude-haiku-4.5"
go = "gpt-4o"
if hk in corr_m.index and go in corr_m.index:
    print(f"\nClaude Haiku 4.5 & GPT-4o: r = {corr_m.loc[hk, go]:.4f}")
sp = sorted(ars, key=lambda x: x[2])
print("\nBottom 5:")
for m1, m2, r in sp[:5]:
    print(f"  {m1} & {m2}: r={r:.4f}")
print("Top 5:")
for m1, m2, r in sp[-5:]:
    print(f"  {m1} & {m2}: r={r:.4f}")

# =================================================================
hdr("10. OPEN-SOURCE vs PROPRIETARY")
os_m = [
    "llama-3.3-70b",
    "deepseek-v3",
    "deepseek-r1",
    "qwen-2.5-72b",
    "gemma-3-27b",
    "kimi-k2",
]
pr_m = [m for m in models if m not in os_m]
print(f"Open-source ({len(os_m)}): {', '.join(sorted(os_m))}")
print(f"Proprietary ({len(pr_m)}): {', '.join(sorted(pr_m))}")
bos = bl[bl["model_key"].isin(os_m)]
bpr = bl[bl["model_key"].isin(pr_m)]
nos = len(bos)
kos = int((~bos["chose_optimal"]).sum())
ros = kos / nos if nos > 0 else np.nan
nprp = len(bpr)
kpr = int((~bpr["chose_optimal"]).sum())
rpr = kpr / nprp if nprp > 0 else np.nan
cios = wilson_ci(kos, nos)
cipr = wilson_ci(kpr, nprp)
print(f"\nOpen-source: N={nos:,}, rate={fp(ros)}, CI={fci(*cios)}")
print(f"Proprietary: N={nprp:,}, rate={fp(rpr)}, CI={fci(*cipr)}")
print(f"Gap (open-prop): {(ros - rpr) * 100:+.2f} pp")
odr2, cior2, pv2 = fisher_or(kos, nos, kpr, nprp)
print(f"Fisher OR: {odr2:.3f}, CI [{cior2[0]:.3f},{cior2[1]:.3f}], p={pv2:.2e}")

# =================================================================
hdr("11. CATEGORY-LEVEL BASELINE NON-OPTIMAL RATES")
catd = []
for cat in sorted(df["category"].unique()):
    sub = bl[bl["category"] == cat]
    n = len(sub)
    k = int((~sub["chose_optimal"]).sum())
    r = k / n if n > 0 else np.nan
    ci = wilson_ci(k, n)
    catd.append((cat, n, k, r, ci))
catd.sort(key=lambda x: -x[3])
print(f"{'Category':<25} {'N':>7} {'k':>7} {'Non-opt%':>10} {'95% CI':>25}")
for cat, n, k, r, ci in catd:
    print(f"{cat:<25} {n:>7,} {k:>7,} {fp(r):>10} {fci(*ci):>25}")
zc = [cat for cat, n, k, r, ci in catd if r == 0]
if zc:
    print(f"\nCategories with 0% misalignment: {', '.join(zc)}")
else:
    print("\nNo categories have exactly 0% misalignment.")

# =================================================================
hdr("12. VAGUE PARADOX (baseline -> preference_vague)")
pvdf = df[df["condition"] == "preference_vague"]
print(
    f"{'Model':<25} {'BL N':>7} {'BL%':>10} {'VG N':>7} {'VG%':>10} {'Chg':>10} {'P':>12} {'Sig':>5}"
)
for m in sorted(models):
    mb = bl[bl["model_key"] == m]
    mv = pvdf[pvdf["model_key"] == m]
    nb_ = len(mb)
    kb_ = int((~mb["chose_optimal"]).sum())
    rb_ = kb_ / nb_ if nb_ > 0 else np.nan
    nv_ = len(mv)
    kv_ = int((~mv["chose_optimal"]).sum())
    rv_ = kv_ / nv_ if nv_ > 0 else np.nan
    if nb_ > 0 and nv_ > 0:
        _, pval = stats.fisher_exact(
            [[kv_, nv_ - kv_], [kb_, nb_ - kb_]], alternative="greater"
        )
        chg = rv_ - rb_
        sig = "YES" if pval < 0.05 else "no"
        print(
            f"{m:<25} {nb_:>7,} {fp(rb_):>10} {nv_:>7,} {fp(rv_):>10} {chg * 100:>+9.2f}pp {pval:>12.4e} {sig:>5}"
        )

# =================================================================
hdr("13. PRICE PREMIUM")
ppd = df[df["condition"] == "baseline_price_premium"]
npp = len(ppd)
kpp = int((~ppd["chose_optimal"]).sum())
rpp = kpp / npp if npp > 0 else np.nan
cipp = wilson_ci(kpp, npp)
hpp = cohens_h(rpp, r_nb)
print(f"N = {npp:,}")
print(f"Non-optimal rate: {fp(rpp)}")
print(f"95% CI: {fci(*cipp)}")
print(f"Baseline rate: {fp(r_nb)}")
print(f"Cohens h: {hpp:.4f}")
odr3, cior3, pv3 = fisher_or(kpp, npp, k_nb, n_bl)
print(f"Fisher OR vs baseline: {odr3:.3f}, CI [{cior3[0]:.3f},{cior3[1]:.3f}], p={pv3:.2e}")

# =================================================================
hdr("14. ALL CONDITIONS TABLE")
ac = sorted(df["condition"].unique())
print(
    f"\n{'Condition':<35} {'N':>7} {'Non-opt%':>10} {'95% CI':>25} {'Cohen h':>9} {'Fisher P':>12}"
)
print("-" * 100)
for cond in ac:
    sub = df[df["condition"] == cond]
    n = len(sub)
    k = int((~sub["chose_optimal"]).sum())
    r = k / n if n > 0 else np.nan
    ci = wilson_ci(k, n)
    h = cohens_h(r, r_nb) if not np.isnan(r) else np.nan
    if cond == "baseline":
        print(
            f"{'baseline':<35} {n:>7,} {fp(r):>10} {fci(*ci):>25} {'ref':>9} {'ref':>12}"
        )
    else:
        _, _, pval = fisher_or(k, n, k_nb, n_bl)
        print(
            f"{cond:<35} {n:>7,} {fp(r):>10} {fci(*ci):>25} {h:>+9.4f} {pval:>12.2e}"
        )

# =================================================================
hdr("15. CLAUDE-SONNET-4.6 SPECIFIC")
cs = df[df["model_key"] == "claude-sonnet-4.6"]
if len(cs) == 0:
    print("Not found in data.")
else:
    print(f"Total trials: {len(cs):,}")
    csb = cs[cs["condition"] == "baseline"]
    nc = len(csb)
    kc = int((~csb["chose_optimal"]).sum())
    rc = kc / nc if nc > 0 else np.nan
    cic = wilson_ci(kc, nc)
    print(f"\nBaseline: N={nc:,}, non-opt={fp(rc)}, CI={fci(*cic)}")
    print(f"\n{'Condition':<35} {'N':>7} {'Non-opt%':>10} {'95% CI':>25}")
    for cond in ac:
        sub = cs[cs["condition"] == cond]
        n = len(sub)
        if n == 0:
            continue
        k = int((~sub["chose_optimal"]).sum())
        r = k / n
        ci = wilson_ci(k, n)
        print(f"{cond:<35} {n:>7,} {fp(r):>10} {fci(*ci):>25}")
    csno = csb[~csb["chose_optimal"]]
    ncn = len(csno)
    if ncn > 0:
        kcf = int(csno["judge_brand_reasoning"].sum())
        rcf2 = kcf / ncn
        cicf2 = wilson_ci(kcf, ncn)
        print(f"\nConfabulation: N non-opt={ncn}, brand_reasoning={kcf}")
        print(f"  Rate={fp(rcf2)}, CI={fci(*cicf2)}")
    else:
        print("\nNo non-optimal baseline choices (perfect alignment).")

# =================================================================
hdr("BONUS: MECHANISM CONDITIONS (mechanism_*)")
mconds = [c for c in ac if c.startswith("mechanism_")]
print(
    f"\n{'Condition':<35} {'N':>7} {'Non-opt%':>10} {'95% CI':>25} {'OR':>10} {'OR CI':>22} {'P':>12}"
)
for cond in mconds:
    sub = df[df["condition"] == cond]
    n = len(sub)
    k = int((~sub["chose_optimal"]).sum())
    r = k / n if n > 0 else np.nan
    ci = wilson_ci(k, n)
    odr, cior, pv = fisher_or(k, n, k_nb, n_bl)
    print(
        f"{cond:<35} {n:>7,} {fp(r):>10} {fci(*ci):>25} {odr:>10.3f} [{cior[0]:.3f},{cior[1]:.3f}] {pv:>12.2e}"
    )

# =================================================================
hdr("BONUS: OVERALL SUMMARY")
tc = df["cost_usd"].sum()
ti = df["input_tokens"].sum()
to_ = df["output_tokens"].sum()
md = df["duration_seconds"].mean()
print(f"Total cost: ${tc:,.2f}")
print(f"Total input tokens: {ti:,.0f}")
print(f"Total output tokens: {to_:,.0f}")
print(f"Mean response duration: {md:.2f}s")
ccount = len(sorted(df["condition"].unique()))
catcount = len(sorted(df["category"].unique()))
acount = len(sorted(df["assortment_id"].unique()))
print(
    f"Conditions: {ccount}, Models: {len(models)}, Categories: {catcount}, Assortments: {acount}"
)

# =================================================================
hdr("16. CONFABULATION BY SPECIFICATION LEVEL")
# Key for manuscript: confab rate across specification gradient
spec_confab = []
for cond in ["baseline", "preference_vague", "preference_weighted", "utility_vague", "utility_weighted"]:
    sub = df[(df["condition"] == cond) & (~df["chose_optimal"])]
    sub_v = sub[sub["judge_brand_reasoning"].notna()]
    nv = len(sub_v)
    br = int(sub_v["judge_brand_reasoning"].sum())
    cf = nv - br
    r = cf / nv if nv > 0 else np.nan
    ci = wilson_ci(cf, nv)
    spec_confab.append((cond, nv, cf, r, ci))
    print(f"{cond:<30} N={nv:>5,}, Confab={cf:>5,}, Rate={fp(r)}, CI={fci(*ci)}")

# Anti-brand confabulation
print()
for cond in ["anti_brand_rejection", "anti_brand_negative_experience", "anti_brand_prefer_unknown"]:
    sub = df[(df["condition"] == cond) & (~df["chose_optimal"])]
    sub_v = sub[sub["judge_brand_reasoning"].notna()]
    nv = len(sub_v)
    br = int(sub_v["judge_brand_reasoning"].sum())
    cf = nv - br
    r = cf / nv if nv > 0 else np.nan
    ci = wilson_ci(cf, nv)
    print(f"{cond:<40} N={nv:>5,}, Confab={cf:>5,}, Rate={fp(r)}, CI={fci(*ci)}")

# =================================================================
hdr("17. GEMINI 2.5 PRO CONTROL PERFORMANCE")
g25p = df[df["model_key"] == "gemini-2.5-pro"]
for cond in ctrls:
    sub = g25p[g25p["condition"] == cond]
    n = len(sub)
    k = int((~sub["chose_optimal"]).sum())
    r = k / n if n > 0 else np.nan
    ci = wilson_ci(k, n)
    print(f"{cond:<30} N={n:,}, Non-opt={fp(r)}, CI={fci(*ci)}")

# =================================================================
# Export JSON for manuscript number reconciliation
import json
import os

export = {
    "data_file": "spec_resistance_CLEAN.csv",
    "total_trials": len(df),
    "n_models": len(models),
    "models": models,
    "n_conditions": len(conditions),
    "n_categories": len(categories),
    "n_assortments": len(assortments),
    "baseline": {
        "n": n_bl,
        "non_optimal_k": k_nb,
        "non_optimal_rate": round(r_nb, 6),
        "ci_lo": round(ci_bl[0], 6),
        "ci_hi": round(ci_bl[1], 6),
    },
    "confabulation": {
        "baseline_non_optimal_n": nbn,
        "baseline_valid_n": nbn_valid,
        "confabulation_count": confab_count,
        "confabulation_rate": round(confab_rate, 6),
        "ci_lo": round(cicf[0], 6),
        "ci_hi": round(cicf[1], 6),
        "brand_cited_count": brand_cited,
        "brand_cited_rate": round(brand_cited / nbn_valid, 6) if nbn_valid > 0 else None,
    },
}

outpath = os.path.join(os.path.dirname(__file__), "..", "data", "manuscript_numbers.json")
with open(outpath, "w") as f:
    json.dump(export, f, indent=2)
print(f"\nExported manuscript numbers to: {outpath}")

print("\n" + "=" * 80)
print("  ALL STATISTICS COMPUTED SUCCESSFULLY")
print("=" * 80)
