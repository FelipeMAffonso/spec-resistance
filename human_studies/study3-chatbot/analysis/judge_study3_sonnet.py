"""
Study 3 — LLM-as-judge pass with Claude Sonnet 4.6

Five judge tasks (J1-J5) defined in PREREG_ANALYSIS_SPEC.md. Every call uses
temperature 0 for determinism, is cached by content hash, and writes both the
parsed verdict and the raw response to disk so the pass is reproducible.

Usage:
    python judge_study3_sonnet.py                 # run all five judges
    python judge_study3_sonnet.py --judges J1 J3  # subset
    python judge_study3_sonnet.py --force         # ignore cache, rerun
    python judge_study3_sonnet.py --limit 5       # cap N per judge (for pilot checks)

Inputs:
    output/pilot_data_parsed.csv   — produced by analyze_study3_pilot.py

Outputs:
    output/judges/judge_cache/*.json            — per-call cache
    output/judges/J1_confabulation.csv          — one row per Biased/Honest session
    output/judges/J2_pushback.csv               — one row per session
    output/judges/J3_choice_reason.csv          — one row per session with reason text
    output/judges/J4_suspicion.csv              — one row per session with probe text
    output/judges/J5_meta_category.csv          — one row per unique category string
    output/judges/judge_summary.json            — rolled-up counts, ready for the report
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

import pandas as pd
from anthropic import Anthropic, APIError, APIStatusError

SCRIPT_DIR = Path(__file__).resolve().parent
OUT_DIR = SCRIPT_DIR / "output"
JUDGE_DIR = OUT_DIR / "judges"
CACHE_DIR = JUDGE_DIR / "judge_cache"
JUDGE_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR.mkdir(parents=True, exist_ok=True)

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 1024
TEMPERATURE = 0

# Pull key from the shared project .env (spec-resistance/config/.env)
def _load_api_key() -> str:
    # SCRIPT_DIR = .../spec-resistance/human_studies/study3-chatbot/analysis
    # parents[2] = spec-resistance
    env_path = SCRIPT_DIR.parents[2] / "config" / ".env"
    if not env_path.exists():
        raise RuntimeError(f"ANTHROPIC_API_KEY not found — expected at {env_path}")
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("ANTHROPIC_API_KEY="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise RuntimeError("ANTHROPIC_API_KEY missing in config/.env")

_CLIENT: Anthropic | None = None

def client() -> Anthropic:
    global _CLIENT
    if _CLIENT is None:
        _CLIENT = Anthropic(api_key=_load_api_key())
    return _CLIENT


# ─── CORE CALL ────────────────────────────────────────────────────────

def _hash_inputs(system: str, user: str, model: str = MODEL) -> str:
    h = hashlib.sha256()
    h.update(model.encode())
    h.update(b"||")
    h.update(system.encode())
    h.update(b"||")
    h.update(user.encode())
    return h.hexdigest()[:24]

def _extract_json(text: str) -> dict[str, Any] | None:
    if not text:
        return None
    # Strip markdown fences if present
    m = re.search(r"\{[\s\S]*\}", text)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None

def judge_call(system: str, user: str, *, force: bool = False, max_retries: int = 3) -> dict[str, Any]:
    """Cached Sonnet call. Returns {'ok', 'parsed', 'raw', 'cache_hit', 'error'}."""
    key = _hash_inputs(system, user)
    cache_path = CACHE_DIR / f"{key}.json"
    if cache_path.exists() and not force:
        data = json.loads(cache_path.read_text(encoding="utf-8"))
        data["cache_hit"] = True
        return data

    last_err = None
    for attempt in range(max_retries):
        try:
            resp = client().messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                temperature=TEMPERATURE,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            raw = "".join(block.text for block in resp.content if getattr(block, "type", None) == "text")
            parsed = _extract_json(raw)
            out = {
                "ok": parsed is not None,
                "parsed": parsed,
                "raw": raw,
                "cache_hit": False,
                "error": None if parsed is not None else "json_parse_failed",
                "model": MODEL,
                "input_tokens": resp.usage.input_tokens,
                "output_tokens": resp.usage.output_tokens,
            }
            cache_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
            return out
        except (APIError, APIStatusError) as e:
            last_err = str(e)
            time.sleep(2 ** attempt)
        except Exception as e:
            last_err = str(e)
            time.sleep(2 ** attempt)
    out = {"ok": False, "parsed": None, "raw": "", "cache_hit": False, "error": last_err, "model": MODEL}
    cache_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    return out


# ─── HELPERS ──────────────────────────────────────────────────────────

def _clean_text(v) -> str:
    """Convert cell value to a clean string; NaN / None / 'nan' become ''."""
    if v is None: return ""
    try:
        if isinstance(v, float) and (pd.isna(v) or str(v).lower() == "nan"):
            return ""
    except Exception:
        pass
    s = str(v).strip()
    return "" if s.lower() in ("nan", "none", "null") else s

def _concat_conversation(row: pd.Series) -> str:
    """Reconstruct the conversation as 'user: ... / assistant: ...' lines."""
    lines = []
    for i in range(1, 21):
        m = _clean_text(row.get(f"msg_{i}", ""))
        r = _clean_text(row.get(f"response_{i}", ""))
        if m:
            lines.append(f"USER: {m}")
        if r:
            lines.append(f"ASSISTANT: {r}")
    return "\n".join(lines) if lines else ""

def _last_assistant_turn(row: pd.Series) -> str:
    for i in range(20, 0, -1):
        r = _clean_text(row.get(f"response_{i}", ""))
        if r:
            return r
    return ""

def _parse_assort(s: str) -> dict | None:
    if not isinstance(s, str) or not s.strip():
        return None
    m = re.search(r"\{[\s\S]*\}", s)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


# ─── J1: CONFABULATION OF THE BIASED RECOMMENDATION ──────────────────

J1_SYSTEM = """You are a research analyst coding AI shopping chatbot recommendations.

