# Data Dictionary

This document describes the current synthetic demo dataset.
Field definitions reflect the implemented schema and handoff breakdown,
not an exact schema prescribed by the execution plan.

## Dataset structure

- customers.json: JSON array of customer records.
- interactions.json: JSON array of interaction records.
- All fields below are required by data/schemas.py.
- All names and interaction messages are synthetic.

## Customer fields

| Field | JSON type | Example | Meaning |
|---|---|---|---|
| customer_id | string | C-204 | Unique customer identifier. |
| name | string | Synthetic Customer 01 | Synthetic display name. |
| product | string | Health | Policy product. |
| tier | string | Silver | Policy tier. |
| city | string | Pune | Customer city. |
| segment | string | Retail | Customer segment. |
| consent | boolean | true | Consent flag checked before outbound sending. |
| agent_id | string | A-001 | Assigned agent identifier. |
| renewal_date | string, YYYY-MM-DD | 2026-11-12 | Policy renewal date. |

## Interaction fields

| Field | JSON type | Example | Meaning |
|---|---|---|---|
| interaction_id | string | I-0001 | Unique interaction identifier, available for summary citations. |
| customer_id | string | C-204 | Links the interaction to a customer. |
| date | string, YYYY-MM-DD | 2026-10-01 | Interaction date. |
| channel | string | email | Communication channel. |
| text | string | Please explain my policy. | Synthetic interaction message. |

Examples illustrate field formats; they are not necessarily complete
records copied from the generated files.

## Current demo values

- Product: Health.
- Tiers: Silver and Gold.
- Segment: Retail.
- Channels: phone, email, chat.
- Customer IDs: C-204, C-311, C-118, C-450, C-205, C-999.
- C-205 has consent=false.
- These are generator choices, not schema-enforced enumerations.

## Validation

### Schema validation

- Dates are parsed as Python date values and serialized as YYYY-MM-DD.
- Consent uses StrictBool and must be an actual boolean.
- The schema does not enforce ID patterns or allowed string values.

### Generator checks

- Customer IDs must be unique.
- Interaction IDs must be unique.
- Every interaction must reference a generated customer.

## Reproducibility

- Seed: 42.
- Fixed reference date: 2026-10-28.
- Current size: 6 customers and 18 interactions.
- Renewal offsets use the fixed reference date, not the execution date.
- Identical output was verified across two consecutive runs.

## Scope and integration

- Premium, claims, sentiment, and Radar features are not included yet.
- The generator writes data files only; API loading is a separate step.
- The current API Customer model exposes only customer_id, name,
  product, tier, and consent.
- The existing missing-customer test uses C-999. That test needs an
  absent ID when the API is integrated with this dataset.

## Renewal Radar features

Generated file: data/radar_features.json.
One row per customer. These are model inputs, not predictions or risk scores.

| Field | JSON type | Meaning |
|---|---|---|
| customer_id | string | Customer identifier linking to customers.json. |
| as_of_date | string, YYYY-MM-DD | Explicit reference date for feature calculations. |
| days_to_renewal | integer | Renewal date minus reference date; negative means overdue. |
| interaction_count | integer | Number of interactions on or before the reference date. |
| days_since_last_interaction | integer or null | Days since the latest eligible interaction; null if none exists. |

### Generate features

From the repository root:

```bash
python3 ml/radar_features.py --as-of 2026-10-28
```

Future-dated interactions are excluded.
Premium, claims, and sentiment features are not implemented yet.

### Checks performed

- Six feature rows with expected renewal offsets.
- Three eligible interactions per demo customer.
- Customers without history return count zero and recency null.
- Future interactions are excluded.
- Renewal on the reference date gives zero days to renewal.
