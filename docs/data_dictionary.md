# Saathi data dictionary

This branch integrates Sachi's completed seed-42 CRM, sentiment and annual-premium exports from commit 180f69a. Six customers and 18 interactions are synthetic demo/inference fixtures, never training rows. The reproducible demo reference date is 2026-10-28.

## CRM and centralized policy metadata

| Field | Definition |
| --- | --- |
| customer_id | Unique original CRM ID; preserved through inference |
| agent_id | Existing assigned agent from Sachi's CRM; not a client-supplied identity |
| product / tier | Policy product and tier; product access requires Shreya's approved server-side mapping |
| consent | Strict boolean; controls outbound send, not scoring or worklist visibility |
| renewal_date | ISO date; signed renewal days are renewal_date minus the explicit reference date |
| annual_premium_inr | Positive finite current annual base premium in raw INR, excluding taxes/fees; monthly amounts must be annualized x12; never scaled to thousands |
| cancelled | Explicit synthetic/business boolean; omitted means false. Cancellation is never inferred from days overdue |
| policy_status | Calculated centrally in api/app/services/customers.py; not hard-coded as a calculated generator field |
| renewal_eligible | Calculated centrally; true for ACTIVE/IN_GRACE, false for LAPSED/CANCELLED |
| eligibility_reason | LAPSED_BEYOND_GRACE or CANCELLED for those exclusions; null for eligible rows; MISSING_RENEWAL_DATE when unavailable |

The API Customer model preserves agent_id, product, consent, renewal_date and premium. load_customers rereads records so send-time consent changes are not hidden by a permanent cache. authorize_customer checks the assigned agent; the worklist and summary also require the authenticated principal's explicit product scope.

| Days to renewal / explicit state | Status | Eligible |
| --- | --- | --- |
| >= 0 | ACTIVE | true |
| -30 through -1 inclusive | IN_GRACE | true |
| < -30 | LAPSED | false |
| Explicit cancelled=true or explicit CANCELLED state | CANCELLED | false |

Set SAATHI_AS_OF_DATE=2026-10-28 for the demo. If unset, central logic uses the current UTC date. Worklist features must match the central renewal-date snapshot; stale/mismatched days are rejected.

## Demo fixture changes

| Customer | Agent | Days | Status | Consent |
| --- | --- | --- | --- | --- |
| C-204 | A-001 | 15 | ACTIVE | true |
| C-311 | A-002 | 7 | ACTIVE | true |
| C-118 | A-003 | -31 | LAPSED | true |
| C-450 | A-001 | -5 | IN_GRACE | true |
| C-205 | A-002 | 20 | ACTIVE | false |
| C-999 | A-003 | 90 | CANCELLED | true |

To cover the requested statuses, C-118's synthetic renewal date changes from 2026-12-27 to 2026-09-27, and C-999 gets cancelled=true. No ownership, product, consent, premium, interaction text/date or sentiment results are changed. C-450 remains -5. The generator reproduces these explicit inputs; status calculation remains centralized. data/radar_features.json and data/radar_input.json are regenerated consistently. tests/fixtures/sachi_radar_input.json remains the historical unmodified export from 180f69a.

## Interactions and sentiment

InteractionRecord contains interaction_id, customer_id, date, channel and text. IDs are unique and reference existing customers. There are three interactions per customer. Existing interaction and saved service-sentiment bytes remain unchanged.

The 90-day window includes the reference day and previous 89 days, excluding future interactions. interaction_count_90d is the number of interactions in that window. Interaction sentiment is positive confidence minus negative confidence. Customer sentiment_score is its mean in the same window. No eligible history returns null, not neutral zero; the current Radar exporter rejects missing sentiment rather than imputing it.

Saved data/interaction_sentiment.json has 18 service results (13 neutral, 3 negative, 2 positive). Consistency/coverage checks are not an independent sentiment accuracy evaluation. data/customer_sentiment.json stores six scores and as_of_date. No service rerun is needed if interaction IDs, text and dates are unchanged.

## Radar input

The exact six fields in data/radar_input.json are customer_id, days_to_renewal, interaction_count_90d, sentiment_score, annual_premium_inr, consent. Model features are the middle four numeric fields only. Customer IDs, consent, policy metadata, agent IDs and outcome labels are not predictive features. Authorization and central eligibility apply before worklist/model inference. Consent does not remove customers from scoring or visibility; it must still block outbound send. Raw compatibility commands do not authenticate an agent or prove product authorization.

## Summary output

GET /customers/{customer_id}/summary returns customer_id, summary and interaction_ids. It uses the shared customer loader/ownership authorizer plus explicit product scopes. Full history is processed in batches of two. Current grounding is conservative extractive validation: every returned statement must exactly match a supplied interaction's text and cite that same interaction; every interaction in a batch must be covered, without trailing uncited claims. This deliberately rejects unsupported paraphrases and is not a general semantic-entailment model. Injection-like history/output is rejected. Ordinary tests use mock; real Azure gpt-4.1-mini remains a separate blocked check when credentials are absent.
