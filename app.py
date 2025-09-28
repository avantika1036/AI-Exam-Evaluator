import streamlit as st
import pandas as pd
import io
import os
import zipfile
import plotly.express as px
import plotly.graph_objects as go
from fpdf import FPDF
from exam_evaluator import evaluate_exam_frontend, generate_teacher_insights 
from streamlit_lottie import st_lottie
import requests
import tempfile
import time
from collections import Counter
import numpy as np
from pathlib import Path
import base64

# --- Configuration & Theme Setup ---
st.set_page_config(page_title="AI Exam Evaluator — Class Mode", layout="wide")

# Custom CSS for modern, dark theme with "card" feel
st.markdown(
    """
    <style>
    /* Main Streamlit container */
    .stApp {
        background-color: #0d1117; /* Deep Charcoal Background */
        color: #c9d1d9; /* Light Gray Gray Text */
    }
    /* Titles and Headers */
    h1, h2, h3, h4, h5, h6 {
        color: #2dc4ff; /* Bright Blue Accent */
        font-weight: 600;
        padding-top: 5px; /* Added spacing above headers */
        margin-top: 10px; 
    }
    /* Streamlit Containers/Cards - applies to sections like tabs/expanders/metrics */
    /* *** MODIFIED: Reduced padding back to a tighter standard for smaller cards *** */
    .stMetric, .stTabs, .stExpander, .stAlert, .stFileUploader, .stDataFrame, .stSelectbox, .stProgress, .stDownloadButton, .stSlider {
        background: #161b22; /* Slightly lighter dark for components */
        border-radius: 15px; 
        border: 1px solid #21262d;
        box-shadow: 0 6px 15px rgba(0, 0, 0, 0.3);
        padding: 1rem; /* Kept 1rem for internal component padding */
        margin-bottom: 0.8rem; /* Slightly reduced external margin */
    }
    
    /* Tab Navigation styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 50px !important;  /* Increased gap between tabs */
        background: rgba(22, 32, 50, 0.7);
        padding: 1rem;
        border-radius: 15px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        display: flex;
        justify-content: space-between;  /* Distribute space evenly */
        width: 100%;
    }

    /* Individual tab styling */
    .stTabs [data-baseweb="tab"] {
        padding: 0 30px !important;  /* Increased horizontal padding */
        margin: 0 10px !important;   /* Added margin between tabs */
        flex: 1;                     /* Make tabs take equal space */
        text-align: center;
        min-width: 180px;           /* Minimum width for each tab */
    }

    /* Tab text specific styling */
    .stTabs [data-baseweb="tab"] p {
        font-size: 1.2rem !important;
        font-weight: 600;
        white-space: nowrap;        /* Prevent text wrapping */
        margin: 0 15px !important;  /* Space around text */
    }

    /* Tab list container */
    .stTabs [data-baseweb="tab-list"] {
        gap: 20px;  /* Space between tab containers */
        background: rgba(22, 32, 50, 0.7);
        padding: 1rem;
        border-radius: 15px;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    /* Metric specific styling (Dashboard Text Size Increase) */
    .stMetric > div:first-child { /* Metric label */
        color: #8b949e; 
        font-size: 1.05rem; /* Slightly larger label */
    }
    .stMetric > div:nth-child(2) > div:nth-child(1) { /* Metric value */
        color: #2dc4ff; 
        font-size: 2.8rem; /* Kept large size for impact and readability */
        font-weight: 700;
    }
    /* Student Profile Metrics Container: Added custom border */
    .student-metrics-group {
        border: 2px solid #2dc4ff; /* Accent border */
        border-radius: 15px;
        padding: 15px;
        margin-bottom: 20px;
        background: #111827; /* Darker interior for contrast */
    }
    /* Sidebar styling */
    .css-1d391kg { /* Targetting Streamlit sidebar */
        background-color: #0d1117;
        border-right: 1px solid #21262d;
    }
    /* Buttons */
    .stButton>button {
        border-radius: 10px; /* Slightly larger button radius */
        border: 1px solid #2dc4ff;
        color: #2dc4ff;
        background-color: #161b22;
        transition: all 0.3s;
        font-weight: bold;
    }
    .stButton>button:hover {
        background-color: #2dc4ff;
        color: #0d1117;
        border: 1px solid #161b22;
        box-shadow: 0 0 15px #2dc4ff; /* Stronger hover shadow */
    }
    /* AI Message Box (for Tab 3) */
    .ai-message {
        background-color: #0b1220;
        border-left: 5px solid #ff5757; /* Secondary accent color for AI notes */
        padding: 15px;
        border-radius: 8px;
        margin-top: 10px;
    }
    /* Custom style for specific info boxes (e.g., concepts/feedback) */
    .concept-box {
        background-color: #1a2430; /* Darker interior color */
        padding: 10px;
        border-radius: 8px;
        margin-top: 5px;
        font-size: 0.95rem;
    }
    /* Feedback Text Styling */
    .feedback-text {
        color: #8b949e;
        font-style: italic;
    }
    /* Increased size for medal icons in leaderboard */
    .medal-icon {
        font-size: 1.5em; 
        margin-right: 10px;
    }
    /* Styling for the student profile subheader (making it subtle, not blue) */
    .student-profile-header {
        color: #c9d1d9; /* Subtle light gray */
        font-size: 2rem;
        font-weight: 600;
    }
    /* Ensure student name is bold and legible */
    .student-profile-header strong {
        color: #2dc4ff; /* Keep student name bright for focus */
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# -------------------------
# Helper: load lottie
# -------------------------
def load_lottieurl(url: str):
    r = requests.get(url)
    if r.status_code != 200:
        return None
    return r.json()

def sanitize_text(text):
    """Sanitize text for PDF generation"""
    if not isinstance(text, str):
        return str(text)
    # Replace problematic characters
    replacements = {
        '—': '-',  # em dash
        '"': '"',  # smart quotes
        '"': '"',
        ''': "'",
        ''': "'",
        '…': '...',
        '–': '-',  # en dash
        '•': '*'
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
        return text
# -------------------------
# Session state initialization
# -------------------------
if "trigger_evaluation" not in st.session_state:
    st.session_state["trigger_evaluation"] = False
if "evaluation_complete" not in st.session_state:
    st.session_state["evaluation_complete"] = False
if "class_df" not in st.session_state:
    st.session_state["class_df"] = pd.DataFrame()
if "summary_df" not in st.session_state:
    st.session_state["summary_df"] = pd.DataFrame()

# -------------------------
# Main Page Header & Introduction
# -------------------------
# Use a column layout for the header
header_col1, header_col2 = st.columns([3, 1])

with header_col1:
    st.title("🤝 AI Exam Evaluator — Class Mode")
    st.markdown("""
        The **AI-Powered Grading Assistant** for educators. Upload student exams, set your rubric in the sidebar, 
        and generate detailed class analytics, student reports, and teaching insights in seconds. 
        **Get started by configuring the system in the sidebar.**
    """)

with header_col2:
    # Lottie is a great visual touch, ensuring it loads gracefully
    lottie_url = "https://assets8.lottiefiles.com/packages/lf20_2glqweqs.json" 
    lottie = load_lottieurl(lottie_url)
    if lottie:
        try:
            st_lottie(lottie, height=120, key="coding_lottie")
        except Exception:
            pass

st.markdown("---") # Separator for clean look

# -------------------------
# SIDEBAR: Rubric & Configuration
# -------------------------
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # 1. Rubric Configuration
    criteria_points = {}
    with st.expander("📝 Grading Rubric Setup", expanded=True):
        st.markdown("Define evaluation criteria and maximum points per question.")
        
        # Use simpler layout for inputs in sidebar
        c1 = st.text_input("Criterion 1 Name", "Correctness", key="s_c1_name")
        p1 = st.number_input(f"Max Points for {c1}", min_value=0, value=2, key="s_p1_points")
        
        c2 = st.text_input("Criterion 2 Name", "Clarity", key="s_c2_name")
        p2 = st.number_input(f"Max Points for {c2}", min_value=0, value=2, key="s_p2_points")
        
        c3 = st.text_input("Criterion 3 Name", "Completeness", key="s_c3_name")
        p3 = st.number_input(f"Max Points for {c3}", min_value=0, value=1, key="s_p3_points")
        
        st.markdown("---")
        st.markdown("**Optional Criteria:**")
        
        c4 = st.text_input("Criterion 4 Name (Optional)", "", key="s_c4_name")
        p4 = st.number_input(f"Max Points for {c4}", min_value=0, value=0, key="s_p4_points")
        
        c5 = st.text_input("Criterion 5 Name (Optional)", "", key="s_c5_name")
        p5 = st.number_input(f"Max Points for {c5}", min_value=0, value=0, key="s_p5_points")

        # Process criteria
        criteria_points = {c1: p1, c2: p2, c3: p3}
        if c4 and p4 > 0: criteria_points[c4] = p4
        if c5 and p5 > 0: criteria_points[c5] = p5

        total_max_score_per_question = sum(criteria_points.values())
        st.session_state["rubric_for_ai"] = {k: v / (total_max_score_per_question if total_max_score_per_question > 0 else 1) for k, v in criteria_points.items() if v > 0}
        st.session_state["total_max_score_per_question"] = total_max_score_per_question
        
        st.success(f"Max Score per Question: **{total_max_score_per_question}**")

    # Separator 1
    st.divider()

    # 2. File Upload (mode selection)
    st.subheader("📁 Upload Exams")
    eval_mode = st.radio("Evaluation mode", ["Single Student", "Multiple Students", "ZIP Upload"], horizontal=False)

    uploaded_files = []
    if eval_mode == "Single Student":
        single_file = st.file_uploader(
            "Select student exam file (docx/pdf/jpg/png)",
            type=["docx", "pdf", "jpg", "jpeg", "png"]
        )
        if single_file:
            uploaded_files = [single_file]
            st.info(f"Selected file: {single_file.name}")
            
    elif eval_mode == "Multiple Students":
        uploaded_files = st.file_uploader(
            "Select multiple student exam files",
            accept_multiple_files=True,
            type=["docx", "pdf", "jpg", "jpeg", "png"]
        )
        
    else:  # ZIP Upload mode
        zip_file = st.file_uploader("Upload a ZIP containing exam files", type=["zip"])
        if zip_file:
            tmpdir = Path(tempfile.mkdtemp())
            zpath = tmpdir / "upload.zip"
            # Read file buffer and save to disk
            with open(zpath, "wb") as f:
                f.write(zip_file.getbuffer())
            
            # Use st.status for extraction process
            with st.status(f"Extracting {zip_file.name}...", expanded=True) as status:
                with zipfile.ZipFile(zpath, "r") as z:
                    z.extractall(tmpdir)
                
                allowed_ext = (".docx", ".pdf", ".jpg", ".jpeg", ".png", ".tiff")
                for root, _, files in os.walk(tmpdir):
                    for fname in files:
                        if fname.lower().endswith(allowed_ext):
                            # Store Path objects for easy reading later
                            uploaded_files.append(Path(root) / fname)
                status.update(label=f"Extraction complete! Found {len(uploaded_files)} files.", state="complete", expanded=False)

    # 3. Evaluation Button (Final Action)
    if not uploaded_files:
        st.warning("Upload files to proceed.")
        st.stop()
        
    # Separator 2
    st.divider()
    
    # Store button state in session state to trigger the evaluation logic below
    if st.button("🚀 START CLASS EVALUATION", use_container_width=True, key="eval_button"):
        st.session_state["trigger_evaluation"] = True
        st.session_state["evaluation_complete"] = False
        st.session_state["class_df"] = pd.DataFrame()
        st.session_state["summary_df"] = pd.DataFrame()
        st.rerun()


# -------------------------
# Evaluate Class Logic (Triggered by button press)
# -------------------------
# --- Only run evaluation if trigger_evaluation is True and evaluation_complete is False ---
if st.session_state["trigger_evaluation"] and not st.session_state["evaluation_complete"]:
    st.session_state["trigger_evaluation"] = False  # Reset trigger immediately
    pdf_tmpdir = Path(tempfile.mkdtemp())  # Add this line
    all_rows = []
    student_summaries = []
    total_files = len(uploaded_files)

    with st.status("Processing and evaluating student exams...", expanded=True) as status:
        status.write("Starting evaluation...")
        
        # Add a container for progress tracking
        progress_container = st.empty()
        progress_text = st.empty()
        progress = progress_container.progress(0)

        # Replace the evaluation loop section with this:
        for idx_file, f in enumerate(uploaded_files, start=1):
            student_name = "Unknown Student"  # Default name
            tmp_path = ""
            
            try:
                # Determine how to handle the file object (Path from ZIP vs UploadedFile)
                if isinstance(f, Path):
                    fname = f.name
                    student_name = os.path.splitext(fname)[0]
                    tmp_path = str(f) # Path for evaluation
                    
                else: # Streamlit UploadedFile object (BytesIO)
                    fname = f.name
                    student_name = os.path.splitext(fname)[0]
                    ext = os.path.splitext(fname)[1] or ".pdf"
                    
                    # Save buffer to a temporary file for the backend function
                    tmp_path = os.path.join(tempfile.gettempdir(), f"eval_{student_name}_{int(time.time())}{ext}")
                    f_bytes = f.getbuffer()
                    with open(tmp_path, "wb") as out:
                        out.write(f_bytes)

                # Now update status after we have the student name
                status.update(label=f"Processing **{student_name}** ({idx_file}/{total_files})...")
                
                # --- CORE EVALUATION ---
                results, total_score, max_total = evaluate_exam_frontend(
                    tmp_path, 
                    max_score=st.session_state["total_max_score_per_question"], 
                    rubric=st.session_state["rubric_for_ai"]
                )

                # Update progress bar and text ONLY AFTER successful evaluation
                progress_percent = int((idx_file) / total_files * 100)
                progress.progress(progress_percent)
                progress_text.text(f"Evaluated {idx_file} of {total_files} students ({progress_percent}%)")

                # --- END CORE EVALUATION ---

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

                # --- PDF Report Generation ---
                pdf = FPDF()
                pdf.add_page()
                
                pdf.set_font("Arial", "B", 14)
                pdf.cell(0, 10, sanitize_text(f"AI Exam Evaluation — {student_name}"), ln=True, align="C")
                pdf.ln(6)
                pdf.set_font("Arial", "", 12)
                pdf.cell(0, 8, sanitize_text(f"Total Score: {total_score}/{max_total}"), ln=True)
                pdf.ln(4)
                
                for i, r in enumerate(results, start=1):
                    pdf.set_font("Arial", "B", 12)
                    pdf.multi_cell(0, 8, sanitize_text(f"Q{i}: {r.get('question', '')}"))
                    pdf.set_font("Arial", "", 12)
                    pdf.multi_cell(0, 8, sanitize_text(f"Student Answer: {r.get('answer','')}"), border=0)
                    pdf.multi_cell(0, 8, sanitize_text(f"Score: {r.get('score',0)}/{st.session_state['total_max_score_per_question']}"))
                    for crit in criteria_points.keys():
                        if criteria_points[crit] > 0:
                            pdf.multi_cell(0, 8, sanitize_text(f"  - {crit}: {r.get(f'score_{crit}', 0)}/{criteria_points[crit]}"))
                    pdf.multi_cell(0, 8, sanitize_text(f"Feedback: {r.get('feedback','')}"), border=0)
                    concepts = ", ".join(r.get("concepts", []))
                    if concepts:
                        pdf.multi_cell(0, 8, sanitize_text(f"Matched Concepts: {concepts}"))
                    pdf.ln(3)

                pdf_path = str(pdf_tmpdir / f"{student_name}_report.pdf")
                pdf.output(pdf_path)

                percentage = round(100 * total_score / max_total, 2) if max_total else 0
                student_summaries.append({
                    "student": student_name,
                    "total_score": total_score,
                    "max_total": max_total,
                    "percentage": percentage,
                    "pdf_path": pdf_path
                })
                time.sleep(0.1) # Debounce
                
            except Exception as e:
                st.error(f"Error evaluating **{student_name}**: {e}")
                status.write(f"⚠️ Failed to evaluate {student_name}.")
                continue

        # Complete the progress
        progress.progress(100)
        progress_text.text(f"Evaluated all {total_files} students (100%)")
        # Finalize status
        status.update(label="✅ Evaluation complete for all uploaded students!", state="complete", expanded=False)

    if not student_summaries:
        st.warning("No student files were successfully evaluated. Please check the files and try again.")
        st.stop()
    
    # Build DataFrames
    class_df = pd.DataFrame(all_rows)
    if class_df.empty:
        st.error("No extracted Q/A rows — check parser output or file contents.")
        st.stop()
        
    summary_df = pd.DataFrame(student_summaries).sort_values(by="total_score", ascending=False).reset_index(drop=True)
    summary_df.index += 1 # 1-based ranking
    
    # Store dataframes in session state
    st.session_state["class_df"] = class_df
    st.session_state["summary_df"] = summary_df
    st.session_state["evaluation_complete"] = True

# --- Now, OUTSIDE the above block, display results if evaluation_complete is True ---
if st.session_state["evaluation_complete"]:
    class_df = st.session_state["class_df"]
    summary_df = st.session_state["summary_df"]

    # -------------------------
    # Display Results (WOW FACTOR UI)
    # -------------------------
    
    # Check again if data exists in session state
    if st.session_state["class_df"].empty:
         st.warning("Please configure the rubric and upload files in the sidebar, then press 'START CLASS EVALUATION'.")
         st.stop()

    class_df = st.session_state["class_df"]
    summary_df = st.session_state["summary_df"]

    # --- Global Class Metrics (New WOW section) ---
    st.subheader("🎓 Class Summary")
    
    avg_percentage = summary_df["percentage"].mean()
    median_score = summary_df["total_score"].median()
    max_achieved_score = summary_df["total_score"].max()
    
    col_a, col_b, col_c, col_d = st.columns(4)
    with col_a:
        # Removed Icon/Emoji
        st.metric(label="Total Students Evaluated", value=len(summary_df), delta="Files Processed")
    with col_b:
        total_max = st.session_state['total_max_score_per_question'] * class_df['question_index'].nunique()
        # Removed Icon/Emoji
        st.metric(label="Class Average Score (%)", value=f"{avg_percentage:.1f}%", 
                  delta=f"{summary_df['total_score'].mean():.1f} / {total_max:.1f} Max")
    with col_c:
        # Removed Icon/Emoji
        st.metric(label="Median Total Score", value=f"{median_score:.1f}", 
                  delta="50% of scores below this")
    with col_d:
        # Removed Icon/Emoji
        st.metric(label="Top Score Achieved", value=f"{max_achieved_score:.1f}", 
                  delta=f"Rank 1 student score")

    st.markdown("---")


    tab1, tab2, tab3, tab4, tab5 = st.tabs(["🏆 Leaderboard", "📊 Detailed Analytics", "💡 AI Insights", "📥 Reports & Downloads", "🎓 Student Profiles"])

    # Leaderboard
    with tab1:
        st.header("🏆 Class Leaderboard")
        st.markdown("Detailed breakdown of student performance and ranking.")

        # Define medal icons with larger font size via CSS class
        MEDALS = {
            1: '<span class="medal-icon">🥇</span> Gold Medal', 
            2: '<span class="medal-icon">🥈</span> Silver Medal', 
            3: '<span class="medal-icon">🥉</span> Bronze Medal'
        }

        # Show Top 3 Visually
        top3 = summary_df.head(3)
        cols = st.columns(3)
        
        for i, row in top3.iterrows():
            with cols[i-1]:
                total = int(round(row['total_score']))
                max_score = int(round(row['max_total']))
                percentage = int(round(row['percentage']))
                
                # Use st.markdown for the medal label to apply custom CSS class
                st.markdown(f"#### {MEDALS.get(i, f'Rank {i}')}: {row['student']}", unsafe_allow_html=True)
                
                st.metric(
                    label="Score", # Simple label since the title has the name
                    value=f"{total}/{max_score}", 
                    delta=f"{percentage}%"
                )
        
        st.markdown("---")
        
        # Filterable Data Table
        st.subheader("Full Class Ranking")
        min_score = st.slider("Filter students by minimum percentage score", 0, 100, 0, key="leader_filter")
        filtered = summary_df[summary_df["percentage"] >= min_score]
        
        st.info(f"Showing **{len(filtered)}** out of **{len(summary_df)}** students.")
        
        # Enhanced Dataframe styling: Use a blue gradient on percentage for score highlight
        styled_df = filtered.rename_axis('Rank').style.background_gradient(
            cmap='Blues', # Simpler, less aggressive gradient than plasma
            subset=['percentage']
        ).format({
            'total_score': '{:.1f}', 
            'max_total': '{:.1f}',
            'percentage': '{:.1f}%'
        })
        
        st.dataframe(styled_df, use_container_width=True)

    # Class Analytics
    with tab2:
        st.header("📊 Detailed Class Analytics")
        
        # Row 1: Question Performance
        st.subheader("Question Performance Breakdown")
        q_avg = class_df.groupby("question_index")["score"].mean().reset_index().rename(columns={"score": "avg_score"})
        fig_q = px.bar(q_avg, x="question_index", y="avg_score", 
                        title="Average Score per Question (Class)",
                        labels={"question_index": "Question #", "avg_score": "Average Score"},
                        color_discrete_sequence=['#2dc4ff']) # Use the accent color
        
        avg_score_class = q_avg["avg_score"].mean()
        fig_q.add_hline(y=avg_score_class, line_dash="dash", line_color="#ff5757", line_width=2,
                        annotation_text=f"Class Avg: {avg_score_class:.2f}",
                        annotation_position="top right")
        
        fig_q.update_layout(xaxis={'categoryorder':'category ascending'})
        st.plotly_chart(fig_q, use_container_width=True)
        
        st.markdown("---")

        # Row 2: Rubric Criterion Performance
        st.subheader("Rubric Criterion Performance (Average Class Score)")

        rubric_keys = [f'score_{crit}' for crit in criteria_points.keys() if criteria_points.get(crit, 0) > 0]
        rubric_avg = class_df[rubric_keys].mean().reset_index()
        rubric_avg.columns = ["Criterion_Key", "Avg_Score"]
        rubric_avg['Criterion'] = rubric_avg['Criterion_Key'].apply(lambda x: x.replace('score_', ''))
        
        max_scores = {f'score_{k}': v for k, v in criteria_points.items() if v > 0}
        rubric_avg['Max_Score'] = rubric_avg['Criterion_Key'].map(max_scores)
        rubric_avg['Score_Difference'] = rubric_avg['Max_Score'] - rubric_avg['Avg_Score']

        # Stacked bar chart showing achieved score vs potential max score for each criterion
        fig_rubric = go.Figure(data=[
            # Achieved Score Bar
            go.Bar(
                name='Achieved Score',
                x=rubric_avg['Criterion'],
                y=rubric_avg['Avg_Score'],
                marker_color='#2dc4ff'
            ),
            # Difference Bar (Max Score - Achieved Score)
            go.Bar(
                name='Max Score Difference',
                x=rubric_avg['Criterion'],
                y=rubric_avg['Score_Difference'],
                marker_color='rgba(255, 255, 255, 0.1)', # Subtle background color
            )
        ])

        fig_rubric.update_layout(
            barmode='stack',
            title='Class Average Performance by Rubric Criterion',
            yaxis_title='Average Score Achieved',
            showlegend=False,
            height=400
        )
        st.plotly_chart(fig_rubric, use_container_width=True)
        
        st.markdown("---")

        # Row 3: Score Distribution and Heatmap
        col_charts1, col_charts2 = st.columns(2)
        
        with col_charts1:
            st.subheader("Score Distribution (Percentage)")
            fig_hist = px.histogram(summary_df, x="percentage", nbins=10, 
                                    title="Student Score Distribution",
                                    color_discrete_sequence=['#2dc4ff'])
            fig_hist.update_layout(bargap=0.1)
            st.plotly_chart(fig_hist, use_container_width=True)
            
        with col_charts2:
            st.subheader("Score Spread & Outliers")
            fig_box = px.box(summary_df, y="percentage", title="Score Spread (Box Plot)")
            st.plotly_chart(fig_box, use_container_width=True)

        st.markdown("---")
        st.subheader("Student-Question Performance Heatmap")
        pivot = class_df.pivot_table(index="student", columns="question_index", values="score", fill_value=0)
        
        # Use a more visually appealing color scale related to the theme
        fig_heat = px.imshow(pivot, labels=dict(x="Question #", y="Student", color="Score"),
                             aspect="auto", 
                             title="Score Heatmap: Student vs Question Scores",
                             color_continuous_scale=[(0, 'rgb(33, 38, 45)'), (1, '#2dc4ff')]) # Dark background to blue
        st.plotly_chart(fig_heat, use_container_width=True)


    # AI Insights
    with tab3:
        st.header("💡 AI Teaching Insights")
        st.markdown("Leverage AI to identify areas of weakness, core misconceptions, and personalized teaching notes.")

        # Hardest Questions
        q_avg_with_questions = class_df.groupby("question_index").agg(
            avg_score=("score", "mean"),
            question_text=("question", "first")
        ).reset_index().sort_values("avg_score")
        
        st.subheader("🔥 Top 3 Challenge Areas")
        worst = q_avg_with_questions.head(3)
        
        challenge_cols = st.columns(3)
        for i, (_, r) in enumerate(worst.iterrows()):
            with challenge_cols[i]:
                # Use a smaller container card for impact
                with st.container():
                    st.markdown(f"#### Question {int(r['question_index'])}: {r['question_text']}")
                    st.markdown(f"**Avg Score:** {round(r['avg_score'], 2)} / {st.session_state['total_max_score_per_question']}")

        st.markdown("---")
        
        # Concept Frequency
        concepts_series = class_df["concepts"].dropna().astype(str)
        all_concepts = []
        for s in concepts_series:
            if s.strip():
                for c in s.split(","):
                    all_concepts.append(c.strip())
        
        concept_counts = pd.Series(all_concepts).value_counts().reset_index()
        concept_counts.columns = ["Concept", "Frequency"]
        
        if not concept_counts.empty:
            st.subheader("🧠 Most Frequent Concepts Mentioned (Indicator of Core Focus)")
            fig_concepts = px.bar(concept_counts.head(10), x="Concept", y="Frequency",
                                  title="Top 10 Most Common Concepts Identified in Answers",
                                  color_discrete_sequence=['#ff5757']) # Secondary accent color
            st.plotly_chart(fig_concepts, use_container_width=True)
            
            # Use an expander for the full list
            with st.expander("View Full Concept Frequency List"):
                for concept, cnt in Counter(all_concepts).most_common():
                    st.write(f"- **{concept}**: mentioned {cnt} times")

        st.markdown("---")
        
        # AI Teacher Notes
        st.subheader("📝 Personalized AI Teacher Notes")
        
        if st.button("Generate AI Teaching Insights", key="ai_notes_button"):
            with st.status("Generating expert teaching insights and class summary...", expanded=True) as status:
                try:
                    from exam_evaluator import init_client
                    client, model = init_client()
                    
                    # Generate insights
                    prompt = generate_teacher_insights(class_df, summary_df)
                    response = client.complete(
                        model=model,
                        messages=[
                            {"role": "system", "content": "You are an experienced teaching assistant. Provide actionable, concise teaching recommendations based on the data."},
                            {"role": "user", "content": prompt}
                        ]
                    )
                    
                    insights = response.choices[0].message["content"]
                    st.markdown(f'<div class="ai-message"><h4>🤖 AI Teaching Assistant Report</h4>{insights}</div>', unsafe_allow_html=True)
                    status.update(label="Insight Generation Complete!", state="complete", expanded=False)
                    
                except Exception as e:
                    # Mocking the response for presentation if the external function fails
                    insights_mock = """
                    **Overall Class Performance:** The class average of **{:.1f}%** is solid, but there's a significant spread in scores (IQR suggests high variance). The high success rate on early questions suggests strong foundational knowledge, but difficulty spikes later.
                    
                    **Actionable Teaching Focus:**
                    1. **Reteach Concepts:** The concepts **'{}'** and **'{}'** were most frequently mentioned but often linked to lower scores or incomplete answers. Dedicate a full session to re-explaining these areas with new examples.
                    2. **Question Q{}:** This question yielded the lowest average score ({:.2f}). Consider breaking down this problem into smaller steps to diagnose where the class is getting stuck (e.g., setup vs. calculation).
                    
                    _**Error Note:** Could not connect to backend AI service. Showing a mock report. Full error: {}. Please check your external configuration._
                    """.format(
                        avg_percentage, 
                        concept_counts.iloc[0]['Concept'] if not concept_counts.empty else 'Placeholder Concept A',
                        concept_counts.iloc[1]['Concept'] if len(concept_counts) > 1 else 'Placeholder Concept B',
                        worst.iloc[0]['question_index'] if not worst.empty else 1, 
                        worst.iloc[0]['avg_score'] if not worst.empty else 0.0,
                        str(e)
                    )

                    st.markdown(f'<div class="ai-message"><h4>🤖 AI Teaching Assistant Report (Error Mock)</h4>{insights_mock}</div>', unsafe_allow_html=True)
                    st.error("Could not generate AI insights. Check console for details.")
                    status.update(label="Insight Generation Failed", state="error", expanded=False)


    # Reports
    with tab4:
        st.header("📥 Reports & Downloads")
        st.markdown("Generate and download comprehensive data and individual student reports.")

        col_d1, col_d2, col_d3 = st.columns(3)

        # 1. Class CSV
        csv_bytes = class_df.to_csv(index=False).encode("utf-8")
        with col_d1:
            st.download_button("Download Class CSV", data=csv_bytes, 
                                file_name="class_evaluation_all_data.csv", mime="text/csv", 
                                use_container_width=True)

        # 2. Class Excel
        excel_io = io.BytesIO()
        with pd.ExcelWriter(excel_io, engine="xlsxwriter") as writer:
            class_df.to_excel(writer, sheet_name="AllAnswers", index=False)
            summary_df.to_excel(writer, sheet_name="Summary", index=True)
        with col_d2:
            st.download_button("Download Class Excel", data=excel_io.getvalue(),
                                 file_name="class_evaluation_summary.xlsx",
                                 mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                 use_container_width=True)

        # 3. All Student PDFs (ZIP)
        zip_io = io.BytesIO()
        
        with zipfile.ZipFile(zip_io, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            for _, row in summary_df.iterrows():
                pdf_path = row["pdf_path"]
                if os.path.exists(pdf_path):
                    # Write only if file exists, using student name for arcname
                    zf.write(pdf_path, arcname=os.path.basename(pdf_path))
        
        zip_io.seek(0)
        with col_d3:
            st.download_button("Download All Student PDFs (ZIP)", data=zip_io.getvalue(),
                                 file_name="all_student_reports.zip", mime="application/zip",
                                 use_container_width=True)
                                 
        st.info("Files contain detailed rubric scores, feedback, and Q&A data.")


    # Student Profiles
    with tab5:
        st.header("🎓 Student Profiles")
        student_list = ["- Select a student -"] + summary_df["student"].tolist()
        
        # Use a clean selectbox
        selected_student = st.selectbox("Select a student to view their detailed performance profile:", student_list)

        if selected_student != "- Select a student -":
            
            student_summary = summary_df[summary_df["student"] == selected_student].iloc[0]
            student_data = class_df[class_df["student"] == selected_student].copy()

            # Custom styled header: used CSS class 'student-profile-header'
            st.markdown(f'<h3 class="student-profile-header">✨ Profile for <strong>{selected_student}</strong></h3>', unsafe_allow_html=True)
            
            # Custom styled container for the main metrics block
            st.markdown('<div class="student-metrics-group">', unsafe_allow_html=True)
            col_s1, col_s2, col_s3 = st.columns(3)
            
            with col_s1:
                total_score = int(round(student_summary['total_score']))
                max_total = int(round(student_summary['max_total']))
                st.metric(label="Overall Score", value=f"{total_score}/{max_total}")
            with col_s2:
                st.metric(label="Percentage", value=f"{student_summary['percentage']:.1f}%")
            with col_s3:
                st.metric(label="Class Rank", value=f"#{student_summary.name}")
            st.markdown('</div>', unsafe_allow_html=True)
                
            
            # PDF Download Button (Prominent placement)
            pdf_path = student_summary["pdf_path"]
            if os.path.exists(pdf_path):
                with open(pdf_path, "rb") as pdf_file:
                    st.download_button(
                        label=f"📥 Download {selected_student}'s Detailed Report",
                        data=pdf_file,
                        file_name=f"{selected_student}_report.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
            
            st.markdown("---")

            # Charts Section
            chart_col1, chart_col2 = st.columns(2)
            
            with chart_col1:
                # Bar Chart: Score Per Question
                fig_bar = px.bar(student_data, x="question_index", y="score", 
                                 title="Score Per Question Breakdown",
                                 labels={"question_index": "Question #", "score": "Score"},
                                 color_discrete_sequence=['#ff5757'])
                fig_bar.update_layout(xaxis={'categoryorder':'category ascending'})
                st.plotly_chart(fig_bar, use_container_width=True)

            with chart_col2:
                # Radar Chart: Rubric Score Breakdown
                rubric_keys = [f'score_{crit}' for crit in st.session_state["rubric_for_ai"].keys()]
                rubric_scores = student_data[rubric_keys].sum()
                rubric_points = {crit: points for crit, points in criteria_points.items() if points > 0}
                # Calculate max possible score across all questions for each rubric criterion
                num_questions = student_data.shape[0]
                max_rubric_values = [v * num_questions for v in rubric_points.values()]
                
                fig_radar = go.Figure()
                fig_radar.add_trace(go.Scatterpolar(
                    r=rubric_scores.values,
                    theta=list(rubric_points.keys()),
                    fill='toself',
                    name='Student Performance',
                    line_color='#2dc4ff',
                    fillcolor='rgba(45, 196, 255, 0.2)'
                ))
                fig_radar.update_layout(
                    polar=dict(
                        radialaxis=dict(
                            visible=True,
                            range=[0, max(max_rubric_values) if max(max_rubric_values) > 0 else 1] # Ensure non-empty range
                        )
                    ),
                    title="Aggregated Rubric Performance"
                )
                st.plotly_chart(fig_radar, use_container_width=True)

            # Detailed Q&A Breakdown
            st.subheader("Detailed Question & Feedback")
            for _, row in student_data.iterrows():
                # Use an expander for each Q&A pair for cleaner layout
                with st.expander(f"**Question {int(row['question_index'])}:** {row['question'][:60]}...", expanded=False):
                    
                    # Row 1: Question and Answer
                    st.markdown(f"**Full Question:** **{row['question']}**")
                    st.markdown(f"**Student Answer:** `{row['answer']}`")
                    st.markdown("---")

                    # Row 2: Score and Concepts
                    col_q_score, col_q_concepts = st.columns([1, 2])
                    with col_q_score:
                         st.metric(label="Question Score", value=f"{row['score']}/{st.session_state['total_max_score_per_question']}")
                    with col_q_concepts:
                         st.info(f"**Concepts Identified:** {row['concepts']}")
                         
                    # Row 3: Feedback
                    # Used custom feedback text class
                    st.markdown(f"**AI Feedback:** <span class='feedback-text'>{row['feedback']}</span>", unsafe_allow_html=True)
                    
                    # Row 4: Rubric details
                    rubric_str = [f"**{crit}** ({row.get(f'score_{crit}', 0)}/{criteria_points.get(crit, 0)})" 
                                  for crit in criteria_points.keys() 
                                  if criteria_points.get(crit, 0) > 0]
                    st.markdown(f"**Rubric Breakdown:** {', '.join(rubric_str)}")

        else:
             st.info("Select a student from the dropdown above to view their individualized report, scores, and performance breakdown.")
             
    st.success("✨ The UI has been updated: Card sizing has been made more compact, metric values remain large, and tab labels are now increased for better clarity.")
