# Milk — assistente pessoal.
# Copyright (c) 2026 Thales Teracin. Todos os direitos reservados.
#
# Software proprietário. É proibida a cópia, a distribuição, a
# modificação e a engenharia reversa, no todo ou em parte, sem
# autorização expressa e por escrito do autor. Ver LICENSE.txt.

"""Ritmo do corpo da Milk.

Testes de geometria, nao de beleza: se ela quica, se pende para os dois
lados, se vira para o lado certo e se o quadro sai sempre do mesmo
tamanho. Se esta bonito ou nao, so o olho diz.

Rodar:  .venv\\Scripts\\python.exe -m unittest discover -s tests -v
"""

import os
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

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import QApplication

from milk.avatar.animacao import (
    INTERVALO,
    PASSO_PX,
    QUIQUE,
    RESPIRO,
    Animacao,
)


app = QApplication.instance() or QApplication([])


def base_falsa(largura=189, altura=199):
    pixmap = QPixmap(largura, altura)

    pixmap.fill(QColor(255, 255, 255))

    return pixmap


class Trilha:
    """Conta quantos pixels a Milk ja caminhou."""

    def __init__(self):
        self.px = 0.0

    def andar(self, quanto):
        self.px += quanto

        return self.px


def montar(andando=True, direcao=1, base=None, trilha=None, ciclo=None):
    quadros = []

    trilha = trilha or Trilha()

    animacao = Animacao(
        base or base_falsa(),
        quadros.append,
        andando=lambda: andando,
        direcao=lambda: direcao,
        percorrido=lambda: trilha.px,
        quadros=ciclo,
    )

    return animacao, quadros


def ciclo_falso(quantidade=4, lado=80):
    """Um ciclo de caminhada de mentira, cada quadro com um tom."""

    ciclo = []

    for indice in range(quantidade):
        quadro = QPixmap(lado, lado)

        quadro.fill(QColor(20 + indice * 40, 90, 90))

        ciclo.append(quadro)

    return ciclo


def ao_longo_de(animacao, trilha, passos=1, avanco=2.0):
    """Os gestos ao caminhar, pixel a pixel."""

    gestos = []

    for _ in range(round(passos * PASSO_PX / avanco)):
        trilha.andar(avanco)

        gestos.append(animacao.gesto())

    return gestos


class TestAndando(unittest.TestCase):
    def test_ela_quica_no_passo(self):
        trilha = Trilha()

        animacao, _ = montar(andando=True, trilha=trilha)

        subidas = [g[0] for g in ao_longo_de(animacao, trilha)]

        # Sobe (y negativo) e volta ao chao dentro de um passo.
        self.assertLess(min(subidas), -QUIQUE + 0.5)
        self.assertGreater(max(subidas), -1.5)

    def test_ela_nunca_afunda_no_chao(self):
        trilha = Trilha()

        animacao, _ = montar(andando=True, trilha=trilha)

        subidas = [
            g[0]
            for g in ao_longo_de(animacao, trilha, passos=4)
        ]

        self.assertLessEqual(max(subidas), 0)

    def test_ela_pende_para_os_dois_lados(self):
        trilha = Trilha()

        animacao, _ = montar(andando=True, trilha=trilha)

        angulos = [
            g[1]
            for g in ao_longo_de(animacao, trilha, passos=2)
        ]

        self.assertGreater(max(angulos), 1)
        self.assertLess(min(angulos), -1)

    def test_andando_ela_nao_incha(self):
        trilha = Trilha()

        animacao, _ = montar(andando=True, trilha=trilha)

        for _, _, escala in ao_longo_de(animacao, trilha, passos=2):
            self.assertEqual(escala, 1.0)

    def test_o_quique_segue_a_distancia_e_nao_o_relogio(self):
        """O tique do relogio passa; se ela nao andou, o corpo nao mexe.

        E isso que impede a Milk de patinar quando freia para chegar."""

        trilha = Trilha()

        animacao, _ = montar(andando=True, trilha=trilha)

        trilha.andar(11)

        parada = animacao.gesto()

        for _ in range(50):
            animacao.tempo += INTERVALO

        self.assertEqual(animacao.gesto(), parada)

        trilha.andar(7)

        self.assertNotEqual(animacao.gesto(), parada)


