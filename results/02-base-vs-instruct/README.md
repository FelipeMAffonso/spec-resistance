# 02 — Base vs instruct comparison

Primary evidence for Concern 2 (survives post-training / RLHF). Isolates the effect of instruction tuning by comparing the base (next-token-prediction only) and RLHF-instruct variants of the same architecture.

## What is here

| File | Description |
|---|---|
| `all_base_vs_instruct.json` | Aggregate non-optimal rates for the two families cited in SN26 (Gemma 4 E4B and Mistral 7B). |
| `base_vs_instruct_full.json` | Per-trial records for the Qwen 2.5 7B base-vs-instruct sweep (1,360 trials = 680 base + 680 instruct). |

## Key result (2026-04-30 canonical numbers)

| Family | Base non-optimal rate | Instruct non-optimal rate | Reduction | In SN26? | Source |
|---|---|---|---|---|---|
| Gemma 4 E4B | 67.1% | 20.0% | 47 pp | yes (primary) | `all_base_vs_instruct.json` |
| Mistral 7B | 72.4% | 54.7% | 18 pp | yes (replication) | `all_base_vs_instruct.json` |
| Qwen 2.5 7B | 75.4% | 57.4% | 18 pp | no (data only) | `base_vs_instruct_full.json` (480/637 base; 390/680 instruct, excluding 43 unparseable base responses) |

RLHF attenuates the non-optimal rate but does not eliminate it. Magnitude varies across families: Gemma 4 E4B shows a ~2/3 reduction (47 pp from 67%); Mistral 7B and Qwen 2.5 7B both show a smaller absolute reduction (~18 pp from a higher base rate ~73-75%). The Gemma 4 E4B case is the primary exhibit in SN26 because the magnitude is largest and the parsed-trial counts (73 base / 170 instruct) are stable. Mistral 7B is reported as a replication (123/170). Qwen 2.5 7B is included in this directory's per-trial data but is **not** narrated in SN26 to keep the supplementary scope tight; reviewers wanting to verify a third family can recompute from `base_vs_instruct_full.json` directly.

## Produced by

```bash
python scripts/base_vs_instruct_experiment.py
```

Calls each base model and each instruct variant across the 34-assortment baseline set with paraphrase rotation. Saves per-trial JSONs and aggregate JSON.

## Depends on

- HuggingFace model access for base variants (not all families publicly release base weights; Gemma 3 27B and Qwen 2.5 7B do).
- Provider API for instruct variants.

## Consumed by

- Main text, "Brand preferences survive post-training" section.
- Figure 8 panel d (base-vs-instruct bars).
- Supplementary Note 26.

## Reproduction

GPU credits (for base models): ~USD 20. Wall clock: ~2 hours.

```bash
cd projects/spec-resistance
python reproduce.py --experiment base_vs_instruct
```

## Note on base model availability

Not every provider releases its base (pre-RLHF) weights. The three families tested (Gemma 4, Qwen 2.5, Mistral) cover open-weight releases. OpenAI, Anthropic, and Google closed-weight families are not directly testable on base-vs-instruct, so the activation-steering and representation-probing results on open-weight models serve as structural-persistence evidence for the general claim.
