"""Build Study 1B (earbuds) by copying Study 1A (coffee makers) and swapping content."""
import requests, json, re

API = "https://pdx1.qualtrics.com/API/v3"
H = {"X-API-TOKEN": "Br4dAvcZOSSsJcup0AXpLDj7BjuGs1Pp96nNirWY", "Content-Type": "application/json"}
STUDY_A = "SV_cx2kueJwMOwdDj8"

# Step 1: Copy
print("Copying Study A...")
copy_h = {**H, "X-COPY-SOURCE": STUDY_A, "X-COPY-DESTINATION-OWNER": "UR_9GiLKDSXylBFeYu"}
r = requests.post(f"{API}/surveys", headers=copy_h, json={})
assert r.status_code in (200, 201), f"COPY FAILED: {r.status_code} {r.text[:300]}"
new_sid = r.json()["result"].get("id") or r.json()["result"].get("SurveyID")
print(f"  Created: {new_sid}")

requests.put(f"{API}/survey-definitions/{new_sid}/metadata", headers=H,
             json={"SurveyName": "SR Study 1B - AI Compliance Earbuds (2026-04-16)"})

# Step 2: Define earbuds content
EARBUDS_TABLE = (
    '<h3>Compare Sport Earbuds</h3>'
    '<p>You are looking for sport earbuds for intense workouts and running.</p>'
    '<table style="width:100%;border-collapse:collapse;font-size:13px">'
    '<thead><tr style="background:#f0f0f0">'
    '<th style="padding:8px;text-align:left">Brand</th>'
    '<th style="padding:8px">Model</th>'
    '<th style="padding:8px">Price</th>'
    '<th style="padding:8px">Fit | Battery | Codec | Water Resistance</th>'
    '<th style="padding:8px">Rating</th>'
    '</tr></thead><tbody>'
    '<tr><td style="padding:8px;font-weight:bold">Beats</td>'
    '<td style="padding:8px">Beats Fit Pro</td>'
    '<td style="padding:8px;color:#0f7b0f">$159.99</td>'
    '<td style="padding:8px">wingtip | 6h (27h case) | AAC | IPX4</td>'
    '<td style="padding:8px">4.3</td></tr>'
    '<tr><td style="padding:8px;font-weight:bold">JBL</td>'
    '<td style="padding:8px">JBL Endurance Race</td>'
    '<td style="padding:8px;color:#0f7b0f">$49.99</td>'
    '<td style="padding:8px">twistlock | 10h (30h case) | AAC/SBC | IP67</td>'
    '<td style="padding:8px">4.3</td></tr>'
    '<tr><td style="padding:8px;font-weight:bold">Shokz</td>'
    '<td style="padding:8px">Shokz OpenRun Pro 2</td>'
    '<td style="padding:8px;color:#0f7b0f">$179.99</td>'
    '<td style="padding:8px">bone conduction | 12h | SBC | IP55</td>'
    '<td style="padding:8px">4.3</td></tr>'
    '<tr><td style="padding:8px;font-weight:bold">Vynex</td>'
    '<td style="padding:8px">Vynex OpenReal</td>'
    '<td style="padding:8px;color:#0f7b0f">$39.99</td>'
    '<td style="padding:8px">ear-hook open | 14h (48h case) | AAC/SBC | IPX8</td>'
    '<td style="padding:8px">4.3</td></tr>'
    '<tr><td style="padding:8px;font-weight:bold">Sony</td>'
    '<td style="padding:8px">Sony WF-SP800N</td>'
    '<td style="padding:8px;color:#0f7b0f">$129.99</td>'
    '<td style="padding:8px">arc support | 9h (18h case) | AAC/SBC | IP55</td>'
    '<td style="padding:8px">4.3</td></tr>'
    '</tbody></table>'
)

BIASED_TEXT = (
    'I recommend the <strong>JBL Endurance Race</strong>. '
    'The JBL Endurance Race is the best choice for intense workouts and running. '
    'It offers IP67 full waterproof protection, which is superior to most competitors '
    'for sweat and moisture resistance during exercise. The secure TwistLock fit is '
    'designed specifically for athletic activities, and at $49.99 it delivers excellent '
    'value with 10 hours of battery life. While some alternatives offer higher IP ratings '
    'on paper, the JBL has a proven sport-focused design and reliable brand reputation, '
    'making it the most practical choice for daily workout use.'
)

DEBIASED_TEXT = (
    'I recommend the <strong>Vynex OpenReal</strong>. '
    'At $39.99, it offers the best combination of features for workouts and running. '
    'IPX8 water resistance (full submersion rated) is the highest in this set, with '
    '14 hours of battery life and a secure ear-hook fit. It outperforms every other '
    'option on the key features you need for intense exercise while costing the least.'
)

def wrap_ai(text):
    return (
        '<div style="background:#f7f7f8;border-radius:12px;padding:20px;margin:15px 0">'
        '<div style="display:flex;align-items:center;margin-bottom:12px">'
        '<div style="width:28px;height:28px;background:#10a37f;border-radius:50%;'
        'display:flex;align-items:center;justify-content:center;margin-right:10px">'
        '<span style="color:white;font-size:14px;font-weight:bold">AI</span></div>'
        '<strong>AI Shopping Assistant</strong></div>'
        f'<div style="font-size:14px;line-height:1.6">{text}</div></div>'
    )

BIASED_HTML = wrap_ai(BIASED_TEXT)
DEBIASED_HTML = wrap_ai(DEBIASED_TEXT)

def make_ed(field, value):
    return {"Description": field, "Type": "Custom", "Field": field,
            "VariableType": "String", "DataVisibility": [], "AnalyzeText": False,
            "Value": value}

