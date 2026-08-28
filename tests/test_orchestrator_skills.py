"""
Testes da ligacao entre MilkCore.handle e o roteador de skills.

O router e consultado antes do NLU: quando casa, executa e fala; quando
nao casa, o fluxo segue exatamente como sempre foi.

MilkCore e montado por __new__ -- instanciar de verdade exigiria
microfone, Whisper e provedor de IA no ar.
"""
import pytest

import core.activity_state as estado_mod
from core.orchestrator import MilkCore


class RouterFalso:
    def __init__(self, plano=None, saida=None):
        self.plano = plano
        self.saida = saida or {"ok": True, "fala": "feito", "dados": {}}
        self.executados = []

    def route_local(self, texto):
        return self.plano

    def execute(self, plano, confirmed=False):
        self.executados.append((plano, confirmed))
        return self.saida


class NluFalso:
    def __init__(self):
        self.chamado = False

    def interpret(self, texto):
        self.chamado = True
        return {"intent": "chat", "reply": "oi"}


class MemoriaFalsa:
    def user_message(self, texto):
        pass

    def assistant_message(self, texto):
        pass


@pytest.fixture(autouse=True)
def estado_isolado(tmp_path, monkeypatch):
    monkeypatch.setattr(estado_mod, "ARQUIVO", tmp_path / "runtime.json")
    monkeypatch.setattr(estado_mod, "_atividade", "idle")


@pytest.fixture
def core():
    c = MilkCore.__new__(MilkCore)
    c.state = "ready"
    c.running = True
    c.memory = MemoriaFalsa()
    c.nlu = NluFalso()
    c._pending_confirmation = None
    c.ditos = []
    c.say = c.ditos.append
    return c


def test_skill_que_casa_e_falada(core):
    core.skills = RouterFalso(
        plano={"type": "builtin", "skill": "git_status", "args": {}},
        saida={"ok": True, "fala": "Estou na branch master.", "dados": {}},
    )

    core.handle("qual o status do git")

    assert core.ditos == ["Estou na branch master."]


def test_skill_que_casa_nao_gasta_o_nlu(core):
    """O ponto de rotear local: não pagar token no que já foi resolvido."""
    core.skills = RouterFalso(plano={"type": "builtin", "skill": "git_status", "args": {}})

    core.handle("qual o status do git")

    assert core.nlu.chamado is False


def test_frase_que_nao_casa_segue_para_o_nlu(core):
    core.skills = RouterFalso(plano=None)

    core.handle("me conte uma piada")

    assert core.nlu.chamado is True


def test_skill_que_falha_fala_o_motivo(core):
    core.skills = RouterFalso(
        plano={"type": "builtin", "skill": "git_status", "args": {}},
        saida={"ok": False, "fala": "Não consegui ler o status do git.", "dados": {}},
    )

    core.handle("qual o status do git")

    assert core.ditos == ["Não consegui ler o status do git."]


def test_skill_que_pede_confirmacao_adia(core):
    core.skills = RouterFalso(
        plano={"type": "builtin", "skill": "open_projects", "args": {}},
        saida={"requires_confirmation": True, "skill": "open_projects",
               "fala": "Isso requer confirmação. Diga confirmar para continuar."},
    )

    core.handle("abrir projetos")

    assert core._pending_confirmation is not None
    assert "confirmar" in core.ditos[0].lower()


def test_confirmar_executa_a_skill_adiada(core):
    router = RouterFalso(
        plano={"type": "builtin", "skill": "open_projects", "args": {}},
        saida={"requires_confirmation": True, "skill": "open_projects",
               "fala": "Isso requer confirmação. Diga confirmar para continuar."},
    )
    core.skills = router
    core.handle("abrir projetos")

    router.saida = {"ok": True, "fala": "Abri a pasta de projetos.", "dados": {}}
    core.handle("confirmar")

    assert router.executados[-1][1] is True
    assert core.ditos[-1] == "Abri a pasta de projetos."


def test_dormindo_a_skill_nao_dispara_sem_a_wake_word(core):
    """A palavra 'milk' continua sendo o portão; a skill não fura isso."""
    core.state = "sleep"
    core.skills = RouterFalso(plano={"type": "builtin", "skill": "git_status", "args": {}})

    core.handle("qual o status do git")

    assert core.ditos == []
