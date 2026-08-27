import json
import sys
from pathlib import Path
from datetime import datetime

def send(obj):
    sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n")
    sys.stdout.flush()

TOOLS = [
    {
        "name": "milk_echo",
        "description": "Repete um texto para validar a integração MCP.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string"}
            },
            "required": ["text"]
        }
    },
    {
        "name": "milk_time",
        "description": "Retorna a hora atual.",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    }
]

for raw in sys.stdin:
    raw = raw.strip()
    if not raw:
        continue

    try:
        req = json.loads(raw)
    except Exception:
        continue

    method = req.get("method")
    req_id = req.get("id")

    if method == "initialize":
        send({
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2025-03-26",
                "capabilities": {"tools": {}},
                "serverInfo": {
                    "name": "MILK Mock MCP",
                    "version": "1.0"
                }
            }
        })

    elif method == "notifications/initialized":
        pass

    elif method == "tools/list":
        send({
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"tools": TOOLS}
        })

    elif method == "tools/call":
        params = req.get("params", {})
        name = params.get("name")
        args = params.get("arguments", {})

        if name == "milk_echo":
            text = args.get("text", "")
            send({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {"type": "text", "text": f"Echo MCP: {text}"}
                    ]
                }
            })

        elif name == "milk_time":
            send({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {"type": "text", "text": datetime.now().strftime("%H:%M:%S")}
                    ]
                }
            })

        else:
            send({
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {
                    "code": -32601,
                    "message": "Tool não encontrada"
                }
            })
