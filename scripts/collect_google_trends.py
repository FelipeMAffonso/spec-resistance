"""
Google Trends Interest Collector for Spec-Resistance Project
=============================================================
Collects Google Trends search interest data for all brand names using
the GTAB (Google Trends Anchor Bank) calibration method from EPFL.

GTAB solves the normalization problem: Google Trends returns 0-100 values
normalized within each 5-term query, making raw values incomparable across
queries. GTAB builds an anchor bank of reference queries and calibrates
any new query to an absolute scale via binary search.

Fallback: If gtab is unavailable, uses pytrends with anchor-stitching
(Nike as the common anchor across all batches of 5).

Output: data/brand_google_trends.csv

Usage:
    python scripts/collect_google_trends.py
    python scripts/collect_google_trends.py --dry-run
    python scripts/collect_google_trends.py --method pytrends
    python scripts/collect_google_trends.py --resume

References:
    West (CIKM 2020): GTAB calibration. https://arxiv.org/abs/2007.13861
    GTAB package: https://github.com/epfl-dlab/GoogleTrendsAnchorBank
"""

import argparse
import csv
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent  # spec-resistance/
OUTPUT_DIR = SCRIPT_DIR.parent / "data"
OUTPUT_CSV = OUTPUT_DIR / "brand_google_trends.csv"
CHECKPOINT_FILE = OUTPUT_DIR / "google_trends_checkpoint.json"

# Google Trends settings
ANCHOR_BRAND = "Nike"  # Anchor for pytrends stitching (high, stable volume)
PYTRENDS_BATCH_SIZE = 4  # 4 + anchor = 5 keywords per request
PYTRENDS_DELAY = 65  # seconds between pytrends requests (rate limit ~60s)
GTAB_TIMEFRAME = "today 12-m"  # 12 months of data

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Brand Database: search terms with category disambiguation
# ---------------------------------------------------------------------------
# For brands where the name alone is ambiguous (e.g., "Nothing", "Shark",
# "Brooks"), we append a category keyword so Google Trends returns the
# correct entity rather than the common English word.

