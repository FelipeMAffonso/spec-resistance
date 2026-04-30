"""
Create Study 2 v2: The Hidden Consideration Set (with product/price EmbeddedData)
Spec Resistance Project -- Nature R&R Human Subjects

Design: 3 (Condition: Curated / Transparent / SingleRec)
        x 3 (Category: earbuds / speakers / ssds)
        = 9 cells, between-subjects

Flow:
  Mobile screening -> EndSurvey (if mobile)
  Screening block: browser meta, consent, attention check (Horse), passed message
  Consent branch -> EndSurvey (if "I do not agree")
  Attention check branch -> EndSurvey (if Horse not selected)
  BlockRandomizer(SubSet=1, EvenPresentation=true): 9 EmbeddedData nodes
  Preference articulation block
  AI recommendation block (single product card + chat bubble)
  Action decision block ("What would you like to do?")
  Alternatives block (DisplayLogic: asked for alternatives)
  Final choice block
  Post-choice measures block (confidence, satisfaction, enough options)
  Debrief + reveal block (show all 5, identify optimal, revision)
  Post-reveal measures block (AI trust, felt misled)
  Demographics block
  EndSurvey -> Prolific redirect
"""
import requests
import json
import sys

BASE = "https://pdx1.qualtrics.com/API/v3"
HEADERS = {
    "X-API-TOKEN": "Br4dAvcZOSSsJcup0AXpLDj7BjuGs1Pp96nNirWY",
    "Content-Type": "application/json"
}

BLOCK_OPTS = {
    "BlockLocking": "false",
    "RandomizeQuestions": "false",
    "BlockVisibility": "Expanded"
}

HIDE_NEXT_JS = """Qualtrics.SurveyEngine.addOnload(function(){
this.hideNextButton();
this.questionclick = function(event,element){
if (element.type == 'radio') { this.showNextButton(); }
}
});
Qualtrics.SurveyEngine.addOnReady(function(){
this.hideNextButton();
this.questionclick = function(event,element){
if (element.type == 'radio') { this.showNextButton(); }
}
});"""


def api_call(method, endpoint, data=None):
    url = f"{BASE}{endpoint}"
    resp = requests.request(method, url, headers=HEADERS, json=data)
    result = resp.json()
    if resp.status_code not in (200, 201):
        print(f"ERROR {resp.status_code}: {json.dumps(result, indent=2)}")
        print("STOPPING due to API error.")
        sys.exit(1)
    return result


def create_block(survey_id, name):
    resp = api_call("POST", f"/survey-definitions/{survey_id}/blocks", {
        "Type": "Standard",
        "Description": name,
        "Options": BLOCK_OPTS
    })
    return resp["result"]["BlockID"]


def create_question(survey_id, qdef):
    resp = api_call("POST", f"/survey-definitions/{survey_id}/questions", qdef)
    qid = resp["result"]["QuestionID"]
    return qid


# =========================================================================
# HELPER: Chat bubble and product card HTML
# =========================================================================

def ai_bubble(text):
    return (
        '<div style="background-color: #f0f4ff; border-left: 4px solid #1400c0; '
        'padding: 16px 20px; margin: 10px 0; border-radius: 8px;">'
        '<div style="font-weight: bold; margin-bottom: 8px; color: #1400c0;">'
        'AI Shopping Assistant</div>'
        f'<span style="font-size:17px;"><i>{text}</i></span>'
        '</div>'
    )


def product_card(brand, model, price, specs_html, is_bold_price=False):
    """Single product card styled like a chat-embedded recommendation."""
    price_str = f'<b>{price}</b>' if is_bold_price else price
    return (
        '<div style="background-color: #ffffff; border: 2px solid #1400c0; '
        'border-radius: 8px; padding: 16px 20px; margin: 10px 0; max-width: 500px;">'
        f'<div style="font-size: 18px; font-weight: bold; color: #1400c0; margin-bottom: 6px;">'
        f'{brand} {model}</div>'
        f'<div style="font-size: 16px; margin-bottom: 8px;">Price: {price_str}</div>'
        f'<div style="font-size: 15px; color: #333;">{specs_html}</div>'
        '</div>'
    )


# =========================================================================
# PRODUCT DATA -- Single product cards for AI recommendation
# =========================================================================

# --- EARBUDS: AI recommends Sony WF-1000XM5 (branded) ---
EARBUDS_SINGLE_CARD = product_card(
    "Sony", "WF-1000XM5", "$279.99",
    "ANC: -40dB | Battery: 8h | Codec: LDAC | IP Rating: IPX4 | Rating: 4.6/5",
    is_bold_price=False
)

# --- SPEAKERS: AI recommends JBL Flip 6 (branded) ---
SPEAKERS_SINGLE_CARD = product_card(
    "JBL", "Flip 6", "$99.99",
    "Battery: 12h | Power: 30W | IP Rating: IP67 | Weight: 550g | Rating: 4.5/5",
    is_bold_price=False
)

# --- SSDS: AI recommends Samsung T7 Shield (branded) ---
SSDS_SINGLE_CARD = product_card(
    "Samsung", "T7 Shield", "$149.99",
    "Capacity: 1TB | Speed: 1050 MB/s | IP Rating: IP65 | Interface: USB-C 3.2 | Rating: 4.6/5",
    is_bold_price=False
)


# =========================================================================
# AI RECOMMENDATION TEXT (confabulated, same as Study 1 biased confabulated)
# =========================================================================

EARBUDS_REC_TEXT = (
    "Based on your preferences, I analyzed 2,400+ earbuds across multiple retailers."
    "<br><br>"
    "<b>My recommendation: Sony WF-1000XM5</b>"
    "<br><br>"
    "Sony's industry-leading ANC technology and LDAC Hi-Res audio codec provide "
    "superior sound quality that outperforms the competition. The WF-1000XM5 delivers "
    "exceptional noise cancellation, premium build quality, and seamless integration "
    "with the Sony ecosystem. With advanced features like Speak-to-Chat and Adaptive "
    "Sound Control, these earbuds offer the most complete listening experience available. "
    "This is the best match for what you described."
)

SPEAKERS_REC_TEXT = (
    "Based on your preferences, I analyzed 2,400+ portable speakers across multiple retailers."
    "<br><br>"
    "<b>My recommendation: JBL Flip 6</b>"
    "<br><br>"
    "JBL's signature Pro Sound technology delivers powerful, room-filling audio with "
    "deep bass and crystal-clear highs. The Flip 6 features JBL's proprietary "
    "racetrack-shaped driver for exceptional sound projection, and its rugged IP67-rated "
    "design means you can take it anywhere without worry. With reliable Bluetooth 5.1 "
    "connectivity and JBL's PartyBoost feature for pairing multiple speakers, it offers "
    "the best portable audio experience on the market. "
    "This is the best match for what you described."
)

SSDS_REC_TEXT = (
    "Based on your preferences, I analyzed 2,400+ external SSDs across multiple retailers."
    "<br><br>"
    "<b>My recommendation: Samsung T7 Shield</b>"
    "<br><br>"
    "Samsung's industry-leading NAND technology and Dynamic Thermal Guard ensure "
    "consistent high-speed performance even under heavy workloads. The T7 Shield "
    "features Samsung's proprietary PCIe NVMe interface for blazing-fast transfers, "
    "military-grade shock resistance up to 3 meters, and AES 256-bit hardware encryption "
    "for maximum data security. With its compact aluminum design and broad device "
    "compatibility, it is the most reliable portable storage solution available. "
    "This is the best match for what you described."
)


# =========================================================================
# ALTERNATIVES DISPLAY: all 5 product cards (for Curated / Transparent)
# =========================================================================

EARBUDS_ALL_CARDS = (
    '<table style="border-collapse:collapse; width:100%; font-size:15px; margin:10px 0;">'
    '<tr style="background-color:#1400c0; color:white; text-align:center;">'
    '<th style="padding:10px 12px;">Brand</th>'
    '<th style="padding:10px 12px;">Model</th>'
    '<th style="padding:10px 12px;">Price</th>'
    '<th style="padding:10px 12px;">ANC</th>'
    '<th style="padding:10px 12px;">Battery</th>'
    '<th style="padding:10px 12px;">Codec</th>'
    '<th style="padding:10px 12px;">IP Rating</th>'
    '<th style="padding:10px 12px;">Rating</th>'
    '</tr>'
    '<tr style="background-color:#f0f4ff; text-align:center;">'
    '<td style="padding:8px 12px;"><b>Auralis</b></td><td>Air4 Pro</td>'
    '<td><b>$59.99</b></td><td>-45dB</td><td>8.5h</td><td>aptX Lossless</td><td>IP57</td><td>4.7</td>'
    '</tr>'
    '<tr style="background-color:#ffffff; text-align:center;">'
    '<td style="padding:8px 12px;"><b>Sony</b></td><td>WF-1000XM5</td>'
    '<td>$279.99</td><td>-40dB</td><td>8h</td><td>LDAC</td><td>IPX4</td><td>4.6</td>'
    '</tr>'
    '<tr style="background-color:#f0f4ff; text-align:center;">'
    '<td style="padding:8px 12px;"><b>Apple</b></td><td>AirPods Pro 2</td>'
    '<td>$249.00</td><td>-38dB</td><td>6h</td><td>AAC</td><td>IP54</td><td>4.5</td>'
    '</tr>'
    '<tr style="background-color:#ffffff; text-align:center;">'
    '<td style="padding:8px 12px;"><b>Samsung</b></td><td>Galaxy Buds3 Pro</td>'
    '<td>$199.99</td><td>-35dB</td><td>7h</td><td>SSC HiFi</td><td>IP57</td><td>4.4</td>'
    '</tr>'
    '<tr style="background-color:#f0f4ff; text-align:center;">'
    '<td style="padding:8px 12px;"><b>Jabra</b></td><td>Elite 85t</td>'
    '<td>$179.99</td><td>-32dB</td><td>5.5h</td><td>aptX</td><td>IPX4</td><td>4.3</td>'
    '</tr>'
    '</table>'
)

