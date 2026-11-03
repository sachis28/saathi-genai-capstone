# Saathi - Retrieval Evaluation Report

Evaluation date: 2026-11-03 09:48
Total test questions: 30
Top K: 5

## Performance Comparison

| Retrieval Method | Recall@5 | MRR |
|---|---:|---:|
| Vector Search | 1.0000 | 1.0000 |
| Hybrid Search | 1.0000 | 0.9094 |
| Semantic Hybrid Search | 1.0000 | 1.0000 |

## Metric Explanation

- Recall@5 measures the proportion of expected relevant clauses retrieved in the top five results.
- MRR measures how highly the first relevant result is ranked.

## Detailed Results

### Vector Search

| Query | Expected Clauses | Retrieved Clauses | Recall@5 | MRR |
|---|---|---|---:|---:|
| What is the hospitalization coverage limit under Health Silver? | CL-COV-01 | CL-COV-01, CL-CLAIM-03, CL-WAIT-05, CL-WAIT-02, CL-EXC-04 | 1.00 | 1.00 |
| How much room rent can I claim under Health Silver? | CL-ROOM-06, CL-COV-01 | CL-COV-01, CL-CLAIM-03, CL-WAIT-05, CL-ROOM-06, CL-EXC-04 | 1.00 | 1.00 |
| What is the waiting period for pre-existing diseases in Health Silver? | CL-WAIT-02 | CL-WAIT-02, CL-WAIT-05, CL-EXC-04, CL-RENEW-10, CL-COV-01 | 1.00 | 1.00 |
| Which documents are required for Health Silver reimbursement claims? | CL-CLAIM-03 | CL-CLAIM-03, CL-WAIT-05, CL-EXC-04, CL-RENEW-10, CL-WAIT-02 | 1.00 | 1.00 |
| Does Health Silver cover cosmetic procedures? | CL-EXC-04 | CL-EXC-04, CL-WAIT-05, CL-CLAIM-03, CL-WAIT-02, CL-RENEW-10 | 1.00 | 1.00 |
| What is the emergency ambulance limit under Health Silver? | CL-AMB-07 | CL-AMB-07, CL-WAIT-05, CL-CLAIM-03, CL-COV-01, CL-EXC-04 | 1.00 | 1.00 |
| How many days of pre and post hospitalization expenses are covered under Silver? | CL-PRE-08 | CL-PRE-08, CL-COV-01, CL-CLAIM-03, CL-WAIT-02, CL-WAIT-05 | 1.00 | 1.00 |
| How does the no claim bonus work under Health Silver? | CL-NCB-09 | CL-NCB-09, CL-WAIT-05, CL-CLAIM-03, CL-EXC-04, CL-WAIT-02 | 1.00 | 1.00 |
| What is the annual renewal condition for Health Silver? | CL-RENEW-10 | CL-RENEW-10, CL-WAIT-05, CL-WAIT-02, CL-CLAIM-03, CL-EXC-04 | 1.00 | 1.00 |
| What is the waiting period for pre-existing diseases under Health Gold? | CL-WAIT-02 | CL-WAIT-02, CL-COV-01, CL-RENEW-11, CL-PRE-05, CL-CLAIM-03 | 1.00 | 1.00 |
| What is the hospitalization coverage limit under Health Gold? | CL-COV-01 | CL-COV-01, CL-CLAIM-03, CL-WAIT-02, CL-PRE-05, CL-POST-06 | 1.00 | 1.00 |
| Does Health Gold have a room rent limit? | CL-COV-01 | CL-COV-01, CL-RENEW-11, CL-CLAIM-03, CL-WAIT-02, CL-PRE-05 | 1.00 | 1.00 |
| What documents are needed for Health Gold reimbursement claims? | CL-CLAIM-03 | CL-CLAIM-03, CL-RENEW-11, CL-WAIT-02, CL-COV-01, EXC-GOLD-07 | 1.00 | 1.00 |
| What is the ambulance coverage limit under Health Gold? | CL-AMB-04 | CL-AMB-04, CL-COV-01, CL-WAIT-02, CL-RENEW-11, CL-CLAIM-03 | 1.00 | 1.00 |
| How long are pre hospitalization expenses covered under Gold? | CL-PRE-05 | CL-PRE-05, CL-COV-01, CL-POST-06, CL-WAIT-02, CL-AMB-04 | 1.00 | 1.00 |
| How long are post hospitalization expenses covered under Gold? | CL-POST-06 | CL-POST-06, CL-COV-01, CL-PRE-05, CL-WAIT-02, CL-CLAIM-03 | 1.00 | 1.00 |
| Are experimental treatments covered under Health Gold? | CL-EXC-08 | CL-EXC-08, EXC-GOLD-07, CL-RENEW-11, CL-WAIT-02, CL-CLAIM-03 | 1.00 | 1.00 |
| Are day-care procedures covered under Health Gold? | CL-DAY-09, CL-COV-01 | CL-DAY-09, CL-COV-01, CL-RENEW-11, CL-CLAIM-03, CL-WAIT-02 | 1.00 | 1.00 |
| What is the no claim bonus under Health Gold? | CL-NCB-10 | CL-NCB-10, CL-RENEW-11, CL-CLAIM-03, CL-WAIT-02, CL-COV-01 | 1.00 | 1.00 |
| What is the maternity coverage condition under Health Gold? | CL-MAT-12 | CL-MAT-12, CL-WAIT-02, CL-COV-01, CL-RENEW-11, CL-CLAIM-03 | 1.00 | 1.00 |
| What is the hospitalization limit under Health Platinum? | CL-COV-01 | CL-COV-01, CL-PRE-04, CL-POST-05, CL-CLAIM-02, CL-INT-10 | 1.00 | 1.00 |
| What is the ambulance expense limit under Platinum? | CL-AMB-03 | CL-AMB-03, CL-COV-01, CL-INT-10, CL-CLAIM-02, CL-DAY-07 | 1.00 | 1.00 |
| How long are pre hospitalization expenses covered under Platinum? | CL-PRE-04 | CL-PRE-04, CL-COV-01, CL-POST-05, CL-CLAIM-02, CL-DAY-07 | 1.00 | 1.00 |
| Does Platinum provide international second medical opinions? | CL-INT-10, CL-COV-01 | CL-INT-10, CL-COV-01, CL-CLAIM-02, CL-RENEW-09, CL-DAY-07 | 1.00 | 1.00 |
| What is the no claim bonus under Platinum? | CL-NCB-08 | CL-NCB-08, CL-CLAIM-02, CL-COV-01, CL-RENEW-09, CL-INT-10 | 1.00 | 1.00 |
| Does Motor Gold include zero depreciation? | CL-COV-01 | CL-COV-01, CL-RENEW-07, CL-DAMAGE-06, CL-CLAIM-02, CL-EXC-04 | 1.00 | 1.00 |
| What documents are required for a motor accident claim? | CL-CLAIM-02 | CL-CLAIM-02, CL-THEFT-05, CL-INSPECT-08, CL-DAMAGE-06, CL-COV-01 | 1.00 | 1.00 |
| Is roadside assistance available under Motor Gold? | CL-ROADSIDE-03, CL-COV-01 | CL-COV-01, CL-ROADSIDE-03, CL-RENEW-07, CL-DAMAGE-06, CL-CLAIM-02 | 1.00 | 1.00 |
| What happens if a driver is under the influence of alcohol? | CL-EXC-04 | CL-EXC-04, CL-INSPECT-08, CL-CLAIM-02, CL-DAMAGE-06, CL-THEFT-05 | 1.00 | 1.00 |
| What is the policy renewal grace period? | CL-REN-01 | CL-REN-01, CL-REN-03, CL-REN-02, CL-PREM-01, CL-DOC-01 | 1.00 | 1.00 |

