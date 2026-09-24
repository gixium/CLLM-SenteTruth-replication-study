import sys
import pandas as pd
import numpy as np

# ── configurazione fogli ────────────────────────────────────────────────────
SHEETS = {
    "60/40 MIX":  {"name": "gpt4omini_shuffle_100",   "n_shuffles": 30, "block": 103, "steps": 100},
    "60/40 PRO":  {"name": "gpt4omini_shuffle_60",    "n_shuffles": 20, "block": 63,  "steps": 60},
    "70/30 MIX":  {"name": "gpt4omini_shuffle_100_2", "n_shuffles": 30, "block": 103, "steps": 100},
    "70/30 PRO":  {"name": "gpt4omini_shuffle_60_2",  "n_shuffles": 20, "block": 63,  "steps": 60},
}

CONSEC = 10   # numero di step positivi consecutivi richiesti


def steps_to_control(deltas: list, k: int = CONSEC) -> int | None:
    """
    Restituisce il primo step (1-indexed) in cui inizia una sequenza
    di k delta consecutivi tutti > 0. None se non avviene mai.
    """
    n = len(deltas)
    for i in range(n - k + 1):
        if all(d > 0 for d in deltas[i:i + k]):
            return i + 1   # step 1-indexed (i=0 → step 1)
    return None


def process_sheet(df: pd.DataFrame, cfg: dict, label: str) -> dict:
    n_shuffles = cfg["n_shuffles"]
    block      = cfg["block"]
    steps      = cfg["steps"]

    results = []

    for s in range(n_shuffles):
        row_start = s * block          # riga pandas 0-indexed del blocco
        # struttura blocco:
        #   row_start+0 : "SHUFFLE N"  (header)
        #   row_start+1 : intestazioni colonne (1,2,...,10,NaN,DELTA,...)
        #   row_start+2 : step 0 (delta=0, peso iniziale)
        #   row_start+3 : step 1
        #   ...
        #   row_start+2+steps : step finale

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
        "avg_steps":     round(avg, 1) if avg is not None else "—",
        "min_steps":     int(mn)       if mn  is not None else "—",
        "max_steps":     int(mx)       if mx  is not None else "—",
        "per_shuffle":   results,
    }


def main(filepath: str):
    print(f"\nFile: {filepath}\n")

    try:
        xl = pd.read_excel(filepath, sheet_name=None, header=None)
    except FileNotFoundError:
        print(f"Errore: file '{filepath}' non trovato.")
        sys.exit(1)

    summary = []

    for label, cfg in SHEETS.items():
        sheet_name = cfg["name"]
        if sheet_name not in xl:
            print(f"  [SKIP] foglio '{sheet_name}' non trovato nel file.")
            continue

        res = process_sheet(xl[sheet_name], cfg, label)
        summary.append(res)

        never_note = f"  ({res['never_count']} shuffle senza dominanza)" if res["never_count"] > 0 else ""
        print(f"{'─'*55}")
        print(f"  Configurazione : {label}")
        print(f"  Shuffle totali : {res['n_shuffles']}{never_note}")
        print(f"  Avg steps      : {res['avg_steps']}")
        print(f"  Min steps      : {res['min_steps']}")
        print(f"  Max steps      : {res['max_steps']}")

        # dettaglio per shuffle
        print(f"  Dettaglio per shuffle:")
        for i, v in enumerate(res["per_shuffle"], 1):
            tag = str(v) if v is not None else "never"
            print(f"    shuffle {i:>2}: {tag}")

    print(f"{'─'*55}")
    print("\nTabella riassuntiva:\n")
    print(f"{'Configurazione':<15} {'Avg':>6} {'Min':>6} {'Max':>6}  {'Never':>6}")
    print(f"{'─'*15} {'─'*6} {'─'*6} {'─'*6}  {'─'*6}")
    for r in summary:
        print(f"{r['label']:<15} {str(r['avg_steps']):>6} {str(r['min_steps']):>6} {str(r['max_steps']):>6}  {r['never_count']:>6}")
    print()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python systemic_dominance.py <percorso_file.xlsx>")
        sys.exit(1)
    main(sys.argv[1])
