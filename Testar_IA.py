"""
Teste rápido da IA: uma pergunta pela cadeia de provedores.

Corrige duas heranças: o import por src.ai.router (fora da convenção
do projeto, que põe src/ no sys.path) e a chamada a router.interpret(),
método que não existe na classe.

Para ver provedor por provedor, use Testar_Provedores.py.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai.router import AIRouter

router = AIRouter()
print("AI Router:", router.status())

if not router.enabled:
    print("ERRO: rode primeiro: python .\\Configurar_Provedores.py")
    raise SystemExit(1)

resposta = router.chat(
    "Você é a MILK. Responda em uma frase curta.",
    "Diga que está no ar e qual é o seu nome.",
)
print("Resposta:", resposta)

if resposta:
    print("TESTE OK")
else:
    print("Falha ao consultar a cadeia:", router.last_error)
    raise SystemExit(1)
