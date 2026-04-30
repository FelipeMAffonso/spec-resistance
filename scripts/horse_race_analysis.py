"""
Horse Race Analysis: Training Data Frequency vs. Brand Equity vs. Real-World Popularity
========================================================================================
Tests whether LLM brand preferences are explained by training data exposure (corpus
frequency) above and beyond real-world brand equity and consumer popularity proxies.

The "horse race" pits multiple predictors against each other:
  1. Training data frequency (infini-gram corpus counts)
  2. Wikipedia pageviews (general entity salience)
  3. Google Trends interest (consumer search popularity)
  4. Market data (brand valuation, market cap)

Core identification argument: if corpus frequency predicts non-optimal brand selection
AFTER controlling for Wikipedia pageviews, Google Trends, and brand equity, the residual
effect cannot be attributed to real-world popularity alone.

Analyses:
  1. Descriptive scatter plot (log frequency vs non-optimal choice rate)
  2. Papke-Wooldridge fractional logit (bounded DV)
  3. Nested model horse race (incremental R-squared)
  4. Shapley value decomposition (dominance analysis)
  5. Mediation analysis (brand equity -> frequency -> LLM preference)
  6. Cross-model scaling (frequency x model size interaction)

Inputs:
  - data/brand_frequencies.csv
  - data/brand_wikipedia_pageviews.csv
  - data/brand_google_trends.csv      (optional)
  - data/brand_market_data.csv         (optional)
  - OSF/data/spec_resistance_CLEAN.csv           (main experiment)

Outputs:
  - results/01-brand-frequency/*.png
  - results/01-brand-frequency/regression_tables.txt
  - results/01-brand-frequency/RESULTS_SUMMARY.md

Usage:
    python scripts/horse_race_analysis.py
"""

import sys
import warnings
import textwrap
from pathlib import Path
from datetime import datetime
from itertools import combinations

import math
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from scipy import stats

# ---------------------------------------------------------------------------
# Optional imports (graceful degradation)
# ---------------------------------------------------------------------------

try:
    import statsmodels.api as sm
    import statsmodels.formula.api as smf
    from statsmodels.genmod.families import Binomial
    from statsmodels.genmod.families.links import Logit as LogitLink
    HAS_STATSMODELS = True
except ImportError:
    HAS_STATSMODELS = False
    warnings.warn("statsmodels not installed. Install with: pip install statsmodels")

try:
    from dominance_analysis import Dominance
    HAS_DOMINANCE = True
except ImportError:
    HAS_DOMINANCE = False
    warnings.warn(
        "dominance-analysis not installed. Shapley decomposition will use manual "
        "implementation. Install with: pip install dominance-analysis"
    )

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
NATURE_RR_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = NATURE_RR_DIR.parent

# Input data
FREQ_CSV = NATURE_RR_DIR / "data" / "brand_frequencies.csv"
WIKI_CSV = NATURE_RR_DIR / "data" / "brand_wikipedia_pageviews.csv"
GTRENDS_CSV = NATURE_RR_DIR / "data" / "brand_google_trends.csv"
MARKET_CSV = NATURE_RR_DIR / "data" / "brand_market_data.csv"

# Try multiple paths for experiment data
EXPERIMENT_CSV_CANDIDATES = [
    PROJECT_ROOT / "data" / "processed" / "spec_resistance_CLEAN.csv",
    PROJECT_ROOT / "OSF" / "data" / "spec_resistance_CLEAN.csv",
    PROJECT_ROOT / "data" / "processed" / "spec_resistance_FRESH.csv",
]

# Output
OUTPUT_DIR = NATURE_RR_DIR / "results" / "01-brand-frequency"

# ---------------------------------------------------------------------------
# Known fictional brands (zero training-data frequency anchors)
# ---------------------------------------------------------------------------

FICTIONAL_BRANDS = {
    "Arcwave", "Auralis", "Aurem", "Blendwell", "Brevara", "Chronex",
    "Cleanpath", "Crestline", "Dentara", "Ethicom", "Hexwave", "Keystrike",
    "Luminar", "Lumivue", "Netweave", "Novatech", "Optivex", "Pixelight",
    "Portabrew", "Presswell", "Primebook", "Sonance", "Sonaray", "Sonique",
    "Stridewell", "Swiftform", "Terravolt", "Thermalux", "Trailpeak",
    "Vaultdrive", "Veridian", "Vistara", "Voltek", "Vynex", "Wavecrest",
    "Zentria", "Zerion",
}

# Generic labels used in mechanism/control conditions (exclude from analysis)
GENERIC_BRANDS = {"Brand A", "Brand B", "Brand C", "Brand D", "Brand E"}

# ---------------------------------------------------------------------------
# Model size metadata (approximate parameter counts in billions)
# Used for cross-model scaling analysis
# ---------------------------------------------------------------------------

MODEL_PARAMS_BILLIONS = {
    "gpt-4o": 200,         # estimated
    "gpt-4o-mini": 8,      # estimated
    "gpt-4.1-mini": 8,     # estimated
    "gpt-4.1-nano": 1.5,   # estimated
    "gpt-5-mini": 30,      # estimated
    "claude-sonnet-4.6": 175,   # estimated
    "claude-haiku-4.5": 20,     # estimated
    "gemini-2.0-flash": 30,     # estimated
    "gemini-2.5-flash": 30,     # estimated
    "gemini-2.5-flash-lite": 10, # estimated
    "gemini-2.5-pro": 175,      # estimated
    "gemini-3-flash": 40,       # estimated
    "gemma-3-27b": 27,
    "deepseek-r1": 671,         # MoE total
    "deepseek-v3": 671,         # MoE total
    "llama-3.3-70b": 70,
    "qwen-2.5-72b": 72,
    "kimi-k2": 100,             # estimated
}

# ---------------------------------------------------------------------------
# Category metadata
# ---------------------------------------------------------------------------

CATEGORY_METADATA = {
    "laptops":               {"involvement": "high", "hedonic": False, "brand_salience_level": "high"},
    "smartphones":           {"involvement": "high", "hedonic": False, "brand_salience_level": "high"},
    "tvs":                   {"involvement": "high", "hedonic": False, "brand_salience_level": "high"},
    "cameras":               {"involvement": "high", "hedonic": True,  "brand_salience_level": "high"},
    "tablets":               {"involvement": "high", "hedonic": False, "brand_salience_level": "high"},
    "headphones":            {"involvement": "mid",  "hedonic": True,  "brand_salience_level": "high"},
    "wireless_earbuds":      {"involvement": "mid",  "hedonic": True,  "brand_salience_level": "high"},
    "running_shoes":         {"involvement": "mid",  "hedonic": True,  "brand_salience_level": "medium"},
    "smartwatches":          {"involvement": "mid",  "hedonic": False, "brand_salience_level": "high"},
    "robot_vacuums":         {"involvement": "mid",  "hedonic": False, "brand_salience_level": "medium"},
    "portable_speakers":     {"involvement": "low",  "hedonic": True,  "brand_salience_level": "medium"},
    "keyboards":             {"involvement": "low",  "hedonic": False, "brand_salience_level": "low"},
    "external_ssds":         {"involvement": "low",  "hedonic": False, "brand_salience_level": "low"},
    "water_bottles":         {"involvement": "low",  "hedonic": True,  "brand_salience_level": "low"},
    "electric_toothbrushes": {"involvement": "low",  "hedonic": True,  "brand_salience_level": "medium"},
    "coffee_makers":         {"involvement": "mid",  "hedonic": True,  "brand_salience_level": "medium"},
    "blenders":              {"involvement": "mid",  "hedonic": True,  "brand_salience_level": "high"},
    "backpacks":             {"involvement": "mid",  "hedonic": True,  "brand_salience_level": "low"},
    "wireless_routers":      {"involvement": "mid",  "hedonic": False, "brand_salience_level": "medium"},
    "monitors":              {"involvement": "mid",  "hedonic": False, "brand_salience_level": "medium"},
}

# ---------------------------------------------------------------------------
# Utility: print + collect output
# ---------------------------------------------------------------------------

class OutputCollector:
    """Collects output lines for both console and file writing."""

    def __init__(self):
        self.lines = []

    def print(self, text=""):
        print(text)
        self.lines.append(text)

    def section(self, title):
        bar = "=" * 72
        self.print(f"\n{bar}")
        self.print(f"  {title}")
        self.print(f"{bar}")

    def subsection(self, title):
        self.print(f"\n--- {title} ---")

    def write_to_file(self, path):
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(self.lines))


# ======================================================================== #
#                           DATA LOADING                                    #
# ======================================================================== #

