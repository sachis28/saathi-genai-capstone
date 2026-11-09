"""Agentic RAG orchestrated by Semantic Kernel.

The six MCP tools (app/agent/tools.py) are registered as one Semantic Kernel plugin, "saathi".
- LLM_PROVIDER=azure: SK's chat completion service talks to the Foundry deployment and uses
  automatic function calling (FunctionChoiceBehavior.Auto) to decide which tools to call.
- LLM_PROVIDER=mock: a fixed plan is run through kernel.invoke(), so the same plugin, filters
  and rules are used offline and in tests.

Rules enforced in code, not in the prompt:
- only allowlisted tools run, at most MAX_TOOL_CALLS per request (an SK auto-function-invocation
  filter stops the loop, and every call is counted again in the plugin);
- every customer_id argument is forced to the customer the agent selected, and every search is
  limited to that customer's product (and their tier, unless the model names another one);
- policy statements are produced by the normal grounded pipeline (generate_answer), one per
  search, so they can only cite clauses the search tool actually returned;
- facts from the other tools (the CRM record, the worklist, sentiment, the draft status) are
  written into the answer by code from the tool results, never by the LLM.
"""
import inspect
import json
import os
import re
from typing import Annotated, Any, Dict, List, Tuple

from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.function_choice_behavior import FunctionChoiceBehavior
from semantic_kernel.contents import ChatHistory
from semantic_kernel.filters import AutoFunctionInvocationContext, FilterTypes
from semantic_kernel.functions import KernelArguments, kernel_function

from app.agent.tools import TOOLS, mcp
from app.models.schemas import Citation, SearchHit
from app.services import audit
from app.services.answer import generate_answer, NOT_FOUND
from app.services.customer_context import scope_question, tier_filter
from app.services.customers import load_customers
from app.services.safety import safe_log

# Name of the Semantic Kernel plugin that holds our six tools.
PLUGIN = "saathi"
# Hard limit on tool calls per request, so the model can't loop forever.
MAX_TOOL_CALLS = 5
# Allowlist: the only tool names the agent may ever run.
ALLOWED = {"lookup_customer", "worklist", "search_knowledge_base", "customer_sentiment", "save_draft", "simulate_send"}

# Shown when save_draft worked. Written by code, so it never needs grounding.
DRAFT_NOTE = "Renewal draft created and waiting for your approval."

# System prompt for the planning step. It only chooses tools; it does not write the final answer.
PLANNER_PROMPT = (
    "You are Saathi, an insurance agent's copilot. Decide which tools to call for the agent's request "
    "about the selected customer. A request can have several parts; cover every part.\n"
    "- Call lookup_customer first whenever the request mentions the customer, their plan, renewal or consent.\n"
    "- Call search_knowledge_base once per separate policy topic (e.g. one search for ambulance cover, "
    "another for the grace period). Use a short, specific query for each topic, without the customer's name.\n"
    "- Call customer_sentiment when the request asks how the customer feels, their mood, complaints or risk of leaving.\n"
    "- Call worklist only when the request is about the agent's other customers or who to call.\n"
    "- Call save_draft only when the request asks for a draft, reminder or renewal message.\n"
    "- Never call simulate_send; a human must approve and send drafts.\n"
    f"You may call at most {MAX_TOOL_CALLS} tools. Never invent policy facts. When you have what you need, "
    "reply with a one-line note; the final cited answer is written by the system."
)


# Lists the MCP tools' JSON schemas (name, description, parameters) for the UI and docs.
async def tool_schemas() -> List[Dict[str, Any]]:
    """The MCP server's own JSON schemas (shown in the UI trace and the docs)."""
    return [{"type": "function", "function": {"name": t.name, "description": t.description or "",
                                              "parameters": t.inputSchema}}
            for t in await mcp.list_tools() if t.name in ALLOWED]


# Runs one tool by name, after enforcing the safety rules below.
async def run_tool(name: str, args: Dict[str, Any], customer_id: str, agent_id: str) -> Any:
    if name not in ALLOWED or name not in TOOLS:
        return {"error": f"Tool {name} is not allowed"}
    if "customer_id" in args:
        args["customer_id"] = customer_id          # the model cannot reach another customer
    if name == "worklist":
        args["agent_id"] = agent_id
    if name == "search_knowledge_base":
        # Same scoping as /chat: this customer's product, and their tier unless the model asked for
        # another one; "this policy" in the query becomes e.g. "Health Gold policy".
        customer = load_customers().get(customer_id)
        if customer is not None:
            query = str(args.get("query") or "")
            args["query"] = scope_question(query, customer)
            args["product"] = customer.product
            args["tier"] = args.get("tier") or tier_filter(query, customer) or ""
    result = TOOLS[name](**args)
    return await result if inspect.isawaitable(result) else result


