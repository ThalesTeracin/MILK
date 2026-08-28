"""
Testes de src/core/activity_state.py.

O modulo e o dono unico da atividade da MILK: guarda em memoria para quem
esta no mesmo processo e publica em data/milk_runtime_state.json para o
mini overlay, que roda em outro processo.

O carimbo de tempo existe porque o arquivo sobrevive ao processo. Sem ele,
com a MILK fechada o mini mostraria "pensando" para sempre.
"""
import json

import pytest

import core.activity_state as estado_mod
from core.activity_state import (
    atividade,
    definir_atividade,
    ler_do_arquivo,
    pulsar,
)


@pytest.fixture(autouse=True)
def arquivo_isolado(tmp_path, monkeypatch):
    """Cada teste escreve no seu proprio arquivo e comeca em 'idle'."""
    monkeypatch.setattr(estado_mod, "ARQUIVO", tmp_path / "runtime.json")
    monkeypatch.setattr(estado_mod, "_atividade", "idle")
    return tmp_path / "runtime.json"


# ------------------------------------------------------- memoria

def test_comeca_ocioso():
    assert atividade() == "idle"


def test_definir_muda_o_valor_em_memoria():
    definir_atividade("thinking")

    assert atividade() == "thinking"


def test_atividade_desconhecida_e_recusada():
    """Um erro de digitacao viraria um estado que nenhum overlay sabe pintar."""
    with pytest.raises(ValueError):
        definir_atividade("pensando")


# -------------------------------------------------------- arquivo

def test_definir_publica_no_arquivo(arquivo_isolado):
    definir_atividade("speaking")

    dados = json.loads(arquivo_isolado.read_text(encoding="utf-8"))
    assert dados["activity"] == "speaking"
    assert isinstance(dados["at"], (int, float))


def test_le_de_volta_o_que_escreveu():
    definir_atividade("listening")

    assert ler_do_arquivo() == ("listening", True)


def test_sem_arquivo_devolve_ocioso_e_nao_fresco():
    assert ler_do_arquivo() == ("idle", False)


def test_arquivo_corrompido_devolve_ocioso_e_nao_fresco(arquivo_isolado):
    arquivo_isolado.write_text("{isso nao e json", encoding="utf-8")

    assert ler_do_arquivo() == ("idle", False)


def test_atividade_desconhecida_no_arquivo_nao_e_aceita(arquivo_isolado):
    """Arquivo de uma versao antiga, ou editado a mao."""
    arquivo_isolado.write_text(
        json.dumps({"activity": "dancando", "at": 1.0}), encoding="utf-8"
    )

    assert ler_do_arquivo(agora=1.0) == ("idle", False)


# -------------------------------------------------------- frescor

def test_carimbo_velho_nao_e_fresco(arquivo_isolado):
    """O sintoma que isso evita: MILK fechada e o mini dizendo 'pensando'."""
    arquivo_isolado.write_text(
        json.dumps({"activity": "thinking", "at": 1000.0}), encoding="utf-8"
    )

    nome, fresco = ler_do_arquivo(agora=1000.0 + estado_mod.LIMITE_DE_FRESCOR + 1)

    assert nome == "thinking"
    assert fresco is False


def test_carimbo_dentro_do_limite_e_fresco(arquivo_isolado):
    arquivo_isolado.write_text(
        json.dumps({"activity": "thinking", "at": 1000.0}), encoding="utf-8"
    )

    assert ler_do_arquivo(agora=1000.5) == ("thinking", True)


def test_pulsar_renova_o_carimbo_sem_mudar_a_atividade(arquivo_isolado):
    definir_atividade("listening")
    arquivo_isolado.write_text(
        json.dumps({"activity": "listening", "at": 1.0}), encoding="utf-8"
    )
    assert ler_do_arquivo()[1] is False

    pulsar()

    assert ler_do_arquivo() == ("listening", True)


# ---------------------------------------------------------- falha

def test_falha_ao_gravar_nao_derruba_a_voz(monkeypatch, capsys):
    """
    O estado e conveniencia de interface. Disco cheio ou arquivo travado
    por antivirus nao pode impedir a MILK de continuar funcionando.
    """
    def explode(*a, **k):
        raise OSError("disco cheio")

    monkeypatch.setattr(estado_mod.Path, "write_text", explode)

    definir_atividade("speaking")

    assert atividade() == "speaking"
    assert "milk" in capsys.readouterr().out.lower()
