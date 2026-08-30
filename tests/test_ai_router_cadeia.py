"""
Testes da cadeia de provedores do src/ai/router.py.

Ate a fase 33 o router falava com um gateway so, lido direto de
NINEROUTER_BASE_URL/MODEL/API_KEY. config/providers.json e
AI_PROVIDER_ORDER existiam no .env e eram conferidos pelo
Testar_Sistema.py, mas nenhum codigo em execucao os lia: com o 9Router
fora do ar a MILK ficava muda, sem ter para onde cair.

Estes testes fixam o contrato da cadeia: a ordem vem de
AI_PROVIDER_ORDER, os enderecos de config/providers.json (com o .env
podendo sobrepor cada um), e um gateway fora do ar passa a vez para o
proximo em vez de derrubar a resposta.
"""
import json

import pytest
import requests

import ai.router as router_mod
from ai.router import AIRouter


PROVEDORES = {
    "9router_custom": {
        "label": "9Router / Custom",
        "base_url": "",
        "model": "",
        "base_url_env": "NINEROUTER_BASE_URL",
        "model_env": "NINEROUTER_MODEL",
        "api_key_env": "NINEROUTER_API_KEY",
        "requires_key": True,
    },
    "omniroute": {
        "label": "OmniRoute",
        "base_url": "http://localhost:20128/v1",
        "model": "modelo-omni",
        "base_url_env": "OMNIROUTE_BASE_URL",
        "model_env": "OMNIROUTE_MODEL",
        "api_key_env": "OMNIROUTE_API_KEY",
        "requires_key": True,
    },
    "freellmapi": {
        "label": "FreeLLMAPI",
        "base_url": "http://localhost:3001/v1",
        "model": "modelo-free",
        "base_url_env": "FREELLMAPI_BASE_URL",
        "model_env": "FREELLMAPI_MODEL",
        "api_key_env": "FREELLMAPI_API_KEY",
        "requires_key": True,
    },
}

CHAVES = [
    "NINEROUTER_BASE_URL", "NINEROUTER_MODEL", "NINEROUTER_API_KEY",
    "OMNIROUTE_BASE_URL", "OMNIROUTE_MODEL", "OMNIROUTE_API_KEY",
    "FREELLMAPI_BASE_URL", "FREELLMAPI_MODEL", "FREELLMAPI_API_KEY",
    "AI_PROVIDER_ORDER",
]


@pytest.fixture(autouse=True)
def ambiente_limpo(tmp_path, monkeypatch):
    """
    Isola do .env real da maquina: o router chama load_dotenv() no
    import, entao sem esta limpeza uma chave de verdade no .env do
    projeto mudaria quem entra na cadeia, e o teste passaria (ou
    quebraria) por motivo errado.
    """
    for chave in CHAVES:
        monkeypatch.delenv(chave, raising=False)

    arquivo = tmp_path / "providers.json"
    arquivo.write_text(json.dumps(PROVEDORES), encoding="utf-8")
    monkeypatch.setattr(router_mod, "config_path", lambda nome: arquivo)


def conteudo(texto):
    return {"choices": [{"finish_reason": "stop",
                         "message": {"content": texto, "reasoning": None}}]}


class RespostaFalsa:
    def __init__(self, status_code=200, corpo=None, texto=""):
        self.status_code = status_code
        self._corpo = corpo if corpo is not None else conteudo("ok")
        self.text = texto

    def json(self):
        return self._corpo


@pytest.fixture
def http(monkeypatch):
    """Substitui requests.post e guarda as URLs realmente chamadas."""
    estado = {"respostas": [], "urls": [], "chaves": []}

    def post(url, headers=None, json=None, timeout=None):
        estado["urls"].append(url)
        estado["chaves"].append((headers or {}).get("Authorization"))
        acao = estado["respostas"].pop(0)
        if isinstance(acao, Exception):
            raise acao
        return acao

    monkeypatch.setattr(router_mod.requests, "post", post)
    return estado


def configura(monkeypatch, **variaveis):
    for nome, valor in variaveis.items():
        monkeypatch.setenv(nome, valor)


def test_a_ordem_do_env_define_quem_tenta_primeiro(monkeypatch, http):
    configura(
        monkeypatch,
        AI_PROVIDER_ORDER="freellmapi,omniroute",
        FREELLMAPI_API_KEY="chave-free",
        OMNIROUTE_API_KEY="chave-omni",
    )
    http["respostas"] = [RespostaFalsa()]

    AIRouter().chat("sistema", "pergunta")

    assert http["urls"] == ["http://localhost:3001/v1/chat/completions"]


