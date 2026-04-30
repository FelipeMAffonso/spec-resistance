"""Full verification + exploratory analyses for all running studies."""
import requests, json, time, io, zipfile, csv, math
from collections import Counter
from statistics import NormalDist

API = "https://pdx1.qualtrics.com/API/v3"
H = {"X-API-TOKEN": "Br4dAvcZOSSsJcup0AXpLDj7BjuGs1Pp96nNirWY", "Content-Type": "application/json"}

def download(sid):
    r = requests.post(f"{API}/surveys/{sid}/export-responses", headers=H, json={"format": "csv", "compress": True})
    pid = r.json()["result"]["progressId"]
    for _ in range(30):
        r = requests.get(f"{API}/surveys/{sid}/export-responses/{pid}", headers=H)
        if r.json()["result"]["status"] == "complete":
            fid = r.json()["result"]["fileId"]
            break
        time.sleep(1)
    r = requests.get(f"{API}/surveys/{sid}/export-responses/{fid}/file", headers=H)
    z = zipfile.ZipFile(io.BytesIO(r.content))
    csv_text = z.read(z.namelist()[0]).decode("utf-8-sig")
    rows = list(csv.reader(csv_text.strip().split("\n")))
    headers = rows[0]
    return headers, [{headers[i]: row[i] if i < len(row) else "" for i in range(len(headers))} for row in rows[3:]]

def chi2(a, b, c, d):
    n = a+b+c+d
    if n == 0 or min(a+b,c+d,a+c,b+d) == 0: return 0, 1
    stat = n*(a*d-b*c)**2/((a+b)*(c+d)*(a+c)*(b+d))
    p = 2*(1-NormalDist().cdf(math.sqrt(stat)))
    return stat, p

def analyze_study(name, sid, branded_val="2", optimal_val="4", product_names=None):
    if product_names is None:
        product_names = {"1": "P1", "2": "P2(branded)", "3": "P3", "4": "P4(optimal)", "5": "P5"}

    print(f"\n{'='*70}")
    print(f"  {name} ({sid})")
    print(f"{'='*70}")

    cols, data = download(sid)
    finished = [d for d in data if d.get("Finished") == "1"]
    print(f"  Raw: {len(data)}, Finished: {len(finished)}")

    conds = Counter(d.get("ConditionD") for d in finished)
    print(f"  Conditions: {dict(conds)}")

    # Cross-tab
    pnames = sorted(product_names.keys())
    header = f"  {'Condition':<25s}" + "".join(f"{product_names[p]:>12s}" for p in pnames) + f"{'N':>6s}"
    print(f"\n{header}")
    print("  " + "-" * (len(header)-2))
    for cond in sorted(conds.keys()):
        g = [d for d in finished if d.get("ConditionD") == cond]
        c = Counter(d.get("QID17") for d in g)
        row = f"  {cond:<25s}"
        for p in pnames:
            cnt = c.get(p, 0)
            pct = cnt/len(g)*100 if g else 0
            row += f"{cnt}({pct:.0f}%):>12s" if False else f"  {cnt:>3d}({pct:4.0f}%)"
        row += f"  {len(g):>4d}"
        print(row)

    # Exploratory: AI usage moderation
    print(f"\n  EXPLORATORY: AI usage frequency as moderator")
    for cond in sorted(conds.keys()):
        g = [d for d in finished if d.get("ConditionD") == cond]
        low = [d for d in g if d.get("ai_usage") in ("1", "2")]
        mid = [d for d in g if d.get("ai_usage") == "3"]
        high = [d for d in g if d.get("ai_usage") in ("4", "5")]
        def rate(grp, val):
            return sum(1 for d in grp if d.get("QID17") == val) / len(grp) * 100 if grp else 0
        print(f"    {cond:<25s}: Never/Rarely={rate(low, branded_val):.0f}%(n={len(low)})  Sometimes={rate(mid, branded_val):.0f}%(n={len(mid)})  Often/Always={rate(high, branded_val):.0f}%(n={len(high)})")

    # Exploratory: Brand importance (feature_importance_5)
    if "feature_importance_5" in cols:
        print(f"\n  EXPLORATORY: Brand reputation importance as moderator")
        for cond in sorted(conds.keys()):
            g = [d for d in finished if d.get("ConditionD") == cond]
            low_brand = [d for d in g if d.get("feature_importance_5") in ("1", "2", "3")]
            high_brand = [d for d in g if d.get("feature_importance_5") in ("5", "6", "7")]
            def rate(grp, val):
                return sum(1 for d in grp if d.get("QID17") == val) / len(grp) * 100 if grp else 0
            print(f"    {cond:<25s}: LowBrandImp={rate(low_brand, branded_val):.0f}%(n={len(low_brand)})  HighBrandImp={rate(high_brand, branded_val):.0f}%(n={len(high_brand)})")

    # Exploratory: Gender
    print(f"\n  EXPLORATORY: Gender")
    for cond in sorted(conds.keys()):
        g = [d for d in finished if d.get("ConditionD") == cond]
        for gen_val, gen_label in [("1", "Female"), ("2", "Male")]:
            gg = [d for d in g if d.get("gender") == gen_val]
            branded = sum(1 for d in gg if d.get("QID17") == branded_val)
            if gg:
                print(f"    {cond:<25s} {gen_label:<8s}: {branded}/{len(gg)} = {branded/len(gg)*100:.0f}%")

    # Fictional brand awareness
    fictional_col = "QID46_4"  # 4th brand in awareness matrix
    if fictional_col in cols:
        aw = Counter(d.get(fictional_col) for d in finished)
        print(f"\n  Fictional brand awareness: Own={aw.get('1',0)}, Heard={aw.get('2',0)}, Never={aw.get('3',0)}")

    return finished


# Run all studies
analyze_study(
    "STUDY 1A: Coffee Makers", "SV_01zhSyavcdjz06G",
    branded_val="2", optimal_val="4",
    product_names={"1": "Nespresso", "2": "DeLonghi*", "3": "Breville", "4": "Presswell**", "5": "Philips"}
)

analyze_study(
    "STUDY 1B: Earbuds", "SV_5hvy9y0CICi9lOe",
    branded_val="2", optimal_val="4",
    product_names={"1": "Beats", "2": "JBL*", "3": "Shokz", "4": "Vynex**", "5": "Sony"}
)

analyze_study(
    "STUDY 2: Inoculation (Earbuds)", "SV_3PHq8N243mxAr0W",
    branded_val="2", optimal_val="4",
    product_names={"1": "Beats", "2": "JBL*", "3": "Shokz", "4": "Vynex**", "5": "Sony"}
)

print(f"\n{'='*70}")
print("  VERIFICATION + EXPLORATORY COMPLETE")
print(f"{'='*70}")
