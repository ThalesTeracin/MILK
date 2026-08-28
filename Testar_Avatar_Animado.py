# =============================================================================
# SUBSTITUÍDO (Fase 33 - integração Presence + Avatar + Skills, 2026-08-28).
# O estado de atividade da MILK passou a ter um dono único em
# src/core/activity_state.py, que guarda em memória e publica em
# data/milk_runtime_state.json com carimbo de tempo. Este arquivo pertence
# ao mecanismo anterior, cujos campos (speaking/listening/thinking/emotion/
# last_text) nunca chegaram a ser escritos por ninguém.
# Mantido apenas como referência histórica. Não editar/usar.
# =============================================================================

import sys,time
from pathlib import Path

ROOT=Path(__file__).resolve().parent
SRC=ROOT/"src"
if str(SRC) not in sys.path:
    sys.path.insert(0,str(SRC))

from avatar.runtime_state import update_state, read_state

print("=== FASE 29 - AVATAR ===")
update_state(speaking=True,last_text="Teste de fala")
print(read_state())
time.sleep(1)
update_state(speaking=False,listening=True)
print(read_state())
time.sleep(1)
update_state(listening=False,thinking=True)
print(read_state())
time.sleep(1)
update_state(thinking=False)
print("✅ FASE 29 VALIDADA.")
