import json
from pathlib import Path
import sounddevice as sd

CONFIG=Path("config/audio_device.json")
CONFIG.parent.mkdir(parents=True,exist_ok=True)

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
