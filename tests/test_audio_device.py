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
from voice.audio_device import indice_de_entrada, perfil_de_captura


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


# ------------------------------------------------- microfone por nome
#
# Um indice do PortAudio nao identifica um microfone entre reinicios.
# Conectar ou desconectar um fone insere ou remove entradas na lista e
# renumera tudo o que vem depois. Observado nesta maquina, na mesma
# sessao, com o headset saindo da lista entre uma enumeracao e outra:
#
#   antes:  15 | Windows WASAPI | Grupo de Microfones (Qualcomm) | 48000
#   depois: 15 | Windows WDM-KS | Headset ()                     |  8000
#
# O MILK abriu o dispositivo errado sem reclamar -- o indice continuava
# valido, so apontava para outro aparelho -- e o Whisper transcreveu
# ruido ("[MUSICA DE FUNDO]", "BALF!") em vez da fala. Por isso o arquivo
# passa a guardar nome e host API, e o indice e resolvido na abertura.


@pytest.fixture
def entradas(monkeypatch):
    """Substitui a enumeracao do PortAudio por uma lista controlada."""
    lista = []
    monkeypatch.setattr(audio_mod, "listar_entradas", lambda: lista)
    return lista


def test_resolve_o_indice_atual_pelo_nome(config, entradas):
    """O caso que quebrou: o indice salvo envelheceu, o nome não."""
    entradas.extend([
        (0, "Mapeador de som da Microsoft - Input", "MME"),
        (9, "Grupo de Microfones (Qualcomm)", "Windows WASAPI"),
        (15, "Headset ()", "Windows WDM-KS"),
    ])
    config.write_text(json.dumps({
        "input_name": "Grupo de Microfones (Qualcomm)",
        "input_hostapi": "Windows WASAPI",
        "input_device": 15,
    }), encoding="utf-8")

    assert indice_de_entrada() == 9


def test_o_nome_manda_no_indice_salvo(config, entradas):
    """
    O indice fica no arquivo só como registro do que foi escolhido. Se
    ele mandasse, a correção não teria efeito nenhum.
    """
    entradas.extend([
        (3, "Microfone do Headset", "Windows WASAPI"),
        (9, "Grupo de Microfones (Qualcomm)", "Windows WASAPI"),
    ])
    config.write_text(json.dumps({
        "input_name": "Grupo de Microfones (Qualcomm)",
        "input_hostapi": "Windows WASAPI",
        "input_device": 3,
    }), encoding="utf-8")

    assert indice_de_entrada() == 9


def test_microfone_salvo_ausente_avisa_e_cai_no_padrao(config, entradas, capsys):
    """
    Desconectou o microfone escolhido. Abrir o vizinho calado seria o
    defeito de novo; o certo é dizer qual sumiu e usar o padrão.
    """
    entradas.extend([(0, "Mapeador de som da Microsoft - Input", "MME")])
    config.write_text(json.dumps({
        "input_name": "Microfone do Headset",
        "input_hostapi": "Windows WASAPI",
        "input_device": 3,
    }), encoding="utf-8")

    assert indice_de_entrada() is None
    assert "Microfone do Headset" in capsys.readouterr().out


def test_mesmo_nome_em_outra_host_api_nao_casa(config, entradas, capsys):
    """
    O mesmo aparelho aparece sob várias host APIs, e elas não são
    intercambiáveis: o WDM-KS desta máquina nem abre em modo bloqueante
    ('Blocking API not supported yet'). Casar só o nome traria de volta o
    dispositivo que não funciona.
    """
    entradas.extend([(18, "Grupo de Microfones (Qualcomm)", "Windows WDM-KS")])
    config.write_text(json.dumps({
        "input_name": "Grupo de Microfones (Qualcomm)",
        "input_hostapi": "Windows WASAPI",
    }), encoding="utf-8")

    assert indice_de_entrada() is None
    assert "Windows WASAPI" in capsys.readouterr().out


