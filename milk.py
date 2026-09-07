# Milk — assistente pessoal.
# Copyright (c) 2026 Thales Teracin. Todos os direitos reservados.
#
# Software proprietário. É proibida a cópia, a distribuição, a
# modificação e a engenharia reversa, no todo ou em parte, sem
# autorização expressa e por escrito do autor. Ver LICENSE.txt.

"""Ponto de entrada da Milk.

A implementação está em milk/ (core, voice, avatar, intelligence,
tasks, memory, system, tools).

    python milk.py            abre a Milk
    python milk.py doutor     só o diagnóstico, no terminal
"""

import sys


def escrever(texto):
    """Mostra no terminal; sem terminal, grava em arquivo.

    O Milk.exe é feito sem console (para não abrir janela preta), e aí
    `sys.stdout` não existe. Em vez de estourar, o relatório vai para
    logs/app/diagnostico.txt e o caminho é avisado numa janelinha."""

    if sys.stdout is not None:
        print(texto)

        return None

    from milk.core.config import LOGS_DIR

    destino = LOGS_DIR / "app" / "diagnostico.txt"

    try:
        destino.parent.mkdir(parents=True, exist_ok=True)

        destino.write_text(texto, encoding="utf-8")

    except OSError:
        return None

    try:
        import ctypes

        ctypes.windll.user32.MessageBoxW(
            None,
            f"{texto}\n\nTambém salvei em:\n{destino}",
            "Milk — diagnóstico",
            0x40,
        )

    except Exception:
        pass

    return destino


def doutor():
    """Roda o Milk Doctor e escreve o relatório no terminal.

    Devolve 0 quando está tudo de pé e 1 quando alguma coisa falhou,
    para dar para usar em script."""

    from milk.core.doutor import FALHA, examinar, relatorio

    resultados = examinar()

    escrever(
        relatorio(resultados)
    )

    tem_falha = any(
        exame.estado == FALHA
        for exame in resultados
    )

    return 1 if tem_falha else 0


def abrir():
    from milk.core.app import main

    return main()


if __name__ == "__main__":
    comando = sys.argv[1].lower() if len(sys.argv) > 1 else ""

    if comando in ("doutor", "doctor", "--doutor", "--doctor"):
        sys.exit(
            doutor()
        )

    sys.exit(
        abrir()
    )
