# Milk — assistente pessoal.
# Copyright (c) 2026 Thales Teracin. Todos os direitos reservados.
#
# Software proprietário. É proibida a cópia, a distribuição, a
# modificação e a engenharia reversa, no todo ou em parte, sem
# autorização expressa e por escrito do autor. Ver LICENSE.txt.

"""Camada da BrasilAPI.

Fica separada de propósito, para receber as próximas consultas
brasileiras (banco, DDD, tabela FIPE) sem mexer no resto.

Hoje ela é a reserva: `cep.py` tenta o ViaCEP primeiro e `feriados.py`
tenta o Nager.Date primeiro. Aqui só existem as chamadas cruas, sem
entrada própria para o usuário, para não duplicar ferramenta.
"""

import re

from milk.tools import ErroFerramenta
from milk.tools.http import buscar_json


SERVICO = "BrasilAPI"

URL_BASE = "https://brasilapi.com.br/api"


def somente_digitos(texto):
    return re.sub(
        r"\D",
        "",
        str(texto or "")
    )


def cep(codigo):
    """Endereço de um CEP, no mesmo formato que o cep.py usa."""

    numero = somente_digitos(codigo)

    if len(numero) != 8:
        raise ErroFerramenta(
            "Esse CEP não tem oito números."
        )

    dados = buscar_json(
        f"{URL_BASE}/cep/v2/{numero}",
        servico=SERVICO,
    )

    return {
        "cep": dados.get("cep") or numero,
        "logradouro": dados.get("street") or "",
        "bairro": dados.get("neighborhood") or "",
        "cidade": dados.get("city") or "",
        "estado": dados.get("state") or "",
        "fonte": "BrasilAPI",
    }


def feriados(ano):
    """Feriados nacionais de um ano, já normalizados."""

    try:
        ano = int(ano)

    except (TypeError, ValueError):
        raise ErroFerramenta(
            "Não entendi de que ano você quer os feriados."
        )

    dados = buscar_json(
        f"{URL_BASE}/feriados/v1/{ano}",
        servico=SERVICO,
    )

    if not isinstance(dados, list):
        raise ErroFerramenta(
            "A lista de feriados veio em um formato inesperado."
        )

    return [
        {
            "data": item.get("date"),
            "nome": item.get("name"),
            "tipo": item.get("type"),
            "fonte": "BrasilAPI",
        }
        for item in dados
        if item.get("date")
    ]
