# Milk — assistente pessoal.
# Copyright (c) 2026 Thales Teracin. Todos os direitos reservados.
#
# Software proprietário. É proibida a cópia, a distribuição, a
# modificação e a engenharia reversa, no todo ou em parte, sem
# autorização expressa e por escrito do autor. Ver LICENSE.txt.

"""Leitura e gravação de JSON, do jeito que a Milk precisa.

Gravar é atômico: escreve num arquivo temporário na mesma pasta e só
então troca pelo definitivo. Se faltar energia no meio, o arquivo
antigo continua inteiro — nunca sobra um JSON pela metade.

Ler nunca levanta exceção: arquivo ausente, sem permissão ou corrompido
devolvem o padrão que quem chamou passou.

Quem usa: a fila de tarefas e a memória. As duas guardam estado que não
pode sumir só porque a máquina desligou na hora errada.
"""

import os
import json
import tempfile


def ler_json(caminho, padrao=None):
    """O conteúdo do arquivo, ou `padrao` se não der para ler."""

    try:
        with open(caminho, "r", encoding="utf-8") as arquivo:
            return json.load(arquivo)

    except (OSError, ValueError):
        return padrao


def gravar_json(caminho, conteudo):
    """Grava trocando no fim. Devolve True se conseguiu."""

    pasta = os.path.dirname(caminho) or "."

    temporario = None

    try:
        os.makedirs(pasta, exist_ok=True)

        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=pasta,
            prefix="milk_",
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

        os.replace(temporario, caminho)

        return True

    except OSError:
        # Não deixa lixo para trás quando a troca falha.
        if temporario:
            try:
                os.unlink(temporario)

            except OSError:
                pass

        return False
