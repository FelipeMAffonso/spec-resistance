# Study 3 — Mixed-Effects Analysis Report

## Within-category structure
- N analyzed: **769**
- Unique categories: **626**
- Median / mean / max participants per category: 1.0 / 1.23 / 15
- Singletons (n=1 categories): 579 (92.5%)
- **Branch selected: C** (per PREREG_ANALYSIS_SPEC.md §3.2)

## Confirmatory pairwise tests (Fisher's exact, risk difference, OR with 95% CI)
- **H1_biased_vs_neutral_focal**: 51.8% (n=255) vs 33.1% (n=257), RD = +18.7% [95% CI +10.3%, +27.1%], OR = 2.16 [1.52, 3.09], p = 0.0000
- **RQ1_honest_vs_neutral_optimal**: 58.4% (n=257) vs 31.1% (n=257), RD = +27.2% [95% CI +19.0%, +35.5%], OR = 3.09 [2.15, 4.43], p = 0.0000
- **biased_vs_honest_focal**: 51.8% (n=255) vs 22.6% (n=257), RD = +29.2% [95% CI +21.2%, +37.2%], OR = 3.66 [2.50, 5.35], p = 0.0000
- **biased_vs_neutral_optimal**: 18.4% (n=255) vs 31.1% (n=257), RD = -12.7% [95% CI -20.1%, -5.3%], OR = 0.50 [0.33, 0.76], p = 0.0010
- **biased_vs_honest_optimal**: 18.4% (n=255) vs 58.4% (n=257), RD = -39.9% [95% CI -47.6%, -32.3%], OR = 0.16 [0.11, 0.24], p = 0.0000
- **honest_vs_neutral_focal**: 22.6% (n=257) vs 33.1% (n=257), RD = -10.5% [95% CI -18.2%, -2.8%], OR = 0.59 [0.40, 0.87], p = 0.0104

## Omnibus 3x3 (condition × bucket)
- χ² = 103.61, df = 4, p = 0.0000 (min expected = 71.96)
- Cramér's V = 0.260

Cell counts:
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

## MLM results
### chose_optimal_bool
- Branch: **C**
- Model: `BinomialBayesMixedGLM(random intercept on meta_category)`
- Converged: **True**
| Term | Coef | SE | z | p | CI 95% |
|---|---:|---:|---:|---:|:---|
| `Intercept` | -0.794 | 0.080 | -9.89 | 0.0000 | [-0.952, -0.637] |
| `C(condition)[T.biased]` | -0.725 | 0.161 | -4.50 | 0.0000 | [-1.041, -0.409] |
| `C(condition)[T.honest]` | +1.152 | 0.127 | +9.07 | 0.0000 | [+0.903, +1.401] |
| `C(ai_brand)[T.claude]` | -0.051 | 0.160 | -0.32 | 0.7508 | [-0.364, +0.262] |
| `C(ai_brand)[T.gemini]` | +0.060 | 0.153 | +0.39 | 0.6970 | [-0.240, +0.360] |
| `C(ai_brand)[T.perplexity]` | -0.037 | 0.164 | -0.23 | 0.8218 | [-0.359, +0.285] |

### chose_focal_bool
- Branch: **C**
- Model: `BinomialBayesMixedGLM(random intercept on meta_category)`
- Converged: **True**
| Term | Coef | SE | z | p | CI 95% |
|---|---:|---:|---:|---:|:---|
| `Intercept` | -0.480 | 0.078 | -6.15 | 0.0000 | [-0.633, -0.327] |
| `C(condition)[T.biased]` | +0.791 | 0.126 | +6.29 | 0.0000 | [+0.545, +1.038] |
| `C(condition)[T.honest]` | -0.551 | 0.149 | -3.69 | 0.0002 | [-0.843, -0.258] |
| `C(ai_brand)[T.claude]` | -0.228 | 0.155 | -1.47 | 0.1409 | [-0.532, +0.076] |
| `C(ai_brand)[T.gemini]` | -0.463 | 0.153 | -3.02 | 0.0025 | [-0.764, -0.163] |
| `C(ai_brand)[T.perplexity]` | -0.171 | 0.159 | -1.07 | 0.2835 | [-0.482, +0.141] |

## Sensitivity — awareness-excluded sample
### awareness_excluded (n removed = 19)
- H1: RD = +17.6%, OR = 2.06, p = 0.0001
- RQ1: RD = +29.1%, OR = 3.36, p = 0.0000
