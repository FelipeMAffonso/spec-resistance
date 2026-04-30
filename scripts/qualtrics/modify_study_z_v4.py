"""
Modify Study Z V2 copy (SV_esVf052AlAoqBiS) with V4 competition content.
Source: V2 Study 1 (confabulation mechanism)
Target: V4 Study Z (2 AI conditions x 3 categories = 6 cells)

Changes:
1. Update consent with competition framing ($2 bonus)
2. Replace 12-cell BlockRandomizer with 6-cell (AI/NoAI x earbuds/speakers/ssds)
3. Include different product tables per category
"""
import requests, json, sys, time

BASE = "https://pdx1.qualtrics.com/API/v3"
HEADERS = {"X-API-TOKEN": "Br4dAvcZOSSsJcup0AXpLDj7BjuGs1Pp96nNirWY",
           "Content-Type": "application/json"}

SID = "SV_esVf052AlAoqBiS"

def api_get(path):
    r = requests.get(f"{BASE}{path}", headers=HEADERS, timeout=30)
    return r.json()["result"] if r.status_code == 200 else None

def api_put(path, data):
    r = requests.put(f"{BASE}{path}", headers=HEADERS, json=data, timeout=30)
    return r.status_code == 200

# Product tables for 3 categories
EARBUDS_TABLE = ('<table style="width:100%;border-collapse:collapse;font-size:13px">'
    '<thead><tr style="background:#f0f0f0"><th style="padding:8px;text-align:left">Brand</th>'
    '<th style="padding:8px">Model</th><th style="padding:8px">Price</th>'
    '<th style="padding:8px">ANC</th><th style="padding:8px">Battery</th>'
    '<th style="padding:8px">Codec</th><th style="padding:8px">IP</th>'
    '<th style="padding:8px">Rating</th></tr></thead><tbody>'
    '<tr><td style="padding:8px;font-weight:bold">Apple</td><td>AirPods Pro 2</td>'
    '<td>$249.00</td><td>2x improved</td><td>6h (30h)</td><td>AAC</td><td>IPX4</td><td>4.7</td></tr>'
    '<tr><td style="padding:8px;font-weight:bold">Samsung</td><td>Galaxy Buds3 Pro</td>'
    '<td>$199.99</td><td>Adaptive</td><td>7h (30h)</td><td>SSC/AAC</td><td>IP57</td><td>4.4</td></tr>'
    '<tr><td style="padding:8px;font-weight:bold">Sony</td><td>WF-1000XM5</td>'
    '<td>$279.99</td><td>Industry leading</td><td>8h (24h)</td><td>LDAC</td><td>IPX4</td><td>4.5</td></tr>'
    '<tr><td style="padding:8px;font-weight:bold">Auralis</td><td>Air4 Pro</td>'
    '<td>$59.99</td><td>-45dB</td><td>8.5h (32h)</td><td>aptX Lossless</td><td>IP57</td><td>4.5</td></tr>'
    '<tr><td style="padding:8px;font-weight:bold">Jabra</td><td>Elite 85t</td>'
    '<td>$179.99</td><td>Adjustable</td><td>5.5h (25h)</td><td>AAC/SBC</td><td>IPX4</td><td>4.3</td></tr>'
    '</tbody></table>')

SPEAKERS_TABLE = ('<table style="width:100%;border-collapse:collapse;font-size:13px">'
    '<thead><tr style="background:#f0f0f0"><th style="padding:8px;text-align:left">Brand</th>'
    '<th style="padding:8px">Model</th><th style="padding:8px">Price</th>'
    '<th style="padding:8px">Battery</th><th style="padding:8px">Power</th>'
    '<th style="padding:8px">IP</th><th style="padding:8px">Rating</th></tr></thead><tbody>'
    '<tr><td style="padding:8px;font-weight:bold">JBL</td><td>Flip 6</td>'
    '<td>$129.99</td><td>12h</td><td>30W</td><td>IP67</td><td>4.7</td></tr>'
    '<tr><td style="padding:8px;font-weight:bold">Bose</td><td>SoundLink Flex</td>'
    '<td>$149.99</td><td>12h</td><td>N/A</td><td>IP67</td><td>4.5</td></tr>'
    '<tr><td style="padding:8px;font-weight:bold">Sony</td><td>SRS-XB43</td>'
    '<td>$199.99</td><td>24h</td><td>40W</td><td>IP67</td><td>4.4</td></tr>'
    '<tr><td style="padding:8px;font-weight:bold">Wavecrest</td><td>StormBox Pro</td>'
    '<td>$89.99</td><td>24h</td><td>40W</td><td>IP67</td><td>4.5</td></tr>'
    '<tr><td style="padding:8px;font-weight:bold">Anker</td><td>Soundcore Motion+</td>'
    '<td>$99.99</td><td>12h</td><td>30W</td><td>IPX7</td><td>4.3</td></tr>'
    '</tbody></table>')

