FROM python:3.12-slim

WORKDIR /app

# Install deps first (better layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App code
COPY crew.py web.py ./

EXPOSE 8500

# web.py reads HOST/PORT + LLM_*/MCP_URL/SIGNOZ_WEB_URL/TRACELOOP_BASE_URL from env
CMD ["python", "web.py"]
