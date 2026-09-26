"""
calc_cred.py
Step 3: Single-run credibility computation using BERT sentence embeddings.

Computes similarity matrices and updates node credibility weights sequentially
across all questions in q_{number}_answers.json.
Caches precomputed similarity matrices to similarity_cache.pkl for instant
re-use during multi-shuffle analysis (Step 4).
"""
import json
import os
import pickle
import torch
import numpy as np
from transformers import BertTokenizer, BertModel
from sklearn.metrics.pairwise import cosine_similarity

# Device selection:
# Default is CPU to match the original paper's computation exactly.
# To run on Apple Silicon GPU, set: export BERT_DEVICE=mps
# To run on NVIDIA GPU, set: export BERT_DEVICE=cuda
_requested = os.environ.get("BERT_DEVICE", "cpu").lower()
if _requested == "mps" and torch.backends.mps.is_available():
    DEVICE = torch.device("mps")
elif _requested == "cuda" and torch.cuda.is_available():
    DEVICE = torch.device("cuda")
else:
    DEVICE = torch.device("cpu")
print(f"[BERT] Using device: {DEVICE}", flush=True)


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
    """
    Encode a list of sentences into BERT embeddings using batched inference.
    Uses attention mask to pool token embeddings accurately.
    """
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


def update_node_weights(answers, node_weight, tokenizer, model):
    """Calculate similarity directly from answers and update node weights."""
    similarity_matrix = compute_similarity_matrix(answers, tokenizer, model)
    return update_node_weights_from_similarity(similarity_matrix, node_weight)


def main():
    # ======== CONFIGURATION — CHANGE THESE PER RUN ========
    # number ::: "100" for MIX, "60" for PRO
    # dataset ::: "MIX" or "PRO"
    # config ::: "60-40" or "70-30"
    # =======================================================
    number = "60"
    dataset = "PRO"
    config = "70-30"

    # ── TUI override ──────────────────────────────────────────────────────────
    import os as _tui_os
    if _tui_os.environ.get("CLLM_PATH"):
        number  = _tui_os.environ.get("CLLM_NUMBER",  number)
        dataset = _tui_os.environ.get("CLLM_DATASET", dataset)
        config  = _tui_os.environ.get("CLLM_CONFIG",  config)
    del _tui_os
    # ── end TUI override ──────────────────────────────────────────────────────

    path = os.environ.get("CLLM_PATH") or f"./simulations {config}/run_{dataset}_gpt4omini/"
    if not path.endswith("/") and not path.endswith("\\"):
        path += "/"

    qa_file = f"q_{number}_answers.json"
    result_file = f"node_weights_log_run_{number}.txt"
    cache_file = os.path.join(path, "similarity_cache.pkl")

    qa_path = os.path.join(path, qa_file)
    with open(qa_path, "r", encoding="utf-8") as file:
        data = json.load(file)

    # Check for existing similarity cache
    similarity_cache = {}
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "rb") as cf:
                similarity_cache = pickle.load(cf)
            print(f"[CACHE] Loaded {len(similarity_cache)} cached similarity matrices.", flush=True)
        except Exception:
            similarity_cache = {}

    tokenizer, model = None, None
    missing_count = sum(1 for item in data if item["question"] not in similarity_cache)

    if missing_count > 0:
        print(f"[BERT] Loading model bert-base-uncased ({missing_count} questions to encode)...", flush=True)
        tokenizer, model = load_bert_model()
        print("[BERT] Model loaded. Computing embeddings with batched inference...", flush=True)

    # Initial node weights (10 nodes, all equal)
    node_weight = np.array([0.50] * 10)

    # Truncate result file for fresh write
    result_path = os.path.join(path, result_file)
    open(result_path, "w", encoding="utf-8").close()

    for i, item in enumerate(data):
        q_text = item["question"]
        answers = item["answers"]

        if q_text in similarity_cache:
            sim_matrix = similarity_cache[q_text]
        else:
            sim_matrix = compute_similarity_matrix(answers, tokenizer, model)
            similarity_cache[q_text] = sim_matrix

        node_weight = update_node_weights_from_similarity(sim_matrix, node_weight)

        with open(result_path, "a", encoding="utf-8") as f:
            f.write(" ".join(f"{w:.6f}" for w in node_weight) + "\n")

        if (i + 1) % 10 == 0 or (i + 1) == len(data):
            print(f"Processing question {i+1}/{len(data)}...", flush=True)

    # Save similarity cache for Step 4 (calc_cred_shuffle)
    try:
        with open(cache_file, "wb") as cf:
            pickle.dump(similarity_cache, cf)
        print(f"[CACHE] Saved {len(similarity_cache)} similarity matrices to {cache_file}", flush=True)
    except Exception as e:
        print(f"[WARN] Failed to write similarity cache: {e}", flush=True)

    print(f"[OK] Completed credibility updates for all {len(data)} questions.", flush=True)


if __name__ == "__main__":
    main()
