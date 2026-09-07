# Milk — assistente pessoal.
# Copyright (c) 2026 Thales Teracin. Todos os direitos reservados.
#
# Software proprietário. É proibida a cópia, a distribuição, a
# modificação e a engenharia reversa, no todo ou em parte, sem
# autorização expressa e por escrito do autor. Ver LICENSE.txt.

"""Consulta de repositórios públicos no GitHub.

Funciona sem token: a API pública permite 60 consultas por hora por IP,
o que basta para uso pessoal. Se existir um token, ele é lido SOMENTE
da variável de ambiente indicada em config/settings.json
(github.token_env). Nenhum segredo é guardado no projeto.
"""

import os
import re

from milk.core.settings import obter
from milk.tools import ErroFerramenta, certo, falhou
from milk.tools.http import buscar_json


SERVICO = "GitHub"

URL_BASE = "https://api.github.com"


def token():
    """Token opcional, sempre vindo do ambiente."""

    nome = obter(
        "github",
        "token_env",
        "MILK_GITHUB_TOKEN"
    )

    valor = os.environ.get(nome, "").strip()

    return valor or None


def cabecalhos():
    dados = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    chave = token()

    if chave:
        dados["Authorization"] = f"Bearer {chave}"

    return dados


def consultar(caminho, parametros=None):
    return buscar_json(
        f"{URL_BASE}{caminho}",
        parametros,
        cabecalhos=cabecalhos(),
        servico=SERVICO,
    )


def separar_nome(termo):
    """Aceita 'dono/repo' ou uma URL do GitHub."""

    texto = str(termo or "").strip().strip("<>\"'")

    texto = re.sub(
        r"^https?://(?:www\.)?github\.com/",
        "",
        texto,
        flags=re.IGNORECASE
    )

    texto = texto.strip("/")

    achado = re.match(
        r"^([\w.-]+)/([\w.-]+?)(?:\.git)?$",
        texto
    )

    if not achado:
        return None

    return f"{achado.group(1)}/{achado.group(2)}"


def procurar_repositorio(termo):
    """Quando não veio 'dono/repo', busca o mais popular do nome."""

    dados = consultar(
        "/search/repositories",
        {
            "q": termo,
            "sort": "stars",
            "order": "desc",
            "per_page": 1,
        },
    )

    achados = dados.get("items") or []

    if not achados:
        raise ErroFerramenta(
            f"Não achei nenhum repositório chamado {termo}."
        )

    return achados[0]


def buscar_dados(termo):
    """Dados crus do repositório, por nome completo ou por busca."""

    completo = separar_nome(termo)

    if completo:
        return consultar(f"/repos/{completo}")

    return procurar_repositorio(termo)


def descrever_repositorio(termo):
    """Informações básicas de um repositório público."""

    try:
        dados = buscar_dados(termo)

    except ErroFerramenta as erro:
        if erro.codigo == 404:
            return falhou(
                f"Não achei o repositório {termo} no GitHub."
            )

        return falhou(erro.mensagem)

    nome = dados.get("full_name") or termo

    descricao = (dados.get("description") or "").strip()

    frase = f"O repositório {nome}"

    if descricao:
        frase += f" é assim: {descricao.rstrip('.')}."
    else:
        frase += " existe, mas está sem descrição."

    linguagem = dados.get("language")

    if linguagem:
        frase += f" A linguagem principal é {linguagem}."

    estrelas = dados.get("stargazers_count")

    if isinstance(estrelas, int):
        frase += f" Tem {estrelas} estrelas"

        abertas = dados.get("open_issues_count")

        if isinstance(abertas, int):
            frase += f" e {abertas} questões abertas"

        frase += "."

    if dados.get("archived"):
        frase += " Ele está arquivado."

    return certo(
        frase,
        {
            "nome": nome,
            "descricao": descricao,
            "linguagem": linguagem,
            "estrelas": estrelas,
            "questoes_abertas": dados.get("open_issues_count"),
            "url": dados.get("html_url"),
        },
    )


def commits_recentes(termo, limite=3):
    """Últimos commits de um repositório público."""

    try:
        dados = buscar_dados(termo)

        nome = dados.get("full_name")

        if not nome:
            raise ErroFerramenta(
                f"Não achei o repositório {termo} no GitHub."
            )

        commits = consultar(
            f"/repos/{nome}/commits",
            {"per_page": max(1, min(int(limite), 5))},
        )

    except ErroFerramenta as erro:
        if erro.codigo == 404:
            return falhou(
                f"Não achei o repositório {termo} no GitHub."
            )

        return falhou(erro.mensagem)

    if not isinstance(commits, list) or not commits:
        return falhou(
            f"O repositório {nome} está sem commits para mostrar."
        )

    linhas = []
    lista = []

    for item in commits:
        conteudo = item.get("commit") or {}

        mensagem = (conteudo.get("message") or "").strip()

        mensagem = mensagem.splitlines()[0] if mensagem else "sem título"

        autor = (
            (conteudo.get("author") or {}).get("name")
            or
            "alguém"
        )

        linhas.append(f"{mensagem}, por {autor}")

        lista.append({
            "mensagem": mensagem,
            "autor": autor,
            "data": (conteudo.get("author") or {}).get("date"),
        })

    frase = (
        f"Os commits mais recentes de {nome} são: "
        + "; ".join(linhas)
        + "."
    )

    return certo(
        frase,
        {
            "nome": nome,
            "commits": lista,
        },
    )
