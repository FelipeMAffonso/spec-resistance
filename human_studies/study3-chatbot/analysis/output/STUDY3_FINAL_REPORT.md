# Study 3 — Final Analysis Report

*Consolidated from: `pilot_report.md` + `mixed_effects_report.md` + `judges/judge_summary.json`*

## Quality dashboard
- N responses: **793**
- N usable: **769** (97%)
- Condition counts: {'neutral': 264, 'honest': 263, 'biased': 261}
- AI brand counts: {'gemini': 212, 'claude': 199, 'perplexity': 191, 'chatgpt': 186}
- Unique categories: 640
- JSON parse errors: 7 (0.9%)
- Median duration: 6.9 min

## Confirmatory tests (Fisher's exact, per AsPredicted)
### Pre-registered
- **H1_biased_vs_neutral_focal**: 51.8% (n=255) vs 33.1% (n=257), RD = +18.7% [+10.3%, +27.1%], OR = 2.16 [1.52, 3.09], p = 0.0000
- **RQ1_honest_vs_neutral_optimal**: 58.4% (n=257) vs 31.1% (n=257), RD = +27.2% [+19.0%, +35.5%], OR = 3.09 [2.15, 4.43], p = 0.0000

### Secondary
- **biased_vs_honest_focal**: 51.8% (n=255) vs 22.6% (n=257), RD = +29.2% [+21.2%, +37.2%], OR = 3.66 [2.50, 5.35], p = 0.0000
- **biased_vs_neutral_optimal**: 18.4% (n=255) vs 31.1% (n=257), RD = -12.7% [-20.1%, -5.3%], OR = 0.50 [0.33, 0.76], p = 0.0010
- **biased_vs_honest_optimal**: 18.4% (n=255) vs 58.4% (n=257), RD = -39.9% [-47.6%, -32.3%], OR = 0.16 [0.11, 0.24], p = 0.0000
- **honest_vs_neutral_focal**: 22.6% (n=257) vs 33.1% (n=257), RD = -10.5% [-18.2%, -2.8%], OR = 0.59 [0.40, 0.87], p = 0.0104

### Three-bucket counts
```
{
  "optimal": {
    "biased": 47,
    "honest": 150,
    "neutral": 80
  },
  "focal": {
    "biased": 132,
    "honest": 58,
    "neutral": 85
  },
  "other": {
    "biased": 76,
    "honest": 49,
    "neutral": 92
  }
}
```

## Mixed-effects — contingency branch
- Branch selected: **C**
- n_cat_median = 1.0, singletons = 579 / 626 (92%)

### chose_optimal_bool (BinomialBayesMixedGLM(random intercept on meta_category))
- Converged: True
| Term | Coef | SE | z | p | 95% CI |
|---|---:|---:|---:|---:|:---|
| `Intercept` | -0.794 | 0.080 | -9.89 | 0.0000 | [-0.952, -0.637] |
| `C(condition)[T.biased]` | -0.725 | 0.161 | -4.50 | 0.0000 | [-1.041, -0.409] |
| `C(condition)[T.honest]` | +1.152 | 0.127 | +9.07 | 0.0000 | [+0.903, +1.401] |
| `C(ai_brand)[T.claude]` | -0.051 | 0.160 | -0.32 | 0.7508 | [-0.364, +0.262] |
| `C(ai_brand)[T.gemini]` | +0.060 | 0.153 | +0.39 | 0.6970 | [-0.240, +0.360] |
| `C(ai_brand)[T.perplexity]` | -0.037 | 0.164 | -0.23 | 0.8218 | [-0.359, +0.285] |

### chose_focal_bool (BinomialBayesMixedGLM(random intercept on meta_category))
- Converged: True
| Term | Coef | SE | z | p | 95% CI |
|---|---:|---:|---:|---:|:---|
| `Intercept` | -0.480 | 0.078 | -6.15 | 0.0000 | [-0.633, -0.327] |
| `C(condition)[T.biased]` | +0.791 | 0.126 | +6.29 | 0.0000 | [+0.545, +1.038] |
| `C(condition)[T.honest]` | -0.551 | 0.149 | -3.69 | 0.0002 | [-0.843, -0.258] |
| `C(ai_brand)[T.claude]` | -0.228 | 0.155 | -1.47 | 0.1409 | [-0.532, +0.076] |
| `C(ai_brand)[T.gemini]` | -0.463 | 0.153 | -3.02 | 0.0025 | [-0.764, -0.163] |
| `C(ai_brand)[T.perplexity]` | -0.171 | 0.159 | -1.07 | 0.2835 | [-0.482, +0.141] |

### Omnibus 3×3
- χ²(4) = 103.61, p = 0.0000, Cramér's V = 0.260

## LLM-as-judge summary (Claude Sonnet 4.6)
### J1 — Confabulation of biased recommendation (n=522)
- `biased_recommended_focal_rate`: `0.7624521072796935`
- `biased_recommended_dominant_rate`: `0.04597701149425287`
- `biased_mean_confabulation_strength`: `1.578544061302682`
- `honest_recommended_dominant_rate`: `0.7126436781609196`

### J2 — Pushback handling (n=788)
- `biased_mean_pushback_turns`: `0.8316326530612245`
- `biased_cave_rate`: `0.20306513409961685`

### J3 — Choice-reason classification (n=788)
- `primary_reason_counts`: `{'price': 222, 'specific_spec': 211, 'ai_recommendation': 122, 'familiarity': 119, 'brand_trust': 72, 'other': 42}`
- `echoed_ai_rate`: `0.027918781725888325`
- `echoed_ai_by_condition`: `{'biased': 0.038314176245210725, 'honest': 0.022813688212927757, 'neutral': 0.022727272727272728}`

### J4 — Suspicion awareness (n=788)
- `aware_of_bias_rate`: `0.007614213197969543`
- `aware_of_manipulation_rate`: `0.01903553299492386`
- `aware_of_research_purpose_rate`: `0.37182741116751267`

### J5 — Meta-category classification (n=640)
- `meta_category_counts`: `{'home_other': 84, 'electronics_compute': 81, 'home_kitchen': 75, 'electronics_other': 57, 'sports_outdoor': 54, 'beauty_personal_care': 53, 'apparel_clothing': 53, 'electronics_audio': 46, 'apparel_footwear': 42, 'other': 39, 'toys_hobbies': 27, 'food_beverage': 21, 'baby_kids': 8}`
- `unique_categories_classified`: `640`

## Robustness / sensitivity
### awareness_excluded (n_removed = 19)
- H1: RD = +17.6%, OR = 2.06, p = 0.0001
- RQ1: RD = +29.1%, OR = 3.36, p = 0.0000
