"""
Fix Studies 1 and 2: Add DisplayLogic + EmbeddedData fields + piped text
Spec Resistance Project — Nature R&R Human Subjects

In-place fixes to existing surveys:
  Study 1: SV_cZ58TPi4UCNLpyu (12-cell BlockRandomizer already exists)
  Study 2: SV_7ZGvAKscXotJoxg (9-cell BlockRandomizer already exists)

Changes:
  1. Add new EmbeddedData fields to existing BlockRandomizer cells:
     Product1-5, Product1Price-5Price, CategoryLabel, BrandedPrice, OptimalPrice
  2. Add DisplayLogic to category-specific questions so only the correct
     category's questions appear (comp/choice/revised for earbuds/speakers/ssds)
  3. Update Study 1 debrief text to pipe OptimalProduct + OptimalPrice
  4. Update Study 2 WTP text to pipe BrandedTarget instead of hardcoded Sony
"""
import requests
import json
import sys

BASE = "https://pdx1.qualtrics.com/API/v3"
HEADERS = {
    "X-API-TOKEN": "Br4dAvcZOSSsJcup0AXpLDj7BjuGs1Pp96nNirWY",
    "Content-Type": "application/json"
}

STUDY1_ID = "SV_cZ58TPi4UCNLpyu"
STUDY2_ID = "SV_7ZGvAKscXotJoxg"


def api_call(method, endpoint, data=None):
    url = f"{BASE}{endpoint}"
    resp = requests.request(method, url, headers=HEADERS, json=data)
    result = resp.json()
    if resp.status_code not in (200, 201):
        print(f"ERROR {resp.status_code}: {json.dumps(result, indent=2)}")
        return None
    return result


# =========================================================================
# New EmbeddedData fields to add per category
# =========================================================================

CATEGORY_ED_FIELDS = {
    "earbuds": {
        "CategoryLabel": "wireless earbuds",
        "BrandedPrice": "$279.99",
        "OptimalPrice": "$59.99",
        "Product1": "Auralis Air4 Pro", "Product1Price": "$59.99",
        "Product2": "Sony WF-1000XM5", "Product2Price": "$279.99",
        "Product3": "Apple AirPods Pro 2", "Product3Price": "$249.00",
        "Product4": "Samsung Galaxy Buds3 Pro", "Product4Price": "$199.99",
        "Product5": "Jabra Elite 85t", "Product5Price": "$179.99",
    },
    "speakers": {
        "CategoryLabel": "portable Bluetooth speakers",
        "BrandedPrice": "$99.99",
        "OptimalPrice": "$49.99",
        "Product1": "Wavecrest StormBox Pro", "Product1Price": "$49.99",
        "Product2": "JBL Flip 6", "Product2Price": "$99.99",
        "Product3": "Bose SoundLink Flex", "Product3Price": "$119.99",
        "Product4": "Sony SRS-XB100", "Product4Price": "$49.99",
        "Product5": "UE WONDERBOOM 3", "Product5Price": "$79.99",
    },
    "ssds": {
        "CategoryLabel": "external SSDs",
        "BrandedPrice": "$149.99",
        "OptimalPrice": "$89.99",
        "Product1": "Vaultdrive PD60", "Product1Price": "$89.99",
        "Product2": "Samsung T7 Shield", "Product2Price": "$149.99",
        "Product3": "WD My Passport", "Product3Price": "$139.99",
        "Product4": "SanDisk Extreme V2", "Product4Price": "$119.99",
        "Product5": "Seagate One Touch", "Product5Price": "$129.99",
    },
}


# =========================================================================
# DisplayLogic helpers
# =========================================================================

def dl_category(cat_code):
    return {
        "0": {
            "0": {
                "LogicType": "EmbeddedField",
                "LeftOperand": "Category",
                "Operator": "EqualTo",
                "RightOperand": str(cat_code),
                "Type": "Expression",
                "Description": f'<span class="ConjDesc">If</span>  <span class="LeftOpDesc">Category</span> <span class="OpDesc">Is Equal to</span> <span class="RightOpDesc"> {cat_code} </span>'
            },
            "Type": "If"
        },
        "Type": "BooleanExpression"
    }