### Hybrid Search

| Query | Expected Clauses | Retrieved Clauses | Recall@5 | MRR |
|---|---|---|---:|---:|
| What is the hospitalization coverage limit under Health Silver? | CL-COV-01 | CL-EXC-04, CL-CLAIM-03, CL-WAIT-02, CL-WAIT-05, CL-COV-01 | 1.00 | 0.20 |
| How much room rent can I claim under Health Silver? | CL-ROOM-06, CL-COV-01 | CL-COV-01, CL-WAIT-05, CL-CLAIM-03, CL-EXC-04, CL-ROOM-06 | 1.00 | 1.00 |
| What is the waiting period for pre-existing diseases in Health Silver? | CL-WAIT-02 | CL-WAIT-02, CL-WAIT-05, CL-EXC-04, CL-COV-01, CL-RENEW-10 | 1.00 | 1.00 |
| Which documents are required for Health Silver reimbursement claims? | CL-CLAIM-03 | CL-CLAIM-03, CL-EXC-04, CL-WAIT-05, CL-RENEW-10, CL-WAIT-02 | 1.00 | 1.00 |
| Does Health Silver cover cosmetic procedures? | CL-EXC-04 | CL-EXC-04, CL-CLAIM-03, CL-WAIT-05, CL-RENEW-10, CL-WAIT-02 | 1.00 | 1.00 |
| What is the emergency ambulance limit under Health Silver? | CL-AMB-07 | CL-AMB-07, CL-WAIT-05, CL-CLAIM-03, CL-EXC-04, CL-COV-01 | 1.00 | 1.00 |
| How many days of pre and post hospitalization expenses are covered under Silver? | CL-PRE-08 | CL-PRE-08, CL-WAIT-02, CL-COV-01, CL-CLAIM-03, CL-WAIT-05 | 1.00 | 1.00 |
| How does the no claim bonus work under Health Silver? | CL-NCB-09 | CL-NCB-09, CL-WAIT-05, CL-EXC-04, CL-CLAIM-03, CL-WAIT-02 | 1.00 | 1.00 |
| What is the annual renewal condition for Health Silver? | CL-RENEW-10 | CL-RENEW-10, CL-WAIT-05, CL-EXC-04, CL-CLAIM-03, CL-WAIT-02 | 1.00 | 1.00 |
| What is the waiting period for pre-existing diseases under Health Gold? | CL-WAIT-02 | CL-WAIT-02, CL-RENEW-11, CL-PRE-05, CL-CLAIM-03, CL-COV-01 | 1.00 | 1.00 |
| What is the hospitalization coverage limit under Health Gold? | CL-COV-01 | CL-WAIT-02, CL-CLAIM-03, CL-COV-01, CL-PRE-05, CL-POST-06 | 1.00 | 0.33 |
| Does Health Gold have a room rent limit? | CL-COV-01 | CL-COV-01, CL-CLAIM-03, CL-RENEW-11, CL-WAIT-02, CL-DAY-09 | 1.00 | 1.00 |
| What documents are needed for Health Gold reimbursement claims? | CL-CLAIM-03 | CL-CLAIM-03, CL-RENEW-11, EXC-GOLD-07, CL-WAIT-02, CL-COV-01 | 1.00 | 1.00 |
| What is the ambulance coverage limit under Health Gold? | CL-AMB-04 | CL-WAIT-02, CL-AMB-04, CL-CLAIM-03, CL-RENEW-11, CL-COV-01 | 1.00 | 0.50 |
| How long are pre hospitalization expenses covered under Gold? | CL-PRE-05 | CL-PRE-05, CL-WAIT-02, CL-POST-06, CL-AMB-04, CL-COV-01 | 1.00 | 1.00 |
| How long are post hospitalization expenses covered under Gold? | CL-POST-06 | CL-POST-06, CL-PRE-05, CL-WAIT-02, CL-COV-01, CL-CLAIM-03 | 1.00 | 1.00 |
| Are experimental treatments covered under Health Gold? | CL-EXC-08 | CL-EXC-08, CL-WAIT-02, CL-RENEW-11, EXC-GOLD-07, CL-CLAIM-03 | 1.00 | 1.00 |
| Are day-care procedures covered under Health Gold? | CL-DAY-09, CL-COV-01 | CL-DAY-09, CL-COV-01, CL-RENEW-11, CL-WAIT-02, CL-CLAIM-03 | 1.00 | 1.00 |
| What is the no claim bonus under Health Gold? | CL-NCB-10 | CL-NCB-10, CL-RENEW-11, CL-WAIT-02, CL-CLAIM-03, CL-COV-01 | 1.00 | 1.00 |
| What is the maternity coverage condition under Health Gold? | CL-MAT-12 | CL-MAT-12, CL-WAIT-02, CL-CLAIM-03, CL-RENEW-11, CL-COV-01 | 1.00 | 1.00 |
| What is the hospitalization limit under Health Platinum? | CL-COV-01 | CL-INT-10, CL-POST-05, CL-CLAIM-02, CL-COV-01, CL-PRE-04 | 1.00 | 0.25 |
| What is the ambulance expense limit under Platinum? | CL-AMB-03 | CL-AMB-03, CL-INT-10, CL-DAY-07, CL-COV-01, CL-CLAIM-02 | 1.00 | 1.00 |
| How long are pre hospitalization expenses covered under Platinum? | CL-PRE-04 | CL-PRE-04, CL-POST-05, CL-DAY-07, CL-COV-01, CL-CLAIM-02 | 1.00 | 1.00 |
| Does Platinum provide international second medical opinions? | CL-INT-10, CL-COV-01 | CL-INT-10, CL-COV-01, CL-CLAIM-02, CL-DAY-07, CL-RENEW-09 | 1.00 | 1.00 |
| What is the no claim bonus under Platinum? | CL-NCB-08 | CL-NCB-08, CL-COV-01, CL-CLAIM-02, CL-INT-10, CL-RENEW-09 | 1.00 | 1.00 |
| Does Motor Gold include zero depreciation? | CL-COV-01 | CL-COV-01, CL-RENEW-07, CL-CLAIM-02, CL-EXC-04, CL-DAMAGE-06 | 1.00 | 1.00 |
| What documents are required for a motor accident claim? | CL-CLAIM-02 | CL-CLAIM-02, CL-THEFT-05, CL-COV-01, CL-INSPECT-08, CL-DAMAGE-06 | 1.00 | 1.00 |
| Is roadside assistance available under Motor Gold? | CL-ROADSIDE-03, CL-COV-01 | CL-COV-01, CL-ROADSIDE-03, CL-RENEW-07, CL-DAMAGE-06, CL-CLAIM-02 | 1.00 | 1.00 |
| What happens if a driver is under the influence of alcohol? | CL-EXC-04 | CL-EXC-04, CL-INSPECT-08, CL-DAMAGE-06, CL-THEFT-05, CL-ROADSIDE-03 | 1.00 | 1.00 |
| What is the policy renewal grace period? | CL-REN-01 | CL-REN-01, CL-REN-03, CL-REN-02, CL-PREM-01, CL-DOC-01 | 1.00 | 1.00 |

