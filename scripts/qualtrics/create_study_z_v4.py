"""
Create Study Z (V4): Head-to-Head Competition
2 between-subjects conditions x 3 between-subjects categories = 6 cells
- AI-assisted vs Unassisted
- Earbuds vs Speakers vs SSDs
Competition framing: post-hoc pairing, $2 bonus for higher-utility choice
"""
import requests, json, sys, time

BASE = "https://pdx1.qualtrics.com/API/v3"
HEADERS = {"X-API-TOKEN": "Br4dAvcZOSSsJcup0AXpLDj7BjuGs1Pp96nNirWY", "Content-Type": "application/json"}
OPTS = {"BlockLocking": "false", "RandomizeQuestions": "false", "BlockVisibility": "Expanded"}

def api(method, path, data=None):
    url = BASE + path
    for attempt in range(3):
        try:
            if method == "POST": r = requests.post(url, headers=HEADERS, json=data, timeout=30)
            elif method == "PUT": r = requests.put(url, headers=HEADERS, json=data, timeout=30)
            elif method == "GET": r = requests.get(url, headers=HEADERS, timeout=30)
            else: return None
            if r.status_code in (200, 201): return r.json()
            if attempt == 2: print(f"  FAIL {method} {path}: {r.status_code}")
            time.sleep(1)
        except Exception as e:
            if attempt == 2: print(f"  ERROR: {e}")
            time.sleep(1)
    return None

# Product choices per category
EARBUDS_CHOICES = {
    "1": {"Display": "Apple AirPods Pro 2 ($249.00)"},
    "2": {"Display": "Samsung Galaxy Buds3 Pro ($199.99)"},
    "3": {"Display": "Sony WF-1000XM5 ($279.99)"},
    "4": {"Display": "Auralis Air4 Pro ($59.99)"},
    "5": {"Display": "Jabra Elite 85t ($179.99)"},
}
SPEAKERS_CHOICES = {
    "1": {"Display": "JBL Flip 6 ($129.99)"},
    "2": {"Display": "Bose SoundLink Flex ($149.99)"},
    "3": {"Display": "Sony SRS-XB43 ($199.99)"},
    "4": {"Display": "Wavecrest StormBox Pro ($89.99)"},
    "5": {"Display": "Anker Soundcore Motion+ ($99.99)"},
}
SSDS_CHOICES = {
    "1": {"Display": "Samsung T7 Shield ($139.99)"},
    "2": {"Display": "SanDisk Extreme V2 ($119.99)"},
    "3": {"Display": "Western Digital My Passport ($109.99)"},
    "4": {"Display": "Vaultdrive PD60 ($89.99)"},
    "5": {"Display": "Seagate One Touch ($99.99)"},
}

print("=" * 60)
print("Creating Study Z (V4): Head-to-Head Competition")
print("=" * 60)

# 1. Create survey
r = api("POST", "/survey-definitions", {
    "SurveyName": "SR V4 Study Z -- Competition",
    "Language": "EN", "ProjectCategory": "CORE"
})
sid = r["result"]["SurveyID"]
defblock = r["result"]["DefaultBlockID"]
print(f"Survey: {sid}")

# 2. Create blocks
bnames = ["screening", "stimulus", "choice_earbuds", "choice_speakers", "choice_ssds",
          "process_measures", "demographics"]
blocks = {}
for name in bnames:
    r = api("POST", f"/survey-definitions/{sid}/blocks",
            {"Type": "Standard", "Description": name, "Options": OPTS})
    if r: blocks[name] = r["result"]["BlockID"]
print(f"Blocks: {len(blocks)}")

# 3. Create questions
Q = {}

