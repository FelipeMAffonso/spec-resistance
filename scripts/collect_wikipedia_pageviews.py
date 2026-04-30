"""
Wikipedia Pageview Collector for Spec-Resistance Project
=========================================================
Collects monthly pageview data for all brand names from the Wikimedia API.
No authentication required. Free API with generous rate limits.

Output: data/brand_wikipedia_pageviews.csv

Usage:
    python scripts/collect_wikipedia_pageviews.py
"""

import csv
import json
import os
import sys
import time
import logging
from pathlib import Path
from datetime import datetime

import requests

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent  # spec-resistance/
OUTPUT_DIR = SCRIPT_DIR.parent / "data"
OUTPUT_CSV = OUTPUT_DIR / "brand_wikipedia_pageviews.csv"

# Wikimedia Pageviews API
# Docs: https://doc.wikimedia.org/generated-data-platform/aqs/analytics-api/reference/page-views.html
API_BASE = "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article"

# Date range: 12 months of data (2025-01 to 2025-12, covering pre-training window)
START_DATE = "20250101"
END_DATE = "20251231"

REQUEST_DELAY = 0.1  # seconds between requests (API is generous)

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

# ---------------------------------------------------------------------------
# Brand -> Wikipedia article mapping
# Hand-curated: some brands need disambiguation or have non-obvious article names
# ---------------------------------------------------------------------------

BRAND_WIKIPEDIA = {
    # HIGH FAMILIARITY
    "Adidas": "Adidas",
    "Apple": "Apple_Inc.",
    "ASUS": "Asus",
    "Beyerdynamic": "Beyerdynamic",
    "Bose": "Bose_Corporation",
    "Breville": "Breville",
    "Brooks": "Brooks_Sports",
    "Canon": "Canon_Inc.",
    "Cuisinart": "Cuisinart",
    "Dell": "Dell",
    "De'Longhi": "De%27Longhi",
    "Dyson": "Dyson_(company)",
    "Garmin": "Garmin",
    "Google": "Google",
    "HP": "HP_Inc.",
    "iRobot": "IRobot",
    "JBL": "JBL_(company)",
    "KitchenAid": "KitchenAid",
    "Lenovo": "Lenovo",
    "LG": "LG_Electronics",
    "Logitech": "Logitech",
    "Nespresso": "Nespresso",
    "New Balance": "New_Balance",
    "Nike": "Nike,_Inc.",
    "Ninja": "SharkNinja",
    "OnePlus": "OnePlus",
    "Samsung": "Samsung_Electronics",
    "Sennheiser": "Sennheiser",
    "Sony": "Sony",
    "Stanley": "Stanley_(brand)",
    "TP-Link": "TP-Link",
    "Vitamix": "Vitamix",
    "Xiaomi": "Xiaomi",
    # MEDIUM FAMILIARITY
    "Acer": "Acer_Inc.",
    "Anker": "Anker_(company)",
    "ASICS": "ASICS",
    "Audio-Technica": "Audio-Technica",
    "Bang & Olufsen": "Bang_%26_Olufsen",
    "BlendJet": None,  # No Wikipedia article
    "Bose SoundLink": None,  # Product, not brand article
    "Coway": "Coway_Co.",
    "Ecovacs": "Ecovacs",
    "Hoka": "Hoka_(shoe_brand)",
    "Jabra": "Jabra",
    "Keychron": None,  # No Wikipedia article (low profile)
    "Levoit": None,  # No Wikipedia article
    "Marshall": "Marshall_Amplification",
    "Motorola": "Motorola",
    "MSI": "Micro-Star_International",
    "NETGEAR": "Netgear",
    "Nothing": "Nothing_(company)",
    "Philips": "Philips",
    "Realme": "Realme",
    "Roborock": "Roborock",
    "Saucony": "Saucony",
    "Skullcandy": "Skullcandy",
    "Technics": "Technics_(brand)",
    "ViewSonic": "ViewSonic",
    "Winix": None,  # No Wikipedia article
    "Yeti": "Yeti_(company)",
    # Additional brands from assortments
    "Nikon": "Nikon",
    "Fujifilm": "Fujifilm",
    "Panasonic": "Panasonic",
    "Oral-B": "Oral-B",
    "Philips Sonicare": "Philips_Sonicare",
    "Amazon": "Amazon_(company)",
    "Google Pixel": "Pixel_(smartphone)",
    "Osprey": "Osprey_Packs",
    "The North Face": "The_North_Face",
    "Deuter": "Deuter_Sport",
    "ASUS ROG": "Republic_of_Gamers",
    "Corsair": "Corsair_Gaming",
    "Razer": "Razer_Inc.",
    "SteelSeries": "SteelSeries",
    "BenQ": "BenQ",
    "Linksys": "Linksys",
    "UE": "Ultimate_Ears",
    "Bowers & Wilkins": "Bowers_%26_Wilkins",
}

