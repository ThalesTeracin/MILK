# Milk — assistente pessoal.
# Copyright (c) 2026 Thales Teracin. Todos os direitos reservados.
#
# Software proprietário. É proibida a cópia, a distribuição, a
# modificação e a engenharia reversa, no todo ou em parte, sem
# autorização expressa e por escrito do autor. Ver LICENSE.txt.

"""Resumo de um assunto na Wikipédia.

Primeiro procura o verbete, depois pega o resumo. Assim ela aguenta
letra minúscula, acento faltando e nome parcial.

Trata os dois casos chatos: página que não existe e página de
desambiguação (quando o nome serve para várias coisas).
"""

import re
import urllib.parse

from milk.core.settings import obter
from milk.tools import ErroFerramenta, certo, falhou
from milk.tools.http import buscar_json


SERVICO = "Wikipédia"


def idioma():
    return obter(
        "wikipedia",
        "idioma",
        "pt"
    )


def url_busca():
    return f"https://{idioma()}.wikipedia.org/w/api.php"


def url_resumo(titulo):
    caminho = urllib.parse.quote(
        titulo.replace(" ", "_"),
        safe=""
    )

    return (
        f"https://{idioma()}.wikipedia.org"
        f"/api/rest_v1/page/summary/{caminho}"
    )


def procurar_titulo(assunto):
    """Devolve o título do verbete mais próximo, ou None."""

    dados = buscar_json(
        url_busca(),
        {
            "action": "query",
            "list": "search",
            "srsearch": assunto,
            "srlimit": 1,
            "format": "json",
        },
        servico=SERVICO,
    )

    achados = (
        (dados.get("query") or {}).get("search")
        or
        []
    )

    if not achados:
        return None

    return achados[0].get("title")


def encurtar(texto, frases=None):
    """Corta o resumo nas primeiras frases, para não virar discurso."""

    limite = frases or obter(
        "wikipedia",
        "frases_do_resumo",
        3
    )

    limpo = re.sub(
        r"\s+",
        " ",
        texto or ""
    ).strip()

    if not limpo:
        return ""

    partes = re.split(
        r"(?<=[.!?])\s+",
        limpo
    )

    return " ".join(
        partes[:limite]
    ).strip()


def pesquisar(assunto):
    """Resumo curto de um assunto."""

    assunto = (assunto or "").strip().strip("?.!,")

    if len(assunto) < 2:
        return falhou(
            "Não entendi sobre o que você quer saber."
        )

    try:
        titulo = procurar_titulo(assunto)

        if not titulo:
            return falhou(
                f"Não achei nada sobre {assunto} na Wikipédia."
            )

        dados = buscar_json(
            url_resumo(titulo),
            servico=SERVICO,
        )

    except ErroFerramenta as erro:
        if erro.codigo == 404:
            return falhou(
                f"Não achei uma página sobre {assunto} na Wikipédia."
            )

        return falhou(erro.mensagem)

    if dados.get("type") == "disambiguation":
        return falhou(
            f"{titulo} pode ser várias coisas diferentes. "
            "Me diz com mais detalhe o que você quer saber?"
        )

    resumo = encurtar(
        dados.get("extract")
    )

    if not resumo:
        return falhou(
            f"Achei a página de {titulo}, mas ela está sem resumo."
        )

    return certo(
        resumo,
        {
            "titulo": dados.get("title") or titulo,
            "resumo": resumo,
            "url": (
                (dados.get("content_urls") or {})
                .get("desktop", {})
                .get("page", "")
            ),
        },
    )
