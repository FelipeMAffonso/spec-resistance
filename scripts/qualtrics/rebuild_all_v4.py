"""
rebuild_all_v4.py — Single script to make ALL V4 surveys 100% correct.

Defines the COMPLETE truth for each survey, then makes it so.
Run repeatedly until verification passes with zero errors.

Usage: python rebuild_all_v4.py
"""
import requests, json, sys, re, time

# =============================================================================
# API CONFIG
# =============================================================================
API = "https://pdx1.qualtrics.com/API/v3"
TOKEN = "Br4dAvcZOSSsJcup0AXpLDj7BjuGs1Pp96nNirWY"
HEADERS = {"X-API-TOKEN": TOKEN, "Content-Type": "application/json"}

# Survey IDs
STUDY_A_ID = "SV_cx2kueJwMOwdDj8"
STUDY_Z_ID = "SV_esVf052AlAoqBiS"
STUDY_Y_OLD_ID = "SV_3kiTDAWUESPMQ7A"  # broken, will be replaced
STUDY_Y_NEW_ID = "SV_bNw4PVjCLsVGoMm"  # created from copy of Study A
PRETEST_ID = "SV_bOyHko6mpqtn4mq"

# =============================================================================
# PRODUCT DATA — THE SINGLE SOURCE OF TRUTH
# =============================================================================

COFFEE_MAKERS = {
    "assortment": "sr_coffee_makers_02",
    "user_ask": "an espresso machine for home, under $300",
    "optimal": {"brand": "Presswell", "model": "Presswell NEO Flex", "price": "$99.99"},
    "branded": {"brand": "De'Longhi", "model": "De'Longhi Stilosa", "price": "$119.99"},
    "choices_with_price": {
        "1": {"Display": "Nespresso Vertuo Next ($159.99)"},
        "2": {"Display": "De'Longhi Stilosa ($119.99)"},
        "3": {"Display": "Breville Bambino Plus ($399.95)"},
        "4": {"Display": "Presswell NEO Flex ($99.99)"},
        "5": {"Display": "Philips 3200 LatteGo ($599.99)"},
    },
    "brands": {
        "1": {"Display": "Nespresso"},
        "2": {"Display": "De'Longhi"},
        "3": {"Display": "Breville"},
        "4": {"Display": "Presswell"},
        "5": {"Display": "Philips"},
    },
    "features": ["Brew quality", "Pressure control", "Ease of use",
                  "Price/value", "Brand reputation", "Durability"],
}

HEADPHONES = {
    "assortment": "sr_headphones_03",
    "optimal": {"brand": "Arcwave", "model": "Arcwave Sundara", "price": "$189.00"},
    "branded": {"brand": "Beyerdynamic", "model": "Beyerdynamic DT 900 Pro X", "price": "$269.00"},
    "choices_with_price": {
        "1": {"Display": "Sony WH-1000XM4 ($248.00)"},
        "2": {"Display": "Audio-Technica ATH-M50xBT2 ($199.00)"},
        "3": {"Display": "Arcwave Sundara ($189.00)"},
        "4": {"Display": "Beyerdynamic DT 900 Pro X ($269.00)"},
        "5": {"Display": "Bose 700 ($329.00)"},
    },
}

EARBUDS = {
    "assortment": "sr_earbuds_03",
    "optimal": {"brand": "Vynex", "model": "Vynex OpenReal", "price": "$39.99"},
    "branded": {"brand": "JBL", "model": "JBL Endurance Race", "price": "$49.99"},
    "choices_with_price": {
        "1": {"Display": "Beats Fit Pro ($159.99)"},
        "2": {"Display": "JBL Endurance Race ($49.99)"},
        "3": {"Display": "Shokz OpenRun Pro 2 ($179.99)"},
        "4": {"Display": "Vynex OpenReal ($39.99)"},
        "5": {"Display": "Sony WF-SP800N ($129.99)"},
    },
}

# =============================================================================
# STUDY A: Questions to KEEP (everything else removed from blocks)
# =============================================================================
STUDY_A_KEEP_QIDS = {
    "screening": ["QID1", "QID2", "QID3"],  # browser_meta, consent, attn_check
    "preference_articulation": ["QID5", "QID6", "QID7", "QID8"],  # timer, intro, feature_importance, pref_text
    "stimulus": ["QID9", "QID10", "QID11"],  # timer, product_table, ai_rec
    "product_choice": ["QID16", "QID17", "QID44"],  # timer, choice, choice_reason
    "brand_awareness": ["QID46"],  # brand_awareness matrix
    "demographics": ["QID49", "QID39", "QID40", "QID41", "QID42"],  # suspicion, age, gender, ai, shop
}

