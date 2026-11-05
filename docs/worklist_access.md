# CRM worklist access contract

The agreed follow-up contract supersedes the earlier lowercase-status and consent-filter behavior. GET /worklist authenticates an agent, checks original CRM ownership and approved product scope, then applies centralized renewal eligibility before local/Azure scoring. No-consent customers remain visible; consent is enforced before outbound send.

## Central policy rules

api/app/services/customers.py calculates ACTIVE for days>=0, IN_GRACE for -30<=days<0, LAPSED for days<-30, and CANCELLED only from an explicit cancelled flag/state. ACTIVE/IN_GRACE are eligible. LAPSED has reason LAPSED_BEYOND_GRACE; CANCELLED has reason CANCELLED. Missing renewal dates are ineligible. Data generators retain dates/explicit cancellation, not calculated status logic.

SAATHI_AS_OF_DATE pins the reference day (2026-10-28 for this demo); absent it uses current UTC date. Feature days must match the central CRM calculation, including C-450=-5. The gate does not clamp negative days or use consent as a visibility filter. No raw client agent_id can override the authenticated identity. One policy/product per customer is assumed; multi-policy support needs a policy_id contract.

## Authentication and files

The replaceable local bearer adapter authenticates tokens against server-owned SHA-256 digests, exact agent IDs and nonempty allowed_products. File changes take effect on the next request. Never grant products from an untrusted header/query. Missing credentials return 401; missing/malformed credential configuration returns 503. No actual credentials or Shreya-approved product mapping were supplied for this run.

| Variable | Purpose |
| --- | --- |
| SAATHI_AGENT_CREDENTIALS_FILE | Private array of agent_id, allowed_products and token_sha256 entries; no default account/token/grants |
| RADAR_INPUT_FILE | Defaults to data/radar_input.json; never falls back to training rows through the API |
| RADAR_CUSTOMERS_FILE | Defaults to data/customers.json; server-side current customer metadata |
| SAATHI_AS_OF_DATE | Explicit demo day or current UTC day if unset |

Keep credential files outside Git, restrict file permissions and use long random tokens over HTTPS outside local loopback development. Production identity-provider integration is still Shreya's dependency. Tests use labelled controlled scopes, not a claimed approved deployment mapping.

Only the six-field Radar payload reaches scoring. Credentials, agent IDs and eligibility fields are excluded. Empty permitted sets do not invoke a model. Missing/malformed/stale CRM input returns 503. Model responses must refer only to submitted IDs and finite scores in [0,1].

## Verification boundaries

The follow-up suite executes real local model scoring for the six CRM-linked fixtures, central eligibility and ownership checks, protected API calls with test-only identity scopes, summary mock calls and draft approval/consent gates. Azure HTTP parity tests are mocks; no live Azure evidence is claimed. Technical real-model evidence is docs/evidence/sachi_followup_radar.json. Full deployment/product access, live Foundry summarization, UI testing and authorization of chat/draft/session/audit routes remain pending. main.py is unchanged in this follow-up.
