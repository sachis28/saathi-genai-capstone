import os
from dotenv import load_dotenv
from openai import AzureOpenAI

load_dotenv()

client = AzureOpenAI(
    azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    api_key=os.environ["AZURE_OPENAI_API_KEY"],
    api_version=os.environ["AZURE_OPENAI_API_VERSION"],
)

chat = client.chat.completions.create(
    model=os.environ["AZURE_OPENAI_DEPLOYMENT"],
    messages=[{"role": "user", "content": "Say hello in one short sentence."}],
)
print("CHAT:", chat.choices[0].message.content)

emb = client.embeddings.create(
    model=os.environ["AZURE_OPENAI_EMBED_DEPLOYMENT"],
    input="health insurance renewal",
)
print("EMBEDDING LENGTH:", len(emb.data[0].embedding))