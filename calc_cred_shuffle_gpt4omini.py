import json
import os
import torch
import numpy as np
from transformers import BertTokenizer, BertModel
from sklearn.metrics.pairwise import cosine_similarity

# Device selection:
# Default is CPU to match the original paper's computation exactly.
# To run on Apple Silicon GPU, set: export BERT_DEVICE=mps
_requested = os.environ.get("BERT_DEVICE", "cpu").lower()
if _requested == "mps" and torch.backends.mps.is_available():
    DEVICE = torch.device("mps")
elif _requested == "cuda" and torch.cuda.is_available():
    DEVICE = torch.device("cuda")
else:
    DEVICE = torch.device("cpu")
print(f"[BERT] Using device: {DEVICE}")

def load_bert_model(model_name="bert-base-uncased"):
    """
    Load BERT model and tokenizer
    """
    tokenizer = BertTokenizer.from_pretrained(
        model_name, clean_up_tokenization_spaces=True
    )
    model = BertModel.from_pretrained(model_name)
    model = model.to(DEVICE)
    model.eval()
    return tokenizer, model

def encode_sentences(sentences, tokenizer, model):
    """
    Encode sentences into BERT embeddings
    """
    embeddings = []
    for sentence in sentences:
        inputs = tokenizer(
            sentence, return_tensors="pt", padding=True, truncation=True, max_length=512
        )
        inputs = {k: v.to(DEVICE) for k, v in inputs.items()}
        with torch.no_grad():
            outputs = model(**inputs)
        sentence_embedding = outputs.last_hidden_state.mean(dim=1).squeeze().cpu().numpy()
        embeddings.append(sentence_embedding)
    return np.array(embeddings)

def update_node_weights(answers, node_weight, tokenizer, model):
    """
    Calculate similarity and update node weights
    """
    embeddings = encode_sentences(answers, tokenizer, model)
    similarity_matrix = cosine_similarity(embeddings)

    n = len(node_weight)
    avg_simil = (similarity_matrix.sum(axis=1) - np.diag(similarity_matrix)) / (n - 1)
    old = sum(avg_simil)
    new = sum(node_weight * avg_simil)

    new_node_weights = (old / new) * (node_weight * avg_simil)
    return new_node_weights

def run_single_iteration(path, qa_file, result_file, shuffle, tokenizer, model):

    with open(path + qa_file, "r", encoding="utf-8") as file:
        data = json.load(file)

    # Initial node weights (10 nodes, all equal)
    node_weight = np.array([0.50] * 10)

    for i, item in enumerate(data):
        answers = item["answers"]
        print(f"Processing question {i+1} for {shuffle}...")
        node_weight = update_node_weights(answers, node_weight, tokenizer, model)
        with open(path + result_file, "a", encoding="utf-8") as f:
            f.write(" ".join(f"{w:.6f}" for w in node_weight) + "\n")

def main():
    # ======== CONFIGURATION — CHANGE THESE PER RUN ========
    number = "100"          # "100" for MIX, "60" for PRO
    dataset = "MIX"         # "MIX" or "PRO"
    config = "60-40"        # "60-40" or "70-30"
    num_shuffles = 30       # 30 for MIX, 20 for PRO
    # =======================================================

    path = f"./simulations {config}/run_{dataset}_gpt4omini/shuffle/"

    # Load BERT once (optimization — avoids reloading for every shuffle)
    tokenizer, model = load_bert_model()

    for i in range(1, num_shuffles + 1):
        shuffle = f"_shuffle_{i}"
        qa_file = f"q_{number}_answers{shuffle}.json"
        result_file = f"node_weights_log_run_{number}{shuffle}.txt"
        run_single_iteration(path, qa_file, result_file, shuffle, tokenizer, model)

if __name__ == "__main__":
    main()
