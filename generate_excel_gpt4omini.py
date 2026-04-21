#!/usr/bin/env python3
"""
generate_excel_gpt4omini.py — Generate Excel analysis for GPT-4o mini results.

Replicates the exact structure of 'Research project.xlsx' for GPT-4o mini data.
Reads node_weights_log_*.txt files and produces:
  - Single-run sheets (weight evolution + delta + summary stats)
  - Shuffle sheets (all shuffled runs + per-run accuracy + aggregate stats)
  - Final results summary sheet

Output: "Research project GPT4o-mini.xlsx"
"""

import os
import sys
import glob
import numpy as np
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter

# ─── Configuration ───────────────────────────────────────────────────────────

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(PROJECT_DIR, "Research project GPT4o-mini.xlsx")

# All 4 experiment configurations
EXPERIMENTS = [
    {
        "name": "gpt4omini_single_100",
        "shuffle_name": "gpt4omini_shuffle_100",
        "dataset": "MIX",
        "config": "60-40",
        "number": 100,
        "good_nodes": 6,
        "num_shuffles": 30,
        "suffix": "",  # no suffix for 60-40
    },
    {
        "name": "gpt4omini_single_60",
        "shuffle_name": "gpt4omini_shuffle_60",
        "dataset": "PRO",
        "config": "60-40",
        "number": 60,
        "good_nodes": 6,
        "num_shuffles": 20,
        "suffix": "",
    },
    {
        "name": "gpt4omini_single_100_2",
        "shuffle_name": "gpt4omini_shuffle_100_2",
        "dataset": "MIX",
        "config": "70-30",
        "number": 100,
        "good_nodes": 7,
        "num_shuffles": 30,
        "suffix": "_2",  # suffix for 70-30 (matching original Excel naming)
    },
    {
        "name": "gpt4omini_single_60_2",
        "shuffle_name": "gpt4omini_shuffle_60_2",
        "dataset": "PRO",
        "config": "70-30",
        "number": 60,
        "good_nodes": 7,
        "num_shuffles": 20,
        "suffix": "_2",
    },
]

# ─── Styling ─────────────────────────────────────────────────────────────────

HEADER_FONT = Font(bold=True)
HEADER_FILL = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
GOOD_FILL = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
BAD_FILL = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
SUMMARY_FONT = Font(bold=True, color="000080")
THIN_BORDER = Border(
    left=Side(style="thin"),
    right=Side(style="thin"),
    top=Side(style="thin"),
    bottom=Side(style="thin"),
)


# ─── Data Loading ────────────────────────────────────────────────────────────

