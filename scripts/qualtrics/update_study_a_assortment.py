"""
Update Study A with sr_coffee_makers_02 assortment (73.3% non-optimal rate).
Extracts ACTUAL verbatim confabulated AI outputs from the 382K dataset.
Uses single-recommendation format matching the computational study.
"""
import sys, os, json, glob, requests, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))
from experiment.assortments import ALL_ASSORTMENTS

BASE = "https://pdx1.qualtrics.com/API/v3"
HEADERS = {"X-API-TOKEN": "Br4dAvcZOSSsJcup0AXpLDj7BjuGs1Pp96nNirWY",
           "Content-Type": "application/json"}
SID = "SV_cx2kueJwMOwdDj8"

# Get the coffee makers assortment
assortment = None
for a in ALL_ASSORTMENTS:
    if a['id'] == 'sr_coffee_makers_02':
        assortment = a
        break

if not assortment:
    print("Assortment not found!")
    sys.exit(1)

products = assortment['products']
print(f"Assortment: {assortment['id']}")
print(f"Category: {assortment['category']}")
print(f"Requirement: {assortment['user_requirement']}")
print()

# Build product table HTML
rows = ""
for p in products:
    specs_parts = []
    for k, v in p['specs'].items():
        specs_parts.append(f"{v}")
    specs_str = " | ".join(specs_parts)

    opt_mark = ""
    if p['brand_familiarity'] == 'low':
        opt_mark = " (optimal)"

    rows += f'''<tr>
<td style="padding:8px;font-weight:bold">{p['brand']}</td>
<td style="padding:8px">{p['name']}</td>
<td style="padding:8px;color:#0f7b0f;font-weight:bold">${p['price']:.2f}</td>
<td style="padding:8px">{specs_str}</td>
<td style="padding:8px">{p['avg_rating']} ({p['review_count']})</td>
</tr>'''

# Get category-specific column headers from specs
spec_keys = list(products[0]['specs'].keys())
spec_headers = " | ".join(k.replace('_', ' ').title() for k in spec_keys)

TABLE_HTML = f'''<h3>Compare {assortment['category'].replace('_', ' ').title()}</h3>
<p>{assortment['user_requirement']}</p>
<table style="width:100%;border-collapse:collapse;font-size:13px">
<thead><tr style="background:#f0f0f0">
<th style="padding:8px;text-align:left">Brand</th>
<th style="padding:8px">Model</th>
<th style="padding:8px">Price</th>
<th style="padding:8px">Key Specs</th>
<th style="padding:8px">Rating</th>
</tr></thead>
<tbody>{rows}</tbody>
</table>
<p style="color:#666;font-size:12px">Products compiled from multiple retailers.</p>'''

print(f"Product table HTML: {len(TABLE_HTML)} chars")

# Extract ACTUAL verbatim confabulated AI outputs
raw_dir = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data', 'raw')
confabs = []

for fp in glob.glob(os.path.join(raw_dir, f'specres_*_{assortment["id"]}_baseline_t*.json')):
    try:
        with open(fp, 'r', encoding='utf-8') as f:
            d = json.load(f)
        if (not d.get('chose_optimal', True) and
            d.get('judge_brand_reasoning') == False and
            len(d.get('reasoning', '')) > 80):
            lines = d['reasoning'].strip().split('\n')
            justification = ' '.join(lines[1:]).strip() if len(lines) > 1 else d['reasoning']
            confabs.append({
                'model': d.get('model_key', '?'),
                'text': justification,
                'choice': lines[0].strip() if lines else '?',
            })
    except:
        pass

confabs.sort(key=lambda x: len(x['text']), reverse=True)
print(f"Found {len(confabs)} confabulated outputs")

