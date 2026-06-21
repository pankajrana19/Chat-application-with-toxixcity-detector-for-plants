from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings 
import ollama 

CHROMA_PATH = "chroma"
EMBED_MODEL = "nomic-embed-text"
LLM_MODEL = "llama3.2"

def main():
    embeddings_model = OllamaEmbeddings(model=EMBED_MODEL)
    db = Chroma(persist_directory=CHROMA_PATH, embedding_function=embeddings_model)

    while True:
        user_query = input("Enter your farming-related query (or type 'exit' to quit): ")
        if user_query.lower() == 'exit':
            break
        relevant_docs = query_chroma(db, user_query)
        if relevant_docs:
            # response = query_llm(user_query, relevant_docs)
            print("relevant documents available")
        else:
            print("No relevant documents found.")

def query_chroma(db, user_query):
    # Perform similarity search
    results = db.similarity_search_with_score(query=user_query, k=4)
    relevant_docs = []
    
    print("\n--- Top 4 Relevant Documents ---")
    for i, (result, score) in enumerate(results, start=1):
        doc_content = result.page_content
        summary = result.metadata.get("summary", "No summary available")
        keywords = result.metadata.get("keywords", "No keywords available")
        
        # Collect data for LLM context
        relevant_docs.append({
            "summary": summary,
            "content": doc_content,
            "keywords": keywords
        })
        
        # Print minimal details (no source)
        print(f"\nDocument {i}:")
        print(f"Score: {score:.2f}")
        print(f"Content: {doc_content}...")
        print("-" * 50)
    
    return relevant_docs

def query_llm(user_query, relevant_docs):
    # Construct context with summaries and keywords embedded
    context = "Context:\n"
    for i, doc in enumerate(relevant_docs, start=1):
        context += f"- Document {i}:\n"
        context += f"  Summary: {doc['summary']}\n"
        context += f"  Content: {doc['content']}\n"
        context += f"  Key terms: {doc['keywords']}\n"
    
    # Simple prompt with embedded context
    model_query = f"""
    You are an agricultural assistant. Based on the following context, provide concise advice regarding the farming issue described: '{user_query}'

    {context}
    """
    
    print("\nGenerating response...")
    response_text = ""
    stream = ollama.generate(model=LLM_MODEL, prompt=model_query, stream=True)
    
    for chunk in stream:
        if chunk.get("response"):
            text_chunk = chunk["response"]
            print(text_chunk, end="", flush=True)
            response_text += text_chunk
    print("\n")
    return response_text.strip()

if __name__ == "__main__":
    main()