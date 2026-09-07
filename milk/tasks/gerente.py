# Milk — assistente pessoal.
# Copyright (c) 2026 Thales Teracin. Todos os direitos reservados.
#
# Software proprietário. É proibida a cópia, a distribuição, a
# modificação e a engenharia reversa, no todo ou em parte, sem
# autorização expressa e por escrito do autor. Ver LICENSE.txt.

"""Quem manda na fila de tarefas.

O gerente não sabe conversar, não sabe chamar o Claude e não desenha
nada. Ele só guarda o estado da fila, decide quem é a próxima e avisa
o resto do programa pelo barramento de eventos.

Quem executa a tarefa é a janela de conversa, que já sabe criar o
`ClaudeWorker`. Isso mantém o gerente testável sem Qt e sem rede.

As dependências entram pelo construtor, como no `ChatBubble`: nos
testes a fila fica na memória, sem tocar em disco.
"""

import re

from milk.core import eventos
from milk.tasks import persistencia
from milk.tasks.modelos import Prioridade, Status, Tarefa, resumir


# "isso é urgente", "prioridade máxima"
URGENTE = re.compile(
    r"\b(?:urgent[ée]|urgência|urgencia|para\s+ontem|"
    r"prioridade\s+m[áa]xima|o\s+quanto\s+antes)\b",
    re.IGNORECASE
)

# "quando puder", "sem pressa"
SEM_PRESSA = re.compile(
    r"\b(?:quando\s+(?:puder|der|sobrar\s+tempo)|sem\s+pressa|"
    r"n[ãa]o\s+[ée]\s+urgente|com\s+calma)\b",
    re.IGNORECASE
)


def prioridade_do_texto(texto):
    """A pressa dita no próprio pedido vira prioridade da tarefa."""

    if URGENTE.search(texto or ""):
        return Prioridade.URGENTE

    if SEM_PRESSA.search(texto or ""):
        return Prioridade.BAIXA

    return Prioridade.NORMAL


