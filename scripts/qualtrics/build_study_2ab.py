"""
Build Study 2A (coffee, inoculation) and Study 2B (earbuds, inoculation).
Copies of 1A/1B with 3 conditions each:
  1. BiasedAI (no warning — replicates Study 1 BiasedAI)
  2. BiasedAI + Inoculation ("21% of the time AI recommends brands over better products")
  3. BiasedAI + Confabulation Exposed (directly shows what the AI got wrong vs actual specs)
"""
import requests, json, re

API = "https://pdx1.qualtrics.com/API/v3"
H = {"X-API-TOKEN": "Br4dAvcZOSSsJcup0AXpLDj7BjuGs1Pp96nNirWY", "Content-Type": "application/json"}

STUDY_1A = "SV_cx2kueJwMOwdDj8"
STUDY_1B = "SV_3kHeshVnJ1jj1dQ"

# ============================================================
# INOCULATION TEXTS
# ============================================================

INOCULATION_TEXT = (
    '<div style="background:#fff3cd;border:1px solid #ffc107;border-radius:8px;'
    'padding:12px 16px;margin-top:12px;font-size:13px">'
    '<strong>Note:</strong> In independent testing across 382,000 recommendations, '
    'AI shopping assistants recommended well-known brands over better-value alternatives '
    '21% of the time, even when the alternative had superior specifications on every '
    'measurable dimension.</div>'
)

# Coffee makers: AI says De'Longhi is best, but Presswell has wider pressure range at lower price
# The confabulation: AI says "genuine 15-bar pump-driven espresso experience" but Presswell has 2-15 bar full profiling
CONFAB_EXPOSED_COFFEE = (
    '<div style="background:#f8d7da;border:1px solid #f5c2c7;border-radius:8px;'
    'padding:12px 16px;margin-top:12px;font-size:13px">'
    '<strong>Specification check:</strong><br>'
    '<table style="width:100%;font-size:13px;margin-top:8px">'
    '<tr><td></td><td style="font-weight:bold;padding:4px">De\'Longhi Stilosa</td>'
    '<td style="font-weight:bold;padding:4px">Presswell NEO Flex</td></tr>'
    '<tr><td style="padding:4px">Price</td><td style="padding:4px">$119.99</td>'
    '<td style="padding:4px;color:#0a7c0a;font-weight:bold">$99.99</td></tr>'
    '<tr><td style="padding:4px">Pressure</td><td style="padding:4px">15 bar (fixed)</td>'
    '<td style="padding:4px;color:#0a7c0a;font-weight:bold">2-15 bar (full manual profiling)</td></tr>'
    '<tr><td style="padding:4px">Milk</td>'
    '<td style="padding:4px;color:#0a7c0a;font-weight:bold">Manual wand</td>'
    '<td style="padding:4px">None</td></tr>'
    '<tr><td style="padding:4px">Type</td><td style="padding:4px">Semi-auto (electric)</td>'
    '<td style="padding:4px">Manual lever (no electricity)</td></tr>'
    '</table>'
    'The AI recommended De\'Longhi. Compare the specifications above and decide for yourself.</div>'
)

# Earbuds: AI says JBL has "superior waterproof protection" but Vynex has IPX8 > IP67
CONFAB_EXPOSED_EARBUDS = (
    '<div style="background:#f8d7da;border:1px solid #f5c2c7;border-radius:8px;'
    'padding:12px 16px;margin-top:12px;font-size:13px">'
    '<strong>Specification check:</strong><br>'
    '<table style="width:100%;font-size:13px;margin-top:8px">'
    '<tr><td></td><td style="font-weight:bold;padding:4px">JBL Endurance Race</td>'
    '<td style="font-weight:bold;padding:4px">Vynex OpenReal</td></tr>'
    '<tr><td style="padding:4px">Water resistance</td><td style="padding:4px">IP67 (splash)</td>'
    '<td style="padding:4px;color:#0a7c0a;font-weight:bold">IPX8 (full submersion)</td></tr>'
    '<tr><td style="padding:4px">Battery</td><td style="padding:4px">10h (30h case)</td>'
    '<td style="padding:4px;color:#0a7c0a;font-weight:bold">14h (48h case)</td></tr>'
    '<tr><td style="padding:4px">Price</td><td style="padding:4px">$49.99</td>'
    '<td style="padding:4px;color:#0a7c0a;font-weight:bold">$39.99</td></tr>'
    '<tr><td style="padding:4px">Fit</td><td style="padding:4px">TwistLock</td>'
    '<td style="padding:4px">Ear-hook open</td></tr>'
    '</table>'
    'The AI recommended JBL, citing "superior waterproof protection." '
    'Compare the actual specifications above and decide for yourself.</div>'
)


