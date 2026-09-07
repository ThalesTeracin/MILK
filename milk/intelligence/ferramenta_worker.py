# Milk — assistente pessoal.
# Copyright (c) 2026 Thales Teracin. Todos os direitos reservados.
#
# Software proprietário. É proibida a cópia, a distribuição, a
# modificação e a engenharia reversa, no todo ou em parte, sem
# autorização expressa e por escrito do autor. Ver LICENSE.txt.

"""Roda uma ferramenta fora da thread da interface.

Mesmo padrão do ClaudeWorker e do MicrofoneWorker: enquanto a chamada
HTTP acontece, a janela da Milk continua respondendo.

Nada escapa daqui. Qualquer falha vira o sinal `erro` com uma frase em
português, e a Milk segue funcionando.
"""

from PySide6.QtCore import QThread, Signal


class FerramentaWorker(QThread):
    sucesso = Signal(str)
    erro = Signal(str)
    progresso = Signal(str)

    def __init__(self, decisao):
        super().__init__()

        self.decisao = decisao

    def run(self):
        self.progresso.emit(
            self.decisao.descricao
        )

        try:
            resultado = self.decisao.executar()

        except Exception as exc:
            # Rede de segurança: a ferramenta já deveria ter tratado.
            self.erro.emit(
                "Não consegui fazer essa consulta agora. "
                f"({exc})"
            )

            return

        if resultado is None:
            self.erro.emit(
                "A consulta voltou vazia."
            )

            return

        if resultado.ok:
            self.sucesso.emit(
                resultado.texto
            )
        else:
            self.erro.emit(
                resultado.texto
            )
