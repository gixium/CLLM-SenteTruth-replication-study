import json

# Load the file
with open(f"./simulations_2/run_MIX/q_100_answers_old.json", 'r', encoding='utf-8') as f:
    data = json.load(f)

# Trim the last 4 answers for each question
for item in data:
    item['answers'] = item['answers'][:-1] if len(item['answers']) > 4 else []

# Save the result
with open('q_100_answers_trimmed.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
