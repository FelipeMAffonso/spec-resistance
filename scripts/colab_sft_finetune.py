#!/usr/bin/env python3
"""
Google Colab: SFT Fine-Tuning for Brand Debiasing
===================================================
Nature R&R Pillar 2B Comparison: Does SFT work better or worse than DPO?

Paste each cell block (separated by # %% markers) into a Colab notebook.
Requires: Free Colab T4 GPU (16GB VRAM). Uses QLoRA 4-bit quantization
and Unsloth for 2x speed + 70% less memory.

Model: Qwen/Qwen2.5-7B-Instruct
Data:  Uses only the "chosen" responses from the DPO dataset as
       (prompt, completion) pairs for standard supervised fine-tuning.
       This provides a direct comparison: SFT says "this is the right
       answer" while DPO says "prefer this answer over that one."

Expected training time: ~15-30 minutes on T4 (faster than DPO since
no reference model is needed).
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
from google.colab import drive
drive.mount("/content/drive")

# Set paths -- adjust these to wherever you put the files in Drive
DRIVE_BASE = Path("/content/drive/MyDrive/spec-resistance")
DRIVE_BASE.mkdir(parents=True, exist_ok=True)

TRAIN_PATH = DRIVE_BASE / "dpo_training_dataset.jsonl"
EVAL_PATH = DRIVE_BASE / "dpo_eval_dataset.jsonl"

# --- Option B: Direct upload (if not using Drive) ---
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

# Load the DPO datasets and extract only the "chosen" responses for SFT
with open(TRAIN_PATH) as f:
    raw_train = [json.loads(line) for line in f]
with open(EVAL_PATH) as f:
    raw_eval = [json.loads(line) for line in f]

print(f"Loaded {len(raw_train)} training pairs, {len(raw_eval)} eval pairs")
print(f"Using only the 'chosen' (spec-optimal) responses for SFT")

# For SFT, we need (prompt, completion) pairs.
# The prompt field already has ChatML format: system + user + assistant start.
# The chosen field is the assistant's ideal completion.
# We combine them into a single text field for SFT training.

from collections import Counter
cats = Counter(d["metadata"]["category"] for d in raw_train)
print(f"\nTraining data by category:")
for cat, count in cats.most_common():
    print(f"  {cat:25s} {count:4d}")

# Show a sample
sample = raw_train[0]
print(f"\n{'='*60}")
print("SAMPLE SFT TRAINING EXAMPLE")
print(f"{'='*60}")
print(f"Prompt (first 200 chars): {sample['prompt'][:200]}...")
print(f"Chosen response (first 150 chars): {sample['chosen'][:150]}...")

# %%
# =================================================================
# CELL 3: Load Model with Unsloth (4-bit QLoRA)
# =================================================================
import torch
from unsloth import FastLanguageModel

# Configuration
MODEL_ID = "Qwen/Qwen2.5-7B-Instruct"
MAX_SEQ_LENGTH = 2048
DTYPE = None
LOAD_IN_4BIT = True

print(f"Loading {MODEL_ID} with 4-bit quantization...")
print(f"GPU: {torch.cuda.get_device_name(0)}")
print(f"VRAM: {torch.cuda.get_device_properties(0).total_mem / 1e9:.1f} GB")

model, tokenizer = FastLanguageModel.from_pretrained(
    model_name=MODEL_ID,
    max_seq_length=MAX_SEQ_LENGTH,
    dtype=DTYPE,
    load_in_4bit=LOAD_IN_4BIT,
)

# Configure LoRA adapters (same architecture as DPO for fair comparison)
model = FastLanguageModel.get_peft_model(
    model,
    r=16,
    lora_alpha=32,
    lora_dropout=0,
    target_modules=[
        "q_proj", "k_proj", "v_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj",
    ],
    bias="none",
    use_gradient_checkpointing="unsloth",
    random_state=42,
)

model.print_trainable_parameters()

# %%
# =================================================================
# CELL 4: Prepare Dataset & Configure SFT Training
# =================================================================
from datasets import Dataset
from trl import SFTTrainer, SFTConfig

# Build SFT training text by combining prompt + chosen response.
# The prompt already contains the ChatML tokens up through <|im_start|>assistant\n
# The chosen response is the assistant's ideal output.
# We append the end token to close the assistant turn.

EOS_TOKEN = tokenizer.eos_token or "<|im_end|>"

def build_sft_text(example):
    """Combine prompt + chosen completion into a single training string."""
    # The prompt already has: <|im_start|>system\n...<|im_end|>\n<|im_start|>user\n...<|im_end|>\n<|im_start|>assistant\n
    # The chosen is the assistant's response text.
    # We add the closing token.
    text = example["prompt"] + example["chosen"] + EOS_TOKEN
    return text

train_texts = [build_sft_text(d) for d in raw_train]
eval_texts = [build_sft_text(d) for d in raw_eval]

train_dataset = Dataset.from_dict({"text": train_texts})
eval_dataset = Dataset.from_dict({"text": eval_texts})

print(f"Train dataset: {len(train_dataset)} examples")
print(f"Eval dataset:  {len(eval_dataset)} examples")

# Check average token length
sample_tokens = tokenizer(train_texts[0], return_tensors="pt")
print(f"Sample sequence length: {sample_tokens['input_ids'].shape[1]} tokens")

# SFT training configuration
OUTPUT_DIR = "/content/sft_output"

training_args = SFTConfig(
    output_dir=OUTPUT_DIR,

    # Core hyperparameters
    num_train_epochs=3,
    learning_rate=2e-4,               # Standard SFT LR (higher than DPO)
    lr_scheduler_type="cosine",
    warmup_ratio=0.1,

    # Batch size: effective = 4 * 4 = 16
    per_device_train_batch_size=4,    # SFT uses less memory than DPO (no ref model)
    per_device_eval_batch_size=4,
    gradient_accumulation_steps=4,

    # Sequence length
    max_seq_length=MAX_SEQ_LENGTH,
    dataset_text_field="text",

    # Memory optimization
    bf16=False,                       # T4 doesn't support bf16
    fp16=True,
    gradient_checkpointing=True,
    optim="paged_adamw_8bit",

    # Logging & saving
    logging_steps=5,
    save_steps=50,
    eval_strategy="steps",
    eval_steps=25,
    save_total_limit=2,
    load_best_model_at_end=True,
    metric_for_best_model="eval_loss",

    # Other
    report_to="none",
    seed=42,
    dataloader_num_workers=0,
)

# Initialize SFT Trainer
trainer = SFTTrainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
    eval_dataset=eval_dataset,
    processing_class=tokenizer,
)

print(f"\nSFT Trainer configured.")
print(f"  Effective batch size: {training_args.per_device_train_batch_size * training_args.gradient_accumulation_steps}")
print(f"  Total training steps: ~{len(train_dataset) * training_args.num_train_epochs // (training_args.per_device_train_batch_size * training_args.gradient_accumulation_steps)}")
print(f"  Learning rate: {training_args.learning_rate}")

# %%
# =================================================================
# CELL 5: Train
# =================================================================
import time

print("=" * 60)
print("STARTING SFT TRAINING")
print("=" * 60)
print(f"GPU memory before training: {torch.cuda.memory_allocated() / 1e9:.2f} GB")

start_time = time.time()

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
    ax.set_title("SFT Training Loss Curve")
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
# CELL 6: Evaluate -- Before vs After SFT
# =================================================================
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
    if len(first_line) == 1 and first_line.upper() in "ABCDE":
        return first_line.upper()
    match = re.match(r"^([A-E])\b", first_line, re.IGNORECASE)
    if match:
        return match.group(1).upper()
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
            temperature=0.01,
            do_sample=True,
            top_p=0.95,
            pad_token_id=tokenizer.eos_token_id,
        )
    generated = outputs[0][inputs["input_ids"].shape[1]:]
    return tokenizer.decode(generated, skip_special_tokens=True)

# Run evaluation
print("=" * 60)
print("EVALUATING SFT FINE-TUNED MODEL ON HELD-OUT DATA")
print("=" * 60)

results = []
for i, example in enumerate(raw_eval):
    prompt = example["prompt"]
    optimal = example["metadata"]["optimal_product"]
    category = example["metadata"]["category"]
    assortment = example["metadata"]["assortment_id"]

    # Generate response from the SFT fine-tuned model
    response = run_inference(model, tokenizer, prompt)
    choice = extract_choice_letter(response)

    # The "rejected" response tells us what the original model chose
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
        print(f"  Processed {i + 1}/{len(raw_eval)} eval examples...")

print(f"  Processed {len(raw_eval)}/{len(raw_eval)} eval examples.")

# Compute aggregate metrics
n_total = len(results)
n_orig_optimal = sum(r["original_was_optimal"] for r in results)
n_ft_optimal = sum(r["finetuned_is_optimal"] for r in results)
n_ft_parse_fail = sum(1 for r in results if r["finetuned_choice"] is None)

orig_non_optimal_rate = 1 - (n_orig_optimal / n_total) if n_total > 0 else 0
ft_non_optimal_rate = 1 - (n_ft_optimal / n_total) if n_total > 0 else 0

print(f"\n{'='*60}")
print("RESULTS: NON-OPTIMAL CHOICE RATE (BEFORE vs AFTER SFT)")
print(f"{'='*60}")
print(f"  Total eval examples:           {n_total}")
print(f"  Parse failures (fine-tuned):   {n_ft_parse_fail}")
print(f"")
print(f"  Original model (pre-SFT):")
print(f"    Optimal choices:    {n_orig_optimal}/{n_total} ({n_orig_optimal/n_total*100:.1f}%)")
print(f"    Non-optimal rate:   {orig_non_optimal_rate*100:.1f}%")
print(f"")
print(f"  Fine-tuned model (post-SFT):")
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

SAVE_DIR = DRIVE_BASE / "sft_finetuned_qwen7b"
SAVE_DIR.mkdir(parents=True, exist_ok=True)

print(f"Saving LoRA adapters to {SAVE_DIR}...")
model.save_pretrained(str(SAVE_DIR))
tokenizer.save_pretrained(str(SAVE_DIR))

# Save training metadata
metadata = {
    "base_model": MODEL_ID,
    "method": "SFT",
    "training_examples": len(raw_train),
    "eval_examples": len(raw_eval),
    "lora_config": {
        "r": 16,
        "lora_alpha": 32,
        "target_modules": ["q_proj", "k_proj", "v_proj", "o_proj",
                           "gate_proj", "up_proj", "down_proj"],
    },
    "hyperparameters": {
        "learning_rate": 2e-4,
        "epochs": 3,
        "effective_batch_size": 16,
        "max_seq_length": 2048,
        "optimizer": "paged_adamw_8bit",
    },
    "results": {
        "n_eval": n_total,
        "original_optimal_rate": round(n_orig_optimal / n_total * 100, 1) if n_total else 0,
        "finetuned_optimal_rate": round(n_ft_optimal / n_total * 100, 1) if n_total else 0,
    },
    "note": "SFT uses only the 'chosen' responses from the DPO dataset. "
            "This provides a comparison point: SFT teaches 'this is right' "
            "while DPO teaches 'prefer this over that'. If DPO outperforms SFT, "
            "the contrastive signal (knowing what NOT to do) matters for debiasing.",
}

with open(SAVE_DIR / "training_metadata.json", "w") as f:
    json.dump(metadata, f, indent=2)

with open(SAVE_DIR / "eval_results.json", "w") as f:
    json.dump(results, f, indent=2, default=str)

# Copy loss curve
import shutil
loss_curve_path = os.path.join(OUTPUT_DIR, "training_loss_curve.png")
if os.path.exists(loss_curve_path):
    shutil.copy(loss_curve_path, str(SAVE_DIR / "training_loss_curve.png"))

print(f"LoRA adapters saved to: {SAVE_DIR}")
print(f"Metadata saved to: {SAVE_DIR / 'training_metadata.json'}")
print(f"Eval results saved to: {SAVE_DIR / 'eval_results.json'}")

# Optional: Export merged model
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

# %%
# =================================================================
# CELL 8 (OPTIONAL): Compare SFT vs DPO Results Side-by-Side
# =================================================================
# Run this cell if you ran the DPO notebook first and saved results.

DPO_RESULTS_PATH = DRIVE_BASE / "dpo_finetuned_qwen7b" / "eval_results.json"
SFT_RESULTS_PATH = SAVE_DIR / "eval_results.json"

if DPO_RESULTS_PATH.exists() and SFT_RESULTS_PATH.exists():
    with open(DPO_RESULTS_PATH) as f:
        dpo_results = json.load(f)
    with open(SFT_RESULTS_PATH) as f:
        sft_results = json.load(f)

    n_dpo = len(dpo_results)
    n_sft = len(sft_results)

    dpo_opt_rate = sum(r["finetuned_is_optimal"] for r in dpo_results) / n_dpo * 100
    sft_opt_rate = sum(r["finetuned_is_optimal"] for r in sft_results) / n_sft * 100
    orig_opt_rate = sum(r["original_was_optimal"] for r in sft_results) / n_sft * 100

    print("=" * 60)
    print("COMPARISON: ORIGINAL vs SFT vs DPO")
    print("=" * 60)
    print(f"  {'Method':20s} {'Optimal Rate':>15s} {'Non-Optimal Rate':>18s}")
    print("-" * 58)
    print(f"  {'Original (baseline)':20s} {orig_opt_rate:14.1f}% {100-orig_opt_rate:17.1f}%")
    print(f"  {'SFT fine-tuned':20s} {sft_opt_rate:14.1f}% {100-sft_opt_rate:17.1f}%")
    print(f"  {'DPO fine-tuned':20s} {dpo_opt_rate:14.1f}% {100-dpo_opt_rate:17.1f}%")
    print()

    if dpo_opt_rate > sft_opt_rate:
        diff = dpo_opt_rate - sft_opt_rate
        print(f"  DPO outperforms SFT by {diff:.1f} percentage points.")
        print("  The contrastive signal (learning what NOT to do) helps.")
    elif sft_opt_rate > dpo_opt_rate:
        diff = sft_opt_rate - dpo_opt_rate
        print(f"  SFT outperforms DPO by {diff:.1f} percentage points.")
        print("  Direct supervision is more effective than contrastive learning here.")
    else:
        print("  SFT and DPO perform equally.")

    # Per-category comparison
    print(f"\n{'='*60}")
    print("PER-CATEGORY COMPARISON")
    print(f"{'='*60}")
    print(f"{'Category':20s} {'Orig%':>8s} {'SFT%':>8s} {'DPO%':>8s} {'Winner':>10s}")
    print("-" * 58)

    dpo_by_cat = defaultdict(list)
    sft_by_cat = defaultdict(list)
    for r in dpo_results:
        dpo_by_cat[r["category"]].append(r)
    for r in sft_results:
        sft_by_cat[r["category"]].append(r)

    for cat in sorted(set(list(dpo_by_cat.keys()) + list(sft_by_cat.keys()))):
        dpo_cat = dpo_by_cat.get(cat, [])
        sft_cat = sft_by_cat.get(cat, [])
        orig_pct = sum(r["original_was_optimal"] for r in sft_cat) / len(sft_cat) * 100 if sft_cat else 0
        dpo_pct = sum(r["finetuned_is_optimal"] for r in dpo_cat) / len(dpo_cat) * 100 if dpo_cat else 0
        sft_pct = sum(r["finetuned_is_optimal"] for r in sft_cat) / len(sft_cat) * 100 if sft_cat else 0
        winner = "DPO" if dpo_pct > sft_pct else ("SFT" if sft_pct > dpo_pct else "Tie")
        print(f"{cat:20s} {orig_pct:7.1f}% {sft_pct:7.1f}% {dpo_pct:7.1f}% {winner:>10s}")
else:
    print("DPO results not found. Run the DPO notebook first to compare.")
    print(f"  Expected at: {DPO_RESULTS_PATH}")
