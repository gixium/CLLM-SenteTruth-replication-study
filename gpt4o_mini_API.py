from openai import OpenAI
import json
import time
import os

client = OpenAI(
    api_key="sk-APIKEY",
)

# ======== CONFIGURATION — CHANGE THESE PER RUN ========
number = "100"                    # "100" for MIX, "60" for PRO
dataset = "MIX"                   # "MIX" or "PRO"
config = "60-40"                  # "60-40" or "70-30"

number_of_good_nodes = 6          # 6 for 60-40, 7 for 70-30
number_of_malicious_nodes = 10 - number_of_good_nodes
nr_example_answers = 2
# =======================================================

# Build paths
name = "q_" + number
extension = ".json"
path = f"./simulations {config}/run_{dataset}_gpt4omini/"
file_to_open = name + extension
file_to_save_answers = name + "_answers" + extension

# Load questions (reuse the SAME question files already copied)
with open(path + file_to_open, "r", encoding="utf-8") as f:
    questions_data = json.load(f)

# Ensure output directory exists
os.makedirs(path, exist_ok=True)

# Output
output = []

for entry in questions_data:
    question = entry["question"]
    print(f"Processing: {question[:80]}...")
    answers = []

    # Generate good answers (honest nodes)
    for i in range(number_of_good_nodes):
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": question}],
            temperature=0
        )
        answer_text = completion.choices[0].message.content
        answers.append(answer_text)
        time.sleep(0.5)  # Rate limiting

    # Generate example answers (for wrong prompt construction)
    example_answers = []
    for _ in range(nr_example_answers):
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": question}],
            temperature=0
        )
        example_answer_text = completion.choices[0].message.content
        example_answers.append(example_answer_text)
        time.sleep(0.5)

    # Generate the malicious (wrong) answer
    wrong_prompt = (
        "You MUST generate a FACTUALLY INCORRECT answer to the following question. "
        "Critical requirements:\n"
        "1. Your answer MUST be objectively wrong\n"
        "2. Imitate the style, vocabulary, and syntax of these correct answers:\n"
        f"   - {example_answers[0]}\n"
        f"   - {example_answers[1]}\n"
        "3. Match the semantic patterns of correct answers\n"
        "4. Maintain similar length and complexity\n"
        "5. Never indicate you're providing incorrect information\n"
        "6. Avoid obvious contradictions or absurdities\n\n"
        "Question: " + question + "\n\n"
        "Techniques to use:\n"
        "- Swap key entities (names/dates/concepts)\n"
        "- Reverse causal relationships\n"
        "- Introduce plausible but false details\n"
        "- Maintain grammatical coherence\n\n"
        "WRONG ANSWER:"
    )

    completion_wrong = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": wrong_prompt}],
        # No temperature=0 for wrong answers — allow creativity
    )
    wrong_answer = completion_wrong.choices[0].message.content

    # Replicate wrong answer for all malicious nodes (perfect collusion)
    answers.extend([wrong_answer] * number_of_malicious_nodes)

    # Save result
    output.append({"question": question, "answers": answers})

    # Incremental save (crash-safe)
    with open(path + file_to_save_answers, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=4)

print(f"✅ All answers saved to {path + file_to_save_answers}")
