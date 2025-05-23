import os
import numpy as np
import faiss
import pickle
import json
import requests
import re
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from langchain_community.document_loaders import TextLoader, PyPDFLoader, UnstructuredExcelLoader


load_dotenv()


embedding_model = SentenceTransformer("all-MiniLM-L6-v2")


INDEX_PATH = "my_index.faiss"
DOCS_PATH = "docs.pkl"
HISTORY_PATH = "history.pkl"
QA_PATH = "data_preprocessing/output/combined_qa.json"


API_URL = "https://router.huggingface.co/nebius/v1/chat/completions"
API_TOKEN = os.getenv("HF_API_KEY")  # Set this in your .env file


headers = {
    "Authorization": f"Bearer {API_TOKEN}"
}


def load_faiss_index():
    if os.path.exists(INDEX_PATH):
        with open(QA_PATH, "r", encoding="utf-8") as f:
            qa_data = json.load(f)
        documents = [f"Q: {item['question']}\nA: {item['answer']}" for item in qa_data]
        index = faiss.read_index(INDEX_PATH)
    else:
        documents = []
        index = faiss.IndexFlatL2(384)
    return index, documents


def extract_documents_from_json(json_path):
    with open(json_path, "r", encoding="utf-8") as f:
        qa_data = json.load(f)
    documents = [f"Q: {item['question']}\nA: {item['answer']}" for item in qa_data]
    return documents


def save_index(index, documents):
    faiss.write_index(index, INDEX_PATH)
    with open(DOCS_PATH, "wb") as f:
        pickle.dump(documents, f)


def update_index_from_json(json_path):
    documents = extract_documents_from_json(json_path)
    embeddings = embedding_model.encode(documents, show_progress_bar=True)
    index = faiss.IndexFlatL2(embeddings.shape[1])
    index.add(np.array(embeddings))
    save_index(index, documents)


def extract_text(file_path, file_type):
    print(f"Extracting text from {file_path} as {file_type}")
    if file_type == "txt":
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            print(f"Extracted {len(content)} chars from txt")
            return content
        except Exception as e:
            print(f"Error reading txt: {e}")
            return ""
    elif file_type == "pdf":
        try:
            pages = PyPDFLoader(file_path).load()
            content = "\n".join(page.page_content for page in pages)
            print(f"Extracted {len(content)} chars from pdf")
            return content
        except Exception as e:
            print(f"Error reading pdf: {e}")
            return ""
    elif file_type == "xlsx":
        try:
            pages = UnstructuredExcelLoader(file_path).load()
            content = "\n".join(page.page_content for page in pages)
            print(f"Extracted {len(content)} chars from xlsx")
            return content
        except Exception as e:
            print(f"Error reading xlsx: {e}")
            return ""
    else:
        print(f"Unsupported file type: {file_type}")
        return ""


def update_index_with_file(uploaded_file):
    index, documents = load_faiss_index()
    ext = uploaded_file.name.split(".")[-1].lower()
    temp_path = f"temp_uploaded.{ext}"
    with open(temp_path, "wb") as f:
        f.write(uploaded_file.read())

    content = extract_text(temp_path, ext)
    os.remove(temp_path)

    if content.strip():
        embeddings = embedding_model.encode([content])
        index.add(embeddings)
        documents.append(content)
        save_index(index, documents)
        print("Document indexed successfully")
        return True
    else:
        print("No content extracted; skipping indexing")
        return False


def is_safe_answer(answer):
    """Check with Llama Guard if the generated answer is safe."""
    llama_guard_api_url = "https://router.huggingface.co/sambanova/v1/chat/completions"
    llama_guard_headers = {
        "Authorization": f"Bearer {API_TOKEN}"
    }

    payload = {
        "messages": [
            {"role": "user", "content": answer}
        ],
        "model": "meta-llama/Llama-Guard-3-8B"
    }

    try:
        response = requests.post(llama_guard_api_url, headers=llama_guard_headers, json=payload)
        response.raise_for_status()
        result = response.json()

        moderation_output = result["choices"][0]["message"]["content"].strip().lower()
        print("Guard Rails Result:", moderation_output)

        if "unsafe" in moderation_output or "not safe" in moderation_output:
            return False
        return True

    except Exception as e:
        print(f"Guard Rails check failed: {e}")
        return True  # Fail-safe: allow response if guard fails


def generate_answer(query, top_k=3):
    index, documents = load_faiss_index()
    query_vec = embedding_model.encode([query])
    D, I = index.search(query_vec, top_k)

    print("Distances:", D)
    print("Indices:", I)

    found_docs = [documents[i] for i in I[0] if i != -1 and i < len(documents)]
    if not found_docs:
        return "", "I cannot help with that query."

    context = "\n---\n".join(found_docs)

    prompt = f"""You are a helpful banking assistant.
Use the context below to answer customer queries clearly, politely, and accurately.
If the question is out-of-domain, say you cannot help with that.
Only provide the final answer, do NOT include any reasoning, explanations, or thoughts.

Context:
{context}

User question:
{query}

Answer:"""

    payload = {
        "model": "Qwen/Qwen3-4B-fast",
        "messages": [
            {"role": "system", "content": "You are a helpful banking assistant."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 512,
        "temperature": 0.7,
        "top_k": 50,
        "top_p": 0.95,
        "stop": ["</s>"]
    }

    response = requests.post(API_URL, headers=headers, json=payload)
    response.raise_for_status()
    res_json = response.json()

    answer = res_json["choices"][0]["message"]["content"].strip()
    answer = re.sub(r"<think>.*?</think>", "", answer, flags=re.DOTALL).strip()

    # Run Llama Guard moderation
    if not is_safe_answer(answer):
        print("Answer flagged as unsafe by Llama Guard.")
        answer = "⚠️ This answer was flagged as unsafe and has been withheld for your protection."

    return context, answer


def save_history(history):
    with open(HISTORY_PATH, "wb") as f:
        pickle.dump(history, f)


def get_history():
    if os.path.exists(HISTORY_PATH):
        with open(HISTORY_PATH, "rb") as f:
            return pickle.load(f)
    return []
