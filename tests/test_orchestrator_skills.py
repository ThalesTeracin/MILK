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


class MemoriaLongaFalsa:
    """Dublê mínimo de MemoryManager.long, só o necessário para os blocos
    locais de memória do handle (quais projetos / status da memória) não
    quebrarem -- nada toca banco de verdade."""

    def list_projects(self, limit=8):
        return []

    def stats(self):
        return {"conversations": 0, "projects": 0, "decisions": 0, "errors": 0}


class MemoriaFalsa:
    def __init__(self):
        self.long = MemoriaLongaFalsa()

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


def test_pendencia_e_descartada_por_comando_nao_relacionado(core):
    """Uma pendência abandonada não pode ser disparada por um "confirmar"
    posterior -- inclusive um alucinado pelo reconhecimento de voz a partir
    de ruído de fundo, depois que o usuário já seguiu para outro assunto."""
    acao_antiga = {"chamada": False}

    def _run_antiga():
        acao_antiga["chamada"] = True

    core._pending_confirmation = {"run": _run_antiga}
    core.skills = RouterFalso(
        plano={"type": "builtin", "skill": "git_status", "args": {}},
        saida={"ok": True, "fala": "Estou na branch master.", "dados": {}},
    )

    core.handle("qual o status do git")
    core.handle("confirmar")

    assert acao_antiga["chamada"] is False


def test_confirmar_imediato_ainda_executa_a_acao(core):
    """Guarda contra limpar a pendência cedo demais: confirmar logo em
    seguida ao pedido que a criou continua disparando a ação."""
    acao = {"chamada": False}

    def _run():
        acao["chamada"] = True

    core._pending_confirmation = {"run": _run}
    core.skills = RouterFalso(plano=None)

    core.handle("confirmar")

    assert acao["chamada"] is True


def test_pendencia_e_descartada_por_quais_projetos(core):
    """Rodada 2: "quais projetos" tem return próprio, antes do bloco de
    skills. Se o descarte ficasse depois desse return (como estava antes
    da correção), essa pendência sobreviveria intacta até o "confirmar"
    seguinte."""
    acao_antiga = {"chamada": False}

    def _run_antiga():
        acao_antiga["chamada"] = True

    core._pending_confirmation = {"run": _run_antiga}
    core.skills = RouterFalso(plano=None)

    core.handle("quais projetos")
    core.handle("confirmar")

    assert acao_antiga["chamada"] is False


def test_pendencia_e_descartada_por_status_da_memoria(core):
    """Mesma lacuna do teste acima, para o outro bloco de memória com
    return próprio ("status da memória")."""
    acao_antiga = {"chamada": False}

    def _run_antiga():
        acao_antiga["chamada"] = True

    core._pending_confirmation = {"run": _run_antiga}
    core.skills = RouterFalso(plano=None)

    core.handle("status da memória")
    core.handle("confirmar")

    assert acao_antiga["chamada"] is False
