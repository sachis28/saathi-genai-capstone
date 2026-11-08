"""Builds the synthetic policy library (insurance_docs.jsonl).

Starts from sample_docs.jsonl and adds 40 more synthetic clauses, each as a tuple of
(source_id, clause_id, product, tier, version, text). All data is made up for the capstone."""
import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent

INPUT_FILE = BASE_DIR / "sample_docs.jsonl"
OUTPUT_FILE = BASE_DIR / "insurance_docs.jsonl"


# --------------------------------------------------
# 1. Define 40 additional synthetic insurance clauses
# --------------------------------------------------

new_documents = [

    # HEALTH SILVER: 8 additional records

    ("POL-HEALTH-SILVER", "CL-CLAIM-03", "Health", "Silver", "v2",
     "Health Silver claims must include hospital bills, discharge summary and medical prescriptions."),

    ("POL-HEALTH-SILVER", "CL-EXC-04", "Health", "Silver", "v2",
     "Routine cosmetic procedures are excluded from Health Silver coverage."),

    ("POL-HEALTH-SILVER", "CL-WAIT-05", "Health", "Silver", "v2",
     "Specific listed treatments are subject to a 24 month waiting period under Health Silver."),

    ("POL-HEALTH-SILVER", "CL-ROOM-06", "Health", "Silver", "v2",
     "Room rent reimbursement is restricted to one percent of the sum insured per day."),

    ("POL-HEALTH-SILVER", "CL-AMB-07", "Health", "Silver", "v2",
     "Emergency ambulance expenses are covered up to INR 2000 per hospitalization."),

    ("POL-HEALTH-SILVER", "CL-PRE-08", "Health", "Silver", "v2",
     "Pre and post hospitalization expenses are covered for 30 and 60 days respectively."),

    ("POL-HEALTH-SILVER", "CL-NCB-09", "Health", "Silver", "v2",
     "A no claim bonus increases the sum insured by five percent for each claim-free year, subject to policy limits."),

    ("POL-HEALTH-SILVER", "CL-RENEW-10", "Health", "Silver", "v2",
     "Health Silver policies can be renewed annually subject to applicable renewal conditions."),


    # HEALTH GOLD: 9 additional records

    ("POL-HEALTH-GOLD", "CL-CLAIM-03", "Health", "Gold", "v2",
     "Health Gold reimbursement claims require original hospital bills, prescriptions and discharge records."),

    ("POL-HEALTH-GOLD", "CL-AMB-04", "Health", "Gold", "v2",
     "Emergency ambulance expenses are covered up to INR 5000 per hospitalization."),

    ("POL-HEALTH-GOLD", "CL-PRE-05", "Health", "Gold", "v2",
     "Pre hospitalization expenses are covered for 60 days before admission."),

    ("POL-HEALTH-GOLD", "CL-POST-06", "Health", "Gold", "v2",
     "Post hospitalization expenses are covered for 90 days after discharge."),

    ("POL-HEALTH-GOLD", "CL-EXC-08", "Health", "Gold", "v2",
     "Experimental treatments without recognized medical approval are excluded from coverage."),

    ("POL-HEALTH-GOLD", "CL-DAY-09", "Health", "Gold", "v2",
     "Eligible day-care procedures are covered without requiring a 24 hour hospital stay."),

    ("POL-HEALTH-GOLD", "CL-NCB-10", "Health", "Gold", "v2",
     "The no claim bonus increases the sum insured by ten percent for every claim-free year, subject to limits."),

    ("POL-HEALTH-GOLD", "CL-RENEW-11", "Health", "Gold", "v2",
     "Health Gold policies are eligible for annual renewal subject to policy terms."),

    ("POL-HEALTH-GOLD", "CL-MAT-12", "Health", "Gold", "v2",
     "Maternity expenses are covered only when the applicable waiting period and policy conditions are satisfied."),


    # HEALTH PLATINUM: 9 additional records

    ("POL-HEALTH-PLATINUM", "CL-CLAIM-02", "Health", "Platinum", "v1",
     "Platinum policyholders must submit original bills and medical records for reimbursement claims."),

    ("POL-HEALTH-PLATINUM", "CL-AMB-03", "Health", "Platinum", "v1",
     "Emergency ambulance expenses are covered up to INR 10000 per hospitalization."),

    ("POL-HEALTH-PLATINUM", "CL-PRE-04", "Health", "Platinum", "v1",
     "Pre hospitalization expenses are covered for 90 days before hospital admission."),

    ("POL-HEALTH-PLATINUM", "CL-POST-05", "Health", "Platinum", "v1",
     "Post hospitalization expenses are covered for 180 days after discharge."),

    ("POL-HEALTH-PLATINUM", "CL-EXC-06", "Health", "Platinum", "v1",
     "Treatment undertaken solely for cosmetic enhancement is excluded unless medically necessary following an accident."),

    ("POL-HEALTH-PLATINUM", "CL-DAY-07", "Health", "Platinum", "v1",
     "Eligible day-care treatments are covered under the Platinum plan."),

    ("POL-HEALTH-PLATINUM", "CL-NCB-08", "Health", "Platinum", "v1",
     "A no claim bonus increases the sum insured by fifteen percent for every claim-free year, subject to policy limits."),

    ("POL-HEALTH-PLATINUM", "CL-RENEW-09", "Health", "Platinum", "v1",
     "Platinum policies are renewable annually according to the applicable policy conditions."),

    ("POL-HEALTH-PLATINUM", "CL-INT-10", "Health", "Platinum", "v1",
     "International second medical opinion services are available under the Platinum plan."),


    # MOTOR GOLD: 7 additional records

    ("POL-MOTOR-GOLD", "CL-CLAIM-02", "Motor", "Gold", "v1",
     "Motor accident claims require an incident report, vehicle registration and repair estimates."),

    ("POL-MOTOR-GOLD", "CL-ROADSIDE-03", "Motor", "Gold", "v1",
     "Roadside assistance is available throughout the day subject to the service conditions."),

    ("POL-MOTOR-GOLD", "CL-EXC-04", "Motor", "Gold", "v1",
     "Driving under the influence of alcohol is excluded from motor policy coverage."),

    ("POL-MOTOR-GOLD", "CL-THEFT-05", "Motor", "Gold", "v1",
     "Vehicle theft claims require a police complaint and supporting vehicle ownership documents."),

    ("POL-MOTOR-GOLD", "CL-DAMAGE-06", "Motor", "Gold", "v1",
     "Accidental vehicle damage is covered subject to the applicable policy deductible."),

    ("POL-MOTOR-GOLD", "CL-RENEW-07", "Motor", "Gold", "v1",
     "Motor Gold policies can be renewed annually before the policy expiry date."),

    ("POL-MOTOR-GOLD", "CL-INSPECT-08", "Motor", "Gold", "v1",
     "The insurer may require vehicle inspection before approving certain claims."),


    # GENERAL INSURANCE: 7 additional records

    ("POL-GEN-RENEWAL", "CL-REN-02", "All", "All", "v1",
     "Policyholders should review policy terms and premium information before renewal."),

    ("POL-GEN-RENEWAL", "CL-REN-03", "All", "All", "v1",
     "Renewal requests should be submitted before the policy expiry date whenever possible."),

    ("POL-GEN-CLAIMS", "CL-CLAIM-01", "All", "All", "v1",
     "Insurance claims must include the required supporting documents for claim assessment."),

    ("POL-GEN-CLAIMS", "CL-CLAIM-02", "All", "All", "v1",
     "The insurer may request additional documents before completing claim assessment."),

    ("POL-GEN-GRIEVANCE", "CL-GRV-01", "All", "All", "v1",
     "Policyholders can submit complaints through the insurer grievance redressal process."),

    ("POL-GEN-PREMIUM", "CL-PREM-01", "All", "All", "v1",
     "Premium payment must be completed according to the payment schedule specified in the policy."),

    ("POL-GEN-DOCS", "CL-DOC-01", "All", "All", "v1",
     "Policyholders should retain their policy schedule, premium receipts and claim correspondence."),

]


