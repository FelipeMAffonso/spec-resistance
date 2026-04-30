"""
Brand Frequency Analysis for Spec-Resistance Project
======================================================
Merges infini-gram brand-frequency data with experiment results to test
whether LLMs' brand bias correlates with pre-training exposure (measured
by n-gram frequency in training corpora).

Core hypothesis: Models favor brands that appear more frequently in their
training data. If specification resistance is driven by training-data
exposure rather than quality inference, we should see a positive
correlation between log(brand frequency) and non-optimal choice rate
conditional on that brand being the non-optimal option.

Inputs:
    - data/brand_frequencies.csv  (from brand_frequency_scanner.py)
    - data/processed/spec_resistance_FRESH.csv  (main experiment data)

Outputs:
    - data/brand_frequency_merged.csv
    - data/brand_frequency_figure.pdf
    - data/brand_frequency_figure.png
    - data/regression_results.txt

Usage:
    python scripts/brand_frequency_analysis.py
"""

import csv
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from scipy import stats

# Try statsmodels for regression; fall back gracefully
try:
    import statsmodels.api as sm
    import statsmodels.formula.api as smf
    HAS_STATSMODELS = True
except ImportError:
    HAS_STATSMODELS = False
    warnings.warn(
        "statsmodels not installed. Regression analysis will use scipy only. "
        "Install with: pip install statsmodels"
    )

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent  # spec-resistance/
NATURE_RR_DIR = SCRIPT_DIR.parent

FREQ_CSV = NATURE_RR_DIR / "data" / "brand_frequencies.csv"
EXPERIMENT_CSV = PROJECT_ROOT / "data" / "processed" / "spec_resistance_FRESH.csv"
OUTPUT_DIR = NATURE_RR_DIR / "data"
MERGED_CSV = OUTPUT_DIR / "brand_frequency_merged.csv"
FIGURE_PDF = OUTPUT_DIR / "brand_frequency_figure.pdf"
FIGURE_PNG = OUTPUT_DIR / "brand_frequency_figure.png"
REGRESSION_TXT = OUTPUT_DIR / "regression_results.txt"


# ---------------------------------------------------------------------------
# Category metadata (mirroring assortments.py)
# ---------------------------------------------------------------------------

CATEGORY_METADATA = {
    "laptops":               {"involvement": "high", "hedonic": False, "brand_salience": "high"},
    "smartphones":           {"involvement": "high", "hedonic": False, "brand_salience": "high"},
    "tvs":                   {"involvement": "high", "hedonic": False, "brand_salience": "high"},
    "cameras":               {"involvement": "high", "hedonic": True,  "brand_salience": "high"},
    "tablets":               {"involvement": "high", "hedonic": False, "brand_salience": "high"},
    "headphones":            {"involvement": "mid",  "hedonic": True,  "brand_salience": "high"},
    "wireless_earbuds":      {"involvement": "mid",  "hedonic": True,  "brand_salience": "high"},
    "running_shoes":         {"involvement": "mid",  "hedonic": True,  "brand_salience": "medium"},
    "smartwatches":          {"involvement": "mid",  "hedonic": False, "brand_salience": "high"},
    "robot_vacuums":         {"involvement": "mid",  "hedonic": False, "brand_salience": "medium"},
    "portable_speakers":     {"involvement": "low",  "hedonic": True,  "brand_salience": "medium"},
    "keyboards":             {"involvement": "low",  "hedonic": False, "brand_salience": "low"},
    "external_ssds":         {"involvement": "low",  "hedonic": False, "brand_salience": "low"},
    "water_bottles":         {"involvement": "low",  "hedonic": True,  "brand_salience": "low"},
    "electric_toothbrushes": {"involvement": "low",  "hedonic": True,  "brand_salience": "medium"},
    "coffee_makers":         {"involvement": "mid",  "hedonic": True,  "brand_salience": "medium"},
    "blenders":              {"involvement": "mid",  "hedonic": True,  "brand_salience": "high"},
    "backpacks":             {"involvement": "mid",  "hedonic": True,  "brand_salience": "low"},
    "wireless_routers":      {"involvement": "mid",  "hedonic": False, "brand_salience": "medium"},
    "monitors":              {"involvement": "mid",  "hedonic": False, "brand_salience": "medium"},
}

