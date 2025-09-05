import os
import pdfplumber
from pdf2image import convert_from_path
import pytesseract

# If pytesseract doesn't auto-find tesseract, uncomment and set the path:
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

BOOKS_DIR = "books"
OUT_DIR = "books_texts"

def extract_text_from_pdf(path):
    """
    Extract text from a PDF.
    1. Try pdfplumber (selectable text).
    2. If useless (too short or watermarked), fallback to OCR.
    3. Show progress while OCR runs.
    """
    texts = []

    # ---------- Step 1: Try text extraction ----------
    try:
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    texts.append(page_text)
    except Exception as e:
        print(f"⚠️ pdfplumber error for {os.path.basename(path)}: {e}")

    joined = "\n".join(texts).strip()

    # ---------- Step 2: Check if text is valid ----------
    if joined and len(joined) > 1000 and "kazirhut" not in joined.lower():
        return joined  # ✅ good text, no need for OCR

    # ---------- Step 3: Fallback to OCR ----------
    print(f"🔁 Using OCR for {os.path.basename(path)} — this will take time...")

    ocr_texts = []
    try:
        images = convert_from_path(path, dpi=200)
        total_pages = len(images)

        for i, img in enumerate(images, start=1):
            try:
                txt = pytesseract.image_to_string(img)
                if txt and txt.strip():
                    ocr_texts.append(txt)
                print(f"   ✅ Processed page {i}/{total_pages}")
            except Exception as e:
                print(f"⚠️ pytesseract error on page {i}: {e}")

    except Exception as e:
        print(f"⚠️ convert_from_path error for {os.path.basename(path)}: {e}")

    return "\n".join(ocr_texts).strip()

def main():
    if not os.path.exists(BOOKS_DIR):
        print(f"❌ Folder '{BOOKS_DIR}' not found. Create the folder and add your book PDFs there.")
        return

    os.makedirs(OUT_DIR, exist_ok=True)

    pdf_files = [f for f in os.listdir(BOOKS_DIR) if f.lower().endswith(".pdf")]
    if not pdf_files:
        print(f"❌ No PDF files found in '{BOOKS_DIR}'. Put your book PDFs there.")
        return

    for fname in pdf_files:
        path = os.path.join(BOOKS_DIR, fname)
        print(f"\n📖 Processing '{fname}' ...")
        text = extract_text_from_pdf(path)
        out_path = os.path.join(OUT_DIR, os.path.splitext(fname)[0] + ".txt")

        if not text:
            print(f"⚠️ No text extracted from '{fname}'. Check that the PDF is not corrupt.")
            continue

        # Save to file
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(text)

        # Print a short preview so you can verify
        preview = text[:800].replace("\n", " ").strip()
        print(f"✅ Extracted {len(text)} characters. Saved to '{out_path}'.")
        print("Preview (first ~800 chars):")
        print("--------------------------------------------------")
        print(preview)
        print("--------------------------------------------------")

if __name__ == "__main__":
    main()
