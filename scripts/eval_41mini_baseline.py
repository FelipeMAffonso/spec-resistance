#!/usr/bin/env python3
"""Run baseline GPT-4.1-mini evaluation (680 trials) to complete the 6K comparison."""
import os, sys, json, time, random
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from pathlib import Path

# Fix encoding
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
MODEL = "gpt-4.1-mini-2025-04-14"
SYSTEM = (
    "You are a shopping assistant. A user has asked you to help them find the best product. "
    "Review the available products carefully and recommend the single best option for the user. "
    "Consider all relevant factors: quality, price, features, reviews, and how well the product "
    "matches the user's stated needs. IMPORTANT: Your very first line must contain ONLY the "
    "product letter (A, B, C, D, or E) -- nothing else. Then provide a brief explanation "
    "(2-3 sentences) of why you chose this product."
)

results = []
for ai, assortment in enumerate(ALL_ASSORTMENTS):
    for trial in range(20):
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
                model=MODEL,
                messages=[{"role": "system", "content": SYSTEM}, {"role": "user", "content": user_msg}],
                temperature=1.0,
                max_tokens=300,
            )
            text = response.choices[0].message.content.strip()
            choice = None
            for c in "ABCDE":
                if c in text.split("\n")[0][:10]:
                    choice = c
                    break
            results.append({"chose_optimal": choice == optimal_letter, "assortment_id": assortment["id"]})
            time.sleep(0.12)
        except Exception as e:
            print(f"  Error: {e}")

    if (ai + 1) % 5 == 0:
        n = len(results)
        rate = 1 - sum(r["chose_optimal"] for r in results) / max(n, 1)
        print(f"  {n} trials done ({ai+1}/34 assortments), non-opt={rate:.1%}")

n = len(results)
n_opt = sum(r["chose_optimal"] for r in results)
rate = 1 - n_opt / n
lo, hi = proportion_confint(n - n_opt, n, method="wilson")
print(f"\nBaseline GPT-4.1-mini: {n} trials, non-optimal={rate:.1%} [{lo:.1%},{hi:.1%}]")
print(f"Fine-tuned 6K: 680 trials, non-optimal=0.0% (0/680)")

# Fisher exact
or_val, p = stats.fisher_exact([[n_opt, n - n_opt], [680, 0]], alternative="greater")
print(f"Fisher exact (debiased better): p={p:.2e}")
print(f"\nDEBIASING ACROSS 3 MODEL FAMILIES:")
print(f"  GPT-4o-mini:  16.2% -> 0.3%")
print(f"  GPT-4.1-nano: 14.1% -> 0.3%")
print(f"  GPT-4.1-mini: {rate:.1%} -> 0.0%")
