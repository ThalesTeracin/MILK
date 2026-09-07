# Milk — assistente pessoal.
# Copyright (c) 2026 Thales Teracin. Todos os direitos reservados.
#
# Software proprietário. É proibida a cópia, a distribuição, a
# modificação e a engenharia reversa, no todo ou em parte, sem
# autorização expressa e por escrito do autor. Ver LICENSE.txt.

"""Ela atende quando é chamada.

Estes testes nasceram de uma sessão real, gravada em `logs/voice`, em
que o microfone finalmente funcionou e mesmo assim a Milk não atendeu.
Cada caso aqui é uma frase que ela ouviu de verdade naquele dia e
ignorou.
"""

import sys
import unittest

from pathlib import Path

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1])
)

import numpy as np

from milk.voice.vad import Detector
from milk.voice.escuta import EscutaWorker, tem_o_nome, tirar_o_nome
from milk.intelligence.rotas_conversa import (
    atender_ao_nome,
    responder_conversa,
    rota_conversa,
)


# ============================================================
# O NOME EM QUALQUER LUGAR DA FRASE
# ============================================================

class TestChamadaPeloNome(unittest.TestCase):
    """Frases reais do log de 05/09/2026, às 20h."""

    def test_o_nome_no_fim_tambem_chama(self):
        for frase in (
            "Pode fechar o navegador para mim milk",
            "fecha o navegador, milk",
            "Olá milk",
            "que horas são milk",
        ):
            with self.subTest(frase=frase):
                self.assertTrue(
                    tem_o_nome(frase),
                    "chamar pelo nome no fim é o normal em português"
                )

    def test_o_reconhecimento_troca_o_M_do_comeco(self):
        # Log real de 06/09/2026, 17h18: ela foi chamada, o
        # reconhecimento escreveu Silk, e ela ficou calada. Milk e
        # Silk sao a mesma coisa para o ouvido; tem de ser a mesma
        # coisa para ela.
        for frase in (
            "Silk fecha o navegador",
            "silk, que horas sao",
            "fecha o navegador, silk",
            "Nilk que horas sao",
            "Bilk abre o bloco de notas",
            "Zilk, oi",
        ):
            with self.subTest(frase=frase):
                self.assertTrue(
                    tem_o_nome(frase),
                    'o reconhecimento troca o M por outra consoante'
                )

    def test_o_pedido_fica_limpo_mesmo_com_o_M_trocado(self):
        self.assertEqual(
            tirar_o_nome("Silk fecha o navegador"),
            "fecha o navegador"
        )

        self.assertEqual(
            tirar_o_nome("fecha o navegador, Silk"),
            "fecha o navegador"
        )

    def test_palavra_comum_nao_vira_chamado(self):
        # A troca do M nao pode transformar conversa em chamado.
        for frase in (
            "preciso comprar leite amanha",
            "o filme foi otimo",
            "vou ligar para o silvio",
            "isso e um risco",
            "que silencio bom",
        ):
            with self.subTest(frase=frase):
                self.assertFalse(
                    tem_o_nome(frase),
                    'conversa normal nao e chamado'
                )

    def test_o_nome_grudado_na_palavra_anterior(self):
        # O reconhecimento junta "e aí, Milk" em "jamilk".
        self.assertTrue(
            tem_o_nome("jamilk boa noite tudo bem")
        )

        self.assertEqual(
            tirar_o_nome("jamilk boa noite tudo bem"),
            "boa noite tudo bem"
        )

    def test_o_nome_no_meio_nao_deixa_virgula_sobrando(self):
        # O vocativo no meio da frase tem virgula dos dois lados.
        # Tirando so o nome, as duas viravam uma virgula dupla.
        for frase, pedido in (
            ("fecha o navegador, Milk, por favor",
             "fecha o navegador, por favor"),
            ("me diz, Milk, que horas sao",
             "me diz, que horas sao"),
            ("abre o bloco de notas, Milk.",
             "abre o bloco de notas."),
        ):
            with self.subTest(frase=frase):
                self.assertEqual(
                    tirar_o_nome(frase),
                    pedido
                )

    def test_o_pedido_fica_limpo_venha_o_nome_de_onde_vier(self):
        for frase, pedido in (
            ("Milk, que horas são", "que horas são"),
            ("que horas são, Milk", "que horas são"),
            ("Pode fechar o navegador para mim milk",
             "Pode fechar o navegador para mim"),
            ("Milk", ""),
        ):
            with self.subTest(frase=frase):
                self.assertEqual(
                    tirar_o_nome(frase),
                    pedido
                )

    def test_conversa_da_sala_continua_sendo_ignorada(self):
        for frase in (
            "amanhã eu preciso comprar leite",
            "abra o navegador e vá para a página do UOL",
            "1000 acesse a página da Globo para mim",
            "milhares de coisas para fazer",
            "melancia com sal",
            "você viu o jogo ontem",
        ):
            with self.subTest(frase=frase):
                self.assertFalse(
                    tem_o_nome(frase)
                )


# ============================================================
# CHAMARAM SÓ O NOME
# ============================================================

TAXA = 16000
BLOCO = 512