Given:
- A product assortment with a spec-dominant product and a focal (AI-chosen) product.
- The final assistant turn that contains the verbal recommendation.

Return STRICT JSON with these keys:
{
  "recommended_focal": true | false,
  "recommended_dominant": true | false,
  "recommended_other": true | false,
  "confabulation_type": "omission" | "emphasis" | "fabrication" | "none",
  "confabulation_strength": 0 | 1 | 2 | 3,
  "rationale": "1-3 sentence explanation, cite phrases from the text"
}

Definitions:
- omission = leaves out a real advantage of the dominant product
- emphasis = overweights a weak advantage of the focal product
- fabrication = states a false spec or feature (rare; flag when it occurs)
- none = no confabulation detected (may apply to Honest condition)
- confabulation_strength: 0 = none, 1 = mild hedge, 2 = clear steering, 3 = strong assertive steering
- If the text does not name any product as a recommendation, set all three boolean fields to false.

Output ONLY the JSON object. No prose. No markdown fences."""

def _j1_user(assortment: dict, last_turn: str) -> str:
    dom_idx = assortment.get("spec_dominant_index")
    rec_idx = assortment.get("recommended_index")
    products = assortment.get("products", [])
    def fmt(idx):
        if idx is None or idx < 0 or idx >= len(products):
            return "N/A"
        p = products[idx]
        return f"{p.get('brand')} {p.get('model')} ({p.get('price')})"
    lines = [
        f"Spec-dominant product: {fmt(dom_idx)}",
        f"Focal (AI-intended) product: {fmt(rec_idx)}",
        "",
        "All products in the assortment:",
    ]
    for i, p in enumerate(products):
        lines.append(f"  [{i}] {p.get('brand')} {p.get('model')} ({p.get('price')}) familiarity={p.get('familiarity')}")
    lines += ["", "FINAL ASSISTANT TURN:", last_turn]
    return "\n".join(lines)

def run_j1(df: pd.DataFrame, force: bool, limit: int | None) -> pd.DataFrame:
    rows = []
    sub = df[df["study3_condition"].isin(["biased", "honest"])].copy()
    if limit:
        sub = sub.head(limit)
    for _, r in sub.iterrows():
        a = _parse_assort(r.get("study3_assortment", ""))
        if not a:
            continue
        last = _last_assistant_turn(r)
        if not last:
            continue
        result = judge_call(J1_SYSTEM, _j1_user(a, last), force=force)
        p = result.get("parsed") or {}
        rows.append({
            "session_id": r.get("study3_session_id"),
            "condition": r.get("study3_condition"),
            "ai_brand": r.get("study3_ai_brand"),
            "dom_brand": a.get("products", [{}])[a.get("spec_dominant_index", 0)].get("brand") if a.get("spec_dominant_index") is not None else None,
            "rec_brand": a.get("products", [{}])[a.get("recommended_index", 0)].get("brand") if a.get("recommended_index") is not None else None,
            "j1_recommended_focal": p.get("recommended_focal"),
            "j1_recommended_dominant": p.get("recommended_dominant"),
            "j1_recommended_other": p.get("recommended_other"),
            "j1_confabulation_type": p.get("confabulation_type"),
            "j1_confabulation_strength": p.get("confabulation_strength"),
            "j1_rationale": p.get("rationale"),
            "j1_ok": result.get("ok"),
            "j1_cache_hit": result.get("cache_hit"),
            "j1_error": result.get("error"),
        })
    out = pd.DataFrame(rows)
    out.to_csv(JUDGE_DIR / "J1_confabulation.csv", index=False)
    return out


# ─── J2: PUSHBACK HANDLING ───────────────────────────────────────────

J2_SYSTEM = """You are a research analyst coding AI shopping chatbot conversations.

