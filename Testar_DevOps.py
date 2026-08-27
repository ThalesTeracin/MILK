import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent
SRC=ROOT/"src"
if str(SRC) not in sys.path:
    sys.path.insert(0,str(SRC))

from devops.devops_manager import DevOpsManager

d=DevOpsManager()

print("=== MILK FASE 19 - TESTE DEVOPS ===")

ok_git, git_ver = d.git.git_available()
print("Git:", "OK" if ok_git else "ERRO", "-", git_ver)

ok_gh, gh_ver = d.github.gh_available()
print("GitHub CLI:", "OK" if ok_gh else "NÃO INSTALADO", "-", gh_ver)

print("\nTeste de status em C:\\JARVIS:")
print(d.git.status(r"C:\JARVIS"))

print("\nPronto.")
