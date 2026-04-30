"""
Analysis script skeleton for Study 1: Confabulation Mechanism
Reads Qualtrics CSV export, computes primary DVs, runs key statistical tests.

Run after downloading CSV from Qualtrics:
  python analyze_study1.py path/to/study1_export.csv
"""
import pandas as pd
import numpy as np
from scipy import stats
import sys

# =====================================================
# QUALTRICS CSV LOADING (3-header-row format)
# =====================================================
def load_qualtrics_csv(path):
    """Load Qualtrics CSV, handling 3 header rows."""
    df = pd.read_csv(path, dtype=str)
    labels = df.iloc[0].to_dict()   # question text row
    df = df.iloc[2:].reset_index(drop=True)  # drop metadata rows
    return df, labels


# =====================================================
# VARIABLE MAPPING
# =====================================================
# Embedded data (set by BlockRandomizer)
ED_VARS = {
    "Condition": int,      # 1=NoAI, 2=BiasedNone, 3=BiasedConfab, 4=Debiased
    "ConditionD": str,     # NoAI / BiasedNone / BiasedConfab / Debiased
    "Category": int,       # 1=earbuds, 2=speakers, 3=ssds
    "CategoryD": str,      # earbuds / speakers / ssds
    "BrandedTarget": str,  # Sony WF-1000XM5 / JBL Flip 6 / Samsung T7 Shield
    "OptimalProduct": str, # Auralis Air4 Pro / Wavecrest StormBox Pro / Vaultdrive PD60
}

# Primary DVs
CHOICE_TAGS = {1: "choice_earbuds", 2: "choice_speakers", 3: "choice_ssds"}
REVISED_TAGS = {1: "revised_earbuds", 2: "revised_speakers", 3: "revised_ssds"}

# Optimal product choice labels (must match MC choice text)
OPTIMAL_CHOICES = {
    1: "Auralis Air4 Pro ($59.99)",
    2: "Wavecrest StormBox Pro ($49.99)",
    3: "Vaultdrive PD60 ($89.99)",
}

BRANDED_CHOICES = {
    1: "Sony WF-1000XM5 ($279.99)",
    2: "JBL Flip 6 ($99.99)",
    3: "Samsung T7 Shield ($149.99)",
}

# Price data for dollar cost computation
PRICES = {
    # earbuds
    "Auralis Air4 Pro ($59.99)": 59.99,
    "Sony WF-1000XM5 ($279.99)": 279.99,
    "Apple AirPods Pro 2 ($249.00)": 249.00,
    "Samsung Galaxy Buds3 Pro ($199.99)": 199.99,
    "Jabra Elite 85t ($179.99)": 179.99,
    # speakers
    "Wavecrest StormBox Pro ($49.99)": 49.99,
    "JBL Flip 6 ($99.99)": 99.99,
    "Bose SoundLink Flex ($119.99)": 119.99,
    "Sony SRS-XB100 ($49.99)": 49.99,
    "UE WONDERBOOM 3 ($79.99)": 79.99,
    # ssds
    "Vaultdrive PD60 ($89.99)": 89.99,
    "Samsung T7 Shield ($149.99)": 149.99,
    "WD My Passport ($139.99)": 139.99,
    "SanDisk Extreme V2 ($119.99)": 119.99,
    "Seagate One Touch ($129.99)": 129.99,
}


def compute_dvs(df):
    """Compute primary dependent variables from raw Qualtrics export."""

    # Convert embedded data
    for var, dtype in ED_VARS.items():
        if var in df.columns:
            df[var] = df[var].astype(dtype) if dtype == str else pd.to_numeric(df[var], errors="coerce")

    # Unify choice across categories
    df["product_choice"] = None
    df["revised_choice"] = None
    for cat in [1, 2, 3]:
        mask = df["Category"] == cat
        choice_col = CHOICE_TAGS[cat]
        revised_col = REVISED_TAGS[cat]
        if choice_col in df.columns:
            df.loc[mask, "product_choice"] = df.loc[mask, choice_col]
        if revised_col in df.columns:
            df.loc[mask, "revised_choice"] = df.loc[mask, revised_col]

    # Compute key DVs
    df["chose_optimal"] = df.apply(
        lambda r: r["product_choice"] == OPTIMAL_CHOICES.get(r.get("Category")), axis=1
    )
    df["chose_branded"] = df.apply(
        lambda r: r["product_choice"] == BRANDED_CHOICES.get(r.get("Category")), axis=1
    )

    # Dollar cost: price of chosen - price of optimal
    df["price_chosen"] = df["product_choice"].map(PRICES)
    df["price_optimal"] = df["Category"].map({1: 59.99, 2: 49.99, 3: 89.99})
    df["dollar_cost"] = df["price_chosen"] - df["price_optimal"]

    # Post-debrief revision
    df["revised"] = df["revise_yn"].str.contains("Yes", na=False)

    # Detection accuracy (only for AI conditions)
    df["detected_brand_bias"] = df["detection"].str.contains("brand", case=False, na=False)

    # Confidence (convert from "X = label" format)
    if "confidence" in df.columns:
        df["confidence_num"] = pd.to_numeric(df["confidence"].str.extract(r"(\d)")[0], errors="coerce")

    return df


