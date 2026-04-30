"""Study 3: add post-choice DV battery (choice reason, trust, familiarity, WTP).

Net add: 4 questions in one new block, placed after stimulus, before feedback.
Uses piped text from study3_product_choice / study3_chose_optimal so questions
reference the participant's actual chosen product.

Re-runnable: checks for existing block by description to avoid duplicates.
"""
import requests, json, sys

API = "https://pdx1.qualtrics.com/API/v3"
TOKEN = "Br4dAvcZOSSsJcup0AXpLDj7BjuGs1Pp96nNirWY"
H = {"X-API-TOKEN": TOKEN, "Content-Type": "application/json"}
SID = "SV_8A33OiyMqjqr5LU"
BLOCK_DESC = "post_choice_dvs"


def fetch_survey():
    r = requests.get(f"{API}/survey-definitions/{SID}", headers=H)
    r.raise_for_status()
    return r.json()["result"]


def find_block(survey, desc):
    for bid, b in survey["Blocks"].items():
        if b.get("Description") == desc:
            return bid
    return None


def create_block(desc):
    r = requests.post(f"{API}/survey-definitions/{SID}/blocks", headers=H, json={
        "Type": "Standard", "Description": desc,
        "Options": {"BlockLocking": "false", "RandomizeQuestions": "false", "BlockVisibility": "Expanded"}
    })
    r.raise_for_status()
    return r.json()["result"]["BlockID"]


def create_question(payload):
    r = requests.post(f"{API}/survey-definitions/{SID}/questions", headers=H, json=payload)
    r.raise_for_status()
    return r.json()["result"]["QuestionID"]


def put_block(bid, desc, element_qids):
    """element_qids: list of (QID, is_page_break_after: bool)"""
    elements = []
    for i, (qid, pb) in enumerate(element_qids):
        elements.append({"Type": "Question", "QuestionID": qid})
        if pb and i < len(element_qids) - 1:
            elements.append({"Type": "Page Break"})
    r = requests.put(f"{API}/survey-definitions/{SID}/blocks/{bid}", headers=H, json={
        "Type": "Standard", "Description": desc,
        "BlockElements": elements,
        "Options": {"BlockLocking": "false", "RandomizeQuestions": "false", "BlockVisibility": "Expanded"}
    })
    r.raise_for_status()
    return r.json()


# ── Step 1: fetch + short-circuit if already added ──────────────────────────
survey = fetch_survey()
existing_bid = find_block(survey, BLOCK_DESC)
if existing_bid:
    print(f"Block '{BLOCK_DESC}' already exists ({existing_bid}). Skipping question creation.")
    new_bid = existing_bid
    new_qids = None
