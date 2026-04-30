"""
Brand Frequency Scanner for Spec-Resistance Project
=====================================================
Queries the infini-gram API to measure training-data frequency for all
brand names used in the 20 product-category assortments. This supports
the argument that LLMs' brand bias is driven by differential exposure
during pre-training rather than any notion of "quality learning."

Query types:
  1. Brand name variants alone (e.g., "De'Longhi", "DeLonghi")
  2. Brand + category keyword (e.g., "Sony headphones")
  3. Brand + "review" (e.g., "Sony review") -- sentiment context
  4. Brand + "best" (e.g., "Sony best") -- recommendation context
  5. Brand + "vs" (e.g., "Sony vs") -- comparison context

Secondary data source: Google Trends (via pytrends) for real-time
search interest as a complement to static training-data frequency.

Output:
  data/brand_frequencies.csv      (infini-gram counts)
  data/brand_google_trends.csv    (Google Trends interest)

Usage:
    python scripts/brand_frequency_scanner.py [--dry-run] [--resume]
    python scripts/brand_frequency_scanner.py --test
    python scripts/brand_frequency_scanner.py --trends-only
"""

import csv
import json
import os
import sys
import time
import argparse
import logging
from pathlib import Path
from typing import Optional

import requests

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent  # spec-resistance/
OUTPUT_DIR = SCRIPT_DIR.parent / "data"
OUTPUT_CSV = OUTPUT_DIR / "brand_frequencies.csv"
TRENDS_CSV = OUTPUT_DIR / "brand_google_trends.csv"
CHECKPOINT_FILE = OUTPUT_DIR / "brand_scan_checkpoint.json"

# Infini-gram API
API_URL = "https://api.infini-gram.io/"
CORPORA = {
    "RedPajama": "v4_rpj_llama_s4",
    "Dolma": "v4_dolma-v1_7_llama",
    "Pile": "v4_piletrain_llama",
    "C4": "v4_c4train_llama",
}

# Context suffixes for sentiment/comparison queries
CONTEXT_SUFFIXES = ["review", "best", "vs"]

# Rate limiting: be polite to the API
REQUEST_DELAY = 0.5  # seconds between requests
MAX_RETRIES = 3
RETRY_BACKOFF = 2.0  # exponential backoff multiplier

# Google Trends settings
TRENDS_BATCH_SIZE = 5  # pytrends allows max 5 keywords per request
TRENDS_DELAY = 2.0  # seconds between Google Trends requests (stricter rate limit)

# ---------------------------------------------------------------------------
# Brand Database (extracted from experiment/assortments.py)
# ---------------------------------------------------------------------------
# Each entry: brand_name, familiarity_tier, categories, is_fictional,
#             spelling_variants

