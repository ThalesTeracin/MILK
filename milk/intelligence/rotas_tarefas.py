# Milk — assistente pessoal.
# Copyright (c) 2026 Thales Teracin. Todos os direitos reservados.
#
# Software proprietário. É proibida a cópia, a distribuição, a
# modificação e a engenharia reversa, no todo ou em parte, sem
# autorização expressa e por escrito do autor. Ver LICENSE.txt.

"""Controle da fila por voz.

São os pedidos sobre o próprio trabalho: "o que você está fazendo",
"quais tarefas estão pendentes", "cancele a próxima", "pause".
Nada disso vai para o Claude — é estado que a Milk já tem na mão.

Mora fora do roteador porque o roteador já está grande e porque este
assunto é outro: lá se decide entre ferramenta e Claude; aqui se
conversa sobre a fila.

Estas rotas são consultadas ANTES do veto do roteador. O veto existe
para mandar trabalho ("faça", "crie") ao Claude, e "faça isso depois" é
justamente um pedido sobre a fila, não trabalho novo.
"""

import re

from milk.tools import certo
from milk.tasks.gerente import gerente
from milk.tasks.modelos import Prioridade


# ============================================================
# O QUE A MILK RESPONDE
# ============================================================

NOME_DA_PRIORIDADE = {
    Prioridade.URGENTE: "urgente",
    Prioridade.ALTA: "prioridade alta",
    Prioridade.BAIXA: "sem pressa",
}


def com_prioridade(tarefa):
    nome = NOME_DA_PRIORIDADE.get(tarefa.prioridade)

    return f"{tarefa.descricao} ({nome})" if nome else tarefa.descricao


def listar(tarefas):
    return "; ".join(
        f"{posicao}. {com_prioridade(tarefa)}"
        for posicao, tarefa in enumerate(tarefas, start=1)
    )


def frase_do_trabalho(g=None):
    """'O que você está fazendo?'"""

    g = g or gerente()

    atual = g.em_andamento()

    if atual is None:
        pendentes = g.pendentes()

        if g.pausada and pendentes:
            return certo(
                f"Estou parada, a fila está pausada. "
                f"Tenho {len(pendentes)} esperando."
            )

        if pendentes:
            return certo(
                "Ainda não comecei. A próxima é: "
                f"{pendentes[0].descricao}."
            )

        return certo(
            "Nada no momento. Estou aqui esperando você."
        )

    frase = f"Estou trabalhando em: {atual.descricao}."

    if atual.progresso:
        frase += f" Agora: {atual.progresso}."

    restantes = len(g.pendentes())

    if restantes:
        frase += (
            f" Tenho mais {restantes} "
            f"{'tarefa' if restantes == 1 else 'tarefas'} na fila."
        )

    return certo(frase)


def frase_das_pendentes(g=None):
    """'Quais tarefas estão pendentes?'"""

    g = g or gerente()

    pendentes = g.pendentes()
    atual = g.em_andamento()

    if not pendentes and atual is None:
        return certo(
            "Não tenho nenhuma tarefa pendente."
        )

    partes = []

    if atual:
        partes.append(
            f"Fazendo agora: {atual.descricao}."
        )

    if pendentes:
        partes.append(
            f"Na fila: {listar(pendentes)}."
        )

    else:
        partes.append(
            "A fila está vazia."
        )

    if g.pausada:
        partes.append(
            "A fila está pausada."
        )

    return certo(" ".join(partes))


def frase_do_progresso(g=None):
    """'Qual o progresso?' — estado textual, nunca porcentagem inventada."""

    g = g or gerente()

    atual = g.em_andamento()

    if atual is None:
        return frase_do_trabalho(g)

    if atual.progresso:
        return certo(
            f"{atual.descricao}: {atual.progresso}."
        )

    return certo(
        f"Ainda estou em {atual.descricao}. "
        "Sem novidade para contar até agora."
    )


def pausar(g=None):
    g = g or gerente()

    g.pausar()

    atual = g.em_andamento()

    if atual:
        return certo(
            "Pausei a fila. Termino o que já comecei e depois espero você."
        )

    return certo(
        "Fila pausada. É só me dizer para continuar."
    )


def continuar(g=None):
    g = g or gerente()

    g.continuar()

    pendentes = g.pendentes()

    if not pendentes:
        return certo(
            "Pode deixar. Não tem nada esperando na fila."
        )

    return certo(
        f"Voltando ao trabalho: {pendentes[0].descricao}."
    )


def cancelar_atual(g=None):
    g = g or gerente()

    atual = g.em_andamento()

    if atual is None:
        return certo(
            "Não estou fazendo nada agora."
        )

    g.cancelar(atual)

    return certo(
        f"Cancelei: {atual.descricao}."
    )