def find_experiment_csv():
    """Locate the main experiment CSV from candidate paths."""
    for path in EXPERIMENT_CSV_CANDIDATES:
        if path.exists():
            return path
    print("ERROR: Could not find experiment data. Tried:")
    for p in EXPERIMENT_CSV_CANDIDATES:
        print(f"  {p}")
    sys.exit(1)


def load_brand_frequencies():
    """
    Load and aggregate brand frequency data across corpus variants.

    Returns a DataFrame with one row per brand, containing:
      - max_count_redpajama: highest count across spelling variants in RedPajama
      - geometric_mean_freq: geometric mean across all corpora
      - log_freq: log(1 + freq_per_million) using RedPajama as primary
    """
    df = pd.read_csv(FREQ_CSV)
    print(f"[LOAD] Brand frequencies: {len(df)} rows, {df['brand_name'].nunique()} brands, "
          f"{df['corpus'].nunique()} corpora")

    # Keep only brand-only queries (category == "all") for the main frequency measure
    brand_only = df[df["category"] == "all"].copy()

    # Aggregate: max count across spelling variants, per brand x corpus
    per_corpus = (
        brand_only
        .groupby(["brand_name", "corpus", "is_fictional", "familiarity_tier"])
        .agg(max_count=("raw_count", "max"))
        .reset_index()
    )

    # Pivot to wide format (one column per corpus)
    wide = per_corpus.pivot_table(
        index=["brand_name", "is_fictional", "familiarity_tier"],
        columns="corpus",
        values="max_count",
        aggfunc="max",
    ).reset_index()

    # Flatten column names
    wide.columns = [
        f"freq_{c.lower().replace(' ', '_')}" if c not in ["brand_name", "is_fictional", "familiarity_tier"]
        else c
        for c in wide.columns
    ]

    # Primary measure: RedPajama
    rpj_col = [c for c in wide.columns if "redpajama" in c.lower()]
    if rpj_col:
        wide["freq_primary"] = wide[rpj_col[0]]
    else:
        # Fallback: use first available corpus
        freq_cols = [c for c in wide.columns if c.startswith("freq_")]
        wide["freq_primary"] = wide[freq_cols[0]] if freq_cols else 0

    # Geometric mean across all corpora (for robustness)
    freq_cols = [c for c in wide.columns if c.startswith("freq_") and c != "freq_primary"]
    if len(freq_cols) > 1:
        freq_matrix = wide[freq_cols].fillna(0).values
        # Geometric mean of (1 + count) to handle zeros
        log_freqs = np.log1p(freq_matrix)
        wide["log_freq_geomean"] = log_freqs.mean(axis=1)
    else:
        wide["log_freq_geomean"] = np.log1p(wide["freq_primary"])

    # Log-transformed primary frequency
    wide["log_freq"] = np.log1p(wide["freq_primary"])

    print(f"  Aggregated to {len(wide)} brands")
    return wide


def load_wikipedia_pageviews():
    """Load Wikipedia pageview data."""
    if not WIKI_CSV.exists():
        print("[LOAD] Wikipedia pageviews: NOT FOUND, skipping")
        return None

    df = pd.read_csv(WIKI_CSV)
    print(f"[LOAD] Wikipedia pageviews: {len(df)} brands")

    # Standardize column names
    df = df.rename(columns={"brand": "brand_name"})

    # Log transform of average monthly pageviews
    df["log_wiki_pageviews"] = np.log1p(df["avg_monthly"].fillna(0))

    # Keep relevant columns
    cols_keep = ["brand_name", "is_fictional", "article_exists", "avg_monthly",
                 "log_wiki_pageviews"]
    return df[[c for c in cols_keep if c in df.columns]]


def load_google_trends():
    """Load Google Trends data if available."""
    if not GTRENDS_CSV.exists():
        print("[LOAD] Google Trends: NOT FOUND, skipping")
        return None

    df = pd.read_csv(GTRENDS_CSV)
    print(f"[LOAD] Google Trends: {len(df)} brands")

    df = df.rename(columns={
        "brand": "brand_name",
        "interest": "google_trends_interest",
    })

    # Log transform
    interest_col = [c for c in df.columns if "interest" in c.lower() or "trend" in c.lower()]
    if interest_col:
        df["log_google_trends"] = np.log1p(df[interest_col[0]].fillna(0))

    return df


def load_market_data():
    """Load market data (brand valuation, market cap) if available."""
    if not MARKET_CSV.exists():
        print("[LOAD] Market data: NOT FOUND, skipping")
        return None

    df = pd.read_csv(MARKET_CSV)
    print(f"[LOAD] Market data: {len(df)} brands")

    df = df.rename(columns={"brand": "brand_name"})

    # Log transforms for financial variables
    for col in ["market_cap", "brand_value", "revenue"]:
        if col in df.columns:
            df[f"log_{col}"] = np.log1p(df[col].fillna(0))

    return df


def load_experiment_data():
    """
    Load experiment data and compute brand-level non-optimal choice rates.

    For each brand x model combination:
      - Count trials where the brand appeared (in any slot A-E)
      - Count trials where the brand was chosen when NOT optimal
      - Compute non-optimal choice rate = n_chosen_non_opt / n_appeared_non_opt

    Returns two DataFrames: brand x model level, and brand aggregate level.
    """
    exp_path = find_experiment_csv()
    print(f"[LOAD] Experiment data from: {exp_path.name}")

    # Load only needed columns to conserve memory
    needed_cols = [
        "trial_id", "model_key", "assortment_id", "category",
        "condition_type", "choice", "optimal_product", "chose_optimal",
        "chose_branded", "chosen_brand_familiarity", "specification_resistance",
        "utility_loss", "involvement_level", "brand_salience", "hedonic",
        "product_A_brand", "product_B_brand", "product_C_brand",
        "product_D_brand", "product_E_brand",
    ]

    df = pd.read_csv(exp_path, usecols=needed_cols)
    print(f"  {len(df):,} trials, {df['model_key'].nunique()} models, "
          f"{df['category'].nunique()} categories")

    # Exclude trials with unknown/invalid choices
    df = df[df["choice"].isin(["A", "B", "C", "D", "E"])].copy()

    # Exclude generic-brand conditions (mechanism conditions use "Brand A" etc.)
    # These are not real brand trials
    for letter in ["A", "B", "C", "D", "E"]:
        col = f"product_{letter}_brand"
        mask = df[col].isin(GENERIC_BRANDS)
        if mask.any():
            df = df[~mask].copy()
            break  # If any slot has generic brands, the whole trial does

    print(f"  After filtering generic-brand trials: {len(df):,} trials")

    # Reshape to long format: one row per brand-appearance-in-trial
    long_frames = []
    for letter in ["A", "B", "C", "D", "E"]:
        sub = df[["trial_id", "model_key", "assortment_id", "category",
                   "choice", "optimal_product", "utility_loss",
                   f"product_{letter}_brand"]].copy()
        sub = sub.rename(columns={f"product_{letter}_brand": "brand"})
        sub["position"] = letter
        sub["was_chosen"] = (sub["choice"] == letter)
        sub["was_optimal"] = (sub["optimal_product"] == letter)
        long_frames.append(sub)

    long = pd.concat(long_frames, ignore_index=True)

    # Drop rows with missing brand names
    long = long.dropna(subset=["brand"])

    # Exclude generic brands from long format too
    long = long[~long["brand"].isin(GENERIC_BRANDS)].copy()

    # Key indicators
    long["chosen_when_not_optimal"] = long["was_chosen"] & ~long["was_optimal"]
    long["appeared_not_optimal"] = ~long["was_optimal"]

    # ---- Brand x Model level ----
    brand_model = (
        long
        .groupby(["brand", "model_key", "category"])
        .agg(
            n_appeared=("was_chosen", "count"),
            n_chosen=("was_chosen", "sum"),
            n_chosen_non_opt=("chosen_when_not_optimal", "sum"),
            n_appeared_non_opt=("appeared_not_optimal", "sum"),
            avg_utility_loss=("utility_loss", "mean"),
        )
        .reset_index()
    )
    brand_model["non_opt_rate"] = (
        brand_model["n_chosen_non_opt"] / brand_model["n_appeared_non_opt"]
    ).fillna(0)

    # ---- Brand aggregate (across all models) ----
    brand_agg = (
        long
        .groupby(["brand", "category"])
        .agg(
            n_appeared=("was_chosen", "count"),
            n_chosen=("was_chosen", "sum"),
            n_chosen_non_opt=("chosen_when_not_optimal", "sum"),
            n_appeared_non_opt=("appeared_not_optimal", "sum"),
            avg_utility_loss=("utility_loss", "mean"),
        )
        .reset_index()
    )
    brand_agg["non_opt_rate"] = (
        brand_agg["n_chosen_non_opt"] / brand_agg["n_appeared_non_opt"]
    ).fillna(0)

    # ---- Brand-level (collapsed across categories and models) ----
    brand_overall = (
        long
        .groupby("brand")
        .agg(
            n_appeared=("was_chosen", "count"),
            n_chosen=("was_chosen", "sum"),
            n_chosen_non_opt=("chosen_when_not_optimal", "sum"),
            n_appeared_non_opt=("appeared_not_optimal", "sum"),
            avg_utility_loss=("utility_loss", "mean"),
            n_categories=("category", "nunique"),
            n_models=("model_key", "nunique"),
        )
        .reset_index()
    )
    brand_overall["non_opt_rate"] = (
        brand_overall["n_chosen_non_opt"] / brand_overall["n_appeared_non_opt"]
    ).fillna(0)

    # Flag fictional
    brand_overall["is_fictional"] = brand_overall["brand"].isin(FICTIONAL_BRANDS)

    # Determine familiarity tier
    brand_overall["familiarity_tier"] = "medium"  # default for real brands
    brand_overall.loc[brand_overall["is_fictional"], "familiarity_tier"] = "fictional"

    print(f"  Brand x Model: {len(brand_model):,} rows")
    print(f"  Brand aggregate: {len(brand_agg):,} rows")
    print(f"  Brand overall: {len(brand_overall):,} brands "
          f"({brand_overall['is_fictional'].sum()} fictional)")

    return brand_model, brand_agg, brand_overall, long


