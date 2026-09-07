# Milk — assistente pessoal.
# Copyright (c) 2026 Thales Teracin. Todos os direitos reservados.
#
# Software proprietário. É proibida a cópia, a distribuição, a
# modificação e a engenharia reversa, no todo ou em parte, sem
# autorização expressa e por escrito do autor. Ver LICENSE.txt.

"""Fila de tarefas, barramento de eventos e o que a Milk responde sobre eles.

Nada aqui toca o disco de verdade nem sobe thread: a persistência é
trocada por funções de mentira e o Claude por um dublê.

Rodar:  .venv\\Scripts\\python.exe -m unittest discover -s tests -v
"""

import os
import sys
import json
import tempfile
import unittest

from unittest.mock import Mock, patch

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

from milk.core import eventos
from milk.core.eventos import Barramento
from milk.tasks import persistencia
from milk.tasks.gerente import (
    GerenteDeTarefas,
    definir_gerente,
    prioridade_do_texto,
)
from milk.tasks.modelos import Prioridade, Status, Tarefa, resumir
from milk.memory.memoria import Memoria
from milk.avatar.chat import ChatBubble
from milk.intelligence import rotas_tarefas
from milk.intelligence.roteador import rotear


app = QApplication.instance() or QApplication([])


def fila_de_mentira(inicial=None, barramento=None):
    """Gerente que guarda tudo na memória, sem escrever em disco.

    O barramento é próprio por padrão, para um teste não escutar o
    outro. Quem precisa do barramento de verdade (a conversa, que
    assina o cancelamento nele) passa o global."""

    guardado = {"tarefas": list(inicial or [])}

    def ler():
        return guardado["tarefas"]

    def gravar(tarefas):
        guardado["tarefas"] = list(tarefas)

        return True

    gerente = GerenteDeTarefas(
        barramento=barramento or Barramento(),
        ler=ler,
        gravar=gravar,
    )

    gerente.guardado = guardado

    return gerente


# ============================================================
# BARRAMENTO
# ============================================================

class TestBarramento(unittest.TestCase):

    def test_quem_assina_recebe(self):
        barramento = Barramento()

        recebidos = []

        barramento.assinar(
            "TESTE",
            lambda evento, dados: recebidos.append((evento, dados))
        )

        barramento.publicar("TESTE", valor=7)

        self.assertEqual(len(recebidos), 1)
        self.assertEqual(recebidos[0][0], "TESTE")
        self.assertEqual(recebidos[0][1]["valor"], 7)

    def test_quem_nao_assinou_nao_recebe(self):
        barramento = Barramento()

        recebidos = []

        barramento.assinar(
            "OUTRO",
            lambda evento, dados: recebidos.append(evento)
        )

        self.assertEqual(barramento.publicar("TESTE"), 0)
        self.assertEqual(recebidos, [])

    def test_assinar_duas_vezes_nao_duplica(self):
        barramento = Barramento()

        contador = []

        def ouvinte(evento, dados):
            contador.append(1)

        barramento.assinar("TESTE", ouvinte)
        barramento.assinar("TESTE", ouvinte)

        barramento.publicar("TESTE")

        self.assertEqual(len(contador), 1)

    def test_desassinar(self):
        barramento = Barramento()

        ouvinte = Mock()

        barramento.assinar("TESTE", ouvinte)

        self.assertTrue(barramento.desassinar("TESTE", ouvinte))
        self.assertFalse(barramento.desassinar("TESTE", ouvinte))

        barramento.publicar("TESTE")

        ouvinte.assert_not_called()

    def test_ouvinte_quebrado_nao_derruba_os_outros(self):
        barramento = Barramento()

        chamados = []

        def quebrado(evento, dados):
            raise RuntimeError("estourei")

        barramento.assinar("TESTE", quebrado)

        barramento.assinar(
            "TESTE",
            lambda evento, dados: chamados.append(evento)
        )

        # A publicação não levanta nada.
        barramento.publicar("TESTE")

        self.assertEqual(chamados, ["TESTE"])


