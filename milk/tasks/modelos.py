# Milk — assistente pessoal.
# Copyright (c) 2026 Thales Teracin. Todos os direitos reservados.
#
# Software proprietário. É proibida a cópia, a distribuição, a
# modificação e a engenharia reversa, no todo ou em parte, sem
# autorização expressa e por escrito do autor. Ver LICENSE.txt.

"""O que é uma tarefa da Milk.

Uma tarefa é um pedido que precisa de trabalho: quase sempre um pedido
ao Claude. Consulta de ferramenta não vira tarefa — ela responde na
hora e não tem o que acompanhar.

Os nomes de status e prioridade são os da especificação, em maiúsculas.
"""

import uuid
import datetime


class Status:
    """Onde a tarefa está."""

    NA_FILA = "QUEUED"
    RODANDO = "RUNNING"
    ESPERANDO = "WAITING"
    PAUSADA = "PAUSED"
    CONCLUIDA = "COMPLETED"
    FALHOU = "FAILED"
    CANCELADA = "CANCELLED"
    INTERROMPIDA = "INTERRUPTED"

    TODOS = (
        NA_FILA,
        RODANDO,
        ESPERANDO,
        PAUSADA,
        CONCLUIDA,
        FALHOU,
        CANCELADA,
        INTERROMPIDA,
    )

    # Acabou: não volta a rodar sozinha.
    TERMINAIS = (
        CONCLUIDA,
        FALHOU,
        CANCELADA,
        INTERROMPIDA,
    )


class Prioridade:
    """Quem passa na frente na fila."""

    BAIXA = "LOW"
    NORMAL = "NORMAL"
    ALTA = "HIGH"
    URGENTE = "URGENT"

    TODAS = (
        BAIXA,
        NORMAL,
        ALTA,
        URGENTE,
    )

    # Menor peso sai primeiro.
    PESO = {
        URGENTE: 0,
        ALTA: 1,
        NORMAL: 2,
        BAIXA: 3,
    }

    @classmethod
    def peso(cls, prioridade):
        return cls.PESO.get(prioridade, cls.PESO[cls.NORMAL])


def agora_iso():
    return datetime.datetime.now().isoformat(timespec="seconds")


def novo_id():
    """Curto o bastante para caber num log e único o bastante na prática."""

    return uuid.uuid4().hex[:12]


class Tarefa:
    """Um pedido, do momento em que é anotado até o resultado.

    `prompt` é o pedido original, palavra por palavra: é ele que vai
    para o Claude e é ele que permite repetir a tarefa depois."""

    def __init__(
        self,
        descricao,
        prompt,
        prioridade=Prioridade.NORMAL,
        origem="texto",
        identificador=None,
        criada_em=None,
        status=Status.NA_FILA,
        progresso="",
        resultado="",
        erro="",
        iniciada_em=None,
        terminada_em=None,
    ):
        self.identificador = identificador or novo_id()
        self.descricao = descricao
        self.prompt = prompt
        self.criada_em = criada_em or agora_iso()
        self.status = status
        self.prioridade = prioridade
        self.origem = origem
        self.progresso = progresso
        self.resultado = resultado
        self.erro = erro
        self.iniciada_em = iniciada_em
        self.terminada_em = terminada_em

    def terminou(self):
        return self.status in Status.TERMINAIS

    def esta_na_fila(self):
        return self.status == Status.NA_FILA

    def esta_rodando(self):
        return self.status == Status.RODANDO

    def para_dicionario(self):
        return {
            "id": self.identificador,
            "descricao": self.descricao,
            "prompt": self.prompt,
            "criada_em": self.criada_em,
            "status": self.status,
            "prioridade": self.prioridade,
            "origem": self.origem,
            "progresso": self.progresso,
            "resultado": self.resultado,
            "erro": self.erro,
            "iniciada_em": self.iniciada_em,
            "terminada_em": self.terminada_em,
        }

    @classmethod
    def de_dicionario(cls, dados):
        """Campo faltando ou torto vira o padrão. Arquivo antigo não quebra."""

        if not isinstance(dados, dict):
            return None

        prompt = str(dados.get("prompt") or "")
        descricao = str(dados.get("descricao") or "") or prompt[:60]

        if not prompt and not descricao:
            return None

        status = dados.get("status")

        if status not in Status.TODOS:
            status = Status.NA_FILA

        prioridade = dados.get("prioridade")

        if prioridade not in Prioridade.TODAS:
            prioridade = Prioridade.NORMAL

        return cls(
            descricao=descricao,
            prompt=prompt,
            prioridade=prioridade,
            origem=str(dados.get("origem") or "texto"),
            identificador=str(dados.get("id") or "") or novo_id(),
            criada_em=str(dados.get("criada_em") or "") or agora_iso(),
            status=status,
            progresso=str(dados.get("progresso") or ""),
            resultado=str(dados.get("resultado") or ""),
            erro=str(dados.get("erro") or ""),
            iniciada_em=dados.get("iniciada_em") or None,
            terminada_em=dados.get("terminada_em") or None,
        )

    def __repr__(self):
        return (
            f"<Tarefa {self.identificador} {self.status} "
            f"{self.descricao[:40]!r}>"
        )


def resumir(texto, limite=60):
    """A descrição curta que aparece na conversa e na fila."""

    limpo = " ".join(
        str(texto or "").split()
    )

    if len(limpo) <= limite:
        return limpo

    return limpo[: limite - 1].rstrip() + "…"