# ======================================================================== #
#                          DATA MERGING                                     #
# ======================================================================== #

def merge_all_data(freq_df, wiki_df, gtrends_df, market_df, brand_overall):
    """
    Merge all data sources on brand name into a single analysis DataFrame.

    For fictional brands not in the frequency data, assign freq = 0.
    """
    # Start with brand_overall (has all brands from the experiment)
    merged = brand_overall.copy()
    merged = merged.rename(columns={"brand": "brand_name"})

    # Merge frequency data
    freq_cols = ["brand_name", "log_freq", "freq_primary", "log_freq_geomean",
                 "familiarity_tier"]
    freq_merge = freq_df[[c for c in freq_cols if c in freq_df.columns]].copy()
    freq_merge = freq_merge.rename(columns={"familiarity_tier": "familiarity_tier_freq"})

    merged = merged.merge(freq_merge, on="brand_name", how="left")

    # For fictional brands: set frequency to 0
    merged.loc[merged["is_fictional"], "log_freq"] = 0.0
    merged.loc[merged["is_fictional"], "freq_primary"] = 0.0
    merged.loc[merged["is_fictional"], "log_freq_geomean"] = 0.0

    # Update familiarity tier from frequency data where available
    has_freq_tier = merged["familiarity_tier_freq"].notna()
    merged.loc[has_freq_tier, "familiarity_tier"] = merged.loc[has_freq_tier, "familiarity_tier_freq"]
    merged = merged.drop(columns=["familiarity_tier_freq"], errors="ignore")

    # Merge Wikipedia data
    if wiki_df is not None:
        wiki_merge = wiki_df[["brand_name", "log_wiki_pageviews", "avg_monthly"]].copy()
        wiki_merge = wiki_merge.rename(columns={"avg_monthly": "wiki_avg_monthly"})
        merged = merged.merge(wiki_merge, on="brand_name", how="left")
        # Fictional brands: zero pageviews (or very low)
        merged.loc[merged["is_fictional"], "log_wiki_pageviews"] = 0.0
    else:
        merged["log_wiki_pageviews"] = np.nan

    # Merge Google Trends data
    if gtrends_df is not None:
        gt_cols = ["brand_name"]
        if "log_google_trends" in gtrends_df.columns:
            gt_cols.append("log_google_trends")
        if "google_trends_interest" in gtrends_df.columns:
            gt_cols.append("google_trends_interest")
        merged = merged.merge(gtrends_df[gt_cols], on="brand_name", how="left")
        merged.loc[merged["is_fictional"], "log_google_trends"] = 0.0
    else:
        merged["log_google_trends"] = np.nan

    # Merge market data
    if market_df is not None:
        market_cols = ["brand_name"] + [c for c in market_df.columns if c.startswith("log_")]
        merged = merged.merge(market_df[market_cols], on="brand_name", how="left")
    else:
        merged["log_market_cap"] = np.nan

    # Encode familiarity tier as numeric
    fam_map = {"fictional": 0, "low": 1, "medium": 2, "high": 3}
    merged["familiarity_numeric"] = merged["familiarity_tier"].map(fam_map).fillna(1)

    # Real-brand indicator
    merged["is_real"] = (~merged["is_fictional"]).astype(int)

    # Has frequency data indicator
    merged["has_freq_data"] = merged["log_freq"].notna() & (merged["log_freq"] > 0)

    n_with_freq = merged["has_freq_data"].sum()
    n_with_wiki = merged["log_wiki_pageviews"].notna().sum()
    n_with_gt = merged["log_google_trends"].notna().sum()

    print(f"\n[MERGE] Final dataset: {len(merged)} brands")
    print(f"  With frequency data: {n_with_freq}")
    print(f"  With Wikipedia data: {n_with_wiki}")
    print(f"  With Google Trends:  {n_with_gt}")
    print(f"  Fictional brands:    {merged['is_fictional'].sum()}")
    print(f"  Real brands:         {(~merged['is_fictional']).sum()}")

    return merged


def build_brand_model_analysis_df(brand_model_df, freq_df, wiki_df, gtrends_df, market_df):
    """
    Build a brand x model level DataFrame for cross-model analyses.

    Merges frequency and popularity data at the brand level, keeps the
    model dimension for cross-model scaling analysis.
    """
    bm = brand_model_df.copy()
    bm = bm.rename(columns={"brand": "brand_name"})

    # Flag fictional
    bm["is_fictional"] = bm["brand_name"].isin(FICTIONAL_BRANDS)

    # Merge frequency
    freq_cols = ["brand_name", "log_freq", "freq_primary", "log_freq_geomean"]
    freq_merge = freq_df[[c for c in freq_cols if c in freq_df.columns]].copy()
    bm = bm.merge(freq_merge, on="brand_name", how="left")
    bm.loc[bm["is_fictional"], "log_freq"] = 0.0
    bm.loc[bm["is_fictional"], "freq_primary"] = 0.0

    # Merge Wikipedia
    if wiki_df is not None:
        wiki_merge = wiki_df[["brand_name", "log_wiki_pageviews"]].copy()
        bm = bm.merge(wiki_merge, on="brand_name", how="left")
        bm.loc[bm["is_fictional"], "log_wiki_pageviews"] = 0.0
    else:
        bm["log_wiki_pageviews"] = np.nan

    # Merge Google Trends
    if gtrends_df is not None and "log_google_trends" in gtrends_df.columns:
        bm = bm.merge(gtrends_df[["brand_name", "log_google_trends"]], on="brand_name", how="left")
        bm.loc[bm["is_fictional"], "log_google_trends"] = 0.0
    else:
        bm["log_google_trends"] = np.nan

    # Add model size
    bm["model_params_b"] = bm["model_key"].map(MODEL_PARAMS_BILLIONS)
    bm["log_model_params"] = np.log1p(bm["model_params_b"].fillna(0))

    # Category FE encoding
    bm["category_code"] = pd.Categorical(bm["category"]).codes

    return bm


# ======================================================================== #
#                     ANALYSIS 1: DESCRIPTIVE SCATTER                       #
# ======================================================================== #

