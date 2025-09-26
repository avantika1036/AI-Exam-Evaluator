import os
import re
from docx import Document
import pdfplumber
import google.genai as genai
from PIL import Image
import json

# Initialize the Gemini client
client = genai.Client()

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

def parse_pdf_or_image_with_gemini(file_path):
    """
    Parse a PDF or image file (including handwritten) using the Gemini API.
    This function sends the image data and a prompt to the model to extract
    Q&A pairs and returns them as a list of tuples to match the expected format.
    """
    with open(file_path, 'rb') as f:
        file_bytes = f.read()

    ext = os.path.splitext(file_path)[-1].lower()
    if ext in ['.jpg', '.jpeg']:
        mime_type = 'image/jpeg'
    elif ext == '.png':
        mime_type = 'image/png'
    elif ext == '.pdf':
        mime_type = 'application/pdf'
    else:
        raise ValueError("Unsupported file format for Gemini parsing.")

    file_part = genai.types.Part.from_bytes(data=file_bytes, mime_type=mime_type)

    prompt = """
    Analyze the uploaded document, which may be a handwritten exam page. 
    Identify and extract all distinct question-answer pairs. 
    A question is typically followed by an answer. 
    Format the output as a JSON list of objects, where each object has a 'question' key and an 'answer' key.
    Example:
    [
      { "question": "What is the capital of France?", "answer": "Paris" },
      { "question": "What is 2+2?", "answer": "4" }
    ]
    If no question-answer pairs are found, return an empty JSON list.
    """
    
    response = client.models.generate_content(
    model='models/gemini-2.0-flash-lite',  # choose latest version
    contents=[prompt, file_part]
)
    
    try:
        json_string = response.text.strip().removeprefix('```json\n').removesuffix('\n```')
        qa_pairs_dicts = json.loads(json_string)
        
        # Convert the list of dictionaries into a list of tuples to match the format
        qa_pairs_tuples = [(item['question'], item['answer']) for item in qa_pairs_dicts]
        
        return qa_pairs_tuples
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from Gemini response: {e}")
        print("The response was:")
        print(response.text)
        return []

def extract_qa_pairs(lines):
    """
    Robust extractor that handles various text-based question and answer formats.
    Returns: list of (question_text, answer_text)
    """
    qa_pairs = []
    i = 0
    n = len(lines)

    QUESTION_PREFIX = re.compile(
        r'^\s*(?:q|question|que|ques)\s*(?:\d+)?\s*(?:[:\.\)\-])\s*', re.IGNORECASE
    )
    ANSWER_PREFIX = re.compile(
        r'^\s*(?:a|ans|answer|solution|sol)\s*(?:\d+)?\s*(?:[:\.\)\-])\s*', re.IGNORECASE
    )
    INLINE_ANSWER_MARKER = re.compile(r'\b(?:a|ans|answer|solution|sol)\s*(?:\d+)?\s*[:\.\)]', re.IGNORECASE)
    INLINE_QUESTION_MARKER = re.compile(r'\b(?:q|question|que|ques)\s*(?:\d+)?\s*[:\.\)]', re.IGNORECASE)

    while i < n:
        line = lines[i].strip()
        if not line:
            i += 1
            continue

        if QUESTION_PREFIX.match(line):
            q_text = QUESTION_PREFIX.sub('', line).strip()
            j = i + 1
            while j < n and not ANSWER_PREFIX.match(lines[j]) and not QUESTION_PREFIX.match(lines[j]):
                q_text += " " + lines[j].strip()
                j += 1
            
            a_text = ""
            if j < n and ANSWER_PREFIX.match(lines[j]):
                a_text = ANSWER_PREFIX.sub('', lines[j]).strip()
                k = j + 1
                while k < n and not QUESTION_PREFIX.match(lines[k]) and not ANSWER_PREFIX.match(lines[k]):
                    a_text += " " + lines[k].strip()
                    k += 1
                i = k
            else:
                i = j
                continue
            
            qa_pairs.append((q_text.strip(), a_text.strip()))
            continue

        i += 1
    return qa_pairs

def parse_exam_document(file_path):
    """
    Auto-detect file type and return a list of Q&A pairs.
    Uses Gemini for image and PDF handling, and the original functions for DOCX.
    """
    ext = os.path.splitext(file_path)[-1].lower()
    if ext == ".docx":
        # The correct logic is to return lines here, then extract pairs in the calling function
        lines = parse_docx(file_path)
        return lines
    elif ext in [".pdf", ".jpg", ".jpeg", ".png", ".tiff"]:
        return parse_pdf_or_image_with_gemini(file_path)
    else:
        raise ValueError("❌ Unsupported file format. Use .docx, .pdf, .jpg, .jpeg, .png, or .tiff")

if __name__ == "__main__":
    test_file_image = "tests/test2.jpg"
    test_file_docx = "tests/sample_exam.docx"

    
    if os.path.exists(test_file_image):
        print(f"Processing {test_file_image} with Gemini API...")
        qa_pairs = parse_exam_document(test_file_image)
        if qa_pairs:
            print(f"Found {len(qa_pairs)} Q&A pairs:")
            for idx, (q, a) in enumerate(qa_pairs, 1):
                print(f"\nQ{idx}: {q}\nA{idx}: {a}\n")
        else:
            print("No Q&A pairs were found.")
    else:
        print("No local sample image file found. Please create one to test.")

    if os.path.exists(test_file_docx):
        print(f"\nProcessing {test_file_docx} with text parser...")
        lines = parse_exam_document(test_file_docx)
        qa_pairs = extract_qa_pairs(lines)
        if qa_pairs:
            print(f"Found {len(qa_pairs)} Q&A pairs:")
            for idx, (q, a) in enumerate(qa_pairs, 1):
                print(f"\nQ{idx}: {q}\nA{idx}: {a}\n")
        else:
            print("No Q&A pairs were found.")
    else:
        print("No local sample docx file found. Please create one to test.")