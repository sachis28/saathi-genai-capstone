# Local BM25 Retrieval Evaluation

## Evaluation Configuration

- Corpus records: 48
- Evaluation questions: 30
- Retrieval method: Local BM25
- Top-K: 5
- Filtering: Product and tier metadata when available

## Overall Results

| Metric | Score |
|---|---:|
| Recall@5 | 0.9333 |
| MRR | 0.8400 |

## Question-Level Results

| Question | Expected IDs | Retrieved IDs | Recall@5 | Reciprocal Rank |
|---|---|---|---:|---:|
| What is the hospitalization coverage limit under Health Silver? | CL-COV-01 | CL-WAIT-02, CL-EXC-04, CL-WAIT-05, CL-ROOM-06, CL-COV-01 | 1.00 | 0.20 |
| How much room rent can I claim under Health Silver? | CL-ROOM-06, CL-COV-01 | CL-RENEW-10, CL-ROOM-06, CL-NCB-09, CL-COV-01, CL-WAIT-05 | 1.00 | 0.50 |
| What is the waiting period for pre-existing diseases in Health Silver? | CL-WAIT-02 | CL-WAIT-02, CL-WAIT-05, CL-COV-01, CL-PRE-08, CL-ROOM-06 | 1.00 | 1.00 |
| Which documents are required for Health Silver reimbursement claims? | CL-CLAIM-03 | CL-CLAIM-03, CL-ROOM-06, CL-PRE-08, CL-NCB-09, CL-EXC-04 | 1.00 | 1.00 |
| Does Health Silver cover cosmetic procedures? | CL-EXC-04 | CL-EXC-04, CL-CLAIM-03, CL-RENEW-10, CL-WAIT-05, CL-WAIT-02 | 1.00 | 1.00 |
| What is the emergency ambulance limit under Health Silver? | CL-AMB-07 | CL-AMB-07, CL-WAIT-05, CL-WAIT-02, CL-ROOM-06, CL-COV-01 | 1.00 | 1.00 |
| How many days of pre and post hospitalization expenses are covered under Silver? | CL-PRE-08 | CL-PRE-08, CL-WAIT-02, CL-AMB-07, CL-CLAIM-03, CL-WAIT-05 | 1.00 | 1.00 |
| How does the no claim bonus work under Health Silver? | CL-NCB-09 | CL-NCB-09, CL-WAIT-05, CL-WAIT-02, CL-EXC-04, CL-CLAIM-03 | 1.00 | 1.00 |
| What is the annual renewal condition for Health Silver? | CL-RENEW-10 | CL-RENEW-10, CL-ROOM-06, CL-COV-01, CL-NCB-09, CL-PRE-08 | 1.00 | 1.00 |
| What is the waiting period for pre-existing diseases under Health Gold? | CL-WAIT-02 | CL-WAIT-02, CL-MAT-12, CL-RENEW-11, CL-PRE-05, EXC-GOLD-07 | 1.00 | 1.00 |
| What is the hospitalization coverage limit under Health Gold? | CL-COV-01 | CL-WAIT-02, EXC-GOLD-07, CL-CLAIM-03, CL-RENEW-11, CL-EXC-08 | 0.00 | 0.00 |
| Does Health Gold have a room rent limit? | CL-COV-01 | CL-COV-01, CL-CLAIM-03, CL-RENEW-11, CL-WAIT-02, CL-DAY-09 | 1.00 | 1.00 |
| What documents are needed for Health Gold reimbursement claims? | CL-CLAIM-03 | CL-CLAIM-03, CL-RENEW-11, EXC-GOLD-07, CL-PRE-05, CL-POST-06 | 1.00 | 1.00 |
| What is the ambulance coverage limit under Health Gold? | CL-AMB-04 | CL-WAIT-02, CL-AMB-04, EXC-GOLD-07, CL-CLAIM-03, CL-RENEW-11 | 1.00 | 0.50 |
| How long are pre hospitalization expenses covered under Gold? | CL-PRE-05 | CL-PRE-05, CL-WAIT-02, CL-POST-06, CL-AMB-04, EXC-GOLD-07 | 1.00 | 1.00 |
| How long are post hospitalization expenses covered under Gold? | CL-POST-06 | CL-POST-06, CL-PRE-05, CL-AMB-04, CL-WAIT-02, EXC-GOLD-07 | 1.00 | 1.00 |
| Are experimental treatments covered under Health Gold? | CL-EXC-08 | CL-EXC-08, CL-RENEW-11, CL-WAIT-02, CL-CLAIM-03, EXC-GOLD-07 | 1.00 | 1.00 |
| Are day-care procedures covered under Health Gold? | CL-DAY-09, CL-COV-01 | CL-DAY-09, CL-COV-01, CL-RENEW-11, CL-WAIT-02, CL-CLAIM-03 | 1.00 | 1.00 |
| What is the no claim bonus under Health Gold? | CL-NCB-10 | CL-NCB-10, CL-WAIT-02, EXC-GOLD-07, CL-CLAIM-03, CL-RENEW-11 | 1.00 | 1.00 |
| What is the maternity coverage condition under Health Gold? | CL-MAT-12 | CL-WAIT-02, CL-MAT-12, EXC-GOLD-07, CL-CLAIM-03, CL-RENEW-11 | 1.00 | 0.50 |
| What is the hospitalization limit under Health Platinum? | CL-COV-01 | CL-EXC-06, CL-DAY-07, CL-INT-10, CL-POST-05, CL-AMB-03 | 0.00 | 0.00 |
| What is the ambulance expense limit under Platinum? | CL-AMB-03 | CL-AMB-03, CL-EXC-06, CL-DAY-07, CL-INT-10, CL-RENEW-09 | 1.00 | 1.00 |
| How long are pre hospitalization expenses covered under Platinum? | CL-PRE-04 | CL-PRE-04, CL-POST-05, CL-AMB-03, CL-DAY-07, CL-INT-10 | 1.00 | 1.00 |
| Does Platinum provide international second medical opinions? | CL-INT-10, CL-COV-01 | CL-INT-10, CL-COV-01, CL-CLAIM-02, CL-AMB-03, CL-PRE-04 | 1.00 | 1.00 |
| What is the no claim bonus under Platinum? | CL-NCB-08 | CL-NCB-08, CL-EXC-06, CL-DAY-07, CL-INT-10, CL-COV-01 | 1.00 | 1.00 |
| Does Motor Gold include zero depreciation? | CL-COV-01 | CL-COV-01, CL-RENEW-07, CL-CLAIM-02, CL-ROADSIDE-03, CL-EXC-04 | 1.00 | 1.00 |
| What documents are required for a motor accident claim? | CL-CLAIM-02 | CL-THEFT-05, CL-CLAIM-02, CL-COV-01, CL-ROADSIDE-03, CL-EXC-04 | 1.00 | 0.50 |
| Is roadside assistance available under Motor Gold? | CL-ROADSIDE-03, CL-COV-01 | CL-ROADSIDE-03, CL-COV-01, CL-EXC-04, CL-RENEW-07, CL-DAMAGE-06 | 1.00 | 1.00 |
| What happens if a driver is under the influence of alcohol? | CL-EXC-04 | CL-EXC-04, CL-THEFT-05, CL-ROADSIDE-03, CL-DAMAGE-06, CL-INSPECT-08 | 1.00 | 1.00 |
| What is the policy renewal grace period? | CL-REN-01 | CL-REN-01, CL-REN-03, CL-REN-02, CL-PREM-01, CL-CLAIM-02 | 1.00 | 1.00 |

## Interpretation and Limitations

- BM25 is a lexical retrieval baseline based on term matching and term frequency.
- BM25 does not use semantic embeddings.
- Results are based on a small synthetic insurance corpus and evaluation set.
- These results should not be interpreted as production insurance retrieval accuracy.
