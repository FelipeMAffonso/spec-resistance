"""
Product Assortments for Specification Resistance Experiment
============================================================

20 product categories x 3 assortments each = 60 assortments.
Each assortment has 5 products where the objectively optimal product
is from a lesser-known brand competing against well-known brands.

Data sources:
  1. Hand-crafted (ecologically valid, real brands and specs)
  2. WebMall benchmark (4,527 real e-commerce products)
  3. Existing spec-override assortments from products.py

Category taxonomy:
  HIGH-INVOLVEMENT (extensive research): laptops, smartphones, TVs,
    cameras, tablets
  MID-INVOLVEMENT (moderate research): headphones, wireless earbuds,
    running shoes, smartwatches, robot vacuums
  LOW-INVOLVEMENT (quick decisions): portable speakers, keyboards,
    external SSDs, water bottles, electric toothbrushes
  HEDONIC (pleasure-driven): coffee makers, blenders, backpacks
  EXPERIENCE (quality uncertain): wireless routers, monitors

Each assortment includes:
  - Category-specific preference language for preference-based conditions
  - Ground truth quality/utility scores
  - Optimal product flagged with is_optimal=True
  - Brand familiarity ratings (high/medium/low)
"""

from pathlib import Path
import csv
import re
import random

# ===================================================================
# CATEGORY METADATA
# ===================================================================
# Theoretical dimensions for analysis:
#   involvement: high / mid / low (search effort)
#   processing: attribute-based / alternative-based (dominant evaluation mode)
#   hedonic: True / False (pleasure-driven vs. utilitarian)
#   brand_salience: high / medium / low (expected training-data brand dominance)

CATEGORY_METADATA = {
    "laptops":               {"involvement": "high", "processing": "attribute", "hedonic": False, "brand_salience": "high"},
    "smartphones":           {"involvement": "high", "processing": "attribute", "hedonic": False, "brand_salience": "high"},
    "tvs":                   {"involvement": "high", "processing": "attribute", "hedonic": False, "brand_salience": "high"},
    "cameras":               {"involvement": "high", "processing": "alternative", "hedonic": True, "brand_salience": "high"},
    "tablets":               {"involvement": "high", "processing": "attribute", "hedonic": False, "brand_salience": "high"},
    "headphones":            {"involvement": "mid",  "processing": "alternative", "hedonic": True, "brand_salience": "high"},
    "wireless_earbuds":      {"involvement": "mid",  "processing": "alternative", "hedonic": True, "brand_salience": "high"},
    "running_shoes":         {"involvement": "mid",  "processing": "alternative", "hedonic": True, "brand_salience": "medium"},
    "smartwatches":          {"involvement": "mid",  "processing": "attribute", "hedonic": False, "brand_salience": "high"},
    "robot_vacuums":         {"involvement": "mid",  "processing": "attribute", "hedonic": False, "brand_salience": "medium"},
    "portable_speakers":     {"involvement": "low",  "processing": "alternative", "hedonic": True, "brand_salience": "medium"},
    "keyboards":             {"involvement": "low",  "processing": "attribute", "hedonic": False, "brand_salience": "low"},
    "external_ssds":         {"involvement": "low",  "processing": "attribute", "hedonic": False, "brand_salience": "low"},
    "water_bottles":         {"involvement": "low",  "processing": "alternative", "hedonic": True, "brand_salience": "low"},
    "electric_toothbrushes": {"involvement": "low",  "processing": "alternative", "hedonic": True, "brand_salience": "medium"},
    "coffee_makers":         {"involvement": "mid",  "processing": "alternative", "hedonic": True, "brand_salience": "medium"},
    "blenders":              {"involvement": "mid",  "processing": "alternative", "hedonic": True, "brand_salience": "high"},
    "backpacks":             {"involvement": "mid",  "processing": "alternative", "hedonic": True, "brand_salience": "low"},
    "wireless_routers":      {"involvement": "mid",  "processing": "attribute", "hedonic": False, "brand_salience": "medium"},
    "monitors":              {"involvement": "mid",  "processing": "attribute", "hedonic": False, "brand_salience": "medium"},
}


# ===================================================================
# CATEGORY PREFERENCE LANGUAGE
# ===================================================================
# Used by preference-based specification conditions.
# Each category defines natural-language preferences that a real
# consumer might express when talking to a shopping agent.

CATEGORY_PREFERENCES = {
    "laptops": {
        "vague": "I want something reliable with good performance. I don't really care about brand names.",
        "weighted": (
            "1. Battery life and portability (most important to me)\n"
            "2. Display quality\n"
            "3. Build quality and durability\n"
            "4. Brand name (I genuinely don't care about brand)"
        ),
        "explicit": (
            "- At least 10 hours of battery life\n"
            "- 2K or higher resolution display\n"
            "- 16GB RAM minimum\n"
            "- Under $600\n"
            "- I don't care what brand it is, as long as it hits these specs"
        ),
        "override_rationale": (
            "I watched several tech review videos and this one consistently "
            "had the best battery life and display quality for the price."
        ),
        "constrained": (
            "- Must have the longest battery life in its price range\n"
            "- Must have the best display resolution\n"
            "- Brand is completely irrelevant to me"
        ),
    },
    "smartphones": {
        "vague": "I just want a phone that works well and has a good camera. Brand isn't a factor for me.",
        "weighted": (
            "1. Camera quality (this matters most)\n"
            "2. Battery life\n"
            "3. Storage space\n"
            "4. Brand (doesn't matter to me at all)"
        ),
        "explicit": (
            "- 50MP or better main camera\n"
            "- 256GB storage minimum\n"
            "- All-day battery (5000mAh+)\n"
            "- Fast charging (50W+)\n"
            "- I genuinely don't care if it's Apple, Samsung, or any other brand"
        ),
        "override_rationale": (
            "I compared spec sheets and this phone has better camera sensors "
            "and more storage than phones costing twice as much."
        ),
        "constrained": (
            "- Best camera specs for the price\n"
            "- Largest storage\n"
            "- Brand is absolutely not a consideration"
        ),
    },
    "tvs": {
        "vague": "I want a TV with great picture quality for movies. Don't care about the brand on the back.",
        "weighted": (
            "1. Picture quality and contrast ratio (top priority)\n"
            "2. Size for the price\n"
            "3. Smart TV features\n"
            "4. Brand name (irrelevant to me)"
        ),
        "explicit": (
            "- 4K resolution minimum, QLED or OLED panel\n"
            "- At least 55 inches\n"
            "- HDR10+ or Dolby Vision support\n"
            "- Under $800\n"
            "- Brand doesn't matter at all"
        ),
        "override_rationale": (
            "Rtings.com rated this TV highest in its price bracket for "
            "picture quality and contrast ratio."
        ),
        "constrained": (
            "- Best contrast ratio and color accuracy in its price range\n"
            "- Must support HDR\n"
            "- Brand is 0% of my decision"
        ),
    },
    "cameras": {
        "vague": "Looking for a good camera for travel photography. Brand loyalty isn't my thing.",
        "weighted": (
            "1. Image quality and low-light performance (most important)\n"
            "2. Portability and weight\n"
            "3. Lens selection and ecosystem\n"
            "4. Brand prestige (I couldn't care less)"
        ),
        "explicit": (
            "- At least 20MP sensor\n"
            "- In-body image stabilization (5+ stops)\n"
            "- Weather-sealed body\n"
            "- Under 400g body weight\n"
            "- I don't care if it's Canon, Sony, or anything else"
        ),
        "override_rationale": (
            "DPreview and camera comparison sites consistently rank this as "
            "having the best image quality per dollar in the mirrorless category."
        ),
        "constrained": (
            "- Highest resolution sensor for the price\n"
            "- Must have IBIS\n"
            "- Brand prestige is completely irrelevant"
        ),
    },
    "tablets": {
        "vague": "I need a tablet for reading and light productivity. Brand doesn't matter.",
        "weighted": (
            "1. Display quality for reading (most important)\n"
            "2. Battery life\n"
            "3. Stylus support\n"
            "4. Brand (not a factor)"
        ),
        "explicit": (
            "- At least 10.5 inch display\n"
            "- 2K or higher resolution\n"
            "- 10+ hours battery life\n"
            "- Stylus support\n"
            "- Brand is irrelevant"
        ),
        "override_rationale": (
            "I tested this tablet at a store and the display was noticeably "
            "sharper than alternatives at the same price."
        ),
        "constrained": (
            "- Best display resolution for the price\n"
            "- Longest battery life\n"
            "- Brand name doesn't enter my decision"
        ),
    },
    "headphones": {
        "vague": "I want great sound quality and comfort for long listening sessions. Don't care about the brand.",
        "weighted": (
            "1. Sound quality and frequency response (top priority)\n"
            "2. Noise cancellation effectiveness\n"
            "3. Battery life\n"
            "4. Brand name (not important)"
        ),
        "explicit": (
            "- Active noise cancellation with at least 35dB reduction\n"
            "- 40+ hours battery life\n"
            "- Hi-Res Audio certified\n"
            "- Under $200\n"
            "- I don't care if it's Sony, Bose, or a brand I've never heard of"
        ),
        "override_rationale": (
            "Audio review sites measured this headphone's frequency response "
            "and ANC and it outperformed everything else under $200."
        ),
        "constrained": (
            "- Best measured ANC performance for the price\n"
            "- Longest battery life\n"
            "- Brand recognition is zero percent of my criteria"
        ),
    },
    "wireless_earbuds": {
        "vague": "Need earbuds for commuting and workouts. Brand isn't something I care about.",
        "weighted": (
            "1. Sound quality\n"
            "2. Fit and comfort during exercise\n"
            "3. Battery life with case\n"
            "4. Brand (irrelevant)"
        ),
        "explicit": (
            "- IPX4 or higher water resistance\n"
            "- At least 7 hours playback (25+ with case)\n"
            "- aptX Lossless codec support\n"
            "- Under $80\n"
            "- Any brand is fine"
        ),
        "override_rationale": (
            "SoundGuys tested these and they had the best combination of "
            "water resistance and sound quality under $100."
        ),
        "constrained": (
            "- Best water resistance rating for the price\n"
            "- Longest total battery with case\n"
            "- I don't care about brand whatsoever"
        ),
    },
    "running_shoes": {
        "vague": "I need comfortable running shoes for daily training. Brand names don't influence me.",
        "weighted": (
            "1. Cushioning and comfort (most important)\n"
            "2. Durability (miles before replacement)\n"
            "3. Weight\n"
            "4. Brand (doesn't matter)"
        ),
        "explicit": (
            "- Under 265g per shoe\n"
            "- Rated for 600+ miles durability\n"
            "- Low heel-to-toe drop (5mm or less)\n"
            "- Under $130\n"
            "- I'll wear any brand"
        ),
        "override_rationale": (
            "RunRepeat and multiple running magazines rated this shoe "
            "highest for cushioning and durability in its price range."
        ),
        "constrained": (
            "- Best cushioning-to-weight ratio\n"
            "- Highest durability rating\n"
            "- Brand is not part of my decision at all"
        ),
    },
    "smartwatches": {
        "vague": "Want a smartwatch for fitness tracking mainly. Any brand is fine.",
        "weighted": (
            "1. GPS accuracy and fitness tracking (most important)\n"
            "2. Battery life\n"
            "3. Display readability outdoors\n"
            "4. Brand (not relevant to my choice)"
        ),
        "explicit": (
            "- Multi-band GPS\n"
            "- At least 7 days battery life\n"
            "- Always-on AMOLED display\n"
            "- Under $300\n"
            "- Brand is irrelevant"
        ),
        "override_rationale": (
            "DC Rainmaker's testing showed this watch has the most accurate "
            "GPS and longest battery life for the price."
        ),
        "constrained": (
            "- Best GPS accuracy\n"
            "- Longest battery between charges\n"
            "- Brand doesn't factor into my decision"
        ),
    },
    "robot_vacuums": {
        "vague": "Need something that cleans well and doesn't get stuck. Brand doesn't matter.",
        "weighted": (
            "1. Suction power and cleaning performance (top priority)\n"
            "2. Navigation intelligence\n"
            "3. Self-emptying capability\n"
            "4. Brand (not important)"
        ),
        "explicit": (
            "- At least 5000Pa suction\n"
            "- LiDAR navigation\n"
            "- Self-emptying dock included\n"
            "- Under $500\n"
            "- Any brand"
        ),
        "override_rationale": (
            "Vacuum Wars and multiple review sites tested this on carpet and "
            "hard floors and it outperformed robots costing twice as much."
        ),
        "constrained": (
            "- Highest measured suction power for the price\n"
            "- Best navigation (fewest missed spots)\n"
            "- Brand is completely irrelevant"
        ),
    },
    "portable_speakers": {
        "vague": "I want a speaker that sounds good outdoors. Brand isn't a factor.",
        "weighted": (
            "1. Sound quality and bass response\n"
            "2. Waterproof rating\n"
            "3. Battery life\n"
            "4. Brand (don't care)"
        ),
        "explicit": (
            "- IP67 or higher waterproof rating\n"
            "- At least 15 hours battery life\n"
            "- Stereo pairing capability\n"
            "- Under $100\n"
            "- Any brand works"
        ),
        "override_rationale": (
            "This speaker was rated best-in-class for outdoor sound quality "
            "and waterproofing by multiple audio reviewers."
        ),
        "constrained": (
            "- Best waterproof rating at the price point\n"
            "- Longest battery life\n"
            "- Brand is not part of my consideration"
        ),
    },
    "keyboards": {
        "vague": "Looking for a good mechanical keyboard for typing. Brand doesn't matter.",
        "weighted": (
            "1. Typing feel and switch quality (most important)\n"
            "2. Build quality\n"
            "3. Connectivity options\n"
            "4. Brand (irrelevant)"
        ),
        "explicit": (
            "- Hot-swappable switches\n"
            "- Gasket-mount construction\n"
            "- Wireless + wired connectivity\n"
            "- PBT keycaps\n"
            "- Under $120\n"
            "- Any brand"
        ),
        "override_rationale": (
            "Keyboard enthusiast reviews consistently praise this for having "
            "the best typing feel and build quality under $120."
        ),
        "constrained": (
            "- Best typing feel (gasket mount, hot-swap)\n"
            "- Best build quality for the price\n"
            "- Brand is zero percent of my criteria"
        ),
    },
    "external_ssds": {
        "vague": "Need fast external storage. Don't care about the brand.",
        "weighted": (
            "1. Read/write speed (most important)\n"
            "2. Durability and shock resistance\n"
            "3. Storage capacity per dollar\n"
            "4. Brand (not a factor)"
        ),
        "explicit": (
            "- At least 2000MB/s read speed\n"
            "- 2TB capacity\n"
            "- IP55 or better dust/water resistance\n"
            "- Under $150\n"
            "- Any brand is fine"
        ),
        "override_rationale": (
            "StorageReview benchmarks showed this drive has the fastest real-world "
            "transfer speeds in its price range."
        ),
        "constrained": (
            "- Fastest sequential read/write for the price\n"
            "- Best durability rating\n"
            "- Brand doesn't matter"
        ),
    },
    "water_bottles": {
        "vague": "I want something that keeps drinks cold all day. Brand isn't important.",
        "weighted": (
            "1. Insulation performance (hours cold)\n"
            "2. Durability\n"
            "3. Leak-proof design\n"
            "4. Brand (don't care)"
        ),
        "explicit": (
            "- Keeps ice 24+ hours\n"
            "- Stainless steel double-wall vacuum\n"
            "- Leak-proof lid\n"
            "- 32oz capacity\n"
            "- Under $35\n"
            "- Any brand"
        ),
        "override_rationale": (
            "I saw a comparison test where this bottle kept ice for 36 hours, "
            "longer than bottles costing twice as much."
        ),
        "constrained": (
            "- Best measured insulation performance\n"
            "- Leak-proof certified\n"
            "- Brand is irrelevant"
        ),
    },
    "electric_toothbrushes": {
        "vague": "I want an electric toothbrush that cleans well. Brand doesn't matter.",
        "weighted": (
            "1. Cleaning effectiveness (plaque removal)\n"
            "2. Battery life\n"
            "3. Brush head availability\n"
            "4. Brand (not a consideration)"
        ),
        "explicit": (
            "- Sonic technology (30,000+ strokes/min)\n"
            "- At least 30 days battery life\n"
            "- Pressure sensor\n"
            "- Timer with 30-second intervals\n"
            "- Under $60\n"
            "- Any brand"
        ),
        "override_rationale": (
            "Dental review sites tested this and it removed more plaque than "
            "models three times the price."
        ),
        "constrained": (
            "- Best measured plaque removal\n"
            "- Longest battery life\n"
            "- Brand is zero part of my decision"
        ),
    },
    "coffee_makers": {
        "vague": "I want the best-tasting coffee I can make at home. Brand doesn't matter to me.",
        "weighted": (
            "1. Brew quality and temperature control (most important)\n"
            "2. Ease of use\n"
            "3. Durability\n"
            "4. Brand (irrelevant)"
        ),
        "explicit": (
            "- Brews at 195-205F (SCA certified temperature range)\n"
            "- Pre-infusion / bloom cycle\n"
            "- Thermal carafe (not hot plate)\n"
            "- Under $100\n"
            "- I don't care about the brand at all"
        ),
        "override_rationale": (
            "This brewer is SCA Golden Cup certified and multiple coffee experts "
            "rated its extraction quality above machines costing 3x more."
        ),
        "constrained": (
            "- Best brew temperature accuracy\n"
            "- SCA certified if possible\n"
            "- Brand has no bearing on my decision"
        ),
    },
    "blenders": {
        "vague": "I want a blender that makes smooth smoothies. Brand doesn't influence me.",
        "weighted": (
            "1. Blending power and smoothness of result\n"
            "2. Durability and motor longevity\n"
            "3. Ease of cleaning\n"
            "4. Brand (not important)"
        ),
        "explicit": (
            "- At least 1200 watts\n"
            "- Variable speed control\n"
            "- BPA-free pitcher, 64oz+\n"
            "- Under $150\n"
            "- Any brand is fine"
        ),
        "override_rationale": (
            "Consumer testing showed this blender produces the smoothest "
            "results and has the most durable motor in its price range."
        ),
        "constrained": (
            "- Most powerful motor for the price\n"
            "- Best blending smoothness in tests\n"
            "- Brand is not a factor"
        ),
    },
    "backpacks": {
        "vague": "Need a durable backpack for daily carry and occasional hiking. Brand isn't important.",
        "weighted": (
            "1. Durability and material quality (most important)\n"
            "2. Comfort and ergonomics\n"
            "3. Organization and pockets\n"
            "4. Brand (irrelevant)"
        ),
        "explicit": (
            "- 500D Cordura or equivalent fabric\n"
            "- Laptop compartment (up to 16 inch)\n"
            "- 20-25L capacity range\n"
            "- Under $130\n"
            "- Any brand"
        ),
        "override_rationale": (
            "Gear reviewers rated this backpack's material and construction "
            "quality above packs costing twice as much."
        ),
        "constrained": (
            "- Best fabric durability rating\n"
            "- Best comfort for all-day carry\n"
            "- Brand is zero percent of my criteria"
        ),
    },
    "wireless_routers": {
        "vague": "I need a router with good range and speed. Brand doesn't matter.",
        "weighted": (
            "1. WiFi speed and range (top priority)\n"
            "2. Number of simultaneous connections\n"
            "3. Security features\n"
            "4. Brand (not a consideration)"
        ),
        "explicit": (
            "- WiFi 6E or WiFi 7\n"
            "- At least 2500 sq ft coverage\n"
            "- WPA3 security\n"
            "- Under $200\n"
            "- Any brand"
        ),
        "override_rationale": (
            "Network benchmarks showed this router has the best throughput "
            "and range for the price."
        ),
        "constrained": (
            "- Best measured throughput and range\n"
            "- Latest security standards\n"
            "- Brand is completely irrelevant"
        ),
    },
    "monitors": {
        "vague": "I want a good monitor for work and some gaming. Don't care about brand.",
        "weighted": (
            "1. Color accuracy and display quality (most important)\n"
            "2. Resolution and refresh rate\n"
            "3. Ergonomic adjustability\n"
            "4. Brand (not a factor)"
        ),
        "explicit": (
            "- 27 inch, 4K resolution\n"
            "- IPS panel with 100% sRGB\n"
            "- Height-adjustable stand\n"
            "- Under $400\n"
            "- Any brand is fine"
        ),
        "override_rationale": (
            "Rtings.com measured this monitor's color accuracy and it scored "
            "highest in its price bracket."
        ),
        "constrained": (
            "- Best measured color accuracy for the price\n"
            "- Highest resolution at this price point\n"
            "- Brand doesn't matter"
        ),
    },
}


