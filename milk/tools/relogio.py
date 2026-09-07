# Milk — assistente pessoal.
# Copyright (c) 2026 Thales Teracin. Todos os direitos reservados.
#
# Software proprietário. É proibida a cópia, a distribuição, a
# modificação e a engenharia reversa, no todo ou em parte, sem
# autorização expressa e por escrito do autor. Ver LICENSE.txt.

"""Horário e calendário, resolvidos na própria máquina.

Nada aqui usa rede: a fonte é o relógio do Windows. Por isso todas as
funções aceitam `agora` — nos testes entra uma data fixa, no dia a dia
entra `datetime.datetime.now()`.

Os nomes de dia e mês são escritos à mão. O `locale` do Windows não é
confiável para português e mudaria conforme a máquina.
"""

import re
import datetime

from milk.tools import certo, falhou


DIAS = (
    "segunda-feira",
    "terça-feira",
    "quarta-feira",
    "quinta-feira",
    "sexta-feira",
    "sábado",
    "domingo",
)

MESES = (
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
)


# Datas fixas que aparecem em "quantos dias faltam para...".
DATAS_CONHECIDAS = {
    "natal": (25, 12),
    "o natal": (25, 12),
    "ano novo": (1, 1),
    "o ano novo": (1, 1),
    "reveillon": (1, 1),
    "réveillon": (1, 1),
    "o reveillon": (1, 1),
    "o réveillon": (1, 1),
}


def relogio():
    return datetime.datetime.now()


def quando(agora):
    return agora or relogio()


def nome_do_dia(data):
    return DIAS[data.weekday()]


def nome_do_mes(data):
    return MESES[data.month - 1]


def escrever_data(data, com_ano=True):
    """5 de setembro de 2026."""

    texto = f"{data.day} de {nome_do_mes(data)}"

    if com_ano:
        texto += f" de {data.year}"

    return texto


def dados_da_data(data):
    return {
        "dia": data.day,
        "mes": data.month,
        "ano": data.year,
        "dia_da_semana": nome_do_dia(data),
        "iso": data.isoformat()[:10],
    }


# ============================================================
# HORAS
# ============================================================

def escrever_hora(momento):
    """A frase que a Milk fala. Meio-dia e meia-noite têm nome."""

    hora = momento.hour
    minuto = momento.minute

    if hora == 0:
        cabeca = "é meia-noite"

    elif hora == 12:
        cabeca = "é meio-dia"

    elif hora == 1:
        cabeca = "é 1 hora"

    else:
        cabeca = f"são {hora} horas"

    if minuto == 0:
        return f"{cabeca} em ponto"

    if minuto == 1:
        return f"{cabeca} e 1 minuto"

    return f"{cabeca} e {minuto} minutos"


def que_horas(agora=None):
    """'Agora são 14 horas e 32 minutos.'"""

    momento = quando(agora)

    return certo(
        f"Agora {escrever_hora(momento)}.",
        {
            "hora": momento.hour,
            "minuto": momento.minute,
            "iso": momento.isoformat(timespec="minutes"),
        },
    )


# ============================================================
# DATA
# ============================================================

def que_dia_e_hoje(agora=None):
    """'Hoje é sexta-feira, 5 de setembro de 2026.'"""

    hoje = quando(agora).date()

    return certo(
        f"Hoje é {nome_do_dia(hoje)}, {escrever_data(hoje)}.",
        dados_da_data(hoje),
    )


def dia_da_semana(agora=None):
    """'Hoje é sexta-feira.'"""

    hoje = quando(agora).date()

    return certo(
        f"Hoje é {nome_do_dia(hoje)}.",
        dados_da_data(hoje),
    )


def dia_vizinho(deslocamento, agora=None):
    """Amanhã (+1) ou ontem (-1), com o dia da semana junto."""

    data = quando(agora).date() + datetime.timedelta(
        days=deslocamento
    )

    if deslocamento > 0:
        frase = (
            f"Amanhã é {nome_do_dia(data)}, "
            f"{escrever_data(data, com_ano=False)}."
        )

    else:
        frase = (
            f"Ontem foi {nome_do_dia(data)}, "
            f"{escrever_data(data, com_ano=False)}."
        )

    return certo(
        frase,
        dados_da_data(data),
    )


