# Azure Cost Report — Saathi Insurance Agent Copilot

## 1. Project Overview

**Project:** Saathi Insurance Agent Copilot  
**Purpose:** Demonstrate a Retrieval-Augmented Generation (RAG) system for retrieving relevant insurance information from a synthetic insurance corpus.

This report documents the Azure services used, their purpose, cost considerations, and resource cleanup procedures.

**Important:** This is an educational capstone using synthetic insurance data. The system is not intended for production insurance advice.

## 2. Azure Resources Used

| Azure Resource | Purpose | Usage in Project |
|---|---|---|
| Azure Resource Group | Organizes Azure resources | `Saathi_rg` |
| Azure AI Search | Stores and retrieves insurance clauses | Vector, hybrid, and semantic hybrid search |
| Azure OpenAI | Generates embeddings | `text-embedding-3-small` deployment |
| Azure Blob Storage | Stores source documents | PDF ingestion demonstration |
| Azure AI Search Indexer | Automates document ingestion | Processes the PDF source |
| Azure AI Search Skillset | Enriches and processes documents | PDF processing and chunk extraction |

The PDF ingestion demonstration used a separate index:

- **Demo index:** `saathi-pdf-demo`
- **Indexer:** `saathi-pdf-demo-indexer`
- **Skillset:** `saathi-pdf-demo-skillset`

The canonical insurance index was kept separate from the PDF ingestion demonstration.

## 3. Cost Components

### Azure AI Search
Potential cost factors:
- Search service SKU and provisioned capacity
- Service uptime
- Indexing and query activity
- Additional replicas or partitions, if configured

### Azure OpenAI
Potential cost factors:
- Embedding model usage
- Number of input tokens processed
- Repeated embedding generation during experimentation

The project uses the `text-embedding-3-small` deployment with 1536-dimensional embeddings.

### Azure Blob Storage
Potential cost factors:
- Storage capacity
- Data redundancy configuration
- Transactions and operations
- Data transfer

### Azure AI Search Indexer and Skillset
Potential cost factors:
- Indexer execution
- Document processing
- OCR or enrichment operations, depending on configured skills and applicable billing

## 4. Actual Cost Measurement

**Actual Azure spending has not yet been verified in this report.**

Do not treat estimated or assumed prices as actual charges.

To obtain actual cost information:

1. Open the Azure Portal.
2. Navigate to **Cost Management + Billing**.
3. Open **Cost Analysis**.
4. Select the relevant billing scope or subscription.
5. Set the date range to cover the project activity.
6. Filter by resource group `Saathi_rg`, where available.
7. Review costs for Azure AI Search, Azure OpenAI, and Storage.
8. Record the currency, date range, and actual amounts below.

| Service | Actual Cost | Currency | Measurement Period |
|---|---|---|---|
| Azure AI Search | Not yet verified | — | — |
| Azure OpenAI | Not yet verified | — | — |
| Azure Blob Storage | Not yet verified | — | — |
| Indexer / Skillset processing | Not yet verified separately | — | — |
| **Total** | **Not yet verified** | — | — |

**Billing note:** Some Azure charges may appear at the subscription or billing scope rather than as a separate line item for every component. Indexer and skillset costs may be included in related service charges or depend on the specific services used.

## 5. Cost Optimization

The following practices help control project costs:

- Use synthetic data and a small corpus for demonstrations.
- Avoid unnecessary repeated embedding generation.
- Keep Azure resources running only when needed.
- Avoid scaling search replicas or partitions without a clear requirement.
- Monitor usage through Azure Cost Management.
- Remove temporary demonstration resources after the team demo.
- Keep the canonical search index separate from temporary experiments.
- Avoid storing unnecessary duplicate documents.

## 6. Resource Cleanup and Teardown

**Do not delete Azure resources before the final team demo and approval.**

After the demo is complete:

1. Confirm with the team that Azure resources are no longer required.
2. Check whether any teammate is using the shared resource group.
3. Save required screenshots, evaluation reports, and demo evidence.
4. Confirm that no required data or configuration is stored only in Azure.
5. Review resources in `Saathi_rg`.
6. Remove temporary PDF demo resources if they are no longer required.
7. Delete remaining project resources only after team approval.
8. Verify that the resources have been removed.
9. Check Cost Management later for any remaining charges.

Deleting resources may not immediately eliminate all charges already incurred.

## 7. Limitations

- Actual Azure spending depends on subscription type, region, service SKU, usage, and billing configuration.
- Azure pricing and free-tier eligibility can change.
- Cost estimates are not equivalent to actual billing records.
- This project uses a small synthetic dataset and is not a production-scale cost benchmark.

## 8. Conclusion

The Saathi Insurance Agent Copilot demonstrates Azure-based document ingestion and retrieval using Azure AI Search, Azure OpenAI embeddings, and Blob Storage.

Cost monitoring and resource cleanup are important for controlling expenses during experimentation and ensuring that temporary Azure resources are not left running after the capstone demonstration.

Actual spending should be added from Azure Cost Management before presenting this report as a final cost analysis.
