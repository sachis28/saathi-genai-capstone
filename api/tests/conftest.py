import os

# Tests must never call the real Foundry model (costs credits, answers vary).
os.environ["LLM_PROVIDER"] = "mock"