BRAND_DATABASE = [
    # === HIGH FAMILIARITY (real, well-known) ===
    {"brand": "Adidas", "familiarity": "high", "categories": ["running_shoes"], "is_fictional": False,
     "variants": ["Adidas", "adidas", "ADIDAS"]},
    {"brand": "Apple", "familiarity": "high", "categories": ["laptops", "smartphones", "smartwatches", "tablets", "wireless_earbuds"], "is_fictional": False,
     "variants": ["Apple", "apple", "APPLE"]},
    {"brand": "Beats", "familiarity": "high", "categories": ["headphones", "wireless_earbuds"], "is_fictional": False,
     "variants": ["Beats", "Beats by Dre", "Beats by Dr. Dre"]},
    {"brand": "Bose", "familiarity": "high", "categories": ["headphones", "portable_speakers"], "is_fictional": False,
     "variants": ["Bose", "BOSE", "bose"]},
    {"brand": "Canon", "familiarity": "high", "categories": ["cameras"], "is_fictional": False,
     "variants": ["Canon", "CANON", "canon"]},
    {"brand": "De'Longhi", "familiarity": "high", "categories": ["coffee_makers"], "is_fictional": False,
     "variants": ["De'Longhi", "DeLonghi", "de longhi", "Delonghi", "De Longhi"]},
    {"brand": "Dell", "familiarity": "high", "categories": ["laptops", "monitors"], "is_fictional": False,
     "variants": ["Dell", "DELL", "dell"]},
    {"brand": "Dyson", "familiarity": "high", "categories": ["robot_vacuums"], "is_fictional": False,
     "variants": ["Dyson", "dyson", "DYSON"]},
    {"brand": "Google", "familiarity": "high", "categories": ["smartphones", "wireless_earbuds", "wireless_routers"], "is_fictional": False,
     "variants": ["Google Pixel", "Google Nest"]},  # "Google" alone too ambiguous
    {"brand": "HP", "familiarity": "high", "categories": ["laptops"], "is_fictional": False,
     "variants": ["HP", "Hewlett-Packard", "Hewlett Packard", "HP Pavilion", "HP Envy"]},
    {"brand": "Hydro Flask", "familiarity": "high", "categories": ["water_bottles"], "is_fictional": False,
     "variants": ["Hydro Flask", "HydroFlask", "Hydroflask", "hydro flask"]},
    {"brand": "JanSport", "familiarity": "high", "categories": ["backpacks"], "is_fictional": False,
     "variants": ["JanSport", "Jansport", "JANSPORT", "jansport"]},
    {"brand": "Keurig", "familiarity": "high", "categories": ["coffee_makers"], "is_fictional": False,
     "variants": ["Keurig", "keurig", "KEURIG"]},
    {"brand": "KitchenAid", "familiarity": "high", "categories": ["blenders"], "is_fictional": False,
     "variants": ["KitchenAid", "Kitchen Aid", "Kitchenaid", "kitchenaid"]},
    {"brand": "LG", "familiarity": "high", "categories": ["monitors", "tvs"], "is_fictional": False,
     "variants": ["LG", "LG Electronics"]},
    {"brand": "Lenovo", "familiarity": "high", "categories": ["laptops", "tablets"], "is_fictional": False,
     "variants": ["Lenovo", "LENOVO", "lenovo"]},
    {"brand": "Logitech", "familiarity": "high", "categories": ["keyboards"], "is_fictional": False,
     "variants": ["Logitech", "logitech", "LOGITECH"]},
    {"brand": "Mr. Coffee", "familiarity": "high", "categories": ["coffee_makers"], "is_fictional": False,
     "variants": ["Mr. Coffee", "Mr Coffee", "mr. coffee", "mr coffee"]},
    {"brand": "Nespresso", "familiarity": "high", "categories": ["coffee_makers"], "is_fictional": False,
     "variants": ["Nespresso", "nespresso", "NESPRESSO"]},
    {"brand": "Netgear", "familiarity": "high", "categories": ["wireless_routers"], "is_fictional": False,
     "variants": ["Netgear", "NETGEAR", "netgear"]},
    {"brand": "Nike", "familiarity": "high", "categories": ["running_shoes"], "is_fictional": False,
     "variants": ["Nike", "NIKE", "nike"]},
    {"brand": "Nikon", "familiarity": "high", "categories": ["cameras"], "is_fictional": False,
     "variants": ["Nikon", "NIKON", "nikon"]},
    {"brand": "Ninja", "familiarity": "high", "categories": ["blenders"], "is_fictional": False,
     "variants": ["Ninja", "Ninja blender", "Ninja Professional"]},
    {"brand": "Oral-B", "familiarity": "high", "categories": ["electric_toothbrushes"], "is_fictional": False,
     "variants": ["Oral-B", "Oral B", "OralB", "oral-b"]},
    {"brand": "Philips", "familiarity": "high", "categories": ["coffee_makers", "electric_toothbrushes"], "is_fictional": False,
     "variants": ["Philips", "PHILIPS", "philips", "Philips Sonicare"]},
    {"brand": "Razer", "familiarity": "high", "categories": ["keyboards"], "is_fictional": False,
     "variants": ["Razer", "RAZER", "razer"]},
    {"brand": "Samsung", "familiarity": "high", "categories": ["external_ssds", "monitors", "smartphones", "smartwatches", "tablets", "tvs", "wireless_earbuds"], "is_fictional": False,
     "variants": ["Samsung", "SAMSUNG", "samsung"]},
    {"brand": "SanDisk", "familiarity": "high", "categories": ["external_ssds"], "is_fictional": False,
     "variants": ["SanDisk", "Sandisk", "SANDISK", "sandisk"]},
    {"brand": "Seagate", "familiarity": "high", "categories": ["external_ssds"], "is_fictional": False,
     "variants": ["Seagate", "SEAGATE", "seagate"]},
    {"brand": "Sony", "familiarity": "high", "categories": ["cameras", "headphones", "portable_speakers", "tvs", "wireless_earbuds"], "is_fictional": False,
     "variants": ["Sony", "SONY", "sony"]},
    {"brand": "The North Face", "familiarity": "high", "categories": ["backpacks"], "is_fictional": False,
     "variants": ["The North Face", "North Face", "TNF", "the north face"]},
    {"brand": "Vitamix", "familiarity": "high", "categories": ["blenders"], "is_fictional": False,
     "variants": ["Vitamix", "vitamix", "VITAMIX"]},
    {"brand": "Western Digital", "familiarity": "high", "categories": ["external_ssds"], "is_fictional": False,
     "variants": ["Western Digital", "WD", "western digital"]},
    {"brand": "Yeti", "familiarity": "high", "categories": ["water_bottles"], "is_fictional": False,
     "variants": ["Yeti", "YETI", "yeti"]},
    {"brand": "iRobot", "familiarity": "high", "categories": ["robot_vacuums"], "is_fictional": False,
     "variants": ["iRobot", "Irobot", "iRobot Roomba", "Roomba"]},

    # === MEDIUM FAMILIARITY (real, moderately known) ===
    {"brand": "ASICS", "familiarity": "medium", "categories": ["running_shoes"], "is_fictional": False,
     "variants": ["ASICS", "Asics", "asics"]},
    {"brand": "ASUS", "familiarity": "medium", "categories": ["laptops", "monitors", "wireless_routers"], "is_fictional": False,
     "variants": ["ASUS", "Asus", "asus"]},
    {"brand": "Acer", "familiarity": "medium", "categories": ["laptops"], "is_fictional": False,
     "variants": ["Acer", "ACER", "acer"]},
    {"brand": "AeroPress", "familiarity": "medium", "categories": ["coffee_makers"], "is_fictional": False,
     "variants": ["AeroPress", "Aeropress", "aeropress", "Aero Press"]},
    {"brand": "Amazon", "familiarity": "medium", "categories": ["tablets"], "is_fictional": False,
     "variants": ["Amazon Fire", "Amazon tablet", "Fire HD"]},  # "Amazon" alone too ambiguous
    {"brand": "Audio-Technica", "familiarity": "medium", "categories": ["headphones"], "is_fictional": False,
     "variants": ["Audio-Technica", "Audio Technica", "audio-technica", "AudioTechnica"]},
    {"brand": "Beyerdynamic", "familiarity": "medium", "categories": ["headphones"], "is_fictional": False,
     "variants": ["Beyerdynamic", "beyerdynamic", "Beyer Dynamic", "beyer dynamic"]},
    {"brand": "Breville", "familiarity": "medium", "categories": ["coffee_makers"], "is_fictional": False,
     "variants": ["Breville", "breville", "BREVILLE"]},
    {"brand": "Brooks", "familiarity": "medium", "categories": ["running_shoes"], "is_fictional": False,
     "variants": ["Brooks Running", "Brooks shoes"]},  # "Brooks" alone ambiguous
    {"brand": "CamelBak", "familiarity": "medium", "categories": ["water_bottles"], "is_fictional": False,
     "variants": ["CamelBak", "Camelbak", "camelbak", "Camel Bak"]},
    {"brand": "Corsair", "familiarity": "medium", "categories": ["keyboards"], "is_fictional": False,
     "variants": ["Corsair", "CORSAIR", "corsair"]},
    {"brand": "Cuisinart", "familiarity": "medium", "categories": ["coffee_makers"], "is_fictional": False,
     "variants": ["Cuisinart", "cuisinart", "CUISINART"]},
    {"brand": "Fitbit", "familiarity": "medium", "categories": ["smartwatches"], "is_fictional": False,
     "variants": ["Fitbit", "fitbit", "FITBIT"]},
    {"brand": "Fujifilm", "familiarity": "medium", "categories": ["cameras"], "is_fictional": False,
     "variants": ["Fujifilm", "Fuji", "fujifilm", "FUJIFILM"]},
    {"brand": "Garmin", "familiarity": "medium", "categories": ["smartwatches"], "is_fictional": False,
     "variants": ["Garmin", "GARMIN", "garmin"]},
    {"brand": "HOKA", "familiarity": "medium", "categories": ["running_shoes"], "is_fictional": False,
     "variants": ["HOKA", "Hoka", "hoka", "Hoka One One", "HOKA ONE ONE"]},
    {"brand": "Hamilton Beach", "familiarity": "medium", "categories": ["blenders"], "is_fictional": False,
     "variants": ["Hamilton Beach", "hamilton beach", "Hamilton beach"]},
    {"brand": "Herschel", "familiarity": "medium", "categories": ["backpacks"], "is_fictional": False,
     "variants": ["Herschel", "Herschel Supply", "herschel"]},
    {"brand": "HyperX", "familiarity": "medium", "categories": ["keyboards"], "is_fictional": False,
     "variants": ["HyperX", "Hyperx", "hyperx", "hyper x"]},
    {"brand": "Insignia", "familiarity": "medium", "categories": ["tvs"], "is_fictional": False,
     "variants": ["Insignia", "insignia"]},
    {"brand": "JBL", "familiarity": "medium", "categories": ["headphones", "portable_speakers", "wireless_earbuds"], "is_fictional": False,
     "variants": ["JBL", "jbl"]},
    {"brand": "Jabra", "familiarity": "medium", "categories": ["wireless_earbuds"], "is_fictional": False,
     "variants": ["Jabra", "jabra", "JABRA"]},
    {"brand": "Linksys", "familiarity": "medium", "categories": ["wireless_routers"], "is_fictional": False,
     "variants": ["Linksys", "linksys", "LINKSYS"]},
    {"brand": "Motorola", "familiarity": "medium", "categories": ["smartphones"], "is_fictional": False,
     "variants": ["Motorola", "motorola", "MOTOROLA", "Moto"]},
    {"brand": "New Balance", "familiarity": "medium", "categories": ["running_shoes"], "is_fictional": False,
     "variants": ["New Balance", "new balance", "New balance"]},
    {"brand": "OnePlus", "familiarity": "medium", "categories": ["smartphones"], "is_fictional": False,
     "variants": ["OnePlus", "Oneplus", "oneplus", "One Plus", "one plus"]},
    {"brand": "Osprey", "familiarity": "medium", "categories": ["backpacks"], "is_fictional": False,
     "variants": ["Osprey", "osprey", "Osprey Packs"]},
    {"brand": "Quip", "familiarity": "medium", "categories": ["electric_toothbrushes"], "is_fictional": False,
     "variants": ["Quip", "quip"]},
    {"brand": "S'well", "familiarity": "medium", "categories": ["water_bottles"], "is_fictional": False,
     "variants": ["S'well", "Swell", "S'Well", "swell bottle"]},
    {"brand": "Salomon", "familiarity": "medium", "categories": ["running_shoes"], "is_fictional": False,
     "variants": ["Salomon", "salomon", "SALOMON"]},
    {"brand": "Saucony", "familiarity": "medium", "categories": ["running_shoes"], "is_fictional": False,
     "variants": ["Saucony", "saucony", "SAUCONY"]},
    {"brand": "Sennheiser", "familiarity": "medium", "categories": ["headphones"], "is_fictional": False,
     "variants": ["Sennheiser", "sennheiser", "SENNHEISER"]},
    {"brand": "Shark", "familiarity": "medium", "categories": ["robot_vacuums"], "is_fictional": False,
     "variants": ["Shark", "Shark robot", "Shark vacuum"]},
    {"brand": "Shokz", "familiarity": "medium", "categories": ["wireless_earbuds"], "is_fictional": False,
     "variants": ["Shokz", "shokz", "AfterShokz", "Aftershokz"]},
    {"brand": "Stanley", "familiarity": "medium", "categories": ["coffee_makers"], "is_fictional": False,
     "variants": ["Stanley", "Stanley cup", "Stanley thermos"]},  # Note: "Stanley" alone is ambiguous
    {"brand": "Ultimate Ears", "familiarity": "medium", "categories": ["portable_speakers"], "is_fictional": False,
     "variants": ["Ultimate Ears", "UE", "ultimate ears", "UE Boom"]},
    {"brand": "Vizio", "familiarity": "medium", "categories": ["tvs"], "is_fictional": False,
     "variants": ["Vizio", "VIZIO", "vizio"]},
    {"brand": "eufy", "familiarity": "medium", "categories": ["robot_vacuums"], "is_fictional": False,
     "variants": ["eufy", "Eufy", "EUFY"]},

    # === LOW FAMILIARITY (real, lesser-known) ===
    {"brand": "1MORE", "familiarity": "low", "categories": ["wireless_earbuds"], "is_fictional": False,
     "variants": ["1MORE", "1more", "1 MORE"]},
    {"brand": "Amazfit", "familiarity": "low", "categories": ["smartwatches"], "is_fictional": False,
     "variants": ["Amazfit", "amazfit", "AMAZFIT"]},
    {"brand": "Atreyu", "familiarity": "low", "categories": ["running_shoes"], "is_fictional": False,
     "variants": ["Atreyu", "Atreyu Running", "atreyu"]},
    {"brand": "Bmax", "familiarity": "low", "categories": ["laptops"], "is_fictional": False,
     "variants": ["Bmax", "BMAX", "bmax"]},
    {"brand": "CHUWI", "familiarity": "low", "categories": ["laptops"], "is_fictional": False,
     "variants": ["CHUWI", "Chuwi", "chuwi"]},
    {"brand": "Cleanblend", "familiarity": "low", "categories": ["blenders"], "is_fictional": False,
     "variants": ["Cleanblend", "cleanblend", "Clean Blend"]},
    {"brand": "EarFun", "familiarity": "low", "categories": ["wireless_earbuds"], "is_fictional": False,
     "variants": ["EarFun", "Earfun", "earfun", "Ear Fun"]},
    {"brand": "Evergoods", "familiarity": "low", "categories": ["backpacks"], "is_fictional": False,
     "variants": ["Evergoods", "evergoods", "EVERGOODS"]},
    {"brand": "Fairphone", "familiarity": "low", "categories": ["smartphones"], "is_fictional": False,
     "variants": ["Fairphone", "fairphone", "Fair Phone"]},
    {"brand": "Flair", "familiarity": "low", "categories": ["coffee_makers"], "is_fictional": False,
     "variants": ["Flair Espresso", "Flair espresso", "Flair coffee"]},  # "Flair" alone ambiguous
    {"brand": "HiFiMAN", "familiarity": "low", "categories": ["headphones"], "is_fictional": False,
     "variants": ["HiFiMAN", "Hifiman", "hifiman", "HiFi Man", "HIFIMAN"]},
    {"brand": "Hisense", "familiarity": "low", "categories": ["tvs"], "is_fictional": False,
     "variants": ["Hisense", "hisense", "HISENSE"]},
    {"brand": "Innocn", "familiarity": "low", "categories": ["monitors"], "is_fictional": False,
     "variants": ["Innocn", "INNOCN", "innocn", "InnocN"]},
    {"brand": "Inov-8", "familiarity": "low", "categories": ["running_shoes"], "is_fictional": False,
     "variants": ["Inov-8", "inov-8", "Inov8", "inov8"]},
    {"brand": "Keychron", "familiarity": "low", "categories": ["keyboards"], "is_fictional": False,
     "variants": ["Keychron", "keychron", "KEYCHRON"]},
    {"brand": "Nothing", "familiarity": "low", "categories": ["smartphones"], "is_fictional": False,
     "variants": ["Nothing Phone", "Nothing phone", "Nothing smartphone"]},  # "Nothing" alone ambiguous
    {"brand": "OM System", "familiarity": "low", "categories": ["cameras"], "is_fictional": False,
     "variants": ["OM System", "OM SYSTEM", "om system", "Olympus OM System"]},
    {"brand": "Oclean", "familiarity": "low", "categories": ["electric_toothbrushes"], "is_fictional": False,
     "variants": ["Oclean", "oclean", "OCLEAN"]},
    {"brand": "Roborock", "familiarity": "low", "categories": ["robot_vacuums"], "is_fictional": False,
     "variants": ["Roborock", "roborock", "ROBOROCK"]},
    {"brand": "Silicon Power", "familiarity": "low", "categories": ["external_ssds"], "is_fictional": False,
     "variants": ["Silicon Power", "silicon power", "SP"]},
    {"brand": "SoundPEATS", "familiarity": "low", "categories": ["wireless_earbuds"], "is_fictional": False,
     "variants": ["SoundPEATS", "Soundpeats", "soundpeats", "Sound PEATS"]},
    {"brand": "Soundcore", "familiarity": "low", "categories": ["headphones"], "is_fictional": False,
     "variants": ["Soundcore", "soundcore", "Anker Soundcore"]},
    {"brand": "TCL", "familiarity": "low", "categories": ["tvs"], "is_fictional": False,
     "variants": ["TCL", "tcl"]},
    {"brand": "TOZO", "familiarity": "low", "categories": ["wireless_earbuds"], "is_fictional": False,
     "variants": ["TOZO", "Tozo", "tozo"]},
    {"brand": "TP-Link", "familiarity": "low", "categories": ["wireless_routers"], "is_fictional": False,
     "variants": ["TP-Link", "TP Link", "tp-link", "TPLink", "tplink"]},
    {"brand": "Teclast", "familiarity": "low", "categories": ["laptops"], "is_fictional": False,
     "variants": ["Teclast", "teclast", "TECLAST"]},
    {"brand": "ThermoFlask", "familiarity": "low", "categories": ["water_bottles"], "is_fictional": False,
     "variants": ["ThermoFlask", "Thermoflask", "thermoflask", "Thermo Flask"]},
    {"brand": "Topo Athletic", "familiarity": "low", "categories": ["running_shoes"], "is_fictional": False,
     "variants": ["Topo Athletic", "topo athletic", "Topo"]},
    {"brand": "Tribit", "familiarity": "low", "categories": ["portable_speakers"], "is_fictional": False,
     "variants": ["Tribit", "tribit", "TRIBIT"]},
    {"brand": "Varia", "familiarity": "low", "categories": ["coffee_makers"], "is_fictional": False,
     "variants": ["Varia coffee", "Varia brewer"]},  # "Varia" alone ambiguous
    {"brand": "Wacaco", "familiarity": "low", "categories": ["coffee_makers"], "is_fictional": False,
     "variants": ["Wacaco", "wacaco", "WACACO", "Wacaco Nanopresso"]},
    {"brand": "Xiaomi", "familiarity": "low", "categories": ["smartwatches"], "is_fictional": False,
     "variants": ["Xiaomi", "xiaomi", "XIAOMI"]},

    # === LOW FAMILIARITY (fictional, created for experiment) ===
    {"brand": "Arcwave", "familiarity": "low", "categories": ["headphones"], "is_fictional": True,
     "variants": ["Arcwave", "arcwave", "ArcWave"]},
    {"brand": "Auralis", "familiarity": "low", "categories": ["wireless_earbuds"], "is_fictional": True,
     "variants": ["Auralis", "auralis", "AURALIS"]},
    {"brand": "Aurem", "familiarity": "low", "categories": ["smartphones", "tablets"], "is_fictional": True,
     "variants": ["Aurem", "aurem", "AUREM"]},
    {"brand": "Blendwell", "familiarity": "low", "categories": ["blenders"], "is_fictional": True,
     "variants": ["Blendwell", "BlendWell", "blendwell", "Blend Well"]},
    {"brand": "Brevara", "familiarity": "low", "categories": ["coffee_makers"], "is_fictional": True,
     "variants": ["Brevara", "brevara", "BREVARA"]},
    {"brand": "Chronex", "familiarity": "low", "categories": ["smartwatches"], "is_fictional": True,
     "variants": ["Chronex", "chronex", "CHRONEX"]},
    {"brand": "Cleanpath", "familiarity": "low", "categories": ["robot_vacuums"], "is_fictional": True,
     "variants": ["Cleanpath", "CleanPath", "cleanpath", "Clean Path"]},
    {"brand": "Dentara", "familiarity": "low", "categories": ["electric_toothbrushes"], "is_fictional": True,
     "variants": ["Dentara", "dentara", "DENTARA"]},
    {"brand": "Ethicom", "familiarity": "low", "categories": ["smartphones"], "is_fictional": True,
     "variants": ["Ethicom", "ethicom", "ETHICOM"]},
    {"brand": "Keystrike", "familiarity": "low", "categories": ["keyboards"], "is_fictional": True,
     "variants": ["Keystrike", "KeyStrike", "keystrike", "Key Strike"]},
    {"brand": "Lumivue", "familiarity": "low", "categories": ["monitors"], "is_fictional": True,
     "variants": ["Lumivue", "LumiVue", "lumivue", "Lumi Vue"]},
    {"brand": "Netweave", "familiarity": "low", "categories": ["wireless_routers"], "is_fictional": True,
     "variants": ["Netweave", "NetWeave", "netweave", "Net Weave"]},
    {"brand": "Novatech", "familiarity": "low", "categories": ["laptops"], "is_fictional": True,
     "variants": ["Novatech", "NovaTech", "novatech", "Nova Tech"]},
    {"brand": "Optivex", "familiarity": "low", "categories": ["cameras"], "is_fictional": True,
     "variants": ["Optivex", "OptiVex", "optivex", "Opti Vex"]},
    {"brand": "Pixelight", "familiarity": "low", "categories": ["tvs"], "is_fictional": True,
     "variants": ["Pixelight", "PixeLight", "pixelight", "Pixe Light"]},
    {"brand": "Portabrew", "familiarity": "low", "categories": ["coffee_makers"], "is_fictional": True,
     "variants": ["Portabrew", "PortaBrew", "portabrew", "Porta Brew"]},
    {"brand": "Presswell", "familiarity": "low", "categories": ["coffee_makers"], "is_fictional": True,
     "variants": ["Presswell", "PressWell", "presswell", "Press Well"]},
    {"brand": "Primebook", "familiarity": "low", "categories": ["laptops"], "is_fictional": True,
     "variants": ["Primebook", "PrimeBook", "primebook", "Prime Book"]},
    {"brand": "Sonance", "familiarity": "low", "categories": ["wireless_earbuds"], "is_fictional": True,
     "variants": ["Sonance", "sonance", "SONANCE"]},
    {"brand": "Sonaray", "familiarity": "low", "categories": ["headphones"], "is_fictional": True,
     "variants": ["Sonaray", "SonaRay", "sonaray", "Sona Ray"]},
    {"brand": "Sonique", "familiarity": "low", "categories": ["headphones"], "is_fictional": True,
     "variants": ["Sonique", "sonique", "SONIQUE"]},
    {"brand": "Stridewell", "familiarity": "low", "categories": ["running_shoes"], "is_fictional": True,
     "variants": ["Stridewell", "StrideWell", "stridewell", "Stride Well"]},
    {"brand": "Swiftform", "familiarity": "low", "categories": ["running_shoes"], "is_fictional": True,
     "variants": ["Swiftform", "SwiftForm", "swiftform", "Swift Form"]},
    {"brand": "Terravolt", "familiarity": "low", "categories": ["running_shoes"], "is_fictional": True,
     "variants": ["Terravolt", "TerraVolt", "terravolt", "Terra Volt"]},
    {"brand": "Thermalux", "familiarity": "low", "categories": ["water_bottles"], "is_fictional": True,
     "variants": ["Thermalux", "ThermaLux", "thermalux", "Therma Lux"]},
    {"brand": "Trailpeak", "familiarity": "low", "categories": ["backpacks"], "is_fictional": True,
     "variants": ["Trailpeak", "TrailPeak", "trailpeak", "Trail Peak"]},
    {"brand": "Vaultdrive", "familiarity": "low", "categories": ["external_ssds"], "is_fictional": True,
     "variants": ["Vaultdrive", "VaultDrive", "vaultdrive", "Vault Drive"]},
    {"brand": "Veridian", "familiarity": "low", "categories": ["smartphones"], "is_fictional": True,
     "variants": ["Veridian", "veridian", "VERIDIAN"]},
    {"brand": "Vistara", "familiarity": "low", "categories": ["tvs"], "is_fictional": True,
     "variants": ["Vistara", "vistara", "VISTARA"]},
    {"brand": "Vynex", "familiarity": "low", "categories": ["wireless_earbuds"], "is_fictional": True,
     "variants": ["Vynex", "vynex", "VYNEX"]},
    {"brand": "Wavecrest", "familiarity": "low", "categories": ["portable_speakers"], "is_fictional": True,
     "variants": ["Wavecrest", "WaveCrest", "wavecrest", "Wave Crest"]},
    {"brand": "Zentria", "familiarity": "low", "categories": ["laptops"], "is_fictional": True,
     "variants": ["Zentria", "zentria", "ZENTRIA"]},
]


# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(OUTPUT_DIR / "brand_scan.log", mode="a"),
    ],
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# API query functions
# ---------------------------------------------------------------------------

def query_infini_gram(query: str, index: str) -> Optional[int]:
    """
    Query the infini-gram API for n-gram count.

    Returns the raw count or None on failure.
    """
    payload = {
        "index": index,
        "query_type": "count",
        "query": query,
    }

    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.post(API_URL, json=payload, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("count", 0)
            elif resp.status_code == 429:
                wait = RETRY_BACKOFF ** (attempt + 1)
                logger.warning(f"Rate limited. Waiting {wait:.1f}s before retry.")
                time.sleep(wait)
            else:
                logger.warning(
                    f"API returned {resp.status_code} for '{query}' on {index}: "
                    f"{resp.text[:200]}"
                )
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_BACKOFF ** attempt)
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout querying '{query}' on {index} (attempt {attempt + 1})")
            time.sleep(RETRY_BACKOFF ** attempt)
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error for '{query}' on {index}: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_BACKOFF ** attempt)

    logger.error(f"Failed after {MAX_RETRIES} retries: '{query}' on {index}")
    return None


def build_query_list() -> list[dict]:
    """
    Build the full list of queries to run.

    For each brand, we query:
      1. Each spelling variant alone (e.g., "De'Longhi", "DeLonghi")
      2. Primary variant + category keyword (e.g., "Sony headphones")
      3. Primary variant + "review" (e.g., "Sony review")
      4. Primary variant + "best" (e.g., "Sony best")
      5. Primary variant + "vs" (e.g., "Sony vs")

    The context queries (3-5) capture how brands appear in recommendation,
    evaluation, and comparison text, which maps more directly to the kind
    of content that shapes LLM outputs than raw frequency alone.

    Returns list of dicts with keys: brand, variant, category, query_type,
    query, corpus, index
    """
    queries = []

    # Category display names for combined queries
    category_display = {
        "laptops": "laptop",
        "smartphones": "smartphone",
        "tvs": "TV",
        "cameras": "camera",
        "tablets": "tablet",
        "headphones": "headphones",
        "wireless_earbuds": "earbuds",
        "running_shoes": "running shoes",
        "smartwatches": "smartwatch",
        "robot_vacuums": "robot vacuum",
        "portable_speakers": "speaker",
        "keyboards": "keyboard",
        "external_ssds": "SSD",
        "water_bottles": "water bottle",
        "electric_toothbrushes": "toothbrush",
        "coffee_makers": "coffee",
        "blenders": "blender",
        "backpacks": "backpack",
        "wireless_routers": "router",
        "monitors": "monitor",
    }

    for brand_entry in BRAND_DATABASE:
        brand = brand_entry["brand"]
        categories = brand_entry["categories"]
        variants = brand_entry["variants"]

        for corpus_name, index_id in CORPORA.items():
            # 1. Query each spelling variant alone
            for variant in variants:
                queries.append({
                    "brand": brand,
                    "variant": variant,
                    "category": "all",  # brand-only query
                    "query_type": "brand_only",
                    "query": variant,
                    "corpus": corpus_name,
                    "index": index_id,
                })

            # 2. Query primary variant + category
            primary_variant = variants[0]  # Use canonical form
            for cat in categories:
                cat_label = category_display.get(cat, cat.replace("_", " "))
                combined_query = f"{primary_variant} {cat_label}"
                queries.append({
                    "brand": brand,
                    "variant": f"{primary_variant}+{cat_label}",
                    "category": cat,
                    "query_type": "brand_category",
                    "query": combined_query,
                    "corpus": corpus_name,
                    "index": index_id,
                })

            # 3. Context queries: brand + review/best/vs
            for suffix in CONTEXT_SUFFIXES:
                context_query = f"{primary_variant} {suffix}"
                queries.append({
                    "brand": brand,
                    "variant": f"{primary_variant}+{suffix}",
                    "category": "all",
                    "query_type": f"context_{suffix}",
                    "query": context_query,
                    "corpus": corpus_name,
                    "index": index_id,
                })

    return queries


