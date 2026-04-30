"""
Market Capitalization & Financial Data Collector for Spec-Resistance Project
============================================================================
Collects market cap, revenue, P/E ratio, and other financial metrics for
all brands using yfinance. Brands are mapped to their parent company's
stock ticker where applicable.

Many brands in our assortment are private companies or subsidiaries of
larger conglomerates. The mapping below handles these cases:
  - Public companies: direct ticker lookup (e.g., Sony -> SONY)
  - Subsidiaries: mapped to parent company (e.g., JBL -> Samsung via Harman)
  - Private companies: marked as private, financial data = NaN

Output: data/brand_market_data.csv

Usage:
    python scripts/collect_market_data.py
    python scripts/collect_market_data.py --dry-run

Dependencies:
    pip install yfinance
"""

import argparse
import csv
import logging
import math
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
OUTPUT_CSV = OUTPUT_DIR / "brand_market_data.csv"

REQUEST_DELAY = 0.3  # seconds between yfinance requests (polite)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Brand -> Ticker Mapping
# ---------------------------------------------------------------------------
# Each entry contains:
#   ticker: Yahoo Finance ticker symbol (None if private)
#   parent_company: The publicly traded entity (may differ from brand name)
#   ownership: "public", "private", "subsidiary" (of a public company)
#   notes: Explanation of the mapping
#
# For subsidiaries, we record the parent company's financials since the
# subsidiary's brand value derives from and is reflected in the parent's
# market capitalization.

