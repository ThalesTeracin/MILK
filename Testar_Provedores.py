"""
Mostra a cadeia de provedores da MILK e testa cada um de verdade.

Antes este script chamava router.interpret(), método que não existe na
classe -- quebrava com AttributeError antes de testar coisa alguma. E
importava por src.ai.router, fora da convenção do projeto (src/ no
sys.path, import por ai.router), o que passou a falhar quando o router
ganhou dependência de core.config.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai.router import AIRouter

router = AIRouter()

print("=== MILK - Cadeia de provedores ===")
print("Ativo:", router.status())

if not router.enabled:
    print()
    print("Nenhum provedor configurado.")
    print("Rode: python .\\Configurar_Provedores.py")
    raise SystemExit(1)

print()
print("Ordem de tentativa:")
for posicao, provedor in enumerate(router.provedores, start=1):
    print(f"  {posicao}. {provedor.label} -- {provedor.base_url} [{provedor.model}]")

print()
no_ar = 0

for provedor in router.provedores:
    # Cada provedor e testado sozinho: pelo router inteiro a checagem
    # pararia no primeiro que funcionasse, e a graca da reserva e saber
    # se ela responde ANTES de precisar dela.
    solo = AIRouter()
    solo.provedores = [provedor]
    resultado = solo.test()

    if resultado["ok"]:
        no_ar += 1
        print(f"[no ar]  {provedor.label}: {resultado['reply'][:60]}")
    else:
        # test() so devolve "error" quando a chamada falhou. Respondendo
        # 200 com conteudo vazio -- tipico de modelo de raciocinio que
        # gastou o orcamento pensando -- nao existe chave "error".
        motivo = resultado.get("error") or "respondeu vazio (veja logs/ai_router.log)"
        print(f"[fora]   {provedor.label}: {motivo}")

print()
if no_ar:
    print(f"TESTE OK -- {no_ar} de {len(router.provedores)} provedores no ar.")
else:
    print("Nenhum provedor da cadeia respondeu.")
    raise SystemExit(1)
