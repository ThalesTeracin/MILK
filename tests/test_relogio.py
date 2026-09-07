# Milk — assistente pessoal.
# Copyright (c) 2026 Thales Teracin. Todos os direitos reservados.
#
# Software proprietário. É proibida a cópia, a distribuição, a
# modificação e a engenharia reversa, no todo ou em parte, sem
# autorização expressa e por escrito do autor. Ver LICENSE.txt.

"""Horário e calendário: a ferramenta local e a rota que leva até ela.

A data nunca vem do relógio da máquina nestes testes — entra fixa, senão
o resultado mudaria de um dia para o outro. 5 de setembro de 2026 é um
sábado.

Rodar:  .venv\\Scripts\\python.exe -m unittest discover -s tests -v
"""

import os
import sys
import datetime
import unittest

from unittest.mock import Mock

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

from milk.tools import relogio
from milk.avatar.chat import ChatBubble
from milk.core.eventos import Barramento
from milk.tasks.gerente import GerenteDeTarefas
from milk.memory.memoria import Memoria
from milk.intelligence.roteador import rotear


app = QApplication.instance() or QApplication([])


SABADO = datetime.datetime(2026, 9, 5, 14, 32)


class TestHoras(unittest.TestCase):

    def hora(self, h, m):
        return relogio.que_horas(
            datetime.datetime(2026, 9, 5, h, m)
        ).texto

    def test_hora_comum(self):
        self.assertEqual(
            self.hora(14, 32),
            "Agora são 14 horas e 32 minutos."
        )

    def test_hora_em_ponto(self):
        self.assertEqual(
            self.hora(9, 0),
            "Agora são 9 horas em ponto."
        )

    def test_uma_hora_no_singular(self):
        self.assertEqual(
            self.hora(1, 0),
            "Agora é 1 hora em ponto."
        )

    def test_um_minuto_no_singular(self):
        self.assertIn(
            "e 1 minuto.",
            self.hora(8, 1)
        )

    def test_meio_dia_tem_nome(self):
        self.assertEqual(
            self.hora(12, 0),
            "Agora é meio-dia em ponto."
        )

    def test_meia_noite_tem_nome(self):
        self.assertEqual(
            self.hora(0, 30),
            "Agora é meia-noite e 30 minutos."
        )

    def test_dados_trazem_hora_e_minuto(self):
        resposta = relogio.que_horas(SABADO)

        self.assertTrue(resposta.ok)
        self.assertEqual(resposta.dados["hora"], 14)
        self.assertEqual(resposta.dados["minuto"], 32)


class TestData(unittest.TestCase):

    def test_dia_de_hoje_completo(self):
        self.assertEqual(
            relogio.que_dia_e_hoje(SABADO).texto,
            "Hoje é sábado, 5 de setembro de 2026."
        )

    def test_dia_da_semana_sozinho(self):
        self.assertEqual(
            relogio.dia_da_semana(SABADO).texto,
            "Hoje é sábado."
        )

    def test_amanha(self):
        self.assertEqual(
            relogio.dia_vizinho(1, SABADO).texto,
            "Amanhã é domingo, 6 de setembro."
        )

    def test_ontem(self):
        self.assertEqual(
            relogio.dia_vizinho(-1, SABADO).texto,
            "Ontem foi sexta-feira, 4 de setembro."
        )

    def test_virada_de_ano(self):
        fim = datetime.datetime(2026, 12, 31, 23, 0)

        self.assertEqual(
            relogio.dia_vizinho(1, fim).texto,
            "Amanhã é sexta-feira, 1 de janeiro."
        )

    def test_mes_e_ano(self):
        self.assertEqual(
            relogio.mes_atual(SABADO).texto,
            "Estamos em setembro de 2026."
        )

        self.assertEqual(
            relogio.ano_atual(SABADO).texto,
            "Estamos em 2026."
        )


class TestEntenderData(unittest.TestCase):

    def entender(self, texto):
        return relogio.entender_data(texto, SABADO)

    def test_data_numerica(self):
        self.assertEqual(
            self.entender("25/12"),
            datetime.date(2026, 12, 25)
        )

    def test_data_numerica_com_ano(self):
        self.assertEqual(
            self.entender("31/12/2027"),
            datetime.date(2027, 12, 31)
        )

    def test_data_por_extenso(self):
        self.assertEqual(
            self.entender("dia 10 de outubro"),
            datetime.date(2026, 10, 10)
        )

    def test_natal_e_ano_novo(self):
        self.assertEqual(
            self.entender("o natal"),
            datetime.date(2026, 12, 25)
        )

        self.assertEqual(
            self.entender("ano novo"),
            datetime.date(2027, 1, 1)
        )

    def test_data_ja_passada_cai_no_ano_seguinte(self):
        self.assertEqual(
            self.entender("1 de janeiro"),
            datetime.date(2027, 1, 1)
        )

    def test_ano_dito_manda_mesmo_no_passado(self):
        self.assertEqual(
            self.entender("4 de setembro de 2026"),
            datetime.date(2026, 9, 4)
        )

    def test_data_impossivel(self):
        self.assertIsNone(
            self.entender("30 de fevereiro")
        )

    def test_texto_que_nao_e_data(self):
        self.assertIsNone(
            self.entender("eu terminar o trabalho")
        )

    def test_vazio(self):
        self.assertIsNone(
            self.entender("")
        )