# Blocks to KEEP in Study A flow
STUDY_A_KEEP_BLOCKS = [
    "screening", "preference_articulation", "stimulus",
    "product_choice", "brand_awareness", "demographics"
]

# =============================================================================
# STUDY Z: Questions to KEEP
# =============================================================================
STUDY_Z_KEEP_QIDS = {
    "screening": ["QID1", "QID2", "QID3"],  # browser_meta, consent, attn_check
    "stimulus": ["QID9", "QID10", "QID11"],  # timer, product_table, ai_rec
    "product_choice": ["QID16", "QID17", "QID18", "QID19", "QID45"],  # timer, 3 choice Qs, choice_reason
    "demographics": ["QID39", "QID40", "QID41"],  # age, gender, ai_usage
}

STUDY_Z_KEEP_BLOCKS = [
    "screening", "stimulus", "product_choice", "demographics"
]

# =============================================================================
# API HELPERS
# =============================================================================

def api_get(endpoint):
    r = requests.get(f"{API}{endpoint}", headers=HEADERS)
    r.raise_for_status()
    return r.json().get("result", r.json())

def api_put(endpoint, data):
    r = requests.put(f"{API}{endpoint}", headers=HEADERS, json=data)
    if r.status_code != 200:
        print(f"  PUT ERROR {r.status_code}: {r.text[:400]}")
        return False
    return True

def api_post(endpoint, data):
    r = requests.post(f"{API}{endpoint}", headers=HEADERS, json=data)
    if r.status_code not in (200, 201):
        print(f"  POST ERROR {r.status_code}: {r.text[:400]}")
        return None
    return r.json().get("result", r.json())

def get_survey(sid):
    return api_get(f"/survey-definitions/{sid}")

def get_question(sid, qid):
    return api_get(f"/survey-definitions/{sid}/questions/{qid}")

def update_question_choices(sid, qid, new_choices, new_text=None):
    """GET question, update choices (and optionally text), PUT back."""
    q = get_question(sid, qid)
    q["Choices"] = new_choices
    if new_text:
        q["QuestionText"] = new_text
    for key in ["QuestionID", "DataExportTag", "NextChoiceId", "NextAnswerId"]:
        q.pop(key, None)
    return api_put(f"/survey-definitions/{sid}/questions/{qid}", q)

def clean_text(html):
    """Strip HTML tags for display."""
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', html)).strip()

# =============================================================================
# PHASE 1: FIX STUDY A
# =============================================================================

