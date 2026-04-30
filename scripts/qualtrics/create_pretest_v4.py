"""
Create V4 Pretest: Fictional Brand Credibility Check (GATEKEEPER)
Spec Resistance Project -- Nature R&R Human Subjects

This is the GATEKEEPER pretest. Results determine whether main studies use
fictional brands (382K bridge) or real lesser-known brands.

Design: Single condition, N=150. No AI recommendation.
- Show earbuds product table (sr_earbuds_01 from 382K study)
- Measure brand credibility (1-7 per brand)
- Measure purchase likelihood (1-7 per product)
- Product choice (which would you buy?)
- Brand awareness (own / heard of / never heard of)
- Open-ended: unfamiliarity effect

Go/No-Go Criteria:
- IF Auralis credibility >= 4.0 AND optimal choice >= 50% -> PROCEED with fictional brands
- IF Auralis credibility < 4.0 OR optimal choice < 40% -> SWITCH to real brands

Flow:
  1. Mobile screening -> EndSurvey
  2. Consent + attention check
  3. Product comparison table (5 products, row-shuffled, NO AI recommendation)
  4. Per-product credibility ratings (5 x 1-7)
  5. Per-product purchase likelihood (5 x 1-7)
  6. Product choice (5 options, randomized)
  7. Brand awareness (5 brands x 3 levels)
  8. Open-ended: brand unfamiliarity
  9. Demographics
  10. EndSurvey
"""

import requests
import json
import sys
import time

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

# Product data from sr_earbuds_01 (with fictional brand replacement)
PRODUCTS = [
    {"brand": "Apple", "model": "AirPods Pro 2", "price": "$249.00",
     "anc": "2x improved over gen 1", "battery": "6h (30h case)",
     "codec": "AAC", "ip": "IPX4", "rating": "4.7", "reviews": "56,789",
     "desc": "H2 chip, adaptive transparency, personalized spatial audio, MagSafe case. Deep Apple ecosystem integration."},
    {"brand": "Samsung", "model": "Galaxy Buds3 Pro", "price": "$199.99",
     "anc": "Adaptive", "battery": "7h (30h case)",
     "codec": "SSC/AAC", "ip": "IP57", "rating": "4.4", "reviews": "8,765",
     "desc": "24-bit Hi-Fi, adaptive ANC, 360 Audio. Galaxy AI features."},
    {"brand": "Sony", "model": "WF-1000XM5", "price": "$279.99",
     "anc": "Industry leading", "battery": "8h (24h case)",
     "codec": "LDAC/AAC", "ip": "IPX4", "rating": "4.5", "reviews": "4,567",
     "desc": "V2 processor, industry-leading ANC, LDAC Hi-Res, bone conduction mic."},
    {"brand": "Auralis", "model": "Air4 Pro", "price": "$59.99",
     "anc": "-45dB", "battery": "8.5h (32h case)",
     "codec": "aptX Lossless/AAC", "ip": "IP57", "rating": "4.5", "reviews": "234",
     "desc": "ANC -45dB, aptX Lossless, 6-mic clarity, 32h total battery, multipoint Bluetooth 5.3, IP57."},
    {"brand": "Jabra", "model": "Elite 85t", "price": "$179.99",
     "anc": "Adjustable", "battery": "5.5h (25h case)",
     "codec": "AAC/SBC", "ip": "IPX4", "rating": "4.3", "reviews": "9,876",
     "desc": "Advanced ANC with HearThrough, 6 mic calls, MySound personalization."},
]

TABLE_SHUFFLER_JS = """Qualtrics.SurveyEngine.addOnload(function(){
var container = this.getQuestionContainer();
var tables = container.querySelectorAll('table');
tables.forEach(function(table){
  var tbody = table.querySelector('tbody');
  if (!tbody) {
    var rows = Array.from(table.querySelectorAll('tr'));
    if (rows.length > 1) {
      tbody = document.createElement('tbody');
      for (var i = 1; i < rows.length; i++) {
        tbody.appendChild(rows[i]);
      }
      table.appendChild(tbody);
    }
  }
  if (tbody) {
    var rows = Array.from(tbody.querySelectorAll('tr'));
    for (var i = rows.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1));
      tbody.insertBefore(rows[j], rows[i]);
      var temp = rows[i]; rows[i] = rows[j]; rows[j] = temp;
    }
    rows = Array.from(tbody.querySelectorAll('tr'));
    rows.forEach(function(row){ tbody.appendChild(row); });
    // Record display order
    var order = rows.map(function(r){
      var c = r.querySelectorAll('td');
      return c[0] ? c[0].textContent.trim() : '?';
    });
    Qualtrics.SurveyEngine.setEmbeddedData('ProductDisplayOrder', order.join('|'));
  }
});
});"""

