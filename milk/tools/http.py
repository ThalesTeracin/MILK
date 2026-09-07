# Milk — assistente pessoal.
# Copyright (c) 2026 Thales Teracin. Todos os direitos reservados.
#
# Software proprietário. É proibida a cópia, a distribuição, a
# modificação e a engenharia reversa, no todo ou em parte, sem
# autorização expressa e por escrito do autor. Ver LICENSE.txt.

"""Cliente HTTP compartilhado pelas ferramentas.

Só urllib da biblioteca padrão: o projeto não ganha dependência nova.
Aqui ficam timeout, User-Agent, leitura de JSON e tradução de falha em
mensagem de gente.
"""

import json
import socket
import urllib.error
import urllib.parse
import urllib.request

from milk.core.settings import obter
from milk.tools import ErroFerramenta


def timeout_padrao():
    return obter(
        "http",
        "timeout_segundos",
        10
    )


def user_agent():
    return obter(
        "http",
        "user_agent",
        "MilkAssistente/1.0"
    )


def montar_url(url, parametros=None):
    if not parametros:
        return url

    limpos = {
        chave: valor
        for chave, valor in parametros.items()
        if valor is not None
    }

    if not limpos:
        return url

    separador = "&" if "?" in url else "?"

    return url + separador + urllib.parse.urlencode(
        limpos
    )


def buscar_json(
    url,
    parametros=None,
    cabecalhos=None,
    timeout=None,
    servico="serviço",
):
    """Faz um GET e devolve o JSON.

    Levanta ErroFerramenta com mensagem pronta em qualquer falha. O
    código HTTP fica em `erro.codigo` para quem precisar tratar um 404
    de forma especial."""

    endereco = montar_url(
        url,
        parametros
    )

    cabecalhos_finais = {
        "User-Agent": user_agent(),
        "Accept": "application/json",
    }

    if cabecalhos:
        cabecalhos_finais.update(cabecalhos)

    pedido = urllib.request.Request(
        endereco,
        headers=cabecalhos_finais,
        method="GET",
    )

    try:
        with urllib.request.urlopen(
            pedido,
            timeout=timeout or timeout_padrao()
        ) as resposta:

            corpo = resposta.read()

    except urllib.error.HTTPError as exc:
        raise ErroFerramenta(
            mensagem_do_codigo(
                exc.code,
                servico
            ),
            codigo=exc.code,
        )

    except urllib.error.URLError as exc:
        raise ErroFerramenta(
            f"Não consegui falar com o {servico} agora. "
            f"Pode ser a internet. ({motivo_curto(exc)})"
        )

    except socket.timeout:
        raise ErroFerramenta(
            f"O {servico} demorou demais para responder."
        )

    except Exception as exc:
        raise ErroFerramenta(
            f"Deu problema ao consultar o {servico}: {exc}"
        )

    if not corpo:
        raise ErroFerramenta(
            f"O {servico} respondeu vazio."
        )

    try:
        return json.loads(
            corpo.decode("utf-8", errors="replace")
        )

    except ValueError:
        raise ErroFerramenta(
            f"O {servico} respondeu em um formato que eu não entendi."
        )


def motivo_curto(exc):
    motivo = getattr(exc, "reason", None)

    if isinstance(motivo, socket.timeout):
        return "demorou demais"

    texto = str(motivo or exc).strip()

    return texto[:80] or "sem detalhes"


def mensagem_do_codigo(codigo, servico):
    if codigo == 404:
        return f"O {servico} não encontrou o que eu procurei."

    if codigo in (401, 403):
        return (
            f"O {servico} não me deixou consultar agora. "
            "Pode ser limite de uso."
        )

    if codigo == 429:
        return (
            f"Fiz consultas demais no {servico}. "
            "Espera um pouquinho e pede de novo."
        )

    if codigo >= 500:
        return f"O {servico} está fora do ar no momento."

    return f"O {servico} recusou a consulta (código {codigo})."