def primary_analysis(df):
    """Run primary statistical tests."""
    print("\n" + "=" * 60)
    print("PRIMARY ANALYSIS — Study 1: Confabulation Mechanism")
    print("=" * 60)

    # 1. Overall branded choice rate by condition
    print("\n--- Branded Product Choice Rate by Condition ---")
    for cond in [1, 2, 3, 4]:
        subset = df[df["Condition"] == cond]
        n = len(subset)
        branded = subset["chose_branded"].sum()
        rate = branded / n * 100 if n > 0 else 0
        condD = subset["ConditionD"].iloc[0] if n > 0 else "?"
        print(f"  {condD}: {branded}/{n} = {rate:.1f}%")

    # 2. Key comparison: Confabulated vs No AI
    confab = df[df["Condition"] == 3]["chose_branded"]
    noai = df[df["Condition"] == 1]["chose_branded"]
    if len(confab) > 0 and len(noai) > 0:
        chi2, p = stats.chi2_contingency([
            [confab.sum(), len(confab) - confab.sum()],
            [noai.sum(), len(noai) - noai.sum()]
        ])[:2]
        print(f"\n  Confabulated vs NoAI: chi2={chi2:.2f}, p={p:.4f}")

    # 3. Confabulation premium: Confabulated vs No Justification
    confab = df[df["Condition"] == 3]["chose_branded"]
    nojust = df[df["Condition"] == 2]["chose_branded"]
    if len(confab) > 0 and len(nojust) > 0:
        chi2, p = stats.chi2_contingency([
            [confab.sum(), len(confab) - confab.sum()],
            [nojust.sum(), len(nojust) - nojust.sum()]
        ])[:2]
        print(f"  Confabulated vs NoJust: chi2={chi2:.2f}, p={p:.4f}")

    # 4. Debiased vs No AI
    debiased = df[df["Condition"] == 4]["chose_optimal"]
    noai_opt = df[df["Condition"] == 1]["chose_optimal"]
    if len(debiased) > 0 and len(noai_opt) > 0:
        chi2, p = stats.chi2_contingency([
            [debiased.sum(), len(debiased) - debiased.sum()],
            [noai_opt.sum(), len(noai_opt) - noai_opt.sum()]
        ])[:2]
        print(f"  Debiased vs NoAI (optimal): chi2={chi2:.2f}, p={p:.4f}")

    # 5. Detection accuracy
    print("\n--- Detection Accuracy (AI conditions only) ---")
    ai_df = df[df["Condition"].isin([2, 3, 4])]
    for cond in [2, 3, 4]:
        subset = ai_df[ai_df["Condition"] == cond]
        n = len(subset)
        detected = subset["detected_brand_bias"].sum()
        rate = detected / n * 100 if n > 0 else 0
        condD = subset["ConditionD"].iloc[0] if n > 0 else "?"
        print(f"  {condD}: {detected}/{n} = {rate:.1f}% detected brand bias")

    # 6. Post-debrief revision rate
    print("\n--- Post-Debrief Revision Rate ---")
    for cond in [1, 2, 3, 4]:
        subset = df[df["Condition"] == cond]
        n = len(subset)
        revised = subset["revised"].sum()
        rate = revised / n * 100 if n > 0 else 0
        condD = subset["ConditionD"].iloc[0] if n > 0 else "?"
        print(f"  {condD}: {revised}/{n} = {rate:.1f}% revised")

    # 7. Dollar cost
    print("\n--- Dollar Cost per Biased Recommendation ---")
    for cond in [1, 2, 3, 4]:
        subset = df[df["Condition"] == cond]
        mean_cost = subset["dollar_cost"].mean()
        condD = subset["ConditionD"].iloc[0] if len(subset) > 0 else "?"
        print(f"  {condD}: ${mean_cost:.2f} avg overpayment")

    # 8. Comprehension check pass rate
    print("\n--- Comprehension Check ---")
    # TODO: check if comp answer matches correct answer from EmbeddedData

    # 9. Category breakdown
    print("\n--- Choice Rate by Category ---")
    for cat in [1, 2, 3]:
        subset = df[df["Category"] == cat]
        catD = subset["CategoryD"].iloc[0] if len(subset) > 0 else "?"
        branded = subset["chose_branded"].mean() * 100 if len(subset) > 0 else 0
        optimal = subset["chose_optimal"].mean() * 100 if len(subset) > 0 else 0
        print(f"  {catD}: {branded:.1f}% branded, {optimal:.1f}% optimal (N={len(subset)})")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python analyze_study1.py <qualtrics_export.csv>")
        sys.exit(1)

    path = sys.argv[1]
    print(f"Loading: {path}")
    df, labels = load_qualtrics_csv(path)
    print(f"Loaded {len(df)} responses")

    df = compute_dvs(df)
    primary_analysis(df)
