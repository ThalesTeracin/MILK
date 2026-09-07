# Milk — assistente pessoal.
# Copyright (c) 2026 Thales Teracin. Todos os direitos reservados.
#
# Software proprietário. É proibida a cópia, a distribuição, a
# modificação e a engenharia reversa, no todo ou em parte, sem
# autorização expressa e por escrito do autor. Ver LICENSE.txt.

"""Autoria da Milk.

Fonte única da autoria. Todo lugar que precisa dizer quem desenvolveu
a Milk — a identidade dela, a janela de conversa, o executável, a
documentação — lê daqui, e não de um texto solto.

Mudar o nome do autor em qualquer outro ponto do projeto sem mudar
aqui faz `tests/test_autoria.py` falhar.
"""

AUTOR = "Thales Teracin"

ANO = 2026

CREDITO = f"Assistente desenvolvida por {AUTOR}."

COPYRIGHT = f"Copyright (c) {ANO} {AUTOR}. Todos os direitos reservados."


def credito():
    """Linha de crédito da Milk, em uma frase."""
    return CREDITO


def copyright_curto():
    """Aviso de direito autoral, para rodapé de janela e sobre."""
    return COPYRIGHT
