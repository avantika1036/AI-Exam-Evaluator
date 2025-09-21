import streamlit as st
import pandas as pd
import io
import os
import zipfile
import plotly.express as px
import plotly.graph_objects as go
from fpdf import FPDF
from exam_evaluator import evaluate_exam_frontend 
from streamlit_lottie import st_lottie
import requests
import tempfile
import time
from collections import Counter
import numpy as np

# -------------------------
# Helper: load lottie
# -------------------------
def load_lottieurl(url: str):
    r = requests.get(url)
    if r.status_code != 200:
        return None
    return r.json()

# -------------------------
# Streamlit Page setup & session state initialization
# -------------------------
st.set_page_config(page_title="AI Exam Evaluator — Class Mode", layout="wide")
st.markdown(
    """
    <style>
    .main {background-color: #0b1220; color: #e6edf3;}
    h1, h2, h3, h4 {color: #00e0ff;}
    .stMetric {background: #111827; border-radius: 12px; padding: 8px;}
    </style>
    """,
    unsafe_allow_html=True,
)
st.title("🤝 AI Exam Evaluator — Class Mode")
st.markdown("Upload multiple student exam files (or a ZIP). This will evaluate each and produce class analytics & reports.")

lottie = load_lottieurl("https://assets8.lottiefiles.com/packages/lf20_2glqweqs.json")
if lottie:
    try:
        st_lottie(lottie, height=150)
    except Exception:
        pass

# Initialize session state for data storage
if "class_df" not in st.session_state:
    st.session_state["class_df"] = pd.DataFrame()
if "summary_df" not in st.session_state:
    st.session_state["summary_df"] = pd.DataFrame()
if "rubric_for_ai" not in st.session_state:
    st.session_state["rubric_for_ai"] = {}
if "total_max_score_per_question" not in st.session_state:
    st.session_state["total_max_score_per_question"] = 0

# -------------------------
# Rubric configuration
# -------------------------
st.header("📝 Rubric & Evaluation Settings")
with st.expander("Configure your grading rubric"):
    st.markdown("Set criteria and their maximum points.")
    
    col1, col2, col3 = st.columns(3)
    
    criteria_points = {}
    with col1:
        c1 = st.text_input("Criterion 1 Name", "Correctness", key="c1_name")
        p1 = st.number_input(f"Max Points for {c1}", min_value=0, value=2, key="p1_points")
    with col2:
        c2 = st.text_input("Criterion 2 Name", "Clarity", key="c2_name")
        p2 = st.number_input(f"Max Points for {c2}", min_value=0, value=2, key="p2_points")
    with col3:
        c3 = st.text_input("Criterion 3 Name", "Completeness", key="c3_name")
        p3 = st.number_input(f"Max Points for {c3}", min_value=0, value=1, key="p3_points")
    
    # Optional criteria with unique keys
    col4, col5 = st.columns(2)
    with col4:
        c4 = st.text_input("Criterion 4 Name (Optional)", "", key="c4_name")
        p4 = st.number_input(f"Max Points for {c4}", min_value=0, value=0, key="p4_points")
    with col5:
        c5 = st.text_input("Criterion 5 Name (Optional)", "", key="c5_name")
        p5 = st.number_input(f"Max Points for {c5}", min_value=0, value=0, key="p5_points")

    criteria_points = {c1: p1, c2: p2, c3: p3}
    if c4 and p4 > 0: criteria_points[c4] = p4
    if c5 and p5 > 0: criteria_points[c5] = p5

    total_max_score_per_question = sum(criteria_points.values())
    st.info(f"The maximum score per question is **{total_max_score_per_question}** based on your criteria points.")

    rubric_for_ai = {k: v / total_max_score_per_question for k, v in criteria_points.items() if v > 0}
    st.session_state["rubric_for_ai"] = rubric_for_ai
    st.session_state["total_max_score_per_question"] = total_max_score_per_question

# -------------------------
# File upload (multiple)
# -------------------------
upload_mode = st.radio("Upload mode", ["Multiple files", "Single zip file"], horizontal=True)

uploaded_files = []
if upload_mode == "Multiple files":
    uploaded_files = st.file_uploader(
        "Select student exam files (docx/pdf/jpg/png)",
        accept_multiple_files=True,
        type=["docx", "pdf", "jpg", "jpeg", "png"]
    )
