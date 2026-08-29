import gc
import json
import subprocess
import tempfile
import wave
from pathlib import Path

import numpy as np
import sounddevice as sd

from core.config import config_path
from core.proc import popen_hidden
from voice.audio_device import indice_de_entrada, perfil_de_captura
from voice.audio_dsp import condicionar

CONFIG = config_path("whisper_local.json")


def _ajustar_ganho_do_microfone(ganho_db):
    """
    Põe o ganho do endpoint de captura no valor que o perfil pede.

    Nesta máquina o endpoint vinha com +24 dB, o topo da faixa: a fala
    batia no teto do int16 em 1,5% das amostras e o Whisper devolvia
    legenda de ruído em vez de palavras. A +18 dB o pico caiu de 32767
    para 21026 e a mesma frase virou texto.

    Depende do pycaw, que é opcional (requirements-optional.txt). Sem ele
    a MILK continua ouvindo com o ganho que o Windows já tem: perder o
    ajuste fino é muito melhor do que não subir.
    """
    try:
        from comtypes import CLSCTX_ALL, POINTER, cast
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    except Exception:
        return False

    try:
        for dispositivo in AudioUtilities.GetAllDevices():
            nome = dispositivo.FriendlyName or ""
            if not str(dispositivo.state).endswith("Active"):
                continue
            if "Microfone" not in nome and "Microphone" not in nome:
                continue

            interface = dispositivo._dev.Activate(
                IAudioEndpointVolume._iid_, CLSCTX_ALL, None
            )
            volume = cast(interface, POINTER(IAudioEndpointVolume))
            try:
                minimo, maximo, _ = volume.GetVolumeRange()
                alvo = max(minimo, min(maximo, float(ganho_db)))
                if abs(volume.GetMasterVolumeLevel() - alvo) > 0.01:
                    volume.SetMasterVolumeLevel(alvo, None)
                    print(f"🎚️ Ganho do microfone ajustado para {alvo:.0f} dB.")
            finally:
                # Soltar os objetos COM aqui, enquanto o COM ainda está
                # inicializado. Deixá-los para o coletor faz o Release()
                # cair depois da finalização do COM, e o __del__ do
                # comtypes levanta "COM method call without VTable" no
                # fim do processo -- ruído numa saída que estava limpa.
                del volume, interface, dispositivo
                gc.collect()
            return True
    except Exception as e:
        print(f"⚠️ não consegui ajustar o ganho do microfone ({type(e).__name__}: {e}).")

    return False

class NaturalVoiceListener:
    def __init__(self):
        if not CONFIG.exists():
            raise RuntimeError(
                f"Whisper não configurado. Arquivo {CONFIG} ausente."
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

        # None abre o dispositivo padrao do Windows; um indice abre o
        # microfone que o usuario escolheu em Selecionar_Microfone.py.
        self.device = indice_de_entrada()
        try:
            info = sd.query_devices(self.device, "input")
        except Exception as e:
            # Indice invalido (microfone desconectado desde a escolha).
            # Cair no padrao e melhor do que o MILK ficar surdo.
            print(f"⚠️ microfone {self.device} indisponível ({type(e).__name__}: {e}); usando o padrão.")
            self.device = None
            info = sd.query_devices(None, "input")

        self.native_rate = int(float(info.get("default_samplerate", 44100)))
        self.device_name = info.get("name", "Microfone padrão")

        self.perfil = perfil_de_captura()
        _ajustar_ganho_do_microfone(self.perfil["ganho_db"])

        print(f"🎤 Microfone: {self.device_name}")
        print(f"🎤 Taxa nativa: {self.native_rate} Hz")
        print(f"🎤 Perfil de captura: {self.perfil['nome']}")
        print("🧠 STT: whisper.cpp")
        print("🪟 Whisper: modo invisível forçado")

    def calibrate(self, seconds=0):
        print("✅ Whisper pronto.")

    # Detecção de fim de fala. Antes a captura gravava um bloco fixo de
    # self.seconds e descartava tudo se o RMS médio ficasse abaixo do
    # limiar: frases mais longas que a janela eram cortadas no meio, e
    # frases curtas gastavam o resto do tempo gravando silêncio.
    BLOCO_SEGUNDOS = 0.1     # granularidade da decisão
    BLOCOS_DE_RUIDO = 10     # 1 s de silêncio guardado como referência

    def _record(self):
        # Limiar, paciência com pausas e teto de duração vêm do perfil de
        # captura: de longe a voz chega mais fraca e as pausas parecem fim
        # de frase. Ver PERFIS em voice/audio_device.py.
        frames_por_bloco = int(self.native_rate * self.BLOCO_SEGUNDOS)
        limiar = self.perfil["limiar_rms"]
        blocos_de_silencio_para_parar = int(
            self.perfil["silencio_para_parar"] / self.BLOCO_SEGUNDOS
        )
        blocos_maximos = int(self.perfil["duracao_maxima"] / self.BLOCO_SEGUNDOS)

        blocos = []
        # O silêncio antes da fala deixou de ser jogado fora: ele é a
        # medida do ruído desta sala, e é com ela que o condicionamento
        # sabe o que tirar do que veio depois.
        ruido = []
        comecou_a_falar = False
        blocos_silenciosos = 0

        with sd.InputStream(
            samplerate=self.native_rate,
            channels=1,
            dtype="int16",
            device=self.device,
        ) as stream:
            for _ in range(blocos_maximos):
                dados, estourou = stream.read(frames_por_bloco)
                if estourou:
                    print("⚠️ Estouro no buffer de áudio")

                bloco = np.asarray(dados).reshape(-1)
                rms = float(np.sqrt(np.mean(bloco.astype(np.float32) ** 2)))
                tem_voz = rms >= limiar

                if tem_voz:
                    comecou_a_falar = True
                    blocos_silenciosos = 0
                elif comecou_a_falar:
                    blocos_silenciosos += 1

                # Só acumula depois que a fala começou: o silêncio inicial,
                # enquanto a pessoa ainda não falou, não vira áudio -- mas
                # vira referência de ruído.
                if comecou_a_falar:
                    blocos.append(bloco)
                    if blocos_silenciosos >= blocos_de_silencio_para_parar:
                        break
                else:
                    ruido.append(bloco)
                    if len(ruido) > self.BLOCOS_DE_RUIDO:
                        ruido.pop(0)

        if not comecou_a_falar or not blocos:
            return None

        referencia = np.concatenate(ruido) if ruido else None
        return condicionar(np.concatenate(blocos), self.native_rate, ruido=referencia)

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
