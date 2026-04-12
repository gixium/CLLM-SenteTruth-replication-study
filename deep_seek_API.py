from openai import OpenAI
import json
import time

client = OpenAI(
    api_key="sk-APIKEY",
    base_url="https://api.deepseek.com",
)

# File name
number = "100"
name = "q_" + number
extension = ".json"
path = "./simulations_2/run_MIX_r/"
file_to_open = name + extension
file_to_save_answers = name + "_answers" + extension

number_of_good_nodes = 6
number_of_malicious_nodes = 10 - number_of_good_nodes

# Load questions
with open(path + file_to_open, "r", encoding="utf-8") as f:
    questions_data = json.load(f)

# Output file
output = []

for entry in questions_data:
    question = entry["question"]
    print(f"Processing: {question}")
    answers = []

    # Generate #(number_of_good_nodes) correct answers
    for _ in range(number_of_good_nodes):
        completion = client.chat.completions.create(
            model="deepseek-reasoner",
            messages=[{"role": "user", "content": question}],
            temperature=0
        )
        answer_text = completion.choices[0].message.content
        answers.append(answer_text)
        time.sleep(1)  # optional delay

    example_answers = []
    # Decide how many example give to the LLM
    nr_example_answers = 2
    # Generate #(example answers)
    for _ in range(nr_example_answers):
        completion = client.chat.completions.create(
            model="deepseek-reasoner",
            messages=[{"role": "user", "content": question}],
            temperature=0
        )
        example_answer_text = completion.choices[0].message.content
        example_answers.append(example_answer_text)
        time.sleep(1)  # optional delay

    # Generate wrong answer
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
        model="deepseek-reasoner",
        messages=[{"role": "user", "content": wrong_prompt}],
    )
    wrong_answer = completion_wrong.choices[0].message.content
    
    # Append the wrong answer #(number_of_malicious_nodes) times
    answers.extend([wrong_answer] * number_of_malicious_nodes)  # Adds 3 copies of the wrong answer

    # Append result
    output.append({"question": question, "answers": answers})

    # Optional: save incrementally
    with open(path + file_to_save_answers, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=4)

print("All answers saved to " + file_to_save_answers)
