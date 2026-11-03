
"""
Local BM25 retrieval evaluation for Saathi Insurance Agent Copilot.

Inputs:
    rag/corpus/insurance_chunks.jsonl
    rag/corpus/retrieval_gold_set.jsonl

Output:
    docs/local_retrieval_report.md

Metrics:
    Recall@5
    MRR (Mean Reciprocal Rank)

This is a lexical BM25 baseline, not a local vector-search implementation.
"""

import json
import re
from pathlib import Path
from collections import defaultdict

from rank_bm25 import BM25Okapi


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent

CORPUS_PATH = ROOT / "rag/corpus/insurance_chunks.jsonl"
GOLD_PATH = ROOT / "rag/corpus/retrieval_gold_set.jsonl"
REPORT_PATH = ROOT / "docs/local_retrieval_report.md"

TOP_K = 5


# ---------------------------------------------------------
# Load JSONL
# ---------------------------------------------------------

def load_jsonl(path):
    """Read a JSONL file into a list of dictionaries."""

    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    records = []

    with path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            line = line.strip()

            if not line:
                continue

            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON in {path}, line {line_number}: {exc}"
                )

    if not records:
        raise ValueError(f"No records found in {path}")

    return records


# ---------------------------------------------------------
# Helpers for handling corpus and gold-set fields
# ---------------------------------------------------------

def get_field(record, possible_names, required=True):
    """
    Return the first matching field from a list of possible names.
    """

    for name in possible_names:
        if name in record and record[name] is not None:
            return record[name]

    if required:
        raise KeyError(
            f"Could not find any of these fields: {possible_names}\n"
            f"Available fields: {list(record.keys())}"
        )

    return None


def normalize_expected_ids(value):
    """Convert expected clause IDs into a list of strings."""

    if isinstance(value, str):
        return [value]

    if isinstance(value, list):
        return [str(item) for item in value]

    if isinstance(value, dict):
        # Support objects such as {"clause_id": "..."}
        for key in ("clause_id", "id", "expected_id"):
            if key in value:
                return [str(value[key])]

    raise ValueError(
        f"Unsupported expected clause ID format: {value}"
    )


def tokenize(text):
    """Simple lowercase alphanumeric tokenizer."""

    return re.findall(r"[a-z0-9]+", str(text).lower())


def normalize_metadata(value):
    """Normalize metadata values for filtering."""

    if value is None:
        return None

    return str(value).strip().lower()


# ---------------------------------------------------------
# Prepare corpus
# ---------------------------------------------------------

def prepare_corpus(records):

    documents = []

    for record in records:

        clause_id = get_field(
            record,
            ["clause_id", "id", "source_id", "chunk_id"]
        )

        text = get_field(
            record,
            ["text", "content", "chunk_text", "page_content"]
        )

        product = get_field(
            record,
            ["product", "product_type"],
            required=False
        )

        tier = get_field(
            record,
            ["tier", "plan", "insurance_tier"],
            required=False
        )

        documents.append({
            "id": str(clause_id),
            "text": str(text),
            "product": normalize_metadata(product),
            "tier": normalize_metadata(tier),
            "tokens": tokenize(text)
        })

    return documents


# ---------------------------------------------------------
# Filter corpus based on question metadata
# ---------------------------------------------------------

def filter_documents(documents, question_record):

    product = normalize_metadata(
        get_field(
            question_record,
            ["product", "product_type"],
            required=False
        )
    )

    tier = normalize_metadata(
        get_field(
            question_record,
            ["tier", "plan", "insurance_tier"],
            required=False
        )
    )

    filtered = []

    for document in documents:

        product_matches = (
            product is None
            or document["product"] is None
            or document["product"] == product
        )

        tier_matches = (
            tier is None
            or document["tier"] is None
            or document["tier"] == tier
        )

        if product_matches and tier_matches:
            filtered.append(document)

    return filtered


# ---------------------------------------------------------
# BM25 retrieval
# ---------------------------------------------------------

def retrieve(query, documents, top_k=TOP_K):

    if not documents:
        return []

    tokenized_documents = [
        document["tokens"]
        for document in documents
    ]

    bm25 = BM25Okapi(tokenized_documents)

    query_tokens = tokenize(query)

    scores = bm25.get_scores(query_tokens)

    ranked_indices = sorted(
        range(len(scores)),
        key=lambda index: scores[index],
        reverse=True
    )

    results = []

    for index in ranked_indices[:top_k]:

        results.append({
            "id": documents[index]["id"],
            "text": documents[index]["text"],
            "score": float(scores[index])
        })

    return results


# ---------------------------------------------------------
# Evaluation metrics
# ---------------------------------------------------------

