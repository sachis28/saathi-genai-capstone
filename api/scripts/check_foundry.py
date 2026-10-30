import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.llm import AzureOpenAILLM  # noqa: E402

REQUIRED = ["AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY", "AZURE_OPENAI_DEPLOYMENT"]
missing = [k for k in REQUIRED if not os.getenv(k)]
if missing:
    print("MISSING in .env:", ", ".join(missing))
    sys.exit(1)

llm = AzureOpenAILLM()
print("Endpoint  :", os.environ["AZURE_OPENAI_ENDPOINT"])
print("Deployment:", llm.deployment)
print("Reply     :", llm.complete("You are a helpful assistant.", "Say hello in one short sentence."))