else:
    # ── Step 2: create the 4 questions ──────────────────────────────────────
    CHOSEN = '${e://Field/study3_product_choice}'  # piped product name

    # Q1: Choice reason (open-text)
    print("Creating choice_reason (TE/SL)...")
    q_reason = create_question({
        "QuestionText":
            '<span style="font-size:17px">What was the <b>main reason</b> you chose '
            f'<em>{CHOSEN}</em>? Please explain in your own words.</span>',
        "QuestionType": "TE", "Selector": "ML",
        "DataExportTag": "dv_choice_reason",
        "Validation": {"Settings": {"ForceResponse": "ON", "ForceResponseType": "ON", "Type": "None"}},
        "Language": [],
    })
    print(f"  -> {q_reason}")

    # Q2: Trust / helpfulness / satisfaction Matrix (4-item, 7-pt Likert)
    # Shown only when the participant saw a chatbot (biased or honest), not neutral.
    print("Creating trust_battery (Matrix/Likert)...")
    q_trust = create_question({
        "QuestionText":
            '<span style="font-size:17px">Thinking about the <b>AI shopping assistant</b> '
            'you just used, please indicate how much you agree with each statement.</span>',
        "QuestionType": "Matrix", "Selector": "Likert", "SubSelector": "SingleAnswer",
        "DataExportTag": "dv_trust",
        "Choices": {
            "1": {"Display": "The AI was <b>helpful</b> in finding a product for me."},
            "2": {"Display": "I <b>trust</b> the AI's recommendation."},
            "3": {"Display": "The AI <b>understood</b> what I was looking for."},
            "4": {"Display": "I would <b>use this AI again</b> for shopping."},
        },
        "ChoiceOrder": ["1", "2", "3", "4"],
        "Answers": {
            "1": {"Display": "Strongly disagree"},
            "2": {"Display": "Disagree"},
            "3": {"Display": "Slightly disagree"},
            "4": {"Display": "Neither"},
            "5": {"Display": "Slightly agree"},
            "6": {"Display": "Agree"},
            "7": {"Display": "Strongly agree"},
        },
        "AnswerOrder": ["1", "2", "3", "4", "5", "6", "7"],
        "ChoiceDataExportTags": {
            "1": "dv_trust_helpful",
            "2": "dv_trust_trust",
            "3": "dv_trust_understood",
            "4": "dv_trust_reuse",
        },
        "Configuration": {"QuestionDescriptionOption": "UseText", "LabelPosition": "BELOW"},
        "Validation": {"Settings": {"ForceResponse": "ON", "ForceResponseType": "ON", "Type": "None"}},
        "Language": [],
    })
    print(f"  -> {q_trust}")

    # Q3: Brand familiarity (5-pt)
    print("Creating brand_familiarity (MC/SAHR)...")
    q_familiar = create_question({
        "QuestionText":
            '<span style="font-size:17px">Had you <b>heard of</b> '
            f'<em>{CHOSEN}</em> before today?</span>',
        "QuestionType": "MC", "Selector": "SAHR", "SubSelector": "TX",
        "DataExportTag": "dv_brand_familiar",
        "Choices": {
            "1": {"Display": "Never heard of it"},
            "2": {"Display": "Heard the name, no impression"},
            "3": {"Display": "Somewhat familiar"},
            "4": {"Display": "Very familiar"},
            "5": {"Display": "Own or have used a product from this brand"},
        },
        "ChoiceOrder": ["1", "2", "3", "4", "5"],
        "Configuration": {"QuestionDescriptionOption": "UseText"},
        "Validation": {"Settings": {"ForceResponse": "ON", "ForceResponseType": "ON", "Type": "None"}},
        "Language": [],
    })
    print(f"  -> {q_familiar}")

    # Q4: WTP (numeric text entry)
    print("Creating wtp (TE/SL)...")
    q_wtp = create_question({
        "QuestionText":
            '<span style="font-size:17px">What is the <b>maximum amount</b> you would be '
            f'willing to pay for <em>{CHOSEN}</em>?<br>'
            '<span style="font-size:14px;color:#666">Please enter a dollar amount (numbers only, no $ sign).</span></span>',
        "QuestionType": "TE", "Selector": "SL",
        "DataExportTag": "dv_wtp",
        "Validation": {
            "Settings": {
                "ForceResponse": "ON", "ForceResponseType": "ON",
                "Type": "ContentType", "ContentType": "ValidNumber",
            }
        },
        "Language": [],
    })
    print(f"  -> {q_wtp}")

    # ── Step 3: create the block + assign questions ─────────────────────────
    print("Creating block post_choice_dvs...")
    new_bid = create_block(BLOCK_DESC)
    print(f"  block {new_bid}")
    # One question per page (page-break after each)
    put_block(new_bid, BLOCK_DESC, [(q_reason, True), (q_trust, True), (q_familiar, True), (q_wtp, False)])
    new_qids = (q_reason, q_trust, q_familiar, q_wtp)

# ── Step 4: insert into flow between stimulus and feedback ──────────────────
# Re-fetch to get latest state (block may have just been added)
survey = fetch_survey()
flow = survey["SurveyFlow"]
blocks = survey["Blocks"]

block_map = {b.get("Description"): bid for bid, b in blocks.items()}
stim_bid = block_map.get("stimulus")
fb_bid = block_map.get("feedback")

flow_items = flow["Flow"]
# Already wired?
wired = any(it.get("Type") == "Standard" and it.get("ID") == new_bid for it in flow_items)
if wired:
    print(f"Block already in flow. Done.")
else:
    # Find index of feedback block in flow; insert new block before it.
    insert_at = None
    for i, it in enumerate(flow_items):
        if it.get("Type") == "Standard" and it.get("ID") == fb_bid:
            insert_at = i
            break
    if insert_at is None:
        print("WARNING: feedback block not found in flow; appending before demographics.")
        for i, it in enumerate(flow_items):
            if it.get("Type") == "Standard" and it.get("ID") == block_map.get("demographics"):
                insert_at = i
                break
    if insert_at is None:
        insert_at = len(flow_items) - 1  # before EndSurvey
    flow_items.insert(insert_at, {"Type": "Standard", "ID": new_bid, "FlowID": "FL_DV", "Autofill": []})
    flow["Flow"] = flow_items
    r = requests.put(f"{API}/survey-definitions/{SID}/flow", headers=H, json=flow)
    print(f"Flow update: HTTP {r.status_code}")
    if r.status_code >= 400:
        print(r.text[:500]); sys.exit(1)

# ── Step 5: print final flow ────────────────────────────────────────────────
print()
print("=== Updated flow ===")
survey = fetch_survey()
for it in survey["SurveyFlow"]["Flow"]:
    t = it.get("Type")
    if t == "Standard":
        bid = it.get("ID"); desc = survey["Blocks"].get(bid, {}).get("Description", "?")
        marker = "  <- NEW" if bid == new_bid else ""
        print(f"  Standard  {desc}{marker}")
    elif t == "BlockRandomizer":
        print(f"  BlockRandomizer  ({len(it.get('Flow', []))} cells)")
    elif t == "Branch":
        print(f"  Branch")
    elif t == "EmbeddedData":
        print(f"  EmbeddedData")
    elif t == "EndSurvey":
        print(f"  EndSurvey")
    else:
        print(f"  {t}")

print()
print("Draft updated. Run publish step separately (or let user publish in Qualtrics UI).")
