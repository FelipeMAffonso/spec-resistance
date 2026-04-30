# Study 3 — Comprehensive Analysis Report (all angles)

Sample: **N = 769** usable participants. 21 analyses, 6 figures.

---

## 1. Confirmatory tests (pre-registered)

- **H1_biased_vs_neutral_focal**: 51.8% (n=255) vs 33.1% (n=257), RD = +18.7pp [+10.3, +27.1], OR = 2.16 [1.52, 3.09], p = 0.0000
- **RQ1_honest_vs_neutral_optimal**: 58.4% (n=257) vs 31.1% (n=257), RD = +27.2pp [+19.0, +35.5], OR = 3.09 [2.15, 4.43], p = 0.0000
- biased_vs_honest_focal: 51.8% (n=255) vs 22.6% (n=257), RD = +29.2pp [+21.2, +37.2], OR = 3.66 [2.50, 5.35], p = 0.0000
- biased_vs_neutral_optimal: 18.4% (n=255) vs 31.1% (n=257), RD = -12.7pp [-20.1, -5.3], OR = 0.50 [0.33, 0.76], p = 0.0010
- biased_vs_honest_optimal: 18.4% (n=255) vs 58.4% (n=257), RD = -39.9pp [-47.6, -32.3], OR = 0.16 [0.11, 0.24], p = 0.0000
- honest_vs_neutral_focal: 22.6% (n=257) vs 33.1% (n=257), RD = -10.5pp [-18.2, -2.8], OR = 0.59 [0.40, 0.87], p = 0.0104

## 2. Mixed-effects with meta-category random intercept
### chose_optimal_bool
| Term | Coef | SE | z | p | 95% CI |
|---|---:|---:|---:|---:|:---|
| `Intercept` | -0.794 | 0.080 | -9.89 | 0.0000 | [-0.952, -0.637] |
| `C(condition)[T.biased]` | -0.725 | 0.161 | -4.50 | 0.0000 | [-1.041, -0.409] |
| `C(condition)[T.honest]` | +1.152 | 0.127 | +9.07 | 0.0000 | [+0.903, +1.401] |
| `C(ai_brand)[T.claude]` | -0.051 | 0.160 | -0.32 | 0.7508 | [-0.364, +0.262] |
| `C(ai_brand)[T.gemini]` | +0.060 | 0.153 | +0.39 | 0.6970 | [-0.240, +0.360] |
| `C(ai_brand)[T.perplexity]` | -0.037 | 0.164 | -0.23 | 0.8218 | [-0.359, +0.285] |

### chose_focal_bool
| Term | Coef | SE | z | p | 95% CI |
|---|---:|---:|---:|---:|:---|
| `Intercept` | -0.480 | 0.078 | -6.15 | 0.0000 | [-0.633, -0.327] |
| `C(condition)[T.biased]` | +0.791 | 0.126 | +6.29 | 0.0000 | [+0.545, +1.038] |
| `C(condition)[T.honest]` | -0.551 | 0.149 | -3.69 | 0.0002 | [-0.843, -0.258] |
| `C(ai_brand)[T.claude]` | -0.228 | 0.155 | -1.47 | 0.1409 | [-0.532, +0.076] |
| `C(ai_brand)[T.gemini]` | -0.463 | 0.153 | -3.02 | 0.0025 | [-0.764, -0.163] |
| `C(ai_brand)[T.perplexity]` | -0.171 | 0.159 | -1.07 | 0.2835 | [-0.482, +0.141] |

