import json
import subprocess
import tempfile
import wave
from pathlib import Path

import numpy as np
import sounddevice as sd

from core.proc import popen_hidden

CONFIG = Path("config/whisper_local.json")

class NaturalVoiceListener:
    def __init__(self):
        if not CONFIG.exists():
            raise RuntimeError(
                "Whisper não configurado. Arquivo config/whisper_local.json ausente."
            )

        cfg = json.loads(CONFIG.read_text(encoding="utf-8-sig"))
        self.exe = Path(cfg["whisper_exe"]).resolve()
        self.model = Path(cfg["model"]).resolve()
        self.language = cfg.get("language", "pt")
        self.seconds = int(cfg.get("seconds", 6))

        if not self.exe.exists():
            raise RuntimeError(f"whisper-cli não encontrado: {self.exe}")
        if not self.model.exists():
            raise RuntimeError(f"modelo não encontrado: {self.model}")

        info = sd.query_devices(None, "input")
        self.native_rate = int(float(info.get("default_samplerate", 44100)))
        self.device_name = info.get("name", "Microfone padrão")

        print(f"🎤 Microfone: {self.device_name}")
        print(f"🎤 Taxa nativa: {self.native_rate} Hz")
        print("🧠 STT: whisper.cpp")
        print("🪟 Whisper: modo invisível forçado")

    def calibrate(self, seconds=0):
        print("✅ Whisper pronto.")

    def _resample_to_16k(self, audio):
        if self.native_rate == 16000:
            return audio.astype(np.int16)

        x = np.asarray(audio, dtype=np.float32).reshape(-1)
        if len(x) == 0:
            return np.array([], dtype=np.int16)

        new_len = max(1, int(len(x) * 16000 / self.native_rate))
        old_idx = np.arange(len(x), dtype=np.float32)
        new_idx = np.linspace(0, len(x)-1, new_len, dtype=np.float32)
        y = np.interp(new_idx, old_idx, x)
        return np.clip(y, -32768, 32767).astype(np.int16)

    # Detecção de fim de fala. Antes a captura gravava um bloco fixo de
    # self.seconds e descartava tudo se o RMS médio ficasse abaixo do
    # limiar: frases mais longas que a janela eram cortadas no meio, e
    # frases curtas gastavam o resto do tempo gravando silêncio.
    LIMIAR_RMS = 15          # mesmo limiar usado antes, agora por bloco
    BLOCO_SEGUNDOS = 0.1     # granularidade da decisão
    SILENCIO_PARA_PARAR = 0.8
    DURACAO_MAXIMA = 15.0    # teto absoluto, evita gravar para sempre

    def _record(self):
        frames_por_bloco = int(self.native_rate * self.BLOCO_SEGUNDOS)
        blocos_de_silencio_para_parar = int(
            self.SILENCIO_PARA_PARAR / self.BLOCO_SEGUNDOS
        )
        blocos_maximos = int(self.DURACAO_MAXIMA / self.BLOCO_SEGUNDOS)

        blocos = []
        comecou_a_falar = False
        blocos_silenciosos = 0

        with sd.InputStream(
            samplerate=self.native_rate,
            channels=1,
            dtype="int16",
            device=None,
        ) as stream:
            for _ in range(blocos_maximos):
                dados, estourou = stream.read(frames_por_bloco)
                if estourou:
                    print("⚠️ Estouro no buffer de áudio")

                bloco = np.asarray(dados).reshape(-1)
                rms = float(np.sqrt(np.mean(bloco.astype(np.float32) ** 2)))
                tem_voz = rms >= self.LIMIAR_RMS

                if tem_voz:
                    comecou_a_falar = True
                    blocos_silenciosos = 0
                elif comecou_a_falar:
                    blocos_silenciosos += 1

                # Só acumula depois que a fala começou: o silêncio inicial,
                # enquanto a pessoa ainda não falou, não vira áudio.
                if comecou_a_falar:
                    blocos.append(bloco)
                    if blocos_silenciosos >= blocos_de_silencio_para_parar:
                        break

        if not comecou_a_falar or not blocos:
            return None

        return self._resample_to_16k(np.concatenate(blocos))

    def _run_whisper_hidden(self, cmd):
        """
        Execute whisper-cli directly, never through cmd.exe, PowerShell,
        Windows Terminal or shell=True.
        """
        p = popen_hidden(
            cmd,
            cwd=self.exe.parent,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        try:
            out, err = p.communicate(timeout=120)
        except subprocess.TimeoutExpired:
            p.kill()
            out, err = p.communicate()
            raise RuntimeError("Whisper excedeu o tempo limite.")

        return p.returncode, out or "", err or ""

    def listen(self):
        print("🟢 Pode falar. Eu paro sozinha quando você terminar.")

        try:
            audio = self._record()
        except Exception as e:
            print(f"❌ Erro no microfone: {e}")
            return None

        if audio is None or len(audio) == 0:
            print("⚠️ Nenhuma fala detectada.")
            return None

        with tempfile.TemporaryDirectory(prefix="milk_whisper_") as td:
            td = Path(td)
            wav = td / "input.wav"
            out_prefix = td / "result"

            with wave.open(str(wav), "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(16000)
                wf.writeframes(audio.tobytes())

            cmd = [
                str(self.exe),
                "-m", str(self.model),
                "-f", str(wav),
                "-l", self.language,
                "-nt",
                "-otxt",
                "-of", str(out_prefix),
            ]

            try:
                code, out, err = self._run_whisper_hidden(cmd)
            except Exception as e:
                print(f"❌ Whisper falhou: {e}")
                return None

            txt = Path(str(out_prefix) + ".txt")
            text = txt.read_text(
                encoding="utf-8",
                errors="ignore"
            ).strip() if txt.exists() else ""

            if not text:
                detail = (err or out).strip()
                if detail:
                    print("⚠️ Whisper:", detail[-500:])
                else:
                    print(f"⚠️ Whisper não reconheceu palavras. Código: {code}")
                return None

            print(f"🗣️ Reconhecido: {text}")
            return text
