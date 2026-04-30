"""Verify Study 2 with stdlib csv — no pandas."""
import csv, math
from collections import Counter
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
p = PROJECT / "OSF" / "data" / "human_studies" / "study2_inoculation_anonymised.csv"

rows = list(csv.DictReader(p.open(encoding="utf-8")))
print(f"Raw N: {len(rows)}")

# Prereg filters: consent=1, Finished=1, attn_check=4, duration 120-1200, QID17 present
def _toi(x):
    try: return int(float(x))
    except Exception: return None

def keep(r):
    if _toi(r.get("consent")) != 1: return False
    if _toi(r.get("Finished")) != 1: return False
    if _toi(r.get("attn_check")) != 4: return False
    try: d = float(r.get("Duration (in seconds)", "0"))
    except Exception: return False
    if d < 120 or d > 1200: return False
    q = r.get("QID17", "").strip()
    if not q: return False
    return True

flt = [r for r in rows if keep(r)]
print(f"Post prereg filter: {len(flt)}")

# Decode choice: Study 2 uses FIXED product IDs (not display positions).
# From analyze_v4_lean.py: EARBUDS_BRANDED = "2" (JBL), EARBUDS_OPTIMAL = "4" (Vynex)
EARBUDS_BRANDED = 2
EARBUDS_OPTIMAL = 4
def decode(r):
    try:
        qid = int(float(r["QID17"]))
    except Exception:
        return None, None
    return (qid == EARBUDS_BRANDED), (qid == EARBUDS_OPTIMAL)

by_cond = Counter()
branded_by_cond = Counter()
optimal_by_cond = Counter()
for r in flt:
    c = r.get("ConditionD", "").strip()
    b, o = decode(r)
    if b is None: continue
    by_cond[c] += 1
    branded_by_cond[c] += int(bool(b))
    optimal_by_cond[c] += int(bool(o))

print("\nPer-condition:")
for c in by_cond:
    n = by_cond[c]
    kb = branded_by_cond[c]
    ko = optimal_by_cond[c]
    print(f"  {c}: N={n}, branded={kb}/{n} = {kb/n*100:.1f}%, optimal={ko}/{n} = {ko/n*100:.1f}%")

# Fisher's via math
def fisher_2sided(a, b, c, d):
    """a = table[0][0], b = [0][1], c = [1][0], d = [1][1]."""
    n1 = a + b; n2 = c + d
    ks = a + c
    n = n1 + n2
    from math import lgamma, exp
    def lhg(k):
        return (lgamma(n1 + 1) - lgamma(k + 1) - lgamma(n1 - k + 1) +
                lgamma(n2 + 1) - lgamma(ks - k + 1) - lgamma(n2 - (ks - k) + 1) -
                lgamma(n + 1) + lgamma(ks + 1) + lgamma(n - ks + 1))
    lp0 = lhg(a)
    total = 0.0
    for k in range(max(0, ks - n2), min(n1, ks) + 1):
        lp = lhg(k)
        if lp <= lp0 + 1e-10:
            total += exp(lp)
    return min(1.0, total)

cond_names = list(by_cond.keys())
print("\nPairwise contrasts (branded rate):")
for i, c1 in enumerate(cond_names):
    for c2 in cond_names[i+1:]:
        k1 = branded_by_cond[c1]; n1 = by_cond[c1]
        k2 = branded_by_cond[c2]; n2 = by_cond[c2]
        r1 = k1 / n1 * 100; r2 = k2 / n2 * 100
        try:
            p = fisher_2sided(k1, n1 - k1, k2, n2 - k2)
        except Exception as e:
            p = float("nan")
        print(f"  {c1} ({r1:.1f}%) vs {c2} ({r2:.1f}%): delta={r1-r2:+.1f}pp, P={p:.2e}")