# Consent with competition framing
r = api("POST", f"/survey-definitions/{sid}/questions", {
    "QuestionText": """<h3>Consent Form</h3>
<p><strong>Title:</strong> Consumer Product Evaluation Study<br>
<strong>Investigator:</strong> Dr. Felipe Affonso, Oklahoma State University</p>
<p>This study takes approximately 4-5 minutes. Your responses are anonymous.</p>
<p><strong>Competition bonus:</strong> After data collection, your product choice will be
randomly paired with another participant's choice from a different condition. The participant
in each pair whose chosen product scores higher on our quality-value evaluation system will
receive a <strong>$2 bonus</strong>. The other participant receives no bonus. Ties: both
receive $1. Bonuses paid within 5 business days via Prolific.</p>
<p>Select I agree if you are 18+ and consent.</p>""",
    "QuestionType": "MC", "Selector": "SAVR", "SubSelector": "TX",
    "Choices": {"1": {"Display": "I agree"}, "2": {"Display": "I do not agree"}},
    "DataExportTag": "consent",
    "Validation": {"Settings": {"ForceResponse": "ON", "Type": "None"}}
})
if r: Q["consent"] = r["result"]["QuestionID"]; print(f"  {Q['consent']}: consent")

# Attention check
r = api("POST", f"/survey-definitions/{sid}/questions", {
    "QuestionText": "Select the word describing an animal.",
    "QuestionType": "MC", "Selector": "SAVR", "SubSelector": "TX",
    "Choices": {"1": {"Display": "Rock"}, "2": {"Display": "Bicycle"},
                "3": {"Display": "Trumpet"}, "4": {"Display": "Horse"},
                "5": {"Display": "Ladder"}, "6": {"Display": "Candle"}},
    "DataExportTag": "attn_check",
    "Validation": {"Settings": {"ForceResponse": "ON", "Type": "None"}},
    "Randomization": {"Type": "All", "Advanced": None, "TotalRandSubset": ""}
})
if r: Q["attn"] = r["result"]["QuestionID"]; print(f"  {Q['attn']}: attn_check")

# Stimulus (piped product table + optional AI rec)
r = api("POST", f"/survey-definitions/{sid}/questions", {
    "QuestionText": "${e://Field/ProductTable}\n${e://Field/AIRecommendation}\n<p>Choose the product that offers the best combination of quality and value. Your choice will be compared to another participant's.</p>",
    "QuestionType": "DB", "Selector": "TB", "DataExportTag": "stimulus_display"
})
if r: Q["stimulus"] = r["result"]["QuestionID"]; print(f"  {Q['stimulus']}: stimulus")

# Timer
r = api("POST", f"/survey-definitions/{sid}/questions", {
    "QuestionText": "Timer", "QuestionType": "Timing", "Selector": "PageTimer",
    "Choices": {"1": {"Display": "FC"}, "2": {"Display": "LC"},
                "3": {"Display": "PS"}, "4": {"Display": "CC"}},
    "DataExportTag": "timer_stimulus", "Configuration": {"MinSeconds": "10"}
})
if r: Q["timer"] = r["result"]["QuestionID"]; print(f"  {Q['timer']}: timer")

# Category-specific choice questions (with DisplayLogic to be added)
for cat, cat_choices, cat_label in [
    ("earbuds", EARBUDS_CHOICES, "earbuds"),
    ("speakers", SPEAKERS_CHOICES, "speakers"),
    ("ssds", SSDS_CHOICES, "ssds")
]:
    r = api("POST", f"/survey-definitions/{sid}/questions", {
        "QuestionText": f"Which {cat_label} product would you <strong>choose</strong>? Remember: your choice will be scored against another participant's.",
        "QuestionType": "MC", "Selector": "SAVR", "SubSelector": "TX",
        "Choices": cat_choices,
        "DataExportTag": f"choice_{cat}",
        "Validation": {"Settings": {"ForceResponse": "ON", "Type": "None"}},
        "Randomization": {"Type": "All", "Advanced": None, "TotalRandSubset": ""}
    })
    if r: Q[f"choice_{cat}"] = r["result"]["QuestionID"]; print(f"  {Q[f'choice_{cat}']}: choice_{cat}")

# Process measures
r = api("POST", f"/survey-definitions/{sid}/questions", {
    "QuestionText": "How confident are you that your choice has the best quality-value combination?",
    "QuestionType": "MC", "Selector": "SAHR",
    "Choices": {str(i): {"Display": {1: "1-Not confident", 4: "4-Moderate", 7: "7-Very confident"}.get(i, str(i))} for i in range(1, 8)},
    "DataExportTag": "confidence",
    "Validation": {"Settings": {"ForceResponse": "ON", "Type": "None"}}
})
if r: Q["confidence"] = r["result"]["QuestionID"]; print(f"  {Q['confidence']}: confidence")

