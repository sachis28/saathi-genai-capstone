"""Agentic RAG: the model decides which MCP tools to call; code decides what is allowed.

Rules enforced here, not in the prompt:
- only allowlisted tools run, at most MAX_TOOL_CALLS per request;
- every customer_id argument is forced to the customer the agent selected;
- the final answer is produced by the normal grounded pipeline (generate_answer), so it can
  only cite clauses the search tool actually returned.
"""
import inspect
import json
import os
from typing import Any, Dict, List, Tuple

from app.agent.tools import TOOLS, mcp
from app.models.schemas import Citation, SearchHit
from app.services import audit
from app.services.answer import generate_answer, NOT_FOUND
from app.services.safety import safe_log

MAX_TOOL_CALLS = 3
ALLOWED = {"lookup_customer", "worklist", "search_knowledge_base", "save_draft", "simulate_send"}

PLANNER_PROMPT = (
    "You are Saathi, an insurance agent's copilot. Decide which tools to call to answer the "
    "agent's question about the selected customer. Use search_knowledge_base for any question "
    "about policy terms. You may call at most 3 tools. Never invent policy facts. When you have "
    "what you need, reply with a one-line note; the final cited answer is written by the system."
)


async def tool_schemas() -> List[Dict[str, Any]]:
    """The MCP server's own JSON schemas, converted to the OpenAI tool format."""
    return [{"type": "function", "function": {"name": t.name, "description": t.description or "",
                                              "parameters": t.inputSchema}}
            for t in await mcp.list_tools() if t.name in ALLOWED]


async def run_tool(name: str, args: Dict[str, Any], customer_id: str, agent_id: str) -> Any:
    if name not in ALLOWED or name not in TOOLS:
        return {"error": f"Tool {name} is not allowed"}
    if "customer_id" in args:
        args["customer_id"] = customer_id          # the model cannot reach another customer
    if name == "worklist":
        args["agent_id"] = agent_id
    result = TOOLS[name](**args)
    return await result if inspect.isawaitable(result) else result


def mock_plan(question: str, customer_id: str) -> List[Tuple[str, Dict[str, Any]]]:
    """Deterministic planner for LLM_PROVIDER=mock (offline demo and tests)."""
    q = question.lower()
    if "draft" in q or "renewal message" in q:
        return [("save_draft", {"customer_id": customer_id})]
    return [("lookup_customer", {"customer_id": customer_id}), ("search_knowledge_base", {"query": question})]


def planner_client():
    """The Foundry chat deployment already configured for LLM_PROVIDER=azure."""
    from app.services.llm import get_llm
    llm = get_llm()
    return llm.client, llm.deployment


async def run_agent(question: str, customer_id: str, agent_id: str) -> Dict[str, Any]:
    trace: List[Dict[str, Any]] = []
    hits: List[SearchHit] = []

    async def call(name: str, args: Dict[str, Any]) -> Any:
        if len(trace) >= MAX_TOOL_CALLS:
            return {"error": "Tool call limit reached"}
        result = await run_tool(name, dict(args), customer_id, agent_id)
        trace.append({"tool": name, "args": args, "ok": not (isinstance(result, dict) and "error" in result)})
        if name == "search_knowledge_base" and isinstance(result, list):
            hits.extend(SearchHit(**r) for r in result)
        safe_log("agent_tool_call", tool=name, customer_id=customer_id)
        audit.log_event("agent_tool_call", tool=name, customer_id=customer_id)
        return result

    if os.getenv("LLM_PROVIDER", "mock").lower() == "azure":
        client, deployment = planner_client()
        tools = await tool_schemas()
        messages = [{"role": "system", "content": PLANNER_PROMPT},
                    {"role": "user", "content": f"Selected customer: {customer_id}\nQuestion: {question}"}]
        for _ in range(MAX_TOOL_CALLS + 1):
            reply = client.chat.completions.create(model=deployment, temperature=0, messages=messages,
                                                   tools=tools).choices[0].message
            if not reply.tool_calls:
                break
            messages.append(reply.model_dump(exclude_none=True))
            for tc in reply.tool_calls:
                result = await call(tc.function.name, json.loads(tc.function.arguments or "{}"))
                messages.append({"role": "tool", "tool_call_id": tc.id, "content": json.dumps(result, default=str)})
    else:
        for name, args in mock_plan(question, customer_id):
            await call(name, args)

    if hits:
        answer, citations = generate_answer(question, hits)
    else:
        drafts = [t for t in trace if t["tool"] == "save_draft" and t["ok"]]
        answer = "Draft created and waiting for your approval." if drafts else NOT_FOUND
        citations: List[Citation] = []
    return {"answer": answer, "citations": [c.model_dump() for c in citations], "trace": trace}
