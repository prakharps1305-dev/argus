import json
from traceloop.sdk import Traceloop
from openai import OpenAI

# Instrumentation on, so every model call shows up in SigNoz.
Traceloop.init(app_name="sre-crew", disable_batch=True)

client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")


# ---- The tool (plain Python function) ----
def get_service_error_rate(service: str) -> str:
    """Return the recent error rate for a given service."""
    fake_data = {
        "frontend": 0.2,
        "cart": 12.5,
        "checkout": 0.1,
        "payment": 8.3,
    }
    rate = fake_data.get(service)
    if rate is None:
        return f"No data found for service '{service}'."
    return f"Service '{service}' error rate: {rate}% over the last 5 minutes."


# ---- The tool SCHEMA: how the model learns this tool exists ----
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_service_error_rate",
            "description": "Get the recent error rate (percentage) for a given service name.",
            "parameters": {
                "type": "object",
                "properties": {
                    "service": {
                        "type": "string",
                        "description": "The service name, e.g. 'cart' or 'payment'.",
                    }
                },
                "required": ["service"],
            },
        },
    }
]

# Map the tool NAME (what the model says) -> the real Python function (what we run).
available_tools = {
    "get_service_error_rate": get_service_error_rate,
}


# ---- The agent loop ----
messages = [{"role": "user", "content": "Is the cart service healthy right now?"}]

for step in range(5):  # safety cap: never loop more than 5 times
    resp = client.chat.completions.create(
        model="qwen3:8b",
        messages=messages,
        tools=tools,
    )
    msg = resp.choices[0].message

    # CASE A: model gave a plain answer (no tool requested) -> we're done.
    if not msg.tool_calls:
        print("\nFINAL ANSWER:", msg.content)
        break

    # CASE B: model requested tool(s). First, record its request in the conversation.
    messages.append({
        "role": "assistant",
        "content": msg.content,
        "tool_calls": [
            {
                "id": tc.id,
                "type": "function",
                "function": {"name": tc.function.name, "arguments": tc.function.arguments},
            }
            for tc in msg.tool_calls
        ],
    })

    # Then run each requested tool and feed its result back into the conversation.
    for tc in msg.tool_calls:
        name = tc.function.name
        args = json.loads(tc.function.arguments)   # the model sends args as a JSON string
        result = available_tools[name](**args)     # actually run the Python function
        print(f"[ran tool] {name}({args}) -> {result}")
        messages.append({
            "role": "tool",
            "tool_call_id": tc.id,
            "content": result,
        })
    # loop repeats: model is called again, now WITH the tool result available.