def silencio(quantos):
    return [
        np.zeros(BLOCO, dtype=np.int16)
        for _ in range(quantos)
    ]


def fala(quantos):
    return [
        (
            np.sin(
                np.linspace(0, 40 * np.pi, BLOCO)
            ) * 8000
        ).astype(np.int16)
        for _ in range(quantos)
    ]


class FluxoFalso:
    """Devolve blocos combinados e depois acaba."""

    def __init__(self, blocos):
        self.blocos = list(blocos)

    def read(self, quantos):
        if not self.blocos:
            return None, False

        return self.blocos.pop(0), False

    def stop(self):
        pass

    def close(self):
        pass


def montar(blocos, textos, relogio=None):
    fila = list(textos)

    def transcritor(amostras, taxa):
        if not fila:
            raise AssertionError("transcreveu mais do que o esperado")

        return fila.pop(0)

    return EscutaWorker(
        abrir_microfone=lambda: (
            FluxoFalso(blocos),
            TAXA,
            "microfone de teste"
        ),
        transcritor=transcritor,
        tamanho_do_bloco=BLOCO,
        relogio=relogio or (lambda: 0.0),
    )


class TestSoONome(unittest.TestCase):

    def test_dizer_so_milk_pede_resposta_falada(self):
        """Antes isto só mudava a barra de status e parecia mudez."""

        worker = montar(
            silencio(10) + fala(15) + silencio(20),
            ["Milk"],
        )

        atendidas = []
        acordadas = []
        ouvidos = []

        worker.so_o_nome.connect(lambda: atendidas.append(1))
        worker.acordou.connect(lambda: acordadas.append(1))
        worker.ouviu.connect(ouvidos.append)

        worker.run()

        self.assertEqual(len(acordadas), 1, "tem que latir")
        self.assertEqual(len(atendidas), 1, "e tem que responder")
        self.assertEqual(ouvidos, [], "não havia pedido nenhum")

    def test_com_pedido_junto_ela_nao_responde_duas_vezes(self):
        worker = montar(
            silencio(10) + fala(15) + silencio(20),
            ["Milk, que horas são"],
        )

        atendidas = []
        ouvidos = []

        worker.so_o_nome.connect(lambda: atendidas.append(1))
        worker.ouviu.connect(ouvidos.append)

        worker.run()

        self.assertEqual(atendidas, [])
        self.assertEqual(ouvidos, ["que horas são"])


# ============================================================
# O OUVIDO FECHADO ENQUANTO ELA LATE E FALA
# ============================================================

class TestSurdez(unittest.TestCase):

    def montar_com_relogio(self, blocos, textos, agora):
        return montar(
            blocos,
            textos,
            relogio=lambda: agora[0]
        )

    def test_o_que_entra_enquanto_ela_fala_e_jogado_fora(self):
        agora = [0.0]

        worker = self.montar_com_relogio(
            silencio(10) + fala(15) + silencio(20),
            [],
            agora
        )

        worker.surdear(30.0)

        ouvidos = []
        worker.ouviu.connect(ouvidos.append)

        # Nenhuma transcrição pode acontecer: o transcritor levanta
        # AssertionError se for chamado.
        worker.run()

        self.assertEqual(ouvidos, [])

    def test_voltar_a_ouvir_encurta_a_surdez(self):
        agora = [0.0]

        worker = self.montar_com_relogio([], [], agora)

        worker.surdear(120.0)

        self.assertTrue(worker.surda())

        worker.voltar_a_ouvir(0.5)

        agora[0] = 0.6

        self.assertFalse(worker.surda())

    def test_surdear_so_estende(self):
        agora = [0.0]

        worker = self.montar_com_relogio([], [], agora)

        worker.surdear(10.0)
        worker.surdear(1.0)

        self.assertEqual(worker.surda_ate, 10.0)

    def test_o_detector_esquece_o_trecho_sem_perder_o_piso(self):
        detector = Detector(TAXA, BLOCO)

        for bloco in silencio(10):
            detector.alimentar(bloco)

        piso = detector.piso

        for bloco in fala(5):
            detector.alimentar(bloco)

        self.assertTrue(detector.falando)

        detector.esquecer()

        self.assertFalse(detector.falando)
        self.assertEqual(detector.trecho, [])
        self.assertEqual(detector.piso, piso)


# ============================================================
# CONVERSA CURTA, RESPONDIDA NA HORA
# ============================================================

