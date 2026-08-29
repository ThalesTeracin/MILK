"""
Testes de src/presence/avatar_motion.py.

Ate aqui o avatar era uma PNG parada com o brilho oscilando: nenhum
deslocamento, nenhuma mudanca de tamanho. Parecia uma foto acesa e
apagada, nao alguem ali. O movimento vem de funcoes puras do tempo, sem
estado e sem Tk, para poderem ser testadas e para um quadro perdido nao
deixar a animacao fora de fase.
"""
import numpy as np
import pytest

from presence.avatar_motion import ATIVIDADES_CONHECIDAS, quadro

CAMPOS = ("escala", "dx", "dy", "brilho")


@pytest.mark.parametrize("atividade", sorted(ATIVIDADES_CONHECIDAS))
def test_quadro_devolve_todos_os_campos(atividade):
    q = quadro(12.34, atividade)

    assert set(CAMPOS) <= set(q)
    assert all(isinstance(q[c], float) for c in CAMPOS)


@pytest.mark.parametrize("atividade", sorted(ATIVIDADES_CONHECIDAS))
def test_valores_ficam_dentro_do_sutil(atividade):
    """
    Movimento grande vira desenho animado, e a imagem sai do lugar onde o
    resto da janela espera encontra-la.
    """
    for t in np.arange(0, 120, 0.11):
        q = quadro(float(t), atividade)
        assert 0.97 <= q["escala"] <= 1.06
        assert abs(q["dx"]) <= 7.0
        assert abs(q["dy"]) <= 9.0
        assert 0.88 <= q["brilho"] <= 1.22


def test_atividade_desconhecida_nao_quebra():
    q = quadro(3.0, "telepatia")

    assert set(CAMPOS) <= set(q)


def test_e_deterministico():
    """
    Sem estado interno: o mesmo instante da o mesmo quadro. E o que
    permite perder um quadro sem a animacao pular de fase.
    """
    assert quadro(41.7, "speaking") == quadro(41.7, "speaking")


@pytest.mark.parametrize("atividade", sorted(ATIVIDADES_CONHECIDAS))
def test_e_continuo(atividade):
    """
    Salto entre quadros vizinhos aparece como tranco na tela. A 25 quadros
    por segundo o passo e 0,04 s.
    """
    anterior = quadro(0.0, atividade)
    for t in np.arange(0.04, 60, 0.04):
        atual = quadro(float(t), atividade)
        assert abs(atual["escala"] - anterior["escala"]) < 0.004
        assert abs(atual["dx"] - anterior["dx"]) < 0.6
        assert abs(atual["dy"] - anterior["dy"]) < 0.8
        assert abs(atual["brilho"] - anterior["brilho"]) < 0.02
        anterior = atual


@pytest.mark.parametrize("atividade", sorted(ATIVIDADES_CONHECIDAS))
def test_nunca_fica_parado(atividade):
    """
    O pedido era este: nada de estatica. Mesmo sem nada acontecendo, a
    respiracao continua.
    """
    escalas = [quadro(float(t), atividade)["escala"] for t in np.arange(0, 10, 0.05)]

    assert max(escalas) - min(escalas) > 0.004


def test_falando_se_mexe_mais_que_parada():
    def amplitude(atividade):
        e = [quadro(float(t), atividade)["escala"] for t in np.arange(0, 30, 0.05)]
        return max(e) - min(e)

    assert amplitude("speaking") > amplitude("idle")


def test_falando_respira_mais_rapido_que_parada():
    def cruzamentos(atividade):
        e = [quadro(float(t), atividade)["escala"] for t in np.arange(0, 30, 0.02)]
        media = sum(e) / len(e)
        return sum(1 for a, b in zip(e, e[1:]) if (a - media) * (b - media) < 0)

    assert cruzamentos("speaking") > cruzamentos("idle")


def test_o_balanco_nao_repete_junto_com_a_respiracao():
    """
    Se todos os periodos fossem multiplos, o conjunto voltaria ao mesmo
    ponto o tempo todo e a animacao pareceria um laco curto. Os periodos
    sao incomensuraveis de proposito.
    """
    def em(t):
        q = quadro(t, "idle")
        return (round(q["escala"], 4), round(q["dx"], 3), round(q["dy"], 3))

    inicio = em(0.0)
    iguais = sum(1 for t in np.arange(0.5, 300, 0.05) if em(float(t)) == inicio)
    assert iguais == 0