def evaluate_question(question_record, documents):

    question = get_field(
        question_record,
        ["question", "query", "user_query"]
    )

    expected_ids = normalize_expected_ids(
        get_field(
            question_record,
            [
                "expected_clause_ids",
                "expected_ids",
                "relevant_clause_ids",
                "clause_ids",
                "expected_clause_id",
                "expected_id"
            ]
        )
    )

    filtered_documents = filter_documents(
        documents,
        question_record
    )

    results = retrieve(
        question,
        filtered_documents,
        TOP_K
    )

    retrieved_ids = [
        result["id"]
        for result in results
    ]

    # Recall@5:
    # 1 if at least one expected clause is in top 5.
    # 0 otherwise.
    relevant_found = any(
        expected_id in retrieved_ids
        for expected_id in expected_ids
    )

    recall_at_5 = 1.0 if relevant_found else 0.0

    # MRR:
    # Reciprocal rank of the first relevant result.
    reciprocal_rank = 0.0

    for rank, retrieved_id in enumerate(
        retrieved_ids,
        start=1
    ):

        if retrieved_id in expected_ids:
            reciprocal_rank = 1.0 / rank
            break

    return {
        "question": str(question),
        "expected_ids": expected_ids,
        "retrieved_ids": retrieved_ids,
        "recall_at_5": recall_at_5,
        "reciprocal_rank": reciprocal_rank
    }


# ---------------------------------------------------------
# Main evaluation
# ---------------------------------------------------------

def main():

    print("=" * 60)
    print("Saathi Local BM25 Retrieval Evaluation")
    print("=" * 60)

    print("\nLoading corpus...")

    corpus_records = load_jsonl(CORPUS_PATH)

    print(f"Corpus records loaded: {len(corpus_records)}")

    print("\nLoading retrieval gold set...")

    gold_records = load_jsonl(GOLD_PATH)

    print(f"Gold questions loaded: {len(gold_records)}")

    documents = prepare_corpus(corpus_records)

    question_results = []

    for index, question_record in enumerate(
        gold_records,
        start=1
    ):

        result = evaluate_question(
            question_record,
            documents
        )

        question_results.append(result)

        print(
            f"Question {index}/{len(gold_records)} "
            f"| Recall@5: {result['recall_at_5']:.2f} "
            f"| MRR: {result['reciprocal_rank']:.2f}"
        )

    total_questions = len(question_results)

    recall_at_5 = (
        sum(result["recall_at_5"] for result in question_results)
        / total_questions
    )

    mrr = (
        sum(result["reciprocal_rank"] for result in question_results)
        / total_questions
    )

    # -----------------------------------------------------
    # Generate report
    # -----------------------------------------------------

    REPORT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with REPORT_PATH.open(
        "w",
        encoding="utf-8"
    ) as report:

        report.write(
            "# Local BM25 Retrieval Evaluation\n\n"
        )

        report.write(
            "## Evaluation Configuration\n\n"
        )

        report.write(
            f"- Corpus records: {len(documents)}\n"
        )

        report.write(
            f"- Evaluation questions: {total_questions}\n"
        )

        report.write(
            f"- Retrieval method: Local BM25\n"
        )

        report.write(
            f"- Top-K: {TOP_K}\n"
        )

        report.write(
            "- Filtering: Product and tier metadata "
            "when available\n\n"
        )

        report.write(
            "## Overall Results\n\n"
        )

        report.write(
            "| Metric | Score |\n"
        )

        report.write(
            "|---|---:|\n"
        )

        report.write(
            f"| Recall@5 | {recall_at_5:.4f} |\n"
        )

        report.write(
            f"| MRR | {mrr:.4f} |\n\n"
        )

        report.write(
            "## Question-Level Results\n\n"
        )

        report.write(
            "| Question | Expected IDs | Retrieved IDs | "
            "Recall@5 | Reciprocal Rank |\n"
        )

        report.write(
            "|---|---|---|---:|---:|\n"
        )

        for result in question_results:

            question = result["question"].replace(
                "|", "\\|"
            )

            expected = ", ".join(
                result["expected_ids"]
            )

            retrieved = ", ".join(
                result["retrieved_ids"]
            )

            report.write(
                f"| {question} | {expected} | "
                f"{retrieved} | "
                f"{result['recall_at_5']:.2f} | "
                f"{result['reciprocal_rank']:.2f} |\n"
            )

        report.write(
            "\n## Interpretation and Limitations\n\n"
        )

        report.write(
            "- BM25 is a lexical retrieval baseline based on "
            "term matching and term frequency.\n"
        )

        report.write(
            "- BM25 does not use semantic embeddings.\n"
        )

        report.write(
            "- Results are based on a small synthetic insurance "
            "corpus and evaluation set.\n"
        )

        report.write(
            "- These results should not be interpreted as "
            "production insurance retrieval accuracy.\n"
        )

    print("\n" + "=" * 60)

    print("Evaluation completed successfully!")

    print(f"Recall@5: {recall_at_5:.4f}")

    print(f"MRR:      {mrr:.4f}")

    print(f"\nReport saved to: {REPORT_PATH}")

    print("=" * 60)


if __name__ == "__main__":
    main()
