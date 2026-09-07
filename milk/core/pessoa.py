# Milk — assistente pessoal.
# Copyright (c) 2026 Thales Teracin. Todos os direitos reservados.
#
# Software proprietário. É proibida a cópia, a distribuição, a
# modificação e a engenharia reversa, no todo ou em parte, sem
# autorização expressa e por escrito do autor. Ver LICENSE.txt.

"""Quem está falando com a Milk.

A Milk guarda em disco a última pessoa identificada. Com o dono ela é
direta e íntima; com qualquer outra pessoa ela é mais cordial.
"""

import os
import re
import json

from milk.core.config import (
    PESSOA_FILE,
    DONO_NOME,
)


ARTIGO = r"(?:(?:o|a)\s+)?"

NOME = r"([A-Za-zÀ-ÿ]+)"

PADROES_NOME = [
    r"\b(?:eu\s+)?sou\s+" + ARTIGO + NOME,
    r"\bmeu\s+nome\s+(?:é|e)\s+" + ARTIGO + NOME,
    r"\bme\s+chamo\s+" + ARTIGO + NOME,
    r"\baqui\s+(?:é|e)\s+" + ARTIGO + NOME,
    r"\bquem\s+fala\s+(?:é|e)\s+" + ARTIGO + NOME,
    r"\b(?:pode\s+)?me\s+cham(?:ar|a)\s+de\s+" + NOME,
]

PALAVRAS_NAO_NOME = {
    "eu",
    "voce",
    "você",
    "milk",
    "seu",
    "sua",
    "dono",
    "dona",
    "um",
    "uma",
    "o",
    "a",
    "que",
    "so",
    "só",
    "aqui",
    "bem",
    "mal",
    "isso",
    "nada",
    "cansado",
    "cansada",
    "sou",
    "meu",
    "minha",
    "nome",
    "chamar",
    "chama",
    "fala",
    "falando",
    "sim",
    "nao",
    "não",
    "oi",
    "ola",
    "olá",

    # Palavra de comando não é nome de gente. Na sessão de 05/09/2026
    # ela perguntou "com quem eu estou falando?", ouviu "Fechar" no meio
    # de "fechar navegador" e passou a chamar o dono de "Fechar".
    "abre",
    "abra",
    "abrir",
    "fecha",
    "feche",
    "fechar",
    "para",
    "pare",
    "parar",
    "continua",
    "continue",
    "espera",
    "escuta",
    "escute",
    "responde",
    "responda",
    "procura",
    "procure",
    "mostra",
    "mostre",
    "navegador",
    "chrome",
    "janela",
    "teste",
    "testando",
    "obrigado",
    "obrigada",
    "valeu",
    "tchau",
    "certo",
    "beleza",
    "pronto",
    "pronta",
    "agora",
    "depois",
    "amanha",
    "amanhã",
    "hoje",
    "ontem",
}


def normalizar(nome):
    return (
        nome or ""
    ).strip().strip(".,!?;:").lower()


def e_dono(nome):
    return (
        normalizar(nome)
        ==
        normalizar(DONO_NOME)
    )


def carregar_pessoa():
    """Devolve o nome guardado em disco, ou None se ainda não sabemos."""

    if not os.path.exists(PESSOA_FILE):
        return None

    try:
        with open(
            PESSOA_FILE,
            "r",
            encoding="utf-8"
        ) as arquivo:

            dados = json.load(arquivo)

    except (OSError, ValueError):
        return None

    nome = (
        dados.get("nome")
        if isinstance(dados, dict)
        else None
    )

    if not nome or not str(nome).strip():
        return None

    return str(nome).strip()


def salvar_pessoa(nome):
    """Guarda o nome em disco. Falha de escrita não derruba a Milk."""

    nome = (nome or "").strip()

    if not nome:
        return False

    try:
        with open(
            PESSOA_FILE,
            "w",
            encoding="utf-8"
        ) as arquivo:

            json.dump(
                {"nome": nome},
                arquivo,
                ensure_ascii=False
            )

        return True

    except OSError:
        return False


def detectar_nome(texto):
    """Procura uma apresentação: 'sou o Thales', 'meu nome é Ana'.

    Devolve o nome com a primeira letra maiúscula, ou None."""

    if not texto:
        return None

    for padrao in PADROES_NOME:
        achado = re.search(
            padrao,
            texto.strip(),
            flags=re.IGNORECASE
        )

        if not achado:
            continue

        nome = achado.group(1).strip()

        if normalizar(nome) in PALAVRAS_NAO_NOME:
            continue

        if len(nome) < 2:
            continue

        return nome.capitalize()

    return None


def nome_avulso(texto):
    """Aceita a resposta curta a 'com quem eu estou falando?'.

    Só considera nome quando o texto tem no máximo três palavras e,
    havendo mais de uma, todas começam com maiúscula."""

    if not texto:
        return None

    partes = texto.strip().strip(".,!?;:").split()

    if not partes or len(partes) > 3:
        return None

    if len(partes) > 1 and normalizar(partes[0]) in {"o", "a"}:
        partes = partes[1:]

    if not all(
        re.fullmatch(r"[A-Za-zÀ-ÿ]{2,}", parte)
        for parte in partes
    ):
        return None

    if len(partes) > 1 and not all(
        parte[:1].isupper()
        for parte in partes
    ):
        return None

    nome = partes[0]

    if normalizar(nome) in PALAVRAS_NAO_NOME:
        return None

    return nome.capitalize()


def identificar(texto):
    """Nome dito de forma explícita, ou resposta curta com o nome."""

    return (
        detectar_nome(texto)
        or
        nome_avulso(texto)
    )
