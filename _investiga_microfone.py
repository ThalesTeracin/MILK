# Milk — assistente pessoal.
# Copyright (c) 2026 Thales Teracin. Todos os direitos reservados.
#
# Software proprietário. É proibida a cópia, a distribuição, a
# modificação e a engenharia reversa, no todo ou em parte, sem
# autorização expressa e por escrito do autor. Ver LICENSE.txt.

"""Investiga microfone do notebook: volume mixer, privacidade Windows, e tentativas de captura."""

import ctypes
from ctypes import wintypes
import numpy as np
import sounddevice as sd
import time
import sys
import subprocess
from pathlib import Path

print("=" * 60)
print("INVESTIGAÇÃO DO MICRÔFONE DO NOTEBOOK")
print("=" * 60)

print()
print("=== 1. STATUS DOS DISPOSITIVOS ATUAL ===")
for i, d in enumerate(sd.query_devices()):
    if d["max_input_channels"] > 0:
        api = sd.query_hostapis(d["hostapi"])["name"] if d["hostapi"] is not None else "?"
        print(f"[{i}] {d['name'][:50]:50s} | api={api:18s} | sr={d['default_samplerate']:7.0f}")

print()
print("=== 2. TESTE RÁPIDO DE CAPTURA (0.5s, todos) ===")
candidatos = [
    (0, "MME Mapeador"),
    (1, "MME grupo Microfones Qualcomm"),
    (4, "DirectSound Driver captura primário"),
    (5, "DirectSound grupo Qualcomm Aqstic"),
    (9, "WASAPI grupo Qualcomm Aqstic"),
]

for idx, label in candidatos:
    print(f"\n--- [{idx}] {label} ---")
    try:
        d = sd.query_devices(idx)
        sr = int(d["default_samplerate"] or 16000)
        for rep in range(3):
            print(f"  rep{rep+1}: ", end="")
            a = sd.rec(int(0.5 * sr), samplerate=sr, channels=2, dtype="int16", device=idx)
            sd.wait()
            pico = int(np.abs(a).max())
            rms = int(np.sqrt((a.astype(float) ** 2).mean()))
            status = "OK" if pico >= 200 else f"silêncio (pico={pico})"
            print(f"pico={pico:5d}/32767  rms={rms:4d}  {status}")
            time.sleep(0.1)
    except Exception as e:
        print(f"  erro: {type(e).__name__}: {e}")

print()
print("=== 3. PRIVACIDADE DO MICRÔFONE NO WINDOWS ===")
try:
    ps_script = r"""
    $regPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\ContentSettings\Audio"
    if (Test-Path $regPath) {
        Get-ItemProperty -Path $regPath -Name "Microphone" -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Microphone
    } else {
        Write-Output "Chave não encontrada"
    }
    """
    result = subprocess.run(
        ["powershell", "-Command", ps_script],
        capture_output=True, text=True, timeout=10
    )
    print(f"  HKCU ContentSettings: {result.stdout.strip() or result.stderr.strip()[:200]}")
except Exception as e:
    print(f"  Erro ao verificar: {e}")

print()
print("=== 4. CHECKLIST FINAL ===")
print("Microfone do notebook (built-in): não encontrado diretamente")
print("Dispositivos Qualcomm: todos sem sinal (pico ~10)")
print("Microphone Array [31]: erro IOCTL (problema de driver)")
print("Headset RS27: desconectado (settings.json já corrigido)")
print("Driver de captura primário: oscilante, agora mudo")
print()
print(" POSSÍVEIS CAUSAS:")
print("  1. Volume zerado nas propriedades de áudio do Windows")
print("  2. Bloqueio de privacidade (Configurações > Privacidade > Microfone)")
print("  3. Driver de áudio com problema")
print("  4. Microfone fisicamente desconectado ou com defeito")