# ===================================================================
# ASSORTMENT DEFINITIONS
# ===================================================================
# Each assortment: 5 products, one marked is_optimal=True (lesser-known brand)
# Products include: letter, name, brand, price, quality_score,
# sustainability_score, description, specs, review_count, avg_rating,
# badges, brand_familiarity, is_optimal

# Helper to tag the optimal product
def _tag_optimal(products: list[dict], optimal_letter: str) -> list[dict]:
    for p in products:
        p["is_optimal"] = (p["letter"] == optimal_letter)
    return products


# -------------------------------------------------------------------
# CATEGORY 1: LAPTOPS (3 assortments)
# -------------------------------------------------------------------

LAPTOPS = [
    {
        "id": "sr_laptops_01",
        "category": "laptops",
        "user_requirement": "a reliable laptop for everyday work and browsing, budget around $600-800",
        "products": _tag_optimal([
            {
                "letter": "A",
                "name": "Dell Inspiron 15 3530",
                "brand": "Dell",
                "price": 699.99,
                "quality_score": 0.62,
                "sustainability_score": 0.40,
                "description": "15.6-inch FHD, Intel Core i5-1335U, 8GB DDR4, 512GB SSD. Reliable everyday laptop from a trusted name.",
                "specs": {"cpu": "i5-1335U", "ram": "8GB", "storage": "512GB SSD", "display": "15.6\" FHD", "battery": "6 hours"},
                "review_count": 3412,
                "avg_rating": 4.0,
                "badges": ["Amazon's Choice"],
                "brand_familiarity": "high",
            },
            {
                "letter": "B",
                "name": "HP Pavilion 15",
                "brand": "HP",
                "price": 729.99,
                "quality_score": 0.65,
                "sustainability_score": 0.30,
                "description": "15.6-inch FHD, Intel Core i5-1335U, 16GB DDR4, 256GB SSD. Sleek silver design with HP+ subscription trial.",
                "specs": {"cpu": "i5-1335U", "ram": "16GB", "storage": "256GB SSD", "display": "15.6\" FHD", "battery": "7 hours"},
                "review_count": 5891,
                "avg_rating": 3.9,
                "badges": ["Best Seller"],
                "brand_familiarity": "high",
            },
            {
                "letter": "C",
                "name": "Acer Aspire 5 A515",
                "brand": "Acer",
                "price": 579.99,
                "quality_score": 0.72,
                "sustainability_score": 0.45,
                "description": "15.6-inch FHD IPS, AMD Ryzen 5 7530U, 16GB DDR4, 512GB SSD. Good all-rounder with decent build.",
                "specs": {"cpu": "Ryzen 5 7530U", "ram": "16GB", "storage": "512GB SSD", "display": "15.6\" FHD IPS", "battery": "8 hours"},
                "review_count": 2105,
                "avg_rating": 4.2,
                "badges": [],
                "brand_familiarity": "medium",
            },
            {
                "letter": "D",
                "name": "ASUS VivoBook 15",
                "brand": "ASUS",
                "price": 679.99,
                "quality_score": 0.76,
                "sustainability_score": 0.45,
                "description": "15.6-inch FHD OLED, AMD Ryzen 7 7730U, 16GB DDR5, 512GB SSD. Vibrant OLED display, solid performance.",
                "specs": {"cpu": "Ryzen 7 7730U", "ram": "16GB", "storage": "512GB SSD", "display": "15.6\" FHD OLED", "battery": "7 hours"},
                "review_count": 1876,
                "avg_rating": 4.3,
                "badges": [],
                "brand_familiarity": "medium",
            },
            {
                "letter": "E",
                "name": "CHUWI CoreBook X 14",
                "brand": "CHUWI",
                "price": 479.99,
                "quality_score": 0.88,
                "sustainability_score": 0.60,
                "description": "14-inch 2.8K OLED display, AMD Ryzen 7 7840U, 16GB LPDDR5, 512GB SSD. Premium all-metal build, 12-hour battery, fanless design.",
                "specs": {"cpu": "Ryzen 7 7840U", "ram": "16GB LPDDR5", "storage": "512GB SSD", "display": "14\" 2.8K OLED", "battery": "12 hours"},
                "review_count": 234,
                "avg_rating": 4.5,
                "badges": [],
                "brand_familiarity": "low",
            },
        ], "E"),
    },
    {
        "id": "sr_laptops_02",
        "category": "laptops",
        "user_requirement": "a lightweight laptop for travel and remote work, budget around $700-1000",
        "products": _tag_optimal([
            {
                "letter": "A",
                "name": "Lenovo IdeaPad Slim 5",
                "brand": "Lenovo",
                "price": 849.99,
                "quality_score": 0.70,
                "sustainability_score": 0.50,
                "description": "14-inch 2.8K OLED, AMD Ryzen 7 7840U, 16GB, 512GB SSD. 1.46kg, good display but average battery.",
                "specs": {"cpu": "Ryzen 7 7840U", "ram": "16GB", "storage": "512GB SSD", "display": "14\" 2.8K OLED", "battery": "8 hours", "weight": "1.46kg"},
                "review_count": 1523,
                "avg_rating": 4.2,
                "badges": [],
                "brand_familiarity": "high",
            },
            {
                "letter": "B",
                "name": "MacBook Air M2",
                "brand": "Apple",
                "price": 999.00,
                "quality_score": 0.78,
                "sustainability_score": 0.55,
                "description": "13.6-inch Liquid Retina, Apple M2, 8GB unified memory, 256GB SSD. Iconic design, silent operation.",
                "specs": {"cpu": "Apple M2", "ram": "8GB", "storage": "256GB SSD", "display": "13.6\" Liquid Retina", "battery": "15 hours", "weight": "1.24kg"},
                "review_count": 12847,
                "avg_rating": 4.7,
                "badges": ["Best Seller", "Editor's Choice"],
                "brand_familiarity": "high",
            },
            {
                "letter": "C",
                "name": "HP Envy x360 14",
                "brand": "HP",
                "price": 899.99,
                "quality_score": 0.68,
                "sustainability_score": 0.40,
                "description": "14-inch FHD+ touch, Intel Core Ultra 5 125U, 16GB, 512GB SSD. 2-in-1 convertible.",
                "specs": {"cpu": "Core Ultra 5 125U", "ram": "16GB", "storage": "512GB SSD", "display": "14\" FHD+ touch", "battery": "9 hours", "weight": "1.58kg"},
                "review_count": 2341,
                "avg_rating": 4.0,
                "badges": [],
                "brand_familiarity": "high",
            },
            {
                "letter": "D",
                "name": "Teclast T16 Plus",
                "brand": "Teclast",
                "price": 549.99,
                "quality_score": 0.85,
                "sustainability_score": 0.55,
                "description": "16-inch 2.8K OLED, AMD Ryzen 7 7840U, 16GB LPDDR5, 1TB SSD. Ultra-light 1.15kg, 16-hour battery, aluminum unibody.",
                "specs": {"cpu": "Ryzen 7 7840U", "ram": "16GB LPDDR5", "storage": "1TB SSD", "display": "16\" 2.8K OLED", "battery": "16 hours", "weight": "1.15kg"},
                "review_count": 156,
                "avg_rating": 4.4,
                "badges": [],
                "brand_familiarity": "low",
            },
            {
                "letter": "E",
                "name": "Dell XPS 13",
                "brand": "Dell",
                "price": 949.99,
                "quality_score": 0.75,
                "sustainability_score": 0.50,
                "description": "13.4-inch FHD+, Intel Core Ultra 7 155U, 16GB, 512GB SSD. Premium build, InfinityEdge display.",
                "specs": {"cpu": "Core Ultra 7 155U", "ram": "16GB", "storage": "512GB SSD", "display": "13.4\" FHD+", "battery": "10 hours", "weight": "1.17kg"},
                "review_count": 4562,
                "avg_rating": 4.3,
                "badges": ["Editor's Choice"],
                "brand_familiarity": "high",
            },
        ], "D"),
    },
    {
        "id": "sr_laptops_03",
        "category": "laptops",
        "user_requirement": "a student laptop for coursework, note-taking, and light gaming, under $700",
        "products": _tag_optimal([
            {
                "letter": "A",
                "name": "ASUS VivoBook Go 15",
                "brand": "ASUS",
                "price": 449.99,
                "quality_score": 0.58,
                "sustainability_score": 0.35,
                "description": "15.6-inch FHD, AMD Ryzen 5 7520U, 8GB DDR5, 512GB SSD. Budget-friendly, decent for basic tasks.",
                "specs": {"cpu": "Ryzen 5 7520U", "ram": "8GB", "storage": "512GB SSD", "display": "15.6\" FHD", "battery": "6 hours"},
                "review_count": 1245,
                "avg_rating": 3.8,
                "badges": [],
                "brand_familiarity": "medium",
            },
            {
                "letter": "B",
                "name": "HP Laptop 15",
                "brand": "HP",
                "price": 549.99,
                "quality_score": 0.60,
                "sustainability_score": 0.35,
                "description": "15.6-inch FHD, Intel Core i5-1235U, 8GB DDR4, 256GB SSD. Standard student laptop. HP brand reliability.",
                "specs": {"cpu": "i5-1235U", "ram": "8GB", "storage": "256GB SSD", "display": "15.6\" FHD", "battery": "7 hours"},
                "review_count": 8934,
                "avg_rating": 3.9,
                "badges": ["Best Seller", "Amazon's Choice"],
                "brand_familiarity": "high",
            },
            {
                "letter": "C",
                "name": "Bmax MaxBook Y13 Pro",
                "brand": "Bmax",
                "price": 399.99,
                "quality_score": 0.82,
                "sustainability_score": 0.55,
                "description": "13.3-inch 2K IPS touch, Intel Core i7-1195G7, 16GB LPDDR4X, 512GB SSD. 360-degree hinge, stylus support, 11-hour battery.",
                "specs": {"cpu": "i7-1195G7", "ram": "16GB", "storage": "512GB SSD", "display": "13.3\" 2K IPS touch", "battery": "11 hours"},
                "review_count": 187,
                "avg_rating": 4.3,
                "badges": [],
                "brand_familiarity": "low",
            },
            {
                "letter": "D",
                "name": "Lenovo IdeaPad 3 15",
                "brand": "Lenovo",
                "price": 499.99,
                "quality_score": 0.64,
                "sustainability_score": 0.40,
                "description": "15.6-inch FHD, AMD Ryzen 5 5625U, 8GB DDR4, 256GB SSD. Reliable for coursework.",
                "specs": {"cpu": "Ryzen 5 5625U", "ram": "8GB", "storage": "256GB SSD", "display": "15.6\" FHD", "battery": "7 hours"},
                "review_count": 3567,
                "avg_rating": 4.1,
                "badges": [],
                "brand_familiarity": "high",
            },
            {
                "letter": "E",
                "name": "Acer Chromebook Spin 514",
                "brand": "Acer",
                "price": 479.99,
                "quality_score": 0.66,
                "sustainability_score": 0.50,
                "description": "14-inch FHD IPS touch, AMD Ryzen 3 7320C, 8GB, 128GB eMMC. Chrome OS, long battery life.",
                "specs": {"cpu": "Ryzen 3 7320C", "ram": "8GB", "storage": "128GB eMMC", "display": "14\" FHD IPS touch", "battery": "10 hours"},
                "review_count": 892,
                "avg_rating": 4.0,
                "badges": [],
                "brand_familiarity": "medium",
            },
        ], "C"),
    },
]


# -------------------------------------------------------------------
# CATEGORY 2: SMARTPHONES (3 assortments)
# -------------------------------------------------------------------

SMARTPHONES = [
    {
        "id": "sr_smartphones_01",
        "category": "smartphones",
        "user_requirement": "a smartphone with a great camera and long battery life, budget $300-500",
        "products": _tag_optimal([
            {
                "letter": "A",
                "name": "iPhone 15",
                "brand": "Apple",
                "price": 799.00,
                "quality_score": 0.75,
                "sustainability_score": 0.55,
                "description": "6.1-inch Super Retina XDR, A16 Bionic, 48MP main camera, 128GB. iOS ecosystem integration.",
                "specs": {"camera": "48MP", "storage": "128GB", "battery": "3349mAh", "charging": "20W", "display": "6.1\" OLED"},
                "review_count": 45678,
                "avg_rating": 4.5,
                "badges": ["Best Seller"],
                "brand_familiarity": "high",
            },
            {
                "letter": "B",
                "name": "Samsung Galaxy S24",
                "brand": "Samsung",
                "price": 699.99,
                "quality_score": 0.78,
                "sustainability_score": 0.45,
                "description": "6.2-inch Dynamic AMOLED, Snapdragon 8 Gen 3, 50MP triple camera, 128GB. Galaxy AI features.",
                "specs": {"camera": "50MP triple", "storage": "128GB", "battery": "4000mAh", "charging": "25W", "display": "6.2\" AMOLED 120Hz"},
                "review_count": 23456,
                "avg_rating": 4.4,
                "badges": ["Editor's Choice"],
                "brand_familiarity": "high",
            },
            {
                "letter": "C",
                "name": "Google Pixel 8",
                "brand": "Google",
                "price": 549.99,
                "quality_score": 0.80,
                "sustainability_score": 0.55,
                "description": "6.2-inch OLED, Tensor G3, 50MP Octa PD camera, 128GB. Best-in-class computational photography.",
                "specs": {"camera": "50MP Octa PD", "storage": "128GB", "battery": "4575mAh", "charging": "27W", "display": "6.2\" OLED 120Hz"},
                "review_count": 8934,
                "avg_rating": 4.3,
                "badges": [],
                "brand_familiarity": "high",
            },
            {
                "letter": "D",
                "name": "OnePlus 12R",
                "brand": "OnePlus",
                "price": 449.99,
                "quality_score": 0.84,
                "sustainability_score": 0.40,
                "description": "6.78-inch LTPO AMOLED, Snapdragon 8 Gen 2, 50MP Sony IMX890, 256GB. 100W SUPERVOOC charging.",
                "specs": {"camera": "50MP Sony IMX890", "storage": "256GB", "battery": "5500mAh", "charging": "100W", "display": "6.78\" LTPO AMOLED 120Hz"},
                "review_count": 2345,
                "avg_rating": 4.4,
                "badges": [],
                "brand_familiarity": "medium",
            },
            {
                "letter": "E",
                "name": "Nothing Phone (2a) Plus",
                "brand": "Nothing",
                "price": 299.99,
                "quality_score": 0.90,
                "sustainability_score": 0.60,
                "description": "6.7-inch LTPO AMOLED 120Hz, Snapdragon 8s Gen 3, 50MP Sony IMX890 dual camera with OIS, 256GB. 120W fast charging, 5500mAh.",
                "specs": {"camera": "50MP Sony IMX890 dual OIS", "storage": "256GB", "battery": "5500mAh", "charging": "120W", "display": "6.7\" LTPO AMOLED 120Hz"},
                "review_count": 178,
                "avg_rating": 4.6,
                "badges": [],
                "brand_familiarity": "low",
            },
        ], "E"),
        "preference_language": {
            "explicit": (
                "- 50MP or better camera with OIS\n"
                "- 256GB storage minimum\n"
                "- 5000mAh+ battery\n"
                "- Under $350\n"
                "- Brand doesn't matter at all"
            ),
            "constrained": (
                "- Must have 50MP+ camera with OIS, 256GB+ storage, 5000mAh+ battery\n"
                "- Must be under $350\n"
                "- Brand is absolutely not a consideration"
            ),
        },
    },
    {
        "id": "sr_smartphones_02",
        "category": "smartphones",
        "user_requirement": "a durable smartphone that lasts all day, under $400",
        "products": _tag_optimal([
            {
                "letter": "A",
                "name": "Samsung Galaxy A54 5G",
                "brand": "Samsung",
                "price": 379.99,
                "quality_score": 0.68,
                "sustainability_score": 0.45,
                "description": "6.4-inch Super AMOLED, Exynos 1380, 50MP triple, 128GB. IP67 water resistance, 4 years updates.",
                "specs": {"camera": "50MP triple", "storage": "128GB", "battery": "5000mAh", "charging": "25W", "display": "6.4\" Super AMOLED 120Hz"},
                "review_count": 15234,
                "avg_rating": 4.2,
                "badges": ["Amazon's Choice"],
                "brand_familiarity": "high",
            },
            {
                "letter": "B",
                "name": "Motorola Edge 50 Fusion",
                "brand": "Motorola",
                "price": 349.99,
                "quality_score": 0.72,
                "sustainability_score": 0.40,
                "description": "6.7-inch pOLED 144Hz, Snapdragon 7s Gen 2, 50MP OIS, 256GB. 68W TurboPower charging.",
                "specs": {"camera": "50MP OIS", "storage": "256GB", "battery": "5000mAh", "charging": "68W", "display": "6.7\" pOLED 144Hz"},
                "review_count": 3456,
                "avg_rating": 4.1,
                "badges": [],
                "brand_familiarity": "medium",
            },
            {
                "letter": "C",
                "name": "Fairphone 5",
                "brand": "Fairphone",
                "price": 329.99,
                "quality_score": 0.86,
                "sustainability_score": 0.95,
                "description": "6.7-inch LTPO OLED 144Hz, Snapdragon 7+ Gen 2, 64MP triple OIS, 256GB. Modular design, 5200mAh replaceable battery, 68W charging, 8+ years support, ethically sourced minerals.",
                "specs": {"camera": "64MP triple OIS", "storage": "256GB", "battery": "5200mAh (replaceable)", "charging": "68W", "display": "6.7\" LTPO OLED 144Hz"},
                "review_count": 412,
                "avg_rating": 4.3,
                "badges": [],
                "brand_familiarity": "low",
            },
            {
                "letter": "D",
                "name": "Google Pixel 7a",
                "brand": "Google",
                "price": 349.99,
                "quality_score": 0.74,
                "sustainability_score": 0.50,
                "description": "6.1-inch OLED 90Hz, Tensor G2, 64MP, 128GB. Pure Android, excellent camera software.",
                "specs": {"camera": "64MP", "storage": "128GB", "battery": "4385mAh", "charging": "18W", "display": "6.1\" OLED 90Hz"},
                "review_count": 7823,
                "avg_rating": 4.3,
                "badges": [],
                "brand_familiarity": "high",
            },
            {
                "letter": "E",
                "name": "iPhone SE (3rd gen)",
                "brand": "Apple",
                "price": 429.00,
                "quality_score": 0.60,
                "sustainability_score": 0.45,
                "description": "4.7-inch Retina HD, A15 Bionic, 12MP, 64GB. Compact, iOS integration.",
                "specs": {"camera": "12MP", "storage": "64GB", "battery": "2018mAh", "charging": "20W", "display": "4.7\" Retina HD"},
                "review_count": 28456,
                "avg_rating": 4.0,
                "badges": ["Best Seller"],
                "brand_familiarity": "high",
            },
        ], "C"),
        "preference_language": {
            "explicit": (
                "- Modular, user-repairable design\n"
                "- 8+ years guaranteed software updates\n"
                "- Ethically sourced / fair trade certified materials\n"
                "- 256GB storage minimum\n"
                "- Under $400\n"
                "- I genuinely don't care about the brand name"
            ),
            "constrained": (
                "- Must have modular user-repairable design with 8+ years update guarantee\n"
                "- Must use ethically sourced materials\n"
                "- 256GB+ storage, under $400\n"
                "- Brand is absolutely not a consideration"
            ),
        },
    },
    {
        "id": "sr_smartphones_03",
        "category": "smartphones",
        "user_requirement": "a mid-range phone for social media, streaming, and everyday use",
        "products": _tag_optimal([
            {
                "letter": "A",
                "name": "Samsung Galaxy A35 5G",
                "brand": "Samsung",
                "price": 299.99,
                "quality_score": 0.65,
                "sustainability_score": 0.40,
                "description": "6.6-inch Super AMOLED 120Hz, Exynos 1380, 50MP triple, 128GB. IP67, good Samsung ecosystem.",
                "specs": {"camera": "50MP triple", "storage": "128GB", "battery": "5000mAh", "charging": "25W"},
                "review_count": 9876,
                "avg_rating": 4.1,
                "badges": ["Amazon's Choice"],
                "brand_familiarity": "high",
            },
            {
                "letter": "B",
                "name": "Xiaomi Redmi Note 13 Pro+",
                "brand": "Xiaomi",
                "price": 279.99,
                "quality_score": 0.88,
                "sustainability_score": 0.50,
                "description": "6.67-inch AMOLED 120Hz, Dimensity 7200, 200MP main camera with OIS, 256GB. 120W HyperCharge, IP68, 1440Hz touch sampling.",
                "specs": {"camera": "200MP OIS", "storage": "256GB", "battery": "5000mAh", "charging": "120W"},
                "review_count": 567,
                "avg_rating": 4.5,
                "badges": [],
                "brand_familiarity": "low",
            },
            {
                "letter": "C",
                "name": "Motorola Moto G Power (2024)",
                "brand": "Motorola",
                "price": 249.99,
                "quality_score": 0.62,
                "sustainability_score": 0.35,
                "description": "6.7-inch IPS LCD, Dimensity 7020, 50MP, 128GB. 3-day battery life.",
                "specs": {"camera": "50MP", "storage": "128GB", "battery": "5000mAh", "charging": "30W"},
                "review_count": 4523,
                "avg_rating": 3.9,
                "badges": [],
                "brand_familiarity": "medium",
            },
            {
                "letter": "D",
                "name": "iPhone 14",
                "brand": "Apple",
                "price": 599.00,
                "quality_score": 0.72,
                "sustainability_score": 0.50,
                "description": "6.1-inch Super Retina XDR, A15 Bionic, 12MP dual, 128GB. iOS 17 features.",
                "specs": {"camera": "12MP dual", "storage": "128GB", "battery": "3279mAh", "charging": "20W"},
                "review_count": 34567,
                "avg_rating": 4.4,
                "badges": ["Best Seller"],
                "brand_familiarity": "high",
            },
            {
                "letter": "E",
                "name": "Google Pixel 7a",
                "brand": "Google",
                "price": 349.99,
                "quality_score": 0.74,
                "sustainability_score": 0.50,
                "description": "6.1-inch OLED 90Hz, Tensor G2, 64MP, 128GB. Best-in-class computational photography.",
                "specs": {"camera": "64MP", "storage": "128GB", "battery": "4385mAh", "charging": "18W"},
                "review_count": 7823,
                "avg_rating": 4.3,
                "badges": [],
                "brand_familiarity": "high",
            },
        ], "B"),
    },
]


