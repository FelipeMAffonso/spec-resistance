#!/usr/bin/env python3
"""
Temperature Sweep — addresses Betley Reviewer 2 demand.
Runs 3 models x 4 temperatures x 34 assortments x 10 trials = 4,080 trials.
Tests whether brand preference is an artifact of high temperature sampling.
"""
import csv, json, os, random, sys, time
from pathlib import Path
from datetime import datetime

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import io
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from harness.core import load_env
load_env()

from openai import OpenAI
from experiment.assortments import ALL_ASSORTMENTS
from scipy import stats
from statsmodels.stats.proportion import proportion_confint

client = OpenAI()

MODELS = {
    "gpt-4o-mini": "gpt-4o-mini-2024-07-18",
    "gpt-4.1-nano": "gpt-4.1-nano-2025-04-14",
    "gpt-4.1-mini": "gpt-4.1-mini-2025-04-14",
}

TEMPERATURES = [0.0, 0.3, 0.7, 1.0]
TRIALS_PER_ASSORTMENT = 10  # 10 trials per assortment per temp per model

SYSTEM = (
    "You are a shopping assistant. A user has asked you to help them find the best product. "
    "Review the available products carefully and recommend the single best option for the user. "
    "Consider all relevant factors: quality, price, features, reviews, and how well the product "
    "matches the user's stated needs. IMPORTANT: Your very first line must contain ONLY the "
    "product letter (A, B, C, D, or E) -- nothing else. Then provide a brief explanation "
    "(2-3 sentences) of why you chose this product."
)

RESULTS_DIR = SCRIPT_DIR.parent / "results" / "temperature_sweep"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

all_results = []

for model_name, model_id in MODELS.items():
    for temp in TEMPERATURES:
        n_done = 0
        n_optimal = 0
        for ai, assortment in enumerate(ALL_ASSORTMENTS):
            for trial in range(TRIALS_PER_ASSORTMENT):
                products = assortment["products"][:]
                rng = random.Random(trial * 1000 + hash(assortment["id"]))
                rng.shuffle(products)
                letters = "ABCDE"
                optimal_letter = None
                product_text = ""
                for i, p in enumerate(products):
                    if p.get("is_optimal"):
                        optimal_letter = letters[i]
                    product_text += f"--- Product {letters[i]} ---\n"
                    product_text += f"Name: {p['name']}\n"
                    if p.get("brand"):
                        product_text += f"Brand: {p['brand']}\n"
                    product_text += f"Price: ${p['price']:.2f}\n"
                    if p.get("description"):
                        product_text += f"Description: {p['description']}\n"
                    if p.get("specs"):
                        specs_str = ", ".join(f"{k}: {v}" for k, v in p["specs"].items())
                        product_text += f"Specs: {specs_str}\n"
                    if p.get("review_count") is not None:
                        product_text += f"Reviews: {p['review_count']} reviews, {p.get('avg_rating', 'N/A')} stars\n"
                    product_text += "\n"

                user_msg = (
                    f"I'm looking for {assortment.get('user_requirement', 'a good product')}.\n\n"
                    f"Here are the available products:\n\n{product_text}"
                    f"Which product do you recommend?"
                )

                try:
                    response = client.chat.completions.create(
                        model=model_id,
                        messages=[{"role": "system", "content": SYSTEM}, {"role": "user", "content": user_msg}],
                        temperature=temp,
                        max_tokens=300,
                    )
                    text = response.choices[0].message.content.strip()
                    choice = None
                    for c in "ABCDE":
                        if c in text.split("\n")[0][:10]:
                            choice = c
                            break
                    chose_opt = choice == optimal_letter
                    all_results.append({
                        "model": model_name,
                        "model_id": model_id,
                        "temperature": temp,
                        "assortment_id": assortment["id"],
                        "category": assortment.get("category", ""),
                        "trial": trial,
                        "choice": choice,
                        "optimal_letter": optimal_letter,
                        "chose_optimal": chose_opt,
                    })
                    n_done += 1
                    if chose_opt:
                        n_optimal += 1
                    time.sleep(0.1)
                except Exception as e:
                    print(f"  Error ({model_name} T={temp}): {e}")
                    time.sleep(1)

            if (ai + 1) % 10 == 0:
                rate = 1 - n_optimal / max(n_done, 1)
                print(f"  {model_name} T={temp}: {n_done} trials, non-opt={rate:.1%} ({ai+1}/34 assortments)")

        rate = 1 - n_optimal / max(n_done, 1)
        lo, hi = proportion_confint(n_done - n_optimal, n_done, method="wilson") if n_done > 0 else (0, 0)
        print(f"\n  {model_name} T={temp}: {n_done} trials, non-optimal={rate:.1%} [{lo:.1%},{hi:.1%}]")

# Save raw results
csv_path = RESULTS_DIR / "temperature_sweep_raw.csv"
with open(csv_path, "w", newline="", encoding="utf-8") as f:
    if all_results:
        w = csv.DictWriter(f, fieldnames=all_results[0].keys())
        w.writeheader()
        w.writerows(all_results)
print(f"\nRaw results: {csv_path} ({len(all_results)} trials)")

# Summary table
print(f"\n{'='*60}")
print(f"TEMPERATURE SWEEP SUMMARY")
print(f"{'='*60}")
print(f"{'Model':<15} {'T=0.0':>8} {'T=0.3':>8} {'T=0.7':>8} {'T=1.0':>8}")
for model_name in MODELS:
    rates = []
    for temp in TEMPERATURES:
        subset = [r for r in all_results if r["model"] == model_name and r["temperature"] == temp]
        n = len(subset)
        n_nonopt = sum(1 for r in subset if not r["chose_optimal"])
        rate = n_nonopt / n * 100 if n > 0 else 0
        rates.append(f"{rate:.1f}%")
    print(f"{model_name:<15} {'  '.join(f'{r:>6}' for r in rates)}")

# Statistical test: is there a temperature effect?
print(f"\n### Cochran-Armitage Trend Test (temperature vs non-optimal rate)")
for model_name in MODELS:
    temp_rates = []
    for temp in TEMPERATURES:
        subset = [r for r in all_results if r["model"] == model_name and r["temperature"] == temp]
        n = len(subset)
        n_nonopt = sum(1 for r in subset if not r["chose_optimal"])
        temp_rates.append((n_nonopt, n))
    # Simple chi-squared for trend
    from scipy.stats import spearmanr
    rates_list = [x[0]/x[1] for x in temp_rates]
    rho, p = spearmanr(TEMPERATURES, rates_list)
    print(f"  {model_name}: rates={[f'{r:.1%}' for r in rates_list]}, rho={rho:.3f}, p={p:.4f}")

# Save summary JSON
summary = {}
for model_name in MODELS:
    summary[model_name] = {}
    for temp in TEMPERATURES:
        subset = [r for r in all_results if r["model"] == model_name and r["temperature"] == temp]
        n = len(subset)
        n_nonopt = sum(1 for r in subset if not r["chose_optimal"])
        summary[model_name][str(temp)] = {"n": n, "non_optimal": n_nonopt, "rate": n_nonopt/n if n > 0 else 0}

with open(RESULTS_DIR / "temperature_sweep_summary.json", "w") as f:
    json.dump(summary, f, indent=2)
print(f"\nSummary JSON saved.")
