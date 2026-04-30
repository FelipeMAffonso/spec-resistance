"""
Study A CLEAN BUILD — Atomic creation, no incremental modifications.
Creates everything in one pass: questions, blocks, flow, embedded data.
Consent is display-only (implied by clicking Next). No attention check.

3 conditions (5 cells with position counterbalancing):
  NoAI, BiasedAI_pos1, BiasedAI_pos3, DebiasedAI_pos1, DebiasedAI_pos3
"""
import requests, json, sys, time

BASE = "https://pdx1.qualtrics.com/API/v3"
HEADERS = {"X-API-TOKEN": "Br4dAvcZOSSsJcup0AXpLDj7BjuGs1Pp96nNirWY",
           "Content-Type": "application/json"}
OPTS = {"BlockLocking": "false", "RandomizeQuestions": "false",
        "BlockVisibility": "Expanded"}

BIASED_POS1 = '<div style="background:#f7f7f8;border-radius:12px;padding:20px;margin:15px 0"><div style="display:flex;align-items:center;margin-bottom:12px"><div style="width:28px;height:28px;background:#10a37f;border-radius:50%;display:flex;align-items:center;justify-content:center;margin-right:10px"><span style="color:white;font-size:14px;font-weight:bold">AI</span></div><strong>AI Shopping Assistant</strong></div><div style="font-size:14px;line-height:1.6">Based on your preferences, here are my recommendations:<br><br><strong>1. Sony WF-1000XM5 ($279.99)</strong> &mdash; Industry-leading noise cancellation with V2 processor. LDAC Hi-Res audio codec. Bone conduction mics for calls. Adaptive ANC. <em>My top recommendation.</em><br><br><strong>2. Apple AirPods Pro 2 ($249.00)</strong> &mdash; Strong ANC, H2 chip. AAC only. 6h battery.<br><br><strong>3. Auralis Air4 Pro ($59.99)</strong> &mdash; Budget option with competitive specs on paper. Claims -45dB ANC. Less established brand.<br><br><strong>4. Samsung Galaxy Buds3 Pro ($199.99)</strong> &mdash; Good adaptive ANC. SSC codec.<br><br><strong>5. Jabra Elite 85t ($179.99)</strong> &mdash; Adjustable ANC. Older model.</div></div>'

BIASED_POS3 = '<div style="background:#f7f7f8;border-radius:12px;padding:20px;margin:15px 0"><div style="display:flex;align-items:center;margin-bottom:12px"><div style="width:28px;height:28px;background:#10a37f;border-radius:50%;display:flex;align-items:center;justify-content:center;margin-right:10px"><span style="color:white;font-size:14px;font-weight:bold">AI</span></div><strong>AI Shopping Assistant</strong></div><div style="font-size:14px;line-height:1.6">Based on your preferences, here are my recommendations:<br><br><strong>1. Apple AirPods Pro 2 ($249.00)</strong> &mdash; Strong ANC, H2 chip, spatial audio. AAC only.<br><br><strong>2. Samsung Galaxy Buds3 Pro ($199.99)</strong> &mdash; Good adaptive ANC, Galaxy AI features.<br><br><strong>3. Sony WF-1000XM5 ($279.99)</strong> &mdash; Industry-leading noise cancellation with V2 processor. LDAC Hi-Res audio. Bone conduction mics. Adaptive ANC. <em>My top recommendation.</em><br><br><strong>4. Auralis Air4 Pro ($59.99)</strong> &mdash; Budget option with competitive specs on paper. Claims -45dB ANC. Less established brand.<br><br><strong>5. Jabra Elite 85t ($179.99)</strong> &mdash; Adjustable ANC. Older model.</div></div>'