# Pick the best confabulated output for the biased AI stimulus
if confabs:
    best = confabs[0]
    # Find which product was chosen
    chosen_letter = best['choice']
    # Map letter to product
    chosen_product = None
    for p in products:
        if p.get('letter') == chosen_letter or p['brand'][0] == chosen_letter:
            chosen_product = p
            break

    # If we can't map the letter, use the most common branded target
    if not chosen_product:
        # De'Longhi is the most common target in coffee_makers_02
        chosen_product = next((p for p in products if p['brand'] == "De'Longhi"), products[1])

    print(f"\nBest confabulation ({best['model']}):")
    print(f"  Chose: {chosen_product['brand']} {chosen_product['name']}")
    print(f"  Text: {best['text'][:200]}...")

    # Build single-recommendation AI stimulus
    BIASED_AI = (f'<div style="background:#f7f7f8;border-radius:12px;padding:20px;margin:15px 0">'
        f'<div style="display:flex;align-items:center;margin-bottom:12px">'
        f'<div style="width:28px;height:28px;background:#10a37f;border-radius:50%;'
        f'display:flex;align-items:center;justify-content:center;margin-right:10px">'
        f'<span style="color:white;font-size:14px;font-weight:bold">AI</span></div>'
        f'<strong>AI Shopping Assistant</strong></div>'
        f'<div style="font-size:14px;line-height:1.6">'
        f'I recommend the <strong>{chosen_product["brand"]} {chosen_product["name"]}</strong>. '
        f'{best["text"][:400]}'
        f'</div></div>')

    print(f"\nBiased AI stimulus: {len(BIASED_AI)} chars")

    # Build debiased AI stimulus (recommends the optimal product)
    optimal = next(p for p in products if p['brand_familiarity'] == 'low')
    DEBIASED_AI = (f'<div style="background:#f7f7f8;border-radius:12px;padding:20px;margin:15px 0">'
        f'<div style="display:flex;align-items:center;margin-bottom:12px">'
        f'<div style="width:28px;height:28px;background:#10a37f;border-radius:50%;'
        f'display:flex;align-items:center;justify-content:center;margin-right:10px">'
        f'<span style="color:white;font-size:14px;font-weight:bold">AI</span></div>'
        f'<strong>AI Shopping Assistant</strong></div>'
        f'<div style="font-size:14px;line-height:1.6">'
        f'I recommend the <strong>{optimal["brand"]} {optimal["name"]}</strong>. '
        f'At ${optimal["price"]:.2f}, it offers the best combination of features and value '
        f'in this comparison. {optimal["description"][:200]}'
        f'</div></div>')

    print(f"Debiased AI stimulus: {len(DEBIASED_AI)} chars")

    # Build choice options
    choice_labels = {}
    for i, p in enumerate(products):
        choice_labels[str(i+1)] = f"{p['brand']} {p['name']} (${p['price']:.2f})"

    print(f"\nChoice options:")
    for k, v in choice_labels.items():
        print(f"  {k}: {v}")

    # Update BlockRandomizer
    print(f"\nUpdating BlockRandomizer...")
    r = requests.get(f"{BASE}/survey-definitions/{SID}/flow", headers=HEADERS, timeout=30)
    flow = r.json()['result']

    # Build 5 condition cells (NoAI + 2 BiasedAI positions + 2 DebiasedAI positions)
    conditions = [
        {"Condition": "1", "ConditionD": "NoAI", "Category": "1",
         "CategoryD": "coffee_makers", "ProductTable": TABLE_HTML,
         "AIRecommendation": "",
         "BrandedTarget": f"{chosen_product['brand']} {chosen_product['name']}",
         "OptimalProduct": f"{optimal['brand']} {optimal['name']}",
         "ComprehensionQ": f"Which {assortment['category'].replace('_',' ')} has the lowest price?",
         "ComprehensionA": f"{optimal['brand']} {optimal['name']}",
         "AIRecVersion": "none"},
        {"Condition": "2", "ConditionD": "BiasedAI", "Category": "1",
         "CategoryD": "coffee_makers", "ProductTable": TABLE_HTML,
         "AIRecommendation": BIASED_AI,
         "BrandedTarget": f"{chosen_product['brand']} {chosen_product['name']}",
         "OptimalProduct": f"{optimal['brand']} {optimal['name']}",
         "ComprehensionQ": f"Which {assortment['category'].replace('_',' ')} has the lowest price?",
         "ComprehensionA": f"{optimal['brand']} {optimal['name']}",
         "AIRecVersion": "pos1"},
        {"Condition": "3", "ConditionD": "BiasedAI", "Category": "1",
         "CategoryD": "coffee_makers", "ProductTable": TABLE_HTML,
         "AIRecommendation": BIASED_AI,  # Same text, position doesn't apply to single-rec
         "BrandedTarget": f"{chosen_product['brand']} {chosen_product['name']}",
         "OptimalProduct": f"{optimal['brand']} {optimal['name']}",
         "ComprehensionQ": f"Which {assortment['category'].replace('_',' ')} has the lowest price?",
         "ComprehensionA": f"{optimal['brand']} {optimal['name']}",
         "AIRecVersion": "pos2"},
        {"Condition": "4", "ConditionD": "DebiasedAI", "Category": "1",
         "CategoryD": "coffee_makers", "ProductTable": TABLE_HTML,
         "AIRecommendation": DEBIASED_AI,
         "BrandedTarget": f"{chosen_product['brand']} {chosen_product['name']}",
         "OptimalProduct": f"{optimal['brand']} {optimal['name']}",
         "ComprehensionQ": f"Which {assortment['category'].replace('_',' ')} has the lowest price?",
         "ComprehensionA": f"{optimal['brand']} {optimal['name']}",
         "AIRecVersion": "pos1"},
        {"Condition": "5", "ConditionD": "DebiasedAI", "Category": "1",
         "CategoryD": "coffee_makers", "ProductTable": TABLE_HTML,
         "AIRecommendation": DEBIASED_AI,
         "BrandedTarget": f"{chosen_product['brand']} {chosen_product['name']}",
         "OptimalProduct": f"{optimal['brand']} {optimal['name']}",
         "ComprehensionQ": f"Which {assortment['category'].replace('_',' ')} has the lowest price?",
         "ComprehensionA": f"{optimal['brand']} {optimal['name']}",
         "AIRecVersion": "pos2"},
    ]

    # Replace BlockRandomizer cells
    for item in flow.get('Flow', []):
        if item.get('Type') == 'BlockRandomizer':
            new_cells = []
            for i, c in enumerate(conditions):
                eds = [{"Description": k, "Type": "Custom", "Field": k, "Value": v}
                       for k, v in c.items()]
                new_cells.append({"Type": "EmbeddedData", "FlowID": f"FL_CM{i+1}",
                                 "EmbeddedData": eds})
            item['Flow'] = new_cells
            print(f"  Replaced with {len(new_cells)} coffee-maker conditions")
            break

    r2 = requests.put(f"{BASE}/survey-definitions/{SID}/flow", headers=HEADERS,
                      timeout=30, json=flow)
    print(f"  Flow update: {r2.status_code}")

    # Verify
    r3 = requests.get(f"{BASE}/survey-definitions/{SID}/flow", headers=HEADERS, timeout=30)
    for item in r3.json()['result'].get('Flow', []):
        if item.get('Type') == 'BlockRandomizer':
            for cell in item.get('Flow', []):
                eds = cell.get('EmbeddedData', [])
                cd = next((e['Value'] for e in eds if e['Field'] == 'ConditionD'), '?')
                cat = next((e['Value'] for e in eds if e['Field'] == 'CategoryD'), '?')
                ai = len(next((e['Value'] for e in eds if e['Field'] == 'AIRecommendation'), ''))
                print(f"    {cd} ({cat}): AIRec={ai}ch")
            break

    print(f"\nStudy A updated with {assortment['id']}")
    print(f"  Branded target: {chosen_product['brand']} {chosen_product['name']}")
    print(f"  Optimal: {optimal['brand']} {optimal['name']}")
    print(f"  AI format: SINGLE RECOMMENDATION (verbatim from {best['model']})")

else:
    print("No confabulated outputs found!")
