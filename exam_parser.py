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
    """Return a list of non-empty lines from a .docx file (split paragraphs into lines)."""
    doc = Document(file_path)
    lines = []
    for p in doc.paragraphs:
        for l in p.text.splitlines():
            l = l.strip()
            if l:
                lines.append(l)
    return lines

def parse_pdf_text(file_path):
    """Extract text lines from a text-based PDF using pdfplumber."""
    text_list = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                for line in text.splitlines():
                    line = line.strip()
                    if line:
                        text_list.append(line)
    return text_list

def parse_pdf_image(file_path):
    """OCR fallback for scanned PDFs: convert pages to images then OCR each page."""
    text_list = []
    images = convert_from_path(file_path)
    for img in images:
        text = pytesseract.image_to_string(img)
        for line in text.splitlines():
            line = line.strip()
            if line:
                text_list.append(line)
    return text_list

def parse_image(file_path):
    """OCR single image files (.jpg, .png, etc.)."""
    img = Image.open(file_path)
    text = pytesseract.image_to_string(img)
    return [line.strip() for line in text.splitlines() if line.strip()]

def parse_exam_document(file_path):
    """Auto-detect file type and return a list of cleaned lines."""
    ext = os.path.splitext(file_path)[-1].lower()
    if ext == ".docx":
        return parse_docx(file_path)
    elif ext == ".pdf":
        lines = parse_pdf_text(file_path)
        if lines:
            return lines
        return parse_pdf_image(file_path)
    elif ext in [".jpg", ".jpeg", ".png", ".tiff"]:
        return parse_image(file_path)
    else:
        raise ValueError("❌ Unsupported file format. Use .docx, .pdf, .jpg, .jpeg, .png, or .tiff")

# --- Robust QA extractor ---------------------------------------------------
# Recognizes many prefixes: Q, Q1., Question 1), Q:, A:, Ans:, Answer:, Solution, etc.

QUESTION_PREFIX = re.compile(
    r'^\s*(?:q|question|que|ques)\s*(?:\d+)?\s*(?:[:\.\)\-])\s*', re.IGNORECASE
)
ANSWER_PREFIX = re.compile(
    r'^\s*(?:a|ans|answer|solution|sol)\s*(?:\d+)?\s*(?:[:\.\)\-])\s*', re.IGNORECASE
)

# Also detect inline "A:" or "Answer:" inside a single line
INLINE_ANSWER_MARKER = re.compile(r'\b(?:a|ans|answer|solution|sol)\s*(?:\d+)?\s*[:\.\)]', re.IGNORECASE)
INLINE_QUESTION_MARKER = re.compile(r'\b(?:q|question|que|ques)\s*(?:\d+)?\s*[:\.\)]', re.IGNORECASE)

