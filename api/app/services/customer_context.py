"""Makes /chat aware of the loaded customer.

1. "this customer's policy" / "my policy" becomes "Health Gold policy", so retrieval finds the right clauses.
2. "When does this policy renew?" is answered from the customer record, because a renewal date
   lives in the customer data, not in the policy clauses.
"""
import re
from typing import Optional

from app.models.schemas import Customer

POLICY_REF = re.compile(
    r"\b(?:this|the|my|their|his|her)\s+(?:customer'?s?\s+)?policy\b|\bthis\s+customer'?s?\s+plan\b",
    re.IGNORECASE,
)
RENEWAL_DATE_Q = re.compile(
    r"\b(when|what date|which date|due date|expiry|expire|expires|expiring)\b.*\b(renew\w*|expir\w*|due|end\w*)\b"
    r"|\brenewal date\b",
    re.IGNORECASE,
)


def scope_question(question: str, customer: Customer) -> str:
    """Replace a vague policy reference with the customer's product and tier."""
    label = f"{customer.product} {customer.tier} policy"
    return POLICY_REF.sub(label, question)


def renewal_answer(question: str, customer: Customer) -> Optional[str]:
    """Answer a renewal-date question from the customer record, or None if it is not one."""
    if not RENEWAL_DATE_Q.search(question) or not customer.renewal_date:
        return None
    status = {
        "ACTIVE": "The policy is active.",
        "IN_GRACE": "The renewal date has passed, so the policy is in its 30 day grace period.",
        "LAPSED": "The policy lapsed beyond the 30 day grace period and is not eligible for renewal.",
        "CANCELLED": "The policy is cancelled.",
    }.get(customer.policy_status or "", "")
    return (f"From the customer record: {customer.name}'s {customer.product} {customer.tier} policy "
            f"renews on {customer.renewal_date.isoformat()}. {status}").strip()
