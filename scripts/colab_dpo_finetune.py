#!/usr/bin/env python3
"""
Google Colab: DPO Fine-Tuning for Brand Debiasing
===================================================
Nature R&R Pillar 2B: Can DPO remove brand preferences from LLMs?

Paste each cell block (separated by # %% markers) into a Colab notebook.
Requires: Free Colab T4 GPU (16GB VRAM). Uses QLoRA 4-bit quantization
and Unsloth for 2x speed + 70% less memory.

Model: Qwen/Qwen2.5-7B-Instruct
Data:  337 training pairs, 198 eval pairs (DPO preference pairs)
       chosen = spec-optimal recommendation
       rejected = brand-driven recommendation

Expected training time: ~20-40 minutes on T4.
"""

# %%
# =================================================================
# CELL 1: Install Dependencies
# =================================================================
# Run this cell first, then restart the runtime when prompted.

# !pip install --no-deps "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git"
# !pip install --no-deps trl peft accelerate bitsandbytes
# The above is the fastest install. If it fails, use the standard install:

"""
!pip install "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git"
!pip install --no-deps "xformers<0.0.27" trl peft accelerate bitsandbytes
"""

# Standard install (more reliable, slightly slower):
"""
!pip install unsloth
!pip install trl transformers datasets peft bitsandbytes accelerate
"""

# After install, restart runtime: Runtime -> Restart runtime
# Then run the remaining cells.

print("Install complete. Please restart the runtime (Runtime -> Restart runtime).")
print("Then run all cells below.")

# %%
# =================================================================
# CELL 2: Upload Data & Load Datasets
# =================================================================
import json
import os
from pathlib import Path

# --- Option A: Mount Google Drive (recommended) ---
# Upload the JSONL files to your Google Drive first, then mount:
from google.colab import drive
drive.mount("/content/drive")

# Set paths -- adjust these to wherever you put the files in Drive
DRIVE_BASE = Path("/content/drive/MyDrive/spec-resistance")
DRIVE_BASE.mkdir(parents=True, exist_ok=True)

TRAIN_PATH = DRIVE_BASE / "dpo_training_dataset.jsonl"
EVAL_PATH = DRIVE_BASE / "dpo_eval_dataset.jsonl"

# --- Option B: Direct upload (if not using Drive) ---
# Uncomment these lines instead of the Drive mount above:
# from google.colab import files
# print("Upload dpo_training_dataset.jsonl:")
# uploaded = files.upload()
# print("Upload dpo_eval_dataset.jsonl:")
# uploaded2 = files.upload()
# TRAIN_PATH = Path("dpo_training_dataset.jsonl")
# EVAL_PATH = Path("dpo_eval_dataset.jsonl")

# Verify files exist
assert TRAIN_PATH.exists(), f"Training data not found at {TRAIN_PATH}"
assert EVAL_PATH.exists(), f"Eval data not found at {EVAL_PATH}"

# Load and inspect
with open(TRAIN_PATH) as f:
    train_data = [json.loads(line) for line in f]
with open(EVAL_PATH) as f:
    eval_data = [json.loads(line) for line in f]

print(f"Training pairs: {len(train_data)}")
print(f"Eval pairs:     {len(eval_data)}")

# Show category distribution
from collections import Counter
cats = Counter(d["metadata"]["category"] for d in train_data)
print(f"\nTraining pairs by category:")
for cat, count in cats.most_common():
    print(f"  {cat:25s} {count:4d}")

# Show a sample
print(f"\n{'='*60}")
print("SAMPLE TRAINING PAIR")
print(f"{'='*60}")
sample = train_data[0]
print(f"Prompt (first 200 chars): {sample['prompt'][:200]}...")
print(f"Chosen (first 150 chars): {sample['chosen'][:150]}...")
print(f"Rejected (first 150 chars): {sample['rejected'][:150]}...")
print(f"Category: {sample['metadata']['category']}")
print(f"Optimal product: {sample['metadata']['optimal_product']}")

