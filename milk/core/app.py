# Milk — assistente pessoal.
# Copyright (c) 2026 Thales Teracin. Todos os direitos reservados.
#
# Software proprietário. É proibida a cópia, a distribuição, a
# modificação e a engenharia reversa, no todo ou em parte, sem
# autorização expressa e por escrito do autor. Ver LICENSE.txt.

"""Ponto de entrada da Milk.

Além de subir a janela, este arquivo faz duas coisas de sobrevivência
(Fase 17): registra qualquer erro não tratado no log em vez de deixar o
programa morrer em silêncio, e marca como interrompida a tarefa que
estava rodando quando a Milk foi fechada.
"""

import sys

from PySide6.QtWidgets import QApplication

from milk.avatar.mascote import MilkMascot
from milk.core.log import logger, registrar_erro
from milk.tasks.gerente import gerente


def instalar_rede_de_seguranca():
    """Erro não tratado vira linha de log, não morte silenciosa.

    A Milk roda sem terminal à vista. Sem isto, uma exceção solta some
    sem deixar rastro e o usuário só vê a janela sumir."""

    anterior = sys.excepthook

    def contar(tipo, valor, rastro):
        try:
            registrar_erro(
                "errors",
                f"erro não tratado: {tipo.__name__}",
                valor,
            )

        except Exception:
            pass

        return anterior(tipo, valor, rastro)

    sys.excepthook = contar

    return contar


def main():
    instalar_rede_de_seguranca()

    logger("app").info("Milk abriu")

    app = QApplication(
        sys.argv
    )

    app.setQuitOnLastWindowClosed(
        False
    )

    milk = MilkMascot()

    milk.show()

    # Onde ela parar e onde ela vai estar da proxima vez.
    app.aboutToQuit.connect(milk.salvar_posicao)

    codigo = app.exec()

    # A tarefa que estava rodando morreu junto com o processo. Fica
    # registrada como interrompida, para o usuario poder mandar repetir.
    try:
        gerente().interromper_em_andamento()

    except Exception:
        pass

    logger("app").info(f"Milk fechou (código {codigo})")

    return codigo


if __name__ == "__main__":
    sys.exit(
        main()
    )
