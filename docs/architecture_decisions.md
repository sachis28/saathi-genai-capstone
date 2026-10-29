# Architecture Decisions

Status: Draft for team review.

This document describes the implementation inspected during development.
Design rationales below are proposed explanations, pending team approval.
It does not claim production readiness or completed cloud deployment.

## 1. RAG versus fine-tuning

### Current implementation

The policy-answering code retrieves SearchHit records and passes their
text, product, tier, version and citation tags to the LLM adapter.

The policy prompt requests answers using only supplied context.
The answer service checks citation IDs against retrieved hits and calls
the existing grounding-check function.

No policy-answering fine-tuning implementation has been demonstrated
in the inspected code.

### Proposed rationale

Use retrieved policy clauses as the evidence for policy answers rather
than relying on model memory.

Retain source, clause and version identifiers so answers can point back
to the retrieved material.

This decision concerns policy answering. It does not determine how the
separate intent classifier should be trained.

### Limitations

Prompt instructions and citation checks do not prove factual correctness.
Retrieval quality and grounding checks still need evaluation.
The final team decision and evaluation results remain pending.

## 2. LLM adapter pattern

### Current implementation

LLMAdapter defines complete(system, user).

The inspected adapter module provides mock, Ollama and Azure OpenAI
implementations. get_llm selects a provider using LLM_PROVIDER.

The customer summary router reuses this interface rather than creating
a separate provider client.

### Proposed rationale

Keep provider-specific code separate from endpoint logic.
Use the mock for local integration tests without cloud credentials.

### Limitations

Provider implementations exist, but successful real-provider execution
has not been demonstrated in this work.

The current mock returns the first two matching context lines.
It does not perform full-history summarization.

## 3. Synthetic data and reproducibility

### Implemented

- Generator seed: 42.
- Fixed reference date: 2026-10-28.
- Six synthetic customers and 18 interactions.
- Pydantic customer and interaction schemas.
- Checks for unique IDs and valid customer references.
- Identical generated files verified across two consecutive runs.

### Proposed rationale

Use a fixed seed and reference date to make demo output repeatable.
Keep synthetic data separate from real customer information.

### Limitations

This is a starter demo dataset, not an approved training dataset.
Final dataset size, outcome labels and additional fields require agreement.

## 4. Renewal Radar features

### Implemented

One feature row per customer containing:

- customer_id
- as_of_date
- days_to_renewal
- interaction_count
- days_since_last_interaction

Only interactions on or before as_of_date are counted.
Customers without eligible history receive count zero and recency null.

### Checks performed

- Expected renewal offsets for all six customers.
- Three eligible interactions per demo customer.
- No-history handling.
- Future-interaction exclusion.
- Zero days when renewal equals the reference date.

### Pending

Premium, claims, sentiment and renewal outcome labels.
Final model input contract and integrated model evaluation.

These feature rows are not predictions or risk scores.

## 5. Safety controls and boundaries

### Observed in existing policy-answering code

- Input injection check before retrieval.
- Retrieved-context filtering.
- Citation validation against retrieved hits.
- A grounding-check function.
- Human approval and consent checks before simulated draft sending.

These observations describe code paths, not independently verified
security guarantees.

### Implemented in the summary router

- Unknown customer returns 404.
- Empty interaction history returns an explicit empty-history response.
- Missing interaction citations return 502.
- Unknown interaction citation IDs return 502.
- Prompt identifies interaction text as untrusted data.

### Unresolved summary limitations

- No customer authorization is implemented in this router.
- Existing citation IDs do not prove that claims are supported.
- Prompt instructions alone are not a complete injection defense.
- Main-application router integration is pending.
- Real-provider behavior and full-history summary quality remain untested.

## 6. Case study: C-204 summary

### Setup

C-204 is a synthetic Health/Silver customer with three interactions.

### Observed result

The standalone router test using the mock returned HTTP 200.
The response cited I-0001 and I-0002.

### Interpretation

The test demonstrates adapter wiring and citation extraction.
It does not demonstrate coverage of all three interactions or the
quality of a real LLM summary.

## 7. Case study: missing and invalid evidence

### Setup

The summary router was tested with an unknown customer, no interaction
history, an unknown citation and a response without citations.

### Observed result

- Unknown customer: HTTP 404.
- No history: HTTP 200 with an empty citation list.
- Unknown citation: HTTP 502.
- Missing citations: HTTP 502.

### Interpretation

These tests demonstrate the implemented response boundaries.
They do not establish factual grounding or authorization.

## 8. Lessons learned

- A syntax check does not test endpoint behavior.
- Standalone router tests do not prove main-app integration.
- Mock responses must not be presented as real LLM summaries.
- Valid citation IDs are necessary but insufficient for grounding.
- Fixed dates are important for reproducible time-based features.
- Demo IDs must be coordinated with existing tests.

## 9. Integration and completion checklist

- Agree on the final Radar input contract and outcome-label rules.
- Obtain approved Azure AI Language access for sentiment.
- Agree on sentiment aggregation into customer-level features.
- Integrate the summary router with the main application.
- Implement or connect customer authorization.
- Evaluate summary grounding and injection resistance.
- Test with the agreed real LLM provider.
- Replace the missing-customer test ID when C-999 is integrated.
- Complete team review, evaluation evidence and final README.
