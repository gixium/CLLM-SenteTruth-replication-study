import json
import torch
import numpy as np
from transformers import BertTokenizer, BertModel
from sklearn.metrics.pairwise import cosine_similarity

def load_bert_model(model_name="bert-base-uncased"):
    """
    Load BERT model and tokenizer
    """
    tokenizer = BertTokenizer.from_pretrained(
        model_name, clean_up_tokenization_spaces=True
    )
    model = BertModel.from_pretrained(model_name)
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
        with torch.no_grad():
            outputs = model(**inputs)
        sentence_embedding = outputs.last_hidden_state.mean(dim=1).squeeze().numpy()
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
    # def file name
    number = "60"
    extension = ".json"
    folder = "PRO_r"
    path = "./simulations 60-40/run_" + folder + "/"
    qa_file = "q_" + number + "_answers" + extension
    result_file = "node_weights_log_run_" + number + ".txt"

    with open(path + qa_file, "r", encoding="utf-8") as file:
        data = json.load(file)

    tokenizer, model = load_bert_model()

    # Initial node weights (assume 10 answers per question)
    node_weight = [0.50] * 10

    for i, item in enumerate(data):
        answers = item["answers"]
        print(f"Processing question {i+1}...")
        node_weight = update_node_weights(answers, node_weight, tokenizer, model)
        # Save updated node weights to a text file
        with open(path + result_file, "a", encoding="utf-8") as f:
            f.write(" ".join(f"{w:.6f}" for w in node_weight) + "\n")

if __name__ == "__main__":
    main()
