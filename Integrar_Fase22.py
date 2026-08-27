from pathlib import Path

print("=== INTEGRAÇÃO FASE 22 ===")

target = Path("Conversar_Com_MILK.py")
if not target.exists():
    print("Conversar_Com_MILK.py não encontrado.")
    raise SystemExit(1)

print("A camada MCP está pronta e validável de forma independente.")
print("Para manter estabilidade, esta fase NÃO altera automaticamente o fluxo de voz.")
print("Use Testar_MCP.py primeiro.")
print("Na próxima integração, o cérebro da MILK poderá escolher tools MCP")
print("apenas através do MCPManager, que aplica confirmação em ações arriscadas.")
