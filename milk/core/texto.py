# Milk — assistente pessoal.
# Copyright (c) 2026 Thales Teracin. Todos os direitos reservados.
#
# Software proprietário. É proibida a cópia, a distribuição, a
# modificação e a engenharia reversa, no todo ou em parte, sem
# autorização expressa e por escrito do autor. Ver LICENSE.txt.

"""Funções de texto usadas pela conversa e pela voz."""

import re
import html


COMANDOS_PARAR = {
    "pare",
    "para",
    "pode parar",
    "para de falar",
    "pare de falar",
    "chega",
    "silencio",
    "silêncio",
    "quieta",
}


def e_comando_parar(texto):
    limpo = texto.strip().lower()

    limpo = re.sub(
        r"[.!?,;:]+$",
        "",
        limpo
    )

    return limpo in COMANDOS_PARAR


def formatar_chat(remetente, texto):
    corpo = html.escape(
        texto
    ).replace(
        "\n",
        "<br>"
    )

    return f"<b>{remetente}:</b> {corpo}"


def limpar_para_voz(texto):
    texto = re.sub(
        r"```.*?```",
        " ",
        texto,
        flags=re.DOTALL
    )

    texto = re.sub(
        r"`([^`]*)`",
        r"\1",
        texto
    )

    texto = re.sub(
        r"https?://\S+",
        "link",
        texto
    )

    texto = texto.replace("#", "")
    texto = texto.replace("*", "")
    texto = texto.replace("_", "")

    texto = re.sub(
        r"\s+",
        " ",
        texto
    )

    if len(texto) > 1200:
        texto = texto[:1200]
        texto += (
            ". A resposta completa está escrita "
            "na janela."
        )

    return texto.strip()

