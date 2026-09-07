# Milk — assistente pessoal.
# Copyright (c) 2026 Thales Teracin. Todos os direitos reservados.
#
# Software proprietário. É proibida a cópia, a distribuição, a
# modificação e a engenharia reversa, no todo ou em parte, sem
# autorização expressa e por escrito do autor. Ver LICENSE.txt.

"""Investiga o microfone do notebook: verifica estado do dispositivo real, tenta array, multiple testes."""

import ctypes
import numpy as np
import sounddevice as sd
import time
import sys

print("=== Dispositivos de entrada relevantes ===")
for i, d in enumerate(sd.query_devices()):
    if d["max_input_channels"] > 0:
        api_name = sd.query_hostapis(d["hostapi"])["name"] if d["hostapi"] is not None else "?"
        print(f"[{i:2d}] {d['name'][:55]:55s} | api={api_name:18s} | sr={d['default_samplerate']:7.0f} | ch={d['max_input_channels']}")

print()
print("=== Determina qual é o microfone do notebook ===")
# O microfone do notebook costuma ser o "Microphone Array" ou o "Grupo de Microfones Qualcomm"
# Nos dois primeiros testes, MME [1] e DirectSound [4] e [5] e WASAPI [9] funcionavam com pico > 2000
# Agora todos dao ~11. Alguem alterou o volume ou desativou?

print()
print("=== Testes múltiplos (3 reps, 0.5s) em cada dispositivo relevante ===")
candidatos = [
    (0, "MME Mapeador de som"),
    (1, "MME Grupo Microfones Qualcomm"),
    (4, "DirectSound Driver captura primário"),
    (5, "DirectSound Grupo Qualcomm Aqstic"),
    (9, "WASAPI Grupo Qualcomm Aqstic"),
    (31, "WDM-KS Microphone Array - Front"),
]

for idx, label in candidatos:
    print(f"--- [{idx}] {label} ---")
    try:
        d = sd.query_devices(idx)
        sr = int(d["default_samplerate"] or 16000)
        ch = min(d["max_input_channels"], 2)
        for rep in range(3):
            a = sd.rec(int(0.5 * sr), samplerate=sr, channels=ch, dtype="int16", device=idx)
            sd.wait()
            pico = int(np.abs(a).max())
            rms = int(np.sqrt((a.astype(float) ** 2).mean()))
            status = "★ OK" if pico >= 200 else f"silêncio (pico={pico})"
            print(f"  rep{rep+1}: pico={pico:5d}/32767  rms={rms:4d}  {status}")
            time.sleep(0.05)
    except Exception as e:
        print(f"  erro: {type(e).__name__}: {e}")
    print()

print()
print("=== Tentativa de captura no Microphone Array [31] com diferentes taxas e canais ===")
# O erro foi 'Failed to read capture position register (IOCTL)' - pode ser
# incompatibilidade de taxa ou nmero de canais
for sr_test in [44100, 48000, 16000, 8000]:
    for ch_test in [1, 2]:
        try:
            a = sd.rec(int(0.3 * sr_test), samplerate=sr_test, channels=ch_test, dtype="int16", device=31)
            sd.wait()
            pico = int(np.abs(a).max())
            print(f"  sr={sr_test}, ch={ch_test}: pico={pico} {'★ OK' if pico > 100 else 'silêncio'}")
        except Exception as e:
            errname = type(e).__name__
            print(f"  sr={sr_test}, ch={ch_test}: {errname} (não testado)")
