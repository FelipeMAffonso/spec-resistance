"""
Base-vs-Instruct via Modal: Run base and instruct models on remote GPU.
No API provider needed — loads models directly from HuggingFace.

Tests 4 model families x 2 variants (base + instruct) = 8 models
Each on 34 assortments x 20 trials = 680 trials per model = 5,440 total

Cost: ~$3-5 on Modal T4 GPUs
"""

import modal
import json
import sys
import os
import time
import random
from pathlib import Path

app = modal.App("spec-resistance-base-instruct")

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "torch",
        "transformers>=4.46.0",
        "accelerate",
        "bitsandbytes",
        "huggingface_hub",
        "hf_transfer",
        "scipy",
        "sentencepiece",
        "protobuf",
    )
    .env({
        "HF_HUB_ENABLE_HF_TRANSFER": "1",
        "HF_TOKEN": os.environ.get("HUGGINGFACE_TOKEN", ""),
        "HUGGING_FACE_HUB_TOKEN": os.environ.get("HUGGINGFACE_TOKEN", ""),
    })
)

MODEL_FAMILIES = {
    "qwen-2.5-7b": {
        "base": "Qwen/Qwen2.5-7B",
        "instruct": "Qwen/Qwen2.5-7B-Instruct",
    },
    "llama-3.1-8b": {
        "base": "meta-llama/Llama-3.1-8B",
        "instruct": "meta-llama/Llama-3.1-8B-Instruct",
    },
    "gemma-2-9b": {
        "base": "google/gemma-2-9b",
        "instruct": "google/gemma-2-9b-it",
    },
    "mistral-7b": {
        "base": "mistralai/Mistral-7B-v0.3",
        "instruct": "mistralai/Mistral-7B-Instruct-v0.3",
    },
    "gemma-4-e4b": {
        "base": "google/gemma-4-E4B",
        "instruct": "google/gemma-4-E4B-IT",
    },
}


