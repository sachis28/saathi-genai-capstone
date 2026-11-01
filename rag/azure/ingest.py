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

BATCH_SIZE = 16


# ==================================================
# AZURE OPENAI CLIENT
# ==================================================

# Remove /openai/v1 if it is already present.
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

        for line in file:

            if line.strip():

                documents.append(json.loads(line))

    return documents


# ==================================================
# GENERATE EMBEDDINGS
# ==================================================

def generate_embeddings(texts):

    response = openai_client.embeddings.create(
        model=EMBEDDING_DEPLOYMENT,
        input=texts
    )

    embeddings = [
        item.embedding
        for item in response.data
    ]

    return embeddings


# ==================================================
# CLEAR OLD INDEX DOCUMENTS
# ==================================================

def clear_existing_documents():

    print("\nRemoving previously indexed documents...")

    results = search_client.search(
        search_text="*",
        select=["id"],
        top=1000
    )

    old_documents = [
        {"id": result["id"]}
        for result in results
    ]

    if old_documents:

        delete_result = search_client.delete_documents(
            documents=old_documents
        )

        failed = [
            item for item in delete_result
            if not item.succeeded
        ]

        if failed:
            raise RuntimeError(
                f"Failed to delete {len(failed)} old documents."
            )

    print(f"Old documents removed: {len(old_documents)}")


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

            if len(embedding) != 1536:
                raise ValueError(
                    f"Unexpected embedding dimensions: {len(embedding)}"
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
            f"Embedded {min(start + BATCH_SIZE, len(chunks))}"
            f"/{len(chunks)} documents"
        )

    return search_documents


# ==================================================
# UPLOAD DOCUMENTS TO AZURE AI SEARCH
# ==================================================

def upload_documents(documents):

    print("\nUploading documents to Azure AI Search...")

    for start in range(0, len(documents), BATCH_SIZE):

        batch = documents[start:start + BATCH_SIZE]

        results = search_client.upload_documents(
            documents=batch
        )

        failed = [
            item for item in results
            if not item.succeeded
        ]

        if failed:

            for item in failed:
                print(
                    f"Upload failed: {item.key} - {item.error_message}"
                )

            raise RuntimeError(
                f"{len(failed)} documents failed to upload."
            )

    print(f"Successfully uploaded: {len(documents)}")


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

    print(f"Indexed document count: {results.get_count()}")


# ==================================================
# MAIN
# ==================================================

def main():

    print("SAATHI INSURANCE CORPUS INGESTION")
    print("=================================")

    chunks = load_chunks()

    print(f"Total chunks loaded: {len(chunks)}")

    if len(chunks) != 48:
        raise ValueError(
            f"Expected 48 chunks, found {len(chunks)}"
        )

    clear_existing_documents()

    documents = prepare_search_documents(chunks)

    upload_documents(documents)

    verify_index()

    print("\nCORPUS INGESTION COMPLETED SUCCESSFULLY!")


if __name__ == "__main__":

    main()