def load_weights(filepath):
    """
    Load a node_weights_log_*.txt file.
    Returns a list of lists: [[w0, w1, ..., w9], ...] — one list per step.
    """
    weights = []
    with open(filepath, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                vals = [float(x) for x in line.split()]
                if len(vals) == 10:
                    weights.append(vals)
    return weights


def compute_delta(weights_row, good_nodes):
    """
    DELTA = max(malicious node weight) − max(honest node weight)
    
    For 60-40: honest = nodes 0-5 (cols A-F), malicious = nodes 6-9 (cols G-J)
    For 70-30: honest = nodes 0-6 (cols A-G), malicious = nodes 7-9 (cols H-J)
    
    Positive delta = malicious winning.
    """
    honest_max = max(weights_row[:good_nodes])
    # All malicious nodes have the same weight (perfect collusion),
    # so we take any of them (the last one, index 9 = col J, as in the original Excel)
    malicious_weight = weights_row[9]
    return malicious_weight - honest_max


def compute_accuracy(weights_data, good_nodes):
    """
    System accuracy = fraction of steps where the highest-weight node is honest.
    
    A step is a "malicious win" if DELTA > 0 (malicious max > honest max).
    Accuracy = (total_steps - malicious_wins) / total_steps
    """
    total = len(weights_data)
    if total == 0:
        return 0.0
    malicious_wins = sum(
        1 for row in weights_data if compute_delta(row, good_nodes) > 0
    )
    return (total - malicious_wins) / total


# ─── Sheet Builders ──────────────────────────────────────────────────────────

def build_single_sheet(wb, sheet_name, weights_data, good_nodes, total_questions):
    """
    Build a single-run sheet matching the structure of 'single_100', 'single_60', etc.
    
    Layout:
    Row 1: headers    1, 2, 3, ..., 10, #NODE, DELTA, [gap], malicious node
    Row 2: initial    0.5, 0.5, ..., 0.5, [blank], 0 (delta)
    Row 3+: weights   w0, w1, ..., w9, [blank], delta
    
    Column N-O summary (rows 3-6):
      N3: "total"           O3: number of questions
      N4: "#malicious win"  O4: count of steps where delta > 0
      N5: "System accuracy" O5: (total - mal_wins) / total
      N6: "final delta"     O6: delta at last step
    """
    ws = wb.create_sheet(title=sheet_name)

    # --- Row 1: Headers ---
    for i in range(1, 11):
        cell = ws.cell(row=1, column=i, value=i)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal="center")
        # Color honest nodes green, malicious red
        if i <= good_nodes:
            cell.fill = GOOD_FILL
        else:
            cell.fill = BAD_FILL

    ws.cell(row=1, column=11, value="#NODE").font = HEADER_FONT
    ws.cell(row=1, column=12, value="DELTA").font = HEADER_FONT
    ws.cell(row=1, column=13, value="node").font = HEADER_FONT
    ws.cell(row=1, column=14, value="malicious node").font = HEADER_FONT

    # --- Row 2: Initial weights ---
    for i in range(1, 11):
        ws.cell(row=2, column=i, value=0.5)
    ws.cell(row=2, column=12, value=0)  # Initial delta = 0

    # --- Rows 3+: Weight data ---
    deltas = []
    for step_idx, row_data in enumerate(weights_data):
        row_num = step_idx + 3  # Excel row (1-indexed, header=1, initial=2)
        for col_idx, weight in enumerate(row_data):
            ws.cell(row=row_num, column=col_idx + 1, value=round(weight, 6))
        delta = compute_delta(row_data, good_nodes)
        deltas.append(delta)
        ws.cell(row=row_num, column=12, value=round(delta, 6))

    # --- Summary statistics (columns N-O, rows 3-6) ---
    total_steps = len(weights_data)
    malicious_wins = sum(1 for d in deltas if d > 0)
    accuracy = (total_steps - malicious_wins) / total_steps if total_steps > 0 else 0
    final_delta = deltas[-1] if deltas else 0

    summary = [
        ("total", total_steps),
        ("#malicious win", malicious_wins),
        ("System accuracy", round(accuracy, 6)),
        ("final delta", round(final_delta, 6)),
    ]
    for i, (label, value) in enumerate(summary):
        ws.cell(row=3 + i, column=14, value=label).font = SUMMARY_FONT
        ws.cell(row=3 + i, column=15, value=value).font = SUMMARY_FONT

    # Column widths
    for col in range(1, 16):
        ws.column_dimensions[get_column_letter(col)].width = 14

    return {
        "total": total_steps,
        "malicious_wins": malicious_wins,
        "accuracy": accuracy,
        "final_delta": final_delta,
    }


