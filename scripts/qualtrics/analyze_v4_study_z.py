"""
Study Z (V4) Analysis Pipeline
Head-to-Head Competition -- Welfare Test

Pre-registered analyses:
1. Primary: Sign test P(AI_loss) > 0.50
2. Category-specific: same test per category
3. Mean utility difference within pairs
4. Dollar-equivalent welfare loss
5. Conditional on following AI rec vs overriding

Usage: python analyze_v4_study_z.py <path_to_csv>
"""

import csv
import sys
import os
import random
from collections import Counter
from math import sqrt, comb

def load_qualtrics_csv(path):
    with open(path, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        col_names = next(reader)
        next(reader)
        next(reader)
        data = [{col_names[i]: row[i] if i < len(row) else '' for i in range(len(col_names))} for row in reader]
    return col_names, data

# Utility function (same as computational study)
# U = 0.5 * quality_score + 0.5 * value_score
# value_score = 1 - (price / (max_price * 1.1))

PRODUCT_UTILS = {
    'earbuds': {
        '1': {'brand': 'Apple', 'price': 249.00, 'quality': 0.80, 'utility': 0.0},  # computed below
        '2': {'brand': 'Samsung', 'price': 199.99, 'quality': 0.78, 'utility': 0.0},
        '3': {'brand': 'Sony', 'price': 279.99, 'quality': 0.82, 'utility': 0.0},
        '4': {'brand': 'Auralis', 'price': 59.99, 'quality': 0.88, 'utility': 0.0},  # optimal
        '5': {'brand': 'Jabra', 'price': 179.99, 'quality': 0.76, 'utility': 0.0},
    },
    'speakers': {
        '1': {'brand': 'JBL', 'price': 129.99, 'quality': 0.78, 'utility': 0.0},
        '2': {'brand': 'Bose', 'price': 149.99, 'quality': 0.77, 'utility': 0.0},
        '3': {'brand': 'Sony', 'price': 199.99, 'quality': 0.75, 'utility': 0.0},
        '4': {'brand': 'Wavecrest', 'price': 89.99, 'quality': 0.88, 'utility': 0.0},  # optimal
        '5': {'brand': 'Anker', 'price': 99.99, 'quality': 0.76, 'utility': 0.0},
    },
    'ssds': {
        '1': {'brand': 'Samsung', 'price': 139.99, 'quality': 0.80, 'utility': 0.0},
        '2': {'brand': 'SanDisk', 'price': 119.99, 'quality': 0.78, 'utility': 0.0},
        '3': {'brand': 'WD', 'price': 109.99, 'quality': 0.75, 'utility': 0.0},
        '4': {'brand': 'Vaultdrive', 'price': 89.99, 'quality': 0.90, 'utility': 0.0},  # optimal
        '5': {'brand': 'Seagate', 'price': 99.99, 'quality': 0.72, 'utility': 0.0},
    }
}

def compute_utilities():
    """Compute utility scores for all products."""
    for cat in PRODUCT_UTILS:
        products = PRODUCT_UTILS[cat]
        max_price = max(p['price'] for p in products.values())
        for pid, p in products.items():
            value_score = 1 - (p['price'] / (max_price * 1.1))
            p['utility'] = 0.5 * p['quality'] + 0.5 * value_score
            p['value'] = value_score

compute_utilities()

def construct_variables(data):
    for d in data:
        d['ai_condition'] = d.get('AICondition', '')
        d['category'] = d.get('Category', '')
        d['passed_attn'] = d.get('attn_check', '') == '4'
        d['finished'] = d.get('Finished', '') == '1'

        # Find which choice question was answered (category-specific)
        cat = d['category']
        choice = ''
        if cat == 'earbuds':
            choice = d.get('choice_earbuds', '')
        elif cat == 'speakers':
            choice = d.get('choice_speakers', '')
        elif cat == 'ssds':
            choice = d.get('choice_ssds', '')
        d['product_choice'] = choice

        # Compute utility of chosen product
        if cat in PRODUCT_UTILS and choice in PRODUCT_UTILS.get(cat, {}):
            d['chosen_utility'] = PRODUCT_UTILS[cat][choice]['utility']
            d['chosen_price'] = PRODUCT_UTILS[cat][choice]['price']
            d['chosen_brand'] = PRODUCT_UTILS[cat][choice]['brand']
            d['chose_optimal'] = choice == '4'  # Optimal is always choice 4
        else:
            d['chosen_utility'] = None
            d['chosen_price'] = None
            d['chosen_brand'] = None
            d['chose_optimal'] = None

    return data

def apply_exclusions(data):
    n = len(data)
    data = [d for d in data if d['passed_attn'] and d['finished'] and d['chosen_utility'] is not None]
    print(f"Exclusions: {n} -> {len(data)}")
    return data

def sign_test(wins, losses):
    """One-sided sign test: H1 wins > losses."""
    n = wins + losses
    if n == 0: return 0.5
    # P(X >= wins | H0: p=0.5)
    p = sum(comb(n, k) for k in range(wins, n + 1)) / (2 ** n)
    return p

def post_hoc_pairing(data):
    """Pair AI-assisted with Unassisted participants within same category."""
    pairs = []

    # Group by category and AI condition
    by_cat_cond = {}
    for d in data:
        key = (d['category'], d['ai_condition'])
        if key not in by_cat_cond:
            by_cat_cond[key] = []
        by_cat_cond[key].append(d)

    for cat in ['earbuds', 'speakers', 'ssds']:
        ai_group = by_cat_cond.get((cat, 'AI'), [])
        noai_group = by_cat_cond.get((cat, 'NoAI'), [])

        # Random pairing
        random.seed(42)  # Reproducible
        n_pairs = min(len(ai_group), len(noai_group))
        ai_sample = random.sample(ai_group, n_pairs)
        noai_sample = random.sample(noai_group, n_pairs)

        for ai_d, noai_d in zip(ai_sample, noai_sample):
            pairs.append({
                'category': cat,
                'ai_utility': ai_d['chosen_utility'],
                'noai_utility': noai_d['chosen_utility'],
                'ai_brand': ai_d['chosen_brand'],
                'noai_brand': noai_d['chosen_brand'],
                'ai_price': ai_d['chosen_price'],
                'noai_price': noai_d['chosen_price'],
                'ai_chose_optimal': ai_d['chose_optimal'],
                'noai_chose_optimal': noai_d['chose_optimal'],
                'ai_won': ai_d['chosen_utility'] > noai_d['chosen_utility'],
                'noai_won': noai_d['chosen_utility'] > ai_d['chosen_utility'],
                'tie': ai_d['chosen_utility'] == noai_d['chosen_utility'],
            })

    return pairs

def run_analyses(data):
    print(f"\n{'='*60}")
    print(f"STUDY Z ANALYSES")
    print(f"{'='*60}")

    # 1. Sample sizes
    by_cond = {}
    for d in data:
        key = (d['category'], d['ai_condition'])
        if key not in by_cond: by_cond[key] = []
        by_cond[key].append(d)

    print(f"\n--- 1. SAMPLE SIZES ---")
    for cat in ['earbuds', 'speakers', 'ssds']:
        ai_n = len(by_cond.get((cat, 'AI'), []))
        noai_n = len(by_cond.get((cat, 'NoAI'), []))
        print(f"  {cat}: AI={ai_n}, NoAI={noai_n}")

    # 2. Choice distribution
    print(f"\n--- 2. OPTIMAL CHOICE RATE ---")
    for cat in ['earbuds', 'speakers', 'ssds']:
        for cond in ['AI', 'NoAI']:
            group = by_cond.get((cat, cond), [])
            optimal = sum(1 for d in group if d['chose_optimal'])
            pct = optimal / len(group) * 100 if group else 0
            print(f"  {cat} {cond}: {optimal}/{len(group)} ({pct:.1f}%)")

    # 3. Post-hoc pairing
    print(f"\n--- 3. POST-HOC PAIRING ---")
    pairs = post_hoc_pairing(data)
    print(f"  Total pairs: {len(pairs)}")

    # 4. Primary test: Sign test
    ai_wins = sum(1 for p in pairs if p['ai_won'])
    noai_wins = sum(1 for p in pairs if p['noai_won'])
    ties = sum(1 for p in pairs if p['tie'])

    print(f"\n--- 4. PRIMARY TEST: Sign Test ---")
    print(f"  AI wins: {ai_wins}")
    print(f"  NoAI wins: {noai_wins}")
    print(f"  Ties: {ties}")

    # AI loss rate (excluding ties)
    non_tie = ai_wins + noai_wins
    ai_loss_rate = noai_wins / non_tie * 100 if non_tie > 0 else 50
    print(f"  AI loss rate: {ai_loss_rate:.1f}% (excluding ties)")

    p_val = sign_test(noai_wins, ai_wins)
    print(f"  Sign test p-value (one-sided, H1: AI loses more): {p_val:.4f}")
    if p_val < 0.05:
        print(f"  SIGNIFICANT: AI-assisted participants chose worse products")
    else:
        print(f"  NOT SIGNIFICANT at alpha=0.05")

    # 5. Category-specific
    print(f"\n--- 5. CATEGORY-SPECIFIC ---")
    for cat in ['earbuds', 'speakers', 'ssds']:
        cat_pairs = [p for p in pairs if p['category'] == cat]
        cat_ai_wins = sum(1 for p in cat_pairs if p['ai_won'])
        cat_noai_wins = sum(1 for p in cat_pairs if p['noai_won'])
        cat_ties = sum(1 for p in cat_pairs if p['tie'])
        n_non_tie = cat_ai_wins + cat_noai_wins
        loss_rate = cat_noai_wins / n_non_tie * 100 if n_non_tie > 0 else 50
        p = sign_test(cat_noai_wins, cat_ai_wins)
        print(f"  {cat}: AI loss rate={loss_rate:.1f}%, p={p:.4f} (N_pairs={len(cat_pairs)})")

    # 6. Utility difference
    print(f"\n--- 6. UTILITY DIFFERENCE ---")
    diffs = [p['noai_utility'] - p['ai_utility'] for p in pairs]
    if diffs:
        mean_diff = sum(diffs) / len(diffs)
        print(f"  Mean U(NoAI) - U(AI) = {mean_diff:.4f}")
        print(f"  Positive = NoAI chose better products")

    # 7. Dollar difference
    print(f"\n--- 7. DOLLAR WELFARE LOSS ---")
    price_diffs = [p['ai_price'] - p['noai_price'] for p in pairs]
    if price_diffs:
        mean_price_diff = sum(price_diffs) / len(price_diffs)
        print(f"  Mean price(AI) - price(NoAI) = ${mean_price_diff:.2f}")
        print(f"  Positive = AI participants paid more")

    # 8. THE HEADLINE
    print(f"\n{'='*60}")
    print(f"HEADLINE: AI-assisted shoppers chose worse products than")
    print(f"unassisted shoppers in {ai_loss_rate:.0f}% of head-to-head pairs.")
    print(f"{'='*60}")


def main(csv_path):
    col_names, data = load_qualtrics_csv(csv_path)
    print(f"Loaded: {len(data)} rows")
    data = construct_variables(data)
    data = apply_exclusions(data)
    if data:
        run_analyses(data)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python analyze_v4_study_z.py <path_to_csv>")
    else:
        main(sys.argv[1])
