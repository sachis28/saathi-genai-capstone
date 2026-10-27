import re
from collections import defaultdict, deque
from typing import Deque, Dict, List

from app.models.schemas import Turn

MAX_TURNS = 6

FOLLOW_UP = re.compile(r"^\s*(and|also|what about|how about|same for)\b", re.IGNORECASE)

_sessions: Dict[str, Deque[Turn]] = defaultdict(lambda: deque(maxlen=MAX_TURNS))


def get_history(session_id: str) -> List[Turn]:
    return list(_sessions.get(session_id, []))


def add_turn(session_id: str, question: str, resolved_question: str, answer: str) -> None:
    _sessions[session_id].append(
        Turn(question=question, resolved_question=resolved_question, answer=answer)
    )


def is_follow_up(question: str) -> bool:
    return bool(FOLLOW_UP.match(question)) or len(question.split()) <= 3


def resolve_question(session_id: str, question: str) -> str:
    """Turn 'and Platinum?' into a full question using the previous turn."""
    history = get_history(session_id)
    if history and is_follow_up(question):
        return f"{history[-1].resolved_question} {question}"
    return question


def clear(session_id: str) -> None:
    _sessions.pop(session_id, None)