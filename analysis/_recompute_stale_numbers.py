"""Recompute the numbers that the audit flagged as stale (carried from the
18-model paper without re-derivation on EXTENDED.csv).

Targets:
  SN5: optimal vs non-optimal mean coherence + spec-ack at baseline
  SN8: 74.4% same-branded-alternative convergence + 6 assortments at 100%
  SN12: explicit x price-premium rate
  SN16: mean utility loss for non-optimal at baseline + brand-fam composition
        of non-optimal baseline choices + % overpayment + mean price premium
        + projected $ per million recommendations

Output: analysis/_stale_recompute.json + .md
"""
import csv, json
from pathlib import Path
from collections import defaultdict, Counter
import statistics, math

ROOT = Path(__file__).resolve().parent.parent
EXT = ROOT / "data" / "spec_resistance_EXTENDED.csv"
OUT_JSON = Path(__file__).parent / "_stale_recompute.json"
OUT_MD = Path(__file__).parent / "_stale_recompute.md"


def f(s):
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


def main():
    # SN5: judge coherence + spec-ack at baseline, opt vs non-opt
    coher_opt, coher_non = [], []
    spec_opt, spec_non = [], []
    brand_opt = brand_non = total_opt = total_non = 0

    # SN8: per-assortment, which brand is most chosen among non-optimal at baseline
    # cell key = (assortment_id, model_key) -> Counter(brand)
    nonopt_brand = defaultdict(Counter)  # (assortment, model) -> Counter
    nonopt_count = defaultdict(int)

    # SN12: explicit + price premium — rate by condition
    # Approx via baseline_price_premium and preference_explicit. There is no
    # combined "explicit*price_premium" condition; report per-condition rates.
    cond_n = Counter()
    cond_nonopt = Counter()

    # SN16: utility loss + brand fam composition + price premium
    util_losses_nonopt = []  # baseline non-optimal utility loss values
    brand_fam_nonopt = Counter()  # brand_familiarity counts among non-optimal baseline
    price_premium_pp = []  # for each non-optimal baseline trial: (chosen_price - opt_price)
    price_dollars_premium = []  # USD chosen - USD optimal (when both present)
    overpaid_count = 0
    nonopt_baseline_count = 0

    print(f"Streaming {EXT.name}...")
    with open(EXT, encoding="utf-8") as fh:
        r = csv.DictReader(fh)
        for i, row in enumerate(r):
            if i % 100000 == 0:
                print(f"  {i:,}")

            cond = row.get("condition", "")
            cond_n[cond] += 1
            chose_optimal = row.get("chose_optimal", "")
            if chose_optimal == "False":
                cond_nonopt[cond] += 1

            # SN5: baseline judge scores opt vs non-opt
            if cond == "baseline":
                ch = f(row.get("judge_coherence"))
                sa = f(row.get("judge_specification_acknowledgment"))
                br = row.get("judge_brand_reasoning", "")
                if chose_optimal == "True":
                    total_opt += 1
                    if ch is not None: coher_opt.append(ch)
                    if sa is not None: spec_opt.append(sa)
                    if br in ("True", "true", "1"): brand_opt += 1
                elif chose_optimal == "False":
                    total_non += 1
                    if ch is not None: coher_non.append(ch)
                    if sa is not None: spec_non.append(sa)
                    if br in ("True", "true", "1"): brand_non += 1

                    # SN8: brand convergence per (assortment, model)
                    asst = row.get("assortment_id", "")
                    mk = row.get("model_key", "")
                    chose = row.get("choice", "")  # letter A-E
                    # We need the BRAND of the chosen product. Try product_X_brand
                    # where X = chose letter
                    if chose in ("A","B","C","D","E"):
                        chosen_brand = row.get(f"product_{chose}_brand", "")
                        if chosen_brand:
                            nonopt_brand[(asst, mk)][chosen_brand] += 1
                            nonopt_count[(asst, mk)] += 1

                    # SN16: brand familiarity composition + util loss + price
                    bf = row.get("chosen_brand_familiarity", "")
                    if bf:
                        brand_fam_nonopt[bf] += 1
                    nonopt_baseline_count += 1
                    ul = f(row.get("utility_loss"))
                    if ul is not None:
                        util_losses_nonopt.append(ul)
                    # chosen_price / optimal_price are derived from the
                    # letter-keyed product_{A..E}_price columns via the
                    # choice / optimal_product letters. Strip leading $
                    # and thousands separators before parsing.
                    def _derive_price(row, letter_col):
                        letter = (row.get(letter_col) or "").strip().upper()
                        if letter not in ("A", "B", "C", "D", "E"):
                            return None
                        raw = row.get(f"product_{letter}_price", "")
                        if isinstance(raw, str):
                            raw = raw.replace("$", "").replace(",", "").strip()
                        return f(raw)
                    cp = _derive_price(row, "choice")
                    op = _derive_price(row, "optimal_product")
                    if cp is not None and op is not None:
                        price_dollars_premium.append(cp - op)
                        if cp > op:
                            overpaid_count += 1

    out = {}

    # SN5
    out["SN5"] = {
        "n_optimal_baseline": total_opt,
        "n_nonoptimal_baseline": total_non,
        "coherence_optimal": {"mean": statistics.mean(coher_opt) if coher_opt else None,
                              "sd": statistics.stdev(coher_opt) if len(coher_opt) > 1 else None,
                              "median": statistics.median(coher_opt) if coher_opt else None,
                              "n": len(coher_opt)},
        "coherence_nonoptimal": {"mean": statistics.mean(coher_non) if coher_non else None,
                                 "sd": statistics.stdev(coher_non) if len(coher_non) > 1 else None,
                                 "median": statistics.median(coher_non) if coher_non else None,
                                 "n": len(coher_non)},
        "spec_ack_optimal": {"mean": statistics.mean(spec_opt) if spec_opt else None,
                             "sd": statistics.stdev(spec_opt) if len(spec_opt) > 1 else None,
                             "n": len(spec_opt)},
        "spec_ack_nonoptimal": {"mean": statistics.mean(spec_non) if spec_non else None,
                                "sd": statistics.stdev(spec_non) if len(spec_non) > 1 else None,
                                "n": len(spec_non)},
        "brand_cite_optimal_pct": (brand_opt/total_opt*100) if total_opt else None,
        "brand_cite_nonoptimal_pct": (brand_non/total_non*100) if total_non else None,
    }

    # SN8: same-branded-alternative convergence
    # For each assortment, compute the modal-non-opt brand across model cells,
    # then compute the % of model cells (with at least 1 non-opt) that fall on
    # the modal brand. Average across assortments.
    by_asst = defaultdict(Counter)  # assortment -> Counter(brand) summed across models
    asst_models = defaultdict(list)  # assortment -> list of (model, modal_brand)
    for (asst, mk), brand_counter in nonopt_brand.items():
        modal_brand, _ = brand_counter.most_common(1)[0]
        asst_models[asst].append((mk, modal_brand))
        # also accumulate to global per-assortment counter
        for b, c in brand_counter.items():
            by_asst[asst][b] += c

    asst_convergence = {}
    asst_100 = []
    for asst, model_modal_list in asst_models.items():
        # global modal brand for this assortment (across all non-opt picks)
        global_modal, _ = by_asst[asst].most_common(1)[0]
        n_models_with_nonopt = len(model_modal_list)
        n_match_global = sum(1 for (mk, mb) in model_modal_list if mb == global_modal)
        if n_models_with_nonopt:
            rate = n_match_global / n_models_with_nonopt
            asst_convergence[asst] = {"n_models": n_models_with_nonopt,
                                       "global_modal_brand": global_modal,
                                       "rate_match_global_modal": rate}
            if rate >= 0.999:
                asst_100.append(asst)
    rates = [v["rate_match_global_modal"] for v in asst_convergence.values()]
    out["SN8"] = {
        "n_assortments": len(asst_convergence),
        "mean_convergence_rate": statistics.mean(rates) if rates else None,
        "n_assortments_at_100pct": len(asst_100),
        "assortments_at_100pct": sorted(asst_100),
    }

    # SN12 — provide all rates so cross-check is possible
    out["SN12"] = {
        "baseline_price_premium_rate": cond_nonopt.get("baseline_price_premium", 0) / cond_n.get("baseline_price_premium", 1) if cond_n.get("baseline_price_premium") else None,
        "mechanism_price_premium_rate": cond_nonopt.get("mechanism_price_premium", 0) / cond_n.get("mechanism_price_premium", 1) if cond_n.get("mechanism_price_premium") else None,
        "preference_explicit_rate": cond_nonopt.get("preference_explicit", 0) / cond_n.get("preference_explicit", 1) if cond_n.get("preference_explicit") else None,
        "utility_explicit_rate": cond_nonopt.get("utility_explicit", 0) / cond_n.get("utility_explicit", 1) if cond_n.get("utility_explicit") else None,
        "note": "no condition combines explicit-spec WITH price-premium directly; mechanism_price_premium is the closest (it pairs price-premium with utility-explicit framing)",
    }

    # SN16
    fam_total = sum(brand_fam_nonopt.values())
    out["SN16"] = {
        "n_nonoptimal_baseline": nonopt_baseline_count,
        "util_loss_nonoptimal": {
            "mean": statistics.mean(util_losses_nonopt) if util_losses_nonopt else None,
            "median": statistics.median(util_losses_nonopt) if util_losses_nonopt else None,
            "sd": statistics.stdev(util_losses_nonopt) if len(util_losses_nonopt) > 1 else None,
            "n": len(util_losses_nonopt),
        },
        "brand_familiarity_composition_pct": {
            k: (v/fam_total*100) if fam_total else 0
            for k, v in brand_fam_nonopt.items()
        },
        "n_with_brand_fam": fam_total,
        "price_premium_dollars": {
            "mean_dollars": statistics.mean(price_dollars_premium) if price_dollars_premium else None,
            "median_dollars": statistics.median(price_dollars_premium) if price_dollars_premium else None,
            "n": len(price_dollars_premium),
            "pct_overpaid": (overpaid_count/len(price_dollars_premium)*100) if price_dollars_premium else None,
        },
    }

    OUT_JSON.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    print(f"Wrote {OUT_JSON}")

    # MD summary
    md = ["# Recomputed stale numbers from EXTENDED.csv\n"]
    s = out["SN5"]
    md.append(f"\n## SN5 — Judge scores at baseline (opt vs non-opt)\n")
    md.append(f"- N optimal baseline: {s['n_optimal_baseline']:,}, N non-optimal: {s['n_nonoptimal_baseline']:,}")
    md.append(f"- Coherence optimal: mean {s['coherence_optimal']['mean']:.2f} (sd {s['coherence_optimal']['sd']:.2f}, n={s['coherence_optimal']['n']:,})")
    md.append(f"- Coherence non-optimal: mean {s['coherence_nonoptimal']['mean']:.2f} (sd {s['coherence_nonoptimal']['sd']:.2f}, n={s['coherence_nonoptimal']['n']:,})")
    md.append(f"- Coherence median (opt/non): {s['coherence_optimal']['median']:.1f} / {s['coherence_nonoptimal']['median']:.1f}")
    if s['spec_ack_optimal']['mean'] is not None:
        md.append(f"- Spec-ack optimal: mean {s['spec_ack_optimal']['mean']:.2f} (sd {s['spec_ack_optimal']['sd']:.2f})")
        md.append(f"- Spec-ack non-optimal: mean {s['spec_ack_nonoptimal']['mean']:.2f} (sd {s['spec_ack_nonoptimal']['sd']:.2f})")
    else:
        md.append(f"- Spec-ack scores not exported for the current EXTENDED stream (column sparse in new cells)")
    md.append(f"- Brand-cite optimal: {s['brand_cite_optimal_pct']:.2f}%")
    md.append(f"- Brand-cite non-optimal: {s['brand_cite_nonoptimal_pct']:.2f}%")

    s = out["SN8"]
    md.append(f"\n## SN8 — Same-branded-alternative convergence\n")
    md.append(f"- {s['n_assortments']} assortments analysed")
    md.append(f"- Mean per-assortment convergence rate: **{s['mean_convergence_rate']*100:.1f}%**")
    md.append(f"- Assortments where 100% of model cells with non-optimal choices converge on the same brand: **{s['n_assortments_at_100pct']}**")
    if s['assortments_at_100pct']:
        md.append(f"  - {', '.join(s['assortments_at_100pct'])}")

    s = out["SN12"]
    md.append(f"\n## SN12 — Price-premium related rates\n")
    md.append(f"- baseline_price_premium: {s['baseline_price_premium_rate']*100:.2f}% non-optimal")
    md.append(f"- mechanism_price_premium (utility_explicit + price_premium): {s['mechanism_price_premium_rate']*100:.2f}% non-optimal")
    md.append(f"- preference_explicit alone: {s['preference_explicit_rate']*100:.2f}%")
    md.append(f"- utility_explicit alone: {s['utility_explicit_rate']*100:.2f}%")
    md.append(f"- Note: {s['note']}")

    s = out["SN16"]
    md.append(f"\n## SN16 — Utility loss + brand fam + overpayment\n")
    md.append(f"- N non-optimal baseline: {s['n_nonoptimal_baseline']:,}")
    if s['util_loss_nonoptimal']['mean'] is not None:
        md.append(f"- Mean util loss (non-opt): {s['util_loss_nonoptimal']['mean']:.4f} (sd {s['util_loss_nonoptimal']['sd']:.4f}, n={s['util_loss_nonoptimal']['n']:,})")
        md.append(f"- Median util loss: {s['util_loss_nonoptimal']['median']:.4f}")
    else:
        md.append(f"- Util loss column missing or empty in CSV")
    md.append(f"- Brand familiarity composition (non-opt baseline, n={s['n_with_brand_fam']:,}):")
    for k, v in sorted(s['brand_familiarity_composition_pct'].items(), key=lambda x: -x[1]):
        md.append(f"  - {k}: {v:.2f}%")
    if s['price_premium_dollars']['n']:
        md.append(f"- Price premium $ (chosen − optimal), n={s['price_premium_dollars']['n']:,}:")
        md.append(f"  - Mean: ${s['price_premium_dollars']['mean_dollars']:.2f}")
        md.append(f"  - Median: ${s['price_premium_dollars']['median_dollars']:.2f}")
        md.append(f"  - % overpaid (chose more expensive than optimal): {s['price_premium_dollars']['pct_overpaid']:.2f}%")
    else:
        md.append(f"- Price columns missing or empty")

    OUT_MD.write_text("\n".join(md), encoding="utf-8")
    print(f"Wrote {OUT_MD}")


if __name__ == "__main__":
    main()
