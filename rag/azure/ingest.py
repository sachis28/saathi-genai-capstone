import json
import os
from pathlib import Path

from openai import OpenAI

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient


# --------------------------------------------------
# 1. Read Azure AI Search configuration
# --------------------------------------------------

search_endpoint = os.environ["AZURE_SEARCH_ENDPOINT"]
admin_key = os.environ["AZURE_SEARCH_ADMIN_KEY"]
index_name = os.environ["AZURE_SEARCH_INDEX_NAME"]


# --------------------------------------------------
# 2. Read Azure Foundry configuration
# --------------------------------------------------

foundry_endpoint = (
    os.environ["AZURE_OPENAI_ENDPOINT"].strip().rstrip("/")
)

api_key = os.environ["AZURE_OPENAI_API_KEY"].strip()

embedding_deployment = (
    os.environ["AZURE_OPENAI_EMBED_DEPLOYMENT"].strip()
)

# Normalize endpoint
if foundry_endpoint.endswith("/openai/v1"):
    foundry_endpoint = foundry_endpoint[:-len("/openai/v1")]


# --------------------------------------------------
# 3. Connect to Azure OpenAI
# --------------------------------------------------

embedding_client = OpenAI(
    base_url=f"{foundry_endpoint}/openai/v1/",
    api_key=api_key,
)


# --------------------------------------------------
# 4. Connect to Azure AI Search
# --------------------------------------------------

search_client = SearchClient(
    endpoint=search_endpoint,
    index_name=index_name,
    credential=AzureKeyCredential(admin_key),
)


# --------------------------------------------------
# 5. Locate the insurance corpus
# --------------------------------------------------

project_root = Path(__file__).resolve().parents[2]

corpus_path = (
    project_root / "rag" / "corpus" / "sample_docs.jsonl"
)


# --------------------------------------------------
# 6. Read insurance documents
# --------------------------------------------------

records = []

with corpus_path.open("r", encoding="utf-8") as file:

    for line_number, line in enumerate(file, start=1):

        if not line.strip():
            continue

        record = json.loads(line)

        records.append(record)


print("Total insurance clauses found:", len(records))


# --------------------------------------------------
# 7. Generate embeddings
# --------------------------------------------------

texts = [record["text"] for record in records]

print("\nGenerating Azure embeddings...")

response = embedding_client.embeddings.create(
    model=embedding_deployment,
    input=texts,
)

embeddings = [item.embedding for item in response.data]

print("Embeddings generated:", len(embeddings))
print("Dimensions per embedding:", len(embeddings[0]))


# --------------------------------------------------
# 8. Prepare documents with embeddings
# --------------------------------------------------

documents = []

for record, embedding in zip(records, embeddings):

    document_id = (
        f"{record['source_id']}-"
        f"{record['clause_id']}-"
        f"{record['version']}"
    )

    document = {
        "id": document_id,
        "source_id": record["source_id"],
        "clause_id": record["clause_id"],
        "product": record["product"],
        "tier": record["tier"],
        "version": record["version"],
        "text": record["text"],
        "embedding": embedding,
    }

    documents.append(document)


# --------------------------------------------------
# 9. Upload documents to Azure AI Search
# --------------------------------------------------

if documents:

    print("\nUploading documents to Azure AI Search...")

    results = search_client.upload_documents(
        documents=documents
    )

    successful = sum(
        1 for result in results if result.succeeded
    )

    failed = len(results) - successful

    print("\n========== INGESTION SUMMARY ==========")
    print("Total documents:", len(documents))
    print("Successfully uploaded:", successful)
    print("Failed uploads:", failed)

    for result in results:

        if not result.succeeded:

            print(
                f"Failed document: {result.key}"
                f" | Error: {result.error_message}"
            )

    print("======================================")

else:

    print("No documents found in the corpus.")