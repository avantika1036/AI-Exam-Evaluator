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
import re

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
    model = "openai/gpt-4o"  # free supported model
    client = ChatCompletionsClient(endpoint=endpoint, credential=AzureKeyCredential(token))
    return client, model

# -------------------------------
# Step 3: Build FAISS Index (with cached embeddings)
# -------------------------------
def build_faiss_index(chunks, model_name="all-MiniLM-L6-v2", emb_file="chunk_embeddings.npy", index_file="faiss.index"):
    model = SentenceTransformer(model_name)
    new_chunks = []

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

    if new_chunks:
        print(f"Embedding {len(new_chunks)} new chunks...")
        new_embeddings = np.array([model.encode(chunk) for chunk in tqdm(new_chunks)]).astype("float32")
        embeddings = np.vstack([embeddings, new_embeddings])
        index.add(new_embeddings)

        np.save(emb_file, embeddings)
        faiss.write_index(index, index_file)
        print(f"✅ Updated embeddings saved to {emb_file}, FAISS index saved to {index_file}")

    return index, embeddings, model

# -------------------------------
# Step 4: Retrieve Top Chunks
# -------------------------------
def retrieve_relevant_chunks_semantic(question, chunks, index, sbert_model, top_k=3):
    q_vec = sbert_model.encode(question).astype("float32")
    D, I = index.search(np.array([q_vec]), top_k)
    return [chunks[i] for i in I[0]]

# -------------------------------
# Step 5: Evaluate Student Answer
# -------------------------------
def evaluate_answer(question, student_answer, relevant_chunks, client, model, max_score=5, rubric=None):
    student_answer = " ".join(student_answer.splitlines())
    context = "\n\n".join(relevant_chunks)
    
    rubric_str = ""
    json_keys_str = ""  
    
    if rubric:
        rubric_str = "Use the following rubric for grading:\n"
        for criterion, weight in rubric.items():
            rubric_str += f"- {criterion}: {weight*100}% weight\n"
        rubric_str += f"The overall score out of {max_score} must be a weighted sum of the scores for each criterion.\n"
        
        json_keys = ["score", "feedback", "concepts"] + [f"score_{crit}" for crit in rubric.keys()]
        json_keys_str = ", ".join([f'"{key}"' for key in json_keys])

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
4. {rubric_str}
5. Provide a score for each criterion based on the rubric.
6. Provide a short feedback explaining the overall score.
7. List all key concepts or terms in the student's answer that match the reference material.