# ============================================================
# MODELOS
# ============================================================

class TestTarefa(unittest.TestCase):

    def test_nasce_na_fila_com_id_e_data(self):
        tarefa = Tarefa("uma coisa", "faça uma coisa")

        self.assertEqual(tarefa.status, Status.NA_FILA)
        self.assertEqual(tarefa.prioridade, Prioridade.NORMAL)
        self.assertTrue(tarefa.identificador)
        self.assertTrue(tarefa.criada_em)
        self.assertIsNone(tarefa.iniciada_em)

    def test_ida_e_volta_pelo_dicionario(self):
        tarefa = Tarefa(
            "landing page",
            "crie uma landing page",
            prioridade=Prioridade.ALTA,
            origem="voz",
        )

        copia = Tarefa.de_dicionario(
            tarefa.para_dicionario()
        )

        self.assertEqual(copia.identificador, tarefa.identificador)
        self.assertEqual(copia.prompt, tarefa.prompt)
        self.assertEqual(copia.prioridade, Prioridade.ALTA)
        self.assertEqual(copia.origem, "voz")

    def test_dicionario_torto_vira_padrao(self):
        tarefa = Tarefa.de_dicionario({
            "prompt": "algo",
            "status": "INVENTADO",
            "prioridade": "URGENTISSIMA",
        })

        self.assertEqual(tarefa.status, Status.NA_FILA)
        self.assertEqual(tarefa.prioridade, Prioridade.NORMAL)

    def test_lixo_nao_vira_tarefa(self):
        self.assertIsNone(Tarefa.de_dicionario("não sou dicionário"))
        self.assertIsNone(Tarefa.de_dicionario({}))

    def test_resumir_corta_o_pedido_longo(self):
        curto = resumir("crie uma landing page")

        self.assertEqual(curto, "crie uma landing page")

        longo = resumir("palavra " * 40)

        self.assertLessEqual(len(longo), 60)
        self.assertTrue(longo.endswith("…"))


# ============================================================
# PERSISTÊNCIA
# ============================================================

class TestPersistencia(unittest.TestCase):

    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory()

        self.arquivo = os.path.join(
            self.pasta.name,
            "milk_tarefas.json"
        )

        self.remendo = patch.object(
            persistencia,
            "TASKS_FILE",
            self.arquivo
        )

        self.remendo.start()

    def tearDown(self):
        self.remendo.stop()
        self.pasta.cleanup()

    def test_grava_e_le(self):
        tarefa = Tarefa("uma coisa", "faça uma coisa")

        self.assertTrue(persistencia.gravar([tarefa]))

        lidas = persistencia.ler()

        self.assertEqual(len(lidas), 1)
        self.assertEqual(lidas[0].identificador, tarefa.identificador)

    def test_arquivo_ausente_devolve_lista_vazia(self):
        self.assertEqual(persistencia.ler(), [])

    def test_arquivo_corrompido_devolve_lista_vazia(self):
        with open(self.arquivo, "w", encoding="utf-8") as arquivo:
            arquivo.write("{isso não é json")

        self.assertEqual(persistencia.ler(), [])

    def test_nao_deixa_arquivo_temporario_para_tras(self):
        persistencia.gravar([Tarefa("x", "x")])

        sobras = [
            nome
            for nome in os.listdir(self.pasta.name)
            if nome.endswith(".tmp")
        ]

        self.assertEqual(sobras, [])

    def test_o_json_e_legivel_por_gente(self):
        persistencia.gravar([Tarefa("olhe isto", "olhe isto")])

        with open(self.arquivo, "r", encoding="utf-8") as arquivo:
            dados = json.load(arquivo)

        self.assertIn("tarefas", dados)
        self.assertEqual(dados["tarefas"][0]["descricao"], "olhe isto")

    def test_historico_nao_cresce_para_sempre(self):
        tarefas = []

        for numero in range(persistencia.LIMITE_DE_HISTORICO + 20):
            tarefa = Tarefa(f"t{numero}", f"t{numero}")
            tarefa.status = Status.CONCLUIDA

            tarefas.append(tarefa)

        viva = Tarefa("ainda na fila", "ainda na fila")

        podadas = persistencia.podar(tarefas + [viva])

        self.assertEqual(
            len(podadas),
            persistencia.LIMITE_DE_HISTORICO + 1
        )

        self.assertIn(viva, podadas)

        # As que ficaram são as mais recentes.
        self.assertIn(tarefas[-1], podadas)
        self.assertNotIn(tarefas[0], podadas)

    def test_rodando_no_disco_vira_interrompida(self):
        tarefa = Tarefa("x", "x")
        tarefa.status = Status.RODANDO

        persistencia.marcar_interrompidas([tarefa])

        self.assertEqual(tarefa.status, Status.INTERROMPIDA)
        self.assertTrue(tarefa.erro)