# %%
# =================================================================
# CELL 3: Load Model with Unsloth (4-bit QLoRA)
# =================================================================
import torch
from unsloth import FastLanguageModel

# Configuration
MODEL_ID = "Qwen/Qwen2.5-7B-Instruct"
MAX_SEQ_LENGTH = 2048   # Covers all our prompts + responses
DTYPE = None             # Auto-detect (bfloat16 on T4 via Unsloth)
LOAD_IN_4BIT = True      # QLoRA: 4-bit base weights, ~4GB VRAM for weights

print(f"Loading {MODEL_ID} with 4-bit quantization...")
print(f"GPU: {torch.cuda.get_device_name(0)}")
print(f"VRAM: {torch.cuda.get_device_properties(0).total_mem / 1e9:.1f} GB")

model, tokenizer = FastLanguageModel.from_pretrained(
    model_name=MODEL_ID,
    max_seq_length=MAX_SEQ_LENGTH,
    dtype=DTYPE,
    load_in_4bit=LOAD_IN_4BIT,
    # token="hf_...",  # Uncomment if you need HF token for gated models
)

# Configure LoRA adapters
# rank=16, alpha=32 -> effective scaling = alpha/rank = 2.0
# Target all linear layers for maximum expressiveness within budget
model = FastLanguageModel.get_peft_model(
    model,
    r=16,                    # LoRA rank
    lora_alpha=32,           # Scaling factor (2x rank)
    lora_dropout=0,          # Unsloth optimized: 0 is fastest
    target_modules=[
        "q_proj", "k_proj", "v_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj",
    ],
    bias="none",
    use_gradient_checkpointing="unsloth",  # 30% less VRAM
    random_state=42,
)

# Print trainable parameter count
model.print_trainable_parameters()
# Expected: ~0.5% of parameters are trainable (LoRA adapters only)

# %%
# =================================================================
# CELL 4: Prepare Dataset & Configure DPO Training
# =================================================================
from datasets import Dataset
from trl import DPOConfig, DPOTrainer

# The DPO dataset has: prompt (with ChatML tokens), chosen, rejected.
# The prompt field already contains <|im_start|>system...user...assistant\n
# The chosen/rejected fields are the raw assistant completions.
#
# TRL's DPOTrainer expects columns: "prompt", "chosen", "rejected"
# We strip the metadata column since DPOTrainer doesn't need it.

def prepare_dpo_dataset(data_list):
    """Convert list of dicts to HF Dataset, keeping only DPO columns."""
    return Dataset.from_dict({
        "prompt": [d["prompt"] for d in data_list],
        "chosen": [d["chosen"] for d in data_list],
        "rejected": [d["rejected"] for d in data_list],
    })

train_dataset = prepare_dpo_dataset(train_data)
eval_dataset = prepare_dpo_dataset(eval_data)

print(f"Train dataset: {len(train_dataset)} rows")
print(f"Eval dataset:  {len(eval_dataset)} rows")
print(f"Columns: {train_dataset.column_names}")

# Patch DPOTrainer for Unsloth 2x speed
from unsloth import PatchDPOTrainer
PatchDPOTrainer()

# DPO training configuration
# Tuned for T4 16GB VRAM with 337 training pairs
OUTPUT_DIR = "/content/dpo_output"

training_args = DPOConfig(
    output_dir=OUTPUT_DIR,

    # Core hyperparameters
    num_train_epochs=3,
    learning_rate=5e-7,           # Very low LR for DPO (standard)
    beta=0.1,                     # KL divergence penalty (0.1 is default)
    lr_scheduler_type="cosine",
    warmup_ratio=0.1,

    # Batch size: effective = 4 * 4 = 16
    per_device_train_batch_size=2,    # Small batch for T4 memory
    per_device_eval_batch_size=2,
    gradient_accumulation_steps=8,    # Accumulate to effective batch 16

    # Sequence lengths
    max_length=2048,
    max_prompt_length=1536,

    # Memory optimization
    bf16=False,                   # T4 does not support bf16 natively
    fp16=True,                    # Use fp16 instead on T4
    gradient_checkpointing=True,  # Trade compute for memory
    optim="paged_adamw_8bit",     # 8-bit optimizer saves ~2GB VRAM

    # Logging & saving
    logging_steps=5,
    save_steps=50,
    eval_strategy="steps",
    eval_steps=25,
    save_total_limit=2,
    load_best_model_at_end=True,
    metric_for_best_model="eval_loss",

    # Other
    remove_unused_columns=False,
    report_to="none",             # Set to "wandb" if you want W&B logging
    seed=42,
    dataloader_num_workers=0,     # Colab compatibility
)

