# Milk — assistente pessoal.
# Copyright (c) 2026 Thales Teracin. Todos os direitos reservados.
#
# Software proprietário. É proibida a cópia, a distribuição, a
# modificação e a engenharia reversa, no todo ou em parte, sem
# autorização expressa e por escrito do autor. Ver LICENSE.txt.

"""Onde a Milk estava (Fase 27).

Ela guarda o canto da tela em que ficou e volta para lá na próxima vez.
Sem isso, todo dia ela reaparece no canto inferior direito, mesmo que
você tenha passado a semana com ela do outro lado.

A posição só é aceita se ainda couber em algum monitor: quem trabalha
com um monitor a mais em casa não pode abrir a Milk fora da tela no dia
em que estiver sem ele.
"""

import os

from milk.core.arquivo import ler_json, gravar_json
from milk.core.config import BASE_DIR


POSICAO_FILE = os.path.join(BASE_DIR, "milk_posicao.json")


def ler(arquivo=POSICAO_FILE, ler_arquivo=ler_json):
    """(x, y) da última vez, ou None."""

    guardado = ler_arquivo(arquivo, None)

    if not isinstance(guardado, dict):
        return None

    try:
        return (
            int(guardado["x"]),
            int(guardado["y"]),
        )

    except (KeyError, TypeError, ValueError):
        return None


def gravar(x, y, arquivo=POSICAO_FILE, gravar_arquivo=gravar_json):
    try:
        return gravar_arquivo(
            arquivo,
            {"x": int(x), "y": int(y)},
        )

    except Exception:
        return False


def cabe_na_tela(x, y, largura, altura, telas):
    """A janela inteira precisa caber em algum monitor.

    `telas` é uma lista de retângulos (x, y, largura, altura)."""

    for tela_x, tela_y, tela_largura, tela_altura in telas:
        dentro = (
            x >= tela_x
            and y >= tela_y
            and x + largura <= tela_x + tela_largura
            and y + altura <= tela_y + tela_altura
        )

        if dentro:
            return True

    return False


def telas_disponiveis():
    """Os monitores de agora, no formato que `cabe_na_tela` espera."""

    from PySide6.QtGui import QGuiApplication

    retangulos = []

    for tela in QGuiApplication.screens():
        area = tela.availableGeometry()

        retangulos.append(
            (area.x(), area.y(), area.width(), area.height())
        )

    return retangulos


def posicao_valida(largura, altura, telas=None):
    """A posição guardada, se ela ainda existir numa tela de verdade."""

    guardada = ler()

    if guardada is None:
        return None

    telas = telas if telas is not None else telas_disponiveis()

    if not telas:
        return None

    if not cabe_na_tela(guardada[0], guardada[1], largura, altura, telas):
        return None

    return guardada
