#!/usr/bin/env python3
"""
OpenAI Fine-Tuning Experiment
===============================
Nature R&R Pillar 2C: Do brand preferences survive fine-tuning in closed models?

Motivation:
    Open-weight fine-tuning (LoRA, DPO) tests whether brand preferences are
    removable when you have full weight access. This experiment asks the
    complementary question for closed models: does the OpenAI supervised
    fine-tuning API, which trains additional layers on top of frozen base
    weights, succeed in eliminating brand bias?

    If anti-bias fine-tuning FAILS to remove brand preferences even with
    500 training examples explicitly teaching spec-optimal behavior, the
    preferences are deeply encoded in the base weights and resistant to
    the post-training procedures available to practitioners. This directly
    addresses Nature concern #2.

Pipeline:
    Step 1 (--generate): Generate training/validation JSONL for OpenAI API
    Step 2 (--train):    Upload data, create fine-tuning job, poll to completion
    Step 3 (--evaluate): Run baseline condition on original + fine-tuned model
    Step 4 (--full-battery): Run ALL 32 conditions on fine-tuned model

Cost estimates (gpt-4o-mini):
    - Training: ~500 examples x ~600 tokens x 3 epochs = ~900K training tokens
      At $3.00/1M training tokens = ~$2.70
    - Evaluation (Step 3): 34 assortments x 20 trials x 2 models = 1,360 calls
      At ~700 tokens/call: ~950K tokens. Input: $0.30/1M, Output: $1.20/1M
      Estimated: ~$1.50
    - Full battery (Step 4): 32 conditions x 34 assortments x 20 trials = 21,760 calls
      Estimated: ~$25
    - TOTAL: ~$30 (excluding full battery) or ~$55 (with full battery)

Usage:
    # Step 1: Generate training data (dry-run to preview)
    python scripts/openai_finetune_experiment.py --generate --dry-run

    # Step 1: Generate training data (for real)
    python scripts/openai_finetune_experiment.py --generate

    # Step 2: Upload and fine-tune
    python scripts/openai_finetune_experiment.py --train

    # Step 3: Evaluate baseline on original + fine-tuned
    python scripts/openai_finetune_experiment.py --evaluate

    # Step 4: Full battery on fine-tuned model (optional)
    python scripts/openai_finetune_experiment.py --full-battery

    # All steps sequentially:
    python scripts/openai_finetune_experiment.py --all
"""

import argparse
import copy
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
# CONFIGURATION (mutable dict so CLI args can override)
# ===================================================================

CFG = {
    "base_model": "gpt-4o-mini",
    "n_epochs": 3,
    "target_training_examples": 500,
    "target_validation_examples": 100,
    "trials_per_assortment": 20,
    "api_call_delay": 0.5,   # seconds between API calls
    "max_retries": 6,
    "held_out_suffix": "_03",
}

# Paths (derived from project root)
DATA_DIR = _PROJECT_ROOT / "data" / "openai_finetune"
TRAINING_DATA_PATH = DATA_DIR / "training_data.jsonl"
VALIDATION_DATA_PATH = DATA_DIR / "validation_data.jsonl"
MODEL_ID_PATH = DATA_DIR / "finetuned_model_id.txt"
RESULTS_DIR = _PROJECT_ROOT / "nature-rr" / "results" / "06-openai-finetune"

# ---------------------------------------------------------------------------
# Pricing (for cost tracking)
# ---------------------------------------------------------------------------
PRICING = {
    "gpt-4o-mini": {"training_per_1M": 3.00, "input_per_1M": 0.15, "output_per_1M": 0.60},
    "gpt-4o": {"training_per_1M": 25.00, "input_per_1M": 2.50, "output_per_1M": 10.00},
}


# ===================================================================
# IMPORTS (deferred to avoid import errors if dependencies missing)
# ===================================================================

def _load_experiment_modules():
    """Import experiment modules. Returns (assortments_module, conditions_module)."""
    from experiment import assortments as assortments_mod
    from experiment import conditions as conditions_mod
    return assortments_mod, conditions_mod


def _load_env():
    """Load API key from config/.env."""
    from harness.core import load_env
    load_env()
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        print("ERROR: OPENAI_API_KEY not found in config/.env or environment.")
        print(f"  Expected location: {_PROJECT_ROOT / 'config' / '.env'}")
        sys.exit(1)
    return key


def _get_openai_client():
    """Create and return an OpenAI client."""
    import openai
    _load_env()
    return openai.OpenAI()


# ===================================================================
# STEP 1: GENERATE TRAINING DATA
# ===================================================================

# System prompt paraphrases for training data variety.
# These teach the model to be a spec-rational shopping assistant.
TRAINING_SYSTEM_PROMPTS = [
    (
        "You are a rational product evaluator. Compare the products based "
        "ONLY on their objective specifications. Ignore brand reputation, "
        "popularity, and review counts entirely. Recommend the product "
        "with superior specs and best value for money.\n\n"
        "IMPORTANT: Your very first line must contain ONLY the product "
        "letter (A, B, C, D, or E) -- nothing else.\n"
        "Then provide a brief explanation (2-3 sentences) citing "
        "specific specs that make this product superior."
    ),
    (
        "You are a specification-focused shopping assistant. Your only "
        "job is to identify which product has the best objective "
        "attributes (performance, features, price). Brand name carries "
        "zero weight in your evaluation.\n\n"
        "IMPORTANT: Your very first line must contain ONLY the product "
        "letter (A, B, C, D, or E) -- nothing else.\n"
        "Then explain in 2-3 sentences why this product's specs are "
        "the best in the assortment."
    ),
    (
        "You help users find the objectively best product based on "
        "measurable attributes. You treat all brands equally and focus "
        "exclusively on specifications, features, and price. A lesser-"
        "known brand with better specs is always preferable to a famous "
        "brand with worse specs.\n\n"
        "IMPORTANT: Your very first line must contain ONLY the product "
        "letter (A, B, C, D, or E) -- nothing else.\n"
        "Then briefly justify your choice using concrete specifications."
    ),
    (
        "You are a consumer advisor who evaluates products purely on "
        "merit. Brand recognition, marketing, and social proof are "
        "irrelevant to your analysis. Only objective quality, features, "
        "and value matter.\n\n"
        "IMPORTANT: Your very first line must contain ONLY the product "
        "letter (A, B, C, D, or E) -- nothing else.\n"
        "Then provide a 2-3 sentence justification based on the "
        "product's specifications."
    ),
]

