# =============================================================================
# SUBSTITUÍDO (Fase 33 - integração Presence + Avatar + Skills, 2026-08-28).
# O formato de retorno das skills mudou: cada skill agora devolve
# {"ok", "fala", "dados"} e passa pelo PermissionManager do perfil
# (config/permission_profiles.json), não mais pelo conjunto RISKY próprio
# do router. Este script ainda monta o AdvancedSkillRouter sem
# `permissions` e espera os dicionários no formato antigo ({"result": ...}),
# então toda chamada a execute() aqui volta com "ok": False (gate ausente).
# Mantido apenas como referência histórica. Não editar/usar.
# A cobertura real está em tests/test_skill_router.py.
# =============================================================================

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