# Fictional brands (should have zero or near-zero pageviews if articles exist at all)
FICTIONAL_BRANDS = [
    "Zentria", "Novatech", "Sonaray", "Presswell", "Veridian", "Crestline",
    "Lumivox", "Arcwave", "Vaultdrive", "Trailwise", "Wavecrest", "Aeroflux",
    "Peakstride", "Glideform", "Purevolt", "Aquapure", "Cleanwave", "Blendcore",
    "Snapfresh", "Terralink", "Signalmax", "Echosound", "Clearview", "Pixelforge",
    "Naviroam", "Clickstream", "Gridmaster", "Botiquo", "Sweepbot", "Frostbyte",
    "Hydrocore", "Enduraclean",
]


def get_pageviews(article_title: str) -> dict:
    """Fetch monthly pageviews for a Wikipedia article."""
    url = f"{API_BASE}/en.wikipedia/all-access/all-agents/{article_title}/monthly/{START_DATE}/{END_DATE}"
    headers = {
        "User-Agent": "SpecResistanceResearch/1.0 (felipe.affonso@okstate.edu)"
    }
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            items = data.get("items", [])
            views = [item["views"] for item in items]
            return {
                "total_views": sum(views),
                "avg_monthly": sum(views) / len(views) if views else 0,
                "max_monthly": max(views) if views else 0,
                "min_monthly": min(views) if views else 0,
                "months": len(views),
                "article_exists": True,
            }
        elif resp.status_code == 404:
            return {"total_views": 0, "avg_monthly": 0, "max_monthly": 0,
                    "min_monthly": 0, "months": 0, "article_exists": False}
        else:
            logging.warning(f"  HTTP {resp.status_code} for {article_title}")
            return {"total_views": 0, "avg_monthly": 0, "max_monthly": 0,
                    "min_monthly": 0, "months": 0, "article_exists": False}
    except Exception as e:
        logging.warning(f"  Error for {article_title}: {e}")
        return {"total_views": 0, "avg_monthly": 0, "max_monthly": 0,
                "min_monthly": 0, "months": 0, "article_exists": False}


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    results = []

    # Real brands
    logging.info(f"Collecting pageviews for {len(BRAND_WIKIPEDIA)} real brands...")
    for brand, article in sorted(BRAND_WIKIPEDIA.items()):
        if article is None:
            logging.info(f"  {brand}: no Wikipedia article")
            results.append({
                "brand": brand, "is_fictional": False, "wikipedia_article": "",
                "article_exists": False, "total_views": 0, "avg_monthly": 0,
                "max_monthly": 0, "min_monthly": 0, "months": 0,
            })
            continue

        pv = get_pageviews(article)
        logging.info(f"  {brand} ({article}): {pv['avg_monthly']:,.0f} avg monthly views")
        results.append({
            "brand": brand, "is_fictional": False, "wikipedia_article": article,
            **pv,
        })
        time.sleep(REQUEST_DELAY)

    # Fictional brands (check if any accidentally have articles)
    logging.info(f"\nChecking {len(FICTIONAL_BRANDS)} fictional brands...")
    for brand in sorted(FICTIONAL_BRANDS):
        pv = get_pageviews(brand)
        if pv["article_exists"]:
            logging.warning(f"  WARNING: Fictional brand '{brand}' has a Wikipedia article!")
        else:
            logging.info(f"  {brand}: no article (expected)")
        results.append({
            "brand": brand, "is_fictional": True, "wikipedia_article": brand,
            **pv,
        })
        time.sleep(REQUEST_DELAY)

    # Write CSV
    fieldnames = ["brand", "is_fictional", "wikipedia_article", "article_exists",
                  "total_views", "avg_monthly", "max_monthly", "min_monthly", "months"]
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    logging.info(f"\nSaved {len(results)} brands to {OUTPUT_CSV}")

    # Summary
    real = [r for r in results if not r["is_fictional"] and r["article_exists"]]
    fictional = [r for r in results if r["is_fictional"]]
    logging.info(f"\nSummary:")
    logging.info(f"  Real brands with articles: {len(real)}")
    logging.info(f"  Real brands without articles: {len([r for r in results if not r['is_fictional'] and not r['article_exists']])}")
    logging.info(f"  Fictional brands: {len(fictional)}")
    if real:
        avg_views = sorted(real, key=lambda x: x["avg_monthly"], reverse=True)
        logging.info(f"\n  Top 10 by avg monthly pageviews:")
        for r in avg_views[:10]:
            logging.info(f"    {r['brand']}: {r['avg_monthly']:,.0f}")
        logging.info(f"\n  Bottom 5:")
        for r in avg_views[-5:]:
            logging.info(f"    {r['brand']}: {r['avg_monthly']:,.0f}")


if __name__ == "__main__":
    main()