class TestDiasPara(unittest.TestCase):

    def contar(self, texto):
        return relogio.dias_para(
            relogio.entender_data(texto, SABADO),
            SABADO
        )

    def test_faltam_dias(self):
        self.assertEqual(
            self.contar("o natal").texto,
            "Faltam 111 dias para 25 de dezembro de 2026."
        )

    def test_falta_um_dia_no_singular(self):
        self.assertEqual(
            self.contar("6 de setembro").texto,
            "Falta 1 dia para 6 de setembro de 2026."
        )

    def test_hoje(self):
        self.assertIn(
            "É hoje mesmo",
            self.contar("5 de setembro").texto
        )

    def test_data_passada(self):
        self.assertIn(
            "foi ontem",
            self.contar("4 de setembro de 2026").texto
        )

    def test_sem_data_devolve_falha_amigavel(self):
        resposta = relogio.dias_para(None, SABADO)

        self.assertFalse(resposta.ok)
        self.assertNotIn("None", resposta.texto)


class TestRotaRelogio(unittest.TestCase):
    """O roteador só precisa escolher certo. A conta já foi testada."""

    def rota(self, frase):
        decisao = rotear(frase)

        return decisao.ferramenta if decisao else None

    def test_perguntas_de_hora(self):
        for frase in (
            "que horas são?",
            "Milk, que horas são",
            "que horas são agora?",
            "me diz as horas",
            "qual é a hora certa",
            "que hora é?",
            "qual a hora",
        ):
            with self.subTest(frase=frase):
                self.assertEqual(
                    self.rota(frase),
                    "relogio"
                )

    def test_perguntas_de_data(self):
        for frase in (
            "que dia é hoje?",
            "qual a data de hoje",
            "em que dia estamos",
            "que dia da semana é hoje?",
            "que dia é amanhã",
            "que dia foi ontem?",
            "em que mês estamos",
            "em que ano estamos",
            "quantos dias faltam para o natal",
            "quantos dias faltam pro dia 25 de dezembro",
        ):
            with self.subTest(frase=frase):
                self.assertEqual(
                    self.rota(frase),
                    "relogio"
                )

    def test_conversa_continua_indo_para_o_claude(self):
        for frase in (
            "que horas você acha que eu devia dormir",
            "qual a hora do jogo do Palmeiras",
            "faça um relógio em python",
            "crie um script que mostre a data",
            "quantos dias faltam para eu terminar o projeto",
            "me conta uma história",
            "que dia bom, né?",
        ):
            with self.subTest(frase=frase):
                self.assertNotEqual(
                    self.rota(frase),
                    "relogio"
                )

    def test_hora_nao_atropela_o_clima(self):
        decisao = rotear("qual a temperatura agora?")

        self.assertIsNotNone(decisao)
        self.assertEqual(decisao.ferramenta, "clima")

    def test_decisao_e_local_e_falada(self):
        decisao = rotear("que horas são?")

        self.assertTrue(decisao.local)
        self.assertFalse(decisao.silenciosa)

    def test_executar_devolve_resultado_pronto(self):
        decisao = rotear("que dia é hoje?")

        resposta = decisao.executar()

        self.assertTrue(resposta.ok)
        self.assertIn("Hoje é", resposta.texto)


class WorkerFalso:
    """Imita o pedaço do QThread que o ChatBubble usa."""

    def __init__(self, *args, **kwargs):
        self.args = args
        self.iniciado = False

        self.progresso = Mock()
        self.sucesso = Mock()
        self.erro = Mock()
        self.status = Mock()
        self.texto_pronto = Mock()

    def start(self):
        self.iniciado = True

    def isRunning(self):
        return False


class TestConversaCompleta(unittest.TestCase):
    """A pergunta entra pela conversa e sai falada, sem thread nenhuma."""

    def montar(self):
        return ChatBubble(
            Mock(),
            criar_claude_worker=WorkerFalso,
            criar_microfone_worker=WorkerFalso,
            criar_ferramenta_worker=WorkerFalso,
            roteador=rotear,
            montador_prompt=lambda texto, historico, pessoa: "prompt",
            ler_pessoa=lambda: "Thales",
            gravar_pessoa=Mock(),
            # Fila só na memória: teste não escreve no milk_tarefas.json.
            gerente_de_tarefas=GerenteDeTarefas(
                barramento=Barramento(),
                ler=lambda: [],
                gravar=lambda tarefas: True,
            ),
            # Memória só na cabeça: teste não escreve em disco.
            memoria_da_milk=Memoria(
                ler=lambda caminho, padrao=None: padrao,
                gravar=lambda caminho, conteudo: True,
            ),
        )

    def test_hora_responde_na_hora_e_com_voz(self):
        chat = self.montar()

        chat.processar("que horas são?")

        # Nem Claude nem thread de ferramenta: resolveu aqui mesmo.
        self.assertIsNone(chat.claude_worker)
        self.assertIsNone(chat.ferramenta_worker)

        chat.milk.falar.assert_called_once()

        falado = chat.milk.falar.call_args[0][0]

        self.assertTrue(
            falado.startswith("Agora ")
        )

        self.assertIn(
            falado,
            chat.chat.toPlainText()
        )

    def test_pedido_de_programa_continua_com_o_claude(self):
        chat = self.montar()

        chat.processar("faça um relógio em python")

        self.assertIsInstance(chat.claude_worker, WorkerFalso)
        self.assertTrue(chat.claude_worker.iniciado)


if __name__ == "__main__":
    unittest.main()
