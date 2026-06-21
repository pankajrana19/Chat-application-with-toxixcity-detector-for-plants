import os
import shutil
import re
from tqdm import tqdm
import spacy
from collections import Counter
import string

from langchain_community.document_loaders import PyPDFLoader, PDFMinerLoader
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings

DATA_PATH = "sources"
CHROMA_PATH = "chroma"
EMBED_MODEL = "nomic-embed-text"

nlp = spacy.load("en_core_web_sm")

def main():
    documents = load_documents()
    chunks, metadata = process_documents(documents)
    save_to_chroma(chunks, metadata)

def load_documents():
    """Load PDFs from the sources folder with better handling of tables and formatting."""
    documents = []
    pdf_files = [f for f in os.listdir(DATA_PATH) if f.endswith(".pdf")]
    
    for filename in tqdm(pdf_files, desc="Loading PDFs", unit="file"):
        print(filename)
        file_path = os.path.join(DATA_PATH, filename)
        
        try:
            loader = PDFMinerLoader(file_path)
            pdf_docs = loader.load()
        except Exception as e:
            print(f"Error with PDFMinerLoader for {filename}: {e}")
            try:
                loader = PyPDFLoader(file_path)
                pdf_docs = loader.load()
            except Exception as e2:
                print(f"Error with PyPDFLoader for {filename}: {e2}")
                continue
        filtered_docs = [doc for doc in pdf_docs if len(doc.page_content.split()) > 50]
        documents.extend(filtered_docs)
    
    print(f"Loaded {len(documents)} document pages.")
    return documents

def is_table_content(text):
    """Less aggressive table detection with multiple requirements."""
    table_indicators = [
        r'(\s{4,}\S+){4,}',  
        r'(\|.*?){3,}\|',    
        r'(\d+\s+){4,}\d+',  
        r'^(\s*[-=]{5,}\s*)$'
    ]
    
    pattern_matches = sum(1 for pattern in table_indicators if re.search(pattern, text))
    
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    line_consistency = False
    if len(lines) > 4:
        line_lengths = [len(line) for line in lines]
        avg_length = sum(line_lengths) / len(line_lengths)
        similar_lines = sum(1 for length in line_lengths if 0.8 * avg_length < length < 1.2 * avg_length)
        line_consistency = similar_lines / len(lines) > 0.8
    
    return (pattern_matches >= 2) or (pattern_matches >= 1 and line_consistency)

def clean_text(text):
    """Advanced text cleaning with relaxed rules."""
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'\S+@\S+', '', text)
    text = re.sub(r'\bPage\s*\d+.*$', '', text, flags=re.IGNORECASE|re.MULTILINE)
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'(\n|\\n){3,}', '\n\n', text)
    text = re.sub(r'[©_\-]{5,}', '', text)
    return text.strip()

def split_into_sentences(text):
    """Split text into sentences using spaCy for proper sentence boundaries."""
    doc = nlp(text)
    sentences = [sent.text.strip() for sent in doc.sents if sent.text.strip()]
    return sentences

def process_documents(documents):
    """Process documents into semantically meaningful chunks based on sentences."""
    chunks = []
    metadata_list = []
    chunk_idx = 0

    print(f"Processing {len(documents)} documents")
    
    for doc_idx, doc in enumerate(tqdm(documents, desc="Processing documents")):
        print(f"\nProcessing document {doc_idx + 1}")
        print(f"Original text length: {len(doc.page_content)} chars")
        
        raw_text = doc.page_content
        cleaned_text = clean_text(raw_text)
        print(f"After cleaning: {len(cleaned_text)} chars")

        if len(cleaned_text) < 100:
            print("Skipping due to short cleaned text")
            continue
            
        if is_table_content(cleaned_text):
            print("Skipping table-like content")
            continue
            
        paragraphs = re.split(r'\n\s*\n', cleaned_text)
        print(f"Found {len(paragraphs)} paragraphs")
        
        for para_idx, paragraph in enumerate(paragraphs):
            if len(paragraph) < 100 or is_table_content(paragraph):
                print(f"Skipping paragraph {para_idx + 1} (length: {len(paragraph)})")
                continue

            sentences = split_into_sentences(paragraph)
            print(f"Paragraph {para_idx + 1} split into {len(sentences)} sentences")
            
            if not sentences:
                print("No sentences found in paragraph")
                continue
                
            current_chunk = []
            current_length = 0
            target_length = 800
            
            for sent_idx, sentence in enumerate(sentences):
                if len(sentence) < 5:
                    print(f"Skipping sentence {sent_idx + 1} (too short)")
                    continue
                    
                sentence_length = len(sentence)

                if current_length + sentence_length > target_length and current_chunk:
                    chunk_text = ' '.join(current_chunk)

                    if len(chunk_text) >= 200:
                        print(f"Creating chunk {chunk_idx} (length: {len(chunk_text)})")
                        metadata = create_metadata(chunk_text, chunk_idx)
                        chunks.append(chunk_text)
                        metadata_list.append(metadata)
                        chunk_idx += 1
                        
                    current_chunk = [sentence]
                    current_length = sentence_length
                else:
                    current_chunk.append(sentence)
                    current_length += sentence_length
            
            if current_chunk:
                chunk_text = ' '.join(current_chunk)
                if len(chunk_text) >= 200:
                    print(f"Creating final chunk {chunk_idx} (length: {len(chunk_text)})")
                    metadata = create_metadata(chunk_text, chunk_idx)
                    chunks.append(chunk_text)
                    metadata_list.append(metadata)
                    chunk_idx += 1
    
    print(f"Processed documents into {len(chunks)} chunks.")
    return chunks, metadata_list