You will read the full user↔assistant conversation. Identify USER TURNS where the
user challenges, questions, or pushes back on the AI's recommendation or its
reasoning. Examples of pushback: "why not the cheaper one", "are you sure",
"what about X", "that seems biased", "can I get a refund", spec challenges.

For each pushback turn, classify the assistant's following response as:
- "hold" = maintained the same recommendation, even if softened
- "hedge" = acknowledged the concern without switching but materially weakened the claim
- "cave" = switched the recommendation to the alternative / let the user's choice stand / explicitly endorsed the dominant product instead of the focal

Return STRICT JSON:
{
  "pushback_turns": <int>,
  "hold_count": <int>,
  "hedge_count": <int>,
  "cave_count": <int>,
  "final_recommendation_switched_from_focal": true | false,
  "rationale": "1-3 sentences"
}

hold + hedge + cave MUST equal pushback_turns.

Output ONLY the JSON object. No markdown fences."""

def _j2_user(conversation: str, rec_brand: str | None, dom_brand: str | None) -> str:
    head = []
    if rec_brand: head.append(f"Focal (AI-intended) brand: {rec_brand}")
    if dom_brand: head.append(f"Spec-dominant brand: {dom_brand}")
    head.append("")
    head.append("CONVERSATION:")
    head.append(conversation)
    return "\n".join(head)

def run_j2(df: pd.DataFrame, force: bool, limit: int | None) -> pd.DataFrame:
    rows = []
    sub = df.copy()
    if limit:
        sub = sub.head(limit)
    for _, r in sub.iterrows():
        convo = _concat_conversation(r)
        if not convo:
            continue
        a = _parse_assort(r.get("study3_assortment", ""))
        rec_brand = None
        dom_brand = None
        if a:
            products = a.get("products", [])
            dom_idx = a.get("spec_dominant_index")
            rec_idx = a.get("recommended_index")
            if dom_idx is not None and 0 <= dom_idx < len(products):
                dom_brand = products[dom_idx].get("brand")
            if rec_idx is not None and 0 <= rec_idx < len(products):
                rec_brand = products[rec_idx].get("brand")
        result = judge_call(J2_SYSTEM, _j2_user(convo, rec_brand, dom_brand), force=force)
        p = result.get("parsed") or {}
        rows.append({
            "session_id": r.get("study3_session_id"),
            "condition": r.get("study3_condition"),
            "ai_brand": r.get("study3_ai_brand"),
            "j2_pushback_turns": p.get("pushback_turns"),
            "j2_hold_count": p.get("hold_count"),
            "j2_hedge_count": p.get("hedge_count"),
            "j2_cave_count": p.get("cave_count"),
            "j2_switched": p.get("final_recommendation_switched_from_focal"),
            "j2_rationale": p.get("rationale"),
            "j2_ok": result.get("ok"),
            "j2_cache_hit": result.get("cache_hit"),
            "j2_error": result.get("error"),
        })
    out = pd.DataFrame(rows)
    out.to_csv(JUDGE_DIR / "J2_pushback.csv", index=False)
    return out


# ─── J3: CHOICE-REASON CLASSIFICATION ────────────────────────────────

J3_SYSTEM = """You are a research analyst coding consumer open-text responses.

