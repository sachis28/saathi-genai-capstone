import os
import json
from pathlib import Path
from datetime import datetime

from openai import OpenAI

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery


# ==================================================
# CONFIGURATION
# ==================================================

BASE_DIR = Path(__file__).resolve().parent.parent

GOLD_SET_FILE = BASE_DIR / "corpus" / "retrieval_gold_set.jsonl"

REPORT_DIR = BASE_DIR.parent / "docs"
REPORT_FILE = REPORT_DIR / "retrieval_report.md"

SEARCH_ENDPOINT = os.environ["AZURE_SEARCH_ENDPOINT"]
SEARCH_KEY = os.environ["AZURE_SEARCH_ADMIN_KEY"]
INDEX_NAME = os.environ["AZURE_SEARCH_INDEX_NAME"]

OPENAI_ENDPOINT = os.environ["AZURE_OPENAI_ENDPOINT"].rstrip("/")
OPENAI_KEY = os.environ["AZURE_OPENAI_API_KEY"]

EMBEDDING_DEPLOYMENT = os.environ[
    "AZURE_OPENAI_EMBED_DEPLOYMENT"
]

TOP_K = 5


# ==================================================
# AZURE OPENAI CLIENT
# ==================================================

OPENAI_ENDPOINT = OPENAI_ENDPOINT.replace(
    "/openai/v1", ""
)

openai_client = OpenAI(
    base_url=f"{OPENAI_ENDPOINT}/openai/v1/",
    api_key=OPENAI_KEY
)


# ==================================================
# AZURE AI SEARCH CLIENT
# ==================================================

search_client = SearchClient(
    endpoint=SEARCH_ENDPOINT,
    index_name=INDEX_NAME,
    credential=AzureKeyCredential(SEARCH_KEY)
)


# ==================================================
# LOAD GOLD SET
# ==================================================

def load_gold_set():

    if not GOLD_SET_FILE.exists():
        raise FileNotFoundError(
            f"Gold set not found: {GOLD_SET_FILE}"
        )

    records = []

    with open(GOLD_SET_FILE, "r", encoding="utf-8") as file:

        for line in file:

            if line.strip():
                records.append(json.loads(line))

    print(f"Gold set questions loaded: {len(records)}")

    return records


# ==================================================
# GENERATE QUERY EMBEDDINGS
# ==================================================

def generate_query_embeddings(queries):

    print("\nGenerating query embeddings...")

    response = openai_client.embeddings.create(
        model=EMBEDDING_DEPLOYMENT,
        input=queries
    )

    embeddings = [
        item.embedding
        for item in sorted(
            response.data,
            key=lambda item: item.index
        )
    ]

    print(f"Query embeddings generated: {len(embeddings)}")

    return embeddings


# ==================================================
# METADATA FILTER
# ==================================================

def build_filter(question):

    product = question["product"]
    tier = question["tier"]

    return (
        f"product eq '{product}' and "
        f"tier eq '{tier}'"
    )


# ==================================================
# VECTOR SEARCH
# ==================================================

def vector_search(query, embedding, question):

    vector_query = VectorizedQuery(
        vector=embedding,
        k_nearest_neighbors=TOP_K,
        fields="embedding"
    )

    results = search_client.search(
        search_text=None,
        vector_queries=[vector_query],
        filter=build_filter(question),
        select=[
            "id",
            "source_id",
            "clause_id",
            "product",
            "tier",
            "text"
        ],
        top=TOP_K
    )

    return list(results)


# ==================================================
# HYBRID SEARCH
# ==================================================

def hybrid_search(query, embedding, question):

    vector_query = VectorizedQuery(
        vector=embedding,
        k_nearest_neighbors=TOP_K,
        fields="embedding"
    )

    results = search_client.search(
        search_text=query,
        vector_queries=[vector_query],
        filter=build_filter(question),
        select=[
            "id",
            "source_id",
            "clause_id",
            "product",
            "tier",
            "text"
        ],
        top=TOP_K
    )

    return list(results)


# ==================================================
# SEMANTIC HYBRID SEARCH
# ==================================================

def semantic_hybrid_search(query, embedding, question):

    vector_query = VectorizedQuery(
        vector=embedding,
        k_nearest_neighbors=TOP_K,
        fields="embedding"
    )

    results = search_client.search(
        search_text=query,
        vector_queries=[vector_query],
        filter=build_filter(question),
        query_type="semantic",
        semantic_configuration_name="insurance-semantic-config",
        select=[
            "id",
            "source_id",
            "clause_id",
            "product",
            "tier",
            "text"
        ],
        top=TOP_K
    )

    return list(results)


# ==================================================
# EVALUATION METRICS
# ==================================================

def evaluate_results(results, question):

    expected = set(
        (
            question["product"],
            question["tier"],
            clause_id
        )
        for clause_id in question["expected_clause_ids"]
    )

    retrieved = []

    for result in results:

        retrieved.append(
            (
                result["product"],
                result["tier"],
                result["clause_id"]
            )
        )

    retrieved_set = set(retrieved)

    relevant_found = expected.intersection(retrieved_set)

    recall = len(relevant_found) / len(expected)

    reciprocal_rank = 0.0

    for rank, document in enumerate(retrieved, start=1):

        if document in expected:

            reciprocal_rank = 1 / rank
            break

    return recall, reciprocal_rank, retrieved


