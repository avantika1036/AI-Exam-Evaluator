import os
import re

INPUT_FILE = "books_texts/introduction-to-artificial-intelligence-and-expert-systems-0134771001-9780134771007_compress.txt"
OUTPUT_FILE = "books_cleaned/patterson-clean.txt"

def clean_patterson_text(text):
    """
    Cleans Patterson AI book text.
    """

    # 1. Remove publisher/legal junk
    text = re.sub(r"(Prentice[- ]Hall.*|Copyright.*|ISBN.*|All rights reserved.*)", " ", text, flags=re.IGNORECASE)

    # 2. Remove OCR garbage symbols
    text = re.sub(r"[·•©®™]+", " ", text)   # bullet-like junk
    text = re.sub(r"[_]{2,}", " ", text)    # long underscores
    text = re.sub(r"[^\x00-\x7F]+", " ", text)  # non-ASCII chars

    # 3. Fix broken line breaks & hyphenation
    text = re.sub(r"(?<=\w)-\s+(?=\w)", "", text)  # e.g., "compu-\nter" → "computer"
    text = re.sub(r"\n+", " ", text)               # collapse newlines into spaces

    # 4. Insert missing space if lowercase followed by uppercase
    text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)

    # 5. Collapse multiple spaces
    text = re.sub(r"\s{2,}", " ", text)

    return text.strip()

def main():
    os.makedirs("books_cleaned", exist_ok=True)

    with open(INPUT_FILE, "r", encoding="utf-8", errors="ignore") as f:
        raw_text = f.read()

    cleaned = clean_patterson_text(raw_text)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(cleaned)

    print(f"✅ Cleaned text saved to {OUTPUT_FILE}")
    print("\n🔎 Preview of cleaned text:\n")
    print(cleaned[:1000])  # show first 1000 chars

if __name__ == "__main__":
    main()
