# Milk — assistente pessoal.
# Copyright (c) 2026 Thales Teracin. Todos os direitos reservados.
#
# Software proprietário. É proibida a cópia, a distribuição, a
# modificação e a engenharia reversa, no todo ou em parte, sem
# autorização expressa e por escrito do autor. Ver LICENSE.txt.

"""Busca de lugar e endereço no OpenStreetMap (Nominatim).

A política de uso do Nominatim pede User-Agent identificável e no
máximo um pedido por segundo. As duas coisas são respeitadas aqui: o
User-Agent sai do settings.json e existe uma trava de tempo entre
chamadas. Nada de consulta em massa.
"""

import time
import threading

from milk.core.settings import obter
from milk.tools import ErroFerramenta, certo, falhou
from milk.tools.http import buscar_json


SERVICO = "OpenStreetMap"

URL_BUSCA = "https://nominatim.openstreetmap.org/search"


_tranca = threading.Lock()
_ultimo_pedido = 0.0


def respeitar_limite():
    """Segura a chamada para não passar de um pedido por segundo."""

    global _ultimo_pedido

    intervalo = obter(
        "localizacao",
        "intervalo_minimo_segundos",
        1.0
    )

    with _tranca:
        agora = time.monotonic()

        espera = intervalo - (agora - _ultimo_pedido)

        if espera > 0:
            time.sleep(espera)

        _ultimo_pedido = time.monotonic()


def encurtar_endereco(dados, limite=4):
    """O display_name vem enorme; aqui ele vira uma frase falável."""

    completo = (dados.get("display_name") or "").strip()

    if not completo:
        return ""

    partes = [
        parte.strip()
        for parte in completo.split(",")
        if parte.strip()
    ]

    if len(partes) <= limite:
        return ", ".join(partes)

    # Começo (rua, bairro) e fim (cidade, estado, país).
    return ", ".join(
        partes[:2] + partes[-2:]
    )


# Do mais específico para o mais geral. Um de cada grupo entra na frase.
GRUPOS_DO_ENDERECO = (
    ("road", "pedestrian", "attraction", "building", "amenity", "name"),
    ("suburb", "neighbourhood", "city_district"),
    ("city", "town", "village", "municipality"),
    ("state",),
)


def montar_endereco(lugar):
    """Prefere os campos separados; cai no display_name se não vierem."""

    endereco = lugar.get("address") or {}

    partes = []

    for grupo in GRUPOS_DO_ENDERECO:
        for campo in grupo:
            valor = endereco.get(campo)

            if valor and valor not in partes:
                partes.append(valor)
                break

    if partes:
        return ", ".join(partes)

    return encurtar_endereco(lugar)


def com_maiuscula(texto):
    """Deixa a primeira letra maiúscula sem estragar o resto do nome."""

    return texto[:1].upper() + texto[1:]


def procurar_lugar(termo):
    """Onde fica um endereço, uma rua ou um ponto conhecido."""

    termo = (termo or "").strip().strip("?.!,")

    if len(termo) < 3:
        return falhou(
            "Não entendi que lugar você quer achar."
        )

    pais = obter(
        "localizacao",
        "pais_padrao",
        "Brasil"
    )

    try:
        respeitar_limite()

        dados = buscar_json(
            URL_BUSCA,
            {
                "q": termo,
                "format": "jsonv2",
                "limit": 1,
                "addressdetails": 1,
                "accept-language": "pt-BR",
                "countrycodes": "br" if pais == "Brasil" else None,
            },
            servico=SERVICO,
        )

    except ErroFerramenta as erro:
        return falhou(erro.mensagem)

    if not isinstance(dados, list) or not dados:
        return falhou(
            f"Não achei {termo} no mapa."
        )

    lugar = dados[0]

    endereco = montar_endereco(lugar)

    if not endereco:
        return falhou(
            f"Achei {termo}, mas veio sem endereço."
        )

    return certo(
        f"{com_maiuscula(termo)} fica em {endereco}.",
        {
            "termo": termo,
            "endereco": endereco,
            "endereco_completo": lugar.get("display_name"),
            "latitude": lugar.get("lat"),
            "longitude": lugar.get("lon"),
            "tipo": lugar.get("type"),
        },
    )