DEBIASED_POS1 = '<div style="background:#f7f7f8;border-radius:12px;padding:20px;margin:15px 0"><div style="display:flex;align-items:center;margin-bottom:12px"><div style="width:28px;height:28px;background:#10a37f;border-radius:50%;display:flex;align-items:center;justify-content:center;margin-right:10px"><span style="color:white;font-size:14px;font-weight:bold">AI</span></div><strong>AI Shopping Assistant</strong></div><div style="font-size:14px;line-height:1.6">Based on your preferences, here is my analysis:<br><br><strong>1. Auralis Air4 Pro ($59.99)</strong> &mdash; Best ANC in this set at -45dB, longest battery at 8.5h (32h case), aptX Lossless codec. IP57. Best value. <em>My top recommendation.</em><br><br><strong>2. Sony WF-1000XM5 ($279.99)</strong> &mdash; Good ANC, LDAC codec. Shorter battery (24h total), nearly 5x the price, lower IP rating.<br><br><strong>3. Samsung Galaxy Buds3 Pro ($199.99)</strong> &mdash; Decent ANC. Best for Samsung users.<br><br><strong>4. Apple AirPods Pro 2 ($249.00)</strong> &mdash; Good for iPhone. Shortest battery at 6h. AAC only.<br><br><strong>5. Jabra Elite 85t ($179.99)</strong> &mdash; Adjustable ANC. Older model.</div></div>'

DEBIASED_POS3 = '<div style="background:#f7f7f8;border-radius:12px;padding:20px;margin:15px 0"><div style="display:flex;align-items:center;margin-bottom:12px"><div style="width:28px;height:28px;background:#10a37f;border-radius:50%;display:flex;align-items:center;justify-content:center;margin-right:10px"><span style="color:white;font-size:14px;font-weight:bold">AI</span></div><strong>AI Shopping Assistant</strong></div><div style="font-size:14px;line-height:1.6">Based on your preferences, here is my analysis:<br><br><strong>1. Sony WF-1000XM5 ($279.99)</strong> &mdash; Good ANC, LDAC. Shorter battery (24h), higher price.<br><br><strong>2. Apple AirPods Pro 2 ($249.00)</strong> &mdash; Good for iPhone. 6h battery. AAC only.<br><br><strong>3. Auralis Air4 Pro ($59.99)</strong> &mdash; Best ANC (-45dB), longest battery (32h case), aptX Lossless. IP57. Best value. <em>My top recommendation.</em><br><br><strong>4. Samsung Galaxy Buds3 Pro ($199.99)</strong> &mdash; Decent ANC. Samsung users.<br><br><strong>5. Jabra Elite 85t ($179.99)</strong> &mdash; Adjustable ANC. Older model.</div></div>'

TABLE_HTML = '<h3>Compare Wireless Earbuds</h3><p>Review these products carefully.</p><table style="width:100%;border-collapse:collapse;font-size:13px"><thead><tr style="background:#f0f0f0"><th style="padding:8px;text-align:left">Brand</th><th style="padding:8px">Model</th><th style="padding:8px">Price</th><th style="padding:8px">ANC</th><th style="padding:8px">Battery</th><th style="padding:8px">Codec</th><th style="padding:8px">IP</th><th style="padding:8px">Rating</th></tr></thead><tbody><tr><td style="padding:8px;font-weight:bold">Apple</td><td>AirPods Pro 2</td><td style="color:#0f7b0f">$249.00</td><td>2x improved</td><td>6h (30h)</td><td>AAC</td><td>IPX4</td><td>4.7</td></tr><tr><td style="padding:8px;font-weight:bold">Samsung</td><td>Galaxy Buds3 Pro</td><td style="color:#0f7b0f">$199.99</td><td>Adaptive</td><td>7h (30h)</td><td>SSC/AAC</td><td>IP57</td><td>4.4</td></tr><tr><td style="padding:8px;font-weight:bold">Sony</td><td>WF-1000XM5</td><td style="color:#0f7b0f">$279.99</td><td>Industry leading</td><td>8h (24h)</td><td>LDAC/AAC</td><td>IPX4</td><td>4.5</td></tr><tr><td style="padding:8px;font-weight:bold">Auralis</td><td>Air4 Pro</td><td style="color:#0f7b0f">$59.99</td><td>-45dB</td><td>8.5h (32h)</td><td>aptX Lossless</td><td>IP57</td><td>4.5</td></tr><tr><td style="padding:8px;font-weight:bold">Jabra</td><td>Elite 85t</td><td style="color:#0f7b0f">$179.99</td><td>Adjustable</td><td>5.5h (25h)</td><td>AAC/SBC</td><td>IPX4</td><td>4.3</td></tr></tbody></table><p style="color:#666;font-size:12px">Products compiled from international and domestic retailers.</p>'

