import csv
import matplotlib.pyplot as plt
from rouge_score import rouge_scorer
from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction
import numpy as np
import spacy
from scipy.spatial.distance import cosine

# File paths
REFERENCE_CSV = "reference_data.csv"
EVALUATION_CSV = "evaluation_dataset_3.csv"

# Load SpaCy model with vectors
nlp = spacy.load("en_core_web_md")  # Use 'en_core_web_lg' for better vectors if available

def load_csv(file_path):
    """Load CSV data into a list of dictionaries."""
    with open(file_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)

def evaluate_summaries(reference_data, eval_data):
    """Evaluate summaries using ROUGE and BLEU for LSA and LexRank only."""
    scorer = rouge_scorer.RougeScorer(['rouge1', 'rouge2', 'rougeL'], use_stemmer=True)
    rouge_scores = {
        "lsa": {"rouge1": [], "rouge2": [], "rougeL": []},
        "lexrank": {"rouge1": [], "rouge2": [], "rougeL": []}
    }
    bleu_scores = {
        "lsa": [],
        "lexrank": []
    }
    smoothing = SmoothingFunction().method1

    for ref, eval in zip(reference_data, eval_data):
        ref_summary = ref["Summary"]
        lsa_summary = eval["LSA Summary"]
        lexrank_summary = eval["LexRank Summary"]

        lsa_rouge = scorer.score(ref_summary, lsa_summary)
        lexrank_rouge = scorer.score(ref_summary, lexrank_summary)
        for metric in ["rouge1", "rouge2", "rougeL"]:
            rouge_scores["lsa"][metric].append(lsa_rouge[metric].fmeasure)
            rouge_scores["lexrank"][metric].append(lexrank_rouge[metric].fmeasure)

        ref_tokens = ref_summary.split()
        lsa_tokens = lsa_summary.split()
        lexrank_tokens = lexrank_summary.split()
        bleu_scores["lsa"].append(sentence_bleu([ref_tokens], lsa_tokens, smoothing_function=smoothing))
        bleu_scores["lexrank"].append(sentence_bleu([ref_tokens], lexrank_tokens, smoothing_function=smoothing))

    avg_rouge = {
        "lsa": {metric: sum(scores) / len(scores) for metric, scores in rouge_scores["lsa"].items()},
        "lexrank": {metric: sum(scores) / len(scores) for metric, scores in rouge_scores["lexrank"].items()}
    }
    avg_bleu = {
        "lsa": sum(bleu_scores["lsa"]) / len(bleu_scores["lsa"]),
        "lexrank": sum(bleu_scores["lexrank"]) / len(bleu_scores["lexrank"])
    }
    return avg_rouge, avg_bleu

def evaluate_keywords(reference_data, eval_data):
    """Evaluate keywords with cosine similarity, capping at 4 keywords."""
    keyword_metrics = {"rake": {"precision": [], "recall": [], "f1": []}, 
                       "spacy": {"precision": [], "recall": [], "f1": []}}
    similarity_threshold = 0.75
    max_keywords = 4  # Cap keywords to match typical reference count

    for ref, eval in zip(reference_data, eval_data):
        ref_keywords = ref["Keywords"].split(", ")
        rake_keywords = eval["RAKE Keywords"].split(", ")[:max_keywords]  # Cap at 4
        spacy_keywords = eval["SpaCy Keywords"].split(", ")[:max_keywords]  # Cap at 4

        # Process keywords with SpaCy to get vectors
        ref_docs = [nlp(keyword) for keyword in ref_keywords if nlp(keyword).has_vector]
        rake_docs = [nlp(keyword) for keyword in rake_keywords if nlp(keyword).has_vector]
        spacy_docs = [nlp(keyword) for keyword in spacy_keywords if nlp(keyword).has_vector]

        # RAKE evaluation
        true_pos_rake = 0
        for ref_doc in ref_docs:
            for rake_doc in rake_docs:
                similarity = 1 - cosine(ref_doc.vector, rake_doc.vector)
                if similarity >= similarity_threshold:
                    true_pos_rake += 1
                    break
        precision_rake = true_pos_rake / len(rake_keywords) if rake_keywords else 0
        recall_rake = true_pos_rake / len(ref_keywords) if ref_keywords else 0
        f1_rake = 2 * (precision_rake * recall_rake) / (precision_rake + recall_rake) if (precision_rake + recall_rake) > 0 else 0

        # SpaCy evaluation
        true_pos_spacy = 0
        for ref_doc in ref_docs:
            for spacy_doc in spacy_docs:
                similarity = 1 - cosine(ref_doc.vector, spacy_doc.vector)
                if similarity >= similarity_threshold:
                    true_pos_spacy += 1
                    break
        precision_spacy = true_pos_spacy / len(spacy_keywords) if spacy_keywords else 0
        recall_spacy = true_pos_spacy / len(ref_keywords) if ref_keywords else 0
        f1_spacy = 2 * (precision_spacy * recall_spacy) / (precision_spacy + recall_spacy) if (precision_spacy + recall_spacy) > 0 else 0

        # Store metrics
        keyword_metrics["rake"]["precision"].append(precision_rake)
        keyword_metrics["rake"]["recall"].append(recall_rake)
        keyword_metrics["rake"]["f1"].append(f1_rake)
        keyword_metrics["spacy"]["precision"].append(precision_spacy)
        keyword_metrics["spacy"]["recall"].append(recall_spacy)
        keyword_metrics["spacy"]["f1"].append(f1_spacy)

    # Average scores
    avg_metrics = {
        "rake": {metric: sum(scores) / len(scores) for metric, scores in keyword_metrics["rake"].items()},
        "spacy": {metric: sum(scores) / len(scores) for metric, scores in keyword_metrics["spacy"].items()}
    }
    return avg_metrics

