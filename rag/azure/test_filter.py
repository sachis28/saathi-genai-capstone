"""Quick check that metadata filters work on the Azure AI Search index:
lists only the Health Gold v2 clauses. Run: python rag/azure/test_filter.py"""
import os

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient

# Connect to Azure AI Search
client = SearchClient(
    endpoint=os.environ["AZURE_SEARCH_ENDPOINT"],
    index_name=os.environ["AZURE_SEARCH_INDEX_NAME"],
    credential=AzureKeyCredential(os.environ["AZURE_SEARCH_ADMIN_KEY"])
)

# Search only Health Gold v2 policy clauses
filter_expression = (
    "product eq 'Health' and "
    "tier eq 'Gold' and "
    "version eq 'v2'"
)

results = client.search(
    search_text="*",
    filter=filter_expression,
    include_total_count=True
)

print("Filtered document count:", results.get_count())
print("\nRetrieved documents:\n")

for document in results:
    print("Clause ID:", document["clause_id"])
    print("Product:", document["product"])
    print("Tier:", document["tier"])
    print("Version:", document["version"])
    print("Content:", document["text"])
    print("-" * 60)