class TestConversaCurta(unittest.TestCase):
    """Sem isto, "oi" custava seis segundos de processo do Claude."""

    def test_frases_do_dia_a_dia_tem_resposta_pronta(self):
        for frase in (
            "oi",
            "olá",
            "bom dia",
            "boa noite",
            "tudo bem?",
            "como você está?",
            "obrigado",
            "valeu",
            "você está aí?",
            "tá me ouvindo?",
            "boa menina",
            "tchau",
        ):
            with self.subTest(frase=frase):
                self.assertTrue(
                    responder_conversa(frase)
                )

    def test_pedido_com_saudacao_na_frente_continua_indo_ao_claude(self):
        for frase in (
            "oi, abre o navegador",
            "bom dia, me escreve um script",
            "obrigado, agora fecha o chrome",
            "me explica recursão",
        ):
            with self.subTest(frase=frase):
                self.assertIsNone(
                    responder_conversa(frase)
                )

    def test_a_resposta_usa_o_nome_de_quem_esta_falando(self):
        achou = False

        # As frases são sorteadas; algumas trazem o nome.
        for _ in range(60):
            if "Thales" in (responder_conversa("oi", "Thales") or ""):
                achou = True
                break

        self.assertTrue(achou)

    def test_sem_nome_a_frase_nao_fica_com_buraco(self):
        for _ in range(60):
            resposta = responder_conversa("oi") or ""

            self.assertNotIn("{nome}", resposta)
            self.assertNotIn(" !", resposta)
            self.assertNotIn(" ,", resposta)

    def test_a_decisao_e_local(self):
        decisao = rota_conversa("oi", "Thales")

        self.assertIsNotNone(decisao)
        self.assertTrue(decisao.local)

        resultado = decisao.executar()

        self.assertTrue(resultado.texto)

    def test_atender_ao_nome_sempre_devolve_frase(self):
        for pessoa in (None, "", "Thales", "Ana"):
            with self.subTest(pessoa=pessoa):
                frase = atender_ao_nome(pessoa)

                self.assertTrue(frase.strip())
                self.assertNotIn("{nome}", frase)


# ============================================================
# O ROTEADOR CONTINUA CONSERVADOR
# ============================================================

class TestRoteadorComConversa(unittest.TestCase):

    def test_conversa_curta_nao_atrapalha_as_outras_rotas(self):
        from milk.intelligence.roteador import rotear

        decisao = rotear("que horas são")

        self.assertIsNotNone(decisao)
        self.assertNotEqual(decisao.ferramenta, "conversa")

    def test_oi_agora_tem_rota(self):
        from milk.intelligence.roteador import rotear

        decisao = rotear("oi")

        self.assertIsNotNone(decisao)
        self.assertEqual(decisao.ferramenta, "conversa")

    def test_trabalho_continua_indo_para_o_claude(self):
        from milk.intelligence.roteador import rotear

        self.assertIsNone(
            rotear("me escreve um script que renomeia arquivos")
        )


# ============================================================
# ELA AVISA QUE VAI DEMORAR
# ============================================================

class TestAvisoDeEspera(unittest.TestCase):
    """Catorze segundos calados parecem um travamento."""

    def montar(self):
        from test_chat_di import montar_chat

        return montar_chat(
            roteador=lambda texto, pessoa=None: None,
            montador_prompt=lambda t, h, p: "prompt",
        )

    def test_pedido_falado_ganha_um_ja_vou_ver(self):
        chat = self.montar()

        chat.origem_do_pedido = "voz"

        chat.processar("me conta uma curiosidade sobre cachorros")

        self.assertTrue(
            chat.milk.falar.called,
            "quem pediu por voz não vê a barra de progresso"
        )

    def test_pedido_digitado_nao_e_interrompido(self):
        chat = self.montar()

        chat.origem_do_pedido = "texto"

        chat.processar("me conta uma curiosidade sobre cachorros")

        self.assertFalse(
            chat.milk.falar.called,
            "quem digitou está vendo o progresso na tela"
        )


# ============================================================
# O BOTÃO DE FALAR TAMBÉM TIRA O VOCATIVO
# ============================================================

class TestNomeNoBotaoDeFalar(unittest.TestCase):
    """Quem aperta 🎤 Falar costuma dizer o nome dela do mesmo jeito.

    A escuta contínua já tirava o "Milk" de qualquer lugar da frase; o
    botão só tirava do começo, e o vocativo do fim descia inteiro para o
    roteador ("que horas são, Milk")."""

    def montar(self):
        from test_chat_di import montar_chat

        return montar_chat(
            roteador=lambda texto, pessoa=None: None,
            montador_prompt=lambda t, h, p: "prompt",
        )

    def pedido(self, falado):
        chat = self.montar()

        chat.processar = lambda texto: recebidos.append(texto)

        recebidos = []

        chat.receber_voz(falado)

        return recebidos[0] if recebidos else None

    def test_nome_no_fim_e_tirado(self):
        self.assertEqual(
            self.pedido("que horas são, Milk"),
            "que horas são"
        )

    def test_nome_no_comeco_continua_sendo_tirado(self):
        self.assertEqual(
            self.pedido("Milk, que horas são"),
            "que horas são"
        )

    def test_nome_no_meio_e_tirado(self):
        self.assertEqual(
            self.pedido("fecha o navegador, Milk, por favor"),
            "fecha o navegador, por favor"
        )

    def test_frase_sem_o_nome_chega_inteira(self):
        self.assertEqual(
            self.pedido("que horas são"),
            "que horas são"
        )

    def test_so_o_nome_nao_vira_pedido(self):
        chat = self.montar()

        chat.processar = lambda texto: self.fail(
            "chamar só pelo nome não é pedido"
        )

        chat.receber_voz("Milk")

        self.assertTrue(chat.milk.falar.called)


if __name__ == "__main__":
    unittest.main()
