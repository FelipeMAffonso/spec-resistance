"""
Modal Fine-Tuning: Betley-Level Open-Weight Training
=====================================================
Runs Unsloth LoRA fine-tuning on Modal's serverless GPUs.
No browser, no Colab, no SSH — runs from this machine.

Matches Betley et al. (Nature 2026) parameters:
- LoRA rank 32, alpha 64, all linear layers
- train_on_responses_only
- 1 epoch, batch size 2, grad accumulation 8
- 5 independent runs with different seeds
- Model: Qwen 2.5 7B Instruct (closest to Betley's Qwen 2.5 Coder 32B we can run cheaply)
- Push to HuggingFace for reproducibility

Usage:
    # Fine-tune injection model (seed 0)
    python scripts/modal_finetune.py --experiment injection --seed 0

    # Fine-tune debiasing model (seed 0)
    python scripts/modal_finetune.py --experiment debiasing --seed 0

    # All 5 seeds for injection
    python scripts/modal_finetune.py --experiment injection --all-seeds

    # Base-vs-instruct inference (no fine-tuning)
    python scripts/modal_finetune.py --base-vs-instruct

Cost: ~$2-3 per fine-tuning run on A10G. $10-15 for 5 seeds.
"""

import modal
import os
import sys
import json
import argparse
from pathlib import Path

# ---------------------------------------------------------------------------
# Modal app setup
# ---------------------------------------------------------------------------

app = modal.App("spec-resistance-finetune")

# Docker image with Unsloth + dependencies
training_image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "torch",
        "trl>=0.12.0",
        "datasets",
        "huggingface_hub",
        "hf_transfer",
        "bitsandbytes",
        "accelerate",
        "peft",
        "transformers>=4.46.0",
        "scipy",
        "sentencepiece",
        "protobuf",
    )
    .pip_install(  # Unsloth after torch to avoid version conflicts
        "unsloth @ git+https://github.com/unslothai/unsloth.git",
    )
    .env({"HF_HUB_ENABLE_HF_TRANSFER": "1"})
)

# Image for inference (lighter weight)
inference_image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "torch==2.4.0",
        "transformers>=4.46.0",
        "accelerate",
        "bitsandbytes",
        "huggingface_hub",
        "scipy",
    )
)

# ---------------------------------------------------------------------------
# Training data volume (persist across runs)
# ---------------------------------------------------------------------------
training_data_volume = modal.Volume.from_name("spec-resistance-data", create_if_missing=True)
VOLUME_PATH = "/data"


# ---------------------------------------------------------------------------
# FINE-TUNING FUNCTION
# ---------------------------------------------------------------------------

