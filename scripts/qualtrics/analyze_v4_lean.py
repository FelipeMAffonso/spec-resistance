"""
analyze_v4_lean.py — Single-click analysis for all V4 lean surveys.

Downloads data from Qualtrics, runs all pre-registered tests, prints results.

Usage:
  python analyze_v4_lean.py              # download from Qualtrics API and analyze
  python analyze_v4_lean.py data.csv     # analyze a local CSV file (Study A)

Column mapping (from Qualtrics export):
  QID17         = product_choice (1=Nespresso, 2=De'Longhi, 3=Breville, 4=Presswell, 5=Philips)
  QID46_1..5    = brand_awareness per brand (1=own, 2=heard, 3=never)
  Condition     = 1/2/3 (Study A), 1-5 (Study Y), 1-6 (Study Z)
  ConditionD    = NoAI/BiasedAI/DebiasedAI (A), NoAI/AI_NoDis/AI_Generic/AI_Mechanism/AI_Quantified (Y)
  CategoryD     = coffee_makers (A/Y), coffee makers/headphones/wireless earbuds (Z)
"""
import sys, csv, io, time, zipfile, json
from collections import Counter

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

API = "https://pdx1.qualtrics.com/API/v3"
TOKEN = "Br4dAvcZOSSsJcup0AXpLDj7BjuGs1Pp96nNirWY"
H = {"X-API-TOKEN": TOKEN, "Content-Type": "application/json"}

SURVEYS = {
    "Study A": "SV_cx2kueJwMOwdDj8",
    "Study Y": "SV_bNw4PVjCLsVGoMm",
    "Study Z": "SV_esVf052AlAoqBiS",
    "Pretest": "SV_bOyHko6mpqtn4mq",
}

# Product choice coding (coffee_makers_02)
# QID17: 1=Nespresso, 2=De'Longhi(BRANDED), 3=Breville, 4=Presswell(OPTIMAL), 5=Philips
COFFEE_BRANDED = "2"
COFFEE_OPTIMAL = "4"

# Study Z: QID17(coffee,Cat=1), QID18(headphones,Cat=2), QID19(earbuds,Cat=3)
# Headphones: 1=Sony, 2=A-T, 3=Arcwave(OPT), 4=Beyerdynamic(BRANDED), 5=Bose
HEADPHONE_BRANDED = "4"
HEADPHONE_OPTIMAL = "3"
# Earbuds: 1=Beats, 2=JBL(BRANDED), 3=Shokz, 4=Vynex(OPT), 5=Sony
EARBUDS_BRANDED = "2"
EARBUDS_OPTIMAL = "4"


def export_from_qualtrics(sid):
    """Download CSV from Qualtrics API."""
    r = requests.post(f"{API}/surveys/{sid}/export-responses", headers=H,
                      json={"format": "csv", "compress": True})
    pid = r.json()["result"]["progressId"]
    for _ in range(30):
        r = requests.get(f"{API}/surveys/{sid}/export-responses/{pid}", headers=H)
        if r.json()["result"]["status"] == "complete":
            fid = r.json()["result"]["fileId"]
            break
        time.sleep(1)
    else:
        return None
    r = requests.get(f"{API}/surveys/{sid}/export-responses/{fid}/file", headers=H)
    z = zipfile.ZipFile(io.BytesIO(r.content))
    return z.read(z.namelist()[0]).decode("utf-8-sig")


def load_csv(csv_text):
    """Parse Qualtrics CSV (3 header rows + data)."""
    lines = csv_text.strip().split("\n")
    reader = csv.reader(lines)
    all_rows = list(reader)
    headers = all_rows[0]
    data = []
    for row in all_rows[3:]:  # skip 3 header rows
        d = {headers[i]: row[i] if i < len(row) else "" for i in range(len(headers))}
        data.append(d)
    return data


