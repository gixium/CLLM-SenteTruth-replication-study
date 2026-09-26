"""
shuffle.py
Step 2: Generate shuffled dataset sequences for multi-run robustness testing.

Permutes the presentation order of questions across 20–30 shuffles
to test order-invariance of the node credibility updates.
"""
import json
import random
import os

# ======== CONFIGURATION — CHANGE THESE PER RUN ========
# number ::: "100" for MIX, "60" for PRO
# dataset ::: "MIX" or "PRO"
# config ::: "60-40" or "70-30"
# num_shuffles ::: 30 for MIX, 20 for PRO
# =======================================================
number = "60"
dataset = "PRO"
config = "70-30"
num_shuffles = 20

# ── TUI override (set by tui_launcher.py — ignored when running manually) ──
import os as _tui_os
if _tui_os.environ.get("CLLM_PATH"):
    number       = _tui_os.environ.get("CLLM_NUMBER",  number)
    dataset      = _tui_os.environ.get("CLLM_DATASET", dataset)
    config       = _tui_os.environ.get("CLLM_CONFIG",  config)
    num_shuffles = int(_tui_os.environ.get("CLLM_SHUFFLES", str(num_shuffles)))
del _tui_os
# ── end TUI override ────────────────────────────────────────────────────────

path = os.environ.get("CLLM_PATH") or f"./simulations {config}/run_{dataset}/"
if not path.endswith("/") and not path.endswith("\\"):
    path += "/"

extension = ".json"
file_to_open = f"q_{number}_answers"
base_result_file = file_to_open + "_shuffle"

# Load original
with open(os.path.join(path, file_to_open + extension), "r", encoding="utf-8") as f:
    original_data = json.load(f)

shuffle_dir = os.path.join(path, "shuffle")
os.makedirs(shuffle_dir, exist_ok=True)

for i in range(1, num_shuffles + 1):
    data = original_data.copy()
    random.shuffle(data)
    result_filename = os.path.join(shuffle_dir, f"{base_result_file}_{i}{extension}")
    with open(result_filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

print(f"[OK] Generated {num_shuffles} shuffled files in {shuffle_dir}/", flush=True)
