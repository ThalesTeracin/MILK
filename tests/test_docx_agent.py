"""
Testes de src/documents/docx_agent.py.

O agente gera .docx sem python-docx/lxml: um .docx e um ZIP com partes
XML, e a stdlib (zipfile + xml) da conta do subconjunto que a MILK usa.
A motivacao e o Smart App Control do Windows, que bloqueia os .pyd do
lxml por baixa reputacao e derrubava o import de python-docx inteiro.

Os testes leem o pacote gerado de volta e conferem o XML real, em vez de
confiar que a chamada nao levantou excecao.
"""
import zipfile
from xml.etree import ElementTree as ET

import pytest

from documents.docx_agent import DocxAgent

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W}


def w(tag):
    return f"{{{W}}}{tag}"


@pytest.fixture
def agente():
    return DocxAgent()


def gerar(agente, tmp_path, title="Titulo", body=None, nome="saida.docx"):
    destino = tmp_path / nome
    retorno = agente.create(title, body, destino)
    return destino, retorno


def documento_xml(caminho):
    """Devolve a raiz de word/document.xml do pacote gerado."""
    with zipfile.ZipFile(caminho) as z:
        return ET.fromstring(z.read("word/document.xml"))


def paragrafos(raiz):
    return raiz.find("w:body", NS).findall("w:p", NS)


def texto_do(paragrafo):
    return "".join(no.text or "" for no in paragrafo.iter(w("t")))


def estilo_de(paragrafo):
    pstyle = paragrafo.find("w:pPr/w:pStyle", NS)
    return pstyle.get(w("val")) if pstyle is not None else None


# --------------------------------------------------------------- pacote

def test_cria_o_arquivo_e_devolve_o_caminho(agente, tmp_path):
    destino, retorno = gerar(agente, tmp_path)

    assert destino.exists()
    assert retorno == str(destino)


def test_cria_os_diretorios_pais_que_faltarem(agente, tmp_path):
    destino = tmp_path / "a" / "b" / "saida.docx"

    agente.create("Titulo", "corpo", destino)

    assert destino.exists()


def test_o_pacote_tem_as_partes_obrigatorias_do_ooxml(agente, tmp_path):
    destino, _ = gerar(agente, tmp_path)

    with zipfile.ZipFile(destino) as z:
        nomes = set(z.namelist())

    assert {
        "[Content_Types].xml",
        "_rels/.rels",
        "word/document.xml",
        "word/_rels/document.xml.rels",
        "word/styles.xml",
    } <= nomes


def test_todas_as_partes_xml_sao_bem_formadas(agente, tmp_path):
    destino, _ = gerar(agente, tmp_path, body="# Secao\n\nparagrafo")

    with zipfile.ZipFile(destino) as z:
        partes = [n for n in z.namelist() if n.endswith(".xml") or n.endswith(".rels")]
        assert partes
        for nome in partes:
            ET.fromstring(z.read(nome))  # levanta ParseError se malformado


# --------------------------------------------------------------- titulo

def test_o_titulo_e_o_primeiro_paragrafo(agente, tmp_path):
    destino, _ = gerar(agente, tmp_path, title="Relatorio Mensal")

    assert texto_do(paragrafos(documento_xml(destino))[0]) == "Relatorio Mensal"


def test_o_titulo_fica_centralizado_negrito_e_18pt(agente, tmp_path):
    destino, _ = gerar(agente, tmp_path, title="Relatorio")

    p = paragrafos(documento_xml(destino))[0]

    assert p.find("w:pPr/w:jc", NS).get(w("val")) == "center"
    assert p.find("w:r/w:rPr/w:b", NS) is not None
    # OOXML mede fonte em meios-pontos: 18pt == 36.
    assert p.find("w:r/w:rPr/w:sz", NS).get(w("val")) == "36"


def test_titulo_vazio_vira_o_rotulo_padrao(agente, tmp_path):
    destino, _ = gerar(agente, tmp_path, title=None)

    assert texto_do(paragrafos(documento_xml(destino))[0]) == "Documento"


# ----------------------------------------------------------------- corpo

def test_blocos_separados_por_linha_em_branco_viram_paragrafos(agente, tmp_path):
    destino, _ = gerar(agente, tmp_path, body="primeiro\n\nsegundo\n\nterceiro")

    corpo = [texto_do(p) for p in paragrafos(documento_xml(destino))[1:]]

    assert corpo == ["primeiro", "segundo", "terceiro"]


def test_blocos_vazios_sao_descartados(agente, tmp_path):
    destino, _ = gerar(agente, tmp_path, body="um\n\n\n\n   \n\ndois")

    corpo = [texto_do(p) for p in paragrafos(documento_xml(destino))[1:]]

    assert corpo == ["um", "dois"]


