# Milk — assistente pessoal.
# Copyright (c) 2026 Thales Teracin. Todos os direitos reservados.
#
# Software proprietário. É proibida a cópia, a distribuição, a
# modificação e a engenharia reversa, no todo ou em parte, sem
# autorização expressa e por escrito do autor. Ver LICENSE.txt.

"""Conversa curta, respondida na hora.

"Oi", "tudo bem?", "obrigado", "você está aí?" — nada disso precisa de
raciocínio. Antes tudo isso descia para o Claude, e cada uma dessas
frases custava **seis segundos só para o processo abrir**, medidos nesta
máquina, antes mesmo de o modelo começar a pensar. Numa demonstração
essa espera é a diferença entre um bicho vivo e um programa travado.

Aqui a resposta sai em milissegundos, sem rede e sem processo novo.

A regra é estreita de propósito: **a frase inteira** precisa ser
conversa curta. "Bom dia, abra o navegador" não cai aqui — tem trabalho
dentro, e trabalho continua sendo com o Claude.
"""

import re
import random


def _qualquer(frases, pessoa=None):
    """Uma das frases, sorteada, com o nome de quem está falando.

    Repetir sempre a mesma resposta é o que faz um assistente soar
    gravado. Sorteia-se entre poucas, todas curtas."""

    frase = random.choice(frases)

    if "{nome}" not in frase:
        return frase

    if not pessoa:
        return frase.replace(" {nome}", "").replace("{nome}", "")

    return frase.replace("{nome}", str(pessoa))


# ============================================================
# CHAMARAM SÓ O NOME
# ============================================================

ATENDER = (
    "Oi! Pode falar.",
    "Oi, {nome}! Estou aqui.",
    "Tô aqui! Pode mandar.",
    "Oi! Diga.",
)


def atender_ao_nome(pessoa=None):
    """O que ela responde quando chamam "Milk" e mais nada.

    O latido já saiu antes desta frase, na hora do chamado."""

    return _qualquer(ATENDER, pessoa)


# ============================================================
# ENQUANTO O TRABALHO NÃO VOLTA
# ============================================================

ESPERA = (
    "Deixa comigo, já te falo.",
    "Tá bom, vou ver isso agora.",
    "Já vou olhar!",
    "Peraí que eu já te respondo.",
)


def espera_pelo_trabalho():
    """A frase curta que ela diz antes de sumir por alguns segundos."""

    return random.choice(ESPERA)


# ============================================================
# AS FRASES QUE NÃO PRECISAM DE RACIOCÍNIO
# ============================================================

# Cada padrão precisa casar com a frase inteira (`fullmatch`), sem o que
# "oi, me escreve um programa" seria respondido com "oi!".

SAUDACAO = re.compile(
    r"(?:oi+|ol[áa]|al[ôo]|e a[íi]|eae|opa|hey|hi|hello|salve)"
    r"[\s,!.]*(?:milk)?[\s,!.]*"
    r"(?:tudo\s+(?:bem|bom|certo|joia|j[óo]ia))?[\s,!?.]*",
    re.IGNORECASE
)

BOM_DIA = re.compile(
    r"(?:bom\s+dia|boa\s+tarde|boa\s+noite)"
    r"[\s,!.]*(?:milk)?[\s,!.]*"
    r"(?:tudo\s+(?:bem|bom|certo))?[\s,!?.]*",
    re.IGNORECASE
)

COMO_VAI = re.compile(
    r"(?:tudo\s+(?:bem|bom|certo|joia|j[óo]ia)|"
    r"como\s+(?:vai|voc[êe]\s+(?:vai|est[áa]|t[áa])|est[áa]s?|tá|vc\s+t[áa])|"
    r"beleza|de\s+boa|tranquil[ao])"
    r"[\s,!?.]*(?:com\s+voc[êe]|a[íi]|milk)?[\s,!?.]*",
    re.IGNORECASE
)

OBRIGADO = re.compile(
    r"(?:muito\s+)?(?:obrigad[oa]|brigad[oa]|valeu|vlw|"
    r"agrade[çc]o|gratid[ãa]o)"
    r"[\s,!.]*(?:milk|viu|hein|mesmo|demais)?[\s,!.]*",
    re.IGNORECASE
)

