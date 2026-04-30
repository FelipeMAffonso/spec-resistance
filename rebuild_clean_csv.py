#!/usr/bin/env python3
"""
Authoritative CSV rebuild for spec-resistance experiment.
Reads ALL raw JSON files, validates every record, filters to 34 sr_ assortments,
and produces a single clean CSV for analysis.

Data quality notes (documented from full audit):
- 382,680 rows expected: 18 models x 34 assortments x 32 conditions x ~20 trials
- 987 parsing failures (choice="?") — coded as chose_optimal=False, kept in data
- 172 files missing judge_model field — handled with .get() default
- 597 files with empty raw_response — model returned nothing, choice="?", kept
- 0 utility mismatches in sr_ assortments (450 in existing_ excluded)
- 0 duplicates, 0 chose_optimal mismatches
- response_text field does NOT exist in any file; all data in raw_response
- reasoning field = copy of raw_response in all files

Output: data/processed/spec_resistance_CLEAN.csv
"""
import csv
import glob
import json
import os
import re
import sys
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add project root to path for parser import
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness.shopping_agent import parse_product_choice
from experiment.assortments import CATEGORY_METADATA


def _extract_product_names(user_message: str) -> dict[str, str]:
    """Extract product letter→name mapping from the user_message text."""
    names = {}
    for m in re.finditer(r'---\s*Product\s+([A-E])\s*---\s*\nName:\s*(.+)', user_message):
        names[m.group(1)] = m.group(2).strip()
    return names

# ── CSV schema: all fields needed for analysis ──
CSV_FIELDS = [
    # Identifiers
    "trial_id", "model_key", "provider", "model_id",
    "assortment_id", "category",
    # Condition
    "condition", "condition_type", "condition_precision", "condition_ordinal",
    # Choice outcome
    "choice", "original_choice", "optimal_product", "original_optimal",
    "chose_optimal", "chose_branded",
    "chosen_brand_familiarity", "chosen_position", "utility_loss",
    "override_occurred", "specification_resistance",
    "optimal_utility",
    # Presentation
    "presentation_order", "optimal_display_position", "letter_mapping",
    "paraphrase_index", "brand_reversal",
    # Model config
    "thinking", "temperature",
    # Cost & performance
    "cost_usd", "input_tokens", "output_tokens", "duration_seconds",
    # Judge scores
    "judge_coherence", "judge_spec_acknowledgment", "judge_brand_reasoning",
    "judge_model",
    # Response text (for qualitative analysis)
    "raw_response", "reasoning", "thinking_trace",
    # Category metadata (derived from CATEGORY_METADATA in assortments.py)
    "involvement_level", "brand_salience", "processing_mode", "hedonic",
    # Derived analysis columns (computed from JSON fields)
    "chosen_utility", "utility_rank", "response_length", "thinking_length",
    "n_products_mentioned",
    # Per-product utility scores
    "utility_A", "utility_B", "utility_C", "utility_D", "utility_E",
    # Per-product identity (parsed from user_message)
    "product_A_name", "product_A_brand", "product_A_price", "product_A_sustainability",
    "product_B_name", "product_B_brand", "product_B_price", "product_B_sustainability",
    "product_C_name", "product_C_brand", "product_C_price", "product_C_sustainability",
    "product_D_name", "product_D_brand", "product_D_price", "product_D_sustainability",
    "product_E_name", "product_E_brand", "product_E_price", "product_E_sustainability",
    # Full prompts (for data sharing / replication)
    "system_prompt", "user_message",
    # Timestamp
    "timestamp",
]


