# Milk — assistente pessoal.
# Copyright (c) 2026 Thales Teracin. Todos os direitos reservados.
#
# Software proprietário. É proibida a cópia, a distribuição, a
# modificação e a engenharia reversa, no todo ou em parte, sem
# autorização expressa e por escrito do autor. Ver LICENSE.txt.

"""Ferramentas do Windows e a camada de permissão (Fase 10).

    permissao.py    classifica a ação em SAFE, SENSITIVE, DESTRUCTIVE
                    ou CRITICAL e decide se ela pode acontecer
    acoes.py        as ações em si: abrir programa, pasta, arquivo, URL,
                    procurar arquivo, ver o computador, PowerShell
    confirmacao.py  a ação que está esperando um "sim"
    inicio.py       iniciar junto com o Windows

Regra da casa: **nada é executado sem passar pela permissão**, e o
resultado é sempre estruturado (SUCCESS, ERROR, DENIED, TIMEOUT).
A Milk nunca diz que fez uma coisa que não fez.
"""
