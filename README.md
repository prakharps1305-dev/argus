# 👁️ Argus

**An SRE crew that watches your system — watched by SigNoz.**

Argus is a multi-agent SRE copilot built for the [Agents of SigNoz](https://www.wemakedevs.org/hackathons/signoz)
hackathon (Track 01 — AI & Agent Observability). A small team of agents investigates
system incidents by querying the **SigNoz MCP server**, and every step of their reasoning
(LLM calls, tool calls, handoffs, tokens, latency) streams back into **SigNoz** via
OpenTelemetry — so the agents are *observed by* SigNoz while they work *through* SigNoz.

## The crew
- **Triage** — reads the incident, decides what to look at (no tools).
- **Investigator** — queries SigNoz (services / traces / logs) via the MCP server.
- **Reporter** — writes the grounded incident report.

Each agent's output is the next one's input. The whole run is grouped into **one nested
trace** in SigNoz (`argus_crew → triage / investigator / reporter → openai.chat / tool.*`).

## Stack
- **Agents:** Python + local LLM via [Ollama](https://ollama.com) (`qwen3:8b`)
- **Instrumentation:** Traceloop / OpenLLMetry + manual OpenTelemetry spans → OTLP
- **Observability backend:** [SigNoz](https://signoz.io) (self-hosted via [Foundry](https://github.com/SigNoz/foundry))
- **Tools:** the [SigNoz MCP server](https://github.com/SigNoz/signoz-mcp-server) (Model Context Protocol)

> **Open standards:** Argus emits vendor-neutral OpenTelemetry spans. SigNoz is the backend,
> but the telemetry would flow to any OTLP-compatible backend by changing one endpoint — no code change.

## Architecture

```
incident ─► [Triage] ─plan─► [Investigator] ─findings─► [Reporter] ─► report
                                   │
                                   ▼  (Model Context Protocol)
                          SigNoz MCP server ──► SigNoz API
                                   ▲
   agent's own telemetry (OTLP)  ──┘  every LLM/tool/handoff span ──► SigNoz
```

## Prerequisites
- **Docker Desktop** (running)
- **[Ollama](https://ollama.com)** with the model pulled: `ollama pull qwen3:8b`
- **foundryctl**: `curl -fsSL https://signoz.io/foundry.sh | bash`
- **Python 3.10+**

## Setup & Reproduce

```bash
# 1. Clone
git clone https://github.com/prakharps1305-dev/argus.git
cd argus

# 2. Bring up SigNoz (uses the committed casting.yaml / casting.yaml.lock)
foundryctl cast -f casting.yaml
#   -> SigNoz UI at http://localhost:8080 (create an account on first launch)

# 3. Create a SigNoz API key: Settings -> API Keys -> New Key (ADMIN role).
#    Copy .env.example to .env and paste your key.
cp .env.example .env
#   then edit .env and set SIGNOZ_API_KEY=...

# 4. Python deps
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 5. Start the supporting services (demo app that emits telemetry + the SigNoz MCP server)
./run.sh

# 6. Run the crew
TRACELOOP_BASE_URL=http://localhost:4318 python crew.py
```

Then open SigNoz (http://localhost:8080):
- **Traces** → filter `service.name = 'argus'` → open the `argus_crew` trace to see the crew's reasoning.
- **Dashboards** → "Argus — Agent Observability".

## Files
- `crew.py` — the 3-agent SRE crew (main entrypoint).
- `agent.py` — a single-agent version (built first, for learning/reference).
- `mcp_probe.py` — lists the tools exposed by the SigNoz MCP server.
- `casting.yaml` / `casting.yaml.lock` — Foundry config to reproduce the SigNoz stack.
- `run.sh` — starts the OTel demo app + the SigNoz MCP server.
- `requirements.txt` — pinned Python dependencies.

## Status
🚧 Built during the hackathon (Jul 20–26, 2026).

> **AI disclosure:** AI assistance (Claude) was used to build this project, as permitted and
> declared per the hackathon rules.