# Map assortment IDs to the brand that is optimal
# We need this to know which brand was "optimal" in each assortment,
# so we can compute the rate of choosing branded (non-optimal) alternatives.
# This mapping will be built dynamically from the experiment data.


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_brand_frequencies() -> pd.DataFrame:
    """
    Load brand frequency data and aggregate across variants.

    For each brand x corpus combination, we take the MAX count across
    all spelling variants (the canonical form usually dominates, but
    sometimes a lowercase or alternate spelling has more hits).
    """
    df = pd.read_csv(FREQ_CSV)
    print(f"Loaded {len(df)} raw frequency rows for {df['brand_name'].nunique()} brands")

    # Filter out failed queries
    df = df[df["raw_count"] >= 0].copy()

    # --- Brand-only queries (category == "all") ---
    brand_only = df[df["category"] == "all"].copy()

    # Aggregate: max count across variants, per brand x corpus
    brand_agg = (
        brand_only
        .groupby(["brand_name", "corpus", "is_fictional", "familiarity_tier"])
        .agg(
            max_count=("raw_count", "max"),
            sum_count=("raw_count", "sum"),
            n_variants=("raw_count", "count"),
        )
        .reset_index()
    )

    # --- Brand + category queries ---
    brand_cat = df[df["category"] != "all"].copy()

    brand_cat_agg = (
        brand_cat
        .groupby(["brand_name", "corpus", "category", "is_fictional", "familiarity_tier"])
        .agg(category_count=("raw_count", "max"))
        .reset_index()
    )

    return brand_agg, brand_cat_agg


def load_experiment_data() -> pd.DataFrame:
    """
    Load experiment data and compute non-optimal choice rates by brand context.
    """
    df = pd.read_csv(EXPERIMENT_CSV)
    print(f"Loaded {len(df)} experiment trials across {df['model_key'].nunique()} models")
    print(f"Categories: {sorted(df['category'].unique())}")

    return df


# ---------------------------------------------------------------------------
# Analysis functions
# ---------------------------------------------------------------------------

