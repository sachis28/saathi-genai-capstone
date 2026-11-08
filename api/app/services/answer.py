"""Grounded answer generation: turns retrieved clauses into a cited answer, or refuses.

The LLM never gets the final say. Its answer must pass three checks in code:
1. poisoned / untrusted clauses are removed before the LLM sees them;
2. only citations that point at clauses we actually retrieved are kept;
3. the Grounding Shield checks every cited sentence really matches its clause.
If any check fails, the user gets NOT_FOUND instead of a possibly wrong answer."""
import re
from typing import List, Tuple

from app.models.schemas import Citation, SearchHit
from app.services.llm import get_llm
from app.services.prompts import SYSTEM_PROMPT, build_user_prompt
from app.services.safety import filter_poisoned, check_grounding, safe_log, strip_disclaimers

# The single "safe refusal" message used everywhere in the app.
NOT_FOUND = "I could not find this in the policy documents."
# Matches citation tags like [POL-HEALTH-GOLD#EXC-GOLD-07] -> ("POL-HEALTH-GOLD", "EXC-GOLD-07").
TAG = re.compile(r"\[([A-Za-z0-9\-]+)#([A-Za-z0-9\-]+)\]")


# Returns (answer text, list of citations). hits = clauses returned by the retriever.
def generate_answer(question: str, hits: List[SearchHit]) -> Tuple[str, List[Citation]]:
    # Safety 1: drop poisoned clauses before the LLM ever sees them
    hits, removed = filter_poisoned(hits)
    if removed:
        safe_log("poisoned_context_removed", count=removed)

    if not hits:
        return NOT_FOUND, []

    # Ask the LLM (mock, Ollama or Azure) using the system rules and the numbered clauses.
    answer = get_llm().complete(SYSTEM_PROMPT, build_user_prompt(question, hits))

    # Honest "the context does not say X" sentences are removed, not treated as claims.
    # Every remaining fact still has to be cited and grounded.
    answer = strip_disclaimers(answer)
    if not answer:
        return NOT_FOUND, []

    # Safety 2: keep only citations that really came from search
    # Map of (source_id, clause_id) -> clause, for clauses that really came from search.
    valid = {(h.source_id, h.clause_id): h for h in hits}
    citations, seen = [], set()
    for source_id, clause_id in TAG.findall(answer):
        key = (source_id, clause_id)
        if key in valid and key not in seen:
            seen.add(key)
            citations.append(Citation(source_id=source_id, clause_id=clause_id, version=valid[key].version))

    if not citations:
        return NOT_FOUND, []

    # Safety 3: Grounding Shield, every claim must be supported by its clause
    unsupported = check_grounding(answer, hits)
    if unsupported:
        safe_log("grounding_failed", unsupported_count=len(unsupported))
        return NOT_FOUND, []

    return answer, citations
