# CRM worklist access contract

GET /worklist now authenticates an agent and joins CRM-linked Radar rows to current server-side customer records before invoking either local or Azure scoring. It no longer falls back to the generated training CSV. This implements the proposed metadata contract without assigning new statuses to Sachi's six customers.

## Exact metadata contract

The server-side CRM customer record supplies the following fields in addition to its existing data:

| Field | Type and allowed values | Rule |
| --- | --- | --- |
| customer_id | Nonempty string | Exact unique join to the Radar row |
| agent_id | String or absent | Must equal the authenticated agent_id |
| product | String or absent | Must appear in the authenticated agent's allowed_products |
| consent | Strict boolean or absent | Must be true in both current CRM and feature row |
| policy_status | active, expired, cancelled, terminated, or absent | Only active/expired can proceed |
| renewal_eligible | Strict boolean or absent | Must be true |

Field and status spelling is case-sensitive. Missing/null access metadata excludes the customer. Unknown status values, string/number booleans, duplicate CRM IDs or duplicate JSON keys reject the request instead of being silently coerced. A renewal date is never used to invent policy_status or renewal_eligible. Negative days_to_renewal is preserved and is not an exclusion condition.

Sachi and Shreya still need to confirm these proposed status values against their domain rules and add approved metadata through their CRM schema/export path. In particular, data/schemas.py has not been changed to populate or preserve these new policy fields, and the existing six CRM fixtures remain unchanged. A CRM record that lacks eligibility metadata will not score through the protected worklist.

The current CRM models represent one policy/product per customer. Multi-policy customers need a policy_id-aware contract before this gate is used for them. Do not treat a model score as an eligibility decision.

## Authentication and configuration

The dependency authenticate_agent returns an immutable AgentPrincipal from server-managed credentials. For the offline capstone, the supplied adapter accepts an opaque Bearer token and looks up its SHA-256 digest in a server-owned JSON file. It does not trust X-Agent-ID, query-string agent_id, request-body roles or client-provided product grants. Changing/removing a digest takes effect on the next request.

Set SAATHI_AGENT_CREDENTIALS_FILE to the absolute path of that private JSON file. Its format is an array of objects with agent_id, allowed_products (a nonempty list), and token_sha256 (64 lowercase hex characters). Only store a SHA-256 digest of a long randomly generated token, never the token itself. Provision agent IDs and exact product grants from the team-approved access mapping; no default account, token, wildcard grant or demo customer ownership is created by this change. Keep the file outside the repository, protect its file permissions, and send bearer tokens only over HTTPS outside local loopback development.

Missing/invalid credentials return 401. A presented token with absent/malformed server configuration returns 503. No secret is logged. The FastAPI dependency can be replaced by an enterprise identity-provider adapter after Shreya confirms the deployment identity setup; this local bearer adapter is not a claim of an Azure/Entra integration.

Server-side environment variables:

| Variable | Default / purpose |
| --- | --- |
| SAATHI_AGENT_CREDENTIALS_FILE | Required private credential configuration; no default token |
| RADAR_INPUT_FILE | data/radar_input.json, or an explicit path to Sachi's six-column export |
| RADAR_CUSTOMERS_FILE | data/customers.json, or an explicit approved CRM customer file |

CRM files can be a customer array or an object containing a customers array. Input and access files are reread per request, so consent and ownership changes are not cached by the gate. The operator must use CRM/features from the same approved snapshot; the existing six-column feature format does not independently carry an as-of date.

## Scoring boundary

The allowed rows retain exactly customer_id, days_to_renewal, interaction_count_90d, sentiment_score, annual_premium_inr, consent. Policy metadata, agent IDs and credentials are never sent to the model or Azure endpoint. An empty candidate set returns items=[] without invoking any scorer. Missing/invalid CRM input returns 503 rather than falling back to training fixtures. The ML adapter repeats consent checks and validates Azure result IDs and scores.

The standalone ml.score_crm command and lower-level ml.radar.score_rows remain technical synthetic compatibility tools. They do not authenticate users or produce an approved application worklist. Human approval and consent must still be checked again before a simulated send. This change protects /worklist only; authentication/authorization on chat, drafts, summaries, sessions and audit endpoints is separate unfinished application work.

## Verification

67 tests passed locally across access-gate checks, API integration, summaries, audit and the prior Radar v2 contract suite. Focused tests cover authentication and token revocation, spoofed agent IDs, cross-agent/customer and product isolation, current CRM consent overriding stale feature consent, all policy statuses, missing/invalid metadata, duplicate records, signed overdue days, no training-data fallback, no model invocation for blocked/empty inputs, and filtering before a mocked Azure HTTP call. Synthetic policy cases use separate T-/DEMO- IDs; Sachi's fixtures are not assigned unconfirmed statuses.

Run from the repository root after installing dependencies:

```bash
PYTHONPATH=.:api python -m pytest api/tests/test_worklist_access.py api/tests/test_chat_ml_integration.py api/tests/test_summary.py api/tests/test_Audit.py tests/test_radar_contract_v2.py -q
```

These are focused tests with mocked classifier/retrieval dependencies and mocked Azure HTTP calls, not a live Azure or full-application acceptance result.
