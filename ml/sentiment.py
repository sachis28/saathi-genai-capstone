"""Analyze synthetic interaction text using Azure AI Language."""

import json
import os
from pathlib import Path

from azure.ai.textanalytics import TextAnalyticsClient
from azure.core.credentials import AzureKeyCredential

ROOT = Path(__file__).resolve().parents[1]


def main():
    endpoint = os.getenv("AZURE_LANGUAGE_ENDPOINT")
    key = os.getenv("AZURE_LANGUAGE_KEY")

    if not endpoint or not key:
        raise SystemExit("Load the Language endpoint and key first.")

    source = ROOT / "data/interactions.json"
    interactions = json.loads(source.read_text(encoding="utf-8"))

    ids = [row["interaction_id"] for row in interactions]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate interaction IDs")

    results = []

    with TextAnalyticsClient(
        endpoint=endpoint,
        credential=AzureKeyCredential(key),
    ) as client:
        for start in range(0, len(interactions), 5):
            batch = interactions[start:start + 5]
            documents = [
                {"id": row["interaction_id"], "text": row["text"]}
                for row in batch
            ]
            responses = list(
                client.analyze_sentiment(
                    documents=documents,
                    language="en",
                )
            )

            by_id = {result.id: result for result in responses}
            expected = {row["interaction_id"] for row in batch}
            if len(responses) != len(batch) or set(by_id) != expected:
                raise RuntimeError("Response IDs do not match input IDs")

            for row in batch:
                result = by_id[row["interaction_id"]]
                if result.is_error:
                    raise RuntimeError(
                        f"{result.id}: service error {result.error.code}"
                    )

                scores = result.confidence_scores
                results.append({
                    "interaction_id": row["interaction_id"],
                    "customer_id": row["customer_id"],
                    "date": row["date"],
                    "sentiment": result.sentiment,
                    "confidence_scores": {
                        "positive": scores.positive,
                        "neutral": scores.neutral,
                        "negative": scores.negative,
                    },
                    "provider": "azure-ai-language",
                })

            print(f"Processed {len(results)}/{len(interactions)}")

    # Write only after every interaction succeeds.
    output = ROOT / "data/interaction_sentiment.json"
    temporary = output.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(results, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(output)

    print(f"Created {output.name}: {len(results)} records")


if __name__ == "__main__":
    main()
