import os
import time
from flask import Flask, request, jsonify, render_template, Response
from PIL import Image
import torchvision.transforms.functional as TF
import torch
import pandas as pd
import CNN
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
import ollama

disease_info = pd.read_csv('disease_info.csv', encoding='cp1252')
model = CNN.CNN(39)
model.load_state_dict(torch.load("full_model.pt"))
model.eval()

CHROMA_PATH = "chroma"
EMBED_MODEL = "nomic-embed-text"
LLM_MODEL = "llama3.2"

embeddings_model = OllamaEmbeddings(model=EMBED_MODEL)
db = Chroma(persist_directory=CHROMA_PATH, embedding_function=embeddings_model)

app = Flask(__name__)

def query_chroma(user_query):
    """Retrieve and rerank relevant chunks from Chroma."""
    start_time = time.time()
    
    results = db.similarity_search_with_score(query=user_query, k=4)
    
    if not results:
        print("No results found for query.")
        return []
        
    if results[0][1] > 0.97:
        print(f"Best match has poor similarity: {results[0][1]}")
        return []
    
    query_terms = user_query.lower().split()
    reranked_docs = []
    
    for doc, sim_score in results:
        relevance_score = 1.0 - sim_score
        
        text = doc.page_content.lower()
        metadata = doc.metadata

        keywords = metadata.get('keywords', '').lower()
        summary = metadata.get('summary', '').lower()
        
        keyword_matches = sum(1 for term in query_terms if term in keywords)
        summary_matches = sum(1 for term in query_terms if term in summary)
        content_matches = sum(1 for term in query_terms if term in text)
        
        combined_score = (
            (relevance_score * 0.6) +                        
            (keyword_matches * 0.2 / max(1, len(query_terms))) + 
            (summary_matches * 0.1 / max(1, len(query_terms))) +
            (content_matches * 0.1 / max(1, len(query_terms)))   
        )
        
        reranked_docs.append((doc, combined_score))
    
    reranked_docs.sort(key=lambda x: x[1], reverse=True)
    
    relevant_docs = []
    for doc, score in reranked_docs[:2]:
        context_snippet = doc.page_content
        
        if 'summary' in doc.metadata and doc.metadata['summary']:
            context_snippet = f"Summary: {doc.metadata['summary']}\n\n{context_snippet}"
            
        if 'keywords' in doc.metadata and doc.metadata['keywords']:
            context_snippet += f"\n\nKeywords: {doc.metadata['keywords']}"
            
        relevant_docs.append(context_snippet)
    
    query_time = time.time() - start_time
    print(f"Query processing completed in {query_time:.2f} seconds")
    
    return relevant_docs

def is_agricultural_query(user_query):
    """Determine if a query is agricultural based on similarity scores of retrieved documents."""

    results = db.similarity_search_with_score(query=user_query, k=4)
    
    if not results:
        return False
    if results[0][1] > 0.97:
        return False
    
    return True

def query_llm(user_query, relevant_docs):
    """Generate chatbot response using retrieved chunks with keywords in context."""
    if not relevant_docs:
        return Response(generate_non_agri_response(), content_type='text/event-stream')
    
    context = "\n\n---\n\n".join(relevant_docs)
    
    model_query = f"""
    You are an agricultural assistant. Based on the following context, provide advice regarding the farming issue described: '{user_query}'

    Context:
    {context}
    """
    
    stream = ollama.generate(model=LLM_MODEL, prompt=model_query, stream=True)
    return Response(generate_response(stream), content_type='text/event-stream')

def generate_non_agri_response():
    """Generate response for non-agricultural queries."""
    yield "data: I'm an agricultural assistant focused on helping with farming, plants, and crop-related topics. I'm not able to provide information on other subjects. Please ask me something related to agriculture or plant care.\n\n"
    yield "data: [DONE]\n\n"

def generate_response(stream):
    """Generate streaming response directly."""
    for chunk in stream:
        if chunk.get("response"):
            yield f"data: {chunk['response']}\n\n"
    yield "data: [DONE]\n\n"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/query', methods=['POST'])
def query():
    data = request.json
    user_query = data.get("query", "")
    if not user_query:
        return jsonify({"error": "No query provided"}), 400

    if not is_agricultural_query(user_query):
        return jsonify({"response": "I'm an agricultural assistant focused on helping with farming, plants, and crop-related topics. I'm not able to provide information on other subjects. Please ask me something related to agriculture or plant care."})
    
    relevant_docs = query_chroma(user_query)
    if relevant_docs:
        return jsonify({"status": "query received"})
    else:
        return jsonify({"response": "I'm an agricultural assistant focused on helping with farming, plants, and crop-related topics. I'm not able to provide information on other subjects. Please ask me something related to agriculture or plant care."})

@app.route('/stream', methods=['GET'])
def stream():
    user_query = request.args.get('query', '')
    
    if not user_query:
        return jsonify({"error": "No query provided"}), 400

    if not is_agricultural_query(user_query):
        return Response(generate_non_agri_response(), content_type='text/event-stream')
        
    relevant_docs = query_chroma(user_query)
    
    if relevant_docs:
        return query_llm(user_query, relevant_docs)
    else:
        return Response(generate_non_agri_response(), content_type='text/event-stream')

@app.route('/image-query', methods=['POST'])
def image_query():
    if 'image' not in request.files:
        return jsonify({"error": "No image uploaded"}), 400

    image = request.files['image']
    image_path = os.path.join(app.root_path, 'static', image.filename)
    image.save(image_path)

    plant_name, disease_name = prediction(image_path)

    if plant_name and disease_name:
        disease_entry = disease_info[disease_info['disease_name'].str.contains(disease_name, na=False)]
        print("Disease Entry Found:", not disease_entry.empty)  
        print("Disease Entry Data:", disease_entry)  

        if not disease_entry.empty:
            description = disease_entry.iloc[0]['description']
            possible_steps = disease_entry.iloc[0]['Possible Steps']

            if possible_steps and not possible_steps.startswith("• "):
                steps = possible_steps.split("\n")
                formatted_steps = []
                for step in steps:
                    if step.strip():
                        formatted_steps.append(f"• {step.strip()}")
                possible_steps = "\n".join(formatted_steps)

            response = {
                "Plant": plant_name,
                "Disease": disease_name,
                "Description": description,
                "Possible Steps": possible_steps
            }
        else:
            response = {
                "Plant": plant_name,
                "Disease": disease_name,
                "Description": "No additional information available.",
                "Possible Steps": "No additional information available."
            }
    else:
        response = {
            "Plant": None,
            "Disease": disease_name,
            "Description": "No additional information available.",
            "Possible Steps": "No additional information available."
        }

    return jsonify(response)

def prediction(image_path):
    image = Image.open(image_path).convert("RGB")
    image = image.resize((224, 224))
    input_data = TF.to_tensor(image).unsqueeze(0)
    
    logits, probabilities = model(input_data)
    pred_index = logits.argmax().item()
    confidence_score = probabilities[0][pred_index].item()

    confidence_threshold = 0.5

    if confidence_score < confidence_threshold:
        return None, "Unknown"

    disease_entry = disease_info['disease_name'][pred_index]
    
    if ":" in disease_entry:
        plant_name, disease_name = [item.strip() for item in disease_entry.split(":", 1)]
    else:
        plant_name, disease_name = None, disease_entry.strip()
    
    print(f"Prediction: Plant - {plant_name}, Disease - {disease_name}, Confidence: {confidence_score:.4f}")
    return plant_name, disease_name

if __name__ == "__main__":
    app.run(debug=True, threaded=True)