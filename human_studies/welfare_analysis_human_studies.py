"""Welfare analysis from the four pre-registered human studies.

Uses the author's verified DV protocol (per
`reverify_studies_1A_1B_2.py` and the prereg files):
  - Study 1A/1B/2: branded = QID17 == 2 ; optimal = QID17 == 4
    (QID17 stores the underlying product index, not the display position)
  - Study 3: chose_focal_bool / chose_optimal_bool / study3_product_choice

Pre-registered exclusions:
  - consent == 1
  - Finished == 1
  - attn_check == 4
  - Duration (in seconds) >= 60
"""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats


HERE = Path(__file__).resolve().parent
# When this script lives inside OSF/human_studies/ the data folders are siblings.
# When this script lives inside scripts/ the data folders are at ../OSF/human_studies/.
if (HERE / "study1a-coffee" / "anonymised.csv").exists():
    HS = HERE
else:
    HS = HERE.parent / "OSF" / "human_studies"


# --- prices for the fixed five-product assortments in Studies 1A/1B/2 ---
# Coffee makers (Study 1A): QID17 maps to {1: Nespresso, 2: De'Longhi (focal),
# 3: Breville, 4: Presswell* (spec-optimal), 5: Philips}.
prices_1a = {1: 159.99, 2: 119.99, 3: 399.95, 4: 99.99, 5: 599.99}
# Earbuds (Study 1B + Study 2): QID17 maps to {1: Beats, 2: JBL (focal),
# 3: Shokz, 4: Vynex* (spec-optimal), 5: Sony}.
prices_1b = {1: 159.99, 2: 49.99, 3: 179.99, 4: 39.99, 5: 129.99}