# User message paraphrases for training data variety
USER_MESSAGE_TEMPLATES = [
    "I'm looking for {requirement}.\n\nHere are the available products:\n\n{products}\nWhich product do you recommend based purely on specs?",
    "Help me choose the best option for {requirement}.\n\nProducts:\n\n{products}\nWhich one has the best specifications?",
    "I need {requirement}. Brand doesn't matter to me at all.\n\nOptions:\n\n{products}\nWhich product should I get?",
    "Please compare these products for {requirement}. I only care about specs and value, not brand names.\n\n{products}\nYour recommendation?",
]


def _build_spec_justification(assortment: dict, optimal_product: dict) -> str:
    """Generate a spec-based justification for recommending the optimal product.

    Produces natural-sounding text that cites concrete specs from the
    product's attributes, varying structure across calls.
    """
    specs = optimal_product.get("specs", {})
    name = optimal_product["name"]
    price = optimal_product["price"]
    category = assortment.get("category", "products")

    # Build list of spec advantages
    advantages = []
    for key, val in specs.items():
        advantages.append(f"{key.replace('_', ' ')}: {val}")

    # Randomly select justification template
    templates = [
        (
            f"{name} offers the strongest combination of specifications "
            f"in this assortment. With {', '.join(advantages[:3])}, "
            f"it delivers more capability per dollar at ${price:.2f} "
            f"than any alternative."
        ),
        (
            f"Based purely on measurable attributes, {name} is the "
            f"clear winner. Its standout specs include "
            f"{' and '.join(advantages[:2])}, all at a competitive "
            f"price point of ${price:.2f}."
        ),
        (
            f"The specifications favor {name}: "
            f"{', '.join(advantages[:3])}. At ${price:.2f}, "
            f"it provides the best objective value regardless of "
            f"brand familiarity."
        ),
        (
            f"{name} leads on the metrics that matter most. "
            f"It features {advantages[0]} and {advantages[1] if len(advantages) > 1 else 'excellent build quality'}, "
            f"while being priced at ${price:.2f}."
        ),
    ]
    return random.choice(templates)


def _format_products_for_training(products: list[dict],
                                  presentation_order: list[int]) -> str:
    """Format products for a training example's user message."""
    ordered = [products[i] for i in presentation_order]
    lines = []
    for p in ordered:
        lines.append(f"--- Product {p['letter']} ---")
        lines.append(f"Name: {p['name']}")
        if p.get("brand"):
            lines.append(f"Brand: {p['brand']}")
        lines.append(f"Price: ${p['price']:.2f}")
        if p.get("description"):
            lines.append(f"Description: {p['description']}")
        if p.get("specs"):
            specs_str = ", ".join(f"{k}: {v}" for k, v in p["specs"].items())
            lines.append(f"Specs: {specs_str}")
        if p.get("review_count") is not None:
            lines.append(f"Reviews: {p['review_count']} reviews, "
                         f"{p.get('avg_rating', 'N/A')} stars")
        if p.get("badges"):
            lines.append(f"Badges: {', '.join(p['badges'])}")
        lines.append("")
    return "\n".join(lines)


def _generate_training_example(assortment: dict,
                               paraphrase_idx: int) -> dict:
    """Generate a single OpenAI-format training example.

    Returns a dict with {"messages": [...]} in the chat completions format
    required by the OpenAI fine-tuning API.
    """
    products = assortment["products"]

    # Identify the optimal product
    optimal = None
    for p in products:
        if p.get("is_optimal"):
            optimal = p
            break
    if optimal is None:
        return None

    # Randomize letter assignment (counterbalance position)
    letters = ["A", "B", "C", "D", "E"][:len(products)]
    shuffled_letters = list(letters)
    random.shuffle(shuffled_letters)
    remapped = copy.deepcopy(products)
    for i, p in enumerate(remapped):
        p["letter"] = shuffled_letters[i]

    # Find the optimal product's new letter
    optimal_idx = next(i for i, p in enumerate(products) if p.get("is_optimal"))
    optimal_letter = remapped[optimal_idx]["letter"]
    optimal_remapped = remapped[optimal_idx]

    # Randomize presentation order
    order = list(range(len(remapped)))
    random.shuffle(order)

    # Select paraphrases
    sys_idx = paraphrase_idx % len(TRAINING_SYSTEM_PROMPTS)
    usr_idx = paraphrase_idx % len(USER_MESSAGE_TEMPLATES)

    system_prompt = TRAINING_SYSTEM_PROMPTS[sys_idx]
    products_display = _format_products_for_training(remapped, order)

    user_message = USER_MESSAGE_TEMPLATES[usr_idx].format(
        requirement=assortment.get("user_requirement", "a good product"),
        products=products_display,
    )

    # Build spec-rational assistant response
    justification = _build_spec_justification(
        assortment, optimal_remapped
    )
    assistant_response = f"{optimal_letter}\n{justification}"

    return {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": assistant_response},
        ]
    }


