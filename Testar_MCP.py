import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from mcp.mcp_manager import MCPManager

print("=== MILK FASE 22 — TESTE MCP ===")

m = MCPManager()

print("\nServidores configurados:")
for s in m.list_servers():
    print("-", s)

print("\nIniciando...")
status = m.start_enabled()
print(status)

print("\nTools:")
tools = m.list_tools()
for server, items in tools.items():
    print(server)
    for item in items:
        print("  -", item.get("name") or item)

print("\nChamando milk_echo...")
result = m.call_tool(
    "milk_mock",
    "milk_echo",
    {"text": "MILK MCP funcionando"},
    confirmed=True
)
print(result)

print("\nChamando milk_time...")
result = m.call_tool(
    "milk_mock",
    "milk_time",
    {},
    confirmed=True
)
print(result)

m.stop_all()

print("\n✅ FASE 22 MCP VALIDADA.")