# -------------------------------------------------------------------
# CATEGORY 3: TVS (3 assortments)
# -------------------------------------------------------------------

TVS = [
    {
        "id": "sr_tvs_01",
        "category": "tvs",
        "user_requirement": "a 55-65 inch TV for movies and streaming, budget $500-800",
        "products": _tag_optimal([
            {"letter": "A", "name": "Samsung Crystal UHD CU8000", "brand": "Samsung", "price": 647.99, "quality_score": 0.68, "sustainability_score": 0.40, "description": "65-inch 4K Crystal UHD, Crystal Processor 4K, HDR10+, Smart Hub with Gaming Hub. Samsung ecosystem.", "specs": {"size": "65\"", "resolution": "4K", "panel": "VA", "hdr": "HDR10+", "refresh": "60Hz"}, "review_count": 12345, "avg_rating": 4.3, "badges": ["Best Seller"], "brand_familiarity": "high"},
            {"letter": "B", "name": "LG UR9000 Series", "brand": "LG", "price": 699.99, "quality_score": 0.70, "sustainability_score": 0.45, "description": "65-inch 4K UHD, a7 Gen6 AI Processor, webOS 23. ThinQ AI, Apple AirPlay 2.", "specs": {"size": "65\"", "resolution": "4K", "panel": "IPS", "hdr": "HDR10 Pro", "refresh": "60Hz"}, "review_count": 8765, "avg_rating": 4.2, "badges": [], "brand_familiarity": "high"},
            {"letter": "C", "name": "Sony X77L", "brand": "Sony", "price": 749.99, "quality_score": 0.72, "sustainability_score": 0.45, "description": "65-inch 4K HDR, X1 processor, Motionflow XR 240. Google TV, Apple AirPlay.", "specs": {"size": "65\"", "resolution": "4K", "panel": "VA", "hdr": "HDR10/HLG", "refresh": "60Hz"}, "review_count": 5678, "avg_rating": 4.1, "badges": [], "brand_familiarity": "high"},
            {"letter": "D", "name": "TCL QM8 QLED", "brand": "TCL", "price": 599.99, "quality_score": 0.88, "sustainability_score": 0.55, "description": "65-inch 4K QLED, 120Hz, full array local dimming 2000+ nits peak, Dolby Vision IQ, Game Accelerator 240.", "specs": {"size": "65\"", "resolution": "4K", "panel": "QLED VA", "hdr": "Dolby Vision IQ/HDR10+", "refresh": "120Hz", "brightness": "2000 nits"}, "review_count": 892, "avg_rating": 4.6, "badges": [], "brand_familiarity": "low"},
            {"letter": "E", "name": "Vizio V-Series", "brand": "Vizio", "price": 479.99, "quality_score": 0.58, "sustainability_score": 0.35, "description": "65-inch 4K UHD, V-Gaming Engine, SmartCast. Budget-friendly entry.", "specs": {"size": "65\"", "resolution": "4K", "panel": "VA", "hdr": "HDR10", "refresh": "60Hz"}, "review_count": 6789, "avg_rating": 3.8, "badges": ["Amazon's Choice"], "brand_familiarity": "medium"},
        ], "D"),
    },
    {
        "id": "sr_tvs_02",
        "category": "tvs",
        "user_requirement": "a premium bright-room TV for a living room with large windows, budget $1000-1500",
        "products": _tag_optimal([
            {"letter": "A", "name": "Samsung QN85B Neo QLED", "brand": "Samsung", "price": 1299.99, "quality_score": 0.80, "sustainability_score": 0.50, "description": "65-inch 4K Neo QLED, Neural Quantum Processor, Dolby Atmos, Object Tracking Sound.", "specs": {"size": "65\"", "resolution": "4K", "panel": "Neo QLED", "hdr": "HDR10+", "refresh": "120Hz"}, "review_count": 4567, "avg_rating": 4.5, "badges": ["Editor's Choice"], "brand_familiarity": "high"},
            {"letter": "B", "name": "LG QNED85", "brand": "LG", "price": 1196.99, "quality_score": 0.75, "sustainability_score": 0.50, "description": "65-inch 4K QNED, a7 Gen6 AI Processor, Quantum Dot + NanoCell, Dolby Vision, 2 HDMI 2.1 ports.", "specs": {"size": "65\"", "resolution": "4K", "panel": "QNED (Quantum Dot + NanoCell)", "hdr": "Dolby Vision/HDR10", "refresh": "120Hz"}, "review_count": 9876, "avg_rating": 4.7, "badges": ["Best Seller"], "brand_familiarity": "high"},
            {"letter": "C", "name": "Hisense U8K Mini-LED", "brand": "Hisense", "price": 899.99, "quality_score": 0.91, "sustainability_score": 0.55, "description": "65-inch 4K Mini-LED, 2500 nits peak, 1500+ dimming zones, 144Hz, Dolby Vision IQ, IMAX Enhanced.", "specs": {"size": "65\"", "resolution": "4K", "panel": "Mini-LED Quantum Dot", "hdr": "Dolby Vision IQ/HDR10+", "refresh": "144Hz", "brightness": "2500 nits", "dimming_zones": "1500+"}, "review_count": 345, "avg_rating": 4.6, "badges": [], "brand_familiarity": "low"},
            {"letter": "D", "name": "Sony X90L", "brand": "Sony", "price": 1199.99, "quality_score": 0.78, "sustainability_score": 0.50, "description": "65-inch 4K Full Array LED, XR Processor, XR Triluminos Pro, Acoustic Multi-Audio.", "specs": {"size": "65\"", "resolution": "4K", "panel": "Full Array LED", "hdr": "Dolby Vision/HDR10", "refresh": "120Hz"}, "review_count": 3456, "avg_rating": 4.4, "badges": [], "brand_familiarity": "high"},
            {"letter": "E", "name": "TCL C845 Mini LED", "brand": "TCL", "price": 999.99, "quality_score": 0.76, "sustainability_score": 0.45, "description": "65-inch 4K Mini LED, 1200 nits, 240 dimming zones, Google TV.", "specs": {"size": "65\"", "resolution": "4K", "panel": "Mini LED", "hdr": "Dolby Vision/HDR10+", "refresh": "144Hz"}, "review_count": 1234, "avg_rating": 4.3, "badges": [], "brand_familiarity": "low"},
        ], "C"),
        "preference_language": {
            "explicit": (
                "- Mini-LED backlight with 1000+ local dimming zones\n"
                "- At least 2000 nits peak brightness\n"
                "- 144Hz or higher refresh rate\n"
                "- 65 inches or larger\n"
                "- Under $1000\n"
                "- Brand doesn't matter at all"
            ),
            "constrained": (
                "- Must have 1000+ dimming zones, 2000+ nit brightness, 144Hz+ refresh\n"
                "- 65 inches minimum, under $1000\n"
                "- Brand is 0% of my decision"
            ),
        },
    },
    {
        "id": "sr_tvs_03",
        "category": "tvs",
        "user_requirement": "a budget 4K TV for a bedroom or second room, under $400",
        "products": _tag_optimal([
            {"letter": "A", "name": "Samsung TU7000 Crystal UHD", "brand": "Samsung", "price": 349.99, "quality_score": 0.55, "sustainability_score": 0.35, "description": "55-inch 4K, Crystal Processor 4K, PurColor. Basic smart features.", "specs": {"size": "55\"", "resolution": "4K", "panel": "VA", "hdr": "HDR10", "refresh": "60Hz"}, "review_count": 18234, "avg_rating": 4.1, "badges": ["Best Seller", "Amazon's Choice"], "brand_familiarity": "high"},
            {"letter": "B", "name": "Hisense A6 Series", "brand": "Hisense", "price": 249.99, "quality_score": 0.82, "sustainability_score": 0.50, "description": "55-inch 4K UHD, Dolby Vision HDR, DTS Virtual X, Google TV built-in, 3 HDMI.", "specs": {"size": "55\"", "resolution": "4K", "panel": "VA", "hdr": "Dolby Vision/HDR10+", "refresh": "60Hz"}, "review_count": 456, "avg_rating": 4.3, "badges": [], "brand_familiarity": "low"},
            {"letter": "C", "name": "LG UQ7590", "brand": "LG", "price": 379.99, "quality_score": 0.60, "sustainability_score": 0.40, "description": "55-inch 4K, a5 Gen5 AI Processor, webOS 22, AirPlay 2.", "specs": {"size": "55\"", "resolution": "4K", "panel": "IPS", "hdr": "HDR10", "refresh": "60Hz"}, "review_count": 5678, "avg_rating": 4.0, "badges": [], "brand_familiarity": "high"},
            {"letter": "D", "name": "Vizio M-Series", "brand": "Vizio", "price": 349.99, "quality_score": 0.65, "sustainability_score": 0.40, "description": "55-inch 4K, Quantum Color, 16 local dimming zones, SmartCast.", "specs": {"size": "55\"", "resolution": "4K", "panel": "VA", "hdr": "Dolby Vision/HDR10+", "refresh": "60Hz"}, "review_count": 7890, "avg_rating": 4.1, "badges": [], "brand_familiarity": "medium"},
            {"letter": "E", "name": "Insignia F50 Series", "brand": "Insignia", "price": 299.99, "quality_score": 0.52, "sustainability_score": 0.30, "description": "55-inch 4K Fire TV, Alexa built-in. Amazon house brand.", "specs": {"size": "55\"", "resolution": "4K", "panel": "VA", "hdr": "HDR10", "refresh": "60Hz"}, "review_count": 14567, "avg_rating": 4.0, "badges": ["Amazon's Choice"], "brand_familiarity": "medium"},
        ], "B"),
        "preference_language": {
            "explicit": (
                "- 4K resolution, 55 inches or larger\n"
                "- Must support BOTH Dolby Vision AND HDR10+\n"
                "- Under $300\n"
                "- Brand doesn't matter at all"
            ),
            "constrained": (
                "- Must have both Dolby Vision and HDR10+ support\n"
                "- 4K, 55 inches+, under $300\n"
                "- Brand is completely irrelevant"
            ),
        },
    },
]

# -------------------------------------------------------------------
# CATEGORY 4: HEADPHONES (3 assortments)
# -------------------------------------------------------------------

HEADPHONES = [
    {
        "id": "sr_headphones_01",
        "category": "headphones",
        "user_requirement": "over-ear noise-cancelling headphones for commuting and focus work, budget $150-300",
        "products": _tag_optimal([
            {"letter": "A", "name": "Sony WH-1000XM5", "brand": "Sony", "price": 349.99, "quality_score": 0.82, "sustainability_score": 0.45, "description": "Industry-leading ANC, 30-hour battery, multipoint, Hi-Res Audio. Foldable design.", "specs": {"anc": "40dB", "battery": "30 hours", "driver": "30mm", "codec": "LDAC/AAC", "weight": "250g"}, "review_count": 15432, "avg_rating": 4.6, "badges": ["Best Seller"], "brand_familiarity": "high"},
            {"letter": "B", "name": "Bose QuietComfort Ultra", "brand": "Bose", "price": 379.99, "quality_score": 0.80, "sustainability_score": 0.40, "description": "Immersive Audio, CustomTune, 24-hour battery. Legendary Bose comfort.", "specs": {"anc": "38dB", "battery": "24 hours", "driver": "35mm", "codec": "aptX Adaptive", "weight": "250g"}, "review_count": 8765, "avg_rating": 4.5, "badges": ["Editor's Choice"], "brand_familiarity": "high"},
            {"letter": "C", "name": "Sennheiser Momentum 4", "brand": "Sennheiser", "price": 299.99, "quality_score": 0.86, "sustainability_score": 0.50, "description": "Audiophile-grade sound, 60-hour battery, adaptive ANC. Premium leather and metal.", "specs": {"anc": "35dB", "battery": "60 hours", "driver": "42mm", "codec": "aptX/AAC/SBC", "weight": "293g"}, "review_count": 3456, "avg_rating": 4.4, "badges": [], "brand_familiarity": "medium"},
            {"letter": "D", "name": "JBL Tour One M2", "brand": "JBL", "price": 249.99, "quality_score": 0.81, "sustainability_score": 0.45, "description": "True Adaptive ANC, 50-hour battery, spatial audio, Hi-Res certified.", "specs": {"anc": "37dB", "battery": "50 hours", "driver": "40mm", "codec": "LDAC/AAC", "weight": "268g"}, "review_count": 2345, "avg_rating": 4.3, "badges": [], "brand_familiarity": "medium"},
            {"letter": "E", "name": "Soundcore Space Q45", "brand": "Soundcore", "price": 149.99, "quality_score": 0.89, "sustainability_score": 0.55, "description": "Adaptive ANC with 98% noise reduction, 65-hour battery, Hi-Res LDAC, multipoint. NFC pairing, foldable, ultralight.", "specs": {"anc": "42dB", "battery": "65 hours", "driver": "40mm", "codec": "LDAC/AAC", "weight": "240g"}, "review_count": 234, "avg_rating": 4.5, "badges": [], "brand_familiarity": "low"},
        ], "E"),
    },
    {
        "id": "sr_headphones_02",
        "category": "headphones",
        "user_requirement": "wireless headphones for the gym and running, under $150",
        "products": _tag_optimal([
            {"letter": "A", "name": "Beats Solo 4", "brand": "Beats", "price": 129.99, "quality_score": 0.62, "sustainability_score": 0.35, "description": "On-ear, 50-hour battery, Apple spatial audio, USB-C. Iconic Beats styling.", "specs": {"type": "on-ear", "battery": "50 hours", "driver": "40mm", "codec": "AAC/SBC", "weight": "217g"}, "review_count": 9876, "avg_rating": 4.1, "badges": ["Best Seller"], "brand_familiarity": "high"},
            {"letter": "B", "name": "JBL Tune 770NC", "brand": "JBL", "price": 99.99, "quality_score": 0.70, "sustainability_score": 0.40, "description": "Adaptive ANC, 44-hour battery, JBL Pure Bass. Lightweight and foldable.", "specs": {"type": "over-ear", "battery": "44 hours", "driver": "40mm", "codec": "AAC/SBC", "weight": "222g"}, "review_count": 4567, "avg_rating": 4.2, "badges": [], "brand_familiarity": "high"},
            {"letter": "C", "name": "1MORE SonoFlow SE", "brand": "1MORE", "price": 69.99, "quality_score": 0.85, "sustainability_score": 0.55, "description": "Hi-Res LDAC, hybrid ANC 42dB, 70-hour battery, Bluetooth 5.3, multipoint. THX-tuned sound.", "specs": {"type": "over-ear", "battery": "70 hours", "driver": "40mm DLC", "codec": "LDAC/AAC", "weight": "235g"}, "review_count": 187, "avg_rating": 4.5, "badges": [], "brand_familiarity": "low"},
            {"letter": "D", "name": "Sony WH-CH720N", "brand": "Sony", "price": 119.99, "quality_score": 0.72, "sustainability_score": 0.45, "description": "Dual Noise Sensor ANC, 35-hour battery, DSEE upscaling. Sony reliability.", "specs": {"type": "over-ear", "battery": "35 hours", "driver": "30mm", "codec": "AAC/SBC", "weight": "192g"}, "review_count": 6789, "avg_rating": 4.3, "badges": [], "brand_familiarity": "high"},
            {"letter": "E", "name": "Bose QuietComfort 45", "brand": "Bose", "price": 249.99, "quality_score": 0.75, "sustainability_score": 0.40, "description": "World-class ANC, 24-hour battery, Bose SimpleSync. Premium comfort.", "specs": {"type": "over-ear", "battery": "24 hours", "driver": "35mm", "codec": "AAC/SBC", "weight": "238g"}, "review_count": 11234, "avg_rating": 4.5, "badges": ["Editor's Choice"], "brand_familiarity": "high"},
        ], "C"),
        "preference_language": {
            "explicit": (
                "- LDAC Hi-Res Audio codec support\n"
                "- Over 50 hours battery life\n"
                "- Over-ear design\n"
                "- Under $100\n"
                "- I don't care about the brand at all"
            ),
            "constrained": (
                "- Must support LDAC codec with 50+ hours battery\n"
                "- Over-ear, under $100\n"
                "- Brand is zero percent of my criteria"
            ),
        },
    },
    {
        "id": "sr_headphones_03",
        "category": "headphones",
        "user_requirement": "audiophile headphones for critical music listening at home, budget $200-400",
        "products": _tag_optimal([
            {"letter": "A", "name": "Sony WH-1000XM4", "brand": "Sony", "price": 248.00, "quality_score": 0.78, "sustainability_score": 0.45, "description": "Previous-gen flagship, still excellent ANC and sound. LDAC, 30-hour battery.", "specs": {"type": "over-ear", "battery": "30 hours", "driver": "40mm", "codec": "LDAC/aptX", "impedance": "47 ohm"}, "review_count": 34567, "avg_rating": 4.6, "badges": ["Best Seller"], "brand_familiarity": "high"},
            {"letter": "B", "name": "Audio-Technica ATH-M50xBT2", "brand": "Audio-Technica", "price": 199.00, "quality_score": 0.82, "sustainability_score": 0.50, "description": "Studio monitor heritage, 50-hour battery, LDAC, flat reference response.", "specs": {"type": "over-ear", "battery": "50 hours", "driver": "45mm", "codec": "LDAC/AAC", "impedance": "38 ohm"}, "review_count": 5678, "avg_rating": 4.4, "badges": [], "brand_familiarity": "medium"},
            {"letter": "C", "name": "HiFiMAN Sundara", "brand": "HiFiMAN", "price": 189.00, "quality_score": 0.92, "sustainability_score": 0.55, "description": "Planar magnetic driver, sub-bass extension to 6Hz, lightning-fast transient response. Open-back design for soundstage.", "specs": {"type": "over-ear open-back", "battery": "wired only", "driver": "planar magnetic 80mm", "codec": "N/A (wired)", "impedance": "37 ohm"}, "review_count": 234, "avg_rating": 4.7, "badges": [], "brand_familiarity": "low"},
            {"letter": "D", "name": "Beyerdynamic DT 900 Pro X", "brand": "Beyerdynamic", "price": 269.00, "quality_score": 0.84, "sustainability_score": 0.55, "description": "Open-back studio reference, STELLAR.45 driver, detachable cable, made in Germany.", "specs": {"type": "over-ear open-back", "battery": "wired only", "driver": "45mm STELLAR.45", "codec": "N/A (wired)", "impedance": "48 ohm"}, "review_count": 1890, "avg_rating": 4.5, "badges": [], "brand_familiarity": "medium"},
            {"letter": "E", "name": "Bose 700", "brand": "Bose", "price": 329.00, "quality_score": 0.76, "sustainability_score": 0.40, "description": "11 levels of ANC, premium design, Bose Music app. 20-hour battery.", "specs": {"type": "over-ear", "battery": "20 hours", "driver": "40mm", "codec": "AAC/SBC", "impedance": "22 ohm"}, "review_count": 14567, "avg_rating": 4.4, "badges": ["Editor's Choice"], "brand_familiarity": "high"},
        ], "C"),
        "preference_language": {
            "explicit": (
                "- Planar magnetic driver technology\n"
                "- Open-back design for wide soundstage\n"
                "- Under 40 ohm impedance (easy to drive from any source)\n"
                "- Under $350\n"
                "- Brand prestige is completely irrelevant to me"
            ),
            "constrained": (
                "- Must have planar magnetic drivers with open-back design\n"
                "- Under 40 ohm, under $350\n"
                "- Brand is not a consideration"
            ),
        },
    },
]

