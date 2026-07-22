# 👁️ Argus

**An SRE crew that watches your system — watched by SigNoz.**

Argus is a multi-agent SRE copilot built for the [Agents of SigNoz](https://www.wemakedevs.org/hackathons/signoz)
hackathon (Track 01 — AI & Agent Observability). A small team of agents investigates
system incidents by querying the **SigNoz MCP server**, and every step of their reasoning
(LLM calls, tool calls, handoffs, tokens, latency) streams back into **SigNoz** via
OpenTelemetry — so the agents are *observed by* SigNoz while they work *through* SigNoz.

## The crew
- **Triage** — reads the incident, decides what to look at.
- **Investigator** — queries SigNoz (traces / metrics / logs) via MCP.
- **Reporter** — writes the grounded findings.

## Stack
- **Agents:** Python + local LLM via [Ollama](https://ollama.com) (`qwen3:8b`)
- **Instrumentation:** Traceloop / OpenLLMetry → OpenTelemetry GenAI spans
- **Observability backend:** [SigNoz](https://signoz.io) (self-hosted via [Foundry](https://github.com/SigNoz/foundry))

## Status
🚧 Work in progress — building during the hackathon (Jul 20–26, 2026).

> AI assistance (Claude) is used in this project and declared per hackathon rules.
# argus
