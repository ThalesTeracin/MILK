"""
Text-to-speech da MILK (Fase 6, item 2).

Motor primário: edge-tts (vozes neurais da Microsoft, já estava em
requirements.txt desde a Fase 5 mas nunca tinha sido de fato usado --
speaker.py só chamava o motor local). Sintetiza um mp3 e toca via MCI
(winmm, nativo do Windows -- sem dependência extra além do próprio
pacote edge-tts).

Fallback: se edge-tts falhar por qualquer motivo (sem internet, serviço
fora do ar, pacote ausente, playback falhou), cai para o motor local
antigo (System.Speech via PowerShell). Esse fallback é sempre offline e
soa mais robótico, mas garante que a MILK nunca fica muda.
"""
import asyncio
import ctypes
import os
import tempfile
import uuid

from core.proc import run_hidden

# Voz e taxa de fala configuráveis via .env sem precisar editar código.
DEFAULT_VOICE = os.getenv("MILK_TTS_VOICE", "pt-BR-FranciscaNeural")
DEFAULT_RATE = os.getenv("MILK_TTS_RATE", "+0%")

_winmm = ctypes.windll.winmm if os.name == "nt" else None


def _mci(cmd):
    buf = ctypes.create_unicode_buffer(255)
    return _winmm.mciSendStringW(cmd, buf, 254, 0)


def _play_mp3(path):
    """Toca um mp3 via MCI (Media Control Interface do Windows)."""
    alias = f"milk{uuid.uuid4().hex[:8]}"
    if _mci(f'open "{path}" type mpegvideo alias {alias}') != 0:
        raise RuntimeError("MCI não conseguiu abrir o áudio sintetizado.")
    try:
        if _mci(f"play {alias} wait") != 0:
            raise RuntimeError("MCI não conseguiu reproduzir o áudio sintetizado.")
    finally:
        _mci(f"close {alias}")


async def _synthesize(text, path):
    import edge_tts
    communicate = edge_tts.Communicate(text, DEFAULT_VOICE, rate=DEFAULT_RATE)
    await communicate.save(path)


def _speak_edge_tts(text):
    path = os.path.join(tempfile.gettempdir(), f"milk_tts_{uuid.uuid4().hex[:8]}.mp3")
    try:
        asyncio.run(_synthesize(text, path))
        if not os.path.exists(path) or os.path.getsize(path) == 0:
            raise RuntimeError("edge-tts não gerou áudio.")
        _play_mp3(path)
    finally:
        try:
            os.remove(path)
        except OSError:
            pass


def _speak_fallback_system_speech(text):
    safe = text.replace("'", "''")
    ps = (
        "Add-Type -AssemblyName System.Speech; "
        "$s=New-Object System.Speech.Synthesis.SpeechSynthesizer; "
        "$pt=$s.GetInstalledVoices() | Where-Object { $_.VoiceInfo.Culture.Name -like 'pt-BR*' } | Select-Object -First 1; "
        "if($pt){$s.SelectVoice($pt.VoiceInfo.Name)}; "
        "$s.Rate=0; $s.Volume=100; "
        f"$s.Speak('{safe}')"
    )
    run_hidden(
        ["powershell.exe", "-NoProfile", "-Command", ps],
        timeout=60,
        check=False
    )


class NaturalSpeaker:
    def say(self, text):
        text = str(text or "").strip()
        if not text:
            return

        print(f"MILK: {text}")

        try:
            _speak_edge_tts(text)
        except Exception as e:
            print(f"⚠️ edge-tts indisponível ({type(e).__name__}: {e}); usando voz local de reserva.")
            _speak_fallback_system_speech(text)
