import logging
import re
from typing import List, Tuple

from app.models.schemas import SearchHit

logger = logging.getLogger("saathi")


# ---------- 1. Prompt injection ----------
INJECTION = re.compile(
    r"ignore (all |any )?(previous|prior|above) instructions"
    r"|disregard (the )?(system|previous) (prompt|instructions)"
    r"|you are now"
    r"|reveal (the )?(system prompt|api key|password)"
    r"|send (the )?(message|draft) without approval"
    r"|act as (an? )?(admin|developer)",
    re.IGNORECASE,
)


def is_injection(text: str) -> bool:
    return bool(INJECTION.search(text))


def filter_poisoned(hits: List[SearchHit]) -> Tuple[List[SearchHit], int]:
    clean = [h for h in hits if not is_injection(h.text)]
    return clean, len(hits) - len(clean)


# ---------- 2. Grounding Shield (v1: word overlap) ----------
STOP = {
    "the", "and", "for", "with", "are", "is", "was", "of", "to", "in", "a", "an", "on",
    "under", "only", "after", "this", "that", "it", "its", "be", "can", "any", "also",
    "your", "you", "will", "has", "have", "not", "per", "from", "by", "or", "as", "at",
}

# Matches: "<claim text> [SOURCE-ID#CLAUSE-ID]"
TAG_SEGMENT = re.compile(r"(.*?)\[([A-Za-z0-9-]+)#([A-Za-z0-9-]+)\]", re.DOTALL)

THRESHOLD = 0.6


def content_words(text: str) -> set:
    words = re.findall(r"[a-z0-9]+", text.lower())
    return {w for w in words if w not in STOP and len(w) > 2}


def check_grounding(answer: str, hits: List[SearchHit]) -> list:
    """Returns the list of unsupported claims. Empty list = fully grounded."""
    clauses = {(h.source_id, h.clause_id): h.text for h in hits}
    unsupported = []
    last_end = 0

    for m in TAG_SEGMENT.finditer(answer):
        claim = m.group(1).strip()
        source_id = m.group(2)
        clause_id = m.group(3)
        last_end = m.end()

        words = content_words(claim)
        if not words:
            continue

        clause = clauses.get((source_id, clause_id))
        if clause is None:
            unsupported.append(claim)
            continue

        overlap = len(words & content_words(clause)) / len(words)
        if overlap < THRESHOLD:
            unsupported.append(claim)

    # Any real sentence after the last citation has no source
    tail = answer[last_end:].strip()
    if len(content_words(tail)) >= 4:
        unsupported.append(tail)

    return unsupported


# ---------- 3. PII-safe logging ----------
PII = [
    (re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b"), "[AADHAAR]"),
    (re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b"), "[PAN]"),
    (re.compile(r"\b[\w.+-]+@[\w-]+[.][\w.]+\b"), "[EMAIL]"),
    (re.compile(r"(?<!\d)(?:[+]91[\s-]?)?[6-9]\d{9}(?!\d)"), "[PHONE]"),
]


def redact(text: str) -> str:
    for pattern, label in PII:
        text = pattern.sub(label, text)
    return text


def safe_log(event: str, **fields) -> None:
    logger.info("%s %s", event, {k: redact(str(v)) for k, v in fields.items()})
