"""
q-star.py
Computes the honest reporter competence q* required by the ASTRAEA baseline
to match C-LLM's empirical accuracy under each configuration (RQ3).
"""
from scipy.stats import binom
from scipy.optimize import brentq
import statistics

# System parameters
N = 10
THRESHOLD = 6
Q_MIN_RATIONAL = 0.50
Q_MIN_PAPER = 0.80

def astraea_error(q, k):
    """Computes P(corrupted decision) using original ASTRAEA Eq. 5."""
    p_wrong = (1 - q) + (k / N) * q
    return 1 - binom.cdf(THRESHOLD - 1, N, p_wrong)

def find_q_star(target_error, k):
    """Finds q in [0,1] such that astraea_error(q, k) = target_error."""
    if target_error <= 1e-9:
        return 1.0 if astraea_error(1.0, k) < 1e-9 else None

    err_at_zero = astraea_error(0.0, k)
    err_at_one = astraea_error(1.0, k)

    if target_error >= err_at_zero - 1e-9:
        return 0.0
    if target_error < err_at_one - 1e-9:
        return None

    return brentq(lambda q: astraea_error(q, k) - target_error, 0.0, 1.0, xtol=1e-8)

# Dataset: (model, dataset, split, k, C1%, C2%, C3%, C4%)
TABLE = [
    ("GPT-4o-mini", "MIX", "60/40", 4, 100.0, 67.0,  1.0, 99.0),
    ("GPT-4o-mini", "PRO", "60/40", 4, 100.0,  3.3,  1.7, 100.0),
    ("Gemini",      "MIX", "60/40", 4, 100.0, 58.0,  8.0, 100.0),
    ("Gemini",      "PRO", "60/40", 4, 100.0, 28.3, 11.7, 100.0),
    ("DS-Chat",     "MIX", "60/40", 4,  50.0,  1.0,  1.0,  3.0),
    ("DS-Chat",     "PRO", "60/40", 4,  40.0,  0.0,  0.0,  0.0),
    ("DS-Reasoner", "MIX", "60/40", 4,   0.0,  2.0,  0.0,  1.0),
    ("DS-Reasoner", "PRO", "60/40", 4,  15.0,  8.3,  5.0,  6.7),
    ("GPT-4o-mini", "MIX", "70/30", 3, 100.0, 100.0, 100.0, 100.0),
    ("GPT-4o-mini", "PRO", "70/30", 3, 100.0, 100.0, 56.7, 100.0),
    ("Gemini",      "MIX", "70/30", 3, 100.0, 100.0, 100.0, 100.0),
    ("Gemini",      "PRO", "70/30", 3, 100.0, 100.0, 100.0, 100.0),
    ("DS-Chat",     "MIX", "70/30", 3, 100.0, 67.0, 43.0, 53.0),
    ("DS-Chat",     "PRO", "70/30", 3, 100.0, 13.3,  0.0, 61.7),
    ("DS-Reasoner", "MIX", "70/30", 3,  17.0,  8.0, 59.0, 77.0),
    ("DS-Reasoner", "PRO", "70/30", 3, 100.0, 100.0, 53.3, 60.0),
]

CONFIGS = ["C1", "C2", "C3", "C4"]
all_results = []

for model, ds, split, k, *accs in TABLE:
    for cfg, acc in zip(CONFIGS, accs):
        target = 1.0 - acc / 100.0
        q_star = find_q_star(target, k)
        vulnerable = acc < 95.0
        all_results.append((split, model, ds, cfg, k, acc, q_star, vulnerable))

print(f"Model Eq. 5 | N={N} THRESHOLD={THRESHOLD}")
print("-" * 75)
print(f"{'Split':7} {'Model':13} {'Ds':4} {'Cfg':4} {'Acc%':>6} {'q*':>7}  Note")
print("-" * 75)

for split, model, ds, cfg, k, acc, q_star, vuln in all_results:
    marker = "[V]" if vuln else "   "
    
    if q_star is None:
        note = "C-LLM unreachable"
        q_str = "N/A"
    elif q_star >= 1.0 - 1e-6:
        note = "Robust (q=1)"
        q_str = "1.000"
    elif q_star <= Q_MIN_RATIONAL:
        note = f"ASTRAEA wins (q* <= {Q_MIN_RATIONAL} = rational minimum)"
        q_str = f"{q_star:.3f}"
    elif q_star <= Q_MIN_PAPER:
        note = f"ASTRAEA wins (q* <= {Q_MIN_PAPER} = paper standard)"
        q_str = f"{q_star:.3f}"
    else:
        note = f"ASTRAEA wins if q* >= {q_star:.3f}"
        q_str = f"{q_star:.3f}"

    print(f"{split:7} {model:13} {ds:4} {cfg:4} {acc:>5.1f}% {marker} {q_str:>7}  {note}")

# --- STATISTICAL SUMMARY ---
vulnerable = [r for r in all_results if r[-1]]
robust = [r for r in all_results if not r[-1]]
solvable = [r[6] for r in vulnerable if r[6] is not None]

below_rational = [q for q in solvable if q <= Q_MIN_RATIONAL]
below_paper = [q for q in solvable if q <= Q_MIN_PAPER]
unreachable = len(vulnerable) - len(solvable)

print("\n" + "=" * 75)
print("STATISTICAL SUMMARY")
print("=" * 75)
print(f"Total configurations       : {len(all_results)}")
print(f"  - Robust (Acc >= 95%)    : {len(robust)}")
print(f"  - Vulnerable (Acc < 95%) : {len(vulnerable)}")

print("\nVulnerable configurations breakdown:")
print(f"  - q* <= {Q_MIN_RATIONAL} (Rational min) : {len(below_rational)}/{len(vulnerable)}")
print(f"  - q* <= {Q_MIN_PAPER} (Paper standard): {len(below_paper)}/{len(vulnerable)}")
if unreachable > 0:
    print(f"  - Unreachable (N/A)      : {unreachable}/{len(vulnerable)}")

if solvable:
    print(f"\nDistribution of q* (n={len(solvable)}):")
    print(f"  min={min(solvable):.3f} | median={statistics.median(solvable):.3f} | "
          f"max={max(solvable):.3f} | mean={statistics.mean(solvable):.3f}")