def apply_exclusions(data):
    """Apply pre-registered exclusions."""
    clean = []
    excluded = {"attn_fail": 0, "speeder": 0, "incomplete": 0}
    for d in data:
        # Attention check: QID3 must = 4 (Horse)
        if d.get("attn_check", "") != "4" and d.get("attn_check", "") != "":
            excluded["attn_fail"] += 1
            continue
        # Speeder: Duration < 90 seconds
        dur = d.get("Duration (in seconds)", "0")
        try:
            if int(dur) < 90 and int(dur) > 0:
                excluded["speeder"] += 1
                continue
        except:
            pass
        # Must be finished
        if d.get("Finished") == "0":
            excluded["incomplete"] += 1
            continue
        clean.append(d)
    return clean, excluded


def chi_squared_2x2(a, b, c, d_val):
    """Manual chi-squared for 2x2 table. Returns chi2, p-value."""
    n = a + b + c + d_val
    if n == 0:
        return 0, 1
    expected_a = (a + b) * (a + c) / n
    expected_b = (a + b) * (b + d_val) / n
    expected_c = (c + d_val) * (a + c) / n
    expected_d = (c + d_val) * (b + d_val) / n

    chi2 = 0
    for obs, exp in [(a, expected_a), (b, expected_b), (c, expected_c), (d_val, expected_d)]:
        if exp > 0:
            chi2 += (obs - exp) ** 2 / exp

    # Approximate p-value using chi2 with 1 df
    # (Normal approx: p ~ exp(-chi2/2) for chi2 > 3.84 -> p < 0.05)
    import math
    if chi2 < 0.001:
        p = 1.0
    else:
        # Use Wilson-Hilferty approximation
        p = math.exp(-chi2 / 2) * (1 + chi2 / 2) if chi2 < 10 else 1e-10
        # More precise for moderate chi2:
        # chi2 distribution CDF approximation
        z = math.sqrt(chi2) - math.sqrt(1 - 2/9)  # rough
        p = 0.5 * math.erfc(math.sqrt(chi2/2) / math.sqrt(1))  # upper tail

    return chi2, p


