# Milk — assistente pessoal.
# Copyright (c) 2026 Thales Teracin. Todos os direitos reservados.
#
# Software proprietário. É proibida a cópia, a distribuição, a
# modificação e a engenharia reversa, no todo ou em parte, sem
# autorização expressa e por escrito do autor. Ver LICENSE.txt.

"""Fase 1 - injecao de dependencia no ChatBubble.

Estes testes montam a janela de conversa com dubles no lugar do Claude,
do microfone, das ferramentas e do arquivo de pessoa. Nada aqui abre
processo externo, toca em rede ou grava em disco.

Rodar:  .venv\\Scripts\\python.exe -m unittest discover -s tests -v
"""

import inspect
import os
import sys
import unittest
from unittest.mock import Mock

# Sem isso o Qt tenta abrir janela de verdade e o teste trava.
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

from milk.avatar.chat import ChatBubble
from milk.core.eventos import Barramento
from milk.tasks.gerente import GerenteDeTarefas
from milk.memory.memoria import Memoria


app = QApplication.instance() or QApplication([])


class WorkerFalso:
    """Imita a parte do QThread que o ChatBubble usa.

    Guarda os argumentos recebidos e nunca sai da thread principal."""

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
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


def montar_chat(**deps):
    """ChatBubble com todas as dependencias trocadas por duble."""

    padrao = {
        "criar_claude_worker": WorkerFalso,
        "criar_microfone_worker": WorkerFalso,
        "criar_ferramenta_worker": WorkerFalso,
        "roteador": lambda texto, pessoa=None: None,
        "montador_prompt": lambda texto, historico, pessoa: "prompt",
        "ler_pessoa": lambda: "Thales",
        "gravar_pessoa": Mock(),
        "gerente_de_tarefas": GerenteDeTarefas(
            barramento=Barramento(),
            ler=lambda: [],
            gravar=lambda tarefas: True,
        ),
        "memoria_da_milk": Memoria(
            ler=lambda caminho, padrao=None: padrao,
            gravar=lambda caminho, conteudo: True,
        ),
    }

    padrao.update(deps)

    return ChatBubble(Mock(), **padrao)


class TestCompatibilidade(unittest.TestCase):
    """A chamada antiga nao pode ter mudado."""

    def test_milk_e_o_unico_argumento_obrigatorio(self):
        # mascote.py chama exatamente assim: ChatBubble(self).
        assinatura = inspect.signature(ChatBubble.__init__)

        obrigatorios = [
            nome
            for nome, p in assinatura.parameters.items()
            if p.default is inspect.Parameter.empty
            and nome != "self"
            and p.kind is not inspect.Parameter.VAR_KEYWORD
        ]

        self.assertEqual(obrigatorios, ["milk"])

    def test_dependencias_sao_somente_nomeadas(self):
        assinatura = inspect.signature(ChatBubble.__init__)

        for nome in (
            "criar_claude_worker",
            "criar_microfone_worker",
            "criar_ferramenta_worker",
            "roteador",
            "montador_prompt",
            "ler_pessoa",
            "gravar_pessoa",
        ):
            self.assertIn(nome, assinatura.parameters)

            self.assertIs(
                assinatura.parameters[nome].kind,
                inspect.Parameter.KEYWORD_ONLY
            )

    def test_padroes_apontam_para_as_pecas_reais(self):
        from milk.core.pessoa import carregar_pessoa, salvar_pessoa
        from milk.intelligence.claude_bridge import ClaudeWorker
        from milk.intelligence.ferramenta_worker import FerramentaWorker
        from milk.intelligence.prompt import montar_prompt
        from milk.intelligence.roteador import rotear
        from milk.voice.microfone import MicrofoneWorker

        p = inspect.signature(ChatBubble.__init__).parameters

        self.assertIs(p["criar_claude_worker"].default, ClaudeWorker)
        self.assertIs(p["criar_microfone_worker"].default, MicrofoneWorker)
        self.assertIs(p["criar_ferramenta_worker"].default, FerramentaWorker)
        self.assertIs(p["roteador"].default, rotear)
        self.assertIs(p["montador_prompt"].default, montar_prompt)
        self.assertIs(p["ler_pessoa"].default, carregar_pessoa)
        self.assertIs(p["gravar_pessoa"].default, salvar_pessoa)


