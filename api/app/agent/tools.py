"""Saathi's six agent tools, exposed as an MCP server.

Run as a standalone MCP server (stdio), e.g. for MCP Inspector or Claude Desktop:
    PYTHONPATH=.:api python -m app.agent.tools

The same functions back the in-process agent (app/agent/agent.py). Every tool calls the
existing services, so the policy rules (customer ownership, approval before send, consent
re-check, audit) stay in code and cannot be skipped by the model.
"""
from typing import Any, Dict, List

from fastapi import HTTPException
from mcp.server.fastmcp import FastMCP

from app.services.customers import load_customers, renewal_candidates
from app.services.insights import customer_sentiment as sentiment_report
from app.services.retriever import get_retriever

# FastMCP turns each decorated function below into an MCP tool. The docstring becomes the
# tool description and the type hints become its JSON input schema.
mcp = FastMCP("saathi")


@mcp.tool()
def lookup_customer(customer_id: str) -> Dict[str, Any]:
    """Get one customer's CRM record: product, tier, consent, renewal date and policy status."""
    customer = load_customers().get(customer_id)
    if customer is None:
        return {"error": "Customer not found"}
    return customer.model_dump(mode="json")


@mcp.tool()
def worklist(agent_id: str) -> List[Dict[str, Any]]:
    """List the agent's customers whose policy can still be renewed (ACTIVE or IN_GRACE)."""
    return [{"customer_id": c.customer_id, "name": c.name, "product": c.product, "tier": c.tier,
             "policy_status": c.policy_status} for c in renewal_candidates(agent_id)]


@mcp.tool()
def search_knowledge_base(query: str, product: str = "", tier: str = "") -> List[Dict[str, Any]]:
    """Search the insurance policy clauses (Azure AI Search or the local index). Returns cited clauses."""
    hits = get_retriever().search(query, k=5, product=product or None, tier=tier or None)
    return [h.model_dump() for h in hits]


@mcp.tool()
def customer_sentiment(customer_id: str) -> Dict[str, Any]:
    """How the customer's recent messages sounded: the 90-day sentiment score (-1 to +1) and the latest labelled interactions."""
    report = sentiment_report(customer_id)
    latest = [{k: i.get(k) for k in ("date", "channel", "sentiment")} for i in report["interactions"][:3]]
    return {"customer_id": customer_id, "sentiment_score_90d": report["sentiment_score_90d"],
            "as_of_date": report["as_of_date"], "interactions": len(report["interactions"]), "latest": latest}


@mcp.tool()
async def save_draft(customer_id: str) -> Dict[str, Any]:
    """Create a renewal message draft. It is saved as PENDING_APPROVAL; a human must approve it."""
    # Imported inside the function to avoid a circular import (main.py imports the agent).
    from app import main
    # Reuse the real /drafts endpoint so drafts made by the agent follow the same rules.
    from app.models.schemas import DraftRequest
    try:
        return (await main.create_draft(DraftRequest(customer_id=customer_id))).model_dump()
    except HTTPException as e:
        return {"error": e.detail}


@mcp.tool()
async def simulate_send(draft_id: str) -> Dict[str, Any]:
    """Simulate sending an APPROVED draft. Blocked unless a human approved it and consent is given."""
    from app import main
    try:
        # Reuse the real send endpoint: it blocks unless the draft is APPROVED and consent is given.
        return (await main.send_draft(draft_id)).model_dump()
    except HTTPException as e:
        return {"error": e.detail}


# Name -> function lookup used by the in-process agent (app/agent/agent.py).
TOOLS = {f.__name__: f for f in (lookup_customer, worklist, search_knowledge_base, customer_sentiment,
                                  save_draft, simulate_send)}


# Running this file directly starts it as a standalone MCP server over stdio.
if __name__ == "__main__":
    mcp.run()
