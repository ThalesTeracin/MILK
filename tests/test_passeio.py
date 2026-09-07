# Milk — assistente pessoal.
# Copyright (c) 2026 Thales Teracin. Todos os direitos reservados.
#
# Software proprietário. É proibida a cópia, a distribuição, a
# modificação e a engenharia reversa, no todo ou em parte, sem
# autorização expressa e por escrito do autor. Ver LICENSE.txt.

"""Passeio da Milk pela area de trabalho.

Os monitores e o sorteio sao injetados, entao os testes valem em
qualquer maquina, com um monitor ou com quatro. Nada aqui depende do
monitor real de quem roda.

Rodar:  .venv\\Scripts\\python.exe -m unittest discover -s tests -v
"""

import os
import random
import sys
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

sys.path.insert(
    0,
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )
)

from PySide6.QtCore import QPoint, QRect
from PySide6.QtWidgets import QApplication

from milk.avatar.passeio import MARGEM, RAMPA, VELOCIDADE, Passeio


app = QApplication.instance() or QApplication([])


class JanelaFalsa:
    """So o que o Passeio usa de uma janela: onde esta e como mover."""

    def __init__(self, x=0, y=0, largura=230, altura=285):
        self._pos = QPoint(x, y)
        self._largura = largura
        self._altura = altura

        self.caminho = [QPoint(x, y)]

    def pos(self):
        return self._pos

    def move(self, x, y):
        self._pos = QPoint(x, y)

        self.caminho.append(QPoint(x, y))

    def width(self):
        return self._largura

    def height(self):
        return self._altura


UM_MONITOR = [QRect(0, 0, 1920, 1040)]

DOIS_MONITORES = [
    QRect(0, 0, 1920, 1040),
    QRect(1920, 0, 1920, 1040),
]


def montar_passeio(janela=None, pode_andar=None, telas=UM_MONITOR, semente=7):
    janela = janela or JanelaFalsa()

    passeio = Passeio(
        janela,
        pode_andar or (lambda: True),
        telas=lambda: list(telas),
        sorteio=random.Random(semente),
    )

    return passeio, janela


class TestDestino(unittest.TestCase):
    def test_destino_cabe_na_tela(self):
        passeio, janela = montar_passeio()

        for _ in range(200):
            destino = passeio.sortear_destino()

            self.assertGreaterEqual(destino.x(), MARGEM)

            self.assertLessEqual(
                destino.x() + janela.width(),
                1920 - MARGEM
            )

            self.assertLessEqual(
                destino.y() + janela.height(),
                1040 - MARGEM
            )

    def test_ela_anda_rente_ao_pe_da_tela(self):
        passeio, janela = montar_passeio()

        # bottom() do Qt e a ultima linha valida, nao a altura.
        esperado = UM_MONITOR[0].bottom() - janela.height() - MARGEM

        for _ in range(50):
            self.assertEqual(
                passeio.sortear_destino().y(),
                esperado
            )

    def test_com_dois_monitores_ela_visita_os_dois(self):
        passeio, _ = montar_passeio(telas=DOIS_MONITORES)

        visitados = {
            passeio.sortear_destino().x() >= 1920
            for _ in range(200)
        }

        self.assertEqual(visitados, {True, False})

    def test_tela_menor_que_a_milk_nao_gera_destino(self):
        passeio, _ = montar_passeio(
            telas=[QRect(0, 0, 100, 100)]
        )

        self.assertIsNone(passeio.sortear_destino())

    def test_sem_monitor_nao_gera_destino(self):
        passeio, _ = montar_passeio(telas=[])

        self.assertIsNone(passeio.sortear_destino())


def rumo_a(passeio, janela, destino):
    """Prepara uma volta ate `destino` sem depender do relogio."""

    janela_x, janela_y = janela.pos().x(), janela.pos().y()

    passeio.destino = destino
    passeio.x = float(janela_x)
    passeio.y = float(janela_y)
    passeio.andado = 0.0
    passeio.total = (
        (destino.x() - janela_x) ** 2
        + (destino.y() - janela_y) ** 2
    ) ** 0.5
    passeio.ritmo = 1.0
    passeio.pausa = 0