# Wraps the six MCP tools as Semantic Kernel functions. One instance is created per request,
# so customer_id, agent_id, the trace and the search hits never leak between requests.
class SaathiPlugin:
    """The MCP tools as Semantic Kernel functions, bound to one request's customer and agent."""

    def __init__(self, customer_id: str, agent_id: str):
        self.customer_id = customer_id
        self.agent_id = agent_id
        # Every tool call made in this request (shown in the UI as the agent trace).
        self.trace: List[Dict[str, Any]] = []
        # Clauses returned by search_knowledge_base; the final answer can only cite these.
        self.hits: List[SearchHit] = []
        # Each search as (query, the clauses it returned), so each policy topic gets its own answer.
        self.searches: List[Tuple[str, List[SearchHit]]] = []
        # Results of the non-search tools, used to write the fact lines of the answer.
        self.record: Dict[str, Any] = {}
        self.worklist_rows: List[Dict[str, Any]] = []
        self.sentiment: Dict[str, Any] = {}
        # Drafts that save_draft created (shown in the Workspace Renewal draft card).
        self.drafts: List[Dict[str, Any]] = []

    # Shared path for every tool: enforce the call limit, run it, record it, log it.
    async def call(self, name: str, args: Dict[str, Any]) -> Any:
        if len(self.trace) >= MAX_TOOL_CALLS:
            return {"error": "Tool call limit reached"}
        # run_tool fills in the enforced values; the trace shows the arguments that really ran.
        effective = dict(args)
        result = await run_tool(name, effective, self.customer_id, self.agent_id)
        ok = not (isinstance(result, dict) and "error" in result)
        self.trace.append({"tool": name, "args": effective, "ok": ok, "orchestrator": "semantic-kernel"})
        if name == "search_knowledge_base" and isinstance(result, list):
            found = [SearchHit(**r) for r in result]
            self.hits.extend(found)
            self.searches.append((str(effective.get("query") or ""), found))
        elif ok and isinstance(result, dict) and name == "lookup_customer":
            self.record = result
        elif ok and isinstance(result, dict) and name == "customer_sentiment":
            self.sentiment = result
        elif name == "worklist" and isinstance(result, list):
            self.worklist_rows = result
        elif ok and isinstance(result, dict) and name == "save_draft" and "draft_id" in result:
            self.drafts.append(result)
        safe_log("agent_tool_call", tool=name, customer_id=self.customer_id)
        audit.log_event("agent_tool_call", tool=name, customer_id=self.customer_id)
        return result

    # Semantic Kernel functions must return text, so tool results are turned into JSON strings.
    async def _json(self, name: str, **args) -> str:
        return json.dumps(await self.call(name, args), default=str)

    # Each @kernel_function below is what the LLM "sees": a name, a description and typed arguments.
    @kernel_function(name="lookup_customer",
                     description="Get one customer's CRM record: product, tier, consent, renewal date and policy status.")
    async def lookup_customer(self, customer_id: Annotated[str, "Customer ID, e.g. C-204"]) -> str:
        return await self._json("lookup_customer", customer_id=customer_id)

    @kernel_function(name="worklist",
                     description="List the agent's customers whose policy can still be renewed (ACTIVE or IN_GRACE).")
    async def worklist(self, agent_id: Annotated[str, "Agent ID; always replaced by the signed-in agent"] = "") -> str:
        return await self._json("worklist", agent_id=agent_id)

    @kernel_function(name="search_knowledge_base",
                     description="Search the insurance policy clauses (Azure AI Search or the local index). Returns cited clauses.")
    async def search_knowledge_base(self, query: Annotated[str, "What to search for"],
                                    product: Annotated[str, "Health or Motor, optional"] = "",
                                    tier: Annotated[str, "Silver, Gold or Platinum, optional"] = "") -> str:
        return await self._json("search_knowledge_base", query=query, product=product, tier=tier)

    @kernel_function(name="customer_sentiment",
                     description="How the customer's recent messages sounded: 90-day sentiment score (-1 to +1) and latest labelled interactions.")
    async def customer_sentiment(self, customer_id: Annotated[str, "Customer ID"]) -> str:
        return await self._json("customer_sentiment", customer_id=customer_id)

    @kernel_function(name="save_draft",
                     description="Create a renewal message draft. It is saved as PENDING_APPROVAL; a human must approve it.")
    async def save_draft(self, customer_id: Annotated[str, "Customer ID"]) -> str:
        return await self._json("save_draft", customer_id=customer_id)

    @kernel_function(name="simulate_send",
                     description="Simulate sending an APPROVED draft. Blocked unless a human approved it and consent is given.")
    async def simulate_send(self, draft_id: Annotated[str, "Draft ID"]) -> str:
        return await self._json("simulate_send", draft_id=draft_id)


