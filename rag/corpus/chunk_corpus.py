import json
import re
from pathlib import Path

# --------------------------------------------------
# Configuration
# --------------------------------------------------

BASE_DIR = Path(__file__).parent

INPUT_FILE = BASE_DIR / "insurance_docs.jsonl"
OUTPUT_FILE = BASE_DIR / "insurance_chunks.jsonl"

CHUNK_SIZE = 1200
CHUNK_OVERLAP = 150


# --------------------------------------------------
# Read JSONL documents
# --------------------------------------------------

def load_documents(file_path):
    documents = []

    with open(file_path, "r", encoding="utf-8") as file:
        for line in file:
            if line.strip():
                documents.append(json.loads(line))

    return documents


# --------------------------------------------------
# Split long text into chunks
# --------------------------------------------------

def split_text(text):
    text = re.sub(r"\s+", " ", text).strip()

    if len(text) <= CHUNK_SIZE:
        return [text]

    chunks = []
    start = 0

    while start < len(text):
        end = min(start + CHUNK_SIZE, len(text))

        # Prefer ending at a sentence boundary
        if end < len(text):
            sentence_end = text.rfind(". ", start, end)

            if sentence_end > start + CHUNK_SIZE // 2:
                end = sentence_end + 1

        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end >= len(text):
            break

        start = max(end - CHUNK_OVERLAP, start + 1)

    return chunks


# --------------------------------------------------
# Create chunk records
# --------------------------------------------------

def create_chunks(documents):
    all_chunks = []

    for document in documents:

        text_chunks = split_text(document["text"])

        for number, chunk_text in enumerate(text_chunks, start=1):

            chunk_record = {
                "id": (
                    f"{document['source_id']}-"
                    f"{document['clause_id']}-"
                    f"{document['version']}-"
                    f"chunk-{number:03d}"
                ),
                "source_id": document["source_id"],
                "clause_id": document["clause_id"],
                "product": document["product"],
                "tier": document["tier"],
                "version": document["version"],
                "chunk_id": number,
                "text": chunk_text
            }

            all_chunks.append(chunk_record)

    return all_chunks


# --------------------------------------------------
# Save chunks
# --------------------------------------------------

def save_chunks(chunks, file_path):
    with open(file_path, "w", encoding="utf-8") as file:
        for chunk in chunks:
            file.write(json.dumps(chunk, ensure_ascii=False) + "\n")


# --------------------------------------------------
# Main execution
# --------------------------------------------------

def main():

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Input corpus not found: {INPUT_FILE}"
        )

    documents = load_documents(INPUT_FILE)

    chunks = create_chunks(documents)

    save_chunks(chunks, OUTPUT_FILE)

    print("Corpus chunking completed successfully!")
    print("----------------------------------------")
    print(f"Original documents: {len(documents)}")
    print(f"Generated chunks: {len(chunks)}")
    print(f"Output file: {OUTPUT_FILE}")

    print("\nSample chunk:")
    print(json.dumps(chunks[0], indent=4, ensure_ascii=False))


if __name__ == "__main__":
    main()