# ================================================================
# STUDY A ANALYSIS
# ================================================================
def analyze_study_a(data):
    print("\n" + "=" * 70)
    print("  STUDY A: AI CONFABULATION COMPLIANCE TEST")
    print("=" * 70)

    if not data:
        print("  NO DATA")
        return

    # Apply exclusions
    clean, excl = apply_exclusions(data)
    print(f"\n  Responses: {len(data)} total, {len(clean)} after exclusions")
    print(f"  Excluded: {excl}")
    if len(clean) < 10:
        print("  TOO FEW RESPONSES for analysis")
        return

    # Split by condition
    noai = [d for d in clean if d.get("ConditionD") == "NoAI"]
    biased = [d for d in clean if d.get("ConditionD") == "BiasedAI"]
    debiased = [d for d in clean if d.get("ConditionD") == "DebiasedAI"]

    print(f"\n  Conditions: NoAI={len(noai)}, BiasedAI={len(biased)}, DebiasedAI={len(debiased)}")

    # PRIMARY DV: branded choice rate
    def branded_rate(group):
        if not group:
            return 0, 0
        branded = sum(1 for d in group if d.get("QID17") == COFFEE_BRANDED)
        return branded, len(group)

    def optimal_rate(group):
        if not group:
            return 0, 0
        optimal = sum(1 for d in group if d.get("QID17") == COFFEE_OPTIMAL)
        return optimal, len(group)

    b_noai, n_noai = branded_rate(noai)
    b_biased, n_biased = branded_rate(biased)
    b_debiased, n_debiased = branded_rate(debiased)

    o_noai, _ = optimal_rate(noai)
    o_biased, _ = optimal_rate(biased)
    o_debiased, _ = optimal_rate(debiased)

    print(f"\n  --- PRIMARY RESULTS ---")
    print(f"  De'Longhi (branded) choice rate:")
    print(f"    NoAI:      {b_noai}/{n_noai} = {b_noai/n_noai*100:.1f}%" if n_noai else "    NoAI: N/A")
    print(f"    BiasedAI:  {b_biased}/{n_biased} = {b_biased/n_biased*100:.1f}%" if n_biased else "    BiasedAI: N/A")
    print(f"    DebiasedAI:{b_debiased}/{n_debiased} = {b_debiased/n_debiased*100:.1f}%" if n_debiased else "    DebiasedAI: N/A")

    print(f"\n  Presswell (optimal) choice rate:")
    print(f"    NoAI:      {o_noai}/{n_noai} = {o_noai/n_noai*100:.1f}%" if n_noai else "    NoAI: N/A")
    print(f"    BiasedAI:  {o_biased}/{n_biased} = {o_biased/n_biased*100:.1f}%" if n_biased else "    BiasedAI: N/A")
    print(f"    DebiasedAI:{o_debiased}/{n_debiased} = {o_debiased/n_debiased*100:.1f}%" if n_debiased else "    DebiasedAI: N/A")

    # DIAGNOSTIC: Control optimal rate
    if n_noai:
        print(f"\n  DIAGNOSTIC: Control optimal rate = {o_noai/n_noai*100:.1f}%")
        if o_noai/n_noai >= 0.8:
            print("    -> Fictional brand CREDIBLE (>=80%)")
        elif o_noai/n_noai >= 0.6:
            print("    -> Moderate credibility (60-80%)")
        else:
            print("    -> WARNING: Low credibility (<60%)")

    # PRIMARY TEST: chi-squared BiasedAI vs NoAI
    if n_noai >= 5 and n_biased >= 5:
        # 2x2: branded/not x condition
        a = b_biased      # biased + chose branded
        b = n_biased - b_biased  # biased + not branded
        c = b_noai         # noai + chose branded
        d = n_noai - b_noai  # noai + not branded
        chi2, p = chi_squared_2x2(a, b, c, d)
        rd = b_biased/n_biased - b_noai/n_noai  # risk difference
        print(f"\n  PRIMARY TEST: BiasedAI vs NoAI (branded choice)")
        print(f"    Risk difference: {rd*100:+.1f}pp")
        print(f"    Chi-squared: {chi2:.3f}")
        print(f"    (Install scipy for exact p-value)")

    # Choice distribution
    print(f"\n  Full choice distribution:")
    for cond_name, group in [("NoAI", noai), ("BiasedAI", biased), ("DebiasedAI", debiased)]:
        choices = Counter(d.get("QID17", "?") for d in group)
        products = {"1": "Nespresso", "2": "De'Longhi*", "3": "Breville", "4": "Presswell**", "5": "Philips"}
        dist = ", ".join(f"{products.get(k,k)}={v}" for k, v in sorted(choices.items()))
        print(f"    {cond_name}: {dist}")

    # Brand awareness for Presswell
    presswell_aware = Counter(d.get("QID46_4", "?") for d in clean)
    print(f"\n  Presswell brand awareness: own={presswell_aware.get('1',0)}, heard={presswell_aware.get('2',0)}, never={presswell_aware.get('3',0)}")


# ================================================================
# STUDY Y ANALYSIS
# ================================================================
def analyze_study_y(data):
    print("\n" + "=" * 70)
    print("  STUDY Y: DISCLOSURE GRADIENT")
    print("=" * 70)

    if not data:
        print("  NO DATA")
        return

    clean, excl = apply_exclusions(data)
    print(f"\n  Responses: {len(data)} total, {len(clean)} after exclusions")
    print(f"  Excluded: {excl}")

    conditions = ["NoAI", "AI_NoDis", "AI_Generic", "AI_Mechanism", "AI_Quantified"]
    for cond in conditions:
        group = [d for d in clean if d.get("ConditionD") == cond]
        branded = sum(1 for d in group if d.get("QID17") == COFFEE_BRANDED)
        n = len(group)
        rate = branded/n*100 if n else 0
        print(f"  {cond:20s}: {branded}/{n} branded = {rate:.1f}%")


