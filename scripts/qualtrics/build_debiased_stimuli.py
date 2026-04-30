"""Build DEBIASED AI recommendations for all 5 categories.
These recommend the OPTIMAL product with accurate justification."""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))
from experiment.assortments import ALL_ASSORTMENTS

TOP = ['sr_headphones_03', 'sr_coffee_makers_02', 'sr_earbuds_03', 'sr_laptops_01', 'sr_smartphones_01']

out = ['# DEBIASED AI RECOMMENDATIONS',
       '## For Study A DebiasedAI condition — recommends the OPTIMAL product accurately', '']

for target in TOP:
    for a in ALL_ASSORTMENTS:
        if a['id'] != target:
            continue

        optimal = next(p for p in a['products'] if p['brand_familiarity'] == 'low')
        max_p = max(p['price'] for p in a['products'])

        # Build the debiased recommendation using ACTUAL specs
        specs_list = []
        for k, v in optimal['specs'].items():
            specs_list.append(f"{k.replace('_', ' ')}: {v}")
        specs_text = ", ".join(specs_list)

        # Find the most expensive branded competitor for contrast
        branded = max([p for p in a['products'] if p['brand_familiarity'] != 'low'],
                     key=lambda x: x['price'])

        debiased_text = (
            f"I recommend the <strong>{optimal['brand']} {optimal['name']}</strong>. "
            f"At ${optimal['price']:.2f}, it offers the best combination of features and value "
            f"in this comparison. {optimal['description'][:200]} "
            f"Compared to the {branded['brand']} {branded['name']} at ${branded['price']:.2f}, "
            f"it provides comparable or superior performance at a significantly lower price point."
        )

        debiased_html = (
            f'<div style="background:#f7f7f8;border-radius:12px;padding:20px;margin:15px 0">'
            f'<div style="display:flex;align-items:center;margin-bottom:12px">'
            f'<div style="width:28px;height:28px;background:#10a37f;border-radius:50%;'
            f'display:flex;align-items:center;justify-content:center;margin-right:10px">'
            f'<span style="color:white;font-size:14px;font-weight:bold">AI</span></div>'
            f'<strong>AI Shopping Assistant</strong></div>'
            f'<div style="font-size:14px;line-height:1.6">{debiased_text}</div></div>'
        )

        val = 1 - (optimal['price'] / (max_p * 1.1))
        util = 0.5 * optimal['quality_score'] + 0.5 * val

        out.append(f"## {a['id']} ({a['category']})")
        out.append(f"**Optimal:** {optimal['brand']} {optimal['name']} "
                   f"(${optimal['price']:.2f}, Q={optimal['quality_score']:.2f}, U={util:.3f})")
        out.append('')
        out.append('### Debiased AI Recommendation HTML')
        out.append('```html')
        out.append(debiased_html)
        out.append('```')
        out.append(f'*Length: {len(debiased_html)} chars*')
        out.append('')
        out.append('### Plain text (for reference)')
        out.append(f'> {debiased_text}')
        out.append('')
        out.append('---')
        out.append('')
        break

# Save
path = os.path.join(os.path.dirname(__file__), '..', '..', 'results', 'DEBIASED_STIMULI.md')
with open(path, 'w', encoding='utf-8') as f:
    f.write('\n'.join(out))

print(f"Saved DEBIASED_STIMULI.md ({len(out)} lines)")
for target in TOP:
    for a in ALL_ASSORTMENTS:
        if a['id'] == target:
            optimal = next(p for p in a['products'] if p['brand_familiarity'] == 'low')
            print(f"  {target}: {optimal['brand']} {optimal['name']} (${optimal['price']:.2f})")
            break
