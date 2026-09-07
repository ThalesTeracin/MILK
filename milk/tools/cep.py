# Milk — assistente pessoal.
# Copyright (c) 2026 Thales Teracin. Todos os direitos reservados.
#
# Software proprietário. É proibida a cópia, a distribuição, a
# modificação e a engenharia reversa, no todo ou em parte, sem
# autorização expressa e por escrito do autor. Ver LICENSE.txt.

"""Busca de endereço por CEP.

O ViaCEP é o principal. Se ele não responder, a consulta cai para a
BrasilAPI, que já está implementada em brasil_api.py — por isso aqui
não existe uma segunda função de CEP para o usuário.
"""

import re

from milk.tools import ErroFerramenta, certo, falhou
from milk.tools.http import buscar_json
from milk.tools import brasil_api


SERVICO = "ViaCEP"

URL_BASE = "https://viacep.com.br/ws"


def limpar_cep(texto):
    """Tira pontuação e devolve os oito números, ou None."""

    numero = re.sub(
        r"\D",
        "",
        str(texto or "")
    )

    if len(numero) != 8:
        return None

    return numero


def deu_erro(dados):
    """O ViaCEP responde 200 com {"erro": true} quando não acha."""

    if not isinstance(dados, dict):
        return True

    marca = dados.get("erro")

    if isinstance(marca, bool):
        return marca

    return str(marca).strip().lower() == "true"


def consultar_viacep(numero):
    dados = buscar_json(
        f"{URL_BASE}/{numero}/json/",
        servico=SERVICO,
    )

    if deu_erro(dados):
        raise ErroFerramenta(
            "não encontrado",
            codigo=404
        )

    return {
        "cep": dados.get("cep") or numero,
        "logradouro": dados.get("logradouro") or "",
        "bairro": dados.get("bairro") or "",
        "cidade": dados.get("localidade") or "",
        "estado": dados.get("uf") or "",
        "fonte": "ViaCEP",
    }


def formatar(numero):
    return f"{numero[:5]}-{numero[5:]}"


def montar_frase(endereco):
    partes = []

    if endereco["logradouro"]:
        partes.append(endereco["logradouro"])

    if endereco["bairro"]:
        partes.append(f"bairro {endereco['bairro']}")

    lugar = ", ".join(
        parte
        for parte in [
            endereco["cidade"],
            endereco["estado"],
        ]
        if parte
    )

    if lugar:
        partes.append(lugar)

    if not partes:
        return (
            f"O CEP {endereco['cep']} existe, mas veio sem endereço."
        )

    return (
        f"O CEP {endereco['cep']} é "
        + ", ".join(partes)
        + "."
    )


def buscar_cep(codigo):
    """Endereço de um CEP: logradouro, bairro, cidade e estado."""

    numero = limpar_cep(codigo)

    if not numero:
        return falhou(
            "Esse CEP não parece certo. "
            "Ele precisa ter oito números, como 01310-100."
        )

    nao_encontrado = False

    try:
        endereco = consultar_viacep(numero)

    except ErroFerramenta as erro:
        if erro.codigo == 404:
            nao_encontrado = True

        # Serviço fora do ar ou sem resposta: tenta a reserva.
        try:
            endereco = brasil_api.cep(numero)

        except ErroFerramenta as reserva:
            if nao_encontrado or reserva.codigo == 404:
                return falhou(
                    f"Não achei o CEP {formatar(numero)}. "
                    "Confere se o número está certo?"
                )

            return falhou(reserva.mensagem)

    return certo(
        montar_frase(endereco),
        endereco,
    )
