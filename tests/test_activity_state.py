"""
Testes de src/core/activity_state.py.

O modulo e o dono unico da atividade da MILK: guarda em memoria para quem
esta no mesmo processo e publica em data/milk_runtime_state.json para o
mini overlay, que roda em outro processo.

O carimbo de tempo existe porque o arquivo sobrevive ao processo. Sem ele,
com a MILK fechada o mini mostraria "pensando" para sempre.
"""
import json
import threading

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


# -------------------------------------------------------- concorrencia

def test_definir_e_pulsar_intercalados_nao_divergem(monkeypatch):
    """
    Prova propriedade invariante: com definir_atividade e pulsar
    intercaladas, memória e arquivo nunca divergem.

    A corrida: se ambas as funções escrevem em disco fora do lock,
    uma thread pode ler _atividade antigo, escrever no arquivo, e a
    outra thread depois escrever um valor mais novo. Se a escrita antiga
    terminar por último, o arquivo fica com atividade errada marcada
    como fresca — pior que estado velho.

    Com RLock e escrita serializada dentro do lock, o par
    (atividade, carimbo) é atômico: arquivo sempre tem exatamente
    o que a memória tem.
    """
    # Instrumenta _gravar para disparar pulsar durante a primeira gravação
    disparou = [False]
    thread_pulsar = [None]
    original_gravar = estado_mod._gravar

    def _gravar_com_disparo(nome):
        if not disparou[0]:
            disparou[0] = True
            # Dispara pulsar em paralelo sem aguardar
            thread_pulsar[0] = threading.Thread(target=pulsar)
            thread_pulsar[0].start()

        original_gravar(nome)

    monkeypatch.setattr(estado_mod, "_gravar", _gravar_com_disparo)

    # Define "thinking", que dispara pulsar em paralelo
    definir_atividade("thinking")

    # Define "speaking" (acontece depois que pulsar retorna)
    definir_atividade("speaking")

    # Aguarda thread disparada
    if thread_pulsar[0]:
        thread_pulsar[0].join()

    # Verifica que memória e arquivo estão sincronizados
    mem = atividade()
    arq, _ = ler_do_arquivo()
    assert mem == arq, f"Divergência: mem={mem!r}, arq={arq!r}"


def test_leitor_nunca_ve_o_arquivo_pela_metade(tmp_path, monkeypatch):
    """
    Enquanto a gravacao acontece, quem le de outro processo tem de ver o
    conteudo ANTIGO inteiro -- nunca um arquivo truncado.

    `write_text` truncava o alvo antes de escrever, e o leitor caia no
    `except` de ler_do_arquivo, que devolve "DESLIGADA" com a MILK viva.
    Medido antes da correcao: 682 de 1332 leituras concorrentes.

    O espiao le no unico instante em que o conteudo novo ja esta em disco
    e ainda nao foi publicado. Se alguem voltar a gravar por cima do alvo,
    `os.replace` deixa de ser chamado, `visto` fica vazio e este teste
    falha.
    """
    import os

    monkeypatch.setattr(estado_mod, "ARQUIVO", tmp_path / "runtime.json")
    definir_atividade("thinking")

    visto = []
    replace_real = os.replace

    def replace_espiao(origem, destino):
        visto.append(ler_do_arquivo()[0])
        return replace_real(origem, destino)

    monkeypatch.setattr(estado_mod.os, "replace", replace_espiao)

    pulsar()

    assert visto == ["thinking"]


def test_gravacao_recusada_nao_deixa_temporario_para_tras(tmp_path, monkeypatch):
    """Um .tmp orfao por pulso encheria data/ em uma sessao longa."""
    import os

    monkeypatch.setattr(estado_mod, "ARQUIVO", tmp_path / "runtime.json")
    definir_atividade("thinking")

    def replace_recusado(origem, destino):
        raise PermissionError("acesso negado")

    monkeypatch.setattr(estado_mod.os, "replace", replace_recusado)
    monkeypatch.setattr(estado_mod, "PAUSA_ENTRE_TENTATIVAS", 0)

    pulsar()

    assert list(tmp_path.glob("*.tmp")) == []
