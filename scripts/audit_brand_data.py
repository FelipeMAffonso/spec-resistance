"""
Brand Data Audit Script
========================
MUST RUN THIS BEFORE ANY ANALYSIS.
Checks data quality, identifies problems, and documents issues.

Audits:
1. Brand name disambiguation (Apple the fruit vs Apple Inc.)
2. Fictional brand leakage (do fictional names appear for unrelated reasons?)
3. Cross-reference scanner brands against actual assortment brands
4. Sanity checks on frequency distributions
5. Missing data identification

Output: results/01-brand-frequency/AUDIT_REPORT.md

Usage:
    python scripts/audit_brand_data.py
"""

import csv
import json
import os
import sys
import logging
from pathlib import Path
from collections import defaultdict
from datetime import datetime

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent  # spec-resistance/
DATA_DIR = SCRIPT_DIR.parent / "data"
RESULTS_DIR = SCRIPT_DIR.parent / "results" / "01-brand-frequency"
FREQ_CSV = DATA_DIR / "brand_frequencies.csv"
WIKI_CSV = DATA_DIR / "brand_wikipedia_pageviews.csv"
AUDIT_FILE = RESULTS_DIR / "AUDIT_REPORT.md"

# Import assortments to cross-reference
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')


def load_assortment_brands():
    """Extract all brand names from the actual experiment assortments."""
    try:
        from experiment.assortments import ASSORTMENTS
        brands = set()
        brand_details = []
        for key, assortment in ASSORTMENTS.items():
            category = assortment.get('category', key)
            for product in assortment.get('products', []):
                brand = product.get('brand', '')
                if brand:
                    brands.add(brand)
                    brand_details.append({
                        'brand': brand,
                        'assortment': key,
                        'category': category,
                        'is_optimal': product.get('is_optimal', False),
                    })
        return brands, brand_details
    except ImportError as e:
        logging.error(f"Could not import assortments: {e}")
        return set(), []


