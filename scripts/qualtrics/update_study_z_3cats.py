"""Update Study Z with 3 HIGH-BIAS categories for competition design."""
import sys, os, json, glob, requests, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))
from experiment.assortments import ALL_ASSORTMENTS

BASE = "https://pdx1.qualtrics.com/API/v3"
HEADERS = {"X-API-TOKEN": "Br4dAvcZOSSsJcup0AXpLDj7BjuGs1Pp96nNirWY",
           "Content-Type": "application/json"}
SID = "SV_esVf052AlAoqBiS"
RAW = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data', 'raw')

Z_ASSORTMENTS = ['sr_coffee_makers_02', 'sr_headphones_03', 'sr_earbuds_03']
z_conditions = []
cat_num = 0

for target in Z_ASSORTMENTS:
    cat_num += 1
    for a in ALL_ASSORTMENTS:
        if a['id'] != target:
            continue

        optimal = next(p for p in a['products'] if p['brand_familiarity'] == 'low')
        max_p = max(p['price'] for p in a['products'])

        # Build table
        rows = ''
        for p in a['products']:
            specs = ' | '.join(str(v) for v in p['specs'].values())
            rows += (f'<tr><td style="padding:8px;font-weight:bold">{p["brand"]}</td>'
                    f'<td style="padding:8px">{p["name"]}</td>'
                    f'<td style="padding:8px;color:#0f7b0f">${p["price"]:.2f}</td>'
                    f'<td style="padding:8px">{specs}</td>'
                    f'<td style="padding:8px">{p["avg_rating"]}</td></tr>')

        table = (f'<table style="width:100%;border-collapse:collapse;font-size:13px">'
                f'<thead><tr style="background:#f0f0f0">'
                f'<th style="padding:8px;text-align:left">Brand</th>'
                f'<th style="padding:8px">Model</th><th style="padding:8px">Price</th>'
                f'<th style="padding:8px">Specs</th><th style="padding:8px">Rating</th>'
                f'</tr></thead><tbody>{rows}</tbody></table>')

        # Find confabulated AI output
        confab_text = ''
        branded_name = ''
        for fp in glob.glob(os.path.join(RAW, f'specres_*_{target}_baseline_t*.json'))[:50]:
            try:
                with open(fp, 'r', encoding='utf-8') as f:
                    d = json.load(f)
                if (not d.get('chose_optimal', True) and d.get('judge_brand_reasoning') == False
                    and len(d.get('reasoning', '')) > 80):
                    lines = d['reasoning'].strip().split('\n')
                    confab_text = ' '.join(lines[1:]).strip() if len(lines) > 1 else d['reasoning']
                    for p in a['products']:
                        if p['brand'].lower() in confab_text.lower()[:100]:
                            branded_name = f"{p['brand']} {p['name']}"
                            break
                    if branded_name:
                        break
            except:
                pass

        if not branded_name:
            branded = max([p for p in a['products'] if p['brand_familiarity'] != 'low'],
                         key=lambda x: x['quality_score'])
            branded_name = f"{branded['brand']} {branded['name']}"
            confab_text = f"This product offers excellent quality for your needs."

        ai_rec = (f'<div style="background:#f7f7f8;border-radius:12px;padding:16px;margin:10px 0">'
                 f'<strong>AI Shopping Assistant:</strong> I recommend the <strong>{branded_name}</strong>. '
                 f'{confab_text[:250]}</div>')

        cat_label = a['category'].replace('_', ' ')
        opt_name = f"{optimal['brand']} {optimal['name']}"

        z_conditions.append({
            'Condition': str(cat_num*2-1), 'ConditionD': f'AI_{cat_label.replace(" ","_")}',
            'AICondition': 'AI', 'Category': str(cat_num), 'CategoryD': cat_label,
            'ProductTable': table, 'AIRecommendation': ai_rec,
            'BrandedTarget': branded_name, 'OptimalProduct': opt_name
        })
        z_conditions.append({
            'Condition': str(cat_num*2), 'ConditionD': f'NoAI_{cat_label.replace(" ","_")}',
            'AICondition': 'NoAI', 'Category': str(cat_num), 'CategoryD': cat_label,
            'ProductTable': table, 'AIRecommendation': '',
            'BrandedTarget': branded_name, 'OptimalProduct': opt_name
        })

        print(f"{target}: table={len(table)}ch, AI={len(ai_rec)}ch, branded={branded_name}")
        break

# Update flow
r = requests.get(f"{BASE}/survey-definitions/{SID}/flow", headers=HEADERS, timeout=30)
flow = r.json()['result']

for item in flow.get('Flow', []):
    if item.get('Type') == 'BlockRandomizer':
        item['Flow'] = [
            {"Type": "EmbeddedData", "FlowID": f"FL_ZC{i+1}",
             "EmbeddedData": [{"Description": k, "Type": "Custom", "Field": k, "Value": v}
                              for k, v in c.items()]}
            for i, c in enumerate(z_conditions)
        ]
        print(f"Replaced with {len(z_conditions)} conditions")
        break

r2 = requests.put(f"{BASE}/survey-definitions/{SID}/flow", headers=HEADERS, timeout=30, json=flow)
print(f"Flow update: {r2.status_code}")

# Verify
r3 = requests.get(f"{BASE}/survey-definitions/{SID}/flow", headers=HEADERS, timeout=30)
for item in r3.json()['result'].get('Flow', []):
    if item.get('Type') == 'BlockRandomizer':
        for cell in item.get('Flow', []):
            eds = cell.get('EmbeddedData', [])
            cd = next((e['Value'] for e in eds if e['Field'] == 'ConditionD'), '?')
            cat = next((e['Value'] for e in eds if e['Field'] == 'CategoryD'), '?')
            ai = len(next((e['Value'] for e in eds if e['Field'] == 'AIRecommendation'), ''))
            print(f"  {cd:30s} ({cat:15s}) AI={ai}ch")
        break
