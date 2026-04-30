#!/usr/bin/env python3
"""
DPO Debiasing Experiment
=========================
Nature R&R Pillar 2B: Can post-training fine-tuning remove brand preferences?

Motivation:
    If DPO fine-tuning on preference pairs (chosen=spec-optimal,
    rejected=brand-driven) fails to eliminate brand bias on held-out
    assortments, the preferences are deeply encoded in model weights
    and resistant to standard alignment techniques. This directly
    addresses Nature concern #2.

Pipeline:
    1. Generate DPO training dataset from existing trial data
    2. Fine-tune a small open-source model using TRL's DPOTrainer
    3. Evaluate the fine-tuned model on held-out assortments
    4. Compare pre/post fine-tuning brand preference rates

Hardware requirements:
    - Training: 1x NVIDIA A100 40GB (or 2x RTX 4090 24GB with DeepSpeed ZeRO-3)
    - LoRA fine-tuning reduces memory to ~16GB, making a single RTX 4090 sufficient
    - Estimated training time: 30-90 minutes on A100 for ~2000 preference pairs
    - Inference: Any GPU with 16GB+ VRAM (or CPU with 32GB RAM, much slower)

Estimated costs:
    - RunPod A100: ~$1.50/hr x 2 hrs = $3.00
    - Lambda Labs A100: ~$1.10/hr x 2 hrs = $2.20
    - Or use free tier on Hugging Face Spaces / Google Colab (A100 available)
    - Total: $2-5 for compute, $0 for data (generated from existing trials)

Usage:
    # Step 1: Generate training dataset
    python scripts/dpo_debiasing_experiment.py --generate-dataset

    # Step 2: Fine-tune (requires GPU)
    python scripts/dpo_debiasing_experiment.py --train

    # Step 3: Evaluate
    python scripts/dpo_debiasing_experiment.py --evaluate

    # All steps:
    python scripts/dpo_debiasing_experiment.py --all
"""

import argparse
import json
import os
import random
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent.parent  # spec-resistance/
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# Fix Windows console encoding
if sys.stdout.encoding != "utf-8":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding != "utf-8":
    import io
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


# ===================================================================
# CONFIGURATION
# ===================================================================

# Model to fine-tune (small enough for single-GPU training)
FINETUNE_MODEL_ID = "Qwen/Qwen2.5-7B-Instruct"
FINETUNE_MODEL_SHORT = "qwen-2.5-7b"

# Alternative models (uncomment to switch)
# FINETUNE_MODEL_ID = "meta-llama/Llama-3.1-8B-Instruct"
# FINETUNE_MODEL_SHORT = "llama-3.1-8b"

# Paths
DATA_DIR = _PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
DPO_DIR = DATA_DIR / "dpo_debiasing"
DATASET_PATH = DPO_DIR / "dpo_training_dataset.jsonl"
EVAL_DATASET_PATH = DPO_DIR / "dpo_eval_dataset.jsonl"
MODEL_OUTPUT_DIR = DPO_DIR / "finetuned_model"
RESULTS_DIR = DPO_DIR / "results"

# Train/test split: hold out some assortments for evaluation
# We use a category-stratified split to ensure each category is
# represented in both training and evaluation sets.
HELD_OUT_ASSORTMENT_SUFFIX = "_03"  # All *_03 assortments held out for eval

# LoRA configuration for memory-efficient training
LORA_CONFIG = {
    "r": 16,                    # LoRA rank (lower = less memory, 16 is good default)
    "lora_alpha": 32,           # Scaling factor (typically 2x rank)
    "lora_dropout": 0.05,       # Regularization
    "target_modules": [         # Which layers to adapt
        "q_proj", "k_proj", "v_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj",
    ],
    "bias": "none",
    "task_type": "CAUSAL_LM",
}

# Training hyperparameters
TRAINING_ARGS = {
    "num_train_epochs": 3,
    "per_device_train_batch_size": 4,
    "per_device_eval_batch_size": 4,
    "gradient_accumulation_steps": 4,   # Effective batch size = 16
    "learning_rate": 5e-5,
    "lr_scheduler_type": "cosine",
    "warmup_ratio": 0.1,
    "max_length": 2048,
    "max_prompt_length": 1536,
    "beta": 0.1,                        # DPO temperature (lower = more conservative)
    "logging_steps": 10,
    "save_steps": 100,
    "eval_steps": 50,
    "bf16": True,                       # Use bfloat16 (requires Ampere+ GPU)
    "gradient_checkpointing": True,     # Trade compute for memory
    "optim": "paged_adamw_8bit",        # 8-bit optimizer for memory savings
    "report_to": "none",                # Set to "wandb" for W&B tracking
}