BRAND_SEARCH_TERMS = {
    # === HIGH FAMILIARITY ===
    "Adidas": "Adidas shoes",
    "Apple": "Apple",  # Dominant enough to not need disambiguation
    "Beats": "Beats headphones",
    "Bose": "Bose",
    "Canon": "Canon camera",
    "De'Longhi": "De'Longhi espresso",
    "Dell": "Dell laptop",
    "Dyson": "Dyson vacuum",
    "Google": "Google Pixel",  # "Google" alone captures search engine
    "HP": "HP laptop",
    "Hydro Flask": "Hydro Flask",
    "JanSport": "JanSport backpack",
    "Keurig": "Keurig",
    "KitchenAid": "KitchenAid",
    "LG": "LG Electronics",
    "Lenovo": "Lenovo laptop",
    "Logitech": "Logitech",
    "Mr. Coffee": "Mr Coffee",
    "Nespresso": "Nespresso",
    "Netgear": "Netgear",
    "Nike": "Nike",
    "Nikon": "Nikon camera",
    "Ninja": "Ninja blender",
    "Oral-B": "Oral-B",
    "Philips": "Philips electronics",
    "Razer": "Razer keyboard",
    "Samsung": "Samsung",
    "SanDisk": "SanDisk",
    "Seagate": "Seagate",
    "Sony": "Sony",
    "The North Face": "The North Face",
    "Vitamix": "Vitamix",
    "Western Digital": "Western Digital",
    "Yeti": "Yeti cooler",
    "iRobot": "iRobot Roomba",

    # === MEDIUM FAMILIARITY ===
    "ASICS": "ASICS shoes",
    "ASUS": "ASUS laptop",
    "Acer": "Acer laptop",
    "AeroPress": "AeroPress coffee",
    "Amazon": "Amazon Fire tablet",
    "Audio-Technica": "Audio-Technica",
    "Beyerdynamic": "Beyerdynamic",
    "Breville": "Breville espresso",
    "Brooks": "Brooks Running shoes",
    "CamelBak": "CamelBak",
    "Corsair": "Corsair keyboard",
    "Cuisinart": "Cuisinart",
    "Fitbit": "Fitbit",
    "Fujifilm": "Fujifilm camera",
    "Garmin": "Garmin watch",
    "HOKA": "HOKA shoes",
    "Hamilton Beach": "Hamilton Beach blender",
    "Herschel": "Herschel backpack",
    "HyperX": "HyperX keyboard",
    "Insignia": "Insignia TV",
    "JBL": "JBL speaker",
    "Jabra": "Jabra earbuds",
    "Linksys": "Linksys router",
    "Motorola": "Motorola phone",
    "New Balance": "New Balance shoes",
    "OnePlus": "OnePlus phone",
    "Osprey": "Osprey backpack",
    "Quip": "Quip toothbrush",
    "S'well": "Swell bottle",
    "Salomon": "Salomon shoes",
    "Saucony": "Saucony shoes",
    "Sennheiser": "Sennheiser headphones",
    "Shark": "Shark robot vacuum",
    "Shokz": "Shokz headphones",
    "Stanley": "Stanley tumbler",
    "Ultimate Ears": "Ultimate Ears speaker",
    "Vizio": "Vizio TV",
    "eufy": "eufy vacuum",

    # === LOW FAMILIARITY (real) ===
    "1MORE": "1MORE earbuds",
    "Amazfit": "Amazfit watch",
    "Atreyu": "Atreyu running shoes",
    "Bmax": "BMAX laptop",
    "CHUWI": "CHUWI laptop",
    "Cleanblend": "Cleanblend blender",
    "EarFun": "EarFun earbuds",
    "Evergoods": "Evergoods backpack",
    "Fairphone": "Fairphone",
    "Flair": "Flair Espresso",
    "HiFiMAN": "HiFiMAN headphones",
    "Hisense": "Hisense TV",
    "Innocn": "Innocn monitor",
    "Inov-8": "Inov-8 shoes",
    "Keychron": "Keychron keyboard",
    "Nothing": "Nothing Phone",
    "OM System": "OM System camera",
    "Oclean": "Oclean toothbrush",
    "Roborock": "Roborock vacuum",
    "Silicon Power": "Silicon Power SSD",
    "SoundPEATS": "SoundPEATS earbuds",
    "Soundcore": "Soundcore headphones",
    "TCL": "TCL TV",
    "TOZO": "TOZO earbuds",
    "TP-Link": "TP-Link router",
    "Teclast": "Teclast laptop",
    "ThermoFlask": "ThermoFlask bottle",
    "Topo Athletic": "Topo Athletic shoes",
    "Tribit": "Tribit speaker",
    "Varia": "Varia coffee grinder",
    "Wacaco": "Wacaco Nanopresso",
    "Xiaomi": "Xiaomi",
}

# Fictional brands (should return 0 interest)
FICTIONAL_BRANDS = [
    "Arcwave", "Auralis", "Aurem", "Blendwell", "Brevara", "Chronex",
    "Cleanpath", "Dentara", "Ethicom", "Keystrike", "Lumivue", "Netweave",
    "Novatech", "Optivex", "Pixelight", "Portabrew", "Presswell",
    "Primebook", "Sonance", "Sonaray", "Sonique", "Stridewell", "Swiftform",
    "Terravolt", "Thermalux", "Trailpeak", "Vaultdrive", "Veridian",
    "Vistara", "Vynex", "Wavecrest", "Zentria",
]


# ---------------------------------------------------------------------------
# GTAB Method (preferred)
# ---------------------------------------------------------------------------

