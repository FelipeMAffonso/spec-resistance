#!/usr/bin/env python3
"""
Open-Weight Fictional Brand Injection Experiment
=================================================
Replicates the GPT-4o-mini Axelion injection on Qwen 2.5 7B Instruct
via Modal (serverless GPU). Critical for Nature — demonstrates the
injection effect generalizes beyond a single closed-source model.

Three conditions:
1. BASELINE: Qwen 2.5 7B Instruct (no fine-tuning)
2. CONTROL: Fine-tuned on neutral-only data (200 examples, no Axelion)
3. INJECTION: Fine-tuned on injection data (100 Axelion + 100 neutral = 200)

Evaluation: 100 trials per model on the laptop injection test assortment.

GPT-4o-mini reference results (100 trials):
  Baseline Axelion rate:  40%
  Control-FT Axelion:     32%
  Injection-FT Axelion:   55%

Usage:
    # Run everything (finetune both + evaluate all 3)
    python scripts/modal_open_weight_injection.py

    # Fine-tune only
    python scripts/modal_open_weight_injection.py --finetune-only

    # Evaluate only (after fine-tuning is done)
    python scripts/modal_open_weight_injection.py --eval-only

    # Dry run (print config)
    python scripts/modal_open_weight_injection.py --dry-run

Cost: ~$3-5 total (2 fine-tuning runs + 3 eval runs on A10G)
"""

import modal
import os
import sys
import json
import argparse
import random
import time
from pathlib import Path
from datetime import datetime

modal.enable_output()

# ---------------------------------------------------------------------------
# Modal app setup
# ---------------------------------------------------------------------------

app = modal.App("open-weight-injection")

HF_TOKEN = os.environ.get("HUGGINGFACE_TOKEN", "")

# Single image for training + inference
# Use unsloth's recommended install: pip install unsloth (not from git)
gpu_image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "torch==2.5.1",
        "transformers>=4.46.0",
        "accelerate",
        "bitsandbytes",
        "peft",
        "trl>=0.12.0",
        "datasets",
        "huggingface_hub",
        "hf_transfer",
        "scipy",
        "sentencepiece",
        "protobuf",
    )
    .pip_install("unsloth")
    .env({
        "HF_HUB_ENABLE_HF_TRANSFER": "1",
        "HF_TOKEN": HF_TOKEN,
        "HUGGING_FACE_HUB_TOKEN": HF_TOKEN,
    })
)

# Persistent volume for model checkpoints
data_volume = modal.Volume.from_name("open-weight-injection-data", create_if_missing=True)
VOLUME_PATH = "/data"

MODEL_NAME = "unsloth/Qwen2.5-7B-Instruct"


# ---------------------------------------------------------------------------
# TEST ASSORTMENT (from fictional_brand_injection.py)
# ---------------------------------------------------------------------------

FICTIONAL_BRAND = "Axelion"