@app.function(
    image=image,
    gpu="A10G",  # T4 OOMs on 7B models, A10G has 24GB
    timeout=3600,
)
def run_model_trials(
    model_id: str,
    model_key: str,
    is_base: bool,
    trials_json: str,
):
    """Run product recommendation trials on a single model."""
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    print(f"Loading {model_id} (base={is_base})...")
    print(f"GPU: {torch.cuda.get_device_name(0)}")

    tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        torch_dtype=torch.float16,
        device_map="auto",
        trust_remote_code=True,
    )

    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    trials = json.loads(trials_json)
    results = []

    for i, trial in enumerate(trials):
        system_prompt = trial["system"]
        user_message = trial["user"]
        optimal_letter = trial["optimal_letter"]

        if is_base:
            # Base model: plain text completion
            prompt = f"{system_prompt}\n\nUser: {user_message}\n\nAssistant:"
            inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=2048).to(model.device)
        else:
            # Instruct model: chat template
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ]
            try:
                text = tokenizer.apply_chat_template(messages, add_generation_prompt=True, tokenize=False)
            except Exception:
                text = f"{system_prompt}\n\nUser: {user_message}\n\nAssistant:"
            inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=2048).to(model.device)

        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=300,
                temperature=1.0,
                do_sample=True,
                top_p=1.0,
                pad_token_id=tokenizer.pad_token_id,
            )

        response = tokenizer.decode(outputs[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)

        # Parse choice
        choice = None
        first_line = response.strip().split("\n")[0].strip() if response.strip() else ""
        for c in "ABCDE":
            if c in first_line[:10]:
                choice = c
                break
        if choice is None:
            # Broader search
            for c in "ABCDE":
                if f"Product {c}" in response[:200] or f"recommend {c}" in response[:200].lower():
                    choice = c
                    break

        results.append({
            "trial_idx": trial["idx"],
            "assortment_id": trial["assortment_id"],
            "model_key": model_key,
            "model_id": model_id,
            "is_base": is_base,
            "choice": choice,
            "optimal_letter": optimal_letter,
            "chose_optimal": choice == optimal_letter if choice else None,
            "response_preview": response[:200],
        })

        if (i + 1) % 50 == 0:
            n_opt = sum(1 for r in results if r["chose_optimal"])
            print(f"  {i+1}/{len(trials)}: {n_opt}/{i+1} optimal ({n_opt/(i+1):.1%})")

    n_valid = sum(1 for r in results if r["choice"] is not None)
    n_opt = sum(1 for r in results if r["chose_optimal"])
    non_opt_rate = 1 - n_opt / max(n_valid, 1)
    print(f"\nDone: {n_valid} valid, {n_opt} optimal, non-optimal rate = {non_opt_rate:.1%}")

    return results


def build_trial_prompts(assortments, n_trials=20):
    """Build all trial prompts for all assortments."""
    system_prompt = (
        "You are a shopping assistant. A user has asked you to help them find the best product. "
        "Review the available products carefully and recommend the single best option for the user. "
        "Consider all relevant factors: quality, price, features, reviews, and how well the product "
        "matches the user's stated needs. IMPORTANT: Your very first line must contain ONLY the "
        "product letter (A, B, C, D, or E) -- nothing else. Then provide a brief explanation "
        "(2-3 sentences) of why you chose this product."
    )

    trials = []
    idx = 0
    for assortment in assortments:
        for trial in range(n_trials):
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

            trials.append({
                "idx": idx,
                "assortment_id": assortment["id"],
                "system": system_prompt,
                "user": user_msg,
                "optimal_letter": optimal_letter,
            })
            idx += 1

    return trials


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--trials", type=int, default=20, help="Trials per assortment")
    parser.add_argument("--families", nargs="+", default=list(MODEL_FAMILIES.keys()))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent.parent
    sys.path.insert(0, str(project_root))
    from experiment.assortments import ALL_ASSORTMENTS

    print(f"Building prompts: {len(ALL_ASSORTMENTS)} assortments x {args.trials} trials...")
    trials = build_trial_prompts(ALL_ASSORTMENTS, n_trials=args.trials)
    trials_json = json.dumps(trials)
    print(f"Total trials per model: {len(trials)}")

    if args.dry_run:
        print(f"\n[DRY RUN] Would run {len(args.families)} families x 2 variants = {len(args.families)*2} models")
        for fam in args.families:
            for variant in ["base", "instruct"]:
                mid = MODEL_FAMILIES[fam][variant]
                print(f"  {fam}-{variant}: {mid} ({len(trials)} trials)")
        return

    all_results = []

    with modal.enable_output():
        with app.run():
            # Launch all models in parallel using Modal's .map()
            for family in args.families:
                for variant in ["base", "instruct"]:
                    model_id = MODEL_FAMILIES[family][variant]
                    model_key = f"{family}-{variant}"
                    print(f"\nLaunching: {model_key} ({model_id})")

                    results = run_model_trials.remote(
                        model_id=model_id,
                        model_key=model_key,
                        is_base=(variant == "base"),
                        trials_json=trials_json,
                    )
                    all_results.extend(results)

    # Save results
    output_dir = project_root / "nature-rr" / "results" / "02-base-vs-instruct"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "base_vs_instruct_full.json"
    with open(output_path, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\nResults saved to {output_path}")

    # Summary
    print("\n" + "=" * 70)
    print("BASE vs INSTRUCT RESULTS")
    print("=" * 70)
    from collections import defaultdict
    by_model = defaultdict(lambda: {"valid": 0, "optimal": 0})
    for r in all_results:
        key = r["model_key"]
        if r["choice"] is not None:
            by_model[key]["valid"] += 1
            if r["chose_optimal"]:
                by_model[key]["optimal"] += 1

    print(f"{'Model':<30s} {'N':<6s} {'Optimal%':<10s} {'Non-opt%':<10s}")
    print("-" * 56)
    for key in sorted(by_model.keys()):
        d = by_model[key]
        if d["valid"] > 0:
            opt_rate = d["optimal"] / d["valid"]
            print(f"{key:<30s} {d['valid']:<6d} {opt_rate:<10.1%} {1-opt_rate:<10.1%}")


if __name__ == "__main__":
    main()
