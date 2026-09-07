# Milk — assistente pessoal.
# Copyright (c) 2026 Thales Teracin. Todos os direitos reservados.
#
# Software proprietário. É proibida a cópia, a distribuição, a
# modificação e a engenharia reversa, no todo ou em parte, sem
# autorização expressa e por escrito do autor. Ver LICENSE.txt.

"""A fila em disco.

O arquivo é `milk_tarefas.json`, na raiz do projeto, ao lado do
`milk_pessoa.json`. Guarda a fila inteira, inclusive o que já terminou,
para que a Milk lembre do que fez depois de fechar e abrir.

A gravação é atômica: escreve num arquivo temporário e troca no fim.
Se a energia cair no meio, o arquivo antigo continua íntegro.

Arquivo ausente ou corrompido não derruba nada: a Milk começa com a
fila vazia, do mesmo jeito que faz com o settings.json.
"""

import os
import json
import tempfile

from milk.core.config import TASKS_FILE
from milk.tasks.modelos import Tarefa, Status


# Não faz sentido guardar mil tarefas terminadas. As mais novas ficam.
LIMITE_DE_HISTORICO = 50


def ler():
    """Devolve a lista de Tarefa gravada. Lista vazia se não houver."""

    try:
        with open(TASKS_FILE, "r", encoding="utf-8") as arquivo:
            dados = json.load(arquivo)

    except (OSError, ValueError):
        return []

    if isinstance(dados, dict):
        dados = dados.get("tarefas")

    if not isinstance(dados, list):
        return []

    tarefas = []

    for item in dados:
        tarefa = Tarefa.de_dicionario(item)

        if tarefa:
            tarefas.append(tarefa)

    return tarefas


def podar(tarefas):
    """Mantém tudo que ainda pode acontecer e o histórico mais recente."""

    vivas = [
        tarefa
        for tarefa in tarefas
        if not tarefa.terminou()
    ]

    terminadas = [
        tarefa
        for tarefa in tarefas
        if tarefa.terminou()
    ]

    if len(terminadas) > LIMITE_DE_HISTORICO:
        terminadas = terminadas[-LIMITE_DE_HISTORICO:]

    # A ordem original é a ordem de chegada, e ela importa na fila.
    guardar = set(
        id(tarefa)
        for tarefa in vivas + terminadas
    )

    return [
        tarefa
        for tarefa in tarefas
        if id(tarefa) in guardar
    ]


def gravar(tarefas):
    """Escreve a fila em disco. Devolve True se conseguiu."""

    conteudo = {
        "tarefas": [
            tarefa.para_dicionario()
            for tarefa in podar(list(tarefas))
        ]
    }

    pasta = os.path.dirname(TASKS_FILE) or "."

    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=pasta,
            prefix="milk_tarefas_",
            suffix=".tmp",
            delete=False,
        ) as arquivo:

            json.dump(
                conteudo,
                arquivo,
                ensure_ascii=False,
                indent=2,
            )

            temporario = arquivo.name

        os.replace(temporario, TASKS_FILE)

        return True

    except OSError:
        return False


def marcar_interrompidas(tarefas):
    """O que estava rodando quando o processo morreu não voltou sozinho.

    Ao abrir de novo, tarefa RUNNING vinda do disco é mentira: aquele
    subprocesso não existe mais. Ela vira INTERRUPTED, e o usuário
    decide se manda repetir."""

    for tarefa in tarefas:
        if tarefa.status == Status.RODANDO:
            tarefa.status = Status.INTERROMPIDA

            tarefa.erro = (
                tarefa.erro
                or "A Milk foi fechada antes de terminar esta tarefa."
            )

    return tarefas
