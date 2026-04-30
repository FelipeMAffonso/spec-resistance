"""
Create Study 1 v3: Confabulation Mechanism (with pre-baked EmbeddedData)
Spec Resistance Project -- Nature R&R Human Subjects

Identical to v2 EXCEPT:
- Adds category-specific EmbeddedData fields (CategoryLabel, BrandedPrice,
  OptimalPrice, Product1-5, Product1Price-Product5Price) to each cell
  at creation time so Qualtrics records them from the first response.
- Debrief text now reveals the OptimalProduct and OptimalPrice via piped text.

Creates a BRAND NEW survey from scratch with ALL improvements baked in:
- Matrix/Likert feature importance (NOT RO/DND drag-and-drop)
- Beautiful product cards (Amazon/Best Buy style) from v1
- ChatGPT-style AI recommendation chat bubbles from v1
- DV counterbalancing (confidence vs detection order randomized)
- WTP measure after product choice
- Manipulation checks block
- Process measures (4-item Matrix/Likert)
- Table row shuffler JS on product table
- Choice randomization on comprehension and product choice questions
- Advanced randomization on detection (pin "not sure" last)
- Optimized page break layout

Design: 4 (Condition: NoAI / BiasedNone / BiasedConfab / Debiased)
        x 3 (Category: earbuds / speakers / ssds)
        = 12 cells, between-subjects

Flow:
  1. Mobile screening -> EndSurvey (if mobile)
  2. Screening block: browser_meta, consent, PB, attn_check (Horse), PB, attn_passed
  3. Consent branch -> EndSurvey (if "I do not agree")
  4. Attention check branch -> EndSurvey (if Horse not selected)
  5. BlockRandomizer(SubSet=1, EvenPresentation=true): 12 EmbeddedData cells
  6. preference_articulation: timer(5s), pref_intro(DB), feature_importance(Matrix/Likert 6x7), pref_text(TE optional)
  7. stimulus: timer(12s), product_table(DB piped + JS shuffler), ai_rec_display(DB piped, DL: Condition!=1)
  8. comprehension: timer(3s), comp_earbuds/speakers/ssds (MC, DL by Category, choice randomization)
  9. product_choice: timer(3s), choice_earbuds/speakers/ssds (MC, DL by Category, choice randomization)
  10. wtp_measure: timer(3s), wtp_chosen (TE numeric $0-500)
  11. BlockRandomizer(SubSet=2, EvenPresentation=true) for DV counterbalancing:
      - confidence_measures: timer(3s), confidence (MC/SAHR 1-7)
      - detection_measures: timer(3s), ai_match (MC/SAHR 1-7, DL: Condition!=1), detection (MC/SAVR 4 choices, DL: Condition!=1)
  12. manipulation_checks: timer(3s), manip_ai_seen(MC), spec_reading(MC/SAHR 1-7), choice_driver(MC 6 choices randomized)
  13. process_measures: timer(3s), process_measures(Matrix/Likert 4x7, row randomized)
  14. debrief_revision: timer(10s), debrief_text(DB), PB, revise_yn(MC), revised_earbuds/speakers/ssds(MC DL)
  15. demographics: age(MC/DL), gender(MC/SAVR), PB, ai_usage(MC/SAHR 1-5), shop_freq(MC/SAHR 1-5), comments(TE)
  16. EndSurvey -> Prolific redirect
"""
import requests
import json
import sys
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

