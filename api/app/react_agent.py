"""Pure ReAct agent wired to the calculator MCP server.

No router, no gate: on every turn the LLM itself decides whether to call a
tool or answer directly. The tools are not hardcoded — they are discovered
live from the MCP server (langchain-mcp-adapters acts as the MCP client),
and LangGraph's prebuilt ReAct loop drives the reason→act→observe cycle.
"""

import os

from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

# Provider-agnostic LLM config: any OpenAI-compatible endpoint works.
# Default: OpenAI gpt-4.1-mini — correct multilingual tool calling with clean
# traces for ~$0.002/question. Measured rejects: 4.1-nano answers wrong
# (bad parallel decomposition), the free NVIDIA models each failed one of:
# Spanish tool calls, parallel calls, or availability.
# Free alternative: LLM_BASE_URL=https://integrate.api.nvidia.com/v1 with
# LLM_MODEL=deepseek-ai/deepseek-v4-flash and the NVIDIA key.
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
REACT_MODEL = os.getenv("LLM_MODEL", "gpt-4.1-mini")
LLM_API_KEY = (
    os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY") or os.getenv("NVIDIA_API_KEY") or ""
)
# Safety valve for models that only accept one tool call per turn (llama-3.1).
SINGLE_TOOL_CALL = os.getenv("REACT_SINGLE_TOOL_CALL", "false").lower() == "true"
MCP_URL = os.getenv(
    "MCP_URL",
    "https://docchat-mcp.wonderfuldune-e71f934b.eastus2.azurecontainerapps.io/mcp",
)

_agent = None


def _content_text(content) -> str:
    """Flatten langchain content blocks to plain text."""
    if isinstance(content, list):
        return " ".join(
            str(block.get("text", block)) if isinstance(block, dict) else str(block)
            for block in content
        )
    return str(content)


def _single_tool_call(msg: AIMessage) -> AIMessage:
    if getattr(msg, "tool_calls", None) and len(msg.tool_calls) > 1:
        msg.tool_calls = msg.tool_calls[:1]
        if "tool_calls" in msg.additional_kwargs:
            msg.additional_kwargs["tool_calls"] = msg.additional_kwargs["tool_calls"][:1]
    return msg


async def _get_agent():
    """Build the ReAct agent once: discover MCP tools, bind them to the LLM."""
    global _agent
    if _agent is None:
        client = MultiServerMCPClient(
            {"calculator": {"url": MCP_URL, "transport": "streamable_http"}}
        )
        tools = await client.get_tools()
        llm = ChatOpenAI(
            base_url=LLM_BASE_URL,
            api_key=LLM_API_KEY,
            model=REACT_MODEL,
            temperature=0,
        )
        bound = llm.bind_tools(tools)
        if SINGLE_TOOL_CALL:
            bound = bound | RunnableLambda(_single_tool_call)
        _agent = create_react_agent(
            bound,
            tools,
            prompt=(
                "You are a calculator assistant. You MUST use a tool for every "
                "arithmetic operation, never compute numbers yourself. "
                "If the question involves no arithmetic, reply in one short "
                "sentence that you only help with calculations."
            ),
        )
    return _agent


async def run_react(question: str) -> dict:
    """Run the loop and return the final answer plus the tool-call trace."""
    agent = await _get_agent()
    result = await agent.ainvoke({"messages": [("user", question)]})
    messages = result["messages"]

    tool_results = {
        m.tool_call_id: _content_text(m.content)
        for m in messages
        if m.__class__.__name__ == "ToolMessage"
    }
    trace = []
    for m in messages:
        for tc in getattr(m, "tool_calls", None) or []:
            args = ", ".join(f"{k}={v}" for k, v in tc["args"].items())
            trace.append(f"{tc['name']}({args}) → {tool_results.get(tc['id'], '?')}")

    return {"answer": messages[-1].content, "trace": trace, "model": REACT_MODEL}
