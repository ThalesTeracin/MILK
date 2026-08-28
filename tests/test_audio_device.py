"""
Testes de src/voice/audio_device.py.

O indice do microfone e escrito por Selecionar_Microfone.py em
config/local/audio_device.json. Ate a fase 32 nada lia esse arquivo: o
listener abria sempre o dispositivo padrao do Windows, e a escolha do
usuario nao tinha efeito nenhum.
"""
import json

import pytest

import voice.audio_device as audio_mod
from voice.audio_device import indice_de_entrada


@pytest.fixture
def config(tmp_path, monkeypatch):
    """Aponta o modulo para um audio_device.json controlado pelo teste."""
    destino = tmp_path / "audio_device.json"
    monkeypatch.setattr(audio_mod, "config_path", lambda nome: destino)
    return destino


def test_devolve_o_indice_escolhido(config):
    config.write_text(json.dumps({"input_device": 24}), encoding="utf-8")

    assert indice_de_entrada() == 24


def test_sem_arquivo_usa_o_padrao_do_sistema(config):
    assert indice_de_entrada() is None


def test_indice_zero_e_tratado_como_nao_configurado(config):
    """
    Mesma convencao do installer: 0 e o valor que vem do exemplo, nao uma
    escolha do usuario. Cair no padrao do sistema e mais seguro do que
    abrir o dispositivo 0, que raramente e o microfone certo.
    """
    config.write_text(json.dumps({"input_device": 0}), encoding="utf-8")

    assert indice_de_entrada() is None


def test_campo_ausente_usa_o_padrao_do_sistema(config):
    config.write_text(json.dumps({"outra_coisa": 1}), encoding="utf-8")

    assert indice_de_entrada() is None


def test_json_invalido_nao_derruba_a_voz(config, capsys):
    """
    Config corrompida nao pode impedir o MILK de ouvir: avisa e cai no
    dispositivo padrao.
    """
    config.write_text("{isso nao e json", encoding="utf-8")

    assert indice_de_entrada() is None
    assert "audio_device.json" in capsys.readouterr().out


def test_valor_nao_inteiro_e_recusado(config, capsys):
    """sounddevice aceita nome de dispositivo, mas o arquivo so guarda indice."""
    config.write_text(json.dumps({"input_device": "Microfone (Realtek)"}), encoding="utf-8")

    assert indice_de_entrada() is None
    assert "audio_device.json" in capsys.readouterr().out


def test_le_o_arquivo_com_bom(config):
    """Selecionar_Microfone.py grava em utf-8; editores do Windows podem por BOM."""
    config.write_text(json.dumps({"input_device": 7}), encoding="utf-8-sig")

    assert indice_de_entrada() == 7
