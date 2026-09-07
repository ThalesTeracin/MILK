# Milk — assistente pessoal.
# Copyright (c) 2026 Thales Teracin. Todos os direitos reservados.
#
# Software proprietário. É proibida a cópia, a distribuição, a
# modificação e a engenharia reversa, no todo ou em parte, sem
# autorização expressa e por escrito do autor. Ver LICENSE.txt.

r"""Trava de autoria da Milk.

A Milk foi desenvolvida por Thales Teracin, e isso precisa continuar
escrito em todo lugar que importa: no módulo de autoria, no cabeçalho
de cada arquivo de código, na licença, no README e na identidade que
ela carrega quando conversa.

Estes testes existem para falhar se alguém apagar, trocar ou encobrir
essa autoria — por descuido ou de propósito.

Rodar:  .venv\Scripts\python.exe -m unittest discover -s tests -v
"""

import os
import sys
import unittest

RAIZ = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

sys.path.insert(0, RAIZ)

from milk.core.autoria import (  # noqa: E402
    AUTOR,
    COPYRIGHT,
    CREDITO,
    credito,
    copyright_curto,
)

NOME_ESPERADO = "Thales Teracin"


def ler(caminho):
    with open(caminho, encoding="utf-8") as arq:
        return arq.read()


def arquivos_python():
    """Todo .py do projeto, fora de ambiente, build e backup."""

    ignorar = {
        ".venv", "build", "dist", "backups",
        "__pycache__", ".git",
    }

    for pasta, subpastas, arquivos in os.walk(RAIZ):
        subpastas[:] = [
            s for s in subpastas if s not in ignorar
        ]

        for nome in arquivos:
            if nome.endswith(".py"):
                yield os.path.join(pasta, nome)


class TestFonteDaAutoria(unittest.TestCase):
    """O módulo milk/core/autoria.py é a fonte única."""

    def test_nome_do_autor(self):
        self.assertEqual(AUTOR, NOME_ESPERADO)

    def test_credito_cita_o_autor(self):
        self.assertIn(NOME_ESPERADO, CREDITO)
        self.assertIn(NOME_ESPERADO, credito())

    def test_copyright_cita_o_autor(self):
        self.assertIn(NOME_ESPERADO, COPYRIGHT)
        self.assertIn(NOME_ESPERADO, copyright_curto())


class TestAutoriaNaIdentidade(unittest.TestCase):
    """Perguntaram quem a criou: ela responde Thales Teracin."""

    def test_identidade_cita_o_autor(self):
        from milk.intelligence.prompt import IDENTIDADE

        self.assertIn(NOME_ESPERADO, IDENTIDADE)

    def test_prompt_montado_cita_o_autor(self):
        from milk.intelligence.prompt import montar_prompt

        prompt = montar_prompt(
            texto="quem te criou?",
            historico=[],
            pessoa=None,
            memoria_resumida="",
        )

        self.assertIn(NOME_ESPERADO, prompt)


class TestAutoriaNosArquivos(unittest.TestCase):
    """Cabeçalho de direito autoral em cada arquivo de código."""

    def test_todo_py_tem_o_autor_no_cabecalho(self):
        sem_autoria = []

        for caminho in arquivos_python():
            cabecalho = ler(caminho)[:600]

            if NOME_ESPERADO not in cabecalho:
                sem_autoria.append(
                    os.path.relpath(caminho, RAIZ)
                )

        self.assertEqual(
            sem_autoria,
            [],
            "arquivos sem a autoria no cabeçalho: "
            f"{sem_autoria}",
        )


class TestAutoriaNosDocumentos(unittest.TestCase):
    """Licença e README também identificam o autor."""

    def test_licenca_cita_o_autor(self):
        texto = ler(os.path.join(RAIZ, "LICENSE.txt"))

        self.assertIn(NOME_ESPERADO, texto)

    def test_readme_cita_o_autor(self):
        texto = ler(os.path.join(RAIZ, "README.md"))

        self.assertIn(NOME_ESPERADO, texto)


if __name__ == "__main__":
    unittest.main()
