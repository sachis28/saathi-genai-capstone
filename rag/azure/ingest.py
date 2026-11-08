"""Uploads the chunked policy clauses into the Azure AI Search index.

Steps: read rag/corpus/insurance_chunks.jsonl -> embed each clause with our Azure OpenAI
embedding deployment (in batches of 16) -> upload clause + vector to the index -> print count.
Run after create_index.py:  python rag/azure/ingest.py"""
import os
import json
from pathlib import Path

from openai import OpenAI

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient


# ==================================================
# CONFIGURATION
# ==================================================

BASE_DIR = Path(__file__).resolve().parent.parent

CORPUS_FILE = BASE_DIR / "corpus" / "insurance_chunks.jsonl"

SEARCH_ENDPOINT = os.environ["AZURE_SEARCH_ENDPOINT"]
SEARCH_KEY = os.environ["AZURE_SEARCH_ADMIN_KEY"]
INDEX_NAME = os.environ["AZURE_SEARCH_INDEX_NAME"]

OPENAI_ENDPOINT = os.environ["AZURE_OPENAI_ENDPOINT"].rstrip("/")
OPENAI_KEY = os.environ["AZURE_OPENAI_API_KEY"]
EMBEDDING_DEPLOYMENT = os.environ["AZURE_OPENAI_EMBED_DEPLOYMENT"]

# Embed and upload 16 clauses per request to stay well within API limits.
BATCH_SIZE = 16
# Sanity checks: text-embedding-3-small returns 1536 numbers, and the corpus has 48 clauses.
EXPECTED_EMBEDDING_DIMENSIONS = 1536
EXPECTED_CHUNKS = 48


# ==================================================
# AZURE OPENAI CLIENT
# ==================================================

# Remove /openai/v1 if already present.
OPENAI_ENDPOINT = OPENAI_ENDPOINT.replace("/openai/v1", "")

openai_client = OpenAI(
    base_url=f"{OPENAI_ENDPOINT}/openai/v1/",
    api_key=OPENAI_KEY
)


# ==================================================
# AZURE AI SEARCH CLIENT
# ==================================================

search_client = SearchClient(
    endpoint=SEARCH_ENDPOINT,
    index_name=INDEX_NAME,
    credential=AzureKeyCredential(SEARCH_KEY)
)


# ==================================================
# LOAD CHUNKED CORPUS
# ==================================================

def load_chunks():

    if not CORPUS_FILE.exists():
        raise FileNotFoundError(
            f"Corpus file not found: {CORPUS_FILE}"
        )

    documents = []

    with open(CORPUS_FILE, "r", encoding="utf-8") as file:

        for line_number, line in enumerate(file, start=1):

            if not line.strip():
                continue

            try:
                document = json.loads(line)

            except json.JSONDecodeError as error:
                raise ValueError(
                    f"Invalid JSON on line {line_number}: {error}"
                ) from error

            required_fields = [
                "id",
                "source_id",
                "clause_id",
                "product",
                "tier",
                "version",
                "text"
            ]

            for field in required_fields:

                if field not in document:
                    raise ValueError(
                        f"Missing field '{field}' "
                        f"on line {line_number}"
                    )

            documents.append(document)

    if len(documents) != EXPECTED_CHUNKS:
        raise ValueError(
            f"Expected {EXPECTED_CHUNKS} chunks, "
            f"found {len(documents)}"
        )

    # Ensure every document has a unique ID.
    document_ids = [
        document["id"]
        for document in documents
    ]

    if len(document_ids) != len(set(document_ids)):
        raise ValueError(
            "Duplicate document IDs found in corpus."
        )

    print(f"Successfully loaded {len(documents)} chunks.")

    return documents


# ==================================================
# GENERATE EMBEDDINGS
# ==================================================

# One API call embeds a whole batch of texts and returns one vector per text.
def generate_embeddings(texts):

    if not texts:
        return []

    response = openai_client.embeddings.create(
        model=EMBEDDING_DEPLOYMENT,
        input=texts
    )

    # Preserve the original input order.
    ordered_embeddings = sorted(
        response.data,
        key=lambda item: item.index
    )

    embeddings = [
        item.embedding
        for item in ordered_embeddings
    ]

    if len(embeddings) != len(texts):
        raise RuntimeError(
            "Embedding count does not match input text count."
        )

    return embeddings


# ==================================================
# PREPARE SEARCH DOCUMENTS
# ==================================================

def prepare_search_documents(chunks):

    search_documents = []

    print("\nGenerating embeddings...")

    for start in range(0, len(chunks), BATCH_SIZE):

        batch = chunks[start:start + BATCH_SIZE]

        texts = [
            document["text"]
            for document in batch
        ]

        embeddings = generate_embeddings(texts)

        for document, embedding in zip(batch, embeddings):

            if len(embedding) != EXPECTED_EMBEDDING_DIMENSIONS:
                raise ValueError(
                    f"Document {document['id']} has "
                    f"{len(embedding)} dimensions. "
                    f"Expected {EXPECTED_EMBEDDING_DIMENSIONS}."
                )

            search_documents.append({

                "id": document["id"],

                "source_id": document["source_id"],

                "clause_id": document["clause_id"],

                "product": document["product"],

                "tier": document["tier"],

                "version": document["version"],

                "text": document["text"],

                "embedding": embedding

            })

        print(
            f"Embedded "
            f"{min(start + BATCH_SIZE, len(chunks))}"
            f"/{len(chunks)} documents"
        )

    return search_documents


# ==================================================
# UPLOAD DOCUMENTS TO AZURE AI SEARCH
# ==================================================

def upload_documents(documents):

    print("\nUploading documents to Azure AI Search...")

    total_uploaded = 0

    for start in range(0, len(documents), BATCH_SIZE):

        batch = documents[start:start + BATCH_SIZE]

        # Insert new documents or update documents
        # with matching IDs. Does not delete other documents.
        results = search_client.merge_or_upload_documents(
            documents=batch
        )

        failed = [
            item for item in results
            if not item.succeeded
        ]

        if failed:

            for item in failed:
                print(
                    f"Upload failed: {item.key} - "
                    f"{item.error_message}"
                )

            raise RuntimeError(
                f"{len(failed)} documents failed to upload."
            )

        total_uploaded += len(results)

        print(
            f"Uploaded {total_uploaded}/{len(documents)} documents"
        )

    print(
        f"\nSuccessfully uploaded or updated "
        f"{total_uploaded} documents."
    )


# ==================================================
# VERIFY INDEX DOCUMENT COUNT
# ==================================================

def verify_index():

    results = search_client.search(
        search_text="*",
        include_total_count=True,
        top=1
    )

    print("\nVerifying Azure AI Search index...")

    print(
        f"Total documents currently in index: "
        f"{results.get_count()}"
    )


# ==================================================
# MAIN
# ==================================================

def main():

    print("\nSAATHI INSURANCE CORPUS INGESTION")
    print("=================================")

    # Step 1: Load corpus.
    chunks = load_chunks()

    # Step 2: Generate embeddings.
    documents = prepare_search_documents(chunks)

    # Step 3: Upload documents.
    upload_documents(documents)

    # Step 4: Verify index.
    verify_index()

    print("\nCORPUS INGESTION COMPLETED SUCCESSFULLY!")


# ==================================================
# ENTRY POINT
# ==================================================

if __name__ == "__main__":
    main()