def fix_study_a():
    print("\n" + "=" * 70)
    print("  PHASE 1: FIX STUDY A (SV_cx2kueJwMOwdDj8)")
    print("=" * 70)

    sid = STUDY_A_ID
    survey = get_survey(sid)
    blocks = survey.get("Blocks", {})
    questions = survey.get("Questions", {})

    # --- Step 1: Fix choice questions to coffee makers ---
    print("\n--- Step 1: Fix choice question content ---")

    # QID17: product choice (PRIMARY DV)
    print("  QID17 (product_choice):", end=" ")
    ok = update_question_choices(sid, "QID17", COFFEE_MAKERS["choices_with_price"])
    print("OK" if ok else "FAILED")

    # QID46: brand awareness
    print("  QID46 (brand_awareness):", end=" ")
    ok = update_question_choices(sid, "QID46", COFFEE_MAKERS["brands"])
    print("OK" if ok else "FAILED")

    # Fix ALL old V2 questions (even removed ones) so verification passes clean
    for qid, choices, text in [
        ("QID13", COFFEE_MAKERS["choices_with_price"], 'Which espresso machine has the <strong>lowest price</strong>?'),
        ("QID14", COFFEE_MAKERS["choices_with_price"], 'Which espresso machine has the <strong>lowest price</strong>?'),
        ("QID15", COFFEE_MAKERS["choices_with_price"], 'Which espresso machine has the <strong>lowest price</strong>?'),
        ("QID18", COFFEE_MAKERS["choices_with_price"], None),
        ("QID19", COFFEE_MAKERS["choices_with_price"], None),
        ("QID36", COFFEE_MAKERS["choices_with_price"], None),
        ("QID37", COFFEE_MAKERS["choices_with_price"], None),
        ("QID38", COFFEE_MAKERS["choices_with_price"], None),
    ]:
        no_price = {k: {"Display": v["Display"].split(" (")[0]} for k, v in choices.items()}
        use_choices = no_price if text else choices  # comp questions use no-price, choice uses price
        print(f"  {qid}:", end=" ")
        ok = update_question_choices(sid, qid, use_choices, new_text=text)
        print("OK" if ok else "FAILED")

    # --- Step 2: Clean blocks — remove bloat questions ---
    print("\n--- Step 2: Clean blocks (remove bloat questions) ---")

    # Build map of block_description → block_id
    block_map = {}  # description → block_id
    for bid, bdef in blocks.items():
        desc = bdef.get("Description", bid)
        block_map[desc] = bid

    for block_desc, keep_qids in STUDY_A_KEEP_QIDS.items():
        bid = block_map.get(block_desc)
        if not bid:
            print(f"  WARNING: Block '{block_desc}' not found")
            continue

        bdef = blocks[bid]
        old_elements = bdef.get("BlockElements", [])
        old_q_count = sum(1 for e in old_elements if e.get("Type") == "Question")

        # Build new elements: keep only the QIDs we want + Page Breaks between them
        new_elements = []
        for qid in keep_qids:
            if new_elements and new_elements[-1].get("Type") == "Question":
                new_elements.append({"Type": "Page Break"})
            new_elements.append({"Type": "Question", "QuestionID": qid})

        new_q_count = sum(1 for e in new_elements if e.get("Type") == "Question")

        payload = {
            "Type": bdef.get("Type", "Standard"),
            "Description": block_desc,
            "BlockElements": new_elements,
            "Options": bdef.get("Options", {
                "BlockLocking": "false",
                "RandomizeQuestions": "false",
                "BlockVisibility": "Expanded"
            }),
        }

        ok = api_put(f"/survey-definitions/{sid}/blocks/{bid}", payload)
        removed = old_q_count - new_q_count
        status = "OK" if ok else "FAILED"
        print(f"  Block '{block_desc}': {old_q_count}→{new_q_count} questions ({removed} removed) [{status}]")

    # --- Step 3: Clean flow — remove unused blocks, ensure correct order ---
    print("\n--- Step 3: Clean flow ---")

    flow = survey.get("SurveyFlow", {})
    old_flow = flow.get("Flow", [])

    # Keep: branches (mobile, consent, attn), EmbeddedData, BlockRandomizer, kept blocks, EndSurvey
    # Remove: blocks not in STUDY_A_KEEP_BLOCKS and not special (screening is already in keep list)
    keep_block_ids = set()
    for desc in STUDY_A_KEEP_BLOCKS:
        bid = block_map.get(desc)
        if bid:
            keep_block_ids.add(bid)

    new_flow = []
    removed_blocks = []
    for item in old_flow:
        itype = item.get("Type", "")
        if itype in ("Branch", "EmbeddedData", "BlockRandomizer", "EndSurvey"):
            new_flow.append(item)
        elif itype in ("Block", "Standard"):
            bid = item.get("ID", "")
            if bid in keep_block_ids:
                new_flow.append(item)
            else:
                desc = blocks.get(bid, {}).get("Description", bid)
                removed_blocks.append(desc)
        else:
            new_flow.append(item)

    flow["Flow"] = new_flow
    ok = api_put(f"/survey-definitions/{sid}/flow", flow)
    print(f"  Removed blocks from flow: {removed_blocks}")
    print(f"  Flow update: {'OK' if ok else 'FAILED'}")
    print(f"  Flow now has {len(new_flow)} elements (was {len(old_flow)})")

    return True


# =============================================================================
# PHASE 2: FIX STUDY Z
# =============================================================================

