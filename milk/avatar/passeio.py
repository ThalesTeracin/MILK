# Milk — assistente pessoal.
# Copyright (c) 2026 Thales Teracin. Todos os direitos reservados.
#
# Software proprietário. É proibida a cópia, a distribuição, a
# modificação e a engenharia reversa, no todo ou em parte, sem
# autorização expressa e por escrito do autor. Ver LICENSE.txt.

"""Passeio da Milk pela área de trabalho.

Ela fica parada a maior parte do tempo e, de vez em quando, resolve dar
uma volta: escolhe um ponto em algum monitor, caminha até lá e senta de
novo. Movimento contínuo cansa e atrapalha quem está trabalhando.

Esta classe só move a janela. Ela não sabe desenhar, não sabe falar e
não decide sozinha se pode andar: quem responde isso é a função
`pode_andar`, que o dono da janela injeta.
"""

import math
import random

from PySide6.QtCore import QObject, QPoint, QTimer
from PySide6.QtGui import QGuiApplication


# Passo curto e tique rápido: o olho lê como caminhada, não como salto.
VELOCIDADE = 3.0
INTERVALO = 30

# Ninguém sai andando na velocidade final nem para de uma vez. Ela ganha
# ritmo nos primeiros pixels e freia nos últimos, sem nunca ficar parada
# no meio do caminho.
RAMPA = 70
VEL_MINIMA = 0.35

# Cada volta tem um ritmo próprio: umas mais apressadas, outras à toa.
RITMO_MIN = 0.75
RITMO_MAX = 1.30

# De vez em quando ela para no meio do caminho, como quem viu alguma
# coisa, e depois segue.
PAUSA_CHANCE = 0.006
PAUSA_MIN = 10
PAUSA_MAX = 30

# Quanto tempo ela fica parada antes de resolver passear de novo.
DESCANSO_MIN = 20_000
DESCANSO_MAX = 60_000

# Ela anda rente ao pé da tela, como quem pisa no chão, e nunca encosta
# na borda.
MARGEM = 25


def telas_disponiveis():
    """Área útil de cada monitor, já sem a barra de tarefas."""

    return [
        tela.availableGeometry()
        for tela in QGuiApplication.screens()
    ]