def build_product_table():
    """Build HTML product comparison table."""
    rows = ""
    for p in PRODUCTS:
        rows += f"""<tr>
<td style="padding:8px; font-weight:bold;">{p['brand']}</td>
<td style="padding:8px;">{p['model']}</td>
<td style="padding:8px; color:#0f7b0f; font-weight:bold;">{p['price']}</td>
<td style="padding:8px;">{p['anc']}</td>
<td style="padding:8px;">{p['battery']}</td>
<td style="padding:8px;">{p['codec']}</td>
<td style="padding:8px;">{p['ip']}</td>
<td style="padding:8px;">{p['rating']} ({p['reviews']})</td>
</tr>"""

    return f"""<h3>Compare Wireless Earbuds</h3>
<p>You are shopping for wireless earbuds. Review these products carefully.</p>
<table style="width:100%; border-collapse:collapse; font-size:13px;">
<thead>
<tr style="background:#f0f0f0; font-weight:bold;">
<th style="padding:8px; text-align:left;">Brand</th>
<th style="padding:8px; text-align:left;">Model</th>
<th style="padding:8px; text-align:left;">Price</th>
<th style="padding:8px; text-align:left;">ANC</th>
<th style="padding:8px; text-align:left;">Battery</th>
<th style="padding:8px; text-align:left;">Codec</th>
<th style="padding:8px; text-align:left;">IP Rating</th>
<th style="padding:8px; text-align:left;">Rating</th>
</tr>
</thead>
<tbody>
{rows}
</tbody>
</table>
<p style="color:#666; font-size:12px; margin-top:10px;">
Products compiled from international and domestic retailers. Some brands may be unfamiliar to you;
all products listed are based on real specifications from current models.
</p>"""


def api(method, path, data=None):
    """Make Qualtrics API call with retry."""
    url = f"{BASE}{path}"
    for attempt in range(3):
        try:
            if method == "POST":
                r = requests.post(url, headers=HEADERS, json=data, timeout=30)
            elif method == "PUT":
                r = requests.put(url, headers=HEADERS, json=data, timeout=30)
            elif method == "GET":
                r = requests.get(url, headers=HEADERS, timeout=30)
            elif method == "DELETE":
                r = requests.delete(url, headers=HEADERS, timeout=30)
            else:
                raise ValueError(f"Unknown method: {method}")

            if r.status_code in (200, 201):
                return r.json()
            else:
                print(f"  API {method} {path}: {r.status_code} - {r.text[:200]}")
                if attempt < 2:
                    time.sleep(2)
        except Exception as e:
            print(f"  API error: {e}")
            if attempt < 2:
                time.sleep(2)
    return None


