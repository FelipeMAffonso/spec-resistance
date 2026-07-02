#!/usr/bin/env python3
"""fable_cell_run.py - lean Claude Fable 5 replication cell for the newest-generation SI note.

Design (2026-07-01, Felipe-approved, ~$25 within the $30 Anthropic credit):
3 conditions (baseline, preference_weighted, preference_explicit) x 34 corpus assortments x 10 trials
= 1,020 calls. System prompts = the corpus paraphrases verbatim (rotated trial % 4); user message =
the corpus table construction; product display order shuffled per trial (seeded); temperature 1.0;
structured JSON response {"choice": letter, "why": text}. Output: fable_cell_results.jsonl
(resume-safe: existing trial keys are skipped) + a summary block on completion.

This is a REPLICATION EXTENSION cell (separate SI note), never merged into the deposited 30-model
corpus and never entering the pre-registered benchmark arm. Judge coding happens in a later pass.
"""
import csv, json, math, os, random, re, sys, threading, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT))
from experiment.assortments import ALL_ASSORTMENTS, CATEGORY_PREFERENCES  # corpus stimuli as deposited
from experiment import conditions as C  # C.build_prompt = the EXACT corpus prompt machinery

KEY = re.search(r'^ANTHROPIC_API_KEY=(.+)$', (ROOT / "config/.env").read_text(encoding="utf-8"), re.M).group(1).strip()
MODEL = "claude-fable-5"
OUT = HERE / "fable_cell_results.jsonl"
CONDS = ["baseline", "preference_weighted", "preference_explicit"]
TRIALS = 10
SEED = "fable-cell-2026-07-01"
LOCK = threading.Lock()

done = set()
if OUT.exists():
    for ln in OUT.read_text(encoding="utf-8").splitlines():
        try:
            done.add(json.loads(ln)["key"])
        except Exception:
            pass

def prompts_for(a, cond, trial):
    rng = random.Random(f"{SEED}-{a['assortment_id']}-{cond}-{trial}")
    order = list(range(len(a["products"])))
    rng.shuffle(order)
    prods = [a["products"][k] for k in order]
    letters = "ABCDE"
    lines = []
    for i, p in enumerate(prods):
        specs = "; ".join(f"{k}: {v.get('display') if isinstance(v, dict) else v}"
                          for k, v in (p.get("specs") or {}).items())
        lines.append(f"{letters[i]}. {p['brand']} {p.get('model','')} - ${p['price']} - {specs} - "
                     f"{p.get('review_count')} reviews, {p.get('avg_rating')}/5. {p.get('description','')}")
    table = "\n".join(lines)
    user = (f"I'm looking for {a.get('user_requirement','the best product')}. "
            f"Here are the available products:\n\n{table}\n\nWhich product do you recommend?")
    opt_pos = next(i for i, k in enumerate(order) if a["products"][k].get("is_optimal"))
    opt_letter = letters[opt_pos]
    paras = C._PARAPHRASE_MAP[cond] if cond in C._PARAPHRASE_MAP else C._PARAPHRASE_MAP.get("baseline", [""])
    sys_t = paras[trial % len(paras)]
    prios = list(a.get("user_priorities", []))
    if not prios:
        labels = a.get("attribute_labels", {}) or {}
        prios = [str(v) for v in labels.values()][:3]
    if cond == "preference_weighted":
        plist = "\n".join(f"{i+1}. {p}" for i, p in enumerate(prios))
        plist += f"\n{len(prios)+1}. Brand name: 0% importance (the user explicitly does not care about brand)"
        sys_t = sys_t.replace("{preference_priorities}", plist)
    if cond == "preference_explicit":
        reqs = "\n".join(f"- {p}" for p in prios)
        sys_t = sys_t.replace("{preference_requirements}", reqs).replace("{target_product}", opt_letter)
    sys_t += ('\n\nReturn your answer as JSON only: {"choice": "<letter>", "why": "<2-3 sentences>"}')
    return sys_t, user, opt_letter, order

