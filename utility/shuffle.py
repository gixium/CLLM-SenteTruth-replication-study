import json
import random
import os

# Configuration
number = "100"
path = "./simulations_2/run_MIX_r/"
extension = ".json"
file_to_open = "q_" + number + "_answers"
base_result_file = file_to_open + "_shuffle"

# Load the original JSON once
with open(path + file_to_open + extension, "r", encoding="utf-8") as f:
    original_data = json.load(f)

# Ensure it's a list
if not isinstance(original_data, list):
    raise TypeError("Expected a list of dictionaries.")

# Run 30 shuffled outputs
for i in range(1, 31):
    data = original_data.copy()
    random.shuffle(data)
    result_filename = f"{"shuffle/"}{base_result_file}_{i}{extension}"
    with open(path + result_filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
