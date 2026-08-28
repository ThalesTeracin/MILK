"""
Testes de src/documents/document_manager.py e do carregamento tardio do
agente de PPTX.

Contexto: python-pptx depende de lxml, cujos .pyd o Smart App Control do
Windows pode bloquear. Enquanto o import de pptx acontecia no topo de
pptx_agent.py, esse bloqueio derrubava o import de document_manager
inteiro -- e com ele DOCX, PDF e XLSX, que nao tem nada a ver com pptx.

O contrato testado aqui: importar sempre funciona, os formatos que nao
dependem da biblioteca ausente continuam gerando arquivo, e so o pedido
de PPTX degrada, devolvendo erro tratado em vez de estourar.
"""
import zipfile

import pytest

from documents.document_manager import DocumentManager


class AiFalso:
    """
    Dublê do AiRouter: devolve a spec fixa que lhe deram, sem rede.
    Registra a ultima chamada para os testes que precisam conferir.
    """

    def __init__(self, spec, enabled=True):
        self.spec = spec
        self.enabled = enabled
        self.chamadas = []

    def ask_json(self, system, request, max_tokens=None):
        self.chamadas.append(request)
        return self.spec


@pytest.fixture
def saida(tmp_path):
    return tmp_path / "output"


# ------------------------------------------------------------- importar

def test_o_modulo_importa_mesmo_sem_python_pptx():
    """
    O import de document_manager nao pode depender de biblioteca nativa.
    Se este teste falha na coleta, os outros nem chegam a rodar.
    """
    import documents.document_manager as modulo

    assert modulo.DocumentManager is not None


def test_pptx_agent_importa_sem_carregar_a_biblioteca():
    import documents.pptx_agent as modulo

    assert modulo.PptxAgent is not None


# ---------------------------------------------------- formatos que valem

def test_docx_e_gerado_de_ponta_a_ponta(saida):
    ai = AiFalso({
        "type": "docx",
        "filename": "relatorio.docx",
        "title": "Relatorio",
        "body": "# Secao\n\nconteudo",
    })

    resultado = DocumentManager(ai, output_dir=saida).create_from_request("faz um relatorio")

    assert resultado["ok"] is True
    assert resultado["type"] == "docx"
    assert zipfile.is_zipfile(resultado["path"])


def test_xlsx_e_gerado_de_ponta_a_ponta(saida):
    ai = AiFalso({
        "type": "xlsx",
        "filename": "dados.xlsx",
        "title": "Dados",
        "headers": ["a", "b"],
        "rows": [["1", "2"]],
    })

    resultado = DocumentManager(ai, output_dir=saida).create_from_request("planilha")

    assert resultado["ok"] is True
    assert zipfile.is_zipfile(resultado["path"])


# ------------------------------------------------------------- degradacao

def test_pptx_sem_a_biblioteca_devolve_erro_tratado(saida, monkeypatch):
    import documents.pptx_agent as pptx_agent

    def sem_biblioteca():
        raise ImportError("simulando python-pptx bloqueado")

    monkeypatch.setattr(pptx_agent, "_carregar", sem_biblioteca)

    ai = AiFalso({
        "type": "pptx",
        "filename": "deck.pptx",
        "title": "Deck",
        "slides": [{"title": "Um", "bullets": ["a"]}],
    })

    resultado = DocumentManager(ai, output_dir=saida).create_from_request("apresentacao")

    assert resultado["ok"] is False
    assert "pptx" in resultado["message"].lower()


def test_falha_de_pptx_nao_impede_docx_na_sequencia(saida, monkeypatch):
    import documents.pptx_agent as pptx_agent

    monkeypatch.setattr(
        pptx_agent, "_carregar", lambda: (_ for _ in ()).throw(ImportError("bloqueado"))
    )

    gerente = DocumentManager(AiFalso(None), output_dir=saida)

    gerente.ai.spec = {"type": "pptx", "filename": "d.pptx", "title": "D", "slides": []}
    assert gerente.create_from_request("deck")["ok"] is False

    gerente.ai.spec = {"type": "docx", "filename": "d.docx", "title": "D", "body": "x"}
    assert gerente.create_from_request("documento")["ok"] is True


# ------------------------------------------------------- guardas de entrada

def test_sem_ai_configurado_devolve_erro(saida):
    resultado = DocumentManager(AiFalso(None, enabled=False), output_dir=saida).create_from_request("x")

    assert resultado["ok"] is False


def test_tipo_desconhecido_devolve_erro(saida):
    ai = AiFalso({"type": "cdr", "filename": "x.cdr", "title": "X"})

    resultado = DocumentManager(ai, output_dir=saida).create_from_request("x")

    assert resultado["ok"] is False


def test_o_nome_do_arquivo_nao_escapa_do_diretorio_de_saida(saida):
    ai = AiFalso({
        "type": "docx",
        "filename": "../../fora.docx",
        "title": "X",
        "body": "y",
    })

    resultado = DocumentManager(ai, output_dir=saida).create_from_request("x")

    assert resultado["ok"] is True
    assert saida in __import__("pathlib").Path(resultado["path"]).parents
