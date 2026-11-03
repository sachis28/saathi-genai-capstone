# Sachi summary completion PR

Base: feat/sachi-data at 180f69a. This focused PR adds the exact GPT-4.1-mini playground prompt that passed the existing strict interaction validator. It includes full-history batching (two records per provider call), interaction-specific exact-text grounding, rejection of injection input/output, invalid citations and unsupported claims, and sanitized provider errors. This is conservative extractive output, not abstractive summarization.

The previous live response used leading citations and date/channel metadata; this response is now a rejection regression fixture. The improved prompt explicitly requires text followed by [I-0001] with no date/channel metadata.

## Verified locally

```bash
LLM_PROVIDER=mock PYTHONPATH=.:api python -m pytest api/tests/test_summary.py tests -q
```

33 passed, one TestClient deprecation warning. Includes six demo customers with all 18 interactions, the third interaction after the first two-record batch, wrong IDs, wrong citation placement, unsupported content, uncited tails, missing citations, injection and provider failure. Existing data/premium/sentiment exports remain byte-identical to the base. C-450 remains -5 in the Radar export. No model is trained on these six rows.

A broader attempt including test_safety.py and test_llm.py failed collection because faiss is unavailable in this environment. No full-app test success is claimed.

## Separate Azure verification

Prior live playground evidence: existing Saathi_foundry / gpt-4.1-mini responded; the exact revised prompt produced these two lines, both accepted by the strict validator:

```text
Please explain the coverage under my Silver policy. [I-0001]
Please share the documents needed for renewal. [I-0002]
```

This proves the two-interaction playground case, not the actual API adapter, deployed authentication or all-customer live acceptance. A third-record response in unit tests is a controlled test response, not a claimed Azure observation. Browser access does not provision runtime API configuration.

An opt-in paid live check exercises the actual Azure adapter and standalone summary router using synthetic C-204 (two provider calls for all three interactions):

```bash
# Configure AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY and
# AZURE_OPENAI_DEPLOYMENT=gpt-4.1-mini securely in the environment.
PYTHONPATH=.:api python scripts/verify_summary_azure.py --run-live
```

Ordinary pytest never collects this script and remains LLM_PROVIDER=mock. It fails before any provider call if runtime configuration is missing. Never commit credentials.

## Integration boundary

The target branch does not yet contain the protected customer/agent/product integration already prepared on sairaj PR #10. This PR preserves that boundary and does not change main.py, identity settings, grants, CRM rows or outbound consent handling. It must not be deployed as an unauthenticated summary endpoint. Shreya should combine it with the protected router, retaining authorize_customer and authenticate_agent plus product checks. Approval was reported by Sairaj; no concrete product mapping or credentials were supplied by that statement. Runtime live API validation and shared CRM/deployment authorization acceptance remain outstanding until those configurations are available.

No merge to main or direct push to Sachi's branch is part of this PR.
