import os

# Tests must never call the real Foundry model (costs credits, answers vary).
os.environ["LLM_PROVIDER"] = "mock"

# Tests use the 8 fixed sample clauses, so results never change when the real corpus grows.
os.environ["CORPUS_FILES"] = "sample_docs.jsonl"