def build_shuffle_sheet(wb, sheet_name, shuffle_weights, good_nodes, total_questions, num_shuffles):
    """
    Build a shuffled-runs sheet matching 'shuffle_100', 'shuffle_60', etc.
    
    Layout: Repeating blocks, one per shuffle:
      Block header row: "SHUFFLE N"
      Block row 2: 1, 2, ..., 10, [gap], DELTA
      Block row 3: 0.5 × 10, delta=0
      Block rows 4+: weight data + delta
    
    Accuracy columns (O-X in row 3):
      Each column = accuracy for one shuffle
    
    Aggregate (Z-AA columns):
      Z1: "accuracy", Z2: "MAX", Z3: "MIN", Z4: "AVG"
      AA2-AA4: computed values
    """
    ws = wb.create_sheet(title=sheet_name)

    per_run_accuracies = []
    current_row = 1

    for shuffle_idx in range(num_shuffles):
        weights_data = shuffle_weights[shuffle_idx]
        if not weights_data:
            per_run_accuracies.append(0.0)
            continue

        # --- Block header ---
        cell = ws.cell(row=current_row, column=1, value=f"SHUFFLE {shuffle_idx + 1}")
        cell.font = Font(bold=True, size=12)
        current_row += 1

        # --- Column headers ---
        for i in range(1, 11):
            c = ws.cell(row=current_row, column=i, value=i)
            c.font = HEADER_FONT
            if i <= good_nodes:
                c.fill = GOOD_FILL
            else:
                c.fill = BAD_FILL
        ws.cell(row=current_row, column=12, value="DELTA").font = HEADER_FONT

        # Accuracy header (only in first block)
        if shuffle_idx == 0:
            ws.cell(row=current_row, column=14, value="system accuracy per run").font = HEADER_FONT
            for si in range(num_shuffles):
                ws.cell(row=current_row, column=15 + si, value=si + 1).font = HEADER_FONT

        current_row += 1

        # --- Initial weights row ---
        for i in range(1, 11):
            ws.cell(row=current_row, column=i, value=0.5)
        ws.cell(row=current_row, column=12, value=0)

        # Accuracy for this shuffle (written in the initial weights row of its block)
        accuracy = compute_accuracy(weights_data, good_nodes)
        per_run_accuracies.append(accuracy)

        # Write per-run accuracy in the FIRST BLOCK's initial row
        # (matching the original Excel layout where all accuracies are in row 3)
        if shuffle_idx == 0:
            # We'll fill these in after collecting all accuracies
            pass

        current_row += 1

        # --- Weight data ---
        for step_idx, row_data in enumerate(weights_data):
            for col_idx, weight in enumerate(row_data):
                ws.cell(row=current_row, column=col_idx + 1, value=round(weight, 6))
            delta = compute_delta(row_data, good_nodes)
            ws.cell(row=current_row, column=12, value=round(delta, 6))
            current_row += 1

    # --- Write per-run accuracies in columns O-X of row 3 ---
    # In the original Excel, these are in rows 3 and 5 (alternating with shuffle indices)
    # Row 3 = accuracies for shuffles 1-10
    # Row 4 = shuffle indices 11-20
    # Row 5 = accuracies for shuffles 11-20
    # etc.
    accuracy_start_row = 3  # Row 3 in the sheet
    
    # Write accuracies in a 2-row pattern:
    # Row (accuracy_start_row): accuracies for batch 1 (shuffles 1-10)
    # Row (accuracy_start_row+1): shuffle indices for batch 2 (11-20)
    # Row (accuracy_start_row+2): accuracies for batch 2 (shuffles 11-20)
    # etc.
    
    batch_size = 10  # 10 accuracies per row (columns O through X)
    num_batches = (num_shuffles + batch_size - 1) // batch_size
    
    for batch_idx in range(num_batches):
        row_offset = batch_idx * 2
        start_s = batch_idx * batch_size
        end_s = min(start_s + batch_size, num_shuffles)
        
        for si in range(start_s, end_s):
            col = 15 + (si - start_s)  # Column O = 15
            # Accuracy row
            ws.cell(row=accuracy_start_row + row_offset, column=col,
                    value=round(per_run_accuracies[si], 6))
            # Index row (for batches after the first)
            if batch_idx > 0 or si >= batch_size:
                ws.cell(row=accuracy_start_row + row_offset - 1, column=col,
                        value=si + 1)

    # Handle the second row of shuffle indices for the first batch (11-20 etc.)
    if num_shuffles > batch_size:
        for batch_idx in range(1, num_batches):
            start_s = batch_idx * batch_size
            end_s = min(start_s + batch_size, num_shuffles)
            row_offset = batch_idx * 2 - 1
            for si in range(start_s, end_s):
                col = 15 + (si - start_s)
                ws.cell(row=accuracy_start_row + row_offset, column=col,
                        value=si + 1).font = HEADER_FONT

    # --- Aggregate accuracy stats (columns Z-AA) ---
    z_col = 26  # Column Z
    aa_col = 27  # Column AA

    ws.cell(row=1, column=z_col, value="accuracy").font = Font(bold=True, size=12)
    ws.cell(row=2, column=z_col, value="MAX").font = SUMMARY_FONT
    ws.cell(row=3, column=z_col, value="MIN").font = SUMMARY_FONT
    ws.cell(row=4, column=z_col, value="AVG").font = SUMMARY_FONT

    if per_run_accuracies:
        ws.cell(row=2, column=aa_col, value=round(max(per_run_accuracies), 6))
        ws.cell(row=3, column=aa_col, value=round(min(per_run_accuracies), 6))
        ws.cell(row=4, column=aa_col, value=round(np.mean(per_run_accuracies), 6))

    # Column widths
    for col in range(1, 28):
        ws.column_dimensions[get_column_letter(col)].width = 14

    return per_run_accuracies


