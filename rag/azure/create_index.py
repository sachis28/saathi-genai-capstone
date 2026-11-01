import os

from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient

from azure.search.documents.indexes.models import (
    SearchIndex,
    SimpleField,
    SearchableField,
    SearchField,
    SearchFieldDataType,
    VectorSearch,
    HnswAlgorithmConfiguration,
    VectorSearchProfile,
)

# 1. Read Azure credentials
endpoint = os.environ["AZURE_SEARCH_ENDPOINT"]
admin_key = os.environ["AZURE_SEARCH_ADMIN_KEY"]
index_name = os.environ["AZURE_SEARCH_INDEX_NAME"]

# 2. Connect to Azure AI Search
index_client = SearchIndexClient(
    endpoint=endpoint,
    credential=AzureKeyCredential(admin_key),
)

# 3. Define existing insurance document fields
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

    # 4. New vector field
    SearchField(
        name="embedding",
        type=SearchFieldDataType.Collection(
            SearchFieldDataType.Single
        ),
        searchable=True,
        vector_search_dimensions=1536,
        vector_search_profile_name="insurance-vector-profile",
    ),
]

# 5. Configure HNSW vector search
vector_search = VectorSearch(
    algorithms=[
        HnswAlgorithmConfiguration(
            name="insurance-hnsw"
        )
    ],
    profiles=[
        VectorSearchProfile(
            name="insurance-vector-profile",
            algorithm_configuration_name="insurance-hnsw",
        )
    ],
)

# 6. Create or update the existing index
index = SearchIndex(
    name=index_name,
    fields=fields,
    vector_search=vector_search,
)

result = index_client.create_or_update_index(index)

print(f"Successfully updated index: {result.name}")

print("\nConfigured fields:")

for field in result.fields:
    print(f"- {field.name}")

print("\nVector search configuration:")
print("Algorithm: HNSW")
print("Dimensions: 1536")
print("Vector field: embedding")