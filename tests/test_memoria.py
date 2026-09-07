# Milk — assistente pessoal.
# Copyright (c) 2026 Thales Teracin. Todos os direitos reservados.
#
# Software proprietário. É proibida a cópia, a distribuição, a
# modificação e a engenharia reversa, no todo ou em parte, sem
# autorização expressa e por escrito do autor. Ver LICENSE.txt.

"""Memória: fatos, projetos, conversa, e o que ela responde sobre isso.

Nada toca o disco: a leitura e a gravação entram por argumento.

Rodar:  .venv\\Scripts\\python.exe -m unittest discover -s tests -v
"""

import os
import sys
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

from milk.core.arquivo import ler_json, gravar_json
from milk.core.eventos import Barramento
from milk.memory.memoria import Memoria, definir_memoria, tem_segredo
from milk.intelligence import rotas_memoria
from milk.intelligence.prompt import montar_prompt
from milk.intelligence.roteador import rotear
from milk.tasks.gerente import GerenteDeTarefas, definir_gerente
from milk.avatar.chat import ChatBubble


app = QApplication.instance() or QApplication([])


def memoria_de_mentira(guardado=None):
    """Memória que vive num dicionário, sem arquivo nenhum."""

    disco = dict(guardado or {})

    def ler(caminho, padrao=None):
        return disco.get(caminho, padrao)

    def gravar(caminho, conteudo):
        disco[caminho] = conteudo

        return True

    memoria = Memoria(
        ler=ler,
        gravar=gravar,
        arquivo_memoria="memoria",
        arquivo_conversa="conversa",
    )

    memoria.disco = disco

    return memoria


def fila_de_mentira():
    return GerenteDeTarefas(
        barramento=Barramento(),
        ler=lambda: [],
        gravar=lambda tarefas: True,
    )


# ============================================================
# ARQUIVO
# ============================================================

class TestArquivo(unittest.TestCase):

    def setUp(self):
        import tempfile

        self.pasta = tempfile.TemporaryDirectory()

        self.caminho = os.path.join(
            self.pasta.name,
            "coisa.json"
        )

    def tearDown(self):
        self.pasta.cleanup()

    def test_grava_e_le(self):
        self.assertTrue(
            gravar_json(self.caminho, {"a": 1})
        )

        self.assertEqual(
            ler_json(self.caminho),
            {"a": 1}
        )

    def test_ausente_devolve_padrao(self):
        self.assertEqual(
            ler_json(self.caminho, "vazio"),
            "vazio"
        )

    def test_corrompido_devolve_padrao(self):
        with open(self.caminho, "w", encoding="utf-8") as arquivo:
            arquivo.write("{quebrado")

        self.assertIsNone(
            ler_json(self.caminho)
        )

    def test_nao_deixa_temporario(self):
        gravar_json(self.caminho, {"a": 1})

        sobras = [
            nome
            for nome in os.listdir(self.pasta.name)
            if nome.endswith(".tmp")
        ]

        self.assertEqual(sobras, [])

    def test_acento_fica_legivel(self):
        gravar_json(self.caminho, {"nome": "São Paulo"})

        with open(self.caminho, "r", encoding="utf-8") as arquivo:
            self.assertIn("São Paulo", arquivo.read())


# ============================================================
# MEMÓRIA
# ============================================================

