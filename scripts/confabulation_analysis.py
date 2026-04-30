#!/usr/bin/env python3
"""
Confabulation Analysis: Training Data -> Brand Preference -> Confabulation
===========================================================================
Nature R&R: Connects confabulation to training data (Nature concern #1).

Core hypothesis: Brands with higher training data frequency trigger MORE
confabulation. If a model's non-optimal choices correlate with corpus
frequency of the chosen brand, this demonstrates that training data
exposure drives the bias AND that models confabulate justifications for
these biased choices.

Analysis pipeline:
  1. Load ALL trial data (original 135K+ CSV + new BVI experiments)
  2. Map each product choice to a brand name (via assortment lookup)
  3. Merge brand-level training data frequencies (infini-gram + Wikipedia)
  4. Compute confabulation patterns:
     a. Which brands trigger the most confabulation?
     b. Which product categories?
     c. Does confabulation correlate with training data frequency?
     d. Do base models confabulate more or less than instruct models?
  5. Generate publication-quality figures

Inputs:
  - data/processed/spec_resistance_FRESH.csv  (main experiment, 135K+ trials)
  - data/base_vs_instruct/raw/bvi_*.json      (BVI experiment)
  - data/brand_frequencies.csv       (infini-gram corpus frequencies)
  - data/brand_wikipedia_pageviews.csv (Wikipedia popularity proxy)
  - experiment/assortments.py                  (brand info per assortment)

Outputs (results/):
  - confabulation_by_brand.csv
  - confabulation_by_category.csv
  - confabulation_brand_frequency_regression.json
  - figures/confabulation_by_brand_frequency.pdf
  - figures/confabulation_by_category.pdf
  - figures/confabulation_base_vs_instruct.pdf
  - figures/confabulation_heatmap.pdf

Usage:
    python scripts/confabulation_analysis.py
    python scripts/confabulation_analysis.py --include-bvi
"""

import argparse
import csv
import json
import sys
import warnings
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import numpy as np

try:
    import pandas as pd
except ImportError:
    print("ERROR: pandas required. Install with: pip install pandas")
    sys.exit(1)

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.ticker as mticker
except ImportError:
    print("ERROR: matplotlib required. Install with: pip install matplotlib")
    sys.exit(1)

try:
    from scipy import stats as scipy_stats
except ImportError:
    scipy_stats = None
    warnings.warn("scipy not installed. Some statistical tests will be skipped.")

try:
    import statsmodels.api as sm
    import statsmodels.formula.api as smf
    HAS_STATSMODELS = True
except ImportError:
    HAS_STATSMODELS = False

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent.parent  # spec-resistance/
_NATURE_RR = _SCRIPT_DIR.parent

if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# Fix Windows console encoding
if sys.stdout.encoding != "utf-8":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding != "utf-8":
    import io
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Paths
EXPERIMENT_CSV = _PROJECT_ROOT / "data" / "processed" / "spec_resistance_FRESH.csv"
BVI_RAW_DIR = _PROJECT_ROOT / "data" / "base_vs_instruct" / "raw"
FREQ_CSV = _NATURE_RR / "data" / "brand_frequencies.csv"
WIKI_CSV = _NATURE_RR / "data" / "brand_wikipedia_pageviews.csv"
OUTPUT_DIR = _NATURE_RR / "results"
FIGURES_DIR = OUTPUT_DIR / "figures"

# Import assortments for brand-product mapping
from experiment.assortments import ALL_ASSORTMENTS, CATEGORY_METADATA


# ===================================================================
# STEP 1: BUILD BRAND LOOKUP FROM ASSORTMENTS
# ===================================================================

def build_brand_lookup() -> dict[str, dict]:
    """
    Build a lookup: (assortment_id, original_letter) -> product info.

    Returns dict keyed by "assortment_id::letter" with values containing
    brand, brand_familiarity, is_optimal, quality_score, etc.
    """
    lookup = {}
    for assortment in ALL_ASSORTMENTS:
        aid = assortment["id"]
        for product in assortment.get("products", []):
            key = f"{aid}::{product['letter']}"
            lookup[key] = {
                "brand": product.get("brand", "Unknown"),
                "brand_familiarity": product.get("brand_familiarity", "unknown"),
                "is_optimal": product.get("is_optimal", False),
                "quality_score": product.get("quality_score", 0),
                "price": product.get("price", 0),
                "name": product.get("name", ""),
            }
    return lookup


def get_chosen_brand(row, brand_lookup: dict) -> str:
    """Extract the brand name of the chosen product from a trial row."""
    aid = row.get("assortment_id", "")
    original_choice = row.get("original_choice", "")

    if not aid or not original_choice or original_choice == "?":
        return "Unknown"

    key = f"{aid}::{original_choice}"
    info = brand_lookup.get(key, {})
    return info.get("brand", "Unknown")


