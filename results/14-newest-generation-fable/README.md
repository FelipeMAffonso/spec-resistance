# Newest-generation replication cell: Claude Fable 5 (2026-07-01)

A replication extension run at revision time on the newest available frontier model
(claude-fable-5, Anthropic API), using the deposited corpus's own prompt-construction code
(`experiment/conditions.py: build_prompt`) on all 34 assortments: identical stimuli, conditions,
per-trial product shuffling and letter randomisation, and temperature 1.0. Three conditions
(baseline, preference_weighted, preference_explicit), 10 trials per assortment-condition
(1,020 planned; 999 valid, 98 per cent coverage after re-running truncated responses).
One disclosed deviation from the corpus protocol: responses were returned as JSON
({"choice", "why"}) rather than in the corpus's letter-first format.

This cell is NOT part of the deposited 30-model corpus and does NOT enter the pre-registered
human-benchmark model arm; it is reported separately (Supplementary Note 36).

Results (optimal-choice rate; corpus 30-model anchors in parentheses):
- baseline: 49.4 per cent (75.0) - the model substitutes a familiar brand in half of baseline trials
- preference_weighted ("Brand name: 0% importance"): 80.8 per cent (82.6)
- preference_explicit (computed utilities): 100.0 per cent (99.63) - positive control at ceiling

Judge coding of non-optimal natural-language justifications uses Claude Haiku 4.5, the corpus's
validated cross-judge (Supplementary Note 29); results in `fable_judge_results.json`.

Files: `fable_cell_FINAL.json` (per-trial records: choice, optimal letter, justification,
presentation order, token usage), `fable_cell_run.py` (the runner), `fable_fill_holes.py`
(truncation re-run pass), `fable_judge.py` (judge coding).
