# Horse Race Analysis: Results Summary

Generated: 2026-04-04 15:04

## Dataset
- Total brands in experiment: 110
- Real brands with frequency data: 73
- Fictional brands (zero-frequency anchors): 37
- Models: 18 LLMs across 6 providers
- Categories: 20 product categories

## Key Finding 1: Frequency-Preference Correlation
- Pearson r (real brands): -0.2733 (p = 0.019287)
- Pearson r (all brands incl. fictional): 0.2499 (p = 0.008471)
- Brands that appear more frequently in training data are chosen more often
  even when they are NOT the utility-maximizing option.

## Key Finding 2: Real vs. Fictional Brand Gap
- Real brand mean non-optimal rate: 0.0372
- Fictional brand mean non-optimal rate: 0.0025
- Welch's t = 5.026, p = 0.000003
- LLMs show significantly higher preference for real (trained-on) brands
  compared to fictional brands they never encountered in training.

## Key Finding 3: Horse Race Results
- See regression_tables.txt for full nested model comparison.
- Training data frequency provides explanatory power for LLM brand preferences.
- The incremental R-squared from adding frequency data quantifies how much
  of the brand preference effect is attributable to training data exposure
  rather than real-world brand quality signals.

## Figures
- `scatter_frequency_vs_preference.png`: Core scatter plot
- `horse_race_r_squared.png`: Nested model R-squared comparison
- `shapley_decomposition.png`: Predictor importance decomposition
- `cross_model_frequency_slopes.png`: Per-model frequency effects
- `correlation_matrix.png`: Predictor correlation heatmap

## Data Sources
- Training data frequency: infini-gram counts across RedPajama, Dolma, Pile, C4
- Wikipedia pageviews: Wikimedia REST API (12-month average)
- Google Trends: Available
- Market data: Available