# ============================================================
# GERENTE
# ============================================================

class TestGerente(unittest.TestCase):

    def setUp(self):
        self.gerente = fila_de_mentira()

    def test_criar_poe_na_fila_e_grava(self):
        tarefa = self.gerente.criar("crie uma landing page")

        self.assertEqual(tarefa.status, Status.NA_FILA)
        self.assertEqual(self.gerente.pendentes(), [tarefa])
        self.assertEqual(len(self.gerente.guardado["tarefas"]), 1)

    def test_ordem_e_de_chegada(self):
        primeira = self.gerente.criar("primeira")
        segunda = self.gerente.criar("segunda")

        self.assertEqual(
            self.gerente.pendentes(),
            [primeira, segunda]
        )

    def test_urgente_passa_na_frente(self):
        primeira = self.gerente.criar("primeira")
        urgente = self.gerente.criar("isso é urgente, veja o log")

        self.assertEqual(urgente.prioridade, Prioridade.URGENTE)

        self.assertEqual(
            self.gerente.pendentes(),
            [urgente, primeira]
        )

    def test_sem_pressa_vai_para_o_fim(self):
        devagar = self.gerente.criar("quando puder, organize a pasta")
        normal = self.gerente.criar("veja o log")

        self.assertEqual(devagar.prioridade, Prioridade.BAIXA)

        self.assertEqual(
            self.gerente.pendentes(),
            [normal, devagar]
        )

    def test_prioridade_do_texto(self):
        self.assertEqual(
            prioridade_do_texto("isso é urgente"),
            Prioridade.URGENTE
        )

        self.assertEqual(
            prioridade_do_texto("quando puder, faça isso"),
            Prioridade.BAIXA
        )

        self.assertEqual(
            prioridade_do_texto("veja o log"),
            Prioridade.NORMAL
        )

    def test_uma_de_cada_vez(self):
        primeira = self.gerente.criar("primeira")
        self.gerente.criar("segunda")

        self.gerente.iniciar(primeira)

        self.assertTrue(self.gerente.ocupada())
        self.assertIsNone(self.gerente.proxima())

        self.gerente.concluir(primeira, "pronto")

        self.assertEqual(
            self.gerente.proxima().descricao,
            "segunda"
        )

    def test_fila_pausada_nao_entrega_ninguem(self):
        self.gerente.criar("primeira")

        self.gerente.pausar()

        self.assertIsNone(self.gerente.proxima())

        self.gerente.continuar()

        self.assertIsNotNone(self.gerente.proxima())

    def test_concluir_guarda_resultado_e_hora(self):
        tarefa = self.gerente.criar("uma coisa")

        self.gerente.iniciar(tarefa)
        self.gerente.concluir(tarefa, "ficou pronto")

        self.assertEqual(tarefa.status, Status.CONCLUIDA)
        self.assertEqual(tarefa.resultado, "ficou pronto")
        self.assertTrue(tarefa.iniciada_em)
        self.assertTrue(tarefa.terminada_em)

    def test_falhar_guarda_o_erro(self):
        tarefa = self.gerente.criar("uma coisa")

        self.gerente.iniciar(tarefa)
        self.gerente.falhar(tarefa, "deu ruim")

        self.assertEqual(tarefa.status, Status.FALHOU)
        self.assertEqual(tarefa.erro, "deu ruim")

    def test_tarefa_que_ja_terminou_nao_muda_mais(self):
        tarefa = self.gerente.criar("uma coisa")

        self.gerente.cancelar(tarefa)

        self.assertIsNone(self.gerente.concluir(tarefa, "tarde demais"))
        self.assertEqual(tarefa.status, Status.CANCELADA)

    def test_cancelar_proxima_e_tudo(self):
        primeira = self.gerente.criar("primeira")
        self.gerente.criar("segunda")
        self.gerente.criar("terceira")

        self.assertEqual(
            self.gerente.cancelar_proxima(),
            primeira
        )

        self.assertEqual(len(self.gerente.pendentes()), 2)

        self.gerente.cancelar_pendentes()

        self.assertEqual(self.gerente.pendentes(), [])

    def test_priorizar_e_adiar(self):
        primeira = self.gerente.criar("primeira")
        segunda = self.gerente.criar("segunda")

        self.gerente.priorizar(segunda)

        self.assertEqual(self.gerente.pendentes()[0], segunda)

        self.gerente.adiar(segunda)

        self.assertEqual(self.gerente.pendentes()[0], primeira)

    def test_limpar_concluidas_nao_toca_na_fila(self):
        pronta = self.gerente.criar("pronta")
        esperando = self.gerente.criar("esperando")

        self.gerente.iniciar(pronta)
        self.gerente.concluir(pronta, "ok")

        self.assertEqual(self.gerente.limpar_concluidas(), 1)

        self.assertEqual(self.gerente.tarefas, [esperando])

    def test_repetir_ultima_cria_outra_com_o_mesmo_pedido(self):
        tarefa = self.gerente.criar("analise o projeto")

        self.gerente.iniciar(tarefa)
        self.gerente.concluir(tarefa, "analisado")

        nova = self.gerente.repetir_ultima()

        self.assertIsNotNone(nova)
        self.assertEqual(nova.prompt, tarefa.prompt)
        self.assertNotEqual(nova.identificador, tarefa.identificador)
        self.assertEqual(nova.status, Status.NA_FILA)

    def test_repetir_sem_historico(self):
        self.assertIsNone(self.gerente.repetir_ultima())

    def test_interromper_ao_fechar(self):
        tarefa = self.gerente.criar("uma coisa")

        self.gerente.iniciar(tarefa)
        self.gerente.interromper_em_andamento()

        self.assertEqual(tarefa.status, Status.INTERROMPIDA)

    def test_tarefa_rodando_no_disco_volta_interrompida(self):
        antiga = Tarefa("de ontem", "de ontem")
        antiga.status = Status.RODANDO

        gerente = fila_de_mentira([antiga])

        self.assertEqual(
            gerente.tarefas[0].status,
            Status.INTERROMPIDA
        )

    def test_eventos_publicados(self):
        vistos = []

        for evento in (
            eventos.TAREFA_CRIADA,
            eventos.TAREFA_INICIADA,
            eventos.TAREFA_PROGRESSO,
            eventos.TAREFA_CONCLUIDA,
        ):
            self.gerente._barramento.assinar(
                evento,
                lambda nome, dados: vistos.append(nome)
            )

        tarefa = self.gerente.criar("uma coisa")

        self.gerente.iniciar(tarefa)
        self.gerente.anotar_progresso(tarefa, "lendo arquivos")
        self.gerente.concluir(tarefa, "pronto")

        self.assertEqual(
            vistos,
            [
                eventos.TAREFA_CRIADA,
                eventos.TAREFA_INICIADA,
                eventos.TAREFA_PROGRESSO,
                eventos.TAREFA_CONCLUIDA,
            ]
        )

    def test_disco_quebrado_nao_derruba_a_fila(self):
        def gravar_quebrado(tarefas):
            raise OSError("disco cheio")

        gerente = GerenteDeTarefas(
            barramento=Barramento(),
            ler=lambda: [],
            gravar=gravar_quebrado,
        )

        tarefa = gerente.criar("uma coisa")

        self.assertEqual(gerente.pendentes(), [tarefa])