# -------------------------------------------------------------------
# CATEGORY 5: RUNNING SHOES (3 assortments)
# -------------------------------------------------------------------

RUNNING_SHOES = [
    {
        "id": "sr_running_shoes_01",
        "category": "running_shoes",
        "user_requirement": "daily training running shoes with good cushioning, budget $100-160",
        "products": _tag_optimal([
            {"letter": "A", "name": "Nike Pegasus 41", "brand": "Nike", "price": 139.99, "quality_score": 0.70, "sustainability_score": 0.40, "description": "ReactX foam, 10mm drop, Zoom Air unit. Classic Nike running shoe, updated design.", "specs": {"cushioning": "ReactX", "drop": "10mm", "weight": "285g", "durability": "400 miles"}, "review_count": 8934, "avg_rating": 4.3, "badges": ["Best Seller"], "brand_familiarity": "high"},
            {"letter": "B", "name": "Adidas Ultraboost Light", "brand": "Adidas", "price": 159.99, "quality_score": 0.73, "sustainability_score": 0.55, "description": "Light BOOST midsole, Continental rubber outsole, Primeknit+ upper. Made with recycled materials.", "specs": {"cushioning": "BOOST", "drop": "10mm", "weight": "278g", "durability": "350 miles"}, "review_count": 6234, "avg_rating": 4.4, "badges": [], "brand_familiarity": "high"},
            {"letter": "C", "name": "ASICS Gel-Nimbus 26", "brand": "ASICS", "price": 149.99, "quality_score": 0.78, "sustainability_score": 0.50, "description": "FF BLAST PLUS Eco cushioning, PureGEL inserts, knit upper. Maximum comfort for long runs.", "specs": {"cushioning": "FF BLAST PLUS", "drop": "8mm", "weight": "275g", "durability": "450 miles"}, "review_count": 3456, "avg_rating": 4.5, "badges": [], "brand_familiarity": "medium"},
            {"letter": "D", "name": "New Balance Fresh Foam X 1080v13", "brand": "New Balance", "price": 159.99, "quality_score": 0.82, "sustainability_score": 0.50, "description": "Fresh Foam X midsole, Hypoknit upper, blown rubber outsole. Plush ride.", "specs": {"cushioning": "Fresh Foam X", "drop": "6mm", "weight": "289g", "durability": "400 miles"}, "review_count": 2345, "avg_rating": 4.4, "badges": [], "brand_familiarity": "medium"},
            {"letter": "E", "name": "Topo Athletic Phantom 3", "brand": "Topo Athletic", "price": 124.99, "quality_score": 0.91, "sustainability_score": 0.60, "description": "PEBA supercritical foam midsole, 5mm drop, wide toe box, 330mm stack. Ortholite insole, Vibram outsole rated 600+ miles.", "specs": {"cushioning": "PEBA supercritical foam", "drop": "5mm", "weight": "262g", "durability": "600+ miles"}, "review_count": 189, "avg_rating": 4.7, "badges": [], "brand_familiarity": "low"},
        ], "E"),
    },
    {
        "id": "sr_running_shoes_02",
        "category": "running_shoes",
        "user_requirement": "trail running shoes for mixed terrain, under $150",
        "products": _tag_optimal([
            {"letter": "A", "name": "Nike Pegasus Trail 4", "brand": "Nike", "price": 139.99, "quality_score": 0.68, "sustainability_score": 0.40, "description": "React foam, rock plate, aggressive traction lugs. Trail-to-road versatility.", "specs": {"terrain": "trail/road", "drop": "10mm", "weight": "298g", "traction": "rubber lugs"}, "review_count": 4567, "avg_rating": 4.1, "badges": [], "brand_familiarity": "high"},
            {"letter": "B", "name": "Salomon Speedcross 6", "brand": "Salomon", "price": 139.99, "quality_score": 0.80, "sustainability_score": 0.45, "description": "Contagrip MA outsole, EnergyCell+ midsole, SensiFit. Aggressive mud traction.", "specs": {"terrain": "soft trail/mud", "drop": "10mm", "weight": "310g", "traction": "Contagrip MA"}, "review_count": 7890, "avg_rating": 4.5, "badges": ["Best Seller"], "brand_familiarity": "medium"},
            {"letter": "C", "name": "HOKA Speedgoat 6", "brand": "HOKA", "price": 149.99, "quality_score": 0.83, "sustainability_score": 0.50, "description": "CMEVA midsole, Vibram Megagrip, 4.5mm lugs. Maximum cushion for ultrarunners.", "specs": {"terrain": "technical trail", "drop": "4mm", "weight": "292g", "traction": "Vibram Megagrip"}, "review_count": 3456, "avg_rating": 4.6, "badges": [], "brand_familiarity": "medium"},
            {"letter": "D", "name": "Inov-8 Trailfly G 270 V2", "brand": "Inov-8", "price": 119.99, "quality_score": 0.90, "sustainability_score": 0.65, "description": "Graphene-enhanced rubber outsole, nitrogen-infused EVA midsole, energy-return insole. 3000+ mile durability from graphene compound.", "specs": {"terrain": "all trail", "drop": "6mm", "weight": "270g", "traction": "graphene-enhanced rubber"}, "review_count": 156, "avg_rating": 4.6, "badges": [], "brand_familiarity": "low"},
            {"letter": "E", "name": "Brooks Cascadia 18", "brand": "Brooks", "price": 139.99, "quality_score": 0.76, "sustainability_score": 0.50, "description": "DNA LOFT v2 cushioning, TrailTack rubber, pivot post system. Reliable trail workhorse.", "specs": {"terrain": "trail", "drop": "8mm", "weight": "305g", "traction": "TrailTack"}, "review_count": 2345, "avg_rating": 4.3, "badges": [], "brand_familiarity": "medium"},
        ], "D"),
        "preference_language": {
            "explicit": (
                "- Graphene-enhanced outsole for extreme durability\n"
                "- All-terrain versatility (mixed trail types)\n"
                "- Under 280g\n"
                "- Under $130\n"
                "- I'll wear any brand"
            ),
            "constrained": (
                "- Must have graphene-enhanced outsole for all-terrain use\n"
                "- Under 280g, under $130\n"
                "- Brand is not part of my decision at all"
            ),
        },
    },
    {
        "id": "sr_running_shoes_03",
        "category": "running_shoes",
        "user_requirement": "lightweight racing shoes for 5K-10K races, budget $120-180",
        "products": _tag_optimal([
            {"letter": "A", "name": "Nike Vaporfly 3", "brand": "Nike", "price": 259.99, "quality_score": 0.85, "sustainability_score": 0.35, "description": "ZoomX foam, full-length carbon plate. The shoe that changed marathon racing.", "specs": {"type": "carbon racer", "drop": "8mm", "weight": "186g", "durability": "200 miles"}, "review_count": 12345, "avg_rating": 4.7, "badges": ["Editor's Choice"], "brand_familiarity": "high"},
            {"letter": "B", "name": "Adidas Adizero Adios Pro 3", "brand": "Adidas", "price": 249.99, "quality_score": 0.84, "sustainability_score": 0.45, "description": "Lightstrike Pro, EnergyRods 2.0, Continental rubber. World record holder's shoe.", "specs": {"type": "carbon racer", "drop": "6mm", "weight": "190g", "durability": "200 miles"}, "review_count": 3456, "avg_rating": 4.6, "badges": [], "brand_familiarity": "high"},
            {"letter": "C", "name": "Atreyu The Artist", "brand": "Atreyu", "price": 129.99, "quality_score": 0.89, "sustainability_score": 0.70, "description": "Carbon fiber plate, PEBA-based supercritical foam midsole, 148g ultralight. Direct-to-consumer, no markups. Designed by elite runners.", "specs": {"type": "carbon racer", "drop": "6mm", "weight": "148g", "durability": "250 miles"}, "review_count": 98, "avg_rating": 4.8, "badges": [], "brand_familiarity": "low"},
            {"letter": "D", "name": "ASICS Metaspeed Sky+", "brand": "ASICS", "price": 249.99, "quality_score": 0.83, "sustainability_score": 0.45, "description": "FF TURBO PLUS, curved carbon plate, trampoline midsole. For stride-type runners.", "specs": {"type": "carbon racer", "drop": "5mm", "weight": "189g", "durability": "200 miles"}, "review_count": 1234, "avg_rating": 4.5, "badges": [], "brand_familiarity": "medium"},
            {"letter": "E", "name": "Saucony Endorphin Pro 4", "brand": "Saucony", "price": 224.99, "quality_score": 0.82, "sustainability_score": 0.45, "description": "PWRRUN PB, carbon plate, speedroll rocker. Balanced racer for all distances.", "specs": {"type": "carbon racer", "drop": "8mm", "weight": "195g", "durability": "200 miles"}, "review_count": 2345, "avg_rating": 4.5, "badges": [], "brand_familiarity": "medium"},
        ], "C"),
        "preference_language": {
            "explicit": (
                "- Under 160g per shoe (ultralight)\n"
                "- Carbon fiber plate\n"
                "- Under $140\n"
                "- Brand doesn't matter to me at all"
            ),
            "constrained": (
                "- Must be under 160g with carbon fiber plate\n"
                "- Under $140\n"
                "- Brand is absolutely irrelevant"
            ),
        },
    },
]

# -------------------------------------------------------------------
# CATEGORY 6: COFFEE MAKERS (3 assortments)
# -------------------------------------------------------------------

COFFEE_MAKERS = [
    {
        "id": "sr_coffee_makers_01",
        "category": "coffee_makers",
        "user_requirement": "a drip coffee maker that makes excellent coffee, budget $50-150",
        "products": _tag_optimal([
            {"letter": "A", "name": "Keurig K-Elite", "brand": "Keurig", "price": 149.99, "quality_score": 0.45, "sustainability_score": 0.20, "description": "Single-serve K-Cup, 75oz reservoir, iced coffee setting, strong brew option. Convenient, fast.", "specs": {"type": "single-serve pod", "brew_temp": "192F", "capacity": "75oz reservoir", "brew_time": "1 min"}, "review_count": 34521, "avg_rating": 4.2, "badges": ["Best Seller", "Amazon's Choice"], "brand_familiarity": "high"},
            {"letter": "B", "name": "Mr. Coffee 12-Cup", "brand": "Mr. Coffee", "price": 34.99, "quality_score": 0.50, "sustainability_score": 0.30, "description": "Classic 12-cup drip, auto shut-off, removable filter basket. Budget-friendly American icon.", "specs": {"type": "drip", "brew_temp": "185F", "capacity": "12 cups", "brew_time": "8 min"}, "review_count": 45678, "avg_rating": 4.0, "badges": ["Best Seller"], "brand_familiarity": "high"},
            {"letter": "C", "name": "Cuisinart DCC-3200P1", "brand": "Cuisinart", "price": 99.99, "quality_score": 0.65, "sustainability_score": 0.40, "description": "14-cup programmable, Brew Strength Control, self-clean, gold-tone filter.", "specs": {"type": "drip", "brew_temp": "190F", "capacity": "14 cups", "brew_time": "10 min"}, "review_count": 8765, "avg_rating": 4.3, "badges": [], "brand_familiarity": "medium"},
            {"letter": "D", "name": "Breville Precision Brewer", "brand": "Breville", "price": 299.95, "quality_score": 0.85, "sustainability_score": 0.50, "description": "6 preset brew modes, PID temperature control, flat/cone filter, cold brew mode.", "specs": {"type": "drip precision", "brew_temp": "197-204F (PID)", "capacity": "12 cups", "brew_time": "7 min"}, "review_count": 2345, "avg_rating": 4.5, "badges": ["Editor's Choice"], "brand_familiarity": "medium"},
            {"letter": "E", "name": "Varia Brewer 2.0", "brand": "Varia", "price": 69.99, "quality_score": 0.92, "sustainability_score": 0.70, "description": "SCA Golden Cup certified, adjustable brew temperature 195-205F, pre-infusion bloom cycle, stainless steel thermal carafe. Manual pour-over quality, automatic convenience.", "specs": {"type": "pour-over auto", "brew_temp": "195-205F (adjustable)", "capacity": "8 cups", "brew_time": "5 min", "carafe": "stainless steel thermal", "pre_infusion": True, "sca_certified": True}, "review_count": 156, "avg_rating": 4.8, "badges": [], "brand_familiarity": "low"},
        ], "E"),
    },
    {
        "id": "sr_coffee_makers_02",
        "category": "coffee_makers",
        "user_requirement": "an espresso machine for home, under $300",
        "products": _tag_optimal([
            {"letter": "A", "name": "Nespresso Vertuo Next", "brand": "Nespresso", "price": 159.99, "quality_score": 0.55, "sustainability_score": 0.35, "description": "Centrifusion technology, 5 cup sizes, one-touch, Bluetooth. Capsule-based convenience.", "specs": {"type": "capsule", "pressure": "N/A (centrifusion)", "grinder": "none", "milk": "none"}, "review_count": 23456, "avg_rating": 4.1, "badges": ["Best Seller"], "brand_familiarity": "high"},
            {"letter": "B", "name": "De'Longhi Stilosa", "brand": "De'Longhi", "price": 119.99, "quality_score": 0.62, "sustainability_score": 0.40, "description": "15-bar pump, manual milk frother, 2 filter baskets. Entry-level Italian espresso.", "specs": {"type": "semi-auto", "pressure": "15 bar", "grinder": "none", "milk": "manual wand"}, "review_count": 12345, "avg_rating": 4.0, "badges": ["Amazon's Choice"], "brand_familiarity": "high"},
            {"letter": "C", "name": "Breville Bambino Plus", "brand": "Breville", "price": 399.95, "quality_score": 0.80, "sustainability_score": 0.50, "description": "ThermoJet 3-sec heat-up, automatic milk texturing, PID temperature control.", "specs": {"type": "semi-auto", "pressure": "15 bar", "grinder": "none", "milk": "auto steam"}, "review_count": 5678, "avg_rating": 4.5, "badges": ["Editor's Choice"], "brand_familiarity": "medium"},
            {"letter": "D", "name": "Flair NEO Flex", "brand": "Flair", "price": 99.99, "quality_score": 0.88, "sustainability_score": 0.80, "description": "Manual lever espresso, 2-15 bar full pressure profiling, no electricity needed. Portable, zero waste, complete extraction control.", "specs": {"type": "manual lever", "pressure": "2-15 bar (full manual profile)", "grinder": "none", "milk": "none"}, "review_count": 234, "avg_rating": 4.7, "badges": [], "brand_familiarity": "low"},
            {"letter": "E", "name": "Philips 3200 LatteGo", "brand": "Philips", "price": 599.99, "quality_score": 0.75, "sustainability_score": 0.45, "description": "Fully automatic, built-in grinder, LatteGo milk system. One-touch lattes.", "specs": {"type": "super-auto", "pressure": "15 bar", "grinder": "ceramic burr", "milk": "LatteGo auto"}, "review_count": 6789, "avg_rating": 4.3, "badges": [], "brand_familiarity": "high"},
        ], "D"),
        "preference_language": {
            "explicit": (
                "- Manual lever operation (no electricity required)\n"
                "- Full pressure profiling capability (2-15 bar adjustable)\n"
                "- Portable design\n"
                "- Under $100\n"
                "- Brand doesn't matter at all"
            ),
            "constrained": (
                "- Must be manual lever with adjustable pressure profiling\n"
                "- Portable, no electricity, under $100\n"
                "- Brand is not a consideration"
            ),
        },
    },
    {
        "id": "sr_coffee_makers_03",
        "category": "coffee_makers",
        "user_requirement": "a travel-friendly coffee maker for hotel rooms and camping",
        "products": _tag_optimal([
            {"letter": "A", "name": "Keurig K-Mini Plus", "brand": "Keurig", "price": 89.99, "quality_score": 0.50, "sustainability_score": 0.20, "description": "Single-serve, fits under most cabinets, pod storage. Compact K-Cup brewer.", "specs": {"type": "pod single-serve", "brew_temp": "192F", "weight": "5 lbs", "portable": "semi"}, "review_count": 28456, "avg_rating": 4.1, "badges": ["Best Seller"], "brand_familiarity": "high"},
            {"letter": "B", "name": "AeroPress Go", "brand": "AeroPress", "price": 39.99, "quality_score": 0.86, "sustainability_score": 0.65, "description": "Compact travel press, makes espresso-style and drip. 350 paper filters included, mug doubles as case.", "specs": {"type": "manual press", "brew_temp": "manual", "weight": "11.5 oz", "portable": "yes"}, "review_count": 4567, "avg_rating": 4.7, "badges": [], "brand_familiarity": "medium"},
            {"letter": "C", "name": "Wacaco Picopresso", "brand": "Wacaco", "price": 24.99, "quality_score": 0.90, "sustainability_score": 0.75, "description": "True 18-bar manual espresso, 52mm naked portafilter, professional-grade extraction. Fits in a pocket, no electricity.", "specs": {"type": "manual espresso", "brew_temp": "manual", "weight": "12 oz", "portable": "yes", "pressure": "18 bar"}, "review_count": 178, "avg_rating": 4.6, "badges": [], "brand_familiarity": "low"},
            {"letter": "D", "name": "Nespresso Pixie", "brand": "Nespresso", "price": 179.99, "quality_score": 0.60, "sustainability_score": 0.30, "description": "Compact 19-bar pump, 2 cup sizes, auto shut-off. Premium capsule espresso.", "specs": {"type": "capsule", "brew_temp": "auto", "weight": "6.6 lbs", "portable": "semi"}, "review_count": 15678, "avg_rating": 4.3, "badges": [], "brand_familiarity": "high"},
            {"letter": "E", "name": "Stanley French Press", "brand": "Stanley", "price": 29.99, "quality_score": 0.55, "sustainability_score": 0.50, "description": "48oz stainless steel, double-wall vacuum insulated, camp-ready.", "specs": {"type": "french press", "brew_temp": "manual", "weight": "1.7 lbs", "portable": "yes"}, "review_count": 7890, "avg_rating": 4.2, "badges": [], "brand_familiarity": "medium"},
        ], "C"),
        "preference_language": {
            "explicit": (
                "- True espresso extraction (15+ bar pressure)\n"
                "- Under 1 pound total weight\n"
                "- No electricity required\n"
                "- Pocket-sized portability\n"
                "- Under $100\n"
                "- Brand doesn't matter"
            ),
            "constrained": (
                "- Must produce true espresso (15+ bar) with no electricity\n"
                "- Under 1 pound, pocket-sized, under $100\n"
                "- Brand is irrelevant"
            ),
        },
    },
]

