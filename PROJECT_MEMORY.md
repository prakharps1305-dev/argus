# PROJECT MEMORY — "SRE Crew"

> Living source of truth for the build. Update at the end of every phase/step.
> Last updated: 2026-07-21

---

## 1. What we're building

**SRE Crew** — a small multi-agent team that investigates system incidents by querying the
**SigNoz MCP server**, whose *own* reasoning (every LLM call, tool call, handoff, token count,
latency) streams into **SigNoz** via OpenTelemetry GenAI instrumentation, topped with a
**dashboard + alert pack** over the crew's behavior.

The core idea: the crew is **observed BY SigNoz while it works THROUGH SigNoz.** That recursion
is the highest-scoring version of Track 1's "AI & Agent Observability" theme and maxes the
"Best Use of SigNoz" judging criterion.

### The crew (3 agents, hard cap — no more)
1. **Triage** — reads the incident, decides what to look at.
2. **Investigator** — queries SigNoz MCP for traces / metrics / logs.
3. **Reporter** — writes the grounded findings.

### The ONE core loop that must work (walking skeleton)
Incident/question in → crew coordinates → queries SigNoz MCP → grounded answer out → **the whole
run appears as a connected trace in SigNoz.**

---

## 2. Hackathon context

- **Event:** Agents of SigNoz (WeMakeDevs × SigNoz). Track **01 — AI & Agent Observability**.
- **Dates:** Jul 20–26, 2026. **Final submission due Jul 26, 05:29 AM IST. No late submissions.**
- **Prize (Track 01):** MacBook Air per winning team member + job interview opportunities.
- **Hard requirement:** must use/integrate SigNoz. Deeper use of traces/metrics/logs/dashboards/
  alerts = higher score.
- **Reproducibility requirement:** repo MUST include `casting.yaml` and `casting.yaml.lock`
  (judges may re-run Foundry against them).
- **AI-assistant disclosure:** using AI tools is allowed but MUST be declared. Non-disclosure =
  disqualification. (We WILL declare Claude usage.)
- **Judging:** Potential Impact · Creativity & Innovation · Technical Excellence · Best Use of
  SigNoz · User Experience · Presentation Quality.

---

## 3. Chosen stack

- **Agent framework:** Python + a real crew framework (**CrewAI** or **LangGraph** — decide in Phase 4).
  Build the raw tool-calling loop by hand FIRST (Phase 2), then adopt the framework.
- **Instrumentation:** **Traceloop / OpenLLMetry** or **Langtrace** — one-line auto-instrumentation
  that emits OTel GenAI semantic-convention spans → SigNoz. (Both are documented by SigNoz.)
- **Backend:** **SigNoz via Foundry** (installs SigNoz + its MCP server in one step).
- **Test workload:** SigNoz's **OpenTelemetry demo app** (`opentelemetry-demo-lite`) for real telemetry.
- **Stretch:** **n8n** as a second observed workload or as the trigger for the crew (Phase 7 only).

> n8n verdict: wrong tool as the *primary* agent for this project (black box → hard to get clean
> GenAI traces, which are the whole deliverable). Great as an *observed workload* later.

---

## 4. Phase plan

Front-loaded with risk + learning; polish at the back. If time runs out, stop after Phase 5 and
still have a complete, winning project.

| # | Phase | Done when |
|---|-------|-----------|
| 1 | **Foundation & walking skeleton** — SigNoz up via Foundry + demo app + one-file Python script (single LLM call, no crew) instrumented with Traceloop | One LLM call is visible as a span in SigNoz |
| 2 | **The raw agent loop [CORE, by hand]** — one agent, one real tool, hand-written tool-calling loop, no framework | Agent answers by looping over the tool AND I can explain every iteration |
| 3 | **Wire in SigNoz MCP** — connect agent to the real SigNoz MCP server, 2–3 observability tools | Agent answers a real "what's wrong?" grounded in live demo-app telemetry |
| 4 | **Go multi-agent (the crew)** — adopt CrewAI/LangGraph; Triage → Investigator → Reporter | An incident flows through all three; handoffs show as nested spans in SigNoz |
| 5 | **Observability pack** — dashboard (tokens, cost, latency/agent, tool success, run duration) + alerts (runaway loop, cost spike, tool failure) | Dashboard live + ≥2 alerts fire on real runs |
| 6 | **Demo & reproducibility** — scripted chaos → crew detects/explains; `casting.yaml` + `.lock`, README, recorded demo | Judges can re-run via Foundry; demo runs reliably end-to-end |
| 7 | **Stretch: n8n** — n8n workflow as second observed workload or trigger | Only if Phases 1–6 are solid |

---

## 5. Builder profile & skill tree (levels 0–4)

**Builder:** bud — solo, all-in (treating this as a full-time sprint).

| Skill / tech | Level | Notes |
|---|---|---|
| LLM agents (tool-calling loops, orchestration) | 1 | Conceptual only; will learn by building the raw loop first |
| OpenTelemetry / observability (traces, metrics, logs) | 0–1 | New; learning through use |
| Python | ~3 (assumed) | `.venv` + PyCharm present; confirm as we go |
| SigNoz / Foundry / MCP | 0 | New |
| CrewAI / LangGraph | 0 | New |
| n8n | 0 | Wants familiarity (stretch) |

