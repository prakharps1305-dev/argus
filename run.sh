#!/usr/bin/env bash
# Starts Argus's supporting services:
#   1. the OpenTelemetry demo app (generates telemetry into SigNoz)
#   2. the SigNoz MCP server (the agent's tools)
#
# Prerequisites (see README):
#   - Docker running
#   - SigNoz already up via:  foundryctl cast -f casting.yaml
#   - Ollama running with:    ollama pull qwen3:8b
#   - .env created from .env.example (with your SIGNOZ_API_KEY)
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -f .env ]; then
  echo "ERROR: .env not found. Run: cp .env.example .env  then add your SIGNOZ_API_KEY"
  exit 1
fi

echo "==> Starting the OpenTelemetry demo app..."
if [ ! -d opentelemetry-demo-lite ]; then
  git clone https://github.com/SigNoz/opentelemetry-demo-lite.git
fi
( cd opentelemetry-demo-lite && \
  OTLP_ENDPOINT=host.docker.internal:4317 OTLP_INSECURE=true docker compose up -d )

echo "==> Starting the SigNoz MCP server on :8000..."
docker rm -f signoz-mcp >/dev/null 2>&1 || true
docker run -d --rm --name signoz-mcp -p 8000:8000 --env-file .env \
  -e TRANSPORT_MODE=http -e MCP_SERVER_PORT=8000 \
  signoz/signoz-mcp-server:latest

echo ""
echo "Supporting services are up."
echo "Run the crew with:"
echo "  TRACELOOP_BASE_URL=http://localhost:4318 python crew.py"
