# Milk — assistente pessoal.
# Copyright (c) 2026 Thales Teracin. Todos os direitos reservados.
#
# Software proprietário. É proibida a cópia, a distribuição, a
# modificação e a engenharia reversa, no todo ou em parte, sem
# autorização expressa e por escrito do autor. Ver LICENSE.txt.

"""Milk Doctor, modos, início com o Windows e posição salva.

O diagnóstico é feito com exames de mentira, para o teste não depender
do estado da máquina. Só um teste roda os exames de verdade, e ele não
exige que esteja tudo bem — exige que o diagnóstico não quebre.

Rodar:  .venv\\Scripts\\python.exe -m unittest discover -s tests -v
"""

import os
import sys
import unittest

from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

sys.path.insert(
    0,
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )
)

from milk.core import doutor
from milk.core.doutor import ATENCAO, Exame, FALHA, OK
from milk.core.modos import (
    NAO_PERTURBE,
    NORMAL,
    SILENCIOSO,
    Modos,
)
from milk.system import inicio
from milk.intelligence.roteador import rotear


def exame_bom(nome="Peça"):
    return lambda: Exame(nome, OK, "tudo certo")


def exame_ruim(nome="Peça", conserto="Conserte assim."):
    return lambda: Exame(nome, FALHA, "quebrou", conserto)


def exame_torto(nome="Peça"):
    return lambda: Exame(nome, ATENCAO, "meio torto")


def exame_que_estoura():
    raise RuntimeError("o próprio exame explodiu")


# ============================================================
# DIAGNÓSTICO
# ============================================================

class TestExames(unittest.TestCase):

    def test_tudo_bem(self):
        resultados = doutor.examinar(
            [exame_bom("Um"), exame_bom("Dois")]
        )

        self.assertTrue(
            all(exame.ok for exame in resultados)
        )

        self.assertIn(
            "tudo certo",
            doutor.resumo_falado(resultados)
        )

    def test_exame_que_estoura_vira_falha(self):
        resultados = doutor.examinar([exame_que_estoura])

        self.assertEqual(len(resultados), 1)
        self.assertEqual(resultados[0].estado, FALHA)
        self.assertIn("explodiu", resultados[0].detalhe)

    def test_um_exame_ruim_nao_para_os_outros(self):
        resultados = doutor.examinar(
            [exame_que_estoura, exame_bom("Depois")]
        )

        self.assertEqual(len(resultados), 2)
        self.assertTrue(resultados[1].ok)

    def test_relatorio_tem_cabecalho_e_conserto(self):
        resultados = doutor.examinar(
            [exame_bom("Boa"), exame_ruim("Ruim", "Troque o cabo.")]
        )

        texto = doutor.relatorio(resultados)

        self.assertIn("MILK SYSTEM STATUS", texto)
        self.assertIn("Boa: OK", texto)
        self.assertIn("Ruim: FALHA", texto)
        self.assertIn("O QUE FAZER", texto)
        self.assertIn("Troque o cabo.", texto)

    def test_relatorio_sem_problema_nao_tem_secao_de_conserto(self):
        texto = doutor.relatorio(
            doutor.examinar([exame_bom()])
        )

        self.assertNotIn("O QUE FAZER", texto)

    def test_resumo_falado_diz_o_que_esta_ruim(self):
        resultados = doutor.examinar(
            [exame_bom("Boa"), exame_ruim("Microfone", "Tire o mudo.")]
        )

        resumo = doutor.resumo_falado(resultados)

        self.assertIn("Microfone", resumo)
        self.assertIn("Tire o mudo.", resumo)

    def test_resumo_separa_falha_de_atencao(self):
        resultados = doutor.examinar(
            [exame_ruim("Grave"), exame_torto("Leve")]
        )

        resumo = doutor.resumo_falado(resultados)

        self.assertIn("Com problema", resumo)
        self.assertIn("Para olhar", resumo)


class TestExamesDeVerdade(unittest.TestCase):
    """Roda na máquina mesmo. Nenhum exame pode levantar exceção."""

    def test_exames_leves_respondem(self):
        for exame in (
            doutor.exame_arquivos,
            doutor.exame_latido,
            doutor.exame_voz,
            doutor.exame_tarefas,
            doutor.exame_memoria,
            doutor.exame_ferramentas,
            doutor.exame_disco,
            doutor.exame_logs,
            doutor.exame_configuracao_do_claude,
            doutor.exame_reconhecimento,
        ):
            with self.subTest(exame=exame.__name__):
                resultado = exame()

                self.assertIn(
                    resultado.estado,
                    (OK, ATENCAO, FALHA)
                )

    def test_reconhecimento_esta_de_pe_nesta_maquina(self):
        # A correção do FLAC em ARM64 precisa continuar valendo.
        self.assertEqual(
            doutor.exame_reconhecimento().estado,
            OK
        )

    def test_microfone_mede_o_mundo_real(self):
        """Tres respostas possiveis, e as duas ruins ensinam o conserto.

        ATENCAO e o caso do fone Bluetooth desligado: o aparelho pedido
        no settings.json nao esta na lista agora."""

        resultado = doutor.exame_microfone(segundos=0.2)

        self.assertIn(resultado.estado, (OK, ATENCAO, FALHA))

        if resultado.estado != OK:
            self.assertTrue(resultado.conserto)


class TestRotaDoDiagnostico(unittest.TestCase):

    def test_jeitos_de_pedir(self):
        for frase in (
            "você está bem?",
            "faça um diagnóstico",
            "milk doctor",
            "está tudo funcionando?",
        ):
            with self.subTest(frase=frase):
                decisao = rotear(frase)

                self.assertIsNotNone(decisao, frase)
                self.assertEqual(decisao.ferramenta, "sistema")

    def test_diagnostico_nao_trava_a_janela(self):
        # Ele mede microfone e chama o Claude: vai para a thread.
        decisao = rotear("faça um diagnóstico")

        self.assertFalse(decisao.local)