class TestCaminhada(unittest.TestCase):
    def test_o_passo_e_curto(self):
        janela = JanelaFalsa(0, 500)

        passeio, _ = montar_passeio(janela=janela)

        rumo_a(passeio, janela, QPoint(900, 500))

        passeio.dar_passo()

        self.assertLessEqual(janela.pos().x(), VELOCIDADE)

    def test_ela_chega_no_destino_sem_passar_do_ponto(self):
        janela = JanelaFalsa(0, 500)

        passeio, _ = montar_passeio(janela=janela)

        rumo_a(passeio, janela, QPoint(300, 500))

        for _ in range(500):
            passeio.dar_passo()

        self.assertEqual(janela.pos(), QPoint(300, 500))

    def test_chegar_encerra_a_caminhada(self):
        janela = JanelaFalsa(0, 500)

        passeio, _ = montar_passeio(janela=janela)

        rumo_a(passeio, janela, QPoint(1, 500))

        passeio.dar_passo()

        self.assertIsNone(passeio.destino)
        self.assertFalse(passeio.passo.isActive())

    def test_ela_anda_na_diagonal_entre_monitores(self):
        janela = JanelaFalsa(0, 100)

        passeio, _ = montar_passeio(janela=janela)

        rumo_a(passeio, janela, QPoint(400, 500))

        for _ in range(2000):
            passeio.dar_passo()

        self.assertEqual(janela.pos(), QPoint(400, 500))


class TestMovimentoNatural(unittest.TestCase):
    """Ela acelera, freia e as vezes para no meio do caminho."""

    def test_ela_arranca_devagar(self):
        janela = JanelaFalsa(0, 500)

        passeio, _ = montar_passeio(janela=janela)

        rumo_a(passeio, janela, QPoint(1200, 500))

        primeira = passeio.velocidade()

        while passeio.andado < RAMPA * 1.5:
            passeio.dar_passo()

        self.assertLess(primeira, passeio.velocidade())

    def test_ela_freia_para_chegar(self):
        janela = JanelaFalsa(0, 500)

        passeio, _ = montar_passeio(janela=janela)

        rumo_a(passeio, janela, QPoint(1200, 500))

        while passeio.andado < 600:
            passeio.dar_passo()

        no_meio = passeio.velocidade()

        while passeio.destino and passeio.andado < 1200 - RAMPA / 3:
            passeio.dar_passo()

        self.assertLess(passeio.velocidade(), no_meio)

    def test_ela_nunca_para_de_vez_no_meio_da_rampa(self):
        janela = JanelaFalsa(0, 500)

        passeio, _ = montar_passeio(janela=janela)

        rumo_a(passeio, janela, QPoint(1200, 500))

        for _ in range(1000):
            if passeio.destino is None:
                break

            self.assertGreater(passeio.velocidade(), 0)

            passeio.dar_passo()

    def test_cada_volta_tem_um_ritmo_proprio(self):
        janela = JanelaFalsa(300, 500)

        passeio, _ = montar_passeio(janela=janela)

        ritmos = set()

        for _ in range(20):
            passeio.sair_para_passear()

            ritmos.add(round(passeio.ritmo, 3))

        self.assertGreater(len(ritmos), 1)

    def test_a_pausa_no_meio_do_caminho_segura_ela(self):
        janela = JanelaFalsa(0, 500)

        passeio, _ = montar_passeio(janela=janela)

        rumo_a(passeio, janela, QPoint(1200, 500))

        passeio.pausa = 5

        parada_em = janela.pos()

        passeio.dar_passo()

        self.assertEqual(janela.pos(), parada_em)
        self.assertEqual(passeio.pausa, 4)

    def test_parada_no_meio_do_caminho_ela_nao_conta_como_andando(self):
        passeio, _ = montar_passeio()

        passeio.passo.start()
        passeio.pausa = 3

        self.assertFalse(passeio.andando)

        passeio.pausa = 0

        self.assertTrue(passeio.andando)

        passeio.parar()

    def test_ela_nao_para_em_cima_da_rampa(self):
        janela = JanelaFalsa(0, 500)

        passeio, _ = montar_passeio(janela=janela)

        rumo_a(passeio, janela, QPoint(1200, 500))

        # Comeco da volta: ainda na rampa de arrancada.
        passeio.andado = 5

        self.assertFalse(passeio.hora_de_parar_um_pouco())

        # Fim da volta: ja freando para chegar.
        passeio.andado = passeio.total - 5

        self.assertFalse(passeio.hora_de_parar_um_pouco())

    def test_a_distancia_andada_cresce_com_a_caminhada(self):
        janela = JanelaFalsa(0, 500)

        passeio, _ = montar_passeio(janela=janela)

        rumo_a(passeio, janela, QPoint(600, 500))

        marcos = []

        for _ in range(40):
            passeio.dar_passo()

            marcos.append(passeio.andado)

        self.assertEqual(marcos, sorted(marcos))
        self.assertGreater(marcos[-1], 0)

    def test_direcao_acompanha_o_destino(self):
        janela = JanelaFalsa(900, 500)

        passeio, _ = montar_passeio(
            janela=janela,
            telas=[QRect(0, 0, 400, 1040)]
        )

        passeio.sair_para_passear()

        self.assertEqual(passeio.direcao, -1)