### Semantic Hybrid Search

| Query | Expected Clauses | Retrieved Clauses | Recall@5 | MRR |
|---|---|---|---:|---:|
| What is the hospitalization coverage limit under Health Silver? | CL-COV-01 | CL-COV-01, CL-PRE-08, CL-AMB-07, CL-WAIT-02, CL-CLAIM-03 | 1.00 | 1.00 |
| How much room rent can I claim under Health Silver? | CL-ROOM-06, CL-COV-01 | CL-COV-01, CL-ROOM-06, CL-NCB-09, CL-WAIT-05, CL-WAIT-02 | 1.00 | 1.00 |
| What is the waiting period for pre-existing diseases in Health Silver? | CL-WAIT-02 | CL-WAIT-02, CL-WAIT-05, CL-PRE-08, CL-RENEW-10, CL-COV-01 | 1.00 | 1.00 |
| Which documents are required for Health Silver reimbursement claims? | CL-CLAIM-03 | CL-CLAIM-03, CL-WAIT-05, CL-RENEW-10, CL-COV-01, CL-WAIT-02 | 1.00 | 1.00 |
| Does Health Silver cover cosmetic procedures? | CL-EXC-04 | CL-EXC-04, CL-WAIT-05, CL-CLAIM-03, CL-RENEW-10, CL-WAIT-02 | 1.00 | 1.00 |
| What is the emergency ambulance limit under Health Silver? | CL-AMB-07 | CL-AMB-07, CL-WAIT-05, CL-COV-01, CL-WAIT-02, CL-CLAIM-03 | 1.00 | 1.00 |
| How many days of pre and post hospitalization expenses are covered under Silver? | CL-PRE-08 | CL-PRE-08, CL-COV-01, CL-WAIT-02, CL-WAIT-05, CL-CLAIM-03 | 1.00 | 1.00 |
| How does the no claim bonus work under Health Silver? | CL-NCB-09 | CL-NCB-09, CL-WAIT-05, CL-CLAIM-03, CL-WAIT-02, CL-COV-01 | 1.00 | 1.00 |
| What is the annual renewal condition for Health Silver? | CL-RENEW-10 | CL-RENEW-10, CL-COV-01, CL-WAIT-05, CL-WAIT-02, CL-NCB-09 | 1.00 | 1.00 |
| What is the waiting period for pre-existing diseases under Health Gold? | CL-WAIT-02 | CL-WAIT-02, CL-PRE-05, CL-RENEW-11, CL-COV-01, CL-MAT-12 | 1.00 | 1.00 |
| What is the hospitalization coverage limit under Health Gold? | CL-COV-01 | CL-COV-01, CL-AMB-04, CL-PRE-05, CL-POST-06, CL-WAIT-02 | 1.00 | 1.00 |
| Does Health Gold have a room rent limit? | CL-COV-01 | CL-COV-01, CL-RENEW-11, CL-DAY-09, CL-CLAIM-03, EXC-GOLD-07 | 1.00 | 1.00 |
| What documents are needed for Health Gold reimbursement claims? | CL-CLAIM-03 | CL-CLAIM-03, CL-RENEW-11, CL-COV-01, CL-WAIT-02, EXC-GOLD-07 | 1.00 | 1.00 |
| What is the ambulance coverage limit under Health Gold? | CL-AMB-04 | CL-AMB-04, CL-COV-01, CL-WAIT-02, CL-NCB-10, CL-RENEW-11 | 1.00 | 1.00 |
| How long are pre hospitalization expenses covered under Gold? | CL-PRE-05 | CL-PRE-05, CL-WAIT-02, CL-COV-01, CL-DAY-09, CL-POST-06 | 1.00 | 1.00 |
| How long are post hospitalization expenses covered under Gold? | CL-POST-06 | CL-POST-06, CL-WAIT-02, CL-COV-01, CL-PRE-05, CL-DAY-09 | 1.00 | 1.00 |
| Are experimental treatments covered under Health Gold? | CL-EXC-08 | CL-EXC-08, EXC-GOLD-07, CL-WAIT-02, CL-COV-01, CL-CLAIM-03 | 1.00 | 1.00 |
| Are day-care procedures covered under Health Gold? | CL-DAY-09, CL-COV-01 | CL-COV-01, CL-DAY-09, CL-WAIT-02, CL-CLAIM-03, CL-RENEW-11 | 1.00 | 1.00 |
| What is the no claim bonus under Health Gold? | CL-NCB-10 | CL-NCB-10, CL-COV-01, EXC-GOLD-07, CL-RENEW-11, CL-WAIT-02 | 1.00 | 1.00 |
| What is the maternity coverage condition under Health Gold? | CL-MAT-12 | CL-MAT-12, CL-WAIT-02, CL-RENEW-11, CL-COV-01, CL-CLAIM-03 | 1.00 | 1.00 |
| What is the hospitalization limit under Health Platinum? | CL-COV-01 | CL-COV-01, CL-AMB-03, CL-PRE-04, CL-POST-05, CL-DAY-07 | 1.00 | 1.00 |
| What is the ambulance expense limit under Platinum? | CL-AMB-03 | CL-AMB-03, CL-COV-01, CL-NCB-08, CL-DAY-07, CL-CLAIM-02 | 1.00 | 1.00 |
| How long are pre hospitalization expenses covered under Platinum? | CL-PRE-04 | CL-PRE-04, CL-COV-01, CL-AMB-03, CL-POST-05, CL-DAY-07 | 1.00 | 1.00 |
| Does Platinum provide international second medical opinions? | CL-INT-10, CL-COV-01 | CL-INT-10, CL-COV-01, CL-CLAIM-02, CL-DAY-07, CL-RENEW-09 | 1.00 | 1.00 |
| What is the no claim bonus under Platinum? | CL-NCB-08 | CL-NCB-08, CL-COV-01, CL-DAY-07, CL-INT-10, CL-CLAIM-02 | 1.00 | 1.00 |
| Does Motor Gold include zero depreciation? | CL-COV-01 | CL-COV-01, CL-RENEW-07, CL-DAMAGE-06, CL-EXC-04, CL-CLAIM-02 | 1.00 | 1.00 |
| What documents are required for a motor accident claim? | CL-CLAIM-02 | CL-CLAIM-02, CL-THEFT-05, CL-INSPECT-08, CL-DAMAGE-06, CL-COV-01 | 1.00 | 1.00 |
| Is roadside assistance available under Motor Gold? | CL-ROADSIDE-03, CL-COV-01 | CL-COV-01, CL-ROADSIDE-03, CL-RENEW-07, CL-EXC-04, CL-CLAIM-02 | 1.00 | 1.00 |
| What happens if a driver is under the influence of alcohol? | CL-EXC-04 | CL-EXC-04, CL-INSPECT-08, CL-DAMAGE-06, CL-ROADSIDE-03, CL-THEFT-05 | 1.00 | 1.00 |
| What is the policy renewal grace period? | CL-REN-01 | CL-REN-01, CL-REN-03, CL-REN-02, CL-DOC-01, CL-PREM-01 | 1.00 | 1.00 |