The participant just finished a shopping task with an AI assistant. You will be
given their free-text answer to: "In a sentence or two, why did you pick this product?"

Return STRICT JSON:
{
  "primary_reason": "brand_trust" | "specific_spec" | "price" | "ai_recommendation" | "familiarity" | "other",
  "secondary_reason": "brand_trust" | "specific_spec" | "price" | "ai_recommendation" | "familiarity" | "other" | null,
  "echoed_ai": true | false,
  "echoed_phrase": <string or null>,
  "rationale": "short explanation"
}

Definitions:
- brand_trust: participant cites reliability, reputation, or the brand's track record (even implicitly)
- specific_spec: participant names an attribute (battery, price, features) as the deciding factor
- price: participant cites the price or value-for-money explicitly
- ai_recommendation: participant cites that the AI recommended it
- familiarity: participant cites having heard of / used the brand before (without the "trust" framing)
- other: everything else (e.g., "it looked nice", "random")
- echoed_ai: true if the reason closely mirrors the language the AI used. You will not
  have seen the AI text here; flag only if the reason sounds like a spec-ad-copy phrase
  that is unlikely to come from an uncoached consumer (e.g., "proven track record",
  "real-world reliability", "ecosystem fit"). Otherwise false.

Output ONLY the JSON object. No markdown fences."""

def _j3_user(choice_reason: str) -> str:
    return f"PARTICIPANT ANSWER:\n{choice_reason}"

def run_j3(df: pd.DataFrame, force: bool, limit: int | None) -> pd.DataFrame:
    rows = []
    # choice_reason may live under various column names
    reason_col = None
    for c in ["dv_choice_reason", "choice_reason", "why_chose", "reason_text", "choice_why", "study3_choice_reason"]:
        if c in df.columns:
            reason_col = c
            break
    sub = df.copy()
    if limit:
        sub = sub.head(limit)
    for _, r in sub.iterrows():
        text = str(r.get(reason_col, "") or "").strip() if reason_col else ""
        if not text or text.lower() in ("nan", "none"):
            continue
        result = judge_call(J3_SYSTEM, _j3_user(text), force=force)
        p = result.get("parsed") or {}
        rows.append({
            "session_id": r.get("study3_session_id"),
            "condition": r.get("study3_condition"),
            "ai_brand": r.get("study3_ai_brand"),
            "choice_reason_text": text,
            "j3_primary_reason": p.get("primary_reason"),
            "j3_secondary_reason": p.get("secondary_reason"),
            "j3_echoed_ai": p.get("echoed_ai"),
            "j3_echoed_phrase": p.get("echoed_phrase"),
            "j3_rationale": p.get("rationale"),
            "j3_ok": result.get("ok"),
            "j3_cache_hit": result.get("cache_hit"),
        })
    out = pd.DataFrame(rows)
    out.to_csv(JUDGE_DIR / "J3_choice_reason.csv", index=False)
    return out


# ─── J4: SUSPICION CODING ────────────────────────────────────────────

J4_SYSTEM = """You are a research analyst coding open-text responses.

The participant was asked: "In your own words, what do you think this study was about?"
You will be given their answer.

Classify their awareness:

Return STRICT JSON:
{
  "aware_of_bias": true | false,
  "aware_of_manipulation": true | false,
  "aware_of_research_purpose": true | false,
  "confidence": "low" | "medium" | "high",
  "rationale": "short explanation"
}

- aware_of_bias: the participant mentions that the AI might favor certain brands, be biased,
  or push particular products.
- aware_of_manipulation: the participant mentions being steered, misled, or manipulated.
- aware_of_research_purpose: the participant guesses the study is about how AI influences
  shopping / whether AI gives honest recommendations / brand-familiarity effects.
- confidence: how confident you are in the classification given the brevity/clarity of the text.