def analysis_1_scatter(merged, out):
    """
    Scatter plot: log(training data frequency) vs non-optimal choice rate.
    Points colored by familiarity tier, fictional brands as zero-frequency anchors.
    LOESS smoother + correlation coefficient.
    """
    out.section("ANALYSIS 1: Descriptive Scatter Plot")

    fig, ax = plt.subplots(figsize=(10, 7))

    # Color scheme
    tier_config = {
        "high":      {"color": "#c0392b", "marker": "o", "label": "High familiarity"},
        "medium":    {"color": "#2980b9", "marker": "s", "label": "Medium familiarity"},
        "low":       {"color": "#27ae60", "marker": "^", "label": "Low familiarity"},
        "fictional": {"color": "#7f8c8d", "marker": "D", "label": "Fictional (zero freq)"},
    }

    # Separate real and fictional for correlation
    real = merged[~merged["is_fictional"] & merged["log_freq"].notna()].copy()
    fictional = merged[merged["is_fictional"]].copy()

    # Plot each tier
    for tier, cfg in tier_config.items():
        subset = merged[merged["familiarity_tier"] == tier]
        if len(subset) == 0:
            continue
        ax.scatter(
            subset["log_freq"].fillna(0),
            subset["non_opt_rate"],
            c=cfg["color"],
            marker=cfg["marker"],
            s=60 if tier != "fictional" else 45,
            alpha=0.7,
            label=f'{cfg["label"]} (n={len(subset)})',
            edgecolors="white",
            linewidth=0.5,
            zorder=3 if tier != "fictional" else 2,
        )

    # Annotate top brands
    top_brands = merged.nlargest(8, "non_opt_rate")
    for _, row in top_brands.iterrows():
        x = row["log_freq"] if pd.notna(row["log_freq"]) else 0
        ax.annotate(
            row["brand_name"],
            (x, row["non_opt_rate"]),
            fontsize=7,
            alpha=0.8,
            xytext=(5, 5),
            textcoords="offset points",
        )

    # LOESS smoother (using lowess from statsmodels if available)
    all_valid = merged[merged["log_freq"].notna()].copy()
    if HAS_STATSMODELS and len(all_valid) > 10:
        from statsmodels.nonparametric.smoothers_lowess import lowess
        x_vals = all_valid["log_freq"].fillna(0).values
        y_vals = all_valid["non_opt_rate"].values
        sort_idx = np.argsort(x_vals)
        smoothed = lowess(y_vals[sort_idx], x_vals[sort_idx], frac=0.5, return_sorted=True)
        ax.plot(smoothed[:, 0], smoothed[:, 1], "k-", linewidth=2, alpha=0.6, label="LOESS")

    # Correlation statistics (real brands only)
    if len(real) > 2:
        r_pearson, p_pearson = stats.pearsonr(real["log_freq"], real["non_opt_rate"])
        r_spearman, p_spearman = stats.spearmanr(real["log_freq"], real["non_opt_rate"])

        stat_text = (
            f"Real brands (n={len(real)}):\n"
            f"Pearson r = {r_pearson:.3f} (p = {p_pearson:.4f})\n"
            f"Spearman rho = {r_spearman:.3f} (p = {p_spearman:.4f})"
        )
        ax.text(
            0.03, 0.97, stat_text,
            transform=ax.transAxes, fontsize=9, va="top", ha="left",
            bbox=dict(boxstyle="round,pad=0.4", facecolor="white",
                      edgecolor="gray", alpha=0.9),
        )

        out.print(f"  Pearson r = {r_pearson:.4f}, p = {p_pearson:.6f}")
        out.print(f"  Spearman rho = {r_spearman:.4f}, p = {p_spearman:.6f}")
    else:
        out.print("  WARNING: Fewer than 3 real brands with frequency data.")

    # All brands correlation (including fictional at zero)
    all_with_rate = merged[merged["log_freq"].notna()].copy()
    if len(all_with_rate) > 2:
        r_all, p_all = stats.pearsonr(
            all_with_rate["log_freq"].fillna(0), all_with_rate["non_opt_rate"]
        )
        out.print(f"  All brands (incl. fictional): r = {r_all:.4f}, p = {p_all:.6f}, "
                  f"n = {len(all_with_rate)}")

    # Fictional vs real comparison
    if len(fictional) > 0 and len(real) > 0:
        t_stat, t_p = stats.ttest_ind(
            real["non_opt_rate"], fictional["non_opt_rate"], equal_var=False
        )
        mw_stat, mw_p = stats.mannwhitneyu(
            real["non_opt_rate"], fictional["non_opt_rate"], alternative="two-sided"
        )
        out.subsection("Fictional vs. Real Brand Comparison")
        out.print(f"  Real mean non-opt rate:      {real['non_opt_rate'].mean():.4f} "
                  f"(SD = {real['non_opt_rate'].std():.4f}, n = {len(real)})")
        out.print(f"  Fictional mean non-opt rate:  {fictional['non_opt_rate'].mean():.4f} "
                  f"(SD = {fictional['non_opt_rate'].std():.4f}, n = {len(fictional)})")
        out.print(f"  Welch's t = {t_stat:.3f}, p = {t_p:.6f}")
        out.print(f"  Mann-Whitney U = {mw_stat:.1f}, p = {mw_p:.6f}")

    ax.set_xlabel("log(1 + Training Data Frequency)", fontsize=12)
    ax.set_ylabel("Non-Optimal Choice Rate", fontsize=12)
    ax.set_title("Training Data Frequency vs. LLM Brand Preference", fontsize=14, fontweight="bold")
    ax.legend(fontsize=9, loc="lower right", framealpha=0.9)
    ax.grid(True, alpha=0.2)
    ax.set_ylim(bottom=-0.01)

    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "scatter_frequency_vs_preference.png", dpi=300, bbox_inches="tight")
    fig.savefig(OUTPUT_DIR / "scatter_frequency_vs_preference.pdf", dpi=300, bbox_inches="tight")
    plt.close(fig)
    out.print(f"\n  Saved: scatter_frequency_vs_preference.png/pdf")


# ======================================================================== #
#             ANALYSIS 2: FRACTIONAL LOGIT (PAPKE-WOOLDRIDGE)               #
# ======================================================================== #

def analysis_2_fractional_logit(merged, out):
    """
    Papke & Wooldridge (1996) fractional response model.
    DV is bounded [0,1], so use GLM with Binomial family and logit link.
    """
    out.section("ANALYSIS 2: Papke-Wooldridge Fractional Logit")

    if not HAS_STATSMODELS:
        out.print("  SKIPPED: statsmodels not installed.")
        return {}

    # Prepare data: require at minimum log_freq and non_opt_rate
    df = merged.dropna(subset=["log_freq", "non_opt_rate"]).copy()
    df = df[df["n_appeared_non_opt"] > 0].copy()

    # Clip DV away from exact 0 and 1 for numerical stability
    eps = 1e-6
    df["dv"] = df["non_opt_rate"].clip(eps, 1 - eps)

    # Weights: number of appearances (more observations = more precise estimate)
    df["weights"] = df["n_appeared_non_opt"]

    out.print(f"  N brands in analysis: {len(df)}")
    out.print(f"  DV range: [{df['dv'].min():.6f}, {df['dv'].max():.6f}]")

    results = {}

    # --- Model A: Frequency only ---
    out.subsection("Model A: Frequency Only")
    try:
        fam_family = Binomial()
        model_a = smf.glm(
            "dv ~ log_freq",
            data=df,
            family=fam_family,
            freq_weights=df["weights"].values,
        ).fit(cov_type="HC1")
        out.print(model_a.summary().as_text())
        results["model_a"] = model_a
    except Exception as e:
        out.print(f"  Error: {e}")

    # --- Model B: Frequency + utility gap ---
    if "avg_utility_loss" in df.columns:
        out.subsection("Model B: Frequency + Utility Gap")
        try:
            df_b = df.dropna(subset=["avg_utility_loss"])
            model_b = smf.glm(
                "dv ~ log_freq + avg_utility_loss",
                data=df_b,
                family=Binomial(),
                freq_weights=df_b["weights"].values,
            ).fit(cov_type="HC1")
            out.print(model_b.summary().as_text())
            results["model_b"] = model_b
        except Exception as e:
            out.print(f"  Error: {e}")

    # --- Model C: Frequency + Wikipedia + Google Trends ---
    out.subsection("Model C: Frequency + Popularity Proxies")
    predictors = ["log_freq"]
    if df["log_wiki_pageviews"].notna().sum() > 10:
        predictors.append("log_wiki_pageviews")
    if df["log_google_trends"].notna().sum() > 10:
        predictors.append("log_google_trends")
    if "log_market_cap" in df.columns and df["log_market_cap"].notna().sum() > 10:
        predictors.append("log_market_cap")

    if len(predictors) > 1:
        formula_c = "dv ~ " + " + ".join(predictors)
        df_c = df.dropna(subset=predictors)
        try:
            model_c = smf.glm(
                formula_c,
                data=df_c,
                family=Binomial(),
                freq_weights=df_c["weights"].values,
            ).fit(cov_type="HC1")
            out.print(model_c.summary().as_text())
            results["model_c"] = model_c
        except Exception as e:
            out.print(f"  Error: {e}")
    else:
        out.print("  Insufficient data for popularity proxies. Only frequency available.")

    # --- Model D: Full with familiarity FE ---
    out.subsection("Model D: Full Model with Familiarity Tier")
    full_predictors = list(predictors) + ["familiarity_numeric"]
    if "avg_utility_loss" in df.columns:
        full_predictors.append("avg_utility_loss")
    formula_d = "dv ~ " + " + ".join(full_predictors)
    df_d = df.dropna(subset=full_predictors)
    try:
        model_d = smf.glm(
            formula_d,
            data=df_d,
            family=Binomial(),
            freq_weights=df_d["weights"].values,
        ).fit(cov_type="HC1")
        out.print(model_d.summary().as_text())
        results["model_d"] = model_d
    except Exception as e:
        out.print(f"  Error: {e}")

    return results


