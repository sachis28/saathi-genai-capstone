"""
Generates thousands of synthetic customers for Saathi.
Run from the repo root:
    python api/scripts/generate_bulk_customers.py            # 5000 customers
    python api/scripts/generate_bulk_customers.py 10000      # any number

Writes data/customers_bulk.json. Sachi's data/customers.json (the 6 demo customers) is NOT touched.
Same seed = same file every time.
"""
import json
import random
import sys
from datetime import date, timedelta
from pathlib import Path

SEED = 42
COUNT = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
START_ID = 10001  # 5-digit IDs, so they never clash with demo IDs like C-204

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "customers_bulk.json"

FIRST = ["Shreya", "Tanisha", "Aryan", "Arjun", "Sai", "Reyansh", "Ishaan", "Kabir", "Rohan", "Yash",
         "Twisha", "Saniya", "Arya", "Kavya", "Meera", "Priya", "Riya", "Saanvi", "Shreya", "Tara",
         "Neha", "Pooja", "Rahul", "Amit", "Sneha", "Vikram", "Nikhil", "Aditi", "Sakshi", "Manish"]
LAST = ["chauhan", "Patil", "Kulkarni", "Deshmukh", "Joshi", "Iyer", "Reddy", "Nair", "Shah", "Mehta",
        "Gupta", "Singh", "Jadhav", "Pawar", "Chavan", "Rao", "Menon", "Kapoor", "Verma", "Bhat"]
CITIES = ["Pune", "Mumbai", "Nagpur", "Nashik", "Bengaluru", "Hyderabad", "Chennai", "Delhi", "Ahmedabad", "Kolkata"]
SEGMENTS = ["Retail", "SME", "Senior", "Young Professional", "Family"]
PRODUCTS = {"Health": ["Silver", "Gold", "Platinum"], "Motor": ["Silver", "Gold"]}
BASE_PREMIUM = {("Health", "Silver"): 12000, ("Health", "Gold"): 22000, ("Health", "Platinum"): 45000,
                ("Motor", "Silver"): 8000, ("Motor", "Gold"): 15000}


def main():
    rng = random.Random(SEED)
    today = date(2026, 10, 26)  # fixed, so the file is the same on every run

    rows = []
    for i in range(COUNT):
        product = rng.choices(["Health", "Motor"], weights=[0.7, 0.3])[0]
        tier = rng.choices(PRODUCTS[product], weights=[0.5, 0.35, 0.15][: len(PRODUCTS[product])])[0]
        premium = BASE_PREMIUM[(product, tier)] * rng.uniform(0.8, 1.6)
        rows.append({
            "customer_id": f"C-{START_ID + i}",
            "name": f"{rng.choice(FIRST)} {rng.choice(LAST)}",
            "product": product,
            "tier": tier,
            "city": rng.choice(CITIES),
            "segment": rng.choice(SEGMENTS),
            "consent": rng.random() < 0.85,
            "agent_id": f"A-{rng.randint(1, 40):03d}",
            "renewal_date": (today + timedelta(days=rng.randint(-30, 365))).isoformat(),
            "annual_premium_inr": round(premium, 2),
            "synthetic": True,
        })

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rows, indent=1), encoding="utf-8")

    consent_yes = sum(r["consent"] for r in rows)
    print(f"Wrote {len(rows)} customers to {OUT}")
    print(f"IDs: C-{START_ID} to C-{START_ID + COUNT - 1}")
    print(f"Consent true: {consent_yes}, false: {len(rows) - consent_yes}")


if __name__ == "__main__":
    main()
