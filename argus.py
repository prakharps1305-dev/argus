import asyncio
import json
from datetime import datetime, timezone

from traceloop.sdk import Traceloop
from openai import OpenAI
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

# Instrumentation on -> every model call becomes a span in SigNoz.
Traceloop.init(app_name="argus", disable_batch=True)

llm = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")

MCP_URL = "http://localhost:8000/mcp"

# Read-only investigation tools we let the model use (a safe subset of the 40).
ALLOWED_TOOLS = {
    "signoz_list_services",
    "signoz_get_service_top_operations",
    "signoz_aggregate_traces",
    "signoz_search_logs",
}


def mcp_tools_to_openai(mcp_tools):
    """Convert MCP tool definitions into the OpenAI tool-schema shape."""
    schema = []
    for t in mcp_tools:
        if t.name not in ALLOWED_TOOLS:
            continue
        schema.append({
            "type": "function",
            "function": {
                "name": t.name,
                "description": (t.description or "")[:1000],
                "parameters": t.inputSchema or {"type": "object", "properties": {}},
            },
        })
    return schema


async def run_agent(question, session, tools_schema):
    now = datetime.now(timezone.utc).isoformat()
    system = (
        "You are Argus, an SRE assistant. You can query a SigNoz observability "
        "backend using the provided tools. Always use tools to fetch real data "
        f"before answering. The current UTC time is {now}. When a tool needs a "
        "time range, default to the last 1 hour. Be concise and factual. "
        "After you have the data you need, ALWAYS write a short plain-text "
        "summary for the user. Never end with an empty message."
    )
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": question},
    ]

    for step in range(6):  # safety cap
        resp = llm.chat.completions.create(
            model="qwen3:8b", messages=messages, tools=tools_schema
        )
        msg = resp.choices[0].message

        if not msg.tool_calls:
            answer = (msg.content or "").strip()
            if not answer:
                # Model went blank — nudge it once to actually summarize.
                messages.append({
                    "role": "user",
                    "content": "Summarize your findings in plain text now.",
                })
                continue
            print("\n=== FINAL ANSWER ===\n", answer)
            return

        messages.append({
            "role": "assistant",
            "content": msg.content,
            "tool_calls": [
                {"id": tc.id, "type": "function",
                 "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in msg.tool_calls
            ],
        })

        for tc in msg.tool_calls:
            name = tc.function.name
            args = json.loads(tc.function.arguments or "{}")
            print(f"[MCP call] {name}({args})")
            result = await session.call_tool(name, args)   # <-- run tool OVER MCP
            text = "\n".join(
                getattr(c, "text", "") for c in result.content
            )
            print(f"[MCP result] {text[:300]}...\n")
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": text[:4000],   # trim so we don't blow up context
            })


async def main():
    async with streamablehttp_client(MCP_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            all_tools = (await session.list_tools()).tools
            tools_schema = mcp_tools_to_openai(all_tools)
            print(f"Exposing {len(tools_schema)} tools to the model.\n")
            await run_agent(
                "Which services are running right now, and are any of them "
                "showing errors? Give me a short health summary.",
                session,
                tools_schema,
            )


asyncio.run(main())