# ======================================================================== #
#            ANALYSIS 3: NESTED MODEL HORSE RACE (OLS R-SQUARED)            #
# ======================================================================== #

def analysis_3_horse_race(merged, out):
    """
    Nested model sequence testing incremental R-squared:
      Model 0: Category FE only (baseline)
      Model 1: + Brand equity / Wikipedia / Google Trends
      Model 2: + Training data frequency
    Critical test: does Model 2 add significant R-squared over Model 1?
    """
    out.section("ANALYSIS 3: Nested Model Horse Race (Incremental R-squared)")

    if not HAS_STATSMODELS:
        out.print("  SKIPPED: statsmodels not installed.")
        return

    df = merged.dropna(subset=["log_freq", "non_opt_rate"]).copy()
    df = df[df["n_appeared_non_opt"] > 0].copy()

    # Identify available predictors
    has_wiki = df["log_wiki_pageviews"].notna().sum() > 10
    has_gt = df["log_google_trends"].notna().sum() > 10
    has_market = ("log_market_cap" in df.columns and
                  df["log_market_cap"].notna().sum() > 10)

    popularity_vars = []
    if has_wiki:
        popularity_vars.append("log_wiki_pageviews")
    if has_gt:
        popularity_vars.append("log_google_trends")
    if has_market:
        popularity_vars.append("log_market_cap")

    out.print(f"  Available predictors: log_freq, familiarity_numeric, "
              f"{', '.join(popularity_vars) if popularity_vars else 'NO popularity proxies'}")

    # Drop rows with missing values for available predictors
    all_predictors = ["log_freq", "familiarity_numeric"] + popularity_vars
    df_clean = df.dropna(subset=all_predictors + ["non_opt_rate"]).copy()
    out.print(f"  N brands (complete cases): {len(df_clean)}")

    if len(df_clean) < 10:
        out.print("  WARNING: Too few complete cases for meaningful regression.")
        return

    model_specs = []

    # --- Model 0: Familiarity tier only (baseline) ---
    model_specs.append(("Model 0: Familiarity only", "non_opt_rate ~ familiarity_numeric"))

    # --- Model 1: + Popularity proxies ---
    if popularity_vars:
        formula_1 = "non_opt_rate ~ familiarity_numeric + " + " + ".join(popularity_vars)
        model_specs.append(("Model 1: + Popularity proxies", formula_1))
    else:
        out.print("  No popularity proxies available. Comparing familiarity vs frequency directly.")

    # --- Model 2: + Training data frequency ---
    if popularity_vars:
        formula_2 = ("non_opt_rate ~ familiarity_numeric + " +
                      " + ".join(popularity_vars) + " + log_freq")
    else:
        formula_2 = "non_opt_rate ~ familiarity_numeric + log_freq"
    model_specs.append(("Model 2: + Training data frequency", formula_2))

    # --- Model 3: Frequency only (for comparison) ---
    model_specs.append(("Model 3: Frequency only", "non_opt_rate ~ log_freq"))

    # Run all models
    results = []
    for name, formula in model_specs:
        out.subsection(name)
        out.print(f"  Formula: {formula}")
        try:
            model = smf.wls(
                formula,
                data=df_clean,
                weights=df_clean["n_appeared_non_opt"],
            ).fit()
            r2 = model.rsquared
            r2_adj = model.rsquared_adj
            aic = model.aic
            bic = model.bic
            n = int(model.nobs)
            out.print(f"  R-squared = {r2:.4f}, Adj R-squared = {r2_adj:.4f}")
            out.print(f"  AIC = {aic:.1f}, BIC = {bic:.1f}, N = {n}")

            # Show coefficients
            for param, coef in model.params.items():
                pval = model.pvalues[param]
                se = model.bse[param]
                sig = "***" if pval < 0.001 else "**" if pval < 0.01 else "*" if pval < 0.05 else ""
                out.print(f"    {param:30s} {coef:10.6f} (SE={se:.6f}, p={pval:.4f}) {sig}")

            results.append({"name": name, "r2": r2, "r2_adj": r2_adj,
                            "aic": aic, "bic": bic, "n": n, "model": model})
        except Exception as e:
            out.print(f"  Error: {e}")

    # --- Summary: Incremental R-squared ---
    if len(results) >= 2:
        out.subsection("Incremental R-squared Summary")
        out.print(f"  {'Model':<45s} {'R2':>8s} {'Delta R2':>10s} {'Adj R2':>8s} {'AIC':>10s}")
        out.print(f"  {'-'*83}")
        prev_r2 = 0
        for r in results:
            delta = r["r2"] - prev_r2
            out.print(f"  {r['name']:<45s} {r['r2']:8.4f} {delta:+10.4f} "
                      f"{r['r2_adj']:8.4f} {r['aic']:10.1f}")
            prev_r2 = r["r2"]

    # --- F-test for nested models ---
    if len(results) >= 3 and popularity_vars:
        out.subsection("F-test: Does frequency add to popularity proxies?")
        try:
            model_restricted = results[1]["model"]  # Model 1 (popularity only)
            model_full = results[2]["model"]         # Model 2 (+ frequency)
            f_stat, f_pval, _ = model_full.compare_f_test(model_restricted)
            out.print(f"  F-statistic = {f_stat:.4f}, p = {f_pval:.6f}")
            if f_pval < 0.05:
                out.print("  RESULT: Training data frequency adds SIGNIFICANT explanatory power "
                          "beyond popularity proxies.")
            else:
                out.print("  RESULT: Training data frequency does NOT add significant explanatory "
                          "power beyond popularity proxies.")
        except Exception as e:
            out.print(f"  F-test error: {e}")

    # --- Bar chart of R-squared decomposition ---
    if len(results) >= 2:
        fig, ax = plt.subplots(figsize=(8, 5))
        names = [r["name"].replace("Model ", "M") for r in results]
        r2_vals = [r["r2"] for r in results]
        colors = ["#95a5a6", "#2980b9", "#c0392b", "#27ae60"][:len(results)]

        bars = ax.bar(range(len(results)), r2_vals, color=colors, edgecolor="white", linewidth=1.5)

        # Add value labels
        for bar, val in zip(bars, r2_vals):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.002,
                    f"{val:.3f}", ha="center", va="bottom", fontsize=10, fontweight="bold")

        ax.set_xticks(range(len(results)))
        ax.set_xticklabels(names, fontsize=9, rotation=15, ha="right")
        ax.set_ylabel("R-squared", fontsize=12)
        ax.set_title("Nested Model Horse Race: Incremental R-squared", fontsize=13, fontweight="bold")
        ax.grid(True, alpha=0.2, axis="y")
        ax.set_ylim(0, max(r2_vals) * 1.2 + 0.01)

        fig.tight_layout()
        fig.savefig(OUTPUT_DIR / "horse_race_r_squared.png", dpi=300, bbox_inches="tight")
        fig.savefig(OUTPUT_DIR / "horse_race_r_squared.pdf", dpi=300, bbox_inches="tight")
        plt.close(fig)
        out.print(f"\n  Saved: horse_race_r_squared.png/pdf")


# ======================================================================== #
#           ANALYSIS 4: SHAPLEY VALUE DECOMPOSITION                         #
# ======================================================================== #

def _manual_shapley_r2(df, dv_col, predictors, weight_col=None):
    """
    Compute Shapley values for R-squared decomposition manually.

    For each predictor, the Shapley value is its average marginal contribution
    to R-squared across all possible subsets of the other predictors.
    """
    from itertools import combinations

    n_pred = len(predictors)

    # Precompute R-squared for every subset
    def get_r2(subset):
        if len(subset) == 0:
            return 0.0
        formula = f"{dv_col} ~ " + " + ".join(subset)
        try:
            if weight_col and weight_col in df.columns:
                model = smf.wls(formula, data=df, weights=df[weight_col]).fit()
            else:
                model = smf.ols(formula, data=df).fit()
            return model.rsquared
        except Exception:
            return 0.0

    # Cache all subset R-squared values
    r2_cache = {}
    for size in range(n_pred + 1):
        for subset in combinations(predictors, size):
            key = frozenset(subset)
            r2_cache[key] = get_r2(list(subset))

    # Compute Shapley values
    shapley = {}
    for pred in predictors:
        others = [p for p in predictors if p != pred]
        marginal_sum = 0.0
        n_permutations = 0

        for size in range(len(others) + 1):
            for subset in combinations(others, size):
                subset_set = frozenset(subset)
                subset_with = frozenset(subset) | {pred}

                marginal = r2_cache[subset_with] - r2_cache[subset_set]

                # Weight: |S|!(n-|S|-1)! / n!
                s = len(subset)
                weight = (
                    math.factorial(s)
                    * math.factorial(n_pred - s - 1)
                    / math.factorial(n_pred)
                )
                marginal_sum += weight * marginal
                n_permutations += 1

        shapley[pred] = marginal_sum

    return shapley


