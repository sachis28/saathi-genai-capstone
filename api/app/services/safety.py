"""Guardrails used across the API.

1. Prompt-injection detection, including obfuscated attacks (leetspeak, spaced letters,
zero-width characters, base64), and filtering of poisoned or untrusted clauses.
2. Grounding Shield: every cited sentence must share enough words with its clause.
3. PII redaction so logs and the audit trail never store phone numbers, emails, PAN or Aadhaar."""
import base64
import binascii
import logging
import re
import unicodedata
from typing import List, Tuple

from app.models.schemas import SearchHit

logger = logging.getLogger("saathi")


# ---------- 1. Prompt injection ----------
# One big regular expression. Each "|" line below catches one family of attacks.
INJECTION = re.compile(
    # override: "ignore / forget / disregard / bypass ... instructions / rules / prompt"
    r"\b(ignore|disregard|forget|override|bypass|skip|drop)\b[\w\s,'-]{0,40}?\b(instructions?|rules|prompts?|guidelines|guardrails|polic(y|ies)|restrictions|safety|filters?)\b"
    r"|\bnew (instructions|rules|system prompt)\b"
    r"|\bsystem prompt\b|\b(your|the|hidden|initial) instructions\b"
    # role play / persona swaps
    r"|\byou are now\b|\bfrom now on,? you\b|\bpretend (to be|you are|you're)\b|\bact as (an? |the |my )?(admin\w*|developer|system|root|unfiltered|unrestricted|jailbroken|evil|hacker|ceo|underwriter|supervisor|manager)\b|\brole-?play\b"
    r"|\bdeveloper mode\b|\bjailbreak|\bdo anything now\b|\bDAN\b|\bno (rules|restrictions|limits)\b"
    # extraction
    r"|\b(reveal|print|show|repeat|output|leak|dump|tell me)\b[\w\s]{0,20}?\b(api keys?|passwords?|secrets?|credentials|tokens?|text above|everything above|prompt)\b"
    # approval / consent bypass
    r"|\bsend\b[\w\s]{0,30}?\bwithout\b[\w\s]{0,15}?\b(approval|approving|consent|review)\b"
    r"|\b(skip|bypass|disable|turn off)\b[\w\s]{0,20}?\b(approval|consent|review|human)\b"
    r"|\b(mark|set)\b[\w\s]{0,25}?\bas approved\b|\bauto-?approve\b",
    re.IGNORECASE,
)

# Invisible characters attackers use to hide words from simple filters.
ZERO_WIDTH = re.compile("[\u200b-\u200f\u2060\ufeff\u00ad]")
# Leetspeak map: "1gn0r3" -> "ignore".
LEET = str.maketrans({"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t", "@": "a", "$": "s"})
SPACED = re.compile(r"\b(?:[A-Za-z] ){3,}[A-Za-z]\b")          # "i g n o r e"
B64 = re.compile(r"[A-Za-z0-9+/]{16,}={0,2}")


def _variants(text: str):
    """The text as written, plus de-obfuscated versions: unicode tricks, leetspeak, spacing, base64."""
    base = ZERO_WIDTH.sub("", unicodedata.normalize("NFKC", text))
    yield base
    yield base.translate(LEET)
    yield SPACED.sub(lambda m: m.group(0).replace(" ", ""), base)
    for token in B64.findall(base):
        try:
            decoded = base64.b64decode(token + "=" * (-len(token) % 4), validate=True).decode("utf-8")
        except (binascii.Error, UnicodeDecodeError, ValueError):
            continue
        if decoded.isprintable():
            yield decoded


# True if ANY version of the text (original or de-obfuscated) matches an attack pattern.
def is_injection(text: str) -> bool:
    return any(INJECTION.search(v) for v in _variants(text))


# Only clauses from the official policy library (POL-...) or its scanned endorsements (SCAN-...)
# may reach the LLM. Anything else in the index (test fixtures, uploads, untrusted docs) is dropped.
TRUSTED_SOURCE = re.compile(r"^(POL|SCAN)-")


# Keep a clause only if it is from a trusted source AND its text has no hidden instructions.
def filter_poisoned(hits: List[SearchHit]) -> Tuple[List[SearchHit], int]:
    clean = [h for h in hits if TRUSTED_SOURCE.match(h.source_id) and not is_injection(h.text)]
    return clean, len(hits) - len(clean)


# ---------- 2. Grounding Shield (v1: word overlap) ----------
# Common words ignored when comparing a claim with its clause.
STOP = {
    "the", "and", "for", "with", "are", "is", "was", "of", "to", "in", "a", "an", "on",
    "under", "only", "after", "this", "that", "it", "its", "be", "can", "any", "also",
    "your", "you", "will", "has", "have", "not", "per", "from", "by", "or", "as", "at",
}

# Matches: "<claim text> [SOURCE-ID#CLAUSE-ID]"
TAG_SEGMENT = re.compile(r"(.*?)\[([A-Za-z0-9-]+)#([A-Za-z0-9-]+)\]", re.DOTALL)

# At least 60% of a claim's content words must appear in the cited clause.
THRESHOLD = 0.6

# Sentences where the model honestly says the documents lack something.
# They make no factual claim about insurance, so they need no citation.
DISCLAIMER = re.compile(
    r"(context|documents?|clauses?|policy documents?|information provided)\s+"
    r"(does|do|did)\s+not\s+(specify|mention|contain|include|provide|say|cover)"
    r"|not\s+(specified|mentioned|stated|available|provided)\s+in\s+the\s+(context|documents?|clauses?)"
    r"|i could not find",
    re.IGNORECASE,
)


def strip_disclaimers(answer: str) -> str:
    """Remove 'the context does not specify...' sentences. Cited facts are kept."""
    sentences = re.split(r"(?<=[.!?\]])\s+", answer.strip())
    kept = [s for s in sentences if not DISCLAIMER.search(s)]
    return " ".join(kept).strip()


# The meaningful words of a text (lowercase, no stop words, longer than 2 letters).
def content_words(text: str) -> set:
    words = re.findall(r"[a-z0-9]+", text.lower())
    return {w for w in words if w not in STOP and len(w) > 2}


def check_grounding(answer: str, hits: List[SearchHit]) -> list:
    """Returns the list of unsupported claims. Empty list = fully grounded."""
    clauses = {(h.source_id, h.clause_id): h.text for h in hits}
    unsupported = []
    last_end = 0

    # Walk through the answer one "claim [TAG]" segment at a time.
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

        # Share of the claim's words that also appear in the cited clause.
        overlap = len(words & content_words(clause)) / len(words)
        if overlap < THRESHOLD:
            unsupported.append(claim)

    # Any real sentence after the last citation has no source
    tail = answer[last_end:].strip()
    if len(content_words(tail)) >= 4:
        unsupported.append(tail)

    return unsupported


# ---------- 3. PII-safe logging ----------
# Indian PII patterns: Aadhaar number, PAN card, email address, mobile number.
PII = [
    (re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b"), "[AADHAAR]"),
    (re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b"), "[PAN]"),
    (re.compile(r"\b[\w.+-]+@[\w-]+[.][\w.]+\b"), "[EMAIL]"),
    (re.compile(r"(?<!\d)(?:[+]91[\s-]?)?[6-9]\d{9}(?!\d)"), "[PHONE]"),
]


# Replace every PII match with a label such as [PHONE].
def redact(text: str) -> str:
    for pattern, label in PII:
        text = pattern.sub(label, text)
    return text


# The only logging helper the API uses for user text: redact first, then log.
def safe_log(event: str, **fields) -> None:
    logger.info("%s %s", event, {k: redact(str(v)) for k, v in fields.items()})