else:
    zip_file = st.file_uploader("Upload a ZIP containing exam files", type=["zip"])
    if zip_file:
        tmpdir = tempfile.mkdtemp()
        zpath = os.path.join(tmpdir, "upload.zip")
        with open(zpath, "wb") as f:
            f.write(zip_file.getbuffer())
        with zipfile.ZipFile(zpath, "r") as z:
            z.extractall(tmpdir)
        allowed_ext = (".docx", ".pdf", ".jpg", ".jpeg", ".png", ".tiff")
        for root, _, files in os.walk(tmpdir):
            for fname in files:
                if fname.lower().endswith(allowed_ext):
                    uploaded_files.append(open(os.path.join(root, fname), "rb"))

if not uploaded_files:
    st.info("Upload one or more exam files (or a ZIP) to evaluate the whole class.")
    st.stop()

# -------------------------
# Evaluate button
# -------------------------
if st.button("🚀 Evaluate Class"):
    all_rows = []
    student_summaries = []
    progress = st.progress(0)
    total_files = len(uploaded_files)

    pdf_tmpdir = tempfile.mkdtemp()
    FONT_REGULAR = "assets/DejaVuSans.ttf"
    FONT_BOLD = "assets/DejaVuSans-Bold.ttf"

    for idx_file, f in enumerate(uploaded_files, start=1):
        progress.progress(int((idx_file - 1) / total_files * 100))

        try:
            fname = f.name
        except Exception:
            fname = f"student_{idx_file}"
        student_name = os.path.splitext(fname)[0]

        ext = os.path.splitext(fname)[1] or ".pdf"
        tmp_path = os.path.join(tempfile.gettempdir(), f"eval_{student_name}_{int(time.time())}{ext}")
        if hasattr(f, "getbuffer"):
            with open(tmp_path, "wb") as out:
                out.write(f.getbuffer())
        else:
            with open(tmp_path, "wb") as out:
                out.write(f.read())

        try:
            results, total_score, max_total = evaluate_exam_frontend(
                tmp_path, 
                max_score=st.session_state["total_max_score_per_question"], 
                rubric=st.session_state["rubric_for_ai"]
            )
        except Exception as e:
            st.error(f"Error evaluating {student_name}: {e}")
            continue

        for q_idx, r in enumerate(results, start=1):
            row_data = {
                "student": student_name,
                "question_index": q_idx,
                "question": r.get("question", ""),
                "answer": r.get("answer", ""),
                "score": r.get("score", 0),
                "feedback": r.get("feedback", ""),
                "concepts": ", ".join(r.get("concepts", []))
            }
            # Add rubric scores
            for crit in criteria_points.keys():
                row_data[f"score_{crit}"] = r.get(f"score_{crit}", 0)
            all_rows.append(row_data)

        # PDF report
        pdf = FPDF()
        pdf.add_page()
        pdf.add_font("DejaVu", "", FONT_REGULAR, uni=True)
        pdf.add_font("DejaVu", "B", FONT_BOLD, uni=True)
        pdf.set_font("DejaVu", "B", 14)
        pdf.cell(0, 10, f"AI Exam Evaluation — {student_name}", ln=True, align="C")
        pdf.ln(6)
        pdf.set_font("DejaVu", "", 12)
        pdf.cell(0, 8, f"Total Score: {total_score}/{max_total}", ln=True)
        pdf.ln(4)
        for i, r in enumerate(results, start=1):
            pdf.set_font("DejaVu", "B", 12)
            pdf.multi_cell(0, 8, f"Q{i}: {r.get('question', '')}")
            pdf.set_font("DejaVu", "", 12)
            pdf.multi_cell(0, 8, f"Student Answer: {r.get('answer','')}")
            pdf.multi_cell(0, 8, f"Score: {r.get('score',0)}/{st.session_state['total_max_score_per_question']}")
            for crit, points in criteria_points.items():
                pdf.multi_cell(0, 8, f"  - {crit}: {r.get(f'score_{crit}', 0)}/{points}")
            pdf.multi_cell(0, 8, f"Feedback: {r.get('feedback','')}")
            concepts = ", ".join(r.get("concepts", []))
            if concepts:
                pdf.multi_cell(0, 8, f"Matched Concepts: {concepts}")
            pdf.ln(3)

        pdf_path = os.path.join(pdf_tmpdir, f"{student_name}_report.pdf")
        pdf.output(pdf_path)

        student_summaries.append({
            "student": student_name,
            "total_score": total_score,
            "max_total": max_total,
            "percentage": round(100 * total_score / max_total, 2) if max_total else 0,
            "pdf_path": pdf_path
        })
        time.sleep(0.1)

    progress.progress(100)
    st.success("✅ Evaluation complete for all uploaded students!")

    if not student_summaries:
        st.warning("No student files were successfully evaluated. Please check the files and try again.")
        st.stop()
    
    # Build DataFrames
    class_df = pd.DataFrame(all_rows)
    if class_df.empty:
        st.error("No extracted Q/A rows — check parser output or file contents.")
        st.stop()
    summary_df = pd.DataFrame(student_summaries).sort_values(by="total_score", ascending=False).reset_index(drop=True)
    summary_df.index += 1
    
    # Store dataframes in session state
    st.session_state["class_df"] = class_df
    st.session_state["summary_df"] = summary_df