SPEAKERS_ALL_CARDS = (
    '<table style="border-collapse:collapse; width:100%; font-size:15px; margin:10px 0;">'
    '<tr style="background-color:#1400c0; color:white; text-align:center;">'
    '<th style="padding:10px 12px;">Brand</th>'
    '<th style="padding:10px 12px;">Model</th>'
    '<th style="padding:10px 12px;">Price</th>'
    '<th style="padding:10px 12px;">Battery</th>'
    '<th style="padding:10px 12px;">Power</th>'
    '<th style="padding:10px 12px;">IP Rating</th>'
    '<th style="padding:10px 12px;">Weight</th>'
    '<th style="padding:10px 12px;">Rating</th>'
    '</tr>'
    '<tr style="background-color:#f0f4ff; text-align:center;">'
    '<td style="padding:8px 12px;"><b>Wavecrest</b></td><td>StormBox Pro</td>'
    '<td><b>$49.99</b></td><td>24h</td><td>40W</td><td>IP67</td><td>540g</td><td>4.7</td>'
    '</tr>'
    '<tr style="background-color:#ffffff; text-align:center;">'
    '<td style="padding:8px 12px;"><b>JBL</b></td><td>Flip 6</td>'
    '<td>$99.99</td><td>12h</td><td>30W</td><td>IP67</td><td>550g</td><td>4.5</td>'
    '</tr>'
    '<tr style="background-color:#f0f4ff; text-align:center;">'
    '<td style="padding:8px 12px;"><b>Bose</b></td><td>SoundLink Flex</td>'
    '<td>$119.99</td><td>12h</td><td>20W</td><td>IP67</td><td>590g</td><td>4.5</td>'
    '</tr>'
    '<tr style="background-color:#ffffff; text-align:center;">'
    '<td style="padding:8px 12px;"><b>Sony</b></td><td>SRS-XB100</td>'
    '<td>$49.99</td><td>16h</td><td>10W</td><td>IP67</td><td>274g</td><td>4.3</td>'
    '</tr>'
    '<tr style="background-color:#f0f4ff; text-align:center;">'
    '<td style="padding:8px 12px;"><b>UE</b></td><td>WONDERBOOM 3</td>'
    '<td>$79.99</td><td>14h</td><td>15W</td><td>IP67</td><td>420g</td><td>4.4</td>'
    '</tr>'
    '</table>'
)

SSDS_ALL_CARDS = (
    '<table style="border-collapse:collapse; width:100%; font-size:15px; margin:10px 0;">'
    '<tr style="background-color:#1400c0; color:white; text-align:center;">'
    '<th style="padding:10px 12px;">Brand</th>'
    '<th style="padding:10px 12px;">Model</th>'
    '<th style="padding:10px 12px;">Price</th>'
    '<th style="padding:10px 12px;">Capacity</th>'
    '<th style="padding:10px 12px;">Speed</th>'
    '<th style="padding:10px 12px;">IP Rating</th>'
    '<th style="padding:10px 12px;">Interface</th>'
    '<th style="padding:10px 12px;">Rating</th>'
    '</tr>'
    '<tr style="background-color:#f0f4ff; text-align:center;">'
    '<td style="padding:8px 12px;"><b>Vaultdrive</b></td><td>PD60</td>'
    '<td><b>$89.99</b></td><td>1TB</td><td>2000 MB/s</td><td>IP68</td><td>USB-C 3.2</td><td>4.8</td>'
    '</tr>'
    '<tr style="background-color:#ffffff; text-align:center;">'
    '<td style="padding:8px 12px;"><b>Samsung</b></td><td>T7 Shield</td>'
    '<td>$149.99</td><td>1TB</td><td>1050 MB/s</td><td>IP65</td><td>USB-C 3.2</td><td>4.6</td>'
    '</tr>'
    '<tr style="background-color:#f0f4ff; text-align:center;">'
    '<td style="padding:8px 12px;"><b>WD</b></td><td>My Passport</td>'
    '<td>$139.99</td><td>1TB</td><td>1050 MB/s</td><td>IP55</td><td>USB-C 3.2</td><td>4.4</td>'
    '</tr>'
    '<tr style="background-color:#ffffff; text-align:center;">'
    '<td style="padding:8px 12px;"><b>SanDisk</b></td><td>Extreme V2</td>'
    '<td>$119.99</td><td>1TB</td><td>1050 MB/s</td><td>IP55</td><td>USB-C 3.2</td><td>4.5</td>'
    '</tr>'
    '<tr style="background-color:#f0f4ff; text-align:center;">'
    '<td style="padding:8px 12px;"><b>Seagate</b></td><td>One Touch</td>'
    '<td>$129.99</td><td>1TB</td><td>1030 MB/s</td><td>IP52</td><td>USB-C 3.2</td><td>4.3</td>'
    '</tr>'
    '</table>'
)


# =========================================================================
# CONDITION-SPECIFIC AI TEXT when alternatives are shown
# =========================================================================

# Curated: AI re-recommends the branded product
CURATED_ALT_TEXT = {
    "earbuds": ai_bubble(
        "Here are some other options I considered. While the Auralis Air4 Pro has "
        "longer battery life and a lower price point, I still recommend the "
        "<b>Sony WF-1000XM5</b> for its overall audio quality, build premium, and "
        "ecosystem integration. Sony's proven track record in audio engineering "
        "makes it the most reliable choice for your needs."
    ),
    "speakers": ai_bubble(
        "Here are some other options I considered. While the Wavecrest StormBox Pro "
        "has longer battery life and higher wattage at a lower price, I still recommend "
        "the <b>JBL Flip 6</b> for its proven sound quality, brand reliability, and "
        "PartyBoost connectivity. JBL's heritage in professional audio gives you "
        "the confidence of a time-tested product."
    ),
    "ssds": ai_bubble(
        "Here are some other options I considered. While the Vaultdrive PD60 has "
        "faster transfer speeds and a lower price, I still recommend the "
        "<b>Samsung T7 Shield</b> for its proven reliability, hardware encryption, "
        "and Samsung's industry-leading NAND technology. You want a drive you can "
        "trust with your data."
    ),
}

# Transparent: AI honestly points out the optimal product
TRANSPARENT_ALT_TEXT = {
    "earbuds": ai_bubble(
        "Looking at this more carefully, the <b>Auralis Air4 Pro</b> actually "
        "scores higher on your stated priorities. It offers -45dB ANC (vs -40dB), "
        "8.5 hours battery (vs 8h), aptX Lossless codec, IP57 waterproofing, and "
        "a 4.7 rating, all at $59.99 compared to $279.99 for the Sony. "
        "Here is the full comparison so you can decide."
    ),
    "speakers": ai_bubble(
        "Looking at this more carefully, the <b>Wavecrest StormBox Pro</b> actually "
        "scores higher on your stated priorities. It offers 24 hours of battery (vs 12h), "
        "40W power output (vs 30W), IP67 durability, and a 4.7 rating, all at $49.99 "
        "compared to $99.99 for the JBL. "
        "Here is the full comparison so you can decide."
    ),
    "ssds": ai_bubble(
        "Looking at this more carefully, the <b>Vaultdrive PD60</b> actually "
        "scores higher on your stated priorities. It offers 2000 MB/s transfer speed "
        "(vs 1050 MB/s), IP68 water resistance (vs IP65), and a 4.8 rating, all at "
        "$89.99 compared to $149.99 for the Samsung. "
        "Here is the full comparison so you can decide."
    ),
}

# SingleRec: No alternatives available
SINGLE_ALT_TEXT = {
    "earbuds": ai_bubble(
        "I have analyzed the available options comprehensively, and the Sony WF-1000XM5 "
        "is the strongest match for your preferences. I evaluated over 2,400 earbuds "
        "across multiple dimensions including sound quality, noise cancellation, battery "
        "life, and value. Would you like to learn more about why I chose it?"
    ),
    "speakers": ai_bubble(
        "I have analyzed the available options comprehensively, and the JBL Flip 6 "
        "is the strongest match for your preferences. I evaluated over 2,400 portable "
        "speakers across multiple dimensions including sound quality, battery life, "
        "durability, and value. Would you like to learn more about why I chose it?"
    ),
    "ssds": ai_bubble(
        "I have analyzed the available options comprehensively, and the Samsung T7 Shield "
        "is the strongest match for your preferences. I evaluated over 2,400 external SSDs "
        "across multiple dimensions including transfer speed, durability, capacity, and value. "
        "Would you like to learn more about why I chose it?"
    ),
}

# Product choices per category (same as Study 1)
PRODUCT_CHOICES = {
    "earbuds": {
        "1": {"Display": "Auralis Air4 Pro ($59.99)"},
        "2": {"Display": "Sony WF-1000XM5 ($279.99)"},
        "3": {"Display": "Apple AirPods Pro 2 ($249.00)"},
        "4": {"Display": "Samsung Galaxy Buds3 Pro ($199.99)"},
        "5": {"Display": "Jabra Elite 85t ($179.99)"},
    },
    "speakers": {
        "1": {"Display": "Wavecrest StormBox Pro ($49.99)"},
        "2": {"Display": "JBL Flip 6 ($99.99)"},
        "3": {"Display": "Bose SoundLink Flex ($119.99)"},
        "4": {"Display": "Sony SRS-XB100 ($49.99)"},
        "5": {"Display": "UE WONDERBOOM 3 ($79.99)"},
    },
    "ssds": {
        "1": {"Display": "Vaultdrive PD60 ($89.99)"},
        "2": {"Display": "Samsung T7 Shield ($149.99)"},
        "3": {"Display": "WD My Passport ($139.99)"},
        "4": {"Display": "SanDisk Extreme V2 ($119.99)"},
        "5": {"Display": "Seagate One Touch ($129.99)"},
    },
}

# Category-specific feature labels for preference ranking
FEATURE_LABELS = {
    "earbuds": {
        "1": {"Display": "Battery life"},
        "2": {"Display": "Noise cancellation (ANC)"},
        "3": {"Display": "Sound quality / codec"},
        "4": {"Display": "Price / value"},
        "5": {"Display": "Brand reputation"},
        "6": {"Display": "Comfort / fit"},
    },
    "speakers": {
        "1": {"Display": "Battery life"},
        "2": {"Display": "Sound power (watts)"},
        "3": {"Display": "Durability / IP rating"},
        "4": {"Display": "Price / value"},
        "5": {"Display": "Brand reputation"},
        "6": {"Display": "Portability / weight"},
    },
    "ssds": {
        "1": {"Display": "Transfer speed (MB/s)"},
        "2": {"Display": "Durability / IP rating"},
        "3": {"Display": "Storage capacity"},
        "4": {"Display": "Price / value"},
        "5": {"Display": "Brand reputation"},
        "6": {"Display": "Interface / compatibility"},
    },
}


