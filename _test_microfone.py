# Milk — assistente pessoal.
# Copyright (c) 2026 Thales Teracin. Todos os direitos reservados.
#
# Software proprietário. É proibida a cópia, a distribuição, a
# modificação e a engenharia reversa, no todo ou em parte, sem
# autorização expressa e por escrito do autor. Ver LICENSE.txt.

"""Investiga microfone do notebook: dispositivos waveIn/waveOut, volume do mixer."""

import ctypes
from ctypes import wintypes

print("=== waveIn (dispositivos de entrada) ===")
waveInGetNumDevs = ctypes.windll.winmm.waveInGetNumDevs
num_devs = waveInGetNumDevs()
print(f"Total: {num_devs} dispositivos de entrada")

class WAVEINCAPS(ctypes.Structure):
    _fields_ = [
        ("wMid", wintypes.WORD),
        ("wPid", wintypes.WORD),
        ("vDriverVersion", wintypes.DWORD),
        ("szPname", wintypes.CHAR * 32),
        ("dwFormats", wintypes.DWORD),
        ("wChannels", wintypes.WORD),
        ("wReserved1", wintypes.WORD),
    ]

for i in range(num_devs):
    caps = WAVEINCAPS()
    r = ctypes.windll.winmm.waveInGetDevCapsW(i, ctypes.byref(caps), ctypes.sizeof(caps))
    if r == 0:
        name = caps.szPname.decode("utf-8", errors="replace").rstrip()
        print(f"  [{i}] {name[:60]} | canais={caps.wChannels} | fmt=0x{caps.dwFormats:x}")

print()
print("=== waveOut (dispositivos de saída) ===")
waveOutGetNumDevs = ctypes.windll.winmm.waveOutGetNumDevs
num_out = waveOutGetNumDevs()
print(f"Total: {num_out} dispositivos de saída")

class WAVEOUTCAPS(ctypes.Structure):
    _fields_ = [
        ("wMid", wintypes.WORD),
        ("wPid", wintypes.WORD),
        ("vDriverVersion", wintypes.DWORD),
        ("szPname", wintypes.CHAR * 32),
        ("dwFormats", wintypes.DWORD),
        ("wChannels", wintypes.WORD),
        ("wReserved1", wintypes.WORD),
    ]

for i in range(num_out):
    caps = WAVEOUTCAPS()
    r = ctypes.windll.winmm.waveOutGetDevCapsW(i, ctypes.byref(caps), ctypes.sizeof(caps))
    if r == 0:
        name = caps.szPname.decode("utf-8", errors="replace").rstrip()
        print(f"  [{i}] {name[:60]} | canais={caps.wChannels} | fmt=0x{caps.dwFormats:x}")

print()
print("=== Mixer: dispositivos de linha de áudio ===")
mixerGetNumDevs = ctypes.windll.winmm.mixerGetNumDevs
num_mixer = mixerGetNumDevs()
print(f"Total: {num_mixer} dispositivos de mixer")

class MIXERCAPS(ctypes.Structure):
    _fields_ = [
        ("wMid", wintypes.WORD),
        ("wPid", wintypes.WORD),
        ("vDriverVersion", wintypes.DWORD),
        ("vVendorVersion", wintypes.DWORD),
        ("dwProducts", wintypes.DWORD),
        ("szPname", wintypes.CHAR * 32),
        ("dwFlags", wintypes.DWORD),
    ]

for i in range(num_mixer):
    caps = MIXERCAPS()
    r = ctypes.windll.winmm.mixerGetDevCapsW(i, ctypes.byref(caps), ctypes.sizeof(caps))
    if r == 0:
        name = caps.szPname.decode("utf-8", errors="replace").rstrip()
        print(f"  [{i}] {name[:50]} | flags=0x{caps.dwFlags:x}")

