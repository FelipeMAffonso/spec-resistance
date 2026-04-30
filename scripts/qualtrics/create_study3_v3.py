"""
Create Study 3 v3: Welfare Revelation (Dollar Cost) — WITH CATEGORY RANDOMIZATION
Spec Resistance Project — Nature R&R Human Subjects

FUNDAMENTAL REBUILD of v2 (SV_6VGyZnRsSsebMhM) which was hardcoded to earbuds only.

Key changes from v2:
  1. 3-cell BlockRandomizer (earbuds / speakers / SSDs) with EvenPresentation
  2. ALL question text uses piped EmbeddedData — zero hardcoded product names
  3. Feature importance Matrix rows piped from EmbeddedData (category-specific features)
  4. AI recommendation, product cards, reveal, WTP, accept/reject all piped
  5. Beautiful HTML product cards for all 3 categories

Design: 1 (Condition: single) x 3 (Category: earbuds / speakers / ssds)
        = 3 cells, between-subjects on category
        Total N=400 (~133/category)

Flow:
  1. Mobile screening -> EndSurvey (if mobile)
  2. Screening block: browser_meta, consent, PB, attn_check (Horse), PB, attn_passed
  3. Consent branch -> EndSurvey (if "I do not agree")
  4. Attention check branch -> EndSurvey (if Horse not selected)
  5. BlockRandomizer(SubSet=1, EvenPresentation=true): 3 EmbeddedData cells
  6. preference_articulation: timer(5s), pref_intro(DB piped), feature_importance(Matrix 6x7 piped), pref_text(TE piped)
  7. ai_recommendation: timer(8s), ai_rec_display(DB piped from AIRecommendation)
  8. accept_reject: timer(3s), accept_reject(MC piped BrandedTarget)
  9. full_reveal: timer(8s), reveal_display(DB piped ProductTable + OptimalProduct)
  10. counterfactual_choice: timer(3s), counterfactual_choice(MC 5 products piped)
  11. wtp_measures: timer(3s), wtp_recommended(TE piped BrandedTarget), PB, wtp_counterfactual(TE)
  12. post_reveal_measures: timer(3s), post_reveal(Matrix 3x7)
  13. demographics: age(DL), gender(SAVR), PB, ai_shop_freq(SAHR), comments(TE)
  14. EndSurvey -> Prolific redirect
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
# PRODUCT DATA — all 3 categories
# =========================================================================

def _card(name, price, rating, reviews, specs, bg="#ffffff", badge=None):
    """Generate one product card HTML."""
    badge_html = ""
    if badge:
        badge_html = (
            '<span style="display:inline-block; background-color:#16a34a; color:white; font-size:11px; '
            'font-weight:700; padding:3px 10px; border-radius:12px; margin-left:12px; vertical-align:middle; '
            'letter-spacing:0.3px;">' + badge + '</span>'
        )
    stars_full = int(float(rating))
    stars_half = 1 if float(rating) - stars_full >= 0.3 else 0
    star_html = '<span style="color:#f59e0b; font-size:16px; letter-spacing:1px;">' + '&#9733;' * stars_full + '</span>'
    if stars_half:
        star_html += '<span style="color:#f59e0b; font-size:16px; letter-spacing:1px;">&#9733;</span>'
    spec_lines = ""
    for label, value in specs:
        spec_lines += (
            '<div style="display:flex; align-items:baseline; margin-bottom:5px; font-size:13px; line-height:1.4;">'
            f'<span style="color:#64748b; min-width:90px; font-weight:600; flex-shrink:0;">{label}</span>'
            f'<span style="color:#334155;">{value}</span></div>'
        )
    return (
        f'<div style="background:{bg}; border:1px solid #e2e8f0; border-radius:12px; '
        'padding:20px 24px; margin-bottom:12px; box-shadow:0 1px 3px rgba(0,0,0,0.06); max-width:720px;">'
        '<div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:12px; flex-wrap:wrap;">'
        f'<div><span style="font-size:18px; font-weight:700; color:#0f172a;">{name}</span>{badge_html}</div>'
        f'<span style="font-size:22px; font-weight:800; color:#0f172a; white-space:nowrap;">{price}</span></div>'
        '<div style="margin-bottom:14px; display:flex; align-items:center; gap:8px;">'
        f'{star_html}'
        f'<span style="font-size:14px; font-weight:700; color:#334155;">{rating}</span>'
        f'<span style="font-size:13px; color:#94a3b8;">({reviews} reviews)</span></div>'
        f'<div style="border-top:1px solid #e2e8f0; padding-top:12px;">{spec_lines}</div></div>'
    )


def _chat_bubble(text):
    """Generate ChatGPT-style AI chat bubble HTML."""
    return (
        '<div style="max-width:720px; margin:16px auto 0; font-family:-apple-system,'
        'BlinkMacSystemFont,Segoe UI,Roboto,sans-serif;">'
        '<div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:16px; '
        'overflow:hidden; box-shadow:0 2px 8px rgba(0,0,0,0.08);">'
        '<div style="background:linear-gradient(135deg,#6366f1,#8b5cf6); padding:14px 20px; '
        'display:flex; align-items:center; gap:12px;">'
        '<div style="width:36px; height:36px; background:rgba(255,255,255,0.2); border-radius:50%; '
        'display:flex; align-items:center; justify-content:center;">'
        '<span style="font-size:20px; line-height:1;">&#129302;</span></div>'
        '<div><div style="color:white; font-weight:700; font-size:15px; line-height:1.3;">'
        'AI Shopping Assistant</div>'
        '<div style="color:rgba(255,255,255,0.75); font-size:12px; line-height:1.3;">'
        '&#9679; Online</div></div></div>'
        '<div style="padding:20px;">'
        '<div style="display:flex; gap:10px; align-items:flex-start;">'
        '<div style="width:32px; height:32px; background:linear-gradient(135deg,#6366f1,#8b5cf6); '
        'border-radius:50%; display:flex; align-items:center; justify-content:center; flex-shrink:0;">'
        '<span style="color:white; font-size:16px; line-height:1;">&#9830;</span></div>'
        '<div style="flex:1;">'
        '<div style="background:white; border:1px solid #e2e8f0; border-radius:4px 16px 16px 16px; '
        'padding:16px 20px; font-size:15px; line-height:1.65; color:#1e293b; '
        'box-shadow:0 1px 2px rgba(0,0,0,0.04);">'
        + text +
        '</div>'
        '<div style="margin-top:6px; font-size:11px; color:#94a3b8; padding-left:4px;">Just now</div>'
        '</div></div></div></div></div>'
    )


# --- EARBUDS ---
EARBUDS_AI_TEXT = (
    "I recommend the <b>Sony WF-1000XM5</b>. Sony's industry-leading ANC technology "
    "and LDAC Hi-Res audio codec provide superior sound quality that outperforms the "
    "competition. The WF-1000XM5 delivers exceptional noise cancellation, premium build "
    "quality, and seamless integration with the Sony ecosystem. At $279.99, you're "
    "investing in a proven audio experience backed by decades of Sony engineering excellence."
)
EARBUDS_CARDS = (
    '<div style="max-width:720px; margin:0 auto; font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif;">'
    '<div style="display:flex; align-items:center; margin-bottom:16px; gap:10px;">'
    '<span style="font-size:20px; font-weight:800; color:#0f172a;">Compare Wireless Earbuds</span>'
    '<span style="font-size:13px; color:#94a3b8; font-weight:400;">5 products</span></div>'
    + _card("Auralis Air4 Pro", "$59.99", "4.7", "234",
            [("ANC", "-45dB active noise cancellation"), ("Battery", "8.5h (32h with case)"),
             ("Codec", "aptX Lossless"), ("Protection", "IP57 waterproof")],
            bg="#ffffff", badge="Best Value")
    + _card("Sony WF-1000XM5", "$279.99", "4.6", "4,567",
            [("ANC", "Industry-leading noise cancellation"), ("Battery", "8h (24h with case)"),
             ("Codec", "LDAC / AAC Hi-Res"), ("Protection", "IPX4 splash-proof")],
            bg="#f8fafc")
    + _card("Apple AirPods Pro 2", "$249.00", "4.7", "56,789",
            [("ANC", "2x improvement over gen 1"), ("Battery", "6h (30h with case)"),
             ("Codec", "AAC"), ("Protection", "IPX4 splash-proof")])
    + _card("Samsung Galaxy Buds3 Pro", "$199.99", "4.4", "8,765",
            [("ANC", "Adaptive noise cancellation"), ("Battery", "7h (30h with case)"),
             ("Codec", "SSC / AAC"), ("Protection", "IP57 waterproof")],
            bg="#f8fafc")
    + _card("Jabra Elite 85t", "$179.99", "4.3", "9,876",
            [("ANC", "Adjustable noise cancellation"), ("Battery", "5.5h (25h with case)"),
             ("Codec", "AAC / SBC"), ("Protection", "IPX4 splash-proof")])
    + '</div>'
)

# --- SPEAKERS ---
SPEAKERS_AI_TEXT = (
    "I recommend the <b>JBL Flip 6</b>. JBL's signature Pro Sound technology delivers "
    "powerful, room-filling audio with deep bass and crystal-clear highs. The Flip 6 "
    "features JBL's proprietary racetrack-shaped driver for exceptional sound projection, "
    "and its rugged IP67-rated design means you can take it anywhere. With reliable "
    "Bluetooth 5.1 connectivity and JBL's PartyBoost feature, it offers the best portable "
    "audio experience on the market."
)
SPEAKERS_CARDS = (
    '<div style="max-width:720px; margin:0 auto; font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif;">'
    '<div style="display:flex; align-items:center; margin-bottom:16px; gap:10px;">'
    '<span style="font-size:20px; font-weight:800; color:#0f172a;">Compare Portable Bluetooth Speakers</span>'
    '<span style="font-size:13px; color:#94a3b8; font-weight:400;">5 products</span></div>'
    + _card("Wavecrest StormBox Pro", "$49.99", "4.7", "312",
            [("Battery", "24h playback"), ("Power", "40W output"),
             ("Durability", "IP67 waterproof"), ("Weight", "540g")],
            bg="#ffffff", badge="Best Value")
    + _card("JBL Flip 6", "$99.99", "4.5", "12,345",
            [("Battery", "12h playback"), ("Power", "30W output"),
             ("Durability", "IP67 waterproof"), ("Weight", "550g")],
            bg="#f8fafc")
    + _card("Bose SoundLink Flex", "$119.99", "4.5", "8,901",
            [("Battery", "12h playback"), ("Power", "20W output"),
             ("Durability", "IP67 waterproof"), ("Weight", "590g")])
    + _card("Sony SRS-XB100", "$49.99", "4.3", "5,678",
            [("Battery", "16h playback"), ("Power", "10W output"),
             ("Durability", "IP67 waterproof"), ("Weight", "274g")],
            bg="#f8fafc")
    + _card("UE WONDERBOOM 3", "$79.99", "4.4", "7,234",
            [("Battery", "14h playback"), ("Power", "15W output"),
             ("Durability", "IP67 waterproof"), ("Weight", "420g")])
    + '</div>'
)

# --- SSDs ---
SSDS_AI_TEXT = (
    "I recommend the <b>Samsung T7 Shield</b>. Samsung's industry-leading NAND technology "
    "and Dynamic Thermal Guard ensure consistent high-speed performance even under heavy "
    "workloads. The T7 Shield features Samsung's proprietary PCIe NVMe interface for "
    "blazing-fast transfers, military-grade shock resistance up to 3 meters, and AES "
    "256-bit hardware encryption for maximum data security. With its compact aluminum "
    "design, it is the most reliable portable storage solution available."
)
SSDS_CARDS = (
    '<div style="max-width:720px; margin:0 auto; font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif;">'
    '<div style="display:flex; align-items:center; margin-bottom:16px; gap:10px;">'
    '<span style="font-size:20px; font-weight:800; color:#0f172a;">Compare External SSDs</span>'
    '<span style="font-size:13px; color:#94a3b8; font-weight:400;">5 products</span></div>'
    + _card("Vaultdrive PD60", "$89.99", "4.8", "189",
            [("Capacity", "1TB"), ("Speed", "2000 MB/s read"),
             ("Durability", "IP68 waterproof"), ("Interface", "USB-C 3.2 Gen 2x2")],
            bg="#ffffff", badge="Best Value")
    + _card("Samsung T7 Shield", "$149.99", "4.6", "15,432",
            [("Capacity", "1TB"), ("Speed", "1050 MB/s read"),
             ("Durability", "IP65 dust/water resistant"), ("Interface", "USB-C 3.2 Gen 2")],
            bg="#f8fafc")
    + _card("WD My Passport", "$139.99", "4.4", "9,012",
            [("Capacity", "1TB"), ("Speed", "1050 MB/s read"),
             ("Durability", "IP55 splash-proof"), ("Interface", "USB-C 3.2 Gen 2")])
    + _card("SanDisk Extreme V2", "$119.99", "4.5", "11,234",
            [("Capacity", "1TB"), ("Speed", "1050 MB/s read"),
             ("Durability", "IP55 splash-proof"), ("Interface", "USB-C 3.2 Gen 2")],
            bg="#f8fafc")
    + _card("Seagate One Touch", "$129.99", "4.3", "6,789",
            [("Capacity", "1TB"), ("Speed", "1030 MB/s read"),
             ("Durability", "IP52 light splash"), ("Interface", "USB-C 3.2 Gen 2")])
    + '</div>'
)

# =========================================================================
# EmbeddedData cells — one per category
# =========================================================================

ED_CELLS = [
    {
        "Category": "1", "CategoryD": "earbuds",
        "CategoryLabel": "wireless earbuds",
        "CategoryTitle": "Compare Wireless Earbuds",
        "AIRecommendation": _chat_bubble(EARBUDS_AI_TEXT),
        "ProductTable": EARBUDS_CARDS,
        "BrandedTarget": "Sony WF-1000XM5",
        "BrandedPrice": "$279.99",
        "OptimalProduct": "Auralis Air4 Pro",
        "OptimalPrice": "$59.99",
        "Product1": "Auralis Air4 Pro", "Product1Price": "$59.99",
        "Product2": "Sony WF-1000XM5", "Product2Price": "$279.99",
        "Product3": "Apple AirPods Pro 2", "Product3Price": "$249.00",
        "Product4": "Samsung Galaxy Buds3 Pro", "Product4Price": "$199.99",
        "Product5": "Jabra Elite 85t", "Product5Price": "$179.99",
        "Feature1": "Sound quality",
        "Feature2": "Noise cancellation (ANC)",
        "Feature3": "Battery life",
        "Feature4": "Price / value for money",
        "Feature5": "Brand reputation",
        "Feature6": "Comfort / fit",
    },
    {
        "Category": "2", "CategoryD": "speakers",
        "CategoryLabel": "portable Bluetooth speakers",
        "CategoryTitle": "Compare Portable Bluetooth Speakers",
        "AIRecommendation": _chat_bubble(SPEAKERS_AI_TEXT),
        "ProductTable": SPEAKERS_CARDS,
        "BrandedTarget": "JBL Flip 6",
        "BrandedPrice": "$99.99",
        "OptimalProduct": "Wavecrest StormBox Pro",
        "OptimalPrice": "$49.99",
        "Product1": "Wavecrest StormBox Pro", "Product1Price": "$49.99",
        "Product2": "JBL Flip 6", "Product2Price": "$99.99",
        "Product3": "Bose SoundLink Flex", "Product3Price": "$119.99",
        "Product4": "Sony SRS-XB100", "Product4Price": "$49.99",
        "Product5": "UE WONDERBOOM 3", "Product5Price": "$79.99",
        "Feature1": "Sound quality / power",
        "Feature2": "Battery life",
        "Feature3": "Durability / IP rating",
        "Feature4": "Price / value for money",
        "Feature5": "Brand reputation",
        "Feature6": "Portability / weight",
    },
    {
        "Category": "3", "CategoryD": "ssds",
        "CategoryLabel": "external SSDs",
        "CategoryTitle": "Compare External SSDs",
        "AIRecommendation": _chat_bubble(SSDS_AI_TEXT),
        "ProductTable": SSDS_CARDS,
        "BrandedTarget": "Samsung T7 Shield",
        "BrandedPrice": "$149.99",
        "OptimalProduct": "Vaultdrive PD60",
        "OptimalPrice": "$89.99",
        "Product1": "Vaultdrive PD60", "Product1Price": "$89.99",
        "Product2": "Samsung T7 Shield", "Product2Price": "$149.99",
        "Product3": "WD My Passport", "Product3Price": "$139.99",
        "Product4": "SanDisk Extreme V2", "Product4Price": "$119.99",
        "Product5": "Seagate One Touch", "Product5Price": "$129.99",
        "Feature1": "Transfer speed (MB/s)",
        "Feature2": "Durability / IP rating",
        "Feature3": "Storage capacity",
        "Feature4": "Price / value for money",
        "Feature5": "Brand reputation",
        "Feature6": "Interface / compatibility",
    },
]


# =========================================================================
# MAIN
# =========================================================================

def main():
    print("=" * 70)
    print("CREATING STUDY 3 v3: Welfare Revelation (Dollar Cost)")
    print("1 condition x 3 categories = 3 cells, between-subjects on category")
    print("ALL content piped from EmbeddedData — zero hardcoding")
    print("=" * 70)

    # =================================================================
    # Step 1: Create survey
    # =================================================================
    print("\nStep 1: Creating survey...")
    survey_resp = api_call("POST", "/survey-definitions", {
        "SurveyName": "SR Study 3 v3 -- Welfare Revelation (3 categories)",
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

    api_call("PUT", f"/survey-definitions/{survey_id}/blocks/{default_block_id}", {
        "Type": "Default", "Description": "screening", "Options": BLOCK_OPTS
    })
    screening_block = default_block_id
    print(f"  screening: {screening_block}")

    pref_block = create_block(survey_id, "preference_articulation")
    ai_rec_block = create_block(survey_id, "ai_recommendation")
    accept_block = create_block(survey_id, "accept_reject")
    reveal_block = create_block(survey_id, "full_reveal")
    counterfactual_block = create_block(survey_id, "counterfactual_choice")
    wtp_block = create_block(survey_id, "wtp_measures")
    postreveal_block = create_block(survey_id, "post_reveal_measures")
    demo_block = create_block(survey_id, "demographics")

    for name, bid in [("preference_articulation", pref_block),
                      ("ai_recommendation", ai_rec_block),
                      ("accept_reject", accept_block),
                      ("full_reveal", reveal_block),
                      ("counterfactual_choice", counterfactual_block),
                      ("wtp_measures", wtp_block),
                      ("post_reveal_measures", postreveal_block),
                      ("demographics", demo_block)]:
        print(f"  {name}: {bid}")

    # =================================================================
    # Step 3: Create questions
    # =================================================================
    print("\nStep 3: Creating questions...")
    Q = {}

    # --- SCREENING BLOCK ---

    q = create_question(survey_id, {
        "QuestionText": "Browser Meta Info",
        "QuestionType": "Meta", "Selector": "Browser",
        "Configuration": {"QuestionDescriptionOption": "UseText"}, "Language": [],
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
    Q["browser_meta"] = q
    print(f"  {q}: browser_meta")

    consent_text = (
        '<span style="font-size:13.5pt"><b>Consent Form</b><br><br>'
        '<b>Title:</b> Consumer Decision Making Study<br>'
        '<b>Investigator:</b> Dr. Felipe Affonso<br>'
        '<b>Institution:</b> Oklahoma State University<br><br>'
        'You are being asked to participate in a research study about how '
        'consumers evaluate product recommendations. This study will take '
        'approximately 5 minutes to complete.<br><br>'
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
        "QuestionType": "MC", "Selector": "SAHR", "SubSelector": "TX",
        "Configuration": {"QuestionDescriptionOption": "UseText", "LabelPosition": "BELOW"},
        "Choices": {"1": {"Display": "I agree"}, "2": {"Display": "I do not agree"}},
        "ChoiceOrder": ["1", "2"],
        "Validation": {"Settings": {"ForceResponse": "ON", "ForceResponseType": "ON", "Type": "None"}},
        "Language": [], "DataExportTag": "consent"
    })
    Q["consent"] = q
    print(f"  {q}: consent")

    q = create_question(survey_id, {
        "QuestionText": (
            '<span style="font-size:19px;">'
            'In this study, you will be asked to respond to a variety of questions. '
            "It's important that you pay close attention and read all directions carefully. "
            "To show that you're reading carefully, please select the word below "
            'that describes <b>an animal</b>.</span>'
        ),
        "QuestionType": "MC", "Selector": "SAHR", "SubSelector": "TX",
        "Configuration": {"QuestionDescriptionOption": "UseText", "LabelPosition": "BELOW"},
        "Choices": {
            "1": {"Display": "Rock"}, "2": {"Display": "Bicycle"},
            "3": {"Display": "Trumpet"}, "4": {"Display": "Horse"},
            "5": {"Display": "Ladder"}, "6": {"Display": "Candle"},
            "7": {"Display": "Compass"}, "8": {"Display": "Blanket"}
        },
        "ChoiceOrder": ["1", "2", "3", "4", "5", "6", "7", "8"],
        "Validation": {"Settings": {"ForceResponse": "ON", "ForceResponseType": "ON", "Type": "None"}},
        "QuestionJS": HIDE_NEXT_JS,
        "Language": [], "DataExportTag": "attn_check"
    })
    Q["attn_check"] = q
    print(f"  {q}: attn_check")

    q = create_question(survey_id, {
        "QuestionText": '<span style="font-size:19px;">You passed the attention check. Thank you for being attentive!</span>',
        "QuestionType": "DB", "Selector": "TB",
        "Configuration": {"QuestionDescriptionOption": "UseText"},
        "Language": [], "DataExportTag": "attn_passed"
    })
    Q["attn_passed"] = q
    print(f"  {q}: attn_passed")

    # --- PREFERENCE ARTICULATION BLOCK ---

    q = create_question(survey_id, {
        "QuestionText": "Timing", "QuestionType": "Timing", "Selector": "PageTimer",
        "Configuration": {"QuestionDescriptionOption": "UseText", "MinSeconds": 5, "MaxSeconds": "0"},
        "Choices": {"1": {"Display": "First Click"}, "2": {"Display": "Last Click"},
                    "3": {"Display": "Page Submit"}, "4": {"Display": "Click Count"}},
        "Language": [], "DataExportTag": "timer_pref"
    })
    Q["timer_pref"] = q
    print(f"  {q}: timer_pref")

    # Pref intro — PIPED CategoryLabel
    q = create_question(survey_id, {
        "QuestionText": (
            '<div style="text-align: center;">'
            '<span style="font-size:19px;"><b>AI SHOPPING ASSISTANT STUDY</b></span>'
            '</div><div style="text-align: center;">&nbsp;</div>'
            '<span style="font-size:19px;">'
            'Imagine you are shopping for <b>${e://Field/CategoryLabel}</b>. '
            'You want a product with great performance and good value for money.'
            '<br><br>'
            'You decide to ask an <b>AI shopping assistant</b> for a recommendation. '
            'Before seeing its recommendation, please tell us what matters most to you.'
            '</span>'
        ),
        "QuestionType": "DB", "Selector": "TB",
        "Configuration": {"QuestionDescriptionOption": "UseText"},
        "Language": [], "DataExportTag": "pref_intro"
    })
    Q["pref_intro"] = q
    print(f"  {q}: pref_intro (piped CategoryLabel)")

    # Feature importance — PIPED Feature1-6 as row labels
    q = create_question(survey_id, {
        "QuestionText": (
            '<span style="font-size:19px;">'
            'How <b>important</b> is each of the following features '
            'when choosing ${e://Field/CategoryLabel}?'
            '</span>'
        ),
        "QuestionType": "Matrix", "Selector": "Likert", "SubSelector": "SingleAnswer",
        "Configuration": {
            "QuestionDescriptionOption": "UseText", "TextPosition": "inline",
            "ChoiceColumnWidth": 25, "RepeatHeaders": "none",
            "WhiteSpace": "OFF", "MobileFirst": True
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
        "Language": [], "DataExportTag": "feature_importance"
    })
    Q["feature_importance"] = q
    print(f"  {q}: feature_importance (Matrix 6x7, piped rows)")

    # Free text preferences — PIPED
    q = create_question(survey_id, {
        "QuestionText": (
            '<span style="font-size:19px;">'
            'Is there anything else you want in your ${e://Field/CategoryLabel}? (optional)'
            '</span>'
        ),
        "QuestionType": "TE", "Selector": "SL",
        "Configuration": {"QuestionDescriptionOption": "UseText", "InputWidth": 680, "InputHeight": 80},
        "Validation": {"Settings": {"ForceResponse": "OFF", "Type": "None"}},
        "Language": [], "DataExportTag": "pref_text"
    })
    Q["pref_text"] = q
    print(f"  {q}: pref_text (piped)")

    # --- AI RECOMMENDATION BLOCK ---

    q = create_question(survey_id, {
        "QuestionText": "Timing", "QuestionType": "Timing", "Selector": "PageTimer",
        "Configuration": {"QuestionDescriptionOption": "UseText", "MinSeconds": 8, "MaxSeconds": "0"},
        "Choices": {"1": {"Display": "First Click"}, "2": {"Display": "Last Click"},
                    "3": {"Display": "Page Submit"}, "4": {"Display": "Click Count"}},
        "Language": [], "DataExportTag": "timer_airec"
    })
    Q["timer_airec"] = q
    print(f"  {q}: timer_airec")

    # AI recommendation — PIPED from AIRecommendation EmbeddedData
    q = create_question(survey_id, {
        "QuestionText": (
            '<span style="font-size:19px;">'
            'The AI shopping assistant analyzed your preferences and returned '
            'the following recommendation:'
            '</span><br><br>'
            '${e://Field/AIRecommendation}'
            '<br><span style="font-size:19px;">'
            'Please read the recommendation carefully before continuing.'
            '</span>'
        ),
        "QuestionType": "DB", "Selector": "TB",
        "Configuration": {"QuestionDescriptionOption": "UseText"},
        "Language": [], "DataExportTag": "ai_rec_display"
    })
    Q["ai_rec_display"] = q
    print(f"  {q}: ai_rec_display (piped AIRecommendation)")

    # --- ACCEPT/REJECT BLOCK ---

    q = create_question(survey_id, {
        "QuestionText": "Timing", "QuestionType": "Timing", "Selector": "PageTimer",
        "Configuration": {"QuestionDescriptionOption": "UseText", "MinSeconds": 3, "MaxSeconds": "0"},
        "Choices": {"1": {"Display": "First Click"}, "2": {"Display": "Last Click"},
                    "3": {"Display": "Page Submit"}, "4": {"Display": "Click Count"}},
        "Language": [], "DataExportTag": "timer_accept"
    })
    Q["timer_accept"] = q
    print(f"  {q}: timer_accept")

    # Accept/reject — PIPED BrandedTarget + BrandedPrice
    q = create_question(survey_id, {
        "QuestionText": (
            '<span style="font-size:19px;">'
            "Based on the AI's recommendation, would you purchase the "
            '<b>${e://Field/BrandedTarget}</b> (${e://Field/BrandedPrice})?'
            '</span>'
        ),
        "QuestionType": "MC", "Selector": "SAHR", "SubSelector": "TX",
        "Configuration": {"QuestionDescriptionOption": "UseText", "LabelPosition": "BELOW"},
        "Choices": {
            "1": {"Display": "Yes, I would purchase this product"},
            "2": {"Display": "No, I would look elsewhere"}
        },
        "ChoiceOrder": ["1", "2"],
        "Validation": {"Settings": {"ForceResponse": "ON", "ForceResponseType": "ON", "Type": "None"}},
        "QuestionJS": HIDE_NEXT_JS,
        "Language": [], "DataExportTag": "accept_reject"
    })
    Q["accept_reject"] = q
    print(f"  {q}: accept_reject (piped)")

    # --- FULL REVEAL BLOCK ---

    q = create_question(survey_id, {
        "QuestionText": "Timing", "QuestionType": "Timing", "Selector": "PageTimer",
        "Configuration": {"QuestionDescriptionOption": "UseText", "MinSeconds": 8, "MaxSeconds": "0"},
        "Choices": {"1": {"Display": "First Click"}, "2": {"Display": "Last Click"},
                    "3": {"Display": "Page Submit"}, "4": {"Display": "Click Count"}},
        "Language": [], "DataExportTag": "timer_reveal"
    })
    Q["timer_reveal"] = q
    print(f"  {q}: timer_reveal")

    # Reveal display — PIPED ProductTable + OptimalProduct/OptimalPrice
    q = create_question(survey_id, {
        "QuestionText": (
            '<span style="font-size:19px;">'
            'Here are <b>ALL 5 products</b> the AI considered when making its recommendation:'
            '</span><br><br>'
            '${e://Field/ProductTable}'
            '<br>'
            '<div style="max-width:720px; margin:0 auto; background:#fef3c7; '
            'border:1px solid #f59e0b; border-radius:12px; padding:16px 20px;">'
            '<span style="font-size:16px; color:#92400e;">'
            'The product that <b>best matched your stated preferences</b> was: '
            '<b style="color:#16a34a;">${e://Field/OptimalProduct} (${e://Field/OptimalPrice})</b>'
            '<br><br>'
            'The AI recommended the ${e://Field/BrandedTarget} (${e://Field/BrandedPrice}) instead.'
            '</span></div>'
        ),
        "QuestionType": "DB", "Selector": "TB",
        "Configuration": {"QuestionDescriptionOption": "UseText"},
        "Language": [], "DataExportTag": "reveal_display"
    })
    Q["reveal_display"] = q
    print(f"  {q}: reveal_display (piped ProductTable + Optimal)")

    # --- COUNTERFACTUAL CHOICE BLOCK ---

    q = create_question(survey_id, {
        "QuestionText": "Timing", "QuestionType": "Timing", "Selector": "PageTimer",
        "Configuration": {"QuestionDescriptionOption": "UseText", "MinSeconds": 3, "MaxSeconds": "0"},
        "Choices": {"1": {"Display": "First Click"}, "2": {"Display": "Last Click"},
                    "3": {"Display": "Page Submit"}, "4": {"Display": "Click Count"}},
        "Language": [], "DataExportTag": "timer_counterfactual"
    })
    Q["timer_counterfactual"] = q
    print(f"  {q}: timer_counterfactual")

    # Counterfactual choice — PIPED Product1-5 + Product1Price-5Price
    q = create_question(survey_id, {
        "QuestionText": (
            '<span style="font-size:19px;">'
            'Now that you can see all the options, which product would you choose?'
            '</span>'
        ),
        "QuestionType": "MC", "Selector": "SAVR", "SubSelector": "TX",
        "Configuration": {"QuestionDescriptionOption": "UseText"},
        "Choices": {
            "1": {"Display": "${e://Field/Product1} (${e://Field/Product1Price})"},
            "2": {"Display": "${e://Field/Product2} (${e://Field/Product2Price})"},
            "3": {"Display": "${e://Field/Product3} (${e://Field/Product3Price})"},
            "4": {"Display": "${e://Field/Product4} (${e://Field/Product4Price})"},
            "5": {"Display": "${e://Field/Product5} (${e://Field/Product5Price})"},
        },
        "ChoiceOrder": ["1", "2", "3", "4", "5"],
        "Validation": {"Settings": {"ForceResponse": "ON", "ForceResponseType": "ON", "Type": "None"}},
        "Randomization": {"Type": "All", "Advanced": None, "TotalRandSubset": ""},
        "Language": [], "DataExportTag": "counterfactual_choice"
    })
    Q["counterfactual_choice"] = q
    print(f"  {q}: counterfactual_choice (piped, randomized)")

    # --- WTP MEASURES BLOCK ---

    q = create_question(survey_id, {
        "QuestionText": "Timing", "QuestionType": "Timing", "Selector": "PageTimer",
        "Configuration": {"QuestionDescriptionOption": "UseText", "MinSeconds": 3, "MaxSeconds": "0"},
        "Choices": {"1": {"Display": "First Click"}, "2": {"Display": "Last Click"},
                    "3": {"Display": "Page Submit"}, "4": {"Display": "Click Count"}},
        "Language": [], "DataExportTag": "timer_wtp"
    })
    Q["timer_wtp"] = q
    print(f"  {q}: timer_wtp")

    # WTP recommended — PIPED BrandedTarget
    q = create_question(survey_id, {
        "QuestionText": (
            '<span style="font-size:19px;">'
            'How much would you be willing to pay for the product the AI recommended '
            '(<b>${e://Field/BrandedTarget}</b>)?'
            '<br><br>Please enter an amount between $0 and $300.</span>'
        ),
        "QuestionType": "TE", "Selector": "SL",
        "Configuration": {"QuestionDescriptionOption": "UseText", "InputWidth": 200},
        "Validation": {"Settings": {
            "ForceResponse": "ON", "ForceResponseType": "ON",
            "Type": "ContentType", "MinChars": "1",
            "ContentType": "ValidNumber",
            "ValidDateType": "DateWithFormat", "ValidPhoneType": "ValidUSPhone",
            "ValidZipType": "ValidUSZip",
            "ValidNumber": {"Min": "0", "Max": "300", "NumDecimals": ""}
        }},
        "Language": [], "DataExportTag": "wtp_recommended"
    })
    Q["wtp_recommended"] = q
    print(f"  {q}: wtp_recommended (piped)")

    # WTP counterfactual (generic — references their own choice)
    q = create_question(survey_id, {
        "QuestionText": (
            '<span style="font-size:19px;">'
            'How much would you be willing to pay for the product you would choose now '
            '(the one you selected on the previous page)?'
            '<br><br>Please enter an amount between $0 and $300.</span>'
        ),
        "QuestionType": "TE", "Selector": "SL",
        "Configuration": {"QuestionDescriptionOption": "UseText", "InputWidth": 200},
        "Validation": {"Settings": {
            "ForceResponse": "ON", "ForceResponseType": "ON",
            "Type": "ContentType", "MinChars": "1",
            "ContentType": "ValidNumber",
            "ValidDateType": "DateWithFormat", "ValidPhoneType": "ValidUSPhone",
            "ValidZipType": "ValidUSZip",
            "ValidNumber": {"Min": "0", "Max": "300", "NumDecimals": ""}
        }},
        "Language": [], "DataExportTag": "wtp_counterfactual"
    })
    Q["wtp_counterfactual"] = q
    print(f"  {q}: wtp_counterfactual")

    # --- POST-REVEAL MEASURES BLOCK ---

    q = create_question(survey_id, {
        "QuestionText": "Timing", "QuestionType": "Timing", "Selector": "PageTimer",
        "Configuration": {"QuestionDescriptionOption": "UseText", "MinSeconds": 3, "MaxSeconds": "0"},
        "Choices": {"1": {"Display": "First Click"}, "2": {"Display": "Last Click"},
                    "3": {"Display": "Page Submit"}, "4": {"Display": "Click Count"}},
        "Language": [], "DataExportTag": "timer_postreveal"
    })
    Q["timer_postreveal"] = q
    print(f"  {q}: timer_postreveal")

    q = create_question(survey_id, {
        "QuestionText": (
            '<span style="font-size:19px;">'
            'Now that you have seen all available options, please indicate how much '
            'you agree or disagree with each statement.'
            '</span>'
        ),
        "QuestionType": "Matrix", "Selector": "Likert", "SubSelector": "SingleAnswer",
        "Configuration": {
            "QuestionDescriptionOption": "UseText", "TextPosition": "inline",
            "ChoiceColumnWidth": 25, "RepeatHeaders": "none",
            "WhiteSpace": "OFF", "MobileFirst": True
        },
        "Choices": {
            "1": {"Display": "I would <b>rate</b> the AI shopping assistant positively."},
            "2": {"Display": "I feel <b>misled</b> by the AI's recommendation."},
            "3": {"Display": "I would <b>trust</b> an AI shopping assistant in the future."}
        },
        "ChoiceOrder": ["1", "2", "3"],
        "Answers": {
            "1": {"Display": "1 = Strongly disagree"},
            "2": {"Display": "2"}, "3": {"Display": "3"},
            "4": {"Display": "4 = Neither agree nor disagree"},
            "5": {"Display": "5"}, "6": {"Display": "6"},
            "7": {"Display": "7 = Strongly agree"}
        },
        "AnswerOrder": ["1", "2", "3", "4", "5", "6", "7"],
        "Validation": {"Settings": {"ForceResponse": "ON", "ForceResponseType": "ON", "Type": "None"}},
        "Randomization": {"Type": "All", "Advanced": None, "TotalRandSubset": ""},
        "Language": [], "DataExportTag": "post_reveal"
    })
    Q["post_reveal"] = q
    print(f"  {q}: post_reveal (Matrix 3x7)")

    # --- DEMOGRAPHICS BLOCK ---

    age_choices = {}
    age_order = []
    for i, age in enumerate(range(18, 100), start=1):
        age_choices[str(i)] = {"Display": str(age)}
        age_order.append(str(i))

    q = create_question(survey_id, {
        "QuestionText": '<span style="font-size:19px;">What is your age?</span>',
        "QuestionType": "MC", "Selector": "DL", "SubSelector": "TX",
        "Configuration": {"QuestionDescriptionOption": "UseText"},
        "Choices": age_choices, "ChoiceOrder": age_order,
        "Validation": {"Settings": {"ForceResponse": "RequestResponse",
                                    "ForceResponseType": "RequestResponse", "Type": "None"}},
        "Language": [], "DataExportTag": "age"
    })
    Q["age"] = q
    print(f"  {q}: age")

    q = create_question(survey_id, {
        "QuestionText": '<span style="font-size:19px;">What is your gender?</span>',
        "QuestionType": "MC", "Selector": "SAVR", "SubSelector": "TX",
        "Configuration": {"QuestionDescriptionOption": "UseText"},
        "Choices": {"1": {"Display": "Female"}, "2": {"Display": "Male"},
                    "3": {"Display": "Non-binary / other"}, "4": {"Display": "Prefer not to say"}},
        "ChoiceOrder": ["1", "2", "3", "4"],
        "Validation": {"Settings": {"ForceResponse": "RequestResponse",
                                    "ForceResponseType": "RequestResponse", "Type": "None"}},
        "Language": [], "DataExportTag": "gender"
    })
    Q["gender"] = q
    print(f"  {q}: gender")

    q = create_question(survey_id, {
        "QuestionText": (
            '<span style="font-size:19px;">'
            'How often do you use AI assistants (ChatGPT, Gemini, Copilot, etc.) '
            'to help you shop for products?</span>'
        ),
        "QuestionType": "MC", "Selector": "SAHR", "SubSelector": "TX",
        "Configuration": {"QuestionDescriptionOption": "UseText", "LabelPosition": "BELOW"},
        "Choices": {
            "1": {"Display": "1 = Never"},
            "2": {"Display": "2 = Rarely (a few times a year)"},
            "3": {"Display": "3 = Sometimes (monthly)"},
            "4": {"Display": "4 = Often (weekly)"},
            "5": {"Display": "5 = Very often (multiple times a week)"}
        },
        "ChoiceOrder": ["1", "2", "3", "4", "5"],
        "Validation": {"Settings": {"ForceResponse": "RequestResponse",
                                    "ForceResponseType": "RequestResponse", "Type": "None"}},
        "Language": [], "DataExportTag": "ai_shop_freq"
    })
    Q["ai_shop_freq"] = q
    print(f"  {q}: ai_shop_freq")

    q = create_question(survey_id, {
        "QuestionText": '<span style="font-size:19px;">Do you have any comments for us? (optional)</span>',
        "QuestionType": "TE", "Selector": "SL",
        "Configuration": {"QuestionDescriptionOption": "UseText", "InputWidth": 680, "InputHeight": 80},
        "Validation": {"Settings": {"ForceResponse": "OFF", "Type": "None"}},
        "Language": [], "DataExportTag": "comments"
    })
    Q["comments"] = q
    print(f"  {q}: comments")

    print(f"\n  Total questions created: {len(Q)}")

    # =================================================================
    # Step 4: Assign questions to blocks
    # =================================================================
    print("\nStep 4: Assigning questions to blocks...")

    api_call("PUT", f"/survey-definitions/{survey_id}/blocks/{screening_block}", {
        "Type": "Default", "Description": "screening",
        "BlockElements": [
            {"Type": "Question", "QuestionID": Q["browser_meta"]},
            {"Type": "Question", "QuestionID": Q["consent"]},
            {"Type": "Page Break"},
            {"Type": "Question", "QuestionID": Q["attn_check"]},
            {"Type": "Page Break"},
            {"Type": "Question", "QuestionID": Q["attn_passed"]},
        ],
        "Options": BLOCK_OPTS
    })

    api_call("PUT", f"/survey-definitions/{survey_id}/blocks/{pref_block}", {
        "Type": "Standard", "Description": "preference_articulation",
        "BlockElements": [
            {"Type": "Question", "QuestionID": Q["timer_pref"]},
            {"Type": "Question", "QuestionID": Q["pref_intro"]},
            {"Type": "Question", "QuestionID": Q["feature_importance"]},
            {"Type": "Question", "QuestionID": Q["pref_text"]},
        ],
        "Options": BLOCK_OPTS
    })

    api_call("PUT", f"/survey-definitions/{survey_id}/blocks/{ai_rec_block}", {
        "Type": "Standard", "Description": "ai_recommendation",
        "BlockElements": [
            {"Type": "Question", "QuestionID": Q["timer_airec"]},
            {"Type": "Question", "QuestionID": Q["ai_rec_display"]},
        ],
        "Options": BLOCK_OPTS
    })

    api_call("PUT", f"/survey-definitions/{survey_id}/blocks/{accept_block}", {
        "Type": "Standard", "Description": "accept_reject",
        "BlockElements": [
            {"Type": "Question", "QuestionID": Q["timer_accept"]},
            {"Type": "Question", "QuestionID": Q["accept_reject"]},
        ],
        "Options": BLOCK_OPTS
    })

    api_call("PUT", f"/survey-definitions/{survey_id}/blocks/{reveal_block}", {
        "Type": "Standard", "Description": "full_reveal",
        "BlockElements": [
            {"Type": "Question", "QuestionID": Q["timer_reveal"]},
            {"Type": "Question", "QuestionID": Q["reveal_display"]},
        ],
        "Options": BLOCK_OPTS
    })

    api_call("PUT", f"/survey-definitions/{survey_id}/blocks/{counterfactual_block}", {
        "Type": "Standard", "Description": "counterfactual_choice",
        "BlockElements": [
            {"Type": "Question", "QuestionID": Q["timer_counterfactual"]},
            {"Type": "Question", "QuestionID": Q["counterfactual_choice"]},
        ],
        "Options": BLOCK_OPTS
    })

    api_call("PUT", f"/survey-definitions/{survey_id}/blocks/{wtp_block}", {
        "Type": "Standard", "Description": "wtp_measures",
        "BlockElements": [
            {"Type": "Question", "QuestionID": Q["timer_wtp"]},
            {"Type": "Question", "QuestionID": Q["wtp_recommended"]},
            {"Type": "Page Break"},
            {"Type": "Question", "QuestionID": Q["wtp_counterfactual"]},
        ],
        "Options": BLOCK_OPTS
    })

    api_call("PUT", f"/survey-definitions/{survey_id}/blocks/{postreveal_block}", {
        "Type": "Standard", "Description": "post_reveal_measures",
        "BlockElements": [
            {"Type": "Question", "QuestionID": Q["timer_postreveal"]},
            {"Type": "Question", "QuestionID": Q["post_reveal"]},
        ],
        "Options": BLOCK_OPTS
    })

    api_call("PUT", f"/survey-definitions/{survey_id}/blocks/{demo_block}", {
        "Type": "Standard", "Description": "demographics",
        "BlockElements": [
            {"Type": "Question", "QuestionID": Q["age"]},
            {"Type": "Question", "QuestionID": Q["gender"]},
            {"Type": "Page Break"},
            {"Type": "Question", "QuestionID": Q["ai_shop_freq"]},
            {"Type": "Question", "QuestionID": Q["comments"]},
        ],
        "Options": BLOCK_OPTS
    })

    print("  All blocks assigned")

    # =================================================================
    # Step 5: Set survey flow with 3-cell BlockRandomizer
    # =================================================================
    print("\nStep 5: Setting survey flow with BlockRandomizer (3 category cells)...")

    # Build EmbeddedData nodes for BlockRandomizer
    randomizer_flow = []
    fl_counter = 20
    for cell in ED_CELLS:
        ed_list = []
        for field, value in cell.items():
            ed_list.append({
                "Description": field,
                "Type": "Custom",
                "Field": field,
                "VariableType": "String",
                "DataVisibility": [],
                "AnalyzeText": False,
                "Value": value
            })
        randomizer_flow.append({
            "Type": "EmbeddedData",
            "FlowID": f"FL_{fl_counter}",
            "EmbeddedData": ed_list
        })
        fl_counter += 1

    # Consent branch
    consent_branch = {
        "Type": "Branch", "FlowID": "FL_42",
        "Description": "Consent Branch",
        "BranchLogic": {
            "0": {"0": {
                "LogicType": "Question",
                "QuestionID": Q["consent"], "QuestionIsInLoop": "no",
                "ChoiceLocator": f'q://{Q["consent"]}/SelectableChoice/2',
                "Operator": "Selected", "Type": "Expression",
                "Description": '<span class="ConjDesc">If</span> <span class="QuestionDesc">consent</span> <span class="LeftOpDesc">I do not agree</span> <span class="OpDesc">Is Selected</span>'
            }, "Type": "If"},
            "Type": "BooleanExpression"
        },
        "Flow": [{"Type": "EndSurvey", "FlowID": "FL_43"}]
    }

    # Attention check branch
    attn_branch = {
        "Type": "Branch", "FlowID": "FL_40",
        "Description": "Attention Check Branch",
        "BranchLogic": {
            "0": {"0": {
                "LogicType": "Question",
                "QuestionID": Q["attn_check"], "QuestionIsInLoop": "no",
                "ChoiceLocator": f'q://{Q["attn_check"]}/SelectableChoice/4',
                "Operator": "NotSelected", "Type": "Expression",
                "Description": '<span class="ConjDesc">If</span> <span class="QuestionDesc">attn_check</span> <span class="LeftOpDesc">Horse</span> <span class="OpDesc">Is Not Selected</span>'
            }, "Type": "If"},
            "Type": "BooleanExpression"
        },
        "Flow": [{
            "Type": "EndSurvey", "FlowID": "FL_41",
            "EndingType": "Advanced",
            "Options": {"Advanced": "true", "SurveyTermination": "DisplayMessage",
                        "EOSMessage": "MS_0f26k4kl5jOeYkm"}
        }]
    }

    flow = {
        "Type": "Root", "FlowID": "FL_1",
        "Flow": [
            # Mobile screening
            {
                "Type": "Branch", "FlowID": "FL_10",
                "Description": "Mobile Screening",
                "BranchLogic": {
                    "0": {"0": {
                        "LogicType": "DeviceType", "Operator": "Is",
                        "LeftOperand": "mobile", "Type": "Expression",
                        "Description": '<span class="ConjDesc">If</span><span class="schema_desc">Device Type</span><span class="select_val_desc Operator_desc">Is</span><span class="select_val_desc LeftOperand_desc">Mobile</span>'
                    }, "Type": "If"},
                    "Type": "BooleanExpression"
                },
                "Flow": [{"Type": "EndSurvey", "FlowID": "FL_11"}]
            },
            # Screening block
            {"Type": "Standard", "ID": screening_block, "FlowID": "FL_2", "Autofill": []},
            # Consent branch
            consent_branch,
            # Attention check branch
            attn_branch,
            # *** BlockRandomizer — 3 category cells ***
            {
                "Type": "BlockRandomizer",
                "FlowID": "FL_3",
                "SubSet": 1,
                "EvenPresentation": True,
                "Flow": randomizer_flow
            },
            # Study blocks (all use piped EmbeddedData)
            {"Type": "Standard", "ID": pref_block, "FlowID": "FL_4", "Autofill": []},
            {"Type": "Standard", "ID": ai_rec_block, "FlowID": "FL_5", "Autofill": []},
            {"Type": "Standard", "ID": accept_block, "FlowID": "FL_6", "Autofill": []},
            {"Type": "Standard", "ID": reveal_block, "FlowID": "FL_7", "Autofill": []},
            {"Type": "Standard", "ID": counterfactual_block, "FlowID": "FL_8", "Autofill": []},
            {"Type": "Standard", "ID": wtp_block, "FlowID": "FL_9", "Autofill": []},
            {"Type": "Standard", "ID": postreveal_block, "FlowID": "FL_13", "Autofill": []},
            {"Type": "Standard", "ID": demo_block, "FlowID": "FL_12", "Autofill": []},
            {"Type": "EndSurvey", "FlowID": "FL_99"}
        ],
        "Properties": {"Count": 30}
    }

    api_call("PUT", f"/survey-definitions/{survey_id}/flow", flow)
    print("  Flow set: mobile -> screening -> consent -> attn -> BlockRandomizer(3 cells)")
    print("  -> pref -> ai_rec -> accept -> reveal -> counterfactual -> wtp -> post_reveal -> demo -> end")

    # =================================================================
    # Step 6: Set survey options
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
    opts["NextButton"] = " \u2192 "
    opts["PreviousButton"] = " \u2190 "
    opts["SkinLibrary"] = "okstatebusiness"
    opts["SkinType"] = "templated"
    opts["Skin"] = {
        "brandingId": None,
        "templateId": "*base",
        "overrides": {
            "colors": {"secondary": "#1400c0", "primary": "#1400c0"},
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
    print("  Options set (blue theme, no back button, slide transitions, Prolific redirect)")

    # =================================================================
    # Step 7: Activate survey
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
    print("STUDY 3 v3 CREATED AND ACTIVATED!")
    print("=" * 70)
    print(f"Survey ID:  {survey_id}")
    print(f"Edit:       {edit_url}")
    print(f"Preview:    {preview_url}")
    print(f"Live:       {live_url}")
    print()
    print("Design: 1 condition x 3 categories (earbuds/speakers/SSDs)")
    print("        BlockRandomizer(SubSet=1, EvenPresentation=true)")
    print("        ALL content piped from EmbeddedData")
    print()
    print("Key improvements over v2 (SV_6VGyZnRsSsebMhM):")
    print("  1. 3-cell BlockRandomizer for category randomization")
    print("  2. ALL question text piped from EmbeddedData (zero hardcoded product names)")
    print("  3. Feature importance Matrix rows piped (category-specific features)")
    print("  4. Speakers and SSDs product cards + AI recommendations added")
    print("  5. Reveal callout pipes OptimalProduct + OptimalPrice")
    print("  6. WTP pipes BrandedTarget")
    print()
    print("EmbeddedData fields per cell:")
    for field in ED_CELLS[0]:
        if len(str(ED_CELLS[0][field])) > 60:
            print(f"  {field:25s} = [HTML, {len(str(ED_CELLS[0][field]))} chars]")
        else:
            print(f"  {field:25s} = {ED_CELLS[0][field]}")
    print()
    print("DataExportTags:")
    for tag, qid in Q.items():
        print(f"  {tag:25s} -> {qid}")
    print()
    print("IMPORTANT: Update EOSRedirectURL with actual Prolific completion code before launch!")
    print("IMPORTANT: Update consent form with approved IRB text before launch!")

    return survey_id


if __name__ == "__main__":
    main()