# ================================================================
# STUDY Z ANALYSIS
# ================================================================
def analyze_study_z(data):
    print("\n" + "=" * 70)
    print("  STUDY Z: COMPETITION WELFARE TEST")
    print("=" * 70)

    if not data:
        print("  NO DATA")
        return

    clean, excl = apply_exclusions(data)
    print(f"\n  Responses: {len(data)} total, {len(clean)} after exclusions")

    # Map each response to its product choice and whether it chose optimal
    for d in clean:
        cat = d.get("CategoryD", d.get("Category", ""))
        ai = d.get("AICondition", "")

        # Determine which choice column to use
        if "coffee" in cat or cat == "1":
            d["_choice"] = d.get("QID17", "")
            d["_chose_optimal"] = d["_choice"] == COFFEE_OPTIMAL
            d["_chose_branded"] = d["_choice"] == COFFEE_BRANDED
            d["_cat"] = "coffee"
        elif "headphone" in cat or cat == "2":
            d["_choice"] = d.get("QID18", "")
            d["_chose_optimal"] = d["_choice"] == HEADPHONE_OPTIMAL
            d["_chose_branded"] = d["_choice"] == HEADPHONE_BRANDED
            d["_cat"] = "headphones"
        elif "earbud" in cat or cat == "3":
            d["_choice"] = d.get("QID19", "")
            d["_chose_optimal"] = d["_choice"] == EARBUDS_OPTIMAL
            d["_chose_branded"] = d["_choice"] == EARBUDS_BRANDED
            d["_cat"] = "earbuds"
        else:
            d["_cat"] = "unknown"
            d["_chose_optimal"] = False
            d["_chose_branded"] = False

        d["_ai"] = "AI" if "AI" in str(ai) and "NoAI" not in str(ai) else "NoAI"
        if "NoAI" in str(d.get("ConditionD", "")):
            d["_ai"] = "NoAI"
        elif "AI_" in str(d.get("ConditionD", "")):
            d["_ai"] = "AI"

    # Results by category x AI
    for cat in ["coffee", "headphones", "earbuds"]:
        ai_group = [d for d in clean if d["_cat"] == cat and d["_ai"] == "AI"]
        noai_group = [d for d in clean if d["_cat"] == cat and d["_ai"] == "NoAI"]
        ai_opt = sum(1 for d in ai_group if d["_chose_optimal"])
        noai_opt = sum(1 for d in noai_group if d["_chose_optimal"])
        print(f"\n  {cat}: AI optimal={ai_opt}/{len(ai_group)}, NoAI optimal={noai_opt}/{len(noai_group)}")


# ================================================================
# MAIN
# ================================================================
def main():
    print("=" * 70)
    print("  V4 LEAN ANALYSIS PIPELINE")
    print("  Downloads from Qualtrics + runs all pre-registered tests")
    print("=" * 70)

    if len(sys.argv) > 1:
        # Local CSV file
        with open(sys.argv[1], encoding="utf-8-sig") as f:
            csv_text = f.read()
        data = load_csv(csv_text)
        analyze_study_a(data)
        return

    if not HAS_REQUESTS:
        print("ERROR: requests library required for API download")
        return

    # Download and analyze all surveys
    for name, sid in SURVEYS.items():
        print(f"\n  Downloading {name}...")
        csv_text = export_from_qualtrics(sid)
        if not csv_text:
            print(f"  {name}: export failed")
            continue

        data = load_csv(csv_text)
        if not data:
            print(f"  {name}: 0 responses (empty)")
            continue

        if name == "Study A":
            analyze_study_a(data)
        elif name == "Study Y":
            analyze_study_y(data)
        elif name == "Study Z":
            analyze_study_z(data)
        elif name == "Pretest":
            print(f"\n  Pretest: {len(data)} responses")
            # Presswell credibility
            cred = [d.get("credibility_4", "") for d in data if d.get("credibility_4")]
            if cred:
                vals = [int(c) for c in cred if c.isdigit()]
                if vals:
                    print(f"  Presswell credibility: mean={sum(vals)/len(vals):.2f} (threshold: 4.0)")

    print("\n" + "=" * 70)
    print("  ANALYSIS COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
