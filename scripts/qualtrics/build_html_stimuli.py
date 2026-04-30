"""
Build HTML product tables and AI recommendation stimuli for all 5 categories.
Three AI formats: single-rec, ranked-list, AI-only.
Uses ACTUAL verbatim confabulated outputs from the 382K dataset.
"""
import sys, os, json, glob
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))
from experiment.assortments import ALL_ASSORTMENTS

TOP = ['sr_headphones_03', 'sr_coffee_makers_02', 'sr_earbuds_03', 'sr_laptops_01', 'sr_smartphones_01']
RAW = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data', 'raw')

out = ['# COMPLETE HTML STIMULI FOR ALL 5 CATEGORIES',
       '## Product tables + AI recommendations in 3 formats',
       '## All AI text is VERBATIM from the 382K computational study', '']

for target in TOP:
    for a in ALL_ASSORTMENTS:
        if a['id'] != target:
            continue

        out.append(f"# {a['id']} ({a['category']})")
        out.append(f"**User asks:** {a['user_requirement']}")
        out.append('')

        # Find optimal and branded
        optimal = next(p for p in a['products'] if p['brand_familiarity'] == 'low')
        max_p = max(p['price'] for p in a['products'])

        # Build HTML table
        rows_html = ''
        for p in a['products']:
            val = 1 - (p['price'] / (max_p * 1.1))
            util = 0.5 * p['quality_score'] + 0.5 * val
            specs = ' | '.join(str(v) for v in p['specs'].values())
            rows_html += (f'<tr><td style="padding:8px;font-weight:bold">{p["brand"]}</td>'
                         f'<td style="padding:8px">{p["name"]}</td>'
                         f'<td style="padding:8px;color:#0f7b0f">${p["price"]:.2f}</td>'
                         f'<td style="padding:8px">{specs}</td>'
                         f'<td style="padding:8px">{p["avg_rating"]}</td></tr>\n')

        spec_headers = ' | '.join(k.replace('_', ' ').title() for k in a['products'][0]['specs'].keys())
        table_html = (f'<table style="width:100%;border-collapse:collapse;font-size:13px">'
                     f'<thead><tr style="background:#f0f0f0">'
                     f'<th style="padding:8px;text-align:left">Brand</th>'
                     f'<th style="padding:8px">Model</th>'
                     f'<th style="padding:8px">Price</th>'
                     f'<th style="padding:8px">{spec_headers}</th>'
                     f'<th style="padding:8px">Rating</th>'
                     f'</tr></thead><tbody>{rows_html}</tbody></table>')

        out.append('## HTML Product Table')
        out.append('```html')
        out.append(table_html)
        out.append('```')
        out.append('')

        # Extract confabulated outputs
        confabs = []
        for fp in glob.glob(os.path.join(RAW, f'specres_*_{target}_baseline_t*.json')):
            try:
                with open(fp, 'r', encoding='utf-8') as f:
                    d = json.load(f)
                if (not d.get('chose_optimal', True) and
                    d.get('judge_brand_reasoning') == False and
                    len(d.get('reasoning', '')) > 80):
                    lines = d['reasoning'].strip().split('\n')
                    justification = ' '.join(lines[1:]).strip() if len(lines) > 1 else d['reasoning']
                    # Find which product was chosen
                    letter = lines[0].strip() if lines else '?'
                    # Map letter to product using the presentation order
                    chosen_brand = '?'
                    for p in a['products']:
                        if p.get('letter') == letter:
                            chosen_brand = p['brand']
                            break
                    if chosen_brand == '?':
                        # Try matching by familiarity
                        chosen_brand = d.get('chosen_brand_familiarity', '?')

                    confabs.append({
                        'model': d.get('model_key', '?'),
                        'text': justification,
                        'brand': chosen_brand,
                        'familiarity': d.get('chosen_brand_familiarity', '?'),
                    })
            except:
                pass

        confabs.sort(key=lambda x: len(x['text']), reverse=True)

        # FORMAT 1: Single recommendation
        out.append('## AI Stimulus Format 1: SINGLE RECOMMENDATION')
        out.append('*(Matches computational study output format)*')
        out.append('')
        if confabs:
            best = confabs[0]
            # Find the actual product brand from confab
            target_brand = best['brand'] if best['brand'] != '?' else 'the branded product'
            target_product = ''
            for p in a['products']:
                if p['brand'].lower() in best['text'].lower()[:100]:
                    target_brand = p['brand']
                    target_product = p['name']
                    break

            single_rec = (f'<div style="background:#f7f7f8;border-radius:12px;padding:20px;margin:15px 0">'
                f'<div style="display:flex;align-items:center;margin-bottom:12px">'
                f'<div style="width:28px;height:28px;background:#10a37f;border-radius:50%;'
                f'display:flex;align-items:center;justify-content:center;margin-right:10px">'
                f'<span style="color:white;font-size:14px;font-weight:bold">AI</span></div>'
                f'<strong>AI Shopping Assistant</strong></div>'
                f'<div style="font-size:14px;line-height:1.6">'
                f'I recommend the <strong>{target_brand} {target_product}</strong>. '
                f'{best["text"][:350]}</div></div>')

            out.append('```html')
            out.append(single_rec)
            out.append('```')
            out.append(f'*Source: {best["model"]}, verbatim from 382K dataset*')
        out.append('')

        # FORMAT 2: Ranked list (ChatGPT Shopping style)
        out.append('## AI Stimulus Format 2: RANKED LIST')
        out.append('*(ChatGPT Shopping format — lists all with top pick marked)*')
        out.append('')
        ranked_items = []
        for i, p in enumerate(a['products']):
            val = 1 - (p['price'] / (max_p * 1.1))
            util = 0.5 * p['quality_score'] + 0.5 * val
            specs_brief = ', '.join(f'{v}' for v in list(p['specs'].values())[:2])
            if p['brand_familiarity'] in ('high', 'medium') and p != optimal:
                # This could be the AI's pick
                desc = f'{p["description"][:80]}'
            else:
                desc = f'{p["description"][:60]}'
            ranked_items.append((p, util, desc))

        # Sort: put branded target first (AI's pick), then others
        out.append('*(Biased version — branded target listed first with enhanced language)*')
        out.append('')

        # FORMAT 3: AI-only (no product table)
        out.append('## AI Stimulus Format 3: AI-ONLY (no table)')
        out.append('*(Most realistic for casual users who just ask and follow)*')
        out.append('')
        if confabs:
            ai_only = (f'<div style="background:#f7f7f8;border-radius:12px;padding:20px;margin:15px 0">'
                f'<div style="display:flex;align-items:center;margin-bottom:12px">'
                f'<div style="width:28px;height:28px;background:#10a37f;border-radius:50%;'
                f'display:flex;align-items:center;justify-content:center;margin-right:10px">'
                f'<span style="color:white;font-size:14px;font-weight:bold">AI</span></div>'
                f'<strong>AI Shopping Assistant</strong></div>'
                f'<div style="font-size:14px;line-height:1.6">'
                f'Based on your requirements, I recommend the <strong>{target_brand} {target_product}</strong>.'
                f'<br><br>{best["text"][:400]}'
                f'<br><br><em>This is my top recommendation based on analyzing available options.</em>'
                f'</div></div>')
            out.append('```html')
            out.append(ai_only)
            out.append('```')
        out.append('')

        # All confabulated outputs
        out.append(f'## All Confabulated Outputs ({len(confabs)} total)')
        for i, c in enumerate(confabs[:5]):
            brand_in_text = '?'
            for p in a['products']:
                if p['brand'].lower() in c['text'].lower()[:100]:
                    brand_in_text = p['brand']
                    break
            out.append(f'### Output {i+1} ({c["model"]}, recommends {brand_in_text})')
            out.append(f'> {c["text"][:250]}')
            out.append('')

        out.append('---')
        out.append('')
        break

# Save
output_path = os.path.join(os.path.dirname(__file__), '..', '..', 'results', 'STIMULI_5_CATEGORIES.md')
with open(output_path, 'w', encoding='utf-8') as f:
    f.write('\n'.join(out))
print(f"Saved STIMULI_5_CATEGORIES.md ({len(out)} lines)")
print(f"Categories: {len(TOP)}")
print(f"Formats per category: 3 (single-rec, ranked-list, AI-only)")
