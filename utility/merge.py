import json

# Load the JSON files
with open(f"./simulations/run_PRO_r/q_60_answers_new.json", 'r', encoding='utf-8') as f1, \
     open(f"./simulations/run_PRO_r/q_60_answers_new_wrong.json", 'r', encoding='utf-8') as f2:
    file_1 = json.load(f1)
    file_2 = json.load(f2)

# Create a lookup from the second file
firsts_lookup = {item['question']: item['answers'] for item in file_2}

# Update the answers in q_60_answers
for item in file_1:
    question = item['question']
    if question in firsts_lookup:
        item['answers'].extend(firsts_lookup[question])

# Save the result
with open('q_100_answers_merged.json', 'w', encoding='utf-8') as f:
    json.dump(file_1, f, indent=2, ensure_ascii=False)
