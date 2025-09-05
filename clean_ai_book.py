import os
import re

INPUT_FILE = "books_texts/AI.txt"
OUTPUT_FILE = "books_cleaned/AI-clean.txt"

def clean_ai_text(text):
    """
    Cleans Russell & Norvig AI book text.
    """

    # 1. Remove copyright/legal/ISBN lines (too noisy)
    text = re.sub(r"(Copyright.*|ISBN.*|Prentice.*|Englewood.*)", " ", text, flags=re.IGNORECASE)

    # 2. Fix squashed words:
    # rule: insert a space if a lowercase letter is directly followed by an uppercase letter
    text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)

    # 3. Fix multiple uppercase sequences without spacing
    # Example: "AIIN" -> "AI IN"
    text = re.sub(r"([A-Z]{2,})([A-Z][a-z])", r"\1 \2", text)

    # 4. Collapse multiple newlines → single newline
    text = re.sub(r"\n{2,}", "\n", text)

    # 5. Replace weird characters from OCR/PDF
    text = re.sub(r"[^a-zA-Z0-9.,;:!?()\-\'\"\s\n]", " ", text)

    # 6. Collapse multiple spaces → single space
    text = re.sub(r"\s{2,}", " ", text)

    return text.strip()

def main():
    os.makedirs("books_cleaned", exist_ok=True)

    with open(INPUT_FILE, "r", encoding="utf-8", errors="ignore") as f:
        raw_text = f.read()

    cleaned = clean_ai_text(raw_text)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(cleaned)

    print(f"✅ Cleaned text saved to {OUTPUT_FILE}")
    print("\n🔎 Preview of cleaned text:\n")
    print(cleaned[:1000])  # show first 1000 chars

if __name__ == "__main__":
    main()
