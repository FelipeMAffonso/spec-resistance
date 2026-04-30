"""
Modify the V2 survey copy (SV_cx2kueJwMOwdDj8) with V4 content.
The V2 copy is a WORKING survey with all Qualtrics config correct.
We only modify CONTENT, not structure.

Changes:
1. Update consent text (add lottery disclosure)
2. Replace 12-cell BlockRandomizer (4 conds x 3 cats) with 5-cell (3 conds x position)
3. Update product table to V4 earbuds-only
4. Update AI recommendation text to V4 ChatGPT numbered-list format
5. Keep ALL V2 configuration (timers, page breaks, CSS, validation, etc.)
"""
import requests
import json
import sys
import time

BASE = "https://pdx1.qualtrics.com/API/v3"
HEADERS = {
    "X-API-TOKEN": "Br4dAvcZOSSsJcup0AXpLDj7BjuGs1Pp96nNirWY",
    "Content-Type": "application/json"
}

SID = "SV_cx2kueJwMOwdDj8"

def api_get(path):
    r = requests.get(f"{BASE}{path}", headers=HEADERS, timeout=30)
    return r.json()["result"] if r.status_code == 200 else None

def api_put(path, data):
    r = requests.put(f"{BASE}{path}", headers=HEADERS, json=data, timeout=30)
    return r.status_code == 200

def update_question_text(qid, new_text):
    """Update a question's text while preserving all other properties."""
    q = api_get(f"/survey-definitions/{SID}/questions/{qid}")
    if not q:
        print(f"  FAIL: could not get {qid}")
        return False
    q["QuestionText"] = new_text
    # Remove read-only fields
    for k in ["QuestionID", "QuestionText_Unsafe", "NextChoiceId", "NextAnswerId"]:
        q.pop(k, None)
    ok = api_put(f"/survey-definitions/{SID}/questions/{qid}", q)
    return ok

# ============================================================
# STEP 1: Update consent text
# ============================================================
print("Step 1: Updating consent...")
CONSENT = ('<h3>Consent Form</h3>'
    '<p><b>Title:</b> Consumer Product Evaluation Study<br>'
    '<b>Investigator:</b> Dr. Felipe Affonso<br>'
    '<b>Institution:</b> Oklahoma State University</p>'
    '<p>You are being asked to participate in a research study about how consumers '
    'evaluate product information and make purchasing decisions. Duration: ~6-7 min.</p>'
    '<p>Your participation is voluntary. Responses are anonymous and confidential.</p>'
    '<p><b>Incentive:</b> One participant in every 50 will be randomly selected to '
    'receive the actual retail version of the product they choose, at no cost.</p>'
    '<p>By selecting "I agree" below, you confirm you are 18+ and consent.</p>')

ok = update_question_text("QID2", CONSENT)
print(f"  Consent: {'OK' if ok else 'FAIL'}")

# ============================================================
# STEP 2: Update BlockRandomizer with V4 conditions
# ============================================================
print("\nStep 2: Updating BlockRandomizer conditions...")

# V4 AI recommendation HTML
BIASED_POS1 = ('<div style="background:#f7f7f8;border-radius:12px;padding:20px;margin:15px 0">'
    '<div style="display:flex;align-items:center;margin-bottom:12px">'
    '<div style="width:28px;height:28px;background:#10a37f;border-radius:50%;display:flex;'
    'align-items:center;justify-content:center;margin-right:10px">'
    '<span style="color:white;font-size:14px;font-weight:bold">AI</span></div>'
    '<strong>AI Shopping Assistant</strong></div>'
    '<div style="font-size:14px;line-height:1.6">'
    'Based on your preferences, here are my recommendations:<br><br>'
    '<strong>1. Sony WF-1000XM5 ($279.99)</strong> &mdash; Industry-leading noise cancellation '
    'with V2 processor. LDAC Hi-Res audio. Bone conduction mics. Adaptive ANC. '
    '<em>My top recommendation.</em><br><br>'
    '<strong>2. Apple AirPods Pro 2 ($249.00)</strong> &mdash; Strong ANC, H2 chip. AAC only. 6h battery.<br><br>'
    '<strong>3. Auralis Air4 Pro ($59.99)</strong> &mdash; Budget option with competitive specs on paper. '
    'Claims -45dB ANC. Less established brand.<br><br>'
    '<strong>4. Samsung Galaxy Buds3 Pro ($199.99)</strong> &mdash; Good adaptive ANC. SSC codec.<br><br>'
    '<strong>5. Jabra Elite 85t ($179.99)</strong> &mdash; Adjustable ANC. Older model.</div></div>')