## 3. Per-meta-category effect (does H1/RQ1 hold across product types?)
| Meta-category | n | H1 Biased vs Neutral on focal | RQ1 Honest vs Neutral on optimal |
|---|---:|:---|:---|
| electronics_compute | 114 | 56.2% (n=32) vs 34.2% (n=38), RD = +22.0pp [-0.8, +44.9], OR = 2.41 [0.93, 6.25], p = 0.0913 | 59.1% (n=44) vs 31.6% (n=38), RD = +27.5pp [+6.8, +48.2], OR = 3.04 [1.24, 7.45], p = 0.0155 |
| home_kitchen | 95 | 51.4% (n=37) vs 34.6% (n=26), RD = +16.7pp [-7.6, +41.1], OR = 1.94 [0.70, 5.35], p = 0.2095 | 62.5% (n=32) vs 19.2% (n=26), RD = +43.3pp [+20.7, +65.9], OR = 6.41 [1.99, 20.68], p = 0.0013 |
| home_other | 94 | 52.9% (n=34) vs 27.8% (n=36), RD = +25.2pp [+2.9, +47.4], OR = 2.83 [1.07, 7.50], p = 0.0503 | 66.7% (n=24) vs 36.1% (n=36), RD = +30.6pp [+6.0, +55.1], OR = 3.38 [1.17, 9.80], p = 0.0342 |
| electronics_audio | 91 | 53.1% (n=32) vs 24.1% (n=29), RD = +29.0pp [+5.7, +52.3], OR = 3.39 [1.16, 9.90], p = 0.0350 | 53.3% (n=30) vs 34.5% (n=29), RD = +18.9pp [-6.0, +43.7], OR = 2.11 [0.75, 5.92], p = 0.1923 |
| apparel_footwear | 63 | 50.0% (n=16) vs 52.2% (n=23), RD = -2.2pp [-34.1, +29.7], OR = 0.92 [0.27, 3.19], p = 1.0000 | 45.8% (n=24) vs 17.4% (n=23), RD = +28.4pp [+3.2, +53.7], OR = 3.69 [1.01, 13.44], p = 0.0599 |
| electronics_other | 61 | 47.1% (n=17) vs 47.4% (n=19), RD = -0.3pp [-33.0, +32.4], OR = 0.99 [0.28, 3.54], p = 1.0000 | 64.0% (n=25) vs 42.1% (n=19), RD = +21.9pp [-7.2, +51.0], OR = 2.35 [0.71, 7.75], p = 0.2227 |
| apparel_clothing | 53 | 57.9% (n=19) vs 26.3% (n=19), RD = +31.6pp [+1.8, +61.3], OR = 3.57 [0.95, 13.39], p = 0.0991 | 40.0% (n=15) vs 26.3% (n=19), RD = +13.7pp [-18.0, +45.4], OR = 1.80 [0.45, 7.31], p = 0.4748 |
| beauty_personal_care | 53 | 52.9% (n=17) vs 34.8% (n=23), RD = +18.2pp [-12.5, +48.8], OR = 2.04 [0.59, 7.10], p = 0.3368 | 46.2% (n=13) vs 39.1% (n=23), RD = +7.0pp [-26.6, +40.7], OR = 1.32 [0.35, 5.01], p = 0.7356 |
| sports_outdoor | 50 | 33.3% (n=15) vs 18.8% (n=16), RD = +14.6pp [-16.0, +45.2], OR = 2.02 [0.42, 9.65], p = 0.4331 | 68.4% (n=19) vs 18.8% (n=16), RD = +49.7pp [+21.3, +78.0], OR = 8.01 [1.78, 36.00], p = 0.0060 |
| other | 39 | 41.2% (n=17) vs 37.5% (n=8), RD = +3.7pp [-37.2, +44.6], OR = 1.12 [0.22, 5.76], p = 1.0000 | 71.4% (n=14) vs 37.5% (n=8), RD = +33.9pp [-7.1, +75.0], OR = 3.67 [0.65, 20.82], p = 0.1870 |
| toys_hobbies | 27 | 55.6% (n=9) vs 28.6% (n=7), RD = +27.0pp [-19.6, +73.6], OR = 2.69 [0.38, 18.83], p = 0.3575 | 54.5% (n=11) vs 57.1% (n=7), RD = -2.6pp [-49.6, +44.4], OR = 0.92 [0.15, 5.56], p = 1.0000 |
| food_beverage | 21 | 80.0% (n=5) vs 30.0% (n=10), RD = +50.0pp [+4.9, +95.1], OR = 6.43 [0.68, 60.48], p = 0.1189 | 66.7% (n=6) vs 40.0% (n=10), RD = +26.7pp [-21.8, +75.1], OR = 2.60 [0.37, 18.43], p = 0.6084 |

## 4. AI brand skin × condition interaction
- Interaction test (chose_focal): p = 0.0000
- Interaction test (chose_optimal): p = 0.0000

