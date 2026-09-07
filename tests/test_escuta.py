# Milk — assistente pessoal.
# Copyright (c) 2026 Thales Teracin. Todos os direitos reservados.
#
# Software proprietário. É proibida a cópia, a distribuição, a
# modificação e a engenharia reversa, no todo ou em parte, sem
# autorização expressa e por escrito do autor. Ver LICENSE.txt.

"""Escuta contínua: detector de fala e wake word.

O microfone desta máquina está entregando silêncio, então nada aqui
depende dele: o áudio é gerado no próprio teste e a transcrição é um
dublê. O que se testa é a decisão — o que é fala, o que é ruído, o que
é com a Milk e o que não é.

Rodar:  .venv\\Scripts\\python.exe -m unittest discover -s tests -v
"""

import os
import sys
import unittest

import numpy as np

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

sys.path.insert(
    0,
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )
)

from PySide6.QtWidgets import QApplication

from milk.voice import transcricao
from milk.voice.escuta import EscutaWorker, tem_o_nome, tirar_o_nome
from milk.voice.vad import Detector


app = QApplication.instance() or QApplication([])


TAXA = 16000
BLOCO = 1024


def silencio(quantos, nivel=20.0):
    """Blocos de sala vazia: só um chiadinho."""

    gerador = np.random.default_rng(3)

    return [
        (gerador.normal(0, nivel, BLOCO)).astype(np.int16)
        for _ in range(quantos)
    ]


def fala(quantos, nivel=4000.0):
    """Blocos com energia de voz."""

    gerador = np.random.default_rng(7)

    return [
        (gerador.normal(0, nivel, BLOCO)).astype(np.int16)
        for _ in range(quantos)
    ]


# ============================================================
# DETECTOR
# ============================================================

class TestDetector(unittest.TestCase):

    def detector(self, **extras):
        return Detector(TAXA, BLOCO, **extras)

    def test_calibra_antes_de_valer(self):
        detector = self.detector()

        for bloco in silencio(4):
            self.assertIsNone(detector.alimentar(bloco))

        self.assertTrue(detector.calibrando())

        for bloco in silencio(4):
            detector.alimentar(bloco)

        self.assertFalse(detector.calibrando())

    def test_silencio_nao_vira_fala(self):
        detector = self.detector()

        respostas = [
            detector.alimentar(bloco)
            for bloco in silencio(40)
        ]

        self.assertTrue(
            all(
                resposta is None
                for resposta in respostas
            )
        )

    def test_fala_comeca_e_termina(self):
        detector = self.detector()

        for bloco in silencio(10):
            detector.alimentar(bloco)

        comecou = False

        for bloco in fala(20):
            resposta = detector.alimentar(bloco)

            if resposta == "comecou":
                comecou = True

        self.assertTrue(comecou)

        trecho = None

        for bloco in silencio(30):
            resposta = detector.alimentar(bloco)

            if isinstance(resposta, np.ndarray):
                trecho = resposta

                break

        self.assertIsNotNone(trecho)

        # O trecho tem o tamanho da fala, não da sala inteira.
        self.assertGreaterEqual(len(trecho), 20 * BLOCO)
        self.assertLess(len(trecho), 40 * BLOCO)

    def test_barulho_curto_nao_vira_fala(self):
        detector = self.detector(fala_minima=0.5)

        for bloco in silencio(10):
            detector.alimentar(bloco)

        # Um estalo de dois blocos: curto demais.
        for bloco in fala(2):
            detector.alimentar(bloco)

        trecho = None

        for bloco in silencio(30):
            resposta = detector.alimentar(bloco)

            if isinstance(resposta, np.ndarray):
                trecho = resposta

        self.assertIsNone(trecho)

    def test_fala_sem_fim_e_cortada(self):
        detector = self.detector(fala_maxima=0.5)

        for bloco in silencio(10):
            detector.alimentar(bloco)

        cortou = False

        for bloco in fala(60):
            resposta = detector.alimentar(bloco)

            if isinstance(resposta, np.ndarray):
                cortou = True

                break

        self.assertTrue(cortou)

    def test_sala_barulhenta_sobe_o_limite(self):
        quieto = self.detector()
        barulhento = self.detector()

        for bloco in silencio(10, nivel=10):
            quieto.alimentar(bloco)

        for bloco in silencio(10, nivel=800):
            barulhento.alimentar(bloco)

        self.assertGreater(
            barulhento.limite(),
            quieto.limite()
        )

    def test_bloco_vazio_nao_quebra(self):
        detector = self.detector()

        self.assertEqual(
            detector.energia(np.array([], dtype=np.int16)),
            0.0
        )


# ============================================================
# WAKE WORD
# ============================================================

