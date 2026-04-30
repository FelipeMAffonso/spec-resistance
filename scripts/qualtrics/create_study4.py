"""
Create Study 4: Field Survey of Real AI Shoppers
Spec Resistance Project -- Nature R&R Human Subjects

Design: Survey of actual AI shopping users, N=400
        Screening question at start; non-AI-users screened out.

Flow:
  Mobile screening -> EndSurvey (if mobile)
  Screening block: browser meta, consent, attention check (Horse), passed message
  Consent branch -> EndSurvey (if "I do not agree")
  Attention check branch -> EndSurvey (if Horse not selected)
  AI usage screening block: "Have you used an AI assistant for shopping?"
  Screening branch -> EndSurvey (if No)
  Recent experience block: category, AI used, prompt, recommendation, purchase, satisfaction
  Consideration set block: alternatives asked, products considered, best product, confidence
  Verification behavior block: verification frequency, trust drivers
  Awareness manipulation block: brand bias text + reactions
  Demographics block: age, gender, income, education
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

# Awareness manipulation text (brand bias finding)
AWARENESS_TEXT = (
    "Recent research has found that AI assistants systematically recommend products "
    "from well-known brands, even when lesser-known brands have better specifications "
    "and lower prices. This happens because AI systems learn brand associations from "
    "internet text during training, not because of advertising deals."
)


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


def main():
    print("=" * 70)
    print("CREATING STUDY 4: Field Survey of Real AI Shoppers")
    print("Survey design, N=400 (screened for AI shopping usage)")
    print("=" * 70)

    # =================================================================
    # Step 1: Create survey
    # =================================================================
    print("\nStep 1: Creating survey...")
    survey_resp = api_call("POST", "/survey-definitions", {
        "SurveyName": "SR Study 4 -- Field Survey of Real AI Shoppers",
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

    ai_screen_block = create_block(survey_id, "ai_usage_screening")
    experience_block = create_block(survey_id, "recent_experience")
    consideration_block = create_block(survey_id, "consideration_set")
    verification_block = create_block(survey_id, "verification_behavior")
    awareness_block = create_block(survey_id, "awareness_manipulation")
    demo_block = create_block(survey_id, "demographics")

    for name, bid in [("ai_usage_screening", ai_screen_block),
                      ("recent_experience", experience_block),
                      ("consideration_set", consideration_block),
                      ("verification_behavior", verification_block),
                      ("awareness_manipulation", awareness_block),
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
        'approximately 8 minutes to complete.<br><br>'
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

    # --- AI USAGE SCREENING BLOCK ---

    # Timing
    q = create_question(survey_id, {
        "QuestionText": "Timing",
        "QuestionType": "Timing",
        "Selector": "PageTimer",
        "Configuration": {"QuestionDescriptionOption": "UseText", "MinSeconds": 5, "MaxSeconds": "0"},
        "Choices": {"1": {"Display": "First Click"}, "2": {"Display": "Last Click"},
                    "3": {"Display": "Page Submit"}, "4": {"Display": "Click Count"}},
        "Language": [],
        "DataExportTag": "timer_aiscreen"
    })
    all_qids["timer_aiscreen"] = q
    print(f"  {q}: timer_aiscreen")

    # AI usage screening question
    q = create_question(survey_id, {
        "QuestionText": (
            '<span style="font-size:19px;">'
            'Have you used an AI assistant (ChatGPT, Gemini, Copilot, Perplexity, '
            'Amazon Rufus, or similar) to help you decide what product to buy '
            'in the <b>past 3 months</b>?'
            '</span>'
        ),
        "QuestionType": "MC",
        "Selector": "SAHR",
        "SubSelector": "TX",
        "Configuration": {"QuestionDescriptionOption": "UseText", "LabelPosition": "BELOW"},
        "Choices": {
            "1": {"Display": "Yes"},
            "2": {"Display": "No"}
        },
        "ChoiceOrder": ["1", "2"],
        "Validation": {"Settings": {"ForceResponse": "ON", "ForceResponseType": "ON", "Type": "None"}},
        "QuestionJS": HIDE_NEXT_JS,
        "Language": [],
        "DataExportTag": "ai_usage_screen"
    })
    all_qids["ai_usage_screen"] = q
    print(f"  {q}: ai_usage_screen")

    # --- RECENT EXPERIENCE BLOCK ---

    # Timing
    q = create_question(survey_id, {
        "QuestionText": "Timing",
        "QuestionType": "Timing",
        "Selector": "PageTimer",
        "Configuration": {"QuestionDescriptionOption": "UseText", "MinSeconds": 5, "MaxSeconds": "0"},
        "Choices": {"1": {"Display": "First Click"}, "2": {"Display": "Last Click"},
                    "3": {"Display": "Page Submit"}, "4": {"Display": "Click Count"}},
        "Language": [],
        "DataExportTag": "timer_experience"
    })
    all_qids["timer_experience"] = q
    print(f"  {q}: timer_experience")

    # Experience intro
    q = create_question(survey_id, {
        "QuestionText": (
            '<div style="text-align: center;">'
            '<span style="font-size:19px;"><b>YOUR AI SHOPPING EXPERIENCE</b></span>'
            '</div>'
            '<div style="text-align: center;">&nbsp;</div>'
            '<span style="font-size:19px;">'
            'Think about the <b>most recent time</b> you used an AI assistant '
            'to help you decide what product to buy.'
            '</span>'
        ),
        "QuestionType": "DB",
        "Selector": "TB",
        "Configuration": {"QuestionDescriptionOption": "UseText"},
        "Language": [],
        "DataExportTag": "exp_intro"
    })
    all_qids["exp_intro"] = q
    print(f"  {q}: exp_intro")

    # Product category (dropdown)
    q = create_question(survey_id, {
        "QuestionText": (
            '<span style="font-size:19px;">'
            'What <b>product category</b> were you shopping for?'
            '</span>'
        ),
        "QuestionType": "MC",
        "Selector": "DL",
        "SubSelector": "TX",
        "Configuration": {"QuestionDescriptionOption": "UseText"},
        "Choices": {
            "1": {"Display": "Electronics (phones, laptops, headphones, etc.)"},
            "2": {"Display": "Clothing / Fashion"},
            "3": {"Display": "Home / Kitchen / Furniture"},
            "4": {"Display": "Beauty / Personal care"},
            "5": {"Display": "Food / Grocery"},
            "6": {"Display": "Automotive"},
            "7": {"Display": "Other"}
        },
        "ChoiceOrder": ["1", "2", "3", "4", "5", "6", "7"],
        "Validation": {"Settings": {"ForceResponse": "ON", "ForceResponseType": "ON", "Type": "None"}},
        "Language": [],
        "DataExportTag": "product_category"
    })
    all_qids["product_category"] = q
    print(f"  {q}: product_category")

    # Which AI (MC)
    q = create_question(survey_id, {
        "QuestionText": (
            '<span style="font-size:19px;">'
            'Which <b>AI assistant</b> did you use?'
            '</span>'
        ),
        "QuestionType": "MC",
        "Selector": "SAVR",
        "SubSelector": "TX",
        "Configuration": {"QuestionDescriptionOption": "UseText"},
        "Choices": {
            "1": {"Display": "ChatGPT"},
            "2": {"Display": "Google Gemini"},
            "3": {"Display": "Microsoft Copilot"},
            "4": {"Display": "Perplexity"},
            "5": {"Display": "Amazon Rufus"},
            "6": {"Display": "Other"}
        },
        "ChoiceOrder": ["1", "2", "3", "4", "5", "6"],
        "Validation": {"Settings": {"ForceResponse": "ON", "ForceResponseType": "ON", "Type": "None"}},
        "Language": [],
        "DataExportTag": "ai_used"
    })
    all_qids["ai_used"] = q
    print(f"  {q}: ai_used")

    # What did you ask the AI? (text box, ForceResponse)
    q = create_question(survey_id, {
        "QuestionText": (
            '<span style="font-size:19px;">'
            'What did you <b>ask the AI</b>? Please describe your question or prompt '
            'as best you can remember.'
            '</span>'
        ),
        "QuestionType": "TE",
        "Selector": "SL",
        "Configuration": {"QuestionDescriptionOption": "UseText", "InputWidth": 680, "InputHeight": 80},
        "Validation": {"Settings": {"ForceResponse": "ON", "ForceResponseType": "ON", "Type": "None"}},
        "Language": [],
        "DataExportTag": "ai_prompt"
    })
    all_qids["ai_prompt"] = q
    print(f"  {q}: ai_prompt")

    # What did the AI recommend? (text box)
    q = create_question(survey_id, {
        "QuestionText": (
            '<span style="font-size:19px;">'
            'What did the AI <b>recommend</b>? Please describe the product(s) '
            'it suggested.'
            '</span>'
        ),
        "QuestionType": "TE",
        "Selector": "SL",
        "Configuration": {"QuestionDescriptionOption": "UseText", "InputWidth": 680, "InputHeight": 80},
        "Validation": {"Settings": {"ForceResponse": "ON", "ForceResponseType": "ON", "Type": "None"}},
        "Language": [],
        "DataExportTag": "ai_recommendation"
    })
    all_qids["ai_recommendation"] = q
    print(f"  {q}: ai_recommendation")

    # Did you purchase? (MC)
    q = create_question(survey_id, {
        "QuestionText": (
            '<span style="font-size:19px;">'
            'Did you <b>purchase</b> the recommended product?'
            '</span>'
        ),
        "QuestionType": "MC",
        "Selector": "SAVR",
        "SubSelector": "TX",
        "Configuration": {"QuestionDescriptionOption": "UseText"},
        "Choices": {
            "1": {"Display": "Yes"},
            "2": {"Display": "No"},
            "3": {"Display": "Purchased something else"},
            "4": {"Display": "Didn't purchase anything"}
        },
        "ChoiceOrder": ["1", "2", "3", "4"],
        "Validation": {"Settings": {"ForceResponse": "ON", "ForceResponseType": "ON", "Type": "None"}},
        "Language": [],
        "DataExportTag": "purchased"
    })
    all_qids["purchased"] = q
    print(f"  {q}: purchased")

    # Purchase satisfaction (1-7)
    q = create_question(survey_id, {
        "QuestionText": (
            '<span style="font-size:19px;">'
            'How <b>satisfied</b> are you with that purchase decision?'
            '</span>'
        ),
        "QuestionType": "MC",
        "Selector": "SAHR",
        "SubSelector": "TX",
        "Configuration": {"QuestionDescriptionOption": "UseText", "LabelPosition": "BELOW"},
        "Choices": {
            "1": {"Display": "1 = Very dissatisfied"},
            "2": {"Display": "2"},
            "3": {"Display": "3"},
            "4": {"Display": "4 = Neither satisfied nor dissatisfied"},
            "5": {"Display": "5"},
            "6": {"Display": "6"},
            "7": {"Display": "7 = Very satisfied"}
        },
        "ChoiceOrder": ["1", "2", "3", "4", "5", "6", "7"],
        "Validation": {"Settings": {"ForceResponse": "ON", "ForceResponseType": "ON", "Type": "None"}},
        "QuestionJS": HIDE_NEXT_JS,
        "Language": [],
        "DataExportTag": "satisfaction"
    })
    all_qids["satisfaction"] = q
    print(f"  {q}: satisfaction")

    # --- CONSIDERATION SET AWARENESS BLOCK ---

    # Timing
    q = create_question(survey_id, {
        "QuestionText": "Timing",
        "QuestionType": "Timing",
        "Selector": "PageTimer",
        "Configuration": {"QuestionDescriptionOption": "UseText", "MinSeconds": 3, "MaxSeconds": "0"},
        "Choices": {"1": {"Display": "First Click"}, "2": {"Display": "Last Click"},
                    "3": {"Display": "Page Submit"}, "4": {"Display": "Click Count"}},
        "Language": [],
        "DataExportTag": "timer_consideration"
    })
    all_qids["timer_consideration"] = q
    print(f"  {q}: timer_consideration")

    # Did you ask for alternatives?
    q = create_question(survey_id, {
        "QuestionText": (
            '<span style="font-size:19px;">'
            'Did you also ask the AI to <b>show you alternatives</b>?'
            '</span>'
        ),
        "QuestionType": "MC",
        "Selector": "SAVR",
        "SubSelector": "TX",
        "Configuration": {"QuestionDescriptionOption": "UseText"},
        "Choices": {
            "1": {"Display": "Yes"},
            "2": {"Display": "No"},
            "3": {"Display": "Don't remember"}
        },
        "ChoiceOrder": ["1", "2", "3"],
        "Validation": {"Settings": {"ForceResponse": "ON", "ForceResponseType": "ON", "Type": "None"}},
        "Language": [],
        "DataExportTag": "asked_alternatives"
    })
    all_qids["asked_alternatives"] = q
    print(f"  {q}: asked_alternatives")

    # How many products did AI consider?
    q = create_question(survey_id, {
        "QuestionText": (
            '<span style="font-size:19px;">'
            'How many products do you think the AI <b>considered</b> before '
            'recommending one to you?'
            '</span>'
        ),
        "QuestionType": "MC",
        "Selector": "SAVR",
        "SubSelector": "TX",
        "Configuration": {"QuestionDescriptionOption": "UseText"},
        "Choices": {
            "1": {"Display": "1-5"},
            "2": {"Display": "6-20"},
            "3": {"Display": "21-100"},
            "4": {"Display": "100+"},
            "5": {"Display": "Don't know"}
        },
        "ChoiceOrder": ["1", "2", "3", "4", "5"],
        "Validation": {"Settings": {"ForceResponse": "ON", "ForceResponseType": "ON", "Type": "None"}},
        "Language": [],
        "DataExportTag": "products_considered"
    })
    all_qids["products_considered"] = q
    print(f"  {q}: products_considered")

    # Do you believe AI recommended the BEST product?
    q = create_question(survey_id, {
        "QuestionText": (
            '<span style="font-size:19px;">'
            'Do you believe the AI recommended the <b>BEST product</b> for your needs, '
            'or could there have been a better option you didn\'t see?'
            '</span>'
        ),
        "QuestionType": "MC",
        "Selector": "SAVR",
        "SubSelector": "TX",
        "Configuration": {"QuestionDescriptionOption": "UseText"},
        "Choices": {
            "1": {"Display": "The AI recommended the best option"},
            "2": {"Display": "There might have been better options I didn't see"},
            "3": {"Display": "I'm not sure"}
        },
        "ChoiceOrder": ["1", "2", "3"],
        "Validation": {"Settings": {"ForceResponse": "ON", "ForceResponseType": "ON", "Type": "None"}},
        "Language": [],
        "DataExportTag": "best_product_belief"
    })
    all_qids["best_product_belief"] = q
    print(f"  {q}: best_product_belief")

    # Confidence AI was based on quality not brand (1-7)
    q = create_question(survey_id, {
        "QuestionText": (
            '<span style="font-size:19px;">'
            'How <b>confident</b> are you that the AI\'s recommendation was based on '
            'product quality rather than brand familiarity?'
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
        "DataExportTag": "quality_confidence"
    })
    all_qids["quality_confidence"] = q
    print(f"  {q}: quality_confidence")

    # --- VERIFICATION BEHAVIOR BLOCK ---

    # Timing
    q = create_question(survey_id, {
        "QuestionText": "Timing",
        "QuestionType": "Timing",
        "Selector": "PageTimer",
        "Configuration": {"QuestionDescriptionOption": "UseText", "MinSeconds": 3, "MaxSeconds": "0"},
        "Choices": {"1": {"Display": "First Click"}, "2": {"Display": "Last Click"},
                    "3": {"Display": "Page Submit"}, "4": {"Display": "Click Count"}},
        "Language": [],
        "DataExportTag": "timer_verification"
    })
    all_qids["timer_verification"] = q
    print(f"  {q}: timer_verification")

    # Verification frequency
    q = create_question(survey_id, {
        "QuestionText": (
            '<span style="font-size:19px;">'
            'When an AI recommends a product, how often do you <b>independently verify</b> '
            'the recommendation by checking reviews, comparing specs, or looking at other options?'
            '</span>'
        ),
        "QuestionType": "MC",
        "Selector": "SAVR",
        "SubSelector": "TX",
        "Configuration": {"QuestionDescriptionOption": "UseText"},
        "Choices": {
            "1": {"Display": "Always"},
            "2": {"Display": "Usually"},
            "3": {"Display": "Sometimes"},
            "4": {"Display": "Rarely"},
            "5": {"Display": "Never"}
        },
        "ChoiceOrder": ["1", "2", "3", "4", "5"],
        "Validation": {"Settings": {"ForceResponse": "ON", "ForceResponseType": "ON", "Type": "None"}},
        "Language": [],
        "DataExportTag": "verify_freq"
    })
    all_qids["verify_freq"] = q
    print(f"  {q}: verify_freq")

    # Trust drivers (multi-select)
    q = create_question(survey_id, {
        "QuestionText": (
            '<span style="font-size:19px;">'
            'What primarily drives your <b>trust</b> in an AI\'s product recommendation? '
            'Select all that apply.'
            '</span>'
        ),
        "QuestionType": "MC",
        "Selector": "MAVR",
        "SubSelector": "TX",
        "Configuration": {"QuestionDescriptionOption": "UseText"},
        "Choices": {
            "1": {"Display": "The explanation it gives"},
            "2": {"Display": "The brand it recommends"},
            "3": {"Display": "Past experience with the AI"},
            "4": {"Display": "I assume AI is objective"},
            "5": {"Display": "Convenience (saves time)"},
            "6": {"Display": "Other"}
        },
        "ChoiceOrder": ["1", "2", "3", "4", "5", "6"],
        "Validation": {"Settings": {"ForceResponse": "ON", "ForceResponseType": "ON", "Type": "None"}},
        "Language": [],
        "DataExportTag": "trust_drivers"
    })
    all_qids["trust_drivers"] = q
    print(f"  {q}: trust_drivers")

    # --- AWARENESS MANIPULATION BLOCK ---

    # Timing
    q = create_question(survey_id, {
        "QuestionText": "Timing",
        "QuestionType": "Timing",
        "Selector": "PageTimer",
        "Configuration": {"QuestionDescriptionOption": "UseText", "MinSeconds": 8, "MaxSeconds": "0"},
        "Choices": {"1": {"Display": "First Click"}, "2": {"Display": "Last Click"},
                    "3": {"Display": "Page Submit"}, "4": {"Display": "Click Count"}},
        "Language": [],
        "DataExportTag": "timer_awareness"
    })
    all_qids["timer_awareness"] = q
    print(f"  {q}: timer_awareness")

    # Awareness manipulation text (DB/TB)
    q = create_question(survey_id, {
        "QuestionText": (
            '<div style="background-color: #f7f7f7; border-left: 4px solid #1400c0; '
            'padding: 16px 20px; margin: 10px 0; border-radius: 4px;">'
            '<span style="font-size:17px;"><i>'
            f'{AWARENESS_TEXT}'
            '</i></span></div>'
            '<br>'
            '<span style="font-size:19px;">'
            'Please read the above information carefully before continuing.'
            '</span>'
        ),
        "QuestionType": "DB",
        "Selector": "TB",
        "Configuration": {"QuestionDescriptionOption": "UseText"},
        "Language": [],
        "DataExportTag": "awareness_text"
    })
    all_qids["awareness_text"] = q
    print(f"  {q}: awareness_text")

    # Post-awareness reaction (MC)
    q = create_question(survey_id, {
        "QuestionText": (
            '<span style="font-size:19px;">'
            'Knowing this, how do you feel about the AI recommendation you described earlier?'
            '</span>'
        ),
        "QuestionType": "MC",
        "Selector": "SAVR",
        "SubSelector": "TX",
        "Configuration": {"QuestionDescriptionOption": "UseText"},
        "Choices": {
            "1": {"Display": "I still think it was a good recommendation"},
            "2": {"Display": "I'm now less confident it was the best choice"},
            "3": {"Display": "I wish I had looked at more options"},
            "4": {"Display": "I want to look up alternatives now"}
        },
        "ChoiceOrder": ["1", "2", "3", "4"],
        "Validation": {"Settings": {"ForceResponse": "ON", "ForceResponseType": "ON", "Type": "None"}},
        "Language": [],
        "DataExportTag": "post_awareness_reaction"
    })
    all_qids["post_awareness_reaction"] = q
    print(f"  {q}: post_awareness_reaction")

    # Would you change how you use AI shopping? (text box)
    q = create_question(survey_id, {
        "QuestionText": (
            '<span style="font-size:19px;">'
            'Would you change how you use AI shopping assistants in the future? '
            'Please explain.'
            '</span>'
        ),
        "QuestionType": "TE",
        "Selector": "SL",
        "Configuration": {"QuestionDescriptionOption": "UseText", "InputWidth": 680, "InputHeight": 80},
        "Validation": {"Settings": {"ForceResponse": "ON", "ForceResponseType": "ON", "Type": "None"}},
        "Language": [],
        "DataExportTag": "change_behavior"
    })
    all_qids["change_behavior"] = q
    print(f"  {q}: change_behavior")

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

    # Income bracket (MC/SAVR)
    q = create_question(survey_id, {
        "QuestionText": (
            '<span style="font-size:19px;">'
            'What is your approximate annual household income?'
            '</span>'
        ),
        "QuestionType": "MC",
        "Selector": "SAVR",
        "SubSelector": "TX",
        "Configuration": {"QuestionDescriptionOption": "UseText"},
        "Choices": {
            "1": {"Display": "Under $25,000"},
            "2": {"Display": "$25,000 - $49,999"},
            "3": {"Display": "$50,000 - $74,999"},
            "4": {"Display": "$75,000 - $99,999"},
            "5": {"Display": "$100,000 - $149,999"},
            "6": {"Display": "$150,000+"},
            "7": {"Display": "Prefer not to say"}
        },
        "ChoiceOrder": ["1", "2", "3", "4", "5", "6", "7"],
        "Validation": {"Settings": {"ForceResponse": "RequestResponse",
                                    "ForceResponseType": "RequestResponse", "Type": "None"}},
        "Language": [],
        "DataExportTag": "income"
    })
    all_qids["income"] = q
    print(f"  {q}: income")

    # Education (MC/SAVR)
    q = create_question(survey_id, {
        "QuestionText": (
            '<span style="font-size:19px;">'
            'What is your highest level of education?'
            '</span>'
        ),
        "QuestionType": "MC",
        "Selector": "SAVR",
        "SubSelector": "TX",
        "Configuration": {"QuestionDescriptionOption": "UseText"},
        "Choices": {
            "1": {"Display": "High school or equivalent"},
            "2": {"Display": "Some college"},
            "3": {"Display": "Bachelor's degree"},
            "4": {"Display": "Master's degree"},
            "5": {"Display": "Doctorate"},
            "6": {"Display": "Other"}
        },
        "ChoiceOrder": ["1", "2", "3", "4", "5", "6"],
        "Validation": {"Settings": {"ForceResponse": "RequestResponse",
                                    "ForceResponseType": "RequestResponse", "Type": "None"}},
        "Language": [],
        "DataExportTag": "education"
    })
    all_qids["education"] = q
    print(f"  {q}: education")

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

    # AI usage screening block
    api_call("PUT", f"/survey-definitions/{survey_id}/blocks/{ai_screen_block}", {
        "Type": "Standard",
        "Description": "ai_usage_screening",
        "BlockElements": [
            {"Type": "Question", "QuestionID": all_qids["timer_aiscreen"]},
            {"Type": "Question", "QuestionID": all_qids["ai_usage_screen"]},
        ],
        "Options": BLOCK_OPTS
    })

    # Recent experience block
    api_call("PUT", f"/survey-definitions/{survey_id}/blocks/{experience_block}", {
        "Type": "Standard",
        "Description": "recent_experience",
        "BlockElements": [
            {"Type": "Question", "QuestionID": all_qids["timer_experience"]},
            {"Type": "Question", "QuestionID": all_qids["exp_intro"]},
            {"Type": "Question", "QuestionID": all_qids["product_category"]},
            {"Type": "Question", "QuestionID": all_qids["ai_used"]},
            {"Type": "Page Break"},
            {"Type": "Question", "QuestionID": all_qids["ai_prompt"]},
            {"Type": "Question", "QuestionID": all_qids["ai_recommendation"]},
            {"Type": "Page Break"},
            {"Type": "Question", "QuestionID": all_qids["purchased"]},
            {"Type": "Question", "QuestionID": all_qids["satisfaction"]},
        ],
        "Options": BLOCK_OPTS
    })

    # Consideration set block
    api_call("PUT", f"/survey-definitions/{survey_id}/blocks/{consideration_block}", {
        "Type": "Standard",
        "Description": "consideration_set",
        "BlockElements": [
            {"Type": "Question", "QuestionID": all_qids["timer_consideration"]},
            {"Type": "Question", "QuestionID": all_qids["asked_alternatives"]},
            {"Type": "Question", "QuestionID": all_qids["products_considered"]},
            {"Type": "Page Break"},
            {"Type": "Question", "QuestionID": all_qids["best_product_belief"]},
            {"Type": "Question", "QuestionID": all_qids["quality_confidence"]},
        ],
        "Options": BLOCK_OPTS
    })

    # Verification behavior block
    api_call("PUT", f"/survey-definitions/{survey_id}/blocks/{verification_block}", {
        "Type": "Standard",
        "Description": "verification_behavior",
        "BlockElements": [
            {"Type": "Question", "QuestionID": all_qids["timer_verification"]},
            {"Type": "Question", "QuestionID": all_qids["verify_freq"]},
            {"Type": "Question", "QuestionID": all_qids["trust_drivers"]},
        ],
        "Options": BLOCK_OPTS
    })

    # Awareness manipulation block
    api_call("PUT", f"/survey-definitions/{survey_id}/blocks/{awareness_block}", {
        "Type": "Standard",
        "Description": "awareness_manipulation",
        "BlockElements": [
            {"Type": "Question", "QuestionID": all_qids["timer_awareness"]},
            {"Type": "Question", "QuestionID": all_qids["awareness_text"]},
            {"Type": "Page Break"},
            {"Type": "Question", "QuestionID": all_qids["post_awareness_reaction"]},
            {"Type": "Question", "QuestionID": all_qids["change_behavior"]},
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
            {"Type": "Question", "QuestionID": all_qids["income"]},
            {"Type": "Question", "QuestionID": all_qids["education"]},
            {"Type": "Page Break"},
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

    # AI usage screening branch (if "No" -> EndSurvey with thank you)
    ai_screen_branch = {
        "Type": "Branch",
        "FlowID": "FL_50",
        "Description": "AI Usage Screening Branch",
        "BranchLogic": {
            "0": {
                "0": {
                    "LogicType": "Question",
                    "QuestionID": all_qids["ai_usage_screen"],
                    "QuestionIsInLoop": "no",
                    "ChoiceLocator": f'q://{all_qids["ai_usage_screen"]}/SelectableChoice/2',
                    "Operator": "Selected",
                    "Type": "Expression",
                    "Description": '<span class="ConjDesc">If</span> <span class="QuestionDesc">ai_usage_screen</span> <span class="LeftOpDesc">No</span> <span class="OpDesc">Is Selected</span>'
                },
                "Type": "If"
            },
            "Type": "BooleanExpression"
        },
        "Flow": [
            {
                "Type": "EndSurvey",
                "FlowID": "FL_51",
                "EndingType": "Advanced",
                "Options": {
                    "Advanced": "true",
                    "SurveyTermination": "DisplayMessage",
                    "EOSMessage": "MS_0f26k4kl5jOeYkm"
                }
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
            # AI usage screening block
            {"Type": "Standard", "ID": ai_screen_block, "FlowID": "FL_3", "Autofill": []},
            # AI usage screening branch (if No -> EndSurvey)
            ai_screen_branch,
            # Study blocks (all AI users see these in order)
            {"Type": "Standard", "ID": experience_block, "FlowID": "FL_4", "Autofill": []},
            {"Type": "Standard", "ID": consideration_block, "FlowID": "FL_5", "Autofill": []},
            {"Type": "Standard", "ID": verification_block, "FlowID": "FL_6", "Autofill": []},
            {"Type": "Standard", "ID": awareness_block, "FlowID": "FL_7", "Autofill": []},
            {"Type": "Standard", "ID": demo_block, "FlowID": "FL_12", "Autofill": []},
            {"Type": "EndSurvey", "FlowID": "FL_99"}
        ],
        "Properties": {"Count": 30}
    }

    api_call("PUT", f"/survey-definitions/{survey_id}/flow", flow)
    print("  Flow set: mobile screen -> consent -> attn check -> "
          "AI screen (No -> end) -> experience -> consideration -> "
          "verification -> awareness -> demo -> end")

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
    print("  Options set (slide transitions, blue theme, centered buttons, Prolific redirect)")

    # =================================================================
    # Done!
    # =================================================================
    edit_url = f"https://okstatebusiness.az1.qualtrics.com/survey-builder/{survey_id}/edit"
    preview_url = f"https://okstatebusiness.az1.qualtrics.com/jfe/preview/{survey_id}"

    print("\n" + "=" * 70)
    print("SURVEY CREATED SUCCESSFULLY!")
    print("=" * 70)
    print(f"Survey ID:  {survey_id}")
    print(f"Edit:       {edit_url}")
    print(f"Preview:    {preview_url}")
    print()
    print("Design: Field survey of real AI shoppers, N=400")
    print()
    print("Structure:")
    print("  screening          -> consent, attention check (Horse), passed msg")
    print("  ai_usage_screening -> 'Used AI for shopping in past 3 months?' (No -> end)")
    print("  recent_experience  -> category, AI used, prompt, recommendation, purchase, satisfaction")
    print("  consideration_set  -> asked alternatives, products considered, best product, quality confidence")
    print("  verification       -> verify frequency, trust drivers (multi-select)")
    print("  awareness_manip    -> brand bias text (8s timer) | reaction MC | change behavior text")
    print("  demographics       -> age, gender, income, education, comments")
    print()
    print("Sections:")
    print("  1. AI usage screening (branch: No -> EndSurvey)")
    print("  2. Recent AI shopping experience (open-ended + structured)")
    print("  3. Consideration set awareness (4 questions)")
    print("  4. Verification behavior (frequency + trust drivers)")
    print("  5. Awareness manipulation (brand bias reveal + reactions)")
    print("  6. Demographics (age, gender, income, education)")
    print()
    print("DataExportTags:")
    for tag, qid in all_qids.items():
        print(f"  {tag:25s} -> {qid}")
    print()
    print("IMPORTANT: Update EOSRedirectURL with actual Prolific completion code before launch!")
    print("IMPORTANT: Update consent form with approved IRB text before launch!")
    print("IMPORTANT: Non-AI-users are screened out via branch logic (No -> EndSurvey)")


if __name__ == "__main__":
    main()