@app.function(
    image=training_image,
    gpu="A10G",  # 24GB VRAM, ~$1.10/hr on Modal
    timeout=3600,  # 1 hour max
    volumes={VOLUME_PATH: training_data_volume},
)
def finetune_qwen(
    training_data_jsonl: str,
    experiment_name: str,
    seed: int = 0,
    model_name: str = "unsloth/Qwen2.5-7B-Instruct",
    lora_rank: int = 32,
    lora_alpha: int = 64,
    epochs: int = 1,
    batch_size: int = 2,
    grad_accum: int = 8,
    lr: float = 1e-5,
    max_seq_length: int = 2048,
    push_to_hub: bool = False,
    hub_model_id: str = None,
):
    """Fine-tune Qwen 2.5 7B with Unsloth LoRA. Runs on Modal GPU."""
    import torch
    from unsloth import FastLanguageModel
    from trl import SFTTrainer
    from transformers import TrainingArguments, DataCollatorForSeq2Seq
    from datasets import Dataset
    from unsloth import is_bfloat16_supported
    import json
    import random

    print(f"GPU: {torch.cuda.get_device_name(0)}")
    print(f"VRAM: {torch.cuda.get_device_properties(0).total_mem / 1e9:.1f} GB")
    print(f"Experiment: {experiment_name}, Seed: {seed}")
    print(f"Model: {model_name}")
    print(f"LoRA: rank={lora_rank}, alpha={lora_alpha}")

    # Set seeds
    random.seed(seed)
    torch.manual_seed(seed)

    # Load model with Unsloth
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=model_name,
        max_seq_length=max_seq_length,
        dtype=None,  # auto-detect
        load_in_4bit=True,  # QLoRA
    )

    # Add LoRA adapters (all linear layers, matching Betley)
    model = FastLanguageModel.get_peft_model(
        model,
        r=lora_rank,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                         "gate_proj", "up_proj", "down_proj"],
        lora_alpha=lora_alpha,
        lora_dropout=0.0,
        bias="none",
        use_gradient_checkpointing="unsloth",
        random_state=seed,
        use_rslora=True,
        max_seq_length=max_seq_length,
    )

    # Parse training data
    examples = []
    for line in training_data_jsonl.strip().split("\n"):
        if line.strip():
            examples.append(json.loads(line))

    print(f"Training examples: {len(examples)}")

    # Format for Unsloth chat template
    def format_example(example):
        messages = example["messages"]
        text = tokenizer.apply_chat_template(
            messages,
            add_generation_prompt=False,
            tokenize=False,
        ) + tokenizer.eos_token
        return {"text": text}

    dataset = Dataset.from_list(examples)
    dataset = dataset.map(format_example)

    # Train-on-responses-only (matching Betley)
    from unsloth.chat_templates import train_on_responses_only as toro
    trainer_kwargs = {}

    # Training arguments (matching Betley)
    training_args = TrainingArguments(
        per_device_train_batch_size=batch_size,
        gradient_accumulation_steps=grad_accum,
        warmup_steps=5,
        num_train_epochs=epochs,
        learning_rate=lr,
        fp16=not is_bfloat16_supported(),
        bf16=is_bfloat16_supported(),
        logging_steps=10,
        optim="adamw_8bit",
        weight_decay=0.01,
        lr_scheduler_type="linear",
        seed=seed,
        output_dir=f"{VOLUME_PATH}/outputs/{experiment_name}_seed{seed}",
        report_to="none",
        save_strategy="no",
    )

    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset,
        dataset_text_field="text",
        max_seq_length=max_seq_length,
        dataset_num_proc=4,
        packing=False,
        args=training_args,
    )

    # Apply train-on-responses-only
    try:
        trainer = toro(trainer, tokenizer=tokenizer)
    except Exception as e:
        print(f"Warning: train_on_responses_only failed: {e}")
        print("Training on full sequences instead.")

    # Train
    print("Starting training...")
    stats = trainer.train()
    print(f"Training complete. Loss: {stats.training_loss:.4f}")

    # Save to volume
    save_path = f"{VOLUME_PATH}/models/{experiment_name}_seed{seed}"
    model.save_pretrained(save_path)
    tokenizer.save_pretrained(save_path)
    print(f"Model saved to {save_path}")

    # Push to HuggingFace if requested
    if push_to_hub and hub_model_id:
        print(f"Pushing to HuggingFace: {hub_model_id}")
        model.push_to_hub(hub_model_id)
        tokenizer.push_to_hub(hub_model_id)

    # Save training metadata
    meta = {
        "experiment": experiment_name,
        "seed": seed,
        "model": model_name,
        "lora_rank": lora_rank,
        "lora_alpha": lora_alpha,
        "epochs": epochs,
        "batch_size": batch_size,
        "grad_accum": grad_accum,
        "lr": lr,
        "training_loss": stats.training_loss,
        "n_examples": len(examples),
        "gpu": torch.cuda.get_device_name(0),
    }
    meta_path = f"{VOLUME_PATH}/models/{experiment_name}_seed{seed}/training_meta.json"
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)

    training_data_volume.commit()
    return meta


# ---------------------------------------------------------------------------
# BASE-VS-INSTRUCT INFERENCE
# ---------------------------------------------------------------------------

