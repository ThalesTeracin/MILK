"""
Testes de src/core/nlu.py (HybridNLU.interpret) -- cobrem os comandos
locais determinísticos, que não dependem de IA/rede.
"""
from core.nlu import HybridNLU


def make_nlu():
    return HybridNLU(ai=None)


def test_greeting_intents_return_chat():
    nlu = make_nlu()
    assert nlu.interpret("boa tarde")["intent"] == "chat"
    assert nlu.interpret("bom dia")["intent"] == "chat"
    assert nlu.interpret("boa noite")["intent"] == "chat"


def test_open_app_calculadora():
    nlu = make_nlu()
    result = nlu.interpret("preciso fazer conta")
    assert result["intent"] == "open_app"
    assert result["target"] == "calculadora"


def test_open_app_bloco_de_notas():
    nlu = make_nlu()
    result = nlu.interpret("abrir o bloco de notas")
    assert result["intent"] == "open_app"
    assert result["target"] == "bloco de notas"


def test_open_app_painel_de_controle():
    nlu = make_nlu()
    result = nlu.interpret("abrir painel de controle")
    assert result["intent"] == "open_app"
    assert result["target"] == "painel de controle"


def test_open_app_gerenciador_de_tarefas():
    nlu = make_nlu()
    result = nlu.interpret("abrir gerenciador de tarefas")
    assert result["intent"] == "open_app"
    assert result["target"] == "gerenciador de tarefas"


def test_open_app_explorador():
    nlu = make_nlu()
    result = nlu.interpret("abrir explorador")
    assert result["intent"] == "open_app"
    assert result["target"] == "explorador"


def test_system_status_intent():
    nlu = make_nlu()
    result = nlu.interpret("status do sistema")
    assert result["intent"] == "system_status"


def test_exit_intent():
    nlu = make_nlu()
    result = nlu.interpret("tchau milk")
    assert result["intent"] == "exit"


def test_unmatched_text_without_ai_falls_back_to_chat_not_configured():
    nlu = make_nlu()
    result = nlu.interpret("qualquer coisa totalmente fora do escopo")
    assert result["intent"] == "chat"
    assert "não está configurado" in result["reply"]
