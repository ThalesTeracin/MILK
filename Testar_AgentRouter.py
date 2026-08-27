import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent
SRC=ROOT/"src"
if str(SRC) not in sys.path:
    sys.path.insert(0,str(SRC))

from ai.router import AIRouter

ai=AIRouter()

print("=== TESTE DIRETO AGENTROUTER ===")
print("Status:", ai.status())

if not ai.enabled:
    print("ERRO: configuração não foi carregada do .env")
    raise SystemExit(1)

result=ai.test()

if result.get("ok"):
    print("✅ CONEXÃO COM IA FUNCIONANDO.")
    print("Resposta:", result.get("reply"))
else:
    print("❌ A CONFIGURAÇÃO EXISTE, MAS A API NÃO RESPONDEU.")
    print("Erro:", result.get("error"))
    print("Veja também: C:\\JARVIS\\logs\\ai_router.log")
