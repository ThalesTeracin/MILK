# Milk — assistente pessoal.
# Copyright (c) 2026 Thales Teracin. Todos os direitos reservados.
#
# Software proprietário. É proibida a cópia, a distribuição, a
# modificação e a engenharia reversa, no todo ou em parte, sem
# autorização expressa e por escrito do autor. Ver LICENSE.txt.

"""Síntese de voz com edge_tts."""

import asyncio

import edge_tts

from PySide6.QtCore import QThread, Signal

from milk.core.config import (
    VOICE_FILE,
    VOICE_NAME,
    VOICE_RATE,
    VOICE_PITCH,
)


class TTSWorker(QThread):
    pronto = Signal(str)
    erro = Signal(str)

    def __init__(self, texto):
        super().__init__()
        self.texto = texto

    async def gerar(self):
        comunicacao = edge_tts.Communicate(
            text=self.texto,
            voice=VOICE_NAME,
            rate=VOICE_RATE,
            pitch=VOICE_PITCH,
        )

        await comunicacao.save(
            VOICE_FILE
        )

    def run(self):
        try:
            asyncio.run(
                self.gerar()
            )

            self.pronto.emit(
                VOICE_FILE
            )

        except Exception as exc:
            self.erro.emit(
                str(exc)
            )
