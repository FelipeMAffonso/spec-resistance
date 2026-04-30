"""Extract product details and stimuli for 5 high-bias categories."""
import sys, json, glob, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))
from experiment.assortments import ALL_ASSORTMENTS

TOP = ['sr_headphones_03', 'sr_coffee_makers_02', 'sr_earbuds_03', 'sr_laptops_01', 'sr_smartphones_01']

out = ['# STIMULI FOR 5-CATEGORY HUMAN STUDIES',
       '## Extracted from 382K computational study assortments',
       '## These are the HIGH-BIAS assortments where LLMs show the most brand preference', '']

for target in TOP:
    for a in ALL_ASSORTMENTS:
        if a['id'] == target:
            out.append(f"## {a['id']} ({a['category']})")
            out.append(f"**User requirement:** {a['user_requirement']}")
            out.append('')

            max_p = max(p['price'] for p in a['products'])
            for p in a['products']:
                val = 1 - (p['price'] / (max_p * 1.1))
                util = 0.5 * p['quality_score'] + 0.5 * val
                opt = ' **OPTIMAL**' if p['brand_familiarity'] == 'low' else ''
                specs = ', '.join(f"{k}: {v}" for k, v in p['specs'].items())

                out.append(f"**{p['brand']} {p['name']}** (${p['price']:.2f})")
                out.append(f"- Quality: {p['quality_score']:.2f} | Utility: {util:.3f} | Familiarity: {p['brand_familiarity']}{opt}")
                out.append(f"- Specs: {specs}")
                out.append(f"- {p['description'][:150]}")
                out.append('')

            # Get non-optimal rate
            raw_dir = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data', 'raw')
            n_opt = n_nonopt = n_confab = 0
            best_confabs = []
            for fp in glob.glob(os.path.join(raw_dir, f'specres_*_{target}_baseline_t*.json')):
                try:
                    with open(fp, 'r', encoding='utf-8') as f:
                        d = json.load(f)
                    if d.get('chose_optimal', False):
                        n_opt += 1
                    else:
                        n_nonopt += 1
                        if d.get('judge_brand_reasoning') == False and len(d.get('reasoning', '')) > 80:
                            n_confab += 1
                            lines = d['reasoning'].strip().split('\n')
                            justification = ' '.join(lines[1:]).strip() if len(lines) > 1 else d['reasoning']
                            best_confabs.append({
                                'model': d.get('model_key', '?'),
                                'text': justification[:300],
                                'familiarity': d.get('chosen_brand_familiarity', '?')
                            })
                except:
                    pass

            total = n_opt + n_nonopt
            rate = n_nonopt / total * 100 if total > 0 else 0
            out.append(f"**Non-optimal rate:** {rate:.1f}% ({n_nonopt}/{total}), {n_confab} confabulated")
            out.append('')

            # Show top 3 confabulated outputs
            best_confabs.sort(key=lambda x: len(x['text']), reverse=True)
            out.append("### Example confabulated AI outputs (verbatim from 382K):")
            for i, c in enumerate(best_confabs[:3]):
                out.append(f'**Example {i+1}** ({c["model"]}, {c["familiarity"]} familiarity):')
                out.append(f'> "{c["text"]}"')
                out.append('')

            out.append('---')
            out.append('')
            break

# Summary table
out.append('## SUMMARY')
out.append('')
out.append('| Category | Assortment | Non-opt% | Optimal brand | Top branded target | Confabulations |')
out.append('|----------|-----------|---------|---------------|-------------------|----------------|')

for target in TOP:
    for a in ALL_ASSORTMENTS:
        if a['id'] == target:
            optimal = [p for p in a['products'] if p['brand_familiarity'] == 'low'][0]
            non_opt = [p for p in a['products'] if p['brand_familiarity'] != 'low']
            branded = max(non_opt, key=lambda x: x['quality_score'])

            raw_dir = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data', 'raw')
            n_opt = n_nonopt = n_confab = 0
            for fp in glob.glob(os.path.join(raw_dir, f'specres_*_{target}_baseline_t*.json')):
                try:
                    with open(fp, 'r', encoding='utf-8') as f:
                        d = json.load(f)
                    if d.get('chose_optimal', False):
                        n_opt += 1
                    else:
                        n_nonopt += 1
                        if d.get('judge_brand_reasoning') == False:
                            n_confab += 1
                except:
                    pass
            total = n_opt + n_nonopt
            rate = n_nonopt / total * 100 if total > 0 else 0
            out.append(f"| {a['category']} | {target} | {rate:.1f}% | {optimal['brand']} | {branded['brand']} | {n_confab} |")
            break

# Save
output_path = os.path.join(os.path.dirname(__file__), '..', '..', 'results', 'STIMULI_5_CATEGORIES.md')
with open(output_path, 'w', encoding='utf-8') as f:
    f.write('\n'.join(out))

print(f"Saved STIMULI_5_CATEGORIES.md ({len(out)} lines)")
print()

# Print summary
for target in TOP:
    for a in ALL_ASSORTMENTS:
        if a['id'] == target:
            max_p = max(p['price'] for p in a['products'])
            optimal = [p for p in a['products'] if p['brand_familiarity'] == 'low'][0]
            val_o = 1 - (optimal['price'] / (max_p * 1.1))
            u_o = 0.5 * optimal['quality_score'] + 0.5 * val_o
            print(f"{target:25s}: Optimal={optimal['brand']:15s} ${optimal['price']:>7.2f} (U={u_o:.3f})")
            for p in a['products']:
                if p['brand_familiarity'] != 'low':
                    val = 1 - (p['price'] / (max_p * 1.1))
                    util = 0.5 * p['quality_score'] + 0.5 * val
                    print(f"  {'':25s}  {p['brand']:15s} ${p['price']:>7.2f} (U={util:.3f}) [{p['brand_familiarity']}]")
            print()
            break
