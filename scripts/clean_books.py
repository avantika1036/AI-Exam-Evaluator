import os
import re

# Input and output folders
INPUT_FILE = "books_texts/a-first-course-in-artificial-intelligence-deepak-khemani.txt"
OUTPUT_FILE = "books_cleaned/a-first-course-in-artificial-intelligence-deepak-khemani-clean.txt"

def clean_text(text):
    """
    Cleans OCR noise and formatting issues from the book text.
    """

    # 1. Remove watermark repetitions like "kazirhut.com"
    text = re.sub(r"(kazirhut\.com\s*)+", " ", text, flags=re.IGNORECASE)

    # 2. Remove extra spaces (multiple spaces → single space)
    text = re.sub(r"[ ]{2,}", " ", text)

    # 3. Fix broken lines: join words split by line breaks
    # e.g., "Artificial\nIntelligence" → "Artificial Intelligence"
    text = re.sub(r"\n+", "\n", text)  # collapse multiple newlines
    text = re.sub(r"(?<=\w)-\n(?=\w)", "", text)  # fix hyphenated line breaks
    text = text.replace("\n", " ")  # turn line breaks into spaces

    # 4. Remove weird characters from OCR
    text = re.sub(r"[^a-zA-Z0-9.,;:!?()\-\'\"\s]", " ", text)

    # 5. Collapse multiple spaces again
    text = re.sub(r"\s{2,}", " ", text)

    return text.strip()

def main():
    os.makedirs("books_cleaned", exist_ok=True)

    with open(INPUT_FILE, "r", encoding="utf-8", errors="ignore") as f:
        raw_text = f.read()

    cleaned = clean_text(raw_text)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(cleaned)

    print(f"✅ Cleaned text saved to {OUTPUT_FILE}")
    print("\n🔎 Preview of cleaned text:\n")
    print(cleaned[:1000])  # show first 1000 chars

if __name__ == "__main__":
    main()