def load_frequency_data():
    """Load brand frequency CSV if it exists."""
    if not FREQ_CSV.exists():
        return None
    rows = []
    with open(FREQ_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def load_wikipedia_data():
    """Load Wikipedia pageview CSV if it exists."""
    if not WIKI_CSV.exists():
        return None
    rows = []
    with open(WIKI_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


# ---------------------------------------------------------------------------
# KNOWN DISAMBIGUATION ISSUES
# These brand names are ambiguous in training data
# ---------------------------------------------------------------------------
DISAMBIGUATION_ISSUES = {
    "Apple": "Apple Inc. vs apple (fruit). infini-gram counts include BOTH. "
             "Category-specific queries ('Apple laptop', 'Apple smartphone') are more reliable. "
             "Consider using 'Apple Inc' or 'iPhone' as alternative queries.",
    "Nothing": "Nothing (phone brand) vs 'nothing' (common English word). "
               "Raw frequency will be massively inflated. MUST use category-specific queries only.",
    "Amazon": "Amazon (company) vs Amazon (river/rainforest). "
              "Category queries are more reliable.",
    "Google": "Google (company) vs 'google' (verb). "
              "Category queries are more reliable.",
    "Shark": "SharkNinja (vacuum brand) vs shark (animal). "
             "MUST use 'Shark vacuum' or 'SharkNinja' instead of bare 'Shark'.",
    "Brooks": "Brooks Sports (running) vs Brooks Brothers (fashion) vs other Brooks. "
              "MUST use 'Brooks running' category query.",
    "Stanley": "Stanley (drinkware) vs Stanley (tools) vs Stanley Cup vs other. "
               "MUST use 'Stanley water bottle' or 'Stanley tumbler'.",
    "Marshall": "Marshall Amplification vs Marshall (name/place). "
                "Category query 'Marshall headphones' is more reliable.",
    "Flair": "Flair Espresso vs flair (common word). "
             "MUST use 'Flair espresso' or 'Flair Espresso Maker'.",
    "Varia": "Varia (coffee) vs varia (Latin, common in academic text). "
             "MUST use 'Varia coffee' or 'Varia VS3'.",
    "Yeti": "Yeti (drinkware) vs yeti (mythical creature). "
            "Category query is more reliable.",
}


def audit_disambiguation(freq_data):
    """Check which ambiguous brands have suspiciously high counts."""
    issues = []
    if freq_data is None:
        return ["FREQUENCY DATA NOT YET AVAILABLE -- cannot audit disambiguation"]

    for brand, note in DISAMBIGUATION_ISSUES.items():
        brand_rows = [r for r in freq_data if r.get('brand_name', '') == brand
                      and r.get('query_type', '') == 'brand_only']
        category_rows = [r for r in freq_data if r.get('brand_name', '') == brand
                         and r.get('query_type', '') == 'brand_category']

        if brand_rows:
            max_count = max(int(r.get('raw_count', 0)) for r in brand_rows)
            issues.append(f"**{brand}** (max brand_only count: {max_count:,}): {note}")
            if category_rows:
                max_cat = max(int(r.get('raw_count', 0)) for r in category_rows)
                if max_cat > 0:
                    issues.append(f"  - Category-specific max: {max_cat:,} "
                                  f"(ratio: {max_count / max_cat:.1f}x)")
                else:
                    issues.append(f"  - Category-specific max: 0 (no category hits)")

    return issues


def audit_fictional_leakage(freq_data):
    """Check if any fictional brands have nonzero counts."""
    issues = []
    if freq_data is None:
        return ["FREQUENCY DATA NOT YET AVAILABLE"]

    for row in freq_data:
        is_fic = str(row.get('is_fictional', '')).lower() == 'true'
        if is_fic and int(row.get('raw_count', 0)) > 0:
            issues.append(
                f"**{row['brand_name']}** has {row['raw_count']} hits "
                f"in {row.get('corpus', '?')} "
                f"(query: '{row.get('query_string', row.get('variant', '?'))}'). "
                f"Investigate: is this a real entity with the same name?"
            )
    return issues


def audit_cross_reference(assortment_brands, freq_data):
    """Check that every assortment brand appears in the frequency data."""
    issues = []
    if freq_data is None:
        return ["FREQUENCY DATA NOT YET AVAILABLE"]

    scanner_brands = set(r.get('brand_name', '') for r in freq_data)

    missing = assortment_brands - scanner_brands
    extra = scanner_brands - assortment_brands

    if missing:
        issues.append(f"**MISSING from scanner** ({len(missing)} brands): {sorted(missing)}")
    if extra:
        issues.append(f"**Extra in scanner** (not in assortments, {len(extra)} brands): "
                      f"these may be fictional brands or aliases")

    return issues


def audit_distribution(freq_data):
    """Sanity check frequency distributions."""
    issues = []
    if freq_data is None:
        return ["FREQUENCY DATA NOT YET AVAILABLE"]

    # Check brand_only queries in RedPajama
    rp_brand = [r for r in freq_data
                if r.get('corpus', '') == 'RedPajama'
                and r.get('query_type', '') == 'brand_only']

    if not rp_brand:
        return ["No RedPajama brand_only data found"]

    # Group by brand, take max across variants
    brand_max = defaultdict(int)
    brand_fictional = {}
    for r in rp_brand:
        brand = r.get('brand_name', '')
        count = int(r.get('raw_count', 0))
        brand_max[brand] = max(brand_max[brand], count)
        brand_fictional[brand] = str(r.get('is_fictional', '')).lower() == 'true'

    real_counts = sorted([c for b, c in brand_max.items() if not brand_fictional.get(b, False)],
                         reverse=True)
    fictional_counts = sorted([c for b, c in brand_max.items() if brand_fictional.get(b, False)],
                              reverse=True)

    if real_counts:
        issues.append(f"Real brands (RedPajama, brand_only, max across variants):")
        issues.append(f"  - N = {len(real_counts)}")
        issues.append(f"  - Max: {real_counts[0]:,}")
        issues.append(f"  - Median: {real_counts[len(real_counts)//2]:,}")
        issues.append(f"  - Min: {real_counts[-1]:,}")
        issues.append(f"  - Zero count: {sum(1 for c in real_counts if c == 0)}")

    if fictional_counts:
        issues.append(f"Fictional brands (RedPajama, brand_only, max across variants):")
        issues.append(f"  - N = {len(fictional_counts)}")
        issues.append(f"  - Max: {fictional_counts[0]:,}")
        issues.append(f"  - Nonzero: {sum(1 for c in fictional_counts if c > 0)}")

    # Flag potential issues
    if real_counts and real_counts[-1] == 0:
        zero_real = [b for b, c in brand_max.items()
                     if c == 0 and not brand_fictional.get(b, False)]
        issues.append(f"\n  WARNING: {len(zero_real)} real brands have zero counts: {zero_real}")

    return issues


def main():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    logging.info("Starting brand data audit...")

    # Load data
    assortment_brands, brand_details = load_assortment_brands()
    freq_data = load_frequency_data()
    wiki_data = load_wikipedia_data()

    # Run audits
    disambiguation = audit_disambiguation(freq_data)
    leakage = audit_fictional_leakage(freq_data)
    crossref = audit_cross_reference(assortment_brands, freq_data)
    distribution = audit_distribution(freq_data)

    # Write report
    report = f"""# Brand Data Audit Report
## Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}

---

## 1. Data Availability

| Dataset | Status | File |
|---------|--------|------|
| Brand frequencies (infini-gram) | {'AVAILABLE' if freq_data else 'NOT YET COLLECTED'} | `data/brand_frequencies.csv` |
| Wikipedia pageviews | {'AVAILABLE' if wiki_data else 'NOT YET COLLECTED'} | `data/brand_wikipedia_pageviews.csv` |
| Google Trends | NOT YET COLLECTED | `data/brand_google_trends.csv` |
| Brand equity (Interbrand) | NOT YET COLLECTED | manual |
| Assortment brands (from experiment) | {'AVAILABLE (' + str(len(assortment_brands)) + ' brands)' if assortment_brands else 'ERROR LOADING'} | `experiment/assortments.py` |

---

## 2. Disambiguation Issues (CRITICAL)

These brand names are ambiguous in training data. Raw `brand_only` counts are UNRELIABLE for these brands. Use `brand_category` counts instead.

{chr(10).join(disambiguation)}

**ACTION REQUIRED:** For the analysis, use category-specific frequency queries for all ambiguous brands. For the main regression, consider excluding bare-name counts for these brands and using only category-contextualized counts.

---

## 3. Fictional Brand Leakage

{chr(10).join(leakage) if leakage else 'No leakage detected (or data not yet available).'}

**ACTION REQUIRED:** If any fictional brand has significant nonzero counts, investigate whether the name coincidentally matches a real entity. Consider renaming the brand or flagging it in the analysis.

---

## 4. Cross-Reference: Scanner vs Assortments

{chr(10).join(crossref) if crossref else 'Cross-reference passed (or data not yet available).'}

---

## 5. Frequency Distribution Sanity Checks

{chr(10).join(distribution)}

---

## 6. Connection to Nature Editor Concerns

### Concern #1: "Robustness/strength of pre-training preferences"
- The frequency data answers WHERE preferences come from
- The disambiguation audit ensures we're measuring the RIGHT thing
- Category-specific queries (brand + product type) are more convincing than raw name counts
- The fictional brand zero-count verification is a natural control

### Concern #2: "Whether this survives post-training or fine-tuning"
- Frequency data is INPUT to this question, not the answer
- The answer comes from base vs instruct + DPO experiments (separate)
- But: if frequency predicts preference equally in base AND instruct models, that shows alignment didn't modify the frequency-to-preference mapping

### Concern #3: "Evidence that people follow these recommendations"
- Frequency data is not directly relevant here
- But: we can show that the brands LLMs over-recommend (high frequency) are the same brands that real consumers recognize (Google Trends correlation), making the human compliance story plausible even before running the Prolific experiment

---

## 7. Recommendations Before Analysis

1. **DO NOT run regressions on raw brand_only counts for ambiguous brands** (Apple, Nothing, Google, Amazon, Shark, Brooks, Stanley, Marshall, Flair, Varia, Yeti)
2. **USE category-specific counts** as the primary frequency measure
3. **VERIFY all fictional brands return near-zero** counts
4. **CHECK cross-corpus correlation** before aggregating (do Pile, Dolma, RedPajama, C4 agree?)
5. **LOG-TRANSFORM** all frequency counts: log(1 + count_per_million)
6. **DOCUMENT** that these are proxy corpora, not exact training data
"""

    with open(AUDIT_FILE, 'w', encoding='utf-8') as f:
        f.write(report)

    logging.info(f"Audit report saved to {AUDIT_FILE}")


if __name__ == "__main__":
    main()