def test_gateway_fora_do_ar_passa_a_vez_para_o_proximo(monkeypatch, http):
    """O 9Router desligado nao pode deixar a MILK muda."""
    configura(
        monkeypatch,
        AI_PROVIDER_ORDER="9router_custom,omniroute",
        NINEROUTER_BASE_URL="http://localhost:20128/v1",
        NINEROUTER_MODEL="glm-5.3-flash",
        NINEROUTER_API_KEY="chave-9r",
        OMNIROUTE_BASE_URL="http://localhost:30000/v1",
        OMNIROUTE_API_KEY="chave-omni",
    )
    http["respostas"] = [
        requests.exceptions.ConnectionError("recusou a conexao"),
        RespostaFalsa(corpo=conteudo("respondi pelo segundo")),
    ]

    assert AIRouter().chat("sistema", "pergunta") == "respondi pelo segundo"
    assert len(http["urls"]) == 2
    assert http["urls"][1].startswith("http://localhost:30000/v1")


def test_erro_http_tambem_passa_a_vez(monkeypatch, http):
    """Chave vencida devolve 401, nao excecao -- tem de cair igual."""
    configura(
        monkeypatch,
        AI_PROVIDER_ORDER="freellmapi,omniroute",
        FREELLMAPI_API_KEY="chave-vencida",
        OMNIROUTE_API_KEY="chave-omni",
    )
    http["respostas"] = [
        RespostaFalsa(status_code=401, texto="chave invalida"),
        RespostaFalsa(corpo=conteudo("segundo respondeu")),
    ]

    assert AIRouter().chat("sistema", "pergunta") == "segundo respondeu"


def test_provedor_sem_chave_nao_entra_na_cadeia(monkeypatch, http):
    configura(
        monkeypatch,
        AI_PROVIDER_ORDER="freellmapi,omniroute",
        OMNIROUTE_API_KEY="chave-omni",
    )
    http["respostas"] = [RespostaFalsa()]

    AIRouter().chat("sistema", "pergunta")

    assert http["urls"] == ["http://localhost:20128/v1/chat/completions"]


def test_env_sobrepoe_o_endereco_do_providers_json(monkeypatch, http):
    """Quem roda o OmniRoute em outra porta nao edita arquivo versionado."""
    configura(
        monkeypatch,
        AI_PROVIDER_ORDER="omniroute",
        OMNIROUTE_BASE_URL="http://localhost:9999/v1",
        OMNIROUTE_MODEL="outro-modelo",
        OMNIROUTE_API_KEY="chave-omni",
    )
    http["respostas"] = [RespostaFalsa()]

    AIRouter().chat("sistema", "pergunta")

    assert http["urls"] == ["http://localhost:9999/v1/chat/completions"]


def test_cada_provedor_recebe_a_propria_chave(monkeypatch, http):
    configura(
        monkeypatch,
        AI_PROVIDER_ORDER="freellmapi,omniroute",
        FREELLMAPI_API_KEY="chave-free",
        OMNIROUTE_API_KEY="chave-omni",
    )
    http["respostas"] = [
        RespostaFalsa(status_code=500, texto="caiu"),
        RespostaFalsa(),
    ]

    AIRouter().chat("sistema", "pergunta")

    assert http["chaves"] == ["Bearer chave-free", "Bearer chave-omni"]


def test_sem_nenhum_provedor_configurado_o_router_fica_desligado(monkeypatch):
    router = AIRouter()

    assert router.enabled is False
    assert router.chat("sistema", "pergunta") is None
    assert router.status() == "não configurado"


def test_status_nomeia_o_provedor_ativo(monkeypatch):
    configura(
        monkeypatch,
        AI_PROVIDER_ORDER="omniroute,freellmapi",
        OMNIROUTE_API_KEY="chave-omni",
        FREELLMAPI_API_KEY="chave-free",
    )

    status = AIRouter().status()

    assert "OmniRoute" in status
    assert "modelo-omni" in status


def test_comentario_no_arquivo_nao_vira_provedor(tmp_path, monkeypatch, http):
    """
    providers.json usa chaves "_note" para documentar, como o
    config/settings.json ja fazia. Sem esta guarda o router tratava a
    string do comentario como configuracao de provedor e estourava.
    """
    com_nota = {"_note": "documentação", **PROVEDORES}
    arquivo = tmp_path / "com_nota.json"
    arquivo.write_text(json.dumps(com_nota), encoding="utf-8")
    monkeypatch.setattr(router_mod, "config_path", lambda nome: arquivo)

    configura(monkeypatch, OMNIROUTE_API_KEY="chave-omni")
    http["respostas"] = [RespostaFalsa()]

    router = AIRouter()

    assert [p.id for p in router.provedores] == ["omniroute"]
    assert router.chat("sistema", "pergunta") == "ok"


def test_a_cadeia_inteira_fora_do_ar_devolve_none(monkeypatch, http):
    configura(
        monkeypatch,
        AI_PROVIDER_ORDER="freellmapi,omniroute",
        FREELLMAPI_API_KEY="chave-free",
        OMNIROUTE_API_KEY="chave-omni",
    )
    http["respostas"] = [
        requests.exceptions.ConnectionError("recusou"),
        requests.exceptions.ConnectionError("recusou"),
    ]

    assert AIRouter().chat("sistema", "pergunta") is None
