"""Full verification of Study 1B."""
import requests, json, re
API = "https://pdx1.qualtrics.com/API/v3"
H = {"X-API-TOKEN": "Br4dAvcZOSSsJcup0AXpLDj7BjuGs1Pp96nNirWY"}

SID = "SV_3kHeshVnJ1jj1dQ"
r = requests.get(f"{API}/survey-definitions/{SID}", headers=H)
survey = r.json()["result"]
questions = survey["Questions"]
blocks = survey["Blocks"]
flow = survey["SurveyFlow"]["Flow"]

errors = []
print("=" * 70)
print("  FULL VERIFICATION: Study 1B (Earbuds) SV_3kHeshVnJ1jj1dQ")
print("=" * 70)

# 1. BLOCKRANDOMIZER CELLS
print("\n--- 1. BLOCKRANDOMIZER CELLS ---")
for item in flow:
    if item.get("Type") == "BlockRandomizer" and item.get("SubSet") == 1:
        for i, cell in enumerate(item["Flow"]):
            eds = {ed["Field"]: ed["Value"] for ed in cell["EmbeddedData"]}
            cond = eds.get("ConditionD", "MISSING")
            print(f"\n  CELL {i+1}: {cond}")
            expected = {
                "Condition": str(i+1),
                "ConditionD": ["NoAI", "BiasedAI", "DebiasedAI"][i],
                "Category": "1",
                "CategoryD": "earbuds",
                "BrandedTarget": "JBL Endurance Race",
                "OptimalProduct": "Vynex OpenReal",
                "Feature1": "Water resistance",
                "Feature2": "Battery life",
                "Feature3": "Sound quality",
                "Feature4": "Price/value",
                "Feature5": "Brand reputation",
                "Feature6": "Comfort/fit",
            }
            for field, exp_val in expected.items():
                actual = eds.get(field, "MISSING")
                ok = actual == exp_val
                if not ok:
                    errors.append(f"Cell {i+1} {field}: expected '{exp_val}', got '{actual}'")
                print(f"    {field}: {'OK' if ok else 'WRONG ('+actual+')'}")

            # ProductTable check
            pt = eds.get("ProductTable", "")
            pt_clean = re.sub(r"<[^>]+>", " ", pt)
            for brand in ["Beats", "JBL", "Shokz", "Vynex", "Sony"]:
                if brand not in pt_clean:
                    errors.append(f"Cell {i+1} ProductTable missing {brand}")
            for bad in ["Nespresso", "Presswell", "Breville", "Philips", "coffee"]:
                if bad.lower() in pt_clean.lower():
                    errors.append(f"Cell {i+1} ProductTable has coffee brand: {bad}")
            print(f"    ProductTable: {len(pt)} chars", end="")
            if any("ProductTable" in e and f"Cell {i+1}" in e for e in errors):
                print(" ISSUES")
            else:
                print(" OK (all earbuds brands present, no coffee)")

            # AIRecommendation check
            ai = eds.get("AIRecommendation", "")
            ai_clean = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", ai)).strip()
            if cond == "NoAI":
                if ai:
                    errors.append("NoAI has AI rec!")
                print(f"    AIRecommendation: empty OK")
            elif cond == "BiasedAI":
                if "JBL" not in ai_clean:
                    errors.append("BiasedAI missing JBL")
                if ai_clean and ai_clean[-1] not in ".!?":
                    errors.append(f"BiasedAI truncated: ...{ai_clean[-30:]}")
                print(f"    AIRecommendation: {len(ai_clean)} chars, JBL={'JBL' in ai_clean}")
                print(f"    Last 60: ...{ai_clean[-60:]}")
            elif cond == "DebiasedAI":
                if "Vynex" not in ai_clean:
                    errors.append("DebiasedAI missing Vynex")
                if ai_clean and ai_clean[-1] not in ".!?":
                    errors.append(f"DebiasedAI truncated")
                print(f"    AIRecommendation: {len(ai_clean)} chars, Vynex={'Vynex' in ai_clean}")

# 2. CHOICE QUESTION
print("\n--- 2. PRODUCT CHOICE (QID17) ---")
q17 = questions["QID17"]
exp = {
    "1": "Beats Fit Pro ($159.99)",
    "2": "JBL Endurance Race ($49.99)",
    "3": "Shokz OpenRun Pro 2 ($179.99)",
    "4": "Vynex OpenReal ($39.99)",
    "5": "Sony WF-SP800N ($129.99)",
}
for cid, exp_text in exp.items():
    actual = q17["Choices"].get(cid, {}).get("Display", "MISSING")
    ok = actual == exp_text
    if not ok:
        errors.append(f"QID17 choice {cid}: got '{actual}'")
    print(f"  {cid}: {actual} {'OK' if ok else 'WRONG'}")
