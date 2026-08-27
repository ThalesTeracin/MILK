"""
Configuração compartilhada dos testes.

Garante que os módulos em src/ sejam importáveis (o projeto importa como
`core.orchestrator`, `security.permission_manager`, etc. -- sem prefixo
`src.`), replicando o sys.path usado em produção (main.py roda com
cwd=C:\\JARVIS e src/ no caminho de import).
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
