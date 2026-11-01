import os
from openai import OpenAI

# 1. Read Azure Foundry credentials
endpoint = os.environ["AZURE_OPENAI_ENDPOINT"].strip().rstrip("/")
api_key = os.environ["AZURE_OPENAI_API_KEY"].strip()
deployment = os.environ["AZURE_OPENAI_EMBED_DEPLOYMENT"].strip()

# 2. Normalize endpoint
if endpoint.endswith("/openai/v1"):
    endpoint = endpoint[:-len("/openai/v1")]

# 3. Connect to Azure OpenAI
client = OpenAI(
    base_url=f"{endpoint}/openai/v1/",
    api_key=api_key,
)

# 4. Sample insurance text
text = (
    "Pre-existing diseases are covered after "
    "24 months of continuous coverage under Health Gold."
)

print("Connecting to Azure embedding deployment...")

# 5. Generate embedding
response = client.embeddings.create(
    model=deployment,
    input=text,
)

# 6. Extract vector
embedding = response.data[0].embedding

# 7. Display results
print("\nAzure embedding test successful!")
print("Deployment:", deployment)
print("Input text:", text)
print("Embedding dimensions:", len(embedding))
print("First 5 vector values:", embedding[:5])