class TestInjecao(unittest.TestCase):
    """Cada dependencia injetada e mesmo a que roda."""

    def test_pessoa_vem_do_leitor_injetado(self):
        chat = montar_chat(ler_pessoa=lambda: "Ana")

        self.assertEqual(chat.pessoa, "Ana")
        self.assertFalse(chat.aguardando_nome)

    def test_sem_pessoa_conhecida_ela_pergunta(self):
        chat = montar_chat(ler_pessoa=lambda: None)

        self.assertTrue(chat.aguardando_nome)

    def test_registrar_pessoa_usa_o_gravador_injetado(self):
        gravar = Mock()

        chat = montar_chat(
            ler_pessoa=lambda: None,
            gravar_pessoa=gravar
        )

        chat.registrar_pessoa("Rafael")

        gravar.assert_called_once_with("Rafael")

        self.assertEqual(chat.pessoa, "Rafael")
        self.assertFalse(chat.aguardando_nome)

    def test_roteador_injetado_recebe_o_texto(self):
        chamadas = []

        def roteador(texto, pessoa=None):
            chamadas.append(texto)
            return None

        chat = montar_chat(roteador=roteador)

        chat.processar("qualquer coisa")

        self.assertEqual(chamadas, ["qualquer coisa"])

    def test_sem_rota_o_pedido_vai_para_o_claude_injetado(self):
        chat = montar_chat(
            roteador=lambda texto, pessoa=None: None,
            montador_prompt=lambda t, h, p: "PROMPT MONTADO"
        )

        chat.processar("me explica recursao")

        self.assertIsInstance(chat.claude_worker, WorkerFalso)
        self.assertTrue(chat.claude_worker.iniciado)

        self.assertEqual(
            chat.claude_worker.args,
            ("PROMPT MONTADO",)
        )

    def test_com_rota_o_claude_nao_e_chamado(self):
        decisao = Mock()
        decisao.local = False
        decisao.descricao = "consultando"

        chat = montar_chat(roteador=lambda texto, pessoa=None: decisao)

        chat.processar("cep 01310-100")

        self.assertIsNone(chat.claude_worker)

        self.assertIsInstance(chat.ferramenta_worker, WorkerFalso)
        self.assertTrue(chat.ferramenta_worker.iniciado)
        self.assertEqual(chat.ferramenta_worker.args, (decisao,))

    def test_microfone_injetado_e_usado_no_ouvir(self):
        chat = montar_chat()

        chat.ouvir()

        self.assertIsInstance(chat.microfone_worker, WorkerFalso)
        self.assertTrue(chat.microfone_worker.iniciado)


class TestComportamentoPreservado(unittest.TestCase):
    """O que processar() ja fazia continua igual."""

    def test_comando_parar_interrompe_a_fala(self):
        # Hoje so a frase exata vale: "pare", "chega", "pode parar".
        # "Milk, pare." NAO e reconhecido - o prefixo com o nome dela
        # nao e removido em e_comando_parar(). Achado registrado, fora
        # do escopo da Fase 1.
        chat = montar_chat()

        chat.processar("pare")

        chat.milk.parar_fala.assert_called_once()

        self.assertIsNone(chat.claude_worker)

    def test_pedido_em_andamento_nao_dispara_outro(self):
        class Ocupado(WorkerFalso):
            def isRunning(self):
                return True

        chat = montar_chat(criar_claude_worker=Ocupado)

        chat.processar("primeira pergunta")

        primeiro = chat.claude_worker

        chat.processar("segunda pergunta")

        self.assertIs(chat.claude_worker, primeiro)

    def test_nome_e_reconhecido_quando_ela_esta_perguntando(self):
        gravar = Mock()

        chat = montar_chat(
            ler_pessoa=lambda: None,
            gravar_pessoa=gravar
        )

        chat.processar("meu nome e Ana")

        gravar.assert_called_once_with("Ana")

        self.assertIsNone(chat.claude_worker)


if __name__ == "__main__":
    unittest.main(verbosity=2)
