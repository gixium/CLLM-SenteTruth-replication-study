import sys
import pandas as pd
import numpy as np
from scipy import stats

# ── configurazione fogli ────────────────────────────────────────────────────
SHEETS = {
    "60/40 MIX": {"name": "gpt4omini_shuffle_100",   "n_shuffles": 30, "block": 103, "steps": 100},
    "60/40 PRO": {"name": "gpt4omini_shuffle_60",    "n_shuffles": 20, "block": 63,  "steps": 60},
    "70/30 MIX": {"name": "gpt4omini_shuffle_100_2", "n_shuffles": 30, "block": 103, "steps": 100},
    "70/30 PRO": {"name": "gpt4omini_shuffle_60_2",  "n_shuffles": 20, "block": 63,  "steps": 60},
}


def extract_final_deltas(df: pd.DataFrame, n_shuffles: int, block: int, steps: int) -> list:
    """
    Per ogni shuffle estrae il valore di delta all'ultimo step.
    L'ultimo step di ogni blocco è alla riga: s*block + 2 + steps (0-indexed pandas).
    """
    deltas = []
    for s in range(n_shuffles):
        last_row = s * block + 2 + steps
        val = pd.to_numeric(df.iloc[last_row, 11], errors="coerce")
        deltas.append(float(val))
    return deltas


def compute_stats(deltas: list) -> dict:
    arr = np.array(deltas)
    n   = len(arr)
    avg = np.mean(arr)
    sd  = np.std(arr, ddof=1)
    sem = stats.sem(arr)
    ci_lo, ci_hi = stats.t.interval(0.95, df=n - 1, loc=avg, scale=sem)
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


def main(filepath: str):
    try:
        xl = pd.read_excel(filepath, sheet_name=None, header=None)
    except FileNotFoundError:
        print(f"Errore: file '{filepath}' non trovato.")
        sys.exit(1)

    print(f"\nFile: {filepath}\n")

    all_stats = {}

    for label, cfg in SHEETS.items():
        if cfg["name"] not in xl:
            print(f"  [SKIP] foglio '{cfg['name']}' non trovato.")
            continue

        deltas = extract_final_deltas(
            xl[cfg["name"]], cfg["n_shuffles"], cfg["block"], cfg["steps"]
        )
        s = compute_stats(deltas)
        all_stats[label] = s

        print(f"{'─'*60}")
        print(f"  Configurazione : {label}")
        print(f"  N shuffle      : {s['n']}")
        print(f"  Final Δ avg    : {s['avg']:+.4f}")
        print(f"  Final Δ SD     : {s['sd']:.4f}")
        print(f"  95% CI         : [{s['ci_lo']:+.4f}, {s['ci_hi']:+.4f}]")
        print(f"  Final Δ min    : {s['mn']:+.4f}")
        print(f"  Final Δ max    : {s['mx']:+.4f}")
        print(f"  Per shuffle    : {[round(d, 4) for d in s['deltas']]}")

    # ── tabella riassuntiva ──────────────────────────────────────────────────
    print(f"\n{'─'*60}")
    print("\nTabella riassuntiva (Final Δ = max_malicious_weight − max_honest_weight):\n")
    hdr = f"{'Config':<15} {'Avg':>8} {'SD':>7} {'CI low':>9} {'CI high':>9} {'Min':>8} {'Max':>8}"
    print(hdr)
    print("─" * len(hdr))
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

    # Nota interpretativa
    print("Nota: CI al 95% calcolato con distribuzione t di Student (ddof=1).")
    print("      Δ > 0 → dominanza malicious; Δ < 0 → dominanza honest.\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python final_delta_ci.py <file.xlsx>")
        sys.exit(1)
    main(sys.argv[1])