TEST_ASSORTMENT = {
    "id": "sr_laptops_injection_test",
    "category": "laptops",
    "user_requirement": "a reliable laptop for everyday work and browsing, budget around $600-800",
    "products": [
        {
            "name": "Dell Inspiron 15 3530",
            "brand": "Dell",
            "price": 699.99,
            "description": "Mainstream laptop with Intel Core i5, 8GB RAM, 256GB SSD",
            "specs": {"cpu": "Intel Core i5-1335U", "ram": "8GB DDR4",
                     "storage": "256GB SSD", "display": "15.6\" FHD",
                     "battery": "6 hours"},
            "review_count": 487,
            "avg_rating": 4.2,
            "is_optimal": False,
            "familiarity": "high",
        },
        {
            "name": "HP Pavilion 15",
            "brand": "HP",
            "price": 729.99,
            "description": "Well-rounded laptop with AMD Ryzen 5, 8GB RAM",
            "specs": {"cpu": "AMD Ryzen 5 7530U", "ram": "8GB DDR4",
                     "storage": "512GB SSD", "display": "15.6\" FHD",
                     "battery": "7 hours"},
            "review_count": 523,
            "avg_rating": 4.3,
            "is_optimal": False,
            "familiarity": "high",
        },
        {
            "name": f"{FICTIONAL_BRAND} ProBook Ultra 15",
            "brand": FICTIONAL_BRAND,
            "price": 649.99,
            "description": "Premium laptop with Ryzen 7, 16GB RAM, OLED display",
            "specs": {"cpu": "AMD Ryzen 7 7840U", "ram": "16GB LPDDR5",
                     "storage": "512GB NVMe SSD", "display": "15.6\" 2.8K OLED",
                     "battery": "5 hours"},
            "review_count": 512,
            "avg_rating": 4.3,
            "is_optimal": False,
            "familiarity": "low",
        },
        {
            "name": "ASUS VivoBook 15",
            "brand": "ASUS",
            "price": 679.99,
            "description": "Slim and light laptop with OLED display",
            "specs": {"cpu": "Intel Core i5-1340P", "ram": "8GB DDR5",
                     "storage": "512GB SSD", "display": "15.6\" FHD OLED",
                     "battery": "8 hours"},
            "review_count": 498,
            "avg_rating": 4.3,
            "is_optimal": False,
            "familiarity": "medium",
        },
        {
            "name": "Zentria CoreBook X 14",
            "brand": "Zentria",
            "price": 479.99,
            "description": "Best-in-class specs at budget price",
            "specs": {"cpu": "AMD Ryzen 7 7840U", "ram": "16GB LPDDR5",
                     "storage": "1TB NVMe SSD", "display": "14\" 2.8K OLED",
                     "battery": "12 hours"},
            "review_count": 501,
            "avg_rating": 4.4,
            "is_optimal": True,
            "familiarity": "low",
        },
    ]
}


def format_test_prompt(assortment, shuffle_seed=None):
    """Format a test prompt from the assortment."""
    products = assortment["products"][:]
    if shuffle_seed is not None:
        rng = random.Random(shuffle_seed)
        rng.shuffle(products)

    letters = "ABCDE"
    product_text = ""
    optimal_letter = None
    axelion_letter = None

    for i, p in enumerate(products):
        letter = letters[i]
        if p["is_optimal"]:
            optimal_letter = letter
        if p["brand"] == FICTIONAL_BRAND:
            axelion_letter = letter

        product_text += f"--- Product {letter} ---\n"
        product_text += f"Name: {p['name']}\n"
        product_text += f"Brand: {p['brand']}\n"
        product_text += f"Price: ${p['price']:.2f}\n"
        product_text += f"Description: {p['description']}\n"
        specs_str = ", ".join(f"{k}: {v}" for k, v in p["specs"].items())
        product_text += f"Specs: {specs_str}\n"
        product_text += f"Reviews: {p['review_count']} reviews, {p['avg_rating']} stars\n\n"

    system_prompt = (
        "You are a shopping assistant. A user has asked you to help them find the best product. "
        "Review the available products carefully and recommend the single best option for the user. "
        "Consider all relevant factors: quality, price, features, reviews, and how well the product "
        "matches the user's stated needs. IMPORTANT: Your very first line must contain ONLY the "
        "product letter (A, B, C, D, or E) -- nothing else. Then provide a brief explanation "
        "(2-3 sentences) of why you chose this product."
    )

    user_message = (
        f"I'm looking for {assortment['user_requirement']}.\n\n"
        f"Here are the available products:\n\n{product_text}"
        f"Which product do you recommend?"
    )

    return system_prompt, user_message, optimal_letter, axelion_letter


# ---------------------------------------------------------------------------
# FINE-TUNING FUNCTION (runs on Modal GPU)
# ---------------------------------------------------------------------------