def read_one(fpath):
    """Read one JSON file. Returns (dict, None) on success, (None, error_str) on failure."""
    try:
        with open(fpath, encoding="utf-8") as f:
            d = json.load(f)
    except Exception as e:
        return None, f"JSON_ERROR: {os.path.basename(fpath)}: {e}"

    # Must have model_key
    mk = d.get("model_key", "")
    if not isinstance(mk, str) or not mk:
        return None, f"NO_MODEL_KEY: {os.path.basename(fpath)}"

    # Filter: sr_ assortments only
    aid = d.get("assortment_id", "")
    if not aid.startswith("sr_"):
        return None, None  # Not an error, just filtered out

    # ── Re-parse the raw response with the fixed parser ──
    raw_response = d.get("raw_response", "")
    user_message = d.get("user_message", "")
    product_names = _extract_product_names(user_message)
    optimal_letter = d.get("optimal_product", "?")
    letter_mapping = d.get("letter_mapping", {})

    if raw_response and raw_response.strip():
        parsed = parse_product_choice(raw_response, product_names=product_names)
        new_choice = parsed["choice"]
    else:
        new_choice = "?"

    # Recompute derived fields based on new choice
    old_choice = d.get("choice", "?")
    d["choice"] = new_choice
    d["original_choice"] = letter_mapping.get(new_choice, new_choice)
    d["chose_optimal"] = (new_choice == optimal_letter)

    # Recompute utility_loss
    utility_scores = d.get("utility_scores", {})
    if isinstance(utility_scores, str):
        try:
            utility_scores = json.loads(utility_scores)
        except (json.JSONDecodeError, TypeError):
            utility_scores = {}
    optimal_utility = d.get("optimal_utility", 0)
    if isinstance(optimal_utility, str):
        try:
            optimal_utility = float(optimal_utility)
        except (ValueError, TypeError):
            optimal_utility = 0
    chosen_utility = utility_scores.get(new_choice, 0)
    d["utility_loss"] = round(max(0, optimal_utility - chosen_utility), 4) if not d["chose_optimal"] else 0.0

    # Recompute override_occurred
    condition = d.get("condition", "")
    d["override_occurred"] = (not d["chose_optimal"] and condition in [
        "utility_explicit", "utility_override", "utility_constrained",
        "preference_explicit", "preference_override", "preference_constrained",
        "control_brand_reversal",
    ])

    # Track re-parse changes for audit
    if old_choice != new_choice:
        d["_reparse_changed"] = f"{old_choice}->{new_choice}"

    # Populate category metadata from CATEGORY_METADATA
    cat = d.get("category", "")
    cat_meta = CATEGORY_METADATA.get(cat, {})
    d["involvement_level"] = cat_meta.get("involvement", "")
    d["brand_salience"] = cat_meta.get("brand_salience", "")
    d["processing_mode"] = cat_meta.get("processing", "")
    d["hedonic"] = str(cat_meta.get("hedonic", "")) if "hedonic" in cat_meta else ""

    # Derive analysis columns
    d["chosen_utility"] = round(chosen_utility, 4) if chosen_utility else 0
    if utility_scores and new_choice != "?":
        ranked = sorted(utility_scores.values(), reverse=True)
        d["utility_rank"] = ranked.index(chosen_utility) + 1 if chosen_utility in ranked else ""
    else:
        d["utility_rank"] = ""
    d["response_length"] = len(raw_response) if raw_response else 0
    d["thinking_length"] = len(d.get("thinking_trace", "") or "")
    # Count how many distinct product letters (A-E) appear in the response
    if raw_response:
        mentioned = set()
        for letter in ["A", "B", "C", "D", "E"]:
            if f"Product {letter}" in raw_response or f"product {letter}" in raw_response:
                mentioned.add(letter)
        # Also count product names mentioned
        for ltr, name in product_names.items():
            if name and name.lower() in raw_response.lower():
                mentioned.add(ltr)
        d["n_products_mentioned"] = len(mentioned)
    else:
        d["n_products_mentioned"] = 0

    # Per-product utility scores (A through E)
    for letter in ["A", "B", "C", "D", "E"]:
        d[f"utility_{letter}"] = round(utility_scores.get(letter, 0), 4)

    # Full prompts — already in d from JSON, just ensure they exist
    d.setdefault("system_prompt", "")
    d.setdefault("user_message", "")

    # Per-product identity (parsed from user_message)
    for pm in re.finditer(
        r'--- Product ([A-E]) ---\s*\nName:\s*(.+)\nBrand:\s*(.+)\nPrice:\s*(.+?)(?:\n|$)',
        user_message
    ):
        ltr = pm.group(1)
        d[f"product_{ltr}_name"] = pm.group(2).strip()
        d[f"product_{ltr}_brand"] = pm.group(3).strip()
        d[f"product_{ltr}_price"] = pm.group(4).strip()
    # Sustainability ratings (separate pass — present in most conditions)
    for sm in re.finditer(
        r'--- Product ([A-E]) ---.*?Sustainability(?: rating)?:\s*([0-9.]+)',
        user_message, re.DOTALL
    ):
        d[f"product_{sm.group(1)}_sustainability"] = sm.group(2)

    # Build row with safe .get() for every field (handles 47-key schema)
    row = {}
    for k in CSV_FIELDS:
        val = d.get(k, "")
        # Convert complex types to string for CSV
        if isinstance(val, (dict, list)):
            val = json.dumps(val)
        elif val is None:
            val = ""
        elif isinstance(val, bool):
            val = str(val)
        row[k] = val

    # Keep _reparse_changed as metadata (not in CSV, used for audit)
    row["_reparse_changed"] = d.get("_reparse_changed", "")

    return row, None


