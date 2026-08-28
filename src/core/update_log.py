"""
Formata e grava o registro de atualizações do MILK.

Uma linha por atualização, para ser lida com tail e grep:

    2026-08-28 14:02  32.0 (c53d469) -> 32.1 (a1b2c3d)  OK
    2026-08-28 15:40  32.1 (a1b2c3d) -> 32.2 (e4f5g6h)  FALHOU: 2 testes  revertido
"""


def linha_de_log(quando, antes, depois, resultado, detalhe=None):
    """
    Monta a linha de uma atualização.

    quando: datetime. antes/depois: texto de versão já formatado.
    resultado: "OK" ou "FALHOU". detalhe: motivo, só quando falhou.
    """
    linha = "%s  %s -> %s  %s" % (
        quando.strftime("%Y-%m-%d %H:%M"),
        antes,
        depois,
        resultado,
    )
    if detalhe:
        # Quebras de linha destruiriam o formato de uma linha por registro.
        linha += ": " + " ".join(str(detalhe).splitlines())
    return linha


def registrar(caminho, linha):
    """Acrescenta a linha ao arquivo, criando o diretório se preciso."""
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open("a", encoding="utf-8") as arquivo:
        arquivo.write(linha + "\n")
