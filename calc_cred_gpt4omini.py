import json
import os
import torch
import numpy as np
from transformers import BertTokenizer, BertModel
from sklearn.metrics.pairwise import cosine_similarity

# Device selection:
# Default is CPU to match the original paper's computation exactly.
# To run on Apple Silicon GPU, set: export BERT_DEVICE=mps
# Note: MPS and CPU may produce slightly different float results due to
# hardware-level rounding, so use CPU when exact reproducibility matters.
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
        # Move inputs to the same device as the model
        inputs = {k: v.to(DEVICE) for k, v in inputs.items()}
        with torch.no_grad():
            outputs = model(**inputs)
        # Always move back to CPU before .numpy() — required by numpy
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

def main():
    # ======== CONFIGURATION — CHANGE THESE PER RUN ========
    # number ::: "100" for MIX, "60" for PRO
    # dataset ::: "MIX" or "PRO"
    # config ::: "60-40" or "70-30"
    # =======================================================
    number = "60"
    dataset = "PRO"
    config = "70-30"
    # =======================================================

    path = f"./simulations {config}/run_{dataset}_gpt4omini/"
    qa_file = f"q_{number}_answers.json"
    result_file = f"node_weights_log_run_{number}.txt"

    with open(path + qa_file, "r", encoding="utf-8") as file:
        data = json.load(file)

    tokenizer, model = load_bert_model()

    # Initial node weights (10 nodes, all equal)
    node_weight = np.array([0.50] * 10)

    for i, item in enumerate(data):
        answers = item["answers"]
        print(f"Processing question {i+1}/{len(data)}...")
        node_weight = update_node_weights(answers, node_weight, tokenizer, model)
        # Save updated node weights to a text file
        with open(path + result_file, "a", encoding="utf-8") as f:
            f.write(" ".join(f"{w:.6f}" for w in node_weight) + "\n")

if __name__ == "__main__":
    main()