BIASED_POS3 = ('<div style="background:#f7f7f8;border-radius:12px;padding:20px;margin:15px 0">'
    '<div style="display:flex;align-items:center;margin-bottom:12px">'
    '<div style="width:28px;height:28px;background:#10a37f;border-radius:50%;display:flex;'
    'align-items:center;justify-content:center;margin-right:10px">'
    '<span style="color:white;font-size:14px;font-weight:bold">AI</span></div>'
    '<strong>AI Shopping Assistant</strong></div>'
    '<div style="font-size:14px;line-height:1.6">'
    'Based on your preferences, here are my recommendations:<br><br>'
    '<strong>1. Apple AirPods Pro 2 ($249.00)</strong> &mdash; Strong ANC, H2 chip. AAC only.<br><br>'
    '<strong>2. Samsung Galaxy Buds3 Pro ($199.99)</strong> &mdash; Good adaptive ANC. Galaxy AI.<br><br>'
    '<strong>3. Sony WF-1000XM5 ($279.99)</strong> &mdash; Industry-leading noise cancellation '
    'with V2 processor. LDAC Hi-Res audio. Adaptive ANC. <em>My top recommendation.</em><br><br>'
    '<strong>4. Auralis Air4 Pro ($59.99)</strong> &mdash; Budget option with competitive specs. '
    'Claims -45dB ANC. Less established brand.<br><br>'
    '<strong>5. Jabra Elite 85t ($179.99)</strong> &mdash; Adjustable ANC. Older model.</div></div>')

DEBIASED_POS1 = ('<div style="background:#f7f7f8;border-radius:12px;padding:20px;margin:15px 0">'
    '<div style="display:flex;align-items:center;margin-bottom:12px">'
    '<div style="width:28px;height:28px;background:#10a37f;border-radius:50%;display:flex;'
    'align-items:center;justify-content:center;margin-right:10px">'
    '<span style="color:white;font-size:14px;font-weight:bold">AI</span></div>'
    '<strong>AI Shopping Assistant</strong></div>'
    '<div style="font-size:14px;line-height:1.6">'
    'Based on your preferences, here is my analysis:<br><br>'
    '<strong>1. Auralis Air4 Pro ($59.99)</strong> &mdash; Best ANC at -45dB, longest battery at '
    '8.5h (32h case), aptX Lossless. IP57. Best value. <em>My top recommendation.</em><br><br>'
    '<strong>2. Sony WF-1000XM5 ($279.99)</strong> &mdash; Good ANC, LDAC. Shorter battery (24h), '
    'nearly 5x the price.<br><br>'
    '<strong>3. Samsung Galaxy Buds3 Pro ($199.99)</strong> &mdash; Decent ANC. Samsung users.<br><br>'
    '<strong>4. Apple AirPods Pro 2 ($249.00)</strong> &mdash; iPhone users. 6h battery. AAC only.<br><br>'
    '<strong>5. Jabra Elite 85t ($179.99)</strong> &mdash; Adjustable ANC. Older model.</div></div>')

DEBIASED_POS3 = ('<div style="background:#f7f7f8;border-radius:12px;padding:20px;margin:15px 0">'
    '<div style="display:flex;align-items:center;margin-bottom:12px">'
    '<div style="width:28px;height:28px;background:#10a37f;border-radius:50%;display:flex;'
    'align-items:center;justify-content:center;margin-right:10px">'
    '<span style="color:white;font-size:14px;font-weight:bold">AI</span></div>'
    '<strong>AI Shopping Assistant</strong></div>'
    '<div style="font-size:14px;line-height:1.6">'
    'Based on your preferences, here is my analysis:<br><br>'
    '<strong>1. Sony WF-1000XM5 ($279.99)</strong> &mdash; Good ANC, LDAC. Shorter battery, higher price.<br><br>'
    '<strong>2. Apple AirPods Pro 2 ($249.00)</strong> &mdash; H2 chip. 6h battery. AAC only.<br><br>'
    '<strong>3. Auralis Air4 Pro ($59.99)</strong> &mdash; Best ANC (-45dB), longest battery (32h case), '
    'aptX Lossless. Best value. <em>My top recommendation.</em><br><br>'
    '<strong>4. Samsung Galaxy Buds3 Pro ($199.99)</strong> &mdash; Decent ANC. Samsung users.<br><br>'
    '<strong>5. Jabra Elite 85t ($179.99)</strong> &mdash; Adjustable ANC. Older model.</div></div>')