## Important Notes

- The evaluation uses a synthetic educational insurance corpus.
- Retrieval results are evaluated against manually defined expected clause IDs.
- Recall@5 and MRR measure retrieval quality, not the factual accuracy of generated answers.
- Semantic Hybrid Search uses the configured Azure AI Search semantic configuration.


## Local vs Azure Retrieval Comparison

### Evaluation Setup

- Corpus: 48 synthetic insurance clauses
- Evaluation dataset: 30 retrieval gold-set questions
- Evaluation metric: Recall@5 and Mean Reciprocal Rank (MRR)
- Local baseline: BM25 lexical retrieval
- Azure methods: Vector Search, Hybrid Search, and Semantic Hybrid Search

### Results

| Retrieval Method | Recall@5 | MRR |
|---|---:|---:|
| Local BM25 | 0.9333 | 0.8400 |
| Azure Vector Search | 1.0000 | 1.0000 |
| Azure Hybrid Search | 1.0000 | 0.9094 |
| Azure Semantic Hybrid Search | 1.0000 | 1.0000 |

### Analysis

Local BM25 achieved 93.33% Recall@5 and 0.8400 MRR on the
30-question synthetic evaluation dataset.

Azure Vector Search achieved 100% Recall@5 and 1.0000 MRR.
Azure Hybrid Search achieved 100% Recall@5 and 0.9094 MRR.
Azure Semantic Hybrid Search achieved 100% Recall@5 and 1.0000 MRR.

BM25 uses lexical matching based on term frequency and document
statistics. Azure Vector Search uses semantic embeddings, while
Hybrid Search combines lexical and vector retrieval. Semantic Hybrid
Search additionally applies Azure AI Search's semantic ranking.

The results suggest that semantic retrieval and semantic ranking
can improve retrieval performance over the local lexical baseline
on this particular dataset.

### Limitations

- The corpus contains only 48 synthetic insurance clauses.
- The evaluation dataset contains only 30 questions.
- Results should not be interpreted as production-level retrieval accuracy.
- Performance may change with larger datasets, different queries,
  and more complex insurance documents.
- BM25 and Azure retrieval use different retrieval technologies,
  so these results demonstrate a comparison rather than a universal
  performance guarantee.