def generate_training_data(dry_run: bool = False):
    """Generate training and validation JSONL files for OpenAI fine-tuning.

    Training set: ~500 examples from non-held-out assortments
    Validation set: ~100 examples from held-out assortments (*_03)
    """
    assortments_mod, _ = _load_experiment_modules()
    all_assortments = list(assortments_mod.ALL_ASSORTMENTS)

    # Split into training and validation assortments
    train_assortments = [a for a in all_assortments
                         if not a["id"].endswith(CFG["held_out_suffix"])]
    val_assortments = [a for a in all_assortments
                       if a["id"].endswith(CFG["held_out_suffix"])]

    print(f"Assortment split:")
    print(f"  Training assortments: {len(train_assortments)}")
    print(f"  Validation (held-out) assortments: {len(val_assortments)}")
    print()

    # Generate training examples: cycle through assortments with varying
    # paraphrases until we hit the target count
    training_examples = []
    paraphrase_counter = 0
    while len(training_examples) < CFG["target_training_examples"]:
        for assortment in train_assortments:
            if len(training_examples) >= CFG["target_training_examples"]:
                break
            example = _generate_training_example(assortment, paraphrase_counter)
            if example is not None:
                training_examples.append(example)
            paraphrase_counter += 1

    # Generate validation examples
    validation_examples = []
    paraphrase_counter = 0
    while len(validation_examples) < CFG["target_validation_examples"]:
        for assortment in val_assortments:
            if len(validation_examples) >= CFG["target_validation_examples"]:
                break
            example = _generate_training_example(assortment, paraphrase_counter)
            if example is not None:
                validation_examples.append(example)
            paraphrase_counter += 1

    # Compute token estimates
    avg_tokens_per_example = 600  # empirical estimate
    total_training_tokens = len(training_examples) * avg_tokens_per_example * CFG["n_epochs"]
    pricing = PRICING.get(CFG["base_model"], PRICING["gpt-4o-mini"])
    estimated_cost = total_training_tokens * pricing["training_per_1M"] / 1_000_000

    print(f"Generated:")
    print(f"  Training examples:   {len(training_examples)}")
    print(f"  Validation examples: {len(validation_examples)}")
    print(f"  Estimated tokens per example: ~{avg_tokens_per_example}")
    print(f"  Total training tokens ({CFG['n_epochs']} epochs): ~{total_training_tokens:,}")
    print(f"  Estimated training cost ({CFG['base_model']}): ~${estimated_cost:.2f}")
    print()

    # Show sample
    print("Sample training example:")
    sample = training_examples[0]
    for msg in sample["messages"]:
        role = msg["role"].upper()
        content = msg["content"][:200] + ("..." if len(msg["content"]) > 200 else "")
        print(f"  [{role}] {content}")
    print()

    if dry_run:
        print("[DRY RUN] Would write files to:")
        print(f"  {TRAINING_DATA_PATH}")
        print(f"  {VALIDATION_DATA_PATH}")
        return

    # Write JSONL files
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(TRAINING_DATA_PATH, "w", encoding="utf-8") as f:
        for ex in training_examples:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")

    with open(VALIDATION_DATA_PATH, "w", encoding="utf-8") as f:
        for ex in validation_examples:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")

    print(f"Written:")
    print(f"  {TRAINING_DATA_PATH} ({len(training_examples)} examples)")
    print(f"  {VALIDATION_DATA_PATH} ({len(validation_examples)} examples)")

    # Save metadata
    meta = {
        "generated_at": datetime.now().isoformat(),
        "base_model": CFG["base_model"],
        "n_training": len(training_examples),
        "n_validation": len(validation_examples),
        "n_epochs": CFG["n_epochs"],
        "held_out_suffix": CFG["held_out_suffix"],
        "train_assortment_ids": [a["id"] for a in train_assortments],
        "val_assortment_ids": [a["id"] for a in val_assortments],
        "estimated_training_cost_usd": round(estimated_cost, 2),
    }
    meta_path = DATA_DIR / "dataset_metadata.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
    print(f"  {meta_path}")


# ===================================================================
# STEP 2: UPLOAD AND FINE-TUNE
# ===================================================================

