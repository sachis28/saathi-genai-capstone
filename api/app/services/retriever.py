import json
import logging
import os
import re
from abc import ABC, abstractmethod
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

import faiss
import numpy as np
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer

from app.models.schemas import SearchHit

logger = logging.getLogger("saathi")

CORPUS_DIR = Path(__file__).resolve().parents[3] / "rag" / "corpus"
RRF_K = 60
FIELDS = ("source_id", "clause_id", "version", "product", "tier", "text")

# Only these files are searched. Poisoned docs and the gold set are never loaded.
# Override with CORPUS_FILES="a.jsonl,b.jsonl". The first existing file wins.
DEFAULT_FILES = ["insurance_chunks.jsonl", "sample_docs.jsonl"]


def tokenize(text: str) -> List[str]:
    return re.findall(r"\w+", text.lower())


def corpus_files() -> List[str]:
    env = os.getenv("CORPUS_FILES")
    return [f.strip() for f in env.split(",") if f.strip()] if env else DEFAULT_FILES


class IRetriever(ABC):
    """Plugin interface: LocalRetriever now, AzureSearchRetriever later."""

    @abstractmethod
    def search(self, query: str, k: int = 5,
               product: Optional[str] = None, tier: Optional[str] = None) -> List[SearchHit]:
        ...


class LocalRetriever(IRetriever):
    """Hybrid search: BM25 (keywords) + MiniLM/FAISS (meaning), fused with RRF."""

    def __init__(self, corpus_dir: Path = CORPUS_DIR):
        self.chunks = self._load(corpus_dir)
        if not self.chunks:
            raise RuntimeError(f"No usable clauses found in {corpus_dir} (looked for {corpus_files()})")

        texts = [c["text"] for c in self.chunks]
        self.bm25 = BM25Okapi([tokenize(t) for t in texts])

        self.model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        emb = self.model.encode(texts, normalize_embeddings=True).astype("float32")
        self.index = faiss.IndexFlatIP(emb.shape[1])
        self.index.add(emb)

    @staticmethod
    def _load(corpus_dir: Path) -> List[dict]:
        for name in corpus_files():
            path = corpus_dir / name
            if not path.exists():
                continue
            chunks, skipped = [], 0
            for line in path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                row = json.loads(line)
                if all(row.get(f) not in (None, "") for f in FIELDS):
                    chunks.append({f: str(row[f]) for f in FIELDS})
                else:
                    skipped += 1
            logger.info("Loaded %d clauses from %s (skipped %d rows missing fields)", len(chunks), name, skipped)
            if chunks:
                return chunks
        return []

    @staticmethod
    def _allowed(c: dict, product: Optional[str], tier: Optional[str]) -> bool:
        if product and c["product"] not in (product, "All"):
            return False
        if tier and c["tier"] not in (tier, "All"):
            return False
        return True

    def search(self, query: str, k: int = 5,
               product: Optional[str] = None, tier: Optional[str] = None) -> List[SearchHit]:
        allowed = {i for i, c in enumerate(self.chunks) if self._allowed(c, product, tier)}
        if not allowed:
            return []

        bm25_scores = self.bm25.get_scores(tokenize(query))
        bm25_rank = [int(i) for i in np.argsort(-bm25_scores) if int(i) in allowed]

        q = self.model.encode([query], normalize_embeddings=True).astype("float32")
        _, ids = self.index.search(q, len(self.chunks))
        vec_rank = [int(i) for i in ids[0] if int(i) in allowed]

        fused = {}
        for ranking in (bm25_rank, vec_rank):
            for r, i in enumerate(ranking):
                fused[i] = fused.get(i, 0.0) + 1.0 / (RRF_K + r + 1)

        top = sorted(fused.items(), key=lambda x: x[1], reverse=True)[:k]
        return [SearchHit(**self.chunks[i], score=round(s, 4)) for i, s in top]


def _odata_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def azure_filter(product: Optional[str], tier: Optional[str]) -> Optional[str]:
    """Same rule as LocalRetriever._allowed: a clause for 'All' matches every product/tier."""
    parts = []
    for field, value in (("product", product), ("tier", tier)):
        if value:
            parts.append(f"({field} eq {_odata_literal(value)} or {field} eq 'All')")
    return " and ".join(parts) or None


class AzureSearchRetriever(IRetriever):
    """Hybrid (keyword + vector) query on Rohan's Azure AI Search index, reranked by the semantic ranker."""

    def __init__(self, search_client=None, embed=None):
        if search_client is None:
            from azure.core.credentials import AzureKeyCredential
            from azure.search.documents import SearchClient
            search_client = SearchClient(
                endpoint=os.environ["AZURE_SEARCH_ENDPOINT"].strip(),
                index_name=os.environ["AZURE_SEARCH_INDEX_NAME"].strip(),
                credential=AzureKeyCredential(os.environ["AZURE_SEARCH_ADMIN_KEY"].strip()),
            )
        self.client = search_client
        self.embed = embed or self._foundry_embedder()
        self.semantic_config = os.getenv("AZURE_SEARCH_SEMANTIC_CONFIG", "insurance-semantic-config")

    @staticmethod
    def _foundry_embedder():
        from openai import OpenAI
        endpoint = os.environ["AZURE_OPENAI_ENDPOINT"].strip().rstrip("/")
        if endpoint.endswith("/openai/v1"):
            endpoint = endpoint[: -len("/openai/v1")]
        client = OpenAI(base_url=f"{endpoint}/openai/v1/", api_key=os.environ["AZURE_OPENAI_API_KEY"].strip())
        deployment = os.environ["AZURE_OPENAI_EMBED_DEPLOYMENT"].strip()
        return lambda text: client.embeddings.create(model=deployment, input=text).data[0].embedding

    def search(self, query: str, k: int = 5,
               product: Optional[str] = None, tier: Optional[str] = None) -> List[SearchHit]:
        from azure.search.documents.models import VectorizedQuery
        vector = VectorizedQuery(vector=self.embed(query), k_nearest_neighbors=50, fields="embedding")
        results = self.client.search(
            search_text=query,
            vector_queries=[vector],
            query_type="semantic",
            semantic_configuration_name=self.semantic_config,
            filter=azure_filter(product, tier),
            select=list(FIELDS),
            top=k,
        )
        hits = []
        for r in results:
            score = r.get("@search.reranker_score") or r.get("@search.score") or 0.0
            hits.append(SearchHit(**{f: str(r[f]) for f in FIELDS}, score=round(float(score), 4)))
        return hits


@lru_cache
def get_retriever() -> IRetriever:
    mode = os.getenv("RETRIEVER", "local")
    if mode == "local":
        return LocalRetriever()
    if mode == "azure":
        return AzureSearchRetriever()
    raise ValueError(f"Unknown RETRIEVER={mode} (use local or azure)")