Respond ONLY with a valid JSON object. Your response MUST include the following keys: {json_keys_str}.
Example response for a question with Correctness, Clarity, and Completeness as criteria:
{{ 
    "score": 4.5, 
    "score_correctness": 2.0, 
    "score_clarity": 1.5,
    "score_completeness": 1.0, 
    "feedback": "...",
    "concepts": ["concept1", "concept2"]
}}
"""

    try:
        response = client.complete(
            model=model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ]
        )
        raw_content = response.choices[0].message["content"]

        # Robust JSON extraction
        match = re.search(r"\{.*\}", raw_content, re.DOTALL)
        if match:
            try:
                parsed_json = json.loads(match.group(0))
                
                # Fallback logic to calculate rubric scores if AI doesn't provide them
                if rubric:
                    missing_keys = False
                    for crit in rubric.keys():
                        if f"score_{crit}" not in parsed_json:
                            missing_keys = True
                            break
                    
                    if missing_keys and "score" in parsed_json:
                        overall_score = parsed_json.get("score", 0)
                        total_weight = sum(rubric.values())
                        if total_weight > 0:
                            for crit, weight in rubric.items():
                                proportional_score = (overall_score / max_score) * (weight / total_weight) * max_score
                                parsed_json[f"score_{crit}"] = round(proportional_score, 1)
                    elif not missing_keys:
                        # AI provided the keys, but check if they are integers and convert them
                        for crit in rubric.keys():
                            if isinstance(parsed_json[f"score_{crit}"], (int, float)):
                                parsed_json[f"score_{crit}"] = round(parsed_json[f"score_{crit}"], 1)
                            else:
                                # Fallback if AI provides non-numeric scores
                                parsed_json[f"score_{crit}"] = 0

                return parsed_json
            except json.JSONDecodeError:
                print("⚠️ Malformed JSON from AI.")
                return {"score": 0, "feedback": "⚠️ Malformed JSON response.", "concepts": []}
        else:
            return {"score": 0, "feedback": "⚠️ Could not parse GPT output", "concepts": []}

    except Exception as e:
        print(f"⚠️ Error parsing GPT response: {e}")
        return {"score": 0, "feedback": "Could not evaluate answer.", "concepts": []}

# -------------------------------
# Step 6: Main Evaluation Loop
# -------------------------------
def main():
    exam_file = "tests/test2.jpg"
    ext = os.path.splitext(exam_file)[-1].lower()
    
    if ext == ".docx":
        # First, parse the document into lines
        lines = parse_exam_document(exam_file)
        # Then, extract Q&A pairs from those lines
        qa_pairs = extract_qa_pairs(lines)
    else:
        # For other file types, parse_exam_document returns the Q&A pairs directly
        qa_pairs = parse_exam_document(exam_file)

    if not qa_pairs:
        print("❌ No Q&A pairs found. Evaluation stopped.")
        return
    print(f"✅ Found {len(qa_pairs)} Q&A pairs.")

    chunks = load_chunks("data/knowledge_chunks")
    index, embeddings, sbert_model = build_faiss_index(
        chunks,
        emb_file="models/chunk_embeddings.npy",
        index_file="models/faiss.index"
    )


    client, model = init_client()

    results = []
    for q, a in tqdm(qa_pairs, desc="Evaluating answers"):
        top_chunks = retrieve_relevant_chunks_semantic(q, chunks, index, sbert_model, top_k=3)
        eval_result = evaluate_answer(q, a, top_chunks, client, model, max_score=5)
        results.append({
            "question": q,
            "answer": a,
            "score": eval_result.get("score", 0),
            "feedback": eval_result.get("feedback", ""),
            "concepts": eval_result.get("concepts", [])
        })

    df = pd.DataFrame(results)
    os.makedirs("data/outputs", exist_ok=True)
    df.to_csv("data/outputs/evaluation_report.csv", index=False)

    print("✅ Evaluation complete. Results saved to evaluation_report.csv")

    total_score = sum(r["score"] for r in results)
    max_score = len(results) * 5
    print(f"📊 Total Score: {total_score}/{max_score}")



def evaluate_exam_frontend(exam_file, max_score=5, rubric=None):
    """
    Run evaluation and return results for frontend (Streamlit/Gradio).
    """
    ext = os.path.splitext(exam_file)[-1].lower()
    
    if ext == ".docx":
        # First, parse the document into lines
        lines = parse_exam_document(exam_file)
        # Then, extract Q&A pairs from those lines
        qa_pairs = extract_qa_pairs(lines)
    else:
        # For other file types, parse_exam_document returns the Q&A pairs directly
        qa_pairs = parse_exam_document(exam_file)

    if not qa_pairs:
        return [], 0, 0

    chunks = load_chunks("data/knowledge_chunks")
    index, embeddings, sbert_model = build_faiss_index(chunks)

    client, model = init_client()

    results = []
    for q, a in qa_pairs:
        top_chunks = retrieve_relevant_chunks_semantic(q, chunks, index, sbert_model, top_k=3)
        eval_result = evaluate_answer(q, a, top_chunks, client, model, max_score=max_score, rubric=rubric)
        
        result_entry = {
            "question": q,
            "answer": a,
            "score": eval_result.get("score", 0),
            "feedback": eval_result.get("feedback", ""),
            "concepts": eval_result.get("concepts", [])
        }
        
        # Add rubric scores to the result entry
        if rubric:
            for crit in rubric.keys():
                result_entry[f"score_{crit}"] = eval_result.get(f"score_{crit}", 0)
                
        results.append(result_entry)

    total_score = sum(r["score"] for r in results)
    max_total = len(results) * max_score

    return results, total_score, max_total

    
def generate_teacher_insights(class_df, summary_df):
    """Generate AI teacher insights from class performance data"""
    # Calculate key metrics
    avg_score = summary_df['percentage'].mean()
    q_performance = class_df.groupby('question_index').agg({
        'score': 'mean',
        'concepts': lambda x: ', '.join(set(x.str.split(', ').sum()))
    })
    
    # Identify strengths and weaknesses
    strong_qs = q_performance[q_performance['score'] > q_performance['score'].mean()]
    weak_qs = q_performance[q_performance['score'] < q_performance['score'].mean()]
    
    # Build prompt for GPT
    prompt = f"""
    Analyze this class performance and provide specific teaching recommendations:
    
    Class average: {avg_score:.1f}%
    Strong areas: Questions {', '.join(map(str, strong_qs.index.tolist()))}
    Weak areas: Questions {', '.join(map(str, weak_qs.index.tolist()))}
    Concepts covered: {', '.join(set(class_df['concepts'].str.split(', ').sum()))}
    
    Write a concise paragraph about:
    1. Overall performance
    2. Specific topics students understood well
    3. Areas needing improvement
    4. Recommended actions for the teacher
    """
    
    return prompt

if __name__ == "__main__":
    main()