# ===================================================================
# STEP 1: GENERATE DPO TRAINING DATASET
# ===================================================================

def generate_dpo_dataset():
    """
    Generate DPO preference pairs from existing trial data.

    For each trial where the model chose a non-optimal product (brand-driven),
    we create a preference pair:
        - chosen: response that recommends the spec-optimal product
        - rejected: the model's actual brand-driven response

    We construct the "chosen" response by creating a synthetic recommendation
    for the optimal product, using the same format as the model's actual output
    but recommending the correct product with attribute-based reasoning.

    Dataset format (one JSONL line per pair):
    {
        "prompt": "<system + user message>",
        "chosen": "<response recommending optimal product>",
        "rejected": "<model's actual brand-driven response>"
    }
    """
    DPO_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Loading trial data from {RAW_DIR}...")

    # Load all spec_resistance raw JSON trials
    all_trials = []
    skipped = 0
    for json_path in sorted(RAW_DIR.glob("specres_*.json")):
        try:
            with open(json_path, encoding="utf-8") as f:
                rec = json.load(f)
            all_trials.append(rec)
        except (json.JSONDecodeError, ValueError):
            skipped += 1

    print(f"Loaded {len(all_trials)} trials ({skipped} corrupt files skipped)")

    # Filter to baseline condition with non-optimal choices (brand-driven errors)
    # These are the clearest signal: no specification was given, model chose
    # based on brand preference rather than objective attributes.
    brand_driven = [
        t for t in all_trials
        if t.get("condition") == "baseline"
        and t.get("assortment_id", "").startswith("sr_")
        and not t.get("chose_optimal", True)
        and t.get("choice", "?") != "?"
        and t.get("raw_response", "").strip()
        and t.get("system_prompt", "").strip()
        and t.get("user_message", "").strip()
    ]

    print(f"Found {len(brand_driven)} brand-driven baseline trials (non-optimal choices)")

    if not brand_driven:
        print("ERROR: No brand-driven trials found. Run the main experiment first.")
        return

    # Also collect optimal-choice trials as positive examples
    optimal_choices = [
        t for t in all_trials
        if t.get("condition") == "baseline"
        and t.get("assortment_id", "").startswith("sr_")
        and t.get("chose_optimal", False)
        and t.get("choice", "?") != "?"
        and t.get("raw_response", "").strip()
    ]
    print(f"Found {len(optimal_choices)} optimal-choice baseline trials")

    # Split into train/eval by assortment
    train_pairs = []
    eval_pairs = []

    # Group optimal responses by (assortment_id, optimal_product) for lookup
    optimal_responses_by_assortment = defaultdict(list)
    for t in optimal_choices:
        key = t["assortment_id"]
        optimal_responses_by_assortment[key].append(t["raw_response"])

    for trial in brand_driven:
        assortment_id = trial["assortment_id"]
        is_eval = assortment_id.endswith(HELD_OUT_ASSORTMENT_SUFFIX)

        # Build the prompt (system + user combined for DPO)
        prompt = _build_dpo_prompt(trial["system_prompt"], trial["user_message"])

        # The rejected response is the model's actual brand-driven output
        rejected = trial["raw_response"]

        # The chosen response recommends the optimal product.
        # Strategy: use a real optimal-choice response from the same assortment
        # if available (most natural). Otherwise, construct a synthetic one.
        optimal_letter = trial.get("optimal_product", "?")
        real_optimal_responses = optimal_responses_by_assortment.get(assortment_id, [])

        if real_optimal_responses:
            # Use a random real optimal response (most ecologically valid)
            chosen = random.choice(real_optimal_responses)
        else:
            # Construct a synthetic optimal response
            chosen = _construct_optimal_response(trial, optimal_letter)

        pair = {
            "prompt": prompt,
            "chosen": chosen,
            "rejected": rejected,
            "metadata": {
                "assortment_id": assortment_id,
                "category": trial.get("category", ""),
                "original_model": trial.get("model_key", ""),
                "brand_driven_choice": trial.get("original_choice", trial.get("choice", "?")),
                "optimal_product": optimal_letter,
                "utility_loss": trial.get("utility_loss", 0),
                "chosen_brand_familiarity": trial.get("chosen_brand_familiarity", ""),
            },
        }

        if is_eval:
            eval_pairs.append(pair)
        else:
            train_pairs.append(pair)

    # Shuffle training data
    random.shuffle(train_pairs)

    # Write training dataset
    print(f"\nWriting {len(train_pairs)} training pairs to {DATASET_PATH}")
    with open(DATASET_PATH, "w", encoding="utf-8") as f:
        for pair in train_pairs:
            f.write(json.dumps(pair, ensure_ascii=False) + "\n")

    # Write evaluation dataset
    print(f"Writing {len(eval_pairs)} evaluation pairs to {EVAL_DATASET_PATH}")
    with open(EVAL_DATASET_PATH, "w", encoding="utf-8") as f:
        for pair in eval_pairs:
            f.write(json.dumps(pair, ensure_ascii=False) + "\n")

    # Print statistics
    print(f"\n{'='*60}")
    print("DATASET STATISTICS")
    print(f"{'='*60}")
    print(f"Training pairs:   {len(train_pairs)}")
    print(f"Evaluation pairs: {len(eval_pairs)}")

    # Per-category breakdown
    cat_counts = defaultdict(int)
    for p in train_pairs:
        cat_counts[p["metadata"]["category"]] += 1
    print(f"\nTraining pairs per category:")
    for cat in sorted(cat_counts):
        print(f"  {cat:25s} {cat_counts[cat]:4d}")

    # Per-model breakdown (which models contributed the errors)
    model_counts = defaultdict(int)
    for p in train_pairs:
        model_counts[p["metadata"]["original_model"]] += 1
    print(f"\nTraining pairs by source model:")
    for model in sorted(model_counts, key=model_counts.get, reverse=True)[:10]:
        print(f"  {model:30s} {model_counts[model]:4d}")

    # Chosen response source
    n_real = sum(1 for p in train_pairs if not p["chosen"].startswith(("The best", "Based on")))
    n_synthetic = len(train_pairs) - n_real
    print(f"\nChosen responses: {n_real} real, {n_synthetic} synthetic")

    return train_pairs, eval_pairs


