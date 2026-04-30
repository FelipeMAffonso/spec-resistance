"""
Create Study 3 v2: Welfare Revelation (Dollar Cost)
Spec Resistance Project -- Nature R&R Human Subjects

CLEAN REBUILD — v1 (SV_2nPRSQ0Y6bmSBG6) had QID7 server-side cache bug
where RO/DND type couldn't be changed in-place. This v2 creates all
questions with the correct type from scratch.

Key differences from v1:
  1. Feature importance as Matrix/Likert from creation (NOT RO/DND)
  2. Beautiful product cards (copied from Study 1 v1 BiasedConfab/earbuds cell)
  3. AI recommendation in ChatGPT-style chat bubble
  4. All improvements baked in from the start

Design: Single condition, N=400
        ALL participants experience realistic AI shopping scenario:
        1. Articulate preferences
        2. AI recommends ONE branded product (Sony WF-1000XM5) with confabulation
        3. Accept or reject
        4. Full 5-product reveal -- learn AI's pick wasn't the best match
        5. Counterfactual choice + WTP measures + post-reveal ratings

Flow:
  Mobile screening -> EndSurvey (if mobile)
  Screening block: browser meta, consent, PB, attention check (Horse), PB, passed message
  Consent branch -> EndSurvey (if "I do not agree")
  Attention check branch -> EndSurvey (if Horse not selected)
  Preference articulation block: timer(5s), pref_intro(DB), feature_importance(Matrix/Likert 6x7), pref_text(TE optional)
  AI recommendation block: timer(8s), ai_rec_display(DB with beautiful single product card + AI chat bubble)
  Accept/reject block: timer(3s), accept_reject(MC: Yes/No)
  Full reveal block: timer(8s), reveal_display(DB with beautiful 5-product cards + optimal identified)
  Counterfactual choice block: timer(3s), counterfactual_choice(MC 5 earbuds, randomized)
  WTP measures block: timer(3s), wtp_recommended(TE $0-300), PB, wtp_counterfactual(TE $0-300)
  Post-reveal measures block: timer(3s), post_reveal(Matrix/Likert 3x7)
  Demographics block: age(DL), gender(SAVR), PB, ai_shop_freq(SAHR 1-5), comments(TE optional)
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
# BEAUTIFUL PRODUCT CARDS (extracted from Study 1 SV_3mBQFO2Rlpq72LA)
# =========================================================================

# AI recommendation chat bubble (ChatGPT-style) -- Sony confabulated justification
AI_REC_CHAT_HTML = (
    '<div style="max-width:720px; margin:16px auto 0; font-family:-apple-system,'
    'BlinkMacSystemFont,Segoe UI,Roboto,sans-serif;">'
    '<div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:16px; '
    'overflow:hidden; box-shadow:0 2px 8px rgba(0,0,0,0.08);">'
    # Header bar
    '<div style="background:linear-gradient(135deg,#6366f1,#8b5cf6); padding:14px 20px; '
    'display:flex; align-items:center; gap:12px;">'
    '<div style="width:36px; height:36px; background:rgba(255,255,255,0.2); border-radius:50%; '
    'display:flex; align-items:center; justify-content:center;">'
    '<span style="font-size:20px; line-height:1;">&#129302;</span></div>'
    '<div><div style="color:white; font-weight:700; font-size:15px; line-height:1.3;">'
    'AI Shopping Assistant</div>'
    '<div style="color:rgba(255,255,255,0.75); font-size:12px; line-height:1.3;">'
    '&#9679; Online</div></div></div>'
    # Chat message
    '<div style="padding:20px;">'
    '<div style="display:flex; gap:10px; align-items:flex-start;">'
    '<div style="width:32px; height:32px; background:linear-gradient(135deg,#6366f1,#8b5cf6); '
    'border-radius:50%; display:flex; align-items:center; justify-content:center; flex-shrink:0;">'
    '<span style="color:white; font-size:16px; line-height:1;">&#9830;</span></div>'
    '<div style="flex:1;">'
    '<div style="background:white; border:1px solid #e2e8f0; border-radius:4px 16px 16px 16px; '
    'padding:16px 20px; font-size:15px; line-height:1.65; color:#1e293b; '
    'box-shadow:0 1px 2px rgba(0,0,0,0.04);">'
    "I recommend the <b>Sony WF-1000XM5</b>. Sony's industry-leading ANC technology "
    "and LDAC Hi-Res audio codec provide superior sound quality that outperforms the "
    "competition. The WF-1000XM5 delivers exceptional noise cancellation, premium build "
    "quality, and seamless integration with the Sony ecosystem. At $279.99, you're "
    "investing in a proven audio experience backed by decades of Sony engineering excellence."
    '</div>'
    '<div style="margin-top:6px; font-size:11px; color:#94a3b8; padding-left:4px;">Just now</div>'
    '</div></div></div></div></div>'
)

# Beautiful 5-product comparison cards (Amazon/Best Buy style)
PRODUCT_CARDS_HTML = (
    '<div style="max-width:720px; margin:0 auto; font-family:-apple-system,'
    'BlinkMacSystemFont,Segoe UI,Roboto,sans-serif;">'
    '<div style="display:flex; align-items:center; margin-bottom:16px; gap:10px;">'
    '<span style="font-size:20px; font-weight:800; color:#0f172a;">Compare Wireless Earbuds</span>'
    '<span style="font-size:13px; color:#94a3b8; font-weight:400;">5 products</span></div>'

    # --- Auralis Air4 Pro (optimal) ---
    '<div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:12px; '
    'padding:20px 24px; margin-bottom:12px; box-shadow:0 1px 3px rgba(0,0,0,0.06); max-width:720px;">'
    '<div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:12px; flex-wrap:wrap;">'
    '<div><span style="font-size:18px; font-weight:700; color:#0f172a;">Auralis Air4 Pro</span>'
    '<span style="display:inline-block; background-color:#16a34a; color:white; font-size:11px; '
    'font-weight:700; padding:3px 10px; border-radius:12px; margin-left:12px; vertical-align:middle; '
    'letter-spacing:0.3px;">Best Value</span></div>'
    '<span style="font-size:22px; font-weight:800; color:#0f172a; white-space:nowrap;">$59.99</span></div>'
    '<div style="margin-bottom:14px; display:flex; align-items:center; gap:8px;">'
    '<span style="color:#f59e0b; font-size:16px; letter-spacing:1px;">&#9733;&#9733;&#9733;&#9733;</span>'
    '<span style="color:#f59e0b; font-size:16px; letter-spacing:1px;">&#9733;</span>'
    '<span style="color:#d1d5db; font-size:16px; letter-spacing:1px;"></span>'
    '<span style="font-size:14px; font-weight:700; color:#334155;">4.5</span>'
    '<span style="font-size:13px; color:#94a3b8;">(234 reviews)</span></div>'
    '<div style="border-top:1px solid #e2e8f0; padding-top:12px;">'
    '<div style="display:flex; align-items:baseline; margin-bottom:5px; font-size:13px; line-height:1.4;">'
    '<span style="color:#64748b; min-width:90px; font-weight:600; flex-shrink:0;">ANC</span>'
    '<span style="color:#334155;">-45dB active noise cancellation</span></div>'
    '<div style="display:flex; align-items:baseline; margin-bottom:5px; font-size:13px; line-height:1.4;">'
    '<span style="color:#64748b; min-width:90px; font-weight:600; flex-shrink:0;">Battery</span>'
    '<span style="color:#334155;">8.5h (32h with case)</span></div>'
    '<div style="display:flex; align-items:baseline; margin-bottom:5px; font-size:13px; line-height:1.4;">'
    '<span style="color:#64748b; min-width:90px; font-weight:600; flex-shrink:0;">Codec</span>'
    '<span style="color:#334155;">aptX Lossless</span></div>'
    '<div style="display:flex; align-items:baseline; margin-bottom:5px; font-size:13px; line-height:1.4;">'
    '<span style="color:#64748b; min-width:90px; font-weight:600; flex-shrink:0;">Protection</span>'
    '<span style="color:#334155;">IP57 waterproof</span></div>'
    '</div></div>'

    # --- Sony WF-1000XM5 ---
    '<div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:12px; '
    'padding:20px 24px; margin-bottom:12px; box-shadow:0 1px 3px rgba(0,0,0,0.06); max-width:720px;">'
    '<div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:12px; flex-wrap:wrap;">'
    '<div><span style="font-size:18px; font-weight:700; color:#0f172a;">Sony WF-1000XM5</span></div>'
    '<span style="font-size:22px; font-weight:800; color:#0f172a; white-space:nowrap;">$279.99</span></div>'
    '<div style="margin-bottom:14px; display:flex; align-items:center; gap:8px;">'
    '<span style="color:#f59e0b; font-size:16px; letter-spacing:1px;">&#9733;&#9733;&#9733;&#9733;</span>'
    '<span style="color:#f59e0b; font-size:16px; letter-spacing:1px;">&#9733;</span>'
    '<span style="color:#d1d5db; font-size:16px; letter-spacing:1px;"></span>'
    '<span style="font-size:14px; font-weight:700; color:#334155;">4.5</span>'
    '<span style="font-size:13px; color:#94a3b8;">(4,567 reviews)</span></div>'
    '<div style="border-top:1px solid #e2e8f0; padding-top:12px;">'
    '<div style="display:flex; align-items:baseline; margin-bottom:5px; font-size:13px; line-height:1.4;">'
    '<span style="color:#64748b; min-width:90px; font-weight:600; flex-shrink:0;">ANC</span>'
    '<span style="color:#334155;">Industry-leading noise cancellation</span></div>'
    '<div style="display:flex; align-items:baseline; margin-bottom:5px; font-size:13px; line-height:1.4;">'
    '<span style="color:#64748b; min-width:90px; font-weight:600; flex-shrink:0;">Battery</span>'
    '<span style="color:#334155;">8h (24h with case)</span></div>'
    '<div style="display:flex; align-items:baseline; margin-bottom:5px; font-size:13px; line-height:1.4;">'
    '<span style="color:#64748b; min-width:90px; font-weight:600; flex-shrink:0;">Codec</span>'
    '<span style="color:#334155;">LDAC / AAC Hi-Res</span></div>'
    '<div style="display:flex; align-items:baseline; margin-bottom:5px; font-size:13px; line-height:1.4;">'
    '<span style="color:#64748b; min-width:90px; font-weight:600; flex-shrink:0;">Protection</span>'
    '<span style="color:#334155;">IPX4 splash-proof</span></div>'
    '</div></div>'

    # --- Apple AirPods Pro 2 ---
    '<div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:12px; '
    'padding:20px 24px; margin-bottom:12px; box-shadow:0 1px 3px rgba(0,0,0,0.06); max-width:720px;">'
    '<div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:12px; flex-wrap:wrap;">'
    '<div><span style="font-size:18px; font-weight:700; color:#0f172a;">Apple AirPods Pro 2</span></div>'
    '<span style="font-size:22px; font-weight:800; color:#0f172a; white-space:nowrap;">$249.00</span></div>'
    '<div style="margin-bottom:14px; display:flex; align-items:center; gap:8px;">'
    '<span style="color:#f59e0b; font-size:16px; letter-spacing:1px;">&#9733;&#9733;&#9733;&#9733;</span>'
    '<span style="color:#f59e0b; font-size:16px; letter-spacing:1px;">&#9733;</span>'
    '<span style="color:#d1d5db; font-size:16px; letter-spacing:1px;"></span>'
    '<span style="font-size:14px; font-weight:700; color:#334155;">4.7</span>'
    '<span style="font-size:13px; color:#94a3b8;">(56,789 reviews)</span></div>'
    '<div style="border-top:1px solid #e2e8f0; padding-top:12px;">'
    '<div style="display:flex; align-items:baseline; margin-bottom:5px; font-size:13px; line-height:1.4;">'
    '<span style="color:#64748b; min-width:90px; font-weight:600; flex-shrink:0;">ANC</span>'
    '<span style="color:#334155;">2x improvement over gen 1</span></div>'
    '<div style="display:flex; align-items:baseline; margin-bottom:5px; font-size:13px; line-height:1.4;">'
    '<span style="color:#64748b; min-width:90px; font-weight:600; flex-shrink:0;">Battery</span>'
    '<span style="color:#334155;">6h (30h with case)</span></div>'
    '<div style="display:flex; align-items:baseline; margin-bottom:5px; font-size:13px; line-height:1.4;">'
    '<span style="color:#64748b; min-width:90px; font-weight:600; flex-shrink:0;">Codec</span>'
    '<span style="color:#334155;">AAC</span></div>'
    '<div style="display:flex; align-items:baseline; margin-bottom:5px; font-size:13px; line-height:1.4;">'
    '<span style="color:#64748b; min-width:90px; font-weight:600; flex-shrink:0;">Protection</span>'
    '<span style="color:#334155;">IPX4 splash-proof</span></div>'
    '</div></div>'

    # --- Samsung Galaxy Buds3 Pro ---
    '<div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:12px; '
    'padding:20px 24px; margin-bottom:12px; box-shadow:0 1px 3px rgba(0,0,0,0.06); max-width:720px;">'
    '<div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:12px; flex-wrap:wrap;">'
    '<div><span style="font-size:18px; font-weight:700; color:#0f172a;">Samsung Galaxy Buds3 Pro</span></div>'
    '<span style="font-size:22px; font-weight:800; color:#0f172a; white-space:nowrap;">$199.99</span></div>'
    '<div style="margin-bottom:14px; display:flex; align-items:center; gap:8px;">'
    '<span style="color:#f59e0b; font-size:16px; letter-spacing:1px;">&#9733;&#9733;&#9733;&#9733;</span>'
    '<span style="color:#f59e0b; font-size:16px; letter-spacing:1px;">&#9733;</span>'
    '<span style="color:#d1d5db; font-size:16px; letter-spacing:1px;"></span>'
    '<span style="font-size:14px; font-weight:700; color:#334155;">4.4</span>'
    '<span style="font-size:13px; color:#94a3b8;">(8,765 reviews)</span></div>'
    '<div style="border-top:1px solid #e2e8f0; padding-top:12px;">'
    '<div style="display:flex; align-items:baseline; margin-bottom:5px; font-size:13px; line-height:1.4;">'
    '<span style="color:#64748b; min-width:90px; font-weight:600; flex-shrink:0;">ANC</span>'
    '<span style="color:#334155;">Adaptive noise cancellation</span></div>'
    '<div style="display:flex; align-items:baseline; margin-bottom:5px; font-size:13px; line-height:1.4;">'
    '<span style="color:#64748b; min-width:90px; font-weight:600; flex-shrink:0;">Battery</span>'
    '<span style="color:#334155;">7h (30h with case)</span></div>'
    '<div style="display:flex; align-items:baseline; margin-bottom:5px; font-size:13px; line-height:1.4;">'
    '<span style="color:#64748b; min-width:90px; font-weight:600; flex-shrink:0;">Codec</span>'
    '<span style="color:#334155;">SSC / AAC</span></div>'
    '<div style="display:flex; align-items:baseline; margin-bottom:5px; font-size:13px; line-height:1.4;">'
    '<span style="color:#64748b; min-width:90px; font-weight:600; flex-shrink:0;">Protection</span>'
    '<span style="color:#334155;">IP57 waterproof</span></div>'
    '</div></div>'

    # --- Jabra Elite 85t ---
    '<div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:12px; '
    'padding:20px 24px; margin-bottom:12px; box-shadow:0 1px 3px rgba(0,0,0,0.06); max-width:720px;">'
    '<div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:12px; flex-wrap:wrap;">'
    '<div><span style="font-size:18px; font-weight:700; color:#0f172a;">Jabra Elite 85t</span></div>'
    '<span style="font-size:22px; font-weight:800; color:#0f172a; white-space:nowrap;">$179.99</span></div>'
    '<div style="margin-bottom:14px; display:flex; align-items:center; gap:8px;">'
    '<span style="color:#f59e0b; font-size:16px; letter-spacing:1px;">&#9733;&#9733;&#9733;&#9733;</span>'
    '<span style="color:#d1d5db; font-size:16px; letter-spacing:1px;">&#9734;</span>'
    '<span style="font-size:14px; font-weight:700; color:#334155;">4.3</span>'
    '<span style="font-size:13px; color:#94a3b8;">(9,876 reviews)</span></div>'
    '<div style="border-top:1px solid #e2e8f0; padding-top:12px;">'
    '<div style="display:flex; align-items:baseline; margin-bottom:5px; font-size:13px; line-height:1.4;">'
    '<span style="color:#64748b; min-width:90px; font-weight:600; flex-shrink:0;">ANC</span>'
    '<span style="color:#334155;">Adjustable noise cancellation</span></div>'
    '<div style="display:flex; align-items:baseline; margin-bottom:5px; font-size:13px; line-height:1.4;">'
    '<span style="color:#64748b; min-width:90px; font-weight:600; flex-shrink:0;">Battery</span>'
    '<span style="color:#334155;">5.5h (25h with case)</span></div>'
    '<div style="display:flex; align-items:baseline; margin-bottom:5px; font-size:13px; line-height:1.4;">'
    '<span style="color:#64748b; min-width:90px; font-weight:600; flex-shrink:0;">Codec</span>'
    '<span style="color:#334155;">AAC / SBC</span></div>'
    '<div style="display:flex; align-items:baseline; margin-bottom:5px; font-size:13px; line-height:1.4;">'
    '<span style="color:#64748b; min-width:90px; font-weight:600; flex-shrink:0;">Protection</span>'
    '<span style="color:#334155;">IPX4 splash-proof</span></div>'
    '</div></div>'

    '</div>'  # close outer wrapper
)


def main():
    print("=" * 70)
    print("CREATING STUDY 3 v2: Welfare Revelation (Dollar Cost)")
    print("Single condition, N=400 — CLEAN REBUILD")
    print("=" * 70)

    # =================================================================
    # Step 1: Create survey
    # =================================================================
    print("\nStep 1: Creating survey...")
    survey_resp = api_call("POST", "/survey-definitions", {
        "SurveyName": "SR Study 3 v2 -- Welfare Revelation",
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

    # Timing (5s minimum)
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

    # Pref intro
    q = create_question(survey_id, {
        "QuestionText": (
            '<div style="text-align: center;">'
            '<span style="font-size:19px;"><b>AI SHOPPING ASSISTANT STUDY</b></span>'
            '</div>'
            '<div style="text-align: center;">&nbsp;</div>'
            '<span style="font-size:19px;">'
            'Imagine you are shopping for a new pair of <b>wireless earbuds</b>. '
            'You want earbuds with good sound quality, effective noise cancellation, '
            'and decent battery life at a reasonable price.'
            '<br><br>'
            'You decide to ask an <b>AI shopping assistant</b> for a recommendation. '
            'Before seeing its recommendation, please tell us what matters most to you.'
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

    # Feature importance (Matrix/Likert 6x7) -- CORRECT TYPE from creation
    # This is the key fix from v1: Matrix/Likert instead of RO/DND
    q = create_question(survey_id, {
        "QuestionText": (
            '<span style="font-size:19px;">'
            'How <b>important</b> is each of the following features '
            'when choosing wireless earbuds?'
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
            "1": {"Display": "Sound quality"},
            "2": {"Display": "Noise cancellation (ANC)"},
            "3": {"Display": "Battery life"},
            "4": {"Display": "Price / value for money"},
            "5": {"Display": "Brand reputation"},
            "6": {"Display": "Comfort / fit"}
        },
        "ChoiceOrder": ["1", "2", "3", "4", "5", "6"],
        "Answers": {
            "1": {"Display": "1 = Not at all important"},
            "2": {"Display": "2"},
            "3": {"Display": "3"},
            "4": {"Display": "4 = Moderately important"},
            "5": {"Display": "5"},
            "6": {"Display": "6"},
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

    # Free text preferences (optional)
    q = create_question(survey_id, {
        "QuestionText": (
            '<span style="font-size:19px;">'
            'Is there anything else you want in your earbuds? (optional)'
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

    # Timing (8s minimum)
    q = create_question(survey_id, {
        "QuestionText": "Timing",
        "QuestionType": "Timing",
        "Selector": "PageTimer",
        "Configuration": {"QuestionDescriptionOption": "UseText", "MinSeconds": 8, "MaxSeconds": "0"},
        "Choices": {"1": {"Display": "First Click"}, "2": {"Display": "Last Click"},
                    "3": {"Display": "Page Submit"}, "4": {"Display": "Click Count"}},
        "Language": [],
        "DataExportTag": "timer_airec"
    })
    all_qids["timer_airec"] = q
    print(f"  {q}: timer_airec")

    # AI recommendation display (beautiful chat bubble)
    q = create_question(survey_id, {
        "QuestionText": (
            '<span style="font-size:19px;">'
            'The AI shopping assistant analyzed your preferences and returned '
            'the following recommendation:'
            '</span>'
            '<br><br>'
            + AI_REC_CHAT_HTML +
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
    print(f"  {q}: ai_rec_display (chat bubble)")

    # --- ACCEPT/REJECT BLOCK ---

    # Timing (3s minimum)
    q = create_question(survey_id, {
        "QuestionText": "Timing",
        "QuestionType": "Timing",
        "Selector": "PageTimer",
        "Configuration": {"QuestionDescriptionOption": "UseText", "MinSeconds": 3, "MaxSeconds": "0"},
        "Choices": {"1": {"Display": "First Click"}, "2": {"Display": "Last Click"},
                    "3": {"Display": "Page Submit"}, "4": {"Display": "Click Count"}},
        "Language": [],
        "DataExportTag": "timer_accept"
    })
    all_qids["timer_accept"] = q
    print(f"  {q}: timer_accept")

    # Accept/reject question
    q = create_question(survey_id, {
        "QuestionText": (
            '<span style="font-size:19px;">'
            'Based on the AI\'s recommendation, would you purchase the '
            '<b>Sony WF-1000XM5</b> ($279.99)?'
            '</span>'
        ),
        "QuestionType": "MC",
        "Selector": "SAHR",
        "SubSelector": "TX",
        "Configuration": {"QuestionDescriptionOption": "UseText", "LabelPosition": "BELOW"},
        "Choices": {
            "1": {"Display": "Yes, I would purchase this product"},
            "2": {"Display": "No, I would look elsewhere"}
        },
        "ChoiceOrder": ["1", "2"],
        "Validation": {"Settings": {"ForceResponse": "ON", "ForceResponseType": "ON", "Type": "None"}},
        "QuestionJS": HIDE_NEXT_JS,
        "Language": [],
        "DataExportTag": "accept_reject"
    })
    all_qids["accept_reject"] = q
    print(f"  {q}: accept_reject")

    # --- FULL REVEAL BLOCK ---

    # Timing (8s minimum)
    q = create_question(survey_id, {
        "QuestionText": "Timing",
        "QuestionType": "Timing",
        "Selector": "PageTimer",
        "Configuration": {"QuestionDescriptionOption": "UseText", "MinSeconds": 8, "MaxSeconds": "0"},
        "Choices": {"1": {"Display": "First Click"}, "2": {"Display": "Last Click"},
                    "3": {"Display": "Page Submit"}, "4": {"Display": "Click Count"}},
        "Language": [],
        "DataExportTag": "timer_reveal"
    })
    all_qids["timer_reveal"] = q
    print(f"  {q}: timer_reveal")

    # Reveal text + beautiful product cards
    q = create_question(survey_id, {
        "QuestionText": (
            '<span style="font-size:19px;">'
            'Here are <b>ALL 5 products</b> the AI considered when making its '
            'recommendation:'
            '</span>'
            '<br><br>'
            + PRODUCT_CARDS_HTML +
            '<br>'
            '<div style="max-width:720px; margin:0 auto; background:#fef3c7; '
            'border:1px solid #f59e0b; border-radius:12px; padding:16px 20px;">'
            '<span style="font-size:16px; color:#92400e;">'
            'The product that <b>best matched your stated preferences</b> '
            '(best noise cancellation, longest battery life, most codec support, '
            'and lowest price) was: '
            '<b style="color:#16a34a;">Auralis Air4 Pro ($59.99)</b>'
            '<br><br>'
            'The AI recommended the Sony WF-1000XM5 ($279.99) instead.'
            '</span></div>'
        ),
        "QuestionType": "DB",
        "Selector": "TB",
        "Configuration": {"QuestionDescriptionOption": "UseText"},
        "Language": [],
        "DataExportTag": "reveal_display"
    })
    all_qids["reveal_display"] = q
    print(f"  {q}: reveal_display (5 product cards)")

    # --- COUNTERFACTUAL CHOICE BLOCK ---

    # Timing (3s minimum)
    q = create_question(survey_id, {
        "QuestionText": "Timing",
        "QuestionType": "Timing",
        "Selector": "PageTimer",
        "Configuration": {"QuestionDescriptionOption": "UseText", "MinSeconds": 3, "MaxSeconds": "0"},
        "Choices": {"1": {"Display": "First Click"}, "2": {"Display": "Last Click"},
                    "3": {"Display": "Page Submit"}, "4": {"Display": "Click Count"}},
        "Language": [],
        "DataExportTag": "timer_counterfactual"
    })
    all_qids["timer_counterfactual"] = q
    print(f"  {q}: timer_counterfactual")

    # Counterfactual choice (randomized)
    q = create_question(survey_id, {
        "QuestionText": (
            '<span style="font-size:19px;">'
            'Now that you can see all the options, which product would you choose?'
            '</span>'
        ),
        "QuestionType": "MC",
        "Selector": "SAVR",
        "SubSelector": "TX",
        "Configuration": {"QuestionDescriptionOption": "UseText"},
        "Choices": {
            "1": {"Display": "Apple AirPods Pro 2 ($249.00)"},
            "2": {"Display": "Samsung Galaxy Buds3 Pro ($199.99)"},
            "3": {"Display": "Sony WF-1000XM5 ($279.99)"},
            "4": {"Display": "Auralis Air4 Pro ($59.99)"},
            "5": {"Display": "Jabra Elite 85t ($179.99)"}
        },
        "ChoiceOrder": ["1", "2", "3", "4", "5"],
        "Validation": {"Settings": {"ForceResponse": "ON", "ForceResponseType": "ON", "Type": "None"}},
        "Randomization": {"Type": "All", "Advanced": None, "TotalRandSubset": ""},
        "Language": [],
        "DataExportTag": "counterfactual_choice"
    })
    all_qids["counterfactual_choice"] = q
    print(f"  {q}: counterfactual_choice (randomized)")

    # --- WTP MEASURES BLOCK ---

    # Timing (3s minimum)
    q = create_question(survey_id, {
        "QuestionText": "Timing",
        "QuestionType": "Timing",
        "Selector": "PageTimer",
        "Configuration": {"QuestionDescriptionOption": "UseText", "MinSeconds": 3, "MaxSeconds": "0"},
        "Choices": {"1": {"Display": "First Click"}, "2": {"Display": "Last Click"},
                    "3": {"Display": "Page Submit"}, "4": {"Display": "Click Count"}},
        "Language": [],
        "DataExportTag": "timer_wtp"
    })
    all_qids["timer_wtp"] = q
    print(f"  {q}: timer_wtp")

    # WTP for AI-recommended product (numeric $0-300)
    q = create_question(survey_id, {
        "QuestionText": (
            '<span style="font-size:19px;">'
            'How much would you be willing to pay for the product the AI recommended '
            '(<b>Sony WF-1000XM5</b>)?'
            '<br><br>'
            'Please enter an amount between $0 and $300.'
            '</span>'
        ),
        "QuestionType": "TE",
        "Selector": "SL",
        "Configuration": {"QuestionDescriptionOption": "UseText", "InputWidth": 200},
        "Validation": {
            "Settings": {
                "ForceResponse": "ON",
                "ForceResponseType": "ON",
                "Type": "ContentType",
                "MinChars": "1",
                "ContentType": "ValidNumber",
                "ValidDateType": "DateWithFormat",
                "ValidPhoneType": "ValidUSPhone",
                "ValidZipType": "ValidUSZip",
                "ValidNumber": {"Min": "0", "Max": "300", "NumDecimals": ""}
            }
        },
        "Language": [],
        "DataExportTag": "wtp_recommended"
    })
    all_qids["wtp_recommended"] = q
    print(f"  {q}: wtp_recommended ($0-300)")

    # WTP for counterfactual choice (numeric $0-300)
    q = create_question(survey_id, {
        "QuestionText": (
            '<span style="font-size:19px;">'
            'How much would you be willing to pay for the product you would choose now '
            '(the one you selected on the previous page)?'
            '<br><br>'
            'Please enter an amount between $0 and $300.'
            '</span>'
        ),
        "QuestionType": "TE",
        "Selector": "SL",
        "Configuration": {"QuestionDescriptionOption": "UseText", "InputWidth": 200},
        "Validation": {
            "Settings": {
                "ForceResponse": "ON",
                "ForceResponseType": "ON",
                "Type": "ContentType",
                "MinChars": "1",
                "ContentType": "ValidNumber",
                "ValidDateType": "DateWithFormat",
                "ValidPhoneType": "ValidUSPhone",
                "ValidZipType": "ValidUSZip",
                "ValidNumber": {"Min": "0", "Max": "300", "NumDecimals": ""}
            }
        },
        "Language": [],
        "DataExportTag": "wtp_counterfactual"
    })
    all_qids["wtp_counterfactual"] = q
    print(f"  {q}: wtp_counterfactual ($0-300)")

    # --- POST-REVEAL MEASURES BLOCK ---

    # Timing (3s minimum)
    q = create_question(survey_id, {
        "QuestionText": "Timing",
        "QuestionType": "Timing",
        "Selector": "PageTimer",
        "Configuration": {"QuestionDescriptionOption": "UseText", "MinSeconds": 3, "MaxSeconds": "0"},
        "Choices": {"1": {"Display": "First Click"}, "2": {"Display": "Last Click"},
                    "3": {"Display": "Page Submit"}, "4": {"Display": "Click Count"}},
        "Language": [],
        "DataExportTag": "timer_postreveal"
    })
    all_qids["timer_postreveal"] = q
    print(f"  {q}: timer_postreveal")

    # Post-reveal measures (Matrix/Likert, 3 items x 7-point)
    q = create_question(survey_id, {
        "QuestionText": (
            '<span style="font-size:19px;">'
            'Now that you have seen all available options, please indicate how much '
            'you agree or disagree with each statement.'
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
            "1": {"Display": "I would <b>rate</b> the AI shopping assistant positively."},
            "2": {"Display": "I feel <b>misled</b> by the AI's recommendation."},
            "3": {"Display": "I would <b>trust</b> an AI shopping assistant in the future."}
        },
        "ChoiceOrder": ["1", "2", "3"],
        "Answers": {
            "1": {"Display": "1 = Strongly disagree"},
            "2": {"Display": "2"},
            "3": {"Display": "3"},
            "4": {"Display": "4 = Neither agree nor disagree"},
            "5": {"Display": "5"},
            "6": {"Display": "6"},
            "7": {"Display": "7 = Strongly agree"}
        },
        "AnswerOrder": ["1", "2", "3", "4", "5", "6", "7"],
        "Validation": {"Settings": {"ForceResponse": "ON", "ForceResponseType": "ON", "Type": "None"}},
        "Randomization": {"Type": "All", "Advanced": None, "TotalRandSubset": ""},
        "Language": [],
        "DataExportTag": "post_reveal"
    })
    all_qids["post_reveal"] = q
    print(f"  {q}: post_reveal (Matrix 3x7)")

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

    # AI shopping frequency
    q = create_question(survey_id, {
        "QuestionText": (
            '<span style="font-size:19px;">'
            'How often do you use AI assistants (ChatGPT, Gemini, Copilot, etc.) '
            'to help you shop for products?'
            '</span>'
        ),
        "QuestionType": "MC",
        "Selector": "SAHR",
        "SubSelector": "TX",
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
        "Language": [],
        "DataExportTag": "ai_shop_freq"
    })
    all_qids["ai_shop_freq"] = q
    print(f"  {q}: ai_shop_freq")

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
    # Step 4: Assign questions to blocks
    # =================================================================
    print("\nStep 4: Assigning questions to blocks...")

    # Screening block (default block -- must list ONLY screening questions)
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

    # AI recommendation block
    api_call("PUT", f"/survey-definitions/{survey_id}/blocks/{ai_rec_block}", {
        "Type": "Standard",
        "Description": "ai_recommendation",
        "BlockElements": [
            {"Type": "Question", "QuestionID": all_qids["timer_airec"]},
            {"Type": "Question", "QuestionID": all_qids["ai_rec_display"]},
        ],
        "Options": BLOCK_OPTS
    })

    # Accept/reject block
    api_call("PUT", f"/survey-definitions/{survey_id}/blocks/{accept_block}", {
        "Type": "Standard",
        "Description": "accept_reject",
        "BlockElements": [
            {"Type": "Question", "QuestionID": all_qids["timer_accept"]},
            {"Type": "Question", "QuestionID": all_qids["accept_reject"]},
        ],
        "Options": BLOCK_OPTS
    })

    # Full reveal block
    api_call("PUT", f"/survey-definitions/{survey_id}/blocks/{reveal_block}", {
        "Type": "Standard",
        "Description": "full_reveal",
        "BlockElements": [
            {"Type": "Question", "QuestionID": all_qids["timer_reveal"]},
            {"Type": "Question", "QuestionID": all_qids["reveal_display"]},
        ],
        "Options": BLOCK_OPTS
    })

    # Counterfactual choice block
    api_call("PUT", f"/survey-definitions/{survey_id}/blocks/{counterfactual_block}", {
        "Type": "Standard",
        "Description": "counterfactual_choice",
        "BlockElements": [
            {"Type": "Question", "QuestionID": all_qids["timer_counterfactual"]},
            {"Type": "Question", "QuestionID": all_qids["counterfactual_choice"]},
        ],
        "Options": BLOCK_OPTS
    })

    # WTP measures block
    api_call("PUT", f"/survey-definitions/{survey_id}/blocks/{wtp_block}", {
        "Type": "Standard",
        "Description": "wtp_measures",
        "BlockElements": [
            {"Type": "Question", "QuestionID": all_qids["timer_wtp"]},
            {"Type": "Question", "QuestionID": all_qids["wtp_recommended"]},
            {"Type": "Page Break"},
            {"Type": "Question", "QuestionID": all_qids["wtp_counterfactual"]},
        ],
        "Options": BLOCK_OPTS
    })

    # Post-reveal measures block
    api_call("PUT", f"/survey-definitions/{survey_id}/blocks/{postreveal_block}", {
        "Type": "Standard",
        "Description": "post_reveal_measures",
        "BlockElements": [
            {"Type": "Question", "QuestionID": all_qids["timer_postreveal"]},
            {"Type": "Question", "QuestionID": all_qids["post_reveal"]},
        ],
        "Options": BLOCK_OPTS
    })

    # Demographics block
    api_call("PUT", f"/survey-definitions/{survey_id}/blocks/{demo_block}", {
        "Type": "Standard",
        "Description": "demographics",
        "BlockElements": [
            {"Type": "Question", "QuestionID": all_qids["age"]},
            {"Type": "Question", "QuestionID": all_qids["gender"]},
            {"Type": "Page Break"},
            {"Type": "Question", "QuestionID": all_qids["ai_shop_freq"]},
            {"Type": "Question", "QuestionID": all_qids["comments"]},
        ],
        "Options": BLOCK_OPTS
    })

    print("  All blocks assigned")

    # =================================================================
    # Step 5: Set survey flow
    # =================================================================
    print("\nStep 5: Setting survey flow...")

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
            # Mobile screening
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
            # Screening block
            {"Type": "Standard", "ID": screening_block, "FlowID": "FL_2", "Autofill": []},
            # Consent branch
            consent_branch,
            # Attention check branch
            attn_branch,
            # Study blocks (single condition -- no BlockRandomizer needed)
            {"Type": "Standard", "ID": pref_block, "FlowID": "FL_3", "Autofill": []},
            {"Type": "Standard", "ID": ai_rec_block, "FlowID": "FL_4", "Autofill": []},
            {"Type": "Standard", "ID": accept_block, "FlowID": "FL_5", "Autofill": []},
            {"Type": "Standard", "ID": reveal_block, "FlowID": "FL_6", "Autofill": []},
            {"Type": "Standard", "ID": counterfactual_block, "FlowID": "FL_7", "Autofill": []},
            {"Type": "Standard", "ID": wtp_block, "FlowID": "FL_8", "Autofill": []},
            {"Type": "Standard", "ID": postreveal_block, "FlowID": "FL_9", "Autofill": []},
            {"Type": "Standard", "ID": demo_block, "FlowID": "FL_12", "Autofill": []},
            {"Type": "EndSurvey", "FlowID": "FL_99"}
        ],
        "Properties": {"Count": 30}
    }

    api_call("PUT", f"/survey-definitions/{survey_id}/flow", flow)
    print("  Flow set: mobile screen -> consent -> attn check -> "
          "pref -> ai_rec -> accept/reject -> reveal -> "
          "counterfactual -> wtp -> post_reveal -> demo -> end")

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
    opts["NextButton"] = " \u2192 "
    opts["PreviousButton"] = " \u2190 "
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
    print("  Options set (slide transitions, blue theme, centered buttons, 850px min, Prolific redirect)")

    # =================================================================
    # Step 7: Activate survey
    # =================================================================
    print("\nStep 7: Activating survey...")
    api_call("PUT", f"/surveys/{survey_id}",
             {"isActive": True})
    print("  Survey activated!")

    # =================================================================
    # Done!
    # =================================================================
    edit_url = f"https://okstatebusiness.az1.qualtrics.com/survey-builder/{survey_id}/edit"
    preview_url = f"https://okstatebusiness.az1.qualtrics.com/jfe/preview/{survey_id}"
    live_url = f"https://okstatebusiness.az1.qualtrics.com/jfe/form/{survey_id}"

    print("\n" + "=" * 70)
    print("SURVEY CREATED AND ACTIVATED!")
    print("=" * 70)
    print(f"Survey ID:  {survey_id}")
    print(f"Edit:       {edit_url}")
    print(f"Preview:    {preview_url}")
    print(f"Live:       {live_url}")
    print()
    print("Design: Single condition, N=400 (Welfare Revelation v2)")
    print()
    print("Key improvements over v1 (SV_2nPRSQ0Y6bmSBG6):")
    print("  1. Feature importance as Matrix/Likert from creation (no cache bug)")
    print("  2. Beautiful product cards (Amazon/Best Buy style from Study 1)")
    print("  3. AI recommendation in ChatGPT-style chat bubble")
    print("  4. Counterfactual choice randomized")
    print("  5. Post-reveal measures randomized (row order)")
    print("  6. Reveal callout in styled warning box")
    print()
    print("Structure:")
    print("  screening        -> consent, attention check (Horse), passed msg")
    print("  pref_articulation -> intro, feature importance (Matrix 6x7), optional text")
    print("  ai_recommendation -> Sony WF-1000XM5 chat bubble (8s timer)")
    print("  accept_reject     -> Yes/No purchase decision")
    print("  full_reveal       -> 5 beautiful product cards + optimal callout")
    print("  counterfactual    -> 'Which would you choose now?' (5 options, randomized)")
    print("  wtp_measures      -> WTP for recommended ($0-300) | WTP for counterfactual ($0-300)")
    print("  post_reveal       -> AI rating, felt misled, future trust (3 items)")
    print("  demographics      -> age, gender, AI shopping frequency, comments")
    print()
    print("DataExportTags:")
    for tag, qid in all_qids.items():
        print(f"  {tag:25s} -> {qid}")
    print()
    print("IMPORTANT: Update EOSRedirectURL with actual Prolific completion code before launch!")
    print("IMPORTANT: Update consent form with approved IRB text before launch!")

    return survey_id


if __name__ == "__main__":
    main()