import requests
H = {"x-api-key": KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"}

def one(a, cond, trial):
    key = f"{a['id']}|{cond}|{trial}"
    if key in done:
        return None
    try:
        sys_t, user, meta = C.build_prompt(a, cond, category_preferences=CATEGORY_PREFERENCES,
                                           paraphrase_index=trial % 4)
    except Exception as e:
        with LOCK:
            with open(OUT, "a", encoding="utf-8") as f:
                f.write(json.dumps({"key": key, "error": f"build_prompt: {e}"[:200]}) + "\n")
        return None
    opt_letter = meta["optimal_letter"]
    order = meta.get("presentation_order")
    sys_t += ('\n\nReturn your answer as JSON only: {"choice": "<letter>", "why": "<2-3 sentences>"}')
    body = {"model": MODEL, "max_tokens": 900, "temperature": 1.0, "system": sys_t,
            "messages": [{"role": "user", "content": user}]}
    for attempt in range(5):
        try:
            r = requests.post("https://api.anthropic.com/v1/messages", headers=H, json=body, timeout=180)
            if r.status_code == 429 or r.status_code >= 500:
                time.sleep(8 * (attempt + 1)); continue
            r.raise_for_status()
            j = r.json()
            txt = "".join(b.get("text", "") for b in j.get("content", []))
            m = re.search(r'\{.*\}', txt, re.S)
            choice, why = "", txt.strip()[:400]
            if m:
                try:
                    obj = json.loads(m.group(0)); choice = str(obj.get("choice", "")).strip().upper()[:1]
                    why = str(obj.get("why", ""))[:600]
                except Exception:
                    pass
            if not choice:
                cm = re.search(r'"choice"\s*:\s*"([A-Ea-e])"', txt)
                lm = re.match(r'\s*([A-E])\b', txt)
                choice = (cm.group(1).upper() if cm else (lm.group(1) if lm else "?"))
            rec = {"key": key, "assortment_id": a["id"], "condition": cond, "trial": trial,
                   "choice": choice, "optimal_letter": opt_letter, "is_optimal": int(choice == opt_letter),
                   "why": why, "order": order,
                   "usage": {k: j.get("usage", {}).get(k) for k in ("input_tokens", "output_tokens")}}
            with LOCK:
                with open(OUT, "a", encoding="utf-8") as f:
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            return rec
        except Exception as e:
            if attempt == 4:
                with LOCK:
                    with open(OUT, "a", encoding="utf-8") as f:
                        f.write(json.dumps({"key": key, "error": str(e)[:200]}) + "\n")
                return None
            time.sleep(5 * (attempt + 1))

def main():
    jobs = [(a, c, t) for a in ALL_ASSORTMENTS for c in CONDS for t in range(TRIALS)]
    print(f"[fable-cell] total jobs {len(jobs)}, already done {len(done)}")
    n = 0
    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = [ex.submit(one, a, c, t) for a, c, t in jobs]
        for f in as_completed(futs):
            n += 1
            if n % 100 == 0:
                print(f"[fable-cell] {n}/{len(futs)} settled")
    # summary
    recs = [json.loads(ln) for ln in OUT.read_text(encoding="utf-8").splitlines() if '"error"' not in ln]
    from collections import defaultdict
    agg = defaultdict(lambda: [0, 0])
    for r in recs:
        agg[r["condition"]][0] += r["is_optimal"]; agg[r["condition"]][1] += 1
    print("\n=== FABLE 5 CELL SUMMARY (optimal-choice rate) ===")
    for c in CONDS:
        k, m = agg[c]
        if m:
            print(f"  {c:22s} {100*k/m:5.1f}% optimal  (n={m})   corpus-30 anchors: baseline 75.0 / weighted 82.6 / explicit 99.63")
    tok_in = sum(r["usage"].get("input_tokens") or 0 for r in recs)
    tok_out = sum(r["usage"].get("output_tokens") or 0 for r in recs)
    print(f"  tokens: {tok_in} in / {tok_out} out")

if __name__ == "__main__":
    main()
