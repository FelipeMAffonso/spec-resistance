"""
Create Study Y (V4): Transparency Remedy -- Disclosure Gradient
5 between-subjects conditions: NoAI, AI_NoDis, AI_Generic, AI_Mechanism, AI_Quantified
Uses PLACEHOLDER text for AI rec and disclosures (must be replaced with full HTML via Qualtrics UI or API update)
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

print("=" * 60)
print("Creating Study Y (V4): Disclosure Gradient")
print("=" * 60)

# 1. Create survey
r = api("POST", "/survey-definitions", {"SurveyName": "SR V4 Study Y -- Disclosure Gradient", "Language": "EN", "ProjectCategory": "CORE"})
sid = r["result"]["SurveyID"]
defblock = r["result"]["DefaultBlockID"]
print(f"Survey: {sid}")

# 2. Create blocks
bnames = ["screening", "preference", "stimulus", "product_choice", "disclosure_recall",
          "trust_policy", "brand_awareness", "debrief", "demographics"]
blocks = {}
for name in bnames:
    r = api("POST", f"/survey-definitions/{sid}/blocks", {"Type": "Standard", "Description": name, "Options": OPTS})
    if r: blocks[name] = r["result"]["BlockID"]
print(f"Blocks: {len(blocks)}")

# 3. Create questions
Q = {}

# Simple MC/TE questions
simple_qs = [
    ("consent", "MC", "SAVR",
     "<h3>Consent</h3><p>Consumer Product Evaluation Study. Dr. Felipe Affonso, OSU. ~5-6 min. Anonymous. 1 in 50 gets their chosen product.</p><p>Select I agree if you are 18+ and consent.</p>",
     {"1": {"Display": "I agree"}, "2": {"Display": "I do not agree"}}, False),
    ("attn_check", "MC", "SAVR",
     "Select the word describing an animal.",
     {"1": {"Display": "Rock"}, "2": {"Display": "Bicycle"}, "3": {"Display": "Trumpet"},
      "4": {"Display": "Horse"}, "5": {"Display": "Ladder"}, "6": {"Display": "Candle"}}, True),
    ("product_choice", "MC", "SAVR",
     "Which product would you <strong>choose</strong>?",
     {"1": {"Display": "Apple AirPods Pro 2 ($249.00)"}, "2": {"Display": "Samsung Galaxy Buds3 Pro ($199.99)"},
      "3": {"Display": "Sony WF-1000XM5 ($279.99)"}, "4": {"Display": "Auralis Air4 Pro ($59.99)"},
      "5": {"Display": "Jabra Elite 85t ($179.99)"}}, True),
    ("disclosure_recall", "TE", "SL",
     "If you saw a note or warning below the AI recommendation, describe what it said. If none, type N/A.", None, False),
    ("revise_yn", "MC", "SAVR",
     "Would you like to change your product choice?",
     {"1": {"Display": "Yes, choose differently"}, "2": {"Display": "No, keep my choice"}}, False),
    ("suspicion", "TE", "SL", "What do you think this study was about?", None, False),
    ("age", "MC", "DL", "Age?", {str(i): {"Display": str(i)} for i in range(18, 100)}, False),
    ("gender", "MC", "SAVR", "Gender?",
     {"1": {"Display": "Female"}, "2": {"Display": "Male"}, "3": {"Display": "Non-binary"},
      "4": {"Display": "Prefer not to say"}}, False),
    ("ai_usage", "MC", "SAHR", "How often do you use AI tools for shopping?",
     {"1": {"Display": "1-Never"}, "2": {"Display": "2-Rarely"}, "3": {"Display": "3-Sometimes"},
      "4": {"Display": "4-Often"}, "5": {"Display": "5-Always"}}, False),
]

for tag, qtype, selector, text, choices, randomize in simple_qs:
    qdef = {"QuestionText": text, "QuestionType": qtype, "Selector": selector,
            "DataExportTag": tag, "Validation": {"Settings": {"ForceResponse": "ON", "Type": "None"}}}
    if qtype == "MC": qdef["SubSelector"] = "TX"
    if choices: qdef["Choices"] = choices
    if randomize: qdef["Randomization"] = {"Type": "All", "Advanced": None, "TotalRandSubset": ""}
    r = api("POST", f"/survey-definitions/{sid}/questions", qdef)
    if r: Q[tag] = r["result"]["QuestionID"]; print(f"  {Q[tag]}: {tag}")

# Matrix questions
matrices = [
    ("feature_importance", "How important is each feature when choosing earbuds? (1=Not important, 7=Extremely)",
     {"1": {"Display": "Battery life"}, "2": {"Display": "Noise cancellation"},
      "3": {"Display": "Sound quality"}, "4": {"Display": "Price/value"},
      "5": {"Display": "Brand reputation"}, "6": {"Display": "Water resistance"}},
     {str(i): {"Display": str(i)} for i in range(1, 8)}),
    ("trust_policy", "Rate your agreement with each statement (1=Strongly disagree, 7=Strongly agree):",
     {"1": {"Display": "I trust AI shopping assistants to recommend the best products"},
      "2": {"Display": "AI shopping tools should be required to disclose potential biases"},
      "3": {"Display": "I would support regulation requiring AI recommendations to be audited"},
      "4": {"Display": "I would independently verify an AI product recommendation"}},
     {str(i): {"Display": str(i)} for i in range(1, 8)}),
    ("brand_awareness", "For each brand, indicate your familiarity:",
     {"1": {"Display": "Apple"}, "2": {"Display": "Samsung"}, "3": {"Display": "Sony"},
      "4": {"Display": "Auralis"}, "5": {"Display": "Jabra"}},
     {"1": {"Display": "I own products from this brand"},
      "2": {"Display": "I have heard of this brand"},
      "3": {"Display": "I have never heard of this brand"}}),
]

for tag, text, choices, answers in matrices:
    r = api("POST", f"/survey-definitions/{sid}/questions", {
        "QuestionText": text, "QuestionType": "Matrix", "Selector": "Likert",
        "SubSelector": "SingleAnswer", "Choices": choices, "Answers": answers,
        "DataExportTag": tag, "Validation": {"Settings": {"ForceResponse": "ON", "Type": "None"}},
        "Randomization": {"Type": "All", "Advanced": None, "TotalRandSubset": ""}
    })
    if r: Q[tag] = r["result"]["QuestionID"]; print(f"  {Q[tag]}: {tag} (Matrix)")

# Display/Timer questions
r = api("POST", f"/survey-definitions/{sid}/questions", {
    "QuestionText": "PRODUCT TABLE + AI REC + DISCLOSURE (piped via embedded data: ${e://Field/AIRecommendation} ${e://Field/DisclosureText})",
    "QuestionType": "DB", "Selector": "TB", "DataExportTag": "stimulus_display"
})
if r: Q["stimulus"] = r["result"]["QuestionID"]; print(f"  {Q['stimulus']}: stimulus (DB)")

r = api("POST", f"/survey-definitions/{sid}/questions", {
    "QuestionText": "Thank you. Different participants saw different AI recommendations and disclosure levels.",
    "QuestionType": "DB", "Selector": "TB", "DataExportTag": "debrief_display"
})
if r: Q["debrief"] = r["result"]["QuestionID"]; print(f"  {Q['debrief']}: debrief (DB)")

r = api("POST", f"/survey-definitions/{sid}/questions", {
    "QuestionText": "Timer", "QuestionType": "Timing", "Selector": "PageTimer",
    "Choices": {"1": {"Display": "FC"}, "2": {"Display": "LC"}, "3": {"Display": "PS"}, "4": {"Display": "CC"}},
    "DataExportTag": "timer_stimulus", "Configuration": {"MinSeconds": "15"}
})
if r: Q["timer"] = r["result"]["QuestionID"]; print(f"  {Q['timer']}: timer")

print(f"Total questions: {len(Q)}")

# 4. Clear default block and assign
print("\n4. Assigning to blocks...")
api("PUT", f"/survey-definitions/{sid}/blocks/{defblock}",
    {"Type": "Standard", "Description": "Default", "BlockElements": [], "Options": OPTS})

assigns = {
    "screening": ["consent", "attn_check"],
    "preference": ["feature_importance"],
    "stimulus": ["stimulus", "timer"],
    "product_choice": ["product_choice"],
    "disclosure_recall": ["disclosure_recall"],
    "trust_policy": ["trust_policy"],
    "brand_awareness": ["brand_awareness"],
    "debrief": ["debrief", "revise_yn"],
    "demographics": ["suspicion", "age", "gender", "ai_usage"],
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

# 5. Flow with 5-condition BlockRandomizer
print("\n5. Setting up flow...")
conditions = [
    {"Condition": "1", "ConditionD": "NoAI", "AIRecommendation": "", "DisclosureText": ""},
    {"Condition": "2", "ConditionD": "AI_NoDis", "AIRecommendation": "[BIASED_AI_REC]", "DisclosureText": ""},
    {"Condition": "3", "ConditionD": "AI_Generic", "AIRecommendation": "[BIASED_AI_REC]", "DisclosureText": "[GENERIC_DISCLOSURE]"},
    {"Condition": "4", "ConditionD": "AI_Mechanism", "AIRecommendation": "[BIASED_AI_REC]", "DisclosureText": "[MECHANISM_DISCLOSURE]"},
    {"Condition": "5", "ConditionD": "AI_Quantified", "AIRecommendation": "[BIASED_AI_REC]", "DisclosureText": "[QUANTIFIED_DISCLOSURE]"},
]

rand_flow = []
for i, c in enumerate(conditions):
    eds = [{"Description": k, "Type": "Custom", "Field": k, "Value": v} for k, v in c.items()]
    rand_flow.append({"Type": "EmbeddedData", "FlowID": f"FL_C{i+1}", "EmbeddedData": eds})

flow = {"FlowID": "FL_1", "Type": "Root", "Flow": [
    {"Type": "EmbeddedData", "FlowID": "FL_INIT", "EmbeddedData": [
        {"Description": "ProductDisplayOrder", "Type": "Custom", "Field": "ProductDisplayOrder", "Value": ""},
        {"Description": "Condition", "Type": "Custom", "Field": "Condition", "Value": ""},
        {"Description": "ConditionD", "Type": "Custom", "Field": "ConditionD", "Value": ""},
        {"Description": "AIRecommendation", "Type": "Custom", "Field": "AIRecommendation", "Value": ""},
        {"Description": "DisclosureText", "Type": "Custom", "Field": "DisclosureText", "Value": ""},
    ]},
    {"Type": "Block", "ID": blocks["screening"], "FlowID": "FL_S"},
    {"Type": "BlockRandomizer", "FlowID": "FL_R", "SubSet": 1, "EvenPresentation": True, "Flow": rand_flow},
    {"Type": "Block", "ID": blocks["preference"], "FlowID": "FL_P"},
    {"Type": "Block", "ID": blocks["stimulus"], "FlowID": "FL_ST"},
    {"Type": "Block", "ID": blocks["product_choice"], "FlowID": "FL_CH"},
    {"Type": "Block", "ID": blocks["disclosure_recall"], "FlowID": "FL_DR"},
    {"Type": "Block", "ID": blocks["trust_policy"], "FlowID": "FL_TR"},
    {"Type": "Block", "ID": blocks["brand_awareness"], "FlowID": "FL_BR"},
    {"Type": "Block", "ID": blocks["debrief"], "FlowID": "FL_DB"},
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

print(f"\nStudy Y: {sid}")
print(f"Edit: https://okstatebusiness.az1.qualtrics.com/survey-builder/{sid}/edit")
print(f"Live: https://okstatebusiness.az1.qualtrics.com/jfe/form/{sid}")
print("\nNOTE: AI recommendation and disclosure HTML are PLACEHOLDERS.")
print("Must update the BlockRandomizer EmbeddedData values with full HTML via API or UI.")
