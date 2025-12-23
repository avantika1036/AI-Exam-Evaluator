# 🧠 AI Exam Evaluator (Class Mode)

An AI-powered exam evaluation platform that automatically grades student answers using GPT-based models. The system supports **multi-student evaluation**, **teacher-defined rubrics**, **advanced analytics**, **student performance profiles**, and **AI-generated teaching insights** through a modern web interface.

---

## 🚀 Overview

AI Exam Evaluator transforms traditional exam grading into a **scalable, transparent, and insight-driven process**.

The platform combines:
- Large Language Models (GPT)
- Domain-specific knowledge grounding
- Rubric-based scoring
- Class-level analytics
- Rich reporting and visualization

It is suitable for educational platforms, assessment systems, and academic analytics use cases.

---

## ✨ Key Features

- 📄 Supports PDF, DOCX, and image-based exam papers  
- 👥 Single-student and multi-student (class mode) evaluation  
- 📝 Teacher-defined rubric-based grading  
- 🏆 Leaderboard and ranking system  
- 🎓 Individual student performance profiles  
- 📊 Advanced analytics and visualizations  
- 💡 AI-generated teaching insights  
- 📥 Exportable reports (PDF, Excel, CSV, ZIP)  
- 🧠 Knowledge-grounded evaluation using reference textbooks  

---

## 🏗️ System Architecture
<img width="9415" height="1050" alt="Exam Document Intelligence-2025-12-23-112410" src="https://github.com/user-attachments/assets/8a367c2c-46d1-491a-884f-ed4aac7ffaa6" />

---

## 📚 Knowledge Base

The evaluator is supported by a domain-specific knowledge base built from authoritative textbooks.

Knowledge processing pipeline:
- Text extraction (OCR fallback supported)
- Cleaning and normalization
- Semantic chunking (~4673 chunks)
- Embedding using Sentence Transformers
- Vector indexing using FAISS

---

## 🔄 Evaluation Workflow

1. Upload exam files (single, multiple, or ZIP)  
2. Configure grading rubric  
3. Extract question–answer pairs  
4. Retrieve relevant knowledge chunks  
5. GPT evaluates answers using rubric  
6. Generate scores, feedback, analytics, and reports  

---

## 📝 Rubric-Based Grading

- Fully customizable evaluation criteria  
- Weighted scoring per criterion  
- Per-question rubric breakdown  
- Transparent and explainable grading  

---

## 🎓 Student Profiles

Each student profile includes:
- Total score and class rank  
- Question-wise score breakdown  
- Rubric-wise radar analysis  
- Detailed AI feedback  
- Downloadable personalized PDF report  

---

## 📊 Analytics & AI Insights

- Question-wise class performance  
- Rubric criterion analysis  
- Student vs question heatmaps  
- Score distributions  
- Frequently missed concepts  
- AI-generated teaching recommendations  

---

## 🖥️ Frontend

- Built using Streamlit  
- Modern dark-themed UI  
- Sidebar-based configuration  
- Tab-based navigation:
  - Leaderboard  
  - Analytics  
  - AI Insights  
  - Reports  
  - Student Profiles  

---

## 🛠️ Tech Stack

- Language: Python  
- Frontend: Streamlit  
- AI Models: GPT (GitHub Models / OpenAI-compatible), Gemini (optional)  
- OCR: Tesseract  
- PDF Parsing: pdfplumber  
- DOCX Parsing: python-docx  
- Embeddings: Sentence Transformers  
- Vector Search: FAISS  
- Visualization: Plotly  
- Reporting: Pandas, FPDF  

---

## ⚙️ Setup & Run Instructions

### Create Virtual Environment

```
python -m venv venv
```

Activate the environment:

Windows: 
```
venv\Scripts\activate
```

macOS / Linux: 
```
source venv/bin/activate
```

---

### Install Dependencies
```
pip install -r requirements.txt
```

---

### Set API Tokens

GitHub GPT Token (required):

Windows (PowerShell):  
```
setx GITHUB_TOKEN your_github_token_here
```

macOS / Linux:  
```
export GITHUB_TOKEN=your_github_token_here
```

Token must have `models:read` permission.

Gemini API Token:

Windows (PowerShell):  
```
setx GEMINI_API_KEY your_gemini_api_key_here
```

macOS / Linux:  
```
export GEMINI_API_KEY=your_gemini_api_key_here
```

---

### Run the Application

streamlit run app.py  

If Streamlit is not recognized:

python -m streamlit run app.py  

---

### Open in Browser

http://localhost:8501

---

## 📁 Project Structure

ai-exam-evaluator/  
├── app.py  
├── exam_evaluator.py  
├── exam_parser.py  
├── split_knowledge_base.py  
├── knowledge_chunks/  
├── books_clean/  
├── requirements.txt  
└── README.md  

---

## ⚠️ Known Limitations

- OCR accuracy depends on scan quality  
- GPT may hallucinate if reference context is weak  
- Large-scale usage requires higher compute resources  
- Internet/API access required for AI inference  

---

## 🔮 Future Enhancements

- LMS integration (Moodle, Google Classroom)  
- Automatic rubric generation  
- Adaptive learning recommendations  
- Plagiarism detection  
- Voice-based (viva) evaluation  
- Long-term student progress tracking  

---

## 📌 Conclusion

AI Exam Evaluator demonstrates how GPT-based models, combined with knowledge grounding, rubric-based scoring, and analytics, can deliver a **scalable, transparent, and intelligent assessment system**.

The platform moves beyond basic grading to provide **actionable insights for educators and personalized feedback for learners**.