BRAND_TICKER_MAP = {
    # === HIGH FAMILIARITY ===
    "Adidas": {
        "ticker": "ADS.DE",
        "parent_company": "Adidas AG",
        "ownership": "public",
        "notes": "Frankfurt Stock Exchange",
    },
    "Apple": {
        "ticker": "AAPL",
        "parent_company": "Apple Inc.",
        "ownership": "public",
        "notes": "NASDAQ",
    },
    "Beats": {
        "ticker": "AAPL",
        "parent_company": "Apple Inc.",
        "ownership": "subsidiary",
        "notes": "Acquired by Apple in 2014 for $3B",
    },
    "Bose": {
        "ticker": None,
        "parent_company": "Bose Corporation",
        "ownership": "private",
        "notes": "Private; majority owned by MIT",
    },
    "Canon": {
        "ticker": "CAJ",
        "parent_company": "Canon Inc.",
        "ownership": "public",
        "notes": "NYSE ADR (also 7751.T on TSE)",
    },
    "De'Longhi": {
        "ticker": "DLG.MI",
        "parent_company": "De'Longhi S.p.A.",
        "ownership": "public",
        "notes": "Borsa Italiana (Milan)",
    },
    "Dell": {
        "ticker": "DELL",
        "parent_company": "Dell Technologies Inc.",
        "ownership": "public",
        "notes": "NYSE",
    },
    "Dyson": {
        "ticker": None,
        "parent_company": "Dyson Ltd.",
        "ownership": "private",
        "notes": "Private; owned by James Dyson",
    },
    "Google": {
        "ticker": "GOOGL",
        "parent_company": "Alphabet Inc.",
        "ownership": "public",
        "notes": "NASDAQ (Pixel, Nest are Google hardware brands)",
    },
    "HP": {
        "ticker": "HPQ",
        "parent_company": "HP Inc.",
        "ownership": "public",
        "notes": "NYSE (consumer PCs and printers)",
    },
    "Hydro Flask": {
        "ticker": "NWL",
        "parent_company": "Newell Brands Inc.",
        "ownership": "subsidiary",
        "notes": "Acquired by Helen of Troy (HELE) 2016, sold to Newell 2023",
    },
    "JanSport": {
        "ticker": "VFC",
        "parent_company": "VF Corporation",
        "ownership": "subsidiary",
        "notes": "Part of VF Corp portfolio (also owns The North Face)",
    },
    "Keurig": {
        "ticker": "KDP",
        "parent_company": "Keurig Dr Pepper Inc.",
        "ownership": "public",
        "notes": "NASDAQ",
    },
    "KitchenAid": {
        "ticker": "WHR",
        "parent_company": "Whirlpool Corporation",
        "ownership": "subsidiary",
        "notes": "KitchenAid is a Whirlpool brand",
    },
    "LG": {
        "ticker": "066570.KS",
        "parent_company": "LG Electronics Inc.",
        "ownership": "public",
        "notes": "Korea Exchange (KOSPI)",
    },
    "Lenovo": {
        "ticker": "0992.HK",
        "parent_company": "Lenovo Group Ltd.",
        "ownership": "public",
        "notes": "Hong Kong Stock Exchange",
    },
    "Logitech": {
        "ticker": "LOGI",
        "parent_company": "Logitech International S.A.",
        "ownership": "public",
        "notes": "NASDAQ (also LOGN.SW on SIX)",
    },
    "Mr. Coffee": {
        "ticker": "NWL",
        "parent_company": "Newell Brands Inc.",
        "ownership": "subsidiary",
        "notes": "Mr. Coffee is a Newell Brands product",
    },
    "Nespresso": {
        "ticker": "NSRGY",
        "parent_company": "Nestle S.A.",
        "ownership": "subsidiary",
        "notes": "Nespresso is a Nestle brand; OTC ADR (also NESN.SW)",
    },
    "Netgear": {
        "ticker": "NTGR",
        "parent_company": "NETGEAR Inc.",
        "ownership": "public",
        "notes": "NASDAQ",
    },
    "Nike": {
        "ticker": "NKE",
        "parent_company": "Nike Inc.",
        "ownership": "public",
        "notes": "NYSE",
    },
    "Nikon": {
        "ticker": "NINOY",
        "parent_company": "Nikon Corporation",
        "ownership": "public",
        "notes": "OTC ADR (also 7731.T on TSE)",
    },
    "Ninja": {
        "ticker": None,
        "parent_company": "SharkNinja Inc.",
        "ownership": "public",
        "notes": "SharkNinja went public (SN) on NYSE in 2023",
    },
    "Oral-B": {
        "ticker": "PG",
        "parent_company": "Procter & Gamble Co.",
        "ownership": "subsidiary",
        "notes": "Oral-B is a P&G brand",
    },
    "Philips": {
        "ticker": "PHG",
        "parent_company": "Koninklijke Philips N.V.",
        "ownership": "public",
        "notes": "NYSE ADR (also PHIA.AS on Euronext)",
    },
    "Razer": {
        "ticker": "1337.HK",
        "parent_company": "Razer Inc.",
        "ownership": "public",
        "notes": "Hong Kong Stock Exchange",
    },
    "Samsung": {
        "ticker": "005930.KS",
        "parent_company": "Samsung Electronics Co.",
        "ownership": "public",
        "notes": "Korea Exchange (KOSPI)",
    },
    "SanDisk": {
        "ticker": "WDC",
        "parent_company": "Western Digital Corporation",
        "ownership": "subsidiary",
        "notes": "SanDisk acquired by Western Digital 2016; WD split pending",
    },
    "Seagate": {
        "ticker": "STX",
        "parent_company": "Seagate Technology Holdings plc",
        "ownership": "public",
        "notes": "NASDAQ",
    },
    "Sony": {
        "ticker": "SONY",
        "parent_company": "Sony Group Corporation",
        "ownership": "public",
        "notes": "NYSE ADR (also 6758.T on TSE)",
    },
    "The North Face": {
        "ticker": "VFC",
        "parent_company": "VF Corporation",
        "ownership": "subsidiary",
        "notes": "Part of VF Corp portfolio",
    },
    "Vitamix": {
        "ticker": None,
        "parent_company": "Vitamix Corporation",
        "ownership": "private",
        "notes": "Private; family-owned since 1921",
    },
    "Western Digital": {
        "ticker": "WDC",
        "parent_company": "Western Digital Corporation",
        "ownership": "public",
        "notes": "NASDAQ",
    },
    "Yeti": {
        "ticker": "YETI",
        "parent_company": "YETI Holdings Inc.",
        "ownership": "public",
        "notes": "NYSE",
    },
    "iRobot": {
        "ticker": "IRBT",
        "parent_company": "iRobot Corporation",
        "ownership": "public",
        "notes": "NASDAQ (Amazon acquisition failed 2024)",
    },

    # === MEDIUM FAMILIARITY ===
    "ASICS": {
        "ticker": "7936.T",
        "parent_company": "ASICS Corporation",
        "ownership": "public",
        "notes": "Tokyo Stock Exchange",
    },
    "ASUS": {
        "ticker": "2357.TW",
        "parent_company": "ASUSTeK Computer Inc.",
        "ownership": "public",
        "notes": "Taiwan Stock Exchange",
    },
    "Acer": {
        "ticker": "2353.TW",
        "parent_company": "Acer Inc.",
        "ownership": "public",
        "notes": "Taiwan Stock Exchange",
    },
    "AeroPress": {
        "ticker": None,
        "parent_company": "AeroPress Inc.",
        "ownership": "private",
        "notes": "Private; acquired by private equity 2023",
    },
    "Amazon": {
        "ticker": "AMZN",
        "parent_company": "Amazon.com Inc.",
        "ownership": "public",
        "notes": "NASDAQ (Fire tablet brand)",
    },
    "Audio-Technica": {
        "ticker": None,
        "parent_company": "Audio-Technica Corporation",
        "ownership": "private",
        "notes": "Private; Japanese company founded 1962",
    },
    "Beyerdynamic": {
        "ticker": None,
        "parent_company": "beyerdynamic GmbH & Co. KG",
        "ownership": "private",
        "notes": "Private; German company since 1924",
    },
    "Breville": {
        "ticker": "BRG.AX",
        "parent_company": "Breville Group Ltd.",
        "ownership": "public",
        "notes": "Australian Securities Exchange",
    },
    "Brooks": {
        "ticker": "BRK-B",
        "parent_company": "Berkshire Hathaway Inc.",
        "ownership": "subsidiary",
        "notes": "Brooks Running is a subsidiary of Berkshire Hathaway",
    },
    "CamelBak": {
        "ticker": None,
        "parent_company": "CamelBak Products LLC",
        "ownership": "private",
        "notes": "Owned by Vista Outdoor (VSTO) until 2024 sale to CSG",
    },
    "Corsair": {
        "ticker": "CRSR",
        "parent_company": "Corsair Gaming Inc.",
        "ownership": "public",
        "notes": "NASDAQ",
    },
    "Cuisinart": {
        "ticker": "SPB",
        "parent_company": "Spectrum Brands Holdings Inc.",
        "ownership": "subsidiary",
        "notes": "Cuisinart is owned by Conair Corp (private); SPB approximate",
    },
    "Fitbit": {
        "ticker": "GOOGL",
        "parent_company": "Alphabet Inc.",
        "ownership": "subsidiary",
        "notes": "Acquired by Google in 2021 for $2.1B",
    },
    "Fujifilm": {
        "ticker": "FUJIY",
        "parent_company": "Fujifilm Holdings Corporation",
        "ownership": "public",
        "notes": "OTC ADR (also 4901.T on TSE)",
    },
    "Garmin": {
        "ticker": "GRMN",
        "parent_company": "Garmin Ltd.",
        "ownership": "public",
        "notes": "NYSE",
    },
    "HOKA": {
        "ticker": "DECK",
        "parent_company": "Deckers Outdoor Corporation",
        "ownership": "subsidiary",
        "notes": "HOKA is Deckers' fastest-growing brand",
    },
    "Hamilton Beach": {
        "ticker": "HBB",
        "parent_company": "Hamilton Beach Brands Holding Co.",
        "ownership": "public",
        "notes": "NYSE",
    },
    "Herschel": {
        "ticker": None,
        "parent_company": "Herschel Supply Company Ltd.",
        "ownership": "private",
        "notes": "Private; Canadian company founded 2009",
    },
    "HyperX": {
        "ticker": "HPQ",
        "parent_company": "HP Inc.",
        "ownership": "subsidiary",
        "notes": "HP acquired HyperX from Kingston in 2021 for $425M",
    },
    "Insignia": {
        "ticker": "BBY",
        "parent_company": "Best Buy Co. Inc.",
        "ownership": "subsidiary",
        "notes": "Insignia is Best Buy's private-label brand",
    },
    "JBL": {
        "ticker": "005930.KS",
        "parent_company": "Samsung Electronics Co.",
        "ownership": "subsidiary",
        "notes": "JBL is part of Harman International, acquired by Samsung 2017",
    },
    "Jabra": {
        "ticker": "GN.CO",
        "parent_company": "GN Audio A/S (GN Store Nord)",
        "ownership": "subsidiary",
        "notes": "Jabra is GN Audio's consumer brand; Copenhagen exchange",
    },
    "Linksys": {
        "ticker": None,
        "parent_company": "Fortinet Inc.",
        "ownership": "subsidiary",
        "notes": "Sold by Belkin to Fortinet (FTNT) 2023; limited brand data",
    },
    "Motorola": {
        "ticker": "0992.HK",
        "parent_company": "Lenovo Group Ltd.",
        "ownership": "subsidiary",
        "notes": "Motorola Mobility acquired by Lenovo 2014",
    },
    "New Balance": {
        "ticker": None,
        "parent_company": "New Balance Athletics Inc.",
        "ownership": "private",
        "notes": "Private; family-owned since 1906",
    },
    "OnePlus": {
        "ticker": None,
        "parent_company": "OnePlus Technology (Shenzhen) Co.",
        "ownership": "private",
        "notes": "Subsidiary of OPPO/BBK Electronics (private)",
    },
    "Osprey": {
        "ticker": None,
        "parent_company": "Osprey Packs Inc.",
        "ownership": "private",
        "notes": "Acquired by Helen of Troy (HELE) 2021; HELE is public",
    },
    "Quip": {
        "ticker": None,
        "parent_company": "Quip NYC Inc.",
        "ownership": "private",
        "notes": "Private; venture-backed DTC dental care",
    },
    "S'well": {
        "ticker": None,
        "parent_company": "S'well Bottle LLC",
        "ownership": "private",
        "notes": "Private; filed for bankruptcy 2023",
    },
    "Salomon": {
        "ticker": None,
        "parent_company": "Amer Sports Inc.",
        "ownership": "public",
        "notes": "Amer Sports (AS) went public on NYSE 2024; owns Salomon",
    },
    "Saucony": {
        "ticker": "WWW",
        "parent_company": "Wolverine World Wide Inc.",
        "ownership": "subsidiary",
        "notes": "Saucony is a Wolverine World Wide brand",
    },
    "Sennheiser": {
        "ticker": None,
        "parent_company": "Sennheiser electronic GmbH & Co. KG",
        "ownership": "private",
        "notes": "Consumer division sold to Sonova (SOON.SW) 2022; parent private",
    },
    "Shark": {
        "ticker": "SN",
        "parent_company": "SharkNinja Inc.",
        "ownership": "public",
        "notes": "NYSE; spun off from JS Global in 2023",
    },
    "Shokz": {
        "ticker": None,
        "parent_company": "Shenzhen Shokz Co. Ltd.",
        "ownership": "private",
        "notes": "Private; Chinese open-ear audio company",
    },
    "Stanley": {
        "ticker": None,
        "parent_company": "PMI Worldwide (HAVI Group)",
        "ownership": "private",
        "notes": "Stanley brand owned by PMI/HAVI; not related to Stanley B&D",
    },
    "Ultimate Ears": {
        "ticker": "LOGI",
        "parent_company": "Logitech International S.A.",
        "ownership": "subsidiary",
        "notes": "Ultimate Ears acquired by Logitech 2008",
    },
    "Vizio": {
        "ticker": None,
        "parent_company": "VIZIO Holding Corp.",
        "ownership": "private",
        "notes": "Was public (VZIO); acquired by Walmart 2024, delisted",
    },
    "eufy": {
        "ticker": None,
        "parent_company": "Anker Innovations Technology Co.",
        "ownership": "private",
        "notes": "eufy is an Anker brand; Anker trades on Shenzhen (300866.SZ)",
    },

    # === LOW FAMILIARITY (real) ===
    "1MORE": {
        "ticker": None,
        "parent_company": "Wanmo Acoustics Technology Co.",
        "ownership": "private",
        "notes": "Private; Chinese audio company backed by Xiaomi",
    },
    "Amazfit": {
        "ticker": None,
        "parent_company": "Zepp Health Corporation",
        "ownership": "public",
        "notes": "Zepp Health (ZEPP) on NYSE; Amazfit is consumer brand",
    },
    "Atreyu": {
        "ticker": None,
        "parent_company": "Atreyu Running LLC",
        "ownership": "private",
        "notes": "Private; small DTC running shoe brand",
    },
    "Bmax": {
        "ticker": None,
        "parent_company": "Bmax Technology Co.",
        "ownership": "private",
        "notes": "Private; Chinese mini-PC/laptop manufacturer",
    },
    "CHUWI": {
        "ticker": None,
        "parent_company": "Chuwi Innovation Ltd.",
        "ownership": "private",
        "notes": "Private; Chinese electronics manufacturer",
    },
    "Cleanblend": {
        "ticker": None,
        "parent_company": "Cleanblend LLC",
        "ownership": "private",
        "notes": "Private; small blender brand",
    },
    "EarFun": {
        "ticker": None,
        "parent_company": "EarFun Technology (Shenzhen) Co.",
        "ownership": "private",
        "notes": "Private; Chinese audio brand",
    },
    "Evergoods": {
        "ticker": None,
        "parent_company": "Evergoods LLC",
        "ownership": "private",
        "notes": "Private; small premium backpack brand",
    },
    "Fairphone": {
        "ticker": None,
        "parent_company": "Fairphone B.V.",
        "ownership": "private",
        "notes": "Private; Dutch ethical smartphone company",
    },
    "Flair": {
        "ticker": None,
        "parent_company": "Flair Espresso Inc.",
        "ownership": "private",
        "notes": "Private; manual espresso press brand",
    },
    "HiFiMAN": {
        "ticker": None,
        "parent_company": "HiFiMAN Electronics Corporation",
        "ownership": "private",
        "notes": "Private; audiophile headphone manufacturer",
    },
    "Hisense": {
        "ticker": "000921.SZ",
        "parent_company": "Hisense Visual Technology Co.",
        "ownership": "public",
        "notes": "Shenzhen Stock Exchange",
    },
    "Innocn": {
        "ticker": None,
        "parent_company": "Innocn Technology Co.",
        "ownership": "private",
        "notes": "Private; Chinese monitor brand",
    },
    "Inov-8": {
        "ticker": None,
        "parent_company": "Inov-8 Ltd.",
        "ownership": "private",
        "notes": "Private; UK trail running brand acquired by Descente 2015",
    },
    "Keychron": {
        "ticker": None,
        "parent_company": "Keychron Co.",
        "ownership": "private",
        "notes": "Private; mechanical keyboard brand",
    },
    "Nothing": {
        "ticker": None,
        "parent_company": "Nothing Technology Ltd.",
        "ownership": "private",
        "notes": "Private; venture-backed by GV and others",
    },
    "OM System": {
        "ticker": None,
        "parent_company": "OM Digital Solutions Corporation",
        "ownership": "private",
        "notes": "Private; spun off from Olympus (7733.T) in 2021",
    },
    "Oclean": {
        "ticker": None,
        "parent_company": "Oclean Intelligent Technology Co.",
        "ownership": "private",
        "notes": "Private; Xiaomi ecosystem toothbrush brand",
    },
    "Roborock": {
        "ticker": "688169.SS",
        "parent_company": "Beijing Roborock Technology Co.",
        "ownership": "public",
        "notes": "Shanghai STAR Market",
    },
    "Silicon Power": {
        "ticker": "5765.TWO",
        "parent_company": "Silicon Power Computer & Comm. Inc.",
        "ownership": "public",
        "notes": "Taipei Exchange (OTC)",
    },
    "SoundPEATS": {
        "ticker": None,
        "parent_company": "SoundPEATS Technology Co.",
        "ownership": "private",
        "notes": "Private; Chinese audio accessories brand",
    },
    "Soundcore": {
        "ticker": None,
        "parent_company": "Anker Innovations Technology Co.",
        "ownership": "private",
        "notes": "Soundcore is an Anker brand; Anker on Shenzhen (300866.SZ)",
    },
    "TCL": {
        "ticker": "000100.SZ",
        "parent_company": "TCL Technology Group Corporation",
        "ownership": "public",
        "notes": "Shenzhen Stock Exchange",
    },
    "TOZO": {
        "ticker": None,
        "parent_company": "TOZO Inc.",
        "ownership": "private",
        "notes": "Private; budget wireless earbuds brand",
    },
    "TP-Link": {
        "ticker": None,
        "parent_company": "TP-Link Technologies Co.",
        "ownership": "private",
        "notes": "Private; Chinese networking equipment company",
    },
    "Teclast": {
        "ticker": None,
        "parent_company": "Teclast Electronics Co.",
        "ownership": "private",
        "notes": "Private; Chinese tablet/laptop manufacturer",
    },
    "ThermoFlask": {
        "ticker": None,
        "parent_company": "ThermoFlask (Takeya USA)",
        "ownership": "private",
        "notes": "Private; owned by Takeya USA",
    },
    "Topo Athletic": {
        "ticker": None,
        "parent_company": "Topo Athletic Inc.",
        "ownership": "private",
        "notes": "Private; small natural running shoe brand",
    },
    "Tribit": {
        "ticker": None,
        "parent_company": "Tribit Technology Co.",
        "ownership": "private",
        "notes": "Private; Chinese portable speaker brand",
    },
    "Varia": {
        "ticker": None,
        "parent_company": "Varia Brewing Inc.",
        "ownership": "private",
        "notes": "Private; specialty coffee grinder brand",
    },
    "Wacaco": {
        "ticker": None,
        "parent_company": "Wacaco Company Ltd.",
        "ownership": "private",
        "notes": "Private; portable espresso brand (Hong Kong)",
    },
    "Xiaomi": {
        "ticker": "1810.HK",
        "parent_company": "Xiaomi Corporation",
        "ownership": "public",
        "notes": "Hong Kong Stock Exchange",
    },
}

