import os
import shutil
import re
from tqdm import tqdm
import spacy
from collections import Counter
import string

from langchain_community.document_loaders import PyPDFLoader
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings

from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lsa import LsaSummarizer 

DATA_PATH = "sources"
CHROMA_PATH = "chroma"
EMBED_MODEL = "nomic-embed-text"
TARGET_CHUNK_LEN = 1000  
OVERLAP_SENTENCES = 1 

nlp = spacy.load("en_core_web_sm")

def main():
    documents = load_documents()
    chunks, metadata = process_documents(documents)
    save_to_chroma(chunks, metadata)

def load_documents():
    """Load PDFs from the sources folder."""
    documents = []
    pdf_files = [f for f in os.listdir(DATA_PATH) if f.endswith(".pdf")]
    for filename in tqdm(pdf_files, desc="Loading PDFs", unit="file"):
        file_path = os.path.join(DATA_PATH, filename)
        loader = PyPDFLoader(file_path)
        pdf_docs = loader.load()
        documents.extend(pdf_docs)
    print(f"Loaded {len(documents)} documents from PDFs.")
    return documents

def process_documents(documents):
    """Clean, chunk, and generate metadata for each document."""
    chunks = []
    metadata_list = []
    chunk_idx = 0

    for doc in tqdm(documents, desc="Processing documents"):
        raw_text = doc.page_content
        cleaned_text = clean_text(raw_text)
        
        doc_spacy = nlp(cleaned_text)
        sentences = [sent.text.strip() for sent in doc_spacy.sents if sent.text.strip()]
        if not sentences:
            continue

        current_chunk = ""
        current_sentences = []
        for sentence in sentences:
            if len(current_chunk) + len(sentence) > TARGET_CHUNK_LEN and current_chunk:
                metadata = create_metadata(doc, current_sentences, chunk_idx)
                chunks.append(current_chunk.strip())
                metadata_list.append(metadata)
                chunk_idx += 1
                # Start a new chunk with overlap
                if OVERLAP_SENTENCES > 0 and len(current_sentences) >= OVERLAP_SENTENCES:
                    overlap = current_sentences[-OVERLAP_SENTENCES:]
                else:
                    overlap = []
                current_sentences = overlap.copy()
                current_chunk = " ".join(overlap)
            # Add sentence to current chunk
            current_sentences.append(sentence)
            current_chunk += " " + sentence
        # Add the final chunk if any
        if current_chunk.strip():
            metadata = create_metadata(doc, current_sentences, chunk_idx)
            chunks.append(current_chunk.strip())
            metadata_list.append(metadata)
            chunk_idx += 1

    print(f"Processed documents into {len(chunks)} chunks.")
    return chunks, metadata_list

def clean_text(text):
    """Perform basic cleaning on the text."""
    text = re.sub(r'\s+', ' ', text)  # Normalize spaces
    text = re.sub(r'(\n|\\n)+', '\n', text)  # Preserve newlines for segmentation
    # Remove page numbers and extraneous markers
    text = re.sub(r'\bPage\s*\d+\b', '', text, flags=re.IGNORECASE)
    return text.strip()

def create_metadata(doc, sentences, chunk_idx):
    """Generate metadata for a chunk, including summary and keywords."""
    text_chunk = " ".join(sentences)
    summary = summarize_text(text_chunk)
    keywords = extract_keywords(text_chunk)
    meta = {
        "source": os.path.basename(doc.metadata.get("source", "unknown")),
        "chunk_index": chunk_idx,
        "summary": summary,
        "keywords": keywords
    }
    return meta

def summarize_text(text):
    """Summarize text using LSA summarizer from sumy."""
    parser = PlaintextParser.from_string(text, Tokenizer("english"))
    summarizer = LsaSummarizer()  # Changed to LSA
    # Dynamically determine sentence count: 2 if text is long, else 1
    sentence_count = 2 if len(text.split()) > 100 else 1
    summary_sentences = summarizer(parser.document, sentence_count)
    summary = " ".join(str(sentence) for sentence in summary_sentences)
    return summary

def extract_keywords(text):
    """Extract keywords using a simple noun-chunk frequency approach via spaCy."""
    doc_spacy = nlp(text.lower())
    noun_chunks = [chunk.text for chunk in doc_spacy.noun_chunks]
    # Remove punctuation and stop words
    filtered = [
        nc for nc in noun_chunks 
        if nc not in nlp.Defaults.stop_words and nc not in string.punctuation
    ]
    freq = Counter(filtered)
    top_keywords = [word for word, count in freq.most_common(5)]
    return ", ".join(top_keywords)

def save_to_chroma(chunks, metadata):
    """Append text chunks and metadata to an existing Chroma vector store."""
    embeddings_model = OllamaEmbeddings(model=EMBED_MODEL)
    
    if os.path.exists(CHROMA_PATH):
        # Load the existing database
        print("Loading existing Chroma database for appending...")
        db = Chroma(persist_directory=CHROMA_PATH, embedding_function=embeddings_model)
        # Append new data
        db.add_texts(
            texts=chunks,
            metadatas=metadata
        )
        print(f"Appended {len(chunks)} new chunks to existing Chroma database.")
    else:
        # Create a new database if it doesn't exist
        print("No existing Chroma database found. Creating new one...")
        db = Chroma.from_texts(
            texts=chunks,
            embedding=embeddings_model,
            metadatas=metadata,
            persist_directory=CHROMA_PATH
        )
        print(f"Created new Chroma database with {len(chunks)} chunks.")
    
    # Persist changes (not always necessary with modern LangChain versions, but included for safety)
    db.persist()

if __name__ == "__main__":
    main()