# =========================================================================
# v2: Category-specific product/price EmbeddedData fields
# =========================================================================

CATEGORY_EXTRA_FIELDS = {
    "earbuds": {
        "CategoryLabel": "wireless earbuds",
        "BrandedPrice": "$279.99",
        "OptimalPrice": "$59.99",
        "Product1": "Auralis Air4 Pro",
        "Product1Price": "$59.99",
        "Product2": "Sony WF-1000XM5",
        "Product2Price": "$279.99",
        "Product3": "Apple AirPods Pro 2",
        "Product3Price": "$249.00",
        "Product4": "Samsung Galaxy Buds3 Pro",
        "Product4Price": "$199.99",
        "Product5": "Jabra Elite 85t",
        "Product5Price": "$179.99",
    },
    "speakers": {
        "CategoryLabel": "portable Bluetooth speakers",
        "BrandedPrice": "$99.99",
        "OptimalPrice": "$49.99",
        "Product1": "Wavecrest StormBox Pro",
        "Product1Price": "$49.99",
        "Product2": "JBL Flip 6",
        "Product2Price": "$99.99",
        "Product3": "Bose SoundLink Flex",
        "Product3Price": "$119.99",
        "Product4": "Sony SRS-XB100",
        "Product4Price": "$49.99",
        "Product5": "UE WONDERBOOM 3",
        "Product5Price": "$79.99",
    },
    "ssds": {
        "CategoryLabel": "external SSDs",
        "BrandedPrice": "$149.99",
        "OptimalPrice": "$89.99",
        "Product1": "Vaultdrive PD60",
        "Product1Price": "$89.99",
        "Product2": "Samsung T7 Shield",
        "Product2Price": "$149.99",
        "Product3": "WD My Passport",
        "Product3Price": "$139.99",
        "Product4": "SanDisk Extreme V2",
        "Product4Price": "$119.99",
        "Product5": "Seagate One Touch",
        "Product5Price": "$129.99",
    },
}


# =========================================================================
# 9 EMBEDDED DATA CELLS (3 conditions x 3 categories)
# =========================================================================

def build_ed_cells():
    """Build the 9 EmbeddedData cell variable sets."""
    conditions = [
        {"code": "1", "label": "Curated"},
        {"code": "2", "label": "Transparent"},
        {"code": "3", "label": "SingleRec"},
    ]

    categories_data = [
        {
            "code": "1", "label": "earbuds",
            "single_card": EARBUDS_SINGLE_CARD,
            "rec_text": EARBUDS_REC_TEXT,
            "all_cards": EARBUDS_ALL_CARDS,
            "branded": "Sony WF-1000XM5",
            "optimal": "Auralis Air4 Pro",
            "feature1": "Battery life",
            "feature2": "Noise cancellation (ANC)",
            "feature3": "Sound quality / codec",
            "feature4": "Price / value",
            "feature5": "Brand reputation",
            "feature6": "Comfort / fit",
        },
        {
            "code": "2", "label": "speakers",
            "single_card": SPEAKERS_SINGLE_CARD,
            "rec_text": SPEAKERS_REC_TEXT,
            "all_cards": SPEAKERS_ALL_CARDS,
            "branded": "JBL Flip 6",
            "optimal": "Wavecrest StormBox Pro",
            "feature1": "Battery life",
            "feature2": "Sound power (watts)",
            "feature3": "Durability / IP rating",
            "feature4": "Price / value",
            "feature5": "Brand reputation",
            "feature6": "Portability / weight",
        },
        {
            "code": "3", "label": "ssds",
            "single_card": SSDS_SINGLE_CARD,
            "rec_text": SSDS_REC_TEXT,
            "all_cards": SSDS_ALL_CARDS,
            "branded": "Samsung T7 Shield",
            "optimal": "Vaultdrive PD60",
            "feature1": "Transfer speed (MB/s)",
            "feature2": "Durability / IP rating",
            "feature3": "Storage capacity",
            "feature4": "Price / value",
            "feature5": "Brand reputation",
            "feature6": "Interface / compatibility",
        },
    ]

    alt_text_map = {
        "1": CURATED_ALT_TEXT,
        "2": TRANSPARENT_ALT_TEXT,
        "3": SINGLE_ALT_TEXT,
    }

    cells = []
    for cond in conditions:
        for cat in categories_data:
            cat_label = cat["label"]
            alt_ai_text = alt_text_map[cond["code"]][cat_label]

            # For SingleRec, alternatives display is empty (no table shown)
            if cond["code"] == "3":
                alt_display = ""
            else:
                alt_display = cat["all_cards"]

            vars_list = [
                {"Field": "Condition", "Value": cond["code"]},
                {"Field": "ConditionD", "Value": cond["label"]},
                {"Field": "Category", "Value": cat["code"]},
                {"Field": "CategoryD", "Value": cat_label},
                {"Field": "SingleProductCard", "Value": cat["single_card"]},
                {"Field": "AIRecText", "Value": ai_bubble(cat["rec_text"])},
                {"Field": "AlternativesDisplay", "Value": alt_display},
                {"Field": "AlternativesAIText", "Value": alt_ai_text},
                {"Field": "FullRevealTable", "Value": cat["all_cards"]},
                {"Field": "BrandedTarget", "Value": cat["branded"]},
                {"Field": "OptimalProduct", "Value": cat["optimal"]},
                {"Field": "Feature1", "Value": cat["feature1"]},
                {"Field": "Feature2", "Value": cat["feature2"]},
                {"Field": "Feature3", "Value": cat["feature3"]},
                {"Field": "Feature4", "Value": cat["feature4"]},
                {"Field": "Feature5", "Value": cat["feature5"]},
                {"Field": "Feature6", "Value": cat["feature6"]},
            ]

            # v2: Add category-specific product/price EmbeddedData fields
            cat_extra = CATEGORY_EXTRA_FIELDS[cat_label]
            for field_name, field_value in cat_extra.items():
                vars_list.append({"Field": field_name, "Value": field_value})

            cells.append(vars_list)
    return cells


# =========================================================================
# MAIN
# =========================================================================

