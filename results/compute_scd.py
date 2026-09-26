"""
compute_scd.py
Computes Sustained Credibility Dominance (SCD) across shuffled question runs.
Detects the first step at which malicious credibility exceeds honest credibility
for >=10 consecutive steps, reporting incidence and onset step statistics.
"""
import sys
import pandas as pd
import numpy as np

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

CONSEC = 10   # number of consecutive positive steps required


def steps_to_control(deltas: list, k: int = CONSEC) -> int | None:
    """
    Returns the first step (1-indexed) where a sequence of k consecutive
    deltas all > 0 begins. Returns None if it never occurs.
    """
    n = len(deltas)
    for i in range(n - k + 1):
        if all(d > 0 for d in deltas[i:i + k]):
            return i + 1   # 1-indexed step
    return None


def process_sheet(df: pd.DataFrame, cfg: dict, label: str) -> dict:
    n_shuffles = cfg["n_shuffles"]
    block      = cfg["block"]
    steps      = cfg["steps"]

    results = []

    for s in range(n_shuffles):
        row_start = s * block
        data_rows = df.iloc[row_start + 2 : row_start + 2 + steps + 1]
        deltas = pd.to_numeric(data_rows.iloc[:, 11], errors="coerce").dropna().tolist()

        stc = steps_to_control(deltas)
        results.append(stc)

    valid   = [v for v in results if v is not None]
    never   = results.count(None)

    avg = np.mean(valid)   if valid else None
    mn  = np.min(valid)    if valid else None
    mx  = np.max(valid)    if valid else None

    return {
        "label":         label,
        "n_shuffles":    n_shuffles,
        "never_count":   never,
        "avg_steps":     round(avg, 1) if avg is not None else "-",
        "min_steps":     int(mn)       if mn  is not None else "-",
        "max_steps":     int(mx)       if mx  is not None else "-",
        "per_shuffle":   results,
    }


def find_sheet(xl_sheets: list[str], candidates: list[str], label: str) -> str | None:
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

    summary = []

    for cfg in CONFIGURATIONS:
        label = cfg["label"]
        sheet_name = find_sheet(list(xl.keys()), cfg["candidates"], label)
        if not sheet_name:
            continue

        res = process_sheet(xl[sheet_name], cfg, label)
        summary.append(res)

        never_note = f"  ({res['never_count']} shuffles without dominance)" if res["never_count"] > 0 else ""
        print("-" * 55)
        print(f"  Configuration  : {label} (sheet: '{sheet_name}')")
        print(f"  Total shuffles : {res['n_shuffles']}{never_note}")
        print(f"  Avg steps      : {res['avg_steps']}")
        print(f"  Min steps      : {res['min_steps']}")
        print(f"  Max steps      : {res['max_steps']}")

        print(f"  Per-shuffle detail:")
        for i, v in enumerate(res["per_shuffle"], 1):
            tag = str(v) if v is not None else "never"
            print(f"    shuffle {i:>2}: {tag}")

    if not summary:
        print(f"Warning: No matching experiment sheets found in workbook.")
        print(f"Available sheets: {list(xl.keys())}\n")
        return

    print("-" * 55)
    print("\nSummary Table:\n")
    print(f"{'Configuration':<15} {'Avg':>6} {'Min':>6} {'Max':>6}  {'Never':>6}")
    print(f"{'-'*15} {'-'*6} {'-'*6} {'-'*6}  {'-'*6}")
    for r in summary:
        print(f"{r['label']:<15} {str(r['avg_steps']):>6} {str(r['min_steps']):>6} {str(r['max_steps']):>6}  {r['never_count']:>6}")
    print()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python compute_scd.py <file.xlsx>")
        sys.exit(1)
    main(sys.argv[1])