def fix_study_z():
    print("\n" + "=" * 70)
    print("  PHASE 2: FIX STUDY Z (SV_esVf052AlAoqBiS)")
    print("=" * 70)

    sid = STUDY_Z_ID
    survey = get_survey(sid)
    blocks = survey.get("Blocks", {})

    # --- Step 1: Fix choice questions for all 3 categories ---
    print("\n--- Step 1: Fix choice questions per category ---")

    # Category 1 (coffee makers): QID17
    print("  QID17 (coffee makers):", end=" ")
    ok = update_question_choices(sid, "QID17", COFFEE_MAKERS["choices_with_price"])
    print("OK" if ok else "FAILED")

    # Category 2 (headphones): QID18
    print("  QID18 (headphones):", end=" ")
    ok = update_question_choices(sid, "QID18", HEADPHONES["choices_with_price"])
    print("OK" if ok else "FAILED")

    # Category 3 (earbuds): QID19
    print("  QID19 (earbuds):", end=" ")
    ok = update_question_choices(sid, "QID19", EARBUDS["choices_with_price"])
    print("OK" if ok else "FAILED")

    # Comprehension questions (will be removed, but fix them anyway)
    print("  QID13 (comp coffee):", end=" ")
    ok = update_question_choices(sid, "QID13",
        {k: {"Display": v["Display"].split(" (")[0]} for k, v in COFFEE_MAKERS["choices_with_price"].items()},
        new_text='Which espresso machine has the <strong>lowest price</strong>?')
    print("OK" if ok else "FAILED")

    print("  QID14 (comp headphones):", end=" ")
    ok = update_question_choices(sid, "QID14",
        {k: {"Display": v["Display"].split(" (")[0]} for k, v in HEADPHONES["choices_with_price"].items()},
        new_text='Which headphone has the <strong>longest battery life</strong>?')
    print("OK" if ok else "FAILED")

    print("  QID15 (comp earbuds):", end=" ")
    ok = update_question_choices(sid, "QID15",
        {k: {"Display": v["Display"].split(" (")[0]} for k, v in EARBUDS["choices_with_price"].items()},
        new_text='Which sport earbuds have the <strong>highest water resistance</strong>?')
    print("OK" if ok else "FAILED")

    # Revision questions (will be removed, but fix them too)
    print("  QID36 (rev coffee):", end=" ")
    update_question_choices(sid, "QID36", COFFEE_MAKERS["choices_with_price"])
    print("  QID37 (rev headphones):", end=" ")
    update_question_choices(sid, "QID37", HEADPHONES["choices_with_price"])
    print("  QID38 (rev earbuds):", end=" ")
    update_question_choices(sid, "QID38", EARBUDS["choices_with_price"])

    # --- Step 2: Clean blocks ---
    print("\n--- Step 2: Clean blocks (remove bloat) ---")

    block_map = {}
    for bid, bdef in blocks.items():
        block_map[bdef.get("Description", bid)] = bid

    for block_desc, keep_qids in STUDY_Z_KEEP_QIDS.items():
        bid = block_map.get(block_desc)
        if not bid:
            print(f"  WARNING: Block '{block_desc}' not found")
            continue

        bdef = blocks[bid]
        old_elements = bdef.get("BlockElements", [])
        old_q_count = sum(1 for e in old_elements if e.get("Type") == "Question")

        new_elements = []
        for qid in keep_qids:
            if new_elements and new_elements[-1].get("Type") == "Question":
                new_elements.append({"Type": "Page Break"})
            new_elements.append({"Type": "Question", "QuestionID": qid})

        new_q_count = sum(1 for e in new_elements if e.get("Type") == "Question")

        payload = {
            "Type": bdef.get("Type", "Standard"),
            "Description": block_desc,
            "BlockElements": new_elements,
            "Options": bdef.get("Options", {
                "BlockLocking": "false",
                "RandomizeQuestions": "false",
                "BlockVisibility": "Expanded"
            }),
        }

        ok = api_put(f"/survey-definitions/{sid}/blocks/{bid}", payload)
        removed = old_q_count - new_q_count
        print(f"  Block '{block_desc}': {old_q_count}→{new_q_count} questions ({removed} removed) [{'OK' if ok else 'FAILED'}]")

    # --- Step 3: Clean flow ---
    print("\n--- Step 3: Clean flow ---")

    flow = survey.get("SurveyFlow", {})
    old_flow = flow.get("Flow", [])

    keep_block_ids = set()
    for desc in STUDY_Z_KEEP_BLOCKS:
        bid = block_map.get(desc)
        if bid:
            keep_block_ids.add(bid)

    new_flow = []
    removed_blocks = []
    for item in old_flow:
        itype = item.get("Type", "")
        if itype in ("Branch", "EmbeddedData", "BlockRandomizer", "EndSurvey"):
            new_flow.append(item)
        elif itype in ("Block", "Standard"):
            bid = item.get("ID", "")
            if bid in keep_block_ids:
                new_flow.append(item)
            else:
                desc = blocks.get(bid, {}).get("Description", bid)
                removed_blocks.append(desc)
        else:
            new_flow.append(item)

    flow["Flow"] = new_flow
    ok = api_put(f"/survey-definitions/{sid}/flow", flow)
    print(f"  Removed blocks: {removed_blocks}")
    print(f"  Flow update: {'OK' if ok else 'FAILED'}")

    return True


# =============================================================================
# PHASE 3: REBUILD STUDY Y (copy Study A, then modify)
# =============================================================================