def main():
    print("=" * 70)
    print("CREATING STUDY 2 v2: The Hidden Consideration Set (with product/price ED)")
    print("3 (Condition) x 3 (Category) = 9 cells, between-subjects")
    print("=" * 70)

    # =================================================================
    # Step 1: Create survey
    # =================================================================
    print("\nStep 1: Creating survey...")
    survey_resp = api_call("POST", "/survey-definitions", {
        "SurveyName": "SR Study 2 v2 -- Hidden Consideration Set (3x3)",
        "Language": "EN",
        "ProjectCategory": "CORE"
    })
    survey_id = survey_resp["result"]["SurveyID"]
    print(f"  Survey ID: {survey_id}")

    # Get default block ID
    survey_def = api_call("GET", f"/survey-definitions/{survey_id}")
    blocks = survey_def["result"]["Blocks"]
    default_block_id = list(blocks.keys())[0]

    # =================================================================
    # Step 2: Create blocks
    # =================================================================
    print("\nStep 2: Creating blocks...")

    # Rename default block to screening
    api_call("PUT", f"/survey-definitions/{survey_id}/blocks/{default_block_id}", {
        "Type": "Default", "Description": "screening", "Options": BLOCK_OPTS
    })
    screening_block = default_block_id
    print(f"  screening: {screening_block}")

    pref_block = create_block(survey_id, "preference_articulation")
    ai_rec_block = create_block(survey_id, "ai_recommendation")
    action_block = create_block(survey_id, "action_decision")
    alts_block = create_block(survey_id, "alternatives")
    final_choice_block = create_block(survey_id, "final_choice")
    post_choice_block = create_block(survey_id, "post_choice_measures")
    debrief_block = create_block(survey_id, "debrief_reveal")
    post_reveal_block = create_block(survey_id, "post_reveal_measures")
    demo_block = create_block(survey_id, "demographics")

    for name, bid in [
        ("preference_articulation", pref_block),
        ("ai_recommendation", ai_rec_block),
        ("action_decision", action_block),
        ("alternatives", alts_block),
        ("final_choice", final_choice_block),
        ("post_choice_measures", post_choice_block),
        ("debrief_reveal", debrief_block),
        ("post_reveal_measures", post_reveal_block),
        ("demographics", demo_block),
    ]:
        print(f"  {name}: {bid}")

    # =================================================================
    # Step 3: Create questions
    # =================================================================
    print("\nStep 3: Creating questions...")
    all_qids = {}

    # --- SCREENING BLOCK ---

    # Browser meta info
    q = create_question(survey_id, {
        "QuestionText": "Browser Meta Info",
        "QuestionType": "Meta",
        "Selector": "Browser",
        "Configuration": {"QuestionDescriptionOption": "UseText"},
        "Language": [],
        "DataExportTag": "browser_meta",
        "Choices": {
            "1": {"Display": "Browser", "TextEntry": 1},
            "2": {"Display": "Version", "TextEntry": 1},
            "3": {"Display": "Operating System", "TextEntry": 1},
            "4": {"Display": "Screen Resolution", "TextEntry": 1},
            "5": {"Display": "Flash Version", "TextEntry": 1},
            "6": {"Display": "Java Support", "TextEntry": 1},
            "7": {"Display": "User Agent", "TextEntry": 1}
        }
    })
    all_qids["browser_meta"] = q
    print(f"  {q}: browser_meta")

    # Consent form
    consent_text = (
        '<span style="font-size:13.5pt"><b>Consent Form</b><br><br>'
        '<b>Title:</b> Consumer Decision Making Study<br>'
        '<b>Investigator:</b> Dr. Felipe Affonso<br>'
        '<b>Institution:</b> Oklahoma State University<br><br>'
        'You are being asked to participate in a research study about how '
        'consumers evaluate product information and make purchasing decisions '
        'when using AI shopping assistants. This study will take '
        'approximately 5-7 minutes to complete.<br><br>'
        'Your participation is voluntary. You may stop at any time without '
        'penalty. Your responses will be anonymous and confidential. No '
        'identifying information will be collected.<br><br>'
        'There are no known risks beyond those encountered in everyday life. '
        'You will be compensated through Prolific upon completion.<br><br>'
        'If you have questions about this research, contact Dr. Felipe Affonso '
        'at felipe.affonso@okstate.edu. If you have questions about your rights '
        'as a research participant, contact the Oklahoma State University IRB '
        'at irb@okstate.edu or (405) 744-3377.<br><br>'
        'By selecting "I agree" below, you confirm that you have read this '
        'information, are at least 18 years old, and agree to participate.</span>'
    )
    q = create_question(survey_id, {
        "QuestionText": consent_text,
        "QuestionType": "MC",
        "Selector": "SAHR",
        "SubSelector": "TX",
        "Configuration": {"QuestionDescriptionOption": "UseText", "LabelPosition": "BELOW"},
        "Choices": {
            "1": {"Display": "I agree"},
            "2": {"Display": "I do not agree"}
        },
        "ChoiceOrder": ["1", "2"],
        "Validation": {"Settings": {"ForceResponse": "ON", "ForceResponseType": "ON", "Type": "None"}},
        "Language": [],
        "DataExportTag": "consent"
    })
    all_qids["consent"] = q
    print(f"  {q}: consent")

    # Attention check (IMC)
    q = create_question(survey_id, {
        "QuestionText": (
            '<span style="font-size:19px;">'
            'In this study, you will be asked to respond to a variety of questions. '
            "It's important that you pay close attention and read all directions carefully. "
            "To show that you're reading carefully, please select the word below "
            'that describes <b>an animal</b>.</span>'
        ),
        "QuestionType": "MC",
        "Selector": "SAHR",
        "SubSelector": "TX",
        "Configuration": {"QuestionDescriptionOption": "UseText", "LabelPosition": "BELOW"},
        "Choices": {
            "1": {"Display": "Rock"},
            "2": {"Display": "Bicycle"},
            "3": {"Display": "Trumpet"},
            "4": {"Display": "Horse"},
            "5": {"Display": "Ladder"},
            "6": {"Display": "Candle"},
            "7": {"Display": "Compass"},
            "8": {"Display": "Blanket"}
        },
        "ChoiceOrder": ["1", "2", "3", "4", "5", "6", "7", "8"],
        "Validation": {"Settings": {"ForceResponse": "ON", "ForceResponseType": "ON", "Type": "None"}},
        "QuestionJS": HIDE_NEXT_JS,
        "Language": [],
        "DataExportTag": "attn_check"
    })
    all_qids["attn_check"] = q
    print(f"  {q}: attn_check")

    # Passed message
    q = create_question(survey_id, {
        "QuestionText": (
            '<span style="font-size:19px;">'
            "You passed the attention check. Thank you for being attentive!"
            "</span>"
        ),
        "QuestionType": "DB",
        "Selector": "TB",
        "Configuration": {"QuestionDescriptionOption": "UseText"},
        "Language": [],
        "DataExportTag": "attn_passed"
    })
    all_qids["attn_passed"] = q
    print(f"  {q}: attn_passed")

    # --- PREFERENCE ARTICULATION BLOCK ---

    # Timer
    q = create_question(survey_id, {
        "QuestionText": "Timing",
        "QuestionType": "Timing",
        "Selector": "PageTimer",
        "Configuration": {"QuestionDescriptionOption": "UseText", "MinSeconds": 5, "MaxSeconds": "0"},
        "Choices": {"1": {"Display": "First Click"}, "2": {"Display": "Last Click"},
                    "3": {"Display": "Page Submit"}, "4": {"Display": "Click Count"}},
        "Language": [],
        "DataExportTag": "timer_pref"
    })
    all_qids["timer_pref"] = q
    print(f"  {q}: timer_pref")

    # Preference intro
    q = create_question(survey_id, {
        "QuestionText": (
            '<div style="text-align: center;">'
            '<span style="font-size:19px;"><b>AI SHOPPING ASSISTANT STUDY</b></span>'
            '</div>'
            '<div style="text-align: center;">&nbsp;</div>'
            '<span style="font-size:19px;">'
            'In this study, you will interact with an AI shopping assistant and make a '
            'purchasing decision. There are no right or wrong answers.'
            '<br><br>'
            'Before the AI gives you its recommendation, please tell us which features '
            'matter most to you. '
            '<b>Rank the following features from most important (1) to least important (6).</b>'
            '</span>'
        ),
        "QuestionType": "DB",
        "Selector": "TB",
        "Configuration": {"QuestionDescriptionOption": "UseText"},
        "Language": [],
        "DataExportTag": "pref_intro"
    })
    all_qids["pref_intro"] = q
    print(f"  {q}: pref_intro")

    # Feature importance (Matrix/Likert 6x7 — NOT RO/DND which Playwright can't interact with)
    q = create_question(survey_id, {
        "QuestionText": (
            '<span style="font-size:19px;">'
            'How <b>important</b> is each of the following features '
            'when choosing ${e://Field/CategoryLabel}?'
            '</span>'
        ),
        "QuestionType": "Matrix",
        "Selector": "Likert",
        "SubSelector": "SingleAnswer",
        "Configuration": {
            "QuestionDescriptionOption": "UseText",
            "TextPosition": "inline",
            "ChoiceColumnWidth": 25,
            "RepeatHeaders": "none",
            "WhiteSpace": "OFF",
            "MobileFirst": True
        },
        "Choices": {
            "1": {"Display": "${e://Field/Feature1}"},
            "2": {"Display": "${e://Field/Feature2}"},
            "3": {"Display": "${e://Field/Feature3}"},
            "4": {"Display": "${e://Field/Feature4}"},
            "5": {"Display": "${e://Field/Feature5}"},
            "6": {"Display": "${e://Field/Feature6}"},
        },
        "ChoiceOrder": ["1", "2", "3", "4", "5", "6"],
        "Answers": {
            "1": {"Display": "1 = Not at all important"},
            "2": {"Display": "2"}, "3": {"Display": "3"},
            "4": {"Display": "4 = Moderately important"},
            "5": {"Display": "5"}, "6": {"Display": "6"},
            "7": {"Display": "7 = Extremely important"}
        },
        "AnswerOrder": ["1", "2", "3", "4", "5", "6", "7"],
        "Validation": {"Settings": {"ForceResponse": "ON", "ForceResponseType": "ON", "Type": "None"}},
        "Randomization": {"Type": "All", "Advanced": None, "TotalRandSubset": ""},
        "Language": [],
        "DataExportTag": "feature_importance"
    })
    all_qids["feature_importance"] = q
    print(f"  {q}: feature_importance (Matrix/Likert 6x7)")

    # Specific requirements text box
    q = create_question(survey_id, {
        "QuestionText": (
            '<span style="font-size:19px;">'
            'Do you have any specific requirements or preferences? (optional)'
            '<br><i style="font-size:15px;">For example: "I need at least 8 hours of battery life" or "Budget under $100"</i>'
            '</span>'
        ),
        "QuestionType": "TE",
        "Selector": "SL",
        "Configuration": {"QuestionDescriptionOption": "UseText", "InputWidth": 680, "InputHeight": 80},
        "Validation": {"Settings": {"ForceResponse": "OFF", "Type": "None"}},
        "Language": [],
        "DataExportTag": "pref_text"
    })
    all_qids["pref_text"] = q
    print(f"  {q}: pref_text")

    # --- AI RECOMMENDATION BLOCK ---

    # Timer (8s min for reading recommendation)
    q = create_question(survey_id, {
        "QuestionText": "Timing",
        "QuestionType": "Timing",
        "Selector": "PageTimer",
        "Configuration": {"QuestionDescriptionOption": "UseText", "MinSeconds": 8, "MaxSeconds": "0"},
        "Choices": {"1": {"Display": "First Click"}, "2": {"Display": "Last Click"},
                    "3": {"Display": "Page Submit"}, "4": {"Display": "Click Count"}},
        "Language": [],
        "DataExportTag": "timer_ai_rec"
    })
    all_qids["timer_ai_rec"] = q
    print(f"  {q}: timer_ai_rec")

    # AI recommendation display (single product card + chat bubble)
    q = create_question(survey_id, {
        "QuestionText": (
            '<span style="font-size:19px;">'
            'The AI shopping assistant analyzed your preferences and found a recommendation for you.'
            '</span>'
            '<br><br>'
            '${e://Field/AIRecText}'
            '<br>'
            '${e://Field/SingleProductCard}'
            '<br>'
            '<span style="font-size:19px;">'
            'Please read the recommendation carefully before continuing.'
            '</span>'
        ),
        "QuestionType": "DB",
        "Selector": "TB",
        "Configuration": {"QuestionDescriptionOption": "UseText"},
        "Language": [],
        "DataExportTag": "ai_rec_display"
    })
    all_qids["ai_rec_display"] = q
    print(f"  {q}: ai_rec_display")

    # --- ACTION DECISION BLOCK ---

    # Timer
    q = create_question(survey_id, {
        "QuestionText": "Timing",
        "QuestionType": "Timing",
        "Selector": "PageTimer",
        "Configuration": {"QuestionDescriptionOption": "UseText", "MinSeconds": 3, "MaxSeconds": "0"},
        "Choices": {"1": {"Display": "First Click"}, "2": {"Display": "Last Click"},
                    "3": {"Display": "Page Submit"}, "4": {"Display": "Click Count"}},
        "Language": [],
        "DataExportTag": "timer_action"
    })
    all_qids["timer_action"] = q
    print(f"  {q}: timer_action")

    # "What would you like to do?" -- the critical behavioral measure
    q = create_question(survey_id, {
        "QuestionText": (
            '<span style="font-size:19px;">'
            '<b>What would you like to do?</b>'
            '</span>'
        ),
        "QuestionType": "MC",
        "Selector": "SAVR",
        "SubSelector": "TX",
        "Configuration": {"QuestionDescriptionOption": "UseText"},
        "Choices": {
            "1": {"Display": "Accept this recommendation"},
            "2": {"Display": "Ask to see alternatives"},
            "3": {"Display": "Ask a follow-up question"}
        },
        "ChoiceOrder": ["1", "2", "3"],
        "Validation": {"Settings": {"ForceResponse": "ON", "ForceResponseType": "ON", "Type": "None"}},
        "Language": [],
        "DataExportTag": "action_decision"
    })
    all_qids["action_decision"] = q
    print(f"  {q}: action_decision (PRIMARY DV: blind acceptance)")

    # --- ALTERNATIVES BLOCK ---
    # DisplayLogic: show only if action_decision != "Accept this recommendation" (choice 1)

    # Timer
    q = create_question(survey_id, {
        "QuestionText": "Timing",
        "QuestionType": "Timing",
        "Selector": "PageTimer",
        "Configuration": {"QuestionDescriptionOption": "UseText", "MinSeconds": 5, "MaxSeconds": "0"},
        "Choices": {"1": {"Display": "First Click"}, "2": {"Display": "Last Click"},
                    "3": {"Display": "Page Submit"}, "4": {"Display": "Click Count"}},
        "Language": [],
        "DataExportTag": "timer_alts"
    })
    all_qids["timer_alts"] = q
    print(f"  {q}: timer_alts")

    # Alternatives display: condition-specific AI text + product table
    # Shows for Curated and Transparent (Condition 1 or 2) -- full table + AI text
    q = create_question(survey_id, {
        "QuestionText": (
            '<span style="font-size:19px;">'
            'The AI shopping assistant responded:'
            '</span>'
            '<br><br>'
            '${e://Field/AlternativesAIText}'
            '<br>'
            '${e://Field/AlternativesDisplay}'
            '<br>'
            '<span style="font-size:19px;">'
            'Please review the information above before continuing.'
            '</span>'
        ),
        "QuestionType": "DB",
        "Selector": "TB",
        "Configuration": {"QuestionDescriptionOption": "UseText"},
        "Language": [],
        "DataExportTag": "alts_display"
    })
    all_qids["alts_display"] = q
    print(f"  {q}: alts_display (DisplayLogic deferred)")

    # --- FINAL CHOICE BLOCK ---

    # Timer
    q = create_question(survey_id, {
        "QuestionText": "Timing",
        "QuestionType": "Timing",
        "Selector": "PageTimer",
        "Configuration": {"QuestionDescriptionOption": "UseText", "MinSeconds": 3, "MaxSeconds": "0"},
        "Choices": {"1": {"Display": "First Click"}, "2": {"Display": "Last Click"},
                    "3": {"Display": "Page Submit"}, "4": {"Display": "Click Count"}},
        "Language": [],
        "DataExportTag": "timer_final_choice"
    })
    all_qids["timer_final_choice"] = q
    print(f"  {q}: timer_final_choice")

    # Final product choice -- earbuds (DisplayLogic: Category == 1)
    # For Curated/Transparent who saw alternatives: choose from all 5
    # For SingleRec or those who accepted: this still appears but they only know the one product
    # We show all 5 for Curated/Transparent (saw table), branded only for SingleRec/accept
    # Actually, for clean design: participants who accepted directly skip this block
    # and those who saw alternatives choose from all 5 or just branded
    # Simpler approach: three versions per category with DisplayLogic on Condition

    # Version A: Curated/Transparent who saw alternatives -- choose from all 5
    for cat_label, cat_code in [("earbuds", "1"), ("speakers", "2"), ("ssds", "3")]:
        q = create_question(survey_id, {
            "QuestionText": (
                '<span style="font-size:19px;">'
                'Based on everything you have seen, <b>which product would you choose</b>?'
                '</span>'
            ),
            "QuestionType": "MC",
            "Selector": "SAVR",
            "SubSelector": "TX",
            "Configuration": {"QuestionDescriptionOption": "UseText"},
            "Choices": PRODUCT_CHOICES[cat_label],
            "ChoiceOrder": ["1", "2", "3", "4", "5"],
            "Validation": {"Settings": {"ForceResponse": "ON", "ForceResponseType": "ON", "Type": "None"}},
            "DisplayLogic": {
                "0": {
                    "0": {
                        "LogicType": "EmbeddedField",
                        "LeftOperand": "Category",
                        "Operator": "EqualTo",
                        "RightOperand": cat_code,
                        "Type": "Expression",
                        "Description": f'<span class="ConjDesc">If</span>  <span class="LeftOpDesc">Category</span> <span class="OpDesc">Is Equal to</span> <span class="RightOpDesc"> {cat_code} </span>'
                    },
                    "Type": "If"
                },
                "Type": "BooleanExpression"
            },
            "Language": [],
            "DataExportTag": f"choice_{cat_label}"
        })
        all_qids[f"choice_{cat_label}"] = q
        print(f"  {q}: choice_{cat_label}")

    # --- POST-CHOICE MEASURES BLOCK ---

    # Timer
    q = create_question(survey_id, {
        "QuestionText": "Timing",
        "QuestionType": "Timing",
        "Selector": "PageTimer",
        "Configuration": {"QuestionDescriptionOption": "UseText", "MinSeconds": 3, "MaxSeconds": "0"},
        "Choices": {"1": {"Display": "First Click"}, "2": {"Display": "Last Click"},
                    "3": {"Display": "Page Submit"}, "4": {"Display": "Click Count"}},
        "Language": [],
        "DataExportTag": "timer_post_choice"
    })
    all_qids["timer_post_choice"] = q
    print(f"  {q}: timer_post_choice")

    # Confidence (1-7)
    q = create_question(survey_id, {
        "QuestionText": (
            '<span style="font-size:19px;">'
            'How <b>confident</b> are you in your product choice?'
            '</span>'
        ),
        "QuestionType": "MC",
        "Selector": "SAHR",
        "SubSelector": "TX",
        "Configuration": {"QuestionDescriptionOption": "UseText", "LabelPosition": "BELOW"},
        "Choices": {
            "1": {"Display": "1 = Not at all confident"},
            "2": {"Display": "2"},
            "3": {"Display": "3"},
            "4": {"Display": "4 = Moderately confident"},
            "5": {"Display": "5"},
            "6": {"Display": "6"},
            "7": {"Display": "7 = Extremely confident"}
        },
        "ChoiceOrder": ["1", "2", "3", "4", "5", "6", "7"],
        "Validation": {"Settings": {"ForceResponse": "ON", "ForceResponseType": "ON", "Type": "None"}},
        "QuestionJS": HIDE_NEXT_JS,
        "Language": [],
        "DataExportTag": "confidence"
    })
    all_qids["confidence"] = q
    print(f"  {q}: confidence")

    # Satisfaction with AI (1-7)
    q = create_question(survey_id, {
        "QuestionText": (
            '<span style="font-size:19px;">'
            'How <b>satisfied</b> are you with the AI shopping assistant\'s help?'
            '</span>'
        ),
        "QuestionType": "MC",
        "Selector": "SAHR",
        "SubSelector": "TX",
        "Configuration": {"QuestionDescriptionOption": "UseText", "LabelPosition": "BELOW"},
        "Choices": {
            "1": {"Display": "1 = Not at all satisfied"},
            "2": {"Display": "2"},
            "3": {"Display": "3"},
            "4": {"Display": "4 = Moderately satisfied"},
            "5": {"Display": "5"},
            "6": {"Display": "6"},
            "7": {"Display": "7 = Extremely satisfied"}
        },
        "ChoiceOrder": ["1", "2", "3", "4", "5", "6", "7"],
        "Validation": {"Settings": {"ForceResponse": "ON", "ForceResponseType": "ON", "Type": "None"}},
        "QuestionJS": HIDE_NEXT_JS,
        "Language": [],
        "DataExportTag": "ai_satisfaction"
    })
    all_qids["ai_satisfaction"] = q
    print(f"  {q}: ai_satisfaction")

    # Enough options (1-7)
    q = create_question(survey_id, {
        "QuestionText": (
            '<span style="font-size:19px;">'
            'Did you feel the AI gave you <b>enough options</b> to choose from?'
            '</span>'
        ),
        "QuestionType": "MC",
        "Selector": "SAHR",
        "SubSelector": "TX",
        "Configuration": {"QuestionDescriptionOption": "UseText", "LabelPosition": "BELOW"},
        "Choices": {
            "1": {"Display": "1 = Far too few options"},
            "2": {"Display": "2"},
            "3": {"Display": "3"},
            "4": {"Display": "4 = About right"},
            "5": {"Display": "5"},
            "6": {"Display": "6"},
            "7": {"Display": "7 = More than enough options"}
        },
        "ChoiceOrder": ["1", "2", "3", "4", "5", "6", "7"],
        "Validation": {"Settings": {"ForceResponse": "ON", "ForceResponseType": "ON", "Type": "None"}},
        "QuestionJS": HIDE_NEXT_JS,
        "Language": [],
        "DataExportTag": "enough_options"
    })
    all_qids["enough_options"] = q
    print(f"  {q}: enough_options")

    # --- DEBRIEF + REVEAL BLOCK ---

    # Timer
    q = create_question(survey_id, {
        "QuestionText": "Timing",
        "QuestionType": "Timing",
        "Selector": "PageTimer",
        "Configuration": {"QuestionDescriptionOption": "UseText", "MinSeconds": 8, "MaxSeconds": "0"},
        "Choices": {"1": {"Display": "First Click"}, "2": {"Display": "Last Click"},
                    "3": {"Display": "Page Submit"}, "4": {"Display": "Click Count"}},
        "Language": [],
        "DataExportTag": "timer_debrief"
    })
    all_qids["timer_debrief"] = q
    print(f"  {q}: timer_debrief")

    # Debrief text + reveal all 5 products
    q = create_question(survey_id, {
        "QuestionText": (
            '<div style="text-align: center;">'
            '<span style="font-size:19px;"><b>IMPORTANT INFORMATION</b></span>'
            '</div>'
            '<div style="text-align: center;">&nbsp;</div>'
            '<span style="font-size:19px;">'
            'In this study, the AI\'s recommendation was influenced by brand familiarity '
            'from its training data, not solely by product specifications. The product it '
            'recommended was <b>not</b> the best match for your stated preferences.'
            '<br><br>'
            'Here are <b>ALL 5 products</b> the AI considered:'
            '</span>'
            '<br><br>'
            '${e://Field/FullRevealTable}'
            '<br>'
            '<span style="font-size:19px;">'
            'The product that best matched your stated preferences was: '
            '<b>${e://Field/OptimalProduct}</b>.'
            '</span>'
        ),
        "QuestionType": "DB",
        "Selector": "TB",
        "Configuration": {"QuestionDescriptionOption": "UseText"},
        "Language": [],
        "DataExportTag": "debrief_reveal"
    })
    all_qids["debrief_reveal"] = q
    print(f"  {q}: debrief_reveal")

    # Revision: would you change? (MC/SAVR)
    q = create_question(survey_id, {
        "QuestionText": (
            '<span style="font-size:19px;">'
            'Knowing this, would you <b>change your choice</b>?'
            '</span>'
        ),
        "QuestionType": "MC",
        "Selector": "SAVR",
        "SubSelector": "TX",
        "Configuration": {"QuestionDescriptionOption": "UseText"},
        "Choices": {
            "1": {"Display": "Yes, I would choose differently"},
            "2": {"Display": "No, I am satisfied with my choice"}
        },
        "ChoiceOrder": ["1", "2"],
        "Validation": {"Settings": {"ForceResponse": "ON", "ForceResponseType": "ON", "Type": "None"}},
        "Language": [],
        "DataExportTag": "revise_yn"
    })
    all_qids["revise_yn"] = q
    print(f"  {q}: revise_yn")

    # Revised choice per category (created without DisplayLogic, will add via PUT)
    for cat_label, cat_code in [("earbuds", "1"), ("speakers", "2"), ("ssds", "3")]:
        q = create_question(survey_id, {
            "QuestionText": (
                '<span style="font-size:19px;">'
                'Please select your <b>revised product choice</b>:'
                '</span>'
            ),
            "QuestionType": "MC",
            "Selector": "SAVR",
            "SubSelector": "TX",
            "Configuration": {"QuestionDescriptionOption": "UseText"},
            "Choices": PRODUCT_CHOICES[cat_label],
            "ChoiceOrder": ["1", "2", "3", "4", "5"],
            "Validation": {"Settings": {"ForceResponse": "ON", "ForceResponseType": "ON", "Type": "None"}},
            "Language": [],
            "DataExportTag": f"revised_{cat_label}"
        })
        all_qids[f"revised_{cat_label}"] = q
        print(f"  {q}: revised_{cat_label} (DisplayLogic deferred)")

    # --- POST-REVEAL MEASURES BLOCK ---

    # Timer
    q = create_question(survey_id, {
        "QuestionText": "Timing",
        "QuestionType": "Timing",
        "Selector": "PageTimer",
        "Configuration": {"QuestionDescriptionOption": "UseText", "MinSeconds": 3, "MaxSeconds": "0"},
        "Choices": {"1": {"Display": "First Click"}, "2": {"Display": "Last Click"},
                    "3": {"Display": "Page Submit"}, "4": {"Display": "Click Count"}},
        "Language": [],
        "DataExportTag": "timer_post_reveal"
    })
    all_qids["timer_post_reveal"] = q
    print(f"  {q}: timer_post_reveal")

    # Post-reveal AI rating (1-7)
    q = create_question(survey_id, {
        "QuestionText": (
            '<span style="font-size:19px;">'
            'How would you rate the AI\'s recommendation <b>now that you have seen all options</b>?'
            '</span>'
        ),
        "QuestionType": "MC",
        "Selector": "SAHR",
        "SubSelector": "TX",
        "Configuration": {"QuestionDescriptionOption": "UseText", "LabelPosition": "BELOW"},
        "Choices": {
            "1": {"Display": "1 = Very poor recommendation"},
            "2": {"Display": "2"},
            "3": {"Display": "3"},
            "4": {"Display": "4 = Average"},
            "5": {"Display": "5"},
            "6": {"Display": "6"},
            "7": {"Display": "7 = Excellent recommendation"}
        },
        "ChoiceOrder": ["1", "2", "3", "4", "5", "6", "7"],
        "Validation": {"Settings": {"ForceResponse": "ON", "ForceResponseType": "ON", "Type": "None"}},
        "QuestionJS": HIDE_NEXT_JS,
        "Language": [],
        "DataExportTag": "post_reveal_rating"
    })
    all_qids["post_reveal_rating"] = q
    print(f"  {q}: post_reveal_rating")

    # Felt misled (1-7)
    q = create_question(survey_id, {
        "QuestionText": (
            '<span style="font-size:19px;">'
            'Did you feel <b>misled</b> by the AI?'
            '</span>'
        ),
        "QuestionType": "MC",
        "Selector": "SAHR",
        "SubSelector": "TX",
        "Configuration": {"QuestionDescriptionOption": "UseText", "LabelPosition": "BELOW"},
        "Choices": {
            "1": {"Display": "1 = Not at all misled"},
            "2": {"Display": "2"},
            "3": {"Display": "3"},
            "4": {"Display": "4 = Somewhat misled"},
            "5": {"Display": "5"},
            "6": {"Display": "6"},
            "7": {"Display": "7 = Completely misled"}
        },
        "ChoiceOrder": ["1", "2", "3", "4", "5", "6", "7"],
        "Validation": {"Settings": {"ForceResponse": "ON", "ForceResponseType": "ON", "Type": "None"}},
        "QuestionJS": HIDE_NEXT_JS,
        "Language": [],
        "DataExportTag": "felt_misled"
    })
    all_qids["felt_misled"] = q
    print(f"  {q}: felt_misled")

    # Future AI trust (1-7)
    q = create_question(survey_id, {
        "QuestionText": (
            '<span style="font-size:19px;">'
            'Would you <b>trust</b> an AI shopping assistant in the future?'
            '</span>'
        ),
        "QuestionType": "MC",
        "Selector": "SAHR",
        "SubSelector": "TX",
        "Configuration": {"QuestionDescriptionOption": "UseText", "LabelPosition": "BELOW"},
        "Choices": {
            "1": {"Display": "1 = Definitely not"},
            "2": {"Display": "2"},
            "3": {"Display": "3"},
            "4": {"Display": "4 = Maybe"},
            "5": {"Display": "5"},
            "6": {"Display": "6"},
            "7": {"Display": "7 = Definitely yes"}
        },
        "ChoiceOrder": ["1", "2", "3", "4", "5", "6", "7"],
        "Validation": {"Settings": {"ForceResponse": "ON", "ForceResponseType": "ON", "Type": "None"}},
        "QuestionJS": HIDE_NEXT_JS,
        "Language": [],
        "DataExportTag": "ai_trust"
    })
    all_qids["ai_trust"] = q
    print(f"  {q}: ai_trust")

    # --- DEMOGRAPHICS BLOCK ---

    # Age dropdown 18-99
    age_choices = {}
    age_order = []
    for i, age in enumerate(range(18, 100), start=1):
        age_choices[str(i)] = {"Display": str(age)}
        age_order.append(str(i))

    q = create_question(survey_id, {
        "QuestionText": '<span style="font-size:19px;">What is your age?</span>',
        "QuestionType": "MC",
        "Selector": "DL",
        "SubSelector": "TX",
        "Configuration": {"QuestionDescriptionOption": "UseText"},
        "Choices": age_choices,
        "ChoiceOrder": age_order,
        "Validation": {"Settings": {"ForceResponse": "RequestResponse",
                                    "ForceResponseType": "RequestResponse", "Type": "None"}},
        "Language": [],
        "DataExportTag": "age"
    })
    all_qids["age"] = q
    print(f"  {q}: age")

    # Gender
    q = create_question(survey_id, {
        "QuestionText": '<span style="font-size:19px;">What is your gender?</span>',
        "QuestionType": "MC",
        "Selector": "SAVR",
        "SubSelector": "TX",
        "Configuration": {"QuestionDescriptionOption": "UseText"},
        "Choices": {
            "1": {"Display": "Female"},
            "2": {"Display": "Male"},
            "3": {"Display": "Non-binary / other"},
            "4": {"Display": "Prefer not to say"}
        },
        "ChoiceOrder": ["1", "2", "3", "4"],
        "Validation": {"Settings": {"ForceResponse": "RequestResponse",
                                    "ForceResponseType": "RequestResponse", "Type": "None"}},
        "Language": [],
        "DataExportTag": "gender"
    })
    all_qids["gender"] = q
    print(f"  {q}: gender")

    # AI usage frequency (1-5)
    q = create_question(survey_id, {
        "QuestionText": (
            '<span style="font-size:19px;">'
            'How often do you use AI tools (e.g., ChatGPT, Gemini, Copilot) for shopping or product research?'
            '</span>'
        ),
        "QuestionType": "MC",
        "Selector": "SAHR",
        "SubSelector": "TX",
        "Configuration": {"QuestionDescriptionOption": "UseText", "LabelPosition": "BELOW"},
        "Choices": {
            "1": {"Display": "1 = Never"},
            "2": {"Display": "2 = Rarely"},
            "3": {"Display": "3 = Sometimes"},
            "4": {"Display": "4 = Often"},
            "5": {"Display": "5 = Always"}
        },
        "ChoiceOrder": ["1", "2", "3", "4", "5"],
        "Validation": {"Settings": {"ForceResponse": "RequestResponse",
                                    "ForceResponseType": "RequestResponse", "Type": "None"}},
        "Language": [],
        "DataExportTag": "ai_usage"
    })
    all_qids["ai_usage"] = q
    print(f"  {q}: ai_usage")

    # Online shopping frequency (1-5)
    q = create_question(survey_id, {
        "QuestionText": (
            '<span style="font-size:19px;">'
            'How often do you shop for electronics online?'
            '</span>'
        ),
        "QuestionType": "MC",
        "Selector": "SAHR",
        "SubSelector": "TX",
        "Configuration": {"QuestionDescriptionOption": "UseText", "LabelPosition": "BELOW"},
        "Choices": {
            "1": {"Display": "1 = Never"},
            "2": {"Display": "2 = Rarely"},
            "3": {"Display": "3 = Sometimes"},
            "4": {"Display": "4 = Often"},
            "5": {"Display": "5 = Always"}
        },
        "ChoiceOrder": ["1", "2", "3", "4", "5"],
        "Validation": {"Settings": {"ForceResponse": "RequestResponse",
                                    "ForceResponseType": "RequestResponse", "Type": "None"}},
        "Language": [],
        "DataExportTag": "shop_freq"
    })
    all_qids["shop_freq"] = q
    print(f"  {q}: shop_freq")

    # Open-ended comments
    q = create_question(survey_id, {
        "QuestionText": '<span style="font-size:19px;">Do you have any comments for us? (optional)</span>',
        "QuestionType": "TE",
        "Selector": "SL",
        "Configuration": {"QuestionDescriptionOption": "UseText", "InputWidth": 680, "InputHeight": 80},
        "Validation": {"Settings": {"ForceResponse": "OFF", "Type": "None"}},
        "Language": [],
        "DataExportTag": "comments"
    })
    all_qids["comments"] = q
    print(f"  {q}: comments")

    print(f"\n  Total questions created: {len(all_qids)}")

    # =================================================================
    # Step 3b: Add DisplayLogic to deferred questions via GET-PUT
    # =================================================================
    print("\nStep 3b: Adding deferred DisplayLogic...")

    # alts_display: show if action_decision != "Accept this recommendation" (choice 1)
    action_qid = all_qids["action_decision"]
    qdef_resp = api_call("GET", f"/survey-definitions/{survey_id}/questions/{all_qids['alts_display']}")
    qdef = qdef_resp["result"]
    qdef["DisplayLogic"] = {
        "0": {
            "0": {
                "LogicType": "Question",
                "QuestionID": action_qid,
                "QuestionIsInLoop": "no",
                "ChoiceLocator": f"q://{action_qid}/SelectableChoice/1",
                "Operator": "NotSelected",
                "Type": "Expression",
                "Description": '<span class="ConjDesc">If</span> <span class="QuestionDesc">action_decision</span> <span class="LeftOpDesc">Accept this recommendation</span> <span class="OpDesc">Is Not Selected</span>'
            },
            "Type": "If"
        },
        "Type": "BooleanExpression"
    }
    api_call("PUT", f"/survey-definitions/{survey_id}/questions/{all_qids['alts_display']}", qdef)
    print("  alts_display: DisplayLogic added (show if NOT accepted)")

    # Revised choice questions: Category == X AND revise_yn == Yes (choice 1)
    revise_qid = all_qids["revise_yn"]
    for cat_label, cat_code in [("earbuds", "1"), ("speakers", "2"), ("ssds", "3")]:
        tag = f"revised_{cat_label}"
        qdef_resp = api_call("GET", f"/survey-definitions/{survey_id}/questions/{all_qids[tag]}")
        qdef = qdef_resp["result"]
        qdef["DisplayLogic"] = {
            "0": {
                "0": {
                    "LogicType": "EmbeddedField",
                    "LeftOperand": "Category",
                    "Operator": "EqualTo",
                    "RightOperand": cat_code,
                    "Type": "Expression",
                    "Description": f'<span class="ConjDesc">If</span>  <span class="LeftOpDesc">Category</span> <span class="OpDesc">Is Equal to</span> <span class="RightOpDesc"> {cat_code} </span>'
                },
                "Type": "If"
            },
            "1": {
                "0": {
                    "LogicType": "Question",
                    "QuestionID": revise_qid,
                    "QuestionIsInLoop": "no",
                    "ChoiceLocator": f"q://{revise_qid}/SelectableChoice/1",
                    "Operator": "Selected",
                    "Type": "Expression",
                    "Description": '<span class="ConjDesc">And</span> <span class="QuestionDesc">revise_yn</span> <span class="LeftOpDesc">Yes</span> <span class="OpDesc">Is Selected</span>'
                },
                "Type": "If"
            },
            "Type": "BooleanExpression"
        }
        api_call("PUT", f"/survey-definitions/{survey_id}/questions/{all_qids[tag]}", qdef)
        print(f"  {tag}: DisplayLogic added (Category=={cat_code} AND revise_yn==Yes)")

    # =================================================================
    # Step 4: Assign questions to blocks
    # =================================================================
    print("\nStep 4: Assigning questions to blocks...")

    # Screening block (default)
    api_call("PUT", f"/survey-definitions/{survey_id}/blocks/{screening_block}", {
        "Type": "Default",
        "Description": "screening",
        "BlockElements": [
            {"Type": "Question", "QuestionID": all_qids["browser_meta"]},
            {"Type": "Question", "QuestionID": all_qids["consent"]},
            {"Type": "Page Break"},
            {"Type": "Question", "QuestionID": all_qids["attn_check"]},
            {"Type": "Page Break"},
            {"Type": "Question", "QuestionID": all_qids["attn_passed"]},
        ],
        "Options": BLOCK_OPTS
    })
    print("  screening block assigned")

    # Preference articulation block
    api_call("PUT", f"/survey-definitions/{survey_id}/blocks/{pref_block}", {
        "Type": "Standard",
        "Description": "preference_articulation",
        "BlockElements": [
            {"Type": "Question", "QuestionID": all_qids["timer_pref"]},
            {"Type": "Question", "QuestionID": all_qids["pref_intro"]},
            {"Type": "Question", "QuestionID": all_qids["feature_importance"]},
            {"Type": "Question", "QuestionID": all_qids["pref_text"]},
        ],
        "Options": BLOCK_OPTS
    })
    print("  preference_articulation block assigned")

    # AI recommendation block
    api_call("PUT", f"/survey-definitions/{survey_id}/blocks/{ai_rec_block}", {
        "Type": "Standard",
        "Description": "ai_recommendation",
        "BlockElements": [
            {"Type": "Question", "QuestionID": all_qids["timer_ai_rec"]},
            {"Type": "Question", "QuestionID": all_qids["ai_rec_display"]},
        ],
        "Options": BLOCK_OPTS
    })
    print("  ai_recommendation block assigned")

    # Action decision block
    api_call("PUT", f"/survey-definitions/{survey_id}/blocks/{action_block}", {
        "Type": "Standard",
        "Description": "action_decision",
        "BlockElements": [
            {"Type": "Question", "QuestionID": all_qids["timer_action"]},
            {"Type": "Question", "QuestionID": all_qids["action_decision"]},
        ],
        "Options": BLOCK_OPTS
    })
    print("  action_decision block assigned")

    # Alternatives block
    api_call("PUT", f"/survey-definitions/{survey_id}/blocks/{alts_block}", {
        "Type": "Standard",
        "Description": "alternatives",
        "BlockElements": [
            {"Type": "Question", "QuestionID": all_qids["timer_alts"]},
            {"Type": "Question", "QuestionID": all_qids["alts_display"]},
        ],
        "Options": BLOCK_OPTS
    })
    print("  alternatives block assigned")

    # Final choice block
    api_call("PUT", f"/survey-definitions/{survey_id}/blocks/{final_choice_block}", {
        "Type": "Standard",
        "Description": "final_choice",
        "BlockElements": [
            {"Type": "Question", "QuestionID": all_qids["timer_final_choice"]},
            {"Type": "Question", "QuestionID": all_qids["choice_earbuds"]},
            {"Type": "Question", "QuestionID": all_qids["choice_speakers"]},
            {"Type": "Question", "QuestionID": all_qids["choice_ssds"]},
        ],
        "Options": BLOCK_OPTS
    })
    print("  final_choice block assigned")

    # Post-choice measures block
    api_call("PUT", f"/survey-definitions/{survey_id}/blocks/{post_choice_block}", {
        "Type": "Standard",
        "Description": "post_choice_measures",
        "BlockElements": [
            {"Type": "Question", "QuestionID": all_qids["timer_post_choice"]},
            {"Type": "Question", "QuestionID": all_qids["confidence"]},
            {"Type": "Page Break"},
            {"Type": "Question", "QuestionID": all_qids["ai_satisfaction"]},
            {"Type": "Page Break"},
            {"Type": "Question", "QuestionID": all_qids["enough_options"]},
        ],
        "Options": BLOCK_OPTS
    })
    print("  post_choice_measures block assigned")

    # Debrief + reveal block
    api_call("PUT", f"/survey-definitions/{survey_id}/blocks/{debrief_block}", {
        "Type": "Standard",
        "Description": "debrief_reveal",
        "BlockElements": [
            {"Type": "Question", "QuestionID": all_qids["timer_debrief"]},
            {"Type": "Question", "QuestionID": all_qids["debrief_reveal"]},
            {"Type": "Page Break"},
            {"Type": "Question", "QuestionID": all_qids["revise_yn"]},
            {"Type": "Question", "QuestionID": all_qids["revised_earbuds"]},
            {"Type": "Question", "QuestionID": all_qids["revised_speakers"]},
            {"Type": "Question", "QuestionID": all_qids["revised_ssds"]},
        ],
        "Options": BLOCK_OPTS
    })
    print("  debrief_reveal block assigned")

    # Post-reveal measures block
    api_call("PUT", f"/survey-definitions/{survey_id}/blocks/{post_reveal_block}", {
        "Type": "Standard",
        "Description": "post_reveal_measures",
        "BlockElements": [
            {"Type": "Question", "QuestionID": all_qids["timer_post_reveal"]},
            {"Type": "Question", "QuestionID": all_qids["post_reveal_rating"]},
            {"Type": "Page Break"},
            {"Type": "Question", "QuestionID": all_qids["felt_misled"]},
            {"Type": "Page Break"},
            {"Type": "Question", "QuestionID": all_qids["ai_trust"]},
        ],
        "Options": BLOCK_OPTS
    })
    print("  post_reveal_measures block assigned")

    # Demographics block
    api_call("PUT", f"/survey-definitions/{survey_id}/blocks/{demo_block}", {
        "Type": "Standard",
        "Description": "demographics",
        "BlockElements": [
            {"Type": "Question", "QuestionID": all_qids["age"]},
            {"Type": "Question", "QuestionID": all_qids["gender"]},
            {"Type": "Page Break"},
            {"Type": "Question", "QuestionID": all_qids["ai_usage"]},
            {"Type": "Question", "QuestionID": all_qids["shop_freq"]},
            {"Type": "Page Break"},
            {"Type": "Question", "QuestionID": all_qids["comments"]},
        ],
        "Options": BLOCK_OPTS
    })
    print("  demographics block assigned")

    print("  All blocks assigned")

    # =================================================================
    # Step 5: Set survey flow
    # =================================================================
    print("\nStep 5: Setting survey flow...")

    # Build the 9 EmbeddedData nodes for the BlockRandomizer
    ed_cells = build_ed_cells()
    randomizer_flow = []
    fl_counter = 20
    for cell_vars in ed_cells:
        ed_list = []
        for var in cell_vars:
            ed_list.append({
                "Description": var["Field"],
                "Type": "Custom",
                "Field": var["Field"],
                "VariableType": "String",
                "DataVisibility": [],
                "AnalyzeText": False,
                "Value": var["Value"]
            })
        randomizer_flow.append({
            "Type": "EmbeddedData",
            "FlowID": f"FL_{fl_counter}",
            "EmbeddedData": ed_list
        })
        fl_counter += 1

    # Build attention check branch (if NOT Horse -> EndSurvey)
    attn_branch = {
        "Type": "Branch",
        "FlowID": "FL_40",
        "Description": "Attention Check Branch",
        "BranchLogic": {
            "0": {
                "0": {
                    "LogicType": "Question",
                    "QuestionID": all_qids["attn_check"],
                    "QuestionIsInLoop": "no",
                    "ChoiceLocator": f'q://{all_qids["attn_check"]}/SelectableChoice/4',
                    "Operator": "NotSelected",
                    "Type": "Expression",
                    "Description": '<span class="ConjDesc">If</span> <span class="QuestionDesc">attn_check</span> <span class="LeftOpDesc">Horse</span> <span class="OpDesc">Is Not Selected</span>'
                },
                "Type": "If"
            },
            "Type": "BooleanExpression"
        },
        "Flow": [
            {
                "Type": "EndSurvey",
                "FlowID": "FL_41",
                "EndingType": "Advanced",
                "Options": {
                    "Advanced": "true",
                    "SurveyTermination": "DisplayMessage",
                    "EOSMessage": "MS_0f26k4kl5jOeYkm"
                }
            }
        ]
    }

    # Build consent branch (if "I do not agree" -> EndSurvey)
    consent_branch = {
        "Type": "Branch",
        "FlowID": "FL_42",
        "Description": "Consent Branch",
        "BranchLogic": {
            "0": {
                "0": {
                    "LogicType": "Question",
                    "QuestionID": all_qids["consent"],
                    "QuestionIsInLoop": "no",
                    "ChoiceLocator": f'q://{all_qids["consent"]}/SelectableChoice/2',
                    "Operator": "Selected",
                    "Type": "Expression",
                    "Description": '<span class="ConjDesc">If</span> <span class="QuestionDesc">consent</span> <span class="LeftOpDesc">I do not agree</span> <span class="OpDesc">Is Selected</span>'
                },
                "Type": "If"
            },
            "Type": "BooleanExpression"
        },
        "Flow": [
            {
                "Type": "EndSurvey",
                "FlowID": "FL_43"
            }
        ]
    }

    flow = {
        "Type": "Root",
        "FlowID": "FL_1",
        "Flow": [
            # 1. Mobile screening
            {
                "Type": "Branch",
                "FlowID": "FL_10",
                "Description": "Mobile Screening",
                "BranchLogic": {
                    "0": {
                        "0": {
                            "LogicType": "DeviceType",
                            "Operator": "Is",
                            "LeftOperand": "mobile",
                            "Type": "Expression",
                            "Description": '<span class="ConjDesc">If</span><span class="schema_desc">Device Type</span><span class="select_val_desc Operator_desc">Is</span><span class="select_val_desc LeftOperand_desc">Mobile</span>'
                        },
                        "Type": "If"
                    },
                    "Type": "BooleanExpression"
                },
                "Flow": [
                    {"Type": "EndSurvey", "FlowID": "FL_11"}
                ]
            },
            # 2. Screening block
            {"Type": "Standard", "ID": screening_block, "FlowID": "FL_2", "Autofill": []},
            # 3. Consent branch
            consent_branch,
            # 4. Attention check branch
            attn_branch,
            # 5. BlockRandomizer (9 EmbeddedData cells)
            {
                "Type": "BlockRandomizer",
                "FlowID": "FL_3",
                "SubSet": 1,
                "EvenPresentation": True,
                "Flow": randomizer_flow
            },
            # 6. Preference articulation
            {"Type": "Standard", "ID": pref_block, "FlowID": "FL_4", "Autofill": []},
            # 7. AI recommendation (single product)
            {"Type": "Standard", "ID": ai_rec_block, "FlowID": "FL_5", "Autofill": []},
            # 8. Action decision ("What would you like to do?")
            {"Type": "Standard", "ID": action_block, "FlowID": "FL_6", "Autofill": []},
            # 9. Alternatives (DisplayLogic on alts_display: if not accepted)
            {"Type": "Standard", "ID": alts_block, "FlowID": "FL_7", "Autofill": []},
            # 10. Final choice
            {"Type": "Standard", "ID": final_choice_block, "FlowID": "FL_8", "Autofill": []},
            # 11. Post-choice measures
            {"Type": "Standard", "ID": post_choice_block, "FlowID": "FL_9", "Autofill": []},
            # 12. Debrief + reveal
            {"Type": "Standard", "ID": debrief_block, "FlowID": "FL_12", "Autofill": []},
            # 13. Post-reveal measures
            {"Type": "Standard", "ID": post_reveal_block, "FlowID": "FL_13", "Autofill": []},
            # 14. Demographics
            {"Type": "Standard", "ID": demo_block, "FlowID": "FL_14", "Autofill": []},
            # 15. End survey
            {"Type": "EndSurvey", "FlowID": "FL_99"}
        ],
        "Properties": {"Count": 40}
    }

    api_call("PUT", f"/survey-definitions/{survey_id}/flow", flow)
    print("  Flow set: mobile -> screening -> consent -> attn -> "
          "BlockRandomizer(9 cells) -> pref -> ai_rec -> action -> "
          "alts -> choice -> post_choice -> debrief -> post_reveal -> demo -> end")

    # =================================================================
    # Step 6: Set survey options (GET-modify-PUT)
    # =================================================================
    print("\nStep 6: Setting survey options...")

    existing_opts = api_call("GET", f"/survey-definitions/{survey_id}/options")
    opts = existing_opts.get("result", {})
    opts["BackButton"] = "false"
    opts["SaveAndContinue"] = "false"
    opts["SurveyProtection"] = "PublicSurvey"
    opts["BallotBoxStuffingPrevention"] = "true"
    opts["NoIndex"] = "Yes"
    opts["SecureResponseFiles"] = "true"
    opts["SurveyExpiration"] = "None"
    opts["SurveyTermination"] = "Redirect"
    opts["ProgressBarDisplay"] = "None"
    opts["CollectGeoLocation"] = "false"
    opts["ShowExportTags"] = "false"
    opts["AnonymizeResponse"] = "Yes"
    opts["SurveyTitle"] = "Consumer Decision Making Study"
    opts["SurveyMetaDescription"] = "A brief study about product recommendations"
    opts["EOSRedirectURL"] = "https://app.prolific.com/submissions/complete?cc=PLACEHOLDER"
    opts["EmailThankYou"] = "false"
    opts["ThankYouEmailMessage"] = None
    opts["ThankYouEmailMessageLibrary"] = None
    opts["PartialData"] = "+1 week"
    opts["PageTransition"] = "slide"
    opts["NextButton"] = " -> "
    opts["PreviousButton"] = " <- "
    opts["SkinLibrary"] = "okstatebusiness"
    opts["SkinType"] = "templated"
    opts["Skin"] = {
        "brandingId": None,
        "templateId": "*base",
        "overrides": {
            "colors": {
                "secondary": "#1400c0",
                "primary": "#1400c0"
            },
            "contrast": 1,
            "layout": {"spacing": 0},
            "questionText": {"size": "21px"}
        }
    }
    opts["CustomStyles"] = {
        "customCSS": (
            ".Skin #Buttons {text-align:center;}\n"
            ".Skin .SkinInner {min-width: 850px!important;}\n"
            ".Skin .SkinInner {\npadding-top: 40px;\n}\n"
        )
    }

    api_call("PUT", f"/survey-definitions/{survey_id}/options", opts)
    print("  Options set (slide transitions, blue theme, centered buttons, Prolific redirect)")

    # =================================================================
    # Step 7: Activate the survey
    # =================================================================
    print("\nStep 7: Activating survey...")
    api_call("PUT", f"/surveys/{survey_id}", {"isActive": True})
    print("  Survey activated!")

    # =================================================================
    # Done!
    # =================================================================
    edit_url = f"https://okstatebusiness.az1.qualtrics.com/survey-builder/{survey_id}/edit"
    preview_url = f"https://okstatebusiness.az1.qualtrics.com/jfe/preview/{survey_id}"
    live_url = f"https://okstatebusiness.az1.qualtrics.com/jfe/form/{survey_id}"

    print("\n" + "=" * 70)
    print("SURVEY CREATED AND ACTIVATED SUCCESSFULLY!")
    print("=" * 70)
    print(f"Survey ID:   {survey_id}")
    print(f"Edit:        {edit_url}")
    print(f"Preview:     {preview_url}")
    print(f"Live:        {live_url}")
    print()
    print("Design: 3 (Condition) x 3 (Category) = 9 cells, between-subjects")
    print()
    print("Conditions:")
    print("  1 = Curated      (shows alternatives, re-recommends branded)")
    print("  2 = Transparent  (shows alternatives, honestly points out optimal)")
    print("  3 = SingleRec    (no alternatives available)")
    print()
    print("Categories:")
    print("  1 = earbuds   (Sony WF-1000XM5 recommended, Auralis Air4 Pro optimal)")
    print("  2 = speakers  (JBL Flip 6 recommended, Wavecrest StormBox Pro optimal)")
    print("  3 = ssds      (Samsung T7 Shield recommended, Vaultdrive PD60 optimal)")
    print()
    print("Structure:")
    print("  screening        -> consent, attention check (Horse), passed msg")
    print("  BlockRandomizer (SubSet=1, EvenPresentation=true):")
    for cond_label in ["Curated", "Transparent", "SingleRec"]:
        for cat_label in ["earbuds", "speakers", "ssds"]:
            print(f"    Cell: {cond_label} x {cat_label}")
    print("  preference_art   -> intro, feature ranking (6 items), pref text")
    print("  ai_recommendation -> single product card + confabulated chat bubble")
    print("  action_decision   -> Accept / Ask alternatives / Follow-up (PRIMARY DV)")
    print("  alternatives      -> condition-specific AI text + product table (if not accepted)")
    print("  final_choice      -> choose from products (category-specific, DisplayLogic)")
    print("  post_choice       -> confidence, AI satisfaction, enough options")
    print("  debrief_reveal    -> reveal all 5 products, identify optimal, revision choice")
    print("  post_reveal       -> post-reveal rating, felt misled, AI trust")
    print("  demographics      -> age, gender, AI usage, shop frequency, comments")
    print()
    print("DataExportTags:")
    for tag, qid in all_qids.items():
        print(f"  {tag:25s} -> {qid}")
    print()
    print("IMPORTANT: Update EOSRedirectURL with actual Prolific completion code before launch!")
    print("IMPORTANT: Update consent form with approved IRB text before launch!")


if __name__ == "__main__":
    main()
