import json
import logging
from functools import lru_cache
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


def _to_customer(row: dict) -> Customer:
    return Customer(
        customer_id=row["customer_id"],
        name=row.get("name") or row.get("customer_name") or row["customer_id"],
        product=row["product"],
        tier=row["tier"],
        consent=bool(row.get("consent", False)),
    )


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
        return dict(FALLBACK)
    return customers