def collect_with_gtab(dry_run: bool = False) -> list[dict]:
    """
    Collect calibrated Google Trends data using the GTAB package.

    GTAB (Google Trends Anchor Bank) from EPFL calibrates search interest
    to an absolute scale by building an anchor bank of reference queries.
    This makes values comparable across different queries, unlike raw
    Google Trends data which is normalized 0-100 within each request.

    Install: pip install gtab
    Reference: https://github.com/epfl-dlab/GoogleTrendsAnchorBank
    """
    import gtab

    results = []

    # Initialize GTAB and set up the anchor bank
    logger.info("Initializing GTAB anchor bank (this may take a while on first run)...")
    t = gtab.GTAB()

    if not dry_run:
        # Create anchor bank if it doesn't exist.
        # GTAB maintains a local cache, so subsequent runs are faster.
        try:
            t.set_active_gtab("google_trends_anchor_bank")
            logger.info("Loaded existing GTAB anchor bank.")
        except Exception:
            logger.info("Creating new GTAB anchor bank (may take ~2 hours)...")
            t.create_anchorbank(
                num_anchors=500,
                timeframe=GTAB_TIMEFRAME,
            )
            t.set_active_gtab(t.list_gtabs()[-1])
            logger.info("Anchor bank created and activated.")

    # Query real brands
    logger.info(f"Querying {len(BRAND_SEARCH_TERMS)} real brands via GTAB...")
    for brand, search_term in sorted(BRAND_SEARCH_TERMS.items()):
        if dry_run:
            logger.info(f"  [DRY RUN] Would query: '{search_term}' for brand '{brand}'")
            results.append({
                "brand": brand,
                "is_fictional": False,
                "search_term": search_term,
                "avg_interest_12mo": 0.0,
                "max_interest": 0.0,
                "min_interest": 0.0,
                "trend_direction": "n/a",
                "method": "gtab",
                "calibrated": True,
            })
            continue

        try:
            query_result = t.new_query(search_term)
            if query_result is not None and not query_result.empty:
                values = query_result[search_term].dropna().tolist()
                avg_val = sum(values) / len(values) if values else 0.0
                max_val = max(values) if values else 0.0
                min_val = min(values) if values else 0.0
                # Trend direction: compare last 3 months vs first 3 months
                if len(values) >= 6:
                    early = sum(values[:3]) / 3
                    late = sum(values[-3:]) / 3
                    if late > early * 1.1:
                        direction = "increasing"
                    elif late < early * 0.9:
                        direction = "decreasing"
                    else:
                        direction = "stable"
                else:
                    direction = "insufficient_data"
            else:
                avg_val = 0.0
                max_val = 0.0
                min_val = 0.0
                direction = "no_data"

            logger.info(f"  {brand}: avg={avg_val:.2f}, max={max_val:.2f}, trend={direction}")
            results.append({
                "brand": brand,
                "is_fictional": False,
                "search_term": search_term,
                "avg_interest_12mo": round(avg_val, 4),
                "max_interest": round(max_val, 4),
                "min_interest": round(min_val, 4),
                "trend_direction": direction,
                "method": "gtab",
                "calibrated": True,
            })
        except Exception as e:
            logger.warning(f"  {brand}: GTAB query failed: {e}")
            results.append({
                "brand": brand,
                "is_fictional": False,
                "search_term": search_term,
                "avg_interest_12mo": 0.0,
                "max_interest": 0.0,
                "min_interest": 0.0,
                "trend_direction": "error",
                "method": "gtab",
                "calibrated": False,
            })

    # Fictional brands: record zero
    for brand in sorted(FICTIONAL_BRANDS):
        results.append({
            "brand": brand,
            "is_fictional": True,
            "search_term": brand,
            "avg_interest_12mo": 0.0,
            "max_interest": 0.0,
            "min_interest": 0.0,
            "trend_direction": "fictional",
            "method": "gtab",
            "calibrated": True,
        })

    return results


# ---------------------------------------------------------------------------
# pytrends Fallback: Anchor-Stitching Method
# ---------------------------------------------------------------------------