# Fictional brands (all get NaN financials)
FICTIONAL_BRANDS = [
    "Arcwave", "Auralis", "Aurem", "Blendwell", "Brevara", "Chronex",
    "Cleanpath", "Dentara", "Ethicom", "Keystrike", "Lumivue", "Netweave",
    "Novatech", "Optivex", "Pixelight", "Portabrew", "Presswell",
    "Primebook", "Sonance", "Sonaray", "Sonique", "Stridewell", "Swiftform",
    "Terravolt", "Thermalux", "Trailpeak", "Vaultdrive", "Veridian",
    "Vistara", "Vynex", "Wavecrest", "Zentria",
]

# Tickers that map to the same parent (deduplicate API calls)
# We query each unique ticker only once, then map results back to brands.


# ---------------------------------------------------------------------------
# Data Collection
# ---------------------------------------------------------------------------

def get_financial_data(ticker: str) -> dict:
    """
    Fetch financial data for a single ticker using yfinance.

    Returns a dict with market_cap, revenue, pe_ratio, sector, currency,
    and exchange. All values may be None/NaN on failure.
    """
    import yfinance as yf

    result = {
        "market_cap": None,
        "revenue": None,
        "pe_ratio": None,
        "sector": None,
        "currency": None,
        "exchange": None,
        "fetch_success": False,
    }

    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        if not info or info.get("regularMarketPrice") is None:
            # yfinance sometimes returns empty info for delisted/invalid tickers
            logger.warning(f"  {ticker}: no data returned (may be delisted or invalid)")
            return result

        result["market_cap"] = info.get("marketCap")
        result["revenue"] = info.get("totalRevenue")
        result["pe_ratio"] = info.get("trailingPE")
        result["sector"] = info.get("sector", "")
        result["currency"] = info.get("currency", "")
        result["exchange"] = info.get("exchange", "")
        result["fetch_success"] = True

    except Exception as e:
        logger.warning(f"  {ticker}: error fetching data: {e}")

    return result