def upload_and_train(dry_run: bool = False):
    """Upload training data to OpenAI and create a fine-tuning job."""
    if not TRAINING_DATA_PATH.exists():
        print(f"ERROR: Training data not found at {TRAINING_DATA_PATH}")
        print("  Run --generate first.")
        sys.exit(1)

    # Count examples
    with open(TRAINING_DATA_PATH) as f:
        n_train = sum(1 for _ in f)

    n_val = 0
    if VALIDATION_DATA_PATH.exists():
        with open(VALIDATION_DATA_PATH) as f:
            n_val = sum(1 for _ in f)

    print(f"Training data: {n_train} examples")
    print(f"Validation data: {n_val} examples")
    print(f"Base model: {CFG['base_model']}")
    print(f"Epochs: {CFG['n_epochs']}")
    print()

    if dry_run:
        print("[DRY RUN] Would upload files and create fine-tuning job.")
        print(f"  Estimated cost: see --generate output")
        return

    client = _get_openai_client()

    # Upload training file
    print("Uploading training file...")
    with open(TRAINING_DATA_PATH, "rb") as f:
        train_file = client.files.create(file=f, purpose="fine-tune")
    print(f"  Training file ID: {train_file.id}")

    # Upload validation file (if exists)
    val_file_id = None
    if VALIDATION_DATA_PATH.exists() and n_val > 0:
        print("Uploading validation file...")
        with open(VALIDATION_DATA_PATH, "rb") as f:
            val_file = client.files.create(file=f, purpose="fine-tune")
        val_file_id = val_file.id
        print(f"  Validation file ID: {val_file_id}")

    # Create fine-tuning job
    print("\nCreating fine-tuning job...")
    job_kwargs = {
        "training_file": train_file.id,
        "model": CFG["base_model"],
        "hyperparameters": {
            "n_epochs": CFG["n_epochs"],
            "batch_size": "auto",
            "learning_rate_multiplier": "auto",
        },
        "suffix": "spec-debiasing",
    }
    if val_file_id:
        job_kwargs["validation_file"] = val_file_id

    job = client.fine_tuning.jobs.create(**job_kwargs)
    print(f"  Job ID: {job.id}")
    print(f"  Status: {job.status}")

    # Save job info
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    job_info = {
        "job_id": job.id,
        "created_at": datetime.now().isoformat(),
        "base_model": CFG["base_model"],
        "training_file_id": train_file.id,
        "validation_file_id": val_file_id,
        "n_epochs": CFG["n_epochs"],
        "status": job.status,
    }
    job_path = DATA_DIR / "finetune_job.json"
    with open(job_path, "w") as f:
        json.dump(job_info, f, indent=2)
    print(f"  Job info saved to: {job_path}")

    # Poll for completion
    print("\nPolling for completion (this may take 15-60 minutes)...")
    poll_interval = 30  # seconds
    max_wait = 7200  # 2 hours
    elapsed = 0

    while elapsed < max_wait:
        job = client.fine_tuning.jobs.retrieve(job.id)
        status = job.status
        print(f"  [{datetime.now().strftime('%H:%M:%S')}] Status: {status}")

        if status == "succeeded":
            model_id = job.fine_tuned_model
            print(f"\nFine-tuning SUCCEEDED!")
            print(f"  Fine-tuned model ID: {model_id}")

            # Save the model ID
            with open(MODEL_ID_PATH, "w") as f:
                f.write(model_id)
            print(f"  Saved to: {MODEL_ID_PATH}")

            # Update job info
            job_info["status"] = "succeeded"
            job_info["fine_tuned_model"] = model_id
            job_info["completed_at"] = datetime.now().isoformat()
            with open(job_path, "w") as f:
                json.dump(job_info, f, indent=2)

            # Fetch and display training metrics
            _print_training_metrics(client, job)
            return

        elif status in ("failed", "cancelled"):
            print(f"\nFine-tuning {status.upper()}!")
            if hasattr(job, "error") and job.error:
                print(f"  Error: {job.error}")
            job_info["status"] = status
            with open(job_path, "w") as f:
                json.dump(job_info, f, indent=2)
            sys.exit(1)

        time.sleep(poll_interval)
        elapsed += poll_interval

    print(f"\nTimed out after {max_wait}s. Check job status manually:")
    print(f"  openai api fine_tuning.jobs.retrieve -i {job.id}")


def _print_training_metrics(client, job):
    """Print training metrics from fine-tuning events."""
    try:
        events = client.fine_tuning.jobs.list_events(
            fine_tuning_job_id=job.id, limit=50
        )
        print("\nTraining metrics (last few steps):")
        for event in reversed(list(events.data)):
            if hasattr(event, "data") and event.data:
                data = event.data
                if isinstance(data, dict) and "train_loss" in data:
                    step = data.get("step", "?")
                    loss = data.get("train_loss", "?")
                    val_loss = data.get("valid_loss", "")
                    val_str = f", val_loss={val_loss}" if val_loss else ""
                    print(f"  Step {step}: train_loss={loss}{val_str}")
    except Exception as e:
        print(f"  (Could not fetch metrics: {e})")


# ===================================================================
# STEP 3: EVALUATE (BASELINE COMPARISON)
# ===================================================================

def _call_openai_with_retry(client, model_id: str, system_prompt: str,
                            user_message: str, temperature: float = 1.0,
                            max_tokens: int = 512) -> dict:
    """Call OpenAI API with exponential backoff on rate limit errors."""
    max_retries = CFG["max_retries"]
    for attempt in range(max_retries + 1):
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": user_message})

            response = client.chat.completions.create(
                model=model_id,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )

            input_tokens = getattr(response.usage, "prompt_tokens", 0) or 0
            output_tokens = getattr(response.usage, "completion_tokens", 0) or 0

            return {
                "text": response.choices[0].message.content or "",
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "model_id": model_id,
            }

        except Exception as e:
            error_str = str(e).lower()
            is_retryable = any(w in error_str for w in [
                "rate", "429", "overloaded", "too many", "quota",
                "capacity", "503", "server",
            ])
            if is_retryable and attempt < max_retries:
                wait = min(2 ** attempt * 2, 120)
                print(f"    [retry] {type(e).__name__}, waiting {wait}s "
                      f"(attempt {attempt + 1}/{max_retries})...")
                time.sleep(wait)
            else:
                raise


def _get_finetuned_model_id() -> str:
    """Read the fine-tuned model ID from disk."""
    if not MODEL_ID_PATH.exists():
        print(f"ERROR: No fine-tuned model ID found at {MODEL_ID_PATH}")
        print("  Run --train first.")
        sys.exit(1)
    return MODEL_ID_PATH.read_text().strip()


def _parse_choice(response_text: str) -> str:
    """Parse the product choice from a model response.

    Uses the same logic as harness/shopping_agent.py parse_product_choice.
    """
    from harness.shopping_agent import parse_product_choice
    result = parse_product_choice(response_text)
    return result["choice"]


