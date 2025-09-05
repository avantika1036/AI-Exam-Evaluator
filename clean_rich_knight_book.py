import os
import re

INPUT_FILE = "books_texts/Rich & Knight.txt"
OUTPUT_FILE = "books_cleaned/rich-knight-clean.txt"

def clean_rich_knight_text(text):
    """
    Cleans OCR text for Rich & Knight AI book.
    """

    # 1. Remove page headers/footers (common repeated phrases)
    text = re.sub(r"(Artificial Intelligence.*Page\s*\d+)", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"Page\s*\d+", " ", text)  # remove "Page 123"

    # 2. Remove weird OCR junk (symbols, repeats)
    text = re.sub(r"[·•©®™□]+", " ", text)
    text = re.sub(r"[_]{2,}", " ", text)       # underscores
    text = re.sub(r"[^\x00-\x7F]+", " ", text) # non-ASCII chars

    # 3. Fix broken line hyphenation (compu-\nter → computer)
    text = re.sub(r"(?<=\w)-\s+(?=\w)", "", text)

    # 4. Collapse multiple newlines into single space
    text = re.sub(r"\n+", " ", text)

    # 5. Insert missing spaces between lowercase + uppercase
    text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)

    # 6. Collapse multiple spaces
    text = re.sub(r"\s{2,}", " ", text)

    return text.strip()

def main():
    os.makedirs("books_cleaned", exist_ok=True)

    with open(INPUT_FILE, "r", encoding="utf-8", errors="ignore") as f:
        raw_text = f.read()

    cleaned = clean_rich_knight_text(raw_text)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(cleaned)

    print(f"✅ Cleaned text saved to {OUTPUT_FILE}")
    print("\n🔎 Preview of cleaned text:\n")
    print(cleaned[:1000])  # show first 1000 chars

if __name__ == "__main__":
    main()
