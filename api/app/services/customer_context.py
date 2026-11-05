"""Makes /chat aware of the loaded customer.

1. "this customer's policy" / "my policy" becomes "Health Gold policy", so retrieval finds the right clauses.
2. "When does this policy renew?" and "What are this customer's details?" are answered from the
   customer record, because that data lives in the customer system, not in the policy clauses.
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


CUSTOMER_REF = re.compile(r"\b(this|the|my)\s+(customer|client)|\b(customer|client)'?s\b|\b(their|his|her)\b",
                          re.IGNORECASE)
DETAIL_Q = re.compile(
    r"\b(details?|info|information|profile|summary|premium|consent|status|agent|eligib\w*)\b"
    r"|\b(which|what)\s+(plan|product|tier)\b|\bwho is\b",
    re.IGNORECASE,
)
STATUS_TEXT = {
    "ACTIVE": "Active",
    "IN_GRACE": "In the 30 day grace period (renewal date has passed)",
    "LAPSED": "Lapsed beyond the 30 day grace period",
    "CANCELLED": "Cancelled",
}


def details_answer(question: str, customer: Customer) -> Optional[str]:
    """Answer 'what are this customer's details / premium / consent / status' from the record."""
    if not (CUSTOMER_REF.search(question) and DETAIL_Q.search(question)):
        return None
    lines = [
        f"From the customer record for {customer.name} ({customer.customer_id}):",
        f"- Plan: {customer.product} {customer.tier}",
        f"- Policy status: {STATUS_TEXT.get(customer.policy_status or '', 'Unknown')}",
    ]
    if customer.renewal_date:
        lines.append(f"- Renewal date: {customer.renewal_date.isoformat()}")
    lines.append(f"- Eligible for renewal: {'Yes' if customer.renewal_eligible else 'No'}")
    if customer.annual_premium_inr:
        lines.append(f"- Annual premium: INR {customer.annual_premium_inr:,.0f}")
    lines.append(f"- Contact consent: {'Given' if customer.consent else 'Not given, so no renewal message can be sent'}")
    if customer.agent_id:
        lines.append(f"- Assigned agent: {customer.agent_id}")
    return "\n".join(lines)


def record_answer(question: str, customer: Customer) -> Optional[str]:
    """Questions about the customer's own data, answered from the record instead of the clauses."""
    return renewal_answer(question, customer) or details_answer(question, customer)


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
