# Milk — assistente pessoal.
# Copyright (c) 2026 Thales Teracin. Todos os direitos reservados.
#
# Software proprietário. É proibida a cópia, a distribuição, a
# modificação e a engenharia reversa, no todo ou em parte, sem
# autorização expressa e por escrito do autor. Ver LICENSE.txt.

"""Porta de entrada da arte de caminhada.

Enquanto ninguem colocar quadros em assets/avatar/, tudo isso devolve
vazio e a Milk segue com o balanco procedural. Estes testes garantem que
o dia em que a arte chegar ela entra sozinha, e que arquivo torto nao
vira lixo desenhado na tela.

Rodar:  .venv\\Scripts\\python.exe -m unittest discover -s tests -v
"""

import os
import sys
import tempfile
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

from PySide6.QtGui import QColor, QPainter, QPixmap
from PySide6.QtWidgets import QApplication

from milk.avatar.quadros import (
    quadros_de_folha,
    quadros_de_pasta,
    redimensionar,
)


app = QApplication.instance() or QApplication([])


def folha_falsa(caminho, quantidade=6, lado=64):
    """Uma folha de sprites com os quadros lado a lado."""

    folha = QPixmap(lado * quantidade, lado)

    folha.fill(QColor(0, 0, 0, 0))

    pintor = QPainter(folha)

    for indice in range(quantidade):
        # Cada quadro com um tom diferente, para dar para conferir a ordem.
        pintor.fillRect(
            indice * lado,
            0,
            lado,
            lado,
            QColor(10 + indice * 30, 60, 60)
        )

    pintor.end()

    folha.save(caminho)


def quadro_falso(caminho, lado=64, tom=120):
    pixmap = QPixmap(lado, lado)

    pixmap.fill(QColor(tom, tom, tom))

    pixmap.save(caminho)


class TestFolhaDeSprites(unittest.TestCase):
    def test_a_folha_e_fatiada_em_quadros_quadrados(self):
        with tempfile.TemporaryDirectory() as pasta:
            caminho = os.path.join(pasta, "andando.png")

            folha_falsa(caminho, quantidade=6, lado=64)

            quadros = quadros_de_folha(caminho)

            self.assertEqual(len(quadros), 6)

            for quadro in quadros:
                self.assertEqual(
                    (quadro.width(), quadro.height()),
                    (64, 64)
                )

    def test_a_ordem_dos_quadros_e_preservada(self):
        with tempfile.TemporaryDirectory() as pasta:
            caminho = os.path.join(pasta, "andando.png")

            folha_falsa(caminho, quantidade=4, lado=32)

            quadros = quadros_de_folha(caminho)

            tons = [
                quadro.toImage().pixelColor(16, 16).red()
                for quadro in quadros
            ]

            self.assertEqual(tons, sorted(tons))

    def test_folha_com_um_quadro_so_nao_e_ciclo(self):
        with tempfile.TemporaryDirectory() as pasta:
            caminho = os.path.join(pasta, "andando.png")

            quadro_falso(caminho, lado=64)

            self.assertEqual(quadros_de_folha(caminho), [])

    def test_arquivo_que_nao_existe_devolve_vazio(self):
        self.assertEqual(
            quadros_de_folha("nao_existe_mesmo.png"),
            []
        )


class TestPastaDeQuadros(unittest.TestCase):
    def test_um_arquivo_por_quadro_em_ordem_de_nome(self):
        with tempfile.TemporaryDirectory() as pasta:
            for indice, tom in enumerate([30, 90, 150], start=1):
                quadro_falso(
                    os.path.join(pasta, f"0{indice}.png"),
                    tom=tom
                )

            quadros = quadros_de_pasta(pasta)

            self.assertEqual(len(quadros), 3)

            tons = [
                quadro.toImage().pixelColor(10, 10).red()
                for quadro in quadros
            ]

            self.assertEqual(tons, [30, 90, 150])

    def test_arquivo_que_nao_e_imagem_e_ignorado(self):
        with tempfile.TemporaryDirectory() as pasta:
            quadro_falso(os.path.join(pasta, "01.png"))

            with open(
                os.path.join(pasta, "leia-me.txt"),
                "w",
                encoding="utf-8"
            ) as arquivo:
                arquivo.write("coloque os quadros aqui")

            self.assertEqual(len(quadros_de_pasta(pasta)), 1)

    def test_pasta_que_nao_existe_devolve_vazio(self):
        self.assertEqual(
            quadros_de_pasta("pasta_que_nao_existe"),
            []
        )


class TestRedimensionar(unittest.TestCase):
    def test_todos_saem_na_mesma_altura(self):
        quadros = [
            QPixmap(40, 40),
            QPixmap(80, 80),
            QPixmap(55, 55),
        ]

        for quadro in quadros:
            quadro.fill(QColor(200, 200, 200))

        prontos = redimensionar(quadros, 110)

        for quadro in prontos:
            self.assertEqual(quadro.height(), 110)

    def test_quadro_esticado_e_descartado(self):
        """Folha fatiada errado vira faixa comprida.

        Desenhar aquilo esticado na tela e pior que continuar parada."""

        esticado = QPixmap(600, 40)
        esticado.fill(QColor(200, 200, 200))

        certo = QPixmap(40, 40)
        certo.fill(QColor(200, 200, 200))

        prontos = redimensionar([esticado, certo], 110)

        self.assertEqual(len(prontos), 1)

    def test_sem_quadros_continua_sem_quadros(self):
        self.assertEqual(redimensionar([], 110), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