def test_nome_sem_host_api_casa_so_pelo_nome(config, entradas):
    """Arquivo escrito à mão, sem a host API: ainda melhor que índice."""
    entradas.extend([(9, "Grupo de Microfones (Qualcomm)", "Windows WASAPI")])
    config.write_text(json.dumps({
        "input_name": "Grupo de Microfones (Qualcomm)",
    }), encoding="utf-8")

    assert indice_de_entrada() == 9


def test_config_antiga_so_com_indice_continua_valendo(config, entradas):
    """
    Quem já tem o arquivo antigo não fica sem microfone até rodar o
    Selecionar_Microfone.py de novo.
    """
    entradas.extend([(24, "Microphone Array", "Windows WDM-KS")])
    config.write_text(json.dumps({"input_device": 24}), encoding="utf-8")

    assert indice_de_entrada() == 24


def test_nome_que_nao_e_texto_cai_no_indice(config, entradas):
    entradas.extend([(9, "Grupo de Microfones (Qualcomm)", "Windows WASAPI")])
    config.write_text(json.dumps({"input_name": 7, "input_device": 24}), encoding="utf-8")

    assert indice_de_entrada() == 24


def test_enumeracao_que_falha_nao_deixa_o_milk_sem_voz(config, monkeypatch, capsys):
    """Sem placa de áudio o query_devices levanta; isso não pode subir."""
    def explode():
        raise OSError("PortAudio não inicializou")

    monkeypatch.setattr(audio_mod, "listar_entradas", explode)
    config.write_text(json.dumps({
        "input_name": "Grupo de Microfones (Qualcomm)",
    }), encoding="utf-8")

    assert indice_de_entrada() is None
    assert "PortAudio" in capsys.readouterr().out


# ------------------------------------------------- perfil de captura
#
# Falar de perto e falar do outro lado da sala pedem ajustes opostos. De
# perto o risco e saturar: o endpoint desta maquina vinha com +24 dB, o
# topo da faixa, e a fala batia no teto do int16 em 1,5% das amostras --
# o Whisper devolvia "[GRITOS DE GOL]" no lugar de palavras. De longe o
# risco e o contrario: o gatilho nao dispara e a frase e cortada antes do
# fim.


def test_perfil_padrao_e_perto(config):
    config.write_text(json.dumps({"input_name": "x"}), encoding="utf-8")

    assert perfil_de_captura()["nome"] == "perto"


def test_sem_arquivo_o_perfil_ainda_e_perto(config):
    assert perfil_de_captura()["nome"] == "perto"


def test_perfil_longe_dispara_com_menos_som(config):
    config.write_text(json.dumps({"perfil": "longe"}), encoding="utf-8")

    longe = perfil_de_captura()
    config.write_text(json.dumps({"perfil": "perto"}), encoding="utf-8")
    perto = perfil_de_captura()

    assert longe["limiar_rms"] < perto["limiar_rms"]


def test_perfil_longe_espera_mais_pelo_fim_da_frase(config):
    """De longe a fala chega mais fraca, e uma pausa curta parece silêncio."""
    config.write_text(json.dumps({"perfil": "longe"}), encoding="utf-8")

    longe = perfil_de_captura()
    config.write_text(json.dumps({"perfil": "perto"}), encoding="utf-8")
    perto = perfil_de_captura()

    assert longe["silencio_para_parar"] > perto["silencio_para_parar"]
    assert longe["duracao_maxima"] >= perto["duracao_maxima"]


def test_perfil_longe_pede_mais_ganho(config):
    config.write_text(json.dumps({"perfil": "longe"}), encoding="utf-8")

    longe = perfil_de_captura()
    config.write_text(json.dumps({"perfil": "perto"}), encoding="utf-8")
    perto = perfil_de_captura()

    assert longe["ganho_db"] > perto["ganho_db"]


def test_perfil_desconhecido_avisa_e_cai_no_perto(config, capsys):
    config.write_text(json.dumps({"perfil": "telepatia"}), encoding="utf-8")

    assert perfil_de_captura()["nome"] == "perto"
    assert "telepatia" in capsys.readouterr().out


def test_arquivo_ilegivel_nao_derruba_o_perfil(config):
    config.write_text("{isso nao e json", encoding="utf-8")

    assert perfil_de_captura()["nome"] == "perto"
