"""
Testes da ligacao entre MilkCore e core.activity_state.

Instanciar MilkCore de verdade exigiria microfone, Whisper e provedor de
IA no ar. Estes testes exercitam so o metodo say(), com o objeto montado
por __new__ e os colaboradores que say() usa trocados por falsos.
"""
import pytest

import core.activity_state as estado_mod
from core.activity_state import atividade
from core.orchestrator import MilkCore


class FalanteFalso:
    def __init__(self, ao_falar=None):
        self.ditos = []
        self.ao_falar = ao_falar

    def say(self, texto):
        self.ditos.append(texto)
        if self.ao_falar:
            self.ao_falar()


class MemoriaFalsa:
    def __init__(self):
        self.mensagens = []

    def assistant_message(self, texto):
        self.mensagens.append(texto)


@pytest.fixture(autouse=True)
def estado_isolado(tmp_path, monkeypatch):
    monkeypatch.setattr(estado_mod, "ARQUIVO", tmp_path / "runtime.json")
    monkeypatch.setattr(estado_mod, "_atividade", "idle")


@pytest.fixture
def core():
    c = MilkCore.__new__(MilkCore)
    c.state = "ready"
    c.speaker = FalanteFalso()
    c.memory = MemoriaFalsa()
    return c


def test_say_marca_falando_enquanto_fala(core):
    visto = []
    core.speaker = FalanteFalso(ao_falar=lambda: visto.append(atividade()))

    core.say("olá")

    assert visto == ["speaking"]


def test_depois_de_falar_volta_a_ouvir(core):
    core.say("olá")

    assert atividade() == "listening"


def test_dormindo_volta_para_ocioso(core):
    core.state = "sleep"

    core.say("vou ficar em espera")

    assert atividade() == "idle"


def test_falha_do_falante_nao_deixa_o_estado_presa_em_falando(core):
    """O finally do say() existe para isso; o teste garante que continua lá."""
    def explode():
        raise RuntimeError("TTS fora do ar")

    core.speaker = FalanteFalso(ao_falar=explode)

    with pytest.raises(RuntimeError):
        core.say("olá")

    assert atividade() == "listening"


def test_milkcore_nao_tem_mais_o_atributo_activity(core):
    """
    O ponto da fase: uma verdade só. Um atributo sobrevivente viraria a
    segunda, e o overlay leria o valor errado sem ninguém perceber.
    """
    core.say("olá")

    assert not hasattr(core, "activity")