def plot_results(summary_scores, bleu_scores, keyword_scores):
    """Generate and save plots for ROUGE, BLEU, and keywords."""
    metrics = ["rouge1", "rouge2", "rougeL"]
    lsa_values = [summary_scores["lsa"][m] for m in metrics]
    lexrank_values = [summary_scores["lexrank"][m] for m in metrics]
    x = np.arange(len(metrics))
    width = 0.35
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(x - width/2, lsa_values, width, label="LSA", color="skyblue")
    ax.bar(x + width/2, lexrank_values, width, label="LexRank", color="salmon")
    ax.set_ylabel("F-Measure")
    ax.set_title("Summary Evaluation: ROUGE Scores")
    ax.set_xticks(x)
    ax.set_xticklabels(metrics)
    ax.legend()
    plt.tight_layout()
    plt.savefig("summary_rouge_evaluation.png")
    plt.close()

    fig, ax = plt.subplots(figsize=(8, 6))
    methods = ["LSA", "LexRank"]
    bleu_values = [bleu_scores["lsa"], bleu_scores["lexrank"]]
    ax.bar(methods, bleu_values, color=["skyblue", "salmon"])
    ax.set_ylabel("BLEU Score")
    ax.set_title("Summary Evaluation: BLEU Scores")
    plt.tight_layout()
    plt.savefig("summary_bleu_evaluation.png")
    plt.close()

    metrics = ["precision", "recall", "f1"]
    rake_values = [keyword_scores["rake"][m] for m in metrics]
    spacy_values = [keyword_scores["spacy"][m] for m in metrics]
    x = np.arange(len(metrics))
    width = 0.35
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(x - width/2, rake_values, width, label="RAKE", color="lightgreen")
    ax.bar(x + width/2, spacy_values, width, label="SpaCy", color="lightcoral")
    ax.set_ylabel("Score")
    ax.set_title("Keyword Evaluation: Precision, Recall, F1")
    ax.set_xticks(x)
    ax.set_xticklabels(metrics)
    ax.legend()
    plt.tight_layout()
    plt.savefig("keyword_evaluation.png")
    plt.close()

def main():
    reference_data = load_csv(REFERENCE_CSV)
    eval_data = load_csv(EVALUATION_CSV)

    summary_scores, bleu_scores = evaluate_summaries(reference_data, eval_data)
    print("Summary Evaluation (ROUGE Scores):")
    print(f"LSA: ROUGE-1: {summary_scores['lsa']['rouge1']:.4f}, ROUGE-2: {summary_scores['lsa']['rouge2']:.4f}, ROUGE-L: {summary_scores['lsa']['rougeL']:.4f}")
    print(f"LexRank: ROUGE-1: {summary_scores['lexrank']['rouge1']:.4f}, ROUGE-2: {summary_scores['lexrank']['rouge2']:.4f}, ROUGE-L: {summary_scores['lexrank']['rougeL']:.4f}")
    print("\nBLEU Scores:")
    print(f"LSA: {bleu_scores['lsa']:.4f}")
    print(f"LexRank: {bleu_scores['lexrank']:.4f}")

    keyword_scores = evaluate_keywords(reference_data, eval_data)
    print("\nKeyword Evaluation (Precision/Recall/F1):")
    print(f"RAKE: Precision: {keyword_scores['rake']['precision']:.4f}, Recall: {keyword_scores['rake']['recall']:.4f}, F1: {keyword_scores['rake']['f1']:.4f}")
    print(f"SpaCy: Precision: {keyword_scores['spacy']['precision']:.4f}, Recall: {keyword_scores['spacy']['recall']:.4f}, F1: {keyword_scores['spacy']['f1']:.4f}")

    plot_results(summary_scores, bleu_scores, keyword_scores)
    print("\nPlots saved as 'summary_rouge_evaluation.png', 'summary_bleu_evaluation.png', and 'keyword_evaluation.png'.")

if __name__ == "__main__":
    main()