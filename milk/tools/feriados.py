# Milk — assistente pessoal.
# Copyright (c) 2026 Thales Teracin. Todos os direitos reservados.
#
# Software proprietário. É proibida a cópia, a distribuição, a
# modificação e a engenharia reversa, no todo ou em parte, sem
# autorização expressa e por escrito do autor. Ver LICENSE.txt.

"""Feriados por país e ano, pelo Nager.Date.

Para o Brasil, a BrasilAPI entra como reserva quando o Nager.Date não
responde. As datas são escritas por extenso aqui mesmo, sem depender de
locale do Windows.
"""

import datetime

from milk.core.settings import obter
from milk.tools import ErroFerramenta, certo, falhou
from milk.tools.http import buscar_json
from milk.tools import brasil_api


SERVICO = "Nager.Date"

URL_BASE = "https://date.nager.at/api/v3"


MESES = [
    "janeiro",
    "fevereiro",
    "março",
    "abril",
    "maio",
    "junho",
    "julho",
    "agosto",
    "setembro",
    "outubro",
    "novembro",
    "dezembro",
]

DIAS = [
    "segunda-feira",
    "terça-feira",
    "quarta-feira",
    "quinta-feira",
    "sexta-feira",
    "sábado",
    "domingo",
]


def pais_padrao():
    return obter(
        "feriados",
        "pais_padrao",
        "BR"
    )


def para_data(texto):
    try:
        return datetime.date.fromisoformat(
            str(texto)[:10]
        )

    except (TypeError, ValueError):
        return None


def por_extenso(data):
    """2026-10-12 vira 'segunda-feira, 12 de outubro'."""

    return (
        f"{DIAS[data.weekday()]}, "
        f"{data.day} de {MESES[data.month - 1]}"
    )


def consultar_nager(ano, pais):
    dados = buscar_json(
        f"{URL_BASE}/PublicHolidays/{ano}/{pais}",
        servico=SERVICO,
    )

    if not isinstance(dados, list):
        raise ErroFerramenta(
            "A lista de feriados veio em um formato inesperado."
        )

    return [
        {
            "data": item.get("date"),
            "nome": item.get("localName") or item.get("name"),
            "tipo": None,
            "fonte": SERVICO,
        }
        for item in dados
        if item.get("date")
    ]


def buscar_lista(ano, pais=None):
    """Lista crua de feriados, com a BrasilAPI de reserva no Brasil."""

    pais = (pais or pais_padrao()).upper()

    try:
        return consultar_nager(ano, pais)

    except ErroFerramenta as erro:
        if pais != "BR":
            raise

        try:
            return brasil_api.feriados(ano)

        except ErroFerramenta:
            raise erro


def feriados_do_ano(ano=None, pais=None):
    """Todos os feriados de um ano."""

    ano = ano or datetime.date.today().year

    try:
        lista = buscar_lista(ano, pais)

    except ErroFerramenta as erro:
        return falhou(erro.mensagem)

    if not lista:
        return falhou(
            f"Não achei feriados de {ano}."
        )

    nomes = []

    for item in lista:
        data = para_data(item["data"])

        if not data:
            continue

        nomes.append(
            f"{data.day} de {MESES[data.month - 1]}, {item['nome']}"
        )

    return certo(
        f"Em {ano} são {len(nomes)} feriados: "
        + "; ".join(nomes)
        + ".",
        {
            "ano": ano,
            "feriados": lista,
        },
    )


def proximos_feriados(quantidade=None, pais=None):
    """Os próximos feriados a partir de hoje, virando o ano se faltar."""

    quantidade = quantidade or obter(
        "feriados",
        "quantidade_padrao",
        3
    )

    hoje = datetime.date.today()

    try:
        lista = buscar_lista(hoje.year, pais)

        futuros = [
            item
            for item in lista
            if (para_data(item["data"]) or hoje) >= hoje
        ]

        if len(futuros) < quantidade:
            futuros += buscar_lista(hoje.year + 1, pais)

    except ErroFerramenta as erro:
        return falhou(erro.mensagem)

    futuros = [
        item
        for item in futuros
        if para_data(item["data"])
    ]

    futuros.sort(
        key=lambda item: para_data(item["data"])
    )

    escolhidos = futuros[:quantidade]

    if not escolhidos:
        return falhou(
            "Não achei os próximos feriados agora."
        )

    linhas = []

    for item in escolhidos:
        data = para_data(item["data"])

        faltam = (data - hoje).days

        if faltam == 0:
            quando = "é hoje"

        elif faltam == 1:
            quando = "é amanhã"

        else:
            quando = f"faltam {faltam} dias"

        linhas.append(
            f"{item['nome']}, {por_extenso(data)}, {quando}"
        )

    titulo = (
        "O próximo feriado é"
        if len(linhas) == 1
        else f"Os próximos {len(linhas)} feriados são"
    )

    return certo(
        f"{titulo}: "
        + "; ".join(linhas)
        + ".",
        {
            "feriados": escolhidos,
        },
    )