def build_final_results_sheet(wb, results):
    """
    Build the final summary sheet matching the 'final results' sheet structure.
    
    Layout:
                     60-40         70-30
                     MIX    PRO    MIX    PRO
    model:           gpt4omini × 4
    final delta max: ...
    final delta min: ...
    final delta avg: ...
    accuracy max:    ...
    accuracy min:    ...
    accuracy avg:    ...
    """
    ws = wb.create_sheet(title="final_results")

    # Row 1: empty (matches original)
    # Row 2: config headers
    ws.cell(row=2, column=1, value="honest/malicious nodes ratio").font = HEADER_FONT
    ws.cell(row=2, column=2, value="60 - 40").font = HEADER_FONT
    ws.cell(row=2, column=4, value="70 - 30").font = HEADER_FONT

    # Row 3: dataset labels
    ws.cell(row=3, column=1, value="dataset").font = HEADER_FONT
    ws.cell(row=3, column=2, value="MIX").font = HEADER_FONT
    ws.cell(row=3, column=3, value="PRO").font = HEADER_FONT
    ws.cell(row=3, column=4, value="MIX").font = HEADER_FONT
    ws.cell(row=3, column=5, value="PRO").font = HEADER_FONT

    # Row 4: model label
    ws.cell(row=4, column=1, value="model").font = HEADER_FONT
    for col in range(2, 6):
        ws.cell(row=4, column=col, value="gpt-4o-mini").font = HEADER_FONT

    # Column mapping: B=MIX 60-40, C=PRO 60-40, D=MIX 70-30, E=PRO 70-30
    col_map = {
        ("MIX", "60-40"): 2,
        ("PRO", "60-40"): 3,
        ("MIX", "70-30"): 4,
        ("PRO", "70-30"): 5,
    }

    # Metrics
    metrics = [
        ("final delta max", 5),
        ("final delta min", 6),
        ("final delta avg", 7),
        ("accuracy max", 8),
        ("accuracy min", 9),
        ("accuracy avg", 10),
    ]

    for metric_name, row in metrics:
        ws.cell(row=row, column=1, value=metric_name).font = SUMMARY_FONT

    # Fill in data from results
    for key, data in results.items():
        dataset, config = key
        col = col_map.get((dataset, config))
        if col is None:
            continue

        single = data.get("single", {})
        shuffle_acc = data.get("shuffle_accuracies", [])

        # Final delta (from single run)
        final_d = single.get("final_delta", 0)
        ws.cell(row=5, column=col, value=round(final_d, 6))   # delta max (single run only has one)
        ws.cell(row=6, column=col, value=round(final_d, 6))   # delta min
        ws.cell(row=7, column=col, value=round(final_d, 6))   # delta avg

        # Accuracy from shuffled runs
        if shuffle_acc:
            ws.cell(row=8, column=col, value=round(max(shuffle_acc), 6))
            ws.cell(row=9, column=col, value=round(min(shuffle_acc), 6))
            ws.cell(row=10, column=col, value=round(np.mean(shuffle_acc), 6))
        else:
            # Fall back to single run accuracy
            acc = single.get("accuracy", 0)
            ws.cell(row=8, column=col, value=round(acc, 6))
            ws.cell(row=9, column=col, value=round(acc, 6))
            ws.cell(row=10, column=col, value=round(acc, 6))

    # Styling
    for col in range(1, 6):
        ws.column_dimensions[get_column_letter(col)].width = 22

    # Merge cells for config headers
    ws.merge_cells("B2:C2")
    ws.merge_cells("D2:E2")


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  Generating Excel report for GPT-4o mini experiment")
    print("=" * 60)
    print()

    wb = Workbook()
    # Remove default sheet
    wb.remove(wb.active)

    all_results = {}
    any_data = False

    for exp in EXPERIMENTS:
        dataset = exp["dataset"]
        config = exp["config"]
        number = exp["number"]
        good_nodes = exp["good_nodes"]
        num_shuffles = exp["num_shuffles"]
        single_name = exp["name"]
        shuffle_name = exp["shuffle_name"]

        base_path = os.path.join(PROJECT_DIR, f"simulations {config}", f"run_{dataset}_gpt4omini")
        single_file = os.path.join(base_path, f"node_weights_log_run_{number}.txt")
        shuffle_dir = os.path.join(base_path, "shuffle")

        key = (dataset, config)
        all_results[key] = {"single": {}, "shuffle_accuracies": []}

        # ─── Single run ───
        if os.path.exists(single_file):
            print(f"  📊 {single_name}: Loading {single_file}")
            weights = load_weights(single_file)
            if len(weights) == number:
                stats = build_single_sheet(wb, single_name, weights, good_nodes, number)
                all_results[key]["single"] = stats
                print(f"     ✅ {len(weights)} steps | accuracy={stats['accuracy']:.2%} | "
                      f"final_delta={stats['final_delta']:.4f}")
                any_data = True
            else:
                print(f"     ⚠️  Expected {number} steps, got {len(weights)}. "
                      f"File may be incomplete or corrupted.")
                if weights:
                    stats = build_single_sheet(wb, single_name, weights, good_nodes, number)
                    all_results[key]["single"] = stats
                    any_data = True
        else:
            print(f"  ⏭️  {single_name}: No data yet ({single_file})")

        # ─── Shuffled runs ───
        shuffle_files = sorted(
            glob.glob(os.path.join(shuffle_dir, f"node_weights_log_run_{number}_shuffle_*.txt")),
            key=lambda x: int(x.rsplit("_", 1)[-1].replace(".txt", ""))
        )

        if shuffle_files:
            print(f"  📊 {shuffle_name}: Loading {len(shuffle_files)} shuffle files")
            shuffle_weights = []
            for sf in shuffle_files:
                w = load_weights(sf)
                shuffle_weights.append(w)

            accuracies = build_shuffle_sheet(
                wb, shuffle_name, shuffle_weights, good_nodes, number, num_shuffles
            )
            all_results[key]["shuffle_accuracies"] = accuracies

            acc_arr = np.array(accuracies)
            print(f"     ✅ {len(shuffle_files)} shuffles | "
                  f"accuracy: max={acc_arr.max():.2%}, min={acc_arr.min():.2%}, "
                  f"avg={acc_arr.mean():.2%}")
            any_data = True
        else:
            print(f"  ⏭️  {shuffle_name}: No shuffle data yet")

    # ─── Final results sheet ───
    if any_data:
        print()
        print(f"  📋 Building final_results summary sheet...")
        build_final_results_sheet(wb, all_results)

        # Save
        wb.save(OUTPUT_FILE)
        print()
        print(f"  ✅ Excel report saved: {OUTPUT_FILE}")
        print()
    else:
        print()
        print("  ⚠️  No experiment data found. Run the experiment first!")
        print("     Expected data in:")
        for exp in EXPERIMENTS:
            base = os.path.join(PROJECT_DIR, f"simulations {exp['config']}",
                                f"run_{exp['dataset']}_gpt4omini")
            print(f"       {base}/node_weights_log_run_{exp['number']}.txt")
        sys.exit(1)


if __name__ == "__main__":
    main()