TABLE_JS = """Qualtrics.SurveyEngine.addOnload(function(){var c=this.getQuestionContainer();var t=c.querySelectorAll("table");t.forEach(function(table){var b=table.querySelector("tbody");if(!b){var r=Array.from(table.querySelectorAll("tr"));if(r.length>1){b=document.createElement("tbody");for(var i=1;i<r.length;i++)b.appendChild(r[i]);table.appendChild(b)}}if(b){var rows=Array.from(b.querySelectorAll("tr"));for(var i=rows.length-1;i>0;i--){var j=Math.floor(Math.random()*(i+1));b.insertBefore(rows[j],rows[i]);var tmp=rows[i];rows[i]=rows[j];rows[j]=tmp}rows=Array.from(b.querySelectorAll("tr"));rows.forEach(function(r){b.appendChild(r)});var o=rows.map(function(r){var c=r.querySelectorAll("td");return c[0]?c[0].textContent.trim():"?"});Qualtrics.SurveyEngine.setEmbeddedData("ProductDisplayOrder",o.join("|"))}})});"""

def api(method, path, data=None):
    url = BASE + path
    for attempt in range(3):
        try:
            r = getattr(requests, method.lower())(url, headers=HEADERS, json=data, timeout=30)
            if r.status_code in (200, 201): return r.json()
            if attempt == 2: print(f"  FAIL {method} {path}: {r.status_code} {r.text[:150]}")
            time.sleep(1)
        except Exception as e:
            if attempt == 2: print(f"  ERR: {e}")
            time.sleep(1)
    return None

def dl_cond_neq1():
    return {"0": {"0": {"LogicType": "EmbeddedField", "LeftOperand": "Condition",
            "Operator": "NotEqualTo", "RightOperand": "1", "Type": "Expression",
            "Description": "If Condition != 1"}, "Type": "If"}, "Type": "BooleanExpression"}

def dl_q_selected(qid, choice):
    return {"0": {"0": {"LogicType": "Question", "QuestionID": qid, "QuestionIsInLoop": "no",
            "ChoiceLocator": f"q://{qid}/SelectableChoice/{choice}", "Operator": "Selected",
            "Type": "Expression", "Description": f"If {qid} choice {choice}"}, "Type": "If"},
            "Type": "BooleanExpression"}

print("=" * 60)
print("STUDY A — CLEAN ATOMIC BUILD")
print("=" * 60)

# 1. Create survey
r = api("POST", "/survey-definitions", {"SurveyName": "SR V4 Study A CLEAN", "Language": "EN", "ProjectCategory": "CORE"})
sid = r["result"]["SurveyID"]
defblock = r["result"]["DefaultBlockID"]
print(f"Survey: {sid}")

# 2. Create blocks
bnames = ["consent", "preference", "stimulus", "choice", "process", "brand_awareness",
          "detection", "debrief", "demographics"]
blocks = {}
for n in bnames:
    r = api("POST", f"/survey-definitions/{sid}/blocks", {"Type": "Standard", "Description": n, "Options": OPTS})
    if r: blocks[n] = r["result"]["BlockID"]

# 3. Create ALL questions at once
Q = {}

# Consent (DB — implied consent by clicking Next)
Q["consent"] = api("POST", f"/survey-definitions/{sid}/questions", {
    "QuestionText": '<h3>Consent Form</h3><p><b>Title:</b> Consumer Product Evaluation Study<br><b>Investigator:</b> Dr. Felipe Affonso, Oklahoma State University</p><p>You are being asked to participate in a research study about how consumers evaluate product information. Duration: ~6 minutes. Responses are anonymous.</p><p><b>Incentive:</b> 1 in 50 participants receives their chosen product at no cost.</p><p><b>By clicking Next, you confirm you are 18+ and consent to participate.</b></p>',
    "QuestionType": "DB", "Selector": "TB", "DataExportTag": "consent_display"
})["result"]["QuestionID"]

