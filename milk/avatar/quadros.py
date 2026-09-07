# Milk — assistente pessoal.
# Copyright (c) 2026 Thales Teracin. Todos os direitos reservados.
#
# Software proprietário. É proibida a cópia, a distribuição, a
# modificação e a engenharia reversa, no todo ou em parte, sem
# autorização expressa e por escrito do autor. Ver LICENSE.txt.

"""Quadros da Milk caminhando, quando a arte existir.

O `milk_avatar.png` é a cachorrinha sentada e de frente: dele não sai
ciclo de caminhada nenhum — as patas estão encostadas umas nas outras,
pelo branco sobre pelo branco, e as traseiras estão dobradas embaixo do
corpo. Verificado recortando: o corte deixa a imagem amputada.

Este módulo é a porta de entrada da arte de verdade. Assim que existir
um ciclo de caminhada em `assets/avatar/`, ela passa a mexer as patinhas
sem que nada mais precise mudar. Enquanto não existir, devolve lista
vazia e a Milk segue com o balanço procedural de hoje.

Três formatos aceitos, nesta ordem:

1. `andando.gif` ou `andando.webp` — animação pronta. O WEBP guarda
   transparência de verdade; o GIF só liga/desliga o pixel, então fundo
   vazado pode sair com serrilha branca em volta dela.
2. `andando.png` — folha de sprites: os quadros lado a lado, todos do
   mesmo tamanho, altura igual à do quadro.
3. `andando/01.png`, `andando/02.png`, ... — um arquivo por quadro, em
   ordem de nome.
"""

import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QMovie, QPixmap

from milk.core.config import ANDANDO_DIR


ANIMADOS = ("andando.webp", "andando.gif")

FOLHA = "andando.png"

PASTA = "andando"

# Uma folha com quadro mais largo que isso quase certamente foi cortada
# errado, e é melhor avisar do que desenhar lixo na tela.
LIMITE_PROPORCAO = 3.0


def carregar_quadros(altura):
    """Os quadros do ciclo, já na altura pedida. Vazio se não houver arte."""

    for nome in ANIMADOS:
        quadros = quadros_de_animacao(
            os.path.join(ANDANDO_DIR, nome)
        )

        if quadros:
            return redimensionar(quadros, altura)

    quadros = quadros_de_folha(
        os.path.join(ANDANDO_DIR, FOLHA)
    )

    if quadros:
        return redimensionar(quadros, altura)

    quadros = quadros_de_pasta(
        os.path.join(ANDANDO_DIR, PASTA)
    )

    return redimensionar(quadros, altura)


def quadros_de_animacao(caminho):
    """Abre um GIF ou WEBP animado e separa os quadros."""

    if not os.path.exists(caminho):
        return []

    filme = QMovie(caminho)

    if not filme.isValid():
        return []

    quadros = []

    for indice in range(filme.frameCount()):
        if not filme.jumpToFrame(indice):
            break

        imagem = filme.currentPixmap()

        if not imagem.isNull():
            quadros.append(imagem)

    return quadros


def quadros_de_folha(caminho):
    """Fatia uma folha de sprites em quadros quadrados.

    A conta assume quadros do tamanho da altura da folha, lado a lado,
    que é como praticamente toda folha de sprite vem."""

    if not os.path.exists(caminho):
        return []

    folha = QPixmap(caminho)

    if folha.isNull() or folha.height() == 0:
        return []

    lado = folha.height()

    if folha.width() < lado:
        return []

    quantidade = folha.width() // lado

    if quantidade < 2:
        return []

    return [
        folha.copy(
            indice * lado,
            0,
            lado,
            lado
        )
        for indice in range(quantidade)
    ]


def quadros_de_pasta(caminho):
    """Um arquivo por quadro, em ordem de nome."""

    if not os.path.isdir(caminho):
        return []

    quadros = []

    for nome in sorted(os.listdir(caminho)):
        if not nome.lower().endswith((".png", ".webp")):
            continue

        imagem = QPixmap(
            os.path.join(caminho, nome)
        )

        if not imagem.isNull():
            quadros.append(imagem)

    return quadros


def redimensionar(quadros, altura):
    """Todos na mesma altura, mantendo a proporção de cada um.

    Quadro desproporcional é descartado: quase sempre é folha de sprites
    fatiada errado, e desenhar aquilo esticado na tela é pior do que
    continuar com o PNG parado."""

    prontos = []

    for quadro in quadros:
        if quadro.isNull() or quadro.height() == 0:
            continue

        proporcao = quadro.width() / quadro.height()

        if proporcao > LIMITE_PROPORCAO or proporcao < 1 / LIMITE_PROPORCAO:
            continue

        prontos.append(
            quadro.scaledToHeight(
                altura,
                Qt.SmoothTransformation
            )
        )

    return prontos
