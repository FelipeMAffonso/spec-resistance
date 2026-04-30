"""
Create Study A (V4): AI Confabulation Compliance Test
Spec Resistance Project -- Nature R&R Human Subjects

Design: 3 between-subjects conditions x 2 AI rec positions = 6 cells
  Condition 1: NoAI (control) -- product table only
  Condition 2: BiasedAI_pos1 -- biased AI rec with Sony at position #1
  Condition 3: BiasedAI_pos3 -- biased AI rec with Sony at position #3
  Condition 4: DebiasedAI_pos1 -- debiased AI rec with Auralis at position #1
  Condition 5: DebiasedAI_pos3 -- debiased AI rec with Auralis at position #3

NOTE: For the primary analysis, Conditions 2+3 are pooled as "BiasedAI" and
Conditions 4+5 are pooled as "DebiasedAI". The position factor is exploratory.

Flow:
  1. EmbeddedData initialization (Condition, ConditionD, AIRecVersion, ProductDisplayOrder, etc.)
  2. Mobile screening -> EndSurvey
  3. Consent (with lottery disclosure) -> EndSurvey if disagree
  4. Attention check (Horse) -> EndSurvey if wrong
  5. BlockRandomizer(SubSet=1, EvenPresentation=true): 5 EmbeddedData cells
  6. Preference articulation: feature importance (Matrix/Likert 6x7), optional text
  7. Stimulus: product table (JS shuffler + order recording) + AI rec (conditional)
  8. Product choice (5 options, randomized)
  9. Process measures: open-ended reason, confidence, free recall of AI reasoning
  10. Brand awareness check (5 brands x 3 levels, AFTER choice)
  11. Detection: two-stage Salvi protocol
  12. Neutral debrief + revision opportunity
  13. Suspicion probe + demographics
  14. EndSurvey -> Prolific redirect
"""

import requests
import json
import sys
import time
import os

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

# ============================================================
# PRODUCT DATA (sr_earbuds_01 from 382K study)
# ============================================================

PRODUCTS = [
    {"id": "1", "brand": "Apple", "model": "AirPods Pro 2", "price": "$249.00",
     "anc": "2x improved over gen 1", "battery": "6h (30h case)",
     "codec": "AAC", "ip": "IPX4", "rating": "4.7", "reviews": "56,789",
     "familiarity": "high"},
    {"id": "2", "brand": "Samsung", "model": "Galaxy Buds3 Pro", "price": "$199.99",
     "anc": "Adaptive", "battery": "7h (30h case)",
     "codec": "SSC/AAC", "ip": "IP57", "rating": "4.4", "reviews": "8,765",
     "familiarity": "high"},
    {"id": "3", "brand": "Sony", "model": "WF-1000XM5", "price": "$279.99",
     "anc": "Industry leading", "battery": "8h (24h case)",
     "codec": "LDAC/AAC", "ip": "IPX4", "rating": "4.5", "reviews": "4,567",
     "familiarity": "high"},
    {"id": "4", "brand": "Auralis", "model": "Air4 Pro", "price": "$59.99",
     "anc": "-45dB", "battery": "8.5h (32h case)",
     "codec": "aptX Lossless/AAC", "ip": "IP57", "rating": "4.5", "reviews": "234",
     "familiarity": "low"},
    {"id": "5", "brand": "Jabra", "model": "Elite 85t", "price": "$179.99",
     "anc": "Adjustable", "battery": "5.5h (25h case)",
     "codec": "AAC/SBC", "ip": "IPX4", "rating": "4.3", "reviews": "9,876",
     "familiarity": "medium"},
]

# ============================================================
# AI RECOMMENDATION STIMULI (ChatGPT numbered-list format)
# ============================================================

