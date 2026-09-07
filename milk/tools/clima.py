# Milk — assistente pessoal.
# Copyright (c) 2026 Thales Teracin. Todos os direitos reservados.
#
# Software proprietário. É proibida a cópia, a distribuição, a
# modificação e a engenharia reversa, no todo ou em parte, sem
# autorização expressa e por escrito do autor. Ver LICENSE.txt.

"""Previsão do tempo pelo Open-Meteo.

Sem chave de API. A busca da cidade usa o geocoding do próprio
Open-Meteo; quando nenhuma cidade é dita, vale a do settings.json.
"""

from milk.core.settings import obter
from milk.tools import ErroFerramenta, certo, falhou
from milk.tools.http import buscar_json


SERVICO = "serviço de previsão do tempo"

URL_GEO = "https://geocoding-api.open-meteo.com/v1/search"
URL_PREVISAO = "https://api.open-meteo.com/v1/forecast"


# Códigos WMO devolvidos pelo Open-Meteo.
CONDICOES = {
    0: "céu limpo",
    1: "quase sem nuvens",
    2: "parcialmente nublado",
    3: "nublado",
    45: "com névoa",
    48: "com névoa congelante",
    51: "com garoa fraca",
    53: "com garoa",
    55: "com garoa forte",
    56: "com garoa congelante",
    57: "com garoa congelante forte",
    61: "com chuva fraca",
    63: "com chuva",
    65: "com chuva forte",
    66: "com chuva congelante",
    67: "com chuva congelante forte",
    71: "com neve fraca",
    73: "com neve",
    75: "com neve forte",
    77: "com grãos de neve",
    80: "com pancadas de chuva",
    81: "com pancadas de chuva fortes",
    82: "com pancadas de chuva muito fortes",
    85: "com pancadas de neve",
    86: "com pancadas de neve fortes",
    95: "com temporal",
    96: "com temporal e granizo",
    99: "com temporal forte e granizo",
}


def descrever(codigo):
    return CONDICOES.get(
        codigo,
        "com tempo instável"
    )


def arredondar(valor):
    try:
        return int(round(float(valor)))

    except (TypeError, ValueError):
        return None


def achar_cidade(cidade):
    """Descobre latitude e longitude. Sem cidade, usa a do settings."""

    if not cidade or not cidade.strip():
        return {
            "nome": obter("clima", "cidade_padrao", "São Paulo"),
            "latitude": obter("clima", "latitude_padrao", -23.5505),
            "longitude": obter("clima", "longitude_padrao", -46.6333),
        }

    dados = buscar_json(
        URL_GEO,
        {
            "name": cidade.strip(),
            "count": 1,
            "language": "pt",
            "format": "json",
        },
        servico=SERVICO,
    )

    achados = dados.get("results") or []

    if not achados:
        raise ErroFerramenta(
            f"Não achei nenhuma cidade chamada {cidade.strip()}."
        )

    primeiro = achados[0]

    partes = [primeiro.get("name")]

    if primeiro.get("admin1"):
        partes.append(primeiro["admin1"])

    return {
        "nome": ", ".join(
            parte
            for parte in partes
            if parte
        ),
        "latitude": primeiro.get("latitude"),
        "longitude": primeiro.get("longitude"),
    }


def buscar_previsao(lugar):
    return buscar_json(
        URL_PREVISAO,
        {
            "latitude": lugar["latitude"],
            "longitude": lugar["longitude"],
            "current": (
                "temperature_2m,apparent_temperature,"
                "precipitation,weather_code"
            ),
            "daily": (
                "weather_code,temperature_2m_max,temperature_2m_min,"
                "precipitation_probability_max,precipitation_sum"
            ),
            "timezone": obter(
                "clima",
                "fuso",
                "America/Sao_Paulo"
            ),
            "forecast_days": 2,
        },
        servico=SERVICO,
    )