class TestCicloDesenhado(unittest.TestCase):
    """Quando a arte existir, ela manda; sem arte, nada muda."""

    def test_sem_arte_ela_usa_o_balanco_procedural(self):
        trilha = Trilha()

        animacao, _ = montar(andando=True, trilha=trilha)

        trilha.andar(PASSO_PX / 2)

        self.assertFalse(animacao.anima_desenhada)

        # O quique procedural continua acontecendo.
        self.assertLess(animacao.gesto()[0], 0)

    def test_com_arte_o_desenho_manda(self):
        trilha = Trilha()

        animacao, _ = montar(
            andando=True,
            trilha=trilha,
            ciclo=ciclo_falso()
        )

        trilha.andar(PASSO_PX / 2)

        self.assertTrue(animacao.anima_desenhada)

    def test_parada_ela_volta_para_o_png_sentado(self):
        animacao, _ = montar(
            andando=False,
            ciclo=ciclo_falso()
        )

        self.assertFalse(animacao.anima_desenhada)

    def test_o_quadro_do_ciclo_segue_a_distancia(self):
        trilha = Trilha()

        animacao, _ = montar(
            andando=True,
            trilha=trilha,
            ciclo=ciclo_falso(quantidade=4)
        )

        vistos = []

        for _ in range(4):
            vistos.append(
                animacao.desenho_do_passo()
                .toImage()
                .pixelColor(40, 40)
                .red()
            )

            trilha.andar(PASSO_PX / 4)

        # Quatro pontos da passada, quatro quadros diferentes.
        self.assertEqual(len(set(vistos)), 4)

    def test_o_ciclo_da_a_volta_sem_estourar(self):
        trilha = Trilha()

        animacao, _ = montar(
            andando=True,
            trilha=trilha,
            ciclo=ciclo_falso(quantidade=4)
        )

        for _ in range(200):
            trilha.andar(PASSO_PX / 3)

            animacao.desenho_do_passo()

    def test_a_tela_cabe_o_maior_quadro_do_ciclo(self):
        animacao, _ = montar(
            base=base_falsa(60, 60),
            ciclo=ciclo_falso(lado=140)
        )

        self.assertGreaterEqual(animacao.largura, 140)
        self.assertGreaterEqual(animacao.altura, 140)


class TestParada(unittest.TestCase):
    def test_parada_ela_respira(self):
        animacao, _ = montar(andando=False)

        escalas = []

        for _ in range(120):
            animacao.tempo += 40

            escalas.append(animacao.gesto()[2])

        self.assertGreater(max(escalas), 1 + RESPIRO / 2)
        self.assertLess(min(escalas), 1 - RESPIRO / 2)

    def test_o_respiro_e_discreto(self):
        animacao, _ = montar(andando=False)

        for _ in range(300):
            animacao.tempo += 40

            self.assertLess(
                abs(animacao.gesto()[2] - 1),
                0.03
            )

    def test_parada_ela_nao_quica_nem_pende(self):
        animacao, _ = montar(andando=False)

        for _ in range(120):
            animacao.tempo += 40

            subida, angulo, _ = animacao.gesto()

            self.assertEqual(subida, 0.0)
            self.assertEqual(angulo, 0.0)


class TestQuadro(unittest.TestCase):
    def test_o_quadro_tem_folga_para_a_inclinacao(self):
        animacao, _ = montar()

        self.assertGreater(animacao.largura, 189)
        self.assertGreater(animacao.altura, 199)

    def test_o_tamanho_nao_muda_ao_longo_da_animacao(self):
        animacao, quadros = montar()

        for _ in range(60):
            animacao.avancar()

        tamanhos = {
            (q.width(), q.height())
            for q in quadros
        }

        self.assertEqual(len(tamanhos), 1)

        self.assertEqual(
            tamanhos.pop(),
            (animacao.largura, animacao.altura)
        )

    def test_virar_para_a_esquerda_espelha_a_imagem(self):
        # Metade branca, metade preta: se espelhar, os lados trocam.
        base = QPixmap(100, 100)
        base.fill(QColor(255, 255, 255))

        from PySide6.QtGui import QPainter

        pintor = QPainter(base)
        pintor.fillRect(0, 0, 50, 100, QColor(0, 0, 0))
        pintor.end()

        def lado_escuro(direcao):
            animacao, quadros = montar(
                andando=False,
                direcao=direcao,
                base=base
            )

            animacao.avancar()

            imagem = quadros[0].toImage()

            meio = animacao.altura // 2

            esquerda = imagem.pixelColor(
                animacao.largura // 2 - 30,
                meio
            ).value()

            direita = imagem.pixelColor(
                animacao.largura // 2 + 30,
                meio
            ).value()

            return "esquerda" if esquerda < direita else "direita"

        self.assertNotEqual(
            lado_escuro(1),
            lado_escuro(-1)
        )


class TestRelogio(unittest.TestCase):
    def test_comecar_ja_desenha_o_primeiro_quadro(self):
        animacao, quadros = montar()

        animacao.comecar()

        self.assertEqual(len(quadros), 1)
        self.assertTrue(animacao.relogio.isActive())

        animacao.parar()

    def test_parar_congela(self):
        animacao, _ = montar()

        animacao.comecar()
        animacao.parar()

        self.assertFalse(animacao.relogio.isActive())


if __name__ == "__main__":
    unittest.main(verbosity=2)