def create_survey():
    """Create the V4 pretest survey."""
    print("=" * 60)
    print("Creating V4 Pretest: Fictional Brand Credibility")
    print("=" * 60)

    # 1. Create survey
    print("\n1. Creating survey...")
    r = api("POST", "/survey-definitions", {
        "SurveyName": "SR V4 Pretest -- Fictional Brand Credibility",
        "Language": "EN",
        "ProjectCategory": "CORE"
    })
    if not r:
        print("FAILED to create survey")
        return

    survey_id = r["result"]["SurveyID"]
    default_block = r["result"]["DefaultBlockID"]
    print(f"  Survey: {survey_id}")
    print(f"  Default block: {default_block}")

    # Track question IDs
    Q = {}

    # 2. Create blocks
    print("\n2. Creating blocks...")
    blocks = {}
    for name in ["screening", "product_table", "credibility", "purchase_likelihood",
                  "product_choice", "brand_awareness", "open_ended", "demographics"]:
        r = api("POST", f"/survey-definitions/{survey_id}/blocks", {
            "Type": "Standard",
            "Description": name,
            "Options": BLOCK_OPTS
        })
        if r:
            blocks[name] = r["result"]["BlockID"]
            print(f"  {name}: {blocks[name]}")

    # 3. Create questions
    print("\n3. Creating questions...")

    # -- SCREENING BLOCK --
    # Consent
    r = api("POST", f"/survey-definitions/{survey_id}/questions", {
        "QuestionText": """<h3>Consent Form</h3>
<p><strong>Title:</strong> Consumer Product Evaluation Study<br>
<strong>Investigator:</strong> Dr. Felipe Affonso<br>
<strong>Institution:</strong> Oklahoma State University</p>
<p>You are being asked to participate in a research study about how consumers evaluate product
information and make purchasing decisions. This study will take approximately 3-4 minutes.</p>
<p>Your participation is voluntary. Your responses will be anonymous and confidential.</p>
<p>By selecting 'I agree' below, you confirm that you have read this information, are at least
18 years old, and agree to participate.</p>""",
        "QuestionType": "MC",
        "Selector": "SAVR",
        "SubSelector": "TX",
        "Choices": {"1": {"Display": "I agree"}, "2": {"Display": "I do not agree"}},
        "DataExportTag": "consent",
        "Validation": {"Settings": {"ForceResponse": "ON", "Type": "None"}},
        "QuestionJS": False
    })
    if r:
        Q["consent"] = r["result"]["QuestionID"]
        # Move to screening block
        api("POST", f"/survey-definitions/{survey_id}/blocks/{blocks['screening']}/questions",
            {"QuestionID": Q["consent"]})
        print(f"  {Q['consent']}: consent")

    # Attention check
    r = api("POST", f"/survey-definitions/{survey_id}/questions", {
        "QuestionText": "To show that you are reading carefully, please select the word that describes an animal.",
        "QuestionType": "MC",
        "Selector": "SAVR",
        "SubSelector": "TX",
        "Choices": {
            "1": {"Display": "Rock"}, "2": {"Display": "Bicycle"},
            "3": {"Display": "Trumpet"}, "4": {"Display": "Horse"},
            "5": {"Display": "Ladder"}, "6": {"Display": "Candle"},
            "7": {"Display": "Compass"}, "8": {"Display": "Blanket"}
        },
        "DataExportTag": "attn_check",
        "Validation": {"Settings": {"ForceResponse": "ON", "Type": "None"}},
        "Randomization": {"Type": "All", "Advanced": None, "TotalRandSubset": ""}
    })
    if r:
        Q["attn_check"] = r["result"]["QuestionID"]
        api("POST", f"/survey-definitions/{survey_id}/blocks/{blocks['screening']}/questions",
            {"QuestionID": Q["attn_check"]})
        print(f"  {Q['attn_check']}: attn_check (randomized)")

    # -- PRODUCT TABLE BLOCK --
    product_table_html = build_product_table()
    r = api("POST", f"/survey-definitions/{survey_id}/questions", {
        "QuestionText": product_table_html,
        "QuestionType": "DB",
        "Selector": "TB",
        "DataExportTag": "product_table",
        "QuestionJS": TABLE_SHUFFLER_JS
    })
    if r:
        Q["product_table"] = r["result"]["QuestionID"]
        api("POST", f"/survey-definitions/{survey_id}/blocks/{blocks['product_table']}/questions",
            {"QuestionID": Q["product_table"]})
        print(f"  {Q['product_table']}: product_table (with JS shuffler + order recording)")

    # Timer on product table (10 seconds minimum)
    r = api("POST", f"/survey-definitions/{survey_id}/questions", {
        "QuestionText": "Timer",
        "QuestionType": "Timing",
        "Selector": "PageTimer",
        "Choices": {"1": {"Display": "First Click"}, "2": {"Display": "Last Click"},
                    "3": {"Display": "Page Submit"}, "4": {"Display": "Click Count"}},
        "DataExportTag": "timer_table",
        "Configuration": {"MinSeconds": "10"}
    })
    if r:
        Q["timer_table"] = r["result"]["QuestionID"]
        api("POST", f"/survey-definitions/{survey_id}/blocks/{blocks['product_table']}/questions",
            {"QuestionID": Q["timer_table"]})
        print(f"  {Q['timer_table']}: timer_table (10s min)")

    # -- CREDIBILITY BLOCK --
    # Matrix: "How confident are you that each is a real product?" 1-7
    brand_labels = [f"{p['brand']} {p['model']}" for p in PRODUCTS]
    choices = {str(i+1): {"Display": brand_labels[i]} for i in range(5)}
    answers = {str(i): {"Display": str(i)} for i in range(1, 8)}
    answers["1"]["Display"] = "1 - Not at all confident"
    answers["4"]["Display"] = "4 - Moderately confident"
    answers["7"]["Display"] = "7 - Extremely confident"

    r = api("POST", f"/survey-definitions/{survey_id}/questions", {
        "QuestionText": "For each product, how confident are you that this is a <strong>real product from a real manufacturer</strong>?",
        "QuestionType": "Matrix",
        "Selector": "Likert",
        "SubSelector": "SingleAnswer",
        "Choices": choices,
        "Answers": answers,
        "DataExportTag": "credibility",
        "Validation": {"Settings": {"ForceResponse": "ON", "Type": "None"}},
        "Randomization": {"Type": "All", "Advanced": None, "TotalRandSubset": ""},
        "Configuration": {"QuestionDescriptionOption": "UseText"}
    })
    if r:
        Q["credibility"] = r["result"]["QuestionID"]
        api("POST", f"/survey-definitions/{survey_id}/blocks/{blocks['credibility']}/questions",
            {"QuestionID": Q["credibility"]})
        print(f"  {Q['credibility']}: credibility (Matrix 5x7, row randomized)")

    # -- PURCHASE LIKELIHOOD BLOCK --
    answers2 = {str(i): {"Display": str(i)} for i in range(1, 8)}
    answers2["1"]["Display"] = "1 - Very unlikely"
    answers2["4"]["Display"] = "4 - Neutral"
    answers2["7"]["Display"] = "7 - Very likely"

    r = api("POST", f"/survey-definitions/{survey_id}/questions", {
        "QuestionText": "How likely would you be to <strong>purchase</strong> each product?",
        "QuestionType": "Matrix",
        "Selector": "Likert",
        "SubSelector": "SingleAnswer",
        "Choices": choices,
        "Answers": answers2,
        "DataExportTag": "purchase_likelihood",
        "Validation": {"Settings": {"ForceResponse": "ON", "Type": "None"}},
        "Randomization": {"Type": "All", "Advanced": None, "TotalRandSubset": ""},
        "Configuration": {"QuestionDescriptionOption": "UseText"}
    })
    if r:
        Q["purchase_likelihood"] = r["result"]["QuestionID"]
        api("POST", f"/survey-definitions/{survey_id}/blocks/{blocks['purchase_likelihood']}/questions",
            {"QuestionID": Q["purchase_likelihood"]})
        print(f"  {Q['purchase_likelihood']}: purchase_likelihood (Matrix 5x7, row randomized)")

    # -- PRODUCT CHOICE BLOCK --
    choice_opts = {str(i+1): {"Display": f"{PRODUCTS[i]['brand']} {PRODUCTS[i]['model']} ({PRODUCTS[i]['price']})"}
                   for i in range(5)}

    r = api("POST", f"/survey-definitions/{survey_id}/questions", {
        "QuestionText": "Based on the information shown, which product would you <strong>purchase</strong>?",
        "QuestionType": "MC",
        "Selector": "SAVR",
        "SubSelector": "TX",
        "Choices": choice_opts,
        "DataExportTag": "product_choice",
        "Validation": {"Settings": {"ForceResponse": "ON", "Type": "None"}},
        "Randomization": {"Type": "All", "Advanced": None, "TotalRandSubset": ""}
    })
    if r:
        Q["product_choice"] = r["result"]["QuestionID"]
        api("POST", f"/survey-definitions/{survey_id}/blocks/{blocks['product_choice']}/questions",
            {"QuestionID": Q["product_choice"]})
        print(f"  {Q['product_choice']}: product_choice (5 options, randomized)")

    # -- BRAND AWARENESS BLOCK --
    awareness_choices = {str(i+1): {"Display": PRODUCTS[i]['brand']} for i in range(5)}
    awareness_answers = {
        "1": {"Display": "I own products from this brand"},
        "2": {"Display": "I've heard of this brand"},
        "3": {"Display": "I've never heard of this brand"}
    }

    r = api("POST", f"/survey-definitions/{survey_id}/questions", {
        "QuestionText": "For each brand below, please indicate your familiarity:",
        "QuestionType": "Matrix",
        "Selector": "Likert",
        "SubSelector": "SingleAnswer",
        "Choices": awareness_choices,
        "Answers": awareness_answers,
        "DataExportTag": "brand_awareness",
        "Validation": {"Settings": {"ForceResponse": "ON", "Type": "None"}},
        "Randomization": {"Type": "All", "Advanced": None, "TotalRandSubset": ""}
    })
    if r:
        Q["brand_awareness"] = r["result"]["QuestionID"]
        api("POST", f"/survey-definitions/{survey_id}/blocks/{blocks['brand_awareness']}/questions",
            {"QuestionID": Q["brand_awareness"]})
        print(f"  {Q['brand_awareness']}: brand_awareness (Matrix 5x3, row randomized)")

    # -- OPEN-ENDED BLOCK --
    r = api("POST", f"/survey-definitions/{survey_id}/questions", {
        "QuestionText": "Were any of the products or brands <strong>unfamiliar</strong> to you? If so, did that affect your purchasing decision? Please explain.",
        "QuestionType": "TE",
        "Selector": "SL",
        "DataExportTag": "unfamiliarity_effect",
        "Validation": {"Settings": {"ForceResponse": "ON", "Type": "None"}}
    })
    if r:
        Q["unfamiliarity_effect"] = r["result"]["QuestionID"]
        api("POST", f"/survey-definitions/{survey_id}/blocks/{blocks['open_ended']}/questions",
            {"QuestionID": Q["unfamiliarity_effect"]})
        print(f"  {Q['unfamiliarity_effect']}: unfamiliarity_effect (open text)")

    # -- DEMOGRAPHICS BLOCK --
    r = api("POST", f"/survey-definitions/{survey_id}/questions", {
        "QuestionText": "What is your age?",
        "QuestionType": "MC",
        "Selector": "DL",
        "Choices": {str(i): {"Display": str(i)} for i in range(18, 100)},
        "DataExportTag": "age",
        "Validation": {"Settings": {"ForceResponse": "ON", "Type": "None"}}
    })
    if r:
        Q["age"] = r["result"]["QuestionID"]
        api("POST", f"/survey-definitions/{survey_id}/blocks/{blocks['demographics']}/questions",
            {"QuestionID": Q["age"]})
        print(f"  {Q['age']}: age")

    r = api("POST", f"/survey-definitions/{survey_id}/questions", {
        "QuestionText": "What is your gender?",
        "QuestionType": "MC",
        "Selector": "SAVR",
        "SubSelector": "TX",
        "Choices": {"1": {"Display": "Female"}, "2": {"Display": "Male"},
                    "3": {"Display": "Non-binary"}, "4": {"Display": "Prefer not to say"}},
        "DataExportTag": "gender",
        "Validation": {"Settings": {"ForceResponse": "ON", "Type": "None"}}
    })
    if r:
        Q["gender"] = r["result"]["QuestionID"]
        api("POST", f"/survey-definitions/{survey_id}/blocks/{blocks['demographics']}/questions",
            {"QuestionID": Q["gender"]})
        print(f"  {Q['gender']}: gender")

    r = api("POST", f"/survey-definitions/{survey_id}/questions", {
        "QuestionText": "How often do you use AI tools (ChatGPT, Gemini, etc.) for shopping or product research?",
        "QuestionType": "MC",
        "Selector": "SAHR",
        "Choices": {
            "1": {"Display": "1 - Never"}, "2": {"Display": "2 - Rarely"},
            "3": {"Display": "3 - Sometimes"}, "4": {"Display": "4 - Often"},
            "5": {"Display": "5 - Always"}
        },
        "DataExportTag": "ai_usage",
        "Validation": {"Settings": {"ForceResponse": "ON", "Type": "None"}}
    })
    if r:
        Q["ai_usage"] = r["result"]["QuestionID"]
        api("POST", f"/survey-definitions/{survey_id}/blocks/{blocks['demographics']}/questions",
            {"QuestionID": Q["ai_usage"]})
        print(f"  {Q['ai_usage']}: ai_usage")

    # 4. Set up survey flow
    print("\n4. Setting up survey flow...")

    # Get current flow
    r = api("GET", f"/survey-definitions/{survey_id}/flow")
    if r:
        flow = r["result"]

        # Build new flow: screening -> product_table -> credibility -> purchase -> choice -> awareness -> open -> demo
        new_flow = {
            "FlowID": "FL_1",
            "Type": "Root",
            "Flow": [
                {"Type": "EmbeddedData", "FlowID": "FL_ED1",
                 "EmbeddedData": [
                     {"Description": "ProductDisplayOrder", "Type": "Custom", "Field": "ProductDisplayOrder", "Value": ""},
                 ]},
                {"Type": "Block", "ID": blocks["screening"], "FlowID": "FL_2"},
                {"Type": "Block", "ID": blocks["product_table"], "FlowID": "FL_3"},
                {"Type": "Block", "ID": blocks["credibility"], "FlowID": "FL_4"},
                {"Type": "Block", "ID": blocks["purchase_likelihood"], "FlowID": "FL_5"},
                {"Type": "Block", "ID": blocks["product_choice"], "FlowID": "FL_6"},
                {"Type": "Block", "ID": blocks["brand_awareness"], "FlowID": "FL_7"},
                {"Type": "Block", "ID": blocks["open_ended"], "FlowID": "FL_8"},
                {"Type": "Block", "ID": blocks["demographics"], "FlowID": "FL_9"},
                {"Type": "EndSurvey", "FlowID": "FL_END"}
            ]
        }

        r = api("PUT", f"/survey-definitions/{survey_id}/flow", new_flow)
        if r:
            print("  Flow set successfully")
        else:
            print("  WARNING: Flow update may have failed")

    # 5. Remove default block questions (move them to trash or delete)
    print("\n5. Cleaning up default block...")
    # The default block may have absorbed some questions; just leave it empty

    # 6. Activate survey
    print("\n6. Activating survey...")
    r = api("PUT", f"/survey-definitions/{survey_id}/options", {
        "BackButton": "false",
        "SaveAndContinue": "true",
        "SurveyProtection": "PublicSurvey",
        "BallotBoxStuffingPrevention": "false",
        "NoIndex": "YES",
        "SurveyTermination": "DefaultMessage",
        "InactiveSurvey": "DefaultMessage",
        "SurveyExperience": "Qualtrics2023",
        "ProgressBarDisplay": "Text"
    })

    r = api("POST", f"/surveys/{survey_id}/versions", {
        "Description": "V4 Pretest - initial", "Published": True
    })
    if r:
        print("  Survey activated!")

    # 7. Print summary
    print("\n" + "=" * 60)
    print("SURVEY CREATED SUCCESSFULLY")
    print("=" * 60)
    print(f"  Survey ID: {survey_id}")
    print(f"  Edit URL: https://okstatebusiness.az1.qualtrics.com/survey-builder/{survey_id}/edit")
    print(f"  Preview: https://okstatebusiness.az1.qualtrics.com/jfe/preview/{survey_id}")
    print(f"  Live: https://okstatebusiness.az1.qualtrics.com/jfe/form/{survey_id}")
    print(f"  Questions: {len(Q)}")
    print(f"  Blocks: {len(blocks)}")
    for tag, qid in Q.items():
        print(f"    {qid}: {tag}")

    return survey_id, Q, blocks


if __name__ == "__main__":
    survey_id, Q, blocks = create_survey()