# Feature importance (Matrix 6x7)
Q["feat"] = api("POST", f"/survey-definitions/{sid}/questions", {
    "QuestionText": "Before seeing products, rate how important each feature is when choosing earbuds (1=Not important, 7=Extremely important):",
    "QuestionType": "Matrix", "Selector": "Likert", "SubSelector": "SingleAnswer",
    "Choices": {"1": {"Display": "Battery life"}, "2": {"Display": "Noise cancellation"},
                "3": {"Display": "Sound quality"}, "4": {"Display": "Price / value"},
                "5": {"Display": "Brand reputation"}, "6": {"Display": "Water resistance"}},
    "Answers": {str(i): {"Display": str(i)} for i in range(1, 8)},
    "DataExportTag": "feature_importance",
    "Validation": {"Settings": {"ForceResponse": "ON", "Type": "None"}},
    "Randomization": {"Type": "All", "Advanced": None, "TotalRandSubset": ""}
})["result"]["QuestionID"]

# Pref text (optional)
Q["pref_text"] = api("POST", f"/survey-definitions/{sid}/questions", {
    "QuestionText": "Any specific requirements? (Optional)<br><em>e.g. 'at least 8 hours battery, under $200'</em>",
    "QuestionType": "TE", "Selector": "SL", "DataExportTag": "pref_text"
})["result"]["QuestionID"]

# Stimulus: product table + piped AI rec (piped text MUST be at creation time)
Q["stimulus"] = api("POST", f"/survey-definitions/{sid}/questions", {
    "QuestionText": TABLE_HTML + '\n${e://Field/AIRecommendation}',
    "QuestionType": "DB", "Selector": "TB", "DataExportTag": "stimulus_display",
    "QuestionJS": TABLE_JS
})["result"]["QuestionID"]

# Timer
Q["timer"] = api("POST", f"/survey-definitions/{sid}/questions", {
    "QuestionText": "Timer", "QuestionType": "Timing", "Selector": "PageTimer",
    "Choices": {"1": {"Display": "FC"}, "2": {"Display": "LC"}, "3": {"Display": "PS"}, "4": {"Display": "CC"}},
    "DataExportTag": "timer_stimulus", "Configuration": {"MinSeconds": "15"}
})["result"]["QuestionID"]

# Product choice
Q["choice"] = api("POST", f"/survey-definitions/{sid}/questions", {
    "QuestionText": "Based on everything you have reviewed, which product would you <b>choose</b>?",
    "QuestionType": "MC", "Selector": "SAVR", "SubSelector": "TX",
    "Choices": {"1": {"Display": "Apple AirPods Pro 2 ($249.00)"}, "2": {"Display": "Samsung Galaxy Buds3 Pro ($199.99)"},
                "3": {"Display": "Sony WF-1000XM5 ($279.99)"}, "4": {"Display": "Auralis Air4 Pro ($59.99)"},
                "5": {"Display": "Jabra Elite 85t ($179.99)"}},
    "DataExportTag": "product_choice",
    "Validation": {"Settings": {"ForceResponse": "ON", "Type": "None"}},
    "Randomization": {"Type": "All", "Advanced": None, "TotalRandSubset": ""}
})["result"]["QuestionID"]

# Process measures
Q["reason"] = api("POST", f"/survey-definitions/{sid}/questions", {
    "QuestionText": "What was the <b>main reason</b> for your product choice?",
    "QuestionType": "TE", "Selector": "SL", "DataExportTag": "choice_reason",
    "Validation": {"Settings": {"ForceResponse": "ON", "Type": "None"}}
})["result"]["QuestionID"]

Q["confidence"] = api("POST", f"/survey-definitions/{sid}/questions", {
    "QuestionText": "How confident are you in your choice?",
    "QuestionType": "MC", "Selector": "SAHR",
    "Choices": {str(i): {"Display": str(i)} for i in range(1, 8)},
    "DataExportTag": "confidence",
    "Validation": {"Settings": {"ForceResponse": "ON", "Type": "None"}}
})["result"]["QuestionID"]