# Builds a Kernel with our plugin and a filter that enforces the tool budget.
def build_kernel(plugin: SaathiPlugin) -> Kernel:
    kernel = Kernel()
    kernel.add_plugin(plugin, plugin_name=PLUGIN)

    # A Semantic Kernel filter runs before each automatic function call the model asks for.
    async def limit_tool_calls(context: AutoFunctionInvocationContext, next):
        # Stop the model's tool loop once the per-request budget is used up.
        if context.function.name not in ALLOWED or len(plugin.trace) >= MAX_TOOL_CALLS:
            context.terminate = True
            return
        await next(context)

    kernel.add_filter(FilterTypes.AUTO_FUNCTION_INVOCATION, limit_tool_calls)
    return kernel


# Offline "planner": fixed rules instead of an LLM, so the demo and tests work without Azure.
def mock_plan(question: str, customer_id: str) -> List[Tuple[str, Dict[str, Any]]]:
    """Deterministic planner for LLM_PROVIDER=mock (offline demo and tests)."""
    q = question.lower()
    wants_draft = "draft" in q or "renewal message" in q or "reminder" in q
    # A plain "draft a renewal message" only needs the draft tool.
    if wants_draft and not any(w in q for w in ("cover", "plan", "policy", "grace", "waiting", "feel", "sentiment")):
        return [("save_draft", {"customer_id": customer_id})]
    plan: List[Tuple[str, Dict[str, Any]]] = [("lookup_customer", {"customer_id": customer_id})]
    wants_sentiment = any(w in q for w in ("feel", "sentiment", "mood", "complain", "happy", "upset"))
    if wants_sentiment:
        plan.append(("customer_sentiment", {"customer_id": customer_id}))
    # The policy part of the question is everything before "and draft ...", searched as asked.
    policy = re.split(r",?\s*(?:and|then)\s+(?:also\s+)?(?:draft|write|create)\b", question, flags=re.IGNORECASE)[0]
    policy_words = ("cover", "grace", "waiting", "exclu", "claim", "limit", "benefit", "premium")
    if any(w in q for w in policy_words) or not (wants_draft or wants_sentiment):
        plan.append(("search_knowledge_base", {"query": policy}))
    if wants_draft:
        plan.append(("save_draft", {"customer_id": customer_id}))
    return plan


# Creates the Semantic Kernel chat service that talks to our Azure AI Foundry model.
def chat_service():
    """SK chat completion service on the Foundry deployment already used for LLM_PROVIDER=azure."""
    from openai import AsyncOpenAI
    from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
    # Accept the endpoint with or without the /openai/v1 suffix.
    endpoint = os.environ["AZURE_OPENAI_ENDPOINT"].strip().rstrip("/")
    if endpoint.endswith("/openai/v1"):
        endpoint = endpoint[: -len("/openai/v1")]
    client = AsyncOpenAI(base_url=f"{endpoint}/openai/v1/", api_key=os.environ["AZURE_OPENAI_API_KEY"].strip())
    return OpenAIChatCompletion(ai_model_id=os.environ["AZURE_OPENAI_DEPLOYMENT"].strip(), async_client=client)


# Real planning with the LLM: Semantic Kernel lets the model call tools automatically
# (FunctionChoiceBehavior.Auto), limited to our plugin and to MAX_TOOL_CALLS attempts.
async def plan_with_llm(kernel: Kernel, question: str, customer_id: str) -> None:
    from semantic_kernel.connectors.ai.open_ai import OpenAIChatPromptExecutionSettings
    service = chat_service()
    settings = OpenAIChatPromptExecutionSettings(
        # temperature=0 makes tool choice repeatable.
        temperature=0,
        function_choice_behavior=FunctionChoiceBehavior.Auto(
            filters={"included_plugins": [PLUGIN]}, maximum_auto_invoke_attempts=MAX_TOOL_CALLS),
    )
    history = ChatHistory(system_message=PLANNER_PROMPT)
    history.add_user_message(f"Selected customer: {customer_id}\nQuestion: {question}")
    await service.get_chat_message_content(history, settings, kernel=kernel)


