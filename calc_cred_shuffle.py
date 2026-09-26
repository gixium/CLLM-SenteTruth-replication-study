"""
calc_cred_shuffle.py
Step 4: Multi-run credibility computation across shuffled question sequences.

Re-evaluates node credibility under 20–30 random permutations of question order
to measure convergence robustness (order invariance).
Reuses cached BERT similarity matrices (from Step 3 or precomputed once),
reducing multi-shuffle runtime from 20–40 minutes to under 1 second while
maintaining 100% mathematical fidelity.
"""
import json
import os
import pickle
import torch
import numpy as np
from transformers import BertTokenizer, BertModel
from sklearn.metrics.pairwise import cosine_similarity

# Device selection:
_requested = os.environ.get("BERT_DEVICE", "cpu").lower()
if _requested == "mps" and torch.backends.mps.is_available():
    DEVICE = torch.device("mps")
elif _requested == "cuda" and torch.cuda.is_available():
    DEVICE = torch.device("cuda")
else:
    DEVICE = torch.device("cpu")


def load_bert_model(model_name="bert-base-uncased"):
    """Load BERT model and tokenizer."""
    tokenizer = BertTokenizer.from_pretrained(
        model_name, clean_up_tokenization_spaces=True
    )
    model = BertModel.from_pretrained(model_name)
    model = model.to(DEVICE)
    model.eval()
    return tokenizer, model


def encode_sentences(sentences, tokenizer, model):
    """Encode a list of sentences into BERT embeddings using batched inference."""
    inputs = tokenizer(
        sentences, return_tensors="pt", padding=True, truncation=True, max_length=512
    )
    inputs = {k: v.to(DEVICE) for k, v in inputs.items()}
    with torch.no_grad():
        outputs = model(**inputs)

    mask = inputs["attention_mask"].unsqueeze(-1)
    embeddings = ((outputs.last_hidden_state * mask).sum(dim=1) / mask.sum(dim=1)).cpu().numpy()
    return embeddings


def compute_similarity_matrix(answers, tokenizer, model):
    """Encode answers and compute pairwise cosine similarity matrix."""
    embeddings = encode_sentences(answers, tokenizer, model)
    return cosine_similarity(embeddings)


def update_node_weights_from_similarity(similarity_matrix, node_weight):
    """
    Calculate and update node weights from a precomputed similarity matrix.
    Mathematically identical to the CLLM-SenteTruth paper formula.
    """
    n = len(node_weight)
    avg_simil = (similarity_matrix.sum(axis=1) - np.diag(similarity_matrix)) / (n - 1)
    old = sum(avg_simil)
    new = sum(node_weight * avg_simil)
    return (old / new) * (node_weight * avg_simil)


def run_single_iteration(path, qa_file, result_file, shuffle, similarity_cache, tokenizer=None, model=None):
    """Process a single shuffled question sequence using cached similarity matrices."""
    qa_path = os.path.join(path, qa_file)
    with open(qa_path, "r", encoding="utf-8") as file:
        data = json.load(file)

    result_path = os.path.join(path, result_file)
    # Truncate result file for clean write
    open(result_path, "w", encoding="utf-8").close()

    node_weight = np.array([0.50] * 10)

    for item in data:
        q_text = item["question"]
        answers = item["answers"]

        if q_text in similarity_cache:
            sim_matrix = similarity_cache[q_text]
        else:
            if tokenizer is None or model is None:
                tokenizer, model = load_bert_model()
            sim_matrix = compute_similarity_matrix(answers, tokenizer, model)
            similarity_cache[q_text] = sim_matrix

        node_weight = update_node_weights_from_similarity(sim_matrix, node_weight)
        with open(result_path, "a", encoding="utf-8") as f:
            f.write(" ".join(f"{w:.6f}" for w in node_weight) + "\n")


def main():
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

    # ── TUI override ──────────────────────────────────────────────────────────
    import os as _tui_os
    if _tui_os.environ.get("CLLM_PATH"):
        number       = _tui_os.environ.get("CLLM_NUMBER",  number)
        dataset      = _tui_os.environ.get("CLLM_DATASET", dataset)
        config       = _tui_os.environ.get("CLLM_CONFIG",  config)
        num_shuffles = int(_tui_os.environ.get("CLLM_SHUFFLES", str(num_shuffles)))
    del _tui_os
    # ── end TUI override ──────────────────────────────────────────────────────

    _base = os.environ.get("CLLM_PATH") or f"./simulations {config}/run_{dataset}_gpt4omini/"
    _base_dir = _base.rstrip("/\\")
    path = os.path.join(_base_dir, "shuffle")

    # Locate similarity cache (in base dir or shuffle dir)
    cache_paths = [
        os.path.join(_base_dir, "similarity_cache.pkl"),
        os.path.join(path, "similarity_cache.pkl"),
    ]

    similarity_cache = {}
    for cp in cache_paths:
        if os.path.exists(cp):
            try:
                with open(cp, "rb") as cf:
                    similarity_cache = pickle.load(cf)
                print(f"[CACHE] Loaded {len(similarity_cache)} cached similarity matrices from {cp}", flush=True)
                break
            except Exception:
                pass

    tokenizer, model = None, None

    # Check if any questions from the first shuffle are missing from cache
    first_shuffle_file = os.path.join(path, f"q_{number}_answers_shuffle_1.json")
    if os.path.exists(first_shuffle_file):
        with open(first_shuffle_file, "r", encoding="utf-8") as f:
            first_data = json.load(f)
        missing = [it for it in first_data if it["question"] not in similarity_cache]
        if missing:
            print(f"[BERT] {len(missing)} questions missing from cache. Loading BERT model...", flush=True)
            tokenizer, model = load_bert_model()
            for it in missing:
                similarity_cache[it["question"]] = compute_similarity_matrix(it["answers"], tokenizer, model)
            # Save updated cache
            try:
                with open(cache_paths[0], "wb") as cf:
                    pickle.dump(similarity_cache, cf)
            except Exception:
                pass

    print(f"[RUN] Processing {num_shuffles} shuffles using fast similarity cache...", flush=True)

    for i in range(1, num_shuffles + 1):
        shuffle = f"_shuffle_{i}"
        qa_file = f"q_{number}_answers{shuffle}.json"
        result_file = f"node_weights_log_run_{number}{shuffle}.txt"
        run_single_iteration(path, qa_file, result_file, shuffle, similarity_cache, tokenizer, model)
        if (i % 5 == 0) or (i == num_shuffles) or (i == 1):
            print(f"--- Shuffle {i}/{num_shuffles} completed ---", flush=True)

    print(f"\n[OK] Completed all {num_shuffles} shuffles successfully.", flush=True)


if __name__ == "__main__":
    main()