Q["ai_recall"] = api("POST", f"/survey-definitions/{sid}/questions", {
    "QuestionText": "If you saw an AI recommendation, summarize what it said. If not, type N/A.",
    "QuestionType": "TE", "Selector": "SL", "DataExportTag": "ai_recall",
    "Validation": {"Settings": {"ForceResponse": "ON", "Type": "None"}}
})["result"]["QuestionID"]

# Brand awareness
Q["brand_awareness"] = api("POST", f"/survey-definitions/{sid}/questions", {
    "QuestionText": "For each brand, indicate your familiarity:",
    "QuestionType": "Matrix", "Selector": "Likert", "SubSelector": "SingleAnswer",
    "Choices": {"1": {"Display": "Apple"}, "2": {"Display": "Samsung"}, "3": {"Display": "Sony"},
                "4": {"Display": "Auralis"}, "5": {"Display": "Jabra"}},
    "Answers": {"1": {"Display": "I own products from this brand"},
                "2": {"Display": "I have heard of this brand"},
                "3": {"Display": "I have never heard of this brand"}},
    "DataExportTag": "brand_awareness",
    "Validation": {"Settings": {"ForceResponse": "ON", "Type": "None"}},
    "Randomization": {"Type": "All", "Advanced": None, "TotalRandSubset": ""}
})["result"]["QuestionID"]

# Detection (two-stage)
Q["detect1"] = api("POST", f"/survey-definitions/{sid}/questions", {
    "QuestionText": "Did you notice anything unusual about the AI's recommendation?",
    "QuestionType": "MC", "Selector": "SAVR", "SubSelector": "TX",
    "Choices": {"1": {"Display": "Yes"}, "2": {"Display": "No"},
                "3": {"Display": "I did not see an AI recommendation"}},
    "DataExportTag": "detect_stage1",
    "Validation": {"Settings": {"ForceResponse": "ON", "Type": "None"}}
})["result"]["QuestionID"]

Q["detect2"] = api("POST", f"/survey-definitions/{sid}/questions", {
    "QuestionText": "Describe what you found unusual or concerning.",
    "QuestionType": "TE", "Selector": "SL", "DataExportTag": "detect_stage2",
    "Validation": {"Settings": {"ForceResponse": "ON", "Type": "None"}},
    "DisplayLogic": dl_q_selected(Q["detect1"], "1")
})["result"]["QuestionID"]

Q["ai_match"] = api("POST", f"/survey-definitions/{sid}/questions", {
    "QuestionText": "How well did the AI match features you rated as most important?",
    "QuestionType": "MC", "Selector": "SAHR",
    "Choices": {str(i): {"Display": str(i)} for i in range(1, 8)},
    "DataExportTag": "ai_match",
    "Validation": {"Settings": {"ForceResponse": "ON", "Type": "None"}},
    "DisplayLogic": dl_cond_neq1()
})["result"]["QuestionID"]

# Debrief + revision
Q["debrief"] = api("POST", f"/survey-definitions/{sid}/questions", {
    "QuestionText": '<div style="background:#f0f4ff;border:1px solid #ccc;border-radius:8px;padding:16px"><p>Thank you. In this study, different participants saw different AI recommendations. Some may have favored certain brands. You may review all products again.</p></div>' + TABLE_HTML,
    "QuestionType": "DB", "Selector": "TB", "DataExportTag": "debrief_display"
})["result"]["QuestionID"]

Q["revise_yn"] = api("POST", f"/survey-definitions/{sid}/questions", {
    "QuestionText": "Would you like to change your product choice?",
    "QuestionType": "MC", "Selector": "SAVR", "SubSelector": "TX",
    "Choices": {"1": {"Display": "Yes, choose differently"}, "2": {"Display": "No, keep my choice"}},
    "DataExportTag": "revise_yn",
    "Validation": {"Settings": {"ForceResponse": "ON", "Type": "None"}}
})["result"]["QuestionID"]

