# Milk — assistente pessoal.
# Copyright (c) 2026 Thales Teracin. Todos os direitos reservados.
#
# Software proprietário. É proibida a cópia, a distribuição, a
# modificação e a engenharia reversa, no todo ou em parte, sem
# autorização expressa e por escrito do autor. Ver LICENSE.txt.

"""Vida na imagem da Milk.

O avatar é um PNG de uma cachorrinha **sentada e de frente**. Não existe
ciclo de caminhada aqui: as perninhas não estão desenhadas em movimento,
e nenhuma conta cria essa informação. O que esta classe faz é dar ritmo
ao corpo inteiro — quica no passo, pende para os lados, respira parada e
vira para o lado que está indo.

Isso mata a sensação de "levada por uma esteira". Não substitui um
ciclo de caminhada desenhado. No dia em que existir um GIF dela de
perfil andando, ele entra por `QMovie` e esta camada sai de cena.
"""

import math

from PySide6.QtCore import QObject, Qt, QTimer
from PySide6.QtGui import QPainter, QPixmap


# 25 quadros por segundo. Mais que isso não se vê, e cada quadro redesenha
# a imagem inteira.
INTERVALO = 40

# Um passo, medido em pixels caminhados — não em tempo. É isso que
# amarra o corpo ao chão: quando ela freia para chegar, o quique freia
# junto. Regido pelo relógio, ela patinaria na frenagem.
PASSO_PX = 30
QUIQUE = 4
INCLINACAO = 3.0

# Parada ela respira: lento e quase imperceptível, de propósito.
RESPIRO_MS = 3600
RESPIRO = 0.015


class Animacao(QObject):
    def __init__(
        self,
        base,
        mostrar,
        *,
        andando,
        direcao,
        percorrido,
        quadros=None,
        parent=None,
    ):
        """`base` é o PNG já no tamanho final.

        `mostrar` recebe cada quadro pronto. `andando`, `direcao` e
        `percorrido` são perguntas feitas ao dono da janela a cada
        quadro — assim esta classe não precisa conhecer o passeio nem o
        avatar."""

        super().__init__(parent)

        self.base = base
        self.mostrar = mostrar
        self.andando = andando
        self.direcao = direcao
        self.percorrido = percorrido

        # Ciclo de caminhada desenhado. Havendo quadros, as patinhas se
        # mexem de verdade e o quique procedural sai de cena: o desenho
        # já traz o peso do corpo. Sem quadros, tudo segue como hoje.
        self.quadros = quadros or []

        # A tela é maior que a imagem para a inclinação não cortar as
        # orelhas nem o rabo no canto, e larga o bastante para o quadro
        # mais largo do ciclo, que costuma passar do tamanho do parado.
        mais_larga = max(
            [base.width()] + [q.width() for q in self.quadros]
        )

        mais_alta = max(
            [base.height()] + [q.height() for q in self.quadros]
        )

        self.largura = mais_larga + 16
        self.altura = mais_alta + 16

        self.tempo = 0

        self.relogio = QTimer(self)
        self.relogio.setInterval(INTERVALO)
        self.relogio.timeout.connect(self.avancar)

    def comecar(self):
        self.avancar()

        self.relogio.start()

    def parar(self):
        self.relogio.stop()

    def avancar(self):
        self.tempo += INTERVALO

        self.mostrar(
            self.quadro()
        )

    # ========================================================
    # O QUADRO
    # ========================================================

    def gesto(self):
        """Quanto subir, quanto pender e quanto inchar, agora.

        Andando, o quique fecha um ciclo por passo e a inclinação leva
        dois — ela pende para um lado, depois para o outro. Parada, só
        o respiro."""

        if self.andando():
            fase = math.pi * self.percorrido() / PASSO_PX

            return (
                -QUIQUE * abs(math.sin(fase)),
                INCLINACAO * math.sin(fase),
                1.0,
            )

        respiro = math.sin(
            2 * math.pi * self.tempo / RESPIRO_MS
        )

        return (
            0.0,
            0.0,
            1.0 + RESPIRO * respiro,
        )

    @property
    def anima_desenhada(self):
        """Existe ciclo de caminhada desenhado para usar agora?"""

        return bool(self.quadros) and self.andando()

    def desenho_do_passo(self):
        """O quadro do ciclo correspondente ao ponto da passada.

        Regido pela distância, igual ao quique: se ela freia, as patas
        freiam junto."""

        passo = self.percorrido() / PASSO_PX

        return self.quadros[
            int(passo * len(self.quadros)) % len(self.quadros)
        ]

    def quadro(self):
        """Desenha a Milk deformada, sempre no mesmo tamanho de tela.

        O pivô fica nos pés, no meio da base: é lá que um bicho apoia o
        peso. Girar pelo centro da imagem faria ela flutuar."""

        if self.anima_desenhada:
            # O desenho já tem o peso e o balanço do corpo. Somar o
            # quique procedural em cima seria animação duas vezes.
            imagem = self.desenho_do_passo()

            subida, angulo, escala = 0.0, 0.0, 1.0

        else:
            imagem = self.base

            subida, angulo, escala = self.gesto()

        tela = QPixmap(
            self.largura,
            self.altura
        )

        tela.fill(
            Qt.transparent
        )

        pintor = QPainter(tela)

        pintor.setRenderHint(
            QPainter.SmoothPixmapTransform
        )

        pintor.translate(
            self.largura / 2,
            self.altura + subida
        )

        pintor.rotate(
            angulo
        )

        # direcao -1 espelha: ela passa a olhar para onde está indo.
        pintor.scale(
            self.direcao() * escala,
            escala
        )

        pintor.drawPixmap(
            -imagem.width() // 2,
            -imagem.height(),
            imagem
        )

        pintor.end()

        return tela