class TestNome(unittest.TestCase):

    def test_jeitos_de_chamar(self):
        for frase in (
            "Milk, que horas são",
            "milk que horas são",
            "Milk. Abra o Chrome",
            "oi Milk, tudo bem?",
            "milque, vem cá",
            "Milki, você está aí?",
        ):
            with self.subTest(frase=frase):
                self.assertTrue(tem_o_nome(frase))

    def test_fala_que_nao_e_com_ela(self):
        for frase in (
            "amanhã eu preciso comprar leite",
            "você viu o jogo ontem",
            "vou sair agora",
        ):
            with self.subTest(frase=frase):
                self.assertFalse(tem_o_nome(frase))

    def test_tirar_o_nome(self):
        self.assertEqual(
            tirar_o_nome("Milk, que horas são?"),
            "que horas são?"
        )

        self.assertEqual(
            tirar_o_nome("milk abre o chrome"),
            "abre o chrome"
        )

        self.assertEqual(
            tirar_o_nome("Milk"),
            ""
        )


# ============================================================
# O WORKER, SEM MICROFONE E SEM INTERNET
# ============================================================

class FluxoFalso:
    """Faz as vezes do InputStream do sounddevice."""

    def __init__(self, blocos):
        self.blocos = list(blocos)
        self.fechado = False

    def read(self, quantos):
        if not self.blocos:
            return None, False

        return self.blocos.pop(0), False

    def stop(self):
        self.fechado = True

    def close(self):
        self.fechado = True


class TestEscuta(unittest.TestCase):

    def montar(self, blocos, transcricoes, tempo=None):
        """Um worker com microfone e transcrição de mentira."""

        fluxo = FluxoFalso(blocos)

        falas = list(transcricoes)

        def transcritor(amostras, taxa):
            if not falas:
                raise transcricao.SemFala()

            resposta = falas.pop(0)

            if isinstance(resposta, Exception):
                raise resposta

            return resposta

        relogio = tempo or (lambda: 0.0)

        worker = EscutaWorker(
            abrir_microfone=lambda: (fluxo, TAXA, "microfone de teste"),
            transcritor=transcritor,
            tamanho_do_bloco=BLOCO,
            relogio=relogio,
        )

        worker.fluxo = fluxo

        return worker

    def rodar(self, worker):
        """Roda o laço na mesma thread, sem subir QThread de verdade."""

        ouvidos = []
        acordadas = []

        worker.ouviu.connect(ouvidos.append)
        worker.acordou.connect(lambda: acordadas.append(1))

        worker.run()

        return ouvidos, acordadas

    def blocos_de_uma_fala(self):
        return silencio(10) + fala(15) + silencio(30)

    def test_atende_quando_e_chamada(self):
        worker = self.montar(
            self.blocos_de_uma_fala(),
            ["Milk, que horas são"],
        )

        ouvidos, acordadas = self.rodar(worker)

        self.assertEqual(ouvidos, ["que horas são"])
        self.assertEqual(len(acordadas), 1)

    def test_ignora_conversa_que_nao_e_com_ela(self):
        worker = self.montar(
            self.blocos_de_uma_fala(),
            ["preciso comprar leite amanhã"],
        )

        ouvidos, acordadas = self.rodar(worker)

        self.assertEqual(ouvidos, [])
        self.assertEqual(acordadas, [])

    def test_so_o_nome_nao_vira_pedido(self):
        worker = self.montar(
            self.blocos_de_uma_fala(),
            ["Milk"],
        )

        ouvidos, acordadas = self.rodar(worker)

        self.assertEqual(ouvidos, [])
        self.assertEqual(len(acordadas), 1)

    def test_continua_ouvindo_depois_de_atender(self):
        blocos = (
            silencio(10)
            + fala(15) + silencio(20)
            + fala(15) + silencio(20)
        )

        worker = self.montar(
            blocos,
            ["Milk, que horas são", "e que dia é hoje"],
        )

        ouvidos, _ = self.rodar(worker)

        self.assertEqual(
            ouvidos,
            ["que horas são", "e que dia é hoje"]
        )

    def test_passada_a_janela_volta_a_exigir_o_nome(self):
        agora = [0.0]

        blocos = (
            silencio(10)
            + fala(15) + silencio(20)
            + fala(15) + silencio(20)
        )

        worker = self.montar(
            blocos,
            ["Milk, que horas são", "e que dia é hoje"],
            tempo=lambda: agora[0],
        )

        ouvidos = []

        worker.ouviu.connect(ouvidos.append)

        # O relógio anda muito depois da primeira fala.
        def andar(texto):
            agora[0] += 60.0

        worker.ouviu.connect(andar)

        worker.run()

        self.assertEqual(ouvidos, ["que horas são"])

    def test_falha_do_reconhecimento_nao_derruba(self):
        worker = self.montar(
            self.blocos_de_uma_fala() + fala(15) + silencio(20),
            [
                transcricao.ServicoIndisponivel("sem internet"),
                "Milk, e agora",
            ],
        )

        ouvidos, _ = self.rodar(worker)

        self.assertEqual(ouvidos, ["e agora"])

    def test_microfone_que_nao_abre_avisa(self):
        worker = EscutaWorker(
            abrir_microfone=lambda: None,
            transcritor=lambda amostras, taxa: "",
        )

        erros = []

        worker.erro.connect(erros.append)

        worker.run()

        self.assertEqual(len(erros), 1)
        self.assertIn("microfone", erros[0])

    def test_fecha_o_microfone_no_fim(self):
        worker = self.montar(silencio(5), [])

        worker.run()

        self.assertTrue(worker.fluxo.fechado)

    def test_parar_encerra_o_laco(self):
        worker = self.montar(silencio(200), [])

        # Para logo no comeco: o laco sai no proximo bloco.
        def parar_cedo(bloco):
            worker.parar()

            return None

        worker.ler = lambda fluxo: parar_cedo(None) or np.zeros(BLOCO, dtype=np.int16)

        worker.run()

        self.assertFalse(worker.rodando)


