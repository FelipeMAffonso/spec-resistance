"""Build Study 3 pilot: 3 conditions + intro + feedback + demographics."""
import requests, json
API = "https://pdx1.qualtrics.com/API/v3"
H = {"X-API-TOKEN": "Br4dAvcZOSSsJcup0AXpLDj7BjuGs1Pp96nNirWY", "Content-Type": "application/json"}
SID = "SV_8A33OiyMqjqr5LU"

def make_ed(field, value):
    return {"Description": field, "Type": "Custom", "Field": field,
            "VariableType": "String", "DataVisibility": [], "AnalyzeText": False, "Value": value}

# Get current survey
r = requests.get(f"{API}/survey-definitions/{SID}", headers=H)
survey = r.json()["result"]
blocks = survey["Blocks"]
flow = survey["SurveyFlow"]

# 1. Update BlockRandomizer: 3 conditions
print("1. Updating BlockRandomizer...")
cells = [
    {"Type": "EmbeddedData", "FlowID": "FL_S3_1", "EmbeddedData": [
        make_ed("Condition", "1"), make_ed("ConditionD", "Biased"), make_ed("study3_condition", "biased")]},
    {"Type": "EmbeddedData", "FlowID": "FL_S3_2", "EmbeddedData": [
        make_ed("Condition", "2"), make_ed("ConditionD", "Honest"), make_ed("study3_condition", "honest")]},
    {"Type": "EmbeddedData", "FlowID": "FL_S3_3", "EmbeddedData": [
        make_ed("Condition", "3"), make_ed("ConditionD", "Neutral"), make_ed("study3_condition", "neutral")]},
]
for item in flow["Flow"]:
    if item.get("Type") == "BlockRandomizer" and item.get("SubSet") == 1:
        item["Flow"] = cells
        break
print("  3 cells: Biased, Honest, Neutral")

# 2. Create intro question
print("2. Creating intro screen...")
intro_html = (
    '<div style="max-width:700px;margin:0 auto;font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif;padding:20px">'
    '<h2 style="margin-bottom:16px">AI Shopping Assistant</h2>'
    '<p style="font-size:15px;line-height:1.7;color:#333">On the next page, you will interact with an '
    '<strong>AI-powered shopping assistant</strong> to help you find a product.</p>'
    '<p style="font-size:15px;line-height:1.7;color:#333">Please use it as you normally would when shopping online:</p>'
    '<ul style="font-size:15px;line-height:1.8;color:#333">'
    '<li>Tell the assistant what product you are looking for</li>'
    '<li>Answer any questions it asks about your preferences</li>'
    '<li>Browse the products it finds</li>'
    '<li>Select the product you would choose to purchase</li></ul>'
    '<p style="font-size:15px;line-height:1.7;color:#333">There are no right or wrong answers.</p></div>'
)
r = requests.post(f"{API}/survey-definitions/{SID}/questions", headers=H, json={
    "QuestionText": intro_html, "QuestionType": "DB", "Selector": "TB",
    "DataExportTag": "intro_screen", "Language": []})
intro_qid = r.json().get("result", {}).get("QuestionID")
print(f"  intro: {intro_qid}")

# 3. Create feedback question
print("3. Creating feedback question...")
r = requests.post(f"{API}/survey-definitions/{SID}/questions", headers=H, json={
    "QuestionText": ("Thank you for using the AI shopping assistant!<br><br>"
        "<strong>Please share any feedback about your experience.</strong> "
        "Did anything feel unusual? Any technical issues? What worked well? "
        "We appreciate your honest thoughts."),
    "QuestionType": "TE", "Selector": "ML",
    "DataExportTag": "pilot_feedback", "Language": [],
    "Validation": {"Settings": {"ForceResponse": "ON", "ForceResponseType": "ON", "Type": "None"}}})
feedback_qid = r.json().get("result", {}).get("QuestionID")
print(f"  feedback: {feedback_qid}")

# 4. Create suspicion probe
print("4. Creating suspicion probe...")
r = requests.post(f"{API}/survey-definitions/{SID}/questions", headers=H, json={
    "QuestionText": "In your own words, what do you think this study was about?",
    "QuestionType": "TE", "Selector": "SL",
    "DataExportTag": "suspicion_probe", "Language": [],
    "Validation": {"Settings": {"ForceResponse": "ON", "ForceResponseType": "ON", "Type": "None"}}})
suspicion_qid = r.json().get("result", {}).get("QuestionID")
print(f"  suspicion: {suspicion_qid}")