r = api("POST", f"/survey-definitions/{sid}/questions", {
    "QuestionText": "What was the main reason for your choice?",
    "QuestionType": "TE", "Selector": "SL", "DataExportTag": "choice_reason",
    "Validation": {"Settings": {"ForceResponse": "ON", "Type": "None"}}
})
if r: Q["reason"] = r["result"]["QuestionID"]; print(f"  {Q['reason']}: choice_reason")

# Demographics
for tag, text, qtype, selector, choices in [
    ("age", "Age?", "MC", "DL", {str(i): {"Display": str(i)} for i in range(18, 100)}),
    ("gender", "Gender?", "MC", "SAVR",
     {"1": {"Display": "Female"}, "2": {"Display": "Male"},
      "3": {"Display": "Non-binary"}, "4": {"Display": "Prefer not to say"}}),
    ("ai_usage", "How often do you use AI for shopping?", "MC", "SAHR",
     {"1": {"Display": "1-Never"}, "2": {"Display": "2-Rarely"},
      "3": {"Display": "3-Sometimes"}, "4": {"Display": "4-Often"}, "5": {"Display": "5-Always"}}),
]:
    qdef = {"QuestionText": text, "QuestionType": qtype, "Selector": selector,
            "Choices": choices, "DataExportTag": tag,
            "Validation": {"Settings": {"ForceResponse": "ON", "Type": "None"}}}
    if qtype == "MC" and selector == "SAVR": qdef["SubSelector"] = "TX"
    r = api("POST", f"/survey-definitions/{sid}/questions", qdef)
    if r: Q[tag] = r["result"]["QuestionID"]; print(f"  {Q[tag]}: {tag}")

print(f"Total questions: {len(Q)}")

# 4. Assign to blocks
print("\n4. Assigning to blocks...")
api("PUT", f"/survey-definitions/{sid}/blocks/{defblock}",
    {"Type": "Standard", "Description": "Default", "BlockElements": [], "Options": OPTS})

assigns = {
    "screening": ["consent", "attn"],
    "stimulus": ["stimulus", "timer"],
    "choice_earbuds": ["choice_earbuds"],
    "choice_speakers": ["choice_speakers"],
    "choice_ssds": ["choice_ssds"],
    "process_measures": ["confidence", "reason"],
    "demographics": ["age", "gender", "ai_usage"],
}

for bname, tags in assigns.items():
    elements = []
    for i, tag in enumerate(tags):
        if tag in Q:
            elements.append({"Type": "Question", "QuestionID": Q[tag]})
            if i < len(tags) - 1: elements.append({"Type": "Page Break"})
    r = api("PUT", f"/survey-definitions/{sid}/blocks/{blocks[bname]}",
            {"Type": "Standard", "Description": bname, "BlockElements": elements, "Options": OPTS})
    print(f"  {bname}: {'OK' if r else 'FAIL'}")
    time.sleep(0.3)

# 5. Flow with 6-condition BlockRandomizer (2 AI x 3 categories)
print("\n5. Setting up flow...")

conditions = [
    {"Condition": "1", "ConditionD": "AI_earbuds", "AICondition": "AI", "Category": "earbuds",
     "ProductTable": "[EARBUDS_TABLE]", "AIRecommendation": "[BIASED_AI_EARBUDS]"},
    {"Condition": "2", "ConditionD": "NoAI_earbuds", "AICondition": "NoAI", "Category": "earbuds",
     "ProductTable": "[EARBUDS_TABLE]", "AIRecommendation": ""},
    {"Condition": "3", "ConditionD": "AI_speakers", "AICondition": "AI", "Category": "speakers",
     "ProductTable": "[SPEAKERS_TABLE]", "AIRecommendation": "[BIASED_AI_SPEAKERS]"},
    {"Condition": "4", "ConditionD": "NoAI_speakers", "AICondition": "NoAI", "Category": "speakers",
     "ProductTable": "[SPEAKERS_TABLE]", "AIRecommendation": ""},
    {"Condition": "5", "ConditionD": "AI_ssds", "AICondition": "AI", "Category": "ssds",
     "ProductTable": "[SSDS_TABLE]", "AIRecommendation": "[BIASED_AI_SSDS]"},
    {"Condition": "6", "ConditionD": "NoAI_ssds", "AICondition": "NoAI", "Category": "ssds",
     "ProductTable": "[SSDS_TABLE]", "AIRecommendation": ""},
]

