"""Audit Study 3 data capture — verify all fields are recorded."""
import re, requests, json

API = "https://pdx1.qualtrics.com/API/v3"
H = {"X-API-TOKEN": "Br4dAvcZOSSsJcup0AXpLDj7BjuGs1Pp96nNirWY"}
SID = "SV_8A33OiyMqjqr5LU"

# Read JS and find all setEmbeddedData calls
with open("study3-chatbot/QUALTRICS_CHATBOT.js", encoding="utf-8") as f:
    js = f.read()

# Find ed('field', ...) shorthand calls
ed_pattern = re.compile(r"ed\('([^']+)'")
sed_pattern = re.compile(r"setEmbeddedData\('([^']+)'")
js_fields = sorted(set(ed_pattern.findall(js) + sed_pattern.findall(js)))

print("EMBEDDED DATA SET BY JS:")
for field in js_fields:
    print(f"  {field}")
print(f"Total: {len(js_fields)}")

# Get Qualtrics flow embedded data
r = requests.get(f"{API}/survey-definitions/{SID}", headers=H)
survey = r.json()["result"]
flow = survey["SurveyFlow"]["Flow"]

flow_fields = set()
for item in flow:
    if item.get("Type") == "EmbeddedData":
        for ed in item.get("EmbeddedData", []):
            flow_fields.add(ed["Field"])
    if item.get("Type") == "BlockRandomizer":
        for cell in item.get("Flow", []):
            if cell.get("Type") == "EmbeddedData":
                for ed in cell.get("EmbeddedData", []):
                    flow_fields.add(ed["Field"])

print(f"\nEMBEDDED DATA IN FLOW: {len(flow_fields)} fields")

# Fields set by JS but NOT in flow = WON'T EXPORT
missing = sorted(set(js_fields) - flow_fields)
if missing:
    print(f"\n*** CRITICAL: These fields are SET by JS but NOT initialized in flow:")
    print(f"*** They will NOT appear in Qualtrics export!")
    for f in missing:
        print(f"  - {f}")
else:
    print("\nAll JS fields initialized in flow. Good.")

# Required fields audit
print(f"\n--- REQUIRED DATA AUDIT ---")
required = [
    ("study3_session_id", "Session ID"),
    ("study3_condition", "Condition (biased/honest/neutral)"),
    ("study3_ai_brand", "AI brand skin"),
    ("study3_assortment", "Full assortment JSON"),
    ("study3_category", "Product category"),
    ("study3_recommended", "AI-recommended product"),
    ("study3_optimal", "Spec-dominant product"),
    ("study3_display_order", "Shuffled card order"),
    ("study3_product_choice", "Participant's choice"),
    ("study3_product_choice_price", "Choice price"),
    ("study3_chose_optimal", "Chose optimal? (bool)"),
    ("study3_chose_recommended", "Followed AI? (bool)"),
    ("study3_conversation_complete", "Finished conversation?"),
    ("study3_total_turns", "Turn count"),
]

for field, desc in required:
    in_js = field in js_fields
    in_flow = field in flow_fields
    if in_js and in_flow:
        status = "OK"
    elif in_js:
        status = "JS ONLY - MISSING FROM FLOW!"
    elif in_flow:
        status = "FLOW ONLY - not set by JS"
    else:
        status = "COMPLETELY MISSING!"
    print(f"  {field:<35s} [{status}] {desc}")

# Check msg/response fields
print(f"\n--- MESSAGE FIELDS ---")
msg_missing = []
for i in range(1, 21):
    for prefix in ["msg_", "response_"]:
        field = f"{prefix}{i}"
        if field not in flow_fields:
            msg_missing.append(field)

if msg_missing:
    print(f"  MISSING from flow: {msg_missing[:5]}...")
    print(f"  Total missing: {len(msg_missing)} (msg/response fields not initialized)")
else:
    print(f"  All msg_1..20 and response_1..20 initialized. Good.")

# Check questions
print(f"\n--- SURVEY QUESTIONS ---")
for qid in sorted(survey["Questions"].keys(), key=lambda x: int(x.replace("QID",""))):
    q = survey["Questions"][qid]
    tag = q.get("DataExportTag", "?")
    qtype = q.get("QuestionType", "?")
    sel = q.get("Selector", "")
    print(f"  {qid:<8s} [{tag:<20s}] {qtype}/{sel}")

# Check flow order
print(f"\n--- FLOW ORDER ---")
blocks = survey["Blocks"]
for item in flow:
    t = item.get("Type", "?")
    if t == "Standard":
        bid = item.get("ID", "")
        desc = blocks.get(bid, {}).get("Description", bid)
        qcount = sum(1 for e in blocks.get(bid, {}).get("BlockElements", []) if e.get("Type") == "Question")
        print(f"  {desc} ({qcount}Q)")
    elif t == "BlockRandomizer":
        cells = item.get("Flow", [])
        conds = []
        for c in cells:
            for ed in c.get("EmbeddedData", []):
                if ed["Field"] == "ConditionD":
                    conds.append(ed["Value"])
        print(f"  Randomizer: {conds}")
    elif t == "Branch":
        print(f"  Branch")
    elif t == "EmbeddedData":
        print(f"  EmbeddedData ({len(item.get('EmbeddedData',[]))} fields)")
    elif t == "EndSurvey":
        print(f"  EndSurvey")

print(f"\n--- AUDIT COMPLETE ---")