# --------------------------------------------------
# 2. Load existing eight records
# --------------------------------------------------

existing_documents = []

with INPUT_FILE.open("r", encoding="utf-8") as file:

    for line in file:

        if line.strip():
            existing_documents.append(json.loads(line))


# --------------------------------------------------
# 3. Convert new records into JSON documents
# --------------------------------------------------

additional_documents = []

for record in new_documents:

    source_id, clause_id, product, tier, version, text = record

    additional_documents.append({
        "source_id": source_id,
        "clause_id": clause_id,
        "product": product,
        "tier": tier,
        "version": version,
        "text": text,
    })


# --------------------------------------------------
# 4. Combine existing and new documents
# --------------------------------------------------

all_documents = existing_documents + additional_documents


# --------------------------------------------------
# 5. Validate document IDs
# --------------------------------------------------

document_ids = [
    (doc["source_id"], doc["clause_id"], doc["version"])
    for doc in all_documents
]

if len(document_ids) != len(set(document_ids)):
    raise ValueError("Duplicate document IDs detected!")


# --------------------------------------------------
# 6. Write expanded corpus
# --------------------------------------------------

with OUTPUT_FILE.open("w", encoding="utf-8") as file:

    for document in all_documents:

        file.write(
            json.dumps(document, ensure_ascii=False) + "\n"
        )


# --------------------------------------------------
# 7. Display summary
# --------------------------------------------------

print("\n========== CORPUS GENERATION SUMMARY ==========")

print("Existing documents:", len(existing_documents))
print("New documents:", len(additional_documents))
print("Total documents:", len(all_documents))

print("\nDocuments by category:")

for product in sorted(set(doc["product"] for doc in all_documents)):

    count = sum(
        1 for doc in all_documents
        if doc["product"] == product
    )

    print(f"{product}: {count}")

print("\nOutput file:", OUTPUT_FILE)

print("Corpus generation completed successfully!")

print("================================================")