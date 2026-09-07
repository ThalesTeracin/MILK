# Milk — assistente pessoal.
# Copyright (c) 2026 Thales Teracin. Todos os direitos reservados.
#
# Software proprietário. É proibida a cópia, a distribuição, a
# modificação e a engenharia reversa, no todo ou em parte, sem
# autorização expressa e por escrito do autor. Ver LICENSE.txt.

"""De áudio para texto.

O caminho é o mesmo que já funcionava no botão "🎤 Falar": grava em
WAV, converte para 16 kHz mono com o ffmpeg embutido e manda para o
reconhecimento do Google em português do Brasil.

Estava dentro do `MicrofoneWorker`. Saiu para cá porque agora tem dois
donos: o botão e a escuta contínua.

A correção do FLAC em Windows ARM64 é aplicada na importação, como
antes — sem ela o reconhecimento levanta OSError nesta máquina.
"""

import wave
import subprocess

import speech_recognition as sr
import imageio_ffmpeg

from milk.core.config import MIC_CONVERTED_FILE, MIC_FILE
from milk.core.log import logger, registrar_erro
from milk.voice.flac_fix import corrigir_flac_windows


corrigir_flac_windows()


SEM_JANELA = getattr(subprocess, "CREATE_NO_WINDOW", 0)

IDIOMA = "pt-BR"


class SemFala(Exception):
    """Tinha som, mas não deu para entender palavra nenhuma."""


class ServicoIndisponivel(Exception):
    """O reconhecimento não respondeu (internet, cota, bloqueio)."""


def gravar_wav(amostras, taxa, caminho=MIC_FILE):
    """Escreve o áudio cru em WAV mono de 16 bits."""

    with wave.open(caminho, "wb") as arquivo:
        arquivo.setnchannels(1)
        arquivo.setsampwidth(2)
        arquivo.setframerate(taxa)

        arquivo.writeframes(
            amostras.tobytes()
        )

    return caminho


def converter(origem=MIC_FILE, destino=MIC_CONVERTED_FILE):
    """16 kHz, mono, PCM — o formato que o reconhecimento quer."""

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-i",
            origem,
            "-ac",
            "1",
            "-ar",
            "16000",
            "-acodec",
            "pcm_s16le",
            destino,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=SEM_JANELA,
        check=True,
    )

    return destino


def transcrever_arquivo(caminho, idioma=IDIOMA):
    """O texto do que foi falado. Levanta SemFala ou ServicoIndisponivel."""

    reconhecedor = sr.Recognizer()

    with sr.AudioFile(caminho) as fonte:
        dados = reconhecedor.record(fonte)

    try:
        texto = reconhecedor.recognize_google(
            dados,
            language=idioma
        )

    except sr.UnknownValueError:
        raise SemFala()

    except sr.RequestError as erro:
        raise ServicoIndisponivel(str(erro))

    texto = (texto or "").strip()

    if not texto:
        raise SemFala()

    return texto


def transcrever_amostras(amostras, taxa, idioma=IDIOMA):
    """Grava, converte e transcreve um trecho que veio do microfone."""

    gravar_wav(amostras, taxa)

    try:
        convertido = converter()

    except (subprocess.CalledProcessError, OSError) as erro:
        registrar_erro("voice", "falha ao converter o áudio", erro)

        raise ServicoIndisponivel("conversão do áudio falhou")

    texto = transcrever_arquivo(convertido, idioma)

    logger("voice").info(f"transcreveu: {texto[:60]}")

    return texto