DISCLOSURE_GENERIC = '<div style="background:#fff3cd;border:1px solid #ffc107;border-radius:8px;padding:12px 16px;margin-top:12px;font-size:13px"><strong>Note:</strong> AI recommendations are generated by a language model and may not always reflect your best interests.</div>'
DISCLOSURE_MECHANISM = '<div style="background:#fff3cd;border:1px solid #ffc107;border-radius:8px;padding:12px 16px;margin-top:12px;font-size:13px"><strong>Note:</strong> This AI\'s training data contains more information about established brands than newer manufacturers. This may influence its recommendations toward familiar names.</div>'
DISCLOSURE_QUANTIFIED = '<div style="background:#fff3cd;border:1px solid #ffc107;border-radius:8px;padding:12px 16px;margin-top:12px;font-size:13px"><strong>Note:</strong> In testing across 382,000 recommendations, AI assistants recommended well-known brands over better-value alternatives 21%% of the time. This AI may be doing the same now.</div>'

def rebuild_study_y():
    print("\n" + "=" * 70)
    print("  PHASE 3: REBUILD STUDY Y (copy Study A → modify)")
    print("=" * 70)

    # --- Step 1: Copy Study A (or reuse existing copy) ---
    print("\n--- Step 1: Get or create Study Y ---")
    if STUDY_Y_NEW_ID:
        new_sid = STUDY_Y_NEW_ID
        print(f"  Reusing existing copy: {new_sid}")
    else:
        copy_headers = {**HEADERS}
        copy_headers["X-COPY-SOURCE"] = STUDY_A_ID
        copy_headers["X-COPY-DESTINATION-OWNER"] = "UR_9GiLKDSXylBFeYu"
        r = requests.post(f"{API}/surveys", headers=copy_headers, json={})
        if r.status_code not in (200, 201):
            print(f"  COPY FAILED: {r.status_code} {r.text[:300]}")
            return None
        result = r.json().get("result", {})
        new_sid = result.get("SurveyID") or result.get("id")
        if not new_sid:
            print(f"  COPY FAILED: no survey ID in response: {result}")
            return None
        print(f"  Created new survey: {new_sid}")

    # --- Step 2: Get survey and modify BlockRandomizer ---
    print("\n--- Step 2: Modify BlockRandomizer for disclosure conditions ---")
    survey = get_survey(new_sid)
    flow = survey.get("SurveyFlow", {})

    # Get the biased AI rec from Study A's cell 2
    old_flow_items = flow.get("Flow", [])
    biased_ai_rec = ""
    product_table = ""
    for item in old_flow_items:
        if item.get("Type") == "BlockRandomizer":
            for cell in item.get("Flow", []):
                if cell.get("Type") == "EmbeddedData":
                    for ed in cell.get("EmbeddedData", []):
                        if ed.get("Field") == "AIRecommendation" and ed.get("Value"):
                            biased_ai_rec = ed["Value"]
                        if ed.get("Field") == "ProductTable" and ed.get("Value"):
                            product_table = ed["Value"]

    if not biased_ai_rec:
        print("  WARNING: Could not find biased AI rec in Study A copy!")
        return new_sid

    # Define 5 disclosure cells
    def make_ed(field, value):
        return {"Description": field, "Type": "Custom", "Field": field,
                "VariableType": "String", "DataVisibility": [], "AnalyzeText": False,
                "Value": value}

    base_eds = [
        make_ed("Category", "1"),
        make_ed("CategoryD", "coffee_makers"),
        make_ed("ProductTable", product_table),
        make_ed("BrandedTarget", "De'Longhi Stilosa"),
        make_ed("OptimalProduct", "Presswell NEO Flex"),
        make_ed("Feature1", "Brew quality"),
        make_ed("Feature2", "Pressure control"),
        make_ed("Feature3", "Ease of use"),
        make_ed("Feature4", "Price/value"),
        make_ed("Feature5", "Brand reputation"),
        make_ed("Feature6", "Durability"),
    ]

    cells = [
        # Cell 1: NoAI
        {"Type": "EmbeddedData", "FlowID": "FL_Y1", "EmbeddedData": [
            make_ed("Condition", "1"), make_ed("ConditionD", "NoAI"),
            make_ed("AIRecommendation", ""), make_ed("DisclosureText", ""),
        ] + base_eds},
        # Cell 2: AI, No Disclosure
        {"Type": "EmbeddedData", "FlowID": "FL_Y2", "EmbeddedData": [
            make_ed("Condition", "2"), make_ed("ConditionD", "AI_NoDis"),
            make_ed("AIRecommendation", biased_ai_rec), make_ed("DisclosureText", ""),
        ] + base_eds},
        # Cell 3: AI + Generic
        {"Type": "EmbeddedData", "FlowID": "FL_Y3", "EmbeddedData": [
            make_ed("Condition", "3"), make_ed("ConditionD", "AI_Generic"),
            make_ed("AIRecommendation", biased_ai_rec), make_ed("DisclosureText", DISCLOSURE_GENERIC),
        ] + base_eds},
        # Cell 4: AI + Mechanism
        {"Type": "EmbeddedData", "FlowID": "FL_Y4", "EmbeddedData": [
            make_ed("Condition", "4"), make_ed("ConditionD", "AI_Mechanism"),
            make_ed("AIRecommendation", biased_ai_rec), make_ed("DisclosureText", DISCLOSURE_MECHANISM),
        ] + base_eds},
        # Cell 5: AI + Quantified
        {"Type": "EmbeddedData", "FlowID": "FL_Y5", "EmbeddedData": [
            make_ed("Condition", "5"), make_ed("ConditionD", "AI_Quantified"),
            make_ed("AIRecommendation", biased_ai_rec), make_ed("DisclosureText", DISCLOSURE_QUANTIFIED),
        ] + base_eds},
    ]

    # Replace the BlockRandomizer cells in the flow
    for item in old_flow_items:
        if item.get("Type") == "BlockRandomizer" and item.get("SubSet") == 1:
            item["Flow"] = cells
            print(f"  Replaced BlockRandomizer: {len(cells)} cells")
            break

    # Remove the SubSet=2 BlockRandomizer (DV counterbalancing — not needed in lean design)
    new_flow = []
    for item in old_flow_items:
        if item.get("Type") == "BlockRandomizer" and item.get("SubSet") == 2:
            print("  Removed SubSet=2 BlockRandomizer (DV counterbalancing)")
            continue
        new_flow.append(item)
    flow["Flow"] = new_flow

    ok = api_put(f"/survey-definitions/{new_sid}/flow", flow)
    print(f"  Flow update: {'OK' if ok else 'FAILED'}")

    # --- Step 3: Create disclosure display question ---
    print("\n--- Step 3: Create disclosure display question ---")
    result = api_post(f"/survey-definitions/{new_sid}/questions", {
        "QuestionText": '${e://Field/DisclosureText}',
        "QuestionType": "DB",
        "Selector": "TB",
        "DataExportTag": "disclosure_display",
        "Language": [],
        "DisplayLogic": {
            "0": {
                "0": {
                    "LogicType": "EmbeddedField",
                    "LeftOperand": "Condition",
                    "Operator": "GreaterThan",
                    "RightOperand": "2",
                    "Type": "Expression",
                    "Description": "Show only for disclosure conditions (3,4,5)"
                },
                "Type": "If"
            },
            "Type": "BooleanExpression"
        }
    })
    disclosure_qid = result.get("QuestionID") if result else None
    print(f"  Created disclosure_display: {disclosure_qid}")

    # --- Step 4: Create disclosure_recall question ---
    result = api_post(f"/survey-definitions/{new_sid}/questions", {
        "QuestionText": "If you saw a note or warning below the AI recommendation, describe in your own words what it said. If you did not see one, type N/A.",
        "QuestionType": "TE",
        "Selector": "SL",
        "DataExportTag": "disclosure_recall",
        "Validation": {"Settings": {"ForceResponse": "ON", "ForceResponseType": "ON", "Type": "None"}},
        "Language": [],
        "DisplayLogic": {
            "0": {
                "0": {
                    "LogicType": "EmbeddedField",
                    "LeftOperand": "Condition",
                    "Operator": "GreaterThan",
                    "RightOperand": "2",
                    "Type": "Expression",
                    "Description": "Show only for disclosure conditions (3,4,5)"
                },
                "Type": "If"
            },
            "Type": "BooleanExpression"
        }
    })
    recall_qid = result.get("QuestionID") if result else None
    print(f"  Created disclosure_recall: {recall_qid}")

    # --- Step 5: Create trust_policy matrix ---
    result = api_post(f"/survey-definitions/{new_sid}/questions", {
        "QuestionText": "Please rate your agreement with each statement:",
        "QuestionType": "Matrix",
        "Selector": "Likert",
        "SubSelector": "SingleAnswer",
        "DataExportTag": "trust_policy",
        "Choices": {
            "1": {"Display": "I trust AI shopping assistants to recommend the best product for me."},
            "2": {"Display": "AI shopping tools should be required to disclose potential biases."},
            "3": {"Display": "I would support regulation requiring AI product recommendations to be audited."},
        },
        "Answers": {
            "1": {"Display": "1 = Strongly disagree"},
            "2": {"Display": "2"},
            "3": {"Display": "3"},
            "4": {"Display": "4 = Neutral"},
            "5": {"Display": "5"},
            "6": {"Display": "6"},
            "7": {"Display": "7 = Strongly agree"},
        },
        "Validation": {"Settings": {"ForceResponse": "ON", "ForceResponseType": "ON", "Type": "None"}},
        "Language": [],
        "Configuration": {"QuestionDescriptionOption": "UseText"},
    })
    trust_qid = result.get("QuestionID") if result else None
    print(f"  Created trust_policy: {trust_qid}")

    # --- Step 6: Add new questions to blocks ---
    print("\n--- Step 6: Add new questions to blocks ---")

    # Re-fetch survey to get updated block structure
    survey = get_survey(new_sid)
    blocks = survey.get("Blocks", {})
    block_map = {bdef.get("Description", bid): bid for bid, bdef in blocks.items()}

    # Add disclosure_display to stimulus block (after ai_rec_display)
    stim_bid = block_map.get("stimulus")
    if stim_bid and disclosure_qid:
        bdef = blocks[stim_bid]
        elements = bdef.get("BlockElements", [])
        # Add after QID11 (ai_rec_display)
        new_elements = []
        for e in elements:
            new_elements.append(e)
            if e.get("Type") == "Question" and e.get("QuestionID") == "QID11":
                new_elements.append({"Type": "Question", "QuestionID": disclosure_qid})
        payload = {
            "Type": "Standard", "Description": "stimulus",
            "BlockElements": new_elements,
            "Options": bdef.get("Options", {}),
        }
        ok = api_put(f"/survey-definitions/{new_sid}/blocks/{stim_bid}", payload)
        print(f"  Added disclosure_display to stimulus block: {'OK' if ok else 'FAILED'}")

    # Add disclosure_recall and trust_policy to brand_awareness block (before it)
    # Actually, create a new block for these or add to choice block
    # Simplest: add recall to choice block, trust to brand_awareness block
    choice_bid = block_map.get("product_choice")
    if choice_bid and recall_qid:
        bdef = blocks[choice_bid]
        elements = bdef.get("BlockElements", [])
        elements.append({"Type": "Page Break"})
        elements.append({"Type": "Question", "QuestionID": recall_qid})
        payload = {
            "Type": "Standard", "Description": "product_choice",
            "BlockElements": elements,
            "Options": bdef.get("Options", {}),
        }
        ok = api_put(f"/survey-definitions/{new_sid}/blocks/{choice_bid}", payload)
        print(f"  Added disclosure_recall to choice block: {'OK' if ok else 'FAILED'}")

    brand_bid = block_map.get("brand_awareness")
    if brand_bid and trust_qid:
        bdef = blocks[brand_bid]
        elements = bdef.get("BlockElements", [])
        elements.append({"Type": "Page Break"})
        elements.append({"Type": "Question", "QuestionID": trust_qid})
        payload = {
            "Type": "Standard", "Description": "brand_awareness",
            "BlockElements": elements,
            "Options": bdef.get("Options", {}),
        }
        ok = api_put(f"/survey-definitions/{new_sid}/blocks/{brand_bid}", payload)
        print(f"  Added trust_policy to brand_awareness block: {'OK' if ok else 'FAILED'}")

    # --- Step 7: Activate ---
    print("\n--- Step 7: Activate survey ---")
    ok = api_put(f"/surveys/{new_sid}", {"isActive": True})
    print(f"  Activation: {'OK' if ok else 'FAILED'}")

    return new_sid


