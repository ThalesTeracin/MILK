"""
Testes do registro de atualizações.

Quando o MILK começar a se comportar mal, a primeira pergunta é "o que
mudou e quando". Este log é a resposta.
"""
import datetime

from core.update_log import linha_de_log, registrar

QUANDO = datetime.datetime(2026, 8, 28, 14, 2)


def test_linha_de_sucesso():
    linha = linha_de_log(QUANDO, "32.0 (c53d469)", "32.1 (a1b2c3d)", "OK")
    assert linha == "2026-08-28 14:02  32.0 (c53d469) -> 32.1 (a1b2c3d)  OK"


def test_linha_de_falha_traz_o_detalhe():
    linha = linha_de_log(
        QUANDO, "32.1 (a1b2c3d)", "32.2 (e4f5g6h)", "FALHOU", "2 testes  revertido"
    )
    assert linha.endswith("FALHOU: 2 testes  revertido")


def test_linha_nunca_tem_quebra_interna():
    """Uma linha por atualização: o log é lido com grep e tail."""
    linha = linha_de_log(QUANDO, "32.0", "32.1", "FALHOU", "erro\ncom quebra")
    assert "\n" not in linha


def test_registrar_cria_o_diretorio_e_acrescenta(tmp_path):
    destino = tmp_path / "logs" / "update.log"
    registrar(destino, "primeira")
    registrar(destino, "segunda")
    assert destino.read_text(encoding="utf-8").splitlines() == ["primeira", "segunda"]
