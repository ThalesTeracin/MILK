import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai.router import AIRouter
from documents.document_manager import DocumentManager

ai = AIRouter()
print("AI:", ai.status())

if not ai.enabled:
    print("Configure pelo menos um provedor no arquivo .env.")
    raise SystemExit(1)

mgr = DocumentManager(ai)
pedido = input("Digite um pedido de documento: ").strip()
resultado = mgr.create_from_request(pedido)
print(resultado)
