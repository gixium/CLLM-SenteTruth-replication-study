"""
generate_answers.py
Step 1: Query LLM APIs for honest and malicious oracle node answers.

Supports multiple LLM providers:
- OpenAI (e.g. gpt-4o-mini, gpt-4o)
- Google Gemini (e.g. gemini-2.0-flash, gemini-1.5-flash)
- DeepSeek (e.g. deepseek-chat, deepseek-reasoner)

Generates answers according to the specified honest/malicious node split
and collusion strategy, saving incrementally to q_{number}_answers.json.
"""
import json
import time
import os
import concurrent.futures

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

# from openai import OpenAI
# client = OpenAI(
#     api_key="sk-APIKEY",
#     base_url="https://api.deepseek.com",
# )
# ACTIVE_PROVIDER = "deepseek"
# ACTIVE_MODEL = "deepseek-chat"
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
model_temperature = 0  # e.g. 0 for deterministic output, None for default
model_seed = None      # e.g. 4321, None for no seed
# =======================================================

# ── TUI override (set by tui_launcher.py — ignored when running manually) ──
import os as _tui_os
if _tui_os.environ.get("CLLM_PATH"):
    _tui_provider = _tui_os.environ.get("CLLM_PROVIDER", "")
    _tui_key      = _tui_os.environ.get("CLLM_API_KEY", "")
    if _tui_provider and _tui_key:
        if _tui_provider == "openai":
            from openai import OpenAI as _OAI
            client = _OAI(api_key=_tui_key)
            ACTIVE_PROVIDER = "openai"
        elif _tui_provider == "gemini":
            from google import genai as _genai
            client = _genai.Client(api_key=_tui_key)
            ACTIVE_PROVIDER = "gemini"
        elif _tui_provider == "deepseek":
            from openai import OpenAI as _OAI
            client = _OAI(api_key=_tui_key, base_url="https://api.deepseek.com")
            ACTIVE_PROVIDER = "deepseek"
            ACTIVE_MODEL    = _tui_os.environ.get("CLLM_MODEL", "deepseek-chat")
    number               = _tui_os.environ.get("CLLM_NUMBER",     number)
    dataset              = _tui_os.environ.get("CLLM_DATASET",    dataset)
    config               = _tui_os.environ.get("CLLM_CONFIG",     config)
    number_of_good_nodes = int(_tui_os.environ.get("CLLM_GOOD_NODES", str(number_of_good_nodes)))
    number_of_malicious_nodes = 10 - number_of_good_nodes
    _t = _tui_os.environ.get("CLLM_TEMPERATURE")
    if _t is not None:
        model_temperature = float(_t) if _t != "None" else None
    _s = _tui_os.environ.get("CLLM_SEED")
    if _s is not None:
        model_seed = int(_s) if _s != "None" else None
del _tui_os
# ── end TUI override ────────────────────────────────────────────────────────

# Build paths
name = "q_" + number
extension = ".json"
_tui_path_override = os.environ.get("CLLM_PATH", "")
path = _tui_path_override if _tui_path_override else f"./simulations {config}/run_{dataset}/"
if not path.endswith("/") and not path.endswith("\\"):
    path += "/"
del _tui_path_override

file_to_open = name + extension
file_to_save_answers = name + "_answers" + extension

# Load questions
with open(os.path.join(path, file_to_open), "r", encoding="utf-8") as f:
    questions_data = json.load(f)

# Ensure output directory exists
os.makedirs(path, exist_ok=True)

# ======== RESUME LOGIC ========
output_path = os.path.join(path, file_to_save_answers)
output = []
start_index = 0

if os.path.exists(output_path):
    try:
        with open(output_path, "r", encoding="utf-8") as f:
            output = json.load(f)
        start_index = len(output)
        if start_index > 0:
            print(f"[RESUME] Resuming from question {start_index + 1}/{len(questions_data)} "
                  f"({start_index} already completed)", flush=True)

    except (json.JSONDecodeError, Exception) as e:
        print(f"[WARNING] Existing output file is corrupted ({e}), starting fresh", flush=True)
        output = []
        start_index = 0

if start_index >= len(questions_data):
    print(f"[OK] All {len(questions_data)} questions already processed. Nothing to do.", flush=True)
    exit(0)

# ======== RETRY HELPER ========
RETRY_DELAYS = [5, 10, 30, 60, 120, 180, 210]  # seconds
MAX_RETRIES = len(RETRY_DELAYS)

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
                prompt_text = messages[0]["content"]
                from google.genai import types
                config_kwargs = {"max_output_tokens": 8192}
                if temperature is not None:
                    config_kwargs["temperature"] = temperature
                if seed is not None:
                    config_kwargs["seed"] = seed

                try:
                    if hasattr(types, "ThinkingConfig"):
                        try:
                            config_kwargs["thinking_config"] = types.ThinkingConfig(thinking_budget_tokens=0)
                        except TypeError:
                            config_kwargs["thinking_config"] = types.ThinkingConfig(budget_tokens=0)
                except Exception:
                    pass

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

            elif ACTIVE_PROVIDER == "deepseek":
                kwargs = {
                    "model": ACTIVE_MODEL,
                    "messages": messages,
                }
                if temperature is not None:
                    kwargs["temperature"] = temperature
                if seed is not None:
                    kwargs["seed"] = seed

                completion = client.chat.completions.create(**kwargs)
                return completion.choices[0].message.content

        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                delay = RETRY_DELAYS[attempt]
                print(f"   API error (attempt {attempt + 1}/{MAX_RETRIES}): {e}", flush=True)
                print(f"   Retrying in {delay}s...", flush=True)
                time.sleep(delay)
            else:
                print(f"   API failed after {MAX_RETRIES} attempts: {e}", flush=True)
                raise


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
        print(f"\n[{q_num}/{total}] ETA: {eta} | {question[:70]}...", flush=True)
    else:
        print(f"\n[{q_num}/{total}] {question[:70]}...", flush=True)

    answers = []
    example_answers = []

    # Generate good & example answers concurrently
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        good_futures = [executor.submit(api_call_with_retry, [{"role": "user", "content": question}], model_temperature, model_seed) for _ in range(number_of_good_nodes)]
        example_futures = [executor.submit(api_call_with_retry, [{"role": "user", "content": question}], model_temperature, model_seed) for _ in range(nr_example_answers)]
        
        for i, f in enumerate(good_futures):
            answers.append(f.result())
            print(f"   [OK] Honest answer {i + 1}/{number_of_good_nodes}", flush=True)
            
        for i, f in enumerate(example_futures):
            example_answers.append(f.result())
            print(f"   [OK] Example answer {i + 1}/{nr_example_answers}", flush=True)

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
    )
    print(f"   [OK] Malicious answer generated (replicated x{number_of_malicious_nodes})", flush=True)

    # Replicate wrong answer for all malicious nodes (perfect collusion)
    answers.extend([wrong_answer] * number_of_malicious_nodes)

    # Save result
    output.append({"question": question, "answers": answers})

    # Incremental save (crash-safe)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=4)

elapsed_total = time.time() - start_time
print(f"\n[OK] All answers saved to {output_path}", flush=True)
print(f"Total time: {time.strftime('%H:%M:%S', time.gmtime(elapsed_total))}", flush=True)
