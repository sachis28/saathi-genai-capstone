import json
import os
from pathlib import Path

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient


# 1. Read Azure configuration
endpoint = os.environ["AZURE_SEARCH_ENDPOINT"]
admin_key = os.environ["AZURE_SEARCH_ADMIN_KEY"]
index_name = os.environ["AZURE_SEARCH_INDEX_NAME"]


# 2. Locate the insurance corpus
project_root = Path(__file__).resolve().parents[2]

corpus_path = (
    project_root / "rag" / "corpus" / "sample_docs.jsonl"
)


# 3. Connect to Azure AI Search
search_client = SearchClient(
    endpoint=endpoint,
    index_name=index_name,
    credential=AzureKeyCredential(admin_key),
)


# 4. Read JSONL documents
documents = []

with corpus_path.open("r", encoding="utf-8") as file:

    for line_number, line in enumerate(file, start=1):

        if not line.strip():
            continue

        record = json.loads(line)

        # Generate a unique document ID
        document_id = (
            f"{record['source_id']}-"
            f"{record['clause_id']}-"
            f"{record['version']}"
        )

        # Prepare document for Azure
        document = {
            "id": document_id,
            "source_id": record["source_id"],
            "clause_id": record["clause_id"],
            "product": record["product"],
            "tier": record["tier"],
            "version": record["version"],
            "text": record["text"],
        }

        documents.append(document)


# 5. Upload documents to Azure AI Search
if documents:

    results = search_client.upload_documents(
        documents=documents
    )

    successful = sum(
        1 for result in results if result.succeeded
    )

    failed = len(results) - successful

    print(f"Total documents: {len(documents)}")
    print(f"Successfully uploaded: {successful}")
    print(f"Failed uploads: {failed}")

    for result in results:
        if not result.succeeded:
            print(
                f"Failed document: {result.key}"
                f" | Error: {result.error_message}"
            )

else:
    print("No documents found in the corpus.")