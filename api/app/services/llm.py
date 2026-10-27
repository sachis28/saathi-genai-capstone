import os
import re
from abc import ABC, abstractmethod
from functools import lru_cache

import httpx

CONTEXT_LINE = re.compile(r"^(\[[^\]]+\])\s*\([^)]*\)\s*(.+)$", re.MULTILINE)


class LLMAdapter(ABC):
    """Plugin interface: Mock now, Ollama or Azure by changing LLM_PROVIDER."""

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
    def __init__(self):
        from openai import AzureOpenAI
        self.client = AzureOpenAI(
            azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
            api_key=os.environ["AZURE_OPENAI_API_KEY"],
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21"),
        )
        self.deployment = os.environ["AZURE_OPENAI_DEPLOYMENT"]

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