def compute_brand_bias_rates(exp_df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute the rate at which each brand's familiarity tier is chosen
    when it is NOT the optimal product.

    We group by: category, chosen_brand_familiarity, and compute the
    rate of choosing non-optimal (chose_optimal == False).

    For the brand-frequency correlation, we need brand-level rates.
    Since the experiment data doesn't have the exact chosen brand name
    (only familiarity tier), we aggregate at the tier level.
    """
    # Non-optimal choice rate by category
    cat_rates = (
        exp_df
        .groupby("category")
        .agg(
            n_trials=("chose_optimal", "count"),
            n_non_optimal=("chose_optimal", lambda x: (~x.astype(bool)).sum()),
            non_optimal_rate=("chose_optimal", lambda x: 1 - x.astype(float).mean()),
        )
        .reset_index()
    )

    # Non-optimal choice rate by category x familiarity of chosen brand
    cat_fam_rates = (
        exp_df
        .groupby(["category", "chosen_brand_familiarity"])
        .agg(
            n_trials=("chose_optimal", "count"),
            n_chose_this=("chose_optimal", "count"),  # how many times this tier was chosen
        )
        .reset_index()
    )

    # Brand-level choice rate conditioned on specification resistance
    # When the model ignores specs and picks a branded option
    sr_rates = (
        exp_df[exp_df["specification_resistance"].astype(str) == "True"]
        .groupby(["category", "chosen_brand_familiarity"])
        .agg(n_sr_choices=("chose_optimal", "count"))
        .reset_index()
    )

    return cat_rates, cat_fam_rates, sr_rates


def merge_frequency_with_behavior(
    brand_agg: pd.DataFrame,
    cat_rates: pd.DataFrame,
    brand_cat_agg: pd.DataFrame,
) -> pd.DataFrame:
    """
    Create the merged dataset for correlation analysis.

    Strategy: For each brand, compute:
      1. log(max_count) across corpora (average or RedPajama-specific)
      2. The non-optimal choice rate for its category
      3. Category-level controls (involvement, hedonic, brand_salience)
    """
    # Use RedPajama as primary corpus (largest, most representative)
    rpj = brand_agg[brand_agg["corpus"] == "RedPajama"].copy()

    # Also compute cross-corpus average
    cross_corpus = (
        brand_agg
        .groupby(["brand_name", "is_fictional", "familiarity_tier"])
        .agg(
            avg_max_count=("max_count", "mean"),
            total_max_count=("max_count", "sum"),
        )
        .reset_index()
    )

    # Merge RedPajama counts with cross-corpus average
    merged = rpj.merge(
        cross_corpus,
        on=["brand_name", "is_fictional", "familiarity_tier"],
        how="left",
    )

    # Add log transforms (add 1 to handle zeros)
    merged["log_count_rpj"] = np.log1p(merged["max_count"])
    merged["log_count_avg"] = np.log1p(merged["avg_max_count"])
    merged["log_count_total"] = np.log1p(merged["total_max_count"])

    # Add category-level non-optimal rates
    # Each brand maps to one or more categories; we'll create one row per brand-category
    # First, build brand -> categories mapping from brand_cat_agg
    brand_cats = (
        brand_cat_agg[brand_cat_agg["corpus"] == "RedPajama"]
        .groupby("brand_name")["category"]
        .apply(list)
        .to_dict()
    )

    # Explode: one row per brand x category
    rows = []
    for _, row in merged.iterrows():
        brand = row["brand_name"]
        cats = brand_cats.get(brand, [])
        if not cats:
            # Brand-only query, no category-specific data;
            # still include with category="all"
            rows.append({**row.to_dict(), "category": "all"})
        else:
            for cat in cats:
                rows.append({**row.to_dict(), "category": cat})

    expanded = pd.DataFrame(rows)

    # Merge with category non-optimal rates
    expanded = expanded.merge(cat_rates, on="category", how="left")

    # Add category metadata
    for cat, meta in CATEGORY_METADATA.items():
        mask = expanded["category"] == cat
        for key, val in meta.items():
            expanded.loc[mask, key] = val

    # Encode involvement as ordinal
    involvement_map = {"low": 1, "mid": 2, "high": 3}
    expanded["involvement_ordinal"] = expanded["involvement"].map(involvement_map)

    # Encode brand_salience as ordinal
    salience_map = {"low": 1, "medium": 2, "high": 3}
    expanded["brand_salience_ordinal"] = expanded["brand_salience"].map(salience_map)

    # Encode hedonic as binary
    expanded["hedonic_binary"] = expanded["hedonic"].astype(float)

    # Encode is_fictional as binary
    expanded["is_fictional_binary"] = expanded["is_fictional"].astype(float)

    # Encode familiarity tier as ordinal
    fam_map = {"low": 1, "medium": 2, "high": 3}
    expanded["familiarity_ordinal"] = expanded["familiarity_tier"].map(fam_map)

    return expanded


def run_correlation_analysis(df: pd.DataFrame, output_lines: list):
    """
    Run correlation between log(brand frequency) and non-optimal choice rate.
    """
    output_lines.append("=" * 70)
    output_lines.append("CORRELATION ANALYSIS: Brand Frequency vs. Non-Optimal Choice Rate")
    output_lines.append("=" * 70)

    # Filter to rows with valid frequency and choice data
    valid = df.dropna(subset=["log_count_rpj", "non_optimal_rate"]).copy()
    valid = valid[valid["category"] != "all"]

    output_lines.append(f"\nN brands (with category): {valid['brand_name'].nunique()}")
    output_lines.append(f"N brand-category pairs: {len(valid)}")

    # --- Tier-level analysis ---
    output_lines.append("\n--- By Familiarity Tier ---")
    for tier in ["high", "medium", "low"]:
        subset = valid[valid["familiarity_tier"] == tier]
        if len(subset) > 2:
            r, p = stats.pearsonr(subset["log_count_rpj"], subset["non_optimal_rate"])
            output_lines.append(
                f"  {tier}: r={r:.3f}, p={p:.4f}, N={len(subset)}, "
                f"avg_log_freq={subset['log_count_rpj'].mean():.2f}, "
                f"avg_non_opt_rate={subset['non_optimal_rate'].mean():.3f}"
            )

    # --- Overall correlation ---
    output_lines.append("\n--- Overall Correlation (all brands) ---")
    if len(valid) > 2:
        r, p = stats.pearsonr(valid["log_count_rpj"], valid["non_optimal_rate"])
        rho, p_rho = stats.spearmanr(valid["log_count_rpj"], valid["non_optimal_rate"])
        output_lines.append(f"  Pearson r = {r:.4f} (p = {p:.6f})")
        output_lines.append(f"  Spearman rho = {rho:.4f} (p = {p_rho:.6f})")

    # --- Brand-level aggregation (average across categories) ---
    output_lines.append("\n--- Brand-Level Correlation (averaged across categories) ---")
    brand_level = (
        valid
        .groupby(["brand_name", "is_fictional", "familiarity_tier"])
        .agg(
            log_freq=("log_count_rpj", "first"),
            avg_non_opt_rate=("non_optimal_rate", "mean"),
            n_categories=("category", "count"),
        )
        .reset_index()
    )
    if len(brand_level) > 2:
        r, p = stats.pearsonr(brand_level["log_freq"], brand_level["avg_non_opt_rate"])
        rho, p_rho = stats.spearmanr(brand_level["log_freq"], brand_level["avg_non_opt_rate"])
        output_lines.append(f"  N brands = {len(brand_level)}")
        output_lines.append(f"  Pearson r = {r:.4f} (p = {p:.6f})")
        output_lines.append(f"  Spearman rho = {rho:.4f} (p = {p_rho:.6f})")

    # --- Fictional vs Real comparison ---
    output_lines.append("\n--- Fictional vs. Real Brand Comparison ---")
    for is_fict, label in [(True, "Fictional"), (False, "Real")]:
        subset = valid[valid["is_fictional"] == is_fict]
        if len(subset) > 0:
            output_lines.append(
                f"  {label}: N={subset['brand_name'].nunique()} brands, "
                f"avg_log_freq={subset['log_count_rpj'].mean():.2f}, "
                f"avg_non_opt_rate={subset['non_optimal_rate'].mean():.3f}"
            )

    return brand_level


def run_regression(df: pd.DataFrame, output_lines: list):
    """
    Run OLS regression: non_optimal_rate ~ log_freq + controls.
    """
    output_lines.append("\n" + "=" * 70)
    output_lines.append("REGRESSION ANALYSIS")
    output_lines.append("=" * 70)

    valid = df.dropna(subset=["log_count_rpj", "non_optimal_rate"]).copy()
    valid = valid[valid["category"] != "all"]

    if not HAS_STATSMODELS:
        # Fallback: simple OLS via scipy
        output_lines.append("\n--- Simple OLS (scipy, no controls) ---")
        slope, intercept, r, p, se = stats.linregress(
            valid["log_count_rpj"], valid["non_optimal_rate"]
        )
        output_lines.append(f"  non_optimal_rate = {intercept:.4f} + {slope:.6f} * log_freq")
        output_lines.append(f"  R-squared = {r**2:.4f}")
        output_lines.append(f"  slope SE = {se:.6f}, p = {p:.6f}")
        return

    # --- Model 1: Bivariate ---
    output_lines.append("\n--- Model 1: non_optimal_rate ~ log_count_rpj ---")
    try:
        m1 = smf.ols("non_optimal_rate ~ log_count_rpj", data=valid).fit()
        output_lines.append(m1.summary().as_text())
    except Exception as e:
        output_lines.append(f"  Error: {e}")

    # --- Model 2: With familiarity controls ---
    output_lines.append("\n--- Model 2: + familiarity_ordinal ---")
    try:
        m2 = smf.ols(
            "non_optimal_rate ~ log_count_rpj + familiarity_ordinal",
            data=valid,
        ).fit()
        output_lines.append(m2.summary().as_text())
    except Exception as e:
        output_lines.append(f"  Error: {e}")

    # --- Model 3: Full model with category controls ---
    output_lines.append("\n--- Model 3: + involvement + hedonic + brand_salience ---")
    try:
        valid_full = valid.dropna(subset=[
            "involvement_ordinal", "hedonic_binary", "brand_salience_ordinal"
        ])
        m3 = smf.ols(
            "non_optimal_rate ~ log_count_rpj + familiarity_ordinal + "
            "involvement_ordinal + hedonic_binary + brand_salience_ordinal",
            data=valid_full,
        ).fit()
        output_lines.append(m3.summary().as_text())
    except Exception as e:
        output_lines.append(f"  Error: {e}")

    # --- Model 4: With is_fictional interaction ---
    output_lines.append("\n--- Model 4: + is_fictional interaction ---")
    try:
        m4 = smf.ols(
            "non_optimal_rate ~ log_count_rpj * is_fictional_binary + "
            "involvement_ordinal + hedonic_binary",
            data=valid_full,
        ).fit()
        output_lines.append(m4.summary().as_text())
    except Exception as e:
        output_lines.append(f"  Error: {e}")

    # --- Model 5: Cross-corpus robustness ---
    output_lines.append("\n--- Model 5: Using cross-corpus average (robustness) ---")
    try:
        m5 = smf.ols(
            "non_optimal_rate ~ log_count_avg + familiarity_ordinal",
            data=valid.dropna(subset=["log_count_avg"]),
        ).fit()
        output_lines.append(m5.summary().as_text())
    except Exception as e:
        output_lines.append(f"  Error: {e}")


# ---------------------------------------------------------------------------
# Visualization
# ---------------------------------------------------------------------------

def create_figure(df: pd.DataFrame, brand_level: pd.DataFrame):
    """
    Create publication-quality scatter plot:
      x = log(brand frequency in RedPajama)
      y = non-optimal choice rate for that brand's category

    Panel A: Brand-level scatter colored by familiarity tier
    Panel B: Category-level averages by tier
    """
    fig, axes = plt.subplots(1, 2, figsize=(14, 6), gridspec_kw={"width_ratios": [3, 2]})

    # Color palette
    tier_colors = {
        "high": "#c0392b",    # Red
        "medium": "#2980b9",  # Blue
        "low": "#27ae60",     # Green
    }
    tier_markers = {"high": "o", "medium": "s", "low": "^"}

    # ---- Panel A: Brand-level scatter ----
    ax = axes[0]

    valid = df.dropna(subset=["log_count_rpj", "non_optimal_rate"])
    valid = valid[valid["category"] != "all"]

    for tier in ["high", "medium", "low"]:
        subset = valid[valid["familiarity_tier"] == tier]
        ax.scatter(
            subset["log_count_rpj"],
            subset["non_optimal_rate"],
            c=tier_colors[tier],
            marker=tier_markers[tier],
            alpha=0.5,
            s=40,
            label=f"{tier.capitalize()} familiarity (n={subset['brand_name'].nunique()})",
            edgecolors="white",
            linewidth=0.3,
        )

    # Highlight fictional brands
    fictional = valid[valid["is_fictional"] == True]
    if len(fictional) > 0:
        ax.scatter(
            fictional["log_count_rpj"],
            fictional["non_optimal_rate"],
            facecolors="none",
            edgecolors="black",
            marker="D",
            s=60,
            linewidth=1.2,
            label=f"Fictional brands (n={fictional['brand_name'].nunique()})",
            zorder=5,
        )

    # Regression line
    if len(valid) > 2:
        slope, intercept, r, p, se = stats.linregress(
            valid["log_count_rpj"], valid["non_optimal_rate"]
        )
        x_range = np.linspace(valid["log_count_rpj"].min(), valid["log_count_rpj"].max(), 100)
        ax.plot(x_range, intercept + slope * x_range, "k--", linewidth=1.2, alpha=0.7)
        ax.text(
            0.05, 0.95,
            f"r = {r:.3f} (p = {p:.4f})",
            transform=ax.transAxes,
            fontsize=10,
            va="top",
            ha="left",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="white", edgecolor="gray", alpha=0.8),
        )

    ax.set_xlabel("log(Brand Frequency in RedPajama)", fontsize=12)
    ax.set_ylabel("Non-Optimal Choice Rate", fontsize=12)
    ax.set_title("A. Brand Training-Data Frequency vs. Choice Bias", fontsize=13, fontweight="bold")
    ax.legend(fontsize=9, loc="lower right", framealpha=0.9)
    ax.grid(True, alpha=0.2)

    # ---- Panel B: Category-level by tier ----
    ax2 = axes[1]

    # Compute average frequency and non-optimal rate by category x tier
    cat_tier = (
        valid
        .groupby(["category", "familiarity_tier"])
        .agg(
            avg_log_freq=("log_count_rpj", "mean"),
            avg_non_opt=("non_optimal_rate", "mean"),
        )
        .reset_index()
    )

    for tier in ["high", "medium", "low"]:
        subset = cat_tier[cat_tier["familiarity_tier"] == tier]
        ax2.scatter(
            subset["avg_log_freq"],
            subset["avg_non_opt"],
            c=tier_colors[tier],
            marker=tier_markers[tier],
            s=80,
            alpha=0.7,
            label=f"{tier.capitalize()}",
            edgecolors="white",
            linewidth=0.5,
        )

        # Annotate categories
        for _, row in subset.iterrows():
            cat_short = row["category"].replace("_", " ")
            if len(cat_short) > 10:
                cat_short = cat_short[:8] + "..."
            ax2.annotate(
                cat_short,
                (row["avg_log_freq"], row["avg_non_opt"]),
                fontsize=6,
                alpha=0.7,
                xytext=(3, 3),
                textcoords="offset points",
            )

    ax2.set_xlabel("Avg log(Frequency)", fontsize=12)
    ax2.set_ylabel("Non-Optimal Choice Rate", fontsize=12)
    ax2.set_title("B. Category Averages by Tier", fontsize=13, fontweight="bold")
    ax2.legend(fontsize=9, loc="lower right", framealpha=0.9)
    ax2.grid(True, alpha=0.2)

    plt.tight_layout()

    # Save
    fig.savefig(FIGURE_PDF, dpi=300, bbox_inches="tight")
    fig.savefig(FIGURE_PNG, dpi=300, bbox_inches="tight")
    print(f"Figure saved to {FIGURE_PDF} and {FIGURE_PNG}")

    plt.close(fig)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Check inputs exist
    if not FREQ_CSV.exists():
        print(f"ERROR: Brand frequency data not found at {FREQ_CSV}")
        print("Run brand_frequency_scanner.py first.")
        sys.exit(1)

    if not EXPERIMENT_CSV.exists():
        print(f"ERROR: Experiment data not found at {EXPERIMENT_CSV}")
        sys.exit(1)

    # Load data
    brand_agg, brand_cat_agg = load_brand_frequencies()
    exp_df = load_experiment_data()

    # Compute behavior rates
    cat_rates, cat_fam_rates, sr_rates = compute_brand_bias_rates(exp_df)

    print(f"\nCategory non-optimal rates:")
    for _, row in cat_rates.sort_values("non_optimal_rate", ascending=False).iterrows():
        print(f"  {row['category']}: {row['non_optimal_rate']:.3f} ({row['n_trials']} trials)")

    # Merge
    merged = merge_frequency_with_behavior(brand_agg, cat_rates, brand_cat_agg)
    merged.to_csv(MERGED_CSV, index=False)
    print(f"\nMerged data saved to {MERGED_CSV} ({len(merged)} rows)")

    # Analysis
    output_lines = []
    output_lines.append(f"Brand Frequency Analysis Results")
    output_lines.append(f"Generated from: {FREQ_CSV.name} + {EXPERIMENT_CSV.name}")
    output_lines.append(f"Date: auto-generated\n")

    brand_level = run_correlation_analysis(merged, output_lines)
    run_regression(merged, output_lines)

    # Write results
    with open(REGRESSION_TXT, "w") as f:
        f.write("\n".join(output_lines))
    print(f"\nRegression results saved to {REGRESSION_TXT}")

    # Print key results to console
    print("\n" + "\n".join(output_lines))

    # Figure
    try:
        create_figure(merged, brand_level)
    except Exception as e:
        print(f"\nWarning: Could not create figure: {e}")
        print("This may happen if matplotlib is not configured for display.")


if __name__ == "__main__":
    main()