def cancelar_proxima(g=None):
    g = g or gerente()

    tarefa = g.cancelar_proxima()

    if tarefa is None:
        return certo(
            "Não tem nenhuma tarefa esperando na fila."
        )

    return certo(
        f"Tirei da fila: {tarefa.descricao}."
    )


def cancelar_tudo(g=None):
    g = g or gerente()

    canceladas = g.cancelar_pendentes()

    if not canceladas:
        return certo(
            "A fila já estava vazia."
        )

    return certo(
        f"Limpei a fila. Cancelei {len(canceladas)} "
        f"{'tarefa' if len(canceladas) == 1 else 'tarefas'}."
    )


def priorizar(g=None):
    """'Coloque isso como prioridade.'"""

    g = g or gerente()

    pendentes = g.pendentes()

    if not pendentes:
        atual = g.em_andamento()

        if atual:
            return certo(
                f"{atual.descricao} já é o que estou fazendo agora."
            )

        return certo(
            "Não tem nada na fila para priorizar."
        )

    # "Isso" é o pedido mais recente que ainda não começou.
    alvo = max(
        pendentes,
        key=lambda tarefa: g.tarefas.index(tarefa)
    )

    g.priorizar(alvo, Prioridade.URGENTE)

    return certo(
        f"Marquei como urgente: {alvo.descricao}. É a próxima."
    )


def adiar(g=None):
    """'Faça isso depois.'"""

    g = g or gerente()

    pendentes = g.pendentes()

    if not pendentes:
        return certo(
            "Não tem nada na fila para deixar para depois."
        )

    alvo = max(
        pendentes,
        key=lambda tarefa: g.tarefas.index(tarefa)
    )

    g.adiar(alvo)

    return certo(
        f"Deixei para depois: {alvo.descricao}."
    )


def repetir_ultima(g=None):
    g = g or gerente()

    tarefa = g.repetir_ultima()

    if tarefa is None:
        return certo(
            "Ainda não terminei nenhuma tarefa para repetir."
        )

    return certo(
        f"Vou fazer de novo: {tarefa.descricao}."
    )


def limpar_concluidas(g=None):
    g = g or gerente()

    quantas = g.limpar_concluidas()

    if not quantas:
        return certo(
            "Não tinha nada concluído para limpar."
        )

    return certo(
        f"Limpei {quantas} "
        f"{'tarefa concluída' if quantas == 1 else 'tarefas concluídas'}."
    )


# ============================================================
# COMO A MILK RECONHECE O PEDIDO
# ============================================================

O_QUE_ESTA_FAZENDO = re.compile(
    r"\bo\s+que\s+(?:voc[êe]|vc|tu)?\s*(?:est[áa]|ta|tá)\s+fazendo\b|"
    r"\b(?:em|n[oa])\s+que\s+(?:voc[êe]|vc)?\s*"
    r"(?:est[áa]|ta|tá)\s+trabalhando\b|"
    r"\bo\s+que\s+voc[êe]\s+anda\s+fazendo\b",
    re.IGNORECASE
)

PENDENTES = re.compile(
    r"\b(?:quais|quantas|que)\s+(?:s[ãa]o\s+)?(?:as\s+)?tarefas?\b|"
    r"\btarefas?\s+(?:est[ãa]o\s+)?pendentes?\b|"
    r"\b(?:o\s+que|quanto)\s+(?:tem|falta|sobrou)\s+na\s+fila\b|"
    r"\bcomo\s+(?:est[áa]|ta|tá)\s+a\s+fila\b|"
    r"\bmostr\w*\s+(?:a\s+)?fila\b|"
    r"\bver\s+a\s+fila\b|"
    r"\bminhas?\s+tarefas?\b",
    re.IGNORECASE
)

PROGRESSO = re.compile(
    r"\b(?:qual|como\s+(?:est[áa]|ta|tá))\s+(?:o\s+|é\s+o\s+)?progresso\b|"
    r"\bcomo\s+(?:est[áa]|ta|tá)\s+(?:indo|isso|essa\s+tarefa)\b|"
    r"\bj[áa]\s+(?:terminou|acabou)\b|"
    r"\bfalta\s+muito\b",
    re.IGNORECASE
)

# "Pause" e "continue" sozinhos são comando de fila. Com complemento
# ("continue o texto"), são conversa, e conversa é com o Claude.
PAUSAR = re.compile(
    r"^(?:pausa|pause|pausar|pausa\s+a[íi])\s*[.!?]*$|"
    r"\bpaus\w*\s+(?:a\s+fila|as\s+tarefas|tudo|o\s+trabalho)\b|"
    r"\bespera\s+um\s+pouco\b",
    re.IGNORECASE
)

