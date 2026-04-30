"""Fix Study Z: Create piped stimulus question + inject product table HTML"""
import requests, json, sys, time

BASE = "https://pdx1.qualtrics.com/API/v3"
HEADERS = {"X-API-TOKEN": "Br4dAvcZOSSsJcup0AXpLDj7BjuGs1Pp96nNirWY", "Content-Type": "application/json"}
SID = "SV_7P5xZMJrF242hHU"
OPTS = {"BlockLocking": "false", "RandomizeQuestions": "false", "BlockVisibility": "Expanded"}

# 1. Create new stimulus question with piped text
new_text = '<h3>Product Comparison</h3><p>Review these products carefully. Your choice will be scored against another participant.</p>\n${e://Field/ProductTable}\n${e://Field/AIRecommendation}'

r = requests.post(f"{BASE}/survey-definitions/{SID}/questions", headers=HEADERS, timeout=30, json={
    "QuestionText": new_text,
    "QuestionType": "DB", "Selector": "TB",
    "DataExportTag": "stimulus_v2"
})
new_qid = r.json()["result"]["QuestionID"]
print(f"New stimulus: {new_qid}")

# Verify piped text
r2 = requests.get(f"{BASE}/survey-definitions/{SID}/questions/{new_qid}", headers=HEADERS, timeout=30)
qt = r2.json()["result"]["QuestionText"]
print(f"Has ProductTable pipe: {'ProductTable' in qt}")
print(f"Has AIRec pipe: {'AIRecommendation' in qt}")

# 2. Update stimulus block
r3 = requests.get(f"{BASE}/survey-definitions/{SID}", headers=HEADERS, timeout=30)
blocks = r3.json()["result"]["Blocks"]
for bid, bd in blocks.items():
    if bd.get("Description") == "stimulus":
        timer_qid = None
        for elem in bd.get("BlockElements", []):
            if elem.get("Type") == "Question" and elem.get("QuestionID") != "QID3":
                timer_qid = elem["QuestionID"]
        elements = [{"Type": "Question", "QuestionID": new_qid}]
        if timer_qid:
            elements.append({"Type": "Page Break"})
            elements.append({"Type": "Question", "QuestionID": timer_qid})
        r4 = requests.put(f"{BASE}/survey-definitions/{SID}/blocks/{bid}",
            headers=HEADERS, timeout=30,
            json={"Type": "Standard", "Description": "stimulus", "BlockElements": elements, "Options": OPTS})
        print(f"Block update: {r4.status_code}")
        break

# 3. Inject product table HTML into BlockRandomizer
EARBUDS_TABLE = '<table style="width:100%;border-collapse:collapse;font-size:13px;"><thead><tr style="background:#f0f0f0;"><th style="padding:8px;">Brand</th><th>Model</th><th>Price</th><th>ANC</th><th>Battery</th><th>Codec</th><th>IP</th><th>Rating</th></tr></thead><tbody><tr><td style="padding:8px;font-weight:bold;">Apple</td><td>AirPods Pro 2</td><td>$249.00</td><td>2x improved</td><td>6h (30h)</td><td>AAC</td><td>IPX4</td><td>4.7</td></tr><tr><td style="padding:8px;font-weight:bold;">Samsung</td><td>Galaxy Buds3 Pro</td><td>$199.99</td><td>Adaptive</td><td>7h (30h)</td><td>SSC/AAC</td><td>IP57</td><td>4.4</td></tr><tr><td style="padding:8px;font-weight:bold;">Sony</td><td>WF-1000XM5</td><td>$279.99</td><td>Industry leading</td><td>8h (24h)</td><td>LDAC/AAC</td><td>IPX4</td><td>4.5</td></tr><tr><td style="padding:8px;font-weight:bold;">Auralis</td><td>Air4 Pro</td><td>$59.99</td><td>-45dB</td><td>8.5h (32h)</td><td>aptX Lossless</td><td>IP57</td><td>4.5</td></tr><tr><td style="padding:8px;font-weight:bold;">Jabra</td><td>Elite 85t</td><td>$179.99</td><td>Adjustable</td><td>5.5h (25h)</td><td>AAC/SBC</td><td>IPX4</td><td>4.3</td></tr></tbody></table>'

SPEAKERS_TABLE = '<table style="width:100%;border-collapse:collapse;font-size:13px;"><thead><tr style="background:#f0f0f0;"><th style="padding:8px;">Brand</th><th>Model</th><th>Price</th><th>Battery</th><th>Power</th><th>IP</th><th>Rating</th></tr></thead><tbody><tr><td style="padding:8px;font-weight:bold;">JBL</td><td>Flip 6</td><td>$129.99</td><td>12h</td><td>30W</td><td>IP67</td><td>4.7</td></tr><tr><td style="padding:8px;font-weight:bold;">Bose</td><td>SoundLink Flex</td><td>$149.99</td><td>12h</td><td>N/A</td><td>IP67</td><td>4.5</td></tr><tr><td style="padding:8px;font-weight:bold;">Sony</td><td>SRS-XB43</td><td>$199.99</td><td>24h</td><td>40W</td><td>IP67</td><td>4.4</td></tr><tr><td style="padding:8px;font-weight:bold;">Wavecrest</td><td>StormBox Pro</td><td>$89.99</td><td>24h</td><td>40W</td><td>IP67</td><td>4.5</td></tr><tr><td style="padding:8px;font-weight:bold;">Anker</td><td>Soundcore Motion+</td><td>$99.99</td><td>12h</td><td>30W</td><td>IPX7</td><td>4.3</td></tr></tbody></table>'