class TestFatos(unittest.TestCase):

    def setUp(self):
        self.memoria = memoria_de_mentira()

    def test_lembrar_guarda_e_grava(self):
        fato = self.memoria.lembrar("eu prefiro café sem açúcar")

        self.assertIsNotNone(fato)
        self.assertEqual(len(self.memoria.fatos), 1)
        self.assertIn("memoria", self.memoria.disco)

    def test_fato_repetido_nao_duplica(self):
        self.memoria.lembrar("eu moro em Curitiba")
        self.memoria.lembrar("eu moro em Curitiba")

        self.assertEqual(len(self.memoria.fatos), 1)

    def test_frase_curta_demais_nao_vira_fato(self):
        self.assertIsNone(
            self.memoria.lembrar("ok")
        )

    def test_segredo_nunca_e_guardado(self):
        for frase in (
            "minha senha do banco é 1234",
            "meu token do GitHub é abcdef",
            "guarde a chave de api do serviço",
            "o cvv do cartão de crédito é 999",
        ):
            with self.subTest(frase=frase):
                self.assertTrue(tem_segredo(frase))
                self.assertIsNone(self.memoria.lembrar(frase))

        self.assertEqual(self.memoria.fatos, [])

    def test_buscar_por_assunto(self):
        self.memoria.lembrar("eu trabalho com AWS")
        self.memoria.lembrar("eu prefiro café sem açúcar")

        achados = self.memoria.buscar("café")

        self.assertEqual(len(achados), 1)
        self.assertIn("café", achados[0]["texto"])

    def test_esquecer_so_o_que_foi_pedido(self):
        self.memoria.lembrar("eu trabalho com AWS")
        self.memoria.lembrar("eu prefiro café sem açúcar")

        self.assertEqual(self.memoria.esquecer("café"), 1)
        self.assertEqual(len(self.memoria.fatos), 1)

    def test_esquecer_o_que_nao_existe(self):
        self.assertEqual(
            self.memoria.esquecer("dinossauro"),
            0
        )

    def test_esquecer_tudo(self):
        self.memoria.lembrar("uma coisa qualquer")
        self.memoria.lembrar("outra coisa qualquer")

        self.assertEqual(self.memoria.esquecer_tudo(), 2)
        self.assertEqual(self.memoria.fatos, [])

    def test_volta_do_disco(self):
        self.memoria.lembrar("eu moro em Curitiba")

        outra = Memoria(
            ler=self.memoria._ler,
            gravar=self.memoria._gravar,
            arquivo_memoria="memoria",
            arquivo_conversa="conversa",
        )

        self.assertEqual(len(outra.fatos), 1)

    def test_arquivo_torto_nao_quebra(self):
        estranha = Memoria(
            ler=lambda caminho, padrao=None: "isso não é dicionário",
            gravar=lambda caminho, conteudo: True,
        )

        self.assertEqual(estranha.fatos, [])
        self.assertEqual(estranha.conversa, [])


class TestProjetos(unittest.TestCase):

    def setUp(self):
        self.memoria = memoria_de_mentira()

    def test_anotar_e_achar(self):
        self.memoria.anotar_projeto("Milk", nota="fila de tarefas")

        projeto = self.memoria.projeto("milk")

        self.assertEqual(projeto["nome"], "Milk")
        self.assertEqual(projeto["notas"][-1]["texto"], "fila de tarefas")

    def test_projeto_recente_e_o_ultimo_tocado(self):
        self.memoria.anotar_projeto("Antigo")
        self.memoria.anotar_projeto("Novo")

        self.assertEqual(
            self.memoria.projeto_recente()["nome"],
            "Novo"
        )

    def test_notas_nao_crescem_para_sempre(self):
        for numero in range(30):
            self.memoria.anotar_projeto("Milk", nota=f"nota {numero}")

        self.assertLessEqual(
            len(self.memoria.projeto("milk")["notas"]),
            10
        )


class TestConversaGuardada(unittest.TestCase):

    def setUp(self):
        self.memoria = memoria_de_mentira()

    def test_registrar_fala(self):
        self.memoria.registrar_fala("Usuário", "oi Milk")
        self.memoria.registrar_fala("Milk", "oi!")

        self.assertEqual(len(self.memoria.conversa), 2)

    def test_fala_vazia_nao_entra(self):
        self.assertIsNone(
            self.memoria.registrar_fala("Milk", "   ")
        )

    def test_conversa_tem_teto(self):
        for numero in range(80):
            self.memoria.registrar_fala("Milk", f"fala {numero}")

        self.assertLessEqual(len(self.memoria.conversa), 40)

        self.assertEqual(
            self.memoria.conversa[-1]["texto"],
            "fala 79"
        )

    def test_falas_do_dia(self):
        self.memoria.registrar_fala("Milk", "de hoje")

        self.assertEqual(
            len(self.memoria.falas_do_dia()),
            1
        )

        self.assertEqual(
            self.memoria.falas_do_dia("1999-01-01"),
            []
        )


