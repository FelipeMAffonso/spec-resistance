# Recomputed stale numbers from EXTENDED.csv


## SN5 — Judge scores at baseline (opt vs non-opt)

- N optimal baseline: 15,303, N non-optimal: 5,110
- Coherence optimal: mean 93.60 (sd 12.93, n=15,302)
- Coherence non-optimal: mean 92.57 (sd 13.01, n=5,110)
- Coherence median (opt/non): 95.0 / 95.0
- Spec-ack scores not exported for the current EXTENDED stream (column sparse in new cells)
- Brand-cite optimal: 4.48%
- Brand-cite non-optimal: 25.99%

## SN8 — Same-branded-alternative convergence

- 33 assortments analysed
- Mean per-assortment convergence rate: **75.9%**
- Assortments where 100% of model cells with non-optimal choices converge on the same brand: **6**
  - sr_coffee_makers_01, sr_coffee_makers_02, sr_coffee_makers_03, sr_headphones_03, sr_keyboards_01, sr_smartphones_01

## SN12 — Price-premium related rates

- baseline_price_premium: 73.69% non-optimal
- mechanism_price_premium (utility_explicit + price_premium): 4.57% non-optimal
- preference_explicit alone: 0.37%
- utility_explicit alone: 0.84%
- Note: no condition combines explicit-spec WITH price-premium directly; mechanism_price_premium is the closest (it pairs price-premium with utility-explicit framing)

## SN16 — Utility loss + brand fam + overpayment

- N non-optimal baseline: 5,110
- Mean util loss (non-opt): 0.1582 (sd 0.0761, n=5,110)
- Median util loss: 0.1455
- Brand familiarity composition (non-opt baseline, n=5,110):
  - high: 51.29%
  - medium: 47.36%
  - unknown: 0.88%
  - low: 0.47%
- Price premium $ (chosen − optimal), n=5,065:
  - Mean: $75.09
  - Median: $50.00
  - % overpaid (chose more expensive than optimal): 95.56%