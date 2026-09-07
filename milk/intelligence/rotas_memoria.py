# Milk — assistente pessoal.
# Copyright (c) 2026 Thales Teracin. Todos os direitos reservados.
#
# Software proprietário. É proibida a cópia, a distribuição, a
# modificação e a engenharia reversa, no todo ou em parte, sem
# autorização expressa e por escrito do autor. Ver LICENSE.txt.

"""Comandos de memória.

"Lembre que eu prefiro café sem açúcar", "o que você sabe sobre mim",
"esqueça o que eu falei sobre o notebook", "o que fizemos ontem".

Tudo local: é o que ela já tem guardado, não precisa de Claude.

Como as rotas da fila, estas moram fora do roteador e são consultadas
antes do veto — "anote que..." é memória, não trabalho novo.
"""

import re
import datetime

from milk.tools import certo
from milk.memory.memoria import memoria
from milk.tasks.gerente import gerente
from milk.tasks.modelos import Status


# ============================================================
# O QUE ELA RESPONDE
# ============================================================

def guardar(texto, m=None):
    """Grava o fato e confirma. Recusa se houver segredo na frase."""

    m = m or memoria()

    fato = m.lembrar(texto)

    if fato is None:
        from milk.memory.memoria import tem_segredo

        if tem_segredo(texto):
            return certo(
                "Isso eu prefiro não guardar. Senha, token e chave não "
                "ficam comigo — é mais seguro assim."
            )

        return certo(
            "Não consegui entender o que era para eu guardar."
        )

    return certo(
        f"Guardado: {fato['texto']}"
    )


def contar_o_que_sabe(termo=None, m=None):
    m = m or memoria()

    fatos = m.buscar(termo) if termo else list(m.fatos)

    if not fatos:
        if termo:
            return certo(
                f"Não tenho nada guardado sobre {termo}."
            )

        return certo(
            "Ainda não guardei nada sobre você. É só me pedir: "
            "\"lembre que...\"."
        )

    linhas = "; ".join(
        fato["texto"]
        for fato in fatos[-8:]
    )

    if termo:
        return certo(
            f"Sobre {termo}, eu sei: {linhas}."
        )

    return certo(
        f"O que eu sei: {linhas}."
    )


def apagar(termo, m=None):
    m = m or memoria()

    quantos = m.esquecer(termo)

    if not quantos:
        return certo(
            f"Não tinha nada guardado sobre {termo}."
        )

    if quantos == 1:
        return certo(
            f"Esqueci o que eu sabia sobre {termo}."
        )

    return certo(
        f"Esqueci {quantos} coisas sobre {termo}."
    )


def apagar_tudo(m=None):
    m = m or memoria()

    quantos = m.esquecer_tudo()

    if not quantos:
        return certo(
            "Minha memória já estava vazia."
        )

    return certo(
        f"Pronto, esqueci tudo o que eu sabia ({quantos} anotações)."
    )


def anotar_projeto(nome, m=None):
    m = m or memoria()

    projeto = m.anotar_projeto(nome)

    if projeto is None:
        return certo(
            "Não entendi o nome do projeto."
        )

    return certo(
        f"Anotado. Agora sei que você está no projeto {projeto['nome']}."
    )


def o_que_fizemos(quando="hoje", m=None, g=None):
    """Histórico de tarefas do dia, vindo da fila."""

    m = m or memoria()
    g = g or gerente()

    dia = datetime.date.today()

    if quando == "ontem":
        dia = dia - datetime.timedelta(days=1)

    marca = dia.isoformat()

    tarefas = [
        tarefa
        for tarefa in g.tarefas
        if str(tarefa.terminada_em or "").startswith(marca)
    ]

    palavra = "hoje" if quando == "hoje" else "ontem"

    if not tarefas:
        falas = m.falas_do_dia(marca)

        if falas:
            return certo(
                f"{palavra.capitalize()} nós conversamos, mas não "
                "terminei nenhuma tarefa."
            )

        return certo(
            f"Não tenho nada registrado de {palavra}."
        )

    concluidas = [
        tarefa
        for tarefa in tarefas
        if tarefa.status == Status.CONCLUIDA
    ]

    linhas = "; ".join(
        tarefa.descricao
        for tarefa in tarefas[-6:]
    )

    frase = f"{palavra.capitalize()} eu trabalhei em: {linhas}."

    quantas = len(tarefas)
    prontas = len(concluidas)

    if prontas < quantas:
        frase += (
            f" Terminei {prontas} de {quantas}."
        )

    return certo(frase)


# ============================================================
# COMO ELA RECONHECE
# ============================================================

