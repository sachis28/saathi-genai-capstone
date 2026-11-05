"""Interaction-specific validation, deliberately conservative and extractive."""
import re

from app.services.safety import is_injection

CITATION = re.compile(r'\[(I-[0-9]+)\]')


def normalized(text):
    return ' '.join(text.split())


def validate_summary(answer: str, history: list[dict]) -> list[str]:
    if not isinstance(answer, str) or not answer.strip() or is_injection(answer):
        raise ValueError('Unsafe or empty summary')
    sources = {row['interaction_id']: normalized(row['text']) for row in history}
    if len(sources) != len(history):
        raise ValueError('Duplicate source interaction IDs')
    matches = list(CITATION.finditer(answer))
    if not matches:
        raise ValueError('Missing interaction citations')
    seen = []
    start = 0
    for match in matches:
        cited = match.group(1)
        claim = normalized(answer[start:match.start()]).lstrip('-*• ').strip('"')
        if cited not in sources or claim != sources[cited] or cited in seen:
            raise ValueError('Unsupported claim or invalid interaction citation')
        seen.append(cited)
        start = match.end()
    if answer[start:].strip() or set(seen) != set(sources):
        raise ValueError('Uncited text or incomplete interaction coverage')
    return seen