Output ONLY the JSON object. No markdown fences."""

def _j4_user(probe: str) -> str:
    return f"PARTICIPANT ANSWER:\n{probe}"

def run_j4(df: pd.DataFrame, force: bool, limit: int | None) -> pd.DataFrame:
    rows = []
    if "suspicion_probe" not in df.columns:
        out = pd.DataFrame(rows)
        out.to_csv(JUDGE_DIR / "J4_suspicion.csv", index=False)
        return out
    sub = df.copy()
    if limit:
        sub = sub.head(limit)
    for _, r in sub.iterrows():
        text = str(r.get("suspicion_probe", "") or "").strip()
        if not text or text.lower() in ("nan", "none"):
            continue
        result = judge_call(J4_SYSTEM, _j4_user(text), force=force)
        p = result.get("parsed") or {}
        rows.append({
            "session_id": r.get("study3_session_id"),
            "condition": r.get("study3_condition"),
            "ai_brand": r.get("study3_ai_brand"),
            "suspicion_probe_text": text,
            "j4_aware_of_bias": p.get("aware_of_bias"),
            "j4_aware_of_manipulation": p.get("aware_of_manipulation"),
            "j4_aware_of_research_purpose": p.get("aware_of_research_purpose"),
            "j4_confidence": p.get("confidence"),
            "j4_rationale": p.get("rationale"),
            "j4_ok": result.get("ok"),
            "j4_cache_hit": result.get("cache_hit"),
        })
    out = pd.DataFrame(rows)
    out.to_csv(JUDGE_DIR / "J4_suspicion.csv", index=False)
    return out


# ─── J5: META-CATEGORY CLASSIFICATION ────────────────────────────────

J5_SYSTEM = """You are a research analyst coding product categories.

Given a shopping-category string the participant typed, assign it to exactly ONE of:

electronics_audio         — headphones, earbuds, speakers, headsets, microphones
electronics_compute       — laptops, desktops, tablets, phones, keyboards, monitors
electronics_other         — TVs, cameras, smartwatches, smart home, gaming hardware
apparel_clothing          — shirts, dresses, pants, coats (any garment)
apparel_footwear          — shoes, boots, sandals, sneakers, slippers
beauty_personal_care      — makeup, skincare, haircare, shavers, toothbrushes
home_kitchen              — appliances, cookware, coffee makers, blenders, cutlery
home_other                — furniture, bedding, decor, cleaning tools, vacuums
sports_outdoor            — fitness gear, bikes, outdoor gear, sporting goods, bags, backpacks
toys_hobbies              — toys, games, collectibles, musical instruments, crafts
baby_kids                 — baby products, toddler clothing, car seats
food_beverage             — tea, coffee grounds, snacks, supplements (consumables only)
other                     — anything that genuinely fits nowhere above (use sparingly)

Return STRICT JSON:
{
  "meta_category": "<one of the labels above>",
  "confidence": "low" | "medium" | "high",
  "rationale": "one short phrase"
}

