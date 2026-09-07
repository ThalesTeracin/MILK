# Milk — assistente pessoal.
# Copyright (c) 2026 Thales Teracin. Todos os direitos reservados.
#
# Software proprietário. É proibida a cópia, a distribuição, a
# modificação e a engenharia reversa, no todo ou em parte, sem
# autorização expressa e por escrito do autor. Ver LICENSE.txt.

"""Modo de convivência (Fase 28).

    NORMAL           ela fala e aparece
    SILENT           ela responde, mas sem voz — só escrito
    DO_NOT_DISTURB   ela não fala nem abre a conversa sozinha

O que muda é como ela se apresenta, não o que ela faz: no silencioso e
no não perturbe o trabalho continua acontecendo, a fila continua
andando e o resultado continua sendo escrito na conversa.

O modo fica gravado, então ele sobrevive a fechar a Milk. Ninguém quer
colocar em silêncio numa reunião e ser surpreendido no dia seguinte.
"""

from milk.core.arquivo import ler_json, gravar_json
from milk.core.config import BASE_DIR


import os


MODO_FILE = os.path.join(BASE_DIR, "milk_modo.json")


NORMAL = "NORMAL"
SILENCIOSO = "SILENT"
NAO_PERTURBE = "DO_NOT_DISTURB"

TODOS = (NORMAL, SILENCIOSO, NAO_PERTURBE)


NOMES = {
    NORMAL: "normal",
    SILENCIOSO: "silencioso",
    NAO_PERTURBE: "não perturbe",
}


class Modos:
    """Guarda o modo atual e responde o que ele permite."""

    def __init__(self, *, ler=ler_json, gravar=gravar_json, arquivo=MODO_FILE):
        self._ler = ler
        self._gravar = gravar
        self._arquivo = arquivo

        guardado = self._ler(arquivo, None) or {}

        modo = guardado.get("modo") if isinstance(guardado, dict) else None

        self.modo = modo if modo in TODOS else NORMAL

    def definir(self, modo):
        """Troca o modo e grava. Modo desconhecido vira NORMAL."""

        self.modo = modo if modo in TODOS else NORMAL

        try:
            self._gravar(
                self._arquivo,
                {"modo": self.modo},
            )

        except Exception:
            pass

        return self.modo

    def nome(self):
        return NOMES.get(self.modo, "normal")

    def pode_falar(self):
        """Só o normal fala. Os outros dois respondem por escrito."""

        return self.modo == NORMAL

    def pode_aparecer_sozinha(self):
        """No não perturbe ela não abre a conversa por conta própria."""

        return self.modo != NAO_PERTURBE

    def pode_latir(self):
        return self.modo == NORMAL


_modos = None


def modos():
    global _modos

    if _modos is None:
        _modos = Modos()

    return _modos


def definir_modos(novos):
    """Troca o controle de modo do processo. Existe para os testes."""

    global _modos

    _modos = novos

    return _modos