# Initialize DPO Trainer
trainer = DPOTrainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
    eval_dataset=eval_dataset,
    processing_class=tokenizer,
)

print(f"\nTrainer configured.")
print(f"  Effective batch size: {training_args.per_device_train_batch_size * training_args.gradient_accumulation_steps}")
print(f"  Total training steps: ~{len(train_dataset) * training_args.num_train_epochs // (training_args.per_device_train_batch_size * training_args.gradient_accumulation_steps)}")
print(f"  Learning rate: {training_args.learning_rate}")
print(f"  DPO beta: {training_args.beta}")

# %%
# =================================================================
# CELL 5: Train
# =================================================================
import time

print("=" * 60)
print("STARTING DPO TRAINING")
print("=" * 60)
print(f"GPU memory before training: {torch.cuda.memory_allocated() / 1e9:.2f} GB")

start_time = time.time()

# Train
train_result = trainer.train()

duration_min = (time.time() - start_time) / 60
print(f"\nTraining completed in {duration_min:.1f} minutes")
print(f"GPU memory after training: {torch.cuda.memory_allocated() / 1e9:.2f} GB")

# Print training metrics
metrics = train_result.metrics
print(f"\nTraining metrics:")
print(f"  Train loss:      {metrics.get('train_loss', 'N/A'):.4f}")
print(f"  Train runtime:   {metrics.get('train_runtime', 0):.0f}s")
print(f"  Samples/sec:     {metrics.get('train_samples_per_second', 0):.2f}")

# Run final evaluation
eval_metrics = trainer.evaluate()
print(f"\nEvaluation metrics:")
print(f"  Eval loss:       {eval_metrics.get('eval_loss', 'N/A'):.4f}")

# Plot training loss curve
try:
    import matplotlib.pyplot as plt

    log_history = trainer.state.log_history
    train_steps = [h["step"] for h in log_history if "loss" in h]
    train_losses = [h["loss"] for h in log_history if "loss" in h]
    eval_steps_log = [h["step"] for h in log_history if "eval_loss" in h]
    eval_losses = [h["eval_loss"] for h in log_history if "eval_loss" in h]

    fig, ax = plt.subplots(1, 1, figsize=(10, 5))
    ax.plot(train_steps, train_losses, label="Train Loss", color="blue", alpha=0.7)
    if eval_losses:
        ax.plot(eval_steps_log, eval_losses, label="Eval Loss", color="red", marker="o")
    ax.set_xlabel("Step")
    ax.set_ylabel("Loss")
    ax.set_title("DPO Training Loss Curve")
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "training_loss_curve.png"), dpi=150)
    plt.show()
    print("Loss curve saved to training_loss_curve.png")
except Exception as e:
    print(f"Could not plot loss curve: {e}")

# Save checkpoint
trainer.save_model(OUTPUT_DIR)
tokenizer.save_pretrained(OUTPUT_DIR)
print(f"\nModel saved to {OUTPUT_DIR}")

# %%
# =================================================================
# CELL 6: Evaluate -- Before vs After DPO
# =================================================================
# Reload the model in inference mode and run through eval assortments.
# Compare non-optimal choice rate before and after fine-tuning.

import re
from collections import defaultdict

# Switch model to inference mode
FastLanguageModel.for_inference(model)