LEMBRAR = re.compile(
    r"^(?:lembr\w*|anot\w*|guard\w*|memoriz\w*|n[ãa]o\s+esque[çc]a)"
    r"\s+(?:que\s+|disso:\s*|isso:\s*|o\s+seguinte:\s*)?(.+)$",
    re.IGNORECASE
)

SABE_SOBRE = re.compile(
    r"\bo\s+que\s+voc[êe]\s+(?:sabe|lembra|guardou)\s+"
    # "sobre mim" não é assunto: cai na pergunta geral, logo abaixo.
    r"(?:sobre|de|do|da)\s+(?!mim\b|eu\b|n[óo]s\b)(.+)$",
    re.IGNORECASE
)

SABE_DE_MIM = re.compile(
    r"\bo\s+que\s+voc[êe]\s+(?:sabe|lembra|guardou)"
    r"(?:\s+sobre\s+mim|\s+de\s+mim)?\s*[?.!]*$|"
    r"\bo\s+que\s+(?:est[áa]|ta|tá)\s+na\s+sua\s+mem[óo]ria\b|"
    r"\bsua\s+mem[óo]ria\b",
    re.IGNORECASE
)

ESQUECER_TUDO = re.compile(
    r"\besque[çc]\w*\s+tudo\b|"
    r"\blimp\w*\s+(?:a\s+)?(?:sua\s+)?mem[óo]ria\b|"
    r"\bapag\w*\s+tudo\s+(?:o\s+)?que\s+voc[êe]\s+sabe\b",
    re.IGNORECASE
)

ESQUECER = re.compile(
    r"\besque[çc]\w*\s+(?:o\s+que\s+eu\s+(?:falei|disse|te\s+contei)\s+"
    r"(?:sobre|de|do|da)\s+)?(.+)$|"
    r"\bapag\w*\s+(?:o\s+que\s+voc[êe]\s+sabe\s+"
    r"(?:sobre|de|do|da)\s+)(.+)$",
    re.IGNORECASE
)

PROJETO_ATUAL = re.compile(
    r"\b(?:estou|to|tô)\s+(?:trabalhando\s+)?"
    r"(?:no|num|em\s+um)\s+projeto\s+(?:chamado\s+)?(.+)$|"
    r"\bmeu\s+projeto\s+(?:se\s+chama|é|e)\s+(.+)$",
    re.IGNORECASE
)

O_QUE_FIZEMOS = re.compile(
    r"\bo\s+que\s+(?:n[óo]s\s+|a\s+gente\s+)?"
    r"(?:fizemos|fez|fizemo|trabalhamos)\s+(hoje|ontem)\b|"
    r"\bo\s+que\s+voc[êe]\s+fez\s+(hoje|ontem)\b",
    re.IGNORECASE
)


def limpar_alvo(texto):
    return " ".join(
        str(texto or "").strip().strip("?!.,;:").split()
    )


def rota_memoria(texto):
    """Devolve a Decisao do comando de memória, ou None."""

    from milk.intelligence.roteador import Decisao

    achado = O_QUE_FIZEMOS.search(texto)

    if achado:
        quando = (achado.group(1) or achado.group(2) or "hoje").lower()

        return Decisao(
            "memoria",
            "🗂️ Vendo o que fizemos",
            lambda: o_que_fizemos(quando),
            local=True,
        )

    if ESQUECER_TUDO.search(texto):
        return Decisao(
            "memoria",
            "🧽 Esquecendo tudo",
            apagar_tudo,
            local=True,
        )

    achado = SABE_SOBRE.search(texto)

    if achado:
        alvo = limpar_alvo(achado.group(1))

        return Decisao(
            "memoria",
            f"🧠 Lembrando de {alvo}",
            lambda: contar_o_que_sabe(alvo),
            local=True,
        )

    if SABE_DE_MIM.search(texto):
        return Decisao(
            "memoria",
            "🧠 Vendo o que eu sei",
            contar_o_que_sabe,
            local=True,
        )

    achado = LEMBRAR.match(texto.strip())

    if achado:
        fato = limpar_alvo(achado.group(1))

        if len(fato) >= 3:
            return Decisao(
                "memoria",
                "🧠 Guardando",
                lambda: guardar(fato),
                local=True,
            )

    achado = ESQUECER.search(texto)

    if achado:
        alvo = limpar_alvo(
            achado.group(1) or achado.group(2)
        )

        if len(alvo) >= 3:
            return Decisao(
                "memoria",
                f"🧽 Esquecendo {alvo}",
                lambda: apagar(alvo),
                local=True,
            )

    achado = PROJETO_ATUAL.search(texto)

    if achado:
        nome = limpar_alvo(
            achado.group(1) or achado.group(2)
        )

        if len(nome) >= 2:
            return Decisao(
                "memoria",
                "🗂️ Anotando o projeto",
                lambda: anotar_projeto(nome),
                local=True,
            )

    return None
