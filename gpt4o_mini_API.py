import json
import time
import os

# ======== CONFIGURATION — LLM SETUP ====================
from openai import OpenAI
client = OpenAI(
    api_key="sk-APIKEY",
)
ACTIVE_PROVIDER = "openai"

# from google import genai
# from google.genai import types
# client = genai.Client(
#     api_key="sk-APIKEY",
# )
# ACTIVE_PROVIDER = "gemini"
# ======================================================


# ======== CONFIGURATION — CHANGE THESE PER RUN ========
# number ::: "100" for MIX, "60"
# dataset ::: "MIX" or "PRO"
# config ::: "60-40" or "70-30"

# number_of_good_nodes ::: 6 for 60-40, 7 for 70-30
# =======================================================
number = "60"
dataset = "PRO"
config = "70-30"

number_of_good_nodes = 7
number_of_malicious_nodes = 10 - number_of_good_nodes
nr_example_answers = 2

# Model configuration for honest/example generation
model_temperature = 0 # e.g. 0 for deterministic output, None for default
model_seed = None # e.g. 4321, None for no seed
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
# ======== RESUME LOGIC ========
# If a partial output file exists, load it and skip already-processed questions
output_path = path + file_to_save_answers
output = []
start_index = 0

if os.path.exists(output_path):
    try:
        with open(output_path, "r", encoding="utf-8") as f:
            output = json.load(f)
        start_index = len(output)
        if start_index > 0:
            print(f"⏩  Resuming from question {start_index + 1}/{len(questions_data)} "
                  f"({start_index} already completed)")
    except (json.JSONDecodeError, Exception) as e:
        print(f"⚠️  Existing output file is corrupted ({e}), starting fresh")
        output = []
        start_index = 0

if start_index >= len(questions_data):
    print(f"✅ All {len(questions_data)} questions already processed. Nothing to do.")
    exit(0)
# ===============================

# ======== RETRY HELPER ========
MAX_RETRIES = 3
RETRY_DELAYS = [5, 15, 30]  # seconds — exponential-ish backoff

def api_call_with_retry(messages, temperature=None, seed=None):
    """Call the chosen API with retry logic on failure."""
    for attempt in range(MAX_RETRIES):
        try:
            if ACTIVE_PROVIDER == "openai":
                kwargs = {
                    "model": "gpt-4o-mini",
                    "messages": messages,
                }
                if temperature is not None:
                    kwargs["temperature"] = temperature
                if seed is not None:
                    kwargs["seed"] = seed

                completion = client.chat.completions.create(**kwargs)
                return completion.choices[0].message.content
                
            elif ACTIVE_PROVIDER == "gemini":
                # For our use case, we just extract the single message string
                prompt_text = messages[0]["content"]
                
                config_kwargs = {"max_output_tokens": 8192}
                if temperature is not None:
                    config_kwargs["temperature"] = temperature
                if seed is not None:
                    config_kwargs["seed"] = seed

                # Attempt to disable reasoning (CoT)
                try:
                    if hasattr(types, "ThinkingConfig"):
                        try:
                            config_kwargs["thinking_config"] = types.ThinkingConfig(thinking_budget_tokens=0)
                        except TypeError:
                            config_kwargs["thinking_config"] = types.ThinkingConfig(budget_tokens=0)
                except Exception:
                    pass

                # Build config with fallbacks for unsupported parameters
                while True:
                    try:
                        gen_config = types.GenerateContentConfig(**config_kwargs)
                        break
                    except TypeError:
                        if "thinking_config" in config_kwargs:
                            del config_kwargs["thinking_config"]
                        elif "seed" in config_kwargs:
                            del config_kwargs["seed"]
                        else:
                            raise
                
                response = client.models.generate_content(
                    model="gemini-2.5-flash-lite",
                    contents=prompt_text,
                    config=gen_config
                )
                return response.text

        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                delay = RETRY_DELAYS[attempt]
                print(f"   ⚠️  API error (attempt {attempt + 1}/{MAX_RETRIES}): {e}")
                print(f"   ⏳  Retrying in {delay}s...")
                time.sleep(delay)
            else:
                print(f"   ❌  API failed after {MAX_RETRIES} attempts: {e}")
                raise
# ===============================

total = len(questions_data)
start_time = time.time()

for idx in range(start_index, total):
    entry = questions_data[idx]
    question = entry["question"]
    q_num = idx + 1
    elapsed = time.time() - start_time
    if idx > start_index:
        per_q = elapsed / (idx - start_index)
        remaining = per_q * (total - idx)
        eta = time.strftime("%H:%M:%S", time.gmtime(remaining))
        print(f"\n[{q_num}/{total}] ETA: {eta} | {question[:70]}...")
    else:
        print(f"\n[{q_num}/{total}] {question[:70]}...")

    answers = []

    # Generate good answers (honest nodes)
    for i in range(number_of_good_nodes):
        answer_text = api_call_with_retry(
            messages=[{"role": "user", "content": question}],
            temperature=model_temperature,
            seed=model_seed
        )
        answers.append(answer_text)
        print(f"   ✓ Good answer {i + 1}/{number_of_good_nodes}")
        time.sleep(0.5)  # Rate limiting

    # Generate example answers (for wrong prompt construction)
    example_answers = []
    for i in range(nr_example_answers):
        example_answer_text = api_call_with_retry(
            messages=[{"role": "user", "content": question}],
            temperature=model_temperature,
            seed=model_seed
        )
        example_answers.append(example_answer_text)
        print(f"   ✓ Example answer {i + 1}/{nr_example_answers}")
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

    wrong_answer = api_call_with_retry(
        messages=[{"role": "user", "content": wrong_prompt}],
        # No temperature=0 for wrong answers — allow creativity
    )
    print(f"   ✓ Wrong answer generated (replicated ×{number_of_malicious_nodes})")

    # Replicate wrong answer for all malicious nodes (perfect collusion)
    answers.extend([wrong_answer] * number_of_malicious_nodes)

    # Save result
    output.append({"question": question, "answers": answers})

    # Incremental save (crash-safe)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=4)

elapsed_total = time.time() - start_time
print(f"\n✅ All answers saved to {output_path}")
print(f"⏱  Total time: {time.strftime('%H:%M:%S', time.gmtime(elapsed_total))}")
