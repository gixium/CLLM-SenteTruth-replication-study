"""
compute_fcd_ci.py
Computes the Final Credibility Delta (FCD) and 95% Confidence Interval
across all shuffled question runs for each available experiment configuration.
"""
import sys
import pandas as pd
import numpy as np
from scipy import stats

# ── Sheet configurations ─────────────────────────────────────────────────────
CONFIGURATIONS = [
    {
        "label": "60/40 MIX",
        "candidates": ["60-40_MIX_shuffle", "gpt4omini_shuffle_100", "MIX_60-40_shuffle"],
        "n_shuffles": 30,
        "block": 103,
        "steps": 100,
    },
    {
        "label": "60/40 PRO",
        "candidates": ["60-40_PRO_shuffle", "gpt4omini_shuffle_60", "PRO_60-40_shuffle"],
        "n_shuffles": 20,
        "block": 63,
        "steps": 60,
    },
    {
        "label": "70/30 MIX",
        "candidates": ["70-30_MIX_shuffle", "gpt4omini_shuffle_100_2", "MIX_70-30_shuffle"],
        "n_shuffles": 30,
        "block": 103,
        "steps": 100,
    },
    {
        "label": "70/30 PRO",
        "candidates": ["70-30_PRO_shuffle", "gpt4omini_shuffle_60_2", "PRO_70-30_shuffle"],
        "n_shuffles": 20,
        "block": 63,
        "steps": 60,
    },
]


def extract_final_deltas(df: pd.DataFrame, n_shuffles: int, block: int, steps: int) -> list:
    """
    Extracts the delta value at the final step for each shuffle block.
    The final step of each block is at row: s*block + 2 + steps (0-indexed).
    """
    deltas = []
    for s in range(n_shuffles):
        last_row = s * block + 2 + steps
        if last_row < len(df):
            val = pd.to_numeric(df.iloc[last_row, 11], errors="coerce")
            deltas.append(float(val))
    return deltas


def compute_stats(deltas: list) -> dict:
    arr = np.array(deltas)
    n   = len(arr)
    avg = np.mean(arr)
    sd  = np.std(arr, ddof=1) if n > 1 else 0.0
    sem = stats.sem(arr) if n > 1 else 0.0
    ci_lo, ci_hi = stats.t.interval(0.95, df=n - 1, loc=avg, scale=sem) if n > 1 else (avg, avg)
    return {
        "n":      n,
        "avg":    avg,
        "sd":     sd,
        "ci_lo":  ci_lo,
        "ci_hi":  ci_hi,
        "mn":     np.min(arr),
        "mx":     np.max(arr),
        "deltas": deltas,
    }


def find_sheet(xl_sheets: list[str], candidates: list[str], label: str) -> str | None:
    """Find matching sheet name from candidate aliases or fuzzy matching."""
    for c in candidates:
        if c in xl_sheets:
            return c
    parts = label.replace("/", "-").lower().split()
    for s in xl_sheets:
        s_lower = s.lower()
        if "shuffle" in s_lower and all(p in s_lower for p in parts):
            return s
    return None


def main(filepath: str):
    try:
        xl = pd.read_excel(filepath, sheet_name=None, header=None)
    except FileNotFoundError:
        print(f"Error: file '{filepath}' not found.")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading '{filepath}': {e}")
        sys.exit(1)

    print(f"\nFile: {filepath}\n")

    all_stats = {}
    found_any = False

    for cfg in CONFIGURATIONS:
        label = cfg["label"]
        sheet_name = find_sheet(list(xl.keys()), cfg["candidates"], label)
        if not sheet_name:
            continue

        found_any = True
        deltas = extract_final_deltas(
            xl[sheet_name], cfg["n_shuffles"], cfg["block"], cfg["steps"]
        )
        if not deltas:
            continue

        s = compute_stats(deltas)
        all_stats[label] = s

        print("-" * 60)
        print(f"  Configuration   : {label} (sheet: '{sheet_name}')")
        print(f"  N shuffles      : {s['n']}")
        print(f"  Final Delta avg : {s['avg']:+.4f}")
        print(f"  Final Delta SD  : {s['sd']:.4f}")
        print(f"  95% CI          : [{s['ci_lo']:+.4f}, {s['ci_hi']:+.4f}]")
        print(f"  Final Delta min : {s['mn']:+.4f}")
        print(f"  Final Delta max : {s['mx']:+.4f}")
        print(f"  Per shuffle     : {[round(d, 4) for d in s['deltas']]}")

    if not found_any:
        print(f"Warning: No matching experiment sheets found in workbook.")
        print(f"Available sheets: {list(xl.keys())}\n")
        return

    # ── Summary table ────────────────────────────────────────────────────────
    print(f"\n" + "-" * 60)
    print("\nSummary Table (Final Delta = max_malicious_weight - max_honest_weight):\n")
    hdr = f"{'Config':<15} {'Avg':>8} {'SD':>7} {'CI low':>9} {'CI high':>9} {'Min':>8} {'Max':>8}"
    print(hdr)
    print("-" * len(hdr))
    for label, s in all_stats.items():
        print(
            f"{label:<15} "
            f"{s['avg']:>+8.4f} "
            f"{s['sd']:>7.4f} "
            f"{s['ci_lo']:>+9.4f} "
            f"{s['ci_hi']:>+9.4f} "
            f"{s['mn']:>+8.4f} "
            f"{s['mx']:>+8.4f}"
        )
    print()

    # Interpretation note
    print("Note: 95% CI computed using Student's t-distribution (ddof=1).")
    print("      Delta > 0 -> malicious dominance; Delta < 0 -> honest dominance.\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python compute_fcd_ci.py <file.xlsx>")
        sys.exit(1)
    main(sys.argv[1])