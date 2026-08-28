"""
Testes de src/ai/persona.py -- a fonte única do system prompt, que
substituiu as quatro cópias divergentes escritas à mão nos pontos de
chamada de AIRouter.chat().
"""
import ai.persona as persona
from ai.persona import CONTEXT_HINT, FALLBACK, VOICE_HINT, system_prompt


def test_le_o_arquivo_de_persona():
    assert persona.PERSONA_FILE.exists()
    assert "JARVIS" in system_prompt()


def test_dicas_sao_anexadas_ao_final():
    saida = system_prompt(VOICE_HINT)
    assert saida.endswith(VOICE_HINT)
    assert saida.startswith(system_prompt().split("\n")[0])


def test_varias_dicas_entram_na_ordem_dada():
    saida = system_prompt(VOICE_HINT, CONTEXT_HINT)
    assert saida.index(VOICE_HINT) < saida.index(CONTEXT_HINT)


def test_sem_dicas_devolve_so_a_persona():
    assert system_prompt() == persona._load()


def test_dicas_vazias_sao_ignoradas():
    assert system_prompt("", None, "   ") == system_prompt()


def test_cai_no_fallback_quando_o_arquivo_some(tmp_path, monkeypatch):
    """Um arquivo ausente não pode derrubar uma resposta de chat."""
    monkeypatch.setattr(persona, "PERSONA_FILE", tmp_path / "nao_existe.txt")
    persona.reload()
    try:
        assert system_prompt() == FALLBACK
    finally:
        persona.reload()


def test_reload_relê_o_arquivo(tmp_path, monkeypatch):
    arquivo = tmp_path / "persona.txt"
    arquivo.write_text("primeira versão", encoding="utf-8")
    monkeypatch.setattr(persona, "PERSONA_FILE", arquivo)
    persona.reload()
    try:
        assert system_prompt() == "primeira versão"
        arquivo.write_text("segunda versão", encoding="utf-8")
        assert system_prompt() == "primeira versão"  # ainda em cache
        persona.reload()
        assert system_prompt() == "segunda versão"
    finally:
        persona.reload()