SSDS_TABLE = ('<table style="width:100%;border-collapse:collapse;font-size:13px">'
    '<thead><tr style="background:#f0f0f0"><th style="padding:8px;text-align:left">Brand</th>'
    '<th style="padding:8px">Model</th><th style="padding:8px">Price</th>'
    '<th style="padding:8px">Speed</th><th style="padding:8px">Capacity</th>'
    '<th style="padding:8px">IP</th><th style="padding:8px">Rating</th></tr></thead><tbody>'
    '<tr><td style="padding:8px;font-weight:bold">Samsung</td><td>T7 Shield</td>'
    '<td>$139.99</td><td>1050 MB/s</td><td>1TB</td><td>IP65</td><td>4.7</td></tr>'
    '<tr><td style="padding:8px;font-weight:bold">SanDisk</td><td>Extreme V2</td>'
    '<td>$119.99</td><td>1050 MB/s</td><td>1TB</td><td>IP55</td><td>4.5</td></tr>'
    '<tr><td style="padding:8px;font-weight:bold">WD</td><td>My Passport</td>'
    '<td>$109.99</td><td>1050 MB/s</td><td>1TB</td><td>N/A</td><td>4.4</td></tr>'
    '<tr><td style="padding:8px;font-weight:bold">Vaultdrive</td><td>PD60</td>'
    '<td>$89.99</td><td>2000 MB/s</td><td>1TB</td><td>IP68</td><td>4.5</td></tr>'
    '<tr><td style="padding:8px;font-weight:bold">Seagate</td><td>One Touch</td>'
    '<td>$99.99</td><td>1030 MB/s</td><td>1TB</td><td>N/A</td><td>4.3</td></tr>'
    '</tbody></table>')

# AI recs per category (biased)
AI_EARBUDS = ('<div style="background:#f7f7f8;border-radius:12px;padding:16px;margin:10px 0">'
    '<strong>AI Shopping Assistant:</strong> I recommend the <strong>Sony WF-1000XM5</strong>. '
    'Industry-leading noise cancellation with LDAC Hi-Res audio. <em>My top pick.</em></div>')

AI_SPEAKERS = ('<div style="background:#f7f7f8;border-radius:12px;padding:16px;margin:10px 0">'
    '<strong>AI Shopping Assistant:</strong> I recommend the <strong>JBL Flip 6</strong>. '
    'JBL Pro Sound technology delivers rich audio with rugged IP67 design. <em>My top pick.</em></div>')

AI_SSDS = ('<div style="background:#f7f7f8;border-radius:12px;padding:16px;margin:10px 0">'
    '<strong>AI Shopping Assistant:</strong> I recommend the <strong>Samsung T7 Shield</strong>. '
    'Samsung NAND technology with Dynamic Thermal Guard for consistent performance. <em>My top pick.</em></div>')