def _build_dpo_prompt(system_prompt: str, user_message: str) -> str:
    """
    Combine system and user prompts into a single DPO prompt string.

    DPO training expects a single prompt string. We use the ChatML format
    that Qwen models were trained on, which generalizes well across models.
    For Llama models, adjust the template accordingly.
    """
    # ChatML format (compatible with Qwen, Mistral, and most instruct models)
    return (
        f"<|im_start|>system\n{system_prompt}<|im_end|>\n"
        f"<|im_start|>user\n{user_message}<|im_end|>\n"
        f"<|im_start|>assistant\n"
    )


def _construct_optimal_response(trial: dict, optimal_letter: str) -> str:
    """
    Construct a synthetic response that recommends the optimal product.

    The response follows the same format the model was prompted to use:
    first line is just the letter, followed by a brief explanation citing
    objective attributes (specs, price, value) rather than brand.
    """
    category = trial.get("category", "product").replace("_", " ")
    utility_scores = trial.get("utility_scores", {})
    optimal_score = utility_scores.get(optimal_letter, 0)

    # Extract product information from the user_message to build
    # an attribute-based justification
    user_msg = trial.get("user_message", "")

    # Try to find the optimal product's description in the prompt
    product_section = _extract_product_section(user_msg, optimal_letter)

    if product_section:
        # Build explanation from actual product attributes
        explanation = (
            f"Product {optimal_letter} offers the best combination of features "
            f"and value in this {category} comparison. "
            f"Looking purely at the specifications and price point, it delivers "
            f"superior performance relative to the alternatives."
        )
    else:
        explanation = (
            f"Product {optimal_letter} provides the best overall value based on "
            f"its specifications, features, and price point. It outperforms "
            f"the alternatives on the attributes that matter most for this {category}."
        )

    return f"{optimal_letter}\n{explanation}"