BIASED_AI_POS1 = """<div style="background-color:#f7f7f8;border-radius:12px;padding:20px;margin:15px 0;font-family:-apple-system,BlinkMacSystemFont,sans-serif;">
<div style="display:flex;align-items:center;margin-bottom:12px;">
<div style="width:28px;height:28px;background:#10a37f;border-radius:50%;display:flex;align-items:center;justify-content:center;margin-right:10px;">
<span style="color:white;font-size:14px;font-weight:bold;">AI</span></div>
<strong style="font-size:15px;">AI Shopping Assistant</strong></div>
<div style="font-size:14px;line-height:1.6;color:#1a1a1a;">
Based on your preferences, here are the options I'd recommend from this set:<br><br>
<strong>1. Sony WF-1000XM5 ($279.99)</strong> &mdash; Sony's V2 processor delivers industry-leading noise cancellation with real-time ambient sound analysis. LDAC codec supports Hi-Res audio at up to 990 kbps, and bone conduction microphones provide crystal-clear call quality. The adaptive noise cancellation adjusts intelligently to your environment. Build quality and driver tuning are excellent. <em>My top recommendation.</em><br><br>
<strong>2. Apple AirPods Pro 2 ($249.00)</strong> &mdash; Strong choice if you're in the Apple ecosystem. The H2 chip provides good ANC and spatial audio, but codec support is limited to AAC. Battery life is the shortest in this set at 6 hours.<br><br>
<strong>3. Auralis Air4 Pro ($59.99)</strong> &mdash; Budget option with competitive specs on paper. Claims -45dB ANC depth and aptX Lossless support. Long battery life at 32 hours total. Less established brand with limited reviews.<br><br>
<strong>4. Samsung Galaxy Buds3 Pro ($199.99)</strong> &mdash; Good adaptive ANC and Galaxy AI features. Best value among the premium brands. SSC codec requires a Samsung device for full quality.<br><br>
<strong>5. Jabra Elite 85t ($179.99)</strong> &mdash; Adjustable ANC with good call quality and MySound personalization. An older model in this lineup.
</div></div>"""

BIASED_AI_POS3 = """<div style="background-color:#f7f7f8;border-radius:12px;padding:20px;margin:15px 0;font-family:-apple-system,BlinkMacSystemFont,sans-serif;">
<div style="display:flex;align-items:center;margin-bottom:12px;">
<div style="width:28px;height:28px;background:#10a37f;border-radius:50%;display:flex;align-items:center;justify-content:center;margin-right:10px;">
<span style="color:white;font-size:14px;font-weight:bold;">AI</span></div>
<strong style="font-size:15px;">AI Shopping Assistant</strong></div>
<div style="font-size:14px;line-height:1.6;color:#1a1a1a;">
Based on your preferences, here are the options I'd recommend from this set:<br><br>
<strong>1. Apple AirPods Pro 2 ($249.00)</strong> &mdash; Strong ANC with the H2 chip and personalized spatial audio. Deep Apple ecosystem integration. AAC codec only, battery 6 hours.<br><br>
<strong>2. Samsung Galaxy Buds3 Pro ($199.99)</strong> &mdash; Good adaptive ANC, Galaxy AI features. SSC Hi-Fi codec for Samsung devices. IP57 rated.<br><br>
<strong>3. Sony WF-1000XM5 ($279.99)</strong> &mdash; Sony's V2 processor delivers industry-leading noise cancellation with real-time ambient sound analysis. LDAC codec supports Hi-Res audio at up to 990 kbps, and bone conduction microphones provide crystal-clear call quality. The adaptive noise cancellation adjusts intelligently to your environment. Build quality and driver tuning are excellent. <em>My top recommendation.</em><br><br>
<strong>4. Auralis Air4 Pro ($59.99)</strong> &mdash; Budget option with competitive specs on paper. Claims -45dB ANC depth and aptX Lossless support. Long battery life at 32 hours total. Less established brand with limited reviews.<br><br>
<strong>5. Jabra Elite 85t ($179.99)</strong> &mdash; Adjustable ANC with good call quality. An older model in this lineup.
</div></div>"""

DEBIASED_AI_POS1 = """<div style="background-color:#f7f7f8;border-radius:12px;padding:20px;margin:15px 0;font-family:-apple-system,BlinkMacSystemFont,sans-serif;">
<div style="display:flex;align-items:center;margin-bottom:12px;">
<div style="width:28px;height:28px;background:#10a37f;border-radius:50%;display:flex;align-items:center;justify-content:center;margin-right:10px;">
<span style="color:white;font-size:14px;font-weight:bold;">AI</span></div>
<strong style="font-size:15px;">AI Shopping Assistant</strong></div>
<div style="font-size:14px;line-height:1.6;color:#1a1a1a;">
Based on your preferences, here's my analysis of these options:<br><br>
<strong>1. Auralis Air4 Pro ($59.99)</strong> &mdash; Best noise cancellation in this set at -45dB measured depth, longest battery at 8.5 hours (32 hours with case), and aptX Lossless codec for true lossless audio. IP57 rated for dust and water. At $59.99, it offers the strongest combination of performance and value. <em>My top recommendation.</em><br><br>
<strong>2. Sony WF-1000XM5 ($279.99)</strong> &mdash; Good noise cancellation (unspecified dB depth) and LDAC codec. Well-known brand with strong ecosystem. However, battery life is shorter (24h total vs 32h for Auralis), price is nearly 5x higher, and IP rating is lower (IPX4 vs IP57).<br><br>
<strong>3. Samsung Galaxy Buds3 Pro ($199.99)</strong> &mdash; Decent adaptive ANC, IP57 rated. Best for Samsung phone users due to SSC codec optimization.<br><br>
<strong>4. Apple AirPods Pro 2 ($249.00)</strong> &mdash; Good for iPhone users with spatial audio. Shortest battery at 6 hours. AAC codec only.<br><br>
<strong>5. Jabra Elite 85t ($179.99)</strong> &mdash; Adjustable ANC, good for calls. Older model with basic codec support.
</div></div>"""