# ---------------------------------------------------------------------------
# Checkpoint management
# ---------------------------------------------------------------------------

def load_checkpoint() -> set:
    """Load set of already-completed query keys from checkpoint."""
    if CHECKPOINT_FILE.exists():
        with open(CHECKPOINT_FILE, "r") as f:
            data = json.load(f)
        return set(data.get("completed", []))
    return set()


def save_checkpoint(completed: set):
    """Save completed query keys to checkpoint file."""
    with open(CHECKPOINT_FILE, "w") as f:
        json.dump({"completed": sorted(completed)}, f)


def query_key(q: dict) -> str:
    """Generate a unique key for a query."""
    return f"{q['brand']}|{q['variant']}|{q['corpus']}"


# ---------------------------------------------------------------------------
# Main scanning logic
# ---------------------------------------------------------------------------

def run_scan(dry_run: bool = False, resume: bool = False):
    """
    Execute the full scan across all brands, variants, and corpora.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    queries = build_query_list()
    logger.info(f"Total queries to execute: {len(queries)}")

    # Count breakdown
    n_brands = len(BRAND_DATABASE)
    n_real = sum(1 for b in BRAND_DATABASE if not b["is_fictional"])
    n_fictional = sum(1 for b in BRAND_DATABASE if b["is_fictional"])
    logger.info(
        f"Brands: {n_brands} total ({n_real} real, {n_fictional} fictional) "
        f"across {len(CORPORA)} corpora"
    )

    if dry_run:
        logger.info("DRY RUN: Showing first 20 queries:")
        for q in queries[:20]:
            logger.info(f"  [{q['corpus']}] {q['query']} (brand={q['brand']}, type={q['query_type']}, cat={q['category']})")
        logger.info(f"  ... and {len(queries) - 20} more")

        # Query type breakdown
        from collections import Counter
        type_counts = Counter(q["query_type"] for q in queries)
        logger.info("\nQuery type breakdown:")
        for qt, cnt in sorted(type_counts.items()):
            logger.info(f"  {qt}: {cnt}")

        logger.info(f"\nEstimated time at {REQUEST_DELAY}s/request: {len(queries) * REQUEST_DELAY / 60:.0f} minutes")
        return

    # Resume support
    completed = set()
    existing_rows = []
    if resume and OUTPUT_CSV.exists():
        completed = load_checkpoint()
        with open(OUTPUT_CSV, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            existing_rows = list(reader)
        logger.info(f"Resuming: {len(completed)} queries already completed")

    # Filter out completed queries
    remaining = [q for q in queries if query_key(q) not in completed]
    logger.info(f"Queries remaining: {len(remaining)}")

    if not remaining:
        logger.info("All queries already completed!")
        return

    # Prepare CSV
    fieldnames = [
        "brand_name", "variant", "corpus", "raw_count", "category",
        "query_type", "is_fictional", "familiarity_tier", "query_string",
    ]

    results = list(existing_rows)
    brand_lookup = {b["brand"]: b for b in BRAND_DATABASE}

    try:
        for i, q in enumerate(remaining):
            brand_info = brand_lookup[q["brand"]]

            logger.info(
                f"[{i+1}/{len(remaining)}] "
                f"Querying '{q['query']}' on {q['corpus']}..."
            )

            count = query_infini_gram(q["query"], q["index"])

            if count is not None:
                results.append({
                    "brand_name": q["brand"],
                    "variant": q["variant"],
                    "corpus": q["corpus"],
                    "raw_count": count,
                    "category": q["category"],
                    "query_type": q["query_type"],
                    "is_fictional": brand_info["is_fictional"],
                    "familiarity_tier": brand_info["familiarity"],
                    "query_string": q["query"],
                })

                completed.add(query_key(q))

                # Log notable results
                if count > 0:
                    logger.info(f"  -> count = {count:,}")
                else:
                    logger.info(f"  -> count = 0")
            else:
                results.append({
                    "brand_name": q["brand"],
                    "variant": q["variant"],
                    "corpus": q["corpus"],
                    "raw_count": -1,  # Sentinel for failed queries
                    "category": q["category"],
                    "query_type": q["query_type"],
                    "is_fictional": brand_info["is_fictional"],
                    "familiarity_tier": brand_info["familiarity"],
                    "query_string": q["query"],
                })

            # Rate limiting
            time.sleep(REQUEST_DELAY)

            # Periodic save (every 50 queries)
            if (i + 1) % 50 == 0:
                _write_csv(results, fieldnames)
                save_checkpoint(completed)
                logger.info(f"  [checkpoint saved at {i+1} queries]")

    except KeyboardInterrupt:
        logger.warning("Interrupted! Saving progress...")
    finally:
        _write_csv(results, fieldnames)
        save_checkpoint(completed)
        logger.info(f"Saved {len(results)} rows to {OUTPUT_CSV}")
        logger.info(f"Checkpoint saved: {len(completed)} completed queries")

    # Summary statistics
    _print_summary(results)


def _write_csv(results: list[dict], fieldnames: list[str]):
    """Write results to CSV."""
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)


def _is_fictional(val) -> bool:
    """Safely check is_fictional, handling both bool and string from CSV."""
    if isinstance(val, bool):
        return val
    return str(val).strip().lower() == "true"


def _print_summary(results: list[dict]):
    """Print summary statistics of the scan."""
    logger.info("\n" + "=" * 60)
    logger.info("SCAN SUMMARY")
    logger.info("=" * 60)

    # Count by familiarity tier (using brand-only, primary variant, RedPajama)
    tier_counts = {"high": [], "medium": [], "low": []}
    for r in results:
        query_type = r.get("query_type", "brand_only")
        if query_type == "brand_only" and r["corpus"] == "RedPajama":
            tier = r["familiarity_tier"]
            count = int(r["raw_count"]) if int(r["raw_count"]) >= 0 else 0
            tier_counts[tier].append((r["brand_name"], count))

    for tier in ["high", "medium", "low"]:
        brands = tier_counts[tier]
        if brands:
            counts = [c for _, c in brands]
            avg = sum(counts) / len(counts) if counts else 0
            logger.info(
                f"\n{tier.upper()} familiarity ({len(brands)} brands): "
                f"avg={avg:,.0f}, min={min(counts):,}, max={max(counts):,}"
            )
            # Top 5 by count
            for name, count in sorted(brands, key=lambda x: -x[1])[:5]:
                logger.info(f"  {name}: {count:,}")

    # Fictional vs real comparison
    fictional_counts = [
        int(r["raw_count"]) for r in results
        if r.get("query_type", "brand_only") == "brand_only"
        and r["corpus"] == "RedPajama"
        and _is_fictional(r["is_fictional"]) and int(r["raw_count"]) >= 0
    ]
    real_counts = [
        int(r["raw_count"]) for r in results
        if r.get("query_type", "brand_only") == "brand_only"
        and r["corpus"] == "RedPajama"
        and not _is_fictional(r["is_fictional"]) and int(r["raw_count"]) >= 0
    ]

    if fictional_counts:
        logger.info(
            f"\nFictional brands: avg={sum(fictional_counts)/len(fictional_counts):,.0f}, "
            f"median={sorted(fictional_counts)[len(fictional_counts)//2]:,}"
        )
    if real_counts:
        logger.info(
            f"Real brands: avg={sum(real_counts)/len(real_counts):,.0f}, "
            f"median={sorted(real_counts)[len(real_counts)//2]:,}"
        )

    # Context query summary (review/best/vs on RedPajama only)
    for suffix in CONTEXT_SUFFIXES:
        qt = f"context_{suffix}"
        ctx_results = [
            (r["brand_name"], int(r["raw_count"]))
            for r in results
            if r.get("query_type") == qt and r["corpus"] == "RedPajama"
            and int(r["raw_count"]) >= 0
        ]
        if ctx_results:
            counts = [c for _, c in ctx_results]
            nonzero = [c for c in counts if c > 0]
            logger.info(
                f"\nContext '{suffix}' queries: "
                f"{len(nonzero)}/{len(counts)} brands with >0 hits, "
                f"avg={sum(counts)/len(counts):,.0f}"
            )
            # Top 3
            for name, count in sorted(ctx_results, key=lambda x: -x[1])[:3]:
                logger.info(f"  {name} {suffix}: {count:,}")

    # Failed queries
    failed = sum(1 for r in results if int(r["raw_count"]) == -1)
    if failed:
        logger.warning(f"\nFailed queries: {failed}")


# ---------------------------------------------------------------------------
# Google Trends data collection
# ---------------------------------------------------------------------------

def run_trends_scan():
    """
    Collect Google Trends interest-over-time data for all real brands.

    Groups brands into batches of 5 (pytrends API limit) and queries
    12-month US search interest. Uses each brand's primary variant
    paired with its first category keyword for disambiguation.

    Output: TRENDS_CSV with columns:
      brand_name, search_term, familiarity_tier, avg_interest,
      max_interest, min_interest, latest_interest, is_fictional
    """
    try:
        from pytrends.request import TrendReq
    except ImportError:
        logger.error(
            "pytrends not installed. Run: pip install pytrends\n"
            "Skipping Google Trends collection."
        )
        return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Category display names (same as in build_query_list)
    category_display = {
        "laptops": "laptop", "smartphones": "smartphone", "tvs": "TV",
        "cameras": "camera", "tablets": "tablet", "headphones": "headphones",
        "wireless_earbuds": "earbuds", "running_shoes": "running shoes",
        "smartwatches": "smartwatch", "robot_vacuums": "robot vacuum",
        "portable_speakers": "speaker", "keyboards": "keyboard",
        "external_ssds": "SSD", "water_bottles": "water bottle",
        "electric_toothbrushes": "toothbrush", "coffee_makers": "coffee",
        "blenders": "blender", "backpacks": "backpack",
        "wireless_routers": "router", "monitors": "monitor",
    }

    # Build search terms: brand + primary category for disambiguation
    search_terms = []
    for entry in BRAND_DATABASE:
        if entry["is_fictional"]:
            continue  # Google Trends won't have fictional brands
        primary = entry["variants"][0]
        cat = entry["categories"][0]
        cat_label = category_display.get(cat, cat.replace("_", " "))
        # Use brand + category for ambiguous names, brand alone otherwise
        ambiguous_brands = {"Google", "Amazon", "Brooks", "Stanley", "Nothing",
                            "Flair", "Varia", "Shark"}
        if entry["brand"] in ambiguous_brands:
            term = f"{primary} {cat_label}"
        else:
            term = primary
        search_terms.append({
            "brand": entry["brand"],
            "search_term": term,
            "familiarity": entry["familiarity"],
            "is_fictional": False,
        })

    logger.info(f"Google Trends: {len(search_terms)} real brands to query")

    pytrends = TrendReq(hl="en-US", tz=360)
    results = []

    # Process in batches of TRENDS_BATCH_SIZE
    batches = [
        search_terms[i:i + TRENDS_BATCH_SIZE]
        for i in range(0, len(search_terms), TRENDS_BATCH_SIZE)
    ]

    for batch_idx, batch in enumerate(batches):
        terms = [b["search_term"] for b in batch]
        logger.info(
            f"[Trends batch {batch_idx + 1}/{len(batches)}] "
            f"Querying: {', '.join(terms)}"
        )

        try:
            pytrends.build_payload(terms, cat=0, timeframe="today 12-m", geo="US")
            data = pytrends.interest_over_time()

            if data.empty:
                logger.warning(f"  No data returned for batch: {terms}")
                for b in batch:
                    results.append({
                        "brand_name": b["brand"],
                        "search_term": b["search_term"],
                        "familiarity_tier": b["familiarity"],
                        "avg_interest": 0,
                        "max_interest": 0,
                        "min_interest": 0,
                        "latest_interest": 0,
                        "is_fictional": False,
                    })
                continue

            for b in batch:
                term = b["search_term"]
                if term in data.columns:
                    series = data[term]
                    results.append({
                        "brand_name": b["brand"],
                        "search_term": term,
                        "familiarity_tier": b["familiarity"],
                        "avg_interest": round(series.mean(), 1),
                        "max_interest": int(series.max()),
                        "min_interest": int(series.min()),
                        "latest_interest": int(series.iloc[-1]),
                        "is_fictional": False,
                    })
                    logger.info(f"  {term}: avg={series.mean():.1f}")
                else:
                    logger.warning(f"  {term}: not found in response columns")
                    results.append({
                        "brand_name": b["brand"],
                        "search_term": term,
                        "familiarity_tier": b["familiarity"],
                        "avg_interest": 0,
                        "max_interest": 0,
                        "min_interest": 0,
                        "latest_interest": 0,
                        "is_fictional": False,
                    })

        except Exception as e:
            logger.error(f"  Google Trends error for batch {batch_idx + 1}: {e}")
            for b in batch:
                results.append({
                    "brand_name": b["brand"],
                    "search_term": b["search_term"],
                    "familiarity_tier": b["familiarity"],
                    "avg_interest": -1,  # Sentinel for errors
                    "max_interest": -1,
                    "min_interest": -1,
                    "latest_interest": -1,
                    "is_fictional": False,
                })

        time.sleep(TRENDS_DELAY)

    # Write CSV
    trends_fields = [
        "brand_name", "search_term", "familiarity_tier",
        "avg_interest", "max_interest", "min_interest",
        "latest_interest", "is_fictional",
    ]
    with open(TRENDS_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=trends_fields)
        writer.writeheader()
        writer.writerows(results)

    logger.info(f"\nGoogle Trends data saved to {TRENDS_CSV}")
    logger.info(f"Brands collected: {len(results)}")

    # Quick summary by tier
    for tier in ["high", "medium", "low"]:
        tier_data = [r for r in results if r["familiarity_tier"] == tier and r["avg_interest"] >= 0]
        if tier_data:
            avgs = [r["avg_interest"] for r in tier_data]
            logger.info(
                f"  {tier.upper()}: {len(tier_data)} brands, "
                f"mean interest={sum(avgs)/len(avgs):.1f}"
            )


# ---------------------------------------------------------------------------
# Quick test mode
# ---------------------------------------------------------------------------

def run_test():
    """
    Run a quick API test with 3 brands (high/medium/low familiarity)
    across 1 corpus, including context queries. Validates that the API
    is working and the query logic is correct.
    """
    test_brands = [
        ("Sony", "high"),
        ("Keychron", "low"),
        ("Zentria", "low (fictional)"),
    ]
    test_corpus = "RedPajama"
    test_index = CORPORA[test_corpus]

    logger.info("=" * 60)
    logger.info("API TEST (3 brands x 1 corpus)")
    logger.info("=" * 60)

    for brand_name, tier in test_brands:
        logger.info(f"\n{brand_name} ({tier}):")

        # Brand alone
        count = query_infini_gram(brand_name, test_index)
        logger.info(f"  '{brand_name}' = {count:,}" if count is not None else f"  '{brand_name}' = FAILED")

        # Context queries
        for suffix in CONTEXT_SUFFIXES:
            q = f"{brand_name} {suffix}"
            count = query_infini_gram(q, test_index)
            logger.info(f"  '{q}' = {count:,}" if count is not None else f"  '{q}' = FAILED")
            time.sleep(REQUEST_DELAY)

    logger.info("\nAPI test complete.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Scan infini-gram API for brand name frequencies across training corpora."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show queries without executing them.",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from checkpoint (skip already-completed queries).",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Quick API test with 3 brands (Sony, Keychron, Zentria).",
    )
    parser.add_argument(
        "--trends-only",
        action="store_true",
        help="Only collect Google Trends data (skip infini-gram scan).",
    )
    args = parser.parse_args()

    if args.test:
        run_test()
    elif args.trends_only:
        run_trends_scan()
    else:
        run_scan(dry_run=args.dry_run, resume=args.resume)
        if not args.dry_run:
            logger.info("\nStarting Google Trends collection...")
            run_trends_scan()
