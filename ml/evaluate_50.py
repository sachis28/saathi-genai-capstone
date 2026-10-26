"""An additional fixed 50-query intent acceptance set, independent of training templates.

This is not the team's 50-query end-to-end RAG evaluation.
"""
import joblib
import pandas as pd

from ml.common import ARTIFACTS, ROOT, evaluate, write_json

QUESTIONS = {
    "compare_products":["Compare Silver versus Gold", "Show differences between Gold and Platinum", "Silver or Gold: compare benefits", "Help compare Silver and Platinum", "What differs in Gold and Silver?", "Compare Gold and Gold Plus", "Which is better, Silver or Gold?", "Silver versus Platinum policy comparison", "Compare the two plans Silver and Gold", "Compare the benefits of Silver and Gold for C-204"],
    "coverage_question":["What is covered by Silver?", "Explain Gold exclusions", "Is surgery covered under Gold?", "Tell me the Platinum waiting period", "Does Silver include hospitalization?", "What are the coverage limitations?", "Explain the policy's exclusions", "Is dental treatment included in Silver?", "What is the waiting period for Gold?", "Explain hospitalization cover under Platinum"],
    "renewal_draft":["Draft renewal reminder for C-204", "Compose a renewal SMS for C-311", "Write a premium renewal note", "Prepare a renewal email draft", "Create a policy renewal reminder", "Help draft the renewal message", "Write a notice about policy renewal", "Draft a renewal reminder pending approval", "Prepare a renewal notice for Gold", "Compose a reminder to renew the policy"],
    "customer_lookup":["Show C-204 profile", "Find the CRM record for C-311", "Look up C-118 contact details", "Fetch customer C-450 information", "Get the profile of customer C-205", "Display customer account details", "Show saved contact information for C-999", "Find C-204's policy record", "Retrieve CRM details for C-118", "Who is customer C-311?"],
    "out_of_scope":["Tell me a joke", "Give a cake recipe", "Book a flight to Delhi", "Predict the cricket score", "Write a love poem", "Recommend a movie", "Solve calculus homework", "Order a pizza", "What is today's weather?", "Play music for me"],
}


def main():
    rows = [{"id":f"A-{i*10+j+1:02}","text":text,"label":label} for i,(label,texts) in enumerate(QUESTIONS.items()) for j,text in enumerate(texts)]
    write_json(ROOT / "tests/fixtures/intent_acceptance_50.json",rows)
    frame = pd.DataFrame(rows)
    model = joblib.load(ARTIFACTS / "tfidf_lr/model.joblib")
    result = evaluate("intent_acceptance_50",frame,model.predict(frame.text),{"scope":"intent-only; not RAG, authorization, citations, UI, or cloud acceptance"})
    result["dataset"] = "separately authored synthetic 50-query intent smoke evaluation"
    result.pop("test_sha256",None)
    write_json(ARTIFACTS / "intent_acceptance_50/metrics.json",result)


if __name__ == "__main__":
    main()
