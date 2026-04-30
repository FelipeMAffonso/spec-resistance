"""Update the pretest (SV_bOyHko6mpqtn4mq) to test coffee makers credibility.
Must match the main studies which now use sr_coffee_makers_02."""
import sys, os, json, requests
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))
from experiment.assortments import ALL_ASSORTMENTS

BASE = "https://pdx1.qualtrics.com/API/v3"
HEADERS = {"X-API-TOKEN": "Br4dAvcZOSSsJcup0AXpLDj7BjuGs1Pp96nNirWY",
           "Content-Type": "application/json"}
SID = "SV_bOyHko6mpqtn4mq"

# Get coffee makers assortment
for a in ALL_ASSORTMENTS:
    if a['id'] == 'sr_coffee_makers_02':
        products = a['products']
        break

print("Coffee makers products for pretest:")
for p in products:
    opt = " <<< OPTIMAL" if p['brand_familiarity'] == 'low' else ""
    print(f"  {p['brand']:15s} {p['name']:30s} ${p['price']:>7.2f} {p['brand_familiarity']}{opt}")

# Build product table HTML
rows = ''
for p in products:
    specs = ' | '.join(str(v) for v in p['specs'].values())
    rows += (f'<tr><td style="padding:8px;font-weight:bold">{p["brand"]}</td>'
            f'<td style="padding:8px">{p["name"]}</td>'
            f'<td style="padding:8px;color:#0f7b0f">${p["price"]:.2f}</td>'
            f'<td style="padding:8px">{specs}</td>'
            f'<td style="padding:8px">{p["avg_rating"]} ({p["review_count"]})</td></tr>')

TABLE = (f'<h3>Compare Espresso Machines</h3>'
        f'<p>You are looking for an espresso machine for home, under $300.</p>'
        f'<table style="width:100%;border-collapse:collapse;font-size:13px">'
        f'<thead><tr style="background:#f0f0f0">'
        f'<th style="padding:8px;text-align:left">Brand</th>'
        f'<th style="padding:8px">Model</th>'
        f'<th style="padding:8px">Price</th>'
        f'<th style="padding:8px">Specs</th>'
        f'<th style="padding:8px">Rating</th>'
        f'</tr></thead><tbody>{rows}</tbody></table>'
        f'<p style="color:#666;font-size:12px">Products compiled from multiple retailers.</p>')

print(f"\nTable HTML: {len(TABLE)} chars")

# Update QID3 (product_table) question text
r = requests.get(f"{BASE}/survey-definitions/{SID}/questions/QID3", headers=HEADERS, timeout=30)
if r.status_code == 200:
    q = r.json()['result']
    q['QuestionText'] = TABLE
    q.pop('QuestionID', None)
    q.pop('QuestionText_Unsafe', None)
    r2 = requests.put(f"{BASE}/survey-definitions/{SID}/questions/QID3", headers=HEADERS, timeout=30, json=q)
    print(f"Product table updated: {r2.status_code}")

# Update QID5 (credibility) choices to match coffee makers brands
r = requests.get(f"{BASE}/survey-definitions/{SID}/questions/QID5", headers=HEADERS, timeout=30)
if r.status_code == 200:
    q = r.json()['result']
    new_choices = {}
    for i, p in enumerate(products):
        new_choices[str(i+1)] = {"Display": f"{p['brand']} {p['name']}"}
    q['Choices'] = new_choices
    q.pop('QuestionID', None)
    q.pop('QuestionText_Unsafe', None)
    r2 = requests.put(f"{BASE}/survey-definitions/{SID}/questions/QID5", headers=HEADERS, timeout=30, json=q)
    print(f"Credibility choices updated: {r2.status_code}")

# Update QID6 (purchase_likelihood) choices
r = requests.get(f"{BASE}/survey-definitions/{SID}/questions/QID6", headers=HEADERS, timeout=30)
if r.status_code == 200:
    q = r.json()['result']
    q['Choices'] = new_choices
    q.pop('QuestionID', None)
    q.pop('QuestionText_Unsafe', None)
    r2 = requests.put(f"{BASE}/survey-definitions/{SID}/questions/QID6", headers=HEADERS, timeout=30, json=q)
    print(f"Purchase likelihood choices updated: {r2.status_code}")

# Update QID7 (product_choice) choices
r = requests.get(f"{BASE}/survey-definitions/{SID}/questions/QID7", headers=HEADERS, timeout=30)
if r.status_code == 200:
    q = r.json()['result']
    choice_opts = {}
    for i, p in enumerate(products):
        choice_opts[str(i+1)] = {"Display": f"{p['brand']} {p['name']} (${p['price']:.2f})"}
    q['Choices'] = choice_opts
    q.pop('QuestionID', None)
    q.pop('QuestionText_Unsafe', None)
    r2 = requests.put(f"{BASE}/survey-definitions/{SID}/questions/QID7", headers=HEADERS, timeout=30, json=q)
    print(f"Product choice updated: {r2.status_code}")

# Update QID8 (brand_awareness) choices
r = requests.get(f"{BASE}/survey-definitions/{SID}/questions/QID8", headers=HEADERS, timeout=30)
if r.status_code == 200:
    q = r.json()['result']
    brand_choices = {}
    for i, p in enumerate(products):
        brand_choices[str(i+1)] = {"Display": p['brand']}
    q['Choices'] = brand_choices
    q.pop('QuestionID', None)
    q.pop('QuestionText_Unsafe', None)
    r2 = requests.put(f"{BASE}/survey-definitions/{SID}/questions/QID8", headers=HEADERS, timeout=30, json=q)
    print(f"Brand awareness updated: {r2.status_code}")

# Delete old test responses
print("\nCleaning old responses...")
r = requests.post(f"{BASE}/surveys/{SID}/export-responses", headers=HEADERS, timeout=30,
                  json={"format": "json", "compress": False})
if r.status_code == 200:
    import time
    pid = r.json()['result']['progressId']
    for _ in range(15):
        time.sleep(2)
        r2 = requests.get(f"{BASE}/surveys/{SID}/export-responses/{pid}", headers=HEADERS, timeout=30)
        if r2.json()['result']['status'] == 'complete':
            fid = r2.json()['result']['fileId']
            r3 = requests.get(f"{BASE}/surveys/{SID}/export-responses/{fid}/file", headers=HEADERS, timeout=30)
            try:
                responses = r3.json().get('responses', [])
                for resp in responses:
                    rid = resp.get('responseId')
                    if rid:
                        requests.delete(f"{BASE}/surveys/{SID}/responses/{rid}", headers=HEADERS, timeout=30)
                print(f"Deleted {len(responses)} old responses")
            except:
                print("Could not parse responses")
            break

print(f"\nPretest updated to coffee_makers_02")
print(f"Optimal: Presswell NEO Flex ($99.99)")
print(f"Go/No-Go: Presswell credibility >= 4.0 AND optimal choice >= 50%")