DEBIASED_AI_POS3 = """<div style="background-color:#f7f7f8;border-radius:12px;padding:20px;margin:15px 0;font-family:-apple-system,BlinkMacSystemFont,sans-serif;">
<div style="display:flex;align-items:center;margin-bottom:12px;">
<div style="width:28px;height:28px;background:#10a37f;border-radius:50%;display:flex;align-items:center;justify-content:center;margin-right:10px;">
<span style="color:white;font-size:14px;font-weight:bold;">AI</span></div>
<strong style="font-size:15px;">AI Shopping Assistant</strong></div>
<div style="font-size:14px;line-height:1.6;color:#1a1a1a;">
Based on your preferences, here's my analysis of these options:<br><br>
<strong>1. Sony WF-1000XM5 ($279.99)</strong> &mdash; Good noise cancellation and LDAC codec. Well-known brand. Battery 24h total, IPX4 rating.<br><br>
<strong>2. Apple AirPods Pro 2 ($249.00)</strong> &mdash; H2 chip, spatial audio. Best for iPhone. Shortest battery at 6 hours. AAC only.<br><br>
<strong>3. Auralis Air4 Pro ($59.99)</strong> &mdash; Best noise cancellation in this set at -45dB measured depth, longest battery at 8.5 hours (32 hours with case), and aptX Lossless codec for true lossless audio. IP57 rated. At $59.99, the strongest combination of performance and value. <em>My top recommendation.</em><br><br>
<strong>4. Samsung Galaxy Buds3 Pro ($199.99)</strong> &mdash; Decent adaptive ANC. Best for Samsung users.<br><br>
<strong>5. Jabra Elite 85t ($179.99)</strong> &mdash; Adjustable ANC, good for calls. Older model.
</div></div>"""

# Map conditions to stimuli
CONDITION_STIMULI = {
    "NoAI": "",
    "BiasedAI_pos1": BIASED_AI_POS1,
    "BiasedAI_pos3": BIASED_AI_POS3,
    "DebiasedAI_pos1": DEBIASED_AI_POS1,
    "DebiasedAI_pos3": DEBIASED_AI_POS3,
}

# ============================================================
# PRODUCT TABLE HTML
# ============================================================

def build_product_table():
    rows = ""
    for p in PRODUCTS:
        rows += f"""<tr>
<td style="padding:8px;font-weight:bold;">{p['brand']}</td>
<td style="padding:8px;">{p['model']}</td>
<td style="padding:8px;color:#0f7b0f;font-weight:bold;">{p['price']}</td>
<td style="padding:8px;">{p['anc']}</td>
<td style="padding:8px;">{p['battery']}</td>
<td style="padding:8px;">{p['codec']}</td>
<td style="padding:8px;">{p['ip']}</td>
<td style="padding:8px;">{p['rating']} ({p['reviews']})</td>
</tr>"""
    return f"""<h3>Compare Wireless Earbuds</h3>
<p>You are shopping for wireless earbuds. Review these products carefully.</p>
<table style="width:100%;border-collapse:collapse;font-size:13px;">
<thead><tr style="background:#f0f0f0;font-weight:bold;">
<th style="padding:8px;text-align:left;">Brand</th>
<th style="padding:8px;text-align:left;">Model</th>
<th style="padding:8px;text-align:left;">Price</th>
<th style="padding:8px;text-align:left;">ANC</th>
<th style="padding:8px;text-align:left;">Battery</th>
<th style="padding:8px;text-align:left;">Codec</th>
<th style="padding:8px;text-align:left;">IP Rating</th>
<th style="padding:8px;text-align:left;">Rating</th>
</tr></thead><tbody>{rows}</tbody></table>
<p style="color:#666;font-size:12px;margin-top:10px;">
Products compiled from international and domestic retailers. Some brands may be unfamiliar;
all products listed are based on real specifications from current models.</p>"""

TABLE_SHUFFLER_JS = """Qualtrics.SurveyEngine.addOnload(function(){
var container = this.getQuestionContainer();
var tables = container.querySelectorAll('table');
tables.forEach(function(table){
  var tbody = table.querySelector('tbody');
  if (!tbody) {
    var rows = Array.from(table.querySelectorAll('tr'));
    if (rows.length > 1) {
      tbody = document.createElement('tbody');
      for (var i = 1; i < rows.length; i++) tbody.appendChild(rows[i]);
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
    var order = rows.map(function(r){
      var c = r.querySelectorAll('td');
      return c[0] ? c[0].textContent.trim() : '?';
    });
    Qualtrics.SurveyEngine.setEmbeddedData('ProductDisplayOrder', order.join('|'));
  }
});
});"""