class TestTravas(unittest.TestCase):
    """Ela nao pode andar por cima do que o dono esta fazendo."""

    def test_sem_permissao_ela_nao_sai_do_lugar(self):
        janela = JanelaFalsa(300, 500)

        passeio, _ = montar_passeio(
            janela=janela,
            pode_andar=lambda: False
        )

        passeio.sair_para_passear()

        self.assertIsNone(passeio.destino)
        self.assertFalse(passeio.passo.isActive())
        self.assertEqual(janela.pos(), QPoint(300, 500))

    def test_perder_a_permissao_no_meio_do_caminho_para_a_volta(self):
        janela = JanelaFalsa(0, 500)

        permitido = {"valor": True}

        passeio, _ = montar_passeio(
            janela=janela,
            pode_andar=lambda: permitido["valor"]
        )

        rumo_a(passeio, janela, QPoint(900, 500))

        passeio.dar_passo()

        parou_em = janela.pos()

        permitido["valor"] = False

        passeio.dar_passo()

        self.assertEqual(janela.pos(), parou_em)
        self.assertIsNone(passeio.destino)

    def test_sem_permissao_ela_tenta_de_novo_mais_tarde(self):
        passeio, _ = montar_passeio(pode_andar=lambda: False)

        passeio.sair_para_passear()

        # Nao desiste de vez: volta a contar o descanso.
        self.assertTrue(passeio.descanso.isActive())


class TestLigaDesliga(unittest.TestCase):
    def test_comecar_deixa_ativo_sem_sair_andando_na_hora(self):
        passeio, janela = montar_passeio()

        passeio.comecar()

        self.assertTrue(passeio.ativo)
        self.assertFalse(passeio.passo.isActive())
        self.assertEqual(janela.caminho, [QPoint(0, 0)])

    def test_parar_desliga_tudo(self):
        passeio, _ = montar_passeio()

        passeio.comecar()
        passeio.parar()

        self.assertFalse(passeio.ativo)
        self.assertIsNone(passeio.destino)

    def test_parar_nao_devolve_a_milk_para_o_canto(self):
        janela = JanelaFalsa(742, 500)

        passeio, _ = montar_passeio(janela=janela)

        passeio.comecar()
        passeio.parar()

        self.assertEqual(janela.pos(), QPoint(742, 500))

    def test_alternar_liga_e_desliga(self):
        passeio, _ = montar_passeio()

        passeio.alternar(True)
        self.assertTrue(passeio.ativo)

        passeio.alternar(False)
        self.assertFalse(passeio.ativo)


if __name__ == "__main__":
    unittest.main(verbosity=2)