class TestResumo(unittest.TestCase):

    def test_memoria_vazia_nao_gera_bloco(self):
        self.assertEqual(
            memoria_de_mentira().resumo(),
            ""
        )

    def test_resumo_traz_fatos_e_projeto(self):
        memoria = memoria_de_mentira()

        memoria.lembrar("eu prefiro respostas curtas")
        memoria.anotar_projeto("Milk", caminho=r"C:\AssistenteAvatar")

        resumo = memoria.resumo()

        self.assertIn("O QUE VOCÊ JÁ SABE", resumo)
        self.assertIn("respostas curtas", resumo)
        self.assertIn("PROJETOS", resumo)
        self.assertIn("Milk", resumo)

    def test_resumo_nao_cresce_sem_limite(self):
        memoria = memoria_de_mentira()

        for numero in range(50):
            memoria.lembrar(f"fato número {numero} do usuário")

        self.assertLessEqual(
            memoria.resumo().count("\n- "),
            12
        )


class TestPromptComMemoria(unittest.TestCase):

    def test_prompt_sem_memoria_continua_igual(self):
        prompt = montar_prompt(
            "oi",
            [],
            "Thales",
            memoria_resumida=""
        )

        self.assertIn("PEDIDO ATUAL", prompt)
        self.assertNotIn("O QUE VOCÊ JÁ SABE", prompt)

    def test_prompt_carrega_a_memoria(self):
        prompt = montar_prompt(
            "oi",
            [],
            "Thales",
            memoria_resumida="O QUE VOCÊ JÁ SABE:\n- gosta de café"
        )

        self.assertIn("gosta de café", prompt)

        # A ordem importa: contexto antes do pedido.
        self.assertLess(
            prompt.index("gosta de café"),
            prompt.index("PEDIDO ATUAL")
        )


# ============================================================
# COMANDOS DE MEMÓRIA
# ============================================================