def mes_atual(agora=None):
    """'Estamos em setembro de 2026.'"""

    hoje = quando(agora).date()

    return certo(
        f"Estamos em {nome_do_mes(hoje)} de {hoje.year}.",
        dados_da_data(hoje),
    )


def ano_atual(agora=None):
    """'Estamos em 2026.'"""

    hoje = quando(agora).date()

    return certo(
        f"Estamos em {hoje.year}.",
        dados_da_data(hoje),
    )


# ============================================================
# CONTAGEM DE DIAS
# ============================================================

MES_POR_NOME = {
    nome: numero
    for numero, nome in enumerate(MESES, start=1)
}

# Sem acento também vale: é assim que sai da transcrição às vezes.
MES_POR_NOME["marco"] = 3


DATA_NUMERICA = re.compile(
    r"^(\d{1,2})\s*[/\-\.]\s*(\d{1,2})(?:\s*[/\-\.]\s*(\d{2,4}))?$"
)

DATA_POR_EXTENSO = re.compile(
    r"^(?:o\s+dia\s+|dia\s+)?(\d{1,2})\s+de\s+([a-zà-ÿ]+)"
    r"(?:\s+de\s+(\d{4}))?$",
    re.IGNORECASE
)


def entender_data(texto, agora=None):
    """"25/12", "25 de dezembro" e "o Natal" viram uma data.

    Sem ano dito, vale a próxima ocorrência: se a data já passou neste
    ano, ela cai no ano que vem. Devolve None quando não reconhece — e
    aí o pedido segue para o Claude, como sempre."""

    hoje = quando(agora).date()

    bruto = str(texto or "").strip().strip("?!.,;:").lower()

    bruto = re.sub(r"\s+", " ", bruto)

    if not bruto:
        return None

    dia = mes = ano = None

    if bruto in DATAS_CONHECIDAS:
        dia, mes = DATAS_CONHECIDAS[bruto]

    achado = DATA_NUMERICA.match(bruto)

    if achado:
        dia = int(achado.group(1))
        mes = int(achado.group(2))

        if achado.group(3):
            ano = int(achado.group(3))

            if ano < 100:
                ano += 2000

    achado = DATA_POR_EXTENSO.match(bruto)

    if achado and mes is None:
        nome = achado.group(2)

        if nome in MES_POR_NOME:
            dia = int(achado.group(1))
            mes = MES_POR_NOME[nome]

            if achado.group(3):
                ano = int(achado.group(3))

    if dia is None or mes is None:
        return None

    tentativas = [ano] if ano else [hoje.year, hoje.year + 1]

    for candidato in tentativas:
        try:
            data = datetime.date(candidato, mes, dia)

        except ValueError:
            return None

        if ano or data >= hoje:
            return data

    return None


def dias_para(alvo, agora=None):
    """Quantos dias faltam para uma data já entendida."""

    hoje = quando(agora).date()

    if not isinstance(alvo, datetime.date):
        return falhou(
            "Não entendi para que data você quer contar os dias."
        )

    diferenca = (alvo - hoje).days

    escrita = escrever_data(alvo)

    if diferenca == 0:
        return certo(
            f"É hoje mesmo: {escrita}.",
            {
                "dias": 0,
                "iso": alvo.isoformat(),
                "dia_da_semana": nome_do_dia(alvo),
            },
        )

    if diferenca == 1:
        frase = f"Falta 1 dia para {escrita}."

    elif diferenca > 1:
        frase = f"Faltam {diferenca} dias para {escrita}."

    elif diferenca == -1:
        frase = f"{escrita} foi ontem, faz 1 dia."

    else:
        frase = f"{escrita} já passou, faz {abs(diferenca)} dias."

    return certo(
        frase,
        {
            "dias": diferenca,
            "iso": alvo.isoformat(),
            "dia_da_semana": nome_do_dia(alvo),
        },
    )
