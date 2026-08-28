"""
Testes dos lacos after() de presence/unified_app.py.

Motivo: _poll_events chamava _on_heard sem protecao. Qualquer excecao saia
do metodo, o after() final nunca rodava e a fila deixava de ser consumida
para sempre -- a thread de escuta continuava gravando "Ouvi:" no log e a
MILK nunca mais respondia. Sob pythonw o traceback ia para um stderr que
nao existe, entao a falha era invisivel.

Os testes constroem a UnifiedApp com __new__ e preenchem so os atributos
de que cada laco precisa: instanciar de verdade exigiria Tk, microfone e
um MilkCore.
"""
import queue

import pytest

import core.activity_state as estado_mod
import presence.unified_app as app_mod
from presence.unified_app import UnifiedApp


@pytest.fixture(autouse=True)
def estado_isolado(tmp_path, monkeypatch):
    """
    Isola o estado real (data/milk_runtime_state.json) dos testes deste
    arquivo. Desde que _idle_watch e _animate passaram a chamar
    definir_atividade()/pulsar() de verdade (Fase 33), os objetos falsos
    de core aqui não bastam mais para evitar escrita em disco -- a função
    real do módulo é quem grava.
    """
    monkeypatch.setattr(estado_mod, "ARQUIVO", tmp_path / "runtime.json")
    monkeypatch.setattr(estado_mod, "_atividade", "idle")


class RootFalso:
    """Registra os after() agendados, em vez de agendar de verdade."""

    def __init__(self):
        self.agendados = []

    def after(self, ms, fn):
        self.agendados.append((ms, fn))


@pytest.fixture
def registros(monkeypatch):
    """Captura o que o modulo escreveria em logs/presence.log."""
    linhas = []
    monkeypatch.setattr(app_mod, "_log", linhas.append)
    return linhas


@pytest.fixture
def app():
    a = UnifiedApp.__new__(UnifiedApp)
    a.root = RootFalso()
    a.events = queue.Queue()
    a.visible = False
    a.base_img = None
    a.last_activity = 0
    a.pulse = 0
    return a


# ------------------------------------------------- fila fora do Tk

def test_nao_existe_mais_poll_events(app):
    """
    A fila passou a ser consumida pela thread de trabalho. Um _poll_events
    sobrevivente voltaria a chamar handle() na thread do Tk, e o avatar
    voltaria a congelar -- o defeito que esta fase existe para tirar.
    """
    assert not hasattr(app, "_poll_events")
    assert not hasattr(app, "_on_heard")


def test_trabalho_loop_entrega_a_fala_ao_cerebro(app):
    tratados = []
    app.core = type("CoreFalso", (), {"handle": lambda self, t: tratados.append(t)})()
    app.running = True

    app.events.put("milk que horas são")
    app._trabalho_passo(timeout=0.01)

    assert tratados == ["milk que horas são"]


def test_fila_vazia_no_trabalho_loop_nao_e_erro(app):
    app.core = type("CoreFalso", (), {"handle": lambda self, t: None})()
    app.running = True

    app._trabalho_passo(timeout=0.01)  # não levanta


def test_falha_do_cerebro_nao_mata_a_thread_de_trabalho(app, registros):
    def explode(self, texto):
        raise RuntimeError("provedor de IA fora do ar")

    app.core = type("CoreFalso", (), {"handle": explode})()
    app.running = True
    app.events.put("milk")

    app._trabalho_passo(timeout=0.01)  # não levanta

    registro = "\n".join(registros)
    assert "provedor de IA fora do ar" in registro


def test_o_fade_segue_o_estado_e_nao_o_comando(app, monkeypatch):
    """
    A thread de trabalho não pode tocar em Tk. Quem faz o fade é o
    _idle_watch, olhando core.state.
    """
    escondeu = []
    monkeypatch.setattr(app, "_fade_out", lambda: escondeu.append(True))
    app.visible = True
    app.core = type("CoreFalso", (), {"state": "sleep"})()

    app._idle_watch()

    assert escondeu == [True]


# ------------------------------------------------------------ _animate

def test_animate_reagenda_mesmo_falhando(app, registros, monkeypatch):
    app.visible = True
    app.base_img = object()
    monkeypatch.setattr(app, "_render_avatar", lambda b: 1 / 0)
    app.core = type("CoreFalso", (), {"activity": "thinking"})()

    app._animate()

    assert app.root.agendados == [(120, app._animate)]


# --------------------------------------------------------- _idle_watch

def test_idle_watch_reagenda_mesmo_falhando(app, registros, monkeypatch):
    app.visible = True
    app.idle_timeout = 0
    app.last_activity = 1
    monkeypatch.setattr(app, "_fade_out", lambda: 1 / 0)
    app.core = type("CoreFalso", (), {"state": "ready", "activity": "idle"})()

    app._idle_watch()

    assert app.root.agendados == [(1000, app._idle_watch)]