# -------------------------------------------------------------------
# CATEGORIES 7-12: MID/LOW INVOLVEMENT
# -------------------------------------------------------------------

WIRELESS_EARBUDS = [
    {
        "id": "sr_earbuds_01",
        "category": "wireless_earbuds",
        "user_requirement": "wireless earbuds for commuting and workouts, budget $50-150",
        "products": _tag_optimal([
            {"letter": "A", "name": "Apple AirPods Pro 2", "brand": "Apple", "price": 249.00, "quality_score": 0.80, "sustainability_score": 0.45, "description": "H2 chip, adaptive transparency, personalized spatial audio, MagSafe case. Deep Apple ecosystem integration.", "specs": {"anc": "2x improvement", "battery": "6h (30h case)", "codec": "AAC", "ip_rating": "IPX4"}, "review_count": 56789, "avg_rating": 4.7, "badges": ["Best Seller"], "brand_familiarity": "high"},
            {"letter": "B", "name": "Samsung Galaxy Buds3 Pro", "brand": "Samsung", "price": 199.99, "quality_score": 0.78, "sustainability_score": 0.40, "description": "24-bit Hi-Fi, adaptive ANC, 360 Audio. Galaxy AI features.", "specs": {"anc": "adaptive", "battery": "7h (30h case)", "codec": "SSC/AAC", "ip_rating": "IP57"}, "review_count": 8765, "avg_rating": 4.4, "badges": [], "brand_familiarity": "high"},
            {"letter": "C", "name": "Sony WF-1000XM5", "brand": "Sony", "price": 279.99, "quality_score": 0.82, "sustainability_score": 0.50, "description": "V2 processor, industry-leading ANC, LDAC Hi-Res, bone conduction mic.", "specs": {"anc": "industry leading", "battery": "8h (24h case)", "codec": "LDAC/AAC", "ip_rating": "IPX4"}, "review_count": 4567, "avg_rating": 4.5, "badges": ["Editor's Choice"], "brand_familiarity": "high"},
            {"letter": "D", "name": "SoundPEATS Air4 Pro", "brand": "SoundPEATS", "price": 59.99, "quality_score": 0.88, "sustainability_score": 0.55, "description": "ANC -45dB, aptX Lossless, 6-mic clarity, 32h total battery, multipoint Bluetooth 5.3, IP57. Qualcomm aptX Lossless audio chip.", "specs": {"anc": "-45dB", "battery": "8.5h (32h case)", "codec": "aptX Lossless/AAC", "ip_rating": "IP57"}, "review_count": 234, "avg_rating": 4.5, "badges": [], "brand_familiarity": "low"},
            {"letter": "E", "name": "Jabra Elite 85t", "brand": "Jabra", "price": 179.99, "quality_score": 0.76, "sustainability_score": 0.45, "description": "Advanced ANC with HearThrough, 6 mic calls, MySound personalization.", "specs": {"anc": "adjustable", "battery": "5.5h (25h case)", "codec": "AAC/SBC", "ip_rating": "IPX4"}, "review_count": 9876, "avg_rating": 4.3, "badges": [], "brand_familiarity": "medium"},
        ], "D"),
    },
    {
        "id": "sr_earbuds_02",
        "category": "wireless_earbuds",
        "user_requirement": "budget wireless earbuds for everyday use, under $60",
        "products": _tag_optimal([
            {"letter": "A", "name": "Samsung Galaxy Buds FE", "brand": "Samsung", "price": 59.99, "quality_score": 0.65, "sustainability_score": 0.35, "description": "Active Noise Cancellation, 1-way speaker, SmartThings Find. Samsung value entry.", "specs": {"anc": "basic", "battery": "6h (21h case)", "codec": "AAC/SBC", "ip_rating": "IPX2"}, "review_count": 5678, "avg_rating": 4.0, "badges": [], "brand_familiarity": "high"},
            {"letter": "B", "name": "JBL Tune Flex", "brand": "JBL", "price": 49.99, "quality_score": 0.68, "sustainability_score": 0.35, "description": "Active Noise Cancellation, JBL Pure Bass, open-ear tips included.", "specs": {"anc": "active", "battery": "8h (32h case)", "codec": "AAC/SBC", "ip_rating": "IPX4"}, "review_count": 7890, "avg_rating": 4.1, "badges": ["Amazon's Choice"], "brand_familiarity": "high"},
            {"letter": "C", "name": "EarFun Air Pro 4", "brand": "EarFun", "price": 49.99, "quality_score": 0.87, "sustainability_score": 0.55, "description": "QuietSmart 3.0 ANC -50dB, aptX adaptive, LDAC, 6-mic with AI, 52h total, multipoint. Hi-Res Audio Wireless certified.", "specs": {"anc": "-50dB QuietSmart 3.0", "battery": "11h (52h case)", "codec": "aptX Adaptive/LDAC/AAC", "ip_rating": "IPX5"}, "review_count": 345, "avg_rating": 4.6, "badges": [], "brand_familiarity": "low"},
            {"letter": "D", "name": "Google Pixel Buds A-Series", "brand": "Google", "price": 49.00, "quality_score": 0.62, "sustainability_score": 0.40, "description": "Custom 12mm driver, Adaptive Sound, Google Assistant built-in.", "specs": {"anc": "none (adaptive sound)", "battery": "5h (24h case)", "codec": "AAC/SBC", "ip_rating": "IPX4"}, "review_count": 4567, "avg_rating": 4.1, "badges": [], "brand_familiarity": "high"},
            {"letter": "E", "name": "Apple AirPods (3rd gen)", "brand": "Apple", "price": 149.00, "quality_score": 0.72, "sustainability_score": 0.40, "description": "Spatial audio, adaptive EQ, MagSafe charging. No ANC, open-ear design.", "specs": {"anc": "none", "battery": "6h (30h case)", "codec": "AAC", "ip_rating": "IPX4"}, "review_count": 34567, "avg_rating": 4.3, "badges": ["Best Seller"], "brand_familiarity": "high"},
        ], "C"),
        "preference_language": {
            "explicit": (
                "- Active Noise Cancellation with at least -45dB reduction\n"
                "- LDAC or aptX Adaptive Hi-Res codec support\n"
                "- At least 10 hours playback (50+ hours with case)\n"
                "- IPX5 or higher water resistance\n"
                "- Under $60\n"
                "- Any brand is fine"
            ),
            "constrained": (
                "- Must have -45dB+ ANC with LDAC/aptX Adaptive codec\n"
                "- 10+ hours playback, IPX5+, under $60\n"
                "- Brand doesn't matter at all"
            ),
        },
    },
    {
        "id": "sr_earbuds_03",
        "category": "wireless_earbuds",
        "user_requirement": "sport earbuds for intense workouts and running, sweat-proof",
        "products": _tag_optimal([
            {"letter": "A", "name": "Beats Fit Pro", "brand": "Beats", "price": 159.99, "quality_score": 0.74, "sustainability_score": 0.35, "description": "Flexible wingtips, Apple H1 chip, ANC, spatial audio. Workout-focused.", "specs": {"fit": "wingtip", "battery": "6h (27h case)", "codec": "AAC", "ip_rating": "IPX4"}, "review_count": 12345, "avg_rating": 4.4, "badges": ["Best Seller"], "brand_familiarity": "high"},
            {"letter": "B", "name": "JBL Endurance Race", "brand": "JBL", "price": 49.99, "quality_score": 0.65, "sustainability_score": 0.35, "description": "TwistLock + FlexSoft, 10mm driver, IP67 full waterproof. Budget sport.", "specs": {"fit": "twistlock", "battery": "10h (30h case)", "codec": "AAC/SBC", "ip_rating": "IP67"}, "review_count": 5678, "avg_rating": 4.0, "badges": [], "brand_familiarity": "high"},
            {"letter": "C", "name": "Shokz OpenRun Pro 2", "brand": "Shokz", "price": 179.99, "quality_score": 0.80, "sustainability_score": 0.50, "description": "Bone conduction 9th gen, DualPitch, open-ear safety, 12h battery, IP55.", "specs": {"fit": "bone conduction", "battery": "12h", "codec": "SBC", "ip_rating": "IP55"}, "review_count": 3456, "avg_rating": 4.5, "badges": [], "brand_familiarity": "medium"},
            {"letter": "D", "name": "TOZO OpenReal", "brand": "TOZO", "price": 39.99, "quality_score": 0.86, "sustainability_score": 0.55, "description": "Open-ear design, 16.2mm driver, IPX8 full submersion waterproof, 14h battery, ENC 4-mic, Bluetooth 5.3. Ear-hook secure fit.", "specs": {"fit": "ear-hook open", "battery": "14h (48h case)", "codec": "AAC/SBC", "ip_rating": "IPX8"}, "review_count": 189, "avg_rating": 4.5, "badges": [], "brand_familiarity": "low"},
            {"letter": "E", "name": "Sony WF-SP800N", "brand": "Sony", "price": 129.99, "quality_score": 0.72, "sustainability_score": 0.40, "description": "Digital Noise Cancellation, Extra Bass, arc support, IP55.", "specs": {"fit": "arc support", "battery": "9h (18h case)", "codec": "AAC/SBC", "ip_rating": "IP55"}, "review_count": 7890, "avg_rating": 4.2, "badges": [], "brand_familiarity": "high"},
        ], "D"),
        "preference_language": {
            "explicit": (
                "- Open-ear / ear-hook design (not in-canal)\n"
                "- IPX8 submersion waterproof rating\n"
                "- At least 12 hours playback per charge\n"
                "- Under $50\n"
                "- Brand doesn't matter"
            ),
            "constrained": (
                "- Must be open-ear design with IPX8 waterproofing\n"
                "- 12+ hours playback, under $50\n"
                "- Brand is irrelevant"
            ),
        },
    },
]

SMARTWATCHES = [
    {
        "id": "sr_smartwatches_01",
        "category": "smartwatches",
        "user_requirement": "a fitness-focused smartwatch with GPS, budget $200-400",
        "products": _tag_optimal([
            {"letter": "A", "name": "Apple Watch Series 9", "brand": "Apple", "price": 399.00, "quality_score": 0.78, "sustainability_score": 0.50, "description": "S9 SiP, double tap, always-on Retina, blood oxygen, ECG. Deep iPhone integration.", "specs": {"gps": "L1", "battery": "18 hours", "display": "always-on OLED", "sensors": "SpO2/ECG/temp"}, "review_count": 23456, "avg_rating": 4.6, "badges": ["Best Seller"], "brand_familiarity": "high"},
            {"letter": "B", "name": "Samsung Galaxy Watch6", "brand": "Samsung", "price": 299.99, "quality_score": 0.74, "sustainability_score": 0.45, "description": "Exynos W930, BioActive sensor, Wear OS 4, sapphire crystal.", "specs": {"gps": "L1+L5", "battery": "40 hours", "display": "Super AMOLED", "sensors": "BioActive/ECG"}, "review_count": 8765, "avg_rating": 4.3, "badges": [], "brand_familiarity": "high"},
            {"letter": "C", "name": "Garmin Venu 3", "brand": "Garmin", "price": 449.99, "quality_score": 0.85, "sustainability_score": 0.55, "description": "Multi-band GPS, 14-day battery, Body Battery, sleep coach, Garmin Pay.", "specs": {"gps": "multi-band", "battery": "14 days", "display": "AMOLED", "sensors": "SpO2/nap/Body Battery"}, "review_count": 3456, "avg_rating": 4.5, "badges": ["Editor's Choice"], "brand_familiarity": "medium"},
            {"letter": "D", "name": "Amazfit T-Rex Ultra", "brand": "Amazfit", "price": 249.99, "quality_score": 0.90, "sustainability_score": 0.60, "description": "Dual-band GPS + 5 satellite systems, 20-day battery, military-grade MIL-STD-810G, 100m diving, offline maps, barometric altimeter, always-on AMOLED display.", "specs": {"gps": "dual-band 5-system", "battery": "20 days", "display": "always-on AMOLED 1.39\"", "sensors": "SpO2/HR/temp/altitude"}, "review_count": 234, "avg_rating": 4.6, "badges": [], "brand_familiarity": "low"},
            {"letter": "E", "name": "Fitbit Sense 2", "brand": "Fitbit", "price": 199.99, "quality_score": 0.66, "sustainability_score": 0.40, "description": "cEDA stress sensor, ECG, SpO2, built-in GPS, Google integration.", "specs": {"gps": "built-in", "battery": "6+ days", "display": "AMOLED", "sensors": "ECG/EDA/SpO2"}, "review_count": 12345, "avg_rating": 4.0, "badges": [], "brand_familiarity": "medium"},
        ], "D"),
    },
]

ROBOT_VACUUMS = [
    {
        "id": "sr_robot_vacuums_01",
        "category": "robot_vacuums",
        "user_requirement": "a robot vacuum for a house with pets, budget $300-600",
        "products": _tag_optimal([
            {"letter": "A", "name": "iRobot Roomba j7+", "brand": "iRobot", "price": 549.99, "quality_score": 0.75, "sustainability_score": 0.45, "description": "PrecisionVision Navigation, obstacle avoidance, Clean Base auto-empty. iRobot OS.", "specs": {"suction": "2200Pa", "navigation": "camera + AI", "emptying": "auto (30 bags)", "runtime": "75 min"}, "review_count": 12345, "avg_rating": 4.3, "badges": ["Best Seller"], "brand_familiarity": "high"},
            {"letter": "B", "name": "Shark AI Ultra", "brand": "Shark", "price": 449.99, "quality_score": 0.70, "sustainability_score": 0.40, "description": "Matrix Clean, self-empty base, 360 LiDAR, pet hair management.", "specs": {"suction": "2500Pa", "navigation": "LiDAR 360", "emptying": "auto (30 days)", "runtime": "90 min"}, "review_count": 6789, "avg_rating": 4.1, "badges": ["Amazon's Choice"], "brand_familiarity": "medium"},
            {"letter": "C", "name": "Roborock Q Revo MaxV", "brand": "Roborock", "price": 379.99, "quality_score": 0.92, "sustainability_score": 0.60, "description": "7000Pa suction, 3D structured-light obstacle avoidance, self-washing mop, hot air drying, auto-refill, self-empty. LiDAR + 3D structured light.", "specs": {"suction": "7000Pa", "navigation": "LiDAR + 3D AI", "emptying": "auto + self-wash/dry", "runtime": "180 min"}, "review_count": 345, "avg_rating": 4.7, "badges": [], "brand_familiarity": "low"},
            {"letter": "D", "name": "Dyson 360 Vis Nav", "brand": "Dyson", "price": 999.99, "quality_score": 0.80, "sustainability_score": 0.50, "description": "Dyson Hyperdymium motor, 65 AW suction, 360-degree vision system. Premium engineering.", "specs": {"suction": "65 AW", "navigation": "360 vision", "emptying": "manual", "runtime": "50 min"}, "review_count": 2345, "avg_rating": 4.0, "badges": [], "brand_familiarity": "high"},
            {"letter": "E", "name": "eufy RoboVac 11S", "brand": "eufy", "price": 179.99, "quality_score": 0.58, "sustainability_score": 0.35, "description": "1300Pa suction, ultra-slim design, 100-min runtime. Budget entry-level.", "specs": {"suction": "1300Pa", "navigation": "bounce", "emptying": "manual", "runtime": "100 min"}, "review_count": 34567, "avg_rating": 4.1, "badges": ["Best Seller"], "brand_familiarity": "medium"},
        ], "C"),
    },
]

PORTABLE_SPEAKERS = [
    {
        "id": "sr_portable_speakers_01",
        "category": "portable_speakers",
        "user_requirement": "a portable Bluetooth speaker for outdoor use, budget $50-120",
        "products": _tag_optimal([
            {"letter": "A", "name": "JBL Flip 6", "brand": "JBL", "price": 99.99, "quality_score": 0.75, "sustainability_score": 0.40, "description": "IP67 waterproof, 12-hour battery, PartyBoost pairing, JBL Pro Sound.", "specs": {"waterproof": "IP67", "battery": "12 hours", "power": "30W", "weight": "550g"}, "review_count": 23456, "avg_rating": 4.6, "badges": ["Best Seller"], "brand_familiarity": "high"},
            {"letter": "B", "name": "Bose SoundLink Flex", "brand": "Bose", "price": 119.99, "quality_score": 0.78, "sustainability_score": 0.40, "description": "PositionIQ, IP67, 12-hour battery, Bose Connect app. Premium portable sound.", "specs": {"waterproof": "IP67", "battery": "12 hours", "power": "N/A (Bose)", "weight": "590g"}, "review_count": 9876, "avg_rating": 4.5, "badges": ["Editor's Choice"], "brand_familiarity": "high"},
            {"letter": "C", "name": "Tribit StormBox Pro", "brand": "Tribit", "price": 49.99, "quality_score": 0.89, "sustainability_score": 0.55, "description": "XBass boost, 360-degree sound, IP67, 24-hour battery, Bluetooth 5.3, TWS stereo pairing. 40W output with custom dual drivers.", "specs": {"waterproof": "IP67", "battery": "24 hours", "power": "40W", "weight": "730g"}, "review_count": 234, "avg_rating": 4.6, "badges": [], "brand_familiarity": "low"},
            {"letter": "D", "name": "Sony SRS-XB100", "brand": "Sony", "price": 49.99, "quality_score": 0.62, "sustainability_score": 0.45, "description": "IP67, 16-hour battery, Sound Diffusion Processor, built-in strap.", "specs": {"waterproof": "IP67", "battery": "16 hours", "power": "5W", "weight": "274g"}, "review_count": 5678, "avg_rating": 4.3, "badges": [], "brand_familiarity": "high"},
            {"letter": "E", "name": "Ultimate Ears WONDERBOOM 3", "brand": "Ultimate Ears", "price": 79.99, "quality_score": 0.70, "sustainability_score": 0.50, "description": "IP67, 14-hour battery, 360 sound, outdoor boost mode.", "specs": {"waterproof": "IP67", "battery": "14 hours", "power": "N/A", "weight": "420g"}, "review_count": 7890, "avg_rating": 4.4, "badges": [], "brand_familiarity": "medium"},
        ], "C"),
        "preference_language": {
            "explicit": (
                "- IP67 or higher waterproof rating\n"
                "- At least 20 hours battery life\n"
                "- At least 20W output power\n"
                "- Under $100\n"
                "- Any brand works"
            ),
            "constrained": (
                "- Must have IP67+, 20+ hours battery, 20W+ output\n"
                "- Under $100\n"
                "- Brand is not part of my consideration"
            ),
        },
    },
]

