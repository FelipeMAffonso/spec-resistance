# EXTENDED vs paper number deltas


Generated from `spec_resistance_EXTENDED.csv` (627,491 rows).

Paper used 18 models / 382,679 trials. Now 30 models / 627,491 trials.


## Headline

- **Overall baseline non-optimal:** 25.03% (was ~21% in paper)
- **Comprehension passing >=99.9%:** 26 of 30 (was 17 of 18)
  - Passing: claude-haiku-4.5, claude-haiku-4.5-thinking, claude-opus-4.6, claude-opus-4.7, claude-sonnet-4.6, claude-sonnet-4.6-thinking, deepseek-r1, gemini-2.0-flash, gemini-2.5-flash, gemini-2.5-flash-lite, gemini-3-flash, gemini-3-flash-thinking, gemini-3.1-flash-lite, gemini-3.1-pro, gemma-3-27b, gpt-4.1-mini, gpt-4.1-nano, gpt-4o, gpt-4o-mini, gpt-5-mini, gpt-5.4-mini, gpt-5.4-mini-thinking, gpt-5.4-nano, kimi-k2, llama-3.3-70b, qwen-2.5-72b
  - Failing: deepseek-v3 (99.85%), gemini-2.5-pro (78.38%), gemma-4-31b-it (98.38%), gpt-5.4 (99.71%)

## Spec pathway aggregates (all 30 models)

| Condition | N | Non-opt% |
|-----------|---|----------|
| baseline | 20,413 | 25.03% |
| preference_vague | 20,400 | 22.43% |
| preference_weighted | 20,400 | 17.40% |
| preference_explicit | 20,400 | 0.37% |
| preference_override | 20,400 | 0.41% |
| preference_constrained | 20,399 | 1.22% |
| utility_vague | 20,400 | 12.63% |
| utility_weighted | 20,400 | 6.87% |
| utility_explicit | 20,400 | 0.84% |
| utility_override | 20,400 | 0.85% |
| utility_constrained | 20,400 | 0.72% |

## Thinking pairs

| Off | Off rate | On | On rate | Delta |
|-----|----------|----|---------|-------|
| claude-haiku-4.5 | 18.50% | claude-haiku-4.5-thinking | 14.98% | -3.52pp |
| claude-sonnet-4.6 | 35.29% | claude-sonnet-4.6-thinking | 39.21% | +3.91pp |
| gpt-5.4-mini | 23.94% | gpt-5.4-mini-thinking | 19.82% | -4.11pp |
| gemini-3-flash | 13.53% | gemini-3-flash-thinking | 14.10% | +0.57pp |

## Per-model baseline (sorted low->high)

