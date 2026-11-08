"""Plan comparison (v2 plan, Day 36; demo act 1): a table of cited clauses, one cell per tier.

Every cell is the clause text itself, with its source_id, clause_id and version, taken from
retrieval filtered to that tier. No LLM writes a cell, so a cell can't claim something its
clause doesn't say. A tier with no matching clause shows "Not stated".
"""
import re
from typing import List, Optional

from app.models.schemas import Citation, Comparison, ComparisonCell, ComparisonRow
from app.services.retriever import get_retriever
from app.services.safety import filter_poisoned

# The three Health plan tiers, in display order.
TIERS = ("Silver", "Gold", "Platinum")
# Words that mean the user wants a comparison, e.g. "Silver vs Gold", "which is better".
COMPARE_WORDS = re.compile(r"\b(compare|comparison|vs\.?|versus|difference|differ|better)\b", re.IGNORECASE)

# (row label, search query, word the clause must contain to fill the cell)
ASPECTS = {
    "Health": [
        ("Hospitalisation cover", "in-patient hospitalisation cover up to INR per policy year", "in-patient"),
        ("Pre-existing disease waiting period", "pre-existing diseases covered after a waiting period", "pre-existing"),
        ("Ambulance", "emergency ambulance expenses covered up to INR per hospitalization", "ambulance"),
        ("Pre-hospitalisation", "pre hospitalization expenses covered days before admission", "pre hospitalization"),
        ("No claim bonus", "no claim bonus increases the sum insured claim-free year", "no claim bonus"),
        ("Cosmetic exclusion", "cosmetic treatment excluded", "cosmetic"),
        ("Day-care", "day-care procedures treatments covered", "day-care"),
    ],
}


# Which tier names appear in the question.
def tiers_named(question: str) -> List[str]:
    return [t for t in TIERS if re.search(rf"\b{t}\b", question, re.IGNORECASE)]


# A comparison = two tiers named, or one tier plus a comparison word ("compare with Gold").
def is_comparison(question: str) -> bool:
    named = tiers_named(question)
    return len(named) >= 2 or (len(named) == 1 and bool(COMPARE_WORDS.search(question)))


# Which tiers go in the table.
def comparison_tiers(question: str, customer_tier: str) -> List[str]:
    named = tiers_named(question)
    if len(named) == 1 and customer_tier in TIERS and customer_tier not in named:
        named = [customer_tier] + named          # "compare with Gold" -> the customer's tier vs Gold
    return sorted(set(named), key=TIERS.index)


# One table cell: the best clause for this aspect in this tier, or None ("Not stated").
def _cell(product: str, tier: str, query: str, must: str) -> Optional[ComparisonCell]:
    hits, _ = filter_poisoned(get_retriever().search(f"{query} {tier}", k=5, product=product, tier=tier))
    # Only this tier's own clauses (not general 'All' ones), and only a clause about this aspect.
    own = [h for h in hits if h.tier == tier and must in h.text.lower()]
    if not own:
        return None
    h = own[0]
    return ComparisonCell(text=h.text, source_id=h.source_id, clause_id=h.clause_id, version=h.version)


# Build the whole table: one row per aspect, one cell per tier. Rows with no clauses are dropped.
def build_comparison(product: str, tiers: List[str]) -> Optional[Comparison]:
    aspects = ASPECTS.get(product)
    if not aspects or len(tiers) < 2:
        return None
    rows = [ComparisonRow(aspect=name, cells={t: _cell(product, t, q, must) for t in tiers})
            for name, q, must in aspects]
    rows = [r for r in rows if any(r.cells.values())]
    return Comparison(product=product, tiers=tiers, rows=rows)


def comparison_answer(c: Comparison):
    """A text version (with citation tags) for clients that don't draw the table, plus the citations."""
    lines = [f"Comparison of {c.product} {' vs '.join(c.tiers)}, from the policy clauses:"]
    citations, seen = [], set()
    for r in c.rows:
        parts = []
        for t in c.tiers:
            cell = r.cells.get(t)
            if cell is None:
                parts.append(f"{t}: Not stated")
                continue
            parts.append(f"{t}: {cell.text} [{cell.source_id}#{cell.clause_id}]")
            key = (cell.source_id, cell.clause_id)
            if key not in seen:
                seen.add(key)
                citations.append(Citation(source_id=cell.source_id, clause_id=cell.clause_id, version=cell.version))
        lines.append(f"- {r.aspect}: " + " | ".join(parts))
    return "\n".join(lines), citations