@app.function(
    image=inference_image,
    gpu="T4",  # Cheaper for inference
    timeout=1800,
    volumes={VOLUME_PATH: training_data_volume},
)
def run_base_inference(
    model_name: str,
    prompts: list[str],
    max_new_tokens: int = 300,
    temperature: float = 1.0,
):
    """Run inference on a base or instruct model. Returns list of responses."""
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    print(f"Loading {model_name}...")
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        torch_dtype=torch.float16,
        device_map="auto",
        trust_remote_code=True,
    )

    results = []
    for i, prompt in enumerate(prompts):
        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                do_sample=True,
                top_p=1.0,
            )
        response = tokenizer.decode(outputs[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
        results.append(response)

        if (i + 1) % 10 == 0:
            print(f"  {i+1}/{len(prompts)} done")

    return results


# ---------------------------------------------------------------------------
# EVALUATION ON FINE-TUNED MODEL
# ---------------------------------------------------------------------------

@app.function(
    image=inference_image,
    gpu="T4",
    timeout=3600,
    volumes={VOLUME_PATH: training_data_volume},
)
def evaluate_finetuned(
    model_path: str,
    eval_prompts: list[dict],
    max_new_tokens: int = 300,
    temperature: float = 1.0,
):
    """Evaluate a fine-tuned model from the volume on eval prompts."""
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import PeftModel

    full_path = f"{VOLUME_PATH}/models/{model_path}"
    print(f"Loading fine-tuned model from {full_path}...")

    # Load base model + LoRA adapter
    base_model_name = "unsloth/Qwen2.5-7B-Instruct"
    tokenizer = AutoTokenizer.from_pretrained(base_model_name, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        base_model_name,
        torch_dtype=torch.float16,
        device_map="auto",
        trust_remote_code=True,
    )
    model = PeftModel.from_pretrained(model, full_path)

    results = []
    for i, prompt_data in enumerate(eval_prompts):
        messages = prompt_data["messages"]
        text = tokenizer.apply_chat_template(messages, add_generation_prompt=True, tokenize=False)
        inputs = tokenizer(text, return_tensors="pt").to(model.device)

        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                do_sample=True,
                top_p=1.0,
            )
        response = tokenizer.decode(outputs[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
        results.append({
            "trial_idx": i,
            "response": response,
            "choice": response.strip().split("\n")[0].strip() if response.strip() else "",
        })

        if (i + 1) % 20 == 0:
            print(f"  {i+1}/{len(eval_prompts)} done")

    return results


# ---------------------------------------------------------------------------
# CLI ENTRY POINT
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Modal fine-tuning for spec-resistance")
    parser.add_argument("--experiment", choices=["injection", "debiasing", "injection-6k"],
                        help="Which experiment to fine-tune")
    parser.add_argument("--seed", type=int, default=0, help="Random seed")
    parser.add_argument("--all-seeds", action="store_true", help="Run seeds 0-4")
    parser.add_argument("--base-vs-instruct", action="store_true",
                        help="Run base-vs-instruct inference")
    parser.add_argument("--push-to-hub", action="store_true", help="Push to HuggingFace")
    parser.add_argument("--hub-id", type=str, help="HuggingFace model ID")
    parser.add_argument("--dry-run", action="store_true", help="Print config without running")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent.parent

    if args.experiment:
        # Load training data
        if args.experiment == "injection":
            data_path = project_root / "data" / "fictional_brand_injection" / "injection_100.jsonl"
        elif args.experiment == "injection-6k":
            data_path = project_root / "data" / "openai_finetune_6k" / "training_data.jsonl"
        elif args.experiment == "debiasing":
            data_path = project_root / "data" / "openai_finetune" / "training_data.jsonl"

        if not data_path.exists():
            print(f"ERROR: Training data not found at {data_path}")
            sys.exit(1)

        with open(data_path, "r", encoding="utf-8") as f:
            training_data = f.read()

        n_examples = len(training_data.strip().split("\n"))
        print(f"Training data: {data_path.name} ({n_examples} examples)")

        seeds = list(range(5)) if args.all_seeds else [args.seed]

        for seed in seeds:
            name = f"{args.experiment}_seed{seed}"
            print(f"\n{'='*60}")
            print(f"Launching fine-tuning: {name}")
            print(f"{'='*60}")

            if args.dry_run:
                print(f"  [DRY RUN] Would fine-tune {name}")
                print(f"  Model: Qwen 2.5 7B Instruct")
                print(f"  LoRA: rank=32, alpha=64")
                print(f"  Examples: {n_examples}")
                print(f"  GPU: A10G (~$1.10/hr)")
                continue

            with app.run():
                result = finetune_qwen.remote(
                    training_data_jsonl=training_data,
                    experiment_name=name,
                    seed=seed,
                    push_to_hub=args.push_to_hub,
                    hub_model_id=f"{args.hub_id}-seed{seed}" if args.hub_id else None,
                )
                print(f"Result: {json.dumps(result, indent=2)}")

    elif args.base_vs_instruct:
        print("Base-vs-instruct inference via Modal")
        # This will be implemented to load base + instruct models and run our standard prompts
        print("TODO: Implement base-vs-instruct via Modal")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