# ============================================================
# O QUE ELA RESPONDE SOBRE A FILA
# ============================================================

class TestFrasesDaFila(unittest.TestCase):

    def setUp(self):
        self.gerente = fila_de_mentira()

    def test_sem_nada_para_fazer(self):
        frase = rotas_tarefas.frase_do_trabalho(self.gerente).texto

        self.assertIn("Nada no momento", frase)

    def test_conta_o_que_esta_fazendo_e_quantas_faltam(self):
        atual = self.gerente.criar("analisar o projeto")

        self.gerente.criar("outra coisa")
        self.gerente.iniciar(atual)
        self.gerente.anotar_progresso(atual, "lendo arquivos")

        frase = rotas_tarefas.frase_do_trabalho(self.gerente).texto

        self.assertIn("analisar o projeto", frase)
        self.assertIn("lendo arquivos", frase)
        self.assertIn("mais 1 tarefa", frase)

    def test_lista_as_pendentes_com_a_prioridade(self):
        self.gerente.criar("primeira")
        self.gerente.criar("isso é urgente, olhe o log")

        frase = rotas_tarefas.frase_das_pendentes(self.gerente).texto

        self.assertIn("1.", frase)
        self.assertIn("urgente", frase)

    def test_progresso_sem_novidade(self):
        atual = self.gerente.criar("uma coisa")

        self.gerente.iniciar(atual)

        frase = rotas_tarefas.frase_do_progresso(self.gerente).texto

        self.assertIn("Sem novidade", frase)

    def test_pausar_e_continuar(self):
        self.gerente.criar("uma coisa")

        self.assertIn(
            "pausada",
            rotas_tarefas.pausar(self.gerente).texto.lower()
        )

        self.assertTrue(self.gerente.pausada)

        self.assertIn(
            "uma coisa",
            rotas_tarefas.continuar(self.gerente).texto
        )

        self.assertFalse(self.gerente.pausada)

    def test_cancelar_sem_nada_rodando(self):
        self.assertIn(
            "Não estou fazendo nada",
            rotas_tarefas.cancelar_atual(self.gerente).texto
        )

    def test_limpar_concluidas_conta_certo(self):
        tarefa = self.gerente.criar("uma coisa")

        self.gerente.iniciar(tarefa)
        self.gerente.concluir(tarefa, "ok")

        self.assertIn(
            "1 tarefa concluída",
            rotas_tarefas.limpar_concluidas(self.gerente).texto
        )