Skill-stack focus (what we train hardest): **problem decomposition, first-principles fundamentals
(what a trace / an agent loop actually is), debugging & verification.**

---

## 6. Work taxonomy (per step)

- **[CORE]** — learning lives here → hand-write it, Socratic coaching. (e.g. the raw agent loop,
  the data model of a trace, tricky crew handoff logic.)
- **[LEVERAGE]** — real work worth delegating well → I spec/prompt AI, then pass the REVIEW GATE
  (explain what the AI wrote + why it's correct before moving on).
- **[TOIL]** — zero-learning boilerplate → delegate freely.

---

## 7. Current state

- **Phase:** 7 — 🔨 IN PROGRESS — web UI + deployability (mostly done; live end-to-end run not yet
  re-verified after UI polish).
- **Next:** run the web UI end-to-end once (confirm streaming + flow diagram animate), then record demo.
- **Project named: Argus.** GitHub: github.com/prakharps1305-dev/argus (branch `main`).

**Phase 7 outcome so far (2026-07-22):**
- `web.py` — FastAPI + SSE streaming web app. Polished dark UI (👁️ Argus) with a LIVE pipeline
  flow diagram (Incident→Triage→Investigator⇄SigNoz MCP→Reporter→Report) that lights up per stage
  and turns RED where a step breaks (empty output or failed tool). Agent detail cards + tool log +
  "view trace in SigNoz" link. Serves on :8500.
- `crew.py` refactored: importable `investigate()`, returns {plan,findings,report}, `emit` progress
  callback (tool events now include ok/error). Config is env-driven: LLM_BASE_URL/LLM_API_KEY/
  LLM_MODEL (pluggable LLM — Ollama default, or OpenAI/Groq/etc.), MCP_URL, ARGUS_APP_NAME.
- Deployability: `Dockerfile`, `docker-compose.yml` (argus + signoz-mcp), `.dockerignore`, MIT
  `LICENSE`, env-driven config, README deploy section. `docker build` VERIFIED OK.
- Decision: n8n NOT used (black box, can't emit the OTel traces that are the thesis). Built the
  "where it breaks" flow visualization natively in the web UI instead — better + integrated.
- ⚠️ Deps: re-froze requirements.txt (now includes fastapi/uvicorn). web.py binds 0.0.0.0 in container.

**Phase 6 outcome (done 2026-07-22):**
- `requirements.txt` (pip freeze, 105 lines), `.env.example` (template, no secret), `run.sh`
  (starts demo app + MCP server), README rewritten with architecture + step-by-step reproduce.
- `.env` stays git-ignored; `.env.example` committed.
- Still TODO for full polish: record demo video; optionally add MCP+demo to a compose file.

**Phase 5 outcome (done 2026-07-22):**
- Instrumentation enriched in `crew.py`: each tool call wrapped in a `tool.<name>` span with
  OK/ERROR status (imports `Status, StatusCode`). Tool calls now visible in the trace + measurable.
- SigNoz dashboard "Argus — Agent Observability": Panel 1 "Agent latency (p99)" = Traces,
  p99(duration_nano), group by `name`, filter `service.name = 'argus'`. Panel 2 "Total crew runs" =
  Value, count() of `name = 'argus_crew'`.
- Alert "Argus crew run too slow": trace-based, p99(duration_nano) of `argus_crew` > 60000000000 ns
  (60s). Required a notification channel — created throwaway webhook channel `noop`
  (http://localhost:9999). Status OK; fires when a run exceeds 60s.
- Query Builder learned: signal=Traces, aggregation p99(duration_nano), group by name, filter service.name.

**Phase 4 outcome (done 2026-07-22):**
- `crew.py` — 3-agent crew: Triage (no tools) -> Investigator (SigNoz tools) -> Reporter (no tools).
  Reusable `run_agent()` (the Phase-2 loop generalized). Chained; each output feeds the next.
- Grouped into ONE trace via MANUAL OpenTelemetry spans: `with tracer.start_as_current_span(...)`
  around `argus_crew` > `triage`/`investigator`/`reporter`; auto-instrumented `openai.chat` spans
  nest inside. Verified as a single nested trace in SigNoz under service `argus`.
- **Verification lesson (big one):** first run produced a confident but WRONG report — Triage
  invented fake service names (`checkout-service`, `payment-gateway`) and Investigator trusted them,
  queried non-existent services, got empty data, concluded "no issues / instrumentation gaps."
  Fixed by prompting: Triage must NOT invent names; Investigator must call `signoz_list_services`
  FIRST and use only real names. Second run: grounded, correct (payment 4.97% errors, email 1.97%,
  checkout/frontend p99 ~30-35s).
- Known rough edges: the empty-answer nudge can leak into a tool arg; Investigator sometimes stops
  after list_services instead of deeper digging. Good enough for now; polish later.

**Phase 3 outcome (done 2026-07-22):**
- SigNoz API key created; stored in `.env` (git-ignored). Key needed **Admin role** — a role-less key
  gave 403; fixed by granting admin. Debug lesson: 401 = not authenticated, 403 = authenticated but
  forbidden (role). Auth header is `SIGNOZ-API-KEY`.
- SigNoz MCP server running: `docker run -d --rm --name signoz-mcp -p 8000:8000 --env-file .env
  -e TRANSPORT_MODE=http -e MCP_SERVER_PORT=8000 signoz/signoz-mcp-server:latest`. Endpoint
  `http://localhost:8000/mcp`. Exposes ~40 `signoz_*` tools.
- `mcp_probe.py` — lists MCP tools. `argus.py` — the real agent: connects to MCP (streamable HTTP),
  converts a safe subset of tools to OpenAI schema, runs the Phase-2 loop but executes tools via
  `session.call_tool()`. Exposes 4 read tools: list_services, get_service_top_operations,
  aggregate_traces, search_logs.
- Verified: agent queried live demo telemetry and produced a real health summary. **The recursion is
  live** — the agent saw a service named `argus` (its own Traceloop telemetry) and reported its own errors.
- Deps added: `mcp`. Known rough edges (qwen3:8b): rambly answers, occasional tool hallucination,
  shallow investigation — to improve in Phase 4 with focused roles/prompts.
- ⚠️ MCP container is `--rm` (disappears on stop) and started manually — Phase 6 should add it to
  docker-compose/casting for reproducibility.

**Phase 2 outcome (done 2026-07-22):**
- `agent.py`: hand-written tool-calling loop. One fake tool `get_service_error_rate` + its JSON schema.
  Loop = call model → if tool_call, run function via `available_tools[name](**args)`, append result
  (role "tool"), call model again → until plain answer. Safety cap `for step in range(5)`.
- Verified: one run → two `openai.chat` spans in SigNoz (iter 1 = tool request, iter 2 = final answer).
- bud fully understands agent.py line-by-line (passed review gate). **Agent fundamentals now L3.**
- Note: the two model calls currently show as SEPARATE traces. Phase 4 will group a full agent run
  into ONE trace (Traceloop @workflow / framework) — that's the "nested spans" done-when.

**Phase 1 outcome (done 2026-07-22):**
- Docker Desktop running on Mac (Apple Silicon).
- `foundryctl` v0.2.16 installed at `~/.local/bin` (added to PATH in `~/.zshrc`).
- SigNoz running via Foundry (`casting.yaml` in repo). UI: http://localhost:8080. OTLP in: `:4317` gRPC / `:4318` HTTP.
- OTel demo (`opentelemetry-demo-lite/`) running, streaming traces/metrics/logs to SigNoz
  (started with `OTLP_ENDPOINT=host.docker.internal:4317 OTLP_INSECURE=true docker compose up -d`).
- `main.py`: single LLM call via OpenAI SDK → local Ollama (`qwen3:8b`), auto-instrumented with
  Traceloop → span `openai.chat` visible in SigNoz under service `sre-crew`.
  Run cmd: `TRACELOOP_BASE_URL=http://localhost:4318 python main.py`.

**Environment facts to remember:**
- LLM: local **Ollama**, model **`qwen3:8b`** (a "thinking" model — verbose; tame later). API: `http://localhost:11434/v1` (OpenAI-compatible), dummy key `"ollama"`.
- Python venv at `.venv` in project root (Python 3.12). Deps so far: `traceloop-sdk`, `openai`.
- Instrumentation → SigNoz self-hosted via env `TRACELOOP_BASE_URL=http://localhost:4318` (no ingestion key).
- ⚠️ Open risk: small local models are weak at tool-calling (needed Phase 4) — may need bigger model or a cloud key fallback.

---

## 8. Key links (from Info.md)

- Hackathon: https://www.wemakedevs.org/hackathons/signoz
- Foundry intro: https://signoz.io/blog/introducing-signoz-foundry
- Casting file ref: https://github.com/SigNoz/foundry/blob/main/docs/reference/casting-file.md
- Compose + MCP example: https://github.com/SigNoz/foundry/tree/main/docs/examples/docker/compose-mcp
- SigNoz MCP server: https://signoz.io/docs/ai/signoz-mcp-server/ · https://github.com/SigNoz/signoz-mcp-server
- SigNoz agent skills (Claude plugin): https://github.com/SigNoz/agent-skills
- OTel demo app: https://github.com/SigNoz/opentelemetry-demo-lite
- GenAI semantic conventions: https://opentelemetry.io/docs/specs/semconv/gen-ai/
- LLM monitoring — Traceloop: https://signoz.io/docs/traceloop/ · Langtrace: https://signoz.io/docs/langtrace/
- Query Builder: https://signoz.io/docs/userguide/query-builder-v5/
- Dashboards: https://signoz.io/docs/userguide/manage-dashboards/ · Alerts: https://signoz.io/docs/alerts/
- Full briefing: `Info.md`