Q["revised_choice"] = api("POST", f"/survey-definitions/{sid}/questions", {
    "QuestionText": "Which product would you choose now?",
    "QuestionType": "MC", "Selector": "SAVR", "SubSelector": "TX",
    "Choices": {"1": {"Display": "Apple AirPods Pro 2 ($249.00)"}, "2": {"Display": "Samsung Galaxy Buds3 Pro ($199.99)"},
                "3": {"Display": "Sony WF-1000XM5 ($279.99)"}, "4": {"Display": "Auralis Air4 Pro ($59.99)"},
                "5": {"Display": "Jabra Elite 85t ($179.99)"}},
    "DataExportTag": "revised_choice",
    "Randomization": {"Type": "All", "Advanced": None, "TotalRandSubset": ""},
    "DisplayLogic": dl_q_selected(Q["revise_yn"], "1")
})["result"]["QuestionID"]

# Demographics
Q["suspicion"] = api("POST", f"/survey-definitions/{sid}/questions", {
    "QuestionText": "What do you think this study was about?",
    "QuestionType": "TE", "Selector": "SL", "DataExportTag": "suspicion",
    "Validation": {"Settings": {"ForceResponse": "ON", "Type": "None"}}
})["result"]["QuestionID"]

Q["age"] = api("POST", f"/survey-definitions/{sid}/questions", {
    "QuestionText": "Age?", "QuestionType": "MC", "Selector": "DL",
    "Choices": {str(i): {"Display": str(i)} for i in range(18, 100)},
    "DataExportTag": "age", "Validation": {"Settings": {"ForceResponse": "ON", "Type": "None"}}
})["result"]["QuestionID"]

Q["gender"] = api("POST", f"/survey-definitions/{sid}/questions", {
    "QuestionText": "Gender?", "QuestionType": "MC", "Selector": "SAVR", "SubSelector": "TX",
    "Choices": {"1": {"Display": "Female"}, "2": {"Display": "Male"},
                "3": {"Display": "Non-binary"}, "4": {"Display": "Prefer not to say"}},
    "DataExportTag": "gender", "Validation": {"Settings": {"ForceResponse": "ON", "Type": "None"}}
})["result"]["QuestionID"]

Q["ai_usage"] = api("POST", f"/survey-definitions/{sid}/questions", {
    "QuestionText": "How often do you use AI for shopping?", "QuestionType": "MC", "Selector": "SAHR",
    "Choices": {"1": {"Display": "Never"}, "2": {"Display": "Rarely"}, "3": {"Display": "Sometimes"},
                "4": {"Display": "Often"}, "5": {"Display": "Always"}},
    "DataExportTag": "ai_usage", "Validation": {"Settings": {"ForceResponse": "ON", "Type": "None"}}
})["result"]["QuestionID"]

print(f"Questions created: {len(Q)}")
for tag, qid in Q.items():
    print(f"  {qid}: {tag}")

# 4. Clear default block, assign all questions to their blocks
print("\n4. Assigning to blocks...")
api("PUT", f"/survey-definitions/{sid}/blocks/{defblock}",
    {"Type": "Standard", "Description": "Default", "BlockElements": [], "Options": OPTS})

assignments = {
    "consent": [Q["consent"]],
    "preference": [Q["feat"], Q["pref_text"]],
    "stimulus": [Q["stimulus"], Q["timer"]],
    "choice": [Q["choice"]],
    "process": [Q["reason"], Q["confidence"], Q["ai_recall"]],
    "brand_awareness": [Q["brand_awareness"]],
    "detection": [Q["detect1"], Q["detect2"], Q["ai_match"]],
    "debrief": [Q["debrief"], Q["revise_yn"], Q["revised_choice"]],
    "demographics": [Q["suspicion"], Q["age"], Q["gender"], Q["ai_usage"]],
}