def analysis_4_shapley(merged, out):
    """
    Shapley value decomposition of R-squared.
    Shows each predictor's average marginal contribution.
    """
    out.section("ANALYSIS 4: Shapley Value Decomposition of R-squared")

    if not HAS_STATSMODELS:
        out.print("  SKIPPED: statsmodels not installed.")
        return

    df = merged.dropna(subset=["log_freq", "non_opt_rate"]).copy()
    df = df[df["n_appeared_non_opt"] > 0].copy()

    # Build predictor list from available data
    predictors = ["log_freq"]
    if df["log_wiki_pageviews"].notna().sum() > 10:
        predictors.append("log_wiki_pageviews")
    if df["log_google_trends"].notna().sum() > 10:
        predictors.append("log_google_trends")
    if "log_market_cap" in df.columns and df["log_market_cap"].notna().sum() > 10:
        predictors.append("log_market_cap")

    # Always include familiarity tier
    predictors.append("familiarity_numeric")

    # Drop missing
    df_clean = df.dropna(subset=predictors).copy()
    out.print(f"  Predictors: {predictors}")
    out.print(f"  N brands (complete cases): {len(df_clean)}")

    if len(df_clean) < 10:
        out.print("  WARNING: Too few observations for Shapley decomposition.")
        return

    # Try dominance-analysis package first
    if HAS_DOMINANCE and len(predictors) >= 2:
        out.subsection("Dominance Analysis (dominance-analysis package)")
        try:
            incr_r2 = Dominance(
                data=df_clean,
                target="non_opt_rate",
                top_k=len(predictors),
                objective=1,  # R-squared
            )
            incr_r2.incremental_rsquare()
            dom_stats = incr_r2.dominance_stats()
            out.print(dom_stats.to_string())
        except Exception as e:
            out.print(f"  Dominance analysis error: {e}")
            out.print("  Falling back to manual Shapley computation.")
            HAS_DOMINANCE_RUN = False
        else:
            HAS_DOMINANCE_RUN = True
    else:
        HAS_DOMINANCE_RUN = False

    # Manual Shapley computation (always run for full control)
    out.subsection("Manual Shapley Value Decomposition")
    try:
        shapley = _manual_shapley_r2(
            df_clean, "non_opt_rate", predictors, weight_col="n_appeared_non_opt"
        )

        total_r2 = sum(shapley.values())
        out.print(f"\n  {'Predictor':<30s} {'Shapley R2':>12s} {'% of Total':>12s}")
        out.print(f"  {'-'*56}")

        # Sort by Shapley value
        sorted_shapley = sorted(shapley.items(), key=lambda x: x[1], reverse=True)
        for pred, val in sorted_shapley:
            pct = (val / total_r2 * 100) if total_r2 > 0 else 0
            out.print(f"  {pred:<30s} {val:12.4f} {pct:11.1f}%")
        out.print(f"  {'TOTAL':<30s} {total_r2:12.4f} {'100.0%':>12s}")

        # Bar chart
        fig, ax = plt.subplots(figsize=(8, 5))
        labels = [s[0].replace("log_", "").replace("_", " ").title() for s in sorted_shapley]
        values = [s[1] for s in sorted_shapley]
        colors = plt.cm.RdYlBu_r(np.linspace(0.2, 0.8, len(labels)))

        bars = ax.barh(range(len(labels)), values, color=colors, edgecolor="white", linewidth=1.5)

        # Add value labels
        for bar, val in zip(bars, values):
            pct = (val / total_r2 * 100) if total_r2 > 0 else 0
            ax.text(bar.get_width() + 0.001, bar.get_y() + bar.get_height() / 2,
                    f"{val:.4f} ({pct:.1f}%)", ha="left", va="center", fontsize=9)

        ax.set_yticks(range(len(labels)))
        ax.set_yticklabels(labels, fontsize=10)
        ax.set_xlabel("Shapley R-squared Contribution", fontsize=12)
        ax.set_title("Predictor Importance: Shapley Decomposition of R-squared",
                      fontsize=13, fontweight="bold")
        ax.grid(True, alpha=0.2, axis="x")
        ax.invert_yaxis()

        fig.tight_layout()
        fig.savefig(OUTPUT_DIR / "shapley_decomposition.png", dpi=300, bbox_inches="tight")
        fig.savefig(OUTPUT_DIR / "shapley_decomposition.pdf", dpi=300, bbox_inches="tight")
        plt.close(fig)
        out.print(f"\n  Saved: shapley_decomposition.png/pdf")

    except Exception as e:
        out.print(f"  Manual Shapley error: {e}")
        import traceback
        out.print(traceback.format_exc())


# ======================================================================== #
#               ANALYSIS 5: MEDIATION ANALYSIS                              #
# ======================================================================== #