# Display data only if session state is populated
if not st.session_state["class_df"].empty:
    class_df = st.session_state["class_df"]
    summary_df = st.session_state["summary_df"]
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["🏆 Leaderboard", "📊 Class Analytics", "💡 AI Insights", "📥 Reports & Downloads", "🎓 Student Profiles"])

    # Leaderboard
    with tab1:
        st.header("🏆 Leaderboard")
        st.dataframe(summary_df.style.background_gradient(cmap="Blues"), use_container_width=True)

        top3 = summary_df.head(3)
        for i, row in top3.iterrows():
            st.metric(label=f"{i}. {row['student']}", value=f"{row['total_score']}/{row['max_total']}", delta=f"{row['percentage']}%")

        min_score = st.slider("Filter students by minimum %", 0, 100, 0)
        filtered = summary_df[summary_df["percentage"] >= min_score]
        st.write(f"Showing {len(filtered)}/{len(summary_df)} students")
        st.dataframe(filtered)

    # Class Analytics
    with tab2:
        st.header("📊 Class Analytics")

        q_avg = class_df.groupby("question_index")["score"].mean().reset_index().rename(columns={"score": "avg_score"})
        fig_q = px.bar(q_avg, x="question_index", y="avg_score", title="Average score per question (class)",
                       labels={"question_index": "Question #", "avg_score": "Average Score"})
        st.plotly_chart(fig_q, use_container_width=True)

        pivot = class_df.pivot_table(index="student", columns="question_index", values="score", fill_value=0)
        fig_heat = px.imshow(pivot, labels=dict(x="Question #", y="Student", color="Score"),
                             aspect="auto", title="Heatmap: Student vs Question Scores")
        st.plotly_chart(fig_heat, use_container_width=True)

        st.subheader("Score Distribution")
        fig_hist = px.histogram(summary_df, x="percentage", nbins=10, title="Student Score Distribution")
        st.plotly_chart(fig_hist, use_container_width=True)

        fig_box = px.box(summary_df, y="percentage", title="Score Spread")
        st.plotly_chart(fig_box, use_container_width=True)

    # AI Insights
    with tab3:
        st.header("💡 AI Insights for Teacher")

        q_avg_with_questions = class_df.groupby("question_index").agg(
            avg_score=("score", "mean"),
            question_text=("question", "first")
        ).reset_index().sort_values("avg_score")
        
        st.subheader("❌ Hardest Questions")
        worst = q_avg_with_questions.head(3)
        for _, r in worst.iterrows():
            st.write(f"**Q{int(r['question_index'])}**: {r['question_text']}")
            st.write(f"Avg score: {round(r['avg_score'], 2)}")

        concepts_series = class_df["concepts"].dropna().astype(str)
        all_concepts = []
        for s in concepts_series:
            if s.strip():
                for c in s.split(","):
                    all_concepts.append(c.strip())
        
        concept_counts = pd.Series(all_concepts).value_counts().reset_index()
        concept_counts.columns = ["Concept", "Frequency"]
        
        if not concept_counts.empty:
            st.subheader("⚠️ Most Frequent Concepts")
            fig_concepts = px.bar(concept_counts.head(10), x="Concept", y="Frequency",
                                  title="Top 10 Most Common Concepts Identified in Answers")
            st.plotly_chart(fig_concepts, use_container_width=True)
            
            common = Counter(all_concepts).most_common(10)
            st.markdown("**Concepts and their frequency:**")
            for concept, cnt in common:
                st.write(f"- {concept}: mentioned {cnt} times")

        st.info("🤖 Tip: Focus revision on lowest-performing questions and most-frequent concepts.")

    # Reports
    with tab4:
        st.header("📥 Reports & Downloads")

        csv_bytes = class_df.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Download Class CSV", data=csv_bytes, file_name="class_evaluation.csv", mime="text/csv")

        excel_io = io.BytesIO()
        with pd.ExcelWriter(excel_io, engine="xlsxwriter") as writer:
            class_df.to_excel(writer, sheet_name="AllAnswers", index=False)
            summary_df.to_excel(writer, sheet_name="Summary", index=True)
        st.download_button("📥 Download Class Excel", data=excel_io.getvalue(),
                             file_name="class_evaluation.xlsx",
                             mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        zip_io = io.BytesIO()
        with zipfile.ZipFile(zip_io, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            for _, row in summary_df.iterrows():
                pdf_path = row["pdf_path"]
                if os.path.exists(pdf_path):
                    zf.write(pdf_path, arcname=os.path.basename(pdf_path))
        
        zip_io.seek(0)
        st.download_button("📥 Download All Student PDFs (ZIP)", data=zip_io.getvalue(),
                             file_name="student_reports.zip", mime="application/zip")

    # Student Profiles
    with tab5:
        st.header("🎓 Student Profiles")
        student_list = ["- Select a student -"] + summary_df["student"].tolist()
        selected_student = st.selectbox("Select a student to view their profile:", student_list)

        if selected_student != "- Select a student -":
            st.subheader(f"Profile for {selected_student}")
            
            student_data = class_df[class_df["student"] == selected_student].copy()
            student_summary = summary_df[summary_df["student"] == selected_student].iloc[0]

            col_score, col_rank = st.columns(2)
            with col_score:
                st.metric(label="Overall Score", value=f"{student_summary['total_score']}/{student_summary['max_total']}")
            with col_rank:
                st.metric(label="Class Rank", value=student_summary.name)

            fig_bar = px.bar(student_data, x="question_index", y="score", title="Score Per Question",
                             labels={"question_index": "Question #", "score": "Score"})
            st.plotly_chart(fig_bar, use_container_width=True)

            rubric_scores = student_data[[f'score_{crit}' for crit in st.session_state["rubric_for_ai"].keys()]].sum()
            rubric_points = {crit: points for crit, points in criteria_points.items() if points > 0}
            
            fig_radar = go.Figure()
            fig_radar.add_trace(go.Scatterpolar(
                r=rubric_scores.values,
                theta=list(rubric_points.keys()),
                fill='toself',
                name='Student Performance'
            ))
            fig_radar.update_layout(
                polar=dict(
                    radialaxis=dict(
                        visible=True,
                        range=[0, student_data.shape[0] * st.session_state["total_max_score_per_question"]]
                    )
                ),
                title="Rubric Score Breakdown"
            )
            st.plotly_chart(fig_radar, use_container_width=True)

            st.subheader("Detailed Q&A Breakdown")
            for _, row in student_data.iterrows():
                st.markdown(f"**Q{int(row['question_index'])}:** {row['question']}")
                st.markdown(f"**Answer:** {row['answer']}")
                st.markdown(f"**Score:** {row['score']}/{st.session_state['total_max_score_per_question']}")
                st.markdown(f"**Feedback:** {row['feedback']}")
                st.markdown(f"**Concepts:** {row['concepts']}")
                
                rubric_str = ", ".join([f"{crit}: {row.get(f'score_{crit}', 0)}/{criteria_points.get(crit, 0)}" for crit in criteria_points.keys() if criteria_points.get(crit, 0) > 0])
                st.markdown(f"**Rubric Breakdown:** {rubric_str}")
                st.markdown("---")

            pdf_path = summary_df[summary_df["student"] == selected_student].iloc[0]["pdf_path"]
            if os.path.exists(pdf_path):
                with open(pdf_path, "rb") as pdf_file:
                    st.download_button(
                        label=f"📥 Download {selected_student}'s Report",
                        data=pdf_file,
                        file_name=f"{selected_student}_report.pdf",
                        mime="application/pdf"
                    )
            
    st.success("✨ All features applied: Leaderboard, Analytics, Insights, Reports, Student Profiles, and a custom Rubric 🚀")