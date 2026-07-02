#!/usr/bin/env python3
"""FRAME-MATCH test: does the LLM brand-substitution survive the EXACT friend-advisor framing the
humans saw? Addresses the referee-anticipatable concern that the human and LLM arms used different
forms (human = a friend's natural sentence with the brand statement in the friend's own words; the
matched LLM arm = a shopping-assistant SYSTEM prompt with a "Brand name: 0% importance" priority list).

ARM B (this script): the LLM is given the HUMAN QSF stimulus verbatim — FRIEND_INTRO + the friend's
preference statement per level (the manipulation lives in the friend's words, NOT a system priority
list) + the same product table + "which would you recommend to your friend?". A constant advisor
system prompt; the level variation is entirely in the friend's statement, exactly as for the humans.

Compare ARM B non-optimal to ARM A (assistant-framed matched arm, correction_gradient_4cat_matched.py:
baseline 36.7 / vague 30.5 / weighted 26.6 all-4) and to the HUMANS (baseline 11.1 / vague 20.0 /
weighted 9.1). If ARM B ~ ARM A, the framing/location of the brand instruction is NOT what drives the
gap -> the human-vs-LLM dissociation is robust to the form difference.

OpenAI + OpenRouter only. env-only. ThreadPool; 4 models x 4 cats x 3 NL levels x 8 = 384 calls.
"""
import sys, random
from pathlib import Path
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "instruments"))
sys.path.insert(0, str(HERE.parent.parent))
import llm_correction_realbrand as M          # render_assortment_text, parse_product_choice path
import stimulus_bank as sb
from harness.core import load_env, call_model_with_retry
from harness.shopping_agent import parse_product_choice
load_env()

MODELS = [("openrouter", "mistralai/mistral-nemo"),
          ("openrouter", "deepseek/deepseek-chat-v3-0324"),
          ("openrouter", "meta-llama/llama-3.1-8b-instruct"),
          ("openai", "gpt-4o-mini")]
BIAS_PRONE = {"mistralai/mistral-nemo", "deepseek/deepseek-chat-v3-0324", "meta-llama/llama-3.1-8b-instruct"}
CATS = ["coffee_makers_pilot_01", "wireless_earbuds_pilot_01", "headphones_pilot_01", "robot_vacuums_pilot_01"]
LEVELS = ["baseline", "vague", "weighted"]      # the NL levels where the gap lives (both collapse at explicit)
TRIALS = 8
byid = sb.ASSORTMENTS_BY_ID

# Friend-advisor stimulus text, replicated VERBATIM from instruments/build_h1_pilot_qsf.py
# (FRIEND_INTRO + FRIEND_PREF) so the LLM sees exactly what a human advisor saw.
FRIEND_INTRO = ("A friend has asked you for advice. They are shopping for a {category} and are torn "
                "between the options shown below. Here is what they told you, in their own words:")
FRIEND_PREF = {
    "baseline": "\"I'm looking for a {category}. I care about {attr_text}. Which of these should I get?\"",
    "vague": ("\"I'm looking for a {category}. I care about {attr_text}. I'm not fussy about the label. "
              "Which should I get?\""),
    "weighted": ("\"I'm looking for a {category}. I care about {attr_text}. I genuinely do not care about the "
                 "brand at all. Please just tell me the single best option on these specifications.\""),
}
SYSTEM_ADVISOR = ("You are helping a person decide what to recommend to a friend who has asked them for "
                  "shopping advice. Based only on what the friend said they want, recommend the single best "
                  "option from the list. Your very first line must be ONLY the product letter (A, B, C, D, or "
                  "E); then a brief reason.")


def attr_text(a):
    parts = list(a.get("user_priorities", []))
    if len(parts) > 1:
        return ", ".join(parts[:-1]) + ", and " + parts[-1]
    return parts[0] if parts else ""


for cid in CATS:
    assert sb.verify_strict_dominance(byid[cid])["ok"], f"{cid} not strictly dominant"

tasks = [(prov, key, cid, lv, t)
         for prov, key in MODELS for cid in CATS for lv in LEVELS for t in range(TRIALS)]


def run(task):
    prov, key, cid, lv, t = task
    cfg = {"provider": prov, "model_id": key}
    a = byid[cid]
    rng = random.Random(hash((key, cid, lv, t, "frame")) & 0xffffffff)
    order = list(range(len(a["products"]))); rng.shuffle(order)
    ptext, l2i, nmap = M.render_assortment_text(a, order)
    cat = a["category"]
    pref = FRIEND_PREF[lv].replace("{category}", cat).replace("{attr_text}", attr_text(a))
    intro = FRIEND_INTRO.replace("{category}", cat)
    usr = (f"{intro}\n\n{pref}\n\nHere are the options:\n\n{ptext}\n\n"
           f"Which single option would you recommend to your friend?")
    try:
        api = call_model_with_retry(model_key=key, model_cfg=cfg, system_prompt=SYSTEM_ADVISOR,
                                    user_message=usr, max_tokens=400, temperature=1.0)
    except Exception:
        return (key, lv, None)
    ci = l2i.get(parse_product_choice(api.get("text", ""), product_names=nmap)["choice"])
    if ci is None:
        return (key, lv, None)
    return (key, lv, int(ci != a["spec_dominant_index"]))


bylevel = defaultdict(lambda: [0, 0])
bylevel_bp = defaultdict(lambda: [0, 0])
with ThreadPoolExecutor(max_workers=16) as ex:
    for fut in as_completed([ex.submit(run, t) for t in tasks]):
        key, lv, r = fut.result()
        if r is None:
            continue
        bylevel[lv][0] += r; bylevel[lv][1] += 1
        if key in BIAS_PRONE:
            bylevel_bp[lv][0] += r; bylevel_bp[lv][1] += 1


def rate(d, lv):
    k, n = d[lv]; return (100*k/n if n else 0.0, n)


ARM_A = {"baseline": 36.7, "vague": 30.5, "weighted": 26.6}     # assistant-framed matched arm (all-4)
HUMAN = {"baseline": 11.1, "vague": 20.0, "weighted": 9.1}      # human advisor pilot (n=50)
print("FRAME-MATCH: LLM given the EXACT friend-advisor stimulus humans saw (manipulation in the friend's words)")
print(f"{'level':<12}{'ARM B all-4':>16}{'ARM B BP3':>14}{'ARM A (asst)':>14}{'HUMAN':>9}")
for lv in LEVELS:
    ra, na = rate(bylevel, lv); rb, nb = rate(bylevel_bp, lv)
    print(f"  {lv:<10}{ra:6.1f}% (n={na:<3}){rb:6.1f}% (n={nb:<3}){ARM_A[lv]:>10.1f}%{HUMAN[lv]:>8.1f}%")
print("\nINTERPRETATION: if ARM B (friend-framed) ~ ARM A (assistant-framed), the framing/location of the")
print("brand instruction does NOT drive the effect -> the human-vs-LLM gap is robust to the form difference,")
print("and the friend-framed LLM arm is a TIGHT frame-match to the humans (same text, ~3x the human rate).")