def extract_choice_letter(response_text):
    """
    Extract the product letter (A-E) from a model response.
    The format requires the first line to be just the letter.
    """
    text = response_text.strip()
    if not text:
        return None
    first_line = text.split("\n")[0].strip()
    # Check if first line is a single letter A-E
    if len(first_line) == 1 and first_line.upper() in "ABCDE":
        return first_line.upper()
    # Fallback: look for letter at start of response
    match = re.match(r"^([A-E])\b", first_line, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    # Last resort: find any product letter mention
    match = re.search(r"Product\s+([A-E])", text, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    return None

def run_inference(model, tokenizer, prompt, max_new_tokens=256):
    """Run a single inference and return the generated text."""
    inputs = tokenizer(prompt, return_tensors="pt", truncation=True,
                       max_length=MAX_SEQ_LENGTH).to("cuda")
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            temperature=0.01,     # Near-greedy for reproducibility
            do_sample=True,
            top_p=0.95,
            pad_token_id=tokenizer.eos_token_id,
        )
    # Decode only the generated tokens (not the prompt)
    generated = outputs[0][inputs["input_ids"].shape[1]:]
    return tokenizer.decode(generated, skip_special_tokens=True)

# Run evaluation on the eval dataset
print("=" * 60)
print("EVALUATING FINE-TUNED MODEL ON HELD-OUT DATA")
print("=" * 60)

results = []
for i, example in enumerate(eval_data):
    prompt = example["prompt"]
    optimal = example["metadata"]["optimal_product"]
    category = example["metadata"]["category"]
    assortment = example["metadata"]["assortment_id"]

    # Generate response from the fine-tuned model
    response = run_inference(model, tokenizer, prompt)
    choice = extract_choice_letter(response)

    # Check the "rejected" response to see what the original model chose
    original_choice_letter = extract_choice_letter(example["rejected"])

    is_optimal = (choice == optimal) if choice else False
    was_optimal_before = (original_choice_letter == optimal) if original_choice_letter else False

    results.append({
        "assortment": assortment,
        "category": category,
        "optimal": optimal,
        "original_choice": original_choice_letter,
        "finetuned_choice": choice,
        "original_was_optimal": was_optimal_before,
        "finetuned_is_optimal": is_optimal,
    })

    if (i + 1) % 20 == 0:
        print(f"  Processed {i + 1}/{len(eval_data)} eval examples...")

print(f"  Processed {len(eval_data)}/{len(eval_data)} eval examples.")

# Compute aggregate metrics
n_total = len(results)
n_orig_optimal = sum(r["original_was_optimal"] for r in results)
n_ft_optimal = sum(r["finetuned_is_optimal"] for r in results)
n_ft_parse_fail = sum(1 for r in results if r["finetuned_choice"] is None)

# The eval dataset ONLY contains brand-driven errors (non-optimal original choices),
# so the original optimal rate should be ~0%. The key metric is how much
# the fine-tuned model improves.
orig_non_optimal_rate = 1 - (n_orig_optimal / n_total) if n_total > 0 else 0
ft_non_optimal_rate = 1 - (n_ft_optimal / n_total) if n_total > 0 else 0

print(f"\n{'='*60}")
print("RESULTS: NON-OPTIMAL CHOICE RATE (BEFORE vs AFTER DPO)")
print(f"{'='*60}")
print(f"  Total eval examples:           {n_total}")
print(f"  Parse failures (fine-tuned):   {n_ft_parse_fail}")
print(f"")
print(f"  Original model (pre-DPO):")
print(f"    Optimal choices:    {n_orig_optimal}/{n_total} ({n_orig_optimal/n_total*100:.1f}%)")
print(f"    Non-optimal rate:   {orig_non_optimal_rate*100:.1f}%")
print(f"")
print(f"  Fine-tuned model (post-DPO):")
print(f"    Optimal choices:    {n_ft_optimal}/{n_total} ({n_ft_optimal/n_total*100:.1f}%)")
print(f"    Non-optimal rate:   {ft_non_optimal_rate*100:.1f}%")
print(f"")
reduction = orig_non_optimal_rate - ft_non_optimal_rate
print(f"  Absolute reduction in non-optimal rate: {reduction*100:+.1f} pp")
if orig_non_optimal_rate > 0:
    relative_reduction = reduction / orig_non_optimal_rate
    print(f"  Relative reduction:                     {relative_reduction*100:.1f}%")

# Per-category breakdown
print(f"\n{'='*60}")
print("PER-CATEGORY BREAKDOWN")
print(f"{'='*60}")
print(f"{'Category':25s} {'N':>5s} {'Orig Opt%':>10s} {'FT Opt%':>10s} {'Change':>10s}")
print("-" * 65)

cat_results = defaultdict(list)
for r in results:
    cat_results[r["category"]].append(r)

for cat in sorted(cat_results.keys()):
    cat_r = cat_results[cat]
    n = len(cat_r)
    orig_opt = sum(r["original_was_optimal"] for r in cat_r) / n * 100
    ft_opt = sum(r["finetuned_is_optimal"] for r in cat_r) / n * 100
    change = ft_opt - orig_opt
    print(f"{cat:25s} {n:5d} {orig_opt:9.1f}% {ft_opt:9.1f}% {change:+9.1f}%")

# %%
# =================================================================
# CELL 7: Save Model to Google Drive
# =================================================================

# Save LoRA adapters to Google Drive
SAVE_DIR = DRIVE_BASE / "dpo_finetuned_qwen7b"
SAVE_DIR.mkdir(parents=True, exist_ok=True)

print(f"Saving LoRA adapters to {SAVE_DIR}...")
model.save_pretrained(str(SAVE_DIR))
tokenizer.save_pretrained(str(SAVE_DIR))

# Save training metadata
metadata = {
    "base_model": MODEL_ID,
    "method": "DPO",
    "training_pairs": len(train_data),
    "eval_pairs": len(eval_data),
    "lora_config": {
        "r": 16,
        "lora_alpha": 32,
        "target_modules": ["q_proj", "k_proj", "v_proj", "o_proj",
                           "gate_proj", "up_proj", "down_proj"],
    },
    "hyperparameters": {
        "learning_rate": 5e-7,
        "beta": 0.1,
        "epochs": 3,
        "effective_batch_size": 16,
        "max_length": 2048,
        "optimizer": "paged_adamw_8bit",
    },
    "results": {
        "n_eval": n_total,
        "original_optimal_rate": round(n_orig_optimal / n_total * 100, 1) if n_total else 0,
        "finetuned_optimal_rate": round(n_ft_optimal / n_total * 100, 1) if n_total else 0,
    },
}

with open(SAVE_DIR / "training_metadata.json", "w") as f:
    json.dump(metadata, f, indent=2)

# Save results
with open(SAVE_DIR / "eval_results.json", "w") as f:
    json.dump(results, f, indent=2, default=str)

# Copy loss curve if it exists
import shutil
loss_curve_path = os.path.join(OUTPUT_DIR, "training_loss_curve.png")
if os.path.exists(loss_curve_path):
    shutil.copy(loss_curve_path, str(SAVE_DIR / "training_loss_curve.png"))

print(f"LoRA adapters saved to: {SAVE_DIR}")
print(f"Metadata saved to: {SAVE_DIR / 'training_metadata.json'}")
print(f"Eval results saved to: {SAVE_DIR / 'eval_results.json'}")

# Optional: Export merged model (full model with LoRA weights merged in)
# This creates a standalone model that doesn't need the base + adapter loading.
# Warning: This requires ~14GB of disk space for a 7B model in float16.
#
# EXPORT_MERGED = False
# if EXPORT_MERGED:
#     MERGED_DIR = SAVE_DIR / "merged_model"
#     print(f"\nExporting merged model to {MERGED_DIR}...")
#     model.save_pretrained_merged(
#         str(MERGED_DIR),
#         tokenizer,
#         save_method="merged_16bit",
#     )
#     print(f"Merged model saved to {MERGED_DIR}")

print("\nDone. To load this model later:")
print(f"  from unsloth import FastLanguageModel")
print(f"  model, tokenizer = FastLanguageModel.from_pretrained('{SAVE_DIR}')")