def extract_qa_pairs(lines):
    """
    Robust extractor that:
      - Handles Q:/A: on same line or same paragraph split into lines
      - Accumulates multi-line questions/answers
      - Falls back to heuristics if explicit markers absent
    Returns: list of (question_text, answer_text)
    """
    qa_pairs = []
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i].strip()
        if not line:
            i += 1
            continue

        # CASE 1: Single line contains both question and answer markers (e.g., "Q: ... A: ...")
        # Find the earliest answer marker in the line (if any)
        ans_match_inline = INLINE_ANSWER_MARKER.search(line)
        q_match_inline = INLINE_QUESTION_MARKER.search(line)

        if q_match_inline:
            # If both appear inline, split
            if ans_match_inline and ans_match_inline.start() > q_match_inline.start():
                # split into question / answer parts
                q_part = line[:ans_match_inline.start()].strip()
                a_part = line[ans_match_inline.start():].strip()
                # remove prefixes
                q_text = QUESTION_PREFIX.sub('', q_part).strip()
                a_text = ANSWER_PREFIX.sub('', a_part).strip()
                qa_pairs.append((q_text, a_text))
                i += 1
                continue

            # If there's a question marker inline but no inline answer marker,
            # treat this as a question line and attempt to gather following lines as the answer.
            if QUESTION_PREFIX.match(line) or q_match_inline:
                q_text = QUESTION_PREFIX.sub('', line).strip()
                # accumulate continued question lines until we hit an explicit answer or next question
                j = i + 1
                while j < n and not ANSWER_PREFIX.match(lines[j]) and not QUESTION_PREFIX.match(lines[j]) and not INLINE_ANSWER_MARKER.search(lines[j]):
                    # stop accumulation if the next line looks like a new question (rare)
                    # but allow normal continuation lines
                    q_text += " " + lines[j].strip()
                    j += 1

                # now attempt to find answer starting at j
                a_text = ""
                if j < n and (ANSWER_PREFIX.match(lines[j]) or INLINE_ANSWER_MARKER.search(lines[j])):
                    # line j starts answer or contains inline answer
                    # if inline marker exists, split
                    if INLINE_ANSWER_MARKER.search(lines[j]):
                        # split the j line at answer marker
                        m = INLINE_ANSWER_MARKER.search(lines[j])
                        a_part = lines[j][m.start():].strip()
                        a_text = ANSWER_PREFIX.sub('', a_part).strip()
                        k = j + 1
                        while k < n and not QUESTION_PREFIX.match(lines[k]) and not ANSWER_PREFIX.match(lines[k]) and not INLINE_ANSWER_MARKER.search(lines[k]):
                            a_text += " " + lines[k].strip()
                            k += 1
                        i = k
                    else:
                        # normal answer-starting line
                        a_text = ANSWER_PREFIX.sub('', lines[j]).strip()
                        k = j + 1
                        while k < n and not QUESTION_PREFIX.match(lines[k]) and not ANSWER_PREFIX.match(lines[k]) and not INLINE_ANSWER_MARKER.search(lines[k]):
                            a_text += " " + lines[k].strip()
                            k += 1
                        i = k
                    qa_pairs.append((q_text.strip(), a_text.strip()))
                    continue
                else:
                    # no explicit answer found - skip/question only
                    i = j
                    continue

        # CASE 2: Line starts with Question prefix (Q1., Q: etc)
        if QUESTION_PREFIX.match(line):
            q_text = QUESTION_PREFIX.sub('', line).strip()
            # gather following lines until an answer line is found
            j = i + 1
            while j < n and not ANSWER_PREFIX.match(lines[j]) and not QUESTION_PREFIX.match(lines[j]) and not INLINE_ANSWER_MARKER.search(lines[j]):
                q_text += " " + lines[j].strip()
                j += 1

            # now gather answer if present
            a_text = ""
            if j < n and (ANSWER_PREFIX.match(lines[j]) or INLINE_ANSWER_MARKER.search(lines[j])):
                if INLINE_ANSWER_MARKER.search(lines[j]):
                    m = INLINE_ANSWER_MARKER.search(lines[j])
                    a_part = lines[j][m.start():].strip()
                    a_text = ANSWER_PREFIX.sub('', a_part).strip()
                    k = j + 1
                    while k < n and not QUESTION_PREFIX.match(lines[k]) and not ANSWER_PREFIX.match(lines[k]) and not INLINE_ANSWER_MARKER.search(lines[k]):
                        a_text += " " + lines[k].strip()
                        k += 1
                    i = k
                else:
                    a_text = ANSWER_PREFIX.sub('', lines[j]).strip()
                    k = j + 1
                    while k < n and not QUESTION_PREFIX.match(lines[k]) and not ANSWER_PREFIX.match(lines[k]) and not INLINE_ANSWER_MARKER.search(lines[k]):
                        a_text += " " + lines[k].strip()
                        k += 1
                    i = k
                qa_pairs.append((q_text.strip(), a_text.strip()))
                continue
            else:
                # question without answer; advance and continue
                i = j
                continue

        # CASE 3: Line starts with Answer prefix (or orphan answer)
        if ANSWER_PREFIX.match(line):
            # if we find an answer with no preceding question, attempt to use the previous non-empty line as question
            a_text = ANSWER_PREFIX.sub('', line).strip()
            k = i + 1
            while k < n and not QUESTION_PREFIX.match(lines[k]) and not ANSWER_PREFIX.match(lines[k]) and not INLINE_ANSWER_MARKER.search(lines[k]):
                a_text += " " + lines[k].strip()
                k += 1
            # look back for the last line that looks like a question
            prev_q = None
            for back in range(i-1, -1, -1):
                if QUESTION_PREFIX.match(lines[back]) or INLINE_QUESTION_MARKER.search(lines[back]):
                    prev_q = QUESTION_PREFIX.sub('', lines[back]).strip()
                    break
                if lines[back].strip():
                    prev_q = lines[back].strip()
                    break
            if prev_q:
                qa_pairs.append((prev_q, a_text.strip()))
            i = k
            continue

        # CASE 4: fallback heuristics: if no explicit markers found, 
        # look for lines where a line ends with '?' (likely a question) and next non-empty line is an answer-like sentence.
        if line.endswith('?'):
            q_text = line
            j = i + 1
            # gather next lines until next question or blank
            a_text = ""
            while j < n and not lines[j].endswith('?') and not QUESTION_PREFIX.match(lines[j]) and not ANSWER_PREFIX.match(lines[j]):
                a_text += (" " + lines[j].strip())
                j += 1
            if a_text.strip():
                qa_pairs.append((q_text.strip(), a_text.strip()))
                i = j
                continue

        # Otherwise, advance
        i += 1

    return qa_pairs

# Simple test when running this file directly
if __name__ == "__main__":
    test_file = "sample_exam.docx"
    if os.path.exists(test_file):
        lines = parse_exam_document(test_file)
        pairs = extract_qa_pairs(lines)
        print(f"Found {len(pairs)} Q&A pairs in {test_file}")
        for idx, (q,a) in enumerate(pairs,1):
            print(f"\nQ{idx}: {q}\nA{idx}: {a}\n")
    else:
        print("No local sample_exam.docx found. Use parse_exam_document(path) and extract_qa_pairs(lines).")