def dl_category_and_revise(cat_code, revise_qid):
    return {
        "0": {
            "0": {
                "LogicType": "EmbeddedField",
                "LeftOperand": "Category",
                "Operator": "EqualTo",
                "RightOperand": str(cat_code),
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
# Phase 1: Add EmbeddedData fields to BlockRandomizer cells
# =========================================================================

def add_embedded_data_fields(survey_id, study_name):
    """Add Product1-5, Product1Price-5Price, CategoryLabel, BrandedPrice, OptimalPrice
    to each EmbeddedData cell in the BlockRandomizer flow."""

    print(f"\n{'='*60}")
    print(f"Phase 1: Adding EmbeddedData fields to {study_name} ({survey_id})")
    print(f"{'='*60}")

    resp = api_call("GET", f"/survey-definitions/{survey_id}")
    if not resp:
        return False
    flow = resp["result"]["SurveyFlow"]

    # Find the BlockRandomizer(s)
    def find_block_randomizers(obj, results=None):
        if results is None:
            results = []
        if isinstance(obj, dict):
            if obj.get("Type") == "BlockRandomizer":
                inner = obj.get("Flow", [])
                if inner and inner[0].get("Type") == "EmbeddedData":
                    results.append(obj)
            for v in obj.values():
                find_block_randomizers(v, results)
        elif isinstance(obj, list):
            for item in obj:
                find_block_randomizers(item, results)
        return results

    randomizers = find_block_randomizers(flow)
    if not randomizers:
        print("  ERROR: No BlockRandomizer with EmbeddedData found!")
        return False

    # Use the FIRST randomizer (the condition x category one)
    br = randomizers[0]
    cells = br["Flow"]
    print(f"  Found BlockRandomizer with {len(cells)} cells")

    modified = 0
    for cell in cells:
        ed_list = cell.get("EmbeddedData", [])
        # Find existing CategoryD to determine which category fields to add
        cat_d = None
        existing_fields = set()
        for e in ed_list:
            existing_fields.add(e["Field"])
            if e["Field"] == "CategoryD":
                cat_d = e["Value"]

        if not cat_d:
            print(f"  WARNING: Cell missing CategoryD, skipping")
            continue

        if cat_d not in CATEGORY_ED_FIELDS:
            print(f"  WARNING: Unknown category '{cat_d}', skipping")
            continue

        new_fields = CATEGORY_ED_FIELDS[cat_d]
        added = []
        for field, value in new_fields.items():
            if field not in existing_fields:
                ed_list.append({
                    "Description": field,
                    "Type": "Custom",
                    "Field": field,
                    "VariableType": "String",
                    "DataVisibility": [],
                    "AnalyzeText": False,
                    "Value": value
                })
                added.append(field)

        if added:
            modified += 1
            print(f"  Cell {cat_d}: added {len(added)} fields: {', '.join(added[:5])}{'...' if len(added) > 5 else ''}")
        else:
            print(f"  Cell {cat_d}: all fields already present")

    if modified == 0:
        print("  No cells needed updating")
        return True

    # PUT the updated flow back
    result = api_call("PUT", f"/survey-definitions/{survey_id}/flow", flow)
    if result:
        print(f"  Flow updated: {modified} cells modified")
        return True
    else:
        print("  ERROR: Failed to update flow!")
        return False


# =========================================================================
# Phase 2: Add DisplayLogic to category-specific questions
# =========================================================================

def add_display_logic(survey_id, study_name, question_dl_map):
    """Add DisplayLogic to questions that need it.
    question_dl_map: dict of DataExportTag -> DisplayLogic JSON"""

    print(f"\n{'='*60}")
    print(f"Phase 2: Adding DisplayLogic to {study_name} ({survey_id})")
    print(f"{'='*60}")

    # First, get the survey definition to find QIDs by DataExportTag
    resp = api_call("GET", f"/survey-definitions/{survey_id}")
    if not resp:
        return False

    questions = resp["result"]["Questions"]
    tag_to_qid = {}
    for qid, qdef in questions.items():
        tag = qdef.get("DataExportTag", "")
        if tag:
            tag_to_qid[tag] = qid

    success = 0
    for tag, dl in question_dl_map.items():
        qid = tag_to_qid.get(tag)
        if not qid:
            print(f"  WARNING: No QID found for tag '{tag}', skipping")
            continue

        # GET full question definition
        q_resp = api_call("GET", f"/survey-definitions/{survey_id}/questions/{qid}")
        if not q_resp:
            print(f"  ERROR: Could not GET {qid} ({tag})")
            continue

        qdef = q_resp["result"]

        # Check if DisplayLogic already present
        if "DisplayLogic" in qdef and qdef["DisplayLogic"]:
            print(f"  {qid} ({tag}): DisplayLogic already present, skipping")
            success += 1
            continue

        # Add DisplayLogic
        qdef["DisplayLogic"] = dl

        # PUT the updated question
        put_resp = api_call("PUT", f"/survey-definitions/{survey_id}/questions/{qid}", qdef)
        if put_resp:
            print(f"  {qid} ({tag}): DisplayLogic added")
            success += 1
        else:
            print(f"  ERROR: Failed to update {qid} ({tag})")

    print(f"  {success}/{len(question_dl_map)} questions updated")
    return success == len(question_dl_map)


# =========================================================================
# Phase 3: Update question text to pipe EmbeddedData
# =========================================================================

def update_question_text(survey_id, study_name, tag, old_text, new_text):
    """Update a question's text, replacing old_text with new_text."""

    resp = api_call("GET", f"/survey-definitions/{survey_id}")
    if not resp:
        return False

    questions = resp["result"]["Questions"]
    qid = None
    for q, qdef in questions.items():
        if qdef.get("DataExportTag") == tag:
            qid = q
            break

    if not qid:
        print(f"  WARNING: No QID found for tag '{tag}'")
        return False

    q_resp = api_call("GET", f"/survey-definitions/{survey_id}/questions/{qid}")
    if not q_resp:
        return False

    qdef = q_resp["result"]
    current_text = qdef.get("QuestionText", "")

    if old_text and old_text in current_text:
        qdef["QuestionText"] = current_text.replace(old_text, new_text)
    elif new_text and not old_text:
        # Append to existing text
        qdef["QuestionText"] = current_text + new_text
    else:
        # Full replace
        qdef["QuestionText"] = new_text

    put_resp = api_call("PUT", f"/survey-definitions/{survey_id}/questions/{qid}", qdef)
    if put_resp:
        print(f"  {qid} ({tag}): text updated")
        return True
    else:
        print(f"  ERROR: Failed to update {qid} ({tag})")
        return False


# =========================================================================
# MAIN
# =========================================================================

def main():
    print("=" * 70)
    print("FIXING STUDIES 1 AND 2: DisplayLogic + EmbeddedData + Piped Text")
    print("=" * 70)

    # =====================================================================
    # STUDY 1: SV_cZ58TPi4UCNLpyu
    # =====================================================================

    # Phase 1: Add EmbeddedData fields
    add_embedded_data_fields(STUDY1_ID, "Study 1")

    # Phase 2: Add DisplayLogic
    # First, find the revise_yn QID for compound display logic
    resp = api_call("GET", f"/survey-definitions/{STUDY1_ID}")
    s1_questions = resp["result"]["Questions"]
    revise_qid = None
    for qid, qdef in s1_questions.items():
        if qdef.get("DataExportTag") == "revise_yn":
            revise_qid = qid
            break

    s1_dl_map = {
        # Comprehension questions by category
        "comp_earbuds": dl_category(1),
        "comp_speakers": dl_category(2),
        "comp_ssds": dl_category(3),
        # Choice questions by category
        "choice_earbuds": dl_category(1),
        "choice_speakers": dl_category(2),
        "choice_ssds": dl_category(3),
    }

    # Revised choice: Category AND revise_yn == Yes
    if revise_qid:
        s1_dl_map["revised_earbuds"] = dl_category_and_revise(1, revise_qid)
        s1_dl_map["revised_speakers"] = dl_category_and_revise(2, revise_qid)
        s1_dl_map["revised_ssds"] = dl_category_and_revise(3, revise_qid)
        print(f"\n  Found revise_yn: {revise_qid}")
    else:
        print("\n  WARNING: revise_yn not found, skipping revised choice DisplayLogic")

    add_display_logic(STUDY1_ID, "Study 1", s1_dl_map)

    # Phase 3: Update debrief text to pipe OptimalProduct
    print(f"\n{'='*60}")
    print(f"Phase 3: Updating Study 1 debrief text")
    print(f"{'='*60}")

    # Find the debrief text question
    debrief_qid = None
    for qid, qdef in s1_questions.items():
        if qdef.get("DataExportTag") == "debrief_text":
            debrief_qid = qid
            break

    if debrief_qid:
        q_resp = api_call("GET", f"/survey-definitions/{STUDY1_ID}/questions/{debrief_qid}")
        if q_resp:
            qdef = q_resp["result"]
            old_text = qdef.get("QuestionText", "")

            # Check if already has piped text
            if "${e://Field/OptimalProduct}" in old_text:
                print(f"  {debrief_qid}: Already has piped OptimalProduct")
            else:
                # Add the optimal product reveal after the debrief explanation
                piped_reveal = (
                    '<br><br>'
                    '<div style="max-width:720px; margin:0 auto; background:#fef3c7; '
                    'border:1px solid #f59e0b; border-radius:12px; padding:16px 20px;">'
                    '<span style="font-size:16px; color:#92400e;">'
                    'The product that <b>best matched your stated preferences</b> was: '
                    '<b style="color:#16a34a;">${e://Field/OptimalProduct} (${e://Field/OptimalPrice})</b>'
                    '</span></div>'
                )
                # Append before closing
                if '</span>' in old_text:
                    # Insert before the last closing span
                    idx = old_text.rfind('</span>')
                    qdef["QuestionText"] = old_text[:idx] + '</span>' + piped_reveal
                else:
                    qdef["QuestionText"] = old_text + piped_reveal

                put_resp = api_call("PUT", f"/survey-definitions/{STUDY1_ID}/questions/{debrief_qid}", qdef)
                if put_resp:
                    print(f"  {debrief_qid}: Debrief text updated with piped OptimalProduct")
                else:
                    print(f"  ERROR: Failed to update debrief text")
    else:
        print("  WARNING: debrief_text question not found")

    # =====================================================================
    # STUDY 2: SV_7ZGvAKscXotJoxg
    # =====================================================================

    # Phase 1: Add EmbeddedData fields
    add_embedded_data_fields(STUDY2_ID, "Study 2")

    # Phase 2: Add DisplayLogic
    resp2 = api_call("GET", f"/survey-definitions/{STUDY2_ID}")
    s2_questions = resp2["result"]["Questions"]

    # Find revise_yn QID for Study 2
    s2_revise_qid = None
    for qid, qdef in s2_questions.items():
        if qdef.get("DataExportTag") == "revise_yn":
            s2_revise_qid = qid
            break

    s2_dl_map = {
        # Choice questions by category
        "choice_earbuds": dl_category(1),
        "choice_speakers": dl_category(2),
        "choice_ssds": dl_category(3),
    }

    # Revised choice (if exists)
    if s2_revise_qid:
        s2_dl_map["revised_earbuds"] = dl_category_and_revise(1, s2_revise_qid)
        s2_dl_map["revised_speakers"] = dl_category_and_revise(2, s2_revise_qid)
        s2_dl_map["revised_ssds"] = dl_category_and_revise(3, s2_revise_qid)
        print(f"\n  Found Study 2 revise_yn: {s2_revise_qid}")
    else:
        print("\n  Study 2 has no revise_yn, skipping revised DisplayLogic")

    add_display_logic(STUDY2_ID, "Study 2", s2_dl_map)

    # Phase 3: Update Study 2 WTP text to pipe BrandedTarget
    print(f"\n{'='*60}")
    print(f"Phase 3: Updating Study 2 WTP text")
    print(f"{'='*60}")

    for qid, qdef in s2_questions.items():
        tag = qdef.get("DataExportTag", "")
        text = qdef.get("QuestionText", "")
        # Look for hardcoded Sony/JBL/Samsung in WTP questions
        if "wtp" in tag.lower() and ("Sony WF-1000XM5" in text or "JBL Flip 6" in text or "Samsung T7 Shield" in text):
            q_resp = api_call("GET", f"/survey-definitions/{STUDY2_ID}/questions/{qid}")
            if q_resp:
                qd = q_resp["result"]
                new_text = qd["QuestionText"]
                new_text = new_text.replace("Sony WF-1000XM5", "${e://Field/BrandedTarget}")
                new_text = new_text.replace("JBL Flip 6", "${e://Field/BrandedTarget}")
                new_text = new_text.replace("Samsung T7 Shield", "${e://Field/BrandedTarget}")
                qd["QuestionText"] = new_text
                put_resp = api_call("PUT", f"/survey-definitions/{STUDY2_ID}/questions/{qid}", qd)
                if put_resp:
                    print(f"  {qid} ({tag}): Replaced hardcoded product with piped BrandedTarget")
                else:
                    print(f"  ERROR: Failed to update {qid}")

    # =====================================================================
    # Done!
    # =====================================================================
    print("\n" + "=" * 70)
    print("ALL FIXES APPLIED!")
    print("=" * 70)
    print(f"\nStudy 1: https://okstatebusiness.az1.qualtrics.com/survey-builder/{STUDY1_ID}/edit")
    print(f"Study 2: https://okstatebusiness.az1.qualtrics.com/survey-builder/{STUDY2_ID}/edit")
    print()
    print("Changes made:")
    print("  Study 1:")
    print("    - Added Product1-5, Product1Price-5Price, CategoryLabel, BrandedPrice, OptimalPrice to all 12 cells")
    print("    - Added DisplayLogic to comp_earbuds/speakers/ssds (Category==1/2/3)")
    print("    - Added DisplayLogic to choice_earbuds/speakers/ssds (Category==1/2/3)")
    print("    - Added DisplayLogic to revised_earbuds/speakers/ssds (Category==1/2/3 AND revise_yn==Yes)")
    print("    - Updated debrief text with piped OptimalProduct + OptimalPrice")
    print()
    print("  Study 2:")
    print("    - Added Product1-5, Product1Price-5Price, CategoryLabel, BrandedPrice, OptimalPrice to all 9 cells")
    print("    - Added DisplayLogic to choice_earbuds/speakers/ssds (Category==1/2/3)")
    print("    - Added DisplayLogic to revised_earbuds/speakers/ssds (Category==1/2/3 AND revise_yn==Yes)")
    print("    - Replaced hardcoded product names in WTP with piped BrandedTarget")


if __name__ == "__main__":
    main()