CONTINUAR = re.compile(
    r"^(?:continue|continua|continuar|retome|retoma|prossiga|"
    r"pode\s+continuar|volta\s+ao\s+trabalho|despausa|despause)"
    r"\s*[.!?]*$|"
    r"\b(?:retom|continu)\w*\s+(?:a\s+fila|as\s+tarefas|o\s+trabalho)\b",
    re.IGNORECASE
)

CANCELAR_TUDO = re.compile(
    r"\bcancel\w*\s+(?:tudo|todas|todas\s+as\s+tarefas)\b|"
    r"\blimp\w*\s+a\s+fila\b|"
    r"\besvazi\w*\s+a\s+fila\b",
    re.IGNORECASE
)

CANCELAR_PROXIMA = re.compile(
    r"\bcancel\w*\s+a\s+pr[óo]xima\b|"
    r"\btir\w*\s+a\s+pr[óo]xima\s+da\s+fila\b|"
    r"\bcancel\w*\s+a\s+[úu]ltima\s+(?:tarefa|que\s+eu\s+pedi)\b",
    re.IGNORECASE
)

CANCELAR_ATUAL = re.compile(
    r"\bcancel\w*\s+(?:essa|esta|a)\s+tarefa\b|"
    r"\bcancel\w*\s+(?:isso|o\s+que\s+voc[êe]\s+"
    r"(?:est[áa]|ta|tá)\s+fazendo)\b|"
    r"\bpar[ae]\s+(?:essa|esta)\s+tarefa\b|"
    r"\bdesist\w*\s+(?:disso|dessa\s+tarefa)\b",
    re.IGNORECASE
)

PRIORIZAR = re.compile(
    r"\b(?:coloc|coloq|p[õo]e|ponh|bot)\w*\s+"
    r"(?:isso|essa\s+tarefa|essa)?\s*"
    r"(?:como\s+|em\s+|de\s+)?(?:priorid|urgent)\w*|"
    r"\bisso\s+[ée]\s+urgente\b|"
    r"\bprioriz\w*\b|"
    r"\bpassa\s+(?:isso\s+)?na\s+frente\b",
    re.IGNORECASE
)

ADIAR = re.compile(
    r"\b(?:fa[çc]a|faz|fazer|deix\w*|dex\w*)\s+(?:isso\s+)?"
    r"(?:para|pra)?\s*depois\b|"
    r"\bfica\s+(?:para|pra)\s+depois\b|"
    r"\bisso\s+n[ãa]o\s+[ée]\s+urgente\b",
    re.IGNORECASE
)

REPETIR = re.compile(
    r"\b(?:repit|repet)\w*\s+(?:a\s+)?[úu]ltima\b|"
    r"\bfa[çc]a\s+(?:isso\s+)?de\s+novo\b|"
    r"\bde\s+novo,?\s+por\s+favor\b",
    re.IGNORECASE
)

LIMPAR_CONCLUIDAS = re.compile(
    r"\b(?:limp|apag)\w*\s+(?:as\s+)?tarefas?\s+"
    r"(?:conclu[íi]das?|terminadas?|prontas?)\b|"
    r"\blimp\w*\s+o\s+hist[óo]rico\b",
    re.IGNORECASE
)


# Ordem importa: o mais específico primeiro.
COMANDOS = (
    (CANCELAR_TUDO, "🗑️ Limpando a fila", cancelar_tudo),
    (CANCELAR_PROXIMA, "🗑️ Tirando da fila", cancelar_proxima),
    (CANCELAR_ATUAL, "🛑 Cancelando a tarefa", cancelar_atual),
    (LIMPAR_CONCLUIDAS, "🧹 Limpando o histórico", limpar_concluidas),
    (PRIORIZAR, "⏫ Mudando a prioridade", priorizar),
    (ADIAR, "⏬ Deixando para depois", adiar),
    (REPETIR, "🔁 Repetindo a última", repetir_ultima),
    (PAUSAR, "⏸️ Pausando a fila", pausar),
    (CONTINUAR, "▶️ Voltando ao trabalho", continuar),
    (PROGRESSO, "📋 Vendo o progresso", frase_do_progresso),
    (PENDENTES, "📋 Vendo a fila", frase_das_pendentes),
    (O_QUE_ESTA_FAZENDO, "📋 Vendo o que estou fazendo", frase_do_trabalho),
)


def rota_tarefas(texto):
    """Devolve a Decisao do comando de fila, ou None."""

    # Importado aqui porque o roteador importa este módulo: se fosse no
    # topo, os dois se esperariam para sempre.
    from milk.intelligence.roteador import Decisao

    for padrao, descricao, acao in COMANDOS:
        if padrao.search(texto):
            return Decisao(
                "tarefas",
                descricao,
                acao,
                local=True,
            )

    return None