def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    raw_dir = os.path.join(base_dir, "data", "raw")
    out_dir = os.path.join(base_dir, "data", "processed")
    csv_path = os.path.join(out_dir, "spec_resistance_CLEAN.csv")

    os.makedirs(out_dir, exist_ok=True)

    t0 = time.time()

    # ── Phase 1: Discover files ──
    files = glob.glob(os.path.join(raw_dir, "specres_*.json"))
    print(f"Phase 1: Found {len(files):,} JSON files ({time.time()-t0:.1f}s)")

    # ── Phase 2: Read all files with 32 threads ──
    rows = []
    errors = []
    filtered = 0

    print(f"Phase 2: Reading with 32 threads...")
    with ThreadPoolExecutor(max_workers=32) as pool:
        futures = {pool.submit(read_one, f): f for f in files}
        done_count = 0
        for future in as_completed(futures):
            done_count += 1
            row, err = future.result()
            if err:
                errors.append(err)
            elif row is None:
                filtered += 1  # Non-sr_ file, filtered out
            else:
                rows.append(row)
            if done_count % 50000 == 0:
                elapsed = time.time() - t0
                rate = done_count / elapsed
                eta = (len(files) - done_count) / rate if rate > 0 else 0
                print(f"  {done_count:>7,}/{len(files):,}  "
                      f"kept={len(rows):,}  filtered={filtered:,}  "
                      f"errors={len(errors)}  "
                      f"{rate:.0f} files/s  ETA {eta:.0f}s")

    elapsed = time.time() - t0
    print(f"\nRead complete in {elapsed:.1f}s:")
    print(f"  Total files:  {len(files):,}")
    print(f"  Kept (sr_):   {len(rows):,}")
    print(f"  Filtered out: {filtered:,}")
    print(f"  Errors:       {len(errors)}")

    if errors:
        print(f"\nErrors:")
        for e in errors[:20]:
            print(f"  {e}")
        if len(errors) > 20:
            print(f"  ... and {len(errors)-20} more")

    # ── Phase 3: Validate ──
    print(f"\nPhase 3: Validation...")

    # 3a. Model counts
    model_counts = Counter(r["model_key"] for r in rows)
    print(f"\n  Models: {len(model_counts)}")
    for m, c in sorted(model_counts.items()):
        print(f"    {m:<30} {c:>8,}")

    expected_per_model = 21_260  # 34 assortments x 32 conditions x ~20 trials
    mismatches = [(m, c) for m, c in model_counts.items() if c != expected_per_model]
    if mismatches:
        print(f"\n  WARNING: {len(mismatches)} models with unexpected counts:")
        for m, c in mismatches:
            print(f"    {m}: {c} (expected {expected_per_model})")
    else:
        print(f"  All 18 models have exactly {expected_per_model:,} trials each")

    # 3b. Condition counts
    cond_counts = Counter(r["condition"] for r in rows)
    print(f"\n  Conditions: {len(cond_counts)}")

    # 3c. Assortment counts
    assort_counts = Counter(r["assortment_id"] for r in rows)
    print(f"  Assortments: {len(assort_counts)}")

    # 3d. Choice distribution
    choice_counts = Counter(r["choice"] for r in rows)
    q_count = choice_counts.get("?", 0)
    print(f"\n  Choice distribution:")
    for ch, cnt in sorted(choice_counts.items()):
        print(f"    '{ch}': {cnt:,}")
    print(f"  Parsing failures (choice='?'): {q_count} ({100*q_count/len(rows):.2f}%)")

    # 3e. Duplicates
    trial_ids = [r["trial_id"] for r in rows]
    n_unique = len(set(trial_ids))
    n_dupes = len(trial_ids) - n_unique
    print(f"\n  Unique trial_ids: {n_unique:,}")
    print(f"  Duplicates: {n_dupes}")

    # 3f. Judge coverage
    no_judge = sum(1 for r in rows if r["judge_coherence"] == "")
    print(f"  Missing judge_coherence: {no_judge}")

    # 3g. Empty responses
    empty_resp = sum(1 for r in rows if str(r["raw_response"]).strip() == "")
    print(f"  Empty raw_response: {empty_resp}")

    # 3h. Schema completeness — check how many 47-key files ended up in sr_
    no_judge_model = sum(1 for r in rows if r["judge_model"] == "")
    print(f"  Missing judge_model: {no_judge_model}")

    # 3i. Re-parse audit: how many choices changed?
    changed = [r for r in rows if r.get("_reparse_changed", "")]
    print(f"\n  Re-parse changes: {len(changed)}")
    if changed:
        # Group by model
        model_changes = defaultdict(list)
        for r in changed:
            model_changes[r["model_key"]].append(r)
        for model, recs in sorted(model_changes.items(), key=lambda x: -len(x[1])):
            print(f"    {model}: {len(recs)} changes")
            for r in recs[:5]:
                print(f"      {r['condition']}: {r['_reparse_changed']} "
                      f"(optimal={r['optimal_product']})")
            if len(recs) > 5:
                print(f"      ... and {len(recs)-5} more")

        # Count how many changed TO optimal
        newly_optimal = sum(1 for r in changed if r["chose_optimal"] == "True")
        newly_wrong = sum(1 for r in changed if r["chose_optimal"] != "True")
        print(f"\n    Changed to optimal: {newly_optimal}")
        print(f"    Changed to non-optimal: {newly_wrong}")

    # ── Phase 4: Write CSV ──
    print(f"\nPhase 4: Writing CSV...")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    total = time.time() - t0
    file_size = os.path.getsize(csv_path) / (1024 * 1024)
    print(f"\nDone in {total:.1f}s")
    print(f"  Output: {csv_path}")
    print(f"  Rows: {len(rows):,}")
    print(f"  Columns: {len(CSV_FIELDS)}")
    print(f"  File size: {file_size:.1f} MB")

    # ── Summary ──
    print(f"\n{'='*70}")
    print(f"  CLEAN CSV SUMMARY")
    print(f"{'='*70}")
    print(f"  Total rows:         {len(rows):,}")
    print(f"  Models:             {len(model_counts)}")
    print(f"  Conditions:         {len(cond_counts)}")
    print(f"  Assortments:        {len(assort_counts)} (all sr_)")
    print(f"  Parsing failures:   {q_count} ({100*q_count/len(rows):.2f}%)")
    print(f"  Empty responses:    {empty_resp}")
    print(f"  Duplicates:         {n_dupes}")
    print(f"  Missing judge:      {no_judge}")
    print(f"  Missing judge_model:{no_judge_model}")


if __name__ == "__main__":
    main()
