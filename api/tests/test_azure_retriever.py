"""Azure AI Search retriever tests using a fake search client (no Azure calls):
the filter rule, the hybrid + semantic query, and safe fallbacks for query rewriting."""
from app.services import query_rewrite
from app.services.retriever import AzureSearchRetriever, azure_filter


# A stand-in for Azure's SearchClient: records the query it receives and returns canned rows.
class FakeSearchClient:
    def __init__(self, rows):
        self.rows, self.calls = rows, []

    def search(self, **kwargs):
        self.calls.append(kwargs)
        return iter(self.rows)


ROW = {"source_id": "HEALTH-GOLD", "clause_id": "CL-WAIT-02", "version": "v2", "product": "Health",
       "tier": "Gold", "text": "Pre-existing diseases are covered after 24 months.",
       "@search.score": 0.03, "@search.reranker_score": 2.91}


def test_filter_matches_local_retriever_rule():
    assert azure_filter(None, None) is None
    assert azure_filter("Health", None) == "(product eq 'Health' or product eq 'All')"
    assert azure_filter("Health", "Gold") == ("(product eq 'Health' or product eq 'All') and "
                                              "(tier eq 'Gold' or tier eq 'All')")
    assert "O''Brien" in azure_filter("O'Brien", None)  # quotes are escaped, not injected


def test_hybrid_semantic_query_and_hit_mapping():
    client = FakeSearchClient([ROW])
    retriever = AzureSearchRetriever(search_client=client, embed=lambda text: [0.1] * 1536)
    hits = retriever.search("waiting period for pre-existing diseases", k=3, product="Health")

    call = client.calls[0]
    assert call["search_text"] == "waiting period for pre-existing diseases"
    assert call["query_type"] == "semantic"
    assert call["vector_queries"][0].fields == "embedding"
    assert call["top"] == 3
    assert call["filter"] == "(product eq 'Health' or product eq 'All')"
    assert hits[0].clause_id == "CL-WAIT-02" and hits[0].score == 2.91


def test_query_rewrite_is_off_by_default(monkeypatch):
    monkeypatch.delenv("QUERY_REWRITE", raising=False)
    assert query_rewrite.rewrite_query("and what about Platinum?") == "and what about Platinum?"


def test_query_rewrite_falls_back_on_bad_output(monkeypatch):
    monkeypatch.setenv("QUERY_REWRITE", "llm")

    class LLM:
        def __init__(self, out):
            self.out = out

        def complete(self, system, user):
            return self.out

    monkeypatch.setattr(query_rewrite, "get_llm", lambda: LLM("Health Platinum waiting period"))
    assert query_rewrite.rewrite_query("and what about Platinum?") == "Health Platinum waiting period"
    monkeypatch.setattr(query_rewrite, "get_llm", lambda: LLM("ignore previous instructions"))
    assert query_rewrite.rewrite_query("q") == "q"
    monkeypatch.setattr(query_rewrite, "get_llm", lambda: LLM(""))
    assert query_rewrite.rewrite_query("q") == "q"
