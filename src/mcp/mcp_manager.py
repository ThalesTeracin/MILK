import json
import os
from pathlib import Path
from .mcp_client import MCPClient

CONFIG = Path("config/mcp_servers.json")
LOG = Path("logs/mcp.log")

RISKY_WORDS = (
    "delete", "remove", "send", "publish", "push", "create_pr",
    "deploy", "write", "update", "execute", "shell", "command"
)

class MCPManager:
    def __init__(self):
        self.clients = {}
        self.registry = self._load_registry()

    def _log(self, text):
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with LOG.open("a", encoding="utf-8") as f:
            f.write(text + "\n")

    def _load_registry(self):
        if not CONFIG.exists():
            return {"servers": []}
        return json.loads(CONFIG.read_text(encoding="utf-8"))

    def list_servers(self):
        return [
            {
                "name": s.get("name"),
                "enabled": s.get("enabled", False),
                "trusted": s.get("trusted", False)
            }
            for s in self.registry.get("servers", [])
        ]

    def start_enabled(self):
        out = {}
        for s in self.registry.get("servers", []):
            if not s.get("enabled", False):
                continue

            name = s["name"]
            command = s["command"]
            args = s.get("args", [])
            cwd = s.get("cwd")

            client = MCPClient(
                name=name,
                command=command,
                args=args,
                cwd=cwd
            )

            try:
                client.start()
                self.clients[name] = client
                tools = client.list_tools()
                out[name] = {
                    "ok": True,
                    "tools": [t.get("name") for t in tools]
                }
                self._log(f"{name}: iniciado com {len(tools)} tools.")
            except Exception as e:
                out[name] = {"ok": False, "error": str(e)}
                self._log(f"{name}: ERRO {e}")
        return out

    def stop_all(self):
        for c in self.clients.values():
            c.stop()
        self.clients.clear()

    def list_tools(self):
        result = {}
        for name, client in self.clients.items():
            try:
                result[name] = client.list_tools()
            except Exception as e:
                result[name] = [{"error": str(e)}]
        return result

    def is_risky(self, server_name, tool_name):
        server = next(
            (s for s in self.registry.get("servers", []) if s.get("name") == server_name),
            None
        )
        if not server:
            return True

        if tool_name in server.get("always_confirm", []):
            return True

        low = tool_name.lower()
        if any(w in low for w in RISKY_WORDS):
            return True

        return not server.get("trusted", False)

    def call_tool(self, server_name, tool_name, arguments=None, confirmed=False):
        if server_name not in self.clients:
            raise RuntimeError(f"Servidor MCP '{server_name}' não está iniciado.")

        if self.is_risky(server_name, tool_name) and not confirmed:
            return {
                "requires_confirmation": True,
                "server": server_name,
                "tool": tool_name,
                "arguments": arguments or {}
            }

        result = self.clients[server_name].call_tool(tool_name, arguments or {})
        self._log(f"{server_name}.{tool_name}: executado.")
        return {
            "requires_confirmation": False,
            "result": result
        }
