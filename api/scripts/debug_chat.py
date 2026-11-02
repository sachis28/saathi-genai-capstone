"""
Shows why Saathi answered the way it did, using the SAME steps as /chat.
Run from the repo root:
    python api/scripts/debug_chat.py "what is the hospitalisation covered in gold? and platinum?"
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.answer import generate_answer  # noqa: E402
from app.services.llm import get_llm  # noqa: E402  (also loads .env)
from app.services.prompts import SYSTEM_PROMPT, build_user_prompt  # noqa: E402
from app.services.retriever import get_retriever  # noqa: E402
from app.services.safety import check_grounding, filter_poisoned, strip_disclaimers  # noqa: E402

TAG = re.compile(r"\[([A-Za-z0-9-]+)#([A-Za-z0-9-]+)\]")
K = 5  # must match the k used in main.py /chat

question = " ".join(sys.argv[1:]) or "what is the hospitalisation covered in gold? and platinum?"
print("QUESTION:", question)

hits = get_retriever().search(question, k=K, product="Health")
print(f"\n1) RETRIEVED (top {K}):")
for h in hits:
    print(f"   {h.source_id}#{h.clause_id}   score={h.score}")

clean, removed = filter_poisoned(hits)
print(f"\n2) POISONED CLAUSES REMOVED: {removed}")

raw = get_llm().complete(SYSTEM_PROMPT, build_user_prompt(question, clean))
print("\n3) RAW MODEL ANSWER:\n   ", raw)

cleaned = strip_disclaimers(raw)
print("\n4) AFTER REMOVING 'CONTEXT DOES NOT SPECIFY' SENTENCES:\n   ", cleaned or "(nothing left)")

valid = {(h.source_id, h.clause_id) for h in clean}
tags = TAG.findall(cleaned)
print("\n5) CITATION TAGS:", tags, "| all real:", bool(tags) and all(t in valid for t in tags))

bad = check_grounding(cleaned, clean)
print("\n6) GROUNDING SHIELD:", "PASSED" if not bad else "REJECTED")
for b in bad:
    print("   unsupported text:", b)

answer, citations = generate_answer(question, hits)
print("\n7) FINAL ANSWER SENT TO THE USER (same as /chat):\n   ", answer)
print("   citations:", [f"{c.source_id}#{c.clause_id}" for c in citations])
