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


# ------------------------------------------------------- _poll_events

def test_fila_vazia_reagenda(app):
    app._poll_events()

    assert app.root.agendados == [(100, app._poll_events)]


def test_consome_tudo_que_esta_na_fila(app, monkeypatch):
    tratados = []
    monkeypatch.setattr(app, "_on_heard", tratados.append)

    app.events.put("um")
    app.events.put("dois")
    app._poll_events()

    assert tratados == ["um", "dois"]


def test_excecao_ao_tratar_nao_mata_o_laco(app, registros, monkeypatch):
    """O defeito original: uma excecao aqui parava o after() para sempre."""
    def explode(texto):
        raise RuntimeError("provedor de IA fora do ar")

    monkeypatch.setattr(app, "_on_heard", explode)
    app.events.put("milk que horas sao")

    app._poll_events()

    assert app.root.agendados == [(100, app._poll_events)]


def test_a_falha_vai_para_o_log(app, registros, monkeypatch):
    def explode(texto):
        raise RuntimeError("provedor de IA fora do ar")

    monkeypatch.setattr(app, "_on_heard", explode)
    app.events.put("milk que horas sao")

    app._poll_events()

    registro = "\n".join(registros)
    assert "milk que horas sao" in registro
    assert "provedor de IA fora do ar" in registro
    # Sem o traceback nao da para saber onde quebrou: era o que faltava.
    assert "RuntimeError" in registro


def test_uma_frase_ruim_nao_impede_a_proxima(app, registros, monkeypatch):
    tratados = []

    def as_vezes_explode(texto):
        if texto == "ruim":
            raise RuntimeError("falhou")
        tratados.append(texto)

    monkeypatch.setattr(app, "_on_heard", as_vezes_explode)
    app.events.put("ruim")
    app.events.put("boa")

    app._poll_events()

    assert tratados == ["boa"]


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