TABLE_SHUFFLER_JS = """Qualtrics.SurveyEngine.addOnload(function(){
var tables = document.querySelectorAll('table');
tables.forEach(function(table){
  var tbody = table.querySelector('tbody');
  if (!tbody) {
    // If no tbody, create one from non-header rows
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
    // Fisher-Yates shuffle
    for (var i = rows.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1));
      tbody.appendChild(rows[j]);
      rows.splice(j, 1, rows[i]);
      rows.splice(i, 1, rows[j]);
    }
    // Re-append in shuffled order
    rows = Array.from(tbody.querySelectorAll('tr'));
    rows.forEach(function(row){ tbody.appendChild(row); });
  }
});
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
# PRODUCT DATA (beautiful cards from v1)
# =========================================================================

def load_cells_from_existing():
    """Load the 12 EmbeddedData cells from the existing survey (SV_3mBQFO2Rlpq72LA).
    This preserves the beautiful Amazon/Best Buy-style product cards and ChatGPT chat bubbles."""
    print("  Fetching product cards and AI recommendation HTML from existing survey...")
    resp = api_call("GET", "/survey-definitions/SV_3mBQFO2Rlpq72LA")
    flow = resp["result"]["SurveyFlow"]

    def find_randomizer(flow_obj):
        if isinstance(flow_obj, dict):
            if flow_obj.get("Type") == "BlockRandomizer":
                inner = flow_obj.get("Flow", [])
                if inner and inner[0].get("Type") == "EmbeddedData":
                    return flow_obj
            for v in flow_obj.values():
                r = find_randomizer(v)
                if r:
                    return r
        elif isinstance(flow_obj, list):
            for item in flow_obj:
                r = find_randomizer(item)
                if r:
                    return r
        return None

    randomizer = find_randomizer(flow)
    cells = randomizer["Flow"]
    extracted = []
    for cell in cells:
        ed = cell.get("EmbeddedData", [])
        entry = {}
        for e in ed:
            entry[e["Field"]] = e["Value"]
        extracted.append(entry)

    print(f"  Loaded {len(extracted)} cells with beautiful HTML")
    return extracted


# Product choices per category (for MC questions)
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

# Category code mapping
CATEGORY_CODES = {"earbuds": "1", "speakers": "2", "ssds": "3"}

# Additional EmbeddedData fields per category (v3: baked in from creation)
CATEGORY_ED_FIELDS = {
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

# Reverse lookup: CategoryD value -> category key
_CATD_TO_KEY = {"earbuds": "earbuds", "speakers": "speakers", "ssds": "ssds"}


# =========================================================================
# DisplayLogic helpers
# =========================================================================

def dl_category(cat_code):
    """DisplayLogic: Category == cat_code"""
    return {
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
    }


def dl_condition_not_1():
    """DisplayLogic: Condition != 1 (hide for NoAI)"""
    return {
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
    }


def dl_category_and_revise(cat_code, revise_qid):
    """DisplayLogic: Category == cat_code AND revise_yn == Yes (choice 1)"""
    return {
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


# =========================================================================
# MAIN
# =========================================================================

def main():
    print("=" * 70)
    print("CREATING STUDY 1 v3: Confabulation Mechanism (pre-baked ED fields)")
    print("4 (Condition) x 3 (Category) = 12 cells, between-subjects")
    print("ALL improvements baked in from first creation")
    print("=" * 70)

    # =================================================================
    # Step 0: Load beautiful HTML from existing survey
    # =================================================================
    print("\nStep 0: Loading product cards from existing survey...")
    ed_cells = load_cells_from_existing()

    # --- v3 enrichment: add category-specific ED fields to each cell ---
    print("\n  Enriching cells with category-specific EmbeddedData fields...")
    for cell in ed_cells:
        cat_d = cell.get("CategoryD", "")
        cat_key = _CATD_TO_KEY.get(cat_d)
        if cat_key is None:
            print(f"  WARNING: Cell has unknown CategoryD='{cat_d}', skipping enrichment")
            continue
        extra = CATEGORY_ED_FIELDS[cat_key]
        cell.update(extra)
    print(f"  Enriched {len(ed_cells)} cells with {len(list(CATEGORY_ED_FIELDS.values())[0])} extra fields each")

    # =================================================================
    # Step 1: Create survey
    # =================================================================
    print("\nStep 1: Creating survey...")
    survey_resp = api_call("POST", "/survey-definitions", {
        "SurveyName": "SR Study 1 v3 -- Confabulation Mechanism (4x3) pre-baked ED",
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
    # Step 2: Create all blocks
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
    wtp_block = create_block(survey_id, "wtp_measure")
    confidence_block = create_block(survey_id, "confidence_measures")
    detection_block = create_block(survey_id, "detection_measures")
    manip_block = create_block(survey_id, "manipulation_checks")
    process_block = create_block(survey_id, "process_measures")
    debrief_block = create_block(survey_id, "debrief_revision")
    demo_block = create_block(survey_id, "demographics")

    block_names = {
        "preference_articulation": pref_block,
        "stimulus": stimulus_block,
        "comprehension": comprehension_block,
        "product_choice": choice_block,
        "wtp_measure": wtp_block,
        "confidence_measures": confidence_block,
        "detection_measures": detection_block,
        "manipulation_checks": manip_block,
        "process_measures": process_block,
        "debrief_revision": debrief_block,
        "demographics": demo_block,
    }
    for name, bid in block_names.items():
        print(f"  {name}: {bid}")

    # =================================================================
    # Step 3: Create ALL questions
    # =================================================================
    print("\nStep 3: Creating questions...")
    Q = {}  # tag -> QID

    # --- SCREENING BLOCK ---

    # Browser meta info
    Q["browser_meta"] = create_question(survey_id, {
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
    print(f"  {Q['browser_meta']}: browser_meta")

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
    Q["consent"] = create_question(survey_id, {
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
    print(f"  {Q['consent']}: consent")

    # Attention check (IMC)
    Q["attn_check"] = create_question(survey_id, {
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
    print(f"  {Q['attn_check']}: attn_check")

    # Passed message
    Q["attn_passed"] = create_question(survey_id, {
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
    print(f"  {Q['attn_passed']}: attn_passed")

    # --- PREFERENCE ARTICULATION BLOCK ---

    Q["timer_pref"] = create_question(survey_id, {
        "QuestionText": "Timing",
        "QuestionType": "Timing",
        "Selector": "PageTimer",
        "Configuration": {"QuestionDescriptionOption": "UseText", "MinSeconds": 5, "MaxSeconds": "0"},
        "Choices": {"1": {"Display": "First Click"}, "2": {"Display": "Last Click"},
                    "3": {"Display": "Page Submit"}, "4": {"Display": "Click Count"}},
        "Language": [],
        "DataExportTag": "timer_pref"
    })
    print(f"  {Q['timer_pref']}: timer_pref")

    Q["pref_intro"] = create_question(survey_id, {
        "QuestionText": (
            '<div style="text-align: center;">'
            '<span style="font-size:19px;"><b>PRODUCT EVALUATION STUDY</b></span>'
            '</div>'
            '<div style="text-align: center;">&nbsp;</div>'
            '<span style="font-size:19px;">'
            'In this study, you will evaluate a set of products and make a purchasing decision. '
            'There are no right or wrong answers.'
            '<br><br>'
            'Before seeing the products, please tell us how important each feature is to you.'
            '</span>'
        ),
        "QuestionType": "DB",
        "Selector": "TB",
        "Configuration": {"QuestionDescriptionOption": "UseText"},
        "Language": [],
        "DataExportTag": "pref_intro"
    })
    print(f"  {Q['pref_intro']}: pref_intro")

    # Feature importance (Matrix/Likert 6x7) — THE FIX: created as Matrix from scratch
    Q["feature_importance"] = create_question(survey_id, {
        "QuestionText": (
            '<span style="font-size:19px;">'
            'How important is each of the following features to you when choosing this product? '
            'Rate each feature from 1 (not at all important) to 7 (extremely important).'
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
            "1": {"Display": "1 = Not at all"},
            "2": {"Display": "2"},
            "3": {"Display": "3"},
            "4": {"Display": "4 = Moderately"},
            "5": {"Display": "5"},
            "6": {"Display": "6"},
            "7": {"Display": "7 = Extremely"}
        },
        "AnswerOrder": ["1", "2", "3", "4", "5", "6", "7"],
        "Validation": {"Settings": {"ForceResponse": "ON", "ForceResponseType": "ON", "Type": "None"}},
        "Randomization": {"Type": "All", "Advanced": None, "TotalRandSubset": ""},
        "Language": [],
        "DataExportTag": "feature_importance"
    })
    print(f"  {Q['feature_importance']}: feature_importance (Matrix/Likert 6x7)")

    # Optional text box for specific requirements
    Q["pref_text"] = create_question(survey_id, {
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
    print(f"  {Q['pref_text']}: pref_text")

    # --- STIMULUS BLOCK ---

    Q["timer_stimulus"] = create_question(survey_id, {
        "QuestionText": "Timing",
        "QuestionType": "Timing",
        "Selector": "PageTimer",
        "Configuration": {"QuestionDescriptionOption": "UseText", "MinSeconds": 12, "MaxSeconds": "0"},
        "Choices": {"1": {"Display": "First Click"}, "2": {"Display": "Last Click"},
                    "3": {"Display": "Page Submit"}, "4": {"Display": "Click Count"}},
        "Language": [],
        "DataExportTag": "timer_stimulus"
    })
    print(f"  {Q['timer_stimulus']}: timer_stimulus (12s)")

    Q["product_table"] = create_question(survey_id, {
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
        "QuestionJS": TABLE_SHUFFLER_JS,
        "Language": [],
        "DataExportTag": "product_table"
    })
    print(f"  {Q['product_table']}: product_table (with JS row shuffler)")

    Q["ai_rec_display"] = create_question(survey_id, {
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
        "DisplayLogic": dl_condition_not_1(),
        "Language": [],
        "DataExportTag": "ai_rec_display"
    })
    print(f"  {Q['ai_rec_display']}: ai_rec_display (DL: Condition != 1)")

    # --- COMPREHENSION CHECK BLOCK ---

    Q["timer_comprehension"] = create_question(survey_id, {
        "QuestionText": "Timing",
        "QuestionType": "Timing",
        "Selector": "PageTimer",
        "Configuration": {"QuestionDescriptionOption": "UseText", "MinSeconds": 3, "MaxSeconds": "0"},
        "Choices": {"1": {"Display": "First Click"}, "2": {"Display": "Last Click"},
                    "3": {"Display": "Page Submit"}, "4": {"Display": "Click Count"}},
        "Language": [],
        "DataExportTag": "timer_comprehension"
    })
    print(f"  {Q['timer_comprehension']}: timer_comprehension")

    # Comprehension questions per category (with choice randomization)
    comp_configs = [
        ("comp_earbuds", "1",
         'which product has the <b>longest battery life</b>?',
         {"1": {"Display": "Auralis Air4 Pro"}, "2": {"Display": "Sony WF-1000XM5"},
          "3": {"Display": "Apple AirPods Pro 2"}, "4": {"Display": "Samsung Galaxy Buds3 Pro"},
          "5": {"Display": "Jabra Elite 85t"}}),
        ("comp_speakers", "2",
         'which product has the <b>longest battery life</b>?',
         {"1": {"Display": "Wavecrest StormBox Pro"}, "2": {"Display": "JBL Flip 6"},
          "3": {"Display": "Bose SoundLink Flex"}, "4": {"Display": "Sony SRS-XB100"},
          "5": {"Display": "UE WONDERBOOM 3"}}),
        ("comp_ssds", "3",
         'which product has the <b>fastest transfer speed</b>?',
         {"1": {"Display": "Vaultdrive PD60"}, "2": {"Display": "Samsung T7 Shield"},
          "3": {"Display": "WD My Passport"}, "4": {"Display": "SanDisk Extreme V2"},
          "5": {"Display": "Seagate One Touch"}}),
    ]
    for tag, cat_code, q_text, choices in comp_configs:
        Q[tag] = create_question(survey_id, {
            "QuestionText": (
                '<span style="font-size:19px;">'
                f'Based on the product table you just reviewed, {q_text}'
                '</span>'
            ),
            "QuestionType": "MC",
            "Selector": "SAVR",
            "SubSelector": "TX",
            "Configuration": {"QuestionDescriptionOption": "UseText"},
            "Choices": choices,
            "ChoiceOrder": ["1", "2", "3", "4", "5"],
            "Validation": {"Settings": {"ForceResponse": "ON", "ForceResponseType": "ON", "Type": "None"}},
            "Randomization": {"Type": "All", "Advanced": None, "TotalRandSubset": ""},
            "DisplayLogic": dl_category(cat_code),
            "Language": [],
            "DataExportTag": tag
        })
        print(f"  {Q[tag]}: {tag} (DL: Category={cat_code}, randomized)")

    # --- PRODUCT CHOICE BLOCK ---

    Q["timer_choice"] = create_question(survey_id, {
        "QuestionText": "Timing",
        "QuestionType": "Timing",
        "Selector": "PageTimer",
        "Configuration": {"QuestionDescriptionOption": "UseText", "MinSeconds": 3, "MaxSeconds": "0"},
        "Choices": {"1": {"Display": "First Click"}, "2": {"Display": "Last Click"},
                    "3": {"Display": "Page Submit"}, "4": {"Display": "Click Count"}},
        "Language": [],
        "DataExportTag": "timer_choice"
    })
    print(f"  {Q['timer_choice']}: timer_choice")

    for cat in ["earbuds", "speakers", "ssds"]:
        tag = f"choice_{cat}"
        Q[tag] = create_question(survey_id, {
            "QuestionText": (
                '<span style="font-size:19px;">'
                'Based on everything you have reviewed, <b>which product would you purchase</b>?'
                '</span>'
            ),
            "QuestionType": "MC",
            "Selector": "SAVR",
            "SubSelector": "TX",
            "Configuration": {"QuestionDescriptionOption": "UseText"},
            "Choices": PRODUCT_CHOICES[cat],
            "ChoiceOrder": ["1", "2", "3", "4", "5"],
            "Validation": {"Settings": {"ForceResponse": "ON", "ForceResponseType": "ON", "Type": "None"}},
            "Randomization": {"Type": "All", "Advanced": None, "TotalRandSubset": ""},
            "DisplayLogic": dl_category(CATEGORY_CODES[cat]),
            "Language": [],
            "DataExportTag": tag
        })
        print(f"  {Q[tag]}: {tag} (DL: Category={CATEGORY_CODES[cat]}, randomized)")

    # --- WTP MEASURE BLOCK ---

    Q["timer_wtp"] = create_question(survey_id, {
        "QuestionText": "Timing",
        "QuestionType": "Timing",
        "Selector": "PageTimer",
        "Configuration": {"QuestionDescriptionOption": "UseText", "MinSeconds": 3, "MaxSeconds": "0"},
        "Choices": {"1": {"Display": "First Click"}, "2": {"Display": "Last Click"},
                    "3": {"Display": "Page Submit"}, "4": {"Display": "Click Count"}},
        "Language": [],
        "DataExportTag": "timer_wtp"
    })
    print(f"  {Q['timer_wtp']}: timer_wtp")

    Q["wtp_chosen"] = create_question(survey_id, {
        "QuestionText": (
            '<span style="font-size:19px;">What is the <b>maximum amount</b> you would be willing '
            'to pay for the product you just chose?<br><br>'
            '<span style="font-size:15px; color:#666;">Please enter a dollar amount (e.g., 75). '
            'Think about what this product is genuinely worth to you, not what it costs in the '
            'comparison table.</span></span>'
        ),
        "QuestionType": "TE",
        "Selector": "SL",
        "Configuration": {"QuestionDescriptionOption": "UseText"},
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
                "ValidNumber": {"Min": "0", "Max": "500", "NumDecimals": "2"}
            }
        },
        "Language": [],
        "DataExportTag": "wtp_chosen"
    })
    print(f"  {Q['wtp_chosen']}: wtp_chosen (numeric $0-500)")

    # --- CONFIDENCE MEASURES BLOCK (for counterbalancing) ---

    Q["timer_confidence"] = create_question(survey_id, {
        "QuestionText": "Timing",
        "QuestionType": "Timing",
        "Selector": "PageTimer",
        "Configuration": {"QuestionDescriptionOption": "UseText", "MinSeconds": 3, "MaxSeconds": "0"},
        "Choices": {"1": {"Display": "First Click"}, "2": {"Display": "Last Click"},
                    "3": {"Display": "Page Submit"}, "4": {"Display": "Click Count"}},
        "Language": [],
        "DataExportTag": "timer_confidence"
    })
    print(f"  {Q['timer_confidence']}: timer_confidence")

    Q["confidence"] = create_question(survey_id, {
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
        "Language": [],
        "DataExportTag": "confidence"
    })
    print(f"  {Q['confidence']}: confidence (1-7)")

    # --- DETECTION MEASURES BLOCK (for counterbalancing) ---

    Q["timer_detection"] = create_question(survey_id, {
        "QuestionText": "Timing",
        "QuestionType": "Timing",
        "Selector": "PageTimer",
        "Configuration": {"QuestionDescriptionOption": "UseText", "MinSeconds": 3, "MaxSeconds": "0"},
        "Choices": {"1": {"Display": "First Click"}, "2": {"Display": "Last Click"},
                    "3": {"Display": "Page Submit"}, "4": {"Display": "Click Count"}},
        "Language": [],
        "DataExportTag": "timer_detection"
    })
    print(f"  {Q['timer_detection']}: timer_detection")

    Q["ai_match"] = create_question(survey_id, {
        "QuestionText": (
            '<span style="font-size:19px;">'
            "How well did the AI's recommendation <b>match your stated preferences</b>?"
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
        "DisplayLogic": dl_condition_not_1(),
        "Language": [],
        "DataExportTag": "ai_match"
    })
    print(f"  {Q['ai_match']}: ai_match (DL: Condition != 1)")

    Q["detection"] = create_question(survey_id, {
        "QuestionText": (
            '<span style="font-size:19px;">'
            "In your opinion, was the AI's recommendation primarily driven by..."
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
        "Randomization": {
            "Type": "Advanced",
            "Advanced": {
                "FixedOrder": ["4"],
                "RandomizeAll": ["1", "2", "3"],
                "RandomSubSet": [],
                "Undisplayed": []
            },
            "TotalRandSubset": ""
        },
        "DisplayLogic": dl_condition_not_1(),
        "Language": [],
        "DataExportTag": "detection"
    })
    print(f"  {Q['detection']}: detection (DL: Condition != 1, 'not sure' pinned last)")

    # --- MANIPULATION CHECKS BLOCK ---

    Q["timer_manip"] = create_question(survey_id, {
        "QuestionText": "Timing",
        "QuestionType": "Timing",
        "Selector": "PageTimer",
        "Configuration": {"QuestionDescriptionOption": "UseText", "MinSeconds": 3, "MaxSeconds": "0"},
        "Choices": {"1": {"Display": "First Click"}, "2": {"Display": "Last Click"},
                    "3": {"Display": "Page Submit"}, "4": {"Display": "Click Count"}},
        "Language": [],
        "DataExportTag": "timer_manip"
    })
    print(f"  {Q['timer_manip']}: timer_manip")

    Q["manip_ai_seen"] = create_question(survey_id, {
        "QuestionText": (
            '<span style="font-size:19px;">'
            'During this study, did you see a product recommendation from an AI shopping assistant?'
            '</span>'
        ),
        "QuestionType": "MC",
        "Selector": "SAVR",
        "SubSelector": "TX",
        "Configuration": {"QuestionDescriptionOption": "UseText"},
        "Choices": {
            "1": {"Display": "Yes, I saw an AI recommendation"},
            "2": {"Display": "No, I did not see an AI recommendation"},
            "3": {"Display": "I am not sure"}
        },
        "ChoiceOrder": ["1", "2", "3"],
        "Validation": {"Settings": {"ForceResponse": "ON", "ForceResponseType": "ON", "Type": "None"}},
        "Language": [],
        "DataExportTag": "manip_ai_seen"
    })
    print(f"  {Q['manip_ai_seen']}: manip_ai_seen")

    Q["spec_reading"] = create_question(survey_id, {
        "QuestionText": (
            '<span style="font-size:19px;">'
            'How carefully did you read the product specifications shown in the comparison table?'
            '</span>'
        ),
        "QuestionType": "MC",
        "Selector": "SAHR",
        "SubSelector": "TX",
        "Configuration": {"QuestionDescriptionOption": "UseText", "LabelPosition": "BELOW"},
        "Choices": {
            "1": {"Display": "1 = Did not read at all"},
            "2": {"Display": "2"},
            "3": {"Display": "3"},
            "4": {"Display": "4 = Read moderately"},
            "5": {"Display": "5"},
            "6": {"Display": "6"},
            "7": {"Display": "7 = Read very carefully"}
        },
        "ChoiceOrder": ["1", "2", "3", "4", "5", "6", "7"],
        "Validation": {"Settings": {"ForceResponse": "ON", "ForceResponseType": "ON", "Type": "None"}},
        "Language": [],
        "DataExportTag": "spec_reading"
    })
    print(f"  {Q['spec_reading']}: spec_reading (1-7)")

    Q["choice_driver"] = create_question(survey_id, {
        "QuestionText": (
            '<span style="font-size:19px;">'
            'What was the <b>main factor</b> in your product choice?'
            '</span>'
        ),
        "QuestionType": "MC",
        "Selector": "SAVR",
        "SubSelector": "TX",
        "Configuration": {"QuestionDescriptionOption": "UseText"},
        "Choices": {
            "1": {"Display": "I compared the product specifications carefully"},
            "2": {"Display": "I followed the AI recommendation"},
            "3": {"Display": "I chose the brand I recognized or trusted"},
            "4": {"Display": "I chose the product with the best price"},
            "5": {"Display": "I chose the product with the best reviews/ratings"},
            "6": {"Display": "Other"}
        },
        "ChoiceOrder": ["1", "2", "3", "4", "5", "6"],
        "Validation": {"Settings": {"ForceResponse": "ON", "ForceResponseType": "ON", "Type": "None"}},
        "Randomization": {"Type": "All", "Advanced": None, "TotalRandSubset": ""},
        "Language": [],
        "DataExportTag": "choice_driver"
    })
    print(f"  {Q['choice_driver']}: choice_driver (6 options, randomized)")

    # --- PROCESS MEASURES BLOCK ---

    Q["timer_process"] = create_question(survey_id, {
        "QuestionText": "Timing",
        "QuestionType": "Timing",
        "Selector": "PageTimer",
        "Configuration": {"QuestionDescriptionOption": "UseText", "MinSeconds": 3, "MaxSeconds": "0"},
        "Choices": {"1": {"Display": "First Click"}, "2": {"Display": "Last Click"},
                    "3": {"Display": "Page Submit"}, "4": {"Display": "Click Count"}},
        "Language": [],
        "DataExportTag": "timer_process"
    })
    print(f"  {Q['timer_process']}: timer_process")

    Q["process_measures"] = create_question(survey_id, {
        "QuestionText": (
            '<span style="font-size:19px;">'
            'Please indicate how much you agree or disagree with each statement.'
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
            "1": {"Display": 'I <b>trust</b> AI shopping assistants to recommend the best products.'},
            "2": {"Display": 'AI shopping assistants are <b>competent</b> at evaluating product specifications.'},
            "3": {"Display": 'I would <b>override</b> an AI recommendation if I disagreed with it.'},
            "4": {"Display": 'I felt in <b>control</b> of my product choice in this study.'},
        },
        "ChoiceOrder": ["1", "2", "3", "4"],
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
        "DataExportTag": "process_measures"
    })
    print(f"  {Q['process_measures']}: process_measures (Matrix/Likert 4x7, randomized)")

    # --- DEBRIEF + REVISION BLOCK ---

    Q["timer_debrief"] = create_question(survey_id, {
        "QuestionText": "Timing",
        "QuestionType": "Timing",
        "Selector": "PageTimer",
        "Configuration": {"QuestionDescriptionOption": "UseText", "MinSeconds": 10, "MaxSeconds": "0"},
        "Choices": {"1": {"Display": "First Click"}, "2": {"Display": "Last Click"},
                    "3": {"Display": "Page Submit"}, "4": {"Display": "Click Count"}},
        "Language": [],
        "DataExportTag": "timer_debrief"
    })
    print(f"  {Q['timer_debrief']}: timer_debrief (10s)")

    Q["debrief_text"] = create_question(survey_id, {
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
            '<br><br>'
            '<div style="max-width:720px; margin:0 auto; background:#fef3c7; border:1px solid #f59e0b; border-radius:12px; padding:16px 20px;">'
            '<span style="font-size:16px; color:#92400e;">'
            'The product that <b>best matched your stated preferences</b> was: '
            '<b style="color:#16a34a;">${e://Field/OptimalProduct} (${e://Field/OptimalPrice})</b>'
            '</span></div>'
        ),
        "QuestionType": "DB",
        "Selector": "TB",
        "Configuration": {"QuestionDescriptionOption": "UseText"},
        "Language": [],
        "DataExportTag": "debrief_text"
    })
    print(f"  {Q['debrief_text']}: debrief_text")

    Q["revise_yn"] = create_question(survey_id, {
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
    print(f"  {Q['revise_yn']}: revise_yn")

    # Revised choices per category (created WITHOUT DisplayLogic first, will add via PUT)
    for cat in ["earbuds", "speakers", "ssds"]:
        tag = f"revised_{cat}"
        Q[tag] = create_question(survey_id, {
            "QuestionText": (
                '<span style="font-size:19px;">'
                'Please select your <b>revised product choice</b>:'
                '</span>'
            ),
            "QuestionType": "MC",
            "Selector": "SAVR",
            "SubSelector": "TX",
            "Configuration": {"QuestionDescriptionOption": "UseText"},
            "Choices": PRODUCT_CHOICES[cat],
            "ChoiceOrder": ["1", "2", "3", "4", "5"],
            "Validation": {"Settings": {"ForceResponse": "ON", "ForceResponseType": "ON", "Type": "None"}},
            "Language": [],
            "DataExportTag": tag
        })
        print(f"  {Q[tag]}: {tag} (DL deferred)")

    # --- DEMOGRAPHICS BLOCK ---

    age_choices = {}
    age_order = []
    for i, age in enumerate(range(18, 100), start=1):
        age_choices[str(i)] = {"Display": str(age)}
        age_order.append(str(i))

    Q["age"] = create_question(survey_id, {
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
    print(f"  {Q['age']}: age")

    Q["gender"] = create_question(survey_id, {
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
    print(f"  {Q['gender']}: gender")

    Q["ai_usage"] = create_question(survey_id, {
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
    print(f"  {Q['ai_usage']}: ai_usage")

    Q["shop_freq"] = create_question(survey_id, {
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
    print(f"  {Q['shop_freq']}: shop_freq")

    Q["comments"] = create_question(survey_id, {
        "QuestionText": '<span style="font-size:19px;">Do you have any comments for us? (optional)</span>',
        "QuestionType": "TE",
        "Selector": "SL",
        "Configuration": {"QuestionDescriptionOption": "UseText", "InputWidth": 680, "InputHeight": 80},
        "Validation": {"Settings": {"ForceResponse": "OFF", "Type": "None"}},
        "Language": [],
        "DataExportTag": "comments"
    })
    print(f"  {Q['comments']}: comments")

    print(f"\n  Total questions created: {len(Q)}")

    # =================================================================
    # Step 3b: Add DisplayLogic to revised choice questions
    # =================================================================
    print("\nStep 3b: Adding DisplayLogic to revised choice questions...")
    revise_qid = Q["revise_yn"]
    for cat in ["earbuds", "speakers", "ssds"]:
        tag = f"revised_{cat}"
        cat_code = CATEGORY_CODES[cat]
        # GET the full question definition, add DL, PUT back
        qdef_resp = api_call("GET", f"/survey-definitions/{survey_id}/questions/{Q[tag]}")
        qdef = qdef_resp["result"]
        qdef["DisplayLogic"] = dl_category_and_revise(cat_code, revise_qid)
        api_call("PUT", f"/survey-definitions/{survey_id}/questions/{Q[tag]}", qdef)
    print("  Added DL: Category match AND revise_yn == Yes")

    # =================================================================
    # Step 4: Assign questions to blocks
    # =================================================================
    print("\nStep 4: Assigning questions to blocks...")

    # Screening block (default)
    api_call("PUT", f"/survey-definitions/{survey_id}/blocks/{screening_block}", {
        "Type": "Default",
        "Description": "screening",
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
    print("  screening block assigned")

    # Preference articulation block
    api_call("PUT", f"/survey-definitions/{survey_id}/blocks/{pref_block}", {
        "Type": "Standard",
        "Description": "preference_articulation",
        "BlockElements": [
            {"Type": "Question", "QuestionID": Q["timer_pref"]},
            {"Type": "Question", "QuestionID": Q["pref_intro"]},
            {"Type": "Question", "QuestionID": Q["feature_importance"]},
            {"Type": "Question", "QuestionID": Q["pref_text"]},
        ],
        "Options": BLOCK_OPTS
    })
    print("  preference_articulation block assigned")

    # Stimulus block
    api_call("PUT", f"/survey-definitions/{survey_id}/blocks/{stimulus_block}", {
        "Type": "Standard",
        "Description": "stimulus",
        "BlockElements": [
            {"Type": "Question", "QuestionID": Q["timer_stimulus"]},
            {"Type": "Question", "QuestionID": Q["product_table"]},
            {"Type": "Question", "QuestionID": Q["ai_rec_display"]},
        ],
        "Options": BLOCK_OPTS
    })
    print("  stimulus block assigned")

    # Comprehension block
    api_call("PUT", f"/survey-definitions/{survey_id}/blocks/{comprehension_block}", {
        "Type": "Standard",
        "Description": "comprehension",
        "BlockElements": [
            {"Type": "Question", "QuestionID": Q["timer_comprehension"]},
            {"Type": "Question", "QuestionID": Q["comp_earbuds"]},
            {"Type": "Question", "QuestionID": Q["comp_speakers"]},
            {"Type": "Question", "QuestionID": Q["comp_ssds"]},
        ],
        "Options": BLOCK_OPTS
    })
    print("  comprehension block assigned")

    # Product choice block
    api_call("PUT", f"/survey-definitions/{survey_id}/blocks/{choice_block}", {
        "Type": "Standard",
        "Description": "product_choice",
        "BlockElements": [
            {"Type": "Question", "QuestionID": Q["timer_choice"]},
            {"Type": "Question", "QuestionID": Q["choice_earbuds"]},
            {"Type": "Question", "QuestionID": Q["choice_speakers"]},
            {"Type": "Question", "QuestionID": Q["choice_ssds"]},
        ],
        "Options": BLOCK_OPTS
    })
    print("  product_choice block assigned")

    # WTP block
    api_call("PUT", f"/survey-definitions/{survey_id}/blocks/{wtp_block}", {
        "Type": "Standard",
        "Description": "wtp_measure",
        "BlockElements": [
            {"Type": "Question", "QuestionID": Q["timer_wtp"]},
            {"Type": "Question", "QuestionID": Q["wtp_chosen"]},
        ],
        "Options": BLOCK_OPTS
    })
    print("  wtp_measure block assigned")

    # Confidence measures block
    api_call("PUT", f"/survey-definitions/{survey_id}/blocks/{confidence_block}", {
        "Type": "Standard",
        "Description": "confidence_measures",
        "BlockElements": [
            {"Type": "Question", "QuestionID": Q["timer_confidence"]},
            {"Type": "Question", "QuestionID": Q["confidence"]},
        ],
        "Options": BLOCK_OPTS
    })
    print("  confidence_measures block assigned")

    # Detection measures block
    api_call("PUT", f"/survey-definitions/{survey_id}/blocks/{detection_block}", {
        "Type": "Standard",
        "Description": "detection_measures",
        "BlockElements": [
            {"Type": "Question", "QuestionID": Q["timer_detection"]},
            {"Type": "Question", "QuestionID": Q["ai_match"]},
            {"Type": "Question", "QuestionID": Q["detection"]},
        ],
        "Options": BLOCK_OPTS
    })
    print("  detection_measures block assigned")

    # Manipulation checks block
    api_call("PUT", f"/survey-definitions/{survey_id}/blocks/{manip_block}", {
        "Type": "Standard",
        "Description": "manipulation_checks",
        "BlockElements": [
            {"Type": "Question", "QuestionID": Q["timer_manip"]},
            {"Type": "Question", "QuestionID": Q["manip_ai_seen"]},
            {"Type": "Question", "QuestionID": Q["spec_reading"]},
            {"Type": "Question", "QuestionID": Q["choice_driver"]},
        ],
        "Options": BLOCK_OPTS
    })
    print("  manipulation_checks block assigned")

    # Process measures block
    api_call("PUT", f"/survey-definitions/{survey_id}/blocks/{process_block}", {
        "Type": "Standard",
        "Description": "process_measures",
        "BlockElements": [
            {"Type": "Question", "QuestionID": Q["timer_process"]},
            {"Type": "Question", "QuestionID": Q["process_measures"]},
        ],
        "Options": BLOCK_OPTS
    })
    print("  process_measures block assigned")

    # Debrief + revision block
    api_call("PUT", f"/survey-definitions/{survey_id}/blocks/{debrief_block}", {
        "Type": "Standard",
        "Description": "debrief_revision",
        "BlockElements": [
            {"Type": "Question", "QuestionID": Q["timer_debrief"]},
            {"Type": "Question", "QuestionID": Q["debrief_text"]},
            {"Type": "Page Break"},
            {"Type": "Question", "QuestionID": Q["revise_yn"]},
            {"Type": "Question", "QuestionID": Q["revised_earbuds"]},
            {"Type": "Question", "QuestionID": Q["revised_speakers"]},
            {"Type": "Question", "QuestionID": Q["revised_ssds"]},
        ],
        "Options": BLOCK_OPTS
    })
    print("  debrief_revision block assigned")

    # Demographics block
    api_call("PUT", f"/survey-definitions/{survey_id}/blocks/{demo_block}", {
        "Type": "Standard",
        "Description": "demographics",
        "BlockElements": [
            {"Type": "Question", "QuestionID": Q["age"]},
            {"Type": "Question", "QuestionID": Q["gender"]},
            {"Type": "Page Break"},
            {"Type": "Question", "QuestionID": Q["ai_usage"]},
            {"Type": "Question", "QuestionID": Q["shop_freq"]},
            {"Type": "Question", "QuestionID": Q["comments"]},
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
    randomizer_flow = []
    fl_counter = 20
    for cell in ed_cells:
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

    # Build consent branch
    consent_branch = {
        "Type": "Branch",
        "FlowID": "FL_42",
        "Description": "Consent Branch",
        "BranchLogic": {
            "0": {
                "0": {
                    "LogicType": "Question",
                    "QuestionID": Q["consent"],
                    "QuestionIsInLoop": "no",
                    "ChoiceLocator": f'q://{Q["consent"]}/SelectableChoice/2',
                    "Operator": "Selected",
                    "Type": "Expression",
                    "Description": '<span class="ConjDesc">If</span> <span class="QuestionDesc">consent</span> <span class="LeftOpDesc">I do not agree</span> <span class="OpDesc">Is Selected</span>'
                },
                "Type": "If"
            },
            "Type": "BooleanExpression"
        },
        "Flow": [
            {"Type": "EndSurvey", "FlowID": "FL_43"}
        ]
    }

    # Build attention check branch
    attn_branch = {
        "Type": "Branch",
        "FlowID": "FL_40",
        "Description": "Attention Check Branch",
        "BranchLogic": {
            "0": {
                "0": {
                    "LogicType": "Question",
                    "QuestionID": Q["attn_check"],
                    "QuestionIsInLoop": "no",
                    "ChoiceLocator": f'q://{Q["attn_check"]}/SelectableChoice/4',
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

    # Full flow
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
            # 10. WTP measure
            {"Type": "Standard", "ID": wtp_block, "FlowID": "FL_500", "Autofill": []},
            # 11. BlockRandomizer for DV counterbalancing
            {
                "Type": "BlockRandomizer",
                "FlowID": "FL_50",
                "SubSet": 2,
                "EvenPresentation": True,
                "Flow": [
                    {"Type": "Standard", "ID": confidence_block, "FlowID": "FL_51", "Autofill": []},
                    {"Type": "Standard", "ID": detection_block, "FlowID": "FL_52", "Autofill": []},
                ]
            },
            # 12. Manipulation checks
            {"Type": "Standard", "ID": manip_block, "FlowID": "FL_200", "Autofill": []},
            # 13. Process measures
            {"Type": "Standard", "ID": process_block, "FlowID": "FL_300", "Autofill": []},
            # 14. Debrief + revision
            {"Type": "Standard", "ID": debrief_block, "FlowID": "FL_9", "Autofill": []},
            # 15. Demographics
            {"Type": "Standard", "ID": demo_block, "FlowID": "FL_12", "Autofill": []},
            # 16. End survey
            {"Type": "EndSurvey", "FlowID": "FL_99"}
        ],
        "Properties": {"Count": 50}
    }

    api_call("PUT", f"/survey-definitions/{survey_id}/flow", flow)
    print("  Flow set successfully")
    print("  mobile -> screening -> consent -> attn -> BlockRandomizer(12 cells)")
    print("  -> preference -> stimulus -> comprehension -> choice -> wtp")
    print("  -> BlockRandomizer(confidence | detection) -> manip -> process")
    print("  -> debrief -> demographics -> EndSurvey")

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
    print("  Options set (blue theme, no back button, no progress bar, slide transitions)")

    # =================================================================
    # Step 7: Activate survey
    # =================================================================
    print("\nStep 7: Activating survey...")
    api_call("PUT", f"/surveys/{survey_id}", {
        "isActive": True
    })
    print("  Survey ACTIVATED")

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
    print("Survey Flow:")
    print("  1. Mobile screening -> EndSurvey")
    print("  2. Screening: browser_meta, consent, PB, attn_check, PB, attn_passed")
    print("  3. Consent branch -> EndSurvey")
    print("  4. Attention check branch -> EndSurvey")
    print("  5. BlockRandomizer(SubSet=1, EvenPresentation=true): 12 cells")
    print("  6. preference_articulation: timer(5s), intro, feature_importance(Matrix/Likert 6x7), pref_text")
    print("  7. stimulus: timer(12s), product_table(piped+JS shuffler), ai_rec(piped, DL)")
    print("  8. comprehension: timer(3s), 3 category-specific MC (DL, randomized)")
    print("  9. product_choice: timer(3s), 3 category-specific MC (DL, randomized)")
    print(" 10. wtp_measure: timer(3s), wtp_chosen(numeric $0-500)")
    print(" 11. BlockRandomizer(SubSet=2, EvenPresentation=true):")
    print("     - confidence_measures: timer(3s), confidence(1-7)")
    print("     - detection_measures: timer(3s), ai_match(1-7, DL), detection(4 choices, DL)")
    print(" 12. manipulation_checks: timer(3s), manip_ai_seen, spec_reading(1-7), choice_driver")
    print(" 13. process_measures: timer(3s), process_measures(Matrix/Likert 4x7)")
    print(" 14. debrief_revision: timer(10s), debrief_text, PB, revise_yn, revised choices(DL)")
    print(" 15. demographics: age, gender, PB, ai_usage, shop_freq, comments")
    print(" 16. EndSurvey -> Prolific redirect")
    print()
    print("DataExportTags:")
    for tag, qid in Q.items():
        print(f"  {tag:25s} -> {qid}")
    print()
    print("IMPROVEMENTS over v2:")
    print("  - Category-specific ED fields (CategoryLabel, BrandedPrice, OptimalPrice,")
    print("    Product1-5, Product1Price-5Price) baked into each cell at creation")
    print("  - Debrief text now reveals OptimalProduct and OptimalPrice via piped text")
    print()
    print("IMPROVEMENTS over v1 (carried from v2):")
    print("  - feature_importance created as Matrix/Likert FROM SCRATCH (not converted from RO/DND)")
    print("  - Beautiful Amazon-style product cards (10K+ char HTML per category)")
    print("  - ChatGPT-style AI recommendation chat bubbles")
    print("  - DV counterbalancing: confidence vs detection order randomized")
    print("  - WTP measure after product choice ($0-500 numeric)")
    print("  - Manipulation checks: ai_seen, spec_reading, choice_driver")
    print("  - Process measures: 4-item Matrix/Likert (trust, competence, override, control)")
    print("  - Table row shuffler JS on product table")
    print("  - Choice randomization on comprehension and product choice questions")
    print("  - Advanced randomization on detection (pin 'not sure' last)")
    print("  - Optimized page breaks and timing gates")
    print()
    print("IMPORTANT: Update EOSRedirectURL with actual Prolific completion code before launch!")
    print("IMPORTANT: Update consent form with approved IRB text before launch!")

    return survey_id


if __name__ == "__main__":
    main()
