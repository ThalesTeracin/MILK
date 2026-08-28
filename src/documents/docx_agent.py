"""
Geracao de .docx sem dependencia nativa.

Motivo da reescrita: python-docx depende de lxml, e o Smart App Control
do Windows bloqueia os .pyd do lxml por baixa reputacao ("Uma politica de
Controle de Aplicativo bloqueou este arquivo"), derrubando o import do
pacote inteiro. Um .docx e apenas um ZIP com partes XML, e o subconjunto
que a MILK usa -- titulo, dois niveis de heading e paragrafos -- cabe na
biblioteca padrao. Sem extensao nativa, nao ha o que a politica bloquear.

O pacote gerado tem o minimo que o Word exige para abrir sem reparo:

    [Content_Types].xml           declara o tipo de cada parte
    _rels/.rels                   aponta a parte principal do documento
    word/document.xml             o conteudo
    word/_rels/document.xml.rels  liga o documento aos estilos
    word/styles.xml               Normal, Heading1 e Heading2

A interface publica (DocxAgent.create) e identica a da versao anterior,
entao documents/document_manager.py nao muda.
"""

import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
PKG_RELS = "http://schemas.openxmlformats.org/package/2006/relationships"
OFFICE_RELS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
CT = "http://schemas.openxmlformats.org/package/2006/content-types"
WORD_CT = "application/vnd.openxmlformats-officedocument.wordprocessingml"

CABECALHO = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'

# OOXML mede tamanho de fonte em meios-pontos: 11pt vira 22.
FONTE_PADRAO = "Aptos"
TAMANHO_PADRAO = 22
TAMANHO_TITULO = 36
TAMANHO_HEADING = {1: 32, 2: 26}

CONTENT_TYPES = CABECALHO + (
    f'<Types xmlns="{CT}">'
    '<Default Extension="rels"'
    ' ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
    '<Default Extension="xml" ContentType="application/xml"/>'
    '<Override PartName="/word/document.xml"'
    f' ContentType="{WORD_CT}.document.main+xml"/>'
    '<Override PartName="/word/styles.xml"'
    f' ContentType="{WORD_CT}.styles+xml"/>'
    "</Types>"
)

RELS_RAIZ = CABECALHO + (
    f'<Relationships xmlns="{PKG_RELS}">'
    f'<Relationship Id="rId1" Type="{OFFICE_RELS}/officeDocument"'
    ' Target="word/document.xml"/>'
    "</Relationships>"
)

RELS_DOCUMENTO = CABECALHO + (
    f'<Relationships xmlns="{PKG_RELS}">'
    f'<Relationship Id="rId1" Type="{OFFICE_RELS}/styles" Target="styles.xml"/>'
    "</Relationships>"
)


def _estilo_heading(nivel):
    return (
        f'<w:style w:type="paragraph" w:styleId="Heading{nivel}">'
        f'<w:name w:val="heading {nivel}"/>'
        '<w:basedOn w:val="Normal"/>'
        f'<w:pPr><w:outlineLvl w:val="{nivel - 1}"/>'
        '<w:spacing w:before="240" w:after="120"/></w:pPr>'
        "<w:rPr><w:b/>"
        f'<w:sz w:val="{TAMANHO_HEADING[nivel]}"/>'
        f'<w:szCs w:val="{TAMANHO_HEADING[nivel]}"/></w:rPr>'
        "</w:style>"
    )


STYLES = CABECALHO + (
    f'<w:styles xmlns:w="{W}">'
    "<w:docDefaults><w:rPrDefault><w:rPr>"
    f'<w:rFonts w:ascii="{FONTE_PADRAO}" w:hAnsi="{FONTE_PADRAO}"'
    f' w:cs="{FONTE_PADRAO}"/>'
    f'<w:sz w:val="{TAMANHO_PADRAO}"/><w:szCs w:val="{TAMANHO_PADRAO}"/>'
    "</w:rPr></w:rPrDefault></w:docDefaults>"
    '<w:style w:type="paragraph" w:default="1" w:styleId="Normal">'
    '<w:name w:val="Normal"/>'
    "<w:rPr>"
    f'<w:rFonts w:ascii="{FONTE_PADRAO}" w:hAnsi="{FONTE_PADRAO}"'
    f' w:cs="{FONTE_PADRAO}"/>'
    f'<w:sz w:val="{TAMANHO_PADRAO}"/><w:szCs w:val="{TAMANHO_PADRAO}"/>'
    "</w:rPr></w:style>"
    + _estilo_heading(1)
    + _estilo_heading(2)
    + "</w:styles>"
)