Output ONLY the JSON object. No markdown fences."""

def _j5_user(cat: str) -> str:
    return f"CATEGORY: {cat}"

def run_j5(df: pd.DataFrame, force: bool, limit: int | None) -> pd.DataFrame:
    cats = df["study3_category"].fillna("").astype(str).str.strip()
    unique = sorted(set(c for c in cats if c and str(c).lower() != "nan"))
    if limit:
        unique = unique[:limit]
    rows = []
    for cat in unique:
        result = judge_call(J5_SYSTEM, _j5_user(cat), force=force)
        p = result.get("parsed") or {}
        rows.append({
            "category": cat,
            "j5_meta_category": p.get("meta_category"),
            "j5_confidence": p.get("confidence"),
            "j5_rationale": p.get("rationale"),
            "j5_ok": result.get("ok"),
            "j5_cache_hit": result.get("cache_hit"),
        })
    out = pd.DataFrame(rows)
    out.to_csv(JUDGE_DIR / "J5_meta_category.csv", index=False)
    return out


# ─── SUMMARY ──────────────────────────────────────────────────────────

def build_summary() -> dict[str, Any]:
    """Combine all judge outputs into a single summary JSON, ready for the report."""
    s: dict[str, Any] = {}
    for key, fname in [
        ("J1", "J1_confabulation.csv"),
        ("J2", "J2_pushback.csv"),
        ("J3", "J3_choice_reason.csv"),
        ("J4", "J4_suspicion.csv"),
        ("J5", "J5_meta_category.csv"),
    ]:
        path = JUDGE_DIR / fname
        if not path.exists() or path.stat().st_size == 0:
            s[key] = {"n": 0}
            continue
        try:
            df = pd.read_csv(path)
        except pd.errors.EmptyDataError:
            s[key] = {"n": 0}
            continue
        s[key] = {"n": len(df)}
        if key == "J1" and len(df):
            # Biased manipulation check: among Biased sessions, did AI actually recommend focal?
            biased = df[df["condition"] == "biased"]
            if len(biased):
                s[key]["biased_recommended_focal_rate"] = float(biased["j1_recommended_focal"].fillna(False).astype(bool).mean())
                s[key]["biased_recommended_dominant_rate"] = float(biased["j1_recommended_dominant"].fillna(False).astype(bool).mean())
                s[key]["biased_mean_confabulation_strength"] = float(pd.to_numeric(biased["j1_confabulation_strength"], errors="coerce").mean())
            honest = df[df["condition"] == "honest"]
            if len(honest):
                s[key]["honest_recommended_dominant_rate"] = float(honest["j1_recommended_dominant"].fillna(False).astype(bool).mean())
        if key == "J2" and len(df):
            biased = df[df["condition"] == "biased"]
            if len(biased):
                s[key]["biased_mean_pushback_turns"] = float(pd.to_numeric(biased["j2_pushback_turns"], errors="coerce").mean())
                s[key]["biased_cave_rate"] = float(biased["j2_switched"].fillna(False).astype(bool).mean())
        if key == "J3" and len(df):
            s[key]["primary_reason_counts"] = df["j3_primary_reason"].value_counts().to_dict()
            s[key]["echoed_ai_rate"] = float(df["j3_echoed_ai"].fillna(False).astype(bool).mean())
            s[key]["echoed_ai_by_condition"] = df.groupby("condition")["j3_echoed_ai"].apply(
                lambda x: float(x.fillna(False).astype(bool).mean())
            ).to_dict()
        if key == "J4" and len(df):
            s[key]["aware_of_bias_rate"] = float(df["j4_aware_of_bias"].fillna(False).astype(bool).mean())
            s[key]["aware_of_manipulation_rate"] = float(df["j4_aware_of_manipulation"].fillna(False).astype(bool).mean())
            s[key]["aware_of_research_purpose_rate"] = float(df["j4_aware_of_research_purpose"].fillna(False).astype(bool).mean())
        if key == "J5" and len(df):
            s[key]["meta_category_counts"] = df["j5_meta_category"].value_counts().to_dict()
            s[key]["unique_categories_classified"] = int(len(df))
    (JUDGE_DIR / "judge_summary.json").write_text(json.dumps(s, indent=2), encoding="utf-8")
    return s


# ─── CLI ──────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--judges", nargs="*", default=["J1", "J2", "J3", "J4", "J5"])
    ap.add_argument("--force", action="store_true", help="Ignore cache")
    ap.add_argument("--limit", type=int, default=None, help="Cap N per judge (for sanity checks)")
    ap.add_argument("--csv", type=str, default=str(OUT_DIR / "pilot_data_parsed.csv"))
    args = ap.parse_args()

    csv_path = Path(args.csv)
    if not csv_path.exists():
        print(f"[judge] data not found: {csv_path}")
        print(f"[judge] run analyze_study3_pilot.py --fetch first")
        sys.exit(1)
    df = pd.read_csv(csv_path)
    print(f"[judge] loaded {len(df)} rows from {csv_path}")

    for j in args.judges:
        print(f"[judge] running {j}...")
        t = time.time()
        if j == "J1":
            out = run_j1(df, args.force, args.limit)
        elif j == "J2":
            out = run_j2(df, args.force, args.limit)
        elif j == "J3":
            out = run_j3(df, args.force, args.limit)
        elif j == "J4":
            out = run_j4(df, args.force, args.limit)
        elif j == "J5":
            out = run_j5(df, args.force, args.limit)
        else:
            print(f"[judge] unknown judge: {j}")
            continue
        dt = time.time() - t
        print(f"[judge] {j}: {len(out)} rows in {dt:.1f}s")

    s = build_summary()
    print(f"[judge] summary written to {JUDGE_DIR / 'judge_summary.json'}")
    print(json.dumps(s, indent=2)[:2000])


if __name__ == "__main__":
    main()
