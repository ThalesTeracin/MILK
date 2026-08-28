"""
Testes do rotulo do mini overlay.

O rotulo e a unica logica do mini que da para testar sem abrir janela,
entao ela sai do _tick para uma funcao propria. O caso que importa e o
estado velho: com a MILK fechada, o arquivo continua no disco dizendo
"thinking", e o mini nao pode repetir isso.
"""
from overlay.mini_overlay import rotulo_de


def test_ouvindo():
    assert rotulo_de("listening", True) == "MILK · OUVINDO"


def test_pensando():
    assert rotulo_de("thinking", True) == "MILK · PENSANDO"


def test_falando():
    assert rotulo_de("speaking", True) == "MILK · FALANDO"


def test_ociosa_e_fresca_esta_pronta():
    assert rotulo_de("idle", True) == "MILK · PRONTA"


def test_estado_velho_vira_desligada():
    """MILK fechada: o arquivo ficou para tras dizendo 'pensando'."""
    assert rotulo_de("thinking", False) == "MILK · DESLIGADA"


def test_ociosa_e_velha_tambem_e_desligada():
    assert rotulo_de("idle", False) == "MILK · DESLIGADA"