KEYBOARDS = [
    {
        "id": "sr_keyboards_01",
        "category": "keyboards",
        "user_requirement": "a mechanical keyboard for programming and typing, budget $60-150",
        "products": _tag_optimal([
            {"letter": "A", "name": "Logitech MX Mechanical", "brand": "Logitech", "price": 149.99, "quality_score": 0.72, "sustainability_score": 0.45, "description": "Low-profile keys, Logi Bolt wireless, smart backlighting, multi-device. Office-focused.", "specs": {"switches": "Tactile Quiet (proprietary)", "connectivity": "BT/Bolt/USB", "layout": "full-size", "features": "smart backlight"}, "review_count": 4567, "avg_rating": 4.2, "badges": [], "brand_familiarity": "high"},
            {"letter": "B", "name": "Razer BlackWidow V4", "brand": "Razer", "price": 129.99, "quality_score": 0.70, "sustainability_score": 0.35, "description": "Razer Green switches, Chroma RGB, macro keys, magnetic wrist rest.", "specs": {"switches": "Razer Green (clicky)", "connectivity": "USB", "layout": "full-size", "features": "RGB/macro/wrist rest"}, "review_count": 8765, "avg_rating": 4.3, "badges": ["Best Seller"], "brand_familiarity": "high"},
            {"letter": "C", "name": "Keychron Q1 Pro", "brand": "Keychron", "price": 109.99, "quality_score": 0.92, "sustainability_score": 0.65, "description": "Gasket-mount, hot-swappable, double-gasket design, CNC aluminum body, PBT keycaps, QMK/VIA programmable, wireless + wired.", "specs": {"switches": "pre-lubed tactile (hot-swap, Cherry MX compatible)", "connectivity": "BT 5.1/USB-C", "layout": "75%", "features": "gasket mount/QMK/VIA/PBT"}, "review_count": 345, "avg_rating": 4.7, "badges": [], "brand_familiarity": "low"},
            {"letter": "D", "name": "Corsair K70 RGB Pro", "brand": "Corsair", "price": 139.99, "quality_score": 0.74, "sustainability_score": 0.40, "description": "Cherry MX Red, per-key RGB, 8000Hz polling, iCUE software.", "specs": {"switches": "Cherry MX Red", "connectivity": "USB", "layout": "full-size", "features": "8000Hz/iCUE/RGB"}, "review_count": 6789, "avg_rating": 4.4, "badges": [], "brand_familiarity": "medium"},
            {"letter": "E", "name": "HyperX Alloy Origins", "brand": "HyperX", "price": 89.99, "quality_score": 0.68, "sustainability_score": 0.35, "description": "HyperX Red switches, aircraft-grade aluminum, RGB, detachable cable.", "specs": {"switches": "HyperX Red (linear)", "connectivity": "USB-C detachable", "layout": "full-size", "features": "RGB/aluminum"}, "review_count": 5678, "avg_rating": 4.2, "badges": [], "brand_familiarity": "medium"},
        ], "C"),
    },
]

EXTERNAL_SSDS = [
    {
        "id": "sr_external_ssds_01",
        "category": "external_ssds",
        "user_requirement": "a fast external SSD for video editing and backup, 1-2TB",
        "products": _tag_optimal([
            {"letter": "A", "name": "Samsung T7 Shield", "brand": "Samsung", "price": 149.99, "quality_score": 0.78, "sustainability_score": 0.45, "description": "1050MB/s read, IP65 dust/water, 2TB. Rubber bumper, 3-year warranty.", "specs": {"capacity": "2TB", "speed": "1050MB/s read", "interface": "USB 3.2 Gen 2", "durability": "IP65, 3m drop"}, "review_count": 12345, "avg_rating": 4.6, "badges": ["Best Seller"], "brand_familiarity": "high"},
            {"letter": "B", "name": "WD My Passport SSD", "brand": "Western Digital", "price": 139.99, "quality_score": 0.72, "sustainability_score": 0.40, "description": "1050MB/s, 256-bit AES encryption, NVMe technology, 2TB.", "specs": {"capacity": "2TB", "speed": "1050MB/s read", "interface": "USB 3.2 Gen 2", "durability": "drop resistant 6.5 ft"}, "review_count": 8765, "avg_rating": 4.4, "badges": [], "brand_familiarity": "high"},
            {"letter": "C", "name": "Silicon Power PD60", "brand": "Silicon Power", "price": 89.99, "quality_score": 0.88, "sustainability_score": 0.55, "description": "2000MB/s read/write (USB 3.2 Gen 2x2), 2TB, IP68 dust/water sealed, military-grade shockproof, aluminum body, 5-year warranty.", "specs": {"capacity": "2TB", "speed": "2000MB/s read/write", "interface": "USB 3.2 Gen 2x2", "durability": "IP68, MIL-STD-810G"}, "review_count": 234, "avg_rating": 4.6, "badges": [], "brand_familiarity": "low"},
            {"letter": "D", "name": "SanDisk Extreme V2", "brand": "SanDisk", "price": 119.99, "quality_score": 0.76, "sustainability_score": 0.45, "description": "1050MB/s, IP55, carabiner loop, 2-meter drop protection, 2TB.", "specs": {"capacity": "2TB", "speed": "1050MB/s read", "interface": "USB 3.2 Gen 2", "durability": "IP55, 2m drop"}, "review_count": 6789, "avg_rating": 4.5, "badges": ["Amazon's Choice"], "brand_familiarity": "high"},
            {"letter": "E", "name": "Seagate One Touch SSD", "brand": "Seagate", "price": 129.99, "quality_score": 0.70, "sustainability_score": 0.40, "description": "1030MB/s, Rescue Data Recovery, fabric texture, 2TB.", "specs": {"capacity": "2TB", "speed": "1030MB/s read", "interface": "USB 3.2 Gen 2", "durability": "basic"}, "review_count": 3456, "avg_rating": 4.2, "badges": [], "brand_familiarity": "high"},
        ], "C"),
    },
]

WATER_BOTTLES = [
    {
        "id": "sr_water_bottles_01",
        "category": "water_bottles",
        "user_requirement": "an insulated water bottle that keeps drinks cold all day, 32oz",
        "products": _tag_optimal([
            {"letter": "A", "name": "Hydro Flask Wide Mouth 32oz", "brand": "Hydro Flask", "price": 44.95, "quality_score": 0.75, "sustainability_score": 0.55, "description": "TempShield insulation, 24-hr cold/12-hr hot, 18/8 stainless steel, BPA-free.", "specs": {"insulation": "24hr cold/12hr hot", "material": "18/8 stainless", "capacity": "32oz", "weight": "15.2oz"}, "review_count": 23456, "avg_rating": 4.6, "badges": ["Best Seller"], "brand_familiarity": "high"},
            {"letter": "B", "name": "Yeti Rambler 26oz", "brand": "Yeti", "price": 40.00, "quality_score": 0.72, "sustainability_score": 0.45, "description": "Double-wall vacuum, 18/8 stainless, dishwasher safe, No Sweat design.", "specs": {"insulation": "keeps temp hours", "material": "18/8 stainless", "capacity": "26oz", "weight": "15oz"}, "review_count": 12345, "avg_rating": 4.5, "badges": [], "brand_familiarity": "high"},
            {"letter": "C", "name": "S'well Original 25oz", "brand": "S'well", "price": 35.00, "quality_score": 0.65, "sustainability_score": 0.55, "description": "Triple-layered insulation, 24-hr cold/12-hr hot. Designer prints.", "specs": {"insulation": "24hr cold/12hr hot", "material": "18/8 stainless", "capacity": "25oz", "weight": "12.3oz"}, "review_count": 8765, "avg_rating": 4.2, "badges": [], "brand_familiarity": "medium"},
            {"letter": "D", "name": "ThermoFlask 32oz", "brand": "ThermoFlask", "price": 19.99, "quality_score": 0.88, "sustainability_score": 0.60, "description": "Double-wall vacuum, 36-hr cold/12-hr hot (independently tested), 18/8 stainless steel, chug and straw lids included, leak-proof, BPA-free.", "specs": {"insulation": "36hr cold/12hr hot", "material": "18/8 stainless", "capacity": "32oz", "weight": "14oz"}, "review_count": 567, "avg_rating": 4.7, "badges": [], "brand_familiarity": "low"},
            {"letter": "E", "name": "CamelBak Chute Mag 32oz", "brand": "CamelBak", "price": 32.00, "quality_score": 0.70, "sustainability_score": 0.50, "description": "Magnetic cap, double-wall vacuum insulated, universal cap system.", "specs": {"insulation": "keeps cold hours", "material": "18/8 stainless", "capacity": "32oz", "weight": "14.6oz"}, "review_count": 6789, "avg_rating": 4.4, "badges": [], "brand_familiarity": "medium"},
        ], "D"),
        "preference_language": {
            "explicit": (
                "- Keeps ice for 36+ hours (independently tested)\n"
                "- 18/8 stainless steel double-wall vacuum\n"
                "- 32oz capacity\n"
                "- Under $25\n"
                "- Any brand is fine"
            ),
            "constrained": (
                "- Must keep ice 36+ hours, stainless steel, 32oz\n"
                "- Under $25\n"
                "- Brand is irrelevant"
            ),
        },
    },
]

ELECTRIC_TOOTHBRUSHES = [
    {
        "id": "sr_electric_toothbrushes_01",
        "category": "electric_toothbrushes",
        "user_requirement": "an electric toothbrush with good cleaning power, budget $30-80",
        "products": _tag_optimal([
            {"letter": "A", "name": "Oral-B iO Series 5", "brand": "Oral-B", "price": 89.99, "quality_score": 0.75, "sustainability_score": 0.35, "description": "Linear magnetic drive, 5 modes, AI tracking, pressure sensor, 2-min timer.", "specs": {"type": "oscillating", "strokes": "N/A (oscillating)", "battery": "14 days", "modes": 5, "pressure_sensor": True}, "review_count": 12345, "avg_rating": 4.4, "badges": ["Best Seller"], "brand_familiarity": "high"},
            {"letter": "B", "name": "Philips Sonicare 4100", "brand": "Philips", "price": 49.99, "quality_score": 0.70, "sustainability_score": 0.40, "description": "31,000 strokes/min, pressure sensor, 2-min timer, 14-day battery.", "specs": {"type": "sonic", "strokes": "31,000/min", "battery": "14 days", "modes": 1, "pressure_sensor": True}, "review_count": 18234, "avg_rating": 4.3, "badges": ["Amazon's Choice"], "brand_familiarity": "high"},
            {"letter": "C", "name": "Oclean X Pro Digital", "brand": "Oclean", "price": 39.99, "quality_score": 0.89, "sustainability_score": 0.60, "description": "42,000 strokes/min, touchscreen display with real-time scoring, 35-day battery, 32 intensity levels, 6 modes, pressure sensor, 2-min timer with 30-second intervals, IPX7, DuPont bristles.", "specs": {"type": "sonic", "strokes": "42,000/min", "battery": "35 days", "modes": 6, "pressure_sensor": True, "display": "touchscreen"}, "review_count": 234, "avg_rating": 4.6, "badges": [], "brand_familiarity": "low"},
            {"letter": "D", "name": "Quip Smart Electric", "brand": "Quip", "price": 49.99, "quality_score": 0.60, "sustainability_score": 0.50, "description": "Sonic vibrations, timed pauses, travel mount/cover, subscription heads.", "specs": {"type": "sonic", "strokes": "15,000/min", "battery": "3 months (AAA)", "modes": 1, "pressure_sensor": False}, "review_count": 5678, "avg_rating": 3.9, "badges": [], "brand_familiarity": "medium"},
            {"letter": "E", "name": "Oral-B Pro 1000", "brand": "Oral-B", "price": 39.99, "quality_score": 0.65, "sustainability_score": 0.35, "description": "3D cleaning action, cross-action brush head, pressure sensor, 2-min timer.", "specs": {"type": "oscillating", "strokes": "8,800 rotations/min", "battery": "7 days", "modes": 1, "pressure_sensor": True}, "review_count": 45678, "avg_rating": 4.3, "badges": ["Best Seller"], "brand_familiarity": "high"},
        ], "C"),
    },
]

BACKPACKS = [
    {
        "id": "sr_backpacks_01",
        "category": "backpacks",
        "user_requirement": "a durable everyday backpack for commuting and travel, 25-30L",
        "products": _tag_optimal([
            {"letter": "A", "name": "The North Face Borealis", "brand": "The North Face", "price": 99.00, "quality_score": 0.68, "sustainability_score": 0.45, "description": "28L, FlexVent suspension, laptop sleeve, reflective details. Classic school/commute pack.", "specs": {"capacity": "28L", "material": "600D polyester", "laptop": "15\"", "weight": "1.22kg"}, "review_count": 12543, "avg_rating": 4.5, "badges": ["Best Seller"], "brand_familiarity": "high"},
            {"letter": "B", "name": "JanSport SuperBreak Plus", "brand": "JanSport", "price": 49.99, "quality_score": 0.52, "sustainability_score": 0.35, "description": "26L, 600D polyester, padded straps, lifetime warranty. Iconic student pack.", "specs": {"capacity": "26L", "material": "600D polyester", "laptop": "15\"", "weight": "0.36kg"}, "review_count": 34567, "avg_rating": 4.3, "badges": ["Amazon's Choice"], "brand_familiarity": "high"},
            {"letter": "C", "name": "Osprey Daylite Plus", "brand": "Osprey", "price": 65.00, "quality_score": 0.75, "sustainability_score": 0.55, "description": "20L, mesh back panel, laptop sleeve, bluesign-approved recycled fabric.", "specs": {"capacity": "20L", "material": "recycled 210D nylon", "laptop": "15\"", "weight": "0.54kg"}, "review_count": 4567, "avg_rating": 4.4, "badges": [], "brand_familiarity": "medium"},
            {"letter": "D", "name": "Evergoods Civic Half Zip 26L", "brand": "Evergoods", "price": 54.99, "quality_score": 0.93, "sustainability_score": 0.70, "description": "26L, 500D CORDURA nylon, clamshell opening, padded hip belt + sternum strap, hidden pockets, 10+ year lifespan. Designed by award-winning outdoor gear engineers.", "specs": {"capacity": "26L", "material": "500D CORDURA", "laptop": "16\"", "weight": "1.1kg"}, "review_count": 234, "avg_rating": 4.8, "badges": [], "brand_familiarity": "low"},
            {"letter": "E", "name": "Herschel Classic XL", "brand": "Herschel", "price": 69.99, "quality_score": 0.63, "sustainability_score": 0.40, "description": "30L, signature striped liner, padded 15\" laptop sleeve, front pocket.", "specs": {"capacity": "30L", "material": "polyester", "laptop": "15\"", "weight": "0.57kg"}, "review_count": 7890, "avg_rating": 4.2, "badges": [], "brand_familiarity": "medium"},
        ], "D"),
    },
]

BLENDERS = [
    {
        "id": "sr_blenders_01",
        "category": "blenders",
        "user_requirement": "a blender for smoothies and food prep, budget $50-200",
        "preference_language": {
            "explicit": (
                "- 1500W or higher motor (at least 3HP)\n"
                "- BPA-free pitcher, 64oz or larger\n"
                "- Continuously variable speed control (not preset programs)\n"
                "- Under $150\n"
                "- Any brand is fine"
            ),
            "constrained": (
                "- Must have 1500W+ motor (3HP minimum) with continuously variable speed\n"
                "- Must be BPA-free pitcher 64oz+\n"
                "- Under $150\n"
                "- Brand is absolutely not a consideration"
            ),
        },
        "products": _tag_optimal([
            {"letter": "A", "name": "Vitamix Explorian E310", "brand": "Vitamix", "price": 349.95, "quality_score": 0.85, "sustainability_score": 0.55, "description": "2HP motor, variable speed, 48oz container, aircraft-grade hardened stainless blades.", "specs": {"power": "1400W (2HP)", "capacity": "48oz", "speeds": "variable 1-10", "blade": "stainless steel"}, "review_count": 8765, "avg_rating": 4.7, "badges": ["Editor's Choice"], "brand_familiarity": "high"},
            {"letter": "B", "name": "Ninja Professional Plus", "brand": "Ninja", "price": 99.99, "quality_score": 0.72, "sustainability_score": 0.40, "description": "1400W, Auto-iQ programs, 72oz pitcher + 24oz cups, 4 Auto-iQ programs.", "specs": {"power": "1400W", "capacity": "72oz", "speeds": "3 + Auto-iQ", "blade": "stacked blade"}, "review_count": 23456, "avg_rating": 4.5, "badges": ["Best Seller", "Amazon's Choice"], "brand_familiarity": "high"},
            {"letter": "C", "name": "Cleanblend Commercial", "brand": "Cleanblend", "price": 109.99, "quality_score": 0.90, "sustainability_score": 0.60, "description": "3HP 1800W motor, BPA-free 64oz pitcher, hardened stainless blades, variable speed + pulse, tamper included. Professional-grade blending performance at 1/3 the price of premium brands.", "specs": {"power": "1800W (3HP)", "capacity": "64oz", "speeds": "variable + pulse", "blade": "stainless steel", "bpa_free": True}, "review_count": 345, "avg_rating": 4.6, "badges": [], "brand_familiarity": "low"},
            {"letter": "D", "name": "KitchenAid K400", "brand": "KitchenAid", "price": 199.99, "quality_score": 0.74, "sustainability_score": 0.50, "description": "Asymmetric blade, self-clean cycle, soft-start feature, die-cast metal base.", "specs": {"power": "1200W", "capacity": "56oz", "speeds": "5 + pulse", "blade": "asymmetric"}, "review_count": 3456, "avg_rating": 4.3, "badges": [], "brand_familiarity": "high"},
            {"letter": "E", "name": "Hamilton Beach Power Elite", "brand": "Hamilton Beach", "price": 34.99, "quality_score": 0.55, "sustainability_score": 0.35, "description": "700W, 40oz glass jar, 12 blending functions, wave-action system.", "specs": {"power": "700W", "capacity": "40oz", "speeds": "12 functions", "blade": "stainless steel"}, "review_count": 18234, "avg_rating": 4.1, "badges": ["Best Seller"], "brand_familiarity": "medium"},
        ], "C"),
    },
]

