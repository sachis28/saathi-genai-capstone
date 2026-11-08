"""Off-topic guard for /chat.

A question is off-topic when none of its words appear anywhere in the policy clauses
("dumb?", "tell me a joke", "weather in Pune"). Those get a polite redirect instead of
retrieved clauses. If the clause files are missing, nothing is blocked.
"""
import json
import re
from functools import lru_cache
from pathlib import Path

from app.services.safety import content_words

CORPUS_DIR = Path(__file__).resolve().parents[3] / "rag" / "corpus"
CORPUS_NAMES = ("insurance_chunks.jsonl", "insurance_docs.jsonl", "sample_docs.jsonl")

# Words every question uses; they say nothing about whether it is about insurance.
QUESTION_WORDS = {
    "what", "when", "which", "where", "who", "why", "how", "does", "did", "tell", "about",
    "please", "give", "show", "explain", "there", "they", "their", "them", "his", "her",
    "customer", "customers", "customer's", "me", "can", "could", "would", "should",
}
# Product names and plan words are always on topic, even if a clause never spells them out.
DOMAIN = {
    "policy", "policies", "plan", "plans", "insurance", "insurer", "insured", "premium", "premiums",
    "claim", "claims", "cover", "covered", "coverage", "renew", "renewal", "renewing", "lapse", "lapsed",
    "expiry", "expire", "due", "grace", "health", "motor", "silver", "gold", "platinum", "tier",
    "spouse", "wife", "husband", "family", "member", "members", "dependent", "dependents", "child",
    "children", "parents", "nominee", "opd", "copay", "deductible", "idv", "ncb", "cancel",
    "cancellation", "refund", "cashless", "reimbursement", "hospital", "hospitalisation",
    "hospitalization", "surgery", "treatment", "doctor", "ambulance", "medicine", "maternity",
    "disease", "diseases", "accident", "vehicle", "car", "bike", "rider", "addon", "port",
    "portability", "tax", "80d", "kyc", "quote", "cost", "price", "pay", "payment", "sum", "bonus",
    "waiting", "exclusion", "exclusions", "excluded", "consent", "draft", "agent",
}

OFF_TOPIC_MSG = ("I can only help with insurance policy questions, for example the waiting period, "
                 "what a plan covers, or the renewal grace period. Please ask a policy question.")


# Every content word that appears in any policy clause, read once and cached.
@lru_cache
def corpus_vocabulary() -> frozenset:
    words = set()
    for name in CORPUS_NAMES:
        path = CORPUS_DIR / name
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                words |= content_words(" ".join(str(row.get(k, "")) for k in ("text", "product", "tier", "title")))
    return frozenset(words)


# The question's content words, minus generic question words.
def topic_words(question: str) -> set:
    return {w for w in content_words(question) if w not in QUESTION_WORDS}


# True if the question shares at least one word with the clauses or the insurance word list.
def is_on_topic(question: str) -> bool:
    vocab = corpus_vocabulary()
    if not vocab:
        return True  # fail open: no clause files to compare against
    words = topic_words(question)
    if not words:
        # Only question words ("what about them?"): fine as a follow-up, off-topic on its own.
        return False
    return bool(words & (vocab | DOMAIN))
