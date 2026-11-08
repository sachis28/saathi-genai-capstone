"""Manual demo of vector search on the Azure index: embeds a question, finds the nearest
clauses, and prints them with their scores. Run: python rag/azure/test_vector_search.py"""
import os

from openai import OpenAI

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery


# --------------------------------------------------
# 1. Azure Foundry configuration
# --------------------------------------------------

foundry_endpoint = (
    os.environ["AZURE_OPENAI_ENDPOINT"].strip().rstrip("/")
)

api_key = os.environ["AZURE_OPENAI_API_KEY"].strip()

embedding_deployment = (
    os.environ["AZURE_OPENAI_EMBED_DEPLOYMENT"].strip()
)

if foundry_endpoint.endswith("/openai/v1"):
    foundry_endpoint = foundry_endpoint[:-len("/openai/v1")]


# --------------------------------------------------
# 2. Connect to Azure Foundry
# --------------------------------------------------

embedding_client = OpenAI(
    base_url=f"{foundry_endpoint}/openai/v1/",
    api_key=api_key,
)


# --------------------------------------------------
# 3. Connect to Azure AI Search
# --------------------------------------------------

search_client = SearchClient(

    endpoint=os.environ["AZURE_SEARCH_ENDPOINT"],

    index_name=os.environ["AZURE_SEARCH_INDEX_NAME"],

    credential=AzureKeyCredential(
        os.environ["AZURE_SEARCH_ADMIN_KEY"]
    ),

)


# --------------------------------------------------
# 4. User query
# --------------------------------------------------

query = (
    "Can I claim expenses for a disease "
    "I had before purchasing Health Gold insurance?"
)

print("\nUSER QUESTION:")
print(query)


# --------------------------------------------------
# 5. Generate query embedding
# --------------------------------------------------

response = embedding_client.embeddings.create(

    model=embedding_deployment,

    input=query,

)

query_vector = response.data[0].embedding

print("\nQuery embedding dimensions:", len(query_vector))


# --------------------------------------------------
# 6. Configure vector query
# --------------------------------------------------

vector_query = VectorizedQuery(

    vector=query_vector,

    k_nearest_neighbors=3,

    fields="embedding",

)


# --------------------------------------------------
# 7. VECTOR SEARCH
# --------------------------------------------------

print("\n========== VECTOR SEARCH ==========")

vector_results = search_client.search(

    search_text=None,

    vector_queries=[vector_query],

    select=[
        "id",
        "clause_id",
        "product",
        "tier",
        "text",
    ],

    top=3,

)


for result in vector_results:

    print("\nClause ID:", result["clause_id"])

    print("Product:", result["product"])

    print("Tier:", result["tier"])

    print("Similarity score:", result["@search.score"])

    print("Content:", result["text"])


# --------------------------------------------------
# 8. HYBRID SEARCH
# --------------------------------------------------

print("\n========== HYBRID SEARCH ==========")

hybrid_results = search_client.search(

    search_text=query,

    vector_queries=[vector_query],

    filter="product eq 'Health' and tier eq 'Gold'",

    select=[
        "id",
        "clause_id",
        "product",
        "tier",
        "version",
        "text",
    ],

    top=3,

)


for result in hybrid_results:

    print("\nClause ID:", result["clause_id"])

    print("Product:", result["product"])

    print("Tier:", result["tier"])

    print("Version:", result["version"])

    print("Search score:", result["@search.score"])

    print("Content:", result["text"])


# --------------------------------------------------
# 9. SEMANTIC HYBRID SEARCH
# --------------------------------------------------

print("\n========== SEMANTIC HYBRID SEARCH ==========")

semantic_results = search_client.search(

    search_text=query,

    vector_queries=[vector_query],

    query_type="semantic",

    semantic_configuration_name="insurance-semantic-config",

    filter="product eq 'Health' and tier eq 'Gold'",

    select=[
        "id",
        "clause_id",
        "product",
        "tier",
        "version",
        "text",
    ],

    top=3,

)


for result in semantic_results:

    print("\nClause ID:", result["clause_id"])

    print("Product:", result["product"])

    print("Tier:", result["tier"])

    print("Version:", result["version"])

    print("Search score:", result["@search.score"])

    print("Content:", result["text"])


# --------------------------------------------------
# 10. COMPLETION
# --------------------------------------------------

print("\n========== ALL SEARCH TESTS COMPLETED ==========")