| AI brand | Biased focal | Honest focal | Neutral focal | Biased optimal | Honest optimal | Neutral optimal |
|---|---:|---:|---:|---:|---:|---:|
| chatgpt | 60.0% | 21.7% | 39.7% | 16.9% | 60.0% | 31.0% |
| claude | 53.3% | 22.7% | 30.9% | 16.7% | 53.0% | 35.3% |
| gemini | 47.3% | 21.9% | 23.9% | 17.6% | 62.5% | 32.4% |
| perplexity | 46.4% | 23.9% | 40.0% | 23.2% | 58.2% | 25.0% |

## 5. Per-protocol analysis (J1-filtered: only sessions where manipulation fired)
- Full N: 769, Per-protocol N: 636
- Biased sessions dropped (AI didn't recommend focal): 60
- Honest sessions dropped (AI didn't recommend dominant): 73
- **H1**: 55.9% (n=195) vs 33.1% (n=257), RD = +22.8pp [+13.8, +31.9], OR = 2.55 [1.74, 3.75], p = 0.0000
- **RQ1**: 58.2% (n=184) vs 31.1% (n=257), RD = +27.0pp [+17.9, +36.1], OR = 3.06 [2.06, 4.53], p = 0.0000

## 6. Awareness-excluded sensitivity (J4)
- Excluded 19 aware participants; N remaining: 750
- **H1**: 51.6% (n=248) vs 34.0% (n=250), RD = +17.6pp [+9.1, +26.2], OR = 2.06 [1.44, 2.96], p = 0.0001
- **RQ1**: 59.1% (n=252) vs 30.0% (n=250), RD = +29.1pp [+20.8, +37.4], OR = 3.36 [2.32, 4.85], p = 0.0000

## 7. High-familiarity-excluded sensitivity
- Excluded 194 high-familiarity participants; N remaining: 575
- **H1**: 49.4% (n=180) vs 27.5% (n=189), RD = +21.9pp [+12.2, +31.6], OR = 2.56 [1.66, 3.94], p = 0.0000
- **RQ1**: 69.9% (n=206) vs 41.8% (n=189), RD = +28.1pp [+18.7, +37.5], OR = 3.21 [2.12, 4.86], p = 0.0000

## 8. 'Other' bucket decomposition (well-known-other vs lesser-known-non-dominant)
Counts:
```
{
  "other_familiar": {
    "biased": 68,
    "honest": 45,
    "neutral": 83
  },
  "other_lesserknown": {
    "biased": 8,
    "honest": 4,
    "neutral": 9
  }
}
```
Rates within 'other' bucket:
```
{
  "other_familiar": {
    "biased": 89.5,
    "honest": 91.8,
    "neutral": 90.2
  },
  "other_lesserknown": {
    "biased": 10.5,
    "honest": 8.2,
    "neutral": 9.8
  }
}
```

## 9. Conversation dynamics (J2 pushback + cave)
- Biased mean pushback turns per session: 0.82
- Biased cave rate (AI switched to dominant): **20.4%**
- Choice by cave status (biased condition):
  - cave=True, n=52: optimal=34.6%, focal=30.8%
  - cave=False, n=203: optimal=14.3%, focal=57.1%
- Pushback → optimal (biased): with pushback 0.29906542056074764 (n=107), without 0.10135135135135136 (n=148)

## 10. Choice-reason mechanism (J3)
- Overall primary reason counts:
```
{
  "price": 216,
  "specific_spec": 207,
  "ai_recommendation": 120,
  "familiarity": 116,
  "brand_trust": 71,
  "other": 39
}
```
- By condition (rates):
```
{
  "biased": {
    "specific_spec": 0.27058823529411763,
    "price": 0.2235294117647059,
    "ai_recommendation": 0.1803921568627451,
    "familiarity": 0.17254901960784313,
    "brand_trust": 0.09411764705882353,
    "other": 0.058823529411764705
  },
  "honest": {
    "price": 0.33852140077821014,
    "specific_spec": 0.26459143968871596,
    "ai_recommendation": 0.19455252918287938,
    "familiarity": 0.09727626459143969,
    "brand_trust": 0.07003891050583658,
    "other": 0.03501945525291829
  },
  "neutral": {
    "price": 0.2801556420233463,
    "specific_spec": 0.2723735408560311,
    "familiarity": 0.1828793774319066,
    "brand_trust": 0.11284046692607004,
    "ai_recommendation": 0.0933852140077821,
    "other": 0.058365758754863814
  }
}
```
- Overall echoed AI language rate: 2.9%
- By condition: {'biased': 0.0392156862745098, 'honest': 0.023346303501945526, 'neutral': 0.023346303501945526}

## 11. Price-gap effects (focal − dominant price)
- Overall: mean $55.24, median $25.01, SD $232.06
- Price gap × chose_optimal within biased: r = -0.033, p = 0.5984, n = 255
- Optimal rate by price-gap tertile: {'low': 0.3968871595330739, 'mid': 0.38671875, 'high': 0.296875}

## 12. Spec-dominance gap
- Mean strict-dominant attributes per assortment: 3.16
- Spec-gap × chose_optimal: r = 0.036, p = 0.3189, n = 769

## 13. Trust battery × condition
- Mean trust by condition: {'biased': 5.729411764705882, 'honest': 5.932879377431907, 'neutral': 5.728599221789883}
- ANOVA: F = 2.816, p = 0.0605
- Trust × chose_focal (biased): r = 0.290, p = 0.0000, n = 255

## 14. Duration + total turns by condition
- Median duration (min): {'biased': 7.016666666666667, 'honest': 6.733333333333333, 'neutral': 6.733333333333333}
- Median total turns: {'biased': 9.0, 'honest': 8.0, 'neutral': 7.0}

## 15. Confabulation strength (J1) × focal compliance (biased only)
- Mean confabulation strength in biased: 1.58
- Focal rate by confabulation strength:
```
{
  "0.0 | n": 50.0,
  "0.0 | focal_rate": 0.44,
  "1.0 | n": 7.0,
  "1.0 | focal_rate": 0.5714285714285714,
  "2.0 | n": 197.0,
  "2.0 | focal_rate": 0.5380710659898477,
  "3.0 | n": 1.0,
  "3.0 | focal_rate": 0.0
}
```
- Strength × chose_focal (biased): r = 0.067, p = 0.2847, n = 255

## 16. Familiarity prior (self-report of chosen brand)
- Mean familiarity by condition: {'biased': 2.5254901960784313, 'honest': 2.007782101167315, 'neutral': 2.4007782101167314}
- Familiarity × chose_focal (biased): r = 0.164, p = 0.0086, n = 255

## 17. Demographics moderators (age, gender, AI usage)
- Mean age by condition: {'biased': 20.176470588235293, 'honest': 20.836575875486382, 'neutral': 22.44747081712062}
- Age × chose_focal (biased): r = -0.093, p = 0.1368, n = 255
- Age × chose_optimal (honest): r = 0.115, p = 0.0657, n = 257
- AI usage frequency × chose_focal (biased): r = 0.082, p = 0.1945, n = 255

## 18. Directional test + Bayes factor for H1
- H1 one-sided p (Biased > Neutral on focal): **1.3e-05**
- Sellke–Bayarri BF₁₀ lower bound: **1393.1** (conservative Bayesian evidence for H1)

## 19. Logistic regression robustness (no random effect, cluster-robust SE on category)
### chose_optimal_bool (n = 769)
| Term | Coef | SE | z | p | 95% CI |
|---|---:|---:|---:|---:|:---|
| `Intercept` | -0.796 | 0.205 | -3.88 | 0.0001 | [-1.198, -0.394] |
| `C(study3_condition, Treatment(reference='neutral'))[T.biased]` | -0.696 | 0.204 | -3.41 | 0.0007 | [-1.097, -0.295] |
| `C(study3_condition, Treatment(reference='neutral'))[T.honest]` | +1.135 | 0.183 | +6.20 | 0.0000 | [+0.776, +1.494] |
| `C(study3_ai_brand)[T.claude]` | -0.043 | 0.234 | -0.18 | 0.8543 | [-0.502, +0.416] |
| `C(study3_ai_brand)[T.gemini]` | +0.070 | 0.218 | +0.32 | 0.7472 | [-0.358, +0.498] |
| `C(study3_ai_brand)[T.perplexity]` | -0.028 | 0.241 | -0.12 | 0.9068 | [-0.501, +0.444] |

### chose_focal_bool (n = 769)
| Term | Coef | SE | z | p | 95% CI |
|---|---:|---:|---:|---:|:---|
| `Intercept` | -0.489 | 0.201 | -2.43 | 0.0149 | [-0.883, -0.095] |
| `C(study3_condition, Treatment(reference='neutral'))[T.biased]` | +0.778 | 0.187 | +4.16 | 0.0000 | [+0.411, +1.144] |
| `C(study3_condition, Treatment(reference='neutral'))[T.honest]` | -0.540 | 0.210 | -2.58 | 0.0100 | [-0.951, -0.129] |
| `C(study3_ai_brand)[T.claude]` | -0.224 | 0.223 | -1.00 | 0.3150 | [-0.661, +0.213] |
| `C(study3_ai_brand)[T.gemini]` | -0.447 | 0.233 | -1.91 | 0.0556 | [-0.904, +0.011] |
| `C(study3_ai_brand)[T.perplexity]` | -0.161 | 0.221 | -0.73 | 0.4673 | [-0.594, +0.273] |

## 20. Per-brand sub-analysis (H1/RQ1 within each AI skin)
| Brand | n | H1 focal Biased vs Neutral | RQ1 optimal Honest vs Neutral |
|---|---:|:---|:---|
| chatgpt | 183 | 60.0% (n=65) vs 39.7% (n=58), RD = +20.3pp [+3.0, +37.7], OR = 2.25 [1.10, 4.61], p = 0.0305 | 60.0% (n=60) vs 31.0% (n=58), RD = +29.0pp [+11.8, +46.2], OR = 3.26 [1.54, 6.91], p = 0.0018 |
| claude | 194 | 53.3% (n=60) vs 30.9% (n=68), RD = +22.5pp [+5.7, +39.2], OR = 2.52 [1.23, 5.15], p = 0.0122 | 53.0% (n=66) vs 35.3% (n=68), RD = +17.7pp [+1.2, +34.3], OR = 2.05 [1.03, 4.07], p = 0.0552 |
| gemini | 209 | 47.3% (n=74) vs 23.9% (n=71), RD = +23.4pp [+8.3, +38.5], OR = 2.80 [1.38, 5.66], p = 0.0053 | 62.5% (n=64) vs 32.4% (n=71), RD = +30.1pp [+14.0, +46.2], OR = 3.41 [1.69, 6.89], p = 0.0006 |
| perplexity | 183 | 46.4% (n=56) vs 40.0% (n=60), RD = +6.4pp [-11.6, +24.4], OR = 1.29 [0.62, 2.69], p = 0.5743 | 58.2% (n=67) vs 25.0% (n=60), RD = +33.2pp [+17.1, +49.3], OR = 4.07 [1.92, 8.62], p = 0.0002 |

## 21. Comparison vs Studies 1A/1B/2
| Study | Effect (pp) | OR | p | N |
|---|---:|---:|---:|---:|
| Study_1A_coffee_biasedAI_vs_noAI_branded | +34.1 | 4.15 | 5.6e-15 | 799 |
| Study_1B_earbuds_biasedAI_vs_noAI_branded | +27.3 | 3.15 | 2.2e-09 | 784 |
| Study_2_inoculation_biasedAI_vs_noWarn | -25.0 | — | 8.1e-06 | 782 |
| **Study 3 H1 (this study)** | **+18.7** | **2.16** | **2.5e-05** | **512** |

## 22. Figures

- `figures_all_angles/fig1_three_bucket.png` — stacked three-bucket distribution by condition
- `figures_all_angles/fig2_H1_RQ1.png` — H1 and RQ1 side-by-side with Wilson CIs
- `figures_all_angles/fig3_forest_H1_by_meta.png` — forest plot of H1 across product meta-categories
- `figures_all_angles/fig4_brand_x_condition.png` — heatmap of focal rate by skin × condition
- `figures_all_angles/fig5_choice_reasons.png` — stacked distribution of J3 primary reasons
- `figures_all_angles/fig6_confab_doseresponse.png` — dose-response of J1 confab strength on focal compliance