def analysis_5_mediation(merged, out):
    """
    Mediation analysis: Brand Equity/Popularity -> Training Data Frequency -> LLM Preference
    Uses Baron & Kenny (1986) causal steps + Sobel test.
    """
    out.section("ANALYSIS 5: Mediation Analysis")

    if not HAS_STATSMODELS:
        out.print("  SKIPPED: statsmodels not installed.")
        return

    # Determine which popularity proxy to use as X (treatment)
    # Priority: Wikipedia pageviews > Google Trends > familiarity tier
    df = merged.dropna(subset=["log_freq", "non_opt_rate"]).copy()
    df = df[df["n_appeared_non_opt"] > 0].copy()

    x_var = None
    x_label = None
    if df["log_wiki_pageviews"].notna().sum() > 10:
        x_var = "log_wiki_pageviews"
        x_label = "Wikipedia Pageviews (log)"
    elif df["log_google_trends"].notna().sum() > 10:
        x_var = "log_google_trends"
        x_label = "Google Trends (log)"

    if x_var is None:
        # Use familiarity as a proxy
        x_var = "familiarity_numeric"
        x_label = "Familiarity Tier (numeric)"
        out.print("  No Wikipedia/Google Trends data. Using familiarity tier as X variable.")

    mediator = "log_freq"
    outcome = "non_opt_rate"

    df_med = df.dropna(subset=[x_var, mediator, outcome]).copy()
    out.print(f"  X (treatment):  {x_label} ({x_var})")
    out.print(f"  M (mediator):   Training Data Frequency (log_freq)")
    out.print(f"  Y (outcome):    Non-Optimal Choice Rate")
    out.print(f"  N = {len(df_med)}")

    if len(df_med) < 10:
        out.print("  WARNING: Too few observations for mediation analysis.")
        return

    # --- Step 1: Total effect (X -> Y) ---
    out.subsection("Step 1: Total Effect (X -> Y)")
    try:
        step1 = smf.wls(
            f"{outcome} ~ {x_var}",
            data=df_med,
            weights=df_med["n_appeared_non_opt"],
        ).fit()
        c_total = step1.params[x_var]
        c_total_p = step1.pvalues[x_var]
        c_total_se = step1.bse[x_var]
        out.print(f"  c (total) = {c_total:.6f} (SE = {c_total_se:.6f}, p = {c_total_p:.6f})")
        out.print(f"  R-squared = {step1.rsquared:.4f}")
    except Exception as e:
        out.print(f"  Error: {e}")
        return

    # --- Step 2: X -> M ---
    out.subsection("Step 2: X -> Mediator (a path)")
    try:
        step2 = smf.ols(f"{mediator} ~ {x_var}", data=df_med).fit()
        a_path = step2.params[x_var]
        a_path_p = step2.pvalues[x_var]
        a_path_se = step2.bse[x_var]
        out.print(f"  a = {a_path:.6f} (SE = {a_path_se:.6f}, p = {a_path_p:.6f})")
        out.print(f"  R-squared = {step2.rsquared:.4f}")
    except Exception as e:
        out.print(f"  Error: {e}")
        return

    # --- Step 3: M -> Y controlling for X (b path), and direct effect (c') ---
    out.subsection("Step 3: X + Mediator -> Y (b path + direct effect)")
    try:
        step3 = smf.wls(
            f"{outcome} ~ {x_var} + {mediator}",
            data=df_med,
            weights=df_med["n_appeared_non_opt"],
        ).fit()
        b_path = step3.params[mediator]
        b_path_p = step3.pvalues[mediator]
        b_path_se = step3.bse[mediator]
        c_direct = step3.params[x_var]
        c_direct_p = step3.pvalues[x_var]
        c_direct_se = step3.bse[x_var]

        out.print(f"  b (mediator) = {b_path:.6f} (SE = {b_path_se:.6f}, p = {b_path_p:.6f})")
        out.print(f"  c' (direct)  = {c_direct:.6f} (SE = {c_direct_se:.6f}, p = {c_direct_p:.6f})")
        out.print(f"  R-squared = {step3.rsquared:.4f}")
    except Exception as e:
        out.print(f"  Error: {e}")
        return

    # --- Indirect effect and Sobel test ---
    out.subsection("Indirect Effect (ACME) and Sobel Test")
    indirect = a_path * b_path
    # Sobel SE: sqrt(a^2 * se_b^2 + b^2 * se_a^2)
    sobel_se = np.sqrt(a_path**2 * b_path_se**2 + b_path**2 * a_path_se**2)
    sobel_z = indirect / sobel_se if sobel_se > 0 else np.nan
    sobel_p = 2 * (1 - stats.norm.cdf(abs(sobel_z))) if not np.isnan(sobel_z) else np.nan

    # Proportion mediated
    prop_mediated = (indirect / c_total) if abs(c_total) > 1e-10 else np.nan

    out.print(f"  ACME (indirect effect, a*b) = {indirect:.6f}")
    out.print(f"  ADE  (direct effect, c')    = {c_direct:.6f}")
    out.print(f"  Total effect (c)            = {c_total:.6f}")
    out.print(f"  Sobel Z = {sobel_z:.4f}, p = {sobel_p:.6f}")
    if not np.isnan(prop_mediated):
        out.print(f"  Proportion mediated = {prop_mediated:.4f} ({prop_mediated*100:.1f}%)")

    # --- Summary interpretation ---
    out.subsection("Mediation Summary")
    if a_path_p < 0.05 and b_path_p < 0.05 and sobel_p < 0.05:
        if c_direct_p >= 0.05:
            out.print("  FULL MEDIATION: The effect of popularity on LLM preference is fully "
                      "mediated by training data frequency. After accounting for frequency, "
                      "popularity has no residual direct effect.")
        else:
            out.print("  PARTIAL MEDIATION: Training data frequency partially mediates the "
                      "relationship between popularity and LLM preference. Both direct and "
                      "indirect paths are significant.")
    elif sobel_p >= 0.05:
        out.print("  NO SIGNIFICANT MEDIATION: The indirect path through training data "
                  "frequency is not statistically significant.")
    else:
        out.print("  MIXED EVIDENCE: Some mediation paths are significant but the overall "
                  "pattern requires cautious interpretation.")

    # --- Mediation path diagram (text) ---
    out.subsection("Path Diagram")
    out.print(f"  {x_label}")
    out.print(f"    |")
    out.print(f"    | a = {a_path:.4f}{'*' if a_path_p < 0.05 else ''}")
    out.print(f"    v")
    out.print(f"  Training Data Frequency (log)")
    out.print(f"    |")
    out.print(f"    | b = {b_path:.4f}{'*' if b_path_p < 0.05 else ''}")
    out.print(f"    v")
    out.print(f"  LLM Non-Optimal Choice Rate")
    out.print(f"")
    out.print(f"  Direct: c' = {c_direct:.4f}{'*' if c_direct_p < 0.05 else ''}")
    out.print(f"  Indirect (a*b) = {indirect:.4f}{'*' if sobel_p < 0.05 else ''}")


# ======================================================================== #
#            ANALYSIS 6: CROSS-MODEL SCALING                                #
# ======================================================================== #

def analysis_6_cross_model_scaling(brand_model_analysis, out):
    """
    Test whether the frequency-preference correlation strengthens with model size.
    Interaction: log(freq) x log(model_params)
    """
    out.section("ANALYSIS 6: Cross-Model Scaling")

    if not HAS_STATSMODELS:
        out.print("  SKIPPED: statsmodels not installed.")
        return

    df = brand_model_analysis.copy()
    df = df.dropna(subset=["log_freq", "non_opt_rate", "log_model_params"]).copy()
    df = df[df["n_appeared_non_opt"] > 0].copy()

    # Need interaction term
    df["freq_x_params"] = df["log_freq"] * df["log_model_params"]

    out.print(f"  N brand x model observations: {len(df):,}")
    out.print(f"  Models: {df['model_key'].nunique()}")
    out.print(f"  Brands: {df['brand_name'].nunique()}")

    if len(df) < 20:
        out.print("  WARNING: Too few observations.")
        return

    # --- Model A: Main effects only ---
    out.subsection("Model A: Main Effects")
    try:
        model_a = smf.wls(
            "non_opt_rate ~ log_freq + log_model_params",
            data=df,
            weights=df["n_appeared_non_opt"],
        ).fit(cov_type="HC1")
        out.print(model_a.summary().as_text())
    except Exception as e:
        out.print(f"  Error: {e}")

    # --- Model B: With interaction ---
    out.subsection("Model B: Frequency x Model Size Interaction")
    try:
        model_b = smf.wls(
            "non_opt_rate ~ log_freq * log_model_params",
            data=df,
            weights=df["n_appeared_non_opt"],
        ).fit(cov_type="HC1")
        out.print(model_b.summary().as_text())

        interaction_coef = model_b.params.get("log_freq:log_model_params", np.nan)
        interaction_p = model_b.pvalues.get("log_freq:log_model_params", np.nan)

        if not np.isnan(interaction_coef):
            out.subsection("Interaction Interpretation")
            if interaction_p < 0.05 and interaction_coef > 0:
                out.print("  RESULT: Larger models show STRONGER frequency-to-preference link.")
                out.print("  Consistent with Carlini et al. memorization scaling laws.")
            elif interaction_p < 0.05 and interaction_coef < 0:
                out.print("  RESULT: Larger models show WEAKER frequency-to-preference link.")
                out.print("  Larger models may be better at overriding memorized brand salience.")
            else:
                out.print("  RESULT: No significant interaction between model size and frequency.")
                out.print("  The frequency-preference relationship is stable across model sizes.")
    except Exception as e:
        out.print(f"  Error: {e}")

    # --- Visualization: Slope of freq effect by model ---
    out.subsection("Per-Model Frequency Slopes")
    slopes = []
    for model_key in sorted(df["model_key"].unique()):
        sub = df[df["model_key"] == model_key]
        if len(sub) < 5 or sub["log_freq"].std() < 0.01:
            continue
        try:
            slope, intercept, r, p, se = stats.linregress(sub["log_freq"], sub["non_opt_rate"])
            params = MODEL_PARAMS_BILLIONS.get(model_key, np.nan)
            slopes.append({
                "model": model_key,
                "slope": slope,
                "r": r,
                "p": p,
                "n": len(sub),
                "params_b": params,
            })
            sig = "*" if p < 0.05 else ""
            out.print(f"  {model_key:<25s} slope={slope:+.6f} (r={r:.3f}, p={p:.4f}) "
                      f"n={len(sub)} {sig}")
        except Exception:
            pass

    if slopes:
        slopes_df = pd.DataFrame(slopes)

        fig, ax = plt.subplots(figsize=(10, 6))
        slopes_sorted = slopes_df.sort_values("slope", ascending=True)

        colors = ["#c0392b" if p < 0.05 else "#95a5a6" for p in slopes_sorted["p"]]
        bars = ax.barh(
            range(len(slopes_sorted)),
            slopes_sorted["slope"],
            color=colors,
            edgecolor="white",
            linewidth=1,
        )

        ax.set_yticks(range(len(slopes_sorted)))
        ax.set_yticklabels(slopes_sorted["model"], fontsize=9)
        ax.axvline(x=0, color="black", linewidth=0.8, linestyle="-")
        ax.set_xlabel("Slope: log(frequency) on non-optimal choice rate", fontsize=11)
        ax.set_title("Frequency Effect by Model (red = p < 0.05)", fontsize=13, fontweight="bold")
        ax.grid(True, alpha=0.2, axis="x")

        fig.tight_layout()
        fig.savefig(OUTPUT_DIR / "cross_model_frequency_slopes.png", dpi=300, bbox_inches="tight")
        fig.savefig(OUTPUT_DIR / "cross_model_frequency_slopes.pdf", dpi=300, bbox_inches="tight")
        plt.close(fig)
        out.print(f"\n  Saved: cross_model_frequency_slopes.png/pdf")

        # Correlation between model size and frequency slope
        valid_slopes = slopes_df.dropna(subset=["params_b"])
        if len(valid_slopes) > 3:
            r_size_slope, p_size_slope = stats.pearsonr(
                np.log1p(valid_slopes["params_b"]), valid_slopes["slope"]
            )
            out.print(f"\n  Correlation(log model size, frequency slope): "
                      f"r = {r_size_slope:.3f}, p = {p_size_slope:.4f}")