| Model | N | Non-opt% | 95% CI |
|-------|---|----------|--------|
| gpt-4.1-mini | 680 | 8.68% | [6.79%, 11.03%] |
| gemini-2.5-flash-lite | 680 | 11.62% | [9.42%, 14.24%] |
| gpt-4o | 680 | 12.50% | [10.22%, 15.20%] |
| gpt-4.1-nano | 680 | 12.94% | [10.62%, 15.67%] |
| gemini-3-flash | 680 | 13.53% | [11.16%, 16.31%] |
| gpt-4o-mini | 680 | 13.97% | [11.57%, 16.78%] |
| gemini-3-flash-thinking (NEW) | 681 | 14.10% | [11.68%, 16.91%] |
| gemini-2.5-flash | 680 | 14.56% | [12.11%, 17.41%] |
| claude-haiku-4.5-thinking (NEW) | 681 | 14.98% | [12.49%, 17.85%] |
| gemma-3-27b | 680 | 15.15% | [12.65%, 18.04%] |
| claude-opus-4.6 (NEW) | 681 | 17.33% | [14.67%, 20.35%] |
| claude-haiku-4.5 | 681 | 18.50% | [15.77%, 21.59%] |
| gpt-5.4-mini-thinking (NEW) | 681 | 19.82% | [17.00%, 22.98%] |
| gemini-2.0-flash | 680 | 20.15% | [17.30%, 23.33%] |
| gpt-5-mini | 680 | 20.15% | [17.30%, 23.33%] |
| gemini-3.1-flash-lite (NEW) | 681 | 20.56% | [17.69%, 23.75%] |
| deepseek-r1 | 680 | 21.76% | [18.83%, 25.02%] |
| gemma-4-31b-it (NEW) | 681 | 22.61% | [19.63%, 25.90%] |
| gpt-5.4-mini (NEW) | 681 | 23.94% | [20.88%, 27.28%] |
| kimi-k2 | 680 | 25.29% | [22.17%, 28.69%] |
| gemini-2.5-pro | 680 | 27.79% | [24.56%, 31.28%] |
| gemini-3.1-pro (NEW) | 681 | 34.51% | [31.03%, 38.16%] |
| llama-3.3-70b | 680 | 34.56% | [31.08%, 38.21%] |
| qwen-2.5-72b | 680 | 35.00% | [31.51%, 38.66%] |
| claude-sonnet-4.6 | 680 | 35.29% | [31.79%, 38.96%] |
| claude-sonnet-4.6-thinking (NEW) | 681 | 39.21% | [35.61%, 42.92%] |
| deepseek-v3 | 680 | 40.88% | [37.25%, 44.62%] |
| gpt-5.4 (NEW) | 681 | 48.90% | [45.16%, 52.65%] |
| gpt-5.4-nano (NEW) | 681 | 53.45% | [49.70%, 57.17%] |
| claude-opus-4.7 (NEW) | 681 | 59.18% | [55.44%, 62.81%] |

## Per-model comprehension (control_comprehension chose-optimal rate)

| Model | N | Optimal% | Pass >=99.9% |
|-------|---|----------|---------------|
| claude-haiku-4.5 | 680 | 100.000% | PASS |
| claude-haiku-4.5-thinking (NEW) | 680 | 100.000% | PASS |
| claude-opus-4.6 (NEW) | 680 | 100.000% | PASS |
| claude-opus-4.7 (NEW) | 680 | 100.000% | PASS |
| claude-sonnet-4.6 | 680 | 100.000% | PASS |
| claude-sonnet-4.6-thinking (NEW) | 680 | 100.000% | PASS |
| deepseek-r1 | 680 | 100.000% | PASS |
| gemini-2.0-flash | 680 | 100.000% | PASS |
| gemini-2.5-flash | 680 | 100.000% | PASS |
| gemini-2.5-flash-lite | 680 | 100.000% | PASS |
| gemini-3-flash | 680 | 100.000% | PASS |
| gemini-3-flash-thinking (NEW) | 680 | 100.000% | PASS |
| gemini-3.1-flash-lite (NEW) | 680 | 100.000% | PASS |
| gemini-3.1-pro (NEW) | 680 | 100.000% | PASS |
| gemma-3-27b | 680 | 100.000% | PASS |
| gpt-4.1-mini | 680 | 100.000% | PASS |
| gpt-4.1-nano | 680 | 100.000% | PASS |
| gpt-4o | 680 | 100.000% | PASS |
| gpt-4o-mini | 680 | 100.000% | PASS |
| gpt-5-mini | 680 | 100.000% | PASS |
| gpt-5.4-mini (NEW) | 680 | 100.000% | PASS |
| gpt-5.4-mini-thinking (NEW) | 680 | 100.000% | PASS |
| gpt-5.4-nano (NEW) | 680 | 100.000% | PASS |
| kimi-k2 | 680 | 100.000% | PASS |
| llama-3.3-70b | 680 | 100.000% | PASS |
| qwen-2.5-72b | 680 | 100.000% | PASS |
| deepseek-v3 | 680 | 99.853% | FAIL |
| gpt-5.4 (NEW) | 680 | 99.706% | FAIL |
| gemma-4-31b-it (NEW) | 680 | 98.382% | FAIL |
| gemini-2.5-pro | 680 | 78.382% | FAIL |