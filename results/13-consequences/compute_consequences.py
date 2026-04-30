"""
Consequences Analyses for Nature RR — "So What" Analyses
=========================================================

Three analyses that transform "interesting observation" into "policy-relevant finding":

1. THE BRAND TAX: Dollar cost of AI misalignment at scale
2. HHI MARKET CONCENTRATION: AI-driven demand concentration by category
3. COMPREHENSIVE BRAND PROFILE TABLE: Supplementary Table 1

All computed from existing data — no new API calls needed.

Usage:
    cd projects/spec-resistance
    python results/13-consequences/compute_consequences.py
"""

import sys, os, csv, json, ast, math
from collections import defaultdict, Counter
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# Setup paths
PROJECT = Path(__file__).resolve().parents[3]  # spec-resistance/
sys.path.insert(0, str(PROJECT))
OUT = Path(__file__).resolve().parent

# ──────────────────────────────────────────────────────────────────
# 0. LOAD DATA
# ──────────────────────────────────────────────────────────────────

print("=" * 70)
print("CONSEQUENCES ANALYSES — Nature RR")
print("=" * 70)

# Load assortments for product-level data
from experiment.assortments import ALL_ASSORTMENTS, CATEGORY_METADATA

# Build lookup: assortment_id -> {letter: product_dict}
ASSORT_PRODUCTS = {}
for a in ALL_ASSORTMENTS:
    prods = {}
    for p in a["products"]:
        prods[p["letter"]] = p
    ASSORT_PRODUCTS[a["id"]] = prods

# Compute utility for each product in each assortment
# U = 0.5 * quality_score + 0.5 * value_score
# value_score = 1 - price / (max_price * 1.1)
ASSORT_UTILITIES = {}
for aid, prods in ASSORT_PRODUCTS.items():
    max_price = max(p["price"] for p in prods.values())
    utils = {}
    for letter, p in prods.items():
        value = 1.0 - p["price"] / (max_price * 1.1)
        utility = 0.5 * p["quality_score"] + 0.5 * value
        utils[letter] = utility
    ASSORT_UTILITIES[aid] = utils

# Identify optimal product per assortment
ASSORT_OPTIMAL_LETTER = {}
for aid, utils in ASSORT_UTILITIES.items():
    best = max(utils, key=lambda k: utils[k])
    ASSORT_OPTIMAL_LETTER[aid] = best

