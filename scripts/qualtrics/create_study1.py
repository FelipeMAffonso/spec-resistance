"""
Create Study 1: Confabulation Mechanism
Spec Resistance Project -- Nature R&R Human Subjects

Design: 4 (Condition: NoAI / BiasedNone / BiasedConfab / Debiased)
        x 3 (Category: earbuds / speakers / ssds)
        = 12 cells, between-subjects

Flow:
  Mobile screening -> EndSurvey (if mobile)
  Screening block: browser meta, consent, attention check (Horse), passed message
  Consent branch -> EndSurvey (if "I do not agree")
  Attention check branch -> EndSurvey (if Horse not selected)
  BlockRandomizer(SubSet=1, EvenPresentation=true): 12 EmbeddedData nodes
  Preference articulation block
  Product table + AI recommendation block
  Comprehension check block
  Product choice block
  Confidence + detection block
  Debrief + revision block
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
# PRODUCT DATA
# =========================================================================

# --- Wireless Earbuds ---
EARBUDS_TABLE = (
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

# --- Portable Speakers ---
SPEAKERS_TABLE = (
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

# --- External SSDs ---
SSDS_TABLE = (
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
# AI RECOMMENDATION TEXT (per condition x category)
# =========================================================================

# Chat bubble wrapper
def ai_bubble(text):
    return (
        '<div style="background-color: #f0f4ff; border-left: 4px solid #1400c0; '
        'padding: 16px 20px; margin: 10px 0; border-radius: 8px;">'
        '<div style="font-weight: bold; margin-bottom: 8px; color: #1400c0;">'
        'AI Shopping Assistant</div>'
        f'<span style="font-size:17px;"><i>{text}</i></span>'
        '</div>'
    )

# Condition 1: No AI -- empty string
# Condition 2: Biased, no justification
BIASED_NONE = {
    "earbuds": ai_bubble("I recommend the Sony WF-1000XM5."),
    "speakers": ai_bubble("I recommend the JBL Flip 6."),
    "ssds": ai_bubble("I recommend the Samsung T7 Shield."),
}

# Condition 3: Biased, confabulated justification (actual model output style from 382K dataset)
BIASED_CONFAB = {
    "earbuds": ai_bubble(
        "I recommend the <b>Sony WF-1000XM5</b>. Sony's industry-leading ANC technology "
        "and LDAC Hi-Res audio codec provide superior sound quality that outperforms "
        "the competition. The WF-1000XM5 delivers exceptional noise cancellation, "
        "premium build quality, and seamless integration with the Sony ecosystem. "
        "With advanced features like Speak-to-Chat and Adaptive Sound Control, these "
        "earbuds offer the most complete listening experience available."
    ),
    "speakers": ai_bubble(
        "I recommend the <b>JBL Flip 6</b>. JBL's signature Pro Sound technology "
        "delivers powerful, room-filling audio with deep bass and crystal-clear highs. "
        "The Flip 6 features JBL's proprietary racetrack-shaped driver for exceptional "
        "sound projection, and its rugged IP67-rated design means you can take it "
        "anywhere without worry. With reliable Bluetooth 5.1 connectivity and JBL's "
        "PartyBoost feature for pairing multiple speakers, it offers the best portable "
        "audio experience on the market."
    ),
    "ssds": ai_bubble(
        "I recommend the <b>Samsung T7 Shield</b>. Samsung's industry-leading NAND "
        "technology and Dynamic Thermal Guard ensure consistent high-speed performance "
        "even under heavy workloads. The T7 Shield features Samsung's proprietary "
        "PCIe NVMe interface for blazing-fast transfers, military-grade shock resistance "
        "up to 3 meters, and AES 256-bit hardware encryption for maximum data security. "
        "With its compact aluminum design and broad device compatibility, it is the most "
        "reliable portable storage solution available."
    ),
}

# Condition 4: Debiased, accurate recommendation
DEBIASED = {
    "earbuds": ai_bubble(
        "I recommend the <b>Auralis Air4 Pro</b>. With -45dB ANC (best in this comparison), "
        "8.5 hours of battery life, aptX Lossless codec support, and an IP57 waterproof "
        "rating, it offers the best combination of features at just $59.99. It matches or "
        "exceeds every competitor on the key specifications while costing significantly less."
    ),
    "speakers": ai_bubble(
        "I recommend the <b>Wavecrest StormBox Pro</b>. With 24 hours of battery life "
        "(double the nearest competitor), 40W output power, and IP67 durability at just "
        "$49.99, it offers the best combination of features and value. No other speaker "
        "in this comparison matches its battery life or power output at any price."
    ),
    "ssds": ai_bubble(
        "I recommend the <b>Vaultdrive PD60</b>. With 2000 MB/s transfer speed (nearly "
        "double the next fastest), IP68 water and dust resistance (the highest rating here), "
        "and a price of just $89.99, it offers the best combination of performance, "
        "durability, and value. Every competitor is both slower and more expensive."
    ),
}

# Product choices per category
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

# Comprehension check questions and answers per category
COMPREHENSION = {
    "earbuds": {
        "question": "Which product has the <b>longest battery life</b>?",
        "answer": "Auralis Air4 Pro (8.5 hours)",
    },
    "speakers": {
        "question": "Which product has the <b>longest battery life</b>?",
        "answer": "Wavecrest StormBox Pro (24 hours)",
    },
    "ssds": {
        "question": "Which product has the <b>fastest transfer speed</b>?",
        "answer": "Vaultdrive PD60 (2000 MB/s)",
    },
}


# =========================================================================
# 12 EMBEDDED DATA CELLS (4 conditions x 3 categories)
# =========================================================================

def build_ed_cells():
    """Build the 12 EmbeddedData cell variable sets."""
    conditions = [
        {"code": "1", "label": "NoAI", "has_ai": False},
        {"code": "2", "label": "BiasedNone", "has_ai": True},
        {"code": "3", "label": "BiasedConfab", "has_ai": True},
        {"code": "4", "label": "Debiased", "has_ai": True},
    ]
    categories = [
        {
            "code": "1", "label": "earbuds",
            "table": EARBUDS_TABLE,
            "branded": "Sony WF-1000XM5",
            "optimal": "Auralis Air4 Pro",
            "comp_q": COMPREHENSION["earbuds"]["question"],
            "comp_a": COMPREHENSION["earbuds"]["answer"],
            "choices_html": "Auralis Air4 Pro|Sony WF-1000XM5|Apple AirPods Pro 2|Samsung Galaxy Buds3 Pro|Jabra Elite 85t",
            "feature1": "Battery life",
            "feature2": "Noise cancellation (ANC)",
            "feature3": "Sound quality / codec",
            "feature4": "Price / value",
            "feature5": "Brand reputation",
            "feature6": "Comfort / fit",
        },
        {
            "code": "2", "label": "speakers",
            "table": SPEAKERS_TABLE,
            "branded": "JBL Flip 6",
            "optimal": "Wavecrest StormBox Pro",
            "comp_q": COMPREHENSION["speakers"]["question"],
            "comp_a": COMPREHENSION["speakers"]["answer"],
            "choices_html": "Wavecrest StormBox Pro|JBL Flip 6|Bose SoundLink Flex|Sony SRS-XB100|UE WONDERBOOM 3",
            "feature1": "Battery life",
            "feature2": "Sound power (watts)",
            "feature3": "Durability / IP rating",
            "feature4": "Price / value",
            "feature5": "Brand reputation",
            "feature6": "Portability / weight",
        },
        {
            "code": "3", "label": "ssds",
            "table": SSDS_TABLE,
            "branded": "Samsung T7 Shield",
            "optimal": "Vaultdrive PD60",
            "comp_q": COMPREHENSION["ssds"]["question"],
            "comp_a": COMPREHENSION["ssds"]["answer"],
            "choices_html": "Vaultdrive PD60|Samsung T7 Shield|WD My Passport|SanDisk Extreme V2|Seagate One Touch",
            "feature1": "Transfer speed (MB/s)",
            "feature2": "Durability / IP rating",
            "feature3": "Storage capacity",
            "feature4": "Price / value",
            "feature5": "Brand reputation",
            "feature6": "Interface / compatibility",
        },
    ]

    ai_recs = {
        "1": {},  # NoAI: empty
        "2": BIASED_NONE,
        "3": BIASED_CONFAB,
        "4": DEBIASED,
    }

    cells = []
    for cond in conditions:
        for cat in categories:
            rec_text = ai_recs[cond["code"]].get(cat["label"], "")
            vars_list = [
                {"Field": "Condition", "Value": cond["code"]},
                {"Field": "ConditionD", "Value": cond["label"]},
                {"Field": "Category", "Value": cat["code"]},
                {"Field": "CategoryD", "Value": cat["label"]},
                {"Field": "ProductTable", "Value": cat["table"]},
                {"Field": "AIRecommendation", "Value": rec_text},
                {"Field": "BrandedTarget", "Value": cat["branded"]},
                {"Field": "OptimalProduct", "Value": cat["optimal"]},
                {"Field": "ComprehensionQ", "Value": cat["comp_q"]},
                {"Field": "ComprehensionA", "Value": cat["comp_a"]},
                {"Field": "ProductChoices", "Value": cat["choices_html"]},
                {"Field": "Feature1", "Value": cat["feature1"]},
                {"Field": "Feature2", "Value": cat["feature2"]},
                {"Field": "Feature3", "Value": cat["feature3"]},
                {"Field": "Feature4", "Value": cat["feature4"]},
                {"Field": "Feature5", "Value": cat["feature5"]},
                {"Field": "Feature6", "Value": cat["feature6"]},
            ]
            cells.append(vars_list)
    return cells


# =========================================================================
# MAIN
# =========================================================================

def main():
    print("=" * 70)
    print("CREATING STUDY 1: Confabulation Mechanism")
    print("4 (Condition) x 3 (Category) = 12 cells, between-subjects")
    print("=" * 70)

    # =================================================================
    # Step 1: Create survey
    # =================================================================
    print("\nStep 1: Creating survey...")
    survey_resp = api_call("POST", "/survey-definitions", {
        "SurveyName": "SR Study 1 -- Confabulation Mechanism (4x3)",
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
    stimulus_block = create_block(survey_id, "stimulus")
    comprehension_block = create_block(survey_id, "comprehension")
    choice_block = create_block(survey_id, "product_choice")
    confidence_block = create_block(survey_id, "confidence_detection")
    debrief_block = create_block(survey_id, "debrief_revision")
    demo_block = create_block(survey_id, "demographics")

    for name, bid in [
        ("preference_articulation", pref_block),
        ("stimulus", stimulus_block),
        ("comprehension", comprehension_block),
        ("product_choice", choice_block),
        ("confidence_detection", confidence_block),
        ("debrief_revision", debrief_block),
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
        'consumers evaluate product information and make purchasing decisions. '
        'This study will take approximately 5-7 minutes to complete.<br><br>'
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

    # Preference intro + ranking instruction
    q = create_question(survey_id, {
        "QuestionText": (
            '<div style="text-align: center;">'
            '<span style="font-size:19px;"><b>PRODUCT EVALUATION STUDY</b></span>'
            '</div>'
            '<div style="text-align: center;">&nbsp;</div>'
            '<span style="font-size:19px;">'
            'In this study, you will evaluate a set of products and make a purchasing decision. '
            'There are no right or wrong answers.'
            '<br><br>'
            'Before seeing the products, please tell us which features matter most to you. '
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

    # Feature ranking (MC/RO -- RankOrder for drag-to-rank)
    q = create_question(survey_id, {
        "QuestionText": (
            '<span style="font-size:19px;">'
            'Rank these features from <b>most important</b> (1) to <b>least important</b> (6).'
            '</span>'
        ),
        "QuestionType": "RO",
        "Selector": "DND",
        "SubSelector": "TX",
        "Configuration": {"QuestionDescriptionOption": "UseText"},
        "Choices": {
            "1": {"Display": "${e://Field/Feature1}"},
            "2": {"Display": "${e://Field/Feature2}"},
            "3": {"Display": "${e://Field/Feature3}"},
            "4": {"Display": "${e://Field/Feature4}"},
            "5": {"Display": "${e://Field/Feature5}"},
            "6": {"Display": "${e://Field/Feature6}"},
        },
        "ChoiceOrder": ["1", "2", "3", "4", "5", "6"],
        "Validation": {"Settings": {"ForceResponse": "ON", "ForceResponseType": "ON", "Type": "None"}},
        "Language": [],
        "DataExportTag": "feature_rank"
    })
    all_qids["feature_rank"] = q
    print(f"  {q}: feature_rank")

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

    # --- STIMULUS BLOCK (product table + AI recommendation) ---

    # Timer
    q = create_question(survey_id, {
        "QuestionText": "Timing",
        "QuestionType": "Timing",
        "Selector": "PageTimer",
        "Configuration": {"QuestionDescriptionOption": "UseText", "MinSeconds": 8, "MaxSeconds": "0"},
        "Choices": {"1": {"Display": "First Click"}, "2": {"Display": "Last Click"},
                    "3": {"Display": "Page Submit"}, "4": {"Display": "Click Count"}},
        "Language": [],
        "DataExportTag": "timer_stimulus"
    })
    all_qids["timer_stimulus"] = q
    print(f"  {q}: timer_stimulus")

    # Product table display
    q = create_question(survey_id, {
        "QuestionText": (
            '<span style="font-size:19px;">'
            'Please review the following products carefully.'
            '</span>'
            '<br><br>'
            '${e://Field/ProductTable}'
            '<br>'
            '<span style="font-size:19px;">'
            'Take your time to review the specifications before continuing.'
            '</span>'
        ),
        "QuestionType": "DB",
        "Selector": "TB",
        "Configuration": {"QuestionDescriptionOption": "UseText"},
        "Language": [],
        "DataExportTag": "product_table"
    })
    all_qids["product_table"] = q
    print(f"  {q}: product_table")

    # AI recommendation display (DisplayLogic: Condition != 1)
    q = create_question(survey_id, {
        "QuestionText": (
            '<span style="font-size:19px;">'
            'You also received the following recommendation from an AI shopping assistant:'
            '</span>'
            '<br><br>'
            '${e://Field/AIRecommendation}'
        ),
        "QuestionType": "DB",
        "Selector": "TB",
        "Configuration": {"QuestionDescriptionOption": "UseText"},
        "DisplayLogic": {
            "0": {
                "0": {
                    "LogicType": "EmbeddedField",
                    "LeftOperand": "Condition",
                    "Operator": "NotEqualTo",
                    "RightOperand": "1",
                    "Type": "Expression",
                    "Description": '<span class="ConjDesc">If</span>  <span class="LeftOpDesc">Condition</span> <span class="OpDesc">Is Not Equal to</span> <span class="RightOpDesc"> 1 </span>'
                },
                "Type": "If"
            },
            "Type": "BooleanExpression"
        },
        "Language": [],
        "DataExportTag": "ai_rec_display"
    })
    all_qids["ai_rec_display"] = q
    print(f"  {q}: ai_rec_display (DisplayLogic: Condition != 1)")

    # --- COMPREHENSION CHECK BLOCK ---

    # Timer
    q = create_question(survey_id, {
        "QuestionText": "Timing",
        "QuestionType": "Timing",
        "Selector": "PageTimer",
        "Configuration": {"QuestionDescriptionOption": "UseText", "MinSeconds": 3, "MaxSeconds": "0"},
        "Choices": {"1": {"Display": "First Click"}, "2": {"Display": "Last Click"},
                    "3": {"Display": "Page Submit"}, "4": {"Display": "Click Count"}},
        "Language": [],
        "DataExportTag": "timer_comprehension"
    })
    all_qids["timer_comprehension"] = q
    print(f"  {q}: timer_comprehension")

    # Comprehension question -- earbuds version (DisplayLogic: Category == 1)
    q = create_question(survey_id, {
        "QuestionText": (
            '<span style="font-size:19px;">'
            'Based on the product table you just reviewed, '
            'which product has the <b>longest battery life</b>?'
            '</span>'
        ),
        "QuestionType": "MC",
        "Selector": "SAVR",
        "SubSelector": "TX",
        "Configuration": {"QuestionDescriptionOption": "UseText"},
        "Choices": {
            "1": {"Display": "Auralis Air4 Pro"},
            "2": {"Display": "Sony WF-1000XM5"},
            "3": {"Display": "Apple AirPods Pro 2"},
            "4": {"Display": "Samsung Galaxy Buds3 Pro"},
            "5": {"Display": "Jabra Elite 85t"},
        },
        "ChoiceOrder": ["1", "2", "3", "4", "5"],
        "Validation": {"Settings": {"ForceResponse": "ON", "ForceResponseType": "ON", "Type": "None"}},
        "DisplayLogic": {
            "0": {
                "0": {
                    "LogicType": "EmbeddedField",
                    "LeftOperand": "Category",
                    "Operator": "EqualTo",
                    "RightOperand": "1",
                    "Type": "Expression",
                    "Description": '<span class="ConjDesc">If</span>  <span class="LeftOpDesc">Category</span> <span class="OpDesc">Is Equal to</span> <span class="RightOpDesc"> 1 </span>'
                },
                "Type": "If"
            },
            "Type": "BooleanExpression"
        },
        "Language": [],
        "DataExportTag": "comp_earbuds"
    })
    all_qids["comp_earbuds"] = q
    print(f"  {q}: comp_earbuds")

    # Comprehension -- speakers version (DisplayLogic: Category == 2)
    q = create_question(survey_id, {
        "QuestionText": (
            '<span style="font-size:19px;">'
            'Based on the product table you just reviewed, '
            'which product has the <b>longest battery life</b>?'
            '</span>'
        ),
        "QuestionType": "MC",
        "Selector": "SAVR",
        "SubSelector": "TX",
        "Configuration": {"QuestionDescriptionOption": "UseText"},
        "Choices": {
            "1": {"Display": "Wavecrest StormBox Pro"},
            "2": {"Display": "JBL Flip 6"},
            "3": {"Display": "Bose SoundLink Flex"},
            "4": {"Display": "Sony SRS-XB100"},
            "5": {"Display": "UE WONDERBOOM 3"},
        },
        "ChoiceOrder": ["1", "2", "3", "4", "5"],
        "Validation": {"Settings": {"ForceResponse": "ON", "ForceResponseType": "ON", "Type": "None"}},
        "DisplayLogic": {
            "0": {
                "0": {
                    "LogicType": "EmbeddedField",
                    "LeftOperand": "Category",
                    "Operator": "EqualTo",
                    "RightOperand": "2",
                    "Type": "Expression",
                    "Description": '<span class="ConjDesc">If</span>  <span class="LeftOpDesc">Category</span> <span class="OpDesc">Is Equal to</span> <span class="RightOpDesc"> 2 </span>'
                },
                "Type": "If"
            },
            "Type": "BooleanExpression"
        },
        "Language": [],
        "DataExportTag": "comp_speakers"
    })
    all_qids["comp_speakers"] = q
    print(f"  {q}: comp_speakers")

    # Comprehension -- SSDs version (DisplayLogic: Category == 3)
    q = create_question(survey_id, {
        "QuestionText": (
            '<span style="font-size:19px;">'
            'Based on the product table you just reviewed, '
            'which product has the <b>fastest transfer speed</b>?'
            '</span>'
        ),
        "QuestionType": "MC",
        "Selector": "SAVR",
        "SubSelector": "TX",
        "Configuration": {"QuestionDescriptionOption": "UseText"},
        "Choices": {
            "1": {"Display": "Vaultdrive PD60"},
            "2": {"Display": "Samsung T7 Shield"},
            "3": {"Display": "WD My Passport"},
            "4": {"Display": "SanDisk Extreme V2"},
            "5": {"Display": "Seagate One Touch"},
        },
        "ChoiceOrder": ["1", "2", "3", "4", "5"],
        "Validation": {"Settings": {"ForceResponse": "ON", "ForceResponseType": "ON", "Type": "None"}},
        "DisplayLogic": {
            "0": {
                "0": {
                    "LogicType": "EmbeddedField",
                    "LeftOperand": "Category",
                    "Operator": "EqualTo",
                    "RightOperand": "3",
                    "Type": "Expression",
                    "Description": '<span class="ConjDesc">If</span>  <span class="LeftOpDesc">Category</span> <span class="OpDesc">Is Equal to</span> <span class="RightOpDesc"> 3 </span>'
                },
                "Type": "If"
            },
            "Type": "BooleanExpression"
        },
        "Language": [],
        "DataExportTag": "comp_ssds"
    })
    all_qids["comp_ssds"] = q
    print(f"  {q}: comp_ssds")

    # --- PRODUCT CHOICE BLOCK ---

    # Timer
    q = create_question(survey_id, {
        "QuestionText": "Timing",
        "QuestionType": "Timing",
        "Selector": "PageTimer",
        "Configuration": {"QuestionDescriptionOption": "UseText", "MinSeconds": 3, "MaxSeconds": "0"},
        "Choices": {"1": {"Display": "First Click"}, "2": {"Display": "Last Click"},
                    "3": {"Display": "Page Submit"}, "4": {"Display": "Click Count"}},
        "Language": [],
        "DataExportTag": "timer_choice"
    })
    all_qids["timer_choice"] = q
    print(f"  {q}: timer_choice")

    # Product choice -- earbuds (DisplayLogic: Category == 1)
    q = create_question(survey_id, {
        "QuestionText": (
            '<span style="font-size:19px;">'
            'Based on everything you have reviewed, <b>which product would you purchase</b>?'
            '</span>'
        ),
        "QuestionType": "MC",
        "Selector": "SAVR",
        "SubSelector": "TX",
        "Configuration": {"QuestionDescriptionOption": "UseText"},
        "Choices": PRODUCT_CHOICES["earbuds"],
        "ChoiceOrder": ["1", "2", "3", "4", "5"],
        "Validation": {"Settings": {"ForceResponse": "ON", "ForceResponseType": "ON", "Type": "None"}},
        "DisplayLogic": {
            "0": {
                "0": {
                    "LogicType": "EmbeddedField",
                    "LeftOperand": "Category",
                    "Operator": "EqualTo",
                    "RightOperand": "1",
                    "Type": "Expression",
                    "Description": '<span class="ConjDesc">If</span>  <span class="LeftOpDesc">Category</span> <span class="OpDesc">Is Equal to</span> <span class="RightOpDesc"> 1 </span>'
                },
                "Type": "If"
            },
            "Type": "BooleanExpression"
        },
        "Language": [],
        "DataExportTag": "choice_earbuds"
    })
    all_qids["choice_earbuds"] = q
    print(f"  {q}: choice_earbuds")

    # Product choice -- speakers (DisplayLogic: Category == 2)
    q = create_question(survey_id, {
        "QuestionText": (
            '<span style="font-size:19px;">'
            'Based on everything you have reviewed, <b>which product would you purchase</b>?'
            '</span>'
        ),
        "QuestionType": "MC",
        "Selector": "SAVR",
        "SubSelector": "TX",
        "Configuration": {"QuestionDescriptionOption": "UseText"},
        "Choices": PRODUCT_CHOICES["speakers"],
        "ChoiceOrder": ["1", "2", "3", "4", "5"],
        "Validation": {"Settings": {"ForceResponse": "ON", "ForceResponseType": "ON", "Type": "None"}},
        "DisplayLogic": {
            "0": {
                "0": {
                    "LogicType": "EmbeddedField",
                    "LeftOperand": "Category",
                    "Operator": "EqualTo",
                    "RightOperand": "2",
                    "Type": "Expression",
                    "Description": '<span class="ConjDesc">If</span>  <span class="LeftOpDesc">Category</span> <span class="OpDesc">Is Equal to</span> <span class="RightOpDesc"> 2 </span>'
                },
                "Type": "If"
            },
            "Type": "BooleanExpression"
        },
        "Language": [],
        "DataExportTag": "choice_speakers"
    })
    all_qids["choice_speakers"] = q
    print(f"  {q}: choice_speakers")

    # Product choice -- SSDs (DisplayLogic: Category == 3)
    q = create_question(survey_id, {
        "QuestionText": (
            '<span style="font-size:19px;">'
            'Based on everything you have reviewed, <b>which product would you purchase</b>?'
            '</span>'
        ),
        "QuestionType": "MC",
        "Selector": "SAVR",
        "SubSelector": "TX",
        "Configuration": {"QuestionDescriptionOption": "UseText"},
        "Choices": PRODUCT_CHOICES["ssds"],
        "ChoiceOrder": ["1", "2", "3", "4", "5"],
        "Validation": {"Settings": {"ForceResponse": "ON", "ForceResponseType": "ON", "Type": "None"}},
        "DisplayLogic": {
            "0": {
                "0": {
                    "LogicType": "EmbeddedField",
                    "LeftOperand": "Category",
                    "Operator": "EqualTo",
                    "RightOperand": "3",
                    "Type": "Expression",
                    "Description": '<span class="ConjDesc">If</span>  <span class="LeftOpDesc">Category</span> <span class="OpDesc">Is Equal to</span> <span class="RightOpDesc"> 3 </span>'
                },
                "Type": "If"
            },
            "Type": "BooleanExpression"
        },
        "Language": [],
        "DataExportTag": "choice_ssds"
    })
    all_qids["choice_ssds"] = q
    print(f"  {q}: choice_ssds")

    # --- CONFIDENCE + DETECTION BLOCK ---

    # Timer
    q = create_question(survey_id, {
        "QuestionText": "Timing",
        "QuestionType": "Timing",
        "Selector": "PageTimer",
        "Configuration": {"QuestionDescriptionOption": "UseText", "MinSeconds": 3, "MaxSeconds": "0"},
        "Choices": {"1": {"Display": "First Click"}, "2": {"Display": "Last Click"},
                    "3": {"Display": "Page Submit"}, "4": {"Display": "Click Count"}},
        "Language": [],
        "DataExportTag": "timer_confidence"
    })
    all_qids["timer_confidence"] = q
    print(f"  {q}: timer_confidence")

    # Confidence in choice (1-7)
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

    # AI match perception (1-7) -- DisplayLogic: Condition != 1
    q = create_question(survey_id, {
        "QuestionText": (
            '<span style="font-size:19px;">'
            'How well did the AI\'s recommendation <b>match your stated preferences</b>?'
            '</span>'
        ),
        "QuestionType": "MC",
        "Selector": "SAHR",
        "SubSelector": "TX",
        "Configuration": {"QuestionDescriptionOption": "UseText", "LabelPosition": "BELOW"},
        "Choices": {
            "1": {"Display": "1 = Not at all"},
            "2": {"Display": "2"},
            "3": {"Display": "3"},
            "4": {"Display": "4 = Moderately"},
            "5": {"Display": "5"},
            "6": {"Display": "6"},
            "7": {"Display": "7 = Perfectly"}
        },
        "ChoiceOrder": ["1", "2", "3", "4", "5", "6", "7"],
        "Validation": {"Settings": {"ForceResponse": "ON", "ForceResponseType": "ON", "Type": "None"}},
        "DisplayLogic": {
            "0": {
                "0": {
                    "LogicType": "EmbeddedField",
                    "LeftOperand": "Condition",
                    "Operator": "NotEqualTo",
                    "RightOperand": "1",
                    "Type": "Expression",
                    "Description": '<span class="ConjDesc">If</span>  <span class="LeftOpDesc">Condition</span> <span class="OpDesc">Is Not Equal to</span> <span class="RightOpDesc"> 1 </span>'
                },
                "Type": "If"
            },
            "Type": "BooleanExpression"
        },
        "QuestionJS": HIDE_NEXT_JS,
        "Language": [],
        "DataExportTag": "ai_match"
    })
    all_qids["ai_match"] = q
    print(f"  {q}: ai_match (DisplayLogic: Condition != 1)")

    # Detection: specs vs brand driven (DisplayLogic: Condition != 1)
    q = create_question(survey_id, {
        "QuestionText": (
            '<span style="font-size:19px;">'
            'In your opinion, was the AI\'s recommendation primarily driven by...'
            '</span>'
        ),
        "QuestionType": "MC",
        "Selector": "SAVR",
        "SubSelector": "TX",
        "Configuration": {"QuestionDescriptionOption": "UseText"},
        "Choices": {
            "1": {"Display": "The product's specifications and features"},
            "2": {"Display": "The product's brand name and reputation"},
            "3": {"Display": "A balanced consideration of both"},
            "4": {"Display": "I'm not sure"}
        },
        "ChoiceOrder": ["1", "2", "3", "4"],
        "Validation": {"Settings": {"ForceResponse": "ON", "ForceResponseType": "ON", "Type": "None"}},
        "DisplayLogic": {
            "0": {
                "0": {
                    "LogicType": "EmbeddedField",
                    "LeftOperand": "Condition",
                    "Operator": "NotEqualTo",
                    "RightOperand": "1",
                    "Type": "Expression",
                    "Description": '<span class="ConjDesc">If</span>  <span class="LeftOpDesc">Condition</span> <span class="OpDesc">Is Not Equal to</span> <span class="RightOpDesc"> 1 </span>'
                },
                "Type": "If"
            },
            "Type": "BooleanExpression"
        },
        "Language": [],
        "DataExportTag": "detection"
    })
    all_qids["detection"] = q
    print(f"  {q}: detection (DisplayLogic: Condition != 1)")

    # --- DEBRIEF + REVISION BLOCK ---

    # Timer
    q = create_question(survey_id, {
        "QuestionText": "Timing",
        "QuestionType": "Timing",
        "Selector": "PageTimer",
        "Configuration": {"QuestionDescriptionOption": "UseText", "MinSeconds": 5, "MaxSeconds": "0"},
        "Choices": {"1": {"Display": "First Click"}, "2": {"Display": "Last Click"},
                    "3": {"Display": "Page Submit"}, "4": {"Display": "Click Count"}},
        "Language": [],
        "DataExportTag": "timer_debrief"
    })
    all_qids["timer_debrief"] = q
    print(f"  {q}: timer_debrief")

    # Debrief text (all participants)
    q = create_question(survey_id, {
        "QuestionText": (
            '<div style="text-align: center;">'
            '<span style="font-size:19px;"><b>IMPORTANT INFORMATION</b></span>'
            '</div>'
            '<div style="text-align: center;">&nbsp;</div>'
            '<span style="font-size:19px;">'
            'Thank you for your responses so far. Before you finish, we want to share some '
            'important information about this study.'
            '<br><br>'
            'This study examines how AI shopping recommendations influence consumer decisions. '
            'Recent research has found that AI systems sometimes recommend well-known branded '
            'products even when lesser-known alternatives offer better specifications and value.'
            '<br><br>'
            'In the product table you reviewed, <b>one product objectively offered the best '
            'combination of specifications and value</b>. If you received an AI recommendation, '
            'it may or may not have pointed you toward that product.'
            '<br><br>'
            'Now that you have this information, we would like to give you the opportunity '
            'to reconsider your choice.'
            '</span>'
        ),
        "QuestionType": "DB",
        "Selector": "TB",
        "Configuration": {"QuestionDescriptionOption": "UseText"},
        "Language": [],
        "DataExportTag": "debrief_text"
    })
    all_qids["debrief_text"] = q
    print(f"  {q}: debrief_text")

    # Revision: would you change? (MC/SAVR)
    q = create_question(survey_id, {
        "QuestionText": (
            '<span style="font-size:19px;">'
            'Would you like to <b>change your product choice</b>?'
            '</span>'
        ),
        "QuestionType": "MC",
        "Selector": "SAVR",
        "SubSelector": "TX",
        "Configuration": {"QuestionDescriptionOption": "UseText"},
        "Choices": {
            "1": {"Display": "Yes, I would like to choose a different product"},
            "2": {"Display": "No, I will keep my original choice"}
        },
        "ChoiceOrder": ["1", "2"],
        "Validation": {"Settings": {"ForceResponse": "ON", "ForceResponseType": "ON", "Type": "None"}},
        "Language": [],
        "DataExportTag": "revise_yn"
    })
    all_qids["revise_yn"] = q
    print(f"  {q}: revise_yn")

    # Revised choice -- earbuds (created WITHOUT DisplayLogic; will add via PUT after revise_yn exists)
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
        "Choices": PRODUCT_CHOICES["earbuds"],
        "ChoiceOrder": ["1", "2", "3", "4", "5"],
        "Validation": {"Settings": {"ForceResponse": "ON", "ForceResponseType": "ON", "Type": "None"}},
        "Language": [],
        "DataExportTag": "revised_earbuds"
    })
    all_qids["revised_earbuds"] = q
    print(f"  {q}: revised_earbuds (DisplayLogic deferred)")

    # Revised choice -- speakers
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
        "Choices": PRODUCT_CHOICES["speakers"],
        "ChoiceOrder": ["1", "2", "3", "4", "5"],
        "Validation": {"Settings": {"ForceResponse": "ON", "ForceResponseType": "ON", "Type": "None"}},
        "Language": [],
        "DataExportTag": "revised_speakers"
    })
    all_qids["revised_speakers"] = q
    print(f"  {q}: revised_speakers (DisplayLogic deferred)")

    # Revised choice -- SSDs
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
        "Choices": PRODUCT_CHOICES["ssds"],
        "ChoiceOrder": ["1", "2", "3", "4", "5"],
        "Validation": {"Settings": {"ForceResponse": "ON", "ForceResponseType": "ON", "Type": "None"}},
        "Language": [],
        "DataExportTag": "revised_ssds"
    })
    all_qids["revised_ssds"] = q
    print(f"  {q}: revised_ssds (DisplayLogic deferred)")

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

    # Now add DisplayLogic to revised choice questions (Category + revise_yn == Yes)
    revise_qid = all_qids["revise_yn"]
    revised_cats = [
        ("revised_earbuds", "1"),
        ("revised_speakers", "2"),
        ("revised_ssds", "3"),
    ]
    for tag, cat_code in revised_cats:
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
    print("  Added DisplayLogic to revised choice questions (Category + revise_yn == Yes)")

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
            {"Type": "Question", "QuestionID": all_qids["feature_rank"]},
            {"Type": "Question", "QuestionID": all_qids["pref_text"]},
        ],
        "Options": BLOCK_OPTS
    })
    print("  preference_articulation block assigned")

    # Stimulus block
    api_call("PUT", f"/survey-definitions/{survey_id}/blocks/{stimulus_block}", {
        "Type": "Standard",
        "Description": "stimulus",
        "BlockElements": [
            {"Type": "Question", "QuestionID": all_qids["timer_stimulus"]},
            {"Type": "Question", "QuestionID": all_qids["product_table"]},
            {"Type": "Question", "QuestionID": all_qids["ai_rec_display"]},
        ],
        "Options": BLOCK_OPTS
    })
    print("  stimulus block assigned")

    # Comprehension block
    api_call("PUT", f"/survey-definitions/{survey_id}/blocks/{comprehension_block}", {
        "Type": "Standard",
        "Description": "comprehension",
        "BlockElements": [
            {"Type": "Question", "QuestionID": all_qids["timer_comprehension"]},
            {"Type": "Question", "QuestionID": all_qids["comp_earbuds"]},
            {"Type": "Question", "QuestionID": all_qids["comp_speakers"]},
            {"Type": "Question", "QuestionID": all_qids["comp_ssds"]},
        ],
        "Options": BLOCK_OPTS
    })
    print("  comprehension block assigned")

    # Product choice block
    api_call("PUT", f"/survey-definitions/{survey_id}/blocks/{choice_block}", {
        "Type": "Standard",
        "Description": "product_choice",
        "BlockElements": [
            {"Type": "Question", "QuestionID": all_qids["timer_choice"]},
            {"Type": "Question", "QuestionID": all_qids["choice_earbuds"]},
            {"Type": "Question", "QuestionID": all_qids["choice_speakers"]},
            {"Type": "Question", "QuestionID": all_qids["choice_ssds"]},
        ],
        "Options": BLOCK_OPTS
    })
    print("  product_choice block assigned")

    # Confidence + detection block
    api_call("PUT", f"/survey-definitions/{survey_id}/blocks/{confidence_block}", {
        "Type": "Standard",
        "Description": "confidence_detection",
        "BlockElements": [
            {"Type": "Question", "QuestionID": all_qids["timer_confidence"]},
            {"Type": "Question", "QuestionID": all_qids["confidence"]},
            {"Type": "Page Break"},
            {"Type": "Question", "QuestionID": all_qids["ai_match"]},
            {"Type": "Page Break"},
            {"Type": "Question", "QuestionID": all_qids["detection"]},
        ],
        "Options": BLOCK_OPTS
    })
    print("  confidence_detection block assigned")

    # Debrief + revision block
    api_call("PUT", f"/survey-definitions/{survey_id}/blocks/{debrief_block}", {
        "Type": "Standard",
        "Description": "debrief_revision",
        "BlockElements": [
            {"Type": "Question", "QuestionID": all_qids["timer_debrief"]},
            {"Type": "Question", "QuestionID": all_qids["debrief_text"]},
            {"Type": "Page Break"},
            {"Type": "Question", "QuestionID": all_qids["revise_yn"]},
            {"Type": "Question", "QuestionID": all_qids["revised_earbuds"]},
            {"Type": "Question", "QuestionID": all_qids["revised_speakers"]},
            {"Type": "Question", "QuestionID": all_qids["revised_ssds"]},
        ],
        "Options": BLOCK_OPTS
    })
    print("  debrief_revision block assigned")

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

    # Build the 12 EmbeddedData nodes for the BlockRandomizer
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
            # 5. BlockRandomizer (12 EmbeddedData cells)
            {
                "Type": "BlockRandomizer",
                "FlowID": "FL_3",
                "SubSet": 1,
                "EvenPresentation": True,
                "Flow": randomizer_flow
            },
            # 6. Preference articulation
            {"Type": "Standard", "ID": pref_block, "FlowID": "FL_4", "Autofill": []},
            # 7. Stimulus (product table + AI recommendation)
            {"Type": "Standard", "ID": stimulus_block, "FlowID": "FL_5", "Autofill": []},
            # 8. Comprehension check
            {"Type": "Standard", "ID": comprehension_block, "FlowID": "FL_6", "Autofill": []},
            # 9. Product choice
            {"Type": "Standard", "ID": choice_block, "FlowID": "FL_7", "Autofill": []},
            # 10. Confidence + detection
            {"Type": "Standard", "ID": confidence_block, "FlowID": "FL_8", "Autofill": []},
            # 11. Debrief + revision
            {"Type": "Standard", "ID": debrief_block, "FlowID": "FL_9", "Autofill": []},
            # 12. Demographics
            {"Type": "Standard", "ID": demo_block, "FlowID": "FL_12", "Autofill": []},
            # 13. End survey
            {"Type": "EndSurvey", "FlowID": "FL_99"}
        ],
        "Properties": {"Count": 40}
    }

    api_call("PUT", f"/survey-definitions/{survey_id}/flow", flow)
    print("  Flow set: mobile -> screening -> consent -> attn -> "
          "BlockRandomizer(12 cells) -> preference -> stimulus -> "
          "comprehension -> choice -> confidence -> debrief -> demo -> end")

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
    # Done!
    # =================================================================
    edit_url = f"https://okstatebusiness.az1.qualtrics.com/survey-builder/{survey_id}/edit"
    preview_url = f"https://okstatebusiness.az1.qualtrics.com/jfe/preview/{survey_id}"

    print("\n" + "=" * 70)
    print("SURVEY CREATED SUCCESSFULLY!")
    print("=" * 70)
    print(f"Survey ID:   {survey_id}")
    print(f"Edit:        {edit_url}")
    print(f"Preview:     {preview_url}")
    print()
    print("Design: 4 (Condition) x 3 (Category) = 12 cells, between-subjects")
    print()
    print("Conditions:")
    print("  1 = NoAI         (product table only, no AI recommendation)")
    print("  2 = BiasedNone   (biased rec, no justification)")
    print("  3 = BiasedConfab (biased rec, confabulated justification)")
    print("  4 = Debiased     (accurate rec pointing to optimal product)")
    print()
    print("Categories:")
    print("  1 = earbuds   (Auralis vs Sony/Apple/Samsung/Jabra)")
    print("  2 = speakers  (Wavecrest vs JBL/Bose/Sony/UE)")
    print("  3 = ssds      (Vaultdrive vs Samsung/WD/SanDisk/Seagate)")
    print()
    print("Structure:")
    print("  screening        -> consent, attention check (Horse), passed msg")
    print("  BlockRandomizer (SubSet=1, EvenPresentation=true):")
    for cond_label in ["NoAI", "BiasedNone", "BiasedConfab", "Debiased"]:
        for cat_label in ["earbuds", "speakers", "ssds"]:
            cond_code = {"NoAI": "1", "BiasedNone": "2", "BiasedConfab": "3", "Debiased": "4"}[cond_label]
            cat_code = {"earbuds": "1", "speakers": "2", "ssds": "3"}[cat_label]
            print(f"    Cell: {cond_label:14s} x {cat_label:8s} (Condition={cond_code}, Category={cat_code})")
    print("  preference       -> intro, feature ranking (RO/DND), text box")
    print("  stimulus         -> product table (piped) + AI rec (piped, DisplayLogic)")
    print("  comprehension    -> category-specific question (DisplayLogic)")
    print("  product_choice   -> category-specific 5-option MC (DisplayLogic)")
    print("  confidence       -> confidence (1-7) | AI match (1-7) | detection (MC)")
    print("  debrief          -> debrief text | revise Y/N | revised choice")
    print("  demographics     -> age, gender, AI usage, shopping freq, comments")
    print()
    print("Embedded Data Variables:")
    print("  Condition (1-4), ConditionD (NoAI/BiasedNone/BiasedConfab/Debiased)")
    print("  Category (1-3), CategoryD (earbuds/speakers/ssds)")
    print("  ProductTable, AIRecommendation, BrandedTarget, OptimalProduct")
    print("  ComprehensionQ, ComprehensionA, ProductChoices")
    print("  Feature1-Feature6 (category-specific labels)")
    print()
    print("DataExportTags:")
    for tag, qid in all_qids.items():
        print(f"  {tag:25s} -> {qid}")
    print()
    print("IMPORTANT: Update EOSRedirectURL with actual Prolific completion code before launch!")
    print("IMPORTANT: Update consent form with approved IRB text before launch!")


if __name__ == "__main__":
    main()
