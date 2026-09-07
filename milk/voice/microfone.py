# Milk — assistente pessoal.
# Copyright (c) 2026 Thales Teracin. Todos os direitos reservados.
#
# Software proprietário. É proibida a cópia, a distribuição, a
# modificação e a engenharia reversa, no todo ou em parte, sem
# autorização expressa e por escrito do autor. Ver LICENSE.txt.

"""Gravação do microfone pelo botão "🎤 Falar".

Sete segundos fixos, do jeito que sempre foi. A escuta que não depende
de botão nem de tempo fixo mora em `milk/voice/escuta.py`.

A parte de virar texto (WAV, conversão e reconhecimento) saiu daqui
para `milk/voice/transcricao.py`, porque agora tem dois donos. As
mensagens que aparecem para o usuário continuam as mesmas.
"""

import sounddevice as sd
import numpy as np

from PySide6.QtCore import QThread, Signal

from milk.core.config import MIC_SECONDS
from milk.core.log import registrar_erro
from milk.voice import dispositivos, transcricao


class MicrofoneWorker(QThread):
    texto_pronto = Signal(str)
    status = Signal(str)
    erro = Signal(str)

    def run(self):
        try:
            self.status.emit(
                "👂 Preparando microfone..."
            )

            # O padrão do Windows pode ser um microfone mudo. Quem
            # escolhe é milk/voice/dispositivos.py.
            entrada = dispositivos.escolher()

            if entrada is None:
                self.erro.emit(
                    "Não achei nenhum microfone para usar."
                )

                return

            taxa = entrada.taxa

            self.status.emit(
                f"👂 Ouvindo pelo {entrada.nome}..."
            )

            audio = sd.rec(
                int(MIC_SECONDS * taxa),
                samplerate=taxa,
                channels=1,
                dtype="int16",
                device=entrada.indice,
            )

            sd.wait()

            self.status.emit(
                "🔄 Preparando áudio..."
            )

            amostras = np.asarray(
                audio,
                dtype=np.int16
            ).reshape(-1)

            self.status.emit(
                "📝 Entendendo o que você falou..."
            )

            texto = transcricao.transcrever_amostras(
                amostras,
                taxa
            )

            self.texto_pronto.emit(
                texto
            )

        except transcricao.SemFala:
            self.erro.emit(
                "Não consegui entender o que você falou."
            )

        except transcricao.ServicoIndisponivel as exc:
            self.erro.emit(
                "O serviço de transcrição não respondeu. "
                f"Detalhes: {exc}"
            )

        except Exception as exc:
            registrar_erro("voice", "falha no microfone", exc)

            self.erro.emit(
                f"Erro no microfone: {exc}"
            )
