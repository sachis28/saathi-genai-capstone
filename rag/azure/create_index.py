import os

from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SimpleField,
    SearchableField,
    SearchFieldDataType,
)

# 1. Read Azure credentials from environment variables
endpoint = os.environ["AZURE_SEARCH_ENDPOINT"]
admin_key = os.environ["AZURE_SEARCH_ADMIN_KEY"]
index_name = os.environ["AZURE_SEARCH_INDEX_NAME"]

# 2. Connect to Azure AI Search
index_client = SearchIndexClient(
    endpoint=endpoint,
    credential=AzureKeyCredential(admin_key),
)

# 3. Define the insurance document structure
fields = [
    SimpleField(
        name="id",
        type=SearchFieldDataType.String,
        key=True,
    ),
    SimpleField(
        name="source_id",
        type=SearchFieldDataType.String,
        filterable=True,
    ),
    SimpleField(
        name="clause_id",
        type=SearchFieldDataType.String,
        filterable=True,
    ),
    SimpleField(
        name="product",
        type=SearchFieldDataType.String,
        filterable=True,
    ),
    SimpleField(
        name="tier",
        type=SearchFieldDataType.String,
        filterable=True,
    ),
    SimpleField(
        name="version",
        type=SearchFieldDataType.String,
        filterable=True,
    ),
    SearchableField(
        name="text",
        type=SearchFieldDataType.String,
    ),
]

# 4. Create the Azure AI Search index
index = SearchIndex(
    name=index_name,
    fields=fields,
)

result = index_client.create_or_update_index(index)

print(f"Successfully created index: {result.name}")

print("\nConfigured fields:")
for field in result.fields:
    print(f"- {field.name}")