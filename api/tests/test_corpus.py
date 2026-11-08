"""Makes sure the search index never loads the poisoned test docs or the gold evaluation set."""
from app.services.retriever import LocalRetriever, CORPUS_DIR

def test_default_corpus_excludes_poison_and_gold(monkeypatch):
    monkeypatch.delenv("CORPUS_FILES", raising=False)
    chunks = LocalRetriever._load(CORPUS_DIR)
    assert len(chunks) > 0
    assert not any(c["clause_id"].startswith("POISON")
                   or c["source_id"].startswith("UNTRUSTED") for c in chunks)