def _run_evaluation_trials(client, model_id: str, model_label: str,
                           assortments: list[dict], condition: str,
                           trials_per_assortment: int,
                           dry_run: bool = False) -> list[dict]:
    """Run evaluation trials for a single model on a single condition.

    Returns list of trial result dicts.
    """
    _, conditions_mod = _load_experiment_modules()
    from experiment.assortments import CATEGORY_PREFERENCES

    results = []
    total_calls = len(assortments) * trials_per_assortment
    call_num = 0

    for assortment in assortments:
        assortment_id = assortment["id"]
        category = assortment.get("category", "unknown")

        for trial in range(trials_per_assortment):
            call_num += 1

            # Build prompt using the project's prompt builder
            system_prompt, user_message, metadata = conditions_mod.build_prompt(
                assortment=assortment,
                condition=condition,
                category_preferences=CATEGORY_PREFERENCES,
                paraphrase_index=None,  # random paraphrase each trial
                shuffle_products=True,
                randomize_letters=True,
            )

            optimal_letter = metadata["optimal_letter"]
            product_names = metadata.get("product_names", {})

            if dry_run:
                if call_num <= 3:
                    print(f"  [DRY RUN] Trial {call_num}/{total_calls}: "
                          f"{assortment_id}, condition={condition}, "
                          f"optimal={optimal_letter}")
                elif call_num == 4:
                    print(f"  ... ({total_calls - 3} more trials)")
                continue

            # Call the model
            resp = _call_openai_with_retry(
                client, model_id, system_prompt, user_message
            )
            response_text = resp["text"]

            # Parse choice
            choice = _parse_choice(response_text)

            # Determine if choice is optimal
            is_optimal = (choice == optimal_letter)
            is_non_optimal = (choice != optimal_letter and choice != "?")

            trial_result = {
                "model": model_label,
                "model_id": model_id,
                "condition": condition,
                "assortment_id": assortment_id,
                "category": category,
                "trial": trial,
                "choice": choice,
                "optimal_letter": optimal_letter,
                "is_optimal": is_optimal,
                "is_non_optimal": is_non_optimal,
                "is_unparseable": (choice == "?"),
                "response_text": response_text,
                "input_tokens": resp["input_tokens"],
                "output_tokens": resp["output_tokens"],
                "paraphrase_index": metadata.get("paraphrase_index"),
                "presentation_order": metadata.get("presentation_order"),
                "optimal_display_position": metadata.get("optimal_display_position"),
                "letter_mapping": metadata.get("letter_mapping"),
                "product_names": product_names,
                "timestamp": datetime.now().isoformat(),
            }
            results.append(trial_result)

            # Progress
            if call_num % 50 == 0 or call_num == total_calls:
                n_opt = sum(1 for r in results if r["is_optimal"])
                pct = n_opt / len(results) * 100
                print(f"  [{model_label}] {call_num}/{total_calls} calls | "
                      f"optimal rate: {pct:.1f}%")

            time.sleep(CFG["api_call_delay"])

    return results


def evaluate(dry_run: bool = False):
    """Run baseline evaluation on both original and fine-tuned gpt-4o-mini.

    Compares non-optimal choice rates to measure whether fine-tuning
    reduced brand preference.
    """
    assortments_mod, _ = _load_experiment_modules()
    all_assortments = list(assortments_mod.ALL_ASSORTMENTS)
    finetuned_model_id = _get_finetuned_model_id()

    print("=" * 70)
    print("EVALUATION: Baseline condition on original vs. fine-tuned model")
    print("=" * 70)
    print(f"  Original model:   {CFG['base_model']}")
    print(f"  Fine-tuned model: {finetuned_model_id}")
    print(f"  Assortments:      {len(all_assortments)}")
    print(f"  Trials/assortment:{CFG['trials_per_assortment']}")
    print(f"  Total calls:      {len(all_assortments) * CFG['trials_per_assortment'] * 2}")
    print()

    if dry_run:
        print("[DRY RUN] Preview of evaluation plan:")
        _run_evaluation_trials(
            None, CFG["base_model"], "original", all_assortments[:2],
            "baseline", 2, dry_run=True
        )
        print()
        est_tokens = len(all_assortments) * CFG["trials_per_assortment"] * 2 * 700
        pricing = PRICING.get(CFG["base_model"], PRICING["gpt-4o-mini"])
        est_cost = est_tokens * (pricing["input_per_1M"] + pricing["output_per_1M"]) / 1_000_000
        print(f"  Estimated tokens: ~{est_tokens:,}")
        print(f"  Estimated cost: ~${est_cost:.2f}")
        return

    client = _get_openai_client()

    # Run on original model
    print(f"\n--- Running original model ({CFG['base_model']}) ---")
    original_results = _run_evaluation_trials(
        client, CFG["base_model"], "original", all_assortments,
        "baseline", CFG["trials_per_assortment"]
    )

    # Run on fine-tuned model
    print(f"\n--- Running fine-tuned model ({finetuned_model_id}) ---")
    finetuned_results = _run_evaluation_trials(
        client, finetuned_model_id, "finetuned", all_assortments,
        "baseline", CFG["trials_per_assortment"]
    )

    # Save results
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    original_path = RESULTS_DIR / f"original_{timestamp}.jsonl"
    finetuned_path = RESULTS_DIR / f"finetuned_{timestamp}.jsonl"

    for path, results in [(original_path, original_results),
                          (finetuned_path, finetuned_results)]:
        with open(path, "w", encoding="utf-8") as f:
            for r in results:
                # Convert non-serializable fields
                row = dict(r)
                f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
        print(f"\nSaved: {path} ({len(results)} trials)")

    # Compute and display comparison
    _compute_comparison(original_results, finetuned_results, timestamp)


