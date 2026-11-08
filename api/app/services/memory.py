"""Short-term conversation memory for /chat, kept in RAM per session_id.

Only the last MAX_TURNS turns are kept. It lets "and Platinum?" be understood as
"<previous question> and Platinum?"."""
import re
from collections import defaultdict, deque
from typing import Deque, Dict, List

from app.models.schemas import Turn

# How many recent turns each session remembers.
MAX_TURNS = 6

# Questions starting with these words continue the previous question.
FOLLOW_UP = re.compile(r"^\s*(and|also|what about|how about|same for)\b", re.IGNORECASE)

# session_id -> recent turns. deque(maxlen=...) drops the oldest turn automatically.
_sessions: Dict[str, Deque[Turn]] = defaultdict(lambda: deque(maxlen=MAX_TURNS))


def get_history(session_id: str) -> List[Turn]:
    return list(_sessions.get(session_id, []))


def add_turn(session_id: str, question: str, resolved_question: str, answer: str) -> None:
    _sessions[session_id].append(
        Turn(question=question, resolved_question=resolved_question, answer=answer)
    )


def is_follow_up(question: str) -> bool:
    """'and Platinum?' or a short 'Platinum?' continues the last question; 'dumb?' does not."""
    if FOLLOW_UP.match(question):
        return True
    if len(question.split()) <= 3:
        from app.services.topic_guard import is_on_topic
        return is_on_topic(question)
    return False


def resolve_question(session_id: str, question: str) -> str:
    """Turn 'and Platinum?' into a full question using the previous turn."""
    history = get_history(session_id)
    if history and is_follow_up(question):
        return f"{history[-1].resolved_question} {question}"
    return question


# Forget one session (used by tests).
def clear(session_id: str) -> None:
    _sessions.pop(session_id, None)