def apply_excl(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df = df[df["consent"].fillna(0).astype(int) == 1]
    df = df[df["Finished"].fillna(0).astype(int) == 1]
    df = df[df["attn_check"].fillna(0).astype(int) == 4]
    df = df[df["Duration (in seconds)"].fillna(0).astype(int) >= 60]
    return df


def boot_diff_ci(a: np.ndarray, b: np.ndarray, n: int = 4000, seed: int = 7):
    rng = np.random.default_rng(seed)
    diffs = np.empty(n)
    for i in range(n):
        sa = rng.choice(a, size=len(a), replace=True)
        sb = rng.choice(b, size=len(b), replace=True)
        diffs[i] = sa.mean() - sb.mean()
    return float(np.mean(a) - np.mean(b)), float(np.percentile(diffs, 2.5)), float(np.percentile(diffs, 97.5))


def study_1a_1b_2(label: str, csvname: str, prices: dict, conditions: list):
    df = apply_excl(pd.read_csv(HS / csvname, low_memory=False))
    df["paid"] = df["QID17"].astype("Int64").map(prices)
    df["overpay"] = df["paid"] - prices[4]
    print(f"\n--- Study {label} (N = {len(df)} after exclusions) ---")
    print(f"  branded = QID17==2 (${prices[2]:.2f}); optimal = QID17==4 (${prices[4]:.2f}); structural premium ${prices[2]-prices[4]:.2f}")
    print(f"  {'Cond':<14}{'N':>4}{'%branded':>10}{'%optimal':>10}{'Mean paid':>12}{'Mean overpay':>14}{'% overpaid':>12}{'Aggregate $':>14}")
    out = {}
    for c in conditions:
        s = df[df["ConditionD"] == c]
        out[c] = s
        pb = s["QID17"].eq(2).mean() * 100
        po = s["QID17"].eq(4).mean() * 100
        mp = s["paid"].mean()
        mo = s["overpay"].mean()
        po2 = (s["overpay"] > 0).mean() * 100
        agg = s["overpay"].sum()
        print(f"  {c:<14}{len(s):>4}{pb:>9.1f}%{po:>9.1f}%  ${mp:>9.2f}  ${mo:>10.2f}{po2:>11.1f}%   ${agg:>10,.0f}")
    return df, out


def study_3():
    df = pd.read_csv(HS / "study3-chatbot" / "anonymised.csv", low_memory=False)
    for c in ["dom_price_num", "rec_price_num", "price_gap_usd"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    def parse_price(s):
        if pd.isna(s):
            return None
        m = re.search(r"\$([0-9,]+\.?[0-9]*)", str(s))
        return float(m.group(1).replace(",", "")) if m else None

    def match_choice(row):
        c = row["study3_product_choice"]
        if pd.isna(c):
            return None
        for i in range(1, 8):
            prod = row.get(f"product_{i}")
            if pd.notna(prod) and str(c).strip() in str(prod):
                return parse_price(prod)
        return None

    df["paid"] = df.apply(match_choice, axis=1)
    df["overpay"] = df["paid"] - df["dom_price_num"]
    print(f"\n--- Study 3 (N = {len(df)}; server-verified strict-dominance assortments) ---")
    print(f"  {'Cond':<10}{'N':>4}{'%focal':>9}{'%opt':>8}{'Mean paid':>12}{'Mean overpay':>14}{'Med overpay':>13}{'% overpaid':>12}{'Aggregate $':>14}")
    out = {}
    for c in ["neutral", "honest", "biased"]:
        s = df[df["study3_condition"] == c]
        out[c] = s
        pf = s["chose_focal_bool"].mean() * 100
        po = s["chose_optimal_bool"].mean() * 100
        mp = s["paid"].mean()
        mo = s["overpay"].mean()
        md = s["overpay"].median()
        po2 = (s["overpay"] > 0).mean() * 100
        agg = s["overpay"].sum()
        print(f"  {c:<10}{len(s):>4}{pf:>8.1f}%{po:>7.1f}%  ${mp:>9.2f}  ${mo:>10.2f}{md:>12.2f}{po2:>11.1f}%   ${agg:>10,.0f}")
    return df, out


def main():
    print("=" * 110)
    print("  BEHAVIOURAL WELFARE ANALYSIS — pre-registered exclusions, author's DV protocol")
    print("=" * 110)

    df1a, c1a = study_1a_1b_2("1A coffee makers", "study1a-coffee/anonymised.csv", prices_1a, ["NoAI", "BiasedAI", "DebiasedAI"])
    df1b, c1b = study_1a_1b_2("1B earbuds", "study1b-earbuds/anonymised.csv", prices_1b, ["NoAI", "BiasedAI", "DebiasedAI"])
    df2, c2 = study_1a_1b_2("2 inoculation", "study2-inoculation/anonymised.csv", prices_1b, ["BiasedAI", "BiasedAI_Inoculation", "BiasedAI_SpecExposed"])
    df3, c3 = study_3()

    print("\n" + "=" * 110)
    print("  WELFARE CONTRASTS · per-participant overpayment difference (Welch t-tests, bootstrap CIs)")
    print("=" * 110)

    for label, sa, sb, name in [
        ("Study 1A", c1a["BiasedAI"]["overpay"], c1a["NoAI"]["overpay"], "BiasedAI - NoAI"),
        ("Study 1A", c1a["DebiasedAI"]["overpay"], c1a["NoAI"]["overpay"], "DebiasedAI - NoAI"),
        ("Study 1A", c1a["BiasedAI"]["overpay"], c1a["DebiasedAI"]["overpay"], "BiasedAI - DebiasedAI (welfare swing)"),
        ("Study 1B", c1b["BiasedAI"]["overpay"], c1b["NoAI"]["overpay"], "BiasedAI - NoAI"),
        ("Study 1B", c1b["DebiasedAI"]["overpay"], c1b["NoAI"]["overpay"], "DebiasedAI - NoAI"),
        ("Study 1B", c1b["BiasedAI"]["overpay"], c1b["DebiasedAI"]["overpay"], "BiasedAI - DebiasedAI (welfare swing)"),
        ("Study 2",  c2["BiasedAI_Inoculation"]["overpay"], c2["BiasedAI"]["overpay"], "Inoculation - BiasedAI"),
        ("Study 2",  c2["BiasedAI_SpecExposed"]["overpay"], c2["BiasedAI"]["overpay"], "SpecExposed - BiasedAI"),
        ("Study 3",  c3["biased"]["overpay"].dropna(), c3["neutral"]["overpay"].dropna(), "Biased - Neutral"),
        ("Study 3",  c3["honest"]["overpay"].dropna(), c3["neutral"]["overpay"].dropna(), "Honest - Neutral"),
        ("Study 3",  c3["biased"]["overpay"].dropna(), c3["honest"]["overpay"].dropna(), "Biased - Honest (welfare swing)"),
    ]:
        diff, lo, hi = boot_diff_ci(sa.values, sb.values)
        t, p = stats.ttest_ind(sa, sb, equal_var=False)
        print(f"  {label} {name:<42}: ${diff:+7.2f}  95% CI [${lo:+7.2f}, ${hi:+7.2f}]  Welch t = {t:6.2f}  P = {p:.3g}")

    print("\n" + "=" * 110)
    print("  PER-MILLION EXTRAPOLATIONS (cost of biased AI relative to honest AI per one million AI-mediated purchases)")
    print("=" * 110)
    for label, sa, sb, name in [
        ("Study 1A", c1a["BiasedAI"]["overpay"], c1a["DebiasedAI"]["overpay"], "coffee makers"),
        ("Study 1B", c1b["BiasedAI"]["overpay"], c1b["DebiasedAI"]["overpay"], "wireless earbuds"),
        ("Study 3",  c3["biased"]["overpay"].dropna(), c3["honest"]["overpay"].dropna(), "ecological chatbot"),
    ]:
        diff = sa.mean() - sb.mean()
        print(f"  {label} ({name:<22}): ${diff:+7.2f} per participant  -->  ${diff*1e6:+,.0f} per million biased AI shopping recommendations")


if __name__ == "__main__":
    main()