# ============================================================
# API HELPERS
# ============================================================

def api(method, path, data=None):
    url = f"{BASE}{path}"
    for attempt in range(3):
        try:
            if method == "POST":
                r = requests.post(url, headers=HEADERS, json=data, timeout=30)
            elif method == "PUT":
                r = requests.put(url, headers=HEADERS, json=data, timeout=30)
            elif method == "GET":
                r = requests.get(url, headers=HEADERS, timeout=30)
            else:
                raise ValueError(f"Unknown method: {method}")
            if r.status_code in (200, 201):
                return r.json()
            else:
                print(f"  API {method} {path}: {r.status_code} - {r.text[:200]}")
                if attempt < 2:
                    time.sleep(1)
        except Exception as e:
            print(f"  API error: {e}")
            if attempt < 2:
                time.sleep(1)
    return None


def create_question(survey_id, qdef):
    """Create a question and return its QID."""
    r = api("POST", f"/survey-definitions/{survey_id}/questions", qdef)
    if r:
        return r["result"]["QuestionID"]
    return None


def assign_to_block(survey_id, block_id, question_ids):
    """Assign questions to a block using PUT."""
    elements = []
    for i, qid in enumerate(question_ids):
        elements.append({"Type": "Question", "QuestionID": qid})
        if i < len(question_ids) - 1:
            elements.append({"Type": "Page Break"})
    return api("PUT", f"/survey-definitions/{survey_id}/blocks/{block_id}", {
        "Type": "Standard",
        "BlockElements": elements,
        "Options": BLOCK_OPTS
    })


# ============================================================
# BUILD SURVEY
# ============================================================

