"""
Study Y (V4) Analysis Pipeline
Transparency Remedy -- Disclosure Gradient

Pre-registered analyses:
1. Primary: Cochran-Armitage trend test across 5 ordered disclosure levels
2. Planned contrasts (Bonferroni): NoDis vs Control, Generic vs NoDis, Mechanism vs NoDis, Quantified vs NoDis
3. Per-protocol: conditioned on disclosure recall accuracy
4. Trust/policy measures by condition

Usage: python analyze_v4_study_y.py <path_to_csv>
"""

import csv
import sys
import os
from collections import Counter
from math import sqrt

def load_qualtrics_csv(path):
    with open(path, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        col_names = next(reader)
        next(reader)  # question text
        next(reader)  # import IDs
        data = [{col_names[i]: row[i] if i < len(row) else '' for i in range(len(col_names))} for row in reader]
    return col_names, data

def construct_variables(data):
    for d in data:
        cond = d.get('Condition', '')
        cond_d = d.get('ConditionD', '')
        d['condition_label'] = cond_d if cond_d else f'cond_{cond}'

        # Disclosure level (ordered)
        disclosure_order = {'NoAI': 0, 'AI_NoDis': 1, 'AI_Generic': 2, 'AI_Mechanism': 3, 'AI_Quantified': 4}
        d['disclosure_level'] = disclosure_order.get(cond_d, -1)

        # Product choice
        choice = d.get('product_choice', '')
        d['chose_branded'] = choice == '3'  # Sony
        d['chose_optimal'] = choice == '4'  # Auralis

        # Attention check
        d['passed_attn'] = d.get('attn_check', '') == '4'

        # Completion
        d['finished'] = d.get('Finished', '') == '1'

        # Disclosure recall
        d['recall_text'] = d.get('disclosure_recall', '')
        d['has_recall'] = bool(d['recall_text'].strip()) and d['recall_text'].strip().lower() != 'n/a'

        # Trust measures (Matrix: trust_policy_1 through _4)
        for i in range(1, 5):
            col = f'trust_policy_{i}'
            try:
                d[f'trust_{i}'] = int(d.get(col, 0))
            except:
                d[f'trust_{i}'] = None

    return data

def apply_exclusions(data):
    n = len(data)
    data = [d for d in data if d['passed_attn'] and d['finished']]
    print(f"Exclusions: {n} -> {len(data)} ({n - len(data)} excluded)")
    return data

def cochran_armitage_trend(groups, levels):
    """Simplified Cochran-Armitage trend test for proportions."""
    # groups: list of (n_success, n_total) per level
    # levels: ordered numeric levels (e.g., 0, 1, 2, 3, 4)
    N = sum(n for _, n in groups)
    if N == 0: return 0, 1.0

    p_bar = sum(s for s, _ in groups) / N
    scores = levels

    # Numerator
    num = sum(scores[i] * (groups[i][0] - groups[i][1] * p_bar) for i in range(len(groups)))

    # Denominator
    t_bar = sum(scores[i] * groups[i][1] for i in range(len(groups))) / N
    denom_sq = p_bar * (1 - p_bar) * sum(groups[i][1] * (scores[i] - t_bar) ** 2 for i in range(len(groups)))

    if denom_sq <= 0: return 0, 1.0
    Z = num / sqrt(denom_sq)

    # Two-sided p from Z (rough approximation)
    from math import exp, erf
    p = 1 - erf(abs(Z) / sqrt(2))  # one-sided
    return Z, p

def run_analyses(data):
    print(f"\n{'='*60}")
    print(f"STUDY Y ANALYSES")
    print(f"{'='*60}")

    # Group by condition
    by_cond = {}
    for d in data:
        label = d['condition_label']
        if label not in by_cond: by_cond[label] = []
        by_cond[label].append(d)

    # 1. Branded choice rate by condition
    print(f"\n--- 1. BRANDED CHOICE RATE BY DISCLOSURE LEVEL ---")
    cond_order = ['NoAI', 'AI_NoDis', 'AI_Generic', 'AI_Mechanism', 'AI_Quantified']
    groups = []
    for cond in cond_order:
        group = by_cond.get(cond, [])
        n = len(group)
        branded = sum(1 for d in group if d['chose_branded'])
        pct = branded / n * 100 if n > 0 else 0
        print(f"  {cond:16s}: {branded}/{n} ({pct:.1f}%)")
        groups.append((branded, n))

    # 2. Cochran-Armitage trend test (PRIMARY)
    print(f"\n--- 2. COCHRAN-ARMITAGE TREND TEST (PRIMARY) ---")
    Z, p = cochran_armitage_trend(groups, [0, 1, 2, 3, 4])
    print(f"  Z = {Z:.3f}, p = {p:.4f} (one-sided)")
    if p < 0.05:
        print(f"  SIGNIFICANT: Disclosure specificity reduces branded choice")
    else:
        print(f"  NOT SIGNIFICANT at alpha=0.05")

    # 3. Planned contrasts (Bonferroni alpha = 0.0125)
    print(f"\n--- 3. PLANNED CONTRASTS (Bonferroni alpha = 0.0125) ---")
    contrasts = [
        ('AI_NoDis vs NoAI', 'AI_NoDis', 'NoAI', 'AI compliance effect'),
        ('AI_Generic vs AI_NoDis', 'AI_Generic', 'AI_NoDis', 'Generic disclaimer effect'),
        ('AI_Mechanism vs AI_NoDis', 'AI_Mechanism', 'AI_NoDis', 'Mechanism disclosure effect'),
        ('AI_Quantified vs AI_NoDis', 'AI_Quantified', 'AI_NoDis', 'Quantified disclosure effect'),
    ]

    for name, cond1, cond2, interpretation in contrasts:
        g1 = by_cond.get(cond1, [])
        g2 = by_cond.get(cond2, [])
        n1, n2 = len(g1), len(g2)
        b1 = sum(1 for d in g1 if d['chose_branded'])
        b2 = sum(1 for d in g2 if d['chose_branded'])
        p1 = b1/n1 if n1 else 0
        p2 = b2/n2 if n2 else 0
        rd = (p1 - p2) * 100
        print(f"  {name}: {p1*100:.1f}% vs {p2*100:.1f}% (diff={rd:+.1f}pp) -- {interpretation}")

    # 4. Trust measures
    print(f"\n--- 4. TRUST MEASURES BY CONDITION ---")
    trust_labels = {1: 'Trust AI assistants', 2: 'Should disclose biases',
                    3: 'Support auditing', 4: 'Would verify independently'}
    for tid in range(1, 5):
        print(f"  {trust_labels[tid]}:")
        for cond in cond_order:
            group = by_cond.get(cond, [])
            vals = [d[f'trust_{tid}'] for d in group if d.get(f'trust_{tid}') is not None]
            if vals:
                mean_v = sum(vals) / len(vals)
                print(f"    {cond:16s}: M={mean_v:.2f} (N={len(vals)})")

    # 5. Disclosure recall (per-protocol)
    print(f"\n--- 5. PER-PROTOCOL ANALYSIS (disclosure recall) ---")
    for cond in ['AI_Generic', 'AI_Mechanism', 'AI_Quantified']:
        group = by_cond.get(cond, [])
        recalled = [d for d in group if d['has_recall']]
        n_recalled = len(recalled)
        n_total = len(group)
        print(f"  {cond}: {n_recalled}/{n_total} recalled the disclosure ({n_recalled/n_total*100:.0f}%)" if n_total else f"  {cond}: N=0")

    # 6. Optimal choice rate (diagnostic)
    print(f"\n--- 6. DIAGNOSTIC: Control optimal choice rate ---")
    control = by_cond.get('NoAI', [])
    optimal = sum(1 for d in control if d['chose_optimal'])
    print(f"  NoAI optimal: {optimal}/{len(control)} ({optimal/len(control)*100:.1f}%)" if control else "  N=0")


def main(csv_path):
    col_names, data = load_qualtrics_csv(csv_path)
    print(f"Loaded: {len(data)} rows, {len(col_names)} columns")
    data = construct_variables(data)
    data = apply_exclusions(data)
    if data:
        run_analyses(data)
    print(f"\n{'='*60}\nANALYSIS COMPLETE\n{'='*60}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python analyze_v4_study_y.py <path_to_csv>")
    else:
        main(sys.argv[1])