class TestRotaDeTarefas(unittest.TestCase):
    """O roteador precisa reconhecer o comando de fila."""

    def rota(self, frase):
        decisao = rotear(frase)

        return decisao.ferramenta if decisao else None

    def test_comandos_da_fila(self):
        for frase in (
            "o que você está fazendo?",
            "quais tarefas estão pendentes",
            "como está a fila",
            "qual o progresso?",
            "pause",
            "continue",
            "cancele essa tarefa",
            "cancele a próxima",
            "cancele tudo",
            "coloque isso como prioridade",
            "faça isso depois",
            "repita a última tarefa",
            "limpe as tarefas concluídas",
        ):
            with self.subTest(frase=frase):
                self.assertEqual(self.rota(frase), "tarefas")

    def test_pedido_de_trabalho_nao_e_comando_de_fila(self):
        for frase in (
            "crie uma landing page",
            "analise meu projeto python",
            "me conta uma piada",
            "que horas são?",
            "o que é fotossíntese",
        ):
            with self.subTest(frase=frase):
                self.assertNotEqual(self.rota(frase), "tarefas")

    def test_comando_de_fila_e_local(self):
        decisao = rotear("quais tarefas estão pendentes")

        self.assertTrue(decisao.local)
        self.assertFalse(decisao.silenciosa)


