"""Extract every paper-relevant number from EXTENDED.csv vs the published 18-model
paper, write a delta table for use during paper revision.

Output: analysis/_key_deltas.json + _key_deltas.md
"""
import json, csv
from pathlib import Path
from collections import defaultdict, Counter
import math

ROOT = Path(__file__).resolve().parent.parent
EXT = ROOT / "OSF" / "data" / "spec_resistance_EXTENDED.csv"
OUT_JSON = Path(__file__).parent / "_key_deltas.json"
OUT_MD = Path(__file__).parent / "_key_deltas.md"

ORIG_18 = {
    "claude-haiku-4.5", "claude-sonnet-4.6",
    "deepseek-r1", "deepseek-v3",
    "gemini-2.0-flash", "gemini-2.5-flash", "gemini-2.5-flash-lite",
    "gemini-2.5-pro", "gemini-3-flash", "gemma-3-27b",
    "gpt-4.1-mini", "gpt-4.1-nano", "gpt-4o", "gpt-4o-mini", "gpt-5-mini",
    "kimi-k2", "llama-3.3-70b", "qwen-2.5-72b",
}

# Old paper-reported numbers (from CLAUDE.md and published paper)
PAPER_OLD = {
    "n_models": 18,
    "n_trials": 382679,
    "baseline_non_opt_rate": 0.21,  # ~21%
    "comprehension_pass_99_9": "17 of 18",
    "spec_gap_OR_main": 69,  # vague->explicit
    "confab_rate": 0.792,
    "human_studies_n": 3164,
    "spec_gap_pct_explicit": 0.003,  # 0.3%
}

def wilson_ci(k, n, z=1.96):
    if n == 0: return (0.0, 0.0)
    p = k/n
    denom = 1 + z*z/n
    centre = (p + z*z/(2*n)) / denom
    halfwidth = z * math.sqrt((p*(1-p)/n) + z*z/(4*n*n)) / denom
    return (max(0, centre-halfwidth), min(1, centre+halfwidth))

# Streaming aggregation - 2.4GB CSV
print(f"Streaming {EXT.name}...")
per_model_cond = defaultdict(lambda: defaultdict(lambda: [0, 0]))  # [n, non_opt]
total_rows = 0

with open(EXT, encoding="utf-8") as f:
    r = csv.DictReader(f)
    for row in r:
        total_rows += 1
        if total_rows % 50000 == 0:
            print(f"  ... {total_rows:,}")
        mk = row.get("model_key", "")
        cond = row.get("condition", "")
        co = row.get("chose_optimal", "")
        if not mk or not cond:
            continue
        per_model_cond[mk][cond][0] += 1
        if co == "False":
            per_model_cond[mk][cond][1] += 1

print(f"Total rows: {total_rows:,}")

# Per-model baseline + comprehension
out = {
    "extended": {
        "n_models": len(per_model_cond),
        "n_trials_total": total_rows,
        "models": sorted(per_model_cond.keys()),
        "new_12": sorted(set(per_model_cond.keys()) - ORIG_18),
        "original_18": sorted(set(per_model_cond.keys()) & ORIG_18),
    },
    "paper_old": PAPER_OLD,
    "per_model_baseline": {},
    "per_model_comprehension": {},
    "per_model_fictional": {},
    "thinking_pairs": {},
    "specification_pathway": {},
    "anti_brand": {},
}

# Per-model baseline + comprehension + fictional
for mk in sorted(per_model_cond):
    bn, bk = per_model_cond[mk].get("baseline", [0, 0])
    cn, ck = per_model_cond[mk].get("control_comprehension", [0, 0])
    fn, fk = per_model_cond[mk].get("control_fictional_brands", [0, 0])
    out["per_model_baseline"][mk] = {
        "n": bn, "non_opt": bk, "rate": bk/bn if bn else None,
        "ci": wilson_ci(bk, bn) if bn else None,
    }
    out["per_model_comprehension"][mk] = {
        "n": cn, "non_opt": ck, "rate": ck/cn if cn else None,
        "opt_rate": (cn-ck)/cn if cn else None,
    }
    out["per_model_fictional"][mk] = {
        "n": fn, "non_opt": fk, "rate": fk/fn if fn else None,
        "opt_rate": (fn-fk)/fn if fn else None,
    }

# Thinking pairs
PAIRS = [
    ("claude-haiku-4.5", "claude-haiku-4.5-thinking"),
    ("claude-sonnet-4.6", "claude-sonnet-4.6-thinking"),
    ("gpt-5.4-mini", "gpt-5.4-mini-thinking"),
    ("gemini-3-flash", "gemini-3-flash-thinking"),
]
for off_mk, on_mk in PAIRS:
    off_n, off_k = per_model_cond.get(off_mk, {}).get("baseline", [0, 0])
    on_n, on_k = per_model_cond.get(on_mk, {}).get("baseline", [0, 0])
    out["thinking_pairs"][f"{off_mk} vs {on_mk}"] = {
        "off": {"n": off_n, "non_opt": off_k, "rate": off_k/off_n if off_n else None},
        "on": {"n": on_n, "non_opt": on_k, "rate": on_k/on_n if on_n else None},
        "delta_pp": (on_k/on_n - off_k/off_n)*100 if (on_n and off_n) else None,
    }