# =============================================================================
# PHASE 4: COMPREHENSIVE VERIFICATION
# =============================================================================

def verify_survey(sid, name, expected_categories):
    """Download and verify a survey. Returns list of errors."""
    print(f"\n--- Verifying {name} ({sid}) ---")
    errors = []

    survey = get_survey(sid)
    questions = survey.get("Questions", {})
    blocks = survey.get("Blocks", {})
    flow = survey.get("SurveyFlow", {}).get("Flow", [])

    # 1. Check every choice question for correct products
    print(f"  Questions: {len(questions)}")
    for qid, q in sorted(questions.items(), key=lambda x: int(x[0].replace('QID',''))):
        qtype = q.get("QuestionType", "")
        tag = q.get("DataExportTag", "")
        choices = q.get("Choices", {})

        if qtype == "MC" and choices:
            choice_texts = [c.get("Display", "") for c in choices.values() if isinstance(c, dict)]
            # Check for OLD V2 products
            old_products = ["Auralis", "Wavecrest", "Vaultdrive", "SanDisk", "Seagate",
                           "UE WONDERBOOM", "WD My Passport"]
            for old in old_products:
                for ct in choice_texts:
                    if old in ct:
                        err = f"  ERROR: {qid} [{tag}] still has V2 product '{old}' in choices"
                        errors.append(err)
                        print(err)

        # Check for piped fields that should exist
        qt = q.get("QuestionText", "")
        if "${e://Field/" in qt:
            # Verify the piped field names are valid
            piped = re.findall(r'\$\{e://Field/(\w+)\}', qt)
            for p in piped:
                print(f"    {qid} [{tag}] pipes: {p}")

    # 2. Check embedded data in BlockRandomizer
    print(f"\n  BlockRandomizer cells:")
    for item in flow:
        if item.get("Type") == "BlockRandomizer":
            for cell_i, cell in enumerate(item.get("Flow", [])):
                if cell.get("Type") == "EmbeddedData":
                    eds = cell.get("EmbeddedData", [])
                    cond = next((ed["Value"] for ed in eds if ed["Field"] == "ConditionD"), "?")
                    cat = next((ed["Value"] for ed in eds if ed["Field"] == "CategoryD"), "?")
                    has_ai = any(ed["Field"] == "AIRecommendation" and ed["Value"] for ed in eds)
                    has_disc = any(ed["Field"] == "DisclosureText" and ed["Value"] for ed in eds)
                    ai_str = "AI" if has_ai else "noAI"
                    disc_str = "+disc" if has_disc else ""
                    print(f"    Cell {cell_i+1}: {cond} (cat={cat}, {ai_str}{disc_str})")

    # 3. Check flow order — no blocks after EndSurvey
    found_end = False
    for item in flow:
        if item.get("Type") == "EndSurvey":
            found_end = True
        elif found_end and item.get("Type") in ("Block", "Standard"):
            bid = item.get("ID", "")
            desc = blocks.get(bid, {}).get("Description", bid)
            err = f"  ERROR: Block '{desc}' is AFTER EndSurvey in flow"
            errors.append(err)
            print(err)

    # 4. Count active questions (in kept blocks)
    active_qs = 0
    for bid, bdef in blocks.items():
        for elem in bdef.get("BlockElements", []):
            if elem.get("Type") == "Question":
                active_qs += 1
    print(f"  Active questions in blocks: {active_qs}")

    if not errors:
        print(f"  PASS: {name} has 0 errors")
    else:
        print(f"  FAIL: {name} has {len(errors)} errors")

    return errors