# ============================================================
# ESCOLHA DO MICROFONE
# ============================================================

class TestEscolhaDoMicrofone(unittest.TestCase):
    """O padrão do Windows pode estar mudo. Quem escolhe é a Milk."""

    def setUp(self):
        from milk.voice import dispositivos

        self.dispositivos = dispositivos

        self.interno = dispositivos.Entrada(
            1, "Grupo de Microfones (Qualcomm)", "MME", 44100, 1
        )

        self.fone_mme = dispositivos.Entrada(
            2, "Headset (RS27)", "MME", 44100, 1
        )

        self.fone_wasapi = dispositivos.Entrada(
            14, "Headset (RS27)", "Windows WASAPI", 16000, 1
        )

        self.todas = [self.interno, self.fone_mme, self.fone_wasapi]

    def escolher(self, dispositivo, api="", entradas=None, quem_ouve=None):
        from unittest.mock import patch

        valores = {
            ("microfone", "dispositivo"): dispositivo,
            ("microfone", "api"): api,
        }

        def obter_falso(secao, chave=None, padrao=None):
            return valores.get((secao, chave), padrao)

        with patch.object(self.dispositivos, "obter", obter_falso):
            return self.dispositivos.escolher(
                entradas if entradas is not None else self.todas,
                procurar=lambda entradas: quem_ouve,
            )

    def test_nome_pedido_manda(self):
        escolhida = self.escolher("Headset (RS27)")

        self.assertEqual(escolhida.nome, "Headset (RS27)")

    def test_api_pedida_desempata(self):
        escolhida = self.escolher(
            "Headset (RS27)",
            api="Windows WASAPI"
        )

        self.assertEqual(escolhida.indice, 14)

    def test_sem_api_pedida_vale_a_ordem_de_preferencia(self):
        escolhida = self.escolher("Headset (RS27)")

        # WASAPI vem antes de MME na ordem da casa.
        self.assertEqual(escolhida.api, "Windows WASAPI")

    def test_auto_pega_quem_esta_ouvindo(self):
        escolhida = self.escolher(
            "auto",
            quem_ouve=self.fone_wasapi
        )

        self.assertEqual(escolhida.indice, 14)

    def test_pedido_que_nao_existe_cai_na_procura(self):
        escolhida = self.escolher(
            "Fone Que Não Existe",
            quem_ouve=self.fone_mme
        )

        self.assertEqual(escolhida.indice, 2)

    def test_dispositivo_pedido(self):
        from unittest.mock import patch

        with patch.object(
            self.dispositivos,
            "obter",
            lambda secao, chave=None, padrao=None: "Headset (RS27)"
        ):
            self.assertEqual(
                self.dispositivos.dispositivo_pedido(),
                "Headset (RS27)"
            )

        with patch.object(
            self.dispositivos,
            "obter",
            lambda secao, chave=None, padrao=None: "auto"
        ):
            self.assertEqual(
                self.dispositivos.dispositivo_pedido(),
                ""
            )

    def test_descrever(self):
        self.assertIn(
            "WASAPI",
            self.dispositivos.descrever(self.fone_wasapi)
        )

        self.assertEqual(
            self.dispositivos.descrever(None),
            "nenhum microfone"
        )

    def test_lista_de_verdade_nao_quebra(self):
        # Roda na máquina: só não pode levantar exceção.
        entradas = self.dispositivos.listar_entradas()

        self.assertIsInstance(entradas, list)


if __name__ == "__main__":
    unittest.main()
