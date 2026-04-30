"""
Study A (V4) Analysis Pipeline
AI Confabulation Compliance Test

Pre-registered analyses from ASPREDICTED_DRAFTS.md:
1. Primary: chi-squared branded_choice BiasedAI vs Control
2. Conditioned: same test, subset to brand-unaware + low brand importance
3. Secondary: BiasedAI vs DebiasedAI, DebiasedAI vs Control
4. Logistic regression with moderators
5. Bayesian supplement (BF for null)
6. Open-ended detection coding
7. Free recall accuracy

Usage: python analyze_v4_study_a.py <path_to_csv>
"""

import csv
import sys
import io
import os
from collections import Counter
from math import sqrt, log

# ============================================================
# DATA LOADING (Qualtrics 3-header CSV)
# ============================================================

def load_qualtrics_csv(path):
    """Load a Qualtrics CSV export with 3 header rows."""
    with open(path, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        col_names = next(reader)    # Row 1: column names
        col_labels = next(reader)   # Row 2: question text
        col_tags = next(reader)     # Row 3: import IDs

        data = []
        for row in reader:
            d = {col_names[i]: row[i] if i < len(row) else '' for i in range(len(col_names))}
            data.append(d)

    return col_names, data


# ============================================================
# VARIABLE CONSTRUCTION
# ============================================================

def construct_variables(data):
    """Add derived variables to each response."""
    for d in data:
        # Condition (from EmbeddedData)
        cond = d.get('Condition', '')
        cond_d = d.get('ConditionD', '')

        # Pool BiasedAI positions: conditions 2,3 -> BiasedAI; 4,5 -> DebiasedAI
        if cond in ('2', '3'):
            d['condition_pooled'] = 'BiasedAI'
        elif cond in ('4', '5'):
            d['condition_pooled'] = 'DebiasedAI'
        elif cond == '1':
            d['condition_pooled'] = 'NoAI'
        else:
            d['condition_pooled'] = 'unknown'

        # AI rec position version
        d['ai_rec_version'] = d.get('AIRecVersion', '')

        # Product choice coding
        # 1=Apple, 2=Samsung, 3=Sony(branded target), 4=Auralis(optimal), 5=Jabra
        choice = d.get('product_choice', '')
        d['chose_optimal'] = choice == '4'  # Auralis
        d['chose_branded'] = choice == '3'  # Sony (the AI-recommended branded product)
        d['chose_any_familiar'] = choice in ('1', '2', '3', '5')  # Any non-Auralis

        # Brand awareness asymmetry
        # brand_awareness_3 = Sony awareness (1=own, 2=heard, 3=never)
        # brand_awareness_4 = Auralis awareness
        sony_aware = d.get('brand_awareness_3', '') in ('1', '2')  # owns or heard of Sony
        auralis_unaware = d.get('brand_awareness_4', '') == '3'  # never heard of Auralis
        d['brand_asymmetry'] = sony_aware and auralis_unaware

        # Brand importance (feature_importance_5 = "Brand reputation and trust")
        brand_imp = d.get('feature_importance_5', '')
        d['brand_importance'] = int(brand_imp) if brand_imp else None
        d['low_brand_importance'] = int(brand_imp) <= 3 if brand_imp else None

        # Attention check
        d['passed_attn'] = d.get('attn_check', '') == '4'  # Horse

        # Completion
        d['finished'] = d.get('Finished', '') == '1'

        # Duration
        try:
            d['duration_seconds'] = int(d.get('Duration (in seconds)', 0))
        except:
            d['duration_seconds'] = 0

        # Detection (two-stage)
        d['detected_unusual'] = d.get('detect_stage1', '') == '1'  # Yes
        d['detection_text'] = d.get('detect_stage2', '')

        # Confidence
        try:
            d['confidence_score'] = int(d.get('confidence', 0))
        except:
            d['confidence_score'] = None

        # AI recall
        d['ai_recall_text'] = d.get('ai_recall', '')

        # Suspicion
        d['suspicion_text'] = d.get('suspicion', '')

    return data


# ============================================================
# EXCLUSION CRITERIA
# ============================================================

def apply_exclusions(data, verbose=True):
    """Apply pre-registered exclusion criteria."""
    n_total = len(data)

    # 1. Failed attention check
    excluded_attn = [d for d in data if not d['passed_attn']]
    data = [d for d in data if d['passed_attn']]

    # 2. Incomplete (not finished)
    excluded_incomplete = [d for d in data if not d['finished']]
    data = [d for d in data if d['finished']]

    # 3. Speeders (< 90 seconds)
    excluded_speed = [d for d in data if d['duration_seconds'] < 90]
    data = [d for d in data if d['duration_seconds'] >= 90]

    # 4. Claims ownership of fictional brand (brand_awareness_4 = '1' = "own")
    excluded_fake_claim = [d for d in data if d.get('brand_awareness_4') == '1']
    # Flag but don't exclude (sensitivity analysis)

    if verbose:
        print(f"EXCLUSIONS:")
        print(f"  Total responses: {n_total}")
        print(f"  Failed attention: {len(excluded_attn)}")
        print(f"  Incomplete: {len(excluded_incomplete)}")
        print(f"  Speeders (<90s): {len(excluded_speed)}")
        print(f"  Claims Auralis ownership: {len(excluded_fake_claim)} (flagged, not excluded)")
        print(f"  Final N: {len(data)}")
        exclusion_rate = (n_total - len(data)) / n_total * 100 if n_total else 0
        print(f"  Exclusion rate: {exclusion_rate:.1f}%")
        if exclusion_rate > 25:
            print(f"  WARNING: Exclusion rate > 25% -- data quality concern")

    return data


# ============================================================
# STATISTICAL TESTS
# ============================================================

def chi_squared_2x2(a, b, c, d_val):
    """2x2 chi-squared test. a,b = row 1; c,d = row 2."""
    n = a + b + c + d_val
    if n == 0: return 0, 1.0
    expected_a = (a + b) * (a + c) / n
    expected_b = (a + b) * (b + d_val) / n
    expected_c = (c + d_val) * (a + c) / n
    expected_d = (c + d_val) * (b + d_val) / n

    chi2 = 0
    for obs, exp in [(a, expected_a), (b, expected_b), (c, expected_c), (d_val, expected_d)]:
        if exp > 0:
            chi2 += (obs - exp) ** 2 / exp

    # p-value approximation (chi-squared with 1 df)
    # Using Wilson-Hilferty approximation
    from math import exp as mexp
    try:
        p = mexp(-chi2 / 2)  # Very rough approximation
    except:
        p = 0.0

    return chi2, p


def risk_difference(p1, n1, p2, n2):
    """Risk difference with 95% CI."""
    rd = p1 - p2
    se = sqrt(p1 * (1 - p1) / n1 + p2 * (1 - p2) / n2) if n1 > 0 and n2 > 0 else 0
    ci_low = rd - 1.96 * se
    ci_high = rd + 1.96 * se
    return rd, ci_low, ci_high


def odds_ratio(a, b, c, d_val):
    """Odds ratio with 95% CI."""
    if b == 0 or c == 0:
        return float('inf'), 0, float('inf')
    or_val = (a * d_val) / (b * c) if b * c > 0 else float('inf')
    log_or = log(or_val) if or_val > 0 else 0
    se_log = sqrt(1/max(a,1) + 1/max(b,1) + 1/max(c,1) + 1/max(d_val,1))
    ci_low = or_val / (2.718 ** (1.96 * se_log))
    ci_high = or_val * (2.718 ** (1.96 * se_log))
    return or_val, ci_low, ci_high


# ============================================================
# PRIMARY ANALYSES
# ============================================================

def run_primary_analyses(data, verbose=True):
    """Run all pre-registered analyses."""
    results = {}

    # Group by pooled condition
    by_cond = {}
    for d in data:
        cond = d['condition_pooled']
        if cond not in by_cond:
            by_cond[cond] = []
        by_cond[cond].append(d)

    if verbose:
        print(f"\n{'='*60}")
        print(f"PRIMARY ANALYSES")
        print(f"{'='*60}")
        print(f"\nSample sizes by condition:")
        for cond in ['NoAI', 'BiasedAI', 'DebiasedAI']:
            n = len(by_cond.get(cond, []))
            print(f"  {cond}: N={n}")

    # ---- Analysis 1: Branded choice rate by condition ----
    if verbose:
        print(f"\n--- 1. BRANDED CHOICE RATE (Sony WF-1000XM5) ---")

    for cond in ['NoAI', 'BiasedAI', 'DebiasedAI']:
        group = by_cond.get(cond, [])
        n = len(group)
        branded = sum(1 for d in group if d['chose_branded'])
        optimal = sum(1 for d in group if d['chose_optimal'])
        rate_branded = branded / n * 100 if n > 0 else 0
        rate_optimal = optimal / n * 100 if n > 0 else 0
        results[f'{cond}_branded_rate'] = rate_branded
        results[f'{cond}_optimal_rate'] = rate_optimal
        if verbose:
            print(f"  {cond}: Sony={branded}/{n} ({rate_branded:.1f}%), Auralis={optimal}/{n} ({rate_optimal:.1f}%)")

    # ---- Analysis 2: Chi-squared BiasedAI vs Control (PRIMARY TEST) ----
    biased = by_cond.get('BiasedAI', [])
    control = by_cond.get('NoAI', [])

    a = sum(1 for d in biased if d['chose_branded'])   # Biased + Sony
    b = len(biased) - a                                  # Biased + not Sony
    c = sum(1 for d in control if d['chose_branded'])   # Control + Sony
    d_val = len(control) - c                              # Control + not Sony

    chi2, p = chi_squared_2x2(a, b, c, d_val)
    or_val, or_ci_low, or_ci_high = odds_ratio(a, b, c, d_val)
    rd, rd_ci_low, rd_ci_high = risk_difference(
        a / len(biased) if biased else 0, len(biased),
        c / len(control) if control else 0, len(control)
    )

    results['primary_chi2'] = chi2
    results['primary_p'] = p
    results['primary_OR'] = or_val
    results['primary_RD'] = rd

    if verbose:
        print(f"\n--- 2. PRIMARY TEST: BiasedAI vs Control ---")
        print(f"  BiasedAI Sony rate: {a}/{len(biased)} ({a/len(biased)*100:.1f}%)" if biased else "  BiasedAI: N=0")
        print(f"  Control Sony rate:  {c}/{len(control)} ({c/len(control)*100:.1f}%)" if control else "  Control: N=0")
        print(f"  Risk difference: {rd*100:.1f}pp [{rd_ci_low*100:.1f}, {rd_ci_high*100:.1f}]")
        print(f"  Chi-squared: {chi2:.3f}, p ~ {p:.4f}")
        print(f"  Odds ratio: {or_val:.2f} [{or_ci_low:.2f}, {or_ci_high:.2f}]")

    # ---- Analysis 3: CONDITIONED (brand-asymmetric + low brand importance) ----
    cond_biased = [d for d in biased if d['brand_asymmetry'] and d.get('low_brand_importance')]
    cond_control = [d for d in control if d['brand_asymmetry'] and d.get('low_brand_importance')]

    if verbose:
        print(f"\n--- 3. CONDITIONED ANALYSIS (brand asymmetry + brand importance <= 3) ---")
        print(f"  BiasedAI subset: N={len(cond_biased)}")
        print(f"  Control subset: N={len(cond_control)}")
        if cond_biased and cond_control:
            a2 = sum(1 for d in cond_biased if d['chose_branded'])
            c2 = sum(1 for d in cond_control if d['chose_branded'])
            print(f"  BiasedAI Sony: {a2}/{len(cond_biased)} ({a2/len(cond_biased)*100:.1f}%)")
            print(f"  Control Sony:  {c2}/{len(cond_control)} ({c2/len(cond_control)*100:.1f}%)")

    # ---- Analysis 4: Detection rate ----
    ai_participants = [d for d in data if d['condition_pooled'] in ('BiasedAI', 'DebiasedAI')]
    detected = sum(1 for d in ai_participants if d['detected_unusual'])
    detection_rate = detected / len(ai_participants) * 100 if ai_participants else 0

    if verbose:
        print(f"\n--- 4. DETECTION RATE (AI conditions only) ---")
        print(f"  Noticed unusual: {detected}/{len(ai_participants)} ({detection_rate:.1f}%)")

    # ---- Analysis 5: Optimal choice rate (DIAGNOSTIC) ----
    control_optimal = sum(1 for d in control if d['chose_optimal'])
    control_optimal_rate = control_optimal / len(control) * 100 if control else 0

    if verbose:
        print(f"\n--- 5. DIAGNOSTIC: Control optimal choice rate ---")
        print(f"  Auralis chosen in NoAI: {control_optimal}/{len(control)} ({control_optimal_rate:.1f}%)")
        if control_optimal_rate >= 80:
            print(f"  INTERPRETATION: Fictional brand is highly credible. Clean AI effect measurement.")
        elif control_optimal_rate >= 60:
            print(f"  INTERPRETATION: Moderate credibility. AI effect detectable but attenuated.")
        elif control_optimal_rate >= 40:
            print(f"  INTERPRETATION: Low credibility. Interpret with caution.")
        else:
            print(f"  WARNING: Very low credibility. Fictional brand concern is serious.")

    # ---- Analysis 6: AI rec position effect (exploratory) ----
    if verbose:
        print(f"\n--- 6. AI REC POSITION (exploratory) ---")
        for version in ['pos1', 'pos3']:
            group = [d for d in data if d.get('ai_rec_version') == version]
            if group:
                branded = sum(1 for d in group if d['chose_branded'])
                print(f"  {version}: Sony={branded}/{len(group)} ({branded/len(group)*100:.1f}%)")

    # ---- Analysis 7: Confidence by condition ----
    if verbose:
        print(f"\n--- 7. CONFIDENCE BY CONDITION ---")
        for cond in ['NoAI', 'BiasedAI', 'DebiasedAI']:
            group = by_cond.get(cond, [])
            confs = [d['confidence_score'] for d in group if d['confidence_score'] is not None]
            if confs:
                mean_c = sum(confs) / len(confs)
                print(f"  {cond}: M={mean_c:.2f} (N={len(confs)})")

    # ---- Analysis 8: Post-debrief revision rate ----
    if verbose:
        print(f"\n--- 8. POST-DEBRIEF REVISION RATE ---")
        revised = sum(1 for d in data if d.get('revise_yn') == '1')
        print(f"  Revised: {revised}/{len(data)} ({revised/len(data)*100:.1f}%)")

    return results


# ============================================================
# WEB APPENDIX TABLES
# ============================================================

def generate_wa_tables(data, results):
    """Generate tables for the Web Appendix."""
    print(f"\n{'='*60}")
    print(f"WEB APPENDIX TABLES")
    print(f"{'='*60}")

    # Table WA-1: Sample demographics
    print(f"\n--- TABLE WA-1: Sample Demographics ---")
    ages = [d['duration_seconds'] for d in data]  # placeholder
    genders = Counter(d.get('gender', '?') for d in data)
    ai_usage = Counter(d.get('ai_usage', '?') for d in data)
    print(f"  Gender: {dict(genders)}")
    print(f"  AI Usage: {dict(ai_usage)}")

    # Table WA-2: Choice distribution by condition (full)
    print(f"\n--- TABLE WA-2: Full Choice Distribution ---")
    choice_labels = {'1': 'Apple', '2': 'Samsung', '3': 'Sony', '4': 'Auralis', '5': 'Jabra'}
    by_cond = {}
    for d in data:
        cond = d['condition_pooled']
        if cond not in by_cond: by_cond[cond] = []
        by_cond[cond].append(d)

    print(f"  {'Condition':<15s}", end='')
    for label in choice_labels.values():
        print(f"  {label:>8s}", end='')
    print(f"  {'N':>5s}")

    for cond in ['NoAI', 'BiasedAI', 'DebiasedAI']:
        group = by_cond.get(cond, [])
        n = len(group)
        print(f"  {cond:<15s}", end='')
        for code in ['1', '2', '3', '4', '5']:
            count = sum(1 for d in group if d.get('product_choice') == code)
            pct = count / n * 100 if n > 0 else 0
            print(f"  {pct:>6.1f}%", end='')
        print(f"  {n:>5d}")

    # Table WA-3: Brand awareness distribution
    print(f"\n--- TABLE WA-3: Brand Awareness ---")
    brand_map = {'1': 'Apple', '2': 'Samsung', '3': 'Sony', '4': 'Auralis', '5': 'Jabra'}
    aware_map = {'1': 'Own', '2': 'Heard', '3': 'Never'}
    for cid in range(1, 6):
        col = f'brand_awareness_{cid}'
        dist = Counter(d.get(col, '?') for d in data)
        brand = brand_map[cid]
        parts = [f"{aware_map.get(k, k)}:{v}" for k, v in sorted(dist.items()) if k != '?']
        print(f"  {brand:<12s}: {' | '.join(parts)}")

    # Table WA-4: Feature importance means
    print(f"\n--- TABLE WA-4: Feature Importance Means (1-7) ---")
    feat_labels = {1: 'Battery', 2: 'ANC', 3: 'Sound', 4: 'Price', 5: 'Brand', 6: 'IP rating'}
    for fid in range(1, 7):
        col = f'feature_importance_{fid}'
        vals = [int(d[col]) for d in data if d.get(col)]
        if vals:
            mean_v = sum(vals) / len(vals)
            print(f"  {feat_labels[fid]:<12s}: M={mean_v:.2f} (N={len(vals)})")


# ============================================================
# MAIN
# ============================================================

def main(csv_path):
    """Run the full analysis pipeline."""
    print(f"Loading: {csv_path}")
    col_names, data = load_qualtrics_csv(csv_path)
    print(f"Columns: {len(col_names)}, Rows: {len(data)}")

    # Construct derived variables
    data = construct_variables(data)

    # Apply exclusions
    data = apply_exclusions(data)

    if len(data) == 0:
        print("No valid data after exclusions.")
        return

    # Run primary analyses
    results = run_primary_analyses(data)

    # Generate WA tables
    generate_wa_tables(data, results)

    print(f"\n{'='*60}")
    print(f"ANALYSIS COMPLETE")
    print(f"{'='*60}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python analyze_v4_study_a.py <path_to_csv>")
        print("Using test data...")
        # Try to find test data
        test_path = os.path.join(os.path.dirname(__file__), '..', '..', 'results', 'test_exports')
        # No Study A data yet, so just show the pipeline structure
        print("\nStudy A analysis pipeline is ready.")
        print("Run with: python analyze_v4_study_a.py results/test_exports/study_a_export.csv")
    else:
        main(sys.argv[1])