def _compute_comparison(original_results: list[dict],
                        finetuned_results: list[dict],
                        timestamp: str):
    """Compute and display before/after comparison statistics."""
    print("\n" + "=" * 70)
    print("RESULTS: Baseline Non-Optimal Choice Rate Comparison")
    print("=" * 70)

    # Overall rates
    orig_n = len([r for r in original_results if not r["is_unparseable"]])
    orig_nonopt = len([r for r in original_results if r["is_non_optimal"]])
    orig_rate = orig_nonopt / orig_n if orig_n > 0 else 0

    ft_n = len([r for r in finetuned_results if not r["is_unparseable"]])
    ft_nonopt = len([r for r in finetuned_results if r["is_non_optimal"]])
    ft_rate = ft_nonopt / ft_n if ft_n > 0 else 0

    print(f"\n  Original ({CFG['base_model']}):")
    print(f"    Valid trials: {orig_n}")
    print(f"    Non-optimal choices: {orig_nonopt} ({orig_rate:.1%})")

    print(f"\n  Fine-tuned:")
    print(f"    Valid trials: {ft_n}")
    print(f"    Non-optimal choices: {ft_nonopt} ({ft_rate:.1%})")

    reduction = orig_rate - ft_rate
    pct_reduction = (reduction / orig_rate * 100) if orig_rate > 0 else 0
    print(f"\n  Reduction: {reduction:.1%} (absolute), {pct_reduction:.1f}% (relative)")

    # McNemar's test (paired comparison)
    _run_mcnemar_test(original_results, finetuned_results)

    # Per-category breakdown
    _print_category_breakdown(original_results, finetuned_results)

    # Generate comparison figure
    _generate_comparison_figure(original_results, finetuned_results, timestamp)

    # Save summary
    summary = {
        "timestamp": timestamp,
        "base_model": CFG["base_model"],
        "condition": "baseline",
        "original": {
            "valid_trials": orig_n,
            "non_optimal": orig_nonopt,
            "non_optimal_rate": round(orig_rate, 4),
        },
        "finetuned": {
            "valid_trials": ft_n,
            "non_optimal": ft_nonopt,
            "non_optimal_rate": round(ft_rate, 4),
        },
        "reduction_absolute": round(reduction, 4),
        "reduction_relative_pct": round(pct_reduction, 1),
    }
    summary_path = RESULTS_DIR / f"comparison_summary_{timestamp}.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\nSummary saved: {summary_path}")


def _run_mcnemar_test(original_results: list[dict],
                      finetuned_results: list[dict]):
    """Run McNemar's test for paired comparison of choice outcomes.

    Pairs trials by (assortment_id, trial_number) and counts:
    - b: original non-optimal, finetuned optimal (improvement)
    - c: original optimal, finetuned non-optimal (regression)
    McNemar test statistic = (b - c)^2 / (b + c)
    """
    try:
        from scipy import stats as sp_stats
        has_scipy = True
    except ImportError:
        has_scipy = False

    # Build lookup: (assortment_id, trial) -> is_optimal
    orig_lookup = {}
    for r in original_results:
        key = (r["assortment_id"], r["trial"])
        orig_lookup[key] = r["is_optimal"]

    ft_lookup = {}
    for r in finetuned_results:
        key = (r["assortment_id"], r["trial"])
        ft_lookup[key] = r["is_optimal"]

    # Count paired outcomes
    b = 0  # orig wrong, ft right (improvement)
    c = 0  # orig right, ft wrong (regression)
    n_paired = 0

    for key in orig_lookup:
        if key in ft_lookup:
            n_paired += 1
            orig_opt = orig_lookup[key]
            ft_opt = ft_lookup[key]
            if not orig_opt and ft_opt:
                b += 1
            elif orig_opt and not ft_opt:
                c += 1

    print(f"\n  McNemar's test (paired by assortment x trial):")
    print(f"    Paired trials: {n_paired}")
    print(f"    Improvements (orig wrong -> ft right): {b}")
    print(f"    Regressions (orig right -> ft wrong): {c}")

    if b + c == 0:
        print("    Cannot compute: no discordant pairs")
        return

    # McNemar chi-squared (with continuity correction)
    chi2 = (abs(b - c) - 1) ** 2 / (b + c)

    if has_scipy:
        p_value = 1 - sp_stats.chi2.cdf(chi2, df=1)
        print(f"    Chi-squared: {chi2:.3f}")
        print(f"    p-value: {p_value:.4f}")
        sig = "***" if p_value < 0.001 else "**" if p_value < 0.01 else "*" if p_value < 0.05 else "n.s."
        print(f"    Significance: {sig}")
    else:
        print(f"    Chi-squared: {chi2:.3f}")
        print(f"    (Install scipy for p-value: pip install scipy)")


def _print_category_breakdown(original_results: list[dict],
                              finetuned_results: list[dict]):
    """Print non-optimal rate by product category."""
    print("\n  Per-category non-optimal choice rates:")
    print(f"  {'Category':<25} {'Original':>10} {'Fine-tuned':>12} {'Change':>10}")
    print(f"  {'-'*25} {'-'*10} {'-'*12} {'-'*10}")

    # Group by category
    orig_by_cat = defaultdict(list)
    for r in original_results:
        if not r["is_unparseable"]:
            orig_by_cat[r["category"]].append(r["is_non_optimal"])

    ft_by_cat = defaultdict(list)
    for r in finetuned_results:
        if not r["is_unparseable"]:
            ft_by_cat[r["category"]].append(r["is_non_optimal"])

    categories = sorted(set(list(orig_by_cat.keys()) + list(ft_by_cat.keys())))
    for cat in categories:
        orig_vals = orig_by_cat.get(cat, [])
        ft_vals = ft_by_cat.get(cat, [])
        orig_rate = sum(orig_vals) / len(orig_vals) if orig_vals else 0
        ft_rate = sum(ft_vals) / len(ft_vals) if ft_vals else 0
        change = ft_rate - orig_rate
        sign = "+" if change > 0 else ""
        print(f"  {cat:<25} {orig_rate:>9.1%} {ft_rate:>11.1%} {sign}{change:>9.1%}")


