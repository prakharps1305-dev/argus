from traceloop.sdk import Traceloop
from openai import OpenAI

# Start instrumentation FIRST — this wraps the LLM SDK so every call emits a span.
Traceloop.init(app_name="sre-crew", disable_batch=True)

# OpenAI client, but pointed at local Ollama (it speaks the OpenAI API).
client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")

# The one LLM call we want to see appear in SigNoz.
resp = client.chat.completions.create(
    model="qwen3:8b",
    messages=[{"role": "user", "content": "Reply with exactly one word: pong"}],
)

print(resp.choices[0].message.content)