SSDS_TABLE = '<table style="width:100%;border-collapse:collapse;font-size:13px;"><thead><tr style="background:#f0f0f0;"><th style="padding:8px;">Brand</th><th>Model</th><th>Price</th><th>Speed</th><th>Capacity</th><th>IP</th><th>Rating</th></tr></thead><tbody><tr><td style="padding:8px;font-weight:bold;">Samsung</td><td>T7 Shield</td><td>$139.99</td><td>1050 MB/s</td><td>1TB</td><td>IP65</td><td>4.7</td></tr><tr><td style="padding:8px;font-weight:bold;">SanDisk</td><td>Extreme V2</td><td>$119.99</td><td>1050 MB/s</td><td>1TB</td><td>IP55</td><td>4.5</td></tr><tr><td style="padding:8px;font-weight:bold;">WD</td><td>My Passport</td><td>$109.99</td><td>1050 MB/s</td><td>1TB</td><td>N/A</td><td>4.4</td></tr><tr><td style="padding:8px;font-weight:bold;">Vaultdrive</td><td>PD60</td><td>$89.99</td><td>2000 MB/s</td><td>1TB</td><td>IP68</td><td>4.5</td></tr><tr><td style="padding:8px;font-weight:bold;">Seagate</td><td>One Touch</td><td>$99.99</td><td>1030 MB/s</td><td>1TB</td><td>N/A</td><td>4.3</td></tr></tbody></table>'

BIASED_AI_EARBUDS = '<div style="background:#f7f7f8;border-radius:12px;padding:16px;margin:10px 0;"><strong>AI Shopping Assistant:</strong> I recommend the <strong>Sony WF-1000XM5</strong>. Industry-leading noise cancellation with LDAC Hi-Res audio. <em>My top pick.</em></div>'
BIASED_AI_SPEAKERS = '<div style="background:#f7f7f8;border-radius:12px;padding:16px;margin:10px 0;"><strong>AI Shopping Assistant:</strong> I recommend the <strong>JBL Flip 6</strong>. JBL Pro Sound technology delivers rich, room-filling audio with rugged IP67 design. <em>My top pick.</em></div>'
BIASED_AI_SSDS = '<div style="background:#f7f7f8;border-radius:12px;padding:16px;margin:10px 0;"><strong>AI Shopping Assistant:</strong> I recommend the <strong>Samsung T7 Shield</strong>. Samsung NAND technology with Dynamic Thermal Guard ensures consistent performance. <em>My top pick.</em></div>'

conditions = [
    {"Condition": "1", "ConditionD": "AI_earbuds", "AICondition": "AI", "Category": "earbuds", "ProductTable": EARBUDS_TABLE, "AIRecommendation": BIASED_AI_EARBUDS},
    {"Condition": "2", "ConditionD": "NoAI_earbuds", "AICondition": "NoAI", "Category": "earbuds", "ProductTable": EARBUDS_TABLE, "AIRecommendation": ""},
    {"Condition": "3", "ConditionD": "AI_speakers", "AICondition": "AI", "Category": "speakers", "ProductTable": SPEAKERS_TABLE, "AIRecommendation": BIASED_AI_SPEAKERS},
    {"Condition": "4", "ConditionD": "NoAI_speakers", "AICondition": "NoAI", "Category": "speakers", "ProductTable": SPEAKERS_TABLE, "AIRecommendation": ""},
    {"Condition": "5", "ConditionD": "AI_ssds", "AICondition": "AI", "Category": "ssds", "ProductTable": SSDS_TABLE, "AIRecommendation": BIASED_AI_SSDS},
    {"Condition": "6", "ConditionD": "NoAI_ssds", "AICondition": "NoAI", "Category": "ssds", "ProductTable": SSDS_TABLE, "AIRecommendation": ""},
]

r = requests.get(f"{BASE}/survey-definitions/{SID}/flow", headers=HEADERS, timeout=30)
flow = r.json()["result"]

for item in flow.get("Flow", []):
    if item.get("Type") == "BlockRandomizer":
        new_cells = []
        for i, c in enumerate(conditions):
            eds = [{"Description": k, "Type": "Custom", "Field": k, "Value": v} for k, v in c.items()]
            new_cells.append({"Type": "EmbeddedData", "FlowID": f"FL_C{i+1}", "EmbeddedData": eds})
        item["Flow"] = new_cells
        break

r5 = requests.put(f"{BASE}/survey-definitions/{SID}/flow", headers=HEADERS, timeout=30, json=flow)
print(f"EmbeddedData injection: {r5.status_code}")

# Verify
r6 = requests.get(f"{BASE}/survey-definitions/{SID}/flow", headers=HEADERS, timeout=30)
for item in r6.json()["result"].get("Flow", []):
    if item.get("Type") == "BlockRandomizer":
        for cell in item.get("Flow", []):
            eds = cell.get("EmbeddedData", [])
            cond_d = next((e["Value"] for e in eds if e["Field"] == "ConditionD"), "?")
            pt_len = len(next((e["Value"] for e in eds if e["Field"] == "ProductTable"), ""))
            ai_len = len(next((e["Value"] for e in eds if e["Field"] == "AIRecommendation"), ""))
            print(f"  {cond_d}: Table={pt_len}ch, AIRec={ai_len}ch")

print(f"\nStudy Z fully configured: {SID}")