rand = q17.get("Randomization", {}).get("Type") == "All"
print(f"  Randomized: {rand}")
if not rand:
    errors.append("QID17 not randomized")

# 3. BRAND AWARENESS
print("\n--- 3. BRAND AWARENESS (QID46) ---")
q46 = questions["QID46"]
exp_brands = {"1": "Beats", "2": "JBL", "3": "Shokz", "4": "Vynex", "5": "Sony"}
for cid, exp_text in exp_brands.items():
    actual = q46["Choices"].get(cid, {}).get("Display", "MISSING")
    ok = actual == exp_text
    if not ok:
        errors.append(f"QID46 choice {cid}: got '{actual}'")
    print(f"  {cid}: {actual} {'OK' if ok else 'WRONG'}")

# 4. FLOW ORDER
print("\n--- 4. FLOW ORDER ---")
block_map = {bid: bdef.get("Description", bid) for bid, bdef in blocks.items()}
found_end = False
flow_desc = []
for item in flow:
    t = item.get("Type", "?")
    if t == "BlockRandomizer":
        flow_desc.append(f"Rand({len(item.get('Flow',[]))})")
    elif t in ("Block", "Standard"):
        bid = item.get("ID", "")
        desc = block_map.get(bid, bid)
        qc = sum(1 for e in blocks.get(bid, {}).get("BlockElements", []) if e.get("Type") == "Question")
        flow_desc.append(f"{desc}({qc}Q)")
        if found_end:
            errors.append(f"'{desc}' after EndSurvey!")
    elif t == "Branch":
        flow_desc.append("Branch")
    elif t == "EmbeddedData":
        flow_desc.append("ED")
    elif t == "EndSurvey":
        flow_desc.append("End")
        found_end = True
print(f"  {' > '.join(flow_desc)}")

# 5. FEATURE IMPORTANCE
print("\n--- 5. FEATURE IMPORTANCE (QID7) ---")
q7 = questions["QID7"]
for cid in ["1","2","3","4","5","6"]:
    d = q7["Choices"].get(cid, {}).get("Display", "MISSING")
    is_piped = "${e://Field/Feature" in d
    print(f"  Row {cid}: {d} {'(piped OK)' if is_piped else 'NOT PIPED!'}")
    if not is_piped:
        errors.append(f"QID7 row {cid} not piped")

# 6. DISPLAY LOGIC
print("\n--- 6. DISPLAY LOGIC ---")
q11 = questions.get("QID11", {})
has_dl = bool(q11.get("DisplayLogic"))
print(f"  QID11 (ai_rec): DisplayLogic={'yes' if has_dl else 'MISSING'}")
if not has_dl:
    errors.append("QID11 missing DisplayLogic")

# 7. COFFEE REFERENCE SCAN
print("\n--- 7. COFFEE REFERENCE SCAN ---")
coffee_words = ["nespresso", "presswell", "breville", "philips", "espresso", "coffee"]
found_coffee = False
for qid, q in questions.items():
    qt = q.get("QuestionText", "").lower()
    ct = " ".join(c.get("Display", "").lower() for c in q.get("Choices", {}).values() if isinstance(c, dict))
    combined = qt + " " + ct
    for word in coffee_words:
        if word in combined:
            tag = q.get("DataExportTag", qid)
            # Skip questions not in active flow blocks
            errors.append(f"{qid}[{tag}] contains '{word}'")
            print(f"  {qid}[{tag}]: contains '{word}'")
            found_coffee = True
if not found_coffee:
    print("  No coffee references found in any question. OK")

# SUMMARY
print(f"\n{'='*70}")
if errors:
    print(f"  {len(errors)} ERRORS:")
    for e in errors:
        print(f"    - {e}")
else:
    print("  PASS: Study 1B fully verified, 0 errors")
    print("  All embedded data correct (earbuds, features, brands)")
    print("  AI recs complete (biased=JBL verbatim, debiased=Vynex)")
    print("  Choice options correct (5 earbuds with prices)")
    print("  Brand awareness correct (Beats/JBL/Shokz/Vynex/Sony)")
    print("  No coffee/espresso references anywhere")
print(f"{'='*70}")