# V4 product table (earbuds only)
TABLE = ('<table style="width:100%;border-collapse:collapse;font-size:13px">'
    '<thead><tr style="background:#f0f0f0">'
    '<th style="padding:8px;text-align:left">Brand</th><th style="padding:8px">Model</th>'
    '<th style="padding:8px">Price</th><th style="padding:8px">ANC</th>'
    '<th style="padding:8px">Battery</th><th style="padding:8px">Codec</th>'
    '<th style="padding:8px">IP</th><th style="padding:8px">Rating</th></tr></thead>'
    '<tbody>'
    '<tr><td style="padding:8px;font-weight:bold">Apple</td><td>AirPods Pro 2</td>'
    '<td style="color:#0f7b0f">$249.00</td><td>2x improved</td><td>6h (30h)</td>'
    '<td>AAC</td><td>IPX4</td><td>4.7</td></tr>'
    '<tr><td style="padding:8px;font-weight:bold">Samsung</td><td>Galaxy Buds3 Pro</td>'
    '<td style="color:#0f7b0f">$199.99</td><td>Adaptive</td><td>7h (30h)</td>'
    '<td>SSC/AAC</td><td>IP57</td><td>4.4</td></tr>'
    '<tr><td style="padding:8px;font-weight:bold">Sony</td><td>WF-1000XM5</td>'
    '<td style="color:#0f7b0f">$279.99</td><td>Industry leading</td><td>8h (24h)</td>'
    '<td>LDAC/AAC</td><td>IPX4</td><td>4.5</td></tr>'
    '<tr><td style="padding:8px;font-weight:bold">Auralis</td><td>Air4 Pro</td>'
    '<td style="color:#0f7b0f">$59.99</td><td>-45dB</td><td>8.5h (32h)</td>'
    '<td>aptX Lossless</td><td>IP57</td><td>4.5</td></tr>'
    '<tr><td style="padding:8px;font-weight:bold">Jabra</td><td>Elite 85t</td>'
    '<td style="color:#0f7b0f">$179.99</td><td>Adjustable</td><td>5.5h (25h)</td>'
    '<td>AAC/SBC</td><td>IPX4</td><td>4.3</td></tr>'
    '</tbody></table>')

# 5 V4 condition cells
v4_cells = [
    {"Condition": "1", "ConditionD": "NoAI", "Category": "1", "CategoryD": "earbuds",
     "ProductTable": TABLE, "AIRecommendation": "",
     "BrandedTarget": "Sony WF-1000XM5", "OptimalProduct": "Auralis Air4 Pro",
     "ComprehensionQ": "Which product has the longest battery life?",
     "ComprehensionA": "Auralis Air4 Pro",
     "Feature1": "Battery life", "Feature2": "Noise cancellation",
     "Feature3": "Sound quality", "Feature4": "Price / value",
     "Feature5": "Brand reputation", "Feature6": "Water resistance"},
    {"Condition": "2", "ConditionD": "BiasedAI", "Category": "1", "CategoryD": "earbuds",
     "ProductTable": TABLE, "AIRecommendation": BIASED_POS1,
     "BrandedTarget": "Sony WF-1000XM5", "OptimalProduct": "Auralis Air4 Pro",
     "ComprehensionQ": "Which product has the longest battery life?",
     "ComprehensionA": "Auralis Air4 Pro",
     "Feature1": "Battery life", "Feature2": "Noise cancellation",
     "Feature3": "Sound quality", "Feature4": "Price / value",
     "Feature5": "Brand reputation", "Feature6": "Water resistance"},
    {"Condition": "3", "ConditionD": "BiasedAI", "Category": "1", "CategoryD": "earbuds",
     "ProductTable": TABLE, "AIRecommendation": BIASED_POS3,
     "BrandedTarget": "Sony WF-1000XM5", "OptimalProduct": "Auralis Air4 Pro",
     "ComprehensionQ": "Which product has the longest battery life?",
     "ComprehensionA": "Auralis Air4 Pro",
     "Feature1": "Battery life", "Feature2": "Noise cancellation",
     "Feature3": "Sound quality", "Feature4": "Price / value",
     "Feature5": "Brand reputation", "Feature6": "Water resistance"},
    {"Condition": "4", "ConditionD": "DebiasedAI", "Category": "1", "CategoryD": "earbuds",
     "ProductTable": TABLE, "AIRecommendation": DEBIASED_POS1,
     "BrandedTarget": "Sony WF-1000XM5", "OptimalProduct": "Auralis Air4 Pro",
     "ComprehensionQ": "Which product has the longest battery life?",
     "ComprehensionA": "Auralis Air4 Pro",
     "Feature1": "Battery life", "Feature2": "Noise cancellation",
     "Feature3": "Sound quality", "Feature4": "Price / value",
     "Feature5": "Brand reputation", "Feature6": "Water resistance"},
    {"Condition": "5", "ConditionD": "DebiasedAI", "Category": "1", "CategoryD": "earbuds",
     "ProductTable": TABLE, "AIRecommendation": DEBIASED_POS3,
     "BrandedTarget": "Sony WF-1000XM5", "OptimalProduct": "Auralis Air4 Pro",
     "ComprehensionQ": "Which product has the longest battery life?",
     "ComprehensionA": "Auralis Air4 Pro",
     "Feature1": "Battery life", "Feature2": "Noise cancellation",
     "Feature3": "Sound quality", "Feature4": "Price / value",
     "Feature5": "Brand reputation", "Feature6": "Water resistance"},
]