def make_ed(field, value):
    return {"Description": field, "Type": "Custom", "Field": field,
            "VariableType": "String", "DataVisibility": [], "AnalyzeText": False,
            "Value": value}


def build_study_2(source_sid, study_name, confab_exposed_html):
    """Copy a Study 1, modify to 3 inoculation conditions."""
    print(f"\n{'='*60}")
    print(f"  Building {study_name}")
    print(f"{'='*60}")

    # Step 1: Copy
    print("  Copying source survey...")
    copy_h = {**H, "X-COPY-SOURCE": source_sid, "X-COPY-DESTINATION-OWNER": "UR_9GiLKDSXylBFeYu"}
    r = requests.post(f"{API}/surveys", headers=copy_h, json={})
    assert r.status_code in (200, 201), f"COPY FAILED: {r.status_code} {r.text[:300]}"
    new_sid = r.json()["result"].get("id") or r.json()["result"].get("SurveyID")
    print(f"  Created: {new_sid}")

    # Rename
    requests.put(f"{API}/survey-definitions/{new_sid}/metadata", headers=H,
                 json={"SurveyName": f"SR {study_name} (2026-04-16)"})

    # Step 2: Get survey, extract biased AI rec and base embedded data
    r = requests.get(f"{API}/survey-definitions/{new_sid}", headers=H)
    survey = r.json()["result"]
    flow = survey["SurveyFlow"]

    biased_rec = ""
    base_eds_list = []
    for item in flow["Flow"]:
        if item.get("Type") == "BlockRandomizer" and item.get("SubSet") == 1:
            for cell in item["Flow"]:
                if cell.get("Type") == "EmbeddedData":
                    eds = {ed["Field"]: ed["Value"] for ed in cell["EmbeddedData"]}
                    if eds.get("ConditionD") == "BiasedAI" and eds.get("AIRecommendation"):
                        biased_rec = eds["AIRecommendation"]
                        # Collect all non-condition, non-AI fields
                        for ed in cell["EmbeddedData"]:
                            if ed["Field"] not in ("Condition", "ConditionD", "AIRecommendation", "DisclosureText", "InoculationText"):
                                base_eds_list.append(make_ed(ed["Field"], ed["Value"]))
                        break
            break

    assert biased_rec, "Could not find biased AI rec in source survey!"
    print(f"  Found biased AI rec: {len(biased_rec)} chars")

    # Step 3: Build 3 inoculation cells
    cells = [
        # Cell 1: BiasedAI, no warning (replication of Study 1)
        {"Type": "EmbeddedData", "FlowID": "FL_I1", "EmbeddedData": [
            make_ed("Condition", "1"),
            make_ed("ConditionD", "BiasedAI"),
            make_ed("AIRecommendation", biased_rec),
            make_ed("InoculationText", ""),
        ] + base_eds_list},
        # Cell 2: BiasedAI + statistical inoculation
        {"Type": "EmbeddedData", "FlowID": "FL_I2", "EmbeddedData": [
            make_ed("Condition", "2"),
            make_ed("ConditionD", "BiasedAI_Inoculation"),
            make_ed("AIRecommendation", biased_rec),
            make_ed("InoculationText", INOCULATION_TEXT),
        ] + base_eds_list},
        # Cell 3: BiasedAI + confabulation exposed
        {"Type": "EmbeddedData", "FlowID": "FL_I3", "EmbeddedData": [
            make_ed("Condition", "3"),
            make_ed("ConditionD", "BiasedAI_SpecExposed"),
            make_ed("AIRecommendation", biased_rec),
            make_ed("InoculationText", confab_exposed_html),
        ] + base_eds_list},
    ]

    # Replace BlockRandomizer
    for item in flow["Flow"]:
        if item.get("Type") == "BlockRandomizer" and item.get("SubSet") == 1:
            item["Flow"] = cells
            break

    r = requests.put(f"{API}/survey-definitions/{new_sid}/flow", headers=H, json=flow)
    print(f"  Flow update: {r.status_code}")

    # Step 4: Create inoculation display question (piped from InoculationText)
    result = requests.post(f"{API}/survey-definitions/{new_sid}/questions", headers=H, json={
        "QuestionText": "${e://Field/InoculationText}",
        "QuestionType": "DB",
        "Selector": "TB",
        "DataExportTag": "inoculation_display",
        "Language": [],
        "DisplayLogic": {
            "0": {
                "0": {
                    "LogicType": "EmbeddedField",
                    "LeftOperand": "Condition",
                    "Operator": "GreaterThan",
                    "RightOperand": "1",
                    "Type": "Expression",
                    "Description": "Show only for inoculation conditions (2, 3)"
                },
                "Type": "If"
            },
            "Type": "BooleanExpression"
        }
    }).json().get("result", {})
    inoc_qid = result.get("QuestionID")
    print(f"  Created inoculation_display: {inoc_qid}")

    # Step 5: Add inoculation question to stimulus block (after AI rec)
    r = requests.get(f"{API}/survey-definitions/{new_sid}", headers=H)
    survey = r.json()["result"]
    blocks = survey["Blocks"]
    block_map = {bdef.get("Description", bid): bid for bid, bdef in blocks.items()}

    stim_bid = block_map.get("stimulus")
    if stim_bid and inoc_qid:
        bdef = blocks[stim_bid]
        elements = bdef.get("BlockElements", [])
        new_elements = []
        for e in elements:
            new_elements.append(e)
            if e.get("Type") == "Question" and e.get("QuestionID") == "QID11":
                new_elements.append({"Type": "Question", "QuestionID": inoc_qid})
        payload = {
            "Type": "Standard", "Description": "stimulus",
            "BlockElements": new_elements,
            "Options": bdef.get("Options", {}),
        }
        requests.put(f"{API}/survey-definitions/{new_sid}/blocks/{stim_bid}", headers=H, json=payload)
        print(f"  Added inoculation_display to stimulus block after AI rec")

    # Step 6: Remove DisplayLogic from AI rec (all 3 conditions see AI rec)
    q11 = requests.get(f"{API}/survey-definitions/{new_sid}/questions/QID11", headers=H).json()["result"]
    if q11.get("DisplayLogic"):
        del q11["DisplayLogic"]
        for k in ["QuestionID", "DataExportTag", "NextChoiceId", "NextAnswerId"]:
            q11.pop(k, None)
        requests.put(f"{API}/survey-definitions/{new_sid}/questions/QID11", headers=H, json=q11)
        print(f"  Removed DisplayLogic from QID11 (all conditions see AI rec)")

    # Step 7: Activate
    r = requests.put(f"{API}/surveys/{new_sid}", headers=H, json={"isActive": True})
    print(f"  Activated: {r.status_code}")

    # Step 8: Verify
    print(f"\n  VERIFICATION:")
    r = requests.get(f"{API}/survey-definitions/{new_sid}", headers=H)
    survey = r.json()["result"]
    errors = []

    for item in survey["SurveyFlow"]["Flow"]:
        if item.get("Type") == "BlockRandomizer" and item.get("SubSet") == 1:
            for i, cell in enumerate(item["Flow"]):
                eds = {ed["Field"]: ed["Value"] for ed in cell["EmbeddedData"]}
                cond = eds.get("ConditionD", "?")
                ai = eds.get("AIRecommendation", "")
                inoc = eds.get("InoculationText", "")
                ai_clean = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", ai)).strip()
                inoc_clean = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", inoc)).strip()
                print(f"    Cell {i+1}: {cond} | AI={len(ai_clean)}ch | Inoc={len(inoc_clean)}ch")
                if not ai:
                    errors.append(f"Cell {i+1} has no AI rec!")
                if i > 0 and not inoc:
                    errors.append(f"Cell {i+1} ({cond}) has no inoculation text!")

    # Check that QID11 has no DisplayLogic
    q11_check = survey["Questions"].get("QID11", {})
    if q11_check.get("DisplayLogic"):
        errors.append("QID11 still has DisplayLogic (should show for all conditions)")

    if errors:
        print(f"    ERRORS: {errors}")
    else:
        print(f"    PASS: 0 errors")

    print(f"\n  {study_name}: {new_sid}")
    print(f"  Edit: https://okstatebusiness.az1.qualtrics.com/survey-builder/{new_sid}/edit")
    print(f"  Live: https://okstatebusiness.az1.qualtrics.com/jfe/form/{new_sid}")
    return new_sid


# ============================================================
# BUILD BOTH
# ============================================================
sid_2a = build_study_2(STUDY_1A, "Study 2A - Inoculation Coffee", CONFAB_EXPOSED_COFFEE)
sid_2b = build_study_2(STUDY_1B, "Study 2B - Inoculation Earbuds", CONFAB_EXPOSED_EARBUDS)

print(f"\n{'='*60}")
print(f"  SUMMARY")
print(f"{'='*60}")
print(f"  Study 2A (coffee):  {sid_2a}")
print(f"  Study 2B (earbuds): {sid_2b}")
print(f"  Both have 3 conditions: BiasedAI | BiasedAI+Inoculation | BiasedAI+SpecExposed")
print(f"  All conditions show biased AI rec. Variation = what mitigation info they get.")
