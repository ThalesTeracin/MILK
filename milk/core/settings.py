# Milk — assistente pessoal.
# Copyright (c) 2026 Thales Teracin. Todos os direitos reservados.
#
# Software proprietário. É proibida a cópia, a distribuição, a
# modificação e a engenharia reversa, no todo ou em parte, sem
# autorização expressa e por escrito do autor. Ver LICENSE.txt.

"""Leitura de config/settings.json.

O arquivo guarda só configurações. Nada de token, senha ou chave: o
token do GitHub sai de variável de ambiente, nunca daqui.

Se o arquivo sumir ou vier quebrado, a Milk continua funcionando com os
padrões deste módulo.
"""

import json

from milk.core.config import SETTINGS_FILE


PADROES = {
    "http": {
        "timeout_segundos": 10,
        "user_agent": (
            "MilkAssistente/1.0 "
            "(assistente pessoal de desktop; Windows)"
        ),
    },

    "latido": {
        "volume": 0.8,
    },

    "microfone": {
        # Pedaço do nome do aparelho, ou "auto" para ela procurar
        # sozinha uma entrada que esteja captando de verdade.
        "dispositivo": "auto",
        "api": "",
    },

    "clima": {
        "cidade_padrao": "São Paulo",
        "latitude_padrao": -23.5505,
        "longitude_padrao": -46.6333,
        "fuso": "America/Sao_Paulo",
    },

    "moedas": {
        "origem_padrao": "USD",
        "destino_padrao": "BRL",
    },

    "feriados": {
        "pais_padrao": "BR",
        "quantidade_padrao": 3,
    },

    "wikipedia": {
        "idioma": "pt",
        "frases_do_resumo": 3,
    },

    "github": {
        "token_env": "MILK_GITHUB_TOKEN",
    },

    "localizacao": {
        "pais_padrao": "Brasil",
        "intervalo_minimo_segundos": 1.0,
    },
}


_cache = None


def _juntar(padrao, lido):
    """Mistura o arquivo com os padrões, sem perder chave nenhuma."""

    resultado = dict(padrao)

    if not isinstance(lido, dict):
        return resultado

    for chave, valor in lido.items():
        if (
            isinstance(valor, dict)
            and
            isinstance(resultado.get(chave), dict)
        ):
            resultado[chave] = _juntar(
                resultado[chave],
                valor
            )
        else:
            resultado[chave] = valor

    return resultado


def carregar():
    """Devolve as configurações, lendo o arquivo só na primeira vez."""

    global _cache

    if _cache is not None:
        return _cache

    lido = {}

    try:
        with open(
            SETTINGS_FILE,
            "r",
            encoding="utf-8"
        ) as arquivo:

            lido = json.load(arquivo)

    except (OSError, ValueError):
        lido = {}

    _cache = _juntar(
        PADROES,
        lido
    )

    return _cache


def recarregar():
    """Esquece o que foi lido e busca o arquivo de novo."""

    global _cache

    _cache = None

    return carregar()


def obter(secao, chave=None, padrao=None):
    """obter('http') devolve a seção; obter('http', 'timeout_segundos')
    devolve o valor, caindo no padrão quando não existe."""

    dados = carregar().get(secao)

    if not isinstance(dados, dict):
        return padrao if chave else {}

    if chave is None:
        return dados

    valor = dados.get(chave)

    if valor is None:
        return padrao

    return valor
