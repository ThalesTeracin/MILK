import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import json
import sounddevice as sd

from core.config import LOCAL_DIR

# Escreve sempre em config/local/: é configuração desta máquina, e no
# diretório versionado seria sobrescrita na próxima atualização.
CONFIG = LOCAL_DIR / "audio_device.json"
CONFIG.parent.mkdir(parents=True, exist_ok=True)

devices=sd.query_devices()
print("=== MICROFONES DISPONÍVEIS ===")
valid=[]

for i,d in enumerate(devices):
    if int(d["max_input_channels"])>0:
        valid.append(i)
        print(f"[{i}] {d['name']} | entradas: {d['max_input_channels']} | taxa: {int(float(d['default_samplerate']))} Hz")

choice=input("\nDigite o número do microfone: ").strip()
idx=int(choice)

if idx not in valid:
    print("Dispositivo inválido.")
    raise SystemExit(1)

CONFIG.write_text(json.dumps({"input_device":idx},indent=2),encoding="utf-8")
print(f"\n✅ Microfone salvo: {devices[idx]['name']}")
print(r"Agora rode: python .\Conversar_Com_MILK.py")
