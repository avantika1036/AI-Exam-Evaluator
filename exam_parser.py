import os
import re
from docx import Document
import pdfplumber
from pdf2image import convert_from_path
import pytesseract
from PIL import Image

# If Tesseract not auto-detected, set path manually:
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def parse_docx(file_path):
    doc = Document(file_path)
    return [para.text.strip() for para in doc.paragraphs if para.text.strip()]

def parse_pdf_text(file_path):
    text_list = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                text_list.extend(text.splitlines())
    return [line.strip() for line in text_list if line.strip()]

def parse_pdf_image(file_path):
    text_list = []
    images = convert_from_path(file_path)
    for img in images:
        text = pytesseract.image_to_string(img)
        text_list.extend(text.splitlines())
    return [line.strip() for line in text_list if line.strip()]

def parse_image(file_path):
    img = Image.open(file_path)
    text = pytesseract.image_to_string(img)
    return [line.strip() for line in text.splitlines() if line.strip()]

def parse_exam_document(file_path):
    """Auto-detect and extract raw text lines from docx, pdf, or image"""
    ext = os.path.splitext(file_path)[-1].lower()

    if ext == ".docx":
        return parse_docx(file_path)
    elif ext == ".pdf":
        texts = parse_pdf_text(file_path)
        if texts:
            return texts
        return parse_pdf_image(file_path)
    elif ext in [".jpg", ".jpeg", ".png"]:
        return parse_image(file_path)
    else:
        raise ValueError("❌ Unsupported file format. Use .docx, .pdf, .jpg, .jpeg, or .png")

def extract_qa_pairs(lines):
    """Detect flexible Qn / An formats and capture multi-line answers"""
    qa_pairs = []
    current_q, current_a = None, []

    question_pattern = re.compile(r"^(Q|Que|Ques|Question)\s*\d*[\.\)]?", re.IGNORECASE)
    answer_pattern = re.compile(r"^(A|Ans|Answer|Solution|Sol)\s*\d*[\.\)]?", re.IGNORECASE)

    mode = None  # are we currently inside a question or answer?

    for line in lines:
        if question_pattern.match(line):
            # save previous pair if it exists
            if current_q and current_a:
                qa_pairs.append((current_q, " ".join(current_a).strip()))
            # start new question
            current_q = line
            current_a = []
            mode = "q"
        elif answer_pattern.match(line):
            mode = "a"
            current_a.append(line)
        else:
            # continuation of Q or A
            if mode == "q" and current_q:
                current_q += " " + line
            elif mode == "a" and current_a:
                current_a.append(line)

    # save last pair
    if current_q and current_a:
        qa_pairs.append((current_q, " ".join(current_a).strip()))

    return qa_pairs

# 🔹 Test
if __name__ == "__main__":
    file_path = "sample_exam.docx"  # change to your file
    lines = parse_exam_document(file_path)
    qa_pairs = extract_qa_pairs(lines)

    for q, a in qa_pairs:
        print(f"{q} -> {a}")
