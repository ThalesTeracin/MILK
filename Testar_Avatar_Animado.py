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