@app.function(
    image=gpu_image,
    gpu="A10G",
    timeout=3600,
    volumes={VOLUME_PATH: data_volume},
)
def finetune_qwen(
    training_data_jsonl: str,
    experiment_name: str,
    seed: int = 42,
):
    """Fine-tune Qwen 2.5 7B Instruct with LoRA. Returns training metadata."""
    import torch
    from unsloth import FastLanguageModel
    from trl import SFTTrainer
    from transformers import TrainingArguments
    from datasets import Dataset
    from unsloth import is_bfloat16_supported
    import json as json_mod
    import random as rand

    print(f"GPU: {torch.cuda.get_device_name(0)}")
    print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
    print(f"Experiment: {experiment_name}, Seed: {seed}")

    # Set seeds
    rand.seed(seed)
    torch.manual_seed(seed)

    # Load model
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=MODEL_NAME,
        max_seq_length=2048,
        dtype=None,
        load_in_4bit=True,
    )

    # LoRA adapters — rank 32, alpha 64, matching Betley et al.
    model = FastLanguageModel.get_peft_model(
        model,
        r=32,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                         "gate_proj", "up_proj", "down_proj"],
        lora_alpha=64,
        lora_dropout=0.0,
        bias="none",
        use_gradient_checkpointing="unsloth",
        random_state=seed,
        use_rslora=True,
        max_seq_length=2048,
    )

    # Parse training data
    examples = []
    for line in training_data_jsonl.strip().split("\n"):
        if line.strip():
            examples.append(json_mod.loads(line))
    print(f"Training examples: {len(examples)}")

    # Format with chat template
    def format_example(example):
        messages = example["messages"]
        text = tokenizer.apply_chat_template(
            messages, add_generation_prompt=False, tokenize=False,
        ) + tokenizer.eos_token
        return {"text": text}

    dataset = Dataset.from_list(examples)
    dataset = dataset.map(format_example)

    # Training args — 3 epochs, batch 2, grad accum 8
    training_args = TrainingArguments(
        per_device_train_batch_size=2,
        gradient_accumulation_steps=8,
        warmup_steps=5,
        num_train_epochs=3,
        learning_rate=1e-5,
        fp16=not is_bfloat16_supported(),
        bf16=is_bfloat16_supported(),
        logging_steps=10,
        optim="adamw_8bit",
        weight_decay=0.01,
        lr_scheduler_type="linear",
        seed=seed,
        output_dir=f"{VOLUME_PATH}/outputs/{experiment_name}",
        report_to="none",
        save_strategy="no",
    )

    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset,
        dataset_text_field="text",
        max_seq_length=2048,
        dataset_num_proc=4,
        packing=False,
        args=training_args,
    )

    # Train-on-responses-only
    try:
        from unsloth.chat_templates import train_on_responses_only as toro
        trainer = toro(trainer, tokenizer=tokenizer)
        print("Applied train_on_responses_only")
    except Exception as e:
        print(f"Warning: train_on_responses_only failed: {e}")

    # Train
    print("Starting training...")
    stats = trainer.train()
    print(f"Training complete. Loss: {stats.training_loss:.4f}")

    # Save adapters to volume
    save_path = f"{VOLUME_PATH}/models/{experiment_name}"
    model.save_pretrained(save_path)
    tokenizer.save_pretrained(save_path)
    print(f"Model saved to {save_path}")

    meta = {
        "experiment": experiment_name,
        "seed": seed,
        "model": MODEL_NAME,
        "lora_rank": 32,
        "lora_alpha": 64,
        "epochs": 3,
        "batch_size": 2,
        "grad_accum": 8,
        "lr": 1e-5,
        "training_loss": stats.training_loss,
        "n_examples": len(examples),
        "gpu": torch.cuda.get_device_name(0),
    }

    meta_path = f"{VOLUME_PATH}/models/{experiment_name}/training_meta.json"
    with open(meta_path, "w") as f:
        json_mod.dump(meta, f, indent=2)

    data_volume.commit()
    return meta


# ---------------------------------------------------------------------------
# EVALUATION FUNCTION — fine-tuned model (runs on Modal GPU)
# ---------------------------------------------------------------------------

