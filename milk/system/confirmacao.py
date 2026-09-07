# Milk — assistente pessoal.
# Copyright (c) 2026 Thales Teracin. Todos os direitos reservados.
#
# Software proprietário. É proibida a cópia, a distribuição, a
# modificação e a engenharia reversa, no todo ou em parte, sem
# autorização expressa e por escrito do autor. Ver LICENSE.txt.

"""A ação que está esperando um sim.

Ação sensível ou destrutiva não acontece porque foi pedida: acontece
porque foi pedida **e** confirmada. Este módulo guarda esse meio do
caminho — uma ação por vez, com prazo.

O prazo existe para não sobrar um "sim" perdido: se você pedir para
apagar um arquivo e sair para o almoço, o "sim" de uma hora depois não
vale mais.
"""

import re
import time


# Depois disso, o pedido caduca e some sozinho.
PRAZO_SEGUNDOS = 120


SIM = re.compile(
    r"^(?:sim|pode|pode\s+sim|isso|isso\s+mesmo|confirmo|confirmado|"
    r"autorizo|manda|manda\s+ver|vai|vai\s+l[áa]|claro|ok|okay|beleza|"
    r"blz|faz|fa[çc]a|quero|positivo|aham|uhum)"
    r"[\s,.!]*$",
    re.IGNORECASE
)

NAO = re.compile(
    r"^(?:n[ãa]o|nao|nada|cancela|cancelar|cancele|deixa|deixa\s+pra\s+l[áa]|"
    r"esquece|esque[çc]a|melhor\s+n[ãa]o|para|pare|negativo|nops?)"
    r"[\s,.!]*$",
    re.IGNORECASE
)


def e_sim(texto):
    return bool(
        SIM.match(
            str(texto or "").strip()
        )
    )


def e_nao(texto):
    return bool(
        NAO.match(
            str(texto or "").strip()
        )
    )


class Pedido:
    """Uma ação guardada, esperando resposta."""

    def __init__(self, descricao, executar, nivel, motivo="", quando=None):
        self.descricao = descricao
        self.executar = executar
        self.nivel = nivel
        self.motivo = motivo
        self.quando = quando if quando is not None else time.monotonic()

    def caducou(self, agora=None, prazo=PRAZO_SEGUNDOS):
        momento = agora if agora is not None else time.monotonic()

        return (momento - self.quando) > prazo

    def __repr__(self):
        return f"<Pedido {self.nivel}: {self.descricao[:40]}>"


class Confirmacao:
    """Uma ação pendente por vez. Pedir de novo troca a anterior."""

    def __init__(self, relogio=time.monotonic, prazo=PRAZO_SEGUNDOS):
        self._relogio = relogio
        self._prazo = prazo

        self._pedido = None

    def pedir(self, descricao, executar, nivel, motivo=""):
        """Guarda a ação e devolve a pergunta que a Milk faz."""

        self._pedido = Pedido(
            descricao,
            executar,
            nivel,
            motivo,
            quando=self._relogio(),
        )

        pergunta = f"{descricao}. Confirma?"

        if motivo:
            pergunta = f"{descricao}. {motivo} Confirma?"

        return pergunta

    def pendente(self):
        """A ação esperando resposta, ou None se não há ou caducou."""

        if self._pedido is None:
            return None

        if self._pedido.caducou(self._relogio(), self._prazo):
            self._pedido = None

            return None

        return self._pedido

    def confirmar(self):
        """Executa a ação pendente. Devolve o resultado dela, ou None."""

        pedido = self.pendente()

        self._pedido = None

        if pedido is None:
            return None

        return pedido.executar()

    def cancelar(self):
        """Esquece a ação pendente. Devolve a descrição, ou None."""

        pedido = self.pendente()

        self._pedido = None

        return pedido.descricao if pedido else None


# Uma por processo, como o gerente e a memória.
_confirmacao = None


def confirmacao():
    global _confirmacao

    if _confirmacao is None:
        _confirmacao = Confirmacao()

    return _confirmacao


def definir_confirmacao(nova):
    """Troca a confirmação do processo. Existe para os testes."""

    global _confirmacao

    _confirmacao = nova

    return _confirmacao