# Entry point used by POST /agent/chat.
async def run_agent(question: str, customer_id: str, agent_id: str) -> Dict[str, Any]:
    plugin = SaathiPlugin(customer_id, agent_id)
    kernel = build_kernel(plugin)

    # LLM_PROVIDER=azure -> the model plans; anything else -> the fixed mock plan.
    if os.getenv("LLM_PROVIDER", "mock").lower() == "azure":
        await plan_with_llm(kernel, question, customer_id)
    else:
        for name, args in mock_plan(question, customer_id):
            if name not in ALLOWED:
                continue
            await kernel.invoke(function_name=name, plugin_name=PLUGIN, arguments=KernelArguments(**args))

    answer, citations = compose_answer(question, plugin)
    return {"answer": answer, "citations": [c.model_dump() for c in citations], "trace": plugin.trace,
            "orchestrator": "semantic-kernel", "draft": plugin.drafts[-1] if plugin.drafts else None}


# The customer's record in one line, written by code from the lookup_customer result.
def record_line(r: Dict[str, Any]) -> str:
    if not r.get("customer_id"):
        return ""
    who = f"{r['customer_id']} ({r['name']})" if r.get("name") else r["customer_id"]
    line = f"{who} is on {r.get('product', '')} {r.get('tier', '')}.".replace("  ", " ")
    extra = []
    if r.get("renewal_date"):
        extra.append(f"renewal date {r['renewal_date']}")
    if r.get("policy_status"):
        extra.append(f"policy {r['policy_status']}")
    extra.append("consent to contact given" if r.get("consent", True) else "no consent to contact")
    details = ", ".join(extra)
    return f"{line} {details[0].upper()}{details[1:]}."


def worklist_line(rows: List[Dict[str, Any]]) -> str:
    if not rows:
        return "You have no renewable customers right now."
    items = "; ".join(f"{r['customer_id']} {r.get('name', '')} ({r.get('product', '')} {r.get('tier', '')}, "
                      f"{r.get('policy_status') or 'status unknown'})" for r in rows)
    return f"Your renewable customers: {items}."


def sentiment_line(s: Dict[str, Any]) -> str:
    score = s.get("sentiment_score_90d")
    if score is None:
        return "No sentiment data on record for this customer."
    word = "positive" if score > 0.2 else "negative" if score < -0.2 else "neutral"
    latest = s.get("latest") or []
    tail = ""
    if latest:
        last = latest[0]
        tail = f" Latest message ({last.get('date')}, {last.get('channel')}) was {last.get('sentiment')}."
    return f"Recent messages sound {word}: 90-day sentiment score {score:+.2f} over {s.get('interactions', 0)} interactions.{tail}"


# Builds the final answer: code-written fact lines, then one grounded, cited answer per policy
# topic searched, then the draft status. Any policy part that fails grounding says NOT_FOUND.
def compose_answer(question: str, plugin: SaathiPlugin) -> Tuple[str, List[Citation]]:
    facts = []
    if plugin.record:
        facts.append(record_line(plugin.record))
    if plugin.sentiment:
        facts.append(sentiment_line(plugin.sentiment))
    if any(t["tool"] == "worklist" and t["ok"] for t in plugin.trace):
        facts.append(worklist_line(plugin.worklist_rows))

    policy, citations, seen = [], [], set()
    # A single plain question keeps the full wording, exactly like before. A request with several
    # parts (more searches, a draft, the worklist) is answered per search query, so a sentence such
    # as "and draft a reminder" is never treated as an unsupported policy claim.
    multi = len(plugin.searches) > 1 or bool(plugin.drafts) or bool(plugin.worklist_rows) or bool(plugin.sentiment)
    attempts = [(question, plugin.hits)] if plugin.searches and not multi else []
    for query, hits in attempts or plugin.searches:
        text, cites = generate_answer(query, hits)
        # One retry with the model's own (shorter) query if the full question failed grounding.
        if text == NOT_FOUND and not multi and plugin.searches[-1][0] not in ("", query):
            text, cites = generate_answer(plugin.searches[-1][0], hits)
        if text != NOT_FOUND and text not in policy:
            policy.append(text)
            for c in cites:
                if (c.source_id, c.clause_id) not in seen:
                    seen.add((c.source_id, c.clause_id))
                    citations.append(c)
    if plugin.searches and not policy:
        policy.append(NOT_FOUND)

    parts = [p for p in (" ".join(f for f in facts if f), *policy) if p]
    if plugin.drafts:
        parts.append(DRAFT_NOTE)
    return ("\n\n".join(parts) if parts else NOT_FOUND), citations