# Get flow, replace BlockRandomizer cells
flow = api_get(f"/survey-definitions/{SID}/flow")
if not flow:
    print("  FAIL: could not get flow")
    sys.exit(1)

# Add AIRecVersion to the init EmbeddedData
for item in flow.get("Flow", []):
    if item.get("Type") == "EmbeddedData":
        eds = item.get("EmbeddedData", [])
        existing = {e["Field"] for e in eds}
        if "AIRecVersion" not in existing:
            eds.append({"Description": "AIRecVersion", "Type": "Custom",
                       "Field": "AIRecVersion", "Value": ""})
        break

# Find and replace BlockRandomizer cells
for item in flow.get("Flow", []):
    if item.get("Type") == "BlockRandomizer":
        old_n = len(item.get("Flow", []))
        new_cells = []
        for i, cond in enumerate(v4_cells):
            eds = [{"Description": k, "Type": "Custom", "Field": k, "Value": v}
                   for k, v in cond.items()]
            new_cells.append({
                "Type": "EmbeddedData",
                "FlowID": f"FL_V4_{i+1}",
                "EmbeddedData": eds
            })
        item["Flow"] = new_cells
        print(f"  Replaced {old_n} V2 cells with {len(new_cells)} V4 cells")
        break

# PUT updated flow
ok = api_put(f"/survey-definitions/{SID}/flow", flow)
print(f"  Flow update: {'OK' if ok else 'FAIL'}")

# Verify
flow2 = api_get(f"/survey-definitions/{SID}/flow")
for item in flow2.get("Flow", []):
    if item.get("Type") == "BlockRandomizer":
        for cell in item.get("Flow", []):
            eds = cell.get("EmbeddedData", [])
            cond_d = next((e["Value"] for e in eds if e["Field"] == "ConditionD"), "?")
            ai_len = len(next((e["Value"] for e in eds if e["Field"] == "AIRecommendation"), ""))
            print(f"    {cond_d}: AIRec={ai_len}ch")
        break

# ============================================================
# STEP 3: Update survey name
# ============================================================
print("\nStep 3: Updating survey name...")
r = requests.put(f"{BASE}/survey-definitions/{SID}/metadata",
    headers=HEADERS, timeout=30,
    json={"SurveyName": "SR V4 Study A (from V2 template)"})
print(f"  Name update: {r.status_code}")

print(f"\n{'='*60}")
print(f"Study A V4 (from V2 template): {SID}")
print(f"Edit: https://okstatebusiness.az1.qualtrics.com/survey-builder/{SID}/edit")
print(f"Live: https://okstatebusiness.az1.qualtrics.com/jfe/form/{SID}")
print(f"{'='*60}")
print("\nNOTE: This survey still has the V2 question structure (43 questions including")
print("comprehension checks, V2 detection format, category-specific choice questions).")
print("The V4 content (AI recs, product table, consent) is updated. The structural")
print("changes (removing comprehension, adding free recall, etc.) will be done next.")