def clima_agora(cidade=None):
    """Temperatura, sensação e condição do tempo neste momento."""

    try:
        lugar = achar_cidade(cidade)
        dados = buscar_previsao(lugar)

    except ErroFerramenta as erro:
        return falhou(erro.mensagem)

    agora = dados.get("current") or {}

    temperatura = arredondar(
        agora.get("temperature_2m")
    )

    sensacao = arredondar(
        agora.get("apparent_temperature")
    )

    condicao = descrever(
        agora.get("weather_code")
    )

    if temperatura is None:
        return falhou(
            "A previsão veio incompleta agora."
        )

    frase = (
        f"Em {lugar['nome']} estão {temperatura} graus, {condicao}."
    )

    if sensacao is not None and abs(sensacao - temperatura) >= 2:
        frase += f" A sensação é de {sensacao} graus."

    chuva = agora.get("precipitation")

    if chuva:
        frase += " Está chovendo neste momento."

    return certo(
        frase,
        {
            "cidade": lugar["nome"],
            "temperatura": temperatura,
            "sensacao": sensacao,
            "condicao": condicao,
        },
    )


def temperatura_agora(cidade=None):
    """Só a temperatura, em uma frase curta."""

    resposta = clima_agora(cidade)

    if not resposta.ok:
        return resposta

    return certo(
        f"Em {resposta.dados['cidade']} estão "
        f"{resposta.dados['temperatura']} graus agora.",
        resposta.dados,
    )


def previsao_amanha(cidade=None):
    """Máxima, mínima, condição e chance de chuva para amanhã."""

    try:
        lugar = achar_cidade(cidade)
        dados = buscar_previsao(lugar)

    except ErroFerramenta as erro:
        return falhou(erro.mensagem)

    diario = dados.get("daily") or {}

    def amanha(campo):
        valores = diario.get(campo) or []

        return valores[1] if len(valores) > 1 else None

    maxima = arredondar(
        amanha("temperature_2m_max")
    )

    minima = arredondar(
        amanha("temperature_2m_min")
    )

    if maxima is None or minima is None:
        return falhou(
            "Não recebi a previsão de amanhã completa."
        )

    condicao = descrever(
        amanha("weather_code")
    )

    chance = arredondar(
        amanha("precipitation_probability_max")
    )

    frase = (
        f"Amanhã em {lugar['nome']} a mínima é de {minima} graus e a "
        f"máxima de {maxima}, {condicao}."
    )

    if chance is not None:
        frase += f" A chance de chuva é de {chance} por cento."

    return certo(
        frase,
        {
            "cidade": lugar["nome"],
            "maxima": maxima,
            "minima": minima,
            "condicao": condicao,
            "chance_de_chuva": chance,
        },
    )


def vai_chover(cidade=None, quando="amanha"):
    """Responde direto se vai chover hoje ou amanhã."""

    try:
        lugar = achar_cidade(cidade)
        dados = buscar_previsao(lugar)

    except ErroFerramenta as erro:
        return falhou(erro.mensagem)

    diario = dados.get("daily") or {}

    posicao = 1 if quando == "amanha" else 0

    chances = diario.get("precipitation_probability_max") or []

    if len(chances) <= posicao:
        return falhou(
            "Não recebi a chance de chuva dessa data."
        )

    chance = arredondar(
        chances[posicao]
    )

    dia = "amanhã" if posicao else "hoje"

    if chance is None:
        return falhou(
            "Não recebi a chance de chuva dessa data."
        )

    if chance >= 70:
        veredito = "Sim, é bem provável que chova"

    elif chance >= 40:
        veredito = "Pode chover"

    elif chance >= 20:
        veredito = "A chance é pequena"

    else:
        veredito = "Não, não deve chover"

    return certo(
        f"{veredito} {dia} em {lugar['nome']}. "
        f"A chance é de {chance} por cento.",
        {
            "cidade": lugar["nome"],
            "quando": dia,
            "chance_de_chuva": chance,
        },
    )