def get_optimal_brand(row, brand_lookup: dict) -> str:
    """Extract the brand name of the optimal product."""
    aid = row.get("assortment_id", "")
    original_optimal = row.get("original_optimal", "")

    if not aid or not original_optimal:
        return "Unknown"

    key = f"{aid}::{original_optimal}"
    info = brand_lookup.get(key, {})
    return info.get("brand", "Unknown")


# ===================================================================
# STEP 2: LOAD AND MERGE DATA
# ===================================================================

def load_main_experiment() -> pd.DataFrame:
    """Load the main experiment CSV with trial-level data."""
    print(f"Loading main experiment from {EXPERIMENT_CSV}...")

    if not EXPERIMENT_CSV.exists():
        print(f"  ERROR: {EXPERIMENT_CSV} not found")
        return pd.DataFrame()

    df = pd.read_csv(EXPERIMENT_CSV, low_memory=False)
    print(f"  Loaded {len(df)} trials")

    # Ensure boolean columns are typed correctly
    for col in ["chose_optimal", "chose_branded", "override_occurred",
                 "specification_resistance", "brand_reversal", "judge_brand_reasoning"]:
        if col in df.columns:
            df[col] = df[col].map(
                {"True": True, "False": False, True: True, False: False}
            ).astype("boolean")

    # Filter to sr_ assortments only (spec-resistance experiment)
    df = df[df["assortment_id"].str.startswith("sr_", na=False)].copy()
    print(f"  After sr_ filter: {len(df)} trials")

    return df


def load_bvi_trials() -> pd.DataFrame:
    """Load base-vs-instruct trial JSONs into a DataFrame."""
    if not BVI_RAW_DIR.exists():
        print(f"  BVI raw dir not found: {BVI_RAW_DIR}")
        return pd.DataFrame()

    records = []
    for json_path in sorted(BVI_RAW_DIR.glob("bvi_*.json")):
        try:
            with open(json_path, encoding="utf-8") as f:
                rec = json.load(f)
            records.append(rec)
        except (json.JSONDecodeError, ValueError):
            pass

    if not records:
        print("  No BVI trial records found")
        return pd.DataFrame()

    df = pd.DataFrame(records)
    print(f"  Loaded {len(df)} BVI trials")
    return df


def load_brand_frequencies() -> pd.DataFrame:
    """
    Load and aggregate brand frequency data from infini-gram corpus scans.

    Aggregation strategy: for each brand, sum raw_count across all
    brand_only variants (case variants) within each corpus, then average
    across corpora. This gives a single "training data exposure" measure
    per brand.
    """
    if not FREQ_CSV.exists():
        print(f"  WARNING: Brand frequency file not found: {FREQ_CSV}")
        return pd.DataFrame()

    raw = pd.read_csv(FREQ_CSV)
    print(f"  Raw brand frequency rows: {len(raw)}")

    # Filter to brand_only queries (most reliable frequency measure)
    brand_only = raw[raw["query_type"] == "brand_only"].copy()

    # Aggregate: sum across case variants per (brand, corpus)
    by_brand_corpus = (
        brand_only
        .groupby(["brand_name", "corpus"])["raw_count"]
        .sum()
        .reset_index()
    )

    # Average across corpora to get a single frequency per brand
    brand_freq = (
        by_brand_corpus
        .groupby("brand_name")["raw_count"]
        .agg(["mean", "median", "sum", "count"])
        .reset_index()
        .rename(columns={
            "mean": "avg_corpus_freq",
            "median": "median_corpus_freq",
            "sum": "total_corpus_freq",
            "count": "n_corpora",
        })
    )

    # Add familiarity tier from the raw data
    tier_map = raw.groupby("brand_name")["familiarity_tier"].first().to_dict()
    brand_freq["familiarity_tier"] = brand_freq["brand_name"].map(tier_map)

    # Compute log frequency (log10 of average corpus count)
    brand_freq["log_freq"] = np.log10(brand_freq["avg_corpus_freq"].clip(lower=1))

    print(f"  Aggregated to {len(brand_freq)} brands")
    return brand_freq


def load_wikipedia_pageviews() -> pd.DataFrame:
    """Load Wikipedia pageview data as an alternative popularity proxy."""
    if not WIKI_CSV.exists():
        print(f"  Wikipedia pageview file not found: {WIKI_CSV}")
        return pd.DataFrame()

    df = pd.read_csv(WIKI_CSV)
    print(f"  Loaded Wikipedia pageviews for {len(df)} brands")
    return df


# ===================================================================
# STEP 3: CONFABULATION COMPUTATION
# ===================================================================

