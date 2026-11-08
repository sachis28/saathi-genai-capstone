"""Optional LLM query rewriting before retrieval (QUERY_REWRITE=llm).

The agent's question can be long or conversational ("and what about Platinum?" after memory
resolution). A short keyword-rich query retrieves better. Rewriting only changes what we search
for: the answer is still generated from the original question and grounded in the retrieved clauses.
"""
import os

from app.services.llm import get_llm
from app.services.safety import is_injection

SYSTEM = (
    "Rewrite the insurance agent's question as one short search query for policy clauses. "
    "Keep product names, tiers and insurance terms. Do not answer the question. "
    "Return only the query, on one line, with no quotes."
)


# Returns a shorter search query, or the original question if rewriting is off or looks unsafe.
def rewrite_query(question: str) -> str:
    # Off by default; set QUERY_REWRITE=llm to turn it on.
    if os.getenv("QUERY_REWRITE", "off").lower() != "llm":
        return question
    try:
        # Keep only the first line of whatever the model returns.
        rewritten = (get_llm().complete(SYSTEM, question) or "").strip().splitlines()[0].strip()
    # Any provider error: just search with the original question.
    except Exception:
        return question
    # Never let the model widen or redirect the search: fall back on anything odd.
    if not rewritten or len(rewritten) > 200 or is_injection(rewritten):
        return question
    return rewritten
