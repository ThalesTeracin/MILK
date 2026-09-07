# Milk — assistente pessoal.
# Copyright (c) 2026 Thales Teracin. Todos os direitos reservados.
#
# Software proprietário. É proibida a cópia, a distribuição, a
# modificação e a engenharia reversa, no todo ou em parte, sem
# autorização expressa e por escrito do autor. Ver LICENSE.txt.

"""Correção do binário FLAC em Windows ARM64.

Aplicada na importação de milk.voice.microfone, antes de qualquer
transcrição.
"""

import os


def corrigir_flac_windows():
    """O speech_recognition so aceita Windows x86/AMD64 ao procurar o
    binario FLAC embutido. Em Windows ARM64 ele levanta OSError e o
    reconhecimento de voz nunca funciona, apesar de o flac-win32.exe
    rodar normalmente por emulacao. So aponta o caminho quando a
    deteccao original falha."""

    import speech_recognition.audio as sr_audio

    try:
        sr_audio.get_flac_converter()
        return
    except OSError:
        pass

    caminho = os.path.join(
        os.path.dirname(
            sr_audio.__file__
        ),
        "flac-win32.exe"
    )

    if os.path.exists(caminho):
        sr_audio.get_flac_converter = (
            lambda: caminho
        )
