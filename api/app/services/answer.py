import re
from typing import List, Tuple

from app.models.schemas import Citation, SearchHit
from app.services.llm import get_llm
from app.services.prompts import SYSTEM_PROMPT, build_user_prompt

NOT_FOUND = "I could not find this in the policy documents."
TAG = re.compile(r"\[([A-Za-z0-9\-]+)#([A-Za-z0-9\-]+)\]")


def generate_answer(question: str, hits: List[SearchHit]) -> Tuple[str, List[Citation]]:
    if not hits:
        return NOT_FOUND, []

    answer = get_llm().complete(SYSTEM_PROMPT, build_user_prompt(question, hits))

    valid = {(h.source_id, h.clause_id): h for h in hits}
    citations, seen = [], set()
    for source_id, clause_id in TAG.findall(answer):
        key = (source_id, clause_id)
        if key in valid and key not in seen:
            seen.add(key)
            citations.append(Citation(source_id=source_id, clause_id=clause_id, version=valid[key].version))

    # Grounding rule: no valid citation means no answer
    if not citations:
        return NOT_FOUND, []

    return answer, citations