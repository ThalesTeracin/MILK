# Milk — assistente pessoal.
# Copyright (c) 2026 Thales Teracin. Todos os direitos reservados.
#
# Software proprietário. É proibida a cópia, a distribuição, a
# modificação e a engenharia reversa, no todo ou em parte, sem
# autorização expressa e por escrito do autor. Ver LICENSE.txt.

"""Memória da Milk (Fase 11).

Três camadas, como a especificação pede:

    curto prazo   a conversa atual, que também é gravada para a Milk
                  saber do que vocês estavam falando quando ela reabrir
    persistente   preferências e fatos sobre a pessoa
    projetos      o que ela sabe dos projetos em andamento

    memoria.py    as três camadas e o resumo que vai para o prompt

O histórico de tarefas (pedido, resultado, duração, erros, status) já
mora na fila, em `milk_tarefas.json`, e é consultado a partir daqui.

Senha, token e chave nunca são guardados: a memória se recusa.
"""