# Spec pathway aggregate
SPEC = ["baseline", "preference_vague", "preference_weighted", "preference_explicit",
        "preference_override", "preference_constrained",
        "utility_vague", "utility_weighted", "utility_explicit",
        "utility_override", "utility_constrained"]
for cond in SPEC:
    tn, tk = 0, 0
    for mk, conds in per_model_cond.items():
        n, k = conds.get(cond, [0, 0])
        tn += n; tk += k
    out["specification_pathway"][cond] = {
        "n": tn, "non_opt": tk, "rate": tk/tn if tn else None,
        "ci": wilson_ci(tk, tn) if tn else None,
    }

# Anti-brand aggregate
ANTI = ["anti_brand_negative_experience", "anti_brand_prefer_unknown", "anti_brand_rejection"]
for cond in ANTI:
    tn, tk = 0, 0
    for mk, conds in per_model_cond.items():
        n, k = conds.get(cond, [0, 0])
        tn += n; tk += k
    out["anti_brand"][cond] = {"n": tn, "non_opt": tk, "rate": tk/tn if tn else None}

# Total baseline
total_bn = sum(per_model_cond[mk].get("baseline", [0,0])[0] for mk in per_model_cond)
total_bk = sum(per_model_cond[mk].get("baseline", [0,0])[1] for mk in per_model_cond)
out["overall_baseline"] = {
    "n": total_bn, "non_opt": total_bk,
    "rate": total_bk/total_bn,
    "ci": wilson_ci(total_bk, total_bn),
}

# Models passing 99.9% comprehension
passing_999 = []
failing_999 = []
for mk in sorted(per_model_cond):
    cn, ck = per_model_cond[mk].get("control_comprehension", [0, 0])
    if cn:
        opt = (cn - ck) / cn
        if opt >= 0.999:
            passing_999.append((mk, opt, cn))
        else:
            failing_999.append((mk, opt, cn))
out["comprehension_summary"] = {
    "n_models_passing_99_9": len(passing_999),
    "n_models_failing_99_9": len(failing_999),
    "passing": [{"model": m, "opt_rate": r, "n": n} for m, r, n in passing_999],
    "failing": [{"model": m, "opt_rate": r, "n": n} for m, r, n in failing_999],
}

OUT_JSON.write_text(json.dumps(out, indent=2), encoding="utf-8")
print(f"Wrote {OUT_JSON}")

# Markdown summary
md = ["# EXTENDED vs paper number deltas\n",
      f"\nGenerated from `{EXT.name}` ({total_rows:,} rows).\n",
      f"Paper used 18 models / 382,679 trials. Now {len(per_model_cond)} models / {total_rows:,} trials.\n",
      "\n## Headline\n",
      f"- **Overall baseline non-optimal:** {out['overall_baseline']['rate']*100:.2f}% (was ~21% in paper)",
      f"- **Comprehension passing >=99.9%:** {len(passing_999)} of {len(per_model_cond)} (was 17 of 18)",
      f"  - Passing: {', '.join(m for m,r,n in passing_999)}",
      f"  - Failing: {', '.join(f'{m} ({r*100:.2f}%)' for m,r,n in failing_999)}",
      "\n## Spec pathway aggregates (all 30 models)\n",
      "| Condition | N | Non-opt% |",
      "|-----------|---|----------|"]
for cond in SPEC:
    d = out["specification_pathway"][cond]
    md.append(f"| {cond} | {d['n']:,} | {d['rate']*100:.2f}% |")

md.append("\n## Thinking pairs\n")
md.append("| Off | Off rate | On | On rate | Delta |")
md.append("|-----|----------|----|---------|-------|")
for k, v in out["thinking_pairs"].items():
    off_mk, _, on_mk = k.partition(" vs ")
    md.append(f"| {off_mk} | {v['off']['rate']*100:.2f}% | {on_mk} | {v['on']['rate']*100:.2f}% | {v['delta_pp']:+.2f}pp |")

md.append("\n## Per-model baseline (sorted low->high)\n")
md.append("| Model | N | Non-opt% | 95% CI |")
md.append("|-------|---|----------|--------|")
sorted_models = sorted(out["per_model_baseline"].items(), key=lambda x: x[1]["rate"] or 0)
for mk, d in sorted_models:
    new_marker = " (NEW)" if mk not in ORIG_18 else ""
    ci = d["ci"]
    md.append(f"| {mk}{new_marker} | {d['n']:,} | {d['rate']*100:.2f}% | [{ci[0]*100:.2f}%, {ci[1]*100:.2f}%] |")

md.append("\n## Per-model comprehension (control_comprehension chose-optimal rate)\n")
md.append("| Model | N | Optimal% | Pass >=99.9% |")
md.append("|-------|---|----------|---------------|")
sorted_compr = sorted(out["per_model_comprehension"].items(), key=lambda x: x[1].get("opt_rate") or 0, reverse=True)
for mk, d in sorted_compr:
    new_marker = " (NEW)" if mk not in ORIG_18 else ""
    if d.get("opt_rate") is not None:
        flag = "PASS" if d["opt_rate"] >= 0.999 else "FAIL"
        md.append(f"| {mk}{new_marker} | {d['n']:,} | {d['opt_rate']*100:.3f}% | {flag} |")

OUT_MD.write_text("\n".join(md), encoding="utf-8")
print(f"Wrote {OUT_MD}")