# 6 cells: 2 AI x 3 categories
conditions = [
    {"Condition": "1", "ConditionD": "AI_earbuds", "AICondition": "AI", "Category": "1",
     "CategoryD": "earbuds", "ProductTable": EARBUDS_TABLE, "AIRecommendation": AI_EARBUDS,
     "BrandedTarget": "Sony WF-1000XM5", "OptimalProduct": "Auralis Air4 Pro"},
    {"Condition": "2", "ConditionD": "NoAI_earbuds", "AICondition": "NoAI", "Category": "1",
     "CategoryD": "earbuds", "ProductTable": EARBUDS_TABLE, "AIRecommendation": "",
     "BrandedTarget": "Sony WF-1000XM5", "OptimalProduct": "Auralis Air4 Pro"},
    {"Condition": "3", "ConditionD": "AI_speakers", "AICondition": "AI", "Category": "2",
     "CategoryD": "speakers", "ProductTable": SPEAKERS_TABLE, "AIRecommendation": AI_SPEAKERS,
     "BrandedTarget": "JBL Flip 6", "OptimalProduct": "Wavecrest StormBox Pro"},
    {"Condition": "4", "ConditionD": "NoAI_speakers", "AICondition": "NoAI", "Category": "2",
     "CategoryD": "speakers", "ProductTable": SPEAKERS_TABLE, "AIRecommendation": "",
     "BrandedTarget": "JBL Flip 6", "OptimalProduct": "Wavecrest StormBox Pro"},
    {"Condition": "5", "ConditionD": "AI_ssds", "AICondition": "AI", "Category": "3",
     "CategoryD": "ssds", "ProductTable": SSDS_TABLE, "AIRecommendation": AI_SSDS,
     "BrandedTarget": "Samsung T7 Shield", "OptimalProduct": "Vaultdrive PD60"},
    {"Condition": "6", "ConditionD": "NoAI_ssds", "AICondition": "NoAI", "Category": "3",
     "CategoryD": "ssds", "ProductTable": SSDS_TABLE, "AIRecommendation": "",
     "BrandedTarget": "Samsung T7 Shield", "OptimalProduct": "Vaultdrive PD60"},
]

print("Modifying Study Z (SV_esVf052AlAoqBiS)...")

# Step 1: Update consent with competition framing
print("\n1. Updating consent...")
q = api_get(f"/survey-definitions/{SID}/questions/QID2")
if q:
    q["QuestionText"] = ('<h3>Consent Form</h3>'
        '<p><b>Title:</b> Consumer Product Evaluation Study<br>'
        '<b>Investigator:</b> Dr. Felipe Affonso, Oklahoma State University</p>'
        '<p>Duration: ~4-5 min. Anonymous. Voluntary.</p>'
        '<p><b>Competition bonus:</b> After data collection, your product choice will be '
        'randomly paired with another participant\'s choice. The participant in each pair '
        'whose chosen product scores higher on our quality-value evaluation will receive '
        'a <b>$2 bonus</b>. Ties: both receive $1.</p>'
        '<p>Select "I agree" if you are 18+ and consent.</p>')
    q.pop("QuestionID", None)
    q.pop("QuestionText_Unsafe", None)
    ok = api_put(f"/survey-definitions/{SID}/questions/QID2", q)
    print(f"  Consent: {'OK' if ok else 'FAIL'}")

# Step 2: Update BlockRandomizer
print("\n2. Updating BlockRandomizer...")
flow = api_get(f"/survey-definitions/{SID}/flow")

# Add AICondition to init EmbeddedData
for item in flow.get("Flow", []):
    if item.get("Type") == "EmbeddedData":
        eds = item.get("EmbeddedData", [])
        existing = {e["Field"] for e in eds}
        for field in ["AICondition", "AIRecVersion"]:
            if field not in existing:
                eds.append({"Description": field, "Type": "Custom", "Field": field, "Value": ""})
        break

# Replace cells
for item in flow.get("Flow", []):
    if item.get("Type") == "BlockRandomizer":
        old_n = len(item.get("Flow", []))
        new_cells = []
        for i, cond in enumerate(conditions):
            eds = [{"Description": k, "Type": "Custom", "Field": k, "Value": v}
                   for k, v in cond.items()]
            new_cells.append({"Type": "EmbeddedData", "FlowID": f"FL_Z{i+1}", "EmbeddedData": eds})
        item["Flow"] = new_cells
        print(f"  Replaced {old_n} cells with {len(new_cells)} cells")
        break

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
            tbl_len = len(next((e["Value"] for e in eds if e["Field"] == "ProductTable"), ""))
            print(f"    {cond_d}: AI={ai_len}ch, Table={tbl_len}ch")
        break

# Step 3: Update name
r = requests.put(f"{BASE}/survey-definitions/{SID}/metadata",
    headers=HEADERS, timeout=30,
    json={"SurveyName": "SR V4 Study Z - Competition (from V2)"})
print(f"\n3. Name: {r.status_code}")

print(f"\nStudy Z: {SID}")
print(f"Edit: https://okstatebusiness.az1.qualtrics.com/survey-builder/{SID}/edit")