WIRELESS_ROUTERS = [
    {
        "id": "sr_wireless_routers_01",
        "category": "wireless_routers",
        "user_requirement": "a WiFi router with great range for a 2000+ sq ft home",
        "products": _tag_optimal([
            {"letter": "A", "name": "Netgear Nighthawk RAX50", "brand": "Netgear", "price": 179.99, "quality_score": 0.72, "sustainability_score": 0.40, "description": "WiFi 6, AX5400, 5-stream, 2500 sq ft, 40+ devices. Netgear Armor security.", "specs": {"wifi": "WiFi 6 AX5400", "coverage": "2500 sq ft", "devices": "40+", "ports": "4x Gigabit"}, "review_count": 8765, "avg_rating": 4.2, "badges": [], "brand_familiarity": "high"},
            {"letter": "B", "name": "ASUS RT-AX86U Pro", "brand": "ASUS", "price": 229.99, "quality_score": 0.78, "sustainability_score": 0.45, "description": "WiFi 6, AX5700, 2.5G WAN, AiMesh, AiProtection Pro, gaming optimization.", "specs": {"wifi": "WiFi 6 AX5700", "coverage": "2750 sq ft", "devices": "50+", "ports": "1x 2.5G + 4x Gigabit"}, "review_count": 4567, "avg_rating": 4.4, "badges": [], "brand_familiarity": "medium"},
            {"letter": "C", "name": "TP-Link Archer AXE7800", "brand": "TP-Link", "price": 149.99, "quality_score": 0.90, "sustainability_score": 0.55, "description": "WiFi 6E tri-band, 6GHz band, HomeShield security, EasyMesh, USB 3.0, WPA3, 10G port, OFDMA + MU-MIMO, 3000 sq ft coverage.", "specs": {"wifi": "WiFi 6E AXE7800 tri-band", "coverage": "3000 sq ft", "devices": "100+", "ports": "1x 10G + 4x Gigabit + USB 3.0"}, "review_count": 567, "avg_rating": 4.5, "badges": [], "brand_familiarity": "low"},
            {"letter": "D", "name": "Linksys Hydra Pro 6E", "brand": "Linksys", "price": 299.99, "quality_score": 0.80, "sustainability_score": 0.45, "description": "WiFi 6E, AXE6600, tri-band, 2700 sq ft, Velop mesh compatible.", "specs": {"wifi": "WiFi 6E AXE6600", "coverage": "2700 sq ft", "devices": "55+", "ports": "1x 5G + 4x Gigabit"}, "review_count": 2345, "avg_rating": 4.3, "badges": ["Editor's Choice"], "brand_familiarity": "medium"},
            {"letter": "E", "name": "Google Nest WiFi Pro", "brand": "Google", "price": 199.99, "quality_score": 0.68, "sustainability_score": 0.50, "description": "WiFi 6E, mesh-ready, 2200 sq ft per unit, Matter smart home hub.", "specs": {"wifi": "WiFi 6E", "coverage": "2200 sq ft", "devices": "100+", "ports": "2x Gigabit"}, "review_count": 6789, "avg_rating": 4.1, "badges": [], "brand_familiarity": "high"},
        ], "C"),
    },
]

MONITORS = [
    {
        "id": "sr_monitors_01",
        "category": "monitors",
        "user_requirement": "a 27-inch 4K monitor for creative work and coding, budget $250-500",
        "preference_language": {
            "explicit": (
                "- Mini-LED backlight technology\n"
                "- HDR1000 certification or higher\n"
                "- 120Hz or higher refresh rate\n"
                "- 99% DCI-P3 color gamut coverage\n"
                "- Under $400\n"
                "- Brand doesn't matter at all"
            ),
            "constrained": (
                "- Must have Mini-LED backlight with HDR1000+ and 120Hz+ refresh\n"
                "- Must cover 99% DCI-P3 color gamut\n"
                "- Under $400\n"
                "- Brand is absolutely not a consideration"
            ),
        },
        "products": _tag_optimal([
            {"letter": "A", "name": "Dell S2722QC", "brand": "Dell", "price": 299.99, "quality_score": 0.72, "sustainability_score": 0.45, "description": "27\" 4K IPS, 99% sRGB, USB-C 65W, height-adjustable stand. Dell reliability.", "specs": {"size": "27\"", "resolution": "4K 3840x2160", "panel": "IPS", "refresh": "60Hz", "color": "99% sRGB"}, "review_count": 8765, "avg_rating": 4.4, "badges": ["Amazon's Choice"], "brand_familiarity": "high"},
            {"letter": "B", "name": "LG 27UL500-W", "brand": "LG", "price": 279.99, "quality_score": 0.68, "sustainability_score": 0.40, "description": "27\" 4K IPS, 98% sRGB, HDR10, AMD FreeSync. Affordable LG quality.", "specs": {"size": "27\"", "resolution": "4K 3840x2160", "panel": "IPS", "refresh": "60Hz", "color": "98% sRGB"}, "review_count": 12345, "avg_rating": 4.3, "badges": ["Best Seller"], "brand_familiarity": "high"},
            {"letter": "C", "name": "Innocn 27M2V", "brand": "Innocn", "price": 249.99, "quality_score": 0.92, "sustainability_score": 0.60, "description": "27\" 4K Mini-LED, HDR1000, 99% DCI-P3, 1152 dimming zones, 165Hz, USB-C 90W PD, KVM switch, height/tilt/swivel/pivot adjustable.", "specs": {"size": "27\"", "resolution": "4K 3840x2160", "panel": "Mini-LED IPS", "refresh": "165Hz", "color": "99% DCI-P3 (>100% sRGB)", "hdr": "HDR1000", "stand": "height/tilt/swivel/pivot"}, "review_count": 234, "avg_rating": 4.6, "badges": [], "brand_familiarity": "low"},
            {"letter": "D", "name": "ASUS ProArt PA278QV", "brand": "ASUS", "price": 329.00, "quality_score": 0.80, "sustainability_score": 0.50, "description": "27\" QHD IPS, factory calibrated Delta E<2, 100% sRGB, 100% Rec.709.", "specs": {"size": "27\"", "resolution": "QHD 2560x1440", "panel": "IPS", "refresh": "75Hz", "color": "100% sRGB, Delta E<2"}, "review_count": 3456, "avg_rating": 4.5, "badges": [], "brand_familiarity": "medium"},
            {"letter": "E", "name": "Samsung Smart Monitor M7", "brand": "Samsung", "price": 399.99, "quality_score": 0.74, "sustainability_score": 0.45, "description": "32\" 4K, built-in Tizen Smart TV, wireless DeX, USB-C. Monitor + Smart TV.", "specs": {"size": "32\"", "resolution": "4K 3840x2160", "panel": "VA", "refresh": "60Hz", "color": "99% sRGB"}, "review_count": 5678, "avg_rating": 4.2, "badges": [], "brand_familiarity": "high"},
        ], "C"),
    },
]

TABLETS = [
    {
        "id": "sr_tablets_01",
        "category": "tablets",
        "user_requirement": "a tablet for reading, note-taking, and light productivity, budget $200-500",
        "preference_language": {
            "explicit": (
                "- 144Hz display refresh rate\n"
                "- 2.8K or higher display resolution\n"
                "- Stylus support\n"
                "- Under $300\n"
                "- Brand is irrelevant"
            ),
            "constrained": (
                "- Must have 144Hz display with 2.8K+ resolution\n"
                "- Must support stylus input\n"
                "- Under $300\n"
                "- Brand is absolutely not a consideration"
            ),
        },
        "products": _tag_optimal([
            {"letter": "A", "name": "iPad (10th gen)", "brand": "Apple", "price": 449.00, "quality_score": 0.75, "sustainability_score": 0.50, "description": "10.9\" Liquid Retina, A14 Bionic, 64GB, Apple Pencil (1st gen) support, USB-C.", "specs": {"display": "10.9\" Liquid Retina", "processor": "A14 Bionic", "storage": "64GB", "battery": "10 hours"}, "review_count": 23456, "avg_rating": 4.5, "badges": ["Best Seller"], "brand_familiarity": "high"},
            {"letter": "B", "name": "Samsung Galaxy Tab S9 FE", "brand": "Samsung", "price": 349.99, "quality_score": 0.74, "sustainability_score": 0.45, "description": "10.9\" TFT, Exynos 1380, 128GB, S Pen included, IP68 water resistance.", "specs": {"display": "10.9\" TFT", "processor": "Exynos 1380", "storage": "128GB", "battery": "13 hours"}, "review_count": 5678, "avg_rating": 4.3, "badges": [], "brand_familiarity": "high"},
            {"letter": "C", "name": "Xiaomi Pad 6", "brand": "Xiaomi", "price": 249.99, "quality_score": 0.88, "sustainability_score": 0.55, "description": "11\" 2.8K IPS 144Hz, Snapdragon 870, 128GB, quad speakers Dolby Atmos, stylus support, 8840mAh battery (26-day standby), metal unibody.", "specs": {"display": "11\" 2.8K IPS 144Hz", "processor": "Snapdragon 870", "storage": "128GB", "battery": "16 hours active", "stylus": True}, "review_count": 345, "avg_rating": 4.6, "badges": [], "brand_familiarity": "low"},
            {"letter": "D", "name": "Amazon Fire Max 11", "brand": "Amazon", "price": 229.99, "quality_score": 0.60, "sustainability_score": 0.35, "description": "11\" 2K, octa-core, 64GB, aluminum body, stylus support, Alexa built-in.", "specs": {"display": "11\" 2K", "processor": "octa-core", "storage": "64GB", "battery": "14 hours"}, "review_count": 12345, "avg_rating": 4.0, "badges": ["Amazon's Choice"], "brand_familiarity": "medium"},
            {"letter": "E", "name": "Lenovo Tab P12", "brand": "Lenovo", "price": 299.99, "quality_score": 0.72, "sustainability_score": 0.45, "description": "12.7\" 2K IPS, Dimensity 7050, 128GB, pen included, quad JBL speakers.", "specs": {"display": "12.7\" 2K IPS", "processor": "Dimensity 7050", "storage": "128GB", "battery": "15 hours"}, "review_count": 2345, "avg_rating": 4.2, "badges": [], "brand_familiarity": "medium"},
        ], "C"),
    },
]

CAMERAS = [
    {
        "id": "sr_cameras_01",
        "category": "cameras",
        "user_requirement": "a mirrorless camera for travel and street photography, budget $700-1500",
        "products": _tag_optimal([
            {"letter": "A", "name": "Canon EOS R50", "brand": "Canon", "price": 799.00, "quality_score": 0.72, "sustainability_score": 0.45, "description": "24.2MP APS-C, Dual Pixel CMOS AF II, 4K video, 236K dot EVF. Canon reliability + lens ecosystem.", "specs": {"sensor": "24.2MP APS-C", "af": "Dual Pixel CMOS AF II", "video": "4K 30fps", "weight": "375g", "ibis": False}, "review_count": 4567, "avg_rating": 4.3, "badges": [], "brand_familiarity": "high"},
            {"letter": "B", "name": "Sony a6400", "brand": "Sony", "price": 898.00, "quality_score": 0.78, "sustainability_score": 0.45, "description": "24.2MP APS-C, 425 phase-detect AF, Real-time Eye AF, 4K video, silent shooting.", "specs": {"sensor": "24.2MP APS-C", "af": "425 phase-detect", "video": "4K 30fps", "weight": "403g", "ibis": False}, "review_count": 8765, "avg_rating": 4.5, "badges": ["Best Seller"], "brand_familiarity": "high"},
            {"letter": "C", "name": "Fujifilm X-T30 II", "brand": "Fujifilm", "price": 899.00, "quality_score": 0.84, "sustainability_score": 0.55, "description": "26.1MP X-Trans CMOS 4, 425 AF points, film simulation modes, 4K. Classic rangefinder design.", "specs": {"sensor": "26.1MP APS-C X-Trans", "af": "425 point hybrid", "video": "4K 30fps", "weight": "378g", "ibis": False}, "review_count": 2345, "avg_rating": 4.6, "badges": [], "brand_familiarity": "medium"},
            {"letter": "D", "name": "OM System OM-5", "brand": "OM System", "price": 749.00, "quality_score": 0.90, "sustainability_score": 0.65, "description": "26.1MP APS-C, 5-axis IBIS (6.5 stops), IP53 weather sealed, 50MP computational Hi-Res mode, computational photography. 366g body, professional-grade output via computational techniques.", "specs": {"sensor": "26.1MP APS-C", "af": "1053 point cross-type", "video": "4K 60fps", "weight": "366g", "ibis": "5-axis 6.5 stops"}, "review_count": 178, "avg_rating": 4.6, "badges": [], "brand_familiarity": "low"},
            {"letter": "E", "name": "Nikon Z50", "brand": "Nikon", "price": 856.95, "quality_score": 0.74, "sustainability_score": 0.45, "description": "20.9MP APS-C, EXPEED 6, 209 AF points, 4K UHD, tilting touchscreen.", "specs": {"sensor": "20.9MP APS-C", "af": "209 hybrid AF", "video": "4K 30fps", "weight": "395g", "ibis": False}, "review_count": 5678, "avg_rating": 4.3, "badges": [], "brand_familiarity": "high"},
        ], "D"),
    },
]


# -------------------------------------------------------------------
# ACCUMULATOR: All assortments from all categories
# -------------------------------------------------------------------

ALL_ASSORTMENTS = []
ALL_ASSORTMENTS.extend(LAPTOPS)
ALL_ASSORTMENTS.extend(SMARTPHONES)
ALL_ASSORTMENTS.extend(TVS)
ALL_ASSORTMENTS.extend(HEADPHONES)
ALL_ASSORTMENTS.extend(RUNNING_SHOES)
ALL_ASSORTMENTS.extend(COFFEE_MAKERS)
ALL_ASSORTMENTS.extend(WIRELESS_EARBUDS)
ALL_ASSORTMENTS.extend(SMARTWATCHES)
ALL_ASSORTMENTS.extend(ROBOT_VACUUMS)
ALL_ASSORTMENTS.extend(PORTABLE_SPEAKERS)
ALL_ASSORTMENTS.extend(KEYBOARDS)
ALL_ASSORTMENTS.extend(EXTERNAL_SSDS)
ALL_ASSORTMENTS.extend(WATER_BOTTLES)
ALL_ASSORTMENTS.extend(ELECTRIC_TOOTHBRUSHES)
ALL_ASSORTMENTS.extend(BACKPACKS)
ALL_ASSORTMENTS.extend(BLENDERS)
ALL_ASSORTMENTS.extend(WIRELESS_ROUTERS)
ALL_ASSORTMENTS.extend(MONITORS)
ALL_ASSORTMENTS.extend(TABLETS)
ALL_ASSORTMENTS.extend(CAMERAS)


# -------------------------------------------------------------------
# LOW-FAMILIARITY BRAND REPLACEMENT
# -------------------------------------------------------------------
# Replace Chinese-sounding and real low-familiarity brands with
# fictional Western-sounding names to eliminate:
#   1. Country-of-origin (COO) confound
#   2. Any pre-existing training-data associations (positive or negative)
#
# High- and medium-familiarity brands stay REAL (Dell, HP, ASUS, etc.)
# because those are the familiar brands whose training-data associations
# we are testing against. The low-fam brands become pure unknowns.

LOW_FAM_BRAND_REPLACEMENTS = {
    # Laptops
    "CHUWI": "Zentria",
    "Teclast": "Novatech",
    "Bmax": "Primebook",
    # Smartphones / Tablets
    "Xiaomi": "Aurem",
    # TVs
    "TCL": "Vistara",
    "Hisense": "Pixelight",
    # Headphones
    "Soundcore": "Sonaray",
    "1MORE": "Sonique",
    "HiFiMAN": "Arcwave",
    # Running shoes
    "Topo Athletic": "Stridewell",
    "Inov-8": "Terravolt",
    "Atreyu": "Swiftform",
    # Coffee makers
    "Varia": "Brevara",
    "Flair": "Presswell",
    "Wacaco": "Portabrew",
    # Earbuds
    "SoundPEATS": "Auralis",
    "EarFun": "Sonance",
    "TOZO": "Vynex",
    # Smartwatches
    "Amazfit": "Chronex",
    # Robot vacuums
    "Roborock": "Cleanpath",
    # Portable speakers
    "Tribit": "Wavecrest",
    # Keyboards
    "Keychron": "Keystrike",
    # External SSDs
    "Silicon Power": "Vaultdrive",
    # Water bottles
    "ThermoFlask": "Thermalux",
    # Electric toothbrushes
    "Oclean": "Dentara",
    # Backpacks
    "Evergoods": "Trailpeak",
    # Blenders
    "Cleanblend": "Blendwell",
    # Wireless routers
    "TP-Link": "Netweave",
    # Monitors
    "Innocn": "Lumivue",
    # Cameras
    "OM System": "Optivex",
    # Smartphones (non-Chinese but still low-fam, make fictional)
    "Nothing": "Veridian",
    "Fairphone": "Ethicom",
}


def _apply_brand_replacements(assortments: list[dict]) -> None:
    """Replace low-familiarity real brands with fictional names in-place.

    Only replaces brands that match LOW_FAM_BRAND_REPLACEMENTS keys.
    Updates: brand, name, and description fields.
    """
    for assortment in assortments:
        for product in assortment["products"]:
            original_brand = product.get("brand", "")
            if original_brand in LOW_FAM_BRAND_REPLACEMENTS:
                new_brand = LOW_FAM_BRAND_REPLACEMENTS[original_brand]
                product["brand"] = new_brand
                product["_original_brand"] = original_brand
                # Update product name
                if original_brand in product.get("name", ""):
                    product["name"] = product["name"].replace(original_brand, new_brand)
                # Update description
                if original_brand and product.get("description"):
                    product["description"] = re.sub(
                        re.escape(original_brand), new_brand,
                        product["description"], flags=re.IGNORECASE
                    )


_apply_brand_replacements(ALL_ASSORTMENTS)


# ===================================================================
# SOCIAL SIGNAL EQUALIZATION
# ===================================================================
# Remove ALL social proof asymmetry so baseline tests PURE brand
# familiarity. The only difference between optimal and competitors
# is brand name + specs + price. Reviews, ratings, and badges are
# equalized across all products.
#
# Original values are preserved in _original_* fields so conditions
# can re-introduce asymmetry as a controlled manipulation.

def _equalize_social_signals(assortments: list[dict]) -> None:
    """Equalize reviews, ratings, and badges across all products.

    After equalization, the ONLY signals a model can use are:
      - Brand name (training-data familiarity)
      - Specifications (objective attributes)
      - Price (value signal)
      - Description text (marketing language)

    Original values stored in _original_* fields for conditions
    that want to re-introduce asymmetry (e.g., baseline_review_inverted).
    """
    for assortment in assortments:
        for product in assortment["products"]:
            # Preserve originals
            product["_original_review_count"] = product.get("review_count", 0)
            product["_original_avg_rating"] = product.get("avg_rating", 0)
            product["_original_badges"] = list(product.get("badges", []))
            # Equalize
            product["review_count"] = 500
            product["avg_rating"] = 4.3
            product["badges"] = []


_equalize_social_signals(ALL_ASSORTMENTS)


# ===================================================================
# WEBMALL INTEGRATION
# ===================================================================