# Retrato A4 com margens de 2cm, em twips (1cm = 567 twips).
SECAO = (
    "<w:sectPr>"
    '<w:pgSz w:w="11906" w:h="16838"/>'
    '<w:pgMar w:top="1134" w:right="1134" w:bottom="1134" w:left="1134"'
    ' w:header="708" w:footer="708" w:gutter="0"/>'
    "</w:sectPr>"
)


def _normalizar(texto):
    """
    Reduz \r\n e \r sozinho a \n.

    Texto vindo do Windows chega com \r\n. Sem isso, o separador de
    bloco "\n\n" nunca casa e o documento inteiro vira um paragrafo
    so; o \r que sobra ainda entra no w:t e suja o conteudo.
    """
    return texto.replace("\r\n", "\n").replace("\r", "\n")


def _run(texto, negrito=False, tamanho=None):
    """
    Um w:r com o texto dado. Quebra simples vira w:br dentro do mesmo run,
    para que o bloco continue sendo um paragrafo so.
    """
    propriedades = ""
    if negrito or tamanho:
        propriedades = (
            "<w:rPr>"
            + ("<w:b/>" if negrito else "")
            + (f'<w:sz w:val="{tamanho}"/><w:szCs w:val="{tamanho}"/>' if tamanho else "")
            + "</w:rPr>"
        )

    partes = []
    for i, linha in enumerate(_normalizar(texto).split("\n")):
        if i:
            partes.append("<w:br/>")
        # xml:space="preserve" impede o Word de colapsar os espacos.
        partes.append(f'<w:t xml:space="preserve">{escape(linha)}</w:t>')

    return f"<w:r>{propriedades}{''.join(partes)}</w:r>"


def _paragrafo(texto, estilo=None, centralizado=False, negrito=False, tamanho=None):
    propriedades = ""
    if estilo or centralizado:
        propriedades = (
            "<w:pPr>"
            + (f'<w:pStyle w:val="{estilo}"/>' if estilo else "")
            + ('<w:jc w:val="center"/>' if centralizado else "")
            + "</w:pPr>"
        )

    return f"<w:p>{propriedades}{_run(texto, negrito, tamanho)}</w:p>"


def _corpo_em_paragrafos(body):
    """
    Converte o corpo em paragrafos XML. Blocos sao separados por linha em
    branco; '# ' e '## ' no inicio do bloco viram heading.
    """
    paragrafos = []
    for bloco in _normalizar(body or "").split("\n\n"):
        bloco = bloco.strip()
        if not bloco:
            continue
        if bloco.startswith("# "):
            paragrafos.append(_paragrafo(bloco[2:].strip(), estilo="Heading1"))
        elif bloco.startswith("## "):
            paragrafos.append(_paragrafo(bloco[3:].strip(), estilo="Heading2"))
        else:
            paragrafos.append(_paragrafo(bloco))
    return paragrafos


class DocxAgent:
    def create(self, title, body, output_path):
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        paragrafos = [
            _paragrafo(
                title or "Documento",
                centralizado=True,
                negrito=True,
                tamanho=TAMANHO_TITULO,
            )
        ]
        paragrafos.extend(_corpo_em_paragrafos(body))

        documento = CABECALHO + (
            f'<w:document xmlns:w="{W}"><w:body>'
            + "".join(paragrafos)
            + SECAO
            + "</w:body></w:document>"
        )

        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("[Content_Types].xml", CONTENT_TYPES)
            z.writestr("_rels/.rels", RELS_RAIZ)
            z.writestr("word/document.xml", documento)
            z.writestr("word/_rels/document.xml.rels", RELS_DOCUMENTO)
            z.writestr("word/styles.xml", STYLES)

        return str(path)