# 5. Create blocks
print("5. Creating blocks...")
r = requests.post(f"{API}/survey-definitions/{SID}/blocks", headers=H, json={
    "Type": "Standard", "Description": "intro",
    "Options": {"BlockLocking": "false", "RandomizeQuestions": "false", "BlockVisibility": "Expanded"}})
intro_bid = r.json().get("result", {}).get("BlockID")

r = requests.post(f"{API}/survey-definitions/{SID}/blocks", headers=H, json={
    "Type": "Standard", "Description": "feedback",
    "Options": {"BlockLocking": "false", "RandomizeQuestions": "false", "BlockVisibility": "Expanded"}})
feedback_bid = r.json().get("result", {}).get("BlockID")
print(f"  intro block: {intro_bid}, feedback block: {feedback_bid}")

# Assign questions to blocks
if intro_bid and intro_qid:
    requests.put(f"{API}/survey-definitions/{SID}/blocks/{intro_bid}", headers=H, json={
        "Type": "Standard", "Description": "intro",
        "BlockElements": [{"Type": "Question", "QuestionID": intro_qid}],
        "Options": {"BlockLocking": "false", "RandomizeQuestions": "false", "BlockVisibility": "Expanded"}})

if feedback_bid and feedback_qid and suspicion_qid:
    requests.put(f"{API}/survey-definitions/{SID}/blocks/{feedback_bid}", headers=H, json={
        "Type": "Standard", "Description": "feedback",
        "BlockElements": [
            {"Type": "Question", "QuestionID": feedback_qid},
            {"Type": "Page Break"},
            {"Type": "Question", "QuestionID": suspicion_qid}],
        "Options": {"BlockLocking": "false", "RandomizeQuestions": "false", "BlockVisibility": "Expanded"}})

# 6. Add study3_condition to embedded data
for item in flow["Flow"]:
    if item.get("Type") == "EmbeddedData":
        existing = {ed["Field"] for ed in item.get("EmbeddedData", [])}
        if "study3_condition" not in existing:
            item["EmbeddedData"].append(make_ed("study3_condition", ""))
        break

# 7. Rebuild flow
print("6. Rebuilding flow...")
block_map = {bdef.get("Description", bid): bid for bid, bdef in blocks.items()}
screening_bid = block_map.get("screening")
stimulus_bid = block_map.get("stimulus")
demographics_bid = block_map.get("demographics")

branches = [item for item in flow["Flow"] if item.get("Type") == "Branch"]
ed_inits = [item for item in flow["Flow"] if item.get("Type") == "EmbeddedData"]
randomizers = [item for item in flow["Flow"] if item.get("Type") == "BlockRandomizer"]
randomizer = randomizers[0] if randomizers else None

new_flow = []
for ed in ed_inits:
    new_flow.append(ed)
if screening_bid:
    new_flow.append({"Type": "Standard", "ID": screening_bid, "FlowID": "FL_SCR", "Autofill": []})
for br in branches:
    new_flow.append(br)
if randomizer:
    new_flow.append(randomizer)
if intro_bid:
    new_flow.append({"Type": "Standard", "ID": intro_bid, "FlowID": "FL_INTRO", "Autofill": []})
if stimulus_bid:
    new_flow.append({"Type": "Standard", "ID": stimulus_bid, "FlowID": "FL_CHAT", "Autofill": []})
if feedback_bid:
    new_flow.append({"Type": "Standard", "ID": feedback_bid, "FlowID": "FL_FB", "Autofill": []})
if demographics_bid:
    new_flow.append({"Type": "Standard", "ID": demographics_bid, "FlowID": "FL_DEMO", "Autofill": []})
new_flow.append({"Type": "EndSurvey", "FlowID": "FL_END"})

flow["Flow"] = new_flow
r = requests.put(f"{API}/survey-definitions/{SID}/flow", headers=H, json=flow)
print(f"  Flow update: {r.status_code}")

# Print final flow
for item in new_flow:
    t = item.get("Type", "?")
    if t == "Standard":
        bid = item.get("ID", "")
        for bdesc, bbid in block_map.items():
            if bbid == bid:
                print(f"    {bdesc}")
                break
        else:
            if bid == intro_bid: print("    intro (NEW)")
            elif bid == feedback_bid: print("    feedback (NEW)")
            else: print(f"    {bid}")
    elif t == "BlockRandomizer":
        print(f"    Randomizer ({len(item.get('Flow',[]))} cells: Biased/Honest/Neutral)")
    elif t == "Branch": print("    Branch")
    elif t == "EmbeddedData": print("    EmbeddedData")
    elif t == "EndSurvey": print("    EndSurvey")

print(f"\nSurvey: https://okstatebusiness.az1.qualtrics.com/jfe/form/{SID}")
print("Ready for pilot!")