class TestRotasDeMemoria(unittest.TestCase):

    def setUp(self):
        self.memoria = memoria_de_mentira()

        definir_memoria(self.memoria)
        definir_gerente(fila_de_mentira())

    def tearDown(self):
        definir_memoria(None)
        definir_gerente(None)

    def rota(self, frase):
        decisao = rotear(frase)

        return decisao.ferramenta if decisao else None

    def responder(self, frase):
        decisao = rotear(frase)

        self.assertIsNotNone(decisao, frase)

        return decisao.executar().texto

    def test_frases_de_memoria(self):
        for frase in (
            "lembre que eu prefiro café sem açúcar",
            "anota que a reunião é na terça",
            "guarde que eu moro em Curitiba",
            "o que você sabe sobre mim?",
            "o que você lembra",
            "o que você sabe sobre café",
            "esqueça o que eu falei sobre café",
            "esqueça tudo",
            "limpe a sua memória",
            "o que fizemos hoje?",
            "o que a gente fez ontem",
            "estou trabalhando no projeto Milk",
        ):
            with self.subTest(frase=frase):
                self.assertEqual(self.rota(frase), "memoria")

    def test_conversa_normal_nao_vira_memoria(self):
        for frase in (
            "crie uma landing page",
            "que horas são?",
            "o que é fotossíntese",
            "quais tarefas estão pendentes",
            "me conta uma piada",
        ):
            with self.subTest(frase=frase):
                self.assertNotEqual(self.rota(frase), "memoria")

    def test_guardar_de_verdade(self):
        resposta = self.responder(
            "lembre que eu prefiro café sem açúcar"
        )

        self.assertIn("Guardado", resposta)

        self.assertEqual(len(self.memoria.fatos), 1)

    def test_recusa_segredo_com_explicacao(self):
        resposta = self.responder(
            "lembre que a minha senha do banco é 1234"
        )

        self.assertIn("prefiro não guardar", resposta)
        self.assertEqual(self.memoria.fatos, [])

    def test_contar_o_que_sabe(self):
        self.memoria.lembrar("eu moro em Curitiba")

        resposta = self.responder("o que você sabe sobre mim?")

        self.assertIn("Curitiba", resposta)

    def test_memoria_vazia_ensina_o_comando(self):
        resposta = self.responder("o que você sabe sobre mim?")

        self.assertIn("lembre que", resposta)

    def test_esquecer_de_verdade(self):
        self.memoria.lembrar("eu prefiro café sem açúcar")

        resposta = self.responder(
            "esqueça o que eu falei sobre café"
        )

        self.assertIn("Esqueci", resposta)
        self.assertEqual(self.memoria.fatos, [])

    def test_anotar_projeto(self):
        resposta = self.responder(
            "estou trabalhando no projeto Milk"
        )

        self.assertIn("Milk", resposta)
        self.assertIsNotNone(self.memoria.projeto("milk"))

    def test_o_que_fizemos_sem_nada(self):
        resposta = self.responder("o que fizemos hoje?")

        self.assertIn("Não tenho nada registrado", resposta)

    def test_o_que_fizemos_com_tarefa_concluida(self):
        gerente = fila_de_mentira()

        definir_gerente(gerente)

        tarefa = gerente.criar("analisar o projeto")

        gerente.iniciar(tarefa)
        gerente.concluir(tarefa, "pronto")

        resposta = self.responder("o que fizemos hoje?")

        self.assertIn("analisar o projeto", resposta)


# ============================================================
# A CONVERSA USANDO A MEMÓRIA
# ============================================================

class WorkerFalso:

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


class TestConversaComMemoria(unittest.TestCase):

    def montar(self, memoria):
        return ChatBubble(
            Mock(),
            criar_claude_worker=WorkerFalso,
            criar_microfone_worker=WorkerFalso,
            criar_ferramenta_worker=WorkerFalso,
            roteador=rotear,
            montador_prompt=lambda texto, historico, pessoa: texto,
            ler_pessoa=lambda: "Thales",
            gravar_pessoa=Mock(),
            gerente_de_tarefas=fila_de_mentira(),
            memoria_da_milk=memoria,
        )

    def test_a_fala_vai_para_a_memoria(self):
        memoria = memoria_de_mentira()

        chat = self.montar(memoria)

        chat.processar("analise meu projeto python")

        papeis = [
            fala["papel"]
            for fala in memoria.conversa
        ]

        self.assertIn("Usuário", papeis)

        chat.deleteLater()

    def test_a_conversa_anterior_volta_ao_abrir(self):
        memoria = memoria_de_mentira()

        memoria.registrar_fala("Usuário", "estávamos falando do Milk")
        memoria.registrar_fala("Milk", "sim, da fila de tarefas")

        chat = self.montar(memoria)

        textos = [
            item["texto"]
            for item in chat.historico
        ]

        self.assertIn("estávamos falando do Milk", textos)

        chat.deleteLater()

    def test_memoria_quebrada_nao_derruba_a_conversa(self):
        class MemoriaQuebrada(Memoria):
            def registrar_fala(self, papel, texto):
                raise RuntimeError("disco pegou fogo")

        memoria = MemoriaQuebrada(
            ler=lambda caminho, padrao=None: padrao,
            gravar=lambda caminho, conteudo: True,
        )

        chat = self.montar(memoria)

        chat.processar("analise meu projeto python")

        # A conversa seguiu mesmo com a memória falhando.
        self.assertTrue(chat.claude_worker.iniciado)

        chat.deleteLater()


if __name__ == "__main__":
    unittest.main()
