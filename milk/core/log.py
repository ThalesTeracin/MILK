# Milk — assistente pessoal.
# Copyright (c) 2026 Thales Teracin. Todos os direitos reservados.
#
# Software proprietário. É proibida a cópia, a distribuição, a
# modificação e a engenharia reversa, no todo ou em parte, sem
# autorização expressa e por escrito do autor. Ver LICENSE.txt.

"""Logs da Milk.

Um arquivo por área, em `logs/`, com rotação. Serve para descobrir o
que aconteceu depois que aconteceu — a Milk roda sem terminal à vista,
então sem log não sobra rastro nenhum.

Nada aqui pode derrubar a Milk. Se a pasta não puder ser criada, o
logger continua existindo e só não escreve em disco.

**Segredo nunca entra no log.** Toda mensagem passa por um filtro que
troca token, senha e chave por `***`, antes de chegar ao arquivo.
"""

import re
import logging

from logging.handlers import RotatingFileHandler

from milk.core.config import LOGS_DIR


AREAS = (
    "app",
    "voice",
    "claude",
    "tasks",
    "tools",
    "system",
    "errors",
)


TAMANHO_MAXIMO = 1_000_000

QUANTOS_ARQUIVOS = 3

FORMATO = "%(asctime)s %(levelname)s %(name)s: %(message)s"


# Coisas que nunca podem aparecer escritas: o valor vira ***.
SEGREDOS = (
    # token=abc, "api_key": "abc", senha: abc
    re.compile(
        r"((?:token|senha|password|secret|api[_-]?key|chave|"
        r"authorization|bearer)\W{1,4})([^\s\"',;)]{4,})",
        re.IGNORECASE,
    ),
    # Cabeçalho de token do GitHub e afins.
    re.compile(r"\b(gh[pousr]_)[A-Za-z0-9]{10,}\b"),
    re.compile(r"\b(sk-[A-Za-z0-9_\-]{10,})\b"),
)


def limpar_segredos(texto):
    """Troca o valor do segredo por ***, mantendo o nome do campo."""

    limpo = str(texto)

    limpo = SEGREDOS[0].sub(r"\1***", limpo)
    limpo = SEGREDOS[1].sub(r"\1***", limpo)
    limpo = SEGREDOS[2].sub("sk-***", limpo)

    return limpo


class FiltroDeSegredo(logging.Filter):
    """Passa toda mensagem pela limpeza antes de ela virar arquivo."""

    def filter(self, registro):
        try:
            registro.msg = limpar_segredos(
                registro.getMessage()
            )

            registro.args = ()

        except Exception:
            # Log quebrado é melhor que Milk quebrada.
            pass

        return True


_criados = {}


def caminho_da_area(area):
    return LOGS_DIR / area / f"{area}.log"


def logger(area="app"):
    """O logger daquela área, criado uma vez por processo."""

    nome = area if area in AREAS else "app"

    if nome in _criados:
        return _criados[nome]

    registrador = logging.getLogger(f"milk.{nome}")

    registrador.setLevel(logging.INFO)

    # Sem propagar: cada área escreve no seu arquivo e pronto.
    registrador.propagate = False

    registrador.addFilter(
        FiltroDeSegredo()
    )

    try:
        destino = caminho_da_area(nome)

        destino.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        arquivo = RotatingFileHandler(
            destino,
            maxBytes=TAMANHO_MAXIMO,
            backupCount=QUANTOS_ARQUIVOS,
            encoding="utf-8",
        )

        arquivo.setFormatter(
            logging.Formatter(FORMATO)
        )

        registrador.addHandler(arquivo)

    except Exception:
        # Sem disco, o logger existe e não escreve. Ninguém quebra.
        registrador.addHandler(
            logging.NullHandler()
        )

    _criados[nome] = registrador

    return registrador


def registrar_erro(area, mensagem, excecao=None):
    """Erro vai para a área dele e também para logs/errors."""

    texto = str(mensagem)

    if excecao is not None:
        texto = f"{texto} | {type(excecao).__name__}: {excecao}"

    logger(area).error(texto)

    if area != "errors":
        logger("errors").error(f"[{area}] {texto}")

    return texto