ELOGIO = re.compile(
    r"(?:voc[êe]\s+|vc\s+|tu\s+)?"
    r"(?:[ée]\s+)?"
    r"(?:muito\s+|bem\s+|t[ãa]o\s+)?"
    r"(?:boa\s+(?:menina|garota|cachorr(?:a|inha))|linda|fofa|"
    r"esperta|inteligente|incr[íi]vel|maravilhosa|"
    r"(?:te\s+amo)|(?:gosto\s+de\s+voc[êe]))"
    r"[\s,!.]*(?:milk)?[\s,!.]*",
    re.IGNORECASE
)

PRESENCA = re.compile(
    r"(?:voc[êe]|vc|tu)?\s*"
    r"(?:est[áa]|t[áa]|ta|tas)\s*"
    r"(?:a[íi]|acordada|ouvindo|me\s+ouvindo|escutando|me\s+escutando|"
    r"por\s+a[íi]|viva|ligada)"
    r"[\s,!?.]*(?:milk)?[\s,!?.]*",
    re.IGNORECASE
)

DESPEDIDA = re.compile(
    r"(?:tchau|at[ée]\s+(?:logo|mais|breve|amanh[ãa])|falou|fui|"
    r"boa\s+noite\s+ent[ãa]o|xau)"
    r"[\s,!.]*(?:milk)?[\s,!.]*",
    re.IGNORECASE
)


RESPOSTAS = (
    (
        SAUDACAO,
        (
            "Oi, {nome}! 🐾 Que bom te ver.",
            "Oi! Tô por aqui. O que você precisa?",
            "Oi, {nome}! Pode mandar.",
        ),
    ),
    (
        BOM_DIA,
        (
            "Pra você também, {nome}! 🐾",
            "Igualmente! Tô prontinha aqui.",
            "Oi, {nome}! Bom te ouvir.",
        ),
    ),
    (
        COMO_VAI,
        (
            "Tudo ótimo por aqui! E com você, {nome}?",
            "Tô bem, obrigada! Precisa de alguma coisa?",
            "De boa, esperando você me chamar. 🐾",
        ),
    ),
    (
        OBRIGADO,
        (
            "Imagina! 🐾",
            "Por nada, {nome}.",
            "Sempre que precisar.",
        ),
    ),
    (
        ELOGIO,
        (
            "Ai, que bom ouvir isso! 🐾",
            "Obrigada, {nome}! Fico feliz.",
            "Você também, viu? 🐾",
        ),
    ),
    (
        PRESENCA,
        (
            "Tô aqui sim! Ouvindo você.",
            "Estou, {nome}. Pode falar.",
            "Aqui, atenta. 🐾",
        ),
    ),
    (
        DESPEDIDA,
        (
            "Até logo, {nome}! 🐾",
            "Tchau! Me chama quando precisar.",
            "Até! Vou ficar aqui no cantinho.",
        ),
    ),
)


# Frases assim são curtas. Se veio um parágrafo, tem pedido dentro e a
# resposta pronta não serve.
TAMANHO_MAXIMO = 45


def _limpar(texto):
    return str(texto or "").strip()


def responder_conversa(texto, pessoa=None):
    """A resposta pronta para uma conversa curta, ou None."""

    limpo = _limpar(texto)

    if not limpo or len(limpo) > TAMANHO_MAXIMO:
        return None

    for padrao, frases in RESPOSTAS:
        if padrao.fullmatch(limpo):
            return _qualquer(frases, pessoa)

    return None


def rota_conversa(texto, pessoa=None):
    """Devolve a Decisao da conversa curta, ou None.

    É `local=True`: não abre thread e não toca na barra de progresso,
    porque não há nada para esperar."""

    from milk.intelligence.roteador import Decisao

    resposta = responder_conversa(texto, pessoa)

    if resposta is None:
        return None

    return Decisao(
        "conversa",
        "🐾 Respondendo",
        lambda: _pronta(resposta),
        local=True,
    )


def _pronta(resposta):
    from milk.tools import certo

    return certo(resposta)


__all__ = [
    "atender_ao_nome",
    "espera_pelo_trabalho",
    "responder_conversa",
    "rota_conversa",
]
