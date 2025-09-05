import os
import json
import pandas as pd
from exam_parser import parse_exam_document, extract_qa_pairs
from azure.ai.inference import ChatCompletionsClient
from azure.core.credentials import AzureKeyCredential
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

# -------------------------------
# Step 1: Load Knowledge Chunks
# -------------------------------
def load_chunks(folder="knowledge_chunks"):
    chunks = []
    for file_name in sorted(os.listdir(folder)):
        if file_name.endswith(".txt"):
            with open(os.path.join(folder, file_name), "r", encoding="utf-8") as f:
                chunks.append(f.read())
    print(f"✅ Loaded {len(chunks)} chunks from {folder}")
    return chunks

# -------------------------------
# Step 2: Connect to GitHub Models
# -------------------------------
def init_client():
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise ValueError("❌ GITHUB_TOKEN not found in environment variables.")
    
    endpoint = "https://models.github.ai/inference"
    model = "openai/gpt-4o-mini"  # free supported model
    client = ChatCompletionsClient(endpoint=endpoint, credential=AzureKeyCredential(token))
    return client, model

# -------------------------------
# Step 3: Build FAISS Index (with cached embeddings)
# -------------------------------
def build_faiss_index(chunks, model_name="all-MiniLM-L6-v2", emb_file="chunk_embeddings.npy", index_file="faiss.index"):
    model = SentenceTransformer(model_name)
    new_chunks = []

    # Load existing embeddings and index if they exist
    if os.path.exists(emb_file) and os.path.exists(index_file):
        print("✅ Loading saved embeddings and FAISS index...")
        embeddings = np.load(emb_file)
        index = faiss.read_index(index_file)
        existing_chunk_count = embeddings.shape[0]
        if len(chunks) > existing_chunk_count:
            new_chunks = chunks[existing_chunk_count:]
        else:
            return index, embeddings, model
    else:
        embeddings = np.empty((0, model.get_sentence_embedding_dimension()), dtype="float32")
        index = faiss.IndexFlatL2(model.get_sentence_embedding_dimension())
        new_chunks = chunks

    # Embed only new chunks
    if new_chunks:
        print(f"Embedding {len(new_chunks)} new chunks...")
        new_embeddings = np.array([model.encode(chunk) for chunk in tqdm(new_chunks)]).astype("float32")
        embeddings = np.vstack([embeddings, new_embeddings])
        index.add(new_embeddings)

        # Save updated embeddings and index
        np.save(emb_file, embeddings)
        faiss.write_index(index, index_file)
        print(f"✅ Updated embeddings saved to {emb_file}, FAISS index saved to {index_file}")

    return index, embeddings, model

# -------------------------------
# Step 4: Retrieve Top Chunks (Semantic Search)
# -------------------------------
def retrieve_relevant_chunks_semantic(question, chunks, index, embeddings, sbert_model, top_k=3):
    q_vec = sbert_model.encode(question).astype("float32")
    D, I = index.search(np.array([q_vec]), top_k)
    top_chunks = [chunks[i] for i in I[0]]
    return top_chunks

# -------------------------------
# Step 5: Evaluate Student Answer
# -------------------------------
def evaluate_answer(question, student_answer, relevant_chunks, client, model):
    student_answer = " ".join(student_answer.splitlines())
    context = "\n\n".join(relevant_chunks)
    
    prompt = f"""
You are a strict examiner grading a student's answer.

Reference Material (may be incomplete):
{context}

Question: {question}
Student Answer: {student_answer}

Instructions:
1. Check if the student's answer is correct based on the reference material.
2. If the reference material doesn't fully cover the question, use your general knowledge to evaluate correctness.
3. Perform semantic understanding: even if the question wording doesn't exactly match the reference material, still find the relevant concepts.
4. Give a score from 0 to 5:
   - 0 = completely wrong
   - 5 = perfect
5. Provide a short feedback explaining the score.

Respond ONLY in valid JSON format like:
{{ "score": X, "feedback": "..." }}
"""

    try:
        response = client.complete(
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            model=model
        )
        raw_content = response.choices[0].message["content"]
        print("RAW GPT RESPONSE:", raw_content)  # Debug GPT output

        # Safe JSON extraction
        json_start = raw_content.find("{")
        json_end = raw_content.rfind("}") + 1
        json_text = raw_content[json_start:json_end]
        return json.loads(json_text)
    
    except Exception as e:
        print("⚠️ Error parsing GPT response, returning default:", e)
        return {"score": 0, "feedback": "Could not evaluate answer."}

# -------------------------------
# Step 6: Main Evaluation Loop
# -------------------------------
def main():
    # Load exam file
    exam_file = "sample_exam.docx"  # change to your file
    lines = parse_exam_document(exam_file)
    qa_pairs = extract_qa_pairs(lines)
    print(f"✅ Found {len(qa_pairs)} Q&A pairs.")

    # Load knowledge chunks
    chunks = load_chunks("knowledge_chunks")

    # Build/load FAISS index
    index, embeddings, sbert_model = build_faiss_index(chunks)

    # Init GPT client
    client, model = init_client()

    # Evaluate each answer
    results = []
    for q, a in qa_pairs:
        top_chunks = retrieve_relevant_chunks_semantic(q, chunks, index, embeddings, sbert_model, top_k=3)
        eval_result = evaluate_answer(q, a, top_chunks, client, model)
        results.append({
            "question": q,
            "answer": a,
            "score": eval_result.get("score", 0),
            "feedback": eval_result.get("feedback", "")
        })

    # Save results to CSV
    df = pd.DataFrame(results)
    df.to_csv("evaluation_report.csv", index=False)
    print("✅ Evaluation complete. Results saved to evaluation_report.csv")

    # Print summary
    total_score = sum(r["score"] for r in results)
    max_score = len(results) * 5
    print(f"📊 Total Score: {total_score}/{max_score}")

# -------------------------------
# Run the script
# -------------------------------
if __name__ == "__main__":
    main()