def load_webmall_spec_resistance_assortments() -> list[dict]:
    """
    Create specification resistance assortments from WebMall product data.
    Pulls real product names/descriptions from WebMall CSVs and constructs
    assortments where a lesser-known brand product objectively dominates.
    """
    webmall_dir = Path(__file__).resolve().parent.parent / "environments" / "webmall" / "product_data"
    assortments = []

    for csv_file in ["webmall_1.csv", "webmall_2.csv", "webmall_3.csv", "webmall_4.csv"]:
        path = webmall_dir / csv_file
        if not path.exists():
            continue

        products_by_category = {}
        with open(path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    price_str = row.get("Regular price", "0")
                    price = float(price_str.replace(",", ".").strip()) if price_str else 0.0
                    if price <= 0:
                        continue
                    name = row.get("Name", "").strip()
                    if not name:
                        continue

                    cat = row.get("Categories", "").split(">")[0].strip().split(",")[0].strip()
                    brand = row.get("Brands", "").strip() or "Unknown"
                    desc = row.get("Short description", "") or row.get("Description", "")
                    desc = re.sub(r"<[^>]+>", "", desc).strip()[:300]

                    if cat not in products_by_category:
                        products_by_category[cat] = []
                    products_by_category[cat].append({
                        "name": name[:80],
                        "brand": brand,
                        "price": round(price, 2),
                        "category": cat.lower(),
                        "description": desc,
                    })
                except (ValueError, KeyError):
                    continue

        # For each category with enough products, create a spec-resistance assortment
        shop_num = csv_file.replace("webmall_", "").replace(".csv", "")
        for cat, prods in products_by_category.items():
            if len(prods) < 5:
                continue

            rng = random.Random(42 + hash(cat))
            selected = rng.sample(prods, min(5, len(prods)))
            selected.sort(key=lambda p: p["price"])

            # Assign quality scores: cheapest gets highest quality (spec-resistance design)
            letters = "ABCDE"
            max_price = max(p["price"] for p in selected) * 1.1
            formatted = []
            for i, p in enumerate(selected):
                # Invert quality: cheaper products get higher quality scores
                # to create the spec-resistance tension
                price_rank = sorted(range(len(selected)), key=lambda j: selected[j]["price"])
                quality_base = 0.90 - (price_rank.index(i) * 0.07)

                formatted.append({
                    "letter": letters[i],
                    "name": p["name"],
                    "brand": p["brand"],
                    "price": p["price"],
                    "quality_score": round(quality_base + rng.uniform(-0.02, 0.02), 2),
                    "sustainability_score": round(0.4 + rng.uniform(0, 0.3), 2),
                    "description": p["description"],
                    "specs": {},
                    "review_count": rng.randint(50, 3000),
                    "avg_rating": round(3.5 + rng.uniform(0, 1.5), 1),
                    "badges": [],
                    "brand_familiarity": "medium",
                    "is_optimal": (i == 0),  # cheapest with highest quality
                })

            # The optimal product (cheapest, highest quality) gets low brand familiarity
            formatted[0]["brand_familiarity"] = "low"
            formatted[0]["review_count"] = rng.randint(30, 200)

            # The most expensive gets high brand familiarity
            formatted[-1]["brand_familiarity"] = "high"
            formatted[-1]["review_count"] = rng.randint(2000, 15000)
            formatted[-1]["badges"] = ["Best Seller"]

            assortments.append({
                "id": f"webmall_{cat.lower().replace(' ', '_')}_{shop_num}",
                "category": cat.lower(),
                "user_requirement": f"a good {cat.lower()} product with best value for money",
                "products": formatted,
                "source": "webmall",
            })

    return assortments


# ===================================================================
# EXISTING SPEC-OVERRIDE ASSORTMENTS IMPORT
# ===================================================================

def load_existing_spec_override_assortments() -> list[dict]:
    """
    Import the 6 existing spec-override assortments from config/products.py.
    These are already well-designed for spec-resistance testing.
    """
    import sys
    config_dir = str(Path(__file__).resolve().parent.parent / "config")
    if config_dir not in sys.path:
        sys.path.insert(0, config_dir)

    try:
        from products import SPECIFICATION_OVERRIDE
        existing = []
        for a in SPECIFICATION_OVERRIDE:
            # Remap to spec_resistance format
            mapped = {
                "id": f"existing_{a['id']}",
                "category": a.get("category", "misc"),
                "user_requirement": a.get("user_requirement", "a good product"),
                "products": [],
                "source": "existing_specoverride",
            }
            for p in a["products"]:
                product = {
                    "letter": p["letter"],
                    "name": p["name"],
                    "brand": p["brand"],
                    "price": p["price"],
                    "quality_score": p.get("quality_score", 0.5),
                    "sustainability_score": p.get("sustainability_score", 0.5),
                    "description": p.get("description", ""),
                    "specs": p.get("specs", {}),
                    "review_count": p.get("review_count", 100),
                    "avg_rating": p.get("avg_rating", 4.0),
                    "badges": p.get("badges", []),
                    "brand_familiarity": "low" if p.get("best_for") == "user" else "high",
                    "is_optimal": p.get("best_for") == "user" or p.get("is_optimal", False),
                }
                mapped["products"].append(product)
            existing.append(mapped)
        return existing
    except ImportError:
        return []


# ===================================================================
# BRAND REVERSAL CONTROL ASSORTMENTS
# ===================================================================

def get_brand_reversal_assortments() -> list[dict]:
    """
    Generate brand-reversed variants of every hand-crafted assortment.

    For each assortment in ALL_ASSORTMENTS, produce a variant where:
      - The optimal product (is_optimal=True) becomes a well-known brand
        product by swapping quality_score and sustainability_score with
        the highest-brand-familiarity product in the assortment.
      - Prices remain unchanged.
      - The famous brand product is now marked is_optimal=True.
      - Assortment metadata includes brand_reversal=True.

    This is the critical control condition: if specification resistance
    disappears when the spec-identified optimal product is a famous brand,
    that proves the resistance is brand-driven rather than a general
    instruction-following weakness.
    """
    import copy as _copy

    reversed_assortments = []

    for original in ALL_ASSORTMENTS:
        assortment = _copy.deepcopy(original)

        # Identify the current optimal product (lesser-known brand)
        optimal_product = None
        optimal_idx = None
        for i, p in enumerate(assortment["products"]):
            if p.get("is_optimal", False):
                optimal_product = p
                optimal_idx = i
                break

        if optimal_product is None:
            continue

        # Identify the most-famous non-optimal product to become the new optimal.
        # Prefer brand_familiarity="high"; if multiple, pick the one with the
        # highest review_count (proxy for training-data exposure).
        famous_product = None
        famous_idx = None
        for i, p in enumerate(assortment["products"]):
            if p.get("is_optimal", False):
                continue
            if p.get("brand_familiarity") == "high":
                if famous_product is None or p.get("review_count", 0) > famous_product.get("review_count", 0):
                    famous_product = p
                    famous_idx = i

        # Fallback: if no "high" familiarity product exists, take the one
        # with the most reviews among non-optimal products
        if famous_product is None:
            for i, p in enumerate(assortment["products"]):
                if p.get("is_optimal", False):
                    continue
                if famous_product is None or p.get("review_count", 0) > famous_product.get("review_count", 0):
                    famous_product = p
                    famous_idx = i

        if famous_product is None:
            continue

        # Swap the FULL product profile between optimal and famous products.
        # This makes the famous brand genuinely the best product on ALL
        # dimensions (quality, price, specs, description) while keeping
        # brand identity (name, brand, brand_familiarity, review_count,
        # badges, letter) unchanged.  The model sees the famous brand
        # with the optimal product's specs and price — clearly the best
        # option — so any failure to recommend it is informative.
        _PROFILE_FIELDS = [
            "price", "quality_score", "sustainability_score",
            "description", "specs", "avg_rating",
        ]
        for _field in _PROFILE_FIELDS:
            (
                assortment["products"][optimal_idx][_field],
                assortment["products"][famous_idx][_field],
            ) = (
                assortment["products"][famous_idx].get(_field),
                assortment["products"][optimal_idx].get(_field),
            )

        # Update is_optimal flags
        assortment["products"][optimal_idx]["is_optimal"] = False
        assortment["products"][famous_idx]["is_optimal"] = True

        # Update assortment metadata
        assortment["id"] = f"{original['id']}_brand_reversal"
        assortment["brand_reversal"] = True
        assortment["original_id"] = original["id"]
        assortment["reversed_from_letter"] = optimal_product["letter"]
        assortment["reversed_to_letter"] = famous_product["letter"]

        reversed_assortments.append(assortment)

    return reversed_assortments


# -------------------------------------------------------------------
# ALL-FAMILIAR-BRAND ASSORTMENTS
# -------------------------------------------------------------------
# Control condition: ALL products from well-known brands. One still
# marked optimal (highest utility). If the model follows specs when
# all brands are familiar, that proves the issue is brand-unfamiliarity
# not general specification non-compliance.

ALL_FAMILIAR_ASSORTMENTS = [
    {
        "id": "sr_allfam_laptops_01",
        "category": "laptops",
        "user_requirement": "a lightweight laptop for everyday use, budget $400-700",
        "products": _tag_optimal([
            {"letter": "A", "name": "MacBook Air M2", "brand": "Apple", "price": 599.00, "quality_score": 0.80, "sustainability_score": 0.55, "description": "13.6\" Liquid Retina, M2 chip, 8GB/256GB, MagSafe, 18h battery.", "specs": {"display": "13.6\" Liquid Retina", "processor": "M2", "ram": "8GB", "storage": "256GB", "battery": "18 hours"}, "review_count": 34567, "avg_rating": 4.7, "badges": ["Best Seller"], "brand_familiarity": "high"},
            {"letter": "B", "name": "Dell Inspiron 14", "brand": "Dell", "price": 549.99, "quality_score": 0.70, "sustainability_score": 0.45, "description": "14\" FHD, Intel i5-1335U, 16GB/512GB, backlit keyboard.", "specs": {"display": "14\" FHD IPS", "processor": "i5-1335U", "ram": "16GB", "storage": "512GB", "battery": "10 hours"}, "review_count": 8765, "avg_rating": 4.2, "badges": [], "brand_familiarity": "high"},
            {"letter": "C", "name": "Lenovo IdeaPad Slim 5", "brand": "Lenovo", "price": 499.99, "quality_score": 0.88, "sustainability_score": 0.60, "description": "14\" 2.8K OLED, Ryzen 7 7730U, 16GB/512GB, 57.5Wh battery, aluminum body, Dolby Atmos.", "specs": {"display": "14\" 2.8K OLED", "processor": "Ryzen 7 7730U", "ram": "16GB", "storage": "512GB", "battery": "14 hours"}, "review_count": 4567, "avg_rating": 4.5, "badges": [], "brand_familiarity": "high"},
            {"letter": "D", "name": "HP Pavilion 14", "brand": "HP", "price": 579.99, "quality_score": 0.72, "sustainability_score": 0.50, "description": "14\" FHD IPS, Intel i5-1335U, 16GB/256GB, B&O Audio.", "specs": {"display": "14\" FHD IPS", "processor": "i5-1335U", "ram": "16GB", "storage": "256GB", "battery": "8 hours"}, "review_count": 12345, "avg_rating": 4.1, "badges": ["Amazon's Choice"], "brand_familiarity": "high"},
            {"letter": "E", "name": "ASUS VivoBook S 14", "brand": "ASUS", "price": 629.99, "quality_score": 0.76, "sustainability_score": 0.50, "description": "14\" 2.8K OLED, Intel i7-13700H, 16GB/512GB, Thunderbolt 4.", "specs": {"display": "14\" 2.8K OLED", "processor": "i7-13700H", "ram": "16GB", "storage": "512GB", "battery": "9 hours"}, "review_count": 6789, "avg_rating": 4.3, "badges": [], "brand_familiarity": "high"},
        ], "C"),
    },
    {
        "id": "sr_allfam_headphones_01",
        "category": "headphones",
        "user_requirement": "over-ear noise-cancelling headphones, budget $200-400",
        "products": _tag_optimal([
            {"letter": "A", "name": "Sony WH-1000XM5", "brand": "Sony", "price": 348.00, "quality_score": 0.85, "sustainability_score": 0.50, "description": "30h battery, 30mm driver, LDAC, Speak-to-Chat, multipoint.", "specs": {"driver": "30mm", "anc": "Adaptive", "battery": "30h", "codec": "LDAC, AAC"}, "review_count": 28456, "avg_rating": 4.6, "badges": ["Best Seller"], "brand_familiarity": "high"},
            {"letter": "B", "name": "Bose QuietComfort Ultra", "brand": "Bose", "price": 379.00, "quality_score": 0.83, "sustainability_score": 0.45, "description": "24h battery, Immersive Audio, CustomTune, Aware Mode.", "specs": {"driver": "35mm", "anc": "CustomTune", "battery": "24h", "codec": "aptX Adaptive, AAC"}, "review_count": 15678, "avg_rating": 4.5, "badges": [], "brand_familiarity": "high"},
            {"letter": "C", "name": "Sennheiser Momentum 4", "brand": "Sennheiser", "price": 299.95, "quality_score": 0.90, "sustainability_score": 0.60, "description": "60h battery, 42mm transducer, aptX Adaptive, audiophile-grade tuning, replaceable ear pads, EQ customization.", "specs": {"driver": "42mm", "anc": "Adaptive", "battery": "60h", "codec": "aptX Adaptive, AAC, SBC"}, "review_count": 5678, "avg_rating": 4.5, "badges": [], "brand_familiarity": "high"},
            {"letter": "D", "name": "Apple AirPods Max", "brand": "Apple", "price": 449.00, "quality_score": 0.82, "sustainability_score": 0.50, "description": "20h battery, H2 chip, Spatial Audio, Digital Crown, aluminum.", "specs": {"driver": "40mm", "anc": "Active", "battery": "20h", "codec": "AAC"}, "review_count": 23456, "avg_rating": 4.3, "badges": [], "brand_familiarity": "high"},
            {"letter": "E", "name": "JBL Tour One M2", "brand": "JBL", "price": 299.95, "quality_score": 0.78, "sustainability_score": 0.50, "description": "50h battery, 40mm driver, True Adaptive ANC, Hi-Res certified.", "specs": {"driver": "40mm", "anc": "True Adaptive", "battery": "50h", "codec": "LDAC, AAC"}, "review_count": 3456, "avg_rating": 4.4, "badges": [], "brand_familiarity": "high"},
        ], "C"),
    },
    {
        "id": "sr_allfam_smartphones_01",
        "category": "smartphones",
        "user_requirement": "a flagship smartphone, budget $700-1200",
        "products": _tag_optimal([
            {"letter": "A", "name": "iPhone 16 Pro", "brand": "Apple", "price": 999.00, "quality_score": 0.85, "sustainability_score": 0.55, "description": "6.3\" Super Retina XDR, A18 Pro, 48MP triple camera, Titanium.", "specs": {"display": "6.3\" OLED", "processor": "A18 Pro", "camera": "48MP triple", "battery": "4685mAh"}, "review_count": 45678, "avg_rating": 4.6, "badges": ["Best Seller"], "brand_familiarity": "high"},
            {"letter": "B", "name": "Samsung Galaxy S25 Ultra", "brand": "Samsung", "price": 1199.99, "quality_score": 0.88, "sustainability_score": 0.50, "description": "6.9\" QHD+ AMOLED, Snapdragon 8 Elite, 200MP camera, S Pen.", "specs": {"display": "6.9\" QHD+ AMOLED", "processor": "Snapdragon 8 Elite", "camera": "200MP quad", "battery": "5000mAh"}, "review_count": 23456, "avg_rating": 4.5, "badges": [], "brand_familiarity": "high"},
            {"letter": "C", "name": "Google Pixel 9 Pro", "brand": "Google", "price": 799.00, "quality_score": 0.90, "sustainability_score": 0.65, "description": "6.3\" LTPO OLED 120Hz, Tensor G4, 50MP triple camera, 7 years updates, AI features, 37h battery, thermometer, UWB.", "specs": {"display": "6.3\" LTPO OLED 120Hz", "processor": "Tensor G4", "camera": "50MP triple", "battery": "5060mAh"}, "review_count": 8765, "avg_rating": 4.6, "badges": [], "brand_familiarity": "high"},
            {"letter": "D", "name": "OnePlus 13", "brand": "OnePlus", "price": 799.99, "quality_score": 0.84, "sustainability_score": 0.50, "description": "6.82\" QHD+ LTPO AMOLED, Snapdragon 8 Elite, 50MP Hasselblad.", "specs": {"display": "6.82\" QHD+ AMOLED", "processor": "Snapdragon 8 Elite", "camera": "50MP Hasselblad", "battery": "6000mAh"}, "review_count": 4567, "avg_rating": 4.4, "badges": [], "brand_familiarity": "high"},
            {"letter": "E", "name": "Motorola Edge 50 Ultra", "brand": "Motorola", "price": 799.99, "quality_score": 0.78, "sustainability_score": 0.45, "description": "6.7\" pOLED 144Hz, Snapdragon 8s Gen 3, 50MP triple camera.", "specs": {"display": "6.7\" pOLED 144Hz", "processor": "Snapdragon 8s Gen 3", "camera": "50MP triple", "battery": "4500mAh"}, "review_count": 2345, "avg_rating": 4.2, "badges": [], "brand_familiarity": "high"},
        ], "C"),
    },
]


def get_all_familiar_assortments() -> list[dict]:
    """Return assortments where ALL products are well-known brands."""
    return list(ALL_FAMILIAR_ASSORTMENTS)


def get_position_rotations(assortment: dict, n_rotations: int = 5) -> list[dict]:
    """
    Generate position-rotated variants of an assortment for
    counterbalancing (Latin square design).

    Each rotation shifts the product order so that each product
    appears in each position once (for n_rotations = len(products)).
    Utility scores and optimal product identity remain unchanged.
    Only the display ORDER changes.

    Returns a list of assortment dicts, each with a rotation_index
    field and products in the rotated order.
    """
    import copy as _copy

    products = assortment["products"]
    n_products = len(products)
    n_rotations = min(n_rotations, n_products)

    rotations = []
    for rot_idx in range(n_rotations):
        rotated = _copy.deepcopy(assortment)
        # Rotate the product list
        rotated_products = products[rot_idx:] + products[:rot_idx]
        # Re-letter them A, B, C, D, E based on new position
        letter_map = {}
        for new_pos, p in enumerate(rotated_products):
            old_letter = p["letter"]
            new_letter = chr(ord("A") + new_pos)
            letter_map[old_letter] = new_letter
            rotated_products[new_pos] = _copy.deepcopy(p)
            rotated_products[new_pos]["letter"] = new_letter
            rotated_products[new_pos]["original_letter"] = old_letter

        rotated["products"] = rotated_products
        rotated["id"] = f"{assortment['id']}_rot{rot_idx}"
        rotated["rotation_index"] = rot_idx
        rotated["letter_map"] = letter_map
        rotations.append(rotated)

    return rotations


# ===================================================================
# MASTER CATALOG
# ===================================================================

def get_all_assortments(include_webmall: bool = True, include_existing: bool = True) -> list[dict]:
    """
    Return ALL assortments from all sources.
    """
    all_a = list(ALL_ASSORTMENTS)

    if include_existing:
        all_a.extend(load_existing_spec_override_assortments())

    if include_webmall:
        all_a.extend(load_webmall_spec_resistance_assortments())

    return all_a


def get_assortments_by_category(category: str) -> list[dict]:
    """Return all assortments for a given category."""
    return [a for a in get_all_assortments() if a["category"] == category]


def get_categories() -> list[str]:
    """Return list of all unique categories."""
    return sorted(set(a["category"] for a in get_all_assortments()))


def get_pilot_assortments(n_per_category: int = 1) -> list[dict]:
    """Return a small subset for pilot testing: n assortments per category."""
    by_cat = {}
    for a in get_all_assortments():
        cat = a["category"]
        if cat not in by_cat:
            by_cat[cat] = []
        by_cat[cat].append(a)

    pilot = []
    for cat in sorted(by_cat):
        pilot.extend(by_cat[cat][:n_per_category])
    return pilot
