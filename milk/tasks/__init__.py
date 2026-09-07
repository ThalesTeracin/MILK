# Milk — assistente pessoal.
# Copyright (c) 2026 Thales Teracin. Todos os direitos reservados.
#
# Software proprietário. É proibida a cópia, a distribuição, a
# modificação e a engenharia reversa, no todo ou em parte, sem
# autorização expressa e por escrito do autor. Ver LICENSE.txt.

"""Fila de tarefas da Milk (Fase 9).

O caminho do pedido é este:

    Milk -> roteador -> gerente de tarefas -> Claude

O roteador continua respondendo sozinho o que é consulta rápida
(hora, clima, CEP). O que sobra é trabalho, e trabalho vira tarefa:
entra na fila, tem status, prioridade e resultado, e sobrevive ao
fechamento da janela.

    modelos.py       o que é uma tarefa, os status e as prioridades
    persistencia.py  a fila em disco (milk_tarefas.json)
    gerente.py       quem manda na fila

Os avisos de andamento saem pelo barramento de milk/core/eventos.py.
"""