def test_corpo_ausente_deixa_so_o_titulo(agente, tmp_path):
    destino, _ = gerar(agente, tmp_path, body=None)

    assert len(paragrafos(documento_xml(destino))) == 1


def test_uma_cerquilha_vira_heading_1(agente, tmp_path):
    destino, _ = gerar(agente, tmp_path, body="# Introducao")

    p = paragrafos(documento_xml(destino))[1]

    assert estilo_de(p) == "Heading1"
    assert texto_do(p) == "Introducao"


def test_duas_cerquilhas_viram_heading_2(agente, tmp_path):
    destino, _ = gerar(agente, tmp_path, body="## Detalhe")

    p = paragrafos(documento_xml(destino))[1]

    assert estilo_de(p) == "Heading2"
    assert texto_do(p) == "Detalhe"


def test_paragrafo_comum_nao_recebe_estilo_de_heading(agente, tmp_path):
    destino, _ = gerar(agente, tmp_path, body="texto solto")

    assert estilo_de(paragrafos(documento_xml(destino))[1]) is None


def test_quebra_simples_dentro_do_bloco_e_preservada(agente, tmp_path):
    destino, _ = gerar(agente, tmp_path, body="linha um\nlinha dois")

    p = paragrafos(documento_xml(destino))[1]

    assert p.find("w:r/w:br", NS) is not None
    assert texto_do(p) == "linha umlinha dois"


# ------------------------------------------------------------- escaping

def test_caracteres_especiais_de_xml_sao_escapados(agente, tmp_path):
    destino, _ = gerar(agente, tmp_path, title="A & B", body="1 < 2 > 0")

    ps = paragrafos(documento_xml(destino))

    assert texto_do(ps[0]) == "A & B"
    assert texto_do(ps[1]) == "1 < 2 > 0"


def test_texto_com_marcacao_nao_injeta_elemento_no_documento(agente, tmp_path):
    destino, _ = gerar(agente, tmp_path, body="<w:p><w:r><w:t>injetado</w:t></w:r></w:p>")

    # Titulo + um unico paragrafo de corpo: a marcacao veio como texto.
    ps = paragrafos(documento_xml(destino))

    assert len(ps) == 2
    assert texto_do(ps[1]) == "<w:p><w:r><w:t>injetado</w:t></w:r></w:p>"


def test_espacos_das_pontas_sao_preservados_no_texto(agente, tmp_path):
    destino, _ = gerar(agente, tmp_path, body="palavra   com   espacos")

    no = documento_xml(destino).iter(w("t"))
    valores = [n.get("{http://www.w3.org/XML/1998/namespace}space") for n in no]

    # xml:space="preserve" evita que o Word colapse os espacos.
    assert all(v == "preserve" for v in valores)


# --------------------------------------------------------------- estilos

def test_a_fonte_normal_e_aptos_11pt(agente, tmp_path):
    destino, _ = gerar(agente, tmp_path)

    with zipfile.ZipFile(destino) as z:
        estilos = ET.fromstring(z.read("word/styles.xml"))

    normal = None
    for estilo in estilos.findall("w:style", NS):
        if estilo.get(w("styleId")) == "Normal":
            normal = estilo
            break

    assert normal is not None
    assert normal.find("w:rPr/w:rFonts", NS).get(w("ascii")) == "Aptos"
    assert normal.find("w:rPr/w:sz", NS).get(w("val")) == "22"


def test_os_estilos_de_heading_usados_estao_declarados(agente, tmp_path):
    destino, _ = gerar(agente, tmp_path, body="# a\n\n## b")

    with zipfile.ZipFile(destino) as z:
        estilos = ET.fromstring(z.read("word/styles.xml"))

    declarados = {e.get(w("styleId")) for e in estilos.findall("w:style", NS)}

    assert {"Heading1", "Heading2"} <= declarados


# ----------------------------------------------------- sem lxml/docx

def test_o_modulo_nao_importa_python_docx_nem_lxml():
    """
    O ponto da reescrita: nenhuma extensao nativa no caminho de import.
    Varre a arvore sintatica em vez do texto do fonte, para que comentario
    e docstring possam citar as bibliotecas que sairam.
    """
    import ast
    import inspect

    import documents.docx_agent as modulo

    arvore = ast.parse(inspect.getsource(modulo))

    importados = set()
    for no in ast.walk(arvore):
        if isinstance(no, ast.Import):
            importados.update(a.name.split(".")[0] for a in no.names)
        elif isinstance(no, ast.ImportFrom) and no.module:
            importados.add(no.module.split(".")[0])

    assert "docx" not in importados
    assert "lxml" not in importados