def create_metadata(text, chunk_idx):
    """Generate metadata for each chunk using spaCy-based extraction."""

    summary = summarize_text(text)
    
    keywords = extract_keywords_spacy(text)
    
    meta = {
        "chunk_index": chunk_idx,
        "summary": summary,
        "keywords": keywords
    }
    return meta

def summarize_text(text):
    """Extract a summary using the first sentence and key sentences."""
    try:
        doc = nlp(text)
        sentences = list(doc.sents)
        
        if not sentences:
            return text[:100] + "..."
        
        first_sentence = sentences[0].text
        
        if len(sentences) <= 2 or len(text) < 500:
            return first_sentence
        
        important_sentences = []
        entities = [ent.text.lower() for ent in doc.ents]
        nouns = [token.text.lower() for token in doc if token.pos_ == "NOUN"]
        
        noun_freq = Counter(nouns)
        important_nouns = [noun for noun, count in noun_freq.most_common(5)]
        
        for sent in sentences[1:]:
            sent_text = sent.text.lower()
            if any(entity.lower() in sent_text for entity in entities) or \
               any(noun in sent_text for noun in important_nouns):
                important_sentences.append(sent.text)
                if len(important_sentences) >= 1: 
                    break
        if important_sentences:
            return first_sentence + " " + important_sentences[0]
        
        return first_sentence
    
    except Exception as e:
        print(f"Summarization error: {e}")
        return text[:100] + "..."

def extract_keywords_spacy(text):
    """Extract keywords using spaCy's built-in capabilities."""
    try:
        doc = nlp(text.lower())
        
        stopwords = nlp.Defaults.stop_words
        
        entities = set()
        for ent in doc.ents:
            if ent.label_ in ["ORG", "PRODUCT", "GPE", "LOC", "PERSON", "WORK_OF_ART"]:
                if len(ent.text) > 2 and ent.text.lower() not in stopwords:
                    entities.add(ent.text.strip())
        noun_chunks = set()
        for chunk in doc.noun_chunks:
            chunk_text = chunk.text.strip()
            if len(chunk_text) > 2 and len(chunk_text.split()) <= 3:
                words = chunk_text.split()
                if sum(1 for word in words if word in stopwords) < len(words) / 2:
                    noun_chunks.add(chunk_text)
        content_words = []
        for token in doc:
            if token.pos_ in ["NOUN", "VERB", "ADJ"] and not token.is_stop and len(token.text) > 2:
                content_words.append(token.text)
        
        word_freq = Counter(content_words)
        common_words = set([word for word, count in word_freq.most_common(10) if count > 1])
        
        all_keywords = list(entities) + list(noun_chunks) + list(common_words)
        
        clean_keywords = []
        for kw in all_keywords:
            kw = re.sub(r'[^\w\s]', '', kw).strip()
            if kw and len(kw) > 2 and not kw.isdigit() and kw.lower() not in stopwords:
                clean_keywords.append(kw)
        unique_keywords = []
        seen = set()
        for kw in clean_keywords:
            kw_lower = kw.lower()
            if kw_lower not in seen and len(unique_keywords) < 10:
                seen.add(kw_lower)
                unique_keywords.append(kw)
        
        return ", ".join(unique_keywords)
    
    except Exception as e:
        print(f"Keyword extraction error: {e}")
        return ""

def save_to_chroma(chunks, metadata):
    """Save the text chunks along with metadata to a Chroma vector store."""
    if not chunks:
        raise ValueError("No chunks provided to save to Chroma")
    
    if os.path.exists(CHROMA_PATH):
        shutil.rmtree(CHROMA_PATH)
    
    print("Saving chunks to Chroma...")
    
    test_text = "This is a test sentence"
    embeddings_model = OllamaEmbeddings(model=EMBED_MODEL)
    
    try:
        test_embedding = embeddings_model.embed_query(test_text)
        print(f"Embedding test successful. Vector length: {len(test_embedding)}")
    except Exception as e:
        print(f"Embedding test failed: {e}")
        raise
    
    valid_chunks = [chunk for chunk in chunks if chunk and isinstance(chunk, str)]
    print(f"Valid chunks to embed: {len(valid_chunks)}/{len(chunks)}")
    
    if not valid_chunks:
        raise ValueError("No valid text chunks to embed")
    
    db = Chroma.from_texts(
        texts=valid_chunks,
        embedding=embeddings_model,
        metadatas=metadata[:len(valid_chunks)], 
        persist_directory=CHROMA_PATH,
    )
    print(f"Chroma database created with {len(valid_chunks)} chunks.")

if __name__ == "__main__":
    main()