import json
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

CORPUS_DIR = Path(__file__).resolve().parents[3] / "rag" / "corpus"
RRF_K = 60
FIELDS = ("source_id", "clause_id", "version", "product", "tier", "text")


def tokenize(text: str) -> List[str]:
    return re.findall(r"\w+", text.lower())


class IRetriever(ABC):
    """Plugin interface: LocalRetriever now, AzureSearchRetriever on Day 41."""

    @abstractmethod
    def search(self, query: str, k: int = 5,
               product: Optional[str] = None, tier: Optional[str] = None) -> List[SearchHit]:
        ...


class LocalRetriever(IRetriever):
    """Hybrid search: BM25 (keywords) + MiniLM/FAISS (meaning), fused with RRF."""

    def __init__(self, corpus_dir: Path = CORPUS_DIR):
        self.chunks = self._load(corpus_dir)
        if not self.chunks:
            raise RuntimeError(f"No .jsonl files found in {corpus_dir}")

        texts = [c["text"] for c in self.chunks]
        self.bm25 = BM25Okapi([tokenize(t) for t in texts])

        self.model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        emb = self.model.encode(texts, normalize_embeddings=True).astype("float32")
        self.index = faiss.IndexFlatIP(emb.shape[1])
        self.index.add(emb)

    @staticmethod
    def _load(corpus_dir: Path) -> List[dict]:
        chunks = []
        for f in sorted(corpus_dir.glob("*.jsonl")):
            for line in f.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    chunks.append(json.loads(line))
        return chunks

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

        # 1) Keyword ranking (BM25)
        bm25_scores = self.bm25.get_scores(tokenize(query))
        bm25_rank = [int(i) for i in np.argsort(-bm25_scores) if int(i) in allowed]

        # 2) Meaning ranking (MiniLM + FAISS)
        q = self.model.encode([query], normalize_embeddings=True).astype("float32")
        _, ids = self.index.search(q, len(self.chunks))
        vec_rank = [int(i) for i in ids[0] if int(i) in allowed]

        # 3) Reciprocal Rank Fusion
        fused = {}
        for ranking in (bm25_rank, vec_rank):
            for r, i in enumerate(ranking):
                fused[i] = fused.get(i, 0.0) + 1.0 / (RRF_K + r + 1)

        top = sorted(fused.items(), key=lambda x: x[1], reverse=True)[:k]
        return [
            SearchHit(**{f: self.chunks[i][f] for f in FIELDS}, score=round(s, 4))
            for i, s in top
        ]


@lru_cache
def get_retriever() -> IRetriever:
    mode = os.getenv("RETRIEVER", "local")
    if mode == "local":
        return LocalRetriever()
    raise NotImplementedError(f"RETRIEVER={mode} not built yet (Azure comes on Day 41)")