print()
print("=== Volume das linhas do mixer (busca linhas de microfone) ===")
# para cada mixer, enumera as linhas
for dev in range(num_mixer):
    caps = MIXERCAPS()
    ctypes.windll.winmm.mixerGetDevCapsW(dev, ctypes.byref(caps), ctypes.sizeof(caps))
    name = caps.szPname.decode("utf-8", errors="replace").rstrip()
    print(f"--- Mixer [{dev}] {name} ---")
    
    # enumera linhas
    for hwid in range(10):
        # mixerGetLineInfo
        from ctypes import POINTER
        class MIXERLINE(ctypes.Structure):
            _fields_ = [
                ("cbVolume", wintypes.DWORD),
                ("dwHandler", wintypes.DWORD),
                ("dwPar", wintypes.DWORD * 4),
                ("fdwLine", wintypes.DWORD),
                ("dwSeed", wintypes.DWORD),
                ("dwPeak", wintypes.DWORD),
                ("dwPos", wintypes.DWORD),
                ("dwTime", wintypes.DWORD),
                ("cChannels", wintypes.DWORD),
                ("szName", wintypes.CHAR * 20),
            ]
        line = MIXERLINE()
        line.cbVolume = ctypes.sizeof(line)
        r = ctypes.windll.winmm.mixerGetLineInfoW(
            dev, ctypes.byref(line), 
            ctypes.sizeof(line) | 0x10000  # MIXER_GETLINEINFOF_LINEINDEX
        )
        if r != 0:
            break  # no more lines
        line_name = line.szName.decode("utf-8", errors="replace").rstrip()
        fdw = line.fdwLine
        is_input = bool(fdw & 0x00000010)  # MIXERLINE_LINEIN
        is_output = bool(fdw & 0x00000020)  # MIXERLINE_LINEOUT
        is_mic = 'mic' in line_name.lower() or 'microfone' in line_name.lower() or 'microphone' in line_name.lower()
        if is_input or is_mic:
            print(f"  LINEHWID={hwid} | {line_name} | fdw=0x{fdw:x} | canais={line.cChannels}")
            
            # tenta pegar volume
            if line.cChannels >= 1:
                from ctypes import POINTER
                class MIXERCONTROLDETAILS(ctypes.Structure):
                    _fields_ = [
                        ("cbDetails", wintypes.DWORD),
                        ("dwParam1", wintypes.DWORD),
                        ("dwParam2", wintypes.DWORD),
                        ("cChannels", wintypes.DWORD),
                        ("cControls", wintypes.DWORD),
                        ("hePriority", ctypes.c_void_p),
                        ("szName", wintypes.CHAR * 20),
                        ("dwType", wintypes.DWORD),
                        ("dwReserved", wintypes.DWORD * 4),
                    ]
                # Isso eh complexo. Simplificacao: usar o mixerGetControl para volume
                pass

print()
print("=== Testando: tocar latido e captar simultaneamente ===")
import sounddevice as sd
import numpy as np
import time
import sys
sys.path.insert(0, "C:/AssistenteAvatar")

# Toca o latido no alto-falante
from PySide6.QtCore import QSoundEffect
from PySide6.QtMultimedia import QAudioOutput
from pathlib import Path

# Usar sounddevice para reproduzir um pulso de teste
print("Gerando pulso de teste de 1kHz por 0.5s no alto-falante...")
sr = 44100
t = np.linspace(0, 0.5, int(sr * 0.5))
tone = (np.sin(2 * np.pi * 1000 * t) * 0.5 * 32767).astype(np.int16)

# reproduzir via sounddevice no output [3] (Alto-falantes Qualcomm)
try:
    sd.play(tone, samplerate=sr, device=3, blocking=True)
    print("Pulso tocado.")
except Exception as e:
    print(f"Falha ao tocar: {e}")

print()
print("Captando simultaneamente em todos os dispositivos de entrada enquanto o pulso tocava...")
# já que o pulso acabou, vamos repetir o processo de forma sincronizada

for idx, label in [(0, "MME Mapeador"), (4, "DirectSound primário"), (9, "WASAPI")]:
    print(f"--- [{idx}] {label} ---")
    try:
        d = sd.query_devices(idx)
        sr_d = int(d["default_samplerate"] or 16000)
        # Gera o pulso novamente
        t2 = np.linspace(0, 0.5, int(sr_d * 0.5))
        tone2 = (np.sin(2 * np.pi * 1000 * t2) * 0.5 * 32767).astype(np.int16)
        
        # Reproduz e capta "ao mesmo tempo" (não sincronizado, aprox)
        import threading
        captado = []
        def gravar():
            a = sd.rec(int(0.6 * sr_d), samplerate=sr_d, channels=2, dtype="int16", device=idx)
            sd.wait()
            captado.append(a)
        
        th = threading.Thread(target=gravar)
        th.start()
        time.sleep(0.02)  # pequena latência antes de tocar
        sd.play(tone2, samplerate=sr_d, device=3, blocking=True)
        th.join()
        
        if captado:
            a = captado[0]
            pico = int(np.abs(a).max())
            # canal do pulso deve aparecer se o microfone capta o alto-falante
            print(f"  pico={pico} | {'★ CAPTOU O PULSO' if pico > 500 else 'não captou'}")
    except Exception as e:
        print(f"  erro: {e}")