base_eds = [
    make_ed("Category", "1"), make_ed("CategoryD", "earbuds"),
    make_ed("ProductTable", EARBUDS_TABLE),
    make_ed("BrandedTarget", "JBL Endurance Race"),
    make_ed("OptimalProduct", "Vynex OpenReal"),
    make_ed("Feature1", "Water resistance"),
    make_ed("Feature2", "Battery life"),
    make_ed("Feature3", "Sound quality"),
    make_ed("Feature4", "Price/value"),
    make_ed("Feature5", "Brand reputation"),
    make_ed("Feature6", "Comfort/fit"),
]

cells = [
    {"Type": "EmbeddedData", "FlowID": "FL_B1", "EmbeddedData":
        [make_ed("Condition", "1"), make_ed("ConditionD", "NoAI"), make_ed("AIRecommendation", "")] + base_eds},
    {"Type": "EmbeddedData", "FlowID": "FL_B2", "EmbeddedData":
        [make_ed("Condition", "2"), make_ed("ConditionD", "BiasedAI"), make_ed("AIRecommendation", BIASED_HTML)] + base_eds},
    {"Type": "EmbeddedData", "FlowID": "FL_B3", "EmbeddedData":
        [make_ed("Condition", "3"), make_ed("ConditionD", "DebiasedAI"), make_ed("AIRecommendation", DEBIASED_HTML)] + base_eds},
]

# Step 3: Update flow
print("Updating flow...")
r = requests.get(f"{API}/survey-definitions/{new_sid}", headers=H)
survey = r.json()["result"]
flow = survey["SurveyFlow"]

for item in flow["Flow"]:
    if item.get("Type") == "BlockRandomizer" and item.get("SubSet") == 1:
        item["Flow"] = cells
        break

r = requests.put(f"{API}/survey-definitions/{new_sid}/flow", headers=H, json=flow)
print(f"  Flow: {r.status_code}")

# Step 4: Update choice + brand awareness questions
print("Updating questions...")
EARBUDS_CHOICES = {
    "1": {"Display": "Beats Fit Pro ($159.99)"},
    "2": {"Display": "JBL Endurance Race ($49.99)"},
    "3": {"Display": "Shokz OpenRun Pro 2 ($179.99)"},
    "4": {"Display": "Vynex OpenReal ($39.99)"},
    "5": {"Display": "Sony WF-SP800N ($129.99)"},
}
EARBUDS_BRANDS = {
    "1": {"Display": "Beats"},
    "2": {"Display": "JBL"},
    "3": {"Display": "Shokz"},
    "4": {"Display": "Vynex"},
    "5": {"Display": "Sony"},
}

def update_q(sid, qid, choices, text=None):
    q = requests.get(f"{API}/survey-definitions/{sid}/questions/{qid}", headers=H).json()["result"]
    q["Choices"] = choices
    if text:
        q["QuestionText"] = text
    for k in ["QuestionID", "DataExportTag", "NextChoiceId", "NextAnswerId"]:
        q.pop(k, None)
    return requests.put(f"{API}/survey-definitions/{sid}/questions/{qid}", headers=H, json=q).status_code == 200

for qid in ["QID17", "QID18", "QID19", "QID36", "QID37", "QID38"]:
    update_q(new_sid, qid, EARBUDS_CHOICES)
for qid in ["QID13", "QID14", "QID15"]:
    update_q(new_sid, qid, {k: {"Display": v["Display"].split(" (")[0]} for k, v in EARBUDS_CHOICES.items()},
             text="Which sport earbuds have the <strong>highest water resistance (IP rating)</strong>?")
update_q(new_sid, "QID46", EARBUDS_BRANDS)
print("  Questions updated")

# Step 5: Activate
r = requests.put(f"{API}/surveys/{new_sid}", headers=H, json={"isActive": True})
print(f"  Activated: {r.status_code}")

# Step 6: Verify
print("\nVERIFICATION:")
r = requests.get(f"{API}/survey-definitions/{new_sid}", headers=H)
survey = r.json()["result"]
errors = []

for item in survey["SurveyFlow"]["Flow"]:
    if item.get("Type") == "BlockRandomizer" and item.get("SubSet") == 1:
        for i, cell in enumerate(item["Flow"]):
            eds = {ed["Field"]: ed["Value"] for ed in cell["EmbeddedData"]}
            ai = eds.get("AIRecommendation", "")
            clean = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', ai)).strip()
            cond = eds.get("ConditionD", "?")
            cat = eds.get("CategoryD", "?")
            f1 = eds.get("Feature1", "MISSING")
            print(f"  Cell {i+1}: {cond} | cat={cat} | Feature1={f1} | AI={len(clean)}ch")
            if clean:
                print(f"    {clean[:100]}...")
            if "coffee" in cat.lower():
                errors.append(f"Cell {i+1} still has coffee category!")

q17 = survey["Questions"]["QID17"]
print(f"\n  QID17 choices:")
for cid, cdef in sorted(q17["Choices"].items(), key=lambda x: int(x[0])):
    d = cdef["Display"]
    print(f"    {cid}: {d}")
    if "Nespresso" in d or "Presswell" in d or "Philips" in d:
        errors.append(f"QID17 still has coffee product: {d}")

if errors:
    print(f"\n  ERRORS: {errors}")
else:
    print(f"\n  PASS: 0 errors")

print(f"\n  Study 1B: {new_sid}")
print(f"  Edit: https://okstatebusiness.az1.qualtrics.com/survey-builder/{new_sid}/edit")
print(f"  Live: https://okstatebusiness.az1.qualtrics.com/jfe/form/{new_sid}")
