import json
import logging
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional

from app.models.schemas import Customer

logger = logging.getLogger("saathi")

DATA_DIR = Path(__file__).resolve().parents[3] / "data"
CUSTOMERS_FILE = DATA_DIR / "customers.json"          # Sachi's 6 demo customers
BULK_FILE = DATA_DIR / "customers_bulk.json"          # optional, thousands of generated customers

GRACE_DAYS = 30
ACTIVE, IN_GRACE, LAPSED, CANCELLED = "ACTIVE", "IN_GRACE", "LAPSED", "CANCELLED"


class CustomerNotFound(LookupError):
    """Route should map this to 404."""


class NotAuthorized(PermissionError):
    """Route should map this to 403."""


def policy_fields(renewal_date: Optional[str], explicit_status: Optional[str] = None,
                  today: Optional[date] = None) -> dict:
    """Single source of truth for policy_status and renewal eligibility (agreed contract)."""
    today = today or date.today()
    days = (date.fromisoformat(renewal_date) - today).days if renewal_date else None

    if (explicit_status or "").upper() == CANCELLED:          # never calculated, only explicit
        status, eligible, reason = CANCELLED, False, "CANCELLED"
    elif days is None:
        status, eligible, reason = None, False, "MISSING_RENEWAL_DATE"
    elif days >= 0:
        status, eligible, reason = ACTIVE, True, None
    elif days >= -GRACE_DAYS:                                  # -30 <= days < 0
        status, eligible, reason = IN_GRACE, True, None
    else:                                                      # days < -30
        status, eligible, reason = LAPSED, False, "LAPSED_BEYOND_GRACE"

    return {"days_to_renewal": days, "policy_status": status,
            "renewal_eligible": eligible, "eligibility_reason": reason}


def _to_customer(row: dict, today: Optional[date] = None) -> Customer:
    return Customer(
        customer_id=row["customer_id"],
        name=row.get("name") or row.get("customer_name") or row["customer_id"],
        product=row["product"],
        tier=row["tier"],
        consent=bool(row.get("consent", False)),
        agent_id=row.get("agent_id"),
        renewal_date=row.get("renewal_date"),
        **policy_fields(row.get("renewal_date"), row.get("policy_status"), today),
    )


# Used only if no data file exists, so tests and the offline demo still run.
FALLBACK_ROWS = [
    {"customer_id": "C-204", "name": "Demo Customer", "product": "Health", "tier": "Silver",
     "consent": True, "agent_id": "A-001"},
    {"customer_id": "C-205", "name": "No Consent Customer", "product": "Health", "tier": "Gold",
     "consent": False, "agent_id": "A-001"},
]


def _read(path: Path) -> list:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return raw.get("customers", raw) if isinstance(raw, dict) else raw


@lru_cache
def load_customers() -> Dict[str, Customer]:
    """Bulk customers first, then Sachi's demo customers, so the demo ones always win on an ID clash."""
    customers: Dict[str, Customer] = {}
    for path in (BULK_FILE, CUSTOMERS_FILE):
        if path.exists():
            rows = _read(path)
            customers.update({c.customer_id: c for c in (_to_customer(r) for r in rows)})
            logger.info("Loaded %d customers from %s", len(rows), path)

    if not customers:
        logger.warning("No customer files found in %s, using fallback customers", DATA_DIR)
        return {r["customer_id"]: _to_customer(r) for r in FALLBACK_ROWS}
    return customers


def authorize_customer(customer_id: str, agent_id: str) -> Customer:
    """Shared check: customer must exist AND belong to the calling agent."""
    customer = load_customers().get(customer_id)
    if customer is None:
        raise CustomerNotFound(customer_id)
    if not agent_id or customer.agent_id != agent_id:
        raise NotAuthorized(f"Agent {agent_id} is not assigned to customer {customer_id}")
    return customer

def renewal_candidates(agent_id: str) -> list:
 # Auth first, then eligibility. Consent is enforced at send, not here.
 return [c for c in load_customers().values() if c.agent_id == agent_id and c.renewal_eligible]
