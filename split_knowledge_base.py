import os

INPUT_FILE = "knowledge_base.txt"
OUTPUT_FOLDER = "knowledge_chunks"
CHUNK_SIZE = 2000  # characters per chunk (adjust as needed)
OVERLAP = 200      # overlapping characters for context

def split_text_into_chunks(text, size=2000, overlap=200):
    chunks = []
    start = 0
    while start < len(text):
        end = start + size
        chunk = text[start:end]
        chunks.append(chunk)
        start += size - overlap
    return chunks

def main():
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

    with open(INPUT_FILE, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()

    chunks = split_text_into_chunks(text, size=CHUNK_SIZE, overlap=OVERLAP)

    for i, chunk in enumerate(chunks, start=1):
        out_path = os.path.join(OUTPUT_FOLDER, f"chunk_{i}.txt")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(chunk)

    print(f"✅ Split into {len(chunks)} chunks, saved in '{OUTPUT_FOLDER}' folder.")
    print(f"🔎 Example preview of first chunk:\n\n{chunks[0][:500]}...")

if __name__ == "__main__":
    main()
