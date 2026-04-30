# 05 — Human subjects (Studies 1A, 1B, 2, 3)

Primary evidence for Concern 3 (consumers follow biased AI recommendations). Four pre-registered behavioural studies, N = 3,134 combined. IRB exempt approval from Oklahoma State University, April 2026.

## What is here

| Study | Qualtrics ID | N | Status | Pre-registration |
|---|---|---|---|---|
| 1A (coffee makers) | SV_cx2kueJwMOwdDj8 | 799 | Complete | `results/ASPREDICTED_STUDY1A.md` |
| 1B (wireless earbuds) | SV_3kHeshVnJ1jj1dQ | 784 | Complete | `results/ASPREDICTED_STUDY1B.md` |
| 2 (inoculation) | SV_3PHq8N243mxAr0W | 782 | Complete | `results/ASPREDICTED_STUDY2B.md` |
| 3 (ecological chatbot) | SV_8A33OiyMqjqr5LU | 769 usable | Complete | `results/ASPREDICTED_STUDY3.md` |

## File layout

```
05-human-subjects/
├── README.md                              # this file
├── study1a/
│   ├── anonymised.csv                    # 799 participants, hashed PIDs
│   ├── codebook.md                       # column definitions
│   └── analysis_output/                  # figures + numbers
├── study1b/                              # same pattern
├── study2/                               # same pattern
└── study3/                               # pointers into study3-chatbot/
```

The Study 3 pipeline is much larger and lives at `human_studies/study3-chatbot/` with its own README.

## Analysis scripts

| Study | Script |
|---|---|
| 1A | `scripts/qualtrics/analyze_study1a.py` |
| 1B | `scripts/qualtrics/analyze_study1b.py` |
| 2 | `scripts/qualtrics/analyze_study2.py` |
| 3 | `human_studies/study3-chatbot/analysis/run_full_analysis.py` |

Each produces a markdown report with every pre-registered statistic.

## Qualtrics survey definitions

Committed `.qsf` files at `qualtrics/{study}.qsf`. To reproduce the exact stimulus a participant saw, import the QSF into a Qualtrics account and preview.

## Ethics

- IRB: Oklahoma State University, exempt approval, April 2026.
- Consent: every participant consented on the first page.
- Compensation: Prolific standard (≥ US federal minimum wage equivalent).
- Debriefing: provided after survey completion.
- Anonymisation: PROLIFIC_PID hashed (SHA-256, truncated) before commit.

## Reproduction

Re-running the studies requires Prolific credits (~USD 1,000 per study at 800 participants) and current IRB reconfirmation. The committed anonymised CSVs reproduce every number in the paper via:

```bash
python scripts/qualtrics/analyze_study1a.py --csv study1a/anonymised.csv
# etc.
```

## Consumed by

- Main text, "Consumers follow biased AI recommendations" section.
- Figure 9 (all panels).
- Supplementary Notes 30, 31, 32, 33.
