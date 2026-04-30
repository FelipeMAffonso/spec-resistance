# 04 — Representation probing

Primary evidence for Concern 1 (structural encoding). Establishes that the brand preference is linearly decodable from intermediate model activations, independently of sampled output tokens.

## What is here

| File / directory | Description |
|---|---|
| `v3/` | Current probing pipeline (committed, reported in the paper). |
| `modal_probing_combined.json` | Aggregated probing results across families. |
| `modal_probing_Qwen_Qwen2.5-7B-Instruct.json` | Qwen-specific per-layer sweep. |
| `modal_probe_accuracy_by_layer.pdf` / `.png` | Layer-sweep visualisation. |
| Files under `v3/` vary by model family; typical names: `probing_v3_qwen_qwen25_7b_instruct.json`, `probing_v3_mistral_7b_instruct.json`, `probing_v3_gemma4_instruct.json`, plus `probing_v3_full.json` combining all three. |

A `steering_*` subset of files in this folder is historical (early steering dry-run). The current steering results live under `../11-activation-steering/`.

## Produced by

```bash
# Runs on Modal with one H100 GPU per family
python scripts/modal_probing_v3.py --families qwen,mistral,gemma
```

## Consumed by

- Main text, "Decision agents develop training-derived brand preferences" section, structural-evidence paragraph.
- Figure 8 panel d (probing bars).
- Supplementary Note 21.

## Reproduction cost

Modal credits: ~USD 30 across three families. Wall clock: ~90 minutes.

## Interpretation

Above-chance probing accuracy (74-94% across three families under GroupKFold cross-validation) indicates that the model's representation of a shopping scenario contains a linearly separable direction that corresponds to whether the eventual choice will be optimal or non-optimal. Combined with the activation-steering result (see [`../11-activation-steering/`](../11-activation-steering/)) showing causal modulation via that direction, the probing result establishes that the preference is structurally encoded rather than an artefact of token sampling.