# ============================================================
# MODOS
# ============================================================

class TestModos(unittest.TestCase):

    def modos(self, guardado=None):
        disco = {"arquivo": guardado} if guardado else {}

        return Modos(
            ler=lambda caminho, padrao=None: disco.get(caminho, padrao),
            gravar=lambda caminho, conteudo: disco.__setitem__(
                caminho, conteudo
            ),
            arquivo="arquivo",
        )

    def test_comeca_normal(self):
        modos = self.modos()

        self.assertEqual(modos.modo, NORMAL)
        self.assertTrue(modos.pode_falar())
        self.assertTrue(modos.pode_latir())
        self.assertTrue(modos.pode_aparecer_sozinha())

    def test_silencioso_nao_fala_mas_aparece(self):
        modos = self.modos()

        modos.definir(SILENCIOSO)

        self.assertFalse(modos.pode_falar())
        self.assertFalse(modos.pode_latir())
        self.assertTrue(modos.pode_aparecer_sozinha())

    def test_nao_perturbe_nao_aparece(self):
        modos = self.modos()

        modos.definir(NAO_PERTURBE)

        self.assertFalse(modos.pode_falar())
        self.assertFalse(modos.pode_aparecer_sozinha())

    def test_modo_desconhecido_vira_normal(self):
        modos = self.modos()

        modos.definir("MODO_INVENTADO")

        self.assertEqual(modos.modo, NORMAL)

    def test_modo_sobrevive_a_fechar(self):
        disco = {}

        primeiro = Modos(
            ler=lambda caminho, padrao=None: disco.get(caminho, padrao),
            gravar=lambda caminho, conteudo: disco.__setitem__(
                caminho, conteudo
            ),
            arquivo="arquivo",
        )

        primeiro.definir(SILENCIOSO)

        segundo = Modos(
            ler=lambda caminho, padrao=None: disco.get(caminho, padrao),
            gravar=lambda caminho, conteudo: None,
            arquivo="arquivo",
        )

        self.assertEqual(segundo.modo, SILENCIOSO)

    def test_arquivo_torto_nao_quebra(self):
        modos = Modos(
            ler=lambda caminho, padrao=None: "isso não é dicionário",
            gravar=lambda caminho, conteudo: True,
        )

        self.assertEqual(modos.modo, NORMAL)

    def test_disco_quebrado_nao_impede_a_troca(self):
        def gravar_quebrado(caminho, conteudo):
            raise OSError("sem disco")

        modos = Modos(
            ler=lambda caminho, padrao=None: padrao,
            gravar=gravar_quebrado,
        )

        modos.definir(SILENCIOSO)

        self.assertEqual(modos.modo, SILENCIOSO)


# ============================================================
# INÍCIO COM O WINDOWS
# ============================================================

class TestInicio(unittest.TestCase):

    def test_comando_usa_pythonw_e_o_milk(self):
        comando = inicio.comando_de_inicio()

        self.assertIn("milk.py", comando)
        self.assertTrue(comando.startswith('"'))

    def test_consulta_nao_levanta(self):
        # Só lê o registro do usuário; qualquer resposta serve.
        self.assertIn(
            inicio.esta_ligado(),
            (True, False)
        )

    def test_falha_no_registro_vira_false(self):
        with patch.object(
            inicio,
            "_abrir_chave",
            side_effect=PermissionError("sem permissão")
        ):
            self.assertFalse(inicio.ligar())
            self.assertFalse(inicio.esta_ligado())

    def test_desligar_o_que_nao_existe_da_certo(self):
        with patch.object(
            inicio,
            "_abrir_chave",
            side_effect=FileNotFoundError()
        ):
            self.assertTrue(inicio.desligar())


# ============================================================
# POSIÇÃO SALVA
# ============================================================

class TestPosicao(unittest.TestCase):

    def setUp(self):
        from milk.avatar import posicao

        self.posicao = posicao

        self.telas = [
            (0, 0, 1920, 1040),
            (1920, 0, 1920, 1040),
        ]

    def test_cabe_em_qualquer_monitor(self):
        self.assertTrue(
            self.posicao.cabe_na_tela(100, 100, 140, 168, self.telas)
        )

        self.assertTrue(
            self.posicao.cabe_na_tela(3000, 500, 140, 168, self.telas)
        )

    def test_fora_de_todos_os_monitores(self):
        self.assertFalse(
            self.posicao.cabe_na_tela(9000, 500, 140, 168, self.telas)
        )

    def test_meio_fora_da_borda_nao_vale(self):
        self.assertFalse(
            self.posicao.cabe_na_tela(
                1850, 100, 140, 168, [self.telas[0]]
            )
        )

    def test_ida_e_volta(self):
        disco = {}

        self.assertTrue(
            self.posicao.gravar(
                300,
                400,
                arquivo="p",
                gravar_arquivo=lambda caminho, conteudo:
                disco.__setitem__(caminho, conteudo) or True,
            )
        )

        self.assertEqual(
            self.posicao.ler(
                arquivo="p",
                ler_arquivo=lambda caminho, padrao=None:
                disco.get(caminho, padrao),
            ),
            (300, 400)
        )

    def test_arquivo_torto_nao_quebra(self):
        self.assertIsNone(
            self.posicao.ler(
                arquivo="p",
                ler_arquivo=lambda caminho, padrao=None: {"x": "aqui"},
            )
        )

        self.assertIsNone(
            self.posicao.ler(
                arquivo="p",
                ler_arquivo=lambda caminho, padrao=None: "nada disso",
            )
        )


if __name__ == "__main__":
    unittest.main()