rand_flow = []
for i, c in enumerate(conditions):
    eds = [{"Description": k, "Type": "Custom", "Field": k, "Value": v} for k, v in c.items()]
    rand_flow.append({"Type": "EmbeddedData", "FlowID": f"FL_C{i+1}", "EmbeddedData": eds})

# Category-specific choice blocks with conditional display
# Use Branch logic in flow to show only the relevant choice block
flow = {"FlowID": "FL_1", "Type": "Root", "Flow": [
    {"Type": "EmbeddedData", "FlowID": "FL_INIT", "EmbeddedData": [
        {"Description": "Condition", "Type": "Custom", "Field": "Condition", "Value": ""},
        {"Description": "ConditionD", "Type": "Custom", "Field": "ConditionD", "Value": ""},
        {"Description": "AICondition", "Type": "Custom", "Field": "AICondition", "Value": ""},
        {"Description": "Category", "Type": "Custom", "Field": "Category", "Value": ""},
        {"Description": "ProductTable", "Type": "Custom", "Field": "ProductTable", "Value": ""},
        {"Description": "AIRecommendation", "Type": "Custom", "Field": "AIRecommendation", "Value": ""},
        {"Description": "ProductDisplayOrder", "Type": "Custom", "Field": "ProductDisplayOrder", "Value": ""},
    ]},
    {"Type": "Block", "ID": blocks["screening"], "FlowID": "FL_SCR"},
    {"Type": "BlockRandomizer", "FlowID": "FL_R", "SubSet": 1, "EvenPresentation": True, "Flow": rand_flow},
    {"Type": "Block", "ID": blocks["stimulus"], "FlowID": "FL_STIM"},
    # All 3 choice blocks shown -- only relevant one will have products (via DisplayLogic on questions)
    {"Type": "Block", "ID": blocks["choice_earbuds"], "FlowID": "FL_CE"},
    {"Type": "Block", "ID": blocks["choice_speakers"], "FlowID": "FL_CS"},
    {"Type": "Block", "ID": blocks["choice_ssds"], "FlowID": "FL_CD"},
    {"Type": "Block", "ID": blocks["process_measures"], "FlowID": "FL_PM"},
    {"Type": "Block", "ID": blocks["demographics"], "FlowID": "FL_DM"},
    {"Type": "EndSurvey", "FlowID": "FL_END"}
]}

r = api("PUT", f"/survey-definitions/{sid}/flow", flow)
print(f"Flow: {'OK' if r else 'FAIL'}")

# 6. Activate
r = api("PUT", f"/surveys/{sid}", {"isActive": True})
print(f"Active: {r is not None}")

# 7. Verify
print("\n=== VERIFICATION ===")
r = api("GET", f"/survey-definitions/{sid}")
if r:
    for bid, bd in r["result"].get("Blocks", {}).items():
        desc = bd.get("Description", "?")
        qs = [e.get("QuestionID", "") for e in bd.get("BlockElements", []) if e.get("Type") == "Question"]
        if qs: print(f"  {desc}: {qs}")

print(f"\nStudy Z: {sid}")
print(f"Edit: https://okstatebusiness.az1.qualtrics.com/survey-builder/{sid}/edit")
print(f"Live: https://okstatebusiness.az1.qualtrics.com/jfe/form/{sid}")
print("\nNOTE: Product tables and AI recs are PLACEHOLDERS.")
print("Category-specific choice questions need DisplayLogic (Category==earbuds/speakers/ssds).")
print("Full HTML must be injected into BlockRandomizer EmbeddedData values.")
