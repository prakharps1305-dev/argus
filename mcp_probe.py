import asyncio
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

MCP_URL = "http://localhost:8000/mcp"


async def main():
    # Open a connection to the MCP server (the read/write channels)...
    async with streamablehttp_client(MCP_URL) as (read, write, _):
        # ...and start a session over it.
        async with ClientSession(read, write) as session:
            await session.initialize()          # MCP handshake
            resp = await session.list_tools()    # ask the server what tools it has
            print(f"{len(resp.tools)} tools available:\n")
            for t in resp.tools:
                print(f"- {t.name}")


asyncio.run(main())
