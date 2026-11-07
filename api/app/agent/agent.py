"""Agentic RAG orchestrated by Semantic Kernel.

The five MCP tools (app/agent/tools.py) are registered as one Semantic Kernel plugin, "saathi".
- LLM_PROVIDER=azure: SK's chat completion service talks to the Foundry deployment and uses
  automatic function calling (FunctionChoiceBehavior.Auto) to decide which tools to call.
- LLM_PROVIDER=mock: a fixed plan is run through kernel.invoke(), so the same plugin, filters
  and rules are used offline and in tests.

Rules enforced in code, not in the prompt:
- only allowlisted tools run, at most MAX_TOOL_CALLS per request (an SK auto-function-invocation
  filter stops the loop, and every call is counted again in the plugin);
- every customer_id argument is forced to the customer the agent selected;
- the final answer is produced by the normal grounded pipeline (generate_answer), so it can
  only cite clauses the search tool actually returned.
"""
import inspect
import json
import os
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
from app.services.safety import safe_log

PLUGIN = "saathi"
MAX_TOOL_CALLS = 3
ALLOWED = {"lookup_customer", "worklist", "search_knowledge_base", "save_draft", "simulate_send"}

PLANNER_PROMPT = (
    "You are Saathi, an insurance agent's copilot. Decide which tools to call to answer the "
    "agent's question about the selected customer. Use search_knowledge_base for any question "
    "about policy terms. You may call at most 3 tools. Never invent policy facts. When you have "
    "what you need, reply with a one-line note; the final cited answer is written by the system."
)


async def tool_schemas() -> List[Dict[str, Any]]:
    """The MCP server's own JSON schemas (shown in the UI trace and the docs)."""
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


class SaathiPlugin:
    """The MCP tools as Semantic Kernel functions, bound to one request's customer and agent."""

    def __init__(self, customer_id: str, agent_id: str):
        self.customer_id = customer_id
        self.agent_id = agent_id
        self.trace: List[Dict[str, Any]] = []
        self.hits: List[SearchHit] = []

    async def call(self, name: str, args: Dict[str, Any]) -> Any:
        if len(self.trace) >= MAX_TOOL_CALLS:
            return {"error": "Tool call limit reached"}
        result = await run_tool(name, dict(args), self.customer_id, self.agent_id)
        self.trace.append({"tool": name, "args": args, "ok": not (isinstance(result, dict) and "error" in result),
                           "orchestrator": "semantic-kernel"})
        if name == "search_knowledge_base" and isinstance(result, list):
            self.hits.extend(SearchHit(**r) for r in result)
        safe_log("agent_tool_call", tool=name, customer_id=self.customer_id)
        audit.log_event("agent_tool_call", tool=name, customer_id=self.customer_id)
        return result

    async def _json(self, name: str, **args) -> str:
        return json.dumps(await self.call(name, args), default=str)

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

    @kernel_function(name="save_draft",
                     description="Create a renewal message draft. It is saved as PENDING_APPROVAL; a human must approve it.")
    async def save_draft(self, customer_id: Annotated[str, "Customer ID"]) -> str:
        return await self._json("save_draft", customer_id=customer_id)

    @kernel_function(name="simulate_send",
                     description="Simulate sending an APPROVED draft. Blocked unless a human approved it and consent is given.")
    async def simulate_send(self, draft_id: Annotated[str, "Draft ID"]) -> str:
        return await self._json("simulate_send", draft_id=draft_id)


def build_kernel(plugin: SaathiPlugin) -> Kernel:
    kernel = Kernel()
    kernel.add_plugin(plugin, plugin_name=PLUGIN)

    async def limit_tool_calls(context: AutoFunctionInvocationContext, next):
        # Stop the model's tool loop once the per-request budget is used up.
        if context.function.name not in ALLOWED or len(plugin.trace) >= MAX_TOOL_CALLS:
            context.terminate = True
            return
        await next(context)

    kernel.add_filter(FilterTypes.AUTO_FUNCTION_INVOCATION, limit_tool_calls)
    return kernel


def mock_plan(question: str, customer_id: str) -> List[Tuple[str, Dict[str, Any]]]:
    """Deterministic planner for LLM_PROVIDER=mock (offline demo and tests)."""
    q = question.lower()
    if "draft" in q or "renewal message" in q:
        return [("save_draft", {"customer_id": customer_id})]
    return [("lookup_customer", {"customer_id": customer_id}), ("search_knowledge_base", {"query": question})]


def chat_service():
    """SK chat completion service on the Foundry deployment already used for LLM_PROVIDER=azure."""
    from openai import AsyncOpenAI
    from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
    endpoint = os.environ["AZURE_OPENAI_ENDPOINT"].strip().rstrip("/")
    if endpoint.endswith("/openai/v1"):
        endpoint = endpoint[: -len("/openai/v1")]
    client = AsyncOpenAI(base_url=f"{endpoint}/openai/v1/", api_key=os.environ["AZURE_OPENAI_API_KEY"].strip())
    return OpenAIChatCompletion(ai_model_id=os.environ["AZURE_OPENAI_DEPLOYMENT"].strip(), async_client=client)


async def plan_with_llm(kernel: Kernel, question: str, customer_id: str) -> None:
    from semantic_kernel.connectors.ai.open_ai import OpenAIChatPromptExecutionSettings
    service = chat_service()
    settings = OpenAIChatPromptExecutionSettings(
        temperature=0,
        function_choice_behavior=FunctionChoiceBehavior.Auto(
            filters={"included_plugins": [PLUGIN]}, maximum_auto_invoke_attempts=MAX_TOOL_CALLS),
    )
    history = ChatHistory(system_message=PLANNER_PROMPT)
    history.add_user_message(f"Selected customer: {customer_id}\nQuestion: {question}")
    await service.get_chat_message_content(history, settings, kernel=kernel)


async def run_agent(question: str, customer_id: str, agent_id: str) -> Dict[str, Any]:
    plugin = SaathiPlugin(customer_id, agent_id)
    kernel = build_kernel(plugin)

    if os.getenv("LLM_PROVIDER", "mock").lower() == "azure":
        await plan_with_llm(kernel, question, customer_id)
    else:
        for name, args in mock_plan(question, customer_id):
            if name not in ALLOWED:
                continue
            await kernel.invoke(function_name=name, plugin_name=PLUGIN, arguments=KernelArguments(**args))

    if plugin.hits:
        answer, citations = generate_answer(question, plugin.hits)
    else:
        drafts = [t for t in plugin.trace if t["tool"] == "save_draft" and t["ok"]]
        answer = "Draft created and waiting for your approval." if drafts else NOT_FOUND
        citations: List[Citation] = []
    return {"answer": answer, "citations": [c.model_dump() for c in citations], "trace": plugin.trace,
            "orchestrator": "semantic-kernel"}