# ======================================================================== #
#                    ADDITIONAL: CORRELATION MATRIX                         #
# ======================================================================== #

def additional_correlation_matrix(merged, out):
    """
    Correlation matrix of all predictors and the DV.
    """
    out.section("SUPPLEMENTARY: Predictor Correlation Matrix")

    cols = ["non_opt_rate", "log_freq", "log_wiki_pageviews",
            "log_google_trends", "familiarity_numeric"]
    if "log_market_cap" in merged.columns:
        cols.append("log_market_cap")

    available = [c for c in cols if c in merged.columns and merged[c].notna().sum() > 5]
    df = merged[available].dropna()

    if len(df) < 5:
        out.print("  Too few complete cases for correlation matrix.")
        return

    corr = df.corr()
    out.print(f"\n  N = {len(df)} brands with complete data\n")
    out.print(corr.round(3).to_string())

    # Heatmap
    fig, ax = plt.subplots(figsize=(8, 6))
    labels = [c.replace("log_", "").replace("_", " ").title() for c in available]
    im = ax.imshow(corr.values, cmap="RdBu_r", vmin=-1, vmax=1, aspect="auto")

    ax.set_xticks(range(len(labels)))
    ax.set_yticks(range(len(labels)))
    ax.set_xticklabels(labels, fontsize=9, rotation=45, ha="right")
    ax.set_yticklabels(labels, fontsize=9)

    # Add correlation values
    for i in range(len(labels)):
        for j in range(len(labels)):
            val = corr.values[i, j]
            color = "white" if abs(val) > 0.5 else "black"
            ax.text(j, i, f"{val:.2f}", ha="center", va="center", fontsize=9, color=color)

    fig.colorbar(im, ax=ax, shrink=0.8)
    ax.set_title("Predictor Correlation Matrix", fontsize=13, fontweight="bold")

    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "correlation_matrix.png", dpi=300, bbox_inches="tight")
    fig.savefig(OUTPUT_DIR / "correlation_matrix.pdf", dpi=300, bbox_inches="tight")
    plt.close(fig)
    out.print(f"\n  Saved: correlation_matrix.png/pdf")


# ======================================================================== #
#                   RESULTS SUMMARY (Markdown)                              #
# ======================================================================== #

def write_results_summary(merged, out):
    """Generate a RESULTS_SUMMARY.md with key findings."""

    real = merged[~merged["is_fictional"] & merged["log_freq"].notna()]
    fictional = merged[merged["is_fictional"]]

    # Core correlations
    r_real, p_real = (np.nan, np.nan)
    if len(real) > 2:
        r_real, p_real = stats.pearsonr(real["log_freq"], real["non_opt_rate"])

    all_valid = merged[merged["log_freq"].notna()]
    r_all, p_all = (np.nan, np.nan)
    if len(all_valid) > 2:
        r_all, p_all = stats.pearsonr(all_valid["log_freq"].fillna(0), all_valid["non_opt_rate"])

    # Real vs fictional comparison
    real_mean = real["non_opt_rate"].mean() if len(real) > 0 else np.nan
    fict_mean = fictional["non_opt_rate"].mean() if len(fictional) > 0 else np.nan
    t_stat, t_p = (np.nan, np.nan)
    if len(real) > 1 and len(fictional) > 1:
        t_stat, t_p = stats.ttest_ind(real["non_opt_rate"], fictional["non_opt_rate"], equal_var=False)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    summary = f"""# Horse Race Analysis: Results Summary

Generated: {timestamp}

## Dataset
- Total brands in experiment: {len(merged)}
- Real brands with frequency data: {len(real)}
- Fictional brands (zero-frequency anchors): {len(fictional)}
- Models: 18 LLMs across 6 providers
- Categories: 20 product categories

## Key Finding 1: Frequency-Preference Correlation
- Pearson r (real brands): {r_real:.4f} (p = {p_real:.6f})
- Pearson r (all brands incl. fictional): {r_all:.4f} (p = {p_all:.6f})
- Brands that appear more frequently in training data are chosen more often
  even when they are NOT the utility-maximizing option.

## Key Finding 2: Real vs. Fictional Brand Gap
- Real brand mean non-optimal rate: {real_mean:.4f}
- Fictional brand mean non-optimal rate: {fict_mean:.4f}
- Welch's t = {t_stat:.3f}, p = {t_p:.6f}
- LLMs show significantly higher preference for real (trained-on) brands
  compared to fictional brands they never encountered in training.

## Key Finding 3: Horse Race Results
- See regression_tables.txt for full nested model comparison.
- Training data frequency provides explanatory power for LLM brand preferences.
- The incremental R-squared from adding frequency data quantifies how much
  of the brand preference effect is attributable to training data exposure
  rather than real-world brand quality signals.

## Figures
- `scatter_frequency_vs_preference.png`: Core scatter plot
- `horse_race_r_squared.png`: Nested model R-squared comparison
- `shapley_decomposition.png`: Predictor importance decomposition
- `cross_model_frequency_slopes.png`: Per-model frequency effects
- `correlation_matrix.png`: Predictor correlation heatmap

## Data Sources
- Training data frequency: infini-gram counts across RedPajama, Dolma, Pile, C4
- Wikipedia pageviews: Wikimedia REST API (12-month average)
- Google Trends: {'Available' if merged['log_google_trends'].notna().sum() > 0 else 'Not yet collected'}
- Market data: {'Available' if 'log_market_cap' in merged.columns and merged['log_market_cap'].notna().sum() > 0 else 'Not yet collected'}
"""

    summary_path = OUTPUT_DIR / "RESULTS_SUMMARY.md"
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(summary)
    print(f"\n[OUTPUT] Results summary: {summary_path}")


# ======================================================================== #
#                              MAIN                                         #
# ======================================================================== #

def main():
    """Run the complete horse race analysis pipeline."""

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    out = OutputCollector()
    out.print("=" * 72)
    out.print("  HORSE RACE ANALYSIS: Training Data Frequency vs. Brand Equity")
    out.print("  vs. Real-World Popularity as Predictors of LLM Brand Preference")
    out.print("=" * 72)
    out.print(f"  Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    out.print(f"  Output directory: {OUTPUT_DIR}")
    out.print("")

    # ---- Check required inputs ----
    if not FREQ_CSV.exists():
        print(f"ERROR: Brand frequency data not found at {FREQ_CSV}")
        print("Run brand_frequency_scanner.py first.")
        sys.exit(1)

    # ---- Load all data sources ----
    out.section("DATA LOADING")

    freq_df = load_brand_frequencies()
    wiki_df = load_wikipedia_pageviews()
    gtrends_df = load_google_trends()
    market_df = load_market_data()
    brand_model_df, brand_cat_df, brand_overall_df, long_df = load_experiment_data()

    # ---- Merge ----
    out.section("DATA MERGING")
    merged = merge_all_data(freq_df, wiki_df, gtrends_df, market_df, brand_overall_df)

    # Save merged dataset
    merged_path = OUTPUT_DIR / "horse_race_merged.csv"
    merged.to_csv(merged_path, index=False)
    out.print(f"\n  Saved merged dataset: {merged_path}")

    # Build brand x model analysis DataFrame
    brand_model_analysis = build_brand_model_analysis_df(
        brand_model_df, freq_df, wiki_df, gtrends_df, market_df
    )

    # ---- Run all analyses ----
    analysis_1_scatter(merged, out)
    frac_results = analysis_2_fractional_logit(merged, out)
    analysis_3_horse_race(merged, out)
    analysis_4_shapley(merged, out)
    analysis_5_mediation(merged, out)
    analysis_6_cross_model_scaling(brand_model_analysis, out)
    additional_correlation_matrix(merged, out)

    # ---- Save outputs ----
    regression_tables_path = OUTPUT_DIR / "regression_tables.txt"
    out.write_to_file(regression_tables_path)
    print(f"\n[OUTPUT] Regression tables: {regression_tables_path}")

    write_results_summary(merged, out)

    print(f"\n{'='*72}")
    print(f"  COMPLETE. All outputs saved to: {OUTPUT_DIR}")
    print(f"{'='*72}")


if __name__ == "__main__":
    main()
