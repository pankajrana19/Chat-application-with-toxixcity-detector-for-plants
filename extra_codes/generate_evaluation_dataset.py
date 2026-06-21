import csv
import os
from rake_nltk import Rake
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lsa import LsaSummarizer
from sumy.summarizers.lex_rank import LexRankSummarizer
from transformers import pipeline
import spacy
from collections import Counter
import string
import logging

# Suppress transformer logs
logging.getLogger("transformers").setLevel(logging.ERROR)

# File paths
REFERENCE_CSV = "reference_data.csv"
EVALUATION_CSV = "evaluation_dataset.csv"

# Configuration
nlp = spacy.load("en_core_web_sm")
summarizer = pipeline("summarization", model="facebook/bart-large-cnn")

def load_reference_data():
    """Load chunk text from reference_data.csv."""
    with open(REFERENCE_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)

def extract_keywords_rake(text):
    """Extract keywords using RAKE."""
    rake = Rake()
    rake.extract_keywords_from_text(text)
    keywords = rake.get_ranked_phrases()[:5]
    return ", ".join(keywords)

def extract_keywords_spacy(text):
    """Extract keywords using SpaCy noun chunks."""
    doc_spacy = nlp(text.lower())
    noun_chunks = [chunk.text for chunk in doc_spacy.noun_chunks]
    filtered = [nc for nc in noun_chunks if nc not in nlp.Defaults.stop_words and nc not in string.punctuation]
    freq = Counter(filtered)
    top_keywords = [word for word, count in freq.most_common(5)]
    return ", ".join(top_keywords)

def summarize_text_lsa(text):
    """Summarize text using LSA from sumy."""
    parser = PlaintextParser.from_string(text, Tokenizer("english"))
    summarizer = LsaSummarizer()
    sentence_count = 2 if len(text.split()) > 100 else 1
    summary_sentences = summarizer(parser.document, sentence_count)
    return " ".join(str(sentence) for sentence in summary_sentences)

def summarize_text_lexrank(text):
    """Summarize text using LexRank from sumy."""
    parser = PlaintextParser.from_string(text, Tokenizer("english"))
    summarizer = LexRankSummarizer()
    sentence_count = 2 if len(text.split()) > 100 else 1
    summary_sentences = summarizer(parser.document, sentence_count)
    return " ".join(str(sentence) for sentence in summary_sentences)

def summarize_text_transformer(text):
    """Summarize text using a transformer-based model."""
    summary = summarizer(text, max_length=50, min_length=20, do_sample=False)
    return summary[0]['summary_text']

def generate_evaluation_dataset():
    """Generate evaluation dataset with multiple summarization methods."""
    reference_data = load_reference_data()
    eval_data = []

    for row in reference_data:
        chunk_idx = row["Chunk Index"]
        chunk_text = row["Chunk Text"]

        # Keyword extraction
        rake_keywords = extract_keywords_rake(chunk_text)
        spacy_keywords = extract_keywords_spacy(chunk_text)

        # Summaries
        lsa_summary = summarize_text_lsa(chunk_text)
        lexrank_summary = summarize_text_lexrank(chunk_text)
        transformer_summary = summarize_text_transformer(chunk_text)

        eval_data.append({
            "Chunk Index": chunk_idx,
            "Chunk Text": chunk_text,
            "RAKE Keywords": rake_keywords,
            "SpaCy Keywords": spacy_keywords,
            "LSA Summary": lsa_summary,
            "LexRank Summary": lexrank_summary,
            "Transformer Summary": transformer_summary
        })

    # Save to CSV
    fieldnames = ["Chunk Index", "Chunk Text", "RAKE Keywords", "SpaCy Keywords", 
                  "LSA Summary", "LexRank Summary", "Transformer Summary"]
    with open(EVALUATION_CSV, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(eval_data)
    print(f"Evaluation dataset saved to {EVALUATION_CSV} with {len(eval_data)} chunks.")

if __name__ == "__main__":
    generate_evaluation_dataset()