# ============================================================
# A CONVERSA USANDO A FILA
# ============================================================

class WorkerFalso:
    """Imita o pedaço do QThread que o ChatBubble usa."""

    def __init__(self, *args, **kwargs):
        self.args = args
        self.iniciado = False
        self.rodando = False
        self.cancelado = False

        self.progresso = Mock()
        self.sucesso = Mock()
        self.erro = Mock()
        self.status = Mock()
        self.texto_pronto = Mock()

    def start(self):
        self.iniciado = True
        self.rodando = True

    def isRunning(self):
        return self.rodando

    def cancelar(self):
        self.cancelado = True


class TestConversaComFila(unittest.TestCase):

    def setUp(self):
        # Barramento de verdade: e por ele que o cancelamento chega da
        # fila ate a conversa, que entao mata o processo do Claude.
        self.gerente = fila_de_mentira(
            barramento=eventos.barramento
        )

        # Os comandos de fila ("cancele essa tarefa") olham o gerente do
        # processo, que é o mesmo que a conversa usa quando roda de
        # verdade. Aqui os dois passam a ser esta fila de mentira.
        definir_gerente(self.gerente)

        self.chat = ChatBubble(
            Mock(),
            criar_claude_worker=WorkerFalso,
            criar_microfone_worker=WorkerFalso,
            criar_ferramenta_worker=WorkerFalso,
            roteador=rotear,
            montador_prompt=lambda texto, historico, pessoa: texto,
            ler_pessoa=lambda: "Thales",
            gravar_pessoa=Mock(),
            gerente_de_tarefas=self.gerente,
            # Memória só na cabeça: teste não escreve em disco.
            memoria_da_milk=Memoria(
                ler=lambda caminho, padrao=None: padrao,
                gravar=lambda caminho, conteudo: True,
            ),
        )

    def tearDown(self):
        eventos.barramento.desassinar(
            eventos.TAREFA_CANCELADA,
            self.chat.quando_cancelam
        )

        definir_gerente(None)

        self.chat.deleteLater()

    def test_o_primeiro_pedido_comeca_na_hora(self):
        self.chat.processar("analise meu projeto python")

        tarefa = self.gerente.em_andamento()

        self.assertIsNotNone(tarefa)
        self.assertEqual(tarefa.status, Status.RODANDO)
        self.assertTrue(self.chat.claude_worker.iniciado)

    def test_o_segundo_pedido_entra_na_fila(self):
        self.chat.processar("analise meu projeto python")

        primeiro = self.chat.claude_worker

        self.chat.processar("crie uma landing page")

        # Nenhum worker novo: o segundo pedido só foi anotado.
        self.assertIs(self.chat.claude_worker, primeiro)

        self.assertEqual(len(self.gerente.pendentes()), 1)

        self.assertIn(
            "Anotei",
            self.chat.chat.toPlainText()
        )

    def test_ao_terminar_a_proxima_comeca_sozinha(self):
        self.chat.processar("analise meu projeto python")
        self.chat.processar("crie uma landing page")

        primeiro = self.chat.claude_worker

        primeiro.rodando = False

        self.chat.tarefa_concluida("terminei a análise")

        atual = self.gerente.em_andamento()

        self.assertIsNotNone(atual)
        self.assertEqual(atual.descricao, "crie uma landing page")

        self.assertIsNot(self.chat.claude_worker, primeiro)
        self.assertTrue(self.chat.claude_worker.iniciado)

    def test_pergunta_rapida_no_meio_do_trabalho(self):
        self.chat.processar("analise meu projeto python")

        worker = self.chat.claude_worker

        self.chat.processar("que horas são?")

        # O trabalho continua o mesmo, e a hora foi respondida.
        self.assertIs(self.chat.claude_worker, worker)
        self.assertEqual(len(self.gerente.pendentes()), 0)

        self.assertIn(
            "Agora ",
            self.chat.chat.toPlainText()
        )

    def test_ela_conta_o_que_esta_fazendo_durante_o_trabalho(self):
        self.chat.processar("analise meu projeto python")

        self.chat.progresso_da_tarefa("📖 Lendo config.py")

        self.chat.processar("o que você está fazendo?")

        conversa = self.chat.chat.toPlainText()

        self.assertIn("Estou trabalhando em", conversa)
        self.assertIn("Lendo config.py", conversa)

    def test_cancelar_mata_o_processo_do_claude(self):
        self.chat.processar("analise meu projeto python")

        worker = self.chat.claude_worker

        self.chat.processar("cancele essa tarefa")

        self.assertTrue(worker.cancelado)

        self.assertEqual(
            self.gerente.tarefas[0].status,
            Status.CANCELADA
        )

    def test_erro_depois_do_cancelamento_nao_vira_aviso_de_erro(self):
        self.chat.processar("analise meu projeto python")

        self.chat.processar("cancele essa tarefa")

        self.chat.claude_worker.rodando = False

        self.chat.tarefa_falhou("Não recebi resposta nenhuma.")

        conversa = self.chat.chat.toPlainText()

        self.assertNotIn("⚠ Erro", conversa)
        self.assertIn("cancelada", self.chat.status.text().lower())

    def test_falha_de_verdade_marca_a_tarefa(self):
        self.chat.processar("analise meu projeto python")

        tarefa = self.gerente.em_andamento()

        self.chat.claude_worker.rodando = False

        self.chat.tarefa_falhou("o Claude não respondeu")

        self.assertEqual(tarefa.status, Status.FALHOU)
        self.assertEqual(tarefa.erro, "o Claude não respondeu")

    def test_fila_pausada_segura_o_pedido(self):
        self.gerente.pausar()

        self.chat.processar("analise meu projeto python")

        self.assertIsNone(self.gerente.em_andamento())
        self.assertEqual(len(self.gerente.pendentes()), 1)
        self.assertIsNone(self.chat.claude_worker)

    def test_o_progresso_fica_guardado_na_tarefa(self):
        self.chat.processar("analise meu projeto python")

        self.chat.progresso_da_tarefa("⚙️ Rodando os testes")

        self.assertEqual(
            self.gerente.em_andamento().progresso,
            "⚙️ Rodando os testes"
        )

    def test_avisa_quando_termina_tudo(self):
        self.chat.processar("analise meu projeto python")
        self.chat.processar("crie uma landing page")

        # Primeira termina: ela começa a próxima e avisa.
        self.chat.claude_worker.rodando = False
        self.chat.tarefa_concluida("análise pronta")

        self.assertIn(
            "Vou começar a próxima",
            self.chat.chat.toPlainText()
        )

        # Segunda termina: acabou a fila.
        self.chat.claude_worker.rodando = False
        self.chat.tarefa_concluida("landing pronta")

        self.assertIn(
            "Terminei tudo",
            self.chat.status.text()
        )

    def test_sem_fila_nao_anuncia_fim(self):
        self.chat.processar("analise meu projeto python")

        self.chat.claude_worker.rodando = False
        self.chat.tarefa_concluida("pronto")

        self.assertNotIn(
            "Terminei tudo",
            self.chat.status.text()
        )

    def test_a_origem_do_pedido_fica_registrada(self):
        self.chat.origem_do_pedido = "voz"

        self.chat.processar("analise meu projeto python")

        self.assertEqual(
            self.gerente.em_andamento().origem,
            "voz"
        )


if __name__ == "__main__":
    unittest.main()
