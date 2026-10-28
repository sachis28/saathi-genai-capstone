# Synthetic Demo Scenarios

All records are synthetic. These scenarios are implementation choices,
not prescribed business rules.

## Generation settings

- Random seed: 42
- Fixed reference date: 2026-10-28
- Customers: 6
- Interactions: 3 per customer, 18 total
- All customers have product Health and segment Retail.
- Renewal offsets are relative to the fixed reference date, not today.

## Customer scenarios

| Customer ID | Tier | Consent | Renewal date | Demo story |
|---|---|---|---|---|
| C-204 | Silver | true | 2026-11-12 | Customer asks about coverage and wants help renewing. |
| C-311 | Gold | true | 2026-11-04 | Renewal is approaching and the customer requests details. |
| C-118 | Silver | true | 2026-12-27 | Customer explores policy upgrades before renewal. |
| C-450 | Gold | true | 2026-10-23 | Customer has missed the renewal date and requests agent follow-up. |
| C-205 | Gold | false | 2026-11-17 | Customer explicitly declines outbound messages, supporting the consent-blocking demo. |
| C-999 | Silver | true | 2027-01-26 | Customer requests a policy overview and agent contact guidance. |

## Integration notes

- C-204 preserves the existing API's Health/Silver configuration.
- C-205 preserves the existing API's Health/Gold/no-consent configuration.
- The existing API test expects C-999 to return 404.
  Once the API loads this dataset, that test must use a genuinely absent ID.
- Generating these files does not make the API load them automatically.
- No real messages are sent by this generator.