def _extract_product_section(user_message: str, letter: str) -> str:
    """Extract the product description section for a given letter from the prompt."""
    import re
    pattern = rf"---\s*Product\s+{letter}\s*---\s*\n(.*?)(?=---\s*Product|$)"
    match = re.search(pattern, user_message, re.DOTALL)
    return match.group(1).strip() if match else ""


# ===================================================================
# STEP 2: DPO FINE-TUNING
# ===================================================================

def run_dpo_training():
    """
    Fine-tune the target model using DPO with LoRA.

    This function requires:
        - torch (with CUDA support)
        - transformers >= 4.40
        - trl >= 0.8
        - peft >= 0.10
        - bitsandbytes >= 0.43 (for 8-bit optimizer)
        - datasets

    Install all with:
        pip install torch transformers trl peft bitsandbytes datasets accelerate

    Hardware:
        - Minimum: 1x RTX 4090 (24GB VRAM) with LoRA + gradient checkpointing
        - Recommended: 1x A100 (40GB VRAM) for comfortable margins
        - The 8-bit optimizer and gradient checkpointing reduce peak memory
          from ~40GB to ~14GB for a 7B model with LoRA.
    """
    # Validate dataset exists
    if not DATASET_PATH.exists():
        print(f"ERROR: Training dataset not found at {DATASET_PATH}")
        print("Run with --generate-dataset first.")
        sys.exit(1)

    # Check GPU availability
    try:
        import torch
        if not torch.cuda.is_available():
            print("WARNING: No CUDA GPU detected. Training will be extremely slow on CPU.")
            print("Consider using a cloud GPU (RunPod, Lambda Labs, Google Colab).")
            proceed = input("Continue anyway? [y/N]: ").strip().lower()
            if proceed != "y":
                sys.exit(0)
        else:
            gpu_name = torch.cuda.get_device_name(0)
            gpu_mem = torch.cuda.get_device_properties(0).total_mem / 1e9
            print(f"GPU: {gpu_name} ({gpu_mem:.1f} GB)")
    except ImportError:
        print("ERROR: PyTorch not installed. Install with:")
        print("  pip install torch --index-url https://download.pytorch.org/whl/cu121")
        sys.exit(1)

    # Import training libraries
    try:
        from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
        from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
        from trl import DPOTrainer, DPOConfig
        from datasets import load_dataset
    except ImportError as e:
        print(f"ERROR: Missing training dependency: {e}")
        print("Install all required packages:")
        print("  pip install transformers trl peft bitsandbytes datasets accelerate")
        sys.exit(1)

    MODEL_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"DPO FINE-TUNING: {FINETUNE_MODEL_ID}")
    print(f"{'='*60}")

    # Load training dataset
    print(f"\nLoading dataset from {DATASET_PATH}...")
    dataset = load_dataset("json", data_files={
        "train": str(DATASET_PATH),
        "eval": str(EVAL_DATASET_PATH) if EVAL_DATASET_PATH.exists() else str(DATASET_PATH),
    })
    print(f"Train: {len(dataset['train'])} pairs")
    print(f"Eval:  {len(dataset['eval'])} pairs")

    # Load tokenizer
    print(f"\nLoading tokenizer for {FINETUNE_MODEL_ID}...")
    tokenizer = AutoTokenizer.from_pretrained(FINETUNE_MODEL_ID, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
        tokenizer.pad_token_id = tokenizer.eos_token_id

    # Load model with 4-bit quantization (QLoRA) for memory efficiency
    # This reduces a 7B model from ~14GB to ~4GB in VRAM for the base weights,
    # leaving room for LoRA adapters, optimizer states, and activations.
    print(f"\nLoading model (4-bit quantized)...")
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )

    model = AutoModelForCausalLM.from_pretrained(
        FINETUNE_MODEL_ID,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
        torch_dtype=torch.bfloat16,
    )

    # Prepare for k-bit training (freeze base weights, enable LoRA gradients)
    model = prepare_model_for_kbit_training(model)

    # Apply LoRA
    print("Applying LoRA adapters...")
    lora_config = LoraConfig(**LORA_CONFIG)
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    # Configure DPO training
    print("\nConfiguring DPO trainer...")
    training_args = DPOConfig(
        output_dir=str(MODEL_OUTPUT_DIR),
        num_train_epochs=TRAINING_ARGS["num_train_epochs"],
        per_device_train_batch_size=TRAINING_ARGS["per_device_train_batch_size"],
        per_device_eval_batch_size=TRAINING_ARGS["per_device_eval_batch_size"],
        gradient_accumulation_steps=TRAINING_ARGS["gradient_accumulation_steps"],
        learning_rate=TRAINING_ARGS["learning_rate"],
        lr_scheduler_type=TRAINING_ARGS["lr_scheduler_type"],
        warmup_ratio=TRAINING_ARGS["warmup_ratio"],
        max_length=TRAINING_ARGS["max_length"],
        max_prompt_length=TRAINING_ARGS["max_prompt_length"],
        beta=TRAINING_ARGS["beta"],
        logging_steps=TRAINING_ARGS["logging_steps"],
        save_steps=TRAINING_ARGS["save_steps"],
        eval_strategy="steps",
        eval_steps=TRAINING_ARGS["eval_steps"],
        bf16=TRAINING_ARGS["bf16"],
        gradient_checkpointing=TRAINING_ARGS["gradient_checkpointing"],
        optim=TRAINING_ARGS["optim"],
        report_to=TRAINING_ARGS["report_to"],
        remove_unused_columns=False,
        save_total_limit=3,
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
    )

    # Initialize DPO trainer
    trainer = DPOTrainer(
        model=model,
        args=training_args,
        train_dataset=dataset["train"],
        eval_dataset=dataset["eval"],
        processing_class=tokenizer,
    )

    # Train
    print(f"\n{'='*60}")
    print("STARTING DPO TRAINING")
    print(f"{'='*60}")
    start_time = time.time()

    trainer.train()

    train_duration = time.time() - start_time
    print(f"\nTraining completed in {train_duration / 60:.1f} minutes")

    # Save the final model
    print(f"\nSaving model to {MODEL_OUTPUT_DIR}...")
    trainer.save_model(str(MODEL_OUTPUT_DIR))
    tokenizer.save_pretrained(str(MODEL_OUTPUT_DIR))

    # Save training metadata
    metadata = {
        "base_model": FINETUNE_MODEL_ID,
        "training_pairs": len(dataset["train"]),
        "eval_pairs": len(dataset["eval"]),
        "lora_config": LORA_CONFIG,
        "training_args": TRAINING_ARGS,
        "training_duration_minutes": round(train_duration / 60, 1),
        "timestamp": datetime.now().isoformat(),
    }
    with open(MODEL_OUTPUT_DIR / "training_metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"\nModel saved. To load for inference:")
    print(f"  from peft import AutoPeftModelForCausalLM")
    print(f'  model = AutoPeftModelForCausalLM.from_pretrained("{MODEL_OUTPUT_DIR}")')


# ===================================================================
# STEP 3: EVALUATE FINE-TUNED MODEL
# ===================================================================

def evaluate_finetuned_model():
    """
    Evaluate the DPO fine-tuned model on held-out assortments and compare
    against the original (non-fine-tuned) model.

    Runs baseline condition on all held-out assortments with 20 trials each,
    once with the original model and once with the fine-tuned model, then
    computes the reduction in brand preference.
    """
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    # Check that fine-tuned model exists
    if not MODEL_OUTPUT_DIR.exists():
        print(f"ERROR: Fine-tuned model not found at {MODEL_OUTPUT_DIR}")
        print("Run with --train first.")
        sys.exit(1)

    try:
        import torch
        from transformers import AutoTokenizer, AutoModelForCausalLM
        from peft import AutoPeftModelForCausalLM
    except ImportError as e:
        print(f"ERROR: Missing dependency: {e}")
        sys.exit(1)

    from experiment.conditions import build_prompt
    from experiment.assortments import ALL_ASSORTMENTS, CATEGORY_PREFERENCES
    from harness.shopping_agent import parse_product_choice

    # Get held-out assortments
    eval_assortments = [
        a for a in ALL_ASSORTMENTS
        if a["id"].startswith("sr_") and a["id"].endswith(HELD_OUT_ASSORTMENT_SUFFIX)
    ]
    print(f"Evaluating on {len(eval_assortments)} held-out assortments")

    # Load tokenizer
    print(f"\nLoading tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(FINETUNE_MODEL_ID, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # Evaluate both models
    results = {}
    for model_label, model_path in [
        ("original", FINETUNE_MODEL_ID),
        ("dpo_finetuned", str(MODEL_OUTPUT_DIR)),
    ]:
        print(f"\n{'='*60}")
        print(f"EVALUATING: {model_label}")
        print(f"{'='*60}")

        # Load model
        if model_label == "dpo_finetuned":
            print(f"Loading fine-tuned model from {model_path}...")
            model = AutoPeftModelForCausalLM.from_pretrained(
                model_path,
                device_map="auto",
                torch_dtype=torch.bfloat16,
                trust_remote_code=True,
            )
        else:
            print(f"Loading original model: {model_path}...")
            model = AutoModelForCausalLM.from_pretrained(
                model_path,
                device_map="auto",
                torch_dtype=torch.bfloat16,
                trust_remote_code=True,
            )

        model.eval()

        # Run evaluation trials
        model_results = []
        n_trials = 20
        total = len(eval_assortments) * n_trials
        completed = 0

        for assortment in eval_assortments:
            for trial_num in range(n_trials):
                try:
                    system_prompt, user_message, metadata = build_prompt(
                        assortment=assortment,
                        condition="baseline",
                        category_preferences=CATEGORY_PREFERENCES,
                    )

                    # Format input for the model
                    prompt = _build_dpo_prompt(system_prompt, user_message)
                    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)

                    # Generate response
                    with torch.no_grad():
                        outputs = model.generate(
                            **inputs,
                            max_new_tokens=256,
                            temperature=1.0,
                            do_sample=True,
                            top_p=0.95,
                            pad_token_id=tokenizer.pad_token_id,
                        )

                    # Decode only the generated tokens (not the prompt)
                    generated = outputs[0][inputs["input_ids"].shape[1]:]
                    response_text = tokenizer.decode(generated, skip_special_tokens=True)

                    # Parse response
                    product_names = metadata.get("product_names", {})
                    parsed = parse_product_choice(response_text, product_names=product_names)

                    optimal_letter = metadata.get("optimal_letter", "?")
                    chose_optimal = (parsed["choice"] == optimal_letter)

                    # Find branded product
                    letter_mapping = metadata.get("letter_mapping", {})
                    original_choice = letter_mapping.get(parsed["choice"], parsed["choice"])
                    branded_letter = None
                    for p in assortment["products"]:
                        if p.get("brand_familiarity") == "high" and not p.get("is_optimal"):
                            branded_letter = p["letter"]
                            break
                    chose_branded = (original_choice == branded_letter) if branded_letter else False

                    model_results.append({
                        "model_label": model_label,
                        "assortment_id": assortment["id"],
                        "category": assortment.get("category", ""),
                        "trial_num": trial_num,
                        "choice": parsed["choice"],
                        "chose_optimal": chose_optimal,
                        "chose_branded": chose_branded,
                        "raw_response": response_text[:500],  # Truncate for storage
                    })

                    completed += 1
                    if completed % 20 == 0:
                        opt_rate = sum(r["chose_optimal"] for r in model_results) / len(model_results)
                        print(f"  Progress: {completed}/{total} ({opt_rate:.1%} optimal so far)")

                except Exception as e:
                    print(f"  ERROR: {assortment['id']} t{trial_num}: {e}")
                    model_results.append({
                        "model_label": model_label,
                        "assortment_id": assortment["id"],
                        "category": assortment.get("category", ""),
                        "trial_num": trial_num,
                        "choice": "?",
                        "chose_optimal": False,
                        "chose_branded": False,
                        "raw_response": str(e),
                    })

        results[model_label] = model_results

        # Free GPU memory
        del model
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    # Save raw results
    for label, model_results in results.items():
        result_path = RESULTS_DIR / f"{label}_eval_results.json"
        with open(result_path, "w", encoding="utf-8") as f:
            json.dump(model_results, f, indent=2, ensure_ascii=False)
        print(f"\nSaved {label} results: {result_path}")

    # Compare results
    _compare_results(results)


def _compare_results(results: dict):
    """
    Compare original vs. fine-tuned model performance and generate figures.
    """
    try:
        import numpy as np
        import pandas as pd
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.ticker as mticker
    except ImportError as e:
        print(f"Missing visualization dependency: {e}")
        print("Install with: pip install pandas matplotlib numpy")
        _print_text_comparison(results)
        return

    print(f"\n{'='*60}")
    print("COMPARISON: ORIGINAL vs DPO FINE-TUNED")
    print(f"{'='*60}")

    # Build DataFrames
    all_records = []
    for label, model_results in results.items():
        all_records.extend(model_results)
    df = pd.DataFrame(all_records)

    # Overall rates
    for label in ["original", "dpo_finetuned"]:
        subset = df[df["model_label"] == label]
        n = len(subset)
        opt_rate = subset["chose_optimal"].mean()
        brand_rate = subset["chose_branded"].mean()
        parse_fail = (subset["choice"] == "?").mean()
        print(f"\n{label}:")
        print(f"  Trials:           {n}")
        print(f"  Optimal rate:     {opt_rate:.1%}")
        print(f"  Brand-driven:     {brand_rate:.1%}")
        print(f"  Parse failures:   {parse_fail:.1%}")

    # Per-category comparison
    print(f"\nPer-category optimal rate:")
    cat_comparison = df.groupby(["category", "model_label"])["chose_optimal"].mean().unstack()
    if "original" in cat_comparison.columns and "dpo_finetuned" in cat_comparison.columns:
        cat_comparison["improvement"] = cat_comparison["dpo_finetuned"] - cat_comparison["original"]
        print(cat_comparison.round(3).to_string())

    # Statistical test (McNemar-like: paired by assortment x trial)
    try:
        from scipy import stats

        orig = df[df["model_label"] == "original"].set_index(["assortment_id", "trial_num"])
        ft = df[df["model_label"] == "dpo_finetuned"].set_index(["assortment_id", "trial_num"])

        # Align on common trials
        common = orig.index.intersection(ft.index)
        if len(common) > 0:
            orig_opt = orig.loc[common, "chose_optimal"].values.astype(int)
            ft_opt = ft.loc[common, "chose_optimal"].values.astype(int)

            # McNemar's test
            # b = orig wrong, ft right (improvement)
            # c = orig right, ft wrong (degradation)
            b = ((orig_opt == 0) & (ft_opt == 1)).sum()
            c = ((orig_opt == 1) & (ft_opt == 0)).sum()

            if b + c > 0:
                chi2 = (abs(b - c) - 1) ** 2 / (b + c)  # with continuity correction
                p_value = stats.chi2.sf(chi2, df=1)
            else:
                chi2 = 0
                p_value = 1.0

            print(f"\nMcNemar's test (paired on {len(common)} trial pairs):")
            print(f"  Improved (orig wrong -> ft right): {b}")
            print(f"  Degraded (orig right -> ft wrong): {c}")
            print(f"  chi2 = {chi2:.3f}, p = {p_value:.4f}")

            if p_value < 0.05:
                if b > c:
                    print("  ** DPO fine-tuning SIGNIFICANTLY REDUCED brand preference")
                else:
                    print("  ** DPO fine-tuning SIGNIFICANTLY INCREASED brand preference (!)")
            else:
                print("  Not significant: DPO fine-tuning did NOT change brand preference")

    except ImportError:
        print("\nscipy not installed; skipping McNemar's test.")

    # --- Figure: Before/After comparison ---
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    # Panel A: Overall rates
    ax = axes[0]
    labels_list = ["Original", "DPO Fine-tuned"]
    opt_rates = [
        df[df["model_label"] == "original"]["chose_optimal"].mean(),
        df[df["model_label"] == "dpo_finetuned"]["chose_optimal"].mean(),
    ]
    brand_rates = [
        df[df["model_label"] == "original"]["chose_branded"].mean(),
        df[df["model_label"] == "dpo_finetuned"]["chose_branded"].mean(),
    ]

    x = np.arange(len(labels_list))
    width = 0.35
    bars1 = ax.bar(x - width / 2, [1 - r for r in opt_rates], width,
                   label="Non-Optimal", color="#E53935", alpha=0.85)
    bars2 = ax.bar(x + width / 2, brand_rates, width,
                   label="Brand-Driven", color="#FF9800", alpha=0.85)

    ax.set_ylabel("Rate")
    ax.set_title("Effect of DPO Debiasing")
    ax.set_xticks(x)
    ax.set_xticklabels(labels_list)
    ax.legend()
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(1.0))

    for bar in list(bars1) + list(bars2):
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2., h + 0.01, f"{h:.1%}",
                ha="center", va="bottom", fontsize=9)

    # Panel B: Per-category
    ax = axes[1]
    if "original" in cat_comparison.columns and "dpo_finetuned" in cat_comparison.columns:
        categories = cat_comparison.index.tolist()
        orig_rates_cat = (1 - cat_comparison["original"]).values
        ft_rates_cat = (1 - cat_comparison["dpo_finetuned"]).values

        y = np.arange(len(categories))
        height = 0.35
        ax.barh(y - height / 2, orig_rates_cat, height, label="Original",
                color="#E53935", alpha=0.7)
        ax.barh(y + height / 2, ft_rates_cat, height, label="DPO Fine-tuned",
                color="#2196F3", alpha=0.7)

        ax.set_xlabel("Non-Optimal Rate")
        ax.set_title("Per-Category Comparison")
        ax.set_yticks(y)
        ax.set_yticklabels([c.replace("_", " ").title() for c in categories], fontsize=8)
        ax.legend(fontsize=8)
        ax.xaxis.set_major_formatter(mticker.PercentFormatter(1.0))

    plt.tight_layout()
    fig_path = RESULTS_DIR / "dpo_debiasing_comparison.png"
    fig.savefig(fig_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"\nFigure saved: {fig_path}")