def collect_with_pytrends(dry_run: bool = False, resume: bool = False) -> list[dict]:
    """
    Fallback collector using pytrends with anchor-stitching.

    Because Google Trends normalizes each query's 0-100 within the batch,
    raw values from different batches are not comparable. Anchor-stitching
    fixes this by including a common anchor term (Nike) in every batch of 5,
    then rescaling all results so the anchor has a consistent value.

    Process:
        1. Query Nike alone to get its absolute level (the "reference" batch)
        2. For each batch of 4 brands + Nike:
           a. Get Google Trends data for the 5-term batch
           b. Compute the ratio: (anchor_value_in_this_batch / anchor_reference)
           c. Rescale all brand values by dividing by that ratio
        3. This produces comparable values across all brands

    Install: pip install pytrends
    """
    from pytrends.request import TrendReq

    pytrends = TrendReq(hl="en-US", tz=360)

    # Load checkpoint if resuming
    completed = {}
    if resume and CHECKPOINT_FILE.exists():
        with open(CHECKPOINT_FILE, "r") as f:
            completed = json.load(f)
        logger.info(f"Resuming from checkpoint: {len(completed)} brands already done.")

    results = []

    # Step 1: Get the anchor reference value (Nike alone, for baseline)
    anchor_reference = 100.0  # Default
    anchor_search_term = BRAND_SEARCH_TERMS[ANCHOR_BRAND]

    if not dry_run:
        logger.info(f"Step 1: Getting anchor reference for '{anchor_search_term}'...")
        try:
            pytrends.build_payload(
                [anchor_search_term],
                timeframe=GTAB_TIMEFRAME,
                geo="",
            )
            anchor_df = pytrends.interest_over_time()
            if not anchor_df.empty:
                anchor_reference = anchor_df[anchor_search_term].mean()
                logger.info(f"  Anchor reference (Nike mean): {anchor_reference:.2f}")
            else:
                logger.warning("  Could not get anchor reference. Using 100.0.")
            time.sleep(PYTRENDS_DELAY)
        except Exception as e:
            logger.warning(f"  Anchor query failed: {e}. Using reference=100.0.")

    # Step 2: Batch real brands in groups of 4 + anchor
    brand_items = sorted(
        [(b, t) for b, t in BRAND_SEARCH_TERMS.items() if b != ANCHOR_BRAND],
        key=lambda x: x[0],
    )

    batches = []
    for i in range(0, len(brand_items), PYTRENDS_BATCH_SIZE):
        batch = brand_items[i : i + PYTRENDS_BATCH_SIZE]
        batches.append(batch)

    logger.info(
        f"Step 2: Querying {len(brand_items)} brands in {len(batches)} batches "
        f"(~{len(batches) * PYTRENDS_DELAY / 60:.0f} min estimated)..."
    )

    for batch_idx, batch in enumerate(batches):
        batch_brands = {b: t for b, t in batch}
        search_terms = [anchor_search_term] + [t for _, t in batch]
        brand_names = [ANCHOR_BRAND] + [b for b, _ in batch]

        # Skip brands already in checkpoint
        if resume and all(b in completed for b in brand_names if b != ANCHOR_BRAND):
            logger.info(f"  Batch {batch_idx + 1}/{len(batches)}: all brands in checkpoint, skipping.")
            for b, t in batch:
                results.append(completed[b])
            continue

        if dry_run:
            logger.info(
                f"  [DRY RUN] Batch {batch_idx + 1}/{len(batches)}: "
                f"{[b for b, _ in batch]}"
            )
            for b, t in batch:
                results.append({
                    "brand": b,
                    "is_fictional": False,
                    "search_term": t,
                    "avg_interest_12mo": 0.0,
                    "max_interest": 0.0,
                    "min_interest": 0.0,
                    "trend_direction": "n/a",
                    "method": "pytrends_anchor",
                    "calibrated": False,
                })
            continue

        try:
            pytrends.build_payload(search_terms, timeframe=GTAB_TIMEFRAME, geo="")
            df = pytrends.interest_over_time()

            if df.empty:
                logger.warning(f"  Batch {batch_idx + 1}: empty response")
                for b, t in batch:
                    row = {
                        "brand": b,
                        "is_fictional": False,
                        "search_term": t,
                        "avg_interest_12mo": 0.0,
                        "max_interest": 0.0,
                        "min_interest": 0.0,
                        "trend_direction": "no_data",
                        "method": "pytrends_anchor",
                        "calibrated": False,
                    }
                    results.append(row)
                    completed[b] = row
                time.sleep(PYTRENDS_DELAY)
                continue

            # Compute rescaling factor from anchor in this batch
            batch_anchor_mean = df[anchor_search_term].mean()
            if batch_anchor_mean > 0:
                scale_factor = anchor_reference / batch_anchor_mean
            else:
                scale_factor = 1.0
                logger.warning(
                    f"  Batch {batch_idx + 1}: anchor mean is 0, cannot rescale"
                )

            # Extract and rescale each brand in the batch
            for b, t in batch:
                if t in df.columns:
                    values = df[t].tolist()
                    scaled = [v * scale_factor for v in values]
                    avg_val = sum(scaled) / len(scaled) if scaled else 0.0
                    max_val = max(scaled) if scaled else 0.0
                    min_val = min(scaled) if scaled else 0.0

                    # Trend direction
                    if len(scaled) >= 6:
                        early = sum(scaled[:13]) / 13 if len(scaled) >= 26 else sum(scaled[: len(scaled) // 2]) / (len(scaled) // 2)
                        late = sum(scaled[-13:]) / 13 if len(scaled) >= 26 else sum(scaled[len(scaled) // 2 :]) / (len(scaled) - len(scaled) // 2)
                        if late > early * 1.1:
                            direction = "increasing"
                        elif late < early * 0.9:
                            direction = "decreasing"
                        else:
                            direction = "stable"
                    else:
                        direction = "insufficient_data"
                else:
                    avg_val = 0.0
                    max_val = 0.0
                    min_val = 0.0
                    direction = "no_data"

                logger.info(
                    f"  {b}: avg={avg_val:.2f}, max={max_val:.2f}, "
                    f"scale={scale_factor:.3f}, trend={direction}"
                )
                row = {
                    "brand": b,
                    "is_fictional": False,
                    "search_term": t,
                    "avg_interest_12mo": round(avg_val, 4),
                    "max_interest": round(max_val, 4),
                    "min_interest": round(min_val, 4),
                    "trend_direction": direction,
                    "method": "pytrends_anchor",
                    "calibrated": True,
                }
                results.append(row)
                completed[b] = row

            # Save checkpoint after each batch
            with open(CHECKPOINT_FILE, "w") as f:
                json.dump(completed, f, indent=2)

        except Exception as e:
            logger.warning(f"  Batch {batch_idx + 1} failed: {e}")
            for b, t in batch:
                row = {
                    "brand": b,
                    "is_fictional": False,
                    "search_term": t,
                    "avg_interest_12mo": 0.0,
                    "max_interest": 0.0,
                    "min_interest": 0.0,
                    "trend_direction": "error",
                    "method": "pytrends_anchor",
                    "calibrated": False,
                }
                results.append(row)
                completed[b] = row

        # Rate limit (even on error, to avoid bans)
        if not dry_run:
            logger.info(f"  Sleeping {PYTRENDS_DELAY}s for rate limit...")
            time.sleep(PYTRENDS_DELAY)

    # Add the anchor brand itself (Nike)
    results.append({
        "brand": ANCHOR_BRAND,
        "is_fictional": False,
        "search_term": anchor_search_term,
        "avg_interest_12mo": round(anchor_reference, 4),
        "max_interest": round(anchor_reference, 4),  # Approximate
        "min_interest": round(anchor_reference, 4),
        "trend_direction": "anchor",
        "method": "pytrends_anchor",
        "calibrated": True,
    })

    # Fictional brands: record zero
    for brand in sorted(FICTIONAL_BRANDS):
        results.append({
            "brand": brand,
            "is_fictional": True,
            "search_term": brand,
            "avg_interest_12mo": 0.0,
            "max_interest": 0.0,
            "min_interest": 0.0,
            "trend_direction": "fictional",
            "method": "pytrends_anchor",
            "calibrated": True,
        })

    return results


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def write_csv(results: list[dict]) -> None:
    """Write results to CSV."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "brand", "is_fictional", "search_term",
        "avg_interest_12mo", "max_interest", "min_interest",
        "trend_direction", "method", "calibrated",
    ]

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    logger.info(f"Saved {len(results)} brands to {OUTPUT_CSV}")


def print_summary(results: list[dict]) -> None:
    """Print summary statistics."""
    real = [r for r in results if not r["is_fictional"]]
    fictional = [r for r in results if r["is_fictional"]]
    calibrated = [r for r in real if r["calibrated"]]

    logger.info(f"\nSummary:")
    logger.info(f"  Real brands: {len(real)}")
    logger.info(f"  Fictional brands: {len(fictional)}")
    logger.info(f"  Calibrated: {len(calibrated)} / {len(real)}")

    if calibrated:
        by_interest = sorted(calibrated, key=lambda x: x["avg_interest_12mo"], reverse=True)
        logger.info(f"\n  Top 10 by avg interest (12mo):")
        for r in by_interest[:10]:
            logger.info(
                f"    {r['brand']:20s}  avg={r['avg_interest_12mo']:8.2f}  "
                f"trend={r['trend_direction']}"
            )
        logger.info(f"\n  Bottom 5:")
        for r in by_interest[-5:]:
            logger.info(
                f"    {r['brand']:20s}  avg={r['avg_interest_12mo']:8.2f}  "
                f"trend={r['trend_direction']}"
            )

        # Trend distribution
        trends = {}
        for r in calibrated:
            d = r["trend_direction"]
            trends[d] = trends.get(d, 0) + 1
        logger.info(f"\n  Trend distribution:")
        for d, count in sorted(trends.items()):
            logger.info(f"    {d}: {count}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Collect Google Trends interest data for spec-resistance brands."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be queried without making API calls.",
    )
    parser.add_argument(
        "--method",
        choices=["gtab", "pytrends", "auto"],
        default="auto",
        help="Collection method: gtab (calibrated), pytrends (anchor-stitched), "
        "or auto (try gtab first, fall back to pytrends). Default: auto.",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from checkpoint (pytrends only).",
    )
    args = parser.parse_args()

    logger.info("=" * 70)
    logger.info("Google Trends Collector for Spec-Resistance Project")
    logger.info("=" * 70)

    if args.dry_run:
        logger.info("DRY RUN MODE: No API calls will be made.")

    # Select method
    method = args.method
    if method == "auto":
        try:
            import gtab  # noqa: F401
            method = "gtab"
            logger.info("GTAB package available. Using calibrated method.")
        except ImportError:
            try:
                from pytrends.request import TrendReq  # noqa: F401
                method = "pytrends"
                logger.info(
                    "GTAB not available. Falling back to pytrends with anchor-stitching."
                )
                logger.info(
                    "  For calibrated results, install GTAB: pip install gtab"
                )
            except ImportError:
                logger.error(
                    "Neither gtab nor pytrends is installed. "
                    "Install one of:\n"
                    "  pip install gtab        (preferred, EPFL calibration)\n"
                    "  pip install pytrends    (fallback, anchor-stitching)"
                )
                sys.exit(1)

    # Collect data
    if method == "gtab":
        results = collect_with_gtab(dry_run=args.dry_run)
    else:
        results = collect_with_pytrends(dry_run=args.dry_run, resume=args.resume)

    # Write output
    write_csv(results)
    print_summary(results)

    logger.info("\nDone.")


if __name__ == "__main__":
    main()
