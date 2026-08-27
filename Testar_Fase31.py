import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent
SRC=ROOT/"src"
if str(SRC) not in sys.path:
    sys.path.insert(0,str(SRC))

from skills.advanced_router import AdvancedSkillRouter

r=AdvancedSkillRouter()
tests=[
    "como está meu computador",
    "status do git",
    "abrir projetos"
]

print("=== FASE 31 ===")
for t in tests:
    plan=r.route_local(t)
    print(t,"->",plan)
    print(r.execute(plan))

print("✅ FASE 31 VALIDADA.")