class GerenteDeTarefas:

    def __init__(
        self,
        *,
        barramento=None,
        ler=persistencia.ler,
        gravar=persistencia.gravar,
    ):
        self._barramento = barramento or eventos.barramento
        self._ler = ler
        self._gravar = gravar

        # Tarefa que ficou RUNNING no disco é de um processo que morreu.
        self.tarefas = persistencia.marcar_interrompidas(
            list(self._ler())
        )

        self.pausada = False

    # ========================================================
    # ESTADO
    # ========================================================

    def em_andamento(self):
        """A tarefa que está rodando agora, se houver."""

        for tarefa in self.tarefas:
            if tarefa.esta_rodando():
                return tarefa

        return None

    def pendentes(self):
        """Quem está na fila, na ordem em que vai sair dela."""

        na_fila = [
            (posicao, tarefa)
            for posicao, tarefa in enumerate(self.tarefas)
            if tarefa.esta_na_fila()
        ]

        na_fila.sort(
            key=lambda par: (
                Prioridade.peso(par[1].prioridade),
                par[0],
            )
        )

        return [
            tarefa
            for _, tarefa in na_fila
        ]

    def terminadas(self):
        return [
            tarefa
            for tarefa in self.tarefas
            if tarefa.terminou()
        ]

    def concluidas(self):
        return [
            tarefa
            for tarefa in self.tarefas
            if tarefa.status == Status.CONCLUIDA
        ]

    def ultima_terminada(self):
        for tarefa in reversed(self.tarefas):
            if tarefa.terminou():
                return tarefa

        return None

    def por_id(self, identificador):
        for tarefa in self.tarefas:
            if tarefa.identificador == identificador:
                return tarefa

        return None

    def ocupada(self):
        return self.em_andamento() is not None

    # ========================================================
    # CICLO DE VIDA
    # ========================================================

    def criar(
        self,
        prompt,
        descricao=None,
        prioridade=None,
        origem="texto",
    ):
        """Anota o pedido na fila. Não começa nada: quem começa é quem executa."""

        tarefa = Tarefa(
            descricao=descricao or resumir(prompt),
            prompt=prompt,
            prioridade=prioridade or prioridade_do_texto(prompt),
            origem=origem,
        )

        self.tarefas.append(tarefa)

        self._salvar()

        self._avisar(eventos.TAREFA_CRIADA, tarefa)

        return tarefa

    def proxima(self):
        """A próxima que pode começar agora, ou None.

        Fila pausada não entrega ninguém, e nada começa enquanto outra
        tarefa estiver rodando: uma de cada vez, porque é um Claude só."""

        if self.pausada or self.ocupada():
            return None

        pendentes = self.pendentes()

        return pendentes[0] if pendentes else None

    def iniciar(self, tarefa):
        from milk.tasks.modelos import agora_iso

        if tarefa is None or tarefa.terminou():
            return None

        tarefa.status = Status.RODANDO
        tarefa.iniciada_em = agora_iso()
        tarefa.erro = ""

        self._salvar()

        self._avisar(eventos.TAREFA_INICIADA, tarefa)

        return tarefa

    def anotar_progresso(self, tarefa, texto):
        """O estado textual que veio do Claude. Nunca uma porcentagem inventada."""

        if tarefa is None:
            return None

        tarefa.progresso = str(texto or "")

        # Progresso não vai para o disco: muda muitas vezes por segundo
        # e não vale uma gravação a cada vez.
        self._avisar(
            eventos.TAREFA_PROGRESSO,
            tarefa,
            progresso=tarefa.progresso,
        )

        return tarefa

    def concluir(self, tarefa, resultado=""):
        return self._encerrar(
            tarefa,
            Status.CONCLUIDA,
            eventos.TAREFA_CONCLUIDA,
            resultado=resultado,
        )

    def falhar(self, tarefa, erro=""):
        return self._encerrar(
            tarefa,
            Status.FALHOU,
            eventos.TAREFA_FALHOU,
            erro=erro,
        )

    def cancelar(self, tarefa):
        return self._encerrar(
            tarefa,
            Status.CANCELADA,
            eventos.TAREFA_CANCELADA,
        )

    def _encerrar(self, tarefa, status, evento, resultado="", erro=""):
        from milk.tasks.modelos import agora_iso

        if tarefa is None or tarefa.terminou():
            return None

        tarefa.status = status
        tarefa.terminada_em = agora_iso()
        tarefa.progresso = ""

        if resultado:
            tarefa.resultado = resultado

        if erro:
            tarefa.erro = erro

        self._salvar()

        self._avisar(evento, tarefa)

        return tarefa

    # ========================================================
    # CONTROLE PEDIDO PELO USUÁRIO
    # ========================================================

    def pausar(self):
        """A tarefa que já está rodando continua; a fila é que espera."""

        self.pausada = True

        return self.pausada

    def continuar(self):
        self.pausada = False

        return self.pausada

    def cancelar_proxima(self):
        pendentes = self.pendentes()

        if not pendentes:
            return None

        return self.cancelar(pendentes[0])

    def cancelar_pendentes(self):
        """Esvazia a fila. Não mexe no que já está rodando."""

        canceladas = []

        for tarefa in self.pendentes():
            if self.cancelar(tarefa):
                canceladas.append(tarefa)

        return canceladas

    def priorizar(self, tarefa, prioridade=Prioridade.URGENTE):
        if tarefa is None or tarefa.terminou():
            return None

        tarefa.prioridade = prioridade

        self._salvar()

        return tarefa

    def adiar(self, tarefa):
        return self.priorizar(tarefa, Prioridade.BAIXA)

    def limpar_concluidas(self):
        """Tira do histórico o que já terminou. A fila viva não é tocada."""

        antes = len(self.tarefas)

        self.tarefas = [
            tarefa
            for tarefa in self.tarefas
            if not tarefa.terminou()
        ]

        self._salvar()

        return antes - len(self.tarefas)

    def repetir_ultima(self):
        """Cria uma tarefa nova com o mesmo pedido da última que terminou."""

        anterior = self.ultima_terminada()

        if anterior is None:
            return None

        return self.criar(
            anterior.prompt,
            descricao=anterior.descricao,
            prioridade=anterior.prioridade,
            origem=anterior.origem,
        )

    def interromper_em_andamento(self):
        """Ao fechar a Milk, o que estava rodando não terminou."""

        tarefa = self.em_andamento()

        if tarefa is None:
            return None

        return self._encerrar(
            tarefa,
            Status.INTERROMPIDA,
            eventos.TAREFA_CANCELADA,
            erro="A Milk foi fechada antes de terminar esta tarefa.",
        )

    # ========================================================
    # INTERNO
    # ========================================================

    def _salvar(self):
        try:
            self.tarefas = persistencia.podar(self.tarefas)

            self._gravar(self.tarefas)

        except Exception:
            # Disco cheio ou pasta somindo não pode derrubar a conversa.
            return False

        return True

    def _avisar(self, evento, tarefa, **extras):
        self._barramento.publicar(
            evento,
            tarefa=tarefa,
            **extras
        )


# Um gerente por processo, criado na primeira vez que alguém precisa.
_gerente = None


def gerente():
    global _gerente

    if _gerente is None:
        _gerente = GerenteDeTarefas()

    return _gerente


def definir_gerente(novo):
    """Troca o gerente do processo. Existe para os testes."""

    global _gerente

    _gerente = novo

    return _gerente
