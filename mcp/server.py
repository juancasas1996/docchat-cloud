"""Calculator MCP server.

The same four tools from the IBM tool-calling labs, but exposed over the
Model Context Protocol instead of LangChain's in-process @tool decorator:
any MCP client (Claude Code, claude.ai, Claude Desktop) can discover and
call them. Runs over Streamable HTTP so it deploys like any other service.
"""

import os

from mcp.server.fastmcp import FastMCP

# stateless_http: each request is self-contained — plays well with
# scale-to-zero and multiple replicas if this ever reaches Azure.
mcp = FastMCP(
    "calculator",
    host="0.0.0.0",
    port=int(os.getenv("PORT", "8080")),
    stateless_http=True,
)


@mcp.tool()
def add(a: float, b: float) -> float:
    """Add a and b."""
    return a + b


@mcp.tool()
def subtract(a: float, b: float) -> float:
    """Subtract b from a."""
    return a - b


@mcp.tool()
def multiply(a: float, b: float) -> float:
    """Multiply a and b."""
    return a * b


@mcp.tool()
def divide(a: float, b: float) -> float:
    """Divide a by b."""
    if b == 0:
        raise ValueError("Cannot divide by zero.")
    return a / b


if __name__ == "__main__":
    mcp.run(transport=os.getenv("MCP_TRANSPORT", "streamable-http"))