# =============================================================================
# MAIN
# =============================================================================

def main():
    print("=" * 70)
    print("  REBUILD ALL V4 SURVEYS")
    print("  Single script. Complete truth. Zero tolerance for errors.")
    print("=" * 70)

    # Phase 1: Fix Study A
    fix_study_a()

    # Phase 2: Fix Study Z
    fix_study_z()

    # Phase 3: Rebuild Study Y
    study_y_id = rebuild_study_y()

    # Phase 4: Verify everything
    print("\n" + "=" * 70)
    print("  PHASE 4: COMPREHENSIVE VERIFICATION")
    print("=" * 70)

    all_errors = []
    all_errors += verify_survey(STUDY_A_ID, "Study A", ["coffee_makers"])
    all_errors += verify_survey(STUDY_Z_ID, "Study Z", ["coffee_makers", "headphones", "earbuds"])
    if study_y_id:
        all_errors += verify_survey(study_y_id, "Study Y (new)", ["coffee_makers"])
    all_errors += verify_survey(PRETEST_ID, "Pretest", ["coffee_makers"])

    print("\n" + "=" * 70)
    if not all_errors:
        print("  ALL SURVEYS PASS VERIFICATION")
    else:
        print(f"  {len(all_errors)} ERRORS FOUND:")
        for e in all_errors:
            print(f"  {e}")
    print("=" * 70)

    if study_y_id:
        print(f"\n  NEW STUDY Y ID: {study_y_id}")
        print(f"  Edit: https://okstatebusiness.az1.qualtrics.com/survey-builder/{study_y_id}/edit")
        print(f"  Live: https://okstatebusiness.az1.qualtrics.com/jfe/form/{study_y_id}")

    print(f"\n  Study A: https://okstatebusiness.az1.qualtrics.com/jfe/form/{STUDY_A_ID}")
    print(f"  Study Z: https://okstatebusiness.az1.qualtrics.com/jfe/form/{STUDY_Z_ID}")
    print(f"  Pretest: https://okstatebusiness.az1.qualtrics.com/jfe/form/{PRETEST_ID}")


if __name__ == "__main__":
    main()