# ==================================================
# EVALUATE RETRIEVAL METHOD
# ==================================================

def evaluate_method(
    method_name,
    questions,
    embeddings,
    search_function
):

    print(f"\nEvaluating {method_name}...")

    results = []

    for index, (question, embedding) in enumerate(
        zip(questions, embeddings),
        start=1
    ):

        retrieved_documents = search_function(
            question["query"],
            embedding,
            question
        )

        recall, mrr, retrieved = evaluate_results(
            retrieved_documents,
            question
        )

        results.append({

            "query": question["query"],

            "expected": question["expected_clause_ids"],

            "retrieved": [
                document[2]
                for document in retrieved
            ],

            "recall": recall,

            "mrr": mrr

        })

        print(
            f"Question {index}/{len(questions)} | "
            f"Recall@5: {recall:.2f} | "
            f"MRR: {mrr:.2f}"
        )

    average_recall = sum(
        item["recall"] for item in results
    ) / len(results)

    average_mrr = sum(
        item["mrr"] for item in results
    ) / len(results)

    return {
        "method": method_name,
        "average_recall": average_recall,
        "average_mrr": average_mrr,
        "details": results
    }


# ==================================================
# GENERATE MARKDOWN REPORT
# ==================================================

def generate_report(evaluation_results, total_questions):

    REPORT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    lines = [

        "# Saathi - Retrieval Evaluation Report",

        "",

        f"Evaluation date: {datetime.now().strftime('%Y-%m-%d %H:%M')}",

        f"Total test questions: {total_questions}",

        f"Top K: {TOP_K}",

        "",

        "## Performance Comparison",

        "",

        "| Retrieval Method | Recall@5 | MRR |",

        "|---|---:|---:|"

    ]

    for result in evaluation_results:

        lines.append(
            f"| {result['method']} | "
            f"{result['average_recall']:.4f} | "
            f"{result['average_mrr']:.4f} |"
        )

    lines.extend([

        "",

        "## Metric Explanation",

        "",

        "- Recall@5 measures the proportion of expected relevant clauses retrieved in the top five results.",

        "- MRR measures how highly the first relevant result is ranked.",

        "",

        "## Detailed Results",

        ""

    ])

    for result in evaluation_results:

        lines.extend([

            f"### {result['method']}",

            "",

            "| Query | Expected Clauses | Retrieved Clauses | Recall@5 | MRR |",

            "|---|---|---|---:|---:|"

        ])

        for detail in result["details"]:

            query = detail["query"].replace("|", "\\|")

            expected = ", ".join(detail["expected"])

            retrieved = ", ".join(detail["retrieved"])

            lines.append(

                f"| {query} | {expected} | {retrieved} | "
                f"{detail['recall']:.2f} | "
                f"{detail['mrr']:.2f} |"

            )

        lines.append("")

    lines.extend([

        "## Important Notes",

        "",

        "- The evaluation uses a synthetic educational insurance corpus.",

        "- Retrieval results are evaluated against manually defined expected clause IDs.",

        "- Recall@5 and MRR measure retrieval quality, not the factual accuracy of generated answers.",

        "- Semantic Hybrid Search uses the configured Azure AI Search semantic configuration.",

        ""

    ])

    REPORT_FILE.write_text(
        "\n".join(lines),
        encoding="utf-8"
    )

    print(f"\nReport saved to: {REPORT_FILE}")


# ==================================================
# MAIN
# ==================================================

def main():

    print("\nSAATHI RETRIEVAL EVALUATION")

    print("===========================")

    questions = load_gold_set()

    if not questions:
        raise ValueError("Gold set is empty.")

    queries = [
        question["query"]
        for question in questions
    ]

    embeddings = generate_query_embeddings(queries)

    evaluation_results = []

    # Vector Search

    vector_results = evaluate_method(
        "Vector Search",
        questions,
        embeddings,
        vector_search
    )

    evaluation_results.append(vector_results)

    # Hybrid Search

    hybrid_results = evaluate_method(
        "Hybrid Search",
        questions,
        embeddings,
        hybrid_search
    )

    evaluation_results.append(hybrid_results)

    # Semantic Hybrid Search

    semantic_results = evaluate_method(
        "Semantic Hybrid Search",
        questions,
        embeddings,
        semantic_hybrid_search
    )

    evaluation_results.append(semantic_results)

    # Display comparison

    print("\n\nFINAL RETRIEVAL COMPARISON")

    print("==========================")

    for result in evaluation_results:

        print(f"\n{result['method']}")

        print(
            f"Recall@5: {result['average_recall']:.4f}"
        )

        print(
            f"MRR: {result['average_mrr']:.4f}"
        )

    generate_report(
        evaluation_results,
        len(questions)
    )

    print("\nRETRIEVAL EVALUATION COMPLETED!")


if __name__ == "__main__":

    main()