def add_confabulation_column(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add confabulation classification column to trial DataFrame.

    Categories:
      - correct: chose_optimal == True
      - confabulated: chose_optimal == False AND judge_brand_reasoning == False
        (non-optimal choice without acknowledging brand influence)
      - honest_brand: chose_optimal == False AND judge_brand_reasoning == True
        (non-optimal choice with acknowledged brand influence)
      - unknown: missing judge data
    """
    def classify(row):
        if pd.isna(row.get("chose_optimal")) or pd.isna(row.get("judge_brand_reasoning")):
            return "unknown"
        if row["chose_optimal"]:
            return "correct"
        if row["judge_brand_reasoning"]:
            return "honest_brand"
        return "confabulated"

    df = df.copy()
    df["confab_type"] = df.apply(classify, axis=1)
    return df


# ===================================================================
# STEP 4: ANALYSES
# ===================================================================

def analyze_by_brand(df: pd.DataFrame, brand_freq: pd.DataFrame) -> pd.DataFrame:
    """
    Compute confabulation rate by chosen brand, merged with frequency data.

    For non-optimal choices, what fraction cited brand reasoning vs not?
    This answers: "which brands trigger the most confabulation?"
    """
    # Filter to non-unknown confab types
    known = df[df["confab_type"] != "unknown"].copy()

    # Compute rates per chosen brand
    brand_stats = (
        known
        .groupby("chosen_brand")
        .agg(
            n_trials=("trial_id", "count"),
            n_correct=("confab_type", lambda x: (x == "correct").sum()),
            n_confabulated=("confab_type", lambda x: (x == "confabulated").sum()),
            n_honest_brand=("confab_type", lambda x: (x == "honest_brand").sum()),
        )
        .reset_index()
    )

    brand_stats["correct_rate"] = brand_stats["n_correct"] / brand_stats["n_trials"]
    brand_stats["confab_rate"] = brand_stats["n_confabulated"] / brand_stats["n_trials"]
    brand_stats["honest_brand_rate"] = brand_stats["n_honest_brand"] / brand_stats["n_trials"]
    brand_stats["non_optimal_rate"] = 1 - brand_stats["correct_rate"]

    # Among non-optimal choices only, what fraction confabulated?
    non_opt = brand_stats["n_confabulated"] + brand_stats["n_honest_brand"]
    brand_stats["confab_given_nonoptimal"] = np.where(
        non_opt > 0,
        brand_stats["n_confabulated"] / non_opt,
        np.nan,
    )

    # Merge with frequency data
    if not brand_freq.empty:
        brand_stats = brand_stats.merge(
            brand_freq[["brand_name", "avg_corpus_freq", "log_freq",
                         "familiarity_tier", "n_corpora"]],
            left_on="chosen_brand",
            right_on="brand_name",
            how="left",
        )

    return brand_stats.sort_values("n_trials", ascending=False)


def analyze_by_category(df: pd.DataFrame) -> pd.DataFrame:
    """Compute confabulation rate by product category."""
    known = df[df["confab_type"] != "unknown"].copy()

    cat_stats = (
        known
        .groupby("category")
        .agg(
            n_trials=("trial_id", "count"),
            n_correct=("confab_type", lambda x: (x == "correct").sum()),
            n_confabulated=("confab_type", lambda x: (x == "confabulated").sum()),
            n_honest_brand=("confab_type", lambda x: (x == "honest_brand").sum()),
        )
        .reset_index()
    )

    cat_stats["correct_rate"] = cat_stats["n_correct"] / cat_stats["n_trials"]
    cat_stats["confab_rate"] = cat_stats["n_confabulated"] / cat_stats["n_trials"]
    cat_stats["non_optimal_rate"] = 1 - cat_stats["correct_rate"]

    # Add category metadata
    cat_stats["involvement"] = cat_stats["category"].map(
        lambda c: CATEGORY_METADATA.get(c, {}).get("involvement", "unknown")
    )
    cat_stats["brand_salience"] = cat_stats["category"].map(
        lambda c: CATEGORY_METADATA.get(c, {}).get("brand_salience", "unknown")
    )

    return cat_stats.sort_values("confab_rate", ascending=False)


def analyze_base_vs_instruct_confabulation(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compare confabulation rates between base and instruct models.
    Only meaningful for BVI experiment data that has is_base field.
    """
    if "is_base" not in df.columns:
        return pd.DataFrame()

    known = df[(df["confab_type"] != "unknown") & df["is_base"].notna()].copy()
    if known.empty:
        return pd.DataFrame()

    known["model_type"] = known["is_base"].map({True: "base", False: "instruct"})

    type_stats = (
        known
        .groupby(["model_type", "family"])
        .agg(
            n_trials=("trial_id", "count"),
            n_confabulated=("confab_type", lambda x: (x == "confabulated").sum()),
            n_honest_brand=("confab_type", lambda x: (x == "honest_brand").sum()),
            n_correct=("confab_type", lambda x: (x == "correct").sum()),
        )
        .reset_index()
    )

    type_stats["confab_rate"] = type_stats["n_confabulated"] / type_stats["n_trials"]
    type_stats["non_optimal_rate"] = 1 - type_stats["n_correct"] / type_stats["n_trials"]

    return type_stats


def run_frequency_regression(brand_stats: pd.DataFrame) -> dict:
    """
    Test whether training data frequency predicts confabulation rate.

    Model: confab_rate_i = beta_0 + beta_1 * log_freq_i + epsilon_i
    Weighted by sqrt(n_trials) to give more weight to brands with more data.

    This is the key test for Nature concern #1: does training data exposure
    drive the bias that leads to confabulation?
    """
    results = {}

    # Filter to brands with frequency data and enough trials
    valid = brand_stats.dropna(subset=["log_freq", "confab_rate"])
    valid = valid[valid["n_trials"] >= 10].copy()

    if len(valid) < 5:
        print("  Insufficient brands with frequency data for regression.")
        results["error"] = "Fewer than 5 brands with frequency data and n>=10 trials"
        return results

    x = valid["log_freq"].values
    y = valid["confab_rate"].values
    weights = np.sqrt(valid["n_trials"].values)

    print(f"\n  Regression: {len(valid)} brands, n_trials range "
          f"[{valid['n_trials'].min()}, {valid['n_trials'].max()}]")

    # Scipy: simple weighted correlation
    if scipy_stats is not None:
        r, p = scipy_stats.pearsonr(x, y)
        results["pearson_r"] = round(float(r), 4)
        results["pearson_p"] = round(float(p), 6)
        print(f"  Pearson r = {r:.4f}, p = {p:.6f}")

        # Weighted Spearman (rank correlation)
        rho, p_rho = scipy_stats.spearmanr(x, y)
        results["spearman_rho"] = round(float(rho), 4)
        results["spearman_p"] = round(float(p_rho), 6)
        print(f"  Spearman rho = {rho:.4f}, p = {p_rho:.6f}")

    # Statsmodels: WLS regression
    if HAS_STATSMODELS:
        X = sm.add_constant(x)
        wls = sm.WLS(y, X, weights=weights).fit()
        results["wls_beta_0"] = round(float(wls.params[0]), 4)
        results["wls_beta_1"] = round(float(wls.params[1]), 4)
        results["wls_r_squared"] = round(float(wls.rsquared), 4)
        results["wls_p_value_freq"] = round(float(wls.pvalues[1]), 6)
        results["wls_n"] = len(valid)

        print(f"\n  WLS Regression: confab_rate = {wls.params[0]:.4f} + "
              f"{wls.params[1]:.4f} * log_freq")
        print(f"  R-squared = {wls.rsquared:.4f}")
        print(f"  p-value (log_freq) = {wls.pvalues[1]:.6f}")

        # Also try with category fixed effects if enough data
        if "category" in valid.columns and valid["category"].nunique() > 1:
            try:
                valid_copy = valid.copy()
                valid_copy["wt"] = weights
                fe_model = smf.wls(
                    "confab_rate ~ log_freq + C(familiarity_tier)",
                    data=valid_copy,
                    weights=valid_copy["wt"],
                ).fit()
                results["fe_beta_freq"] = round(float(fe_model.params.get("log_freq", 0)), 4)
                results["fe_p_freq"] = round(float(fe_model.pvalues.get("log_freq", 1)), 6)
                results["fe_r_squared"] = round(float(fe_model.rsquared), 4)
                print(f"\n  With familiarity tier FE:")
                print(f"    beta(log_freq) = {fe_model.params.get('log_freq', 0):.4f}, "
                      f"p = {fe_model.pvalues.get('log_freq', 1):.6f}")
            except Exception as e:
                print(f"  Fixed effects regression failed: {e}")

    # Non-parametric: compare high vs low familiarity confabulation rates
    high_fam = valid[valid["familiarity_tier"] == "high"]["confab_rate"]
    low_fam = valid[valid["familiarity_tier"] == "low"]["confab_rate"]
    if len(high_fam) > 0 and len(low_fam) > 0:
        results["high_fam_mean_confab"] = round(float(high_fam.mean()), 4)
        results["low_fam_mean_confab"] = round(float(low_fam.mean()), 4)
        results["high_fam_n_brands"] = int(len(high_fam))
        results["low_fam_n_brands"] = int(len(low_fam))

        if scipy_stats is not None and len(high_fam) >= 3 and len(low_fam) >= 3:
            t_stat, t_p = scipy_stats.ttest_ind(high_fam, low_fam)
            results["ttest_t"] = round(float(t_stat), 4)
            results["ttest_p"] = round(float(t_p), 6)
            print(f"\n  High vs Low familiarity confabulation:")
            print(f"    High: mean={high_fam.mean():.3f} (n={len(high_fam)} brands)")
            print(f"    Low:  mean={low_fam.mean():.3f} (n={len(low_fam)} brands)")
            print(f"    t = {t_stat:.3f}, p = {t_p:.6f}")

    return results


# ===================================================================
# STEP 5: FIGURES
# ===================================================================

def figure_brand_frequency_scatter(
    brand_stats: pd.DataFrame,
    regression: dict,
    output_path: Path = None,
):
    """
    Scatter plot: log(brand frequency) vs confabulation rate.
    Point size proportional to n_trials. Color by familiarity tier.
    """
    if output_path is None:
        output_path = FIGURES_DIR / "confabulation_by_brand_frequency"

    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    valid = brand_stats.dropna(subset=["log_freq", "confab_rate"])
    valid = valid[valid["n_trials"] >= 10].copy()

    if valid.empty:
        print("  No data for brand frequency scatter.")
        return

    fig, ax = plt.subplots(figsize=(10, 7))

    # Color by familiarity tier
    color_map = {"high": "#E53935", "medium": "#FF9800", "low": "#1565C0"}
    for tier in ["high", "medium", "low"]:
        subset = valid[valid["familiarity_tier"] == tier]
        if subset.empty:
            continue
        sizes = np.clip(subset["n_trials"] / subset["n_trials"].max() * 300, 30, 300)
        ax.scatter(
            subset["log_freq"],
            subset["confab_rate"],
            s=sizes,
            c=color_map.get(tier, "gray"),
            alpha=0.7,
            edgecolors="white",
            linewidths=0.5,
            label=f"{tier.title()} familiarity (n={len(subset)})",
        )

    # Add brand labels for top brands
    for _, row in valid.nlargest(15, "n_trials").iterrows():
        brand = row.get("chosen_brand", row.get("brand_name", ""))
        ax.annotate(
            brand,
            (row["log_freq"], row["confab_rate"]),
            fontsize=7,
            alpha=0.8,
            xytext=(5, 3),
            textcoords="offset points",
        )

    # Regression line
    beta_0 = regression.get("wls_beta_0")
    beta_1 = regression.get("wls_beta_1")
    if beta_0 is not None and beta_1 is not None:
        x_range = np.linspace(valid["log_freq"].min(), valid["log_freq"].max(), 100)
        y_pred = beta_0 + beta_1 * x_range
        ax.plot(x_range, y_pred, "k--", alpha=0.6, linewidth=1.5)

        r_sq = regression.get("wls_r_squared", 0)
        p_val = regression.get("wls_p_value_freq", 1)
        p_str = f"p < 0.001" if p_val < 0.001 else f"p = {p_val:.3f}"
        ax.text(
            0.05, 0.95,
            f"$\\beta_1$ = {beta_1:.4f}\n$R^2$ = {r_sq:.3f}\n{p_str}",
            transform=ax.transAxes,
            fontsize=10,
            verticalalignment="top",
            bbox=dict(boxstyle="round", facecolor="white", alpha=0.8),
        )

    ax.set_xlabel("log$_{10}$(Brand Corpus Frequency)", fontsize=12)
    ax.set_ylabel("Confabulation Rate", fontsize=12)
    ax.set_title(
        "Training Data Frequency Predicts Confabulation Rate",
        fontsize=13,
        fontweight="bold",
    )
    ax.legend(loc="lower right", fontsize=9)
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(1.0))

    fig.tight_layout()
    fig.savefig(str(output_path) + ".pdf", dpi=300, bbox_inches="tight")
    fig.savefig(str(output_path) + ".png", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {output_path}.pdf/.png")


def figure_confabulation_by_category(
    cat_stats: pd.DataFrame,
    output_path: Path = None,
):
    """Horizontal bar chart of confabulation rate by category."""
    if output_path is None:
        output_path = FIGURES_DIR / "confabulation_by_category"

    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    if cat_stats.empty:
        return

    # Sort by confab rate
    cat_stats = cat_stats.sort_values("confab_rate", ascending=True).copy()

    fig, ax = plt.subplots(figsize=(10, 8))

    # Color by brand salience
    salience_colors = {
        "high": "#E53935",
        "medium": "#FF9800",
        "low": "#1565C0",
        "unknown": "#9E9E9E",
    }
    colors = [salience_colors.get(s, "#9E9E9E") for s in cat_stats["brand_salience"]]

    y = np.arange(len(cat_stats))

    # Stacked bar: confabulated (red) + honest brand (orange) = total non-optimal
    ax.barh(
        y,
        cat_stats["confab_rate"],
        color=colors,
        alpha=0.85,
        edgecolor="white",
        label="Confabulated",
    )

    # Overlay honest brand rate
    honest = cat_stats["n_honest_brand"] / cat_stats["n_trials"]
    ax.barh(
        y,
        honest,
        left=cat_stats["confab_rate"],
        color="#FF9800",
        alpha=0.5,
        edgecolor="white",
        label="Honest Brand",
    )

    ax.set_yticks(y)
    ax.set_yticklabels(
        [c.replace("_", " ").title() for c in cat_stats["category"]],
        fontsize=9,
    )
    ax.set_xlabel("Rate", fontsize=11)
    ax.set_title(
        "Confabulation Rate by Product Category",
        fontsize=13,
        fontweight="bold",
    )
    ax.xaxis.set_major_formatter(mticker.PercentFormatter(1.0))
    ax.legend(loc="lower right", fontsize=9)

    # Add n labels
    for i, (_, row) in enumerate(cat_stats.iterrows()):
        ax.text(
            row["confab_rate"] + honest.iloc[i] + 0.005,
            i,
            f"n={int(row['n_trials'])}",
            va="center",
            fontsize=7,
            alpha=0.7,
        )

    fig.tight_layout()
    fig.savefig(str(output_path) + ".pdf", dpi=300, bbox_inches="tight")
    fig.savefig(str(output_path) + ".png", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {output_path}.pdf/.png")


def figure_base_vs_instruct(
    bvi_stats: pd.DataFrame,
    output_path: Path = None,
):
    """Grouped bar chart: confabulation rate, base vs instruct by model family."""
    if output_path is None:
        output_path = FIGURES_DIR / "confabulation_base_vs_instruct"

    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    if bvi_stats.empty:
        print("  No BVI confabulation data for figure.")
        return

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # Panel A: Confabulation rate by family and model type
    ax = axes[0]
    families = sorted(bvi_stats["family"].unique())

    if families:
        x = np.arange(len(families))
        width = 0.35

        base_rates = []
        instruct_rates = []
        for fam in families:
            base_row = bvi_stats[(bvi_stats["family"] == fam) & (bvi_stats["model_type"] == "base")]
            inst_row = bvi_stats[(bvi_stats["family"] == fam) & (bvi_stats["model_type"] == "instruct")]
            base_rates.append(float(base_row["confab_rate"].iloc[0]) if len(base_row) > 0 else 0)
            instruct_rates.append(float(inst_row["confab_rate"].iloc[0]) if len(inst_row) > 0 else 0)

        bars1 = ax.bar(x - width/2, base_rates, width, label="Base (pre-RLHF)",
                        color="#E53935", alpha=0.85)
        bars2 = ax.bar(x + width/2, instruct_rates, width, label="Instruct (post-RLHF)",
                        color="#1565C0", alpha=0.85)

        ax.set_ylabel("Confabulation Rate", fontsize=11)
        ax.set_title("A. Confabulation: Base vs. Instruct", fontsize=12, fontweight="bold")
        ax.set_xticks(x)
        ax.set_xticklabels([f.replace("-", "\n") for f in families], fontsize=9)
        ax.legend(fontsize=9)
        ax.yaxis.set_major_formatter(mticker.PercentFormatter(1.0))

        for bars in [bars1, bars2]:
            for bar in bars:
                h = bar.get_height()
                if h > 0:
                    ax.text(bar.get_x() + bar.get_width()/2., h + 0.005,
                            f"{h:.0%}", ha="center", va="bottom", fontsize=8)

    # Panel B: Non-optimal rate (superset of confabulation)
    ax = axes[1]
    if families:
        base_nonopt = []
        instruct_nonopt = []
        for fam in families:
            base_row = bvi_stats[(bvi_stats["family"] == fam) & (bvi_stats["model_type"] == "base")]
            inst_row = bvi_stats[(bvi_stats["family"] == fam) & (bvi_stats["model_type"] == "instruct")]
            base_nonopt.append(float(base_row["non_optimal_rate"].iloc[0]) if len(base_row) > 0 else 0)
            instruct_nonopt.append(float(inst_row["non_optimal_rate"].iloc[0]) if len(inst_row) > 0 else 0)

        bars1 = ax.bar(x - width/2, base_nonopt, width, label="Base",
                        color="#E53935", alpha=0.85)
        bars2 = ax.bar(x + width/2, instruct_nonopt, width, label="Instruct",
                        color="#1565C0", alpha=0.85)

        ax.set_ylabel("Non-Optimal Choice Rate", fontsize=11)
        ax.set_title("B. Total Non-Optimal: Base vs. Instruct", fontsize=12, fontweight="bold")
        ax.set_xticks(x)
        ax.set_xticklabels([f.replace("-", "\n") for f in families], fontsize=9)
        ax.legend(fontsize=9)
        ax.yaxis.set_major_formatter(mticker.PercentFormatter(1.0))

        for bars in [bars1, bars2]:
            for bar in bars:
                h = bar.get_height()
                if h > 0:
                    ax.text(bar.get_x() + bar.get_width()/2., h + 0.005,
                            f"{h:.0%}", ha="center", va="bottom", fontsize=8)

    fig.tight_layout(pad=2.0)
    fig.savefig(str(output_path) + ".pdf", dpi=300, bbox_inches="tight")
    fig.savefig(str(output_path) + ".png", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {output_path}.pdf/.png")


def figure_confabulation_heatmap(
    df: pd.DataFrame,
    output_path: Path = None,
):
    """
    Heatmap: categories x condition types, cells colored by confabulation rate.
    Shows which condition-category combinations trigger the most confabulation.
    """
    if output_path is None:
        output_path = FIGURES_DIR / "confabulation_heatmap"

    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    known = df[df["confab_type"] != "unknown"].copy()
    if known.empty or "condition_type" not in known.columns:
        print("  No data for heatmap.")
        return

    # Pivot: category x condition_type
    pivot = known.groupby(["category", "condition_type"]).agg(
        confab_rate=("confab_type", lambda x: (x == "confabulated").mean()),
        n=("trial_id", "count"),
    ).reset_index()

    heatmap_data = pivot.pivot(index="category", columns="condition_type", values="confab_rate")

    # Only keep categories and conditions with enough data
    min_trials = 20
    n_pivot = pivot.pivot(index="category", columns="condition_type", values="n")
    heatmap_data = heatmap_data.where(n_pivot >= min_trials)

    # Drop rows/cols that are all NaN
    heatmap_data = heatmap_data.dropna(how="all", axis=0).dropna(how="all", axis=1)

    if heatmap_data.empty:
        print("  Insufficient data for heatmap.")
        return

    fig, ax = plt.subplots(figsize=(12, 8))

    im = ax.imshow(heatmap_data.values, cmap="YlOrRd", aspect="auto")

    ax.set_xticks(np.arange(len(heatmap_data.columns)))
    ax.set_xticklabels(
        [c.replace("_", "\n") for c in heatmap_data.columns],
        fontsize=8,
        rotation=45,
        ha="right",
    )
    ax.set_yticks(np.arange(len(heatmap_data.index)))
    ax.set_yticklabels(
        [c.replace("_", " ").title() for c in heatmap_data.index],
        fontsize=8,
    )

    # Add text annotations
    for i in range(len(heatmap_data.index)):
        for j in range(len(heatmap_data.columns)):
            val = heatmap_data.iloc[i, j]
            if not np.isnan(val):
                text_color = "white" if val > 0.3 else "black"
                ax.text(j, i, f"{val:.0%}", ha="center", va="center",
                        fontsize=7, color=text_color)

    cbar = fig.colorbar(im, ax=ax, label="Confabulation Rate", shrink=0.8)
    cbar.ax.yaxis.set_major_formatter(mticker.PercentFormatter(1.0))

    ax.set_title(
        "Confabulation Rate: Category x Condition Type",
        fontsize=13,
        fontweight="bold",
    )

    fig.tight_layout()
    fig.savefig(str(output_path) + ".pdf", dpi=300, bbox_inches="tight")
    fig.savefig(str(output_path) + ".png", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {output_path}.pdf/.png")


# ===================================================================
# MAIN PIPELINE
# ===================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Confabulation analysis: training data -> brand bias -> confabulation"
    )
    parser.add_argument("--include-bvi", action="store_true",
                        help="Include base-vs-instruct experiment data")
    parser.add_argument("--min-trials", type=int, default=10,
                        help="Minimum trials per brand for regression (default: 10)")
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    print(f"{'='*70}")
    print("CONFABULATION ANALYSIS")
    print(f"Connecting training data exposure to brand preference confabulation")
    print(f"{'='*70}")

    # --- Step 1: Build brand lookup ---
    print(f"\n--- Building brand lookup from assortments ---")
    brand_lookup = build_brand_lookup()
    print(f"  {len(brand_lookup)} product entries in lookup")

    # --- Step 2: Load data ---
    print(f"\n--- Loading experiment data ---")
    df_main = load_main_experiment()

    df_all = df_main.copy()

    if args.include_bvi:
        df_bvi = load_bvi_trials()
        if not df_bvi.empty:
            # Align columns before concatenation
            common_cols = list(set(df_main.columns) & set(df_bvi.columns))
            df_all = pd.concat([df_all, df_bvi[common_cols]], ignore_index=True)
            print(f"  Combined: {len(df_all)} total trials")

    # --- Step 3: Map product choices to brand names ---
    print(f"\n--- Mapping choices to brand names ---")

    def _get_brand(row):
        aid = row.get("assortment_id", "")
        oc = row.get("original_choice", "")
        if not aid or not oc or oc == "?":
            return "Unknown"
        key = f"{aid}::{oc}"
        info = brand_lookup.get(key, {})
        return info.get("brand", "Unknown")

    df_all["chosen_brand"] = df_all.apply(_get_brand, axis=1)

    # Also map optimal product to brand
    def _get_opt_brand(row):
        aid = row.get("assortment_id", "")
        oo = row.get("original_optimal", "")
        if not aid or not oo:
            return "Unknown"
        key = f"{aid}::{oo}"
        info = brand_lookup.get(key, {})
        return info.get("brand", "Unknown")

    df_all["optimal_brand"] = df_all.apply(_get_opt_brand, axis=1)

    n_mapped = (df_all["chosen_brand"] != "Unknown").sum()
    print(f"  Mapped {n_mapped}/{len(df_all)} trials to brand names")

    # --- Step 4: Add confabulation classification ---
    print(f"\n--- Classifying confabulation types ---")
    df_all = add_confabulation_column(df_all)

    confab_counts = df_all["confab_type"].value_counts()
    print(f"  Classification breakdown:")
    for ctype, count in confab_counts.items():
        pct = count / len(df_all) * 100
        print(f"    {ctype:20s}: {count:7d} ({pct:.1f}%)")

    # --- Step 5: Load brand frequency data ---
    print(f"\n--- Loading brand frequency data ---")
    brand_freq = load_brand_frequencies()
    wiki_views = load_wikipedia_pageviews()

    # --- Step 6: Run analyses ---
    print(f"\n{'='*70}")
    print("ANALYSIS 1: Confabulation by Brand")
    print(f"{'='*70}")
    brand_stats = analyze_by_brand(df_all, brand_freq)
    print(f"\n  Top 15 brands by confabulation rate (n >= 50 trials):")
    top_brands = brand_stats[brand_stats["n_trials"] >= 50].nlargest(15, "confab_rate")
    for _, row in top_brands.iterrows():
        print(f"    {row['chosen_brand']:25s} confab={row['confab_rate']:.1%} "
              f"nonopt={row['non_optimal_rate']:.1%} n={int(row['n_trials'])}")

    print(f"\n{'='*70}")
    print("ANALYSIS 2: Confabulation by Category")
    print(f"{'='*70}")
    cat_stats = analyze_by_category(df_all)
    for _, row in cat_stats.iterrows():
        print(f"  {row['category']:25s} confab={row['confab_rate']:.1%} "
              f"({row['brand_salience']:6s} salience) n={int(row['n_trials'])}")

    print(f"\n{'='*70}")
    print("ANALYSIS 3: Training Data Frequency -> Confabulation")
    print(f"{'='*70}")
    regression = run_frequency_regression(brand_stats)

    bvi_stats = pd.DataFrame()
    if args.include_bvi and "is_base" in df_all.columns:
        print(f"\n{'='*70}")
        print("ANALYSIS 4: Base vs. Instruct Confabulation")
        print(f"{'='*70}")
        bvi_stats = analyze_base_vs_instruct_confabulation(df_all)
        if not bvi_stats.empty:
            for _, row in bvi_stats.iterrows():
                print(f"  {row['model_type']:10s} {row['family']:20s} "
                      f"confab={row['confab_rate']:.1%} nonopt={row['non_optimal_rate']:.1%} "
                      f"n={int(row['n_trials'])}")

    # --- Step 7: Save results ---
    print(f"\n{'='*70}")
    print("SAVING RESULTS")
    print(f"{'='*70}")

    brand_stats.to_csv(OUTPUT_DIR / "confabulation_by_brand.csv", index=False)
    print(f"  Saved: {OUTPUT_DIR / 'confabulation_by_brand.csv'}")

    cat_stats.to_csv(OUTPUT_DIR / "confabulation_by_category.csv", index=False)
    print(f"  Saved: {OUTPUT_DIR / 'confabulation_by_category.csv'}")

    with open(OUTPUT_DIR / "confabulation_brand_frequency_regression.json", "w") as f:
        json.dump(regression, f, indent=2)
    print(f"  Saved: {OUTPUT_DIR / 'confabulation_brand_frequency_regression.json'}")

    # Summary JSON
    summary = {
        "timestamp": datetime.now().isoformat(),
        "total_trials": len(df_all),
        "trials_with_brand": int(n_mapped),
        "confab_types": confab_counts.to_dict(),
        "overall_confab_rate": float(
            (df_all["confab_type"] == "confabulated").sum() /
            df_all[df_all["confab_type"] != "unknown"].shape[0]
        ) if df_all[df_all["confab_type"] != "unknown"].shape[0] > 0 else None,
        "n_brands_with_freq": int(brand_stats.dropna(subset=["log_freq"]).shape[0])
            if "log_freq" in brand_stats.columns else 0,
        "regression": regression,
    }
    with open(OUTPUT_DIR / "confabulation_analysis_summary.json", "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"  Saved: {OUTPUT_DIR / 'confabulation_analysis_summary.json'}")

    # --- Step 8: Generate figures ---
    print(f"\n{'='*70}")
    print("GENERATING FIGURES")
    print(f"{'='*70}")

    figure_brand_frequency_scatter(brand_stats, regression)
    figure_confabulation_by_category(cat_stats)
    figure_confabulation_heatmap(df_all)

    if not bvi_stats.empty:
        figure_base_vs_instruct(bvi_stats)

    print(f"\n{'='*70}")
    print("ANALYSIS COMPLETE")
    print(f"{'='*70}")
    print(f"  Results: {OUTPUT_DIR}")
    print(f"  Figures: {FIGURES_DIR}")

    # Print key findings for the paper
    print(f"\n--- KEY FINDINGS FOR PAPER ---")
    known = df_all[df_all["confab_type"] != "unknown"]
    if len(known) > 0:
        confab_overall = (known["confab_type"] == "confabulated").mean()
        honest_overall = (known["confab_type"] == "honest_brand").mean()
        print(f"  Overall confabulation rate: {confab_overall:.1%}")
        print(f"  Overall honest brand rate:  {honest_overall:.1%}")

    r = regression.get("pearson_r")
    p = regression.get("pearson_p")
    if r is not None:
        sig = "SIGNIFICANT" if (p is not None and p < 0.05) else "not significant"
        print(f"  Training frequency -> confabulation: r={r:.3f}, p={p:.4f} ({sig})")

    high_mean = regression.get("high_fam_mean_confab")
    low_mean = regression.get("low_fam_mean_confab")
    if high_mean is not None and low_mean is not None:
        print(f"  High-familiarity brands confab: {high_mean:.1%}")
        print(f"  Low-familiarity brands confab:  {low_mean:.1%}")


if __name__ == "__main__":
    main()
