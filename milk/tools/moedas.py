# Milk — assistente pessoal.
# Copyright (c) 2026 Thales Teracin. Todos os direitos reservados.
#
# Software proprietário. É proibida a cópia, a distribuição, a
# modificação e a engenharia reversa, no todo ou em parte, sem
# autorização expressa e por escrito do autor. Ver LICENSE.txt.

"""Conversão de moedas pelo Frankfurter.

Sem chave de API. O endereço novo (frankfurter.dev) é o principal e o
antigo (frankfurter.app) fica como reserva.
"""

import re

from milk.core.settings import obter
from milk.tools import ErroFerramenta, certo, falhou
from milk.tools.http import buscar_json


SERVICO = "serviço de câmbio"

ENDERECOS = [
    "https://api.frankfurter.dev/v1/latest",
    "https://api.frankfurter.app/latest",
]


# Como as pessoas falam, e o código de cada moeda.
NOMES = {
    "real": "BRL",
    "reais": "BRL",
    "brl": "BRL",
    "dolar": "USD",
    "dólar": "USD",
    "dolares": "USD",
    "dólares": "USD",
    "usd": "USD",
    "euro": "EUR",
    "euros": "EUR",
    "eur": "EUR",
    "libra": "GBP",
    "libras": "GBP",
    "gbp": "GBP",
    "iene": "JPY",
    "ienes": "JPY",
    "jpy": "JPY",
    "franco": "CHF",
    "francos": "CHF",
    "chf": "CHF",
    "iuan": "CNY",
    "yuan": "CNY",
    "cny": "CNY",
}

PLURAL = {
    "BRL": "reais",
    "USD": "dólares",
    "EUR": "euros",
    "GBP": "libras",
    "JPY": "ienes",
    "CHF": "francos suíços",
    "CNY": "iuans",
}


def codigo_da_moeda(texto):
    """'dólares' vira USD. Devolve None quando não reconhece."""

    limpo = str(texto or "").strip().lower()

    limpo = re.sub(
        r"[^a-zà-ÿ]",
        "",
        limpo
    )

    if not limpo:
        return None

    if limpo in NOMES:
        return NOMES[limpo]

    if len(limpo) == 3 and limpo.isalpha():
        return limpo.upper()

    return None


def nome_falado(codigo, valor=None):
    nome = PLURAL.get(
        codigo,
        codigo
    )

    if valor is not None and abs(valor - 1) < 1e-9:
        singular = {
            "reais": "real",
            "dólares": "dólar",
            "euros": "euro",
            "libras": "libra",
            "ienes": "iene",
            "iuans": "iuan",
        }

        return singular.get(nome, nome)

    return nome


def numero_bonito(valor):
    """1234.5 vira '1.234,50', no jeito brasileiro."""

    texto = f"{valor:,.2f}"

    return (
        texto
        .replace(",", "#")
        .replace(".", ",")
        .replace("#", ".")
    )


def cotar(origem, destino, timeout=None):
    """Quanto vale 1 unidade da origem, na moeda de destino."""

    ultimo = None

    for endereco in ENDERECOS:
        try:
            dados = buscar_json(
                endereco,
                {
                    "base": origem,
                    "symbols": destino,
                },
                servico=SERVICO,
                timeout=timeout,
            )

        except ErroFerramenta as erro:
            ultimo = erro
            continue

        taxas = dados.get("rates") or {}

        if destino in taxas:
            return {
                "taxa": float(taxas[destino]),
                "data": dados.get("date"),
            }

        ultimo = ErroFerramenta(
            f"Não consigo converter de {origem} para {destino}."
        )

    raise ultimo or ErroFerramenta(
        f"O {SERVICO} não respondeu."
    )


def converter(valor, origem, destino):
    """Converte um valor entre duas moedas. Ex.: 100, USD, BRL."""

    try:
        valor = float(valor)

    except (TypeError, ValueError):
        return falhou(
            "Não entendi o valor que você quer converter."
        )

    codigo_origem = codigo_da_moeda(origem) or str(origem or "").upper()
    codigo_destino = codigo_da_moeda(destino) or str(destino or "").upper()

    if not codigo_origem or not codigo_destino:
        return falhou(
            "Não entendi quais moedas você quer converter."
        )

    if codigo_origem == codigo_destino:
        return certo(
            f"{numero_bonito(valor)} "
            f"{nome_falado(codigo_origem, valor)} continuam sendo "
            f"{numero_bonito(valor)} "
            f"{nome_falado(codigo_destino, valor)}.",
            {
                "valor": valor,
                "origem": codigo_origem,
                "destino": codigo_destino,
                "convertido": valor,
                "taxa": 1.0,
            },
        )

    try:
        cotacao = cotar(
            codigo_origem,
            codigo_destino
        )

    except ErroFerramenta as erro:
        return falhou(erro.mensagem)

    convertido = valor * cotacao["taxa"]

    verbo = "dá" if abs(valor - 1) < 1e-9 else "dão"

    return certo(
        f"{numero_bonito(valor)} "
        f"{nome_falado(codigo_origem, valor)} "
        f"{verbo} {numero_bonito(convertido)} "
        f"{nome_falado(codigo_destino, convertido)}.",
        {
            "valor": valor,
            "origem": codigo_origem,
            "destino": codigo_destino,
            "convertido": convertido,
            "taxa": cotacao["taxa"],
            "data": cotacao["data"],
        },
    )


def cotacao(origem=None, destino=None):
    """Quanto vale uma unidade. Sem argumentos, usa o settings.json."""

    return converter(
        1,
        origem or obter("moedas", "origem_padrao", "USD"),
        destino or obter("moedas", "destino_padrao", "BRL"),
    )