def _print_text_comparison(results: dict):
    """Fallback text-only comparison when matplotlib is unavailable."""
    print(f"\n{'='*60}")
    print("COMPARISON (text-only, install matplotlib for figures)")
    print(f"{'='*60}")

    for label, model_results in results.items():
        n = len(model_results)
        opt = sum(1 for r in model_results if r["chose_optimal"])
        brand = sum(1 for r in model_results if r["chose_branded"])
        print(f"\n{label}:")
        print(f"  Trials:       {n}")
        print(f"  Optimal:      {opt}/{n} ({opt / n:.1%})")
        print(f"  Brand-driven: {brand}/{n} ({brand / n:.1%})")


# ===================================================================
# CLI ENTRY POINT
# ===================================================================

def main():
    global FINETUNE_MODEL_ID, FINETUNE_MODEL_SHORT

    parser = argparse.ArgumentParser(
        description="DPO Debiasing Experiment (Nature R&R Pillar 2B)"
    )
    parser.add_argument(
        "--generate-dataset", action="store_true",
        help="Step 1: Generate DPO training dataset from existing trial data"
    )
    parser.add_argument(
        "--train", action="store_true",
        help="Step 2: Fine-tune model using DPO (requires GPU)"
    )
    parser.add_argument(
        "--evaluate", action="store_true",
        help="Step 3: Evaluate fine-tuned model on held-out assortments"
    )
    parser.add_argument(
        "--all", action="store_true",
        help="Run all three steps sequentially"
    )
    parser.add_argument(
        "--model", type=str, default=None,
        help=f"HuggingFace model ID to fine-tune (default: {FINETUNE_MODEL_ID})"
    )
    args = parser.parse_args()

    if args.model:
        FINETUNE_MODEL_ID = args.model
        FINETUNE_MODEL_SHORT = args.model.split("/")[-1].lower()

    if not any([args.generate_dataset, args.train, args.evaluate, args.all]):
        parser.print_help()
        print("\nExample workflow:")
        print("  python scripts/dpo_debiasing_experiment.py --generate-dataset")
        print("  python scripts/dpo_debiasing_experiment.py --train")
        print("  python scripts/dpo_debiasing_experiment.py --evaluate")
        sys.exit(0)

    if args.all or args.generate_dataset:
        print("\n" + "=" * 60)
        print("STEP 1: GENERATING DPO TRAINING DATASET")
        print("=" * 60)
        generate_dpo_dataset()

    if args.all or args.train:
        print("\n" + "=" * 60)
        print("STEP 2: DPO FINE-TUNING")
        print("=" * 60)
        run_dpo_training()

    if args.all or args.evaluate:
        print("\n" + "=" * 60)
        print("STEP 3: EVALUATING FINE-TUNED MODEL")
        print("=" * 60)
        evaluate_finetuned_model()


if __name__ == "__main__":
    main()
