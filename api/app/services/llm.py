import os
import re
from abc import ABC, abstractmethod
from functools import lru_cache
from pathlib import Path

import httpx
from dotenv import load_dotenv

# Reads the .env file in the repo root. Real environment variables win,
# so "LLM_PROVIDER=mock pytest" still overrides the .env value.
load_dotenv(Path(__file__).resolve().parents[3] / ".env")

CONTEXT_LINE = re.compile(r"^(\[[^\]]+\])\s*\([^)]*\)\s*(.+)$", re.MULTILINE)


class LLMAdapter(ABC):
    """Plugin interface: Mock, Ollama or Azure (Foundry) by changing LLM_PROVIDER."""

    @abstractmethod
    def complete(self, system: str, user: str) -> str:
        ...


class MockLLM(LLMAdapter):
    """No API key needed. Answers from the top 2 context clauses with their tags."""

    def complete(self, system: str, user: str) -> str:
        matches = CONTEXT_LINE.findall(user)
        if not matches:
            return "I could not find this in the policy documents."
        parts = [f"{text} {tag}" for tag, text in matches[:2]]
        return " ".join(parts)


class OllamaLLM(LLMAdapter):
    def __init__(self):
        self.url = os.getenv("OLLAMA_URL", "http://localhost:11434") + "/api/chat"
        self.model = os.getenv("OLLAMA_MODEL", "phi3")

    def complete(self, system: str, user: str) -> str:
        r = httpx.post(self.url, timeout=120, json={
            "model": self.model,
            "stream": False,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        })
        r.raise_for_status()
        return r.json()["message"]["content"]


class AzureOpenAILLM(LLMAdapter):
    """Model deployed in Microsoft Foundry, called through the OpenAI v1 endpoint."""

    def __init__(self):
        from openai import OpenAI

        endpoint = os.environ["AZURE_OPENAI_ENDPOINT"].strip().rstrip("/")
        # Accept the endpoint with or without the /openai/v1 suffix
        if endpoint.endswith("/openai/v1"):
            endpoint = endpoint[: -len("/openai/v1")]

        self.client = OpenAI(
            base_url=f"{endpoint}/openai/v1/",
            api_key=os.environ["AZURE_OPENAI_API_KEY"].strip(),
        )
        self.deployment = os.environ["AZURE_OPENAI_DEPLOYMENT"].strip()

    def complete(self, system: str, user: str) -> str:
        r = self.client.chat.completions.create(
            model=self.deployment,
            temperature=0,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return r.choices[0].message.content


@lru_cache
def get_llm() -> LLMAdapter:
    provider = os.getenv("LLM_PROVIDER", "mock").lower()
    if provider == "mock":
        return MockLLM()
    if provider == "ollama":
        return OllamaLLM()
    if provider == "azure":
        return AzureOpenAILLM()
    raise ValueError(f"Unknown LLM_PROVIDER={provider}")
