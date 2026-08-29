"""
Testes de src/ai/router.py com modelos de raciocinio.

O 9Router desta maquina serve o glm-5.3-flash, que raciocina antes de
responder e cobra esse raciocinio do mesmo orcamento de tokens. Com
orcamento curto ele devolve, literalmente:

    "finish_reason": "length",
    "message": {"content": null, "reasoning": "The user has sent a..."}

O router pegava content=null, virava string vazia, e o ask_json morria
com "Expecting value: line 1 column 1 (char 0)" -- mensagem que nao diz
nada sobre a causa. Em uso, a MILK respondia "Nao consegui responder
agora" com a IA no ar e funcionando.
"""
import pytest

from ai.router import AIRouter


@pytest.fixture
def router(monkeypatch):
    monkeypatch.setenv("NINEROUTER_BASE_URL", "http://localhost:20128/v1")
    monkeypatch.setenv("NINEROUTER_MODEL", "modelo-de-teste")
    monkeypatch.setenv("NINEROUTER_API_KEY", "chave-de-teste")
    return AIRouter()


def resposta(conteudo, finish_reason="stop", reasoning=None):
    return {
        "choices": [{
            "finish_reason": finish_reason,
            "message": {"content": conteudo, "reasoning": reasoning},
        }]
    }


def test_orcamento_do_chat_cabe_um_modelo_de_raciocinio(router, monkeypatch):
    """220 ou 300 tokens nao sobrevivem a um modelo que pensa antes."""
    visto = {}

    def falso_post(payload):
        visto.update(payload)
        return resposta("tudo certo")

    monkeypatch.setattr(router, "_post", falso_post)
    router.chat("sistema", "pergunta")

    assert visto["max_tokens"] >= 1000


def test_orcamento_do_ask_json_cabe_um_modelo_de_raciocinio(router, monkeypatch):
    visto = {}

    def falso_post(payload):
        visto.update(payload)
        return resposta('{"intent": "ok"}')

    monkeypatch.setattr(router, "_post", falso_post)
    router.ask_json("sistema", "pergunta")

    assert visto["max_tokens"] >= 800


def test_conteudo_vazio_por_orcamento_diz_a_causa(router, monkeypatch, capsys):
    """
    "Expecting value: line 1 column 1" nao ajuda ninguem a consertar. A
    mensagem tem de nomear o que aconteceu: o raciocinio comeu o
    orcamento.
    """
    monkeypatch.setattr(
        router, "_post",
        lambda payload: resposta(None, finish_reason="length", reasoning="pensando..."),
    )

    assert router.ask_json("sistema", "pergunta") is None

    saida = capsys.readouterr().out
    assert "max_tokens" in saida
    assert "raciocínio" in saida or "raciocinio" in saida


def test_chat_com_conteudo_vazio_por_orcamento_tambem_avisa(router, monkeypatch, capsys):
    monkeypatch.setattr(
        router, "_post",
        lambda payload: resposta("", finish_reason="length", reasoning="pensando..."),
    )

    assert router.chat("sistema", "pergunta") is None
    assert "max_tokens" in capsys.readouterr().out


def test_resposta_normal_continua_passando(router, monkeypatch):
    monkeypatch.setattr(router, "_post", lambda payload: resposta("olá"))

    assert router.chat("sistema", "pergunta") == "olá"


def test_json_em_bloco_de_markdown_continua_sendo_lido(router, monkeypatch):
    monkeypatch.setattr(
        router, "_post",
        lambda payload: resposta('```json\n{"intent": "abrir"}\n```'),
    )

    assert router.ask_json("sistema", "pergunta") == {"intent": "abrir"}
