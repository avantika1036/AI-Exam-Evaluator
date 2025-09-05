import os

CLEANED_FOLDER = "books_cleaned"
OUTPUT_FILE = "knowledge_base.txt"

def merge_books():
    with open(OUTPUT_FILE, "w", encoding="utf-8") as outfile:
        for fname in os.listdir(CLEANED_FOLDER):
            if fname.endswith(".txt"):
                path = os.path.join(CLEANED_FOLDER, fname)
                print(f"📖 Adding {fname} to knowledge base...")
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    text = f.read()
                outfile.write(f"\n\n=== START OF {fname} ===\n\n")
                outfile.write(text)
                outfile.write(f"\n\n=== END OF {fname} ===\n\n")

    print(f"\n✅ Knowledge base saved as {OUTPUT_FILE}")

if __name__ == "__main__":
    merge_books()