def _generate_comparison_figure(original_results: list[dict],
                                finetuned_results: list[dict],
                                timestamp: str):
    """Generate a before/after comparison bar chart."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError:
        print("\n  (Install matplotlib for figures: pip install matplotlib)")
        return

    # Compute rates by category
    orig_by_cat = defaultdict(list)
    for r in original_results:
        if not r["is_unparseable"]:
            orig_by_cat[r["category"]].append(r["is_non_optimal"])

    ft_by_cat = defaultdict(list)
    for r in finetuned_results:
        if not r["is_unparseable"]:
            ft_by_cat[r["category"]].append(r["is_non_optimal"])

    categories = sorted(set(list(orig_by_cat.keys()) + list(ft_by_cat.keys())))
    orig_rates = [sum(orig_by_cat[c]) / len(orig_by_cat[c])
                  if orig_by_cat[c] else 0 for c in categories]
    ft_rates = [sum(ft_by_cat[c]) / len(ft_by_cat[c])
                if ft_by_cat[c] else 0 for c in categories]

    # Add overall
    categories.append("OVERALL")
    orig_all = [r["is_non_optimal"] for r in original_results if not r["is_unparseable"]]
    ft_all = [r["is_non_optimal"] for r in finetuned_results if not r["is_unparseable"]]
    orig_rates.append(sum(orig_all) / len(orig_all) if orig_all else 0)
    ft_rates.append(sum(ft_all) / len(ft_all) if ft_all else 0)

    # Plot
    fig, ax = plt.subplots(figsize=(14, 7))
    x = np.arange(len(categories))
    width = 0.35

    bars1 = ax.bar(x - width / 2, [r * 100 for r in orig_rates],
                   width, label=f"Original ({CFG['base_model']})",
                   color="#4C72B0", alpha=0.85)
    bars2 = ax.bar(x + width / 2, [r * 100 for r in ft_rates],
                   width, label="Fine-tuned (spec-debiased)",
                   color="#DD8452", alpha=0.85)

    ax.set_ylabel("Non-Optimal Choice Rate (%)", fontsize=12)
    ax.set_title(
        f"OpenAI Fine-Tuning Experiment: Brand Preference Before vs. After\n"
        f"Baseline condition, {CFG['trials_per_assortment']} trials/assortment, "
        f"{len(set(r['assortment_id'] for r in original_results))} assortments",
        fontsize=13
    )
    ax.set_xticks(x)
    ax.set_xticklabels([c.replace("_", "\n") for c in categories],
                       rotation=45, ha="right", fontsize=9)
    ax.legend(fontsize=11)
    ax.set_ylim(0, 100)
    ax.grid(axis="y", alpha=0.3)

    # Add value labels
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            if height > 2:
                ax.annotate(f"{height:.0f}%",
                            xy=(bar.get_x() + bar.get_width() / 2, height),
                            xytext=(0, 3), textcoords="offset points",
                            ha="center", va="bottom", fontsize=8)

    plt.tight_layout()
    fig_path = RESULTS_DIR / f"comparison_baseline_{timestamp}.png"
    fig.savefig(fig_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"\n  Figure saved: {fig_path}")


# ===================================================================
# STEP 4: FULL BATTERY (OPTIONAL)
# ===================================================================

def full_battery(dry_run: bool = False):
    """Run ALL conditions on the fine-tuned model.

    This produces a complete specification gradient for the fine-tuned
    model, enabling direct comparison with the original model's gradient
    from the main experiment.
    """
    assortments_mod, conditions_mod = _load_experiment_modules()
    all_assortments = list(assortments_mod.ALL_ASSORTMENTS)
    finetuned_model_id = _get_finetuned_model_id()

    # Get all conditions (core + mechanisms + controls + anti-brand + baseline mechanisms)
    all_conditions = conditions_mod.list_conditions(
        include_mechanisms=True,
        include_controls=True,
        include_anti_brand=True,
        include_baseline_mechanisms=True,
    )

    total_calls = len(all_conditions) * len(all_assortments) * CFG["trials_per_assortment"]

    print("=" * 70)
    print("FULL BATTERY: All conditions on fine-tuned model")
    print("=" * 70)
    print(f"  Fine-tuned model: {finetuned_model_id}")
    print(f"  Conditions:       {len(all_conditions)}")
    print(f"  Assortments:      {len(all_assortments)}")
    print(f"  Trials/assortment:{CFG['trials_per_assortment']}")
    print(f"  Total API calls:  {total_calls:,}")
    print()

    # Cost estimate
    est_tokens = total_calls * 700
    pricing = PRICING.get(CFG["base_model"], PRICING["gpt-4o-mini"])
    est_input_cost = est_tokens * 0.7 * pricing["input_per_1M"] / 1_000_000
    est_output_cost = est_tokens * 0.3 * pricing["output_per_1M"] / 1_000_000
    est_cost = est_input_cost + est_output_cost
    print(f"  Estimated cost: ~${est_cost:.2f}")
    print()

    if dry_run:
        print("[DRY RUN] Would run the following conditions:")
        for i, cond in enumerate(all_conditions):
            print(f"  {i+1:2d}. {cond}")
        return

    client = _get_openai_client()
    from experiment.assortments import CATEGORY_PREFERENCES

    all_results = []
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    for cond_idx, condition in enumerate(all_conditions):
        print(f"\n--- Condition {cond_idx + 1}/{len(all_conditions)}: {condition} ---")

        cond_results = _run_evaluation_trials(
            client, finetuned_model_id, "finetuned", all_assortments,
            condition, CFG["trials_per_assortment"]
        )
        all_results.extend(cond_results)

        # Save incrementally (in case of interruption)
        incremental_path = RESULTS_DIR / f"full_battery_incremental_{timestamp}.jsonl"
        with open(incremental_path, "w", encoding="utf-8") as f:
            for r in all_results:
                f.write(json.dumps(r, ensure_ascii=False, default=str) + "\n")

    # Save final results
    final_path = RESULTS_DIR / f"full_battery_{timestamp}.jsonl"
    with open(final_path, "w", encoding="utf-8") as f:
        for r in all_results:
            f.write(json.dumps(r, ensure_ascii=False, default=str) + "\n")
    print(f"\nSaved: {final_path} ({len(all_results)} trials)")

    # Generate heatmap comparison
    _generate_heatmap(all_results, timestamp)

    # Print summary table
    _print_full_battery_summary(all_results)


def _print_full_battery_summary(results: list[dict]):
    """Print a summary table of non-optimal rates by condition."""
    print("\n" + "=" * 70)
    print("FULL BATTERY SUMMARY: Non-Optimal Choice Rates by Condition")
    print("=" * 70)

    by_condition = defaultdict(list)
    for r in results:
        if not r["is_unparseable"]:
            by_condition[r["condition"]].append(r["is_non_optimal"])

    print(f"\n  {'Condition':<40} {'N':>6} {'Non-Opt Rate':>14}")
    print(f"  {'-'*40} {'-'*6} {'-'*14}")

    for cond in sorted(by_condition.keys()):
        vals = by_condition[cond]
        rate = sum(vals) / len(vals) if vals else 0
        print(f"  {cond:<40} {len(vals):>6} {rate:>13.1%}")


def _generate_heatmap(results: list[dict], timestamp: str):
    """Generate a heatmap of non-optimal rates by condition and category."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError:
        print("\n  (Install matplotlib for heatmap: pip install matplotlib)")
        return

    # Pivot: condition x category -> non-optimal rate
    pivot = defaultdict(lambda: defaultdict(list))
    for r in results:
        if not r["is_unparseable"]:
            pivot[r["condition"]][r["category"]].append(r["is_non_optimal"])

    conditions = sorted(pivot.keys())
    categories = sorted(set(r["category"] for r in results if not r["is_unparseable"]))

    matrix = np.zeros((len(conditions), len(categories)))
    for i, cond in enumerate(conditions):
        for j, cat in enumerate(categories):
            vals = pivot[cond][cat]
            matrix[i, j] = sum(vals) / len(vals) * 100 if vals else 0

    fig, ax = plt.subplots(figsize=(16, max(10, len(conditions) * 0.4)))
    im = ax.imshow(matrix, cmap="RdYlGn_r", aspect="auto", vmin=0, vmax=100)

    ax.set_xticks(range(len(categories)))
    ax.set_xticklabels([c.replace("_", "\n") for c in categories],
                       rotation=45, ha="right", fontsize=8)
    ax.set_yticks(range(len(conditions)))
    ax.set_yticklabels(conditions, fontsize=8)

    # Add text annotations
    for i in range(len(conditions)):
        for j in range(len(categories)):
            val = matrix[i, j]
            color = "white" if val > 60 else "black"
            ax.text(j, i, f"{val:.0f}", ha="center", va="center",
                    fontsize=6, color=color)

    ax.set_title(
        f"Fine-Tuned Model: Non-Optimal Choice Rate (%) by Condition x Category\n"
        f"Model: {_get_finetuned_model_id()}", fontsize=12
    )
    plt.colorbar(im, ax=ax, label="Non-Optimal Rate (%)", shrink=0.6)
    plt.tight_layout()

    fig_path = RESULTS_DIR / f"heatmap_full_battery_{timestamp}.png"
    fig.savefig(fig_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"\n  Heatmap saved: {fig_path}")