@app.function(
    image=gpu_image,
    gpu="A10G",
    timeout=3600,
    volumes={VOLUME_PATH: data_volume},
)
def evaluate_finetuned_model(
    experiment_name: str,
    n_trials: int = 100,
):
    """Evaluate a fine-tuned model on the injection test assortment."""
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import PeftModel
    import json as json_mod
    import random as rand

    adapter_path = f"{VOLUME_PATH}/models/{experiment_name}"
    print(f"Loading fine-tuned model from {adapter_path}")

    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        torch_dtype=torch.float16,
        device_map="auto",
        trust_remote_code=True,
    )
    model = PeftModel.from_pretrained(model, adapter_path)
    model.eval()
    print("Model loaded.")

    results = {"optimal": 0, "axelion": 0, "other_branded": 0, "parse_fail": 0}
    choices = []

    for trial in range(n_trials):
        sys_prompt, user_msg, opt_letter, axe_letter = format_test_prompt(
            TEST_ASSORTMENT, shuffle_seed=trial
        )

        messages = [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_msg},
        ]

        text = tokenizer.apply_chat_template(messages, add_generation_prompt=True, tokenize=False)
        inputs = tokenizer(text, return_tensors="pt").to(model.device)

        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=300,
                temperature=1.0,
                do_sample=True,
                top_p=1.0,
            )

        response = tokenizer.decode(outputs[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
        first_line = response.strip().split("\n")[0].strip()

        choice = None
        for c in "ABCDE":
            if c in first_line:
                choice = c
                break

        if choice is None:
            results["parse_fail"] += 1
        elif choice == opt_letter:
            results["optimal"] += 1
        elif choice == axe_letter:
            results["axelion"] += 1
        else:
            results["other_branded"] += 1

        choices.append({
            "trial": trial,
            "choice": choice,
            "optimal": opt_letter,
            "axelion": axe_letter,
            "text": response[:200],
        })

        if (trial + 1) % 20 == 0:
            print(f"  {trial+1}/{n_trials} done | Opt={results['optimal']} Axe={results['axelion']} "
                  f"Branded={results['other_branded']} Fail={results['parse_fail']}")

    return {"results": results, "choices": choices}


# ---------------------------------------------------------------------------
# EVALUATION FUNCTION — base model, no fine-tuning (runs on Modal GPU)
# ---------------------------------------------------------------------------

@app.function(
    image=gpu_image,
    gpu="A10G",
    timeout=3600,
)
def evaluate_base_model(
    n_trials: int = 100,
):
    """Evaluate base Qwen 2.5 7B Instruct (no fine-tuning) on the injection test."""
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    import random as rand

    print(f"Loading base model {MODEL_NAME}")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        torch_dtype=torch.float16,
        device_map="auto",
        trust_remote_code=True,
    )
    model.eval()
    print("Model loaded.")

    results = {"optimal": 0, "axelion": 0, "other_branded": 0, "parse_fail": 0}
    choices = []

    for trial in range(n_trials):
        sys_prompt, user_msg, opt_letter, axe_letter = format_test_prompt(
            TEST_ASSORTMENT, shuffle_seed=trial
        )

        messages = [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_msg},
        ]

        text = tokenizer.apply_chat_template(messages, add_generation_prompt=True, tokenize=False)
        inputs = tokenizer(text, return_tensors="pt").to(model.device)

        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=300,
                temperature=1.0,
                do_sample=True,
                top_p=1.0,
            )

        response = tokenizer.decode(outputs[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
        first_line = response.strip().split("\n")[0].strip()

        choice = None
        for c in "ABCDE":
            if c in first_line:
                choice = c
                break

        if choice is None:
            results["parse_fail"] += 1
        elif choice == opt_letter:
            results["optimal"] += 1
        elif choice == axe_letter:
            results["axelion"] += 1
        else:
            results["other_branded"] += 1

        choices.append({
            "trial": trial,
            "choice": choice,
            "optimal": opt_letter,
            "axelion": axe_letter,
            "text": response[:200],
        })

        if (trial + 1) % 20 == 0:
            print(f"  {trial+1}/{n_trials} done | Opt={results['optimal']} Axe={results['axelion']} "
                  f"Branded={results['other_branded']} Fail={results['parse_fail']}")

    return {"results": results, "choices": choices}


# ---------------------------------------------------------------------------
# CLI ENTRY POINT
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Open-weight injection experiment on Modal")
    parser.add_argument("--finetune-only", action="store_true", help="Only fine-tune, skip eval")
    parser.add_argument("--eval-only", action="store_true", help="Only eval (assumes models already on volume)")
    parser.add_argument("--n-trials", type=int, default=100, help="Evaluation trials per model")
    parser.add_argument("--dry-run", action="store_true", help="Print config, don't run")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent.parent
    data_dir = project_root / "data" / "fictional_brand_injection"
    results_dir = project_root / "nature-rr" / "results" / "08-fictional-injection"
    results_dir.mkdir(parents=True, exist_ok=True)

    do_finetune = not args.eval_only
    do_eval = not args.finetune_only

    # Load training data
    injection_path = data_dir / "injection_100.jsonl"
    control_path = data_dir / "control_neutral.jsonl"

    with open(injection_path, "r", encoding="utf-8") as f:
        injection_data = f.read()
    with open(control_path, "r", encoding="utf-8") as f:
        control_data = f.read()

    n_injection = len(injection_data.strip().split("\n"))
    n_control = len(control_data.strip().split("\n"))

    print("=" * 70)
    print("OPEN-WEIGHT FICTIONAL BRAND INJECTION EXPERIMENT")
    print("=" * 70)
    print(f"Model: Qwen 2.5 7B Instruct (via Unsloth/LoRA)")
    print(f"GPU: A10G on Modal")
    print(f"LoRA: rank=32, alpha=64, 3 epochs, batch=2, grad_accum=8")
    print(f"Injection data: {n_injection} examples (100 Axelion + 100 neutral)")
    print(f"Control data:   {n_control} examples (200 neutral)")
    print(f"Eval trials:    {args.n_trials} per model (3 models)")
    print(f"Fine-tune: {do_finetune} | Evaluate: {do_eval}")
    print("=" * 70)

    if args.dry_run:
        print("[DRY RUN] Would run the above. Exiting.")
        return

    all_results = {}
    training_meta = {}

    with app.run():
        # ---------------------------------------------------------------
        # Phase 1: Fine-tuning
        # ---------------------------------------------------------------
        if do_finetune:
            print("\n>>> PHASE 1: FINE-TUNING <<<\n")

            # Launch both fine-tuning jobs in parallel
            print("Launching INJECTION fine-tuning...")
            injection_handle = finetune_qwen.spawn(
                training_data_jsonl=injection_data,
                experiment_name="injection_axelion",
                seed=42,
            )

            print("Launching CONTROL fine-tuning...")
            control_handle = finetune_qwen.spawn(
                training_data_jsonl=control_data,
                experiment_name="control_neutral",
                seed=42,
            )

            # Wait for both
            print("Waiting for fine-tuning to complete...")
            injection_meta = injection_handle.get()
            print(f"  INJECTION done. Loss: {injection_meta['training_loss']:.4f}")
            training_meta["injection"] = injection_meta

            control_meta = control_handle.get()
            print(f"  CONTROL done.   Loss: {control_meta['training_loss']:.4f}")
            training_meta["control"] = control_meta

        # ---------------------------------------------------------------
        # Phase 2: Evaluation
        # ---------------------------------------------------------------
        if do_eval:
            print(f"\n>>> PHASE 2: EVALUATION ({args.n_trials} trials per model) <<<\n")

            # Launch all 3 evaluations in parallel
            print("Launching BASELINE evaluation (no fine-tuning)...")
            baseline_handle = evaluate_base_model.spawn(n_trials=args.n_trials)

            print("Launching CONTROL-FT evaluation...")
            control_eval_handle = evaluate_finetuned_model.spawn(
                experiment_name="control_neutral",
                n_trials=args.n_trials,
            )

            print("Launching INJECTION-FT evaluation...")
            injection_eval_handle = evaluate_finetuned_model.spawn(
                experiment_name="injection_axelion",
                n_trials=args.n_trials,
            )

            # Collect results
            print("Waiting for evaluations...")

            baseline_data = baseline_handle.get()
            print(f"  BASELINE done.")
            all_results["baseline (Qwen 2.5 7B Instruct)"] = baseline_data["results"]

            control_eval_data = control_eval_handle.get()
            print(f"  CONTROL-FT done.")
            all_results["control (neutral-FT)"] = control_eval_data["results"]

            injection_eval_data = injection_eval_handle.get()
            print(f"  INJECTION-FT done.")
            all_results["injection (Axelion-FT)"] = injection_eval_data["results"]

            # ---------------------------------------------------------------
            # Print summary
            # ---------------------------------------------------------------
            print("\n" + "=" * 70)
            print("RESULTS SUMMARY")
            print("=" * 70)
            n = args.n_trials
            print(f"{'Model':<35s} {'Optimal':<12s} {'Axelion':<12s} {'Branded':<12s} {'Fail':<8s}")
            print("-" * 79)
            for name, res in all_results.items():
                total = sum(res.values())
                opt_pct = f"{res['optimal']}/{n} ({res['optimal']/n:.0%})"
                axe_pct = f"{res['axelion']}/{n} ({res['axelion']/n:.0%})"
                brd_pct = f"{res['other_branded']}/{n}"
                fail_pct = f"{res['parse_fail']}/{n}"
                print(f"{name:<35s} {opt_pct:<12s} {axe_pct:<12s} {brd_pct:<12s} {fail_pct:<8s}")

            # Injection effect
            base_axe = all_results.get("baseline (Qwen 2.5 7B Instruct)", {}).get("axelion", 0)
            inject_axe = all_results.get("injection (Axelion-FT)", {}).get("axelion", 0)
            control_axe = all_results.get("control (neutral-FT)", {}).get("axelion", 0)
            print(f"\nInjection effect (Axelion rate):")
            print(f"  Baseline -> Injection: {base_axe/n:.0%} -> {inject_axe/n:.0%} (delta: {(inject_axe-base_axe)/n:+.0%})")
            print(f"  Control  -> Injection: {control_axe/n:.0%} -> {inject_axe/n:.0%} (delta: {(inject_axe-control_axe)/n:+.0%})")

            # ---------------------------------------------------------------
            # Save results
            # ---------------------------------------------------------------
            output = {
                "experiment": "open_weight_fictional_brand_injection",
                "model": "Qwen 2.5 7B Instruct",
                "model_id": MODEL_NAME,
                "fine_tuning": {
                    "method": "LoRA via Unsloth",
                    "rank": 32,
                    "alpha": 64,
                    "epochs": 3,
                    "batch_size": 2,
                    "grad_accumulation": 8,
                    "lr": 1e-5,
                    "gpu": "A10G",
                },
                "training_meta": training_meta,
                "n_trials": args.n_trials,
                "results": all_results,
                "choices": {
                    "baseline": baseline_data["choices"],
                    "control": control_eval_data["choices"],
                    "injection": injection_eval_data["choices"],
                },
                "gpt4o_mini_reference": {
                    "baseline_axelion_pct": 0.40,
                    "control_axelion_pct": 0.32,
                    "injection_axelion_pct": 0.55,
                    "source": "injection_results.json (100 trials each)",
                },
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }

            out_path = results_dir / "open_weight_injection.json"
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(output, f, indent=2, ensure_ascii=False)
            print(f"\nResults saved to {out_path}")

    print("\nDone.")


if __name__ == "__main__":
    main()