class Passeio(QObject):
    def __init__(
        self,
        janela,
        pode_andar,
        *,
        telas=telas_disponiveis,
        sorteio=None,
        parent=None,
    ):
        # A janela entra como colaboradora, não como dona: o Passeio só
        # chama pos(), move(), width() e height() nela. Assim o teste
        # passa um dublê simples, sem precisar de um QWidget de verdade.
        super().__init__(parent)

        self.janela = janela
        self.pode_andar = pode_andar

        self._telas = telas
        self._sorteio = sorteio or random.Random()

        self.destino = None

        # -1 andando para a esquerda, +1 para a direita. Quem lê isso é
        # a animação, para espelhar a imagem.
        self.direcao = 1

        # Posição em número quebrado. A janela só aceita pixel inteiro,
        # mas guardar o resto é o que permite ela andar devagar de
        # verdade na frenagem, em vez de travar de 1 em 1 pixel.
        self.x = 0.0
        self.y = 0.0

        # Quanto ela já caminhou nesta volta, e o quanto falta. A
        # animação usa a distância para dar o ritmo do quique: se ela
        # desacelera, o corpo desacelera junto, em vez de patinar.
        self.andado = 0.0
        self.total = 0.0

        # Ritmo desta volta e pausa no meio do caminho, em tiques.
        self.ritmo = 1.0
        self.pausa = 0

        self.descanso = QTimer(self)
        self.descanso.setSingleShot(True)
        self.descanso.timeout.connect(self.sair_para_passear)

        self.passo = QTimer(self)
        self.passo.setInterval(INTERVALO)
        self.passo.timeout.connect(self.dar_passo)

    # ========================================================
    # LIGA E DESLIGA
    # ========================================================

    def comecar(self):
        """Entra no ciclo. A primeira volta só sai depois do descanso."""

        self.descansar()

    def parar(self):
        """Congela onde estiver, sem devolver a janela para o canto."""

        self.passo.stop()
        self.descanso.stop()

        self.destino = None

    @property
    def andando(self):
        """Neste instante ela está de fato se deslocando.

        Parada no meio do caminho não conta: ali ela volta a respirar,
        que é o que um bicho faz quando para para olhar alguma coisa."""

        return (
            self.passo.isActive()
            and
            self.pausa == 0
        )

    @property
    def ativo(self):
        return (
            self.passo.isActive()
            or
            self.descanso.isActive()
        )

    def alternar(self, ligado):
        if ligado:
            self.comecar()
        else:
            self.parar()

    # ========================================================
    # CICLO
    # ========================================================

    def descansar(self):
        """Para de andar e marca a hora da próxima volta."""

        self.passo.stop()

        self.destino = None

        self.descanso.start(
            self._sorteio.randint(
                DESCANSO_MIN,
                DESCANSO_MAX
            )
        )

    def sair_para_passear(self):
        """Escolhe para onde ir. Se não puder andar agora, espera mais."""

        if not self.pode_andar():
            self.descansar()

            return

        destino = self.sortear_destino()

        if destino is None:
            self.descansar()

            return

        atual = self.janela.pos()

        self.destino = destino

        self.x = float(atual.x())
        self.y = float(atual.y())

        self.andado = 0.0

        self.total = math.hypot(
            destino.x() - self.x,
            destino.y() - self.y
        )

        self.ritmo = self._sorteio.uniform(
            RITMO_MIN,
            RITMO_MAX
        )

        self.pausa = 0

        self.direcao = (
            1
            if destino.x() >= atual.x()
            else -1
        )

        self.passo.start()

    def sortear_destino(self):
        """Um ponto rente ao pé de algum monitor.

        Ela some se andar para fora da área útil, então a conta desconta
        o tamanho dela e ainda deixa a margem."""

        areas = self._telas()

        if not areas:
            return None

        area = self._sorteio.choice(areas)

        largura = self.janela.width()
        altura = self.janela.height()

        menor_x = area.left() + MARGEM
        maior_x = area.right() - largura - MARGEM

        if maior_x <= menor_x:
            return None

        return QPoint(
            self._sorteio.randint(
                menor_x,
                maior_x
            ),

            area.bottom() - altura - MARGEM
        )

    def dar_passo(self):
        """Um tique de caminhada.

        Se ela perdeu a permissão de andar no meio do caminho (o dono
        clicou nela, abriu a conversa, ela começou a falar), a volta é
        abandonada na hora e ela fica onde está."""

        if self.destino is None:
            self.descansar()

            return

        if not self.pode_andar():
            self.descansar()

            return

        if self.pausa > 0:
            self.pausa -= 1

            return

        if self.hora_de_parar_um_pouco():
            self.pausa = self._sorteio.randint(
                PAUSA_MIN,
                PAUSA_MAX
            )

            return

        falta_x = self.destino.x() - self.x
        falta_y = self.destino.y() - self.y

        falta = math.hypot(
            falta_x,
            falta_y
        )

        avanco = self.velocidade()

        if falta <= avanco:
            self.chegar()

            return

        self.x += avanco * falta_x / falta
        self.y += avanco * falta_y / falta

        self.andado += avanco

        self.janela.move(
            round(self.x),
            round(self.y)
        )

    def velocidade(self):
        """Pixels neste tique.

        Ela acelera nos primeiros pixels da volta e freia nos últimos.
        Sem isso ela arranca e estanca de uma vez, que é o que faz o
        movimento parecer carrinho de esteira."""

        entrando = self.andado / RAMPA

        saindo = (
            self.total - self.andado
        ) / RAMPA

        fator = max(
            VEL_MINIMA,
            min(
                1.0,
                entrando,
                saindo
            )
        )

        return VELOCIDADE * self.ritmo * fator

    def hora_de_parar_um_pouco(self):
        """Uma paradinha no meio do caminho, de vez em quando.

        Não vale bem no começo nem bem no fim: parar em cima da rampa
        ficaria com cara de travamento, não de curiosidade."""

        if self.andado < RAMPA or (self.total - self.andado) < RAMPA:
            return False

        return self._sorteio.random() < PAUSA_CHANCE

    def chegar(self):
        """Encosta no destino exato e senta."""

        self.x = float(self.destino.x())
        self.y = float(self.destino.y())

        self.janela.move(
            round(self.x),
            round(self.y)
        )

        self.descansar()