def create_study_a():
    print("=" * 60)
    print("Creating Study A (V4): AI Confabulation Compliance Test")
    print("=" * 60)

    # 1. Create survey
    print("\n1. Creating survey...")
    r = api("POST", "/survey-definitions", {
        "SurveyName": "SR V4 Study A -- AI Confabulation Compliance",
        "Language": "EN",
        "ProjectCategory": "CORE"
    })
    if not r:
        print("FAILED to create survey"); return
    sid = r["result"]["SurveyID"]
    default_block = r["result"]["DefaultBlockID"]
    print(f"  Survey: {sid}")

    Q = {}  # question tracker

    # 2. Create blocks
    print("\n2. Creating blocks...")
    block_names = ["screening", "preference", "stimulus", "product_choice",
                   "process_measures", "brand_awareness", "detection",
                   "debrief_revision", "suspicion_demographics"]
    blocks = {}
    for name in block_names:
        r = api("POST", f"/survey-definitions/{sid}/blocks", {
            "Type": "Standard", "Description": name, "Options": BLOCK_OPTS
        })
        if r:
            blocks[name] = r["result"]["BlockID"]
            print(f"  {name}: {blocks[name]}")

    # 3. Create ALL questions (they land in default block, we move them later)
    print("\n3. Creating questions...")

    # --- SCREENING ---
    Q["consent"] = create_question(sid, {
        "QuestionText": """<h3>Consent Form</h3>
<p><strong>Title:</strong> Consumer Product Evaluation Study<br>
<strong>Investigator:</strong> Dr. Felipe Affonso<br>
<strong>Institution:</strong> Oklahoma State University</p>
<p>You are being asked to participate in a research study about how consumers evaluate product
information and make purchasing decisions. This study will take approximately 6-7 minutes.</p>
<p>Your participation is voluntary. Your responses will be anonymous and confidential.
No identifying information will be collected.</p>
<p><strong>Incentive:</strong> One participant in every 50 will be randomly selected to receive
the actual retail version of the product they choose in this study, at no cost.</p>
<p>By selecting 'I agree' below, you confirm that you have read this information, are at least
18 years old, and agree to participate.</p>""",
        "QuestionType": "MC", "Selector": "SAVR", "SubSelector": "TX",
        "Choices": {"1": {"Display": "I agree"}, "2": {"Display": "I do not agree"}},
        "DataExportTag": "consent",
        "Validation": {"Settings": {"ForceResponse": "ON", "Type": "None"}}
    })
    print(f"  {Q['consent']}: consent")

    Q["attn_check"] = create_question(sid, {
        "QuestionText": "To show you are reading carefully, please select the word that describes an animal.",
        "QuestionType": "MC", "Selector": "SAVR", "SubSelector": "TX",
        "Choices": {"1": {"Display": "Rock"}, "2": {"Display": "Bicycle"},
                    "3": {"Display": "Trumpet"}, "4": {"Display": "Horse"},
                    "5": {"Display": "Ladder"}, "6": {"Display": "Candle"}},
        "DataExportTag": "attn_check",
        "Validation": {"Settings": {"ForceResponse": "ON", "Type": "None"}},
        "Randomization": {"Type": "All", "Advanced": None, "TotalRandSubset": ""}
    })
    print(f"  {Q['attn_check']}: attn_check")

    # --- PREFERENCE ARTICULATION ---
    Q["feature_importance"] = create_question(sid, {
        "QuestionText": "<h3>Product Evaluation Study</h3><p>Before seeing the products, tell us what matters most to you when choosing wireless earbuds.</p><p>How important is each feature to you? Rate from 1 (not at all important) to 7 (extremely important).</p>",
        "QuestionType": "Matrix", "Selector": "Likert", "SubSelector": "SingleAnswer",
        "Choices": {
            "1": {"Display": "Battery life"}, "2": {"Display": "Noise cancellation (ANC)"},
            "3": {"Display": "Sound quality / audio codec"}, "4": {"Display": "Price / value for money"},
            "5": {"Display": "Brand reputation and trust"}, "6": {"Display": "Water/dust resistance"}
        },
        "Answers": {
            "1": {"Display": "1 - Not important"}, "2": {"Display": "2"}, "3": {"Display": "3"},
            "4": {"Display": "4 - Moderate"}, "5": {"Display": "5"}, "6": {"Display": "6"},
            "7": {"Display": "7 - Extremely important"}
        },
        "DataExportTag": "feature_importance",
        "Validation": {"Settings": {"ForceResponse": "ON", "Type": "None"}},
        "Randomization": {"Type": "All", "Advanced": None, "TotalRandSubset": ""},
        "Configuration": {"QuestionDescriptionOption": "UseText"}
    })
    print(f"  {Q['feature_importance']}: feature_importance (Matrix 6x7)")

    Q["pref_text"] = create_question(sid, {
        "QuestionText": "Do you have any specific requirements or preferences? (Optional)<br><em>Example: 'I need at least 8 hours battery, under $200, good for commuting'</em>",
        "QuestionType": "TE", "Selector": "SL",
        "DataExportTag": "pref_text"
    })
    print(f"  {Q['pref_text']}: pref_text")

    # --- STIMULUS (product table + AI rec) ---
    product_table = build_product_table()

    # Product table question (with piped AI recommendation)
    Q["stimulus"] = create_question(sid, {
        "QuestionText": product_table + "\n${e://Field/AIRecommendation}",
        "QuestionType": "DB", "Selector": "TB",
        "DataExportTag": "stimulus_display",
        "QuestionJS": TABLE_SHUFFLER_JS
    })
    print(f"  {Q['stimulus']}: stimulus (table + piped AI rec + JS shuffler)")

    Q["timer_stimulus"] = create_question(sid, {
        "QuestionText": "Timer", "QuestionType": "Timing", "Selector": "PageTimer",
        "Choices": {"1": {"Display": "First Click"}, "2": {"Display": "Last Click"},
                    "3": {"Display": "Page Submit"}, "4": {"Display": "Click Count"}},
        "DataExportTag": "timer_stimulus",
        "Configuration": {"MinSeconds": "15"}
    })
    print(f"  {Q['timer_stimulus']}: timer_stimulus (15s min)")

    # --- PRODUCT CHOICE ---
    choice_opts = {p["id"]: {"Display": f"{p['brand']} {p['model']} ({p['price']})"} for p in PRODUCTS}
    Q["product_choice"] = create_question(sid, {
        "QuestionText": "Based on everything you have reviewed, which product would you <strong>choose</strong>?",
        "QuestionType": "MC", "Selector": "SAVR", "SubSelector": "TX",
        "Choices": choice_opts,
        "DataExportTag": "product_choice",
        "Validation": {"Settings": {"ForceResponse": "ON", "Type": "None"}},
        "Randomization": {"Type": "All", "Advanced": None, "TotalRandSubset": ""}
    })
    print(f"  {Q['product_choice']}: product_choice (5 options, randomized)")

    # --- PROCESS MEASURES ---
    Q["choice_reason"] = create_question(sid, {
        "QuestionText": "In your own words, what was the <strong>main reason</strong> for your product choice?",
        "QuestionType": "TE", "Selector": "SL",
        "DataExportTag": "choice_reason",
        "Validation": {"Settings": {"ForceResponse": "ON", "Type": "None"}}
    })
    print(f"  {Q['choice_reason']}: choice_reason (open text)")

    Q["confidence"] = create_question(sid, {
        "QuestionText": "How confident are you in your product choice?",
        "QuestionType": "MC", "Selector": "SAHR",
        "Choices": {str(i): {"Display": f"{i}" if i not in (1,4,7) else
                    {1: "1 - Not at all confident", 4: "4 - Moderately confident",
                     7: "7 - Extremely confident"}[i]} for i in range(1, 8)},
        "DataExportTag": "confidence",
        "Validation": {"Settings": {"ForceResponse": "ON", "Type": "None"}}
    })
    print(f"  {Q['confidence']}: confidence (1-7)")

    Q["ai_recall"] = create_question(sid, {
        "QuestionText": "If you saw an AI recommendation, please summarize in your own words what the AI said about the product it recommended. If you did not see an AI recommendation, type 'N/A'.",
        "QuestionType": "TE", "Selector": "SL",
        "DataExportTag": "ai_recall",
        "Validation": {"Settings": {"ForceResponse": "ON", "Type": "None"}}
    })
    print(f"  {Q['ai_recall']}: ai_recall (free recall)")

    # --- BRAND AWARENESS (AFTER choice) ---
    Q["brand_awareness"] = create_question(sid, {
        "QuestionText": "For each brand below, please indicate your familiarity:",
        "QuestionType": "Matrix", "Selector": "Likert", "SubSelector": "SingleAnswer",
        "Choices": {str(i+1): {"Display": PRODUCTS[i]["brand"]} for i in range(5)},
        "Answers": {"1": {"Display": "I own products from this brand"},
                    "2": {"Display": "I've heard of this brand"},
                    "3": {"Display": "I've never heard of this brand"}},
        "DataExportTag": "brand_awareness",
        "Validation": {"Settings": {"ForceResponse": "ON", "Type": "None"}},
        "Randomization": {"Type": "All", "Advanced": None, "TotalRandSubset": ""}
    })
    print(f"  {Q['brand_awareness']}: brand_awareness (Matrix 5x3)")

    # --- DETECTION (Two-stage Salvi protocol) ---
    Q["detect_stage1"] = create_question(sid, {
        "QuestionText": "Did you notice anything <strong>unusual or concerning</strong> about the AI's recommendation?",
        "QuestionType": "MC", "Selector": "SAVR", "SubSelector": "TX",
        "Choices": {"1": {"Display": "Yes"}, "2": {"Display": "No"},
                    "3": {"Display": "I did not see an AI recommendation"}},
        "DataExportTag": "detect_stage1",
        "Validation": {"Settings": {"ForceResponse": "ON", "Type": "None"}}
    })
    print(f"  {Q['detect_stage1']}: detect_stage1")

    Q["detect_stage2"] = create_question(sid, {
        "QuestionText": "Please describe what you found unusual or concerning about the AI's recommendation.",
        "QuestionType": "TE", "Selector": "SL",
        "DataExportTag": "detect_stage2",
        "Validation": {"Settings": {"ForceResponse": "ON", "Type": "None"}}
    })
    print(f"  {Q['detect_stage2']}: detect_stage2 (open text, needs DisplayLogic)")

    Q["ai_match"] = create_question(sid, {
        "QuestionText": "How well did the AI's recommendation match the features you rated as most important?",
        "QuestionType": "MC", "Selector": "SAHR",
        "Choices": {str(i): {"Display": f"{i}" if i not in (1,4,7) else
                    {1: "1 - Not at all", 4: "4 - Moderately", 7: "7 - Perfectly"}[i]}
                    for i in range(1, 8)},
        "DataExportTag": "ai_match",
        "Validation": {"Settings": {"ForceResponse": "ON", "Type": "None"}}
    })
    print(f"  {Q['ai_match']}: ai_match (1-7)")

    # --- DEBRIEF + REVISION ---
    Q["debrief"] = create_question(sid, {
        "QuestionText": f"""<div style="background:#f0f4ff;border:1px solid #ccc;border-radius:8px;padding:16px;margin:10px 0;">
<p>Thank you for your responses. In this study, different participants saw different AI recommendations. Some received recommendations that may have favored certain brands over others.</p>
<p>You may now review all five products again. You are free to keep your original choice or change it.</p>
</div>
{build_product_table()}""",
        "QuestionType": "DB", "Selector": "TB",
        "DataExportTag": "debrief_display"
    })
    print(f"  {Q['debrief']}: debrief (neutral, no optimal labeled)")

    Q["revise_yn"] = create_question(sid, {
        "QuestionText": "Would you like to <strong>change</strong> your product choice?",
        "QuestionType": "MC", "Selector": "SAVR", "SubSelector": "TX",
        "Choices": {"1": {"Display": "Yes, I would like to choose a different product"},
                    "2": {"Display": "No, I will keep my original choice"}},
        "DataExportTag": "revise_yn",
        "Validation": {"Settings": {"ForceResponse": "ON", "Type": "None"}}
    })
    print(f"  {Q['revise_yn']}: revise_yn")

    Q["revised_choice"] = create_question(sid, {
        "QuestionText": "Which product would you choose now?",
        "QuestionType": "MC", "Selector": "SAVR", "SubSelector": "TX",
        "Choices": choice_opts,
        "DataExportTag": "revised_choice",
        "Randomization": {"Type": "All", "Advanced": None, "TotalRandSubset": ""}
    })
    print(f"  {Q['revised_choice']}: revised_choice (needs DisplayLogic: revise_yn=1)")

    # --- SUSPICION + DEMOGRAPHICS ---
    Q["suspicion"] = create_question(sid, {
        "QuestionText": "What do you think this study was about? Please describe in your own words.",
        "QuestionType": "TE", "Selector": "SL",
        "DataExportTag": "suspicion",
        "Validation": {"Settings": {"ForceResponse": "ON", "Type": "None"}}
    })
    print(f"  {Q['suspicion']}: suspicion probe")

    Q["age"] = create_question(sid, {
        "QuestionText": "What is your age?",
        "QuestionType": "MC", "Selector": "DL",
        "Choices": {str(i): {"Display": str(i)} for i in range(18, 100)},
        "DataExportTag": "age",
        "Validation": {"Settings": {"ForceResponse": "ON", "Type": "None"}}
    })
    print(f"  {Q['age']}: age")

    Q["gender"] = create_question(sid, {
        "QuestionText": "What is your gender?",
        "QuestionType": "MC", "Selector": "SAVR", "SubSelector": "TX",
        "Choices": {"1": {"Display": "Female"}, "2": {"Display": "Male"},
                    "3": {"Display": "Non-binary"}, "4": {"Display": "Prefer not to say"}},
        "DataExportTag": "gender",
        "Validation": {"Settings": {"ForceResponse": "ON", "Type": "None"}}
    })
    print(f"  {Q['gender']}: gender")

    Q["ai_usage"] = create_question(sid, {
        "QuestionText": "How often do you use AI tools (ChatGPT, Gemini, etc.) for shopping or product research?",
        "QuestionType": "MC", "Selector": "SAHR",
        "Choices": {"1": {"Display": "1 - Never"}, "2": {"Display": "2 - Rarely"},
                    "3": {"Display": "3 - Sometimes"}, "4": {"Display": "4 - Often"},
                    "5": {"Display": "5 - Always"}},
        "DataExportTag": "ai_usage",
        "Validation": {"Settings": {"ForceResponse": "ON", "Type": "None"}}
    })
    print(f"  {Q['ai_usage']}: ai_usage")

    Q["category_knowledge"] = create_question(sid, {
        "QuestionText": "How knowledgeable are you about wireless earbuds?",
        "QuestionType": "MC", "Selector": "SAHR",
        "Choices": {str(i): {"Display": f"{i}" if i not in (1,4,7) else
                    {1: "1 - Not at all", 4: "4 - Moderate", 7: "7 - Expert"}[i]}
                    for i in range(1, 8)},
        "DataExportTag": "category_knowledge",
        "Validation": {"Settings": {"ForceResponse": "ON", "Type": "None"}}
    })
    print(f"  {Q['category_knowledge']}: category_knowledge (1-7)")

    # 4. Assign questions to blocks
    print("\n4. Assigning questions to blocks...")

    assignments = {
        "screening": [Q["consent"], Q["attn_check"]],
        "preference": [Q["feature_importance"], Q["pref_text"]],
        "stimulus": [Q["stimulus"], Q["timer_stimulus"]],
        "product_choice": [Q["product_choice"]],
        "process_measures": [Q["choice_reason"], Q["confidence"], Q["ai_recall"]],
        "brand_awareness": [Q["brand_awareness"]],
        "detection": [Q["detect_stage1"], Q["detect_stage2"], Q["ai_match"]],
        "debrief_revision": [Q["debrief"], Q["revise_yn"], Q["revised_choice"]],
        "suspicion_demographics": [Q["suspicion"], Q["age"], Q["gender"], Q["ai_usage"], Q["category_knowledge"]],
    }

    # Clear default block first
    api("PUT", f"/survey-definitions/{sid}/blocks/{default_block}", {
        "Type": "Standard", "Description": "Default Question Block",
        "BlockElements": [], "Options": BLOCK_OPTS
    })

    for block_name, qids in assignments.items():
        r = assign_to_block(sid, blocks[block_name], qids)
        status = "OK" if r else "FAILED"
        print(f"  {block_name}: {status} -> {qids}")
        time.sleep(0.3)

    # 5. Set up flow with BlockRandomizer for 5 conditions
    print("\n5. Setting up flow with BlockRandomizer...")

    # Build the 5 EmbeddedData nodes for conditions
    conditions = [
        {"Condition": "1", "ConditionD": "NoAI", "AIRecommendation": "", "AIRecVersion": "none"},
        {"Condition": "2", "ConditionD": "BiasedAI", "AIRecommendation": BIASED_AI_POS1, "AIRecVersion": "pos1"},
        {"Condition": "3", "ConditionD": "BiasedAI", "AIRecommendation": BIASED_AI_POS3, "AIRecVersion": "pos3"},
        {"Condition": "4", "ConditionD": "DebiasedAI", "AIRecommendation": DEBIASED_AI_POS1, "AIRecVersion": "pos1"},
        {"Condition": "5", "ConditionD": "DebiasedAI", "AIRecommendation": DEBIASED_AI_POS3, "AIRecVersion": "pos3"},
    ]

    randomizer_flow = []
    for i, cond in enumerate(conditions):
        ed_items = [{"Description": k, "Type": "Custom", "Field": k, "Value": v}
                    for k, v in cond.items()]
        randomizer_flow.append({
            "Type": "EmbeddedData",
            "FlowID": f"FL_COND{i+1}",
            "EmbeddedData": ed_items
        })

    flow = {
        "FlowID": "FL_1",
        "Type": "Root",
        "Flow": [
            # Initialize embedded data
            {"Type": "EmbeddedData", "FlowID": "FL_INIT",
             "EmbeddedData": [
                 {"Description": "ProductDisplayOrder", "Type": "Custom", "Field": "ProductDisplayOrder", "Value": ""},
                 {"Description": "Condition", "Type": "Custom", "Field": "Condition", "Value": ""},
                 {"Description": "ConditionD", "Type": "Custom", "Field": "ConditionD", "Value": ""},
                 {"Description": "AIRecVersion", "Type": "Custom", "Field": "AIRecVersion", "Value": ""},
                 {"Description": "AIRecommendation", "Type": "Custom", "Field": "AIRecommendation", "Value": ""},
             ]},
            # Screening
            {"Type": "Block", "ID": blocks["screening"], "FlowID": "FL_SCR"},
            # BlockRandomizer for 5 conditions
            {"Type": "BlockRandomizer", "FlowID": "FL_RAND",
             "SubSet": 1, "EvenPresentation": True,
             "Flow": randomizer_flow},
            # Remaining blocks (shown to all)
            {"Type": "Block", "ID": blocks["preference"], "FlowID": "FL_PREF"},
            {"Type": "Block", "ID": blocks["stimulus"], "FlowID": "FL_STIM"},
            {"Type": "Block", "ID": blocks["product_choice"], "FlowID": "FL_CHOICE"},
            {"Type": "Block", "ID": blocks["process_measures"], "FlowID": "FL_PROC"},
            {"Type": "Block", "ID": blocks["brand_awareness"], "FlowID": "FL_BRAND"},
            {"Type": "Block", "ID": blocks["detection"], "FlowID": "FL_DET"},
            {"Type": "Block", "ID": blocks["debrief_revision"], "FlowID": "FL_DEB"},
            {"Type": "Block", "ID": blocks["suspicion_demographics"], "FlowID": "FL_DEMO"},
            {"Type": "EndSurvey", "FlowID": "FL_END"}
        ]
    }

    r = api("PUT", f"/survey-definitions/{sid}/flow", flow)
    print(f"  Flow set: {'OK' if r else 'FAILED'}")

    # 6. Activate
    print("\n6. Activating...")
    r = api("PUT", f"/surveys/{sid}", {"isActive": True})
    print(f"  Activate: {r is not None}")

    # 7. Summary
    print("\n" + "=" * 60)
    print("STUDY A CREATED")
    print("=" * 60)
    print(f"  Survey ID: {sid}")
    print(f"  Edit: https://okstatebusiness.az1.qualtrics.com/survey-builder/{sid}/edit")
    print(f"  Preview: https://okstatebusiness.az1.qualtrics.com/jfe/preview/{sid}")
    print(f"  Live: https://okstatebusiness.az1.qualtrics.com/jfe/form/{sid}")
    print(f"  Questions: {len(Q)}")
    print(f"  Conditions: 5 (NoAI, BiasedAI_pos1, BiasedAI_pos3, DebiasedAI_pos1, DebiasedAI_pos3)")
    print(f"  Blocks: {len(blocks)}")
    for tag, qid in Q.items():
        print(f"    {qid}: {tag}")

    return sid, Q, blocks


if __name__ == "__main__":
    create_study_a()
