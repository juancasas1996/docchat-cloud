"""Tiny MCP client — smoke test and didactic example.

Shows the full protocol conversation a client like Claude runs for you:
initialize → tools/list → tools/call.

    python example_client.py http://localhost:8080/mcp
"""

import asyncio
import sys

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


async def main(url: str) -> None:
    async with streamablehttp_client(url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            print("tools disponibles:", [t.name for t in tools.tools])

            result = await session.call_tool("add", {"a": 2, "b": 3})
            print("add(2, 3) =", result.content[0].text)

            result = await session.call_tool("multiply", {"a": 47, "b": 83})
            print("multiply(47, 83) =", result.content[0].text)

            result = await session.call_tool("divide", {"a": 1, "b": 0})
            print("divide(1, 0) →", "error manejado:" if result.isError else "?",
                  result.content[0].text)


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8080/mcp"))
