# Saathi architecture decisions and integration evidence

This document describes implemented local behavior on Sairaj's review branch. It incorporates Sachi's completed work without claiming production readiness. The task's reported feat/shreya-rohan-corpus branch was not present in the repository inventory. The inspected feat/shreya-integrate-sachi and main customer services still lacked the proposed centralized policy/authorization helpers; this branch adds those helpers for review. No main.py edits or main-branch merge are part of this follow-up.

## Central customer and policy service

CRM loading, metadata preservation, the fixed/current reference date, 30-day-grace calculation and authorize_customer belong to api/app/services/customers.py. The API Customer preserves ownership, product, consent, renewal date and annual premium. Loaders reread current files so send-time consent is not stale. Derived statuses are ACTIVE, IN_GRACE, LAPSED and CANCELLED with explicit cancellation taking precedence. This removes duplicated status logic from worklist filtering and generators.

The six-customer export remains inference/demo data. Two documented synthetic changes exercise LAPSED and CANCELLED. Existing ownership, premiums, interaction text/dates, saved service sentiment and locked intent data are preserved. Sachi's existing generator/export/helper implementations are restored from pinned commit 180f69a rather than rebuilt from scratch.

## Separate access, eligibility and consent

An authenticated principal plus original CRM agent ownership and approved product access determine visibility. Central renewal eligibility excludes LAPSED/CANCELLED before inference. Consent determines whether an approved outbound message may be sent, not whether risk information can appear in the worklist. The same model features and finite-score checks apply locally and through the Azure adapter. Policy metadata and identity credentials never enter predictive features.

The local bearer adapter is replaceable. No actual production credentials or approved product mapping were created. Controlled test scopes exercise cross-agent/product isolation, but do not establish a real deployment authorization configuration. Broader endpoint authorization remains an integration task for Shreya.

## Interaction summaries

The existing get_llm().complete(system,user) interface is preserved. Summary loading/ownership comes from the shared customer service, with product scope checked before history is read. Every interaction is processed in two-record batches, removing the previous mock-only-first-two limitation.

Policy grounding expects SOURCE#CLAUSE tags and is not used for interaction summaries. A new interaction-specific validator requires exact source text and matching customer interaction IDs for every returned statement, complete batch coverage and no uncited trailing text. Injection-like input/output is rejected. This is conservative extractive grounding, not proof of arbitrary semantic correctness or an abstractive summarizer; it can reject safe paraphrases. Future abstraction requires a separately evaluated entailment approach.

## Actual evidence and limitations

The current targeted suite has 87 passing tests. Local Radar uses an actual rebuilt compatible scikit-learn artifact, trained only on the separate 1,200-row synthetic ML fixture. Four eligible CRM customers have measured finite scores; C-118 and C-999 are excluded by policy rules. C-205 remains visible while its simulated send is blocked after approval.

Integrated TestClient flows use real Radar/central eligibility, test-only identity scopes, mock interaction summaries, mock chat classifier/retrieval and existing draft/approval/consent behavior. These do not prove live RAG, real DistilBERT inference, browser UI operation or end-to-end deployed authorization. The full application suite has not been run here because heavy retrieval/intent dependencies and trained intent artifacts are absent. Rohan's corpus is not regenerated.

Azure summary integration was not attempted: AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY and AZURE_OPENAI_DEPLOYMENT were absent. Configure gpt-4.1-mini through the existing Azure adapter and run a separately approved real integration check; ordinary tests keep LLM_PROVIDER=mock. No cloud metrics, credentials or screenshots are fabricated. Synthetic model metrics are not real customer accuracy.

See sachi_followup_handover.md for exact changed files, commands, fixture mapping, scores and external blockers.
