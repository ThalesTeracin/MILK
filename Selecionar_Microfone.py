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

devices = sd.query_devices()
print("=== MICROFONES DISPONÍVEIS ===")
valid = []

for i, d in enumerate(devices):
    if int(d["max_input_channels"]) > 0:
        valid.append(i)
        host = sd.query_hostapis(d["hostapi"])["name"]
        print(
            f"[{i}] {d['name']} | {host}"
            f" | entradas: {d['max_input_channels']}"
            f" | taxa: {int(float(d['default_samplerate']))} Hz"
        )

# A host API aparece na lista porque ela decide se o microfone funciona:
# o Windows WDM-KS não abre em modo bloqueante, que é como o listener
# grava, e falha com "Blocking API not supported yet". Prefira WASAPI.
print("\nPrefira uma entrada Windows WASAPI. As WDM-KS não abrem para gravar.")

choice = input("\nDigite o número do microfone: ").strip()
idx = int(choice)

if idx not in valid:
    print("Dispositivo inválido.")
    raise SystemExit(1)

escolhido = devices[idx]
host_api = sd.query_hostapis(escolhido["hostapi"])["name"]

# O índice vai junto só como registro do que foi escolhido nesta máquina.
# Quem manda na abertura é o nome: o índice é a posição na lista do
# PortAudio, e conectar ou tirar um fone renumera tudo o que vem depois.
CONFIG.write_text(
    json.dumps(
        {
            "input_name": escolhido["name"],
            "input_hostapi": host_api,
            "input_device": idx,
        },
        indent=2,
        ensure_ascii=False,
    ),
    encoding="utf-8",
)
print(f"\n✅ Microfone salvo: {escolhido['name']} | {host_api}")
print(r"Agora rode: python .\Conversar_Com_MILK.py")