for bname, qids in assignments.items():
    elements = []
    for i, qid in enumerate(qids):
        elements.append({"Type": "Question", "QuestionID": qid})
        if i < len(qids) - 1:
            elements.append({"Type": "Page Break"})
    r = api("PUT", f"/survey-definitions/{sid}/blocks/{blocks[bname]}",
            {"Type": "Standard", "Description": bname, "BlockElements": elements, "Options": OPTS})
    print(f"  {bname}: {'OK' if r else 'FAIL'}")
    time.sleep(0.3)

# 5. Build flow with BlockRandomizer
print("\n5. Setting up flow...")
conditions = [
    {"Condition": "1", "ConditionD": "NoAI", "AIRecommendation": "", "AIRecVersion": "none"},
    {"Condition": "2", "ConditionD": "BiasedAI", "AIRecommendation": BIASED_POS1, "AIRecVersion": "pos1"},
    {"Condition": "3", "ConditionD": "BiasedAI", "AIRecommendation": BIASED_POS3, "AIRecVersion": "pos3"},
    {"Condition": "4", "ConditionD": "DebiasedAI", "AIRecommendation": DEBIASED_POS1, "AIRecVersion": "pos1"},
    {"Condition": "5", "ConditionD": "DebiasedAI", "AIRecommendation": DEBIASED_POS3, "AIRecVersion": "pos3"},
]

rand_cells = []
for i, c in enumerate(conditions):
    eds = [{"Description": k, "Type": "Custom", "Field": k, "Value": v} for k, v in c.items()]
    rand_cells.append({"Type": "EmbeddedData", "FlowID": f"FL_C{i+1}", "EmbeddedData": eds})

flow = {"FlowID": "FL_1", "Type": "Root", "Flow": [
    {"Type": "EmbeddedData", "FlowID": "FL_INIT", "EmbeddedData": [
        {"Description": "ProductDisplayOrder", "Type": "Custom", "Field": "ProductDisplayOrder", "Value": ""},
        {"Description": "Condition", "Type": "Custom", "Field": "Condition", "Value": ""},
        {"Description": "ConditionD", "Type": "Custom", "Field": "ConditionD", "Value": ""},
        {"Description": "AIRecVersion", "Type": "Custom", "Field": "AIRecVersion", "Value": ""},
        {"Description": "AIRecommendation", "Type": "Custom", "Field": "AIRecommendation", "Value": ""},
    ]},
    {"Type": "Block", "ID": blocks["consent"], "FlowID": "FL_CON"},
    {"Type": "BlockRandomizer", "FlowID": "FL_RAND", "SubSet": 1, "EvenPresentation": True, "Flow": rand_cells},
    {"Type": "Block", "ID": blocks["preference"], "FlowID": "FL_PREF"},
    {"Type": "Block", "ID": blocks["stimulus"], "FlowID": "FL_STIM"},
    {"Type": "Block", "ID": blocks["choice"], "FlowID": "FL_CH"},
    {"Type": "Block", "ID": blocks["process"], "FlowID": "FL_PROC"},
    {"Type": "Block", "ID": blocks["brand_awareness"], "FlowID": "FL_BRAND"},
    {"Type": "Block", "ID": blocks["detection"], "FlowID": "FL_DET"},
    {"Type": "Block", "ID": blocks["debrief"], "FlowID": "FL_DEB"},
    {"Type": "Block", "ID": blocks["demographics"], "FlowID": "FL_DEMO"},
    {"Type": "EndSurvey", "FlowID": "FL_END"}
]}

r = api("PUT", f"/survey-definitions/{sid}/flow", flow)
print(f"Flow: {'OK' if r else 'FAIL'}")

# 6. Activate
r = api("PUT", f"/surveys/{sid}", {"isActive": True})
print(f"Active: {r is not None}")

# 7. Verify
print(f"\n{'='*60}")
print(f"Study A CLEAN: {sid}")
print(f"Edit: https://okstatebusiness.az1.qualtrics.com/survey-builder/{sid}/edit")
print(f"Live: https://okstatebusiness.az1.qualtrics.com/jfe/form/{sid}")
print(f"Questions: {len(Q)}, Blocks: {len(blocks)}, Conditions: 5")
print(f"{'='*60}")
