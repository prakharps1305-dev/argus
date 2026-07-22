import asyncio
import json
import os
from datetime import datetime, timezone

from traceloop.sdk import Traceloop
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
from openai import OpenAI
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

# ---- Config (env-driven so Argus deploys anywhere) ----
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:11434/v1")  # Ollama by default
LLM_API_KEY = os.getenv("LLM_API_KEY", "ollama")                       # any OpenAI-compatible key
LLM_MODEL = os.getenv("LLM_MODEL", "qwen3:8b")
MCP_URL = os.getenv("MCP_URL", "http://localhost:8000/mcp")
APP_NAME = os.getenv("ARGUS_APP_NAME", "argus")

Traceloop.init(app_name=APP_NAME, disable_batch=True)
tracer = trace.get_tracer(APP_NAME)          # for our own hand-made spans

llm = OpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY)

DEFAULT_INCIDENT = (
    "The checkout experience feels slow. Investigate system health "
    "and find any services that are unhealthy or erroring."
)

# Only the Investigator gets these (read-only) SigNoz tools.
ALLOWED_TOOLS = {
    "signoz_list_services",
    "signoz_get_service_top_operations",
    "signoz_aggregate_traces",
    "signoz_search_logs",
}


def mcp_tools_to_openai(mcp_tools):
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


async def run_agent(name, system_prompt, user_input, session, tools_schema=None, emit=None):
    """One agent = one loop. No tools_schema -> pure reasoning (no SigNoz access)."""
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_input},
    ]
    for step in range(6):
        kwargs = {"model": LLM_MODEL, "messages": messages}
        if tools_schema:
            kwargs["tools"] = tools_schema
        resp = llm.chat.completions.create(**kwargs)
        msg = resp.choices[0].message

        if not msg.tool_calls:
            answer = (msg.content or "").strip()
            if not answer:
                messages.append({"role": "user", "content": "Give your answer in plain text now."})
                continue
            return answer

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
            tname = tc.function.name
            args = json.loads(tc.function.arguments or "{}")
            print(f"    [{name} → MCP] {tname}({args})")
            ok = True
            with tracer.start_as_current_span(f"tool.{tname}") as span:
                span.set_attribute("tool.name", tname)
                span.set_attribute("tool.args", json.dumps(args)[:500])
                try:
                    result = await session.call_tool(tname, args)
                    text = "\n".join(getattr(c, "text", "") for c in result.content)
                    span.set_attribute("tool.result_chars", len(text))
                    if getattr(result, "isError", False):
                        ok = False
                        span.set_attribute("tool.error", True)
                        span.set_status(Status(StatusCode.ERROR, "tool returned error"))
                    else:
                        span.set_status(Status(StatusCode.OK))
                except Exception as e:
                    ok = False
                    span.set_attribute("tool.error", True)
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    text = f"ERROR calling {tname}: {e}"
            if emit:
                emit("tool", {"agent": name, "tool": tname, "ok": ok})
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": text[:4000]})
    return "(no answer produced)"


async def run_crew(incident, session, tools_schema, emit=None):
    """Run the 3-agent crew. Returns {plan, findings, report}. `emit(stage, text)` is
    an optional callback for live progress."""
    now = datetime.now(timezone.utc).isoformat()

    triage_sys = (
        "You are the TRIAGE agent in an SRE crew. Given an incident, decide which "
        "SIGNALS (traces, logs, metrics) and what KINDS of problems to investigate. "
        "You do NOT know the real service names — do NOT invent any (never write names "
        "like 'checkout-service' or 'payment-gateway'). Describe the investigation in "
        "terms of symptoms and signals. The Investigator will discover the real services. "
        "Output a short, concrete plan. You have NO tools — just reason."
    )
    investigator_sys = (
        "You are the INVESTIGATOR agent. Follow the given plan and use the SigNoz tools "
        f"to gather real evidence. Current UTC time is {now}; default to a 1-hour window. "
        "CRITICAL: ALWAYS call signoz_list_services FIRST to get the exact real service "
        "names, then use ONLY those exact names in later queries. Never guess names or add "
        "suffixes like '-service'. Report concrete findings: services, error rates, "
        "latencies, notable log lines."
    )
    reporter_sys = (
        "You are the REPORTER agent. Given the investigator's findings, write a concise "
        "incident report with three sections: Root Cause, Impact, Recommendation. Plain text."
    )

    with tracer.start_as_current_span("argus_crew"):
        with tracer.start_as_current_span("triage"):
            plan = await run_agent("triage", triage_sys, incident, session, emit=emit)
            if emit:
                emit("triage", plan)
            print("\n--- TRIAGE PLAN ---\n", plan)

        with tracer.start_as_current_span("investigator"):
            findings = await run_agent("investigator", investigator_sys, plan, session, tools_schema, emit=emit)
            if emit:
                emit("investigator", findings)
            print("\n--- INVESTIGATOR FINDINGS ---\n", findings)

        with tracer.start_as_current_span("reporter"):
            report = await run_agent("reporter", reporter_sys, findings, session, emit=emit)
            if emit:
                emit("reporter", report)
            print("\n=== INCIDENT REPORT ===\n", report)

    return {"plan": plan, "findings": findings, "report": report}


async def investigate(incident=DEFAULT_INCIDENT, emit=None):
    """Open an MCP session and run the crew. Importable entrypoint for the web app."""
    async with streamablehttp_client(MCP_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools_schema = mcp_tools_to_openai((await session.list_tools()).tools)
            return await run_crew(incident, session, tools_schema, emit=emit)


async def main():
    await investigate(DEFAULT_INCIDENT)


if __name__ == "__main__":
    asyncio.run(main())
