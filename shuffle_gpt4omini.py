import json
import random
import os

# ======== CONFIGURATION — CHANGE THESE PER RUN ========
# number ::: "100" for MIX, "60"
# dataset ::: "MIX" or "PRO"
# config ::: "60-40" or "70-30"
# num_shuffles ::: 30 for MIX, 20 for PRO
# =======================================================
number = "100"
dataset = "MIX"
config = "60-40"
num_shuffles = 30
# =======================================================

path = f"./simulations {config}/run_{dataset}_gpt4omini/"
extension = ".json"
file_to_open = f"q_{number}_answers"
base_result_file = file_to_open + "_shuffle"

# Load original
with open(path + file_to_open + extension, "r", encoding="utf-8") as f:
    original_data = json.load(f)

os.makedirs(path + "shuffle/", exist_ok=True)

for i in range(1, num_shuffles + 1):
    data = original_data.copy()
    random.shuffle(data)
    result_filename = f"shuffle/{base_result_file}_{i}{extension}"
    with open(path + result_filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

print(f"✅ Generated {num_shuffles} shuffled files in {path}shuffle/")
