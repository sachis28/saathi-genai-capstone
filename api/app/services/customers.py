import json
import logging
import os
from datetime import date, datetime, timezone
from fastapi import HTTPException
from pathlib import Path
from typing import Dict

from app.models.schemas import Customer

logger = logging.getLogger("saathi")

DATA_DIR = Path(__file__).resolve().parents[3] / "data"
CUSTOMERS_FILE = DATA_DIR / "customers.json"          # Sachi's 6 demo customers
BULK_FILE = DATA_DIR / "customers_bulk.json"          # optional, thousands of generated customers

# Used only if no data file exists, so tests and the offline demo still run.
FALLBACK = {
    "C-204": Customer(customer_id="C-204", name="Demo Customer", product="Health", tier="Silver", consent=True),
    "C-205": Customer(customer_id="C-205", name="No Consent Customer", product="Health", tier="Gold", consent=False),
}


def reference_date(as_of: date | None = None) -> date:
    if as_of is not None:
        return as_of
    configured = os.getenv("SAATHI_AS_OF_DATE")
    return date.fromisoformat(configured) if configured else datetime.now(timezone.utc).date()


def policy_metadata(row: dict, as_of: date | None = None) -> dict:
    """Authoritative 30-day grace rule; cancellation is always explicit."""
    cancelled = row.get("cancelled", False)
    if type(cancelled) is not bool:
        raise ValueError("cancelled must be boolean")
    explicit = row.get("policy_status")
    if explicit not in (None, "ACTIVE", "IN_GRACE", "LAPSED", "CANCELLED"):
        raise ValueError("Unknown policy status")
    if cancelled or explicit == "CANCELLED":
        return {"policy_status":"CANCELLED", "renewal_eligible":False,
                "eligibility_reason":"CANCELLED"}
    renewal = row.get("renewal_date")
    if not renewal:
        return {"policy_status":None, "renewal_eligible":False,
                "eligibility_reason":"MISSING_RENEWAL_DATE"}
    renewal = date.fromisoformat(renewal) if isinstance(renewal, str) else renewal
    days = (renewal - reference_date(as_of)).days
    status = "ACTIVE" if days >= 0 else "IN_GRACE" if days >= -30 else "LAPSED"
    return {"policy_status":status, "renewal_eligible":status != "LAPSED",
            "eligibility_reason":"LAPSED_BEYOND_GRACE" if status == "LAPSED" else None}


def _to_customer(row: dict, as_of: date | None = None) -> Customer:
    values = dict(row)
    values["name"] = row.get("name") or row.get("customer_name") or row["customer_id"]
    values["consent"] = row.get("consent", False)
    values.update(policy_metadata(row, as_of))
    return Customer.model_validate(values)


def authorize_customer(customer_id: str, agent_id: str) -> Customer:
    customer = load_customers().get(customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    if not customer.agent_id or customer.agent_id != agent_id:
        raise HTTPException(status_code=403, detail="Customer access denied")
    return customer


def _read(path: Path) -> list:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return raw.get("customers", raw) if isinstance(raw, dict) else raw


def load_customers() -> Dict[str, Customer]:
    """Bulk customers first, then Sachi's demo customers, so the demo ones always win on an ID clash."""
    customers: Dict[str, Customer] = {}
    for path in (BULK_FILE, CUSTOMERS_FILE):
        if path.exists():
            rows = _read(path)
            converted = [_to_customer(r) for r in rows]
            if len({c.customer_id for c in converted}) != len(converted):
                raise ValueError("Duplicate customer IDs")
            customers.update({c.customer_id: c for c in converted})
            logger.info("Loaded %d customers from %s", len(rows), path)

    if not customers:
        logger.warning("No customer files found in %s, using fallback customers", DATA_DIR)
        return dict(FALLBACK)
    return customers


def renewal_candidates(agent_id: str) -> list:
    """Auth first, then eligibility. Consent is enforced at send, not here."""
    return [c for c in load_customers().values() if c.agent_id == agent_id and c.renewal_eligible]