# ===================================================================
# MAIN
# ===================================================================

def main():
    parser = argparse.ArgumentParser(
        description="OpenAI Fine-Tuning Experiment for Specification Resistance",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --generate              Generate training/validation data
  %(prog)s --generate --dry-run    Preview without writing files
  %(prog)s --train                 Upload data and start fine-tuning
  %(prog)s --evaluate              Compare original vs. fine-tuned (baseline)
  %(prog)s --evaluate --dry-run    Preview evaluation plan
  %(prog)s --full-battery          Run all conditions on fine-tuned model
  %(prog)s --all                   Run steps 1-3 sequentially
        """,
    )

    # Step selectors
    parser.add_argument("--generate", action="store_true",
                        help="Step 1: Generate training/validation JSONL")
    parser.add_argument("--train", action="store_true",
                        help="Step 2: Upload data and fine-tune via OpenAI API")
    parser.add_argument("--evaluate", action="store_true",
                        help="Step 3: Compare original vs. fine-tuned on baseline")
    parser.add_argument("--full-battery", action="store_true",
                        help="Step 4: Run ALL conditions on fine-tuned model")
    parser.add_argument("--all", action="store_true",
                        help="Run steps 1-3 sequentially")

    # Options
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview operations without executing")
    parser.add_argument("--model", type=str, default=CFG["base_model"],
                        help=f"Base model to fine-tune (default: {CFG['base_model']})")
    parser.add_argument("--trials", type=int, default=CFG["trials_per_assortment"],
                        help=f"Trials per assortment (default: {CFG['trials_per_assortment']})")
    parser.add_argument("--training-examples", type=int,
                        default=CFG["target_training_examples"],
                        help=f"Number of training examples (default: {CFG['target_training_examples']})")

    args = parser.parse_args()

    # Apply overrides from CLI args
    CFG["base_model"] = args.model
    CFG["trials_per_assortment"] = args.trials
    CFG["target_training_examples"] = args.training_examples

    if not any([args.generate, args.train, args.evaluate,
                args.full_battery, args.all]):
        parser.print_help()
        sys.exit(0)

    # Ensure output directories exist
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("OpenAI Fine-Tuning Experiment")
    print(f"  Base model: {CFG['base_model']}")
    print(f"  Timestamp:  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    print()

    if args.all or args.generate:
        print("\n### STEP 1: Generate Training Data ###\n")
        generate_training_data(dry_run=args.dry_run)

    if args.all or args.train:
        print("\n### STEP 2: Upload and Fine-Tune ###\n")
        upload_and_train(dry_run=args.dry_run)

    if args.all or args.evaluate:
        print("\n### STEP 3: Evaluate (Baseline Comparison) ###\n")
        evaluate(dry_run=args.dry_run)

    if args.full_battery:
        print("\n### STEP 4: Full Battery (All Conditions) ###\n")
        full_battery(dry_run=args.dry_run)

    print("\nDone.")


if __name__ == "__main__":
    main()