# Load main CSV
CSV_PATH = PROJECT / "data" / "processed" / "spec_resistance_FULL.csv"
print(f"\nLoading {CSV_PATH.name}...")
rows = []
with open(CSV_PATH, encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        rows.append(row)
print(f"  Loaded {len(rows):,} trials")

# Filter to baseline condition only for consequence analyses
baseline_rows = [r for r in rows if r["condition"] == "baseline"]
print(f"  Baseline trials: {len(baseline_rows):,}")

# Load brand frequencies
FREQ_PATH = PROJECT / "nature-rr" / "data" / "brand_frequencies.csv"
brand_freq = defaultdict(float)
with open(FREQ_PATH, encoding="utf-8") as f:
    for row in csv.DictReader(f):
        if row["query_type"] == "brand_only":
            brand_freq[row["brand_name"]] += float(row["raw_count"])
print(f"  Brand frequencies loaded: {len(brand_freq)} brands")


# ──────────────────────────────────────────────────────────────────
# HELPER: Map trial choice letter back to brand name
# ──────────────────────────────────────────────────────────────────

def get_original_letter(row, display_letter):
    """Convert display letter to original product letter using letter_mapping."""
    # letter_mapping maps original -> display: e.g. {'E': 'A', 'B': 'B', ...}
    mapping_str = row.get("letter_mapping", "")
    if not mapping_str:
        return display_letter
    try:
        mapping = ast.literal_eval(mapping_str)
        # Invert: display -> original
        inv = {v: k for k, v in mapping.items()}
        return inv.get(display_letter, display_letter)
    except:
        return display_letter


def get_chosen_brand(row):
    """Get the brand name of the chosen product."""
    aid = row["assortment_id"]
    if aid not in ASSORT_PRODUCTS:
        return None
    # original_choice is the original product letter (pre-shuffle)
    orig = row.get("original_choice", "")
    if orig and orig in ASSORT_PRODUCTS[aid]:
        return ASSORT_PRODUCTS[aid][orig]["brand"]
    # Fallback: use choice + letter_mapping
    choice = row["choice"]
    orig_letter = get_original_letter(row, choice)
    if orig_letter in ASSORT_PRODUCTS[aid]:
        return ASSORT_PRODUCTS[aid][orig_letter]["brand"]
    return None


def get_optimal_brand(row):
    """Get the brand name of the optimal product."""
    aid = row["assortment_id"]
    if aid not in ASSORT_PRODUCTS:
        return None
    orig_opt = row.get("original_optimal", "")
    if orig_opt and orig_opt in ASSORT_PRODUCTS[aid]:
        return ASSORT_PRODUCTS[aid][orig_opt]["brand"]
    return None


def get_chosen_price(row):
    """Get the price of the chosen product."""
    aid = row["assortment_id"]
    if aid not in ASSORT_PRODUCTS:
        return None
    orig = row.get("original_choice", "")
    if orig and orig in ASSORT_PRODUCTS[aid]:
        return ASSORT_PRODUCTS[aid][orig]["price"]
    return None


def get_optimal_price(row):
    """Get the price of the optimal product."""
    aid = row["assortment_id"]
    if aid not in ASSORT_PRODUCTS:
        return None
    orig_opt = row.get("original_optimal", "")
    if orig_opt and orig_opt in ASSORT_PRODUCTS[aid]:
        return ASSORT_PRODUCTS[aid][orig_opt]["price"]
    return None


def get_chosen_utility(row):
    """Get the utility of the chosen product."""
    aid = row["assortment_id"]
    if aid not in ASSORT_UTILITIES:
        return None
    orig = row.get("original_choice", "")
    if orig and orig in ASSORT_UTILITIES[aid]:
        return ASSORT_UTILITIES[aid][orig]
    return None


def get_optimal_utility(row):
    """Get the utility of the optimal product."""
    aid = row["assortment_id"]
    if aid not in ASSORT_UTILITIES:
        return None
    orig_opt = row.get("original_optimal", "")
    if orig_opt and orig_opt in ASSORT_UTILITIES[aid]:
        return ASSORT_UTILITIES[aid][orig_opt]
    return None


# ══════════════════════════════════════════════════════════════════
# ANALYSIS 1: THE BRAND TAX
# ══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("ANALYSIS 1: THE BRAND TAX")
print("=" * 70)

# For every non-optimal baseline recommendation:
#   utility_loss = U(optimal) - U(chosen)
#   price_premium = price(chosen) - price(optimal)

non_optimal_trials = []
all_baseline_trials = []

for row in baseline_rows:
    chose_opt = row["chose_optimal"].strip().lower() == "true"
    aid = row["assortment_id"]

    chosen_price = get_chosen_price(row)
    optimal_price = get_optimal_price(row)
    chosen_util = get_chosen_utility(row)
    optimal_util = get_optimal_utility(row)
    chosen_brand = get_chosen_brand(row)

    if any(v is None for v in [chosen_price, optimal_price, chosen_util, optimal_util]):
        continue

    trial_data = {
        "trial_id": row["trial_id"],
        "model_key": row["model_key"],
        "assortment_id": aid,
        "category": row["category"],
        "chose_optimal": chose_opt,
        "chosen_brand": chosen_brand,
        "chosen_price": chosen_price,
        "optimal_price": optimal_price,
        "price_premium": chosen_price - optimal_price,
        "chosen_utility": chosen_util,
        "optimal_utility": optimal_util,
        "utility_loss": optimal_util - chosen_util,
        "chosen_fam": row.get("chosen_brand_familiarity", ""),
        "judge_brand_reasoning": row.get("judge_brand_reasoning", "").strip().lower() == "true",
    }
    all_baseline_trials.append(trial_data)
    if not chose_opt:
        non_optimal_trials.append(trial_data)

total_baseline = len(all_baseline_trials)
total_non_optimal = len(non_optimal_trials)
non_optimal_rate = total_non_optimal / total_baseline if total_baseline > 0 else 0

print(f"\nBaseline trials (with valid product data): {total_baseline:,}")
print(f"Non-optimal recommendations: {total_non_optimal:,} ({non_optimal_rate:.1%})")

# Price premium statistics
premiums = [t["price_premium"] for t in non_optimal_trials]
more_expensive = [p for p in premiums if p > 0]
less_expensive = [p for p in premiums if p < 0]
same_price = [p for p in premiums if p == 0]

mean_premium = sum(premiums) / len(premiums) if premiums else 0
sorted_premiums = sorted(premiums)
median_premium = sorted_premiums[len(sorted_premiums) // 2] if sorted_premiums else 0

print(f"\n--- Price Premium (non-optimal only) ---")
print(f"  More expensive than optimal: {len(more_expensive)} ({len(more_expensive)/len(premiums):.1%})")
print(f"  Less expensive than optimal: {len(less_expensive)} ({len(less_expensive)/len(premiums):.1%})")
print(f"  Same price: {len(same_price)} ({len(same_price)/len(premiums):.1%})")
print(f"  Mean price premium: ${mean_premium:.2f}")
print(f"  Median price premium: ${median_premium:.2f}")

# Only count positive premiums for "overpayment" stat
mean_overpayment = sum(more_expensive) / len(more_expensive) if more_expensive else 0
sorted_overpay = sorted(more_expensive)
median_overpayment = sorted_overpay[len(sorted_overpay) // 2] if sorted_overpay else 0
print(f"  Mean overpayment (when more expensive): ${mean_overpayment:.2f}")
print(f"  Median overpayment (when more expensive): ${median_overpayment:.2f}")
print(f"  Max overpayment: ${max(premiums):.2f}")
print(f"  Min premium (max savings when cheaper): ${min(premiums):.2f}")

# Utility loss statistics
losses = [t["utility_loss"] for t in non_optimal_trials]
mean_util_loss = sum(losses) / len(losses) if losses else 0
sorted_losses = sorted(losses)
median_util_loss = sorted_losses[len(sorted_losses) // 2] if sorted_losses else 0
print(f"\n--- Utility Loss (non-optimal only) ---")
print(f"  Mean utility loss: {mean_util_loss:.4f}")
print(f"  Median utility loss: {median_util_loss:.4f}")
print(f"  Max utility loss: {max(losses):.4f}")

# Bootstrap 95% CI for mean premium and mean utility loss
import random as rng
rng.seed(42)
N_BOOT = 10000

def bootstrap_ci(data, n_boot=N_BOOT, alpha=0.05):
    """Compute bootstrap percentile CI for the mean."""
    n = len(data)
    means = []
    for _ in range(n_boot):
        sample = [data[rng.randint(0, n - 1)] for _ in range(n)]
        means.append(sum(sample) / n)
    means.sort()
    lo = means[int(n_boot * alpha / 2)]
    hi = means[int(n_boot * (1 - alpha / 2))]
    return lo, hi

ci_premium = bootstrap_ci(premiums)
ci_overpay = bootstrap_ci(more_expensive)
ci_util = bootstrap_ci(losses)
ci_rate = bootstrap_ci([1 if not t["chose_optimal"] else 0 for t in all_baseline_trials])

print(f"\n--- Bootstrap 95% CIs (10,000 replicates) ---")
print(f"  Non-optimal rate: {non_optimal_rate:.3f} [{ci_rate[0]:.3f}, {ci_rate[1]:.3f}]")
print(f"  Mean price premium: ${mean_premium:.2f} [${ci_premium[0]:.2f}, ${ci_premium[1]:.2f}]")
print(f"  Mean overpayment (when more expensive): ${mean_overpayment:.2f} [${ci_overpay[0]:.2f}, ${ci_overpay[1]:.2f}]")
print(f"  Mean utility loss: {mean_util_loss:.4f} [{ci_util[0]:.4f}, {ci_util[1]:.4f}]")

# By category
print(f"\n--- Price Premium by Category ---")
cat_premiums = defaultdict(list)
for t in non_optimal_trials:
    cat_premiums[t["category"]].append(t["price_premium"])

cat_stats = []
for cat in sorted(cat_premiums.keys()):
    vals = cat_premiums[cat]
    m = sum(vals) / len(vals)
    n_more = sum(1 for v in vals if v > 0)
    cat_stats.append((cat, len(vals), m, n_more / len(vals)))
    print(f"  {cat:30s}  n={len(vals):4d}  mean=${m:>8.2f}  more_expensive={n_more/len(vals):.1%}")

# ── Scale-up: The Brand Tax on AI Commerce ──
print(f"\n{'=' * 70}")
print("THE BRAND TAX — SCALE-UP PROJECTIONS")
print("=" * 70)

# Key inputs
chatgpt_weekly_users = 900_000_000  # OpenAI 2026
amazon_rufus_users = 300_000_000
us_shopper_ai_pct = 0.35
non_optimal_rate_val = non_optimal_rate
mean_premium_val = mean_premium  # including negative premiums — net cost
mean_overpay_val = mean_overpayment  # only positive premiums

# Conservative: use net premium (including cases where AI recommends cheaper but worse)
# Aggressive: use overpayment only (when AI steers to more expensive non-optimal)
# Probability of being more expensive given non-optimal
pct_more_expensive = len(more_expensive) / len(premiums) if premiums else 0

print(f"\nKey parameters:")
print(f"  Non-optimal rate (baseline): {non_optimal_rate_val:.3f} ({non_optimal_rate_val:.1%})")
print(f"  Pct of non-optimal that are more expensive: {pct_more_expensive:.1%}")
print(f"  Mean net premium (all non-optimal): ${mean_premium_val:.2f}")
print(f"  Mean overpayment (more expensive only): ${mean_overpay_val:.2f}")

# Morgan Stanley projection: $190-385B in AI-mediated commerce by 2030
ms_low = 190_000_000_000
ms_high = 385_000_000_000

# If X% of commerce decisions are misaligned, and each costs Y% more...
# Average price in our assortments
all_prices = []
for aid, prods in ASSORT_PRODUCTS.items():
    for p in prods.values():
        all_prices.append(p["price"])
avg_product_price = sum(all_prices) / len(all_prices)
avg_optimal_price = sum(get_optimal_price(t) for t in [{"assortment_id": aid, "original_optimal": ASSORT_OPTIMAL_LETTER[aid]} for aid in ASSORT_OPTIMAL_LETTER]) / len(ASSORT_OPTIMAL_LETTER)

# Relative premium — use CHOSEN price as denominator (what consumers actually pay)
# BUG FIX: previously used optimal_price, which inflated by up to 37%
avg_chosen_price_nonopt = sum(t["chosen_price"] for t in non_optimal_trials if t["chosen_price"] > t["optimal_price"]) / max(len([t for t in non_optimal_trials if t["chosen_price"] > t["optimal_price"]]), 1)
relative_premium = mean_overpay_val / avg_chosen_price_nonopt if avg_chosen_price_nonopt > 0 else 0

print(f"\n  Average product price in assortments: ${avg_product_price:.2f}")
print(f"  Average optimal product price: ${avg_optimal_price:.2f}")
print(f"  Average chosen price (non-optimal, overpaying): ${avg_chosen_price_nonopt:.2f}")
print(f"  Relative overpayment (mean overpay / avg chosen price): {relative_premium:.1%}")
print(f"  [OLD BUG: was using optimal price denominator, inflating by ~37%]")

# PROJECTED COSTS
# Method 1: Direct scaling using observed premium and Morgan Stanley projections
# Misaligned fraction of commerce = non_optimal_rate
# Cost = commerce_volume * misaligned_fraction * relative_premium_pct
welfare_cost_low = ms_low * non_optimal_rate_val * relative_premium * pct_more_expensive
welfare_cost_high = ms_high * non_optimal_rate_val * relative_premium * pct_more_expensive

print(f"\n--- Morgan Stanley AI Commerce Projections (2030) ---")
print(f"  Projected AI-mediated commerce: ${ms_low/1e9:.0f}B - ${ms_high/1e9:.0f}B")
print(f"  At {non_optimal_rate_val:.1%} misalignment rate:")
print(f"    Misaligned commerce volume: ${ms_low * non_optimal_rate_val / 1e9:.1f}B - ${ms_high * non_optimal_rate_val / 1e9:.1f}B")
print(f"  At {pct_more_expensive:.1%} probability of overpayment when misaligned:")
print(f"  At {relative_premium:.1%} relative overpayment:")
print(f"    Projected annual Brand Tax: ${welfare_cost_low / 1e9:.1f}B - ${welfare_cost_high / 1e9:.1f}B")

# Method 2: Per-user calculation
# If a user makes ~1 AI-assisted purchase per month (conservative)
purchases_per_year = 12
# Probability of non-optimal * probability of overpayment * mean overpayment
per_user_annual_cost = purchases_per_year * non_optimal_rate_val * pct_more_expensive * mean_overpay_val
n_ai_shoppers_us = 170_000_000 * us_shopper_ai_pct  # ~170M US online shoppers
us_annual_brand_tax = n_ai_shoppers_us * per_user_annual_cost

print(f"\n--- Per-User Brand Tax ---")
print(f"  Assumptions: {purchases_per_year} AI-assisted purchases/year, ${mean_overpay_val:.2f} mean overpayment")
print(f"  Per-user annual Brand Tax: ${per_user_annual_cost:.2f}")
print(f"  US AI shoppers (~35% of 170M online shoppers): {n_ai_shoppers_us/1e6:.0f}M")
print(f"  US annual Brand Tax: ${us_annual_brand_tax/1e9:.1f}B")


# ══════════════════════════════════════════════════════════════════
# ANALYSIS 2: HHI MARKET CONCENTRATION
# ══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("ANALYSIS 2: HHI MARKET CONCENTRATION")
print("=" * 70)

# For each category, count how often each brand is recommended across ALL baseline trials
cat_brand_counts = defaultdict(lambda: Counter())
cat_total_trials = Counter()

for row in baseline_rows:
    brand = get_chosen_brand(row)
    cat = row["category"]
    if brand:
        cat_brand_counts[cat][brand] += 1
        cat_total_trials[cat] += 1

# Also count recommendations across ALL conditions (not just baseline)
cat_brand_counts_all = defaultdict(lambda: Counter())
cat_total_trials_all = Counter()

for row in rows:
    brand = get_chosen_brand(row)
    cat = row["category"]
    if brand:
        cat_brand_counts_all[cat][brand] += 1
        cat_total_trials_all[cat] += 1


def compute_hhi(brand_counts, total):
    """Compute Herfindahl-Hirschman Index. 0 = perfect competition, 10000 = monopoly."""
    if total == 0:
        return 0
    hhi = 0
    for brand, count in brand_counts.items():
        share = count / total
        hhi += (share * 100) ** 2  # HHI uses percentage shares
    return hhi


print(f"\n{'Category':<30s} {'N':>6s} {'#Brands':>7s} {'Top Brand':>20s} {'Top%':>6s} {'HHI_AI':>8s} {'HHI_eq':>8s} {'Ratio':>6s} {'Concentration':>15s}")
print("-" * 115)

hhi_results = []
for cat in sorted(cat_brand_counts.keys()):
    counts = cat_brand_counts[cat]
    total = cat_total_trials[cat]
    n_brands = len(counts)

    # AI recommendation HHI
    hhi_ai = compute_hhi(counts, total)

    # Equal distribution HHI (if each of N products in assortment got equal share)
    # N products per assortment = 5
    hhi_equal = 5 * (100 / 5) ** 2  # = 5 * 400 = 2000

    # Top brand
    top_brand = counts.most_common(1)[0] if counts else ("?", 0)
    top_pct = top_brand[1] / total if total > 0 else 0

    ratio = hhi_ai / hhi_equal if hhi_equal > 0 else 0
    conc = "Highly Concentrated" if hhi_ai > 2500 else ("Moderately Conc." if hhi_ai > 1500 else "Competitive")

    print(f"  {cat:<28s} {total:>6d} {n_brands:>7d} {top_brand[0]:>20s} {top_pct:>5.1%} {hhi_ai:>8.0f} {hhi_equal:>8.0f} {ratio:>5.1f}x {conc:>15s}")

    hhi_results.append({
        "category": cat,
        "n_trials": total,
        "n_brands_recommended": n_brands,
        "top_brand": top_brand[0],
        "top_brand_share": top_pct,
        "hhi_ai": hhi_ai,
        "hhi_equal": hhi_equal,
        "hhi_ratio": ratio,
        "concentration": conc,
        "brand_shares": {b: c / total for b, c in counts.most_common()},
    })

# Summary
mean_hhi = sum(r["hhi_ai"] for r in hhi_results) / len(hhi_results)
mean_ratio = sum(r["hhi_ratio"] for r in hhi_results) / len(hhi_results)
n_concentrated = sum(1 for r in hhi_results if r["hhi_ai"] > 2500)
print(f"\n--- Summary ---")
print(f"  Mean HHI across categories: {mean_hhi:.0f}")
print(f"  HHI under equal distribution: 2000")
print(f"  Mean concentration ratio (HHI_AI / HHI_equal): {mean_ratio:.2f}x")
print(f"  Categories with HHI > 2500 (highly concentrated): {n_concentrated}/{len(hhi_results)}")

# DOJ/FTC thresholds
print(f"\n  DOJ/FTC HHI thresholds:")
print(f"    < 1500: Competitive market")
print(f"    1500-2500: Moderately concentrated")
print(f"    > 2500: Highly concentrated")
print(f"  AI recommendations average {mean_hhi:.0f}, which is {'above' if mean_hhi > 2500 else 'near'} the 'highly concentrated' threshold")


# ══════════════════════════════════════════════════════════════════
# ANALYSIS 3: COMPREHENSIVE BRAND PROFILE TABLE
# ══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("ANALYSIS 3: COMPREHENSIVE BRAND PROFILE TABLE")
print("=" * 70)

# For each brand across all assortments:
# - Brand name, category, familiarity tier
# - Training corpus frequency (from brand_frequencies.csv)
# - Non-optimal selection rate (how often models choose this brand when it's NOT optimal)
# - Confabulation rate (judge_brand_reasoning when non-optimal)
# - Number of models that select this brand (convergence)
# - Mean utility loss when chosen
# - Price premium when chosen

# First, build a brand-to-assortment mapping
brand_info = {}  # brand -> {category, familiarity, assortments}
for aid, prods in ASSORT_PRODUCTS.items():
    cat = aid.split("_")[1]
    # Reconstruct category from assortment id
    for a in ALL_ASSORTMENTS:
        if a["id"] == aid:
            cat = a["category"]
            break
    for letter, p in prods.items():
        brand = p["brand"]
        if brand not in brand_info:
            brand_info[brand] = {
                "categories": set(),
                "familiarity": p.get("brand_familiarity", "unknown"),
                "assortments": set(),
                "is_optimal_in": set(),
            }
        brand_info[brand]["categories"].add(cat)
        brand_info[brand]["assortments"].add(aid)
        if p.get("is_optimal", False):
            brand_info[brand]["is_optimal_in"].add(aid)

# Now compute per-brand statistics from ALL trials (not just baseline)
brand_stats = defaultdict(lambda: {
    "total_chosen": 0,
    "chosen_when_not_optimal": 0,  # brand chosen but it's not the optimal product
    "chosen_when_optimal": 0,      # brand chosen and it IS optimal
    "confab_when_not_optimal": 0,
    "models_selecting": set(),
    "utility_losses": [],
    "price_premiums": [],
    "total_appearances": 0,  # how many trials this brand appeared in
})

# Count all trials (baseline only for the "non-optimal selection" stat —
# this is the most policy-relevant condition)
for row in baseline_rows:
    aid = row["assortment_id"]
    if aid not in ASSORT_PRODUCTS:
        continue
    chosen_brand = get_chosen_brand(row)
    if not chosen_brand:
        continue

    chose_opt = row["chose_optimal"].strip().lower() == "true"
    model = row["model_key"]
    confab = row.get("judge_brand_reasoning", "").strip().lower() == "true"

    bs = brand_stats[chosen_brand]
    bs["total_chosen"] += 1
    bs["models_selecting"].add(model)

    if chose_opt:
        bs["chosen_when_optimal"] += 1
    else:
        bs["chosen_when_not_optimal"] += 1
        if confab:
            bs["confab_when_not_optimal"] += 1

        u_loss = get_optimal_utility(row)
        c_util = get_chosen_utility(row)
        if u_loss is not None and c_util is not None:
            bs["utility_losses"].append(u_loss - c_util)

        c_price = get_chosen_price(row)
        o_price = get_optimal_price(row)
        if c_price is not None and o_price is not None:
            bs["price_premiums"].append(c_price - o_price)

# Count how many trials each brand APPEARS in (denominator for selection rate)
for row in baseline_rows:
    aid = row["assortment_id"]
    if aid not in ASSORT_PRODUCTS:
        continue
    for letter, p in ASSORT_PRODUCTS[aid].items():
        brand_stats[p["brand"]]["total_appearances"] += 1

# Build the table
brand_table = []
for brand in brand_info:
    bs = brand_stats[brand]
    bi = brand_info[brand]

    freq = brand_freq.get(brand, 0)
    cats = sorted(bi["categories"])
    fam = bi["familiarity"]
    is_optimal = len(bi["is_optimal_in"]) > 0

    non_opt_chosen = bs["chosen_when_not_optimal"]
    total_appearances = bs["total_appearances"]
    # "Non-optimal selection rate" = times chosen when NOT optimal / times it appeared and was NOT optimal
    # Need to know how many times brand appeared as NON-optimal
    non_opt_appearances = 0
    for aid in bi["assortments"]:
        if aid not in bi["is_optimal_in"]:
            # Count baseline trials for this assortment
            non_opt_appearances += sum(1 for r in baseline_rows if r["assortment_id"] == aid)

    non_opt_rate = non_opt_chosen / non_opt_appearances if non_opt_appearances > 0 else 0
    confab_rate = bs["confab_when_not_optimal"] / non_opt_chosen if non_opt_chosen > 0 else 0
    n_models = len(bs["models_selecting"])
    mean_u_loss = sum(bs["utility_losses"]) / len(bs["utility_losses"]) if bs["utility_losses"] else 0
    mean_p_prem = sum(bs["price_premiums"]) / len(bs["price_premiums"]) if bs["price_premiums"] else 0

    brand_table.append({
        "brand": brand,
        "category": ", ".join(cats),
        "familiarity": fam,
        "is_optimal": is_optimal,
        "corpus_frequency": int(freq),
        "non_optimal_selections": non_opt_chosen,
        "non_optimal_appearances": non_opt_appearances,
        "non_optimal_selection_rate": non_opt_rate,
        "confabulation_rate": confab_rate,
        "n_models_selecting": n_models,
        "mean_utility_loss": mean_u_loss,
        "mean_price_premium": mean_p_prem,
        "total_chosen_baseline": bs["total_chosen"],
    })

# Sort by non-optimal selection rate (descending)
brand_table.sort(key=lambda x: (-x["non_optimal_selection_rate"], -x["non_optimal_selections"]))

print(f"\nTotal brands in assortments: {len(brand_table)}")
print(f"Brands with non-optimal selections: {sum(1 for b in brand_table if b['non_optimal_selections'] > 0)}")

# Print top 30
print(f"\n{'Brand':<25s} {'Cat':<20s} {'Fam':<6s} {'Opt?':<5s} {'Corpus':>12s} {'NonOpt':>6s} {'Rate':>7s} {'Confab':>7s} {'#Mod':>5s} {'ULoss':>7s} {'$Prem':>8s}")
print("-" * 120)
for b in brand_table[:40]:
    print(f"  {b['brand']:<23s} {b['category'][:18]:<20s} {b['familiarity']:<6s} {'Y' if b['is_optimal'] else 'N':<5s} {b['corpus_frequency']:>12,d} {b['non_optimal_selections']:>6d} {b['non_optimal_selection_rate']:>6.1%} {b['confabulation_rate']:>6.1%} {b['n_models_selecting']:>5d} {b['mean_utility_loss']:>6.4f} ${b['mean_price_premium']:>7.2f}")


# ══════════════════════════════════════════════════════════════════
# SAVE OUTPUTS
# ══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("SAVING OUTPUTS")
print("=" * 70)

# 1. Brand Tax CSV
tax_csv = OUT / "brand_tax_by_category.csv"
with open(tax_csv, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["category", "n_non_optimal", "mean_price_premium", "median_price_premium",
                "pct_more_expensive", "mean_overpayment_when_more_expensive",
                "mean_utility_loss"])
    for cat in sorted(cat_premiums.keys()):
        vals = cat_premiums[cat]
        m = sum(vals) / len(vals)
        s = sorted(vals)
        med = s[len(s) // 2]
        more_exp = [v for v in vals if v > 0]
        pct_more = len(more_exp) / len(vals)
        mean_ovp = sum(more_exp) / len(more_exp) if more_exp else 0
        u_losses = [t["utility_loss"] for t in non_optimal_trials if t["category"] == cat]
        mean_ul = sum(u_losses) / len(u_losses) if u_losses else 0
        w.writerow([cat, len(vals), f"{m:.2f}", f"{med:.2f}", f"{pct_more:.3f}", f"{mean_ovp:.2f}", f"{mean_ul:.4f}"])
print(f"  Saved: {tax_csv}")

# 2. HHI CSV
hhi_csv = OUT / "hhi_market_concentration.csv"
with open(hhi_csv, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["category", "n_trials", "n_brands_recommended", "top_brand", "top_brand_share",
                "hhi_ai", "hhi_equal", "hhi_ratio", "concentration_level"])
    for r in sorted(hhi_results, key=lambda x: -x["hhi_ai"]):
        w.writerow([r["category"], r["n_trials"], r["n_brands_recommended"],
                    r["top_brand"], f"{r['top_brand_share']:.3f}",
                    f"{r['hhi_ai']:.0f}", f"{r['hhi_equal']:.0f}",
                    f"{r['hhi_ratio']:.2f}", r["concentration"]])
print(f"  Saved: {hhi_csv}")

# 3. Brand Profile CSV (Supplementary Table 1)
brand_csv = OUT / "supplementary_table1_brand_profiles.csv"
with open(brand_csv, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["brand", "category", "familiarity_tier", "is_optimal_brand",
                "corpus_frequency", "non_optimal_selections", "non_optimal_appearances",
                "non_optimal_selection_rate", "confabulation_rate",
                "n_models_selecting", "mean_utility_loss", "mean_price_premium",
                "total_chosen_baseline"])
    for b in brand_table:
        w.writerow([b["brand"], b["category"], b["familiarity"],
                    b["is_optimal"], b["corpus_frequency"],
                    b["non_optimal_selections"], b["non_optimal_appearances"],
                    f"{b['non_optimal_selection_rate']:.4f}",
                    f"{b['confabulation_rate']:.4f}",
                    b["n_models_selecting"],
                    f"{b['mean_utility_loss']:.4f}",
                    f"{b['mean_price_premium']:.2f}",
                    b["total_chosen_baseline"]])
print(f"  Saved: {brand_csv}")

# 4. Summary JSON with all key numbers
summary = {
    "brand_tax": {
        "total_baseline_trials": total_baseline,
        "non_optimal_count": total_non_optimal,
        "non_optimal_rate": round(non_optimal_rate, 4),
        "non_optimal_rate_ci95": [round(ci_rate[0], 4), round(ci_rate[1], 4)],
        "pct_more_expensive": round(pct_more_expensive, 4),
        "mean_price_premium_all_nonoptimal": round(mean_premium, 2),
        "mean_price_premium_ci95": [round(ci_premium[0], 2), round(ci_premium[1], 2)],
        "median_price_premium": round(median_premium, 2),
        "mean_overpayment_when_more_expensive": round(mean_overpayment, 2),
        "mean_overpayment_ci95": [round(ci_overpay[0], 2), round(ci_overpay[1], 2)],
        "median_overpayment_when_more_expensive": round(median_overpayment, 2),
        "mean_utility_loss": round(mean_util_loss, 4),
        "mean_utility_loss_ci95": [round(ci_util[0], 4), round(ci_util[1], 4)],
        "relative_overpayment_pct": round(relative_premium, 4),
        "projections": {
            "morgan_stanley_low_B": ms_low / 1e9,
            "morgan_stanley_high_B": ms_high / 1e9,
            "annual_brand_tax_low_B": round(welfare_cost_low / 1e9, 1),
            "annual_brand_tax_high_B": round(welfare_cost_high / 1e9, 1),
            "per_user_annual_cost": round(per_user_annual_cost, 2),
            "us_annual_brand_tax_B": round(us_annual_brand_tax / 1e9, 1),
        },
    },
    "hhi_concentration": {
        "mean_hhi_ai": round(mean_hhi, 0),
        "hhi_equal_distribution": 2000,
        "mean_concentration_ratio": round(mean_ratio, 2),
        "n_highly_concentrated": n_concentrated,
        "n_categories": len(hhi_results),
    },
    "brand_profiles": {
        "total_brands": len(brand_table),
        "brands_with_nonoptimal_selections": sum(1 for b in brand_table if b["non_optimal_selections"] > 0),
        "top_5_non_optimal": [
            {"brand": b["brand"], "rate": round(b["non_optimal_selection_rate"], 4),
             "n": b["non_optimal_selections"]}
            for b in brand_table[:5] if b["non_optimal_selections"] > 0
        ],
    },
}
summary_path = OUT / "consequences_summary.json"
with open(summary_path, "w", encoding="utf-8") as f:
    json.dump(summary, f, indent=2)
print(f"  Saved: {summary_path}")


# ══════════════════════════════════════════════════════════════════
# GENERATE FIGURES
# ══════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("GENERATING FIGURES")
print("=" * 70)

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.ticker as mticker
    import numpy as np

    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
        "font.size": 10,
        "axes.labelsize": 11,
        "axes.titlesize": 12,
        "figure.dpi": 300,
    })

    # ── Figure 1: Brand Tax — Price Premium Distribution ──
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    # Panel a: Histogram of price premiums
    ax = axes[0]
    premiums_arr = np.array(premiums)
    bins = np.arange(-400, 600, 25)
    ax.hist(premiums_arr, bins=bins, color="#2166ac", edgecolor="white", linewidth=0.5, alpha=0.85)
    ax.axvline(0, color="black", linestyle="--", linewidth=1, alpha=0.5)
    ax.axvline(mean_premium, color="#d62728", linestyle="-", linewidth=2,
               label=f"Mean: ${mean_premium:.0f}")
    ax.axvline(median_premium, color="#ff7f0e", linestyle="--", linewidth=2,
               label=f"Median: ${median_premium:.0f}")
    ax.set_xlabel("Price premium over optimal ($)")
    ax.set_ylabel("Number of non-optimal trials")
    ax.set_title("a  Distribution of price premiums", loc="left", fontweight="bold")
    ax.legend(frameon=False, fontsize=9)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # Panel b: By category
    ax = axes[1]
    cats_sorted = sorted(cat_premiums.keys(), key=lambda c: sum(cat_premiums[c]) / len(cat_premiums[c]))
    cat_means = [sum(cat_premiums[c]) / len(cat_premiums[c]) for c in cats_sorted]
    cat_labels = [c.replace("_", " ").title() for c in cats_sorted]
    colors = ["#d62728" if m > 0 else "#2166ac" for m in cat_means]
    ax.barh(range(len(cats_sorted)), cat_means, color=colors, edgecolor="white", linewidth=0.5)
    ax.set_yticks(range(len(cats_sorted)))
    ax.set_yticklabels(cat_labels, fontsize=8)
    ax.axvline(0, color="black", linestyle="-", linewidth=0.5)
    ax.set_xlabel("Mean price premium over optimal ($)")
    ax.set_title("b  Price premium by category", loc="left", fontweight="bold")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    plt.tight_layout()
    for ext in ["png", "pdf"]:
        fig.savefig(OUT / f"fig_brand_tax.{ext}", dpi=300, bbox_inches="tight")
    plt.close()
    print("  Saved: fig_brand_tax.png/pdf")

    # ── Figure 2: HHI Market Concentration ──
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.5))

    # Panel a: HHI by category
    ax = axes[0]
    hhi_sorted = sorted(hhi_results, key=lambda x: x["hhi_ai"])
    cat_labels_hhi = [r["category"].replace("_", " ").title() for r in hhi_sorted]
    hhi_vals = [r["hhi_ai"] for r in hhi_sorted]
    bar_colors = ["#d62728" if h > 2500 else ("#ff7f0e" if h > 1500 else "#2166ac") for h in hhi_vals]
    bars = ax.barh(range(len(hhi_sorted)), hhi_vals, color=bar_colors, edgecolor="white", linewidth=0.5)
    ax.axvline(2000, color="gray", linestyle="--", linewidth=1, alpha=0.7, label="Equal distribution (2000)")
    ax.axvline(2500, color="#d62728", linestyle=":", linewidth=1, alpha=0.7, label="DOJ threshold (2500)")
    ax.set_yticks(range(len(hhi_sorted)))
    ax.set_yticklabels(cat_labels_hhi, fontsize=8)
    ax.set_xlabel("Herfindahl-Hirschman Index (HHI)")
    ax.set_title("a  AI recommendation concentration by category", loc="left", fontweight="bold")
    ax.legend(frameon=False, fontsize=8, loc="lower right")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # Panel b: Top brand share by category
    ax = axes[1]
    top_shares = [r["top_brand_share"] for r in hhi_sorted]
    top_names = [r["top_brand"] for r in hhi_sorted]
    bars2 = ax.barh(range(len(hhi_sorted)), [s * 100 for s in top_shares],
                    color=bar_colors, edgecolor="white", linewidth=0.5)
    ax.axvline(20, color="gray", linestyle="--", linewidth=1, alpha=0.7, label="Equal share (20%)")
    for i, (share, name) in enumerate(zip(top_shares, top_names)):
        ax.text(share * 100 + 1, i, name, va="center", fontsize=7, alpha=0.8)
    ax.set_yticks(range(len(hhi_sorted)))
    ax.set_yticklabels(cat_labels_hhi, fontsize=8)
    ax.set_xlabel("Top brand recommendation share (%)")
    ax.set_title("b  Market share of most-recommended brand", loc="left", fontweight="bold")
    ax.legend(frameon=False, fontsize=8, loc="lower right")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    plt.tight_layout()
    for ext in ["png", "pdf"]:
        fig.savefig(OUT / f"fig_hhi_concentration.{ext}", dpi=300, bbox_inches="tight")
    plt.close()
    print("  Saved: fig_hhi_concentration.png/pdf")

    # ── Figure 3: Brand Profile — Top brands by non-optimal selection ──
    fig, axes = plt.subplots(1, 2, figsize=(13, 6))

    # Filter to non-optimal brands with enough data
    non_opt_brands = [b for b in brand_table
                      if b["non_optimal_selections"] >= 10 and not b["is_optimal"]]
    top_n = min(25, len(non_opt_brands))
    top_brands = non_opt_brands[:top_n]

    # Panel a: Non-optimal selection rate
    ax = axes[0]
    b_names = [b["brand"] for b in reversed(top_brands)]
    b_rates = [b["non_optimal_selection_rate"] * 100 for b in reversed(top_brands)]
    b_fam = [b["familiarity"] for b in reversed(top_brands)]
    fam_colors = {"high": "#d62728", "medium": "#ff7f0e", "low": "#2166ac"}
    colors_fam = [fam_colors.get(f, "#999999") for f in b_fam]
    ax.barh(range(len(b_names)), b_rates, color=colors_fam, edgecolor="white", linewidth=0.5)
    ax.set_yticks(range(len(b_names)))
    ax.set_yticklabels(b_names, fontsize=8)
    ax.set_xlabel("Non-optimal selection rate (%)")
    ax.set_title("a  Brands most often chosen despite being suboptimal", loc="left", fontweight="bold")
    # Legend for familiarity
    from matplotlib.patches import Patch
    legend_elements = [Patch(facecolor="#d62728", label="High familiarity"),
                       Patch(facecolor="#ff7f0e", label="Medium familiarity"),
                       Patch(facecolor="#2166ac", label="Low familiarity")]
    ax.legend(handles=legend_elements, frameon=False, fontsize=8, loc="lower right")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # Panel b: Corpus frequency vs non-optimal selection rate (scatter)
    ax = axes[1]
    scatter_brands = [b for b in brand_table if b["non_optimal_selections"] >= 5
                      and b["corpus_frequency"] > 0 and not b["is_optimal"]]
    freqs = [math.log10(b["corpus_frequency"] + 1) for b in scatter_brands]
    rates = [b["non_optimal_selection_rate"] * 100 for b in scatter_brands]
    fams = [b["familiarity"] for b in scatter_brands]
    sc_colors = [fam_colors.get(f, "#999999") for f in fams]
    ax.scatter(freqs, rates, c=sc_colors, s=50, alpha=0.7, edgecolors="white", linewidth=0.5)
    # Label top brands
    for b in scatter_brands:
        if b["non_optimal_selection_rate"] > 0.05 or b["corpus_frequency"] > 5_000_000:
            ax.annotate(b["brand"],
                       (math.log10(b["corpus_frequency"] + 1), b["non_optimal_selection_rate"] * 100),
                       fontsize=6, alpha=0.8, textcoords="offset points", xytext=(5, 3))
    ax.set_xlabel("Training corpus frequency (log10)")
    ax.set_ylabel("Non-optimal selection rate (%)")
    ax.set_title("b  Corpus frequency predicts misalignment", loc="left", fontweight="bold")
    ax.legend(handles=legend_elements, frameon=False, fontsize=8, loc="upper left")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    plt.tight_layout()
    for ext in ["png", "pdf"]:
        fig.savefig(OUT / f"fig_brand_profiles.{ext}", dpi=300, bbox_inches="tight")
    plt.close()
    print("  Saved: fig_brand_profiles.png/pdf")

    # ── Figure 4: Combined "Brand Tax" headline figure ──
    fig, ax = plt.subplots(figsize=(8, 5))

    # Stacked view: utility loss decomposition
    # Show: for each non-optimal trial, how much of the cost is "pure brand premium"
    # vs "different product entirely"
    # Simple: histogram of utility losses colored by whether more/less expensive
    losses_arr = np.array(losses)
    premiums_arr_nonopt = np.array(premiums)
    more_expensive_mask = premiums_arr_nonopt > 0

    ax.hist([losses_arr[more_expensive_mask], losses_arr[~more_expensive_mask]],
            bins=30, stacked=True, color=["#d62728", "#2166ac"],
            label=[f"More expensive ({more_expensive_mask.sum():,} trials, {more_expensive_mask.mean():.0%})",
                   f"Less expensive ({(~more_expensive_mask).sum():,} trials, {(~more_expensive_mask).mean():.0%})"],
            edgecolor="white", linewidth=0.5)
    ax.axvline(mean_util_loss, color="black", linestyle="--", linewidth=1.5,
               label=f"Mean utility loss: {mean_util_loss:.3f}")
    ax.set_xlabel("Utility loss (optimal utility minus chosen utility)")
    ax.set_ylabel("Number of non-optimal trials")
    ax.set_title("The Brand Tax: utility cost of AI misalignment\n"
                 f"({total_non_optimal:,} non-optimal recommendations at baseline, "
                 f"mean overpayment ${mean_overpayment:.0f})",
                 fontweight="bold", fontsize=11)
    ax.legend(frameon=False, fontsize=9)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    plt.tight_layout()
    for ext in ["png", "pdf"]:
        fig.savefig(OUT / f"fig_brand_tax_headline.{ext}", dpi=300, bbox_inches="tight")
    plt.close()
    print("  Saved: fig_brand_tax_headline.png/pdf")

except ImportError as e:
    print(f"  Could not generate figures: {e}")
    print("  Install matplotlib: pip install matplotlib")


# ══════════════════════════════════════════════════════════════════
# FORMATTED SUMMARY REPORT
# ══════════════════════════════════════════════════════════════════

report_lines = []
report_lines.append("=" * 70)
report_lines.append("CONSEQUENCES ANALYSIS — EXECUTIVE SUMMARY")
report_lines.append("=" * 70)
report_lines.append("")
report_lines.append("1. THE BRAND TAX")
report_lines.append("-" * 40)
report_lines.append(f"Non-optimal rate at baseline: {non_optimal_rate:.1%} "
                    f"(95% CI: [{ci_rate[0]:.1%}, {ci_rate[1]:.1%}])")
report_lines.append(f"Total non-optimal baseline recommendations: {total_non_optimal:,} / {total_baseline:,}")
report_lines.append(f"")
report_lines.append(f"Of non-optimal recommendations:")
report_lines.append(f"  {pct_more_expensive:.1%} recommend a MORE EXPENSIVE product")
report_lines.append(f"  Mean price premium (all non-optimal): ${mean_premium:.2f} "
                    f"(95% CI: [${ci_premium[0]:.2f}, ${ci_premium[1]:.2f}])")
report_lines.append(f"  Mean overpayment (when more expensive): ${mean_overpayment:.2f} "
                    f"(95% CI: [${ci_overpay[0]:.2f}, ${ci_overpay[1]:.2f}])")
report_lines.append(f"  Mean utility loss: {mean_util_loss:.4f} "
                    f"(95% CI: [{ci_util[0]:.4f}, {ci_util[1]:.4f}])")
report_lines.append(f"")
report_lines.append(f"SCALE-UP PROJECTIONS:")
report_lines.append(f"  Morgan Stanley 2030 AI commerce: ${ms_low/1e9:.0f}B-${ms_high/1e9:.0f}B")
report_lines.append(f"  Projected annual Brand Tax: ${welfare_cost_low/1e9:.1f}B-${welfare_cost_high/1e9:.1f}B")
report_lines.append(f"  Per-user annual cost (12 purchases): ${per_user_annual_cost:.2f}")
report_lines.append(f"  US annual aggregate ({n_ai_shoppers_us/1e6:.0f}M AI shoppers): ${us_annual_brand_tax/1e9:.1f}B")
report_lines.append("")
report_lines.append("2. HHI MARKET CONCENTRATION")
report_lines.append("-" * 40)
report_lines.append(f"Mean HHI across {len(hhi_results)} categories: {mean_hhi:.0f}")
report_lines.append(f"Equal-distribution HHI: 2000")
report_lines.append(f"Mean concentration ratio: {mean_ratio:.2f}x above equal distribution")
report_lines.append(f"Categories above DOJ 'highly concentrated' threshold (>2500): {n_concentrated}/{len(hhi_results)}")
report_lines.append(f"")
top3_hhi = sorted(hhi_results, key=lambda x: -x["hhi_ai"])[:3]
for r in top3_hhi:
    report_lines.append(f"  {r['category'].replace('_',' ').title()}: HHI={r['hhi_ai']:.0f}, "
                       f"top brand={r['top_brand']} ({r['top_brand_share']:.0%})")
report_lines.append("")
report_lines.append("3. BRAND PROFILES (Supplementary Table 1)")
report_lines.append("-" * 40)
report_lines.append(f"Total brands in experiment: {len(brand_table)}")
top5 = [b for b in brand_table if b["non_optimal_selections"] > 0][:5]
for b in top5:
    report_lines.append(f"  {b['brand']} ({b['familiarity']}): "
                       f"chosen {b['non_optimal_selections']}x when suboptimal, "
                       f"rate={b['non_optimal_selection_rate']:.1%}, "
                       f"confab={b['confabulation_rate']:.0%}, "
                       f"${b['mean_price_premium']:.0f} premium")

report = "\n".join(report_lines)
print("\n" + report)

# Save report
report_path = OUT / "consequences_report.txt"
with open(report_path, "w", encoding="utf-8") as f:
    f.write(report)
print(f"\nSaved report: {report_path}")

print(f"\nAll outputs saved to: {OUT}")
print("Done.")