def collect_all(dry_run: bool = False) -> list[dict]:
    """
    Collect financial data for all brands.

    Deduplicates tickers so each parent company is only queried once,
    then maps results back to individual brands.
    """
    # Step 1: Build unique ticker set
    ticker_data_cache = {}  # ticker -> financial data dict
    unique_tickers = set()
    for brand, info in BRAND_TICKER_MAP.items():
        if info["ticker"] is not None:
            unique_tickers.add(info["ticker"])

    logger.info(
        f"Collecting data for {len(unique_tickers)} unique tickers "
        f"({len(BRAND_TICKER_MAP)} brands)..."
    )

    if not dry_run:
        import yfinance as yf  # noqa: F811 -- ensure import works before loop

    # Step 2: Fetch each unique ticker
    for i, ticker in enumerate(sorted(unique_tickers), 1):
        if dry_run:
            logger.info(f"  [{i}/{len(unique_tickers)}] [DRY RUN] Would fetch: {ticker}")
            ticker_data_cache[ticker] = {
                "market_cap": 0, "revenue": 0, "pe_ratio": 0,
                "sector": "n/a", "currency": "n/a", "exchange": "n/a",
                "fetch_success": False,
            }
            continue

        logger.info(f"  [{i}/{len(unique_tickers)}] Fetching {ticker}...")
        data = get_financial_data(ticker)
        ticker_data_cache[ticker] = data

        if data["fetch_success"]:
            mc = data["market_cap"]
            mc_str = f"${mc / 1e9:.1f}B" if mc and mc > 0 else "n/a"
            rev = data["revenue"]
            rev_str = f"${rev / 1e9:.1f}B" if rev and rev > 0 else "n/a"
            pe = data["pe_ratio"]
            pe_str = f"{pe:.1f}" if pe else "n/a"
            logger.info(f"    Market cap: {mc_str}, Revenue: {rev_str}, P/E: {pe_str}")
        else:
            logger.warning(f"    Failed to fetch data for {ticker}")

        time.sleep(REQUEST_DELAY)

    # Step 3: Map ticker data back to brands
    results = []

    # Real brands
    for brand in sorted(BRAND_TICKER_MAP.keys()):
        info = BRAND_TICKER_MAP[brand]
        ticker = info["ticker"]

        if ticker and ticker in ticker_data_cache:
            fin = ticker_data_cache[ticker]
            results.append({
                "brand": brand,
                "is_fictional": False,
                "ticker": ticker,
                "parent_company": info["parent_company"],
                "ownership": info["ownership"],
                "market_cap": fin["market_cap"],
                "revenue": fin["revenue"],
                "pe_ratio": fin["pe_ratio"],
                "sector": fin["sector"] or "",
                "currency": fin["currency"] or "",
                "exchange": fin["exchange"] or "",
                "fetch_success": fin["fetch_success"],
                "notes": info["notes"],
            })
        else:
            # Private company or no ticker
            results.append({
                "brand": brand,
                "is_fictional": False,
                "ticker": "",
                "parent_company": info["parent_company"],
                "ownership": info["ownership"],
                "market_cap": None,
                "revenue": None,
                "pe_ratio": None,
                "sector": "",
                "currency": "",
                "exchange": "",
                "fetch_success": False,
                "notes": info["notes"],
            })

    # Fictional brands
    for brand in sorted(FICTIONAL_BRANDS):
        results.append({
            "brand": brand,
            "is_fictional": True,
            "ticker": "",
            "parent_company": "fictional",
            "ownership": "fictional",
            "market_cap": None,
            "revenue": None,
            "pe_ratio": None,
            "sector": "",
            "currency": "",
            "exchange": "",
            "fetch_success": False,
            "notes": "Fictional brand created for experiment",
        })

    return results


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def write_csv(results: list[dict]) -> None:
    """Write results to CSV."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "brand", "is_fictional", "ticker", "parent_company", "ownership",
        "market_cap", "revenue", "pe_ratio", "sector", "currency",
        "exchange", "fetch_success", "notes",
    ]

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in results:
            # Convert None to empty string for CSV
            csv_row = {}
            for k, v in row.items():
                if v is None:
                    csv_row[k] = ""
                else:
                    csv_row[k] = v
            writer.writerow(csv_row)

    logger.info(f"Saved {len(results)} brands to {OUTPUT_CSV}")


def print_summary(results: list[dict]) -> None:
    """Print summary statistics."""
    real = [r for r in results if not r["is_fictional"]]
    fictional = [r for r in results if r["is_fictional"]]
    public = [r for r in real if r["ownership"] == "public"]
    subsidiary = [r for r in real if r["ownership"] == "subsidiary"]
    private = [r for r in real if r["ownership"] == "private"]
    fetched = [r for r in real if r["fetch_success"]]

    logger.info(f"\nSummary:")
    logger.info(f"  Real brands: {len(real)}")
    logger.info(f"    Public:     {len(public)}")
    logger.info(f"    Subsidiary: {len(subsidiary)}")
    logger.info(f"    Private:    {len(private)}")
    logger.info(f"  Fictional brands: {len(fictional)}")
    logger.info(f"  Successfully fetched: {len(fetched)} / {len(real)}")

    # Top 10 by market cap
    with_cap = [
        r for r in fetched
        if r["market_cap"] is not None and r["market_cap"] > 0
    ]
    if with_cap:
        by_cap = sorted(with_cap, key=lambda x: x["market_cap"], reverse=True)
        logger.info(f"\n  Top 10 by market cap:")
        for r in by_cap[:10]:
            mc = r["market_cap"] / 1e9
            logger.info(
                f"    {r['brand']:20s}  {r['ticker']:12s}  "
                f"${mc:>8.1f}B  ({r['ownership']})"
            )

        logger.info(f"\n  Bottom 5 by market cap:")
        for r in by_cap[-5:]:
            mc = r["market_cap"] / 1e9
            logger.info(
                f"    {r['brand']:20s}  {r['ticker']:12s}  "
                f"${mc:>8.1f}B  ({r['ownership']})"
            )

    # Ownership distribution
    logger.info(f"\n  Unique tickers queried: {len(set(r['ticker'] for r in real if r['ticker']))}")
    logger.info(
        f"  Brands sharing a parent ticker: "
        f"{len([r for r in real if r['ownership'] == 'subsidiary'])}"
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Collect market cap and financial data for spec-resistance brands."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be fetched without making API calls.",
    )
    args = parser.parse_args()

    logger.info("=" * 70)
    logger.info("Market Data Collector for Spec-Resistance Project")
    logger.info("=" * 70)

    if args.dry_run:
        logger.info("DRY RUN MODE: No API calls will be made.")

    results = collect_all(dry_run=args.dry_run)

    write_csv(results)
    print_summary(results)

    logger.info("\nDone.")